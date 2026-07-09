import asyncio
import pandas as pd
import numpy as np
from signal_scanner import SignalScanner
from config import Config

async def check_xau_process():
    scanner = SignalScanner()
    symbol = "XAU/USDT:USDT" # CCXT Futures
    
    print("==================================================")
    print("🔍 KIỂM TRA TÍN HIỆU XAU/USDT THEO QUY TRÌNH HỢP NHẤT")
    print("==================================================")
    
    try:
        # Load exchange markets
        await scanner.data_fetcher.exchange.load_markets()
        
        # 1. Fetch Entry (5m) data - 800 candles for EMA 610 warmup
        print("📥 Đang lấy dữ liệu 5m (800 nến)...")
        df_entry = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df_entry.empty:
            print("❌ Không lấy được dữ liệu 5m!")
            return
            
        # Calculate indicators
        df_entry = scanner.indicators.calculate_all(df_entry)
        last = df_entry.iloc[-1]
        
        # 2. Get Bias D1/H4
        print("📥 Đang kiểm tra xu hướng lớn (Bias D1/H4)...")
        bias = await scanner._get_cached_bias(symbol)
        print(f"   • Hướng giao dịch cấu hình: {Config.TRADE_DIRECTION}")
        print(f"   • Xu hướng lớn (Bias D1/H4): {bias}")
        
        # 3. Check Confluence Conditions
        print("\n⚙️ BẮT ĐẦU KIỂM TRA 4 ĐIỀU KIỆN HỢP LƯU:")
        print("-" * 50)
        
        # --- ĐIỀU KIỆN 1: GIÁ NÉN TẠI CỤM SONIC R ---
        sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES  # 5 candles
        has_squeeze = df_entry['ema_squeeze'].iloc[-sq_lb:].any()
        has_narrow = df_entry['dragon_narrow'].iloc[-sq_lb:].any()
        current_spread = last.get('ema_spread_pct', 100)
        
        ema_cluster_center = (last['ema_89'] + last['ema_200'] + last['ema_610']) / 3
        price_distance_pct = abs(last['close'] - ema_cluster_center) / ema_cluster_center * 100
        price_distance_abs = abs(last['close'] - ema_cluster_center)
        atr = last.get('atr', 0)
        atr_x = price_distance_abs / atr if atr > 0 else 0
        
        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )
        
        cond1_ok = False
        print("1️⃣ ĐIỀU KIỆN 1: GIÁ NÉN TẠI CỤM SONIC R (BẮT BUỘC)")
        print(f"   • EMA Spread: {current_spread:.2f}% (Ngưỡng Squeeze: <{Config.EMA_SQUEEZE_THRESHOLD_PCT}%, Max: <{Config.MAX_EMA_SPREAD_PCT}%)")
        print(f"   • Dragon Narrow: {has_narrow} (Width: {last.get('dragon_width', 0):.3f}%)")
        print(f"   • Squeeze (last 5 nến): {has_squeeze}")
        print(f"   • Price near EMA cluster: {price_near_ema}")
        print(f"   • Giá hiện tại: {last['close']:,.2f} | Tâm cụm EMA: {ema_cluster_center:,.2f}")
        print(f"   • Khoảng cách giá đến EMA: {price_distance_pct:.2f}% (Max: <{Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT}%) | Khoảng cách/ATR: {atr_x:.2f}x (Max: <2.0x)")
        
        if (has_squeeze and price_near_ema and current_spread <= Config.MAX_EMA_SPREAD_PCT and price_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT and atr_x <= 2.0):
            cond1_ok = True
            print("   👉 ĐIỀU KIỆN 1: ĐẠT ĐIỀU KIỆN (EMA Squeeze)")
        elif (has_narrow and price_near_ema and current_spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2 and price_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT and atr_x <= 2.0):
            cond1_ok = True
            print("   👉 ĐIỀU KIỆN 1: ĐẠT ĐIỀU KIỆN (Dragon Narrow & Spread vừa phải)")
        else:
            print("   👉 ĐIỀU KIỆN 1: KHÔNG ĐẠT")
            
        print("-" * 50)
        
        # --- ĐIỀU KIỆN 2 & 3: RÚT CHÂN / ĐẢO CHIỀU & QUÉT THANH KHOẢN (SPRING / UPTHRUST) ---
        print("2️⃣ & 3️⃣ ĐIỀU KIỆN 2 & 3: RÚT CHÂN & QUÉT THANH KHOẢN (BẮT BUỘC)")
        
        # Long criteria
        reversal_with_sweep_long = df_entry['bullish_reversal_at_ema'] & df_entry['sweep_low']
        has_sweep_long = reversal_with_sweep_long.iloc[-3:].any()
        
        # Squeeze breakout check
        has_recent_squeeze = df_entry['ema_squeeze'].iloc[-5:-1].any() or (
            df_entry['dragon_narrow'].iloc[-5:-1].any() and
            df_entry['ema_spread_pct'].iloc[-5:-1].min() <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2
        )
        is_breakout_long = (
            (df_entry['close'].iloc[-1] > df_entry['dragon_high'].iloc[-1]) &
            (df_entry['close'].iloc[-1] > df_entry['ema_89'].iloc[-1]) &
            (df_entry['close'].iloc[-1] > df_entry['ema_200'].iloc[-1]) &
            (df_entry['close'].iloc[-1] > df_entry['open'].iloc[-1]) &
            ((df_entry['close'].iloc[-1] - df_entry['open'].iloc[-1]) > 0.5 * (df_entry['high'].iloc[-1] - df_entry['low'].iloc[-1])) &
            (df_entry['volume_ratio'].iloc[-1] >= 1.2) &
            (price_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5) &
            (price_distance_abs <= 2.5 * atr)
        )
        no_violation_long = not (df_entry['close'].iloc[-12:] < df_entry['ema_200'].iloc[-12:]).any()
        has_breakout_long = has_recent_squeeze and is_breakout_long and no_violation_long
        
        is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT') and (last['ema_89'] >= last['ema_200'] or has_breakout_long)
        is_above_dragon = last['close'] > last.get('dragon_low', 0)
        
        # Short criteria
        reversal_with_sweep_short = df_entry['bearish_reversal_at_ema'] & df_entry['sweep_high']
        has_sweep_short = reversal_with_sweep_short.iloc[-3:].any()
        
        is_breakout_short = (
            (df_entry['close'].iloc[-1] < df_entry['dragon_low'].iloc[-1]) &
            (df_entry['close'].iloc[-1] < df_entry['ema_89'].iloc[-1]) &
            (df_entry['close'].iloc[-1] < df_entry['ema_200'].iloc[-1]) &
            (df_entry['close'].iloc[-1] < df_entry['open'].iloc[-1]) &
            ((df_entry['open'].iloc[-1] - df_entry['close'].iloc[-1]) > 0.5 * (df_entry['high'].iloc[-1] - df_entry['low'].iloc[-1])) &
            (df_entry['volume_ratio'].iloc[-1] >= 1.2) &
            (price_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5) &
            (price_distance_abs <= 2.5 * atr)
        )
        no_violation_short = not (df_entry['close'].iloc[-12:] > df_entry['ema_200'].iloc[-12:]).any()
        has_breakout_short = has_recent_squeeze and is_breakout_short and no_violation_short
        
        is_trending_short = last.get('dragon_direction', 'FLAT') in ('DOWN', 'FLAT') and (last['ema_89'] <= last['ema_200'] or has_breakout_short)
        is_below_dragon = last['close'] < last.get('dragon_high', 0)
        
        print("   🟢 QUÉT LONG:")
        print(f"     • Reversal + Sweep Low (Spring at EMA) (last 3 nến): {has_sweep_long}")
        print(f"     • Squeeze Breakout Long: {has_breakout_long}")
        print(f"     • Dragon trend long ok (UP/FLAT & no 89<200): {is_trending_long} (EMA89: {last['ema_89']:.2f}, EMA200: {last['ema_200']:.2f})")
        print(f"     • Price above dragon low: {is_above_dragon}")
        
        print("   🔴 QUÉT SHORT:")
        print(f"     • Reversal + Sweep High (Upthrust at EMA) (last 3 nến): {has_sweep_short}")
        print(f"     • Squeeze Breakout Short: {has_breakout_short}")
        print(f"     • Dragon trend short ok (DOWN/FLAT & no 89>200): {is_trending_short} (EMA89: {last['ema_89']:.2f}, EMA200: {last['ema_200']:.2f})")
        print(f"     • Price below dragon high: {is_below_dragon}")
        
        long_ok = (has_sweep_long and cond1_ok or has_breakout_long) and is_trending_long and is_above_dragon
        short_ok = (has_sweep_short and cond1_ok or has_breakout_short) and is_trending_short and is_below_dragon
        
        print(f"   👉 KẾT QUẢ LONG: {'ĐẠT ✅' if long_ok else 'KHÔNG ĐẠT ❌'}")
        print(f"   👉 KẾT QUẢ SHORT: {'ĐẠT ✅' if short_ok else 'KHÔNG ĐẠT ❌'}")
        
        print("-" * 50)
        
        # --- ĐIỀU KIỆN 4: FAIR VALUE GAP ---
        print("4️⃣ ĐIỀU KIỆN 4: FAIR VALUE GAP (FVG - BONUS)")
        has_fvg_bull = df_entry['fvg_bullish'].iloc[-10:].any()
        has_fvg_bear = df_entry['fvg_bearish'].iloc[-10:].any()
        print(f"   • Bullish FVG (last 10 nến): {has_fvg_bull}")
        print(f"   • Bearish FVG (last 10 nến): {has_fvg_bear}")
        
        print("-" * 50)
        
        # 4. Final scan using SignalScanner
        print("🎯 KIỂM TRA KẾT QUẢ CUỐI CÙNG QUA SCANNER:")
        signal = await scanner.scan_symbol(symbol)
        if signal:
            print(f"✅ TÌM THẤY TÍN HIỆU GIAO DỊCH!")
            print(f"   • Hướng: {signal.direction}")
            print(f"   • Loại Setup: {signal.setup_type}")
            print(f"   • Grade: {signal.grade} | Score: {signal.confluence_score}/100")
            print(f"   • Entry: {signal.entry_price:,.2f}")
            print(f"   • Stop Loss: {signal.stop_loss:,.2f}")
            print(f"   • Take Profit: TP1={signal.tp1:,.2f} | TP2={signal.tp2:,.2f} | TP3={signal.tp3:,.2f}")
            print(f"   • R:R: 1:{signal.risk_reward:.1f}")
            print(f"   • Chi tiết trigger:\n{signal.trigger_detail}")
        else:
            print("❌ KHÔNG CÓ TÍN HIỆU GIAO DỊCH HỢP LỆ (Không đủ điểm hoặc không thỏa mãn hard-filters).")
            
    except Exception as e:
        print(f"❌ Lỗi quy trình check: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(check_xau_process())
