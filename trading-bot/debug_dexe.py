import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    indicators = TechnicalIndicators()
    df = await fetcher.fetch_ohlcv("DEXE/USDT", "5m", limit=800)
    if df.empty:
        return
    df = indicators.calculate_all(df)
    
    last = df.iloc[-1]
    print(f"Close: {last['close']}")
    print(f"Dragon Close: {last['dragon_close']}")
    print(f"EMA 89: {last['ema_89']}")
    print(f"EMA 200: {last['ema_200']}")
    print(f"EMA 610: {last['ema_610']}")
    
    ema_max = max(last['dragon_close'], last['ema_89'], last['ema_200'], last['ema_610'])
    ema_min = min(last['dragon_close'], last['ema_89'], last['ema_200'], last['ema_610'])
    actual_spread = (ema_max - ema_min) / ema_min * 100
    print(f"Actual Spread: {actual_spread:.2f}%")
    print(f"Bot Spread: {last.get('ema_spread_pct', 'N/A')}%")
    print(f"Squeeze: {df['ema_squeeze'].iloc[-5:].any()}")
    print(f"Dragon Narrow: {df['dragon_narrow'].iloc[-5:].any()}")
    
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
