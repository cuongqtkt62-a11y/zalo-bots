import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner
from config import Config

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'IO/USDT:USDT'
    try:
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=1000)
        df.index = df.index + pd.Timedelta(hours=7) # VN Time
        
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        # Target timestamp: 10:25:00
        target_ts = pd.to_datetime('2026-06-09 10:45:00')
        if target_ts not in df.index:
            print(f"Timestamp {target_ts} not found in fetched data!")
            return
            
        idx = df.index.get_loc(target_ts)
        sub_df = df.iloc[:idx+1].copy()
        
        # Convert index back to UTC for the scanner
        sub_df_utc = sub_df.copy()
        sub_df_utc.index = sub_df_utc.index - pd.Timedelta(hours=7)
        
        last = sub_df_utc.iloc[-1]
        print(f"=== Diagnosing candle at {target_ts} (VN Time) ===")
        print(f"Close: {last['close']:.4f} | Open: {last['open']:.4f} | High: {last['high']:.4f} | Low: {last['low']:.4f}")
        print(f"EMAs: dragon_close: {last['dragon_close']:.4f} | ema_89: {last['ema_89']:.4f} | ema_200: {last['ema_200']:.4f} | ema_610: {last['ema_610']:.4f}")
        
        # Let's run trace on cond1_compression
        sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES
        has_squeeze = sub_df_utc['ema_squeeze'].iloc[-sq_lb:].any()
        has_narrow = sub_df_utc['dragon_narrow'].iloc[-sq_lb:].any()
        current_spread = last['ema_spread_pct']
        
        ema_cluster_center = (last['ema_89'] + last['ema_200']) / 2
        price_distance_pct = abs(last['close'] - ema_cluster_center) / ema_cluster_center * 100
        price_distance_abs = abs(last['close'] - ema_cluster_center)
        atr = last['atr']
        
        print(f"has_squeeze (last {sq_lb}): {has_squeeze}")
        print(f"has_narrow (last {sq_lb}): {has_narrow}")
        print(f"current_spread: {current_spread:.2f}%")
        print(f"price_distance_pct: {price_distance_pct:.2f}% (max allowed: {Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT}%)")
        print(f"price_distance_abs: {price_distance_abs:.4f} vs 2*atr: {2*atr:.4f}")
        
        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )
        print(f"price_near_ema: {price_near_ema} (details: price_in_ema_cluster={last.get('price_in_ema_cluster')}, price_in_dragon={last.get('price_in_dragon')}, touch_ema89={last.get('touch_ema89')}, touch_ema200={last.get('touch_ema200')})")
        
        is_strong_trend_long = last['dragon_close'] > last['ema_89'] and last['ema_89'] > last['ema_200']
        print(f"is_strong_trend_long: {is_strong_trend_long} (dragon_close > ema_89: {last['dragon_close'] > last['ema_89']}, ema_89 > ema_200: {last['ema_89'] > last['ema_200']})")
        
        # Test long conditions
        sweep_lookback = 35
        has_reversal_with_sweep = False
        has_recent_reversal = sub_df_utc['bullish_reversal_at_ema'].iloc[-2:].any()
        print(f"has_recent_reversal: {has_recent_reversal} (bullish_reversal_at_ema last 2: {sub_df_utc['bullish_reversal_at_ema'].iloc[-2:].tolist()})")
        
        # Print reversal indicators
        print(f"Prev candle reversal components:")
        prev = sub_df_utc.iloc[-2]
        print(f"   is_spring: {prev['is_spring']} | is_hammer: {prev['is_hammer']} | is_bull_engulfing: {prev['is_bull_engulfing']} | price_in_dragon: {prev['price_in_dragon']} | touch_ema89: {prev['touch_ema89']} | touch_ema200: {prev['touch_ema200']}")
        print(f"Current candle reversal components:")
        print(f"   is_spring: {last['is_spring']} | is_hammer: {last['is_hammer']} | is_bull_engulfing: {last['is_bull_engulfing']} | price_in_dragon: {last['price_in_dragon']} | touch_ema89: {last['touch_ema89']} | touch_ema200: {last['touch_ema200']}")
        
        # Check sweep search
        sweep_found_details = []
        if has_recent_reversal:
            for idx in range(-1, -sweep_lookback, -1):
                if sub_df_utc['sweep_low'].iloc[idx]:
                    sweep_candle_low = sub_df_utc['low'].iloc[idx]
                    closed_below = (sub_df_utc['close'].iloc[idx:] < sweep_candle_low).any()
                    sweep_found_details.append(f"Sweep found at {sub_df_utc.index[idx] + pd.Timedelta(hours=7)}: low={sweep_candle_low}, closed_below={closed_below}")
        print(f"Sweep search trace: {sweep_found_details}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
