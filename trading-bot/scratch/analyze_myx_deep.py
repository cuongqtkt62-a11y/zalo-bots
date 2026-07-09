"""
Phân tích chuyên sâu tại sao bot báo mua MYX/USDT vào lúc 13:41 ngày 8/6/2026.
Script lấy 800 nến 5m từ Binance, tính indicators, và in ra trạng thái chính xác
tại thời điểm bot báo tín hiệu.
"""
import asyncio
import pandas as pd
import numpy as np
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from config import Config

async def main():
    fetcher = MarketDataFetcher()
    symbol = 'MYX/USDT:USDT'
    
    try:
        print("=" * 70)
        print(f"📊 PHÂN TÍCH CHUYÊN SÂU: {symbol}")
        print("=" * 70)
        
        # Fetch 800 nến 5m
        print("\n⏳ Đang lấy dữ liệu 800 nến 5m từ sàn...")
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        if df.empty:
            print("❌ Không lấy được dữ liệu!")
            return
        
        print(f"✅ Đã lấy {len(df)} nến, từ {df.index[0]} đến {df.index[-1]} (UTC)")
        
        # Tính indicators
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        # Chuyển sang VN time để dễ đọc
        df.index = df.index + pd.Timedelta(hours=7)
        
        # ===== TRẠNG THÁI HIỆN TẠI =====
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        print(f"\n{'='*70}")
        print(f"🕐 NẾN HIỆN TẠI: {df.index[-1]} (VN Time)")
        print(f"{'='*70}")
        print(f"  Open:  {last['open']:.6f}")
        print(f"  High:  {last['high']:.6f}")
        print(f"  Low:   {last['low']:.6f}")
        print(f"  Close: {last['close']:.6f}")
        print(f"  Volume: {last['volume']:.2f} | Volume Ratio: {last.get('volume_ratio', 0):.2f}x")
        
        print(f"\n{'='*70}")
        print(f"📈 TRẠNG THÁI SONIC R (EMA)")
        print(f"{'='*70}")
        print(f"  EMA 34 (Dragon Close): {last['dragon_close']:.6f}")
        print(f"  EMA 34 High (Dragon H): {last['dragon_high']:.6f}")
        print(f"  EMA 34 Low  (Dragon L): {last['dragon_low']:.6f}")
        print(f"  EMA 89:                 {last['ema_89']:.6f}")
        print(f"  EMA 200:                {last['ema_200']:.6f}")
        print(f"  EMA 610:                {last['ema_610']:.6f}")
        
        # So sánh thứ tự EMA
        print(f"\n  ► KIỂM TRA THỨ TỰ EMA (Sonic R):")
        ema34 = last['dragon_close']
        ema89 = last['ema_89']
        ema200 = last['ema_200']
        ema610 = last['ema_610']
        price = last['close']
        
        if price > ema34 > ema89 > ema200 > ema610:
            print(f"    ✅ FULL BULLISH: Price > EMA34 > EMA89 > EMA200 > EMA610")
        elif price > ema34 > ema89 > ema200:
            print(f"    ✅ PARTIAL BULLISH: Price > EMA34 > EMA89 > EMA200 (EMA610 chưa xếp)")
        elif ema34 > ema89 > ema200:
            print(f"    ⚠️ EMA34 > EMA89 > EMA200 nhưng Price ({price:.6f}) < EMA34 ({ema34:.6f})")
        elif ema34 < ema89 < ema200:
            print(f"    🔴 BEARISH: EMA34 < EMA89 < EMA200 → ĐÂY LÀ XU HƯỚNG GIẢM!")
        else:
            order = []
            for name, val in [("EMA34", ema34), ("EMA89", ema89), ("EMA200", ema200), ("EMA610", ema610)]:
                order.append((val, name))
            order.sort(reverse=True)
            order_str = " > ".join([f"{name}({val:.6f})" for val, name in order])
            print(f"    ⚠️ TANGLED (rối): {order_str}")
            print(f"    → Price: {price:.6f}")
        
        # Vị trí giá so với EMA
        print(f"\n  ► VỊ TRÍ GIÁ SO VỚI EMA:")
        print(f"    Price vs EMA34: {'TRÊN' if price > ema34 else 'DƯỚI'} ({((price-ema34)/ema34*100):+.3f}%)")
        print(f"    Price vs EMA89: {'TRÊN' if price > ema89 else 'DƯỚI'} ({((price-ema89)/ema89*100):+.3f}%)")
        print(f"    Price vs EMA200: {'TRÊN' if price > ema200 else 'DƯỚI'} ({((price-ema200)/ema200*100):+.3f}%)")
        print(f"    Price vs EMA610: {'TRÊN' if price > ema610 else 'DƯỚI'} ({((price-ema610)/ema610*100):+.3f}%)")
        
        # Squeeze/Compression
        print(f"\n{'='*70}")
        print(f"🔲 TRẠNG THÁI NÉN (SQUEEZE/COMPRESSION)")
        print(f"{'='*70}")
        print(f"  EMA Spread (4 EMA): {last.get('ema_spread_pct', 0):.3f}%")
        print(f"  Dragon Width (EMA34 band): {last.get('dragon_width', 0):.3f}%")
        print(f"  EMA Squeeze: {last.get('ema_squeeze', False)}")
        print(f"  Dragon Narrow: {last.get('dragon_narrow', False)}")
        print(f"  Price in Dragon: {last.get('price_in_dragon', False)}")
        print(f"  Price in EMA cluster: {last.get('price_in_ema_cluster', False)}")
        print(f"  Dragon Direction: {last.get('dragon_direction', 'N/A')}")
        
        # Squeeze trong 5 nến gần nhất
        sq_lb = 5
        recent_squeeze = df['ema_squeeze'].iloc[-sq_lb:].any()
        recent_narrow = df['dragon_narrow'].iloc[-sq_lb:].any()
        print(f"\n  ► NÉN TRONG {sq_lb} NẾN GẦN NHẤT:")
        print(f"    EMA Squeeze (5 nến): {recent_squeeze}")
        print(f"    Dragon Narrow (5 nến): {recent_narrow}")
        
        # Stop Hunt / Sweep
        print(f"\n{'='*70}")
        print(f"🎣 QUÉT THANH KHOẢN (STOP HUNT / SWEEP)")
        print(f"{'='*70}")
        sweep_lookback = 35
        sweep_lows = df['sweep_low'].iloc[-sweep_lookback:]
        sweep_highs = df['sweep_high'].iloc[-sweep_lookback:]
        print(f"  Sweep Low (quét đáy) trong {sweep_lookback} nến: {sweep_lows.sum()} lần")
        print(f"  Sweep High (quét đỉnh) trong {sweep_lookback} nến: {sweep_highs.sum()} lần")
        
        # Chi tiết sweep
        for i in range(-1, -sweep_lookback, -1):
            if abs(i) > len(df):
                break
            if df['sweep_low'].iloc[i]:
                print(f"    🔻 Sweep Low tại nến #{len(df)+i}: {df.index[i]} | Low: {df['low'].iloc[i]:.6f}")
            if df['sweep_high'].iloc[i]:
                print(f"    🔺 Sweep High tại nến #{len(df)+i}: {df.index[i]} | High: {df['high'].iloc[i]:.6f}")
        
        # Reversal
        print(f"\n{'='*70}")
        print(f"🔄 NẾN ĐẢO CHIỀU (REVERSAL)")
        print(f"{'='*70}")
        has_bull_rev = df['bullish_reversal_at_ema'].iloc[-2:].any()
        has_bear_rev = df['bearish_reversal_at_ema'].iloc[-2:].any()
        print(f"  Bullish reversal at EMA (2 nến gần nhất): {has_bull_rev}")
        print(f"  Bearish reversal at EMA (2 nến gần nhất): {has_bear_rev}")
        print(f"  Lower wick ratio (nến cuối): {last.get('lower_wick_ratio', 0):.3f}")
        print(f"  Upper wick ratio (nến cuối): {last.get('upper_wick_ratio', 0):.3f}")
        
        # FVG
        print(f"\n{'='*70}")
        print(f"📊 FAIR VALUE GAP (FVG)")
        print(f"{'='*70}")
        has_fvg_bull = df['fvg_bullish'].iloc[-10:].any()
        has_fvg_bear = df['fvg_bearish'].iloc[-10:].any()
        print(f"  Bullish FVG (10 nến): {has_fvg_bull}")
        print(f"  Bearish FVG (10 nến): {has_fvg_bear}")
        
        # ATR
        atr = last.get('atr', 0)
        atr_pct = atr / last['close'] * 100
        print(f"\n{'='*70}")
        print(f"📐 ATR & KHOẢNG CÁCH")
        print(f"{'='*70}")
        print(f"  ATR: {atr:.6f} ({atr_pct:.3f}%)")
        
        ema_cluster_center = (ema89 + ema200 + ema610) / 3
        price_dist = abs(price - ema_cluster_center) / ema_cluster_center * 100
        print(f"  Khoảng cách giá → cụm EMA(89/200/610): {price_dist:.3f}%")
        print(f"  Cụm EMA center: {ema_cluster_center:.6f}")
        
        # Trending?
        is_strong_trend_long = (last['dragon_close'] > last['ema_89'] and last['ema_89'] > last['ema_200'])
        is_strong_trend_short = (last['dragon_close'] < last['ema_89'] and last['ema_89'] < last['ema_200'])
        print(f"\n  Strong Trend LONG (Dragon > 89 > 200): {is_strong_trend_long}")
        print(f"  Strong Trend SHORT (Dragon < 89 < 200): {is_strong_trend_short}")
        
        # ===== KIỂM TRA TỔNG HỢP =====
        print(f"\n{'='*70}")
        print(f"⚡ KIỂM TRA TỔNG HỢP — TẠI SAO BOT BÁO LONG?")
        print(f"{'='*70}")
        
        # Điều kiện 1: Nén
        print(f"\n  ĐK1 — GIÁ NÉN TẠI CỤM SONIC R:")
        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )
        print(f"    Price near EMA: {price_near_ema}")
        print(f"    EMA Spread <= {Config.MAX_EMA_SPREAD_PCT}%: {last.get('ema_spread_pct', 100)} <= {Config.MAX_EMA_SPREAD_PCT} → {last.get('ema_spread_pct', 100) <= Config.MAX_EMA_SPREAD_PCT}")
        
        # Điều kiện 2: Reversal + Sweep
        print(f"\n  ĐK2 — NẾN ĐẢO CHIỀU + QUÉT THANH KHOẢN:")
        print(f"    Bullish reversal (2 nến): {has_bull_rev}")
        
        # Kiểm tra sweep_low + reversal 
        has_reversal_with_sweep = False
        if has_bull_rev:
            for idx in range(-1, -sweep_lookback, -1):
                if abs(idx) > len(df):
                    break
                if df['sweep_low'].iloc[idx]:
                    sweep_candle_low = df['low'].iloc[idx]
                    closed_below = (df['close'].iloc[idx:] < sweep_candle_low).any()
                    if not closed_below:
                        has_reversal_with_sweep = True
                        print(f"    ✅ Sweep Low tại {df.index[idx]} | Low sweep: {sweep_candle_low:.6f} → Không có nến nào đóng dưới → HỢP LỆ")
                        break
        
        print(f"    Reversal + Sweep hợp lệ: {has_reversal_with_sweep}")
        
        # Squeeze Breakout
        print(f"\n  ĐK2B — SQUEEZE BREAKOUT (thay thế Stop Hunt):")
        has_recent_squeeze_bo = df['ema_squeeze'].iloc[-5:-1].any()
        if not has_recent_squeeze_bo:
            has_recent_squeeze_bo = (
                df['dragon_narrow'].iloc[-5:-1].any() and 
                df['ema_spread_pct'].iloc[-5:-1].min() <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2
            )
        
        bo_ema_center = (df['ema_89'].iloc[-1] + df['ema_200'].iloc[-1] + df['ema_610'].iloc[-1]) / 3
        breakout_dist_pct = abs(df['close'].iloc[-1] - bo_ema_center) / bo_ema_center * 100
        breakout_dist_abs = abs(df['close'].iloc[-1] - bo_ema_center)
        
        is_bo = (
            (df['close'].iloc[-1] > df['dragon_high'].iloc[-1]) and
            (df['close'].iloc[-1] > df['ema_89'].iloc[-1]) and
            (df['close'].iloc[-1] > df['ema_200'].iloc[-1]) and
            (df['close'].iloc[-1] > df['open'].iloc[-1]) and
            ((df['close'].iloc[-1] - df['open'].iloc[-1]) > 0.5 * (df['high'].iloc[-1] - df['low'].iloc[-1])) and
            (df['volume_ratio'].iloc[-1] >= 1.2) and
            (breakout_dist_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5) and
            (breakout_dist_abs <= 2.5 * df['atr'].iloc[-1])
        )
        no_violation = not (df['close'].iloc[-12:] < df['ema_200'].iloc[-12:]).any()
        has_squeeze_bo = has_recent_squeeze_bo and is_bo and no_violation
        
        print(f"    Recent Squeeze (5 nến): {has_recent_squeeze_bo}")
        print(f"    Breakout candle: {is_bo}")
        print(f"      - Close > Dragon High: {df['close'].iloc[-1] > df['dragon_high'].iloc[-1]}")
        print(f"      - Close > EMA89: {df['close'].iloc[-1] > df['ema_89'].iloc[-1]}")
        print(f"      - Close > EMA200: {df['close'].iloc[-1] > df['ema_200'].iloc[-1]}")
        print(f"      - Close > Open (bullish): {df['close'].iloc[-1] > df['open'].iloc[-1]}")
        body = df['close'].iloc[-1] - df['open'].iloc[-1]
        total_range = df['high'].iloc[-1] - df['low'].iloc[-1]
        print(f"      - Body > 50% range: {body:.6f} > {0.5*total_range:.6f} → {body > 0.5 * total_range}")
        print(f"      - Volume ratio >= 1.2: {df['volume_ratio'].iloc[-1]:.2f} → {df['volume_ratio'].iloc[-1] >= 1.2}")
        print(f"      - Breakout dist <= {Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT*1.5:.2f}%: {breakout_dist_pct:.3f}%")
        print(f"    No trend violation (12 nến): {no_violation}")
        print(f"    → Squeeze Breakout: {has_squeeze_bo}")
        
        # Dragon trend
        is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
        is_above_dragon = last['close'] > last.get('dragon_low', 0)
        
        if last['ema_89'] < last['ema_200'] and not has_squeeze_bo:
            print(f"\n  ⚠️ CHẶN LONG: EMA89 ({ema89:.6f}) < EMA200 ({ema200:.6f}) → KHÔNG LONG trừ khi Squeeze Breakout")
            is_trending_long = False
        
        print(f"\n  ► KẾT LUẬN:")
        print(f"    is_trending_long: {is_trending_long}")
        print(f"    is_above_dragon: {is_above_dragon}")
        print(f"    has_reversal_with_sweep: {has_reversal_with_sweep}")
        print(f"    cond1_compression: True (đã qua filter)")
        print(f"    has_squeeze_breakout: {has_squeeze_bo}")
        
        long_ok = ((has_reversal_with_sweep) or has_squeeze_bo) and is_trending_long and is_above_dragon
        print(f"\n    → LONG SATISFIED: {long_ok}")
        
        # In thêm 10 nến gần nhất để anh tham khảo
        print(f"\n{'='*70}")
        print(f"📋 10 NẾN GẦN NHẤT")
        print(f"{'='*70}")
        for i in range(-10, 0):
            c = df.iloc[i]
            direction = "🟢" if c['close'] > c['open'] else "🔴"
            print(f"  {direction} {df.index[i]} | O:{c['open']:.6f} H:{c['high']:.6f} L:{c['low']:.6f} C:{c['close']:.6f} | V:{c.get('volume_ratio',0):.1f}x | Sq:{c.get('ema_squeeze',False)} | SwL:{c.get('sweep_low',False)} | Rev:{c.get('bullish_reversal_at_ema',False)}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
