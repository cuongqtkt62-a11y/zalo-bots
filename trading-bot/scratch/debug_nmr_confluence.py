import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def debug_confluence():
    symbol = "NMR/USDT:USDT"
    scanner = SignalScanner()
    try:
        await scanner.data_fetcher.exchange.load_markets()
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        df = df.iloc[:-1]
        df_indicators = scanner.indicators.calculate_all(df)
        df_indicators.index = pd.to_datetime(df_indicators.index)
        local_index = df_indicators.index.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh')
        
        for i in range(len(df_indicators)):
            time_str = local_index[i].strftime('%Y-%m-%d %H:%M')
            if time_str == "2026-06-21 19:10":
                sub_df = df_indicators.iloc[:i+1]
                last = sub_df.iloc[-1]
                
                sweep_lookback = 35
                has_reversal_with_sweep = False
                rev_indices = []
                
                print(f"=== Debugging 19:10 VN ===")
                for idx in range(-1, -11, -1):
                    if sub_df['bullish_reversal_at_ema'].iloc[idx]:
                        rev_indices.append((idx, local_index[i + idx + 1].strftime('%Y-%m-%d %H:%M')))
                
                print(f"Found reversal candles (last 10): {rev_indices}")
                
                if rev_indices:
                    for rev_idx, rev_time in rev_indices:
                        print(f"\nChecking reversal at {rev_time} (idx={rev_idx}):")
                        for idx in range(rev_idx, rev_idx - sweep_lookback, -1):
                            if sub_df['sweep_low'].iloc[idx]:
                                sweep_time = local_index[i + idx + 1].strftime('%Y-%m-%d %H:%M')
                                sweep_candle_low = sub_df['low'].iloc[idx]
                                sweep_distance = abs(last['close'] - sweep_candle_low)
                                
                                print(f"  * Found sweep_low at {sweep_time} (idx={idx}), Low={sweep_candle_low:.4f}")
                                
                                if sweep_distance > 3.0 * last.get('atr', 0):
                                    print(f"    - Rejected: distance {sweep_distance:.4f} > 3x ATR ({3.0 * last.get('atr', 0):.4f})")
                                    continue
                                
                                # Slicing df['close'].iloc[idx:]
                                closes = sub_df['close'].iloc[idx:]
                                closed_below_mask = closes < sweep_candle_low
                                closed_below = closed_below_mask.any()
                                
                                print(f"    - Slices from {sweep_time} to 19:10:")
                                for c_idx in range(len(closes)):
                                    c_time = local_index[i + idx + 1 + c_idx].strftime('%Y-%m-%d %H:%M')
                                    print(f"      {c_time}: Close={closes.iloc[c_idx]:.4f} (< {sweep_candle_low:.4f} is {closed_below_mask.iloc[c_idx]})")
                                
                                print(f"    - closed_below result: {closed_below}")
                                if not closed_below:
                                    has_reversal_with_sweep = True
                                    print(f"    -> MATCHED! reversal with sweep found.")
                                    break
                        if has_reversal_with_sweep:
                            break
                            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(debug_confluence())
