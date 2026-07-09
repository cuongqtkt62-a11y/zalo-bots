import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def check_algo():
    symbol = "ALGO/USDT:USDT"
    print(f"=== Analyzing ALGO/USDT ===")
    
    scanner = SignalScanner()
    try:
        # Fetch OHLCV (limit 800 to get enough history)
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df.empty:
            print("❌ Failed to fetch ALGO data.")
            return
            
        print(f"Fetched {len(df)} candles. Last timestamp: {df.index[-1]}")
        
        # Calculate indicators
        df_indicators = scanner.indicators.calculate_all(df)
        
        # Scan for the candle close to 09:02 (02:02 UTC)
        # The timezone is +07:00, so we can convert df index to local time or match string
        df_indicators.index = pd.to_datetime(df_indicators.index)
        local_index = df_indicators.index.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh')
        
        found = False
        for i in range(len(df_indicators)):
            time_str = local_index[i].strftime('%Y-%m-%d %H:%M')
            # Look at candles between 08:55 and 09:10
            if "2026-06-21 08:50" <= time_str <= "2026-06-21 09:15":
                found = True
                row = df_indicators.iloc[i]
                sub_df = df_indicators.iloc[:i+1]
                
                # Check confluence setup
                bias = await scanner._get_cached_bias(symbol)
                signal = scanner._check_confluence_setup(sub_df, symbol, bias)
                
                ema34 = row.get('dragon_close', 0)
                ema_89 = row.get('ema_89', 0)
                ema_200 = row.get('ema_200', 0)
                ema_610 = row.get('ema_610', 0)
                
                has_squeeze = sub_df['ema_squeeze'].iloc[-15:].any()
                has_narrow = sub_df['dragon_narrow'].iloc[-15:].any()
                
                status_str = "🟢 MATCHED" if signal else "❌ REJECTED"
                print(f"\nTime (VN): {time_str} | Close: {row['close']:.5f} | {status_str}")
                print(f"  EMA 34 (Dragon Close): {ema34:.5f} | EMA 89: {ema_89:.5f} | EMA 200: {ema_200:.5f}")
                print(f"  EMA Order (34>89>200): {ema34 > ema_89 > ema_200}")
                print(f"  EMA Direction (dragon_direction): {row.get('dragon_direction', 'NONE')}")
                print(f"  Squeeze/Narrow in 15c: {has_squeeze}/{has_narrow}")
                print(f"  Volume Ratio: {row.get('volume_ratio', 0):.2f}")
                
                if signal:
                    print(f"  >>> SIGNAL DETAILS:")
                    print(f"    * Direction: {signal.direction}")
                    print(f"    * Setup: {signal.setup_type}")
                    print(f"    * Score: {signal.confluence_score}")
                    print(f"    * Entry: {signal.entry_price}")
                    print(f"    * SL: {signal.stop_loss}")
                    print(f"    * TP1: {signal.tp1} | TP2: {signal.tp2} | TP3: {signal.tp3}")
                    
        if not found:
            print("❌ Target time range not found in data.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check_algo())
