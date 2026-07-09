import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def debug_nmr():
    symbol = "NMR/USDT:USDT"
    scanner = SignalScanner()
    try:
        await scanner.data_fetcher.exchange.load_markets()
        
        # Fetch OHLCV
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df.empty:
            print("❌ Failed to fetch NMR data.")
            return
            
        # Truncate the last unclosed candle if scanner does it
        df = df.iloc[:-1]
        
        df_indicators = scanner.indicators.calculate_all(df)
        df_indicators.index = pd.to_datetime(df_indicators.index)
        local_index = df_indicators.index.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh')
        
        print(f"=== DETAILED OHLCV & INDICATOR DUMP FOR NMR/USDT ===")
        for i in range(len(df_indicators)):
            time_str = local_index[i].strftime('%Y-%m-%d %H:%M')
            if "2026-06-21 18:30" <= time_str <= "2026-06-21 19:20":
                row = df_indicators.iloc[i]
                print(f"\nVN Time: {time_str}")
                print(f"  OHLC: O={row['open']:.4f}, H={row['high']:.4f}, L={row['low']:.4f}, C={row['close']:.4f}")
                print(f"  Volume: {row['volume']:.2f} (Avg: {row['volume_avg']:.2f}, Ratio: {row['volume_ratio']:.2f})")
                print(f"  EMAs: Dragon_C={row['dragon_close']:.4f}, EMA89={row['ema_89']:.4f}, EMA200={row['ema_200']:.4f}")
                print(f"  Wick Ratios: Lower={row['lower_wick_ratio']:.2%}, Upper={row['upper_wick_ratio']:.2%}, Body={row['body_ratio']:.2%}")
                
                # Swing points in the window
                print(f"  Swing Points: Swing_Low={row['swing_low'] if not pd.isna(row['swing_low']) else 'None'}, Swing_High={row['swing_high'] if not pd.isna(row['swing_high']) else 'None'}")
                print(f"  Sweep: Sweep_Low={row['sweep_low']} (Level: {row['sweep_low_level']}), Sweep_High={row['sweep_high']} (Level: {row['sweep_high_level']})")
                
                # Reversals
                print(f"  Rejection Flags: is_spring={row['is_spring']}, is_hammer={row['is_hammer']}, is_bull_engulfing={row['is_bull_engulfing']}")
                print(f"  Reversal at EMA: bullish_reversal_at_ema={row['bullish_reversal_at_ema']}, bearish_reversal_at_ema={row['bearish_reversal_at_ema']}")
                
                # FVG & IFVG
                print(f"  FVG Bullish: {row['fvg_bullish']} (Type: {row['fvg_bull_type']}, Quality: {row['fvg_bull_quality']})")
                print(f"  Inverse FVG: ifvg_bullish={row['ifvg_bullish']}")
                print(f"  FVG Rebalance: fvg_bull_rebalanced={row['fvg_bull_rebalanced']}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(debug_nmr())
