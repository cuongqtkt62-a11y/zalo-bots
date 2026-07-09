import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    symbol = 'MYX/USDT:USDT'
    
    try:
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        df = TechnicalIndicators.calculate_all(df)
        df.index = df.index + pd.Timedelta(hours=7)
        
        target_start = pd.to_datetime('2026-06-08 13:20:00')
        target_end = pd.to_datetime('2026-06-08 13:55:00')
        
        sub = df.loc[target_start:target_end]
        print(f"=== OHLC & Indicators for MYX from {target_start} to {target_end} ===")
        for ts, row in sub.iterrows():
            print(f"\nVN Time: {ts}")
            print(f"  Open: {row['open']:.5f} | High: {row['high']:.5f} | Low: {row['low']:.5f} | Close: {row['close']:.5f} | Vol: {row['volume']:.0f}")
            print(f"  EMA34 High: {row['dragon_high']:.5f} | Close: {row['dragon_close']:.5f} | Low: {row['dragon_low']:.5f}")
            print(f"  EMA89: {row['ema_89']:.5f} | EMA200: {row['ema_200']:.5f} | EMA610: {row['ema_610']:.5f}")
            print(f"  Lower Wick Ratio: {row.get('lower_wick_ratio', 0):.2f} | Upper Wick Ratio: {row.get('upper_wick_ratio', 0):.2f}")
            print(f"  Volume Ratio: {row.get('volume_ratio', 0):.2f} | Squeeze: {row.get('ema_squeeze', False)}")
            print(f"  Sweep Low: {row.get('sweep_low', False)} | sweep_low_level: {row.get('sweep_low_level', None)}")
            print(f"  Bullish Rev: {row.get('bullish_reversal_at_ema', False)} | FVG Bullish: {row.get('fvg_bullish', False)}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
