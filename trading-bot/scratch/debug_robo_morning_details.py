import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner
from config import Config

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'ROBO/USDT:USDT'
    try:
        df_raw = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        df_raw_vn = df_raw.copy()
        df_raw_vn.index = df_raw_vn.index + pd.Timedelta(hours=7)
        
        # Sáng nay từ 07:30 đến 08:30 VN Time
        target_indices = df_raw_vn.loc['2026-06-09 07:30:00':'2026-06-09 08:30:00'].index
        
        print("--- Detailed Simulation of ROBO/USDT (Morning June 9th) ---")
        for ts_vn in target_indices:
            ts_utc = ts_vn - pd.Timedelta(hours=7)
            idx = df_raw.index.get_loc(ts_utc)
            sub_df_raw = df_raw.iloc[:idx+1].copy()
            
            indicators = TechnicalIndicators()
            sub_df = indicators.calculate_all(sub_df_raw)
            
            last = sub_df.iloc[-1]
            last_ts_vn = sub_df.index[-1] + pd.Timedelta(hours=7)
            
            # Print indicators at this candle
            close = last['close']
            open_val = last['open']
            low = last['low']
            high = last['high']
            ema34 = last['dragon_close']
            ema89 = last['ema_89']
            ema200 = last['ema_200']
            ema610 = last['ema_610']
            spread = last['ema_spread_pct']
            vol_ratio = last['volume_ratio']
            sweep_low = last['sweep_low']
            bull_reversal = last['bullish_reversal_at_ema']
            
            # Run manual checks corresponding to _check_confluence_setup
            # Check cond1
            sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES
            has_squeeze = sub_df['ema_squeeze'].iloc[-sq_lb:].any()
            has_narrow = sub_df['dragon_narrow'].iloc[-sq_lb:].any()
            
            ema_cluster_center = (ema89 + ema200) / 2
            price_distance_pct = abs(close - ema_cluster_center) / ema_cluster_center * 100
            price_distance_abs = abs(close - ema_cluster_center)
            atr = last.get('atr', 0)
            
            cond1_ok = False
            price_near_ema = (
                last.get('price_in_ema_cluster', False) or
                last.get('price_in_dragon', False) or
                last.get('touch_ema89', False) or
                last.get('touch_ema200', False)
            )
            
            is_strong_trend_long = (ema34 > ema89) and (ema89 > ema200)
            
            cond1_reason = ""
            max_dist_pct = Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT
            is_squeezed_state = has_squeeze or (has_narrow and spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2)
            if is_squeezed_state:
                max_dist_pct *= 1.5
                
            if price_distance_pct > max_dist_pct and price_distance_abs > 2.0 * atr:
                cond1_reason = f"price distance too far ({price_distance_pct:.2f}% > {max_dist_pct:.2f}% and dist_abs {price_distance_abs:.5f} > 2.0*ATR {2.0*atr:.5f})"
            elif has_squeeze and price_near_ema and spread <= Config.MAX_EMA_SPREAD_PCT:
                cond1_ok = True
                cond1_reason = "Squeeze"
            elif has_narrow and price_near_ema and spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2:
                cond1_ok = True
                cond1_reason = "Dragon narrow"
            elif is_strong_trend_long and price_near_ema:
                cond1_ok = True
                cond1_reason = "Strong trend pullback"
            else:
                cond1_reason = f"no squeeze, no narrow, not strong trend pullback or price not near EMA (price_near_ema={price_near_ema})"
                
            # Sweep check
            sweep_lookback = 35
            has_reversal_with_sweep = False
            has_recent_reversal = sub_df['bullish_reversal_at_ema'].iloc[-8:].any()
            
            sweep_reason = ""
            if has_recent_reversal:
                for s_idx in range(-1, -sweep_lookback, -1):
                    if sub_df['sweep_low'].iloc[s_idx]:
                        sweep_candle_low = sub_df['low'].iloc[s_idx]
                        closed_below = (sub_df['close'].iloc[s_idx:] < sweep_candle_low).any()
                        if not closed_below:
                            has_reversal_with_sweep = True
                            sweep_reason = f"Sweep low found at {sub_df.index[s_idx] + pd.Timedelta(hours=7)} (low={sweep_candle_low})"
                            break
                if not has_reversal_with_sweep:
                    sweep_reason = "Recent reversal but no sweep low found in lookback or closed below sweep low"
            else:
                sweep_reason = "No recent reversal"
                
            # Squeeze breakout check
            has_recent_squeeze = sub_df['ema_squeeze'].iloc[-5:-1].any()
            if not has_recent_squeeze:
                has_recent_squeeze = (
                    sub_df['dragon_narrow'].iloc[-5:-1].any() and
                    sub_df['ema_spread_pct'].iloc[-5:-1].min() <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2
                )
            bo_ema_center = (ema89 + ema200 + ema610) / 3
            breakout_distance_pct = abs(close - bo_ema_center) / bo_ema_center * 100
            breakout_distance_abs = abs(close - bo_ema_center)
            
            is_breakout_candle = (
                (close > last['dragon_high']) &
                (close > ema89) &
                (close > ema200) &
                (close > open_val) &
                ((close - open_val) > 0.5 * (high - low)) &
                (vol_ratio >= 1.2) &
                (breakout_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5) &
                (breakout_distance_abs <= 2.5 * atr)
            )
            no_trend_violation = not (sub_df['close'].iloc[-12:] < sub_df['ema_200'].iloc[-12:]).any()
            has_squeeze_breakout = has_recent_squeeze and is_breakout_candle and no_trend_violation
            
            bo_reason = []
            if not has_recent_squeeze: bo_reason.append("no recent squeeze")
            if not (close > last['dragon_high']): bo_reason.append("close <= dragon_high")
            if not (close > ema89): bo_reason.append("close <= ema89")
            if not (close > ema200): bo_reason.append("close <= ema200")
            if not (close > open_val): bo_reason.append("close <= open")
            if not ((close - open_val) > 0.5 * (high - low)): bo_reason.append("candle body ratio too small")
            if not (vol_ratio >= 1.2): bo_reason.append(f"volume ratio too low ({vol_ratio:.2f} < 1.2)")
            if not (breakout_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5): bo_reason.append("breakout too far from EMA")
            if not no_trend_violation: bo_reason.append("trend violation")
            
            # Trend checks
            is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
            is_above_dragon = close > last.get('dragon_low', 0)
            
            # Cho phép đánh ngược trend (Bắt đáy/Spring) khi có Stop Hunt kết hợp Squeeze
            if has_reversal_with_sweep and is_squeezed_state:
                is_trending_long = True
            
            trend_fail_reason = ""
            if not has_squeeze_breakout:
                if is_squeezed_state:
                    if (
                        close <= ema34 or
                        close <= ema89 or
                        close <= ema200
                    ):
                        is_trending_long = False
                        trend_fail_reason = f"Squeeze trend filter failed: close={close:.5f}, E34={ema34:.5f}, E89={ema89:.5f}, E200={ema200:.5f}"
                else:
                    if (
                        close <= ema34 or
                        close <= ema89 or
                        close <= ema200 or
                        ema34 <= ema89 or
                        ema89 <= ema200
                    ):
                        is_trending_long = False
                        trend_fail_reason = f"Normal trend filter failed: close={close:.5f}, E34={ema34:.5f}, E89={ema89:.5f}, E200={ema200:.5f}"
                    
            print(f"\n[{ts_vn}] Close={close:.5f} L={low:.5f} H={high:.5f}")
            print(f"  EMA: E34={ema34:.5f} E89={ema89:.5f} E200={ema200:.5f} spread={spread:.2f}% vol={vol_ratio:.2f}")
            print(f"  COND1: {cond1_ok} ({cond1_reason})")
            print(f"  REVERSAL/SWEEP: {has_reversal_with_sweep} ({sweep_reason})")
            print(f"  SQUEEZE BREAKOUT: {has_squeeze_breakout} (Fails: {', '.join(bo_reason)})")
            print(f"  TREND: is_trending_long={is_trending_long} is_above_dragon={is_above_dragon} ({trend_fail_reason})")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
