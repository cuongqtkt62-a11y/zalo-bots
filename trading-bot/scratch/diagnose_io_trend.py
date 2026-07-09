import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'IO/USDT:USDT'
    try:
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=1000)
        df.index = df.index + pd.Timedelta(hours=7) # VN Time
        
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        timestamps = [
            '2026-06-09 10:25:00',
            '2026-06-09 10:40:00',
            '2026-06-09 10:45:00',
            '2026-06-09 11:05:00',
            '2026-06-09 11:30:00'
        ]
        
        for ts_str in timestamps:
            ts = pd.to_datetime(ts_str)
            if ts not in df.index:
                continue
                
            idx = df.index.get_loc(ts)
            sub_df = df.iloc[:idx+1].copy()
            
            sub_df_utc = sub_df.copy()
            sub_df_utc.index = sub_df_utc.index - pd.Timedelta(hours=7)
            
            last = sub_df_utc.iloc[-1]
            print(f"\n--- Checking candle at {ts_str} ---")
            
            # Check bias
            for bias in ["BULLISH", "NEUTRAL"]:
                sig = scanner._check_confluence_setup(sub_df_utc, symbol, bias)
                if sig:
                    print(f"✅ SIGNAL DETECTED at {ts_str} (Bias={bias}) | Setup={sig.setup_type} | Score={sig.confluence_score}")
                else:
                    # Let's see why it failed:
                    # 1. Check if it passed cond1_compression
                    sq_lb = 5
                    has_squeeze = sub_df_utc['ema_squeeze'].iloc[-sq_lb:].any()
                    has_narrow = sub_df_utc['dragon_narrow'].iloc[-sq_lb:].any()
                    current_spread = last['ema_spread_pct']
                    price_near_ema = (
                        last.get('price_in_ema_cluster', False) or
                        last.get('price_in_dragon', False) or
                        last.get('touch_ema89', False) or
                        last.get('touch_ema200', False)
                    )
                    is_strong_trend_long = last['dragon_close'] > last['ema_89'] and last['ema_89'] > last['ema_200']
                    
                    cond1 = False
                    if has_squeeze and price_near_ema and current_spread <= 6.0:
                        cond1 = True
                    elif has_narrow and price_near_ema and current_spread <= 2.4:
                        cond1 = True
                    elif is_strong_trend_long and price_near_ema:
                        cond1 = True
                        
                    if not cond1:
                        print(f"❌ Failed cond1: has_squeeze={has_squeeze}, has_narrow={has_narrow}, price_near_ema={price_near_ema}, is_strong_trend_long={is_strong_trend_long}")
                        continue
                        
                    # 2. Check if is_trending_long and is_above_dragon
                    is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
                    if last['ema_89'] < last['ema_200']: # We don't have squeeze breakout here
                        is_trending_long = False
                    is_above_dragon = last['close'] > last.get('dragon_low', 0)
                    
                    if not (is_trending_long and is_above_dragon):
                        print(f"❌ Failed trend/position: is_trending_long={is_trending_long}, is_above_dragon={is_above_dragon} (close={last['close']:.4f}, dragon_low={last.get('dragon_low', 0):.4f})")
                        continue
                        
                    # 3. Check long_satisfied trigger
                    # has_reversal_with_sweep or has_squeeze_breakout
                    has_recent_reversal = sub_df_utc['bullish_reversal_at_ema'].iloc[-2:].any()
                    
                    # Squeeze breakout check
                    is_breakout_candle = (
                        (last['close'] > last['dragon_high']) &
                        (last['close'] > last['ema_89']) &
                        (last['close'] > last['ema_200']) &
                        (last['close'] > last['open']) &
                        ((last['close'] - last['open']) > 0.5 * (last['high'] - last['low'])) &
                        (last['volume_ratio'] >= 1.2)
                    )
                    no_trend_violation = not (sub_df_utc['close'].iloc[-12:] < sub_df_utc['ema_200'].iloc[-12:]).any()
                    has_squeeze_breakout = has_squeeze and is_breakout_candle and no_trend_violation
                    
                    print(f"❌ Failed trigger: has_recent_reversal={has_recent_reversal}, has_squeeze_breakout={has_squeeze_breakout}")
                    print(f"   (breakout_candle={is_breakout_candle}, no_trend_violation={no_trend_violation})")
                    
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
