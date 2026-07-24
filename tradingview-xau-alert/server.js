const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

// ============================================================
//  STANDALONE XAU ALGO BOT — Tự quét M5, tính SMC + 4EMA Sonic R, báo Telegram
//  Nguồn dữ liệu: TradingView OANDA:XAUUSD (≈ XAU/USD — Sát giá OANDA)
//  Hệ thống EMA: Sonic R — Dragon 34, EMA 89, EMA 200, EMA 610
// ============================================================

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID;
const SYMBOL = 'XAUUSDT';
const INTERVAL = '5m';
const SWING_LENGTH = 7;
const BOX_WIDTH = 7;
const HISTORY_KEEP = 7;
const SCAN_INTERVAL_MS = 5 * 60 * 1000; // 5 phút

// ============================================================
//  TRẠNG THÁI TOÀN CỤC
// ============================================================
let supplyZones = [];
let demandZones = [];
let alertedBOS = new Set(); // Chống spam: mỗi BOS chỉ báo 1 lần
let lastScanTime = null;
let scanCount = 0;
const STARTUP_TIME = Date.now();
let silentSyncDone = false; // Đánh dấu đã qua giai đoạn Silent Sync

const TradingView = require('@mathieuc/tradingview');

// ============================================================
//  1. LẤY DỮ LIỆU NẾN TỪ TRADINGVIEW (OANDA)
// ============================================================
async function fetchCandles(limit = 500) {
    return new Promise((resolve, reject) => {
        const client = new TradingView.Client();
        const chart = new client.Session.Chart();
        
        chart.setMarket('OANDA:XAUUSD', {
            timeframe: '5',
            range: limit
        });

        chart.onUpdate(() => {
            if (!chart.periods.length) {
                client.end();
                return reject(new Error('No data from TradingView'));
            }
            
            // TradingView module returns array from newest to oldest
            // We need to reverse it to oldest to newest for SMC logic
            const candles = chart.periods.map(c => ({
                time: c.time * 1000,
                open: c.open,
                high: c.max,
                low: c.min,
                close: c.close,
                volume: c.volume
            })).reverse();

            client.end();
            resolve(candles);
        });

        setTimeout(() => {
            client.end();
            reject(new Error('TradingView fetch timeout'));
        }, 10000);
    });
}

// ============================================================
//  2. TÍNH EMA — Sonic R System (34, 89, 200, 610)
// ============================================================
function calcEMA(closes, period) {
    const k = 2 / (period + 1);
    const ema = [closes[0]];
    for (let i = 1; i < closes.length; i++) {
        ema.push(closes[i] * k + ema[i - 1] * (1 - k));
    }
    return ema;
}

// ============================================================
//  3. TÌM SWING HIGH / SWING LOW (PivotHigh / PivotLow)
// ============================================================
function findSwingHighs(highs, length) {
    const swings = [];
    for (let i = length; i < highs.length - length; i++) {
        let isSwing = true;
        for (let j = 1; j <= length; j++) {
            if (highs[i] < highs[i - j] || highs[i] < highs[i + j]) {
                isSwing = false;
                break;
            }
        }
        if (isSwing) swings.push({ index: i, value: highs[i] });
    }
    return swings;
}

function findSwingLows(lows, length) {
    const swings = [];
    for (let i = length; i < lows.length - length; i++) {
        let isSwing = true;
        for (let j = 1; j <= length; j++) {
            if (lows[i] > lows[i - j] || lows[i] > lows[i + j]) {
                isSwing = false;
                break;
            }
        }
        if (isSwing) swings.push({ index: i, value: lows[i] });
    }
    return swings;
}

// ============================================================
//  4. TÍNH ATR (Average True Range)
// ============================================================
function calcATR(candles, period = 50) {
    const trs = [];
    for (let i = 1; i < candles.length; i++) {
        const tr = Math.max(
            candles[i].high - candles[i].low,
            Math.abs(candles[i].high - candles[i - 1].close),
            Math.abs(candles[i].low - candles[i - 1].close)
        );
        trs.push(tr);
    }
    // Simple moving average of TR for the last 'period' values
    if (trs.length < period) return trs.reduce((a, b) => a + b, 0) / trs.length;
    const slice = trs.slice(-period);
    return slice.reduce((a, b) => a + b, 0) / period;
}

