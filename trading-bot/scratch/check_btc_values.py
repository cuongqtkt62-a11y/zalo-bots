import asyncio
import pandas as pd
from config import Config
from signal_scanner import SignalScanner

async def check():
    scanner = SignalScanner()
    try:
        df = await scanner.data_fetcher.fetch_ohlcv("BTC/USDT:USDT", Config.TIMEFRAME_ENTRY, limit=100)
        df = scanner.indicators.calculate_all(df)
        
        print(df[['dragon_close', 'ema_89', 'ema_200', 'ema_610', 'ema_spread_pct', 'dragon_width', 'price_in_ema_cluster', 'price_in_dragon']].tail(5))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check())
