import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    indicators = TechnicalIndicators()
    df = await fetcher.fetch_ohlcv("TIA/USDT", "5m", limit=800)
    if df.empty:
        return
    df = indicators.calculate_all(df)
    
    last = df.iloc[-1]
    print(f"Close: {last['close']}")
    print(f"Dragon Close: {last['dragon_close']}")
    print(f"EMA 89: {last['ema_89']}")
    print(f"EMA 200: {last['ema_200']}")
    print(f"EMA 610: {last['ema_610']}")
    
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