// ============================================================
//  5. XÂY DỰNG VÙNG SUPPLY / DEMAND (SMC Zones)
// ============================================================
function buildZones(candles, swingHighs, swingLows, atr) {
    const atrBuffer = atr * (BOX_WIDTH / 10);
    const supply = [];
    const demand = [];

    // Supply zones from Swing Highs
    for (const sh of swingHighs.slice(-HISTORY_KEEP)) {
        const top = sh.value;
        const bottom = top - atrBuffer;
        const poi = (top + bottom) / 2;
        // Check overlapping
        let overlapping = false;
        for (const zone of supply) {
            const zonePoi = (zone.top + zone.bottom) / 2;
            if (Math.abs(poi - zonePoi) < atr * 2) {
                overlapping = true;
                break;
            }
        }
        if (!overlapping) {
            supply.push({ top, bottom, poi, index: sh.index, broken: false });
        }
    }

    // Demand zones from Swing Lows
    for (const sl of swingLows.slice(-HISTORY_KEEP)) {
        const bottom = sl.value;
        const top = bottom + atrBuffer;
        const poi = (top + bottom) / 2;
        let overlapping = false;
        for (const zone of demand) {
            const zonePoi = (zone.top + zone.bottom) / 2;
            if (Math.abs(poi - zonePoi) < atr * 2) {
                overlapping = true;
                break;
            }
        }
        if (!overlapping) {
            demand.push({ top, bottom, poi, index: sl.index, broken: false });
        }
    }

    return { supply, demand };
}

// ============================================================
//  6. KIỂM TRA BOS (Break of Structure)
// ============================================================
function detectBOS(candles, supply, demand) {
    const signals = [];
    const currentCandle = candles[candles.length - 1];
    const price = currentCandle.close;

    // Check Supply BOS (LONG signal — price breaks above supply)
    for (const zone of supply) {
        if (!zone.broken && price >= zone.top) {
            zone.broken = true;
            const bosKey = `LONG_${zone.top.toFixed(2)}_${zone.index}`;
            if (!alertedBOS.has(bosKey)) {
                alertedBOS.add(bosKey);
                signals.push({
                    signal: 'LONG',
                    msg: 'Giá phá vỡ BOS Supply — Canh LONG',
                    price: price.toFixed(2),
                    zoneTop: zone.top.toFixed(2),
                    zoneBottom: zone.bottom.toFixed(2)
                });
            }
        }
    }

    // Check Demand BOS (SHORT signal — price breaks below demand)
    for (const zone of demand) {
        if (!zone.broken && price <= zone.bottom) {
            zone.broken = true;
            const bosKey = `SHORT_${zone.bottom.toFixed(2)}_${zone.index}`;
            if (!alertedBOS.has(bosKey)) {
                alertedBOS.add(bosKey);
                signals.push({
                    signal: 'SHORT',
                    msg: 'Giá phá vỡ BOS Demand — Canh SHORT',
                    price: price.toFixed(2),
                    zoneTop: zone.top.toFixed(2),
                    zoneBottom: zone.bottom.toFixed(2)
                });
            }
        }
    }

    return signals;
}

// ============================================================
//  7. GỬI TELEGRAM
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

