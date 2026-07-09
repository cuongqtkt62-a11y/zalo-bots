import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner
from config import Config

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'MYX/USDT:USDT'
    
    try:
        # Fetch 800 candles (exactly like the bot)
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        df = TechnicalIndicators.calculate_all(df)
        
        # Convert index to VN time
        df_vn = df.copy()
        df_vn.index = df_vn.index + pd.Timedelta(hours=7)
        
        # Check candles around 13:30, 13:35, 13:40, 13:45
        target_times = [
            pd.to_datetime('2026-06-08 13:30:00'),
            pd.to_datetime('2026-06-08 13:35:00'),
            pd.to_datetime('2026-06-08 13:40:00'),
            pd.to_datetime('2026-06-08 13:45:00')
        ]
        
        for target_time in target_times:
            if target_time not in df_vn.index:
                print(f"Time {target_time} not in index.")
                continue
                
            idx = df_vn.index.get_loc(target_time)
            sub_df = df.iloc[:idx+1]
            
            print(f"\n--- DEBUG FOR {target_time} (VN Time) ---")
            last = sub_df.iloc[-1]
            
            # Check hard filters
            atr_pct = last['atr'] / last['close'] * 100
            print(f"ATR %: {atr_pct:.4f}% (Min: {Config.MIN_ATR_PCT}%)")
            print(f"EMA 610: {last.get('ema_610', None)}")
            
            # Check compression
            sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES
            has_squeeze = sub_df['ema_squeeze'].iloc[-sq_lb:].any()
            has_narrow = sub_df['dragon_narrow'].iloc[-sq_lb:].any()
            current_spread = last.get('ema_spread_pct', 100)
            
            price_near_ema = (
                last.get('price_in_ema_cluster', False) or
                last.get('price_in_dragon', False) or
                last.get('touch_ema89', False) or
                last.get('touch_ema200', False)
            )
            
            cond1_compression = False
            if has_squeeze and price_near_ema:
                cond1_compression = True
            elif has_narrow and price_near_ema and current_spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2:
                cond1_compression = True
            print(f"Compression (Cond 1): {cond1_compression} (Squeeze: {has_squeeze}, Narrow: {has_narrow}, Near EMA: {price_near_ema}, Spread: {current_spread:.2f}%)")
            
            # Check Long
            reversal_with_sweep = sub_df['bullish_reversal_at_ema'] & sub_df['sweep_low']
            has_reversal_with_sweep = reversal_with_sweep.iloc[-3:].any()
            print(f"Sweep Low (current): {sub_df['sweep_low'].iloc[-1]}")
            print(f"Bullish Reversal (current): {sub_df['bullish_reversal_at_ema'].iloc[-1]}")
            print(f"has_reversal_with_sweep (last 3): {has_reversal_with_sweep}")
            
            # Check Squeeze Breakout
            has_recent_squeeze = sub_df['ema_squeeze'].iloc[-5:-1].any()
            if not has_recent_squeeze:
                has_recent_squeeze = (
                    sub_df['dragon_narrow'].iloc[-5:-1].any() and
                    sub_df['ema_spread_pct'].iloc[-5:-1].min() <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2
                )
            bo_ema_center = (sub_df['ema_89'].iloc[-1] + sub_df['ema_200'].iloc[-1] + sub_df['ema_610'].iloc[-1]) / 3
            breakout_distance_pct = abs(sub_df['close'].iloc[-1] - bo_ema_center) / bo_ema_center * 100
            breakout_distance_abs = abs(sub_df['close'].iloc[-1] - bo_ema_center)
            
            is_breakout_candle = (
                (sub_df['close'].iloc[-1] > sub_df['dragon_high'].iloc[-1]) &
                (sub_df['close'].iloc[-1] > sub_df['ema_89'].iloc[-1]) &
                (sub_df['close'].iloc[-1] > sub_df['ema_200'].iloc[-1]) &
                (sub_df['close'].iloc[-1] > sub_df['open'].iloc[-1]) &
                ((sub_df['close'].iloc[-1] - sub_df['open'].iloc[-1]) > 0.5 * (sub_df['high'].iloc[-1] - sub_df['low'].iloc[-1])) &
                (sub_df['volume_ratio'].iloc[-1] >= 1.2) &
                (breakout_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5) &
                (breakout_distance_abs <= 2.5 * sub_df['atr'].iloc[-1])
            )
            no_trend_violation = not (sub_df['close'].iloc[-12:] < sub_df['ema_200'].iloc[-12:]).any()
            has_squeeze_breakout = has_recent_squeeze and is_breakout_candle and no_trend_violation
            print(f"Squeeze Breakout: {has_squeeze_breakout} (Recent Squeeze: {has_recent_squeeze}, Breakout Candle: {is_breakout_candle}, No Trend Violation: {no_trend_violation})")
            
            is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
            is_above_dragon = last['close'] > last.get('dragon_low', 0)
            if last['ema_89'] < last['ema_200'] and not has_squeeze_breakout:
                is_trending_long = False
            print(f"Trending Long: {is_trending_long} (Dragon dir: {last.get('dragon_direction', 'FLAT')}, Above dragon: {is_above_dragon})")
            
            # Let's run the scanner on this slice
            # Override TRADE_DIRECTION to BOTH to be sure
            signal = scanner._check_confluence_setup(sub_df, symbol, bias="NEUTRAL")
            if signal:
                print(f"👉 Scanner result: SUCCESS! Grade: {signal.grade}, Score: {signal.confluence_score}")
            else:
                print("👉 Scanner result: FAILED")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
