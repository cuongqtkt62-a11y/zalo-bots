import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def check_tao_historical():
    symbol = "TAO/USDT:USDT"
    target_time_vn = "2026-06-21 09:45"
    
    # 09:45 VN time is 02:45 UTC
    target_time_utc = pd.to_datetime("2026-06-21 02:45:00")
    
    print(f"=== Historical Simulation for {symbol} at {target_time_vn} VN ===")
    
    scanner = SignalScanner()
    try:
        await scanner.data_fetcher.exchange.load_markets()
        
        # 1. Fetch data
        df_entry = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=1000)
        df_h4 = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_CONTEXT, limit=500)
        df_daily = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_DAILY, limit=300)
        
        # Convert indices to datetime and localize to UTC
        df_entry.index = pd.to_datetime(df_entry.index)
        df_h4.index = pd.to_datetime(df_h4.index)
        df_daily.index = pd.to_datetime(df_daily.index)
        
        # 2. Truncate datasets to simulate the state of the market at target_time_utc
        # We only keep candles up to target_time_utc
        df_entry_hist = df_entry[df_entry.index <= target_time_utc]
        df_h4_hist = df_h4[df_h4.index <= target_time_utc]
        # For daily candle, at 02:45 UTC on 2026-06-21, the 2026-06-21 daily candle was open,
        # but the last closed daily candle was 2026-06-20 (which is 2026-06-20 00:00:00 UTC).
        df_daily_hist = df_daily[df_daily.index <= target_time_utc]
        
        print(f"Entry data up to: {df_entry_hist.index[-1] if not df_entry_hist.empty else 'N/A'}")
        print(f"H4 context data up to: {df_h4_hist.index[-1] if not df_h4_hist.empty else 'N/A'}")
        print(f"Daily data up to: {df_daily_hist.index[-1] if not df_daily_hist.empty else 'N/A'}")
        
        # 3. Calculate indicators
        df_entry_ind = scanner.indicators.calculate_all(df_entry_hist.copy())
        df_h4_ind = scanner.indicators.calculate_all(df_h4_hist.copy())
        df_daily_ind = scanner.indicators.calculate_all(df_daily_hist.copy())
        
        # 4. Check historical bias
        last_h4 = df_h4_ind.iloc[-1]
        last_daily = df_daily_ind.iloc[-1]
        
        print("\n=== Simulated Historical H4 Context ===")
        print(f"Close: {last_h4['close']:.2f}")
        print(f"EMA 34 (Dragon Close): {last_h4['dragon_close']:.2f}")
        print(f"EMA 89: {last_h4['ema_89']:.2f}")
        print(f"partial_bullish_order: {last_h4.get('partial_bullish_order', False)}")
        print(f"partial_bearish_order: {last_h4.get('partial_bearish_order', False)}")
        
        print("\n=== Simulated Historical Daily Bias ===")
        print(f"Close: {last_daily['close']:.2f}")
        print(f"EMA 34 (Dragon Close): {last_daily['dragon_close']:.2f}")
        print(f"EMA 89: {last_daily['ema_89']:.2f}")
        print(f"partial_bullish_order: {last_daily.get('partial_bullish_order', False)}")
        print(f"partial_bearish_order: {last_daily.get('partial_bearish_order', False)}")
        
        bias = scanner._determine_bias(df_daily_ind, df_h4_ind)
        print(f"\nOverall Bias at target time: {bias}")
        
        # 5. Check confluence setup
        signal = scanner._check_confluence_setup(df_entry_ind, symbol, bias)
        
        print("\n=== Confluence Setup Status ===")
        if signal:
            print(f"🟢 SIGNAL GENERATED!")
            print(f"  Setup: {signal.setup_type} | Score: {signal.confluence_score} | Grade: {signal.grade}")
            print(f"  Entry: {signal.entry_price:.2f} | SL: {signal.stop_loss:.2f} | TP1: {signal.tp1:.2f}")
        else:
            print("❌ REJECTED / NO SIGNAL")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check_tao_historical())
