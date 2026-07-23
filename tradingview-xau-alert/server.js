const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json()); // Hỗ trợ JSON payload từ TradingView

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID;

// ============================================================
//  WEBHOOK XAU ALGO BOT — Nhận tín hiệu chuẩn 100% từ TradingView
// ============================================================

async function sendTelegram(text) {
    if (!BOT_TOKEN || !CHAT_ID) {
        console.log('[TELEGRAM SKIP] Missing BOT_TOKEN or CHAT_ID');
        return;
    }
    try {
        const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: CHAT_ID,
                text,
                parse_mode: 'HTML'
            })
        });
        const data = await res.json();
        if (!data.ok) console.error('[TELEGRAM ERROR]', data.description);
    } catch (err) {
        console.error('[TELEGRAM SEND ERROR]', err.message);
    }
}

app.post('/webhook', async (req, res) => {
    try {
        const payload = req.body;
        console.log('\n[WEBHOOK NHẬN TÍN HIỆU]', new Date().toISOString());
        console.log(payload);

        if (!payload || !payload.signal) {
            return res.status(400).send('Invalid payload');
        }

        const emoji = payload.signal === 'LONG' ? '🟢🔼' : '🔴🔽';
        
        let emaContext = '';
        const price = parseFloat(payload.price);
        const ema147 = parseFloat(payload.ema147);
        const ema258 = parseFloat(payload.ema258);
        const ema369 = parseFloat(payload.ema369);

        if (price > ema147 && price > ema258 && price > ema369) {
            emaContext = '✅ Giá trên cả 3 EMA → Xu hướng TĂNG mạnh';
        } else if (price < ema147 && price < ema258 && price < ema369) {
            emaContext = '⚠️ Giá dưới cả 3 EMA → Xu hướng GIẢM mạnh';
        } else if (price > ema147) {
            emaContext = '📊 Giá trên EMA147 → Xu hướng ngắn hạn TĂNG';
        } else {
            emaContext = '📊 Giá dưới EMA147 → Xu hướng ngắn hạn GIẢM';
        }

        const msg = `${emoji} <b>TÍN HIỆU XAU/USD — CANH ${payload.signal === 'LONG' ? 'MUA (LONG)' : 'BÁN (SHORT)'}</b>

📌 <b>${payload.msg}</b>

💰 Giá hiện tại: <b>${payload.price}</b>

📈 EMA 147: ${ema147.toFixed(2)}
📉 EMA 258: ${ema258.toFixed(2)}
📊 EMA 369: ${ema369.toFixed(2)}

${emaContext}

⏰ Khung: ${payload.tf || 'M5'} | Nguồn: TradingView (${payload.ticker})
🕐 ${new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })}

⚡ <i>Nhớ đặt Stoploss!</i>`;

        await sendTelegram(msg);
        res.status(200).send('OK');
    } catch (error) {
        console.error('[WEBHOOK ERROR]', error);
        res.status(500).send('Error processing webhook');
    }
});

// Endpoint giữ kết nối 24/7 cho Render
app.get('/ping', (req, res) => {
    res.json({ status: 'alive', bot: 'TradingView Webhook Bot' });
});

app.get('/', (req, res) => {
    res.send('<h1>🏆 XAU Algo Bot — Đang Hoạt Động (Webhook Mode)</h1><p>Đang chờ tín hiệu chuẩn từ TradingView OANDA...</p>');
});

app.listen(PORT, async () => {
    console.log(`\n🏆 XAU ALGO BOT — Server (Webhook Mode) khởi động trên cổng ${PORT}`);
    console.log(`🔔 Telegram Bot: ${BOT_TOKEN ? 'Đã cấu hình' : '❌ THIẾU'}`);
    console.log(`📡 Chat ID: ${CHAT_ID ? 'Đã cấu hình' : '❌ THIẾU'}\n`);
    await sendTelegram(`🏆 <b>XAU Algo Bot Đã Khôi Phục Chế Độ Webhook</b>\n\n✅ Bot đã sẵn sàng nhận tín hiệu 100% chuẩn từ chỉ báo TradingView của Sếp!`);
});
