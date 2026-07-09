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
        
        # Let's calculate indicators
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        # We want to find candles where low was below 0.1460 and close was below 0.1500
        # which represents the dip before the rally
        print("Finding dip candles...")
        dip_df = df[(df['low'] < 0.1460) & (df.index > '2026-06-09 00:00:00')]
        for ts, row in dip_df.iterrows():
            print(f"Time: {ts} | Open: {row['open']:.4f} | High: {row['high']:.4f} | Low: {row['low']:.4f} | Close: {row['close']:.4f} | Vol: {row['volume']:.0f}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
