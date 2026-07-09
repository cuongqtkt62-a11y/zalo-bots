import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner

async def main():
    fetcher = MarketDataFetcher()
    indicators = TechnicalIndicators()
    scanner = SignalScanner()
    
    symbol = "NIGHT/USDT:USDT"
    print(f"Fetching data for {symbol}...")
    try:
        df = await fetcher.fetch_ohlcv(symbol, "5m", limit=800)
    except Exception as e:
        print(f"Error fetching data: {e}")
        await fetcher.close()
        return
        
    if df.empty:
        print("No data fetched.")
        await fetcher.close()
        return
        
    df = indicators.calculate_all(df)
    
    # Let's search around 15:30:00 (which is 08:30:00 UTC)
    # The current local time is 15:49, so index range [-10, 0] covers it
    print("\n--- Detailed Candle Analysis for NIGHT/USDT (Recent) ---")
    
    for i in range(-15, 0):
        idx_time = df.index[i]
        local_time = idx_time + pd.Timedelta(hours=7)
        row = df.iloc[i]
        
        # Check setup using the scanner's logic
        # We can simulate _check_confluence_setup for this candle
        sub_df = df.iloc[:len(df) + i + 1]
        signal = scanner._check_confluence_setup(sub_df, symbol, "BULLISH")
        
        score_str = f"SCORE: {signal.confluence_score} (Grade: {signal.grade})" if signal else "NO SETUP"
        
        print(f"Candle: {local_time} (Local) | Close: {row['close']:.5f}")
        print(f"  - EMAs: Dragon: {row['dragon_close']:.5f} | EMA89: {row['ema_89']:.5f} | EMA200: {row['ema_200']:.5f} | EMA610: {row['ema_610']:.5f}")
        print(f"  - Spread: {row['ema_spread_pct']:.2f}% (Squeeze: {row['ema_squeeze']}, Narrow: {row['dragon_narrow']})")
        print(f"  - Price in Cluster: {row['price_in_ema_cluster']} | Near Dragon: {row['price_in_dragon']}")
        print(f"  - Bullish Reversal: {row['bullish_reversal_at_ema']} (Spring: {row['is_spring']}, Hammer: {row['is_hammer']}, Engulfing: {row['is_bull_engulfing']})")
        print(f"  - Lower Wick Ratio: {row['lower_wick_ratio']:.2f} | Volume Ratio: {row['volume_ratio']:.2f}")
        print(f"  - Sweep Low: {row['sweep_low']} (Level: {row['sweep_low_level']})")
        print(f"  - FVG Bullish: {row['fvg_bullish']}")
        print(f"  - Scanner verdict: {score_str}")
        if signal:
            details_str = signal.trigger_detail.replace('\n', ', ')
            print(f"  - Details: {details_str}")
        print("-" * 50)
        
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
