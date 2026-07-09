import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def analyze_soxl():
    symbol = "SOXL/USDT:USDT"
    print(f"=== SOXL Current State Analysis ===")
    
    scanner = SignalScanner()
    try:
        # Fetch OHLCV data
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=300)
        df_indicators = scanner.indicators.calculate_all(df)
        
        last = df_indicators.iloc[-1]
        print(f"Current Price: {last['close']:.2f}")
        print(f"EMA 34 (Dragon): {last.get('dragon_close', 0):.2f}")
        print(f"EMA 89: {last.get('ema_89', 0):.2f}")
        print(f"EMA 200: {last.get('ema_200', 0):.2f}")
        print(f"EMA 610: {last.get('ema_610', 0):.2f}")
        
        # Check if EMA order is still bullish
        ema_order_ok = last['dragon_close'] > last['ema_89'] and last['ema_89'] > last['ema_200']
        print(f"EMA Bullish Order: {ema_order_ok}")
        
        # Is price still above EMA 89/200?
        above_ema_89 = last['close'] > last['ema_89']
        above_ema_200 = last['close'] > last['ema_200']
        print(f"Close > EMA 89: {above_ema_89} | Close > EMA 200: {above_ema_200}")
        
        # Check RSI and ATR
        print(f"RSI (5m): {last.get('rsi', 0):.1f}")
        print(f"ATR (5m): {last.get('atr', 0):.2f} ({last.get('atr', 0)/last['close']*100:.2f}%)")
        
        # Recent candles trend
        tail_5 = df_indicators.tail(5)
        print("\nLast 5 candles:")
        for idx, row in tail_5.iterrows():
            print(f"  {idx} | Open: {row['open']:.2f} | High: {row['high']:.2f} | Low: {row['low']:.2f} | Close: {row['close']:.2f} | Vol Ratio: {row.get('volume_ratio', 0):.2f}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(analyze_soxl())
