import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def check_lista():
    symbol = "LISTA/USDT:USDT"
    print(f"=== Analyzing LISTA/USDT ===")
    
    scanner = SignalScanner()
    try:
        # Fetch OHLCV
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df.empty:
            print("❌ Failed to fetch LISTA data.")
            return
            
        print(f"Fetched {len(df)} candles. Last timestamp: {df.index[-1]}")
        
        # Calculate indicators
        df_indicators = scanner.indicators.calculate_all(df)
        
        # We look at the last 15 candles
        recent = df_indicators.iloc[-15:]
        print("\nChecking recent candles for setups:")
        for idx, row in recent.iterrows():
            sub_df = df_indicators.loc[:idx]
            
            # Check confluence setup
            bias = "NEUTRAL"
            signal = scanner._check_confluence_setup(sub_df, symbol, bias)
            
            ema34 = row.get('dragon_close', 0)
            ema_89 = row.get('ema_89', 0)
            ema_200 = row.get('ema_200', 0)
            ema_610 = row.get('ema_610', 0)
            
            has_squeeze = sub_df['ema_squeeze'].iloc[-15:].any()
            has_narrow = sub_df['dragon_narrow'].iloc[-15:].any()
            price_near_ema = (
                row.get('price_in_ema_cluster', False) or
                row.get('price_in_dragon', False) or
                row.get('touch_ema89', False) or
                row.get('touch_ema200', False)
            )
            
            has_reversal = sub_df['bullish_reversal_at_ema'].iloc[-3:].any()
            has_sweep = sub_df['sweep_low'].iloc[-45:].any()
            
            if row.get('volume_ratio', 0) > 1.2 or signal:
                status_str = "🟢 MATCHED" if signal else "❌ REJECTED"
                print(f"\nTime: {idx} | Close: {row['close']:.5f} | {status_str}")
                print(f"  EMA 34: {ema34:.5f} | EMA 89: {ema_89:.5f} | EMA 200: {ema_200:.5f} | EMA 610: {ema_610:.5f}")
                print(f"  EMA Order (34>89>200): {ema34 > ema_89 > ema_200}")
                print(f"  Squeeze/Narrow in 15c: {has_squeeze}/{has_narrow} | Near EMA: {price_near_ema}")
                print(f"  Reversal in 3c: {has_reversal} | Sweep low in 45c: {has_sweep}")
                print(f"  Volume Ratio: {row.get('volume_ratio', 0):.2f}")
                
                if signal:
                    print(f"  >>> SIGNAL DETAILS:")
                    print(f"    * Direction: {signal.direction}")
                    print(f"    * Setup: {signal.setup_type}")
                    print(f"    * Score: {signal.confluence_score}")
                    print(f"    * Entry: {signal.entry_price}")
                    print(f"    * SL: {signal.stop_loss}")
                    print(f"    * TP1: {signal.tp1} | TP2: {signal.tp2} | TP3: {signal.tp3}")
                    print(f"    * Risk/Reward: {signal.risk_reward:.2f}")
                    print(f"    * Volume detail: {signal.volume_detail}")
                    
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check_lista())
