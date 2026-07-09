import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    indicators = TechnicalIndicators()
    try:
        df = await fetcher.fetch_ohlcv("SNDK/USDT", "5m", limit=800)
    except Exception as e:
        print(f"Error: {e}")
        return
        
    if df.empty:
        print("Empty DF")
        return
        
    df = indicators.calculate_all(df)
    
    for i in range(-15, 0):
        last = df.iloc[i]
        timestamp = last.name if isinstance(last.name, pd.Timestamp) else df.index[i]
        ema_max = max(last['dragon_close'], last['ema_89'], last['ema_200'], last['ema_610'])
        ema_min = min(last['dragon_close'], last['ema_89'], last['ema_200'], last['ema_610'])
        actual_spread = (ema_max - ema_min) / ema_min * 100
        
        print(f"[{i}] {timestamp} | Close: {last['close']:.2f} | Dragon: {last['dragon_close']:.2f} | EMA89: {last['ema_89']:.2f} | EMA200: {last['ema_200']:.2f} | EMA610: {last['ema_610']:.2f} | Spread: {actual_spread:.2f}% | Squeeze: {last.get('ema_squeeze', False)} | SpreadVar: {last.get('ema_spread_pct', 100):.2f}%")
    
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
