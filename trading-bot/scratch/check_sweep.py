import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    symbol = 'IO/USDT:USDT'
    try:
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=1000)
        df.index = df.index + pd.Timedelta(hours=7) # VN Time
        
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        target_df = df.loc['2026-06-09 07:00:00':'2026-06-09 11:30:00'].copy()
        
        print("--- Swing Lows and Sweep Lows ---")
        for ts, row in target_df.iterrows():
            if not pd.isna(row['swing_low']) or row['sweep_low'] or row['low'] < 0.1430:
                print(f"{ts} | Close: {row['close']:.4f} | L: {row['low']:.4f} | swing_low: {row['swing_low']} | sweep_low: {row['sweep_low']} | sweep_low_level: {row['sweep_low_level']}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
