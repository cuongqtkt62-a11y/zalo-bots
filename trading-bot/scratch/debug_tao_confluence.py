import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def debug_tao():
    symbol = "TAO/USDT:USDT"
    scanner = SignalScanner()
    try:
        await scanner.data_fetcher.exchange.load_markets()
        df_entry = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=1000)
        df_entry.index = pd.to_datetime(df_entry.index)
        
        target_time_utc = pd.to_datetime("2026-06-21 02:45:00")
        df_entry_hist = df_entry[df_entry.index <= target_time_utc]
        df_entry_ind = scanner.indicators.calculate_all(df_entry_hist.copy())
        
        # Localize index to VN time
        local_index = df_entry_ind.index.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh')
        
        # Print indicators around 09:15 to 09:45 VN time
        print("=== TAO Candlestick Details around 09:15 to 09:45 VN ===")
        for i in range(len(df_entry_ind)):
            time_str = local_index[i].strftime('%Y-%m-%d %H:%M')
            if "2026-06-21 09:10" <= time_str <= "2026-06-21 09:45":
                row = df_entry_ind.iloc[i]
                print(f"\nTime: {time_str} | Close: {row['close']:.2f}")
                print(f"  bullish_reversal_at_ema: {row['bullish_reversal_at_ema']}")
                print(f"  is_spring: {row['is_spring']} | is_hammer: {row['is_hammer']} | is_bull_engulfing: {row['is_bull_engulfing']}")
                print(f"  lower_wick_ratio: {row['lower_wick_ratio']:.2%} | volume_ratio: {row['volume_ratio']:.2f}")
                print(f"  sweep_low: {row['sweep_low']} (Level: {row['sweep_low_level']})")
                print(f"  price_in_dragon: {row['price_in_dragon']} | touch_ema89: {row['touch_ema89']} | touch_ema200: {row['touch_ema200']}")

        # Trace _check_confluence_setup
        print("\n=== Tracing Confluence Logic at 09:45 VN ===")
        bias = "BEARISH"
        
        df = df_entry_ind
        last = df.iloc[-1]
        
        # Check compression
        sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES
        has_squeeze = df['ema_squeeze'].iloc[-sq_lb:].any()
        has_narrow = df['dragon_narrow'].iloc[-sq_lb:].any()
        current_spread = last.get('ema_spread_pct', 100)
        
        print(f"Squeeze: has_squeeze={has_squeeze}, has_narrow={has_narrow}, spread={current_spread:.2f}%")
        
        # Pullback/Trend Setup
        is_strong_trend_long = (last['dragon_close'] > last['ema_89']) & (last['ema_89'] > last['ema_200'])
        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )
        print(f"Trend Pullback check: is_strong_trend_long={is_strong_trend_long}, price_near_ema={price_near_ema}")
        
        # check_long scanning
        sweep_lookback = 35
        has_reversal_with_sweep = False
        rev_indices = []
        for idx in range(-1, -11, -1):
            if df['bullish_reversal_at_ema'].iloc[idx]:
                rev_indices.append(idx)
        print(f"Reversal indices in last 10 candles: {rev_indices}")
        
        if rev_indices:
            for rev_idx in rev_indices:
                rev_time = local_index[len(df) + rev_idx].strftime('%Y-%m-%d %H:%M')
                rev_candle_low = df['low'].iloc[rev_idx]
                is_rev_broken = (df['close'].iloc[rev_idx:] < rev_candle_low).any()
                print(f"  Checking reversal at {rev_time} (idx={rev_idx}), low={rev_candle_low:.2f}. Is broken? {is_rev_broken}")
                if is_rev_broken:
                    continue
                    
                for idx in range(rev_idx, rev_idx - sweep_lookback, -1):
                    if df['sweep_low'].iloc[idx]:
                        sweep_time = local_index[len(df) + idx].strftime('%Y-%m-%d %H:%M')
                        sweep_candle_low = df['low'].iloc[idx]
                        sweep_distance = abs(last['close'] - sweep_candle_low)
                        closed_below = (df['close'].iloc[idx:] < sweep_candle_low).any()
                        print(f"    Found sweep_low at {sweep_time} (idx={idx}), Low={sweep_candle_low:.2f}. Sweep distance ATR: {sweep_distance / last.get('atr', 1):.1f}x. Closed below? {closed_below}")
                        if sweep_distance <= 3.0 * last.get('atr', 0) and not closed_below:
                            has_reversal_with_sweep = True
                            print("    -> Match found!")
                            break
                if has_reversal_with_sweep:
                    break
                    
        print(f"Final has_reversal_with_sweep: {has_reversal_with_sweep}")
        
        is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
        is_above_dragon = last['close'] > last.get('dragon_close', 0)
        
        if has_reversal_with_sweep:
            is_trending_long = True
            is_above_dragon = True
            print("  Overrode is_trending_long & is_above_dragon to True.")
            
        print(f"is_trending_long: {is_trending_long}, is_above_dragon: {is_above_dragon}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(debug_tao())
