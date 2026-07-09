import asyncio
import pandas as pd
import numpy as np
from config import Config
from signal_scanner import SignalScanner

async def debug_akt():
    symbol = "AKT/USDT:USDT"
    print(f"=== Debugging {symbol} ===")
    
    scanner = SignalScanner()
    try:
        # Fetch 800 candles of 5m (which is limit for our optimized scanner)
        df_entry = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df_entry.empty:
            print(f"❌ Failed to fetch data for {symbol}. Check if exchange symbol is correct.")
            return

        df_entry = scanner.indicators.calculate_all(df_entry)
        print(f"Data fetched: {len(df_entry)} rows. Last timestamp: {df_entry.index[-1]}")

        # Let's inspect the last 150 candles to see if we can find where a setup might have been close
        print("\nChecking last 150 candles for setup criteria:")
        recent = df_entry.iloc[-150:]
        
        found_near_misses = 0
        for i in range(20, len(recent)):
            idx = recent.index[i]
            row = recent.iloc[i]
            sub_df = df_entry.loc[:idx]
            
            # Check setup
            # Condition 1: Compression
            has_squeeze = sub_df['ema_squeeze'].iloc[-15:].any()
            has_narrow = sub_df['dragon_narrow'].iloc[-15:].any()
            price_near_ema = (
                row.get('price_in_ema_cluster', False) or
                row.get('price_in_dragon', False) or
                row.get('touch_ema89', False) or
                row.get('touch_ema200', False)
            )
            cond1 = (has_squeeze or has_narrow) and price_near_ema
            
            # Condition 2: Reversal at EMA
            has_reversal = sub_df['bullish_reversal_at_ema'].iloc[-3:].any()
            
            # Condition 3: Sweep low
            has_sweep_low = sub_df['sweep_low'].iloc[-20:].any()
            
            # Condition 4: FVG (bonus)
            has_fvg = sub_df['fvg_bullish'].iloc[-10:].any()
            
            # If it satisfies the conditions, let's print it to see
            if cond1 and has_reversal and has_sweep_low:
                print(f"\n🟢 Time: {idx} | Price: {row['close']:.4f}")
                print(f"  - Cond 1 (Compression): {cond1} (Squeeze: {has_squeeze}, Narrow: {has_narrow}, Near EMA: {price_near_ema})")
                print(f"  - Cond 2 (Reversal): {has_reversal} (is_spring: {row.get('is_spring', False)}, is_hammer: {row.get('is_hammer', False)}, is_bull_engulfing: {row.get('is_bull_engulfing', False)})")
                print(f"  - Cond 3 (Sweep Low): {has_sweep_low} (sweep_low on this candle: {row['sweep_low']})")
                print(f"  - FVG: {has_fvg}")
                
                # Run the actual scanner check
                signal = scanner._check_confluence_setup(sub_df, symbol, bias="NEUTRAL")
                if signal:
                    print(f"  ⭐️ SETUP MATCHED! Direction: {signal.direction}, Grade: {signal.grade}, Score: {signal.confluence_score}")
                else:
                    print("  ❌ Setup rejected by scanner.")
                found_near_misses += 1
            elif idx == recent.index[-1]:
                # Print latest candle status even if it doesn't match all, to see what is missing
                print(f"\n🔍 LATEST CANDLE AT {idx} | Price: {row['close']:.4f}")
                print(f"  - Cond 1 (Compression): {cond1} (Squeeze: {has_squeeze}, Narrow: {has_narrow}, Near EMA: {price_near_ema})")
                print(f"  - Cond 2 (Reversal): {has_reversal} (is_spring: {row.get('is_spring', False)}, is_hammer: {row.get('is_hammer', False)}, is_bull_engulfing: {row.get('is_bull_engulfing', False)})")
                print(f"    (lower_wick_ratio: {row.get('lower_wick_ratio', 0):.2f}, volume_ratio: {row.get('volume_ratio', 0):.2f})")
                print(f"  - Cond 3 (Sweep Low): {has_sweep_low} (sweep_low on this candle: {row['sweep_low']})")
                print(f"  - FVG: {has_fvg}")

        if found_near_misses == 0:
            print("\nℹ️ No fully completed H5 setup found in the last 150 candles.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(debug_akt())