function formatSignalMessage(sig, emaDragon, ema89, ema200, ema610) {
    const emoji = sig.signal === 'LONG' ? '🟢🔼' : '🔴🔽';
    const action = sig.signal === 'LONG' ? 'CANH MUA (LONG)' : 'CANH BÁN (SHORT)';
    
    // Xác định vị trí giá so với 4 EMA Sonic R
    const price = parseFloat(sig.price);
    let emaContext = '';
    const aboveAll = price > emaDragon && price > ema89 && price > ema200 && price > ema610;
    const belowAll = price < emaDragon && price < ema89 && price < ema200 && price < ema610;
    
    if (aboveAll) {
        emaContext = '✅ Giá trên cả 4 EMA Sonic R → Xu hướng TĂNG mạnh';
    } else if (belowAll) {
        emaContext = '⚠️ Giá dưới cả 4 EMA Sonic R → Xu hướng GIẢM mạnh';
    } else if (price > emaDragon && price > ema89) {
        emaContext = '📊 Giá trên Dragon + EMA89 → Xu hướng ngắn hạn TĂNG';
    } else if (price < emaDragon && price < ema89) {
        emaContext = '📊 Giá dưới Dragon + EMA89 → Xu hướng ngắn hạn GIẢM';
    } else {
        emaContext = '⚡ Giá nằm giữa cụm EMA → Vùng nén / Xung đột';
    }

    // Tính EMA spread (khoảng cách giữa EMA cao nhất và thấp nhất)
    const emaMax = Math.max(emaDragon, ema89, ema200, ema610);
    const emaMin = Math.min(emaDragon, ema89, ema200, ema610);
    const emaSpreadPct = ((emaMax - emaMin) / emaMin * 100).toFixed(2);

    return `${emoji} <b>TÍN HIỆU XAU/USD — ${action}</b>

📌 <b>${sig.msg}</b>

💰 Giá hiện tại: <b>${sig.price}</b>
📦 Vùng bị phá: ${sig.zoneBottom} → ${sig.zoneTop}

🐉 Dragon EMA 34: ${emaDragon.toFixed(2)}
📈 EMA 89: ${ema89.toFixed(2)}
📉 EMA 200: ${ema200.toFixed(2)}
⚪ EMA 610: ${ema610.toFixed(2)}
📊 EMA Spread: ${emaSpreadPct}%

${emaContext}

⏰ Khung: M5 | Nguồn: OANDA:XAUUSD
🕐 ${new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })}

⚡ <i>Nhớ đặt Stoploss!</i>`;
}

// ============================================================
//  8. HÀM QUÉT CHÍNH (Main Scanner)
// ============================================================
async function runScan() {
    try {
        console.log(`\n[SCAN ${++scanCount}] ${new Date().toISOString()} — Đang quét...`);

        // 1. Kéo 800 nến M5 (đủ cho EMA 610 warmup)
        const candles = await fetchCandles(800);
        console.log(`  → Lấy được ${candles.length} nến M5`);

        const closes = candles.map(c => c.close);
        const highs = candles.map(c => c.high);
        const lows = candles.map(c => c.low);

        // 2. Tính 4 đường EMA Sonic R
        const emaDragon = calcEMA(closes, 34);    // Dragon Band
        const ema89Arr = calcEMA(closes, 89);      // Trend
        const ema200Arr = calcEMA(closes, 200);    // Long Trend
        const ema610Arr = calcEMA(closes, 610);    // Super Trend

        const currentDragon = emaDragon[emaDragon.length - 1];
        const currentEMA89 = ema89Arr[ema89Arr.length - 1];
        const currentEMA200 = ema200Arr[ema200Arr.length - 1];
        const currentEMA610 = ema610Arr[ema610Arr.length - 1];

        console.log(`  → Dragon(34): ${currentDragon.toFixed(2)} | EMA89: ${currentEMA89.toFixed(2)} | EMA200: ${currentEMA200.toFixed(2)} | EMA610: ${currentEMA610.toFixed(2)}`);

        // 3. Tìm Swing High/Low
        const swingHighs = findSwingHighs(highs, SWING_LENGTH);
        const swingLows = findSwingLows(lows, SWING_LENGTH);
        console.log(`  → Swing Highs: ${swingHighs.length} | Swing Lows: ${swingLows.length}`);

        // 4. Tính ATR
        const atr = calcATR(candles, 50);
        console.log(`  → ATR(50): ${atr.toFixed(2)}`);

        // 5. Xây vùng Supply/Demand
        const { supply, demand } = buildZones(candles, swingHighs, swingLows, atr);
        supplyZones = supply;
        demandZones = demand;
        console.log(`  → Supply Zones: ${supply.length} | Demand Zones: ${demand.length}`);

        // 6. Kiểm tra BOS — CHỈ sau khi qua giai đoạn Silent Sync
        const isSilentSync = (Date.now() - STARTUP_TIME) < 60000;
        
        if (isSilentSync) {
            // KHÔNG gọi detectBOS trong 60s đầu để tránh đánh dấu BOS "đã báo" mà chưa gửi telegram
            console.log(`  ⏳ [SILENT SYNC] Bỏ qua phát hiện BOS (${Math.ceil((60000 - (Date.now() - STARTUP_TIME)) / 1000)}s còn lại)`);
        } else {
            // Sau khi qua Silent Sync, xóa sạch alertedBOS 1 lần duy nhất để quét lại fresh
            if (!silentSyncDone) {
                alertedBOS.clear();
                silentSyncDone = true;
                console.log('  🔄 [POST-SYNC] Đã xóa sạch alertedBOS — Quét BOS fresh!');
            }

            const signals = detectBOS(candles, supply, demand);

            if (signals.length > 0) {
                console.log(`  🚨 PHÁT HIỆN ${signals.length} TÍN HIỆU BOS!`);
                
                for (const sig of signals) {
                    const msg = formatSignalMessage(sig, currentDragon, currentEMA89, currentEMA200, currentEMA610);
                    await sendTelegram(msg);
                    console.log(`  → Đã gửi Telegram: ${sig.signal} @ ${sig.price}`);
                }
            } else {
                console.log(`  ✅ Không có tín hiệu BOS mới.`);
            }
        }

        lastScanTime = new Date().toISOString();
        console.log(`  → Giá hiện tại: ${closes[closes.length - 1].toFixed(2)}`);

        // Dọn dẹp alertedBOS cũ (giữ 100 entry gần nhất)
        if (alertedBOS.size > 100) {
            const arr = Array.from(alertedBOS);
            alertedBOS = new Set(arr.slice(-50));
        }

    } catch (err) {
        console.error('[SCAN ERROR]', err.message);
    }
}

