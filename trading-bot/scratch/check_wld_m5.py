import asyncio
import pandas as pd
from config import Config
from signal_scanner import SignalScanner

async def check():
    scanner = SignalScanner()
    symbol = "WLD/USDT"
    print("--- DEBUGGING WLD M5 SIGNAL CONDITIONS ---")
    try:
        # Load markets
        await scanner.data_fetcher.exchange.load_markets()
        
        # 1. Fetch bias
        df_daily = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_DAILY, limit=200)
        df_h4 = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_CONTEXT, limit=300)
        
        df_daily = scanner.indicators.calculate_all(df_daily)
        df_h4 = scanner.indicators.calculate_all(df_h4)
        
        bias = scanner._determine_bias(df_daily, df_h4)
        print(f"Daily Bias: {bias}")
        
        # 2. Entry timeframe (5m) data
        df_entry = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        df_entry = scanner.indicators.calculate_all(df_entry)
        last = df_entry.iloc[-1]
        
        print("\n--- 5M ENTRY TIMEFRAME STATUS ---")
        print(f"Close Price: {last['close']:.4f}")
        print(f"EMA Spread %: {last.get('ema_spread_pct', 0):.4f}% (Squeeze Threshold: {Config.EMA_SQUEEZE_THRESHOLD_PCT}%)")
        print(f"Dragon Width %: {last.get('dragon_width', 0):.4f}% (Narrow Threshold: {Config.DRAGON_NARROW_THRESHOLD_PCT}%)")
        
        ema_cols = ['dragon_close', 'ema_89', 'ema_200', 'ema_610']
        ema_cluster_center = (last['ema_89'] + last['ema_200'] + last['ema_610']) / 3
        price_distance_pct = abs(last['close'] - ema_cluster_center) / ema_cluster_center * 100
        price_distance_abs = abs(last['close'] - ema_cluster_center)
        print(f"Price Distance from EMA Center: {price_distance_pct:.4f}% (Max Allowed: {Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT}%)")
        print(f"Price Distance Abs: {price_distance_abs:.4f} | 2.0 * ATR: {2.0 * last.get('atr', 0):.4f}")
        
        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )
        print(f"Price near EMA: {price_near_ema}")
        
        sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES
        has_squeeze = df_entry['ema_squeeze'].iloc[-sq_lb:].any()
        has_narrow = df_entry['dragon_narrow'].iloc[-sq_lb:].any()
        print(f"Has Squeeze in last {sq_lb} candles: {has_squeeze}")
        print(f"Has Narrow in last {sq_lb} candles: {has_narrow}")
        
        # Check Long Conditions
        reversal_with_sweep_long = df_entry['bullish_reversal_at_ema'] & df_entry['sweep_low']
        has_reversal_with_sweep_long = reversal_with_sweep_long.iloc[-3:].any()
        print(f"Has Bull Reversal + Sweep Low in last 3 candles: {has_reversal_with_sweep_long}")
        
        # Check Squeeze Breakout (Long)
        has_recent_squeeze_5 = df_entry['ema_squeeze'].iloc[-5:-1].any() or (
            df_entry['dragon_narrow'].iloc[-5:-1].any() and
            df_entry['ema_spread_pct'].iloc[-5:-1].min() <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2
        )
        is_breakout_candle_long = (
            (df_entry['close'].iloc[-1] > df_entry['dragon_high'].iloc[-1]) &
            (df_entry['close'].iloc[-1] > df_entry['ema_89'].iloc[-1]) &
            (df_entry['close'].iloc[-1] > df_entry['ema_200'].iloc[-1]) &
            (df_entry['close'].iloc[-1] > df_entry['open'].iloc[-1]) &
            ((df_entry['close'].iloc[-1] - df_entry['open'].iloc[-1]) > 0.5 * (df_entry['high'].iloc[-1] - df_entry['low'].iloc[-1])) &
            (df_entry['volume_ratio'].iloc[-1] >= 1.2) &
            (price_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5) &
            (price_distance_abs <= 2.5 * df_entry['atr'].iloc[-1])
        )
        print(f"Has Squeeze Breakout (Long): {has_recent_squeeze_5 and is_breakout_candle_long}")
        
        # Check for Sweep Lows in last 20 candles
        recent_sweeps = df_entry['sweep_low'].iloc[-20:]
        print(f"Number of Sweep Lows in last 20 candles: {recent_sweeps.sum()}")
        if recent_sweeps.sum() > 0:
            print(f"Sweep low indexes: {df_entry[df_entry['sweep_low'] == True].index[-3:]}")
        
        # Check for Reversals at EMA
        recent_reversals = df_entry['bullish_reversal_at_ema'].iloc[-10:]
        print(f"Number of Bullish Reversals at EMA in last 10 candles: {recent_reversals.sum()}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check())
