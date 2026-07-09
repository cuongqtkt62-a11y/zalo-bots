"""
📊 HỆ THỐNG GIÁM SÁT VĨ MÔ & CHIẾN LƯỢC DÒNG TIỀN AI + CRYPTO (2026)
Giám sát DXY, BTC Dominance, và Tự động Cảnh báo Vùng Gom các Cổ phiếu AI/Crypto Proxies
"""
import asyncio
import aiohttp
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from datetime import datetime
from config import Config
from telegram_notifier import TelegramNotifier

TARGET_TOKENS = {
    "NEAR": {
        "symbol": "NEAR/USDT",
        "zones": [
            {"name": "Vùng 1 (40% vốn)", "low": 1.70, "high": 1.85},
            {"name": "Vùng 2 (30% vốn)", "low": 1.45, "high": 1.55},
            {"name": "Vùng 3 (30% vốn)", "low": 1.20, "high": 1.35}
        ]
    },
    "RENDER": {
        "symbol": "RENDER/USDT",
        "zones": [
            {"name": "Vùng 1 (50% vốn)", "low": 1.45, "high": 1.60},
            {"name": "Vùng 2 (50% vốn)", "low": 1.20, "high": 1.35}
        ]
    },
    "ARKM": {
        "symbol": "ARKM/USDT",
        "zones": [
            {"name": "Vùng 1 (50% vốn)", "low": 0.105, "high": 0.120},
            {"name": "Vùng 2 (50% vốn)", "low": 0.085, "high": 0.095}
        ]
    },
    "WLD": {
        "symbol": "WLD/USDT",
        "zones": [
            {"name": "Vùng gom chờ tạo đáy", "low": 0.38, "high": 0.44}
        ]
    }
}