// ============================================================
//  9. EXPRESS SERVER (Keep-alive endpoint)
// ============================================================
app.get('/ping', (req, res) => {
    res.json({
        status: 'alive',
        bot: 'XAU Algo Bot (Sonic R)',
        lastScan: lastScanTime,
        scanCount,
        supplyZones: supplyZones.length,
        demandZones: demandZones.length,
        uptime: Math.floor((Date.now() - STARTUP_TIME) / 1000) + 's'
    });
});

app.get('/', (req, res) => {
    res.send(`
        <h1>🏆 XAU Algo Bot — Sonic R System — Đang Hoạt Động</h1>
        <p>Quét nến M5 mỗi 5 phút | 4 EMA Sonic R (34/89/200/610) + SMC BOS → Báo Telegram</p>
        <p>Lần quét cuối: ${lastScanTime || 'Chưa quét'}</p>
        <p>Tổng lần quét: ${scanCount}</p>
        <p>Supply Zones: ${supplyZones.length} | Demand Zones: ${demandZones.length}</p>
    `);
});

// ============================================================
//  10. KHỞI ĐỘNG
// ============================================================
app.listen(PORT, async () => {
    console.log(`\n🏆 XAU ALGO BOT — Sonic R System — Server khởi động trên cổng ${PORT}`);
    console.log(`📊 Symbol: OANDA:XAUUSD | Interval: ${INTERVAL}`);
    console.log(`🐉 EMA: Dragon(34) / 89 / 200 / 610 (Sonic R)`);
    console.log(`🔔 Telegram Bot: ${BOT_TOKEN ? 'Đã cấu hình' : '❌ THIẾU'}`);
    console.log(`📡 Chat ID: ${CHAT_ID ? 'Đã cấu hình' : '❌ THIẾU'}`);
    console.log(`⏰ Quét mỗi ${SCAN_INTERVAL_MS / 1000}s\n`);

    // Thông báo khởi động
    await sendTelegram(`🏆 <b>XAU Algo Bot Khởi Động — Sonic R System</b>\n\n📊 Symbol: OANDA:XAUUSD\n⏰ Khung: M5\n🔄 Quét mỗi 5 phút\n🐉 EMA: Dragon(34) / 89 / 200 / 610\n🧠 Thuật toán: SMC BOS + 4EMA Sonic R\n\n<i>Bot sẽ tự động quét và báo tín hiệu BOS!</i>`);

    // Quét lần đầu sau 5 giây (grace period ngắn)
    setTimeout(() => {
        runScan();
        // Sau đó lặp lại mỗi 5 phút
        setInterval(runScan, SCAN_INTERVAL_MS);
    }, 5000);
});

