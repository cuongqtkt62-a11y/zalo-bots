import asyncio
import pandas as pd
from market_data import MarketDataFetcher

async def main():
    fetcher = MarketDataFetcher()
    symbol = 'ROBO/USDT:USDT'
    try:
        df = await fetcher.fetch_ohlcv(symbol, '30m', limit=200)
        df.index = df.index + pd.Timedelta(hours=7) # VN Time
        
        print("Lows on June 9th:")
        df_june9 = df.loc['2026-06-09 00:00:00':]
        for ts, row in df_june9.iterrows():
            if row['low'] < 0.02000:
                print(f"{ts} | Low: {row['low']:.5f} | Close: {row['close']:.5f} | Vol: {row['volume']:.0f}")
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
