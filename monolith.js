import { Worker } from 'worker_threads';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import express from 'express';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 7860;

app.use(express.json()); // Để nhận webhook JSON

// Health check endpoint cho Render
app.get('/', (req, res) => {
    res.send('Zalo AI Monolith (Bích, Cường, XAU, Telegram) is running 24/7 🚀');
});
app.get('/ping', (req, res) => {
    res.status(200).json({ status: 'alive', uptime: process.uptime() });
});

// Forward Webhook từ TradingView (bên ngoài) vào XAU Bot (nội bộ cổng 7861)
app.post('/webhook', async (req, res) => {
    try {
        const response = await fetch('http://localhost:7861/webhook', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req.body)
        });
        const data = await response.text();
        res.status(response.status).send(data);
    } catch (err) {
        console.error('[MONOLITH WEBHOOK ERROR]', err);
        res.status(500).send('Internal Monolith Error');
    }
});

// Phục vụ tĩnh Web App CEO Voice Assistant
app.use('/ceo', express.static(path.join(__dirname, 'ceo-voice-assistant', 'dist')));

app.listen(PORT, () => {
    console.log(`\n🚀 [MONOLITH] Health & Web Server listening on port ${PORT}`);
});

// Hàm khởi chạy Node.js Worker
function startNodeWorker(name, scriptPath, customEnv = {}, maxMemoryMB = 64) {
    const workerDir = path.dirname(scriptPath).replace('/src', '');
    console.log(`[MONOLITH] Khởi động Worker: ${name} (Max RAM: ${maxMemoryMB}MB, CWD: ${workerDir})...`);
    
    // Inject mã để cô lập process.cwd() cho từng worker
    const evalCode = `
        const path = require('path');
        process.cwd = () => '${workerDir}';
        import('file://' + '${scriptPath}').catch(err => {
            console.error('Worker Import Error:', err);
            process.exit(1);
        });
    `;

    const worker = new Worker(evalCode, {
        eval: true,
        resourceLimits: { maxOldGenerationSizeMb: maxMemoryMB },
        env: {
            ...process.env,
            ...customEnv
        }
    });

    worker.on('message', (msg) => {
        console.log(`[${name}] ${msg}`);
    });

    worker.on('error', (err) => {
        console.error(`[${name}] LỖI:`, err);
    });

    worker.on('exit', (code) => {
        console.log(`[${name}] Dừng hoạt động với mã ${code}. Tự động khởi động lại sau 10 giây...`);
        setTimeout(() => startNodeWorker(name, scriptPath, customEnv, maxMemoryMB), 10000);
    });
}

// Các token chuẩn xác cho từng bot
const TONY_TRADING_TOKEN = '8623878114:AAEvt-qcOGDx2Cykpw-Z-786GLCPZEe3ZKM'; // Dành cho Python Crypto Trading Bot
const THONG_DONG_TOKEN = '8885833462:AAE-ISO4qQ5KpkzYkEnoFyWeVdZ5YMYAGDA'; // Dành cho XAU Algo Bot
const SECRETARY_TOKEN = '8968670034:AAEv_aQj3wUJu36OgOLMj1NbfUmy38UPxXQ'; // Dành cho Thư Kí và Zalo Bots
const CHAT_ID = '1389725436';

console.log('\n======================================================');
console.log('   🔥 KHỞI ĐỘNG HỆ THỐNG ZALO AI MONOLITH 🔥');
console.log('======================================================\n');

// 1. Khởi động Zalo Bot Bích (96MB)
startNodeWorker('Bot-Bich', path.join(__dirname, 'bich-bot', 'src', 'index.js'), {
    ZALO_CREDENTIALS_PATH: './zalo-credentials.json',
    ZALO_ACCOUNT_NAME: 'Cô Lưu Bích',
    TELEGRAM_BOT_TOKEN: SECRETARY_TOKEN,
    TELEGRAM_CHAT_ID: CHAT_ID
}, 96);

// 2. Khởi động Zalo Bot Cường (96MB)
// Để tránh tải nặng cùng lúc, delay 10 giây trước khi bật Cường
setTimeout(() => {
    startNodeWorker('Bot-Cuong', path.join(__dirname, 'cuong-bot', 'src', 'index.js'), {
        ZALO_CREDENTIALS_PATH: './zalo-credentials-cuong.json',
        ZALO_ACCOUNT_NAME: 'Trợ Lý Cường',
        TELEGRAM_BOT_TOKEN: SECRETARY_TOKEN,
        TELEGRAM_CHAT_ID: CHAT_ID
    }, 96);
}, 10000);

// 3. Khởi động Telegram Secretary (48MB)
setTimeout(() => {
    startNodeWorker('Telegram-Secretary', path.join(__dirname, 'telegram-secretary', 'bot.js'), {
        SECRETARY_BOT_TOKEN: SECRETARY_TOKEN,
        TELEGRAM_CHAT_ID: CHAT_ID
    }, 48);
}, 20000);

// 4. Khởi động XAU Algo Bot (48MB)
setTimeout(() => {
    startNodeWorker('XAU-Algo-Bot', path.join(__dirname, 'tradingview-xau-alert', 'server.js'), {
        PORT: 7861, // Tránh đụng cổng 7860
        TELEGRAM_BOT_TOKEN: THONG_DONG_TOKEN,
        TELEGRAM_CHAT_ID: CHAT_ID // Tạm thời gửi về sếp Cường vì Group lỗi "chat not found"
    }, 48);
}, 30000);

// Hàm khởi chạy Python Process
function startPythonProcess(name, scriptDir, scriptName, customEnv = {}) {
    console.log(`[MONOLITH] Khởi động Python Process: ${name}...`);
    
    const py = spawn('python3', [scriptName], {
        cwd: path.join(__dirname, scriptDir),
        env: {
            ...process.env,
            ...customEnv
        }
    });

    py.stdout.on('data', (data) => console.log(`[${name}] ${data.toString().trim()}`));
    py.stderr.on('data', (data) => console.error(`[${name}] ${data.toString().trim()}`));
    
    py.on('close', (code) => {
        console.log(`[${name}] Dừng hoạt động với mã ${code}. Tự động khởi động lại sau 10 giây...`);
        setTimeout(() => startPythonProcess(name, scriptDir, scriptName, customEnv), 10000);
    });
}

// 5. Khởi động Python Trading Bot
setTimeout(() => {
    startPythonProcess('Tony-Trading-Bot', 'trading-bot', 'bot.py', {
        TELEGRAM_BOT_TOKEN: TONY_TRADING_TOKEN,
        TELEGRAM_CHAT_ID: CHAT_ID
    });
}, 40000);
