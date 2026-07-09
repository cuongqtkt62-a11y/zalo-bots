import asyncio
import pandas as pd
from config import Config
from signal_scanner import SignalScanner

async def test_rules():
    symbol = "AKT/USDT:USDT"
    scanner = SignalScanner()
    try:
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        df = scanner.indicators.calculate_all(df)
        
        target_time = pd.to_datetime("2026-05-25 00:25:00")
        if target_time not in df.index:
            matches = [t for t in df.index if t.hour == 0 and t.minute in (25, 40) and t.day == 25]
            if not matches:
                print("No matches.")
                return
            target_time = matches[-1]
            
        print(f"\nTesting new rules at {target_time}:")
        sub_df = df.loc[:target_time]
        last = sub_df.iloc[-1]
        
        has_squeeze = sub_df['ema_squeeze'].iloc[-15:].any()
        has_narrow = sub_df['dragon_narrow'].iloc[-15:].any()
        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )
        cond1 = (has_squeeze or has_narrow) and price_near_ema
        
        has_bull_reversal = sub_df['bullish_reversal_at_ema'].iloc[-3:].any()
        has_sweep_low = sub_df['sweep_low'].iloc[-20:].any()
        
        # Current rules
        curr_is_trending_long = last.get('dragon_direction', 'FLAT') == 'UP'
        curr_is_above_dragon = last['close'] > last.get('dragon_close', 0)
        curr_passed = has_bull_reversal and has_sweep_low and curr_is_trending_long and curr_is_above_dragon
        
        # New rules
        new_is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
        new_is_above_dragon = last['close'] > last.get('dragon_low', 0)
        new_passed = has_bull_reversal and has_sweep_low and new_is_trending_long and new_is_above_dragon
        
        print(f"Candle: Close={last['close']:.4f}, Dragon Close={last.get('dragon_close'):.4f}, Dragon Low={last.get('dragon_low'):.4f}")
        print(f"Current Rules: Trend UP={curr_is_trending_long}, Close Above Close={curr_is_above_dragon} -> PASSED: {curr_passed}")
        print(f"New Rules: Trend in (UP, FLAT)={new_is_trending_long}, Close Above Low={new_is_above_dragon} -> PASSED: {new_passed}")
        
        # Let's also check the next candles, e.g. 00:40:00
        print("\nTesting 00:40:00:")
        target_time_40 = pd.to_datetime("2026-05-25 00:40:00")
        if target_time_40 in df.index:
            sub_df_40 = df.loc[:target_time_40]
            last_40 = sub_df_40.iloc[-1]
            has_bull_reversal_40 = sub_df_40['bullish_reversal_at_ema'].iloc[-3:].any()
            has_sweep_low_40 = sub_df_40['sweep_low'].iloc[-20:].any()
            
            new_is_trending_long_40 = last_40.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
            new_is_above_dragon_40 = last_40['close'] > last_40.get('dragon_low', 0)
            new_passed_40 = has_bull_reversal_40 and has_sweep_low_40 and new_is_trending_long_40 and new_is_above_dragon_40
            print(f"Candle 40: Close={last_40['close']:.4f}, Dragon Close={last_40.get('dragon_close'):.4f}, Dragon Low={last_40.get('dragon_low'):.4f}")
            print(f"New Rules -> PASSED: {new_passed_40}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(test_rules())
