import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner

async def check_tao():
    symbol = "TAO/USDT:USDT"
    print(f"=== Diagnosing TAO/USDT on 2026-06-21 ===")
    
    scanner = SignalScanner()
    try:
        # Load exchange markets
        await scanner.data_fetcher.exchange.load_markets()
        
        # Fetch OHLCV
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df.empty:
            print("❌ Failed to fetch TAO data.")
            return
            
        print(f"Fetched {len(df)} candles. Last timestamp: {df.index[-1]}")
        
        # Calculate indicators
        df_indicators = scanner.indicators.calculate_all(df)
        
        # Convert index to local timezone (+07:00)
        df_indicators.index = pd.to_datetime(df_indicators.index)
        local_index = df_indicators.index.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh')
        
        found = False
        for i in range(len(df_indicators)):
            time_str = local_index[i].strftime('%Y-%m-%d %H:%M')
            # Look at candles between 09:00 and 10:15 on 2026-06-21
            if "2026-06-21 09:00" <= time_str <= "2026-06-21 10:15":
                found = True
                row = df_indicators.iloc[i]
                sub_df = df_indicators.iloc[:i+1]
                
                # Check confluence setup
                # Let's inspect the bias calculation manually first
                df_h4 = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_CONTEXT, limit=300)
                df_daily = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_DAILY, limit=200)
                df_h4 = scanner.indicators.calculate_all(df_h4)
                df_daily = scanner.indicators.calculate_all(df_daily)
                
                last_h4 = df_h4.iloc[-1]
                last_daily = df_daily.iloc[-1]
                
                calculated_bias = scanner._determine_bias(df_daily, df_h4)
                
                print(f"\n==========================================")
                print(f"VN Time: {time_str} | Close: {row['close']:.2f}")
                print(f"==========================================")
                print(f"H4 details:")
                print(f"  • Close: {last_h4['close']:.2f} | Dragon Close: {last_h4['dragon_close']:.2f} | EMA 89: {last_h4['ema_89']:.2f}")
                print(f"  • partial_bullish_order: {last_h4.get('partial_bullish_order', False)}")
                print(f"  • partial_bearish_order: {last_h4.get('partial_bearish_order', False)}")
                print(f"Daily details:")
                print(f"  • Close: {last_daily['close']:.2f} | Dragon Close: {last_daily['dragon_close']:.2f} | EMA 89: {last_daily['ema_89']:.2f}")
                print(f"  • partial_bullish_order: {last_daily.get('partial_bullish_order', False)}")
                print(f"  • partial_bearish_order: {last_daily.get('partial_bearish_order', False)}")
                
                bias = calculated_bias
                signal = scanner._check_confluence_setup(sub_df, symbol, bias)
                
                # Check daily/4h bias
                print(f"Bias (D1/H4): {bias}")
                
                # Check Cond 1: Compression
                current_spread = row.get('ema_spread_pct', 100)
                has_squeeze = sub_df['ema_squeeze'].iloc[-5:].any()
                has_narrow = sub_df['dragon_narrow'].iloc[-5:].any()
                price_near_ema = (
                    row.get('price_in_ema_cluster', False) or
                    row.get('price_in_dragon', False) or
                    row.get('touch_ema89', False) or
                    row.get('touch_ema200', False)
                )
                ema_cluster_center = (row['ema_89'] + row['ema_200'] + row['ema_610']) / 3
                price_distance_pct = abs(row['close'] - ema_cluster_center) / ema_cluster_center * 100
                price_distance_abs = abs(row['close'] - ema_cluster_center)
                atr = row.get('atr', 0)
                atr_x = price_distance_abs / atr if atr > 0 else 0
                
                is_strong_trend_long = (row['dragon_close'] > row['ema_89']) & (row['ema_89'] > row['ema_200'])
                
                cond1_ok = False
                if (has_squeeze and price_near_ema and current_spread <= Config.MAX_EMA_SPREAD_PCT and price_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT and atr_x <= 2.0):
                    cond1_ok = True
                    cond1_reason = "EMA Squeeze"
                elif (has_narrow and price_near_ema and current_spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2 and price_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT and atr_x <= 2.0):
                    cond1_ok = True
                    cond1_reason = "Dragon Narrow"
                elif (is_strong_trend_long) and price_near_ema:
                    cond1_ok = True
                    cond1_reason = "Strong Trend Pullback"
                else:
                    cond1_reason = "Failed"
                    
                print(f"Cond 1 (Sonic R Compression): {cond1_ok} ({cond1_reason})")
                print(f"  • EMA Spread: {current_spread:.2f}% (Threshold: {Config.EMA_SQUEEZE_THRESHOLD_PCT}%)")
                print(f"  • Dragon Narrow: {has_narrow} (Width: {row.get('dragon_width_pct', 0):.2f}%)")
                print(f"  • Price Near EMA: {price_near_ema}")
                print(f"  • Price Distance to EMAs: {price_distance_pct:.2f}% (Max: {Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT}%)")
                print(f"  • Distance / ATR: {atr_x:.2f}x (Max: 2.0x)")
                print(f"  • Strong Trend (34>89>200): {is_strong_trend_long}")
                
                # Check Cond 2: Reversal at EMA
                has_reversal = sub_df['bullish_reversal_at_ema'].iloc[-3:].any()
                print(f"Cond 2 (Bullish Reversal in 3c): {has_reversal}")
                print(f"  • Current candle is_spring: {row.get('is_spring', False)} | is_hammer: {row.get('is_hammer', False)} | is_bull_engulfing: {row.get('is_bull_engulfing', False)}")
                print(f"  • Current price_in_dragon: {row.get('price_in_dragon', False)} | touch_ema89: {row.get('touch_ema89', False)} | touch_ema200: {row.get('touch_ema200', False)}")
                
                # Check Cond 3: Stop Hunt
                has_sweep = sub_df['sweep_low'].iloc[-45:].any()
                print(f"Cond 3 (Stop Hunt / Sweep Low in 45c): {has_sweep}")
                # Print last 5 candles stop hunt status
                recent_sweep = sub_df['sweep_low'].iloc[-5:]
                print(f"  • Sweep Low status in last 5 candles: {recent_sweep.to_dict()}")
                
                # Check Dragon close relation
                is_above_dragon = row['close'] > row.get('dragon_close', 0)
                is_trending_long = row.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
                
                # Print dragon close relation details
                print(f"Dragon Close Check: is_above_dragon={is_above_dragon} | Close: {row['close']:.2f} vs Dragon Close: {row.get('dragon_close', 0):.2f}")
                print(f"Dragon Direction: {row.get('dragon_direction', 'FLAT')}")
                
                # FVG details
                has_fvg = sub_df['fvg_bullish'].iloc[-10:].any()
                print(f"Cond 4 (Bullish FVG in 10c): {has_fvg}")
                
                # Final signal output
                if signal:
                    print(f"👉 RESULT: MATCHED! Setup: {signal.setup_type} | Score: {signal.confluence_score} | Grade: {signal.grade}")
                else:
                    print(f"👉 RESULT: REJECTED")
                    
        if not found:
            print("❌ Target time range not found in data.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check_tao())
