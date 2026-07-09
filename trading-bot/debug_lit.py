import asyncio
import pandas as pd
from config import Config
from signal_scanner import SignalScanner

async def debug_lit():
    symbol = "LIT/USDT:USDT"
    print(f"=== Debugging {symbol} ===")
    
    scanner = SignalScanner()
    try:
        # Fetch 300 candles of 5m (which is limit for our optimized scanner)
        df_entry = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df_entry.empty:
            print(f"❌ Failed to fetch data for {symbol}. Check if exchange symbol is correct.")
            return

        df_entry = scanner.indicators.calculate_all(df_entry)
        print(f"Data fetched: {len(df_entry)} rows. Last timestamp: {df_entry.index[-1]}")

        # Let's inspect the last 50 candles to see if we can find where a setup might have been close
        print("\nChecking last 50 candles for setup criteria:")
        recent = df_entry.iloc[-50:]
        
        # We want to check:
        # 1. ema_squeeze or dragon_narrow
        # 2. price_in_ema_cluster or price_in_dragon or touch_ema89 or touch_ema200
        # 3. sweep_low or sweep_high in last 20 candles
        # 4. bullish_reversal_at_ema or bearish_reversal_at_ema in last 3 candles
        
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
            
            if cond1 or has_reversal or has_sweep_low:
                # If it satisfies at least 2 of the 3 mandatory conditions, let's print it to see what failed
                print(f"\nTime: {idx} | Price: {row['close']:.4f}")
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

        if found_near_misses == 0:
            print("No setup matched even 1 condition in the last 50 candles.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(debug_lit())
