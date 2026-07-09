import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    try:
        df = await fetcher.fetch_ohlcv("SNDK/USDT", "5m", limit=800)
    except Exception as e:
        print(f"Error: {e}")
        return
        
    print(f"Total candles fetched for SNDK: {len(df)}")
    if not df.empty:
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        print(f"EMA 610 is NaN: {df['ema_610'].isna().all()}")
        
        ema_cols = ['dragon_close', 'ema_89', 'ema_200', 'ema_610']
        ema_max = df[ema_cols].max(axis=1)
        ema_min = df[ema_cols].min(axis=1)
        df['ema_spread_pct'] = (ema_max - ema_min) / df['close'] * 100
        print(f"EMA Spread PCT: {df['ema_spread_pct'].iloc[-1]:.2f}%")
        
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
