import asyncio
import pandas as pd
import numpy as np
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner
from config import Config

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'IO/USDT:USDT'
    
    try:
        print("Fetching 800 candles from Binance...")
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        if df.empty:
            print("No data fetched for IO/USDT:USDT")
            return
            
        print("Calculating indicators...")
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        # Convert index to Vietnam timezone (+7) for easy matching
        df.index = df.index + pd.Timedelta(hours=7)
        
        print("\nScanning historically for the last 120 candles...")
        found_signals = []
        for j in range(len(df) - 120, len(df) + 1):
            sub_df = df.iloc[:j]
            if len(sub_df) < 650:
                continue
                
            sub_df_utc = sub_df.copy()
            sub_df_utc.index = sub_df_utc.index - pd.Timedelta(hours=7)
            
            # Print details for candles near the potential setup
            # Let's inspect each candle in the lookback range
            last_candle_time = sub_df_utc.index[-1] + pd.Timedelta(hours=7)
            
            # Check bias
            # Daily and H4 bias
            # We can use the determine_bias if we fetch daily and h4 data
            # For this test, let's try both BULLISH and NEUTRAL bias
            for bias in ["BULLISH", "NEUTRAL"]:
                signal = scanner._check_confluence_setup(sub_df_utc, symbol, bias)
                if signal:
                    sig_ts = pd.to_datetime(signal.timestamp) + pd.Timedelta(hours=7)
                    found_signals.append((sig_ts, bias, signal))
                    print(f"✅ SIGNAL DETECTED AT {sig_ts} with bias {bias}")
                    print(f"   Setup: {signal.setup_type} | Score: {signal.confluence_score}")
                    print(f"   Entry: {signal.entry_price:.4f} | SL: {signal.stop_loss:.4f}")
                    
        # Let's also print technical state of the last 40 candles to diagnose why it might have been skipped
        print("\n--- Technical State of Recent Candles (Last 40 candles) ---")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        # Select columns of interest
        recent_df = df.iloc[-40:].copy()
        
        # We want to see:
        # - Time (index)
        # - Close, Low, High
        # - EMA 34 (dragon_close), 89, 200, 610
        # - sweep_low, ema_squeeze, dragon_narrow, dragon_direction
        # - ema_spread_pct, volume_ratio
        
        cols = ['close', 'high', 'low', 'ema_34_close', 'ema_89', 'ema_200', 'ema_610', 
                'sweep_low', 'ema_squeeze', 'dragon_narrow', 'dragon_direction', 'ema_spread_pct', 'volume_ratio']
        
        # Check which columns exist in df
        cols_to_print = [c for c in cols if c in recent_df.columns]
        print(recent_df[cols_to_print])
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
