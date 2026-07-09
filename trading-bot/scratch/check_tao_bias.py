import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def check_tao_bias():
    symbol = "TAO/USDT:USDT"
    scanner = SignalScanner()
    try:
        await scanner.data_fetcher.exchange.load_markets()
        
        # Fetch Context (4h) and Daily (1d) data
        df_h4 = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_CONTEXT, limit=200)
        df_daily = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_DAILY, limit=200)
        
        print("\n=== Daily Chart (1d) Indicators for TAO ===")
        if not df_daily.empty:
            df_daily_ind = scanner.indicators.calculate_all(df_daily)
            last_d1 = df_daily_ind.iloc[-1]
            close_d1 = last_d1['close']
            dragon_close_d1 = last_d1.get('dragon_close', 0)
            ema_89_d1 = last_d1.get('ema_89', 0)
            partial_bull_d1 = last_d1.get('partial_bullish_order', False)
            partial_bear_d1 = last_d1.get('partial_bearish_order', False)
            
            print(f"Close: {close_d1:.2f}")
            print(f"EMA 34 (Dragon Close): {dragon_close_d1:.2f}")
            print(f"EMA 89: {ema_89_d1:.2f}")
            print(f"partial_bullish_order: {partial_bull_d1}")
            print(f"partial_bearish_order: {partial_bear_d1}")
            print(f"Order Check (Close > Dragon > 89): {close_d1 > dragon_close_d1 > ema_89_d1}")
            print(f"Order Check (Close < Dragon < 89): {close_d1 < dragon_close_d1 < ema_89_d1}")
        else:
            print("❌ Empty Daily data")
            
        print("\n=== Context Chart (4h) Indicators for TAO ===")
        if not df_h4.empty:
            df_h4_ind = scanner.indicators.calculate_all(df_h4)
            last_h4 = df_h4_ind.iloc[-1]
            close_h4 = last_h4['close']
            dragon_close_h4 = last_h4.get('dragon_close', 0)
            ema_89_h4 = last_h4.get('ema_89', 0)
            partial_bull_h4 = last_h4.get('partial_bullish_order', False)
            partial_bear_h4 = last_h4.get('partial_bearish_order', False)
            
            print(f"Close: {close_h4:.2f}")
            print(f"EMA 34 (Dragon Close): {dragon_close_h4:.2f}")
            print(f"EMA 89: {ema_89_h4:.2f}")
            print(f"partial_bullish_order: {partial_bull_h4}")
            print(f"partial_bearish_order: {partial_bear_h4}")
            print(f"Order Check (Close > Dragon > 89): {close_h4 > dragon_close_h4 > ema_89_h4}")
            print(f"Order Check (Close < Dragon < 89): {close_h4 < dragon_close_h4 < ema_89_h4}")
        else:
            print("❌ Empty 4h data")
            
        # Determine overall bias
        bias = scanner._determine_bias(df_daily, df_h4)
        print(f"\nFinal determined bias: {bias}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check_tao_bias())