class MacroMonitor:
    def __init__(self):
        self.notifier = TelegramNotifier()
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json"
        }

    async def close(self):
        await self.exchange.close()

    async def fetch_dxy(self):
        """Lấy chỉ số DXY từ Yahoo Finance v8 chart API"""
        url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1d&range=2d"
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                        price = meta.get("regularMarketPrice")
                        prev = meta.get("previousClose") or meta.get("chartPreviousClose")
                        change = ((price - prev) / prev * 100) if prev else 0
                        return price, change
        except Exception as e:
            print(f"Error fetching DXY: {e}")
        return None, None

    async def fetch_btc_dominance(self):
        """Lấy chỉ số BTC Dominance từ CoinGecko public API"""
        url = "https://api.coingecko.com/api/v3/global"
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        btc_d = data.get("data", {}).get("market_cap_percentage", {}).get("btc", 0)
                        return btc_d
        except Exception as e:
            print(f"Error fetching BTC.D: {e}")
        return None

    def calculate_rsi(self, df, period=14):
        """Tính toán RSI 14"""
        close = df['close']
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    async def analyze_token(self, ticker_symbol):
        """Lấy giá hiện tại và tính RSI Daily cho token"""
        try:
            # Fetch OHLCV daily
            ohlcv = await self.exchange.fetch_ohlcv(ticker_symbol, '1d', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            price = df['close'].iloc[-1]
            rsi = self.calculate_rsi(df)
            
            # Kiểm tra xem có đang ở trong vùng gom nào không
            token_name = ticker_symbol.split('/')[0]
            token_config = TARGET_TOKENS.get(token_name, {})
            current_zone = None
            if token_config:
                for zone in token_config["zones"]:
                    if zone["low"] <= price <= zone["high"]:
                        current_zone = zone["name"]
                        break
            
            return {
                "price": price,
                "rsi": rsi,
                "current_zone": current_zone
            }
        except Exception as e:
            print(f"Error analyzing {ticker_symbol}: {e}")
            return None

    async def run_monitor(self, send_telegram=True):
        print("Starting Macro Monitor...")
        # 1. Fetch Macro Data
        dxy, dxy_change = await self.fetch_dxy()
        btc_d = await self.fetch_btc_dominance()

        # 2. Analyze Tokens
        token_results = {}
        for token_name, config in TARGET_TOKENS.items():
            res = await self.analyze_token(config["symbol"])
            if res:
                token_results[token_name] = res
            await asyncio.sleep(0.2)  # rate limit safety

        # 3. Format Report
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Tiêu đề báo cáo
        msg = (
            f"📊 <b>BÁO CÁO VĨ MÔ & CHIẾN LƯỢC DÒNG TIỀN AI + CRYPTO</b>\n"
            f"🕐 Cập nhật: {date_str}\n"
            f"{'━' * 30}\n\n"
        )

        # Phần 1: Chỉ số vĩ mô liên thị trường
        msg += "🌍 <b>1. CHỈ SỐ VĨ MÔ LIÊN THỊ TRƯỜNG</b>\n"
        if dxy is not None:
            dxy_status = "🔴 USD Rất Mạnh (Xấu cho Altcoin)" if dxy > 106.5 else (
                "🟢 USD Giảm (Thuận lợi cho Altcoin)" if dxy < 104.5 else "🟡 Đi ngang ổn định"
            )
            msg += f"• <b>DXY (Dollar Index):</b> {dxy:.2f} ({dxy_change:+.2f}%) | {dxy_status}\n"
        else:
            msg += "• <b>DXY (Dollar Index):</b> Không lấy được dữ liệu\n"

        if btc_d is not None:
            btcd_status = "⚠️ BTC hút máu Altcoin" if btc_d > 58.0 else (
                "🟢 Thuận lợi Altcoin Season" if btc_d < 55.0 else "🟡 Ổn định"
            )
            msg += f"• <b>BTC Dominance:</b> {btc_d:.2f}% | {btcd_status}\n"
        else:
            msg += "• <b>BTC Dominance:</b> Không lấy được dữ liệu\n"

        msg += "\n" + "─" * 30 + "\n"

        # Phần 2: Cảnh báo vùng gom Crypto AI
        msg += "🤖 <b>2. TRẠNG THÁI CÁC CRYPTO AI PROXIES</b>\n"
        for token_name, data in token_results.items():
            price = data["price"]
            rsi = data["rsi"]
            zone = data["current_zone"]
            
            rsi_emoji = "💀" if rsi < 15 else ("🚨" if rsi < 25 else "⏳")
            zone_text = f"🎯 <b>ĐÃ CHẠM {zone.upper()}</b>" if zone else "❌ Ngoài vùng gom"
            
            msg += (
                f"• <b>{token_name}</b>: ${price:,.4f}\n"
                f"  └ RSI Daily: {rsi:.0f} {rsi_emoji}\n"
                f"  └ Trạng thái: {zone_text}\n"
            )
        
        msg += "\n" + "─" * 30 + "\n"

        # Phần 3: Khuyến nghị kỷ luật
        msg += (
            "💡 <b>3. KHUYẾN NGHỊ HÀNH ĐỘNG HÔM NAY</b>\n"
            "• Chỉ gom **SPOT**, tuyệt đối **KHÔNG FUTURES** trước thềm IPO SpaceX ngày 12/06.\n"
            "• Ưu tiên vốn gom **NEAR** và **RENDER** khi đã chạm vùng hỗ trợ mong muốn.\n"
            "• Tiếp tục nắm giữ phần lớn **Stablecoin** để phòng ngừa rủi ro BTC quét đáy.\n"
            f"{'━' * 30}\n"
            "<i>Đầu Tư Thông Dong AI Assistant 🧘‍♂️</i>"
        )

        print(msg)

        if send_telegram:
            await self.notifier.send_status(msg)
            print("Telegram notification sent successfully.")

async def main():
    monitor = MacroMonitor()
    try:
        await monitor.run_monitor(send_telegram=True)
    finally:
        await monitor.close()

if __name__ == "__main__":
    asyncio.run(main())
