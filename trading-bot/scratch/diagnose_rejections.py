import asyncio
import pandas as pd
from config import Config
from signal_scanner import SignalScanner

async def diagnose():
    print("Starting detailed diagnostic scan on top 5 volume symbols...")
    scanner = SignalScanner()
    try:
        symbols = await scanner.data_fetcher.get_symbol_names(5)
        
        for symbol in symbols:
            print(f"\n--- {symbol} (Last 200 candles) ---")
            df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
            if df.empty:
                continue
            df = scanner.indicators.calculate_all(df)
            
            recent = df.iloc[-200:]
            n_compression = 0
            n_reversal_at_ema = 0
            n_sweep_low = 0
            n_both_reversal_and_sweep = 0
            
            for i in range(20, len(recent)):
                idx = recent.index[i]
                row = recent.iloc[i]
                sub_df = df.loc[:idx]
                
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
                if cond1:
                    n_compression += 1
                
                # Reversal
                has_reversal = row.get('bullish_reversal_at_ema', False)
                if has_reversal:
                    n_reversal_at_ema += 1
                    
                # Sweep low
                has_sweep = row.get('sweep_low', False)
                if has_sweep:
                    n_sweep_low += 1
                    
                # Both on same candle
                if has_reversal and has_sweep:
                    n_both_reversal_and_sweep += 1
                    print(f"  [Match Same Candle] {idx} | Price: {row['close']:.4f} | is_trending_long: {row.get('dragon_direction') in ('UP', 'FLAT')}")
                    
            print(f"  Compression at EMA count: {n_compression}")
            print(f"  Reversal at EMA count: {n_reversal_at_ema}")
            print(f"  Sweep Low count: {n_sweep_low}")
            print(f"  Both Reversal & Sweep on same candle: {n_both_reversal_and_sweep}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
