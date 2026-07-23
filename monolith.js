import { Worker } from 'worker_threads';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import express from 'express';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 7860;

// Health check endpoint cho Render
app.get('/', (req, res) => {
    res.send('Zalo AI Monolith (Bích, Cường, XAU, Telegram) is running 24/7 🚀');
});
app.get('/ping', (req, res) => {
    res.status(200).json({ status: 'alive', uptime: process.uptime() });
});

// Phục vụ tĩnh Web App CEO Voice Assistant
// Phải chạy npm run build bên trong ceo-voice-assistant trước
app.use('/ceo', express.static(path.join(__dirname, 'ceo-voice-assistant', 'dist')));

app.listen(PORT, () => {
    console.log(`\n🚀 [MONOLITH] Health & Web Server listening on port ${PORT}`);
});

// Hàm khởi chạy Node.js Worker
function startNodeWorker(name, scriptPath, customEnv = {}) {
    console.log(`[MONOLITH] Khởi động Worker: ${name}...`);
    
    const worker = new Worker(scriptPath, {
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
        console.log(`[${name}] Dừng hoạt động với mã ${code}. Tự động khởi động lại sau 5 giây...`);
        setTimeout(() => startNodeWorker(name, scriptPath, customEnv), 5000);
    });
}

// Hàm khởi chạy Python Process
function startPythonProcess(name, scriptDir, scriptName, customEnv = {}) {
    console.log(`[MONOLITH] Khởi động Python Process: ${name}...`);
    
    const py = spawn('python3', [scriptName], {
        cwd: path.join(__dirname, scriptDir),
        env: {
            ...process.env,
            ...customEnv
        },
        stdio: 'inherit'
    });

    py.on('error', (err) => {
        console.error(`[${name}] LỖI:`, err);
    });

    py.on('exit', (code) => {
        console.log(`[${name}] Dừng hoạt động với mã ${code}. Tự động khởi động lại sau 5 giây...`);
        setTimeout(() => startPythonProcess(name, scriptDir, scriptName, customEnv), 5000);
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

// 1. Khởi động Zalo Bot Bích
startNodeWorker('Bot-Bich', path.join(__dirname, 'bich-bot', 'src', 'index.js'), {
    ZALO_CREDENTIALS_PATH: './zalo-credentials.json',
    ZALO_ACCOUNT_NAME: 'Cô Lưu Bích',
    TELEGRAM_BOT_TOKEN: SECRETARY_TOKEN,
    TELEGRAM_CHAT_ID: CHAT_ID
});

// 2. Khởi động Zalo Bot Cường
// Để tránh tải nặng cùng lúc, delay 10 giây trước khi bật Cường
setTimeout(() => {
    startNodeWorker('Bot-Cuong', path.join(__dirname, 'cuong-bot', 'src', 'index.js'), {
        ZALO_CREDENTIALS_PATH: './zalo-credentials-cuong.json',
        ZALO_ACCOUNT_NAME: 'Trợ Lý Cường',
        TELEGRAM_BOT_TOKEN: SECRETARY_TOKEN,
        TELEGRAM_CHAT_ID: CHAT_ID
    });
}, 10000);

// 3. Khởi động Telegram Secretary
setTimeout(() => {
    startNodeWorker('Telegram-Secretary', path.join(__dirname, 'telegram-secretary', 'bot.js'), {
        SECRETARY_BOT_TOKEN: SECRETARY_TOKEN,
        ADMIN_TELEGRAM_ID: CHAT_ID
    });
}, 20000);

// 4. Khởi động XAU Algo Bot
setTimeout(() => {
    startNodeWorker('XAU-Algo-Bot', path.join(__dirname, 'tradingview-xau-alert', 'server.js'), {
        PORT: 7861, // Tránh đụng cổng 7860
        TELEGRAM_BOT_TOKEN: THONG_DONG_TOKEN,
        TELEGRAM_CHAT_ID: CHAT_ID
    });
}, 30000);

// 5. Khởi động Python Trading Bot
setTimeout(() => {
    startPythonProcess('Python-Trading', 'trading-bot', 'bot.py', {
        TELEGRAM_BOT_TOKEN: TONY_TRADING_TOKEN,
        TELEGRAM_CHAT_ID: CHAT_ID
    });
}, 40000);
