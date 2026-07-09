import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    symbol = 'ROBO/USDT:USDT'
    try:
        df = await fetcher.fetch_ohlcv(symbol, '30m', limit=100)
        df.index = df.index + pd.Timedelta(hours=7) # VN Time
        
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        target_df = df.loc['2026-06-09 00:00:00':].copy()
        
        print("--- 30m Candlestick Data for ROBO/USDT ---")
        for ts, row in target_df.iterrows():
            print(f"{ts} | Close: {row['close']:.5f} | Open: {row['open']:.5f} | Low: {row['low']:.5f} | High: {row['high']:.5f} | Vol: {row['volume']:.0f}")
            print(f"             | E34: {row['dragon_close']:.5f} | E89: {row['ema_89']:.5f} | E200: {row['ema_200']:.5f} | E610: {row['ema_610']:.5f}")
            print(f"             | sweep_low: {row['sweep_low']} | spread: {row['ema_spread_pct']:.2f}% | vol_ratio: {row['volume_ratio']:.2f}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
