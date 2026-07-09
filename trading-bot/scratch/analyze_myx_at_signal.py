"""
Phân tích trạng thái EMA tại ĐÚNG thời điểm bot báo MYX LONG (13:40 ngày 8/6/2026 VN time = 06:40 UTC)
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
        # Fetch 800 nến 5m
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        if df.empty:
            print("❌ Không lấy được dữ liệu!")
            return
        
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        # Chuyển sang VN time
        df.index = df.index + pd.Timedelta(hours=7)
        
        # Tìm nến tại 13:40 ngày 8/6 (bot báo lúc 13:41, tức là đang ở nến 13:40)
        target_time = pd.Timestamp('2026-06-08 13:40:00')
        
        # Tìm nến gần nhất
        if target_time in df.index:
            target_idx = df.index.get_loc(target_time)
        else:
            # Tìm nến gần nhất trước target_time
            mask = df.index <= target_time
            if mask.any():
                target_idx = mask.sum() - 1
            else:
                print(f"❌ Không tìm thấy nến tại {target_time}")
                return
        
        # Cắt dataframe đến thời điểm target (simulate trạng thái lúc bot scan)
        df_at_signal = df.iloc[:target_idx + 1]
        last = df_at_signal.iloc[-1]
        
        print("=" * 70)
        print(f"📊 TRẠNG THÁI MYX/USDT TẠI THỜI ĐIỂM BOT BÁO LONG")
        print(f"   Nến: {df_at_signal.index[-1]} (VN Time)")
        print("=" * 70)
        
        print(f"\n🕐 NẾN TẠI THỜI ĐIỂM BÁO:")
        print(f"  Open:  {last['open']:.6f}")
        print(f"  High:  {last['high']:.6f}")
        print(f"  Low:   {last['low']:.6f}")
        print(f"  Close: {last['close']:.6f}")
        print(f"  Volume Ratio: {last.get('volume_ratio', 0):.2f}x")
        
        price = last['close']
        ema34 = last['dragon_close']
        ema89 = last['ema_89']
        ema200 = last['ema_200']
        ema610 = last['ema_610']
        
        print(f"\n📈 TRẠNG THÁI EMA TẠI {df_at_signal.index[-1]}:")
        print(f"  Price:       {price:.6f}")
        print(f"  EMA 34:      {ema34:.6f}")
        print(f"  EMA 89:      {ema89:.6f}")
        print(f"  EMA 200:     {ema200:.6f}")
        print(f"  EMA 610:     {ema610:.6f}")
        
        print(f"\n  ► THỨ TỰ EMA:")
        if price > ema34 > ema89 > ema200 > ema610:
            print(f"    ✅ FULL BULLISH: Price > EMA34 > EMA89 > EMA200 > EMA610")
        elif price > ema34 > ema89 > ema200:
            print(f"    ✅ PARTIAL BULLISH: Price > EMA34 > EMA89 > EMA200")
        elif ema34 > ema89 > ema200:
            print(f"    ⚠️ EMA34 > EMA89 > EMA200 nhưng Price nằm dưới")
        elif ema34 < ema89:
            print(f"    🔴 EMA34 < EMA89 → CHƯA CÓ XU HƯỚNG TĂNG!")
        
        order = sorted(
            [("Price", price), ("EMA34", ema34), ("EMA89", ema89), ("EMA200", ema200), ("EMA610", ema610)],
            key=lambda x: -x[1]
        )
        order_str = " > ".join([f"{name}({val:.6f})" for name, val in order])
        print(f"    Thứ tự: {order_str}")
        
        print(f"\n  ► VỊ TRÍ GIÁ SO VỚI EMA:")
        print(f"    Price vs EMA34: {'TRÊN ✅' if price > ema34 else 'DƯỚI ❌'} ({((price-ema34)/ema34*100):+.3f}%)")
        print(f"    Price vs EMA89: {'TRÊN ✅' if price > ema89 else 'DƯỚI ❌'} ({((price-ema89)/ema89*100):+.3f}%)")
        print(f"    Price vs EMA200: {'TRÊN ✅' if price > ema200 else 'DƯỚI ❌'} ({((price-ema200)/ema200*100):+.3f}%)")
        print(f"    Price vs EMA610: {'TRÊN ✅' if price > ema610 else 'DƯỚI ❌'} ({((price-ema610)/ema610*100):+.3f}%)")
        
        # Squeeze
        print(f"\n🔲 TRẠNG THÁI NÉN:")
        print(f"  EMA Spread: {last.get('ema_spread_pct', 0):.3f}%")
        print(f"  EMA Squeeze: {last.get('ema_squeeze', False)}")
        print(f"  Dragon Narrow: {last.get('dragon_narrow', False)}")
        print(f"  Dragon Direction: {last.get('dragon_direction', 'N/A')}")
        print(f"  Price in Dragon: {last.get('price_in_dragon', False)}")
        print(f"  Price in EMA cluster: {last.get('price_in_ema_cluster', False)}")
        print(f"  Touch EMA89: {last.get('touch_ema89', False)}")
        print(f"  Touch EMA200: {last.get('touch_ema200', False)}")
        
        # Is strong trend
        is_strong_long = ema34 > ema89 and ema89 > ema200
        is_strong_short = ema34 < ema89 and ema89 < ema200
        print(f"\n  Strong Trend LONG (EMA34 > EMA89 > EMA200): {is_strong_long}")
        print(f"  Strong Trend SHORT (EMA34 < EMA89 < EMA200): {is_strong_short}")
        
        # Sweep
        print(f"\n🎣 SWEEP (35 nến trước thời điểm báo):")
        sweep_lookback = 35
        start_idx = max(0, target_idx - sweep_lookback)
        sweep_data = df_at_signal.iloc[start_idx:]
        
        for i in range(len(sweep_data)):
            c = sweep_data.iloc[i]
            if c.get('sweep_low', False):
                print(f"  🔻 Sweep Low: {sweep_data.index[i]} | Low: {c['low']:.6f}")
            if c.get('sweep_high', False):
                print(f"  🔺 Sweep High: {sweep_data.index[i]} | High: {c['high']:.6f}")
        
        # Reversal
        has_bull_rev = df_at_signal['bullish_reversal_at_ema'].iloc[-2:].any()
        print(f"\n🔄 REVERSAL:")
        print(f"  Bullish reversal (2 nến gần nhất): {has_bull_rev}")
        
        # Check reversal with sweep
        has_reversal_with_sweep = False
        if has_bull_rev:
            for idx in range(-1, -sweep_lookback, -1):
                if abs(idx) > len(df_at_signal):
                    break
                if df_at_signal['sweep_low'].iloc[idx]:
                    sweep_candle_low = df_at_signal['low'].iloc[idx]
                    closed_below = (df_at_signal['close'].iloc[idx:] < sweep_candle_low).any()
                    if not closed_below:
                        has_reversal_with_sweep = True
                        print(f"  ✅ Sweep Low hợp lệ tại {df_at_signal.index[idx]}")
                        break
        print(f"  Reversal + Sweep: {has_reversal_with_sweep}")
        
        # Squeeze Breakout
        has_recent_sq = df_at_signal['ema_squeeze'].iloc[-5:-1].any()
        is_bo = (
            last['close'] > last['dragon_high'] and
            last['close'] > last['ema_89'] and
            last['close'] > last['ema_200'] and
            last['close'] > last['open'] and
            (last['close'] - last['open']) > 0.5 * (last['high'] - last['low']) and
            last.get('volume_ratio', 0) >= 1.2
        )
        no_viol = not (df_at_signal['close'].iloc[-12:] < df_at_signal['ema_200'].iloc[-12:]).any()
        squeeze_bo = has_recent_sq and is_bo and no_viol
        print(f"\n🚀 SQUEEZE BREAKOUT:")
        print(f"  Recent squeeze: {has_recent_sq}")
        print(f"  Breakout candle: {is_bo}")
        print(f"    Close > Dragon High ({last['dragon_high']:.6f}): {last['close'] > last['dragon_high']}")
        print(f"    Close > EMA89 ({ema89:.6f}): {last['close'] > ema89}")
        print(f"    Close > EMA200 ({ema200:.6f}): {last['close'] > ema200}")
        print(f"    Bullish (Close > Open): {last['close'] > last['open']}")
        if last['close'] > last['open']:
            body = last['close'] - last['open']
            rng = last['high'] - last['low']
            print(f"    Body/Range: {body:.6f}/{rng:.6f} = {body/rng*100:.1f}% (need > 50%)")
        print(f"    Volume >= 1.2x: {last.get('volume_ratio', 0):.2f}x")
        print(f"  No violation (12 nến): {no_viol}")
        print(f"  → Squeeze Breakout: {squeeze_bo}")
        
        # Final check (simulate bot logic)
        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )
        current_spread = last.get('ema_spread_pct', 100)
        has_squeeze = df_at_signal['ema_squeeze'].iloc[-5:].any()
        has_narrow = df_at_signal['dragon_narrow'].iloc[-5:].any()
        
        cond1 = False
        if has_squeeze and price_near_ema and current_spread <= Config.MAX_EMA_SPREAD_PCT:
            cond1 = True
            print(f"\n✅ ĐK1 PASS: Nén Sonic R ({current_spread:.1f}%)")
        elif has_narrow and price_near_ema and current_spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2:
            cond1 = True
            print(f"\n✅ ĐK1 PASS: Dragon Narrow ({current_spread:.1f}%)")
        elif (is_strong_long or is_strong_short) and price_near_ema:
            cond1 = True
            print(f"\n✅ ĐK1 PASS: Strong Trend + Price near EMA")
        else:
            print(f"\n❌ ĐK1 FAIL:")
            print(f"    has_squeeze: {has_squeeze}, price_near_ema: {price_near_ema}, spread: {current_spread:.2f}%")
            print(f"    has_narrow: {has_narrow}")
            print(f"    is_strong_long: {is_strong_long}, is_strong_short: {is_strong_short}")
        
        # LONG logic
        is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
        is_above_dragon = last['close'] > last.get('dragon_low', 0)
        if ema89 < ema200 and not squeeze_bo:
            is_trending_long = False
        
        long_ok = ((has_reversal_with_sweep and cond1) or squeeze_bo) and is_trending_long and is_above_dragon
        
        print(f"\n{'='*70}")
        print(f"⚡ KẾT LUẬN CUỐI CÙNG TẠI {df_at_signal.index[-1]}:")
        print(f"{'='*70}")
        print(f"  ĐK1 (Nén/Trend): {cond1}")
        print(f"  ĐK2+3 (Reversal+Sweep): {has_reversal_with_sweep}")
        print(f"  ĐK2B (Squeeze Breakout): {squeeze_bo}")
        print(f"  is_trending_long: {is_trending_long}")
        print(f"  is_above_dragon: {is_above_dragon}")
        print(f"  → LONG SATISFIED: {long_ok}")
        
        if not long_ok:
            print(f"\n⚠️ HIỆN TẠI tín hiệu KHÔNG hợp lệ — có thể tại thời điểm 13:40")
            print(f"   nến đang hình thành khác (realtime vs historical)")
            print(f"   Bot quét tín hiệu trên dữ liệu realtime, candle chưa đóng.")
        
        # Xem 10 nến xung quanh thời điểm báo
        print(f"\n{'='*70}")
        print(f"📋 10 NẾN XUNG QUANH THỜI ĐIỂM BÁO ({df_at_signal.index[-1]}):")
        print(f"{'='*70}")
        start = max(0, target_idx - 10)
        for i in range(start, min(target_idx + 5, len(df))):
            c = df.iloc[i]
            marker = " ◄◄◄ BOT BÁO" if i == target_idx else ""
            direction = "🟢" if c['close'] > c['open'] else "🔴"
            ema34_v = c['dragon_close']
            ema89_v = c['ema_89']
            ema200_v = c['ema_200']
            is_above_all = c['close'] > ema34_v and c['close'] > ema89_v and c['close'] > ema200_v
            above_str = "✅ TRÊN 3 EMA" if is_above_all else ""
            below_str = ""
            if c['close'] < ema34_v:
                below_str += " <34"
            if c['close'] < ema89_v:
                below_str += " <89"
            if c['close'] < ema200_v:
                below_str += " <200"
            if below_str:
                below_str = f"❌ DƯỚI{below_str}"
            
            print(f"  {direction} {df.index[i]} | C:{c['close']:.6f} | E34:{ema34_v:.6f} E89:{ema89_v:.6f} E200:{ema200_v:.6f} | {above_str}{below_str}{marker}")
        
        # Kiểm tra kết quả lệnh — giá sau khi bot báo
        print(f"\n{'='*70}")
        print(f"📈 KẾT QUẢ SAU KHI BOT BÁO (nến tiếp theo):")
        print(f"{'='*70}")
        entry_price = last['close']
        print(f"  Entry Price (Close tại 13:40): {entry_price:.6f}")
        
        for i in range(target_idx + 1, min(target_idx + 40, len(df))):
            c = df.iloc[i]
            pnl = (c['close'] - entry_price) / entry_price * 100
            max_pnl = (c['high'] - entry_price) / entry_price * 100
            min_pnl = (c['low'] - entry_price) / entry_price * 100
            direction = "🟢" if pnl > 0 else "🔴"
            print(f"  {direction} {df.index[i]} | C:{c['close']:.6f} | PnL: {pnl:+.2f}% | Max: {max_pnl:+.2f}% | Min: {min_pnl:+.2f}%")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
