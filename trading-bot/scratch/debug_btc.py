import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner
from config import Config

async def analyze_btc():
    fetcher = MarketDataFetcher()
    indicators = TechnicalIndicators()
    scanner = SignalScanner()
    symbol = "BTC/USDT:USDT"
    
    print(f"Fetching live data for {symbol}...")
    try:
        df_5m = await fetcher.fetch_ohlcv(symbol, "5m", limit=800)
        df_1h = await fetcher.fetch_ohlcv(symbol, "1h", limit=300)
        df_4h = await fetcher.fetch_ohlcv(symbol, "4h", limit=300)
        df_1d = await fetcher.fetch_ohlcv(symbol, "1d", limit=150)
    except Exception as e:
        print(f"Error fetching data: {e}")
        await fetcher.close()
        return
        
    if df_5m.empty or df_4h.empty or df_1d.empty:
        print("Failed to load some timeframes.")
        await fetcher.close()
        return
        
    # Calculate indicators
    df_5m = indicators.calculate_all(df_5m)
    df_1h = indicators.calculate_all(df_1h)
    df_4h = indicators.calculate_all(df_4h)
    df_1d = indicators.calculate_all(df_1d)
    
    last_5m = df_5m.iloc[-1]
    last_1h = df_1h.iloc[-1]
    last_4h = df_4h.iloc[-1]
    last_1d = df_1d.iloc[-1]
    
    # 1. Determine Bias (D1/H4)
    bias = scanner._determine_bias(df_1d, df_4h)
    
    print("\n" + "="*50)
    print("📈 BTC/USDT MULTI-TIMEFRAME ANALYSIS")
    print("="*50)
    
    # 2. Daily Analysis
    print(f"\n📅 Daily Frame (D1):")
    print(f"  - Price: ${last_1d['close']:.2f}")
    print(f"  - EMAs: Dragon: ${last_1d['dragon_close']:.2f} | EMA89: ${last_1d['ema_89']:.2f} | EMA200: ${last_1d['ema_200']:.2f}")
    d1_order = "BULLISH" if last_1d['partial_bullish_order'] else "BEARISH" if last_1d['partial_bearish_order'] else "NEUTRAL"
    print(f"  - EMA Trend: {d1_order}")
    print(f"  - RSI: {last_1d['rsi']:.1f}")
    
    # 3. 4H Analysis
    print(f"\n⏳ 4H Frame (Context):")
    print(f"  - Price: ${last_4h['close']:.2f}")
    print(f"  - EMAs: Dragon: ${last_4h['dragon_close']:.2f} | EMA89: ${last_4h['ema_89']:.2f} | EMA200: ${last_4h['ema_200']:.2f} | EMA610: ${last_4h['ema_610']:.2f}")
    h4_order = "BULLISH" if last_4h['partial_bullish_order'] else "BEARISH" if last_4h['partial_bearish_order'] else "NEUTRAL"
    print(f"  - EMA Trend: {h4_order}")
    print(f"  - RSI: {last_4h['rsi']:.1f}")
    print(f"  - Overall Context Bias: {bias}")
    
    # 4. 1H Analysis
    print(f"\n⏰ 1H Frame (Intermediate):")
    print(f"  - Price: ${last_1h['close']:.2f}")
    print(f"  - EMAs: Dragon: ${last_1h['dragon_close']:.2f} | EMA89: ${last_1h['ema_89']:.2f} | EMA200: ${last_1h['ema_200']:.2f}")
    h1_order = "BULLISH" if last_1h['partial_bullish_order'] else "BEARISH" if last_1h['partial_bearish_order'] else "NEUTRAL"
    print(f"  - EMA Trend: {h1_order}")
    print(f"  - RSI: {last_1h['rsi']:.1f}")
    
    # 5. 5m Analysis (Entry)
    print(f"\n⚡ 5m Frame (Entry Scanner):")
    print(f"  - Price: ${last_5m['close']:.2f}")
    print(f"  - EMAs: Dragon: ${last_5m['dragon_close']:.2f} | EMA89: ${last_5m['ema_89']:.2f} | EMA200: ${last_5m['ema_200']:.2f} | EMA610: ${last_5m['ema_610']:.2f}")
    
    # Squeeze & narrow status
    print(f"  - 4-EMA Spread: {last_5m['ema_spread_pct']:.2f}% (Squeeze Threshold < {Config.EMA_SQUEEZE_THRESHOLD_PCT}%)")
    print(f"  - Squeeze Status: Squeeze={last_5m['ema_squeeze']} | Dragon Narrow={last_5m['dragon_narrow']}")
    
    # Price distance from EMA cluster center
    ema_center = (last_5m['ema_89'] + last_5m['ema_200'] + last_5m['ema_610']) / 3
    dist_pct = abs(last_5m['close'] - ema_center) / ema_center * 100
    atr = last_5m['atr']
    dist_atr = abs(last_5m['close'] - ema_center) / atr if atr > 0 else 0
    print(f"  - Distance from Price to EMA Cluster: {dist_pct:.2f}% (Threshold: {Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT}%) | {dist_atr:.1f}x ATR (Threshold: 2.0x)")
    print(f"  - Price in EMA Cluster: {last_5m['price_in_ema_cluster']} | Near Dragon: {last_5m['price_in_dragon']}")
    
    # Sweep & rejection check on recent 15 candles
    print(f"\n🔍 Recent 5m Indicators (Last 15 candles):")
    for i in range(-15, 0):
        t = df_5m.index[i]
        local_t = t + pd.Timedelta(hours=7)
        row = df_5m.iloc[i]
        if row['sweep_low'] or row['sweep_high'] or row['bullish_reversal_at_ema'] or row['bearish_reversal_at_ema'] or row['fvg_bullish'] or row['fvg_bearish']:
            events = []
            if row['sweep_low']: events.append(f"Spring/Sweep Low (at ${row['sweep_low_level']:.2f})")
            if row['sweep_high']: events.append(f"Upthrust/Sweep High (at ${row['sweep_high_level']:.2f})")
            if row['bullish_reversal_at_ema']: events.append("Bullish Reversal at EMA")
            if row['bearish_reversal_at_ema']: events.append("Bearish Reversal at EMA")
            if row['fvg_bullish']: events.append("Bullish FVG")
            if row['fvg_bearish']: events.append("Bearish FVG")
            print(f"  - {local_t.strftime('%H:%M')} -> {', '.join(events)} | Close: ${row['close']:.2f}")

    # 6. Simulate scan_symbol
    signal = await scanner.scan_symbol(symbol)
    print(f"\n🎯 BOT SCANNER VERDICT:")
    if signal:
        print(f"  - RESULT: SIGNAL DETECTED! ({signal.grade} {signal.direction})")
        print(f"  - Setup: {signal.setup_type} | Confluence Score: {signal.confluence_score}/100")
        print(f"  - Entry: ${signal.entry_price:.2f} | SL: ${signal.stop_loss:.2f} | TP1: ${signal.tp1:.2f} | TP2: ${signal.tp2:.2f}")
        print(f"  - Trigger Reasons:\n{signal.trigger_detail}")
    else:
        print("  - RESULT: NO ACTIVE SIGNAL FOUND")
        # Find why it failed
        reasons = []
        if atr / last_5m['close'] * 100 < Config.MIN_ATR_PCT:
            reasons.append(f"ATR too low ({atr / last_5m['close'] * 100:.3f}% < {Config.MIN_ATR_PCT}%)")
        if dist_pct > Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT:
            reasons.append(f"Price is too far from EMA Cluster ({dist_pct:.2f}% > {Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT}%) -> Late Entry warning")
        if dist_atr > 2.0:
            reasons.append(f"Price distance is > 2.0x ATR ({dist_atr:.1f}x)")
        
        # Squeeze criteria
        sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES
        has_squeeze = df_5m['ema_squeeze'].iloc[-sq_lb:].any()
        has_narrow = df_5m['dragon_narrow'].iloc[-sq_lb:].any()
        if not (has_squeeze or has_narrow):
            reasons.append(f"No EMA squeeze or narrow dragon band in last {sq_lb} candles")
            
        if not reasons:
            reasons.append("Market did not form any valid swing liquidity sweep or rejection candle near the EMA support zone.")
            
        print(f"  - Reasons for no signal:\n      * " + "\n      * ".join(reasons))
        
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(analyze_btc())
