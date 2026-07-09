import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    indicators = TechnicalIndicators()
    df = await fetcher.fetch_ohlcv("MU/USDT", "5m", limit=100)
    if df.empty:
        print("No data for MU/USDT")
        return
    df = indicators.calculate_all(df)
    last = df.iloc[-1]
    
    print(f"Close: {last['close']}")
    print(f"Spread %: {last.get('ema_spread_pct', 'N/A')}")
    print(f"ATR: {last.get('atr', 'N/A')}")
    print(f"ATR %: {last.get('atr', 0) / last['close'] * 100:.4f}%")
    
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
