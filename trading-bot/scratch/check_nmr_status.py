import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def check_nmr():
    symbol = "NMR/USDT:USDT"
    print(f"=== Analyzing NMR/USDT at 19:15 VN ===")
    
    scanner = SignalScanner()
    try:
        await scanner.data_fetcher.exchange.load_markets()
        
        # Fetch OHLCV
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df.empty:
            print("❌ Failed to fetch NMR data.")
            return
            
        print(f"Fetched {len(df)} candles. Last timestamp: {df.index[-1]}")
        
        # Calculate indicators
        df_indicators = scanner.indicators.calculate_all(df)
        
        # Convert index to VN time
        df_indicators.index = pd.to_datetime(df_indicators.index)
        local_index = df_indicators.index.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh')
        
        found = False
        for i in range(len(df_indicators)):
            time_str = local_index[i].strftime('%Y-%m-%d %H:%M')
            if "2026-06-21 19:10" <= time_str <= "2026-06-21 19:20":
                found = True
                row = df_indicators.iloc[i]
                sub_df = df_indicators.iloc[:i+1]
                
                # Fetch H4 and Daily bias historically at this point
                # For simulation, we can just truncate H4/D1 to the timestamp of this candle
                target_time_utc = df_indicators.index[i]
                
                df_h4 = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_CONTEXT, limit=300)
                df_daily = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_DAILY, limit=200)
                
                df_h4.index = pd.to_datetime(df_h4.index)
                df_daily.index = pd.to_datetime(df_daily.index)
                
                df_h4_hist = df_h4[df_h4.index <= target_time_utc]
                df_daily_hist = df_daily[df_daily.index <= target_time_utc]
                
                df_h4_ind = scanner.indicators.calculate_all(df_h4_hist.copy())
                df_daily_ind = scanner.indicators.calculate_all(df_daily_hist.copy())
                
                bias = scanner._determine_bias(df_daily_ind, df_h4_ind)
                signal = scanner._check_confluence_setup(sub_df, symbol, bias)
                
                print(f"\n==========================================")
                print(f"VN Time: {time_str} | Close: {row['close']:.4f}")
                print(f"==========================================")
                print(f"Daily/4H Bias: {bias}")
                print(f"  • H4 Close: {df_h4_ind.iloc[-1]['close']:.4f} | Dragon: {df_h4_ind.iloc[-1]['dragon_close']:.4f}")
                print(f"  • H4 Trend (partial_bullish): {df_h4_ind.iloc[-1].get('partial_bullish_order', False)}")
                print(f"  • Daily Close: {df_daily_ind.iloc[-1]['close']:.4f} | Dragon: {df_daily_ind.iloc[-1]['dragon_close']:.4f}")
                print(f"  • Daily Trend (partial_bullish): {df_daily_ind.iloc[-1].get('partial_bullish_order', False)}")
                
                if signal:
                    print(f"👉 SIGNAL DETECTED:")
                    print(f"  * Setup Type: {signal.setup_type}")
                    print(f"  * Score: {signal.confluence_score}")
                    print(f"  * Grade: {signal.grade}")
                    print(f"  * Entry: {signal.entry_price:.4f}")
                    print(f"  * SL: {signal.stop_loss:.4f}")
                    print(f"  * TP1: {signal.tp1:.4f} | TP2: {signal.tp2:.4f} | TP3: {signal.tp3:.4f}")
                    print(f"  * Trigger details:\n{signal.trigger_detail}")
                else:
                    print("❌ REJECTED")
                    
        if not found:
            print("❌ Target time range not found in data.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check_nmr())
