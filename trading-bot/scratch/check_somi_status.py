import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def check_somi():
    symbol = "SOMI/USDT:USDT"
    print(f"=== Debugging SOMI/USDT ===")
    
    scanner = SignalScanner()
    try:
        # Fetch OHLCV
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df.empty:
            print("❌ Failed to fetch SOMI data.")
            return
            
        print(f"Fetched {len(df)} candles. Last timestamp: {df.index[-1]}")
        
        # Calculate indicators
        df_indicators = scanner.indicators.calculate_all(df)
        
        # Find the breakout candle (look for the largest volume spike or close change in last 50 candles)
        recent = df_indicators.iloc[-50:]
        print("\nChecking recent candles for setups:")
        for idx, row in recent.iterrows():
            sub_df = df_indicators.loc[:idx]
            
            # Check confluence setup
            bias = "NEUTRAL" # Let's assume NEUTRAL bias for debug
            signal = scanner._check_confluence_setup(sub_df, symbol, bias)
            
            # Print if there was any sweep or squeeze indicator
            ema34 = row.get('dragon_close', 0)
            ema_89 = row.get('ema_89', 0)
            ema_200 = row.get('ema_200', 0)
            ema_spread = row.get('ema_spread_pct', 0)
            
            has_squeeze = sub_df['ema_squeeze'].iloc[-15:].any()
            has_narrow = sub_df['dragon_narrow'].iloc[-15:].any()
            price_near_ema = (
                row.get('price_in_ema_cluster', False) or
                row.get('price_in_dragon', False) or
                row.get('touch_ema89', False) or
                row.get('touch_ema200', False)
            )
            
            # Bullish reversal and sweep check
            has_reversal = sub_df['bullish_reversal_at_ema'].iloc[-3:].any()
            has_sweep = sub_df['sweep_low'].iloc[-20:].any()
            
            # Print status if it's the breakout candle or near it
            if row.get('volume_ratio', 0) > 2.0 or signal:
                status_str = "🟢 MATCHED" if signal else "❌ REJECTED"
                print(f"\nTime: {idx} | Close: {row['close']:.4f} | {status_str}")
                print(f"  EMA Order (34>89>200): {ema34 > ema_89 > ema_200} (34: {ema34:.4f}, 89: {ema_89:.4f}, 200: {ema_200:.4f})")
                print(f"  Squeeze/Narrow in 15c: {has_squeeze}/{has_narrow} | Near EMA: {price_near_ema}")
                print(f"  Reversal in 3c: {has_reversal} | Sweep low in 20c: {has_sweep}")
                print(f"  Volume Ratio: {row.get('volume_ratio', 0):.2f} (Vol: {row['volume']:.0f})")
                
                # Check why it would be rejected if it didn't trigger
                if not signal:
                    # Let's print the exact hard filter values
                    ema_cluster_center = (ema_89 + ema_200) / 2
                    price_distance_pct = abs(row['close'] - ema_cluster_center) / ema_cluster_center * 100
                    price_distance_abs = abs(row['close'] - ema_cluster_center)
                    atr_val = row.get('atr', 0)
                    
                    print(f"  Rejection Details:")
                    print(f"    * Price distance pct: {price_distance_pct:.2f}% vs max {Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT}%")
                    print(f"    * Price distance abs: {price_distance_abs:.5f} vs max 3.0*ATR: {3.0*atr_val:.5f}")
                    
        # Let's check 24h volume in ccxt to see if it was excluded by volume filter
        ticker = await scanner.data_fetcher.exchange.fetch_ticker(symbol)
        quote_volume = ticker.get('quoteVolume', 0)
        print(f"\n24h Quote Volume for SOMI: ${quote_volume/1e6:.2f}M")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check_somi())
