import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from config import Config
from signal_scanner import SignalScanner
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
COINS = ["ZEN/USDT:USDT", "SUI/USDT:USDT", "JASMY/USDT:USDT", "PEOPLE/USDT:USDT"]

async def analyze_coins():
    print("=" * 80)
    print("🔍 ĐANG PHÂN TÍCH CHI TIẾT 3 TOKEN CANDIDATES THEO HỆ THỐNG GIAO DỊCH H5")
    print(f"📅 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    scanner = SignalScanner()
    fetcher = MarketDataFetcher()
    
    try:
        # Load markets
        await fetcher.exchange.load_markets()
        
        for symbol in COINS:
            print(f"\n────────────────────────────────────────────────────────────")
            print(f"💎 TOKEN: {symbol.split('/')[0]}")
            print(f"────────────────────────────────────────────────────────────")
            
            # 1. Fetch Market Ticker (Current Price)
            ticker = await fetcher.fetch_ticker(symbol)
            price = ticker.get('last', 0)
            change_24h = ticker.get('change_24h', 0)
            print(f"💵 Giá hiện tại: ${price:.6f} | Thay đổi 24h: {change_24h:+.2f}%")
            
            # 2. Fetch Funding Rate & Open Interest (OI)
            funding = await fetcher.fetch_funding_rate(symbol)
            oi = await fetcher.fetch_open_interest(symbol)
            fr = funding.get('funding_rate', 0) * 100
            print(f"📊 Funding Rate: {fr:.4f}% | Open Interest (OI): {oi:,.2f} token (~${oi * price:,.2f})")
            
            # 3. Daily and H4 Trend Analysis
            df_daily = await fetcher.fetch_ohlcv(symbol, '1d', limit=50)
            df_h4 = await fetcher.fetch_ohlcv(symbol, '4h', limit=100)
            
            if not df_daily.empty:
                df_daily = TechnicalIndicators.calculate_all(df_daily)
                last_d1 = df_daily.iloc[-1]
                rsi_d1 = last_d1.get('rsi', 0)
                d1_trend = "BULLISH" if last_d1.get('partial_bullish_order', False) else "BEARISH" if last_d1.get('partial_bearish_order', False) else "NEUTRAL"
                print(f"📅 Khung Daily (D1): Trend = {d1_trend} | RSI = {rsi_d1:.1f}")
            
            if not df_h4.empty:
                df_h4 = TechnicalIndicators.calculate_all(df_h4)
                last_h4 = df_h4.iloc[-1]
                rsi_h4 = last_h4.get('rsi', 0)
                h4_trend = "BULLISH" if last_h4.get('partial_bullish_order', False) else "BEARISH" if last_h4.get('partial_bearish_order', False) else "NEUTRAL"
                print(f"⏳ Khung H4: Trend = {h4_trend} | RSI = {rsi_h4:.1f} | Volume Ratio = {last_h4.get('volume_ratio', 0):.2f}x")
            
            # 4. H5 (5m) Detail Trigger Check
            df_5m = await fetcher.fetch_ohlcv(symbol, '5m', limit=300)
            if df_5m.empty:
                print("❌ Không lấy được dữ liệu H5 (5m)")
                continue
                
            df_5m = TechnicalIndicators.calculate_all(df_5m)
            last_5m = df_5m.iloc[-1]
            
            # Indicators on 5m
            rsi_5m = last_5m.get('rsi', 0)
            atr_5m = last_5m.get('atr', 0)
            ema34_close = last_5m.get('dragon_close', 0)
            ema89 = last_5m.get('ema_89', 0)
            ema200 = last_5m.get('ema_200', 0)
            
            # Check conditions for Long (since these are our chosen winner picks)
            # Cond 1: Compression
            has_squeeze_5m = df_5m['ema_squeeze'].iloc[-15:].any()
            has_narrow_5m = df_5m['dragon_narrow'].iloc[-15:].any()
            price_near_ema_5m = (
                last_5m.get('price_in_ema_cluster', False) or
                last_5m.get('price_in_dragon', False) or
                last_5m.get('touch_ema89', False) or
                last_5m.get('touch_ema200', False)
            )
            cond1_comp = (has_squeeze_5m or has_narrow_5m) and price_near_ema_5m
            
            # Cond 2: Reversal candle in last 5 candles
            has_bull_reversal_5m = df_5m['bullish_reversal_at_ema'].iloc[-5:].any()
            # Find the specific candle index
            reversal_candle = None
            for idx in range(-1, -6, -1):
                if df_5m['bullish_reversal_at_ema'].iloc[idx]:
                    reversal_candle = df_5m.iloc[idx]
                    break
                    
            # Cond 3: Sweep low in last 20 candles
            has_sweep_low_5m = df_5m['sweep_low'].iloc[-20:].any()
            sweep_level = np.nan
            if has_sweep_low_5m:
                sweep_candles = df_5m.iloc[-20:]
                sweep_idx = sweep_candles[sweep_candles['sweep_low'] == True].index
                if len(sweep_idx) > 0:
                    sweep_level = df_5m.loc[sweep_idx, 'sweep_low_level'].iloc[-1]
            
            # Cond 4: FVG in last 10 candles
            has_fvg_5m = df_5m['fvg_bullish'].iloc[-10:].any()
            
            print(f"⚡ H5 (5m) Indicators & Checklist:")
            print(f"   • RSI 5m: {rsi_5m:.1f} | ATR 5m: {atr_5m:.6f}")
            print(f"   • Sonic R EMAs: EMA34={ema34_close:.6f} | EMA89={ema89:.6f} | EMA200={ema200:.6f}")
            print(f"   • [Cond 1] Nén Sonic R (4 EMA Spread/Dragon Narrow): {'✅ THỎA MÃN' if cond1_comp else '❌ CHƯA NÉN CHẶT'}")
            print(f"     (Ema spread: {last_5m.get('ema_spread_pct', 0):.2f}% | Dragon width: {last_5m.get('dragon_width', 0):.2f}%)")
            print(f"   • [Cond 2] Nến đảo chiều LONG tại EMA: {'✅ THỎA MÃN' if has_bull_reversal_5m else '⏳ CHỜ TÍN HIỆU'}")
            if reversal_candle is not None:
                print(f"     (Nến rút chân: Râu dưới={reversal_candle['lower_wick_ratio']*100:.0f}%, Vol ratio={reversal_candle['volume_ratio']:.2f}x)")
            print(f"   • [Cond 3] Quét thanh khoản đáy (Spring/Stop Hunt): {'✅ THỎA MÃN' if has_sweep_low_5m else '❌ CHƯA CÓ STOP HUNT'}")
            if not np.isnan(sweep_level):
                print(f"     (Mức giá bị quét: ${sweep_level:.6f})")
            print(f"   • [Cond 4] Fair Value Gap (FVG) Bullish: {'🔥 CÓ FVG (Điểm cộng)' if has_fvg_5m else '❌ Không có FVG'}")
            
            # 5. Calculate Exact Orders
            print(f"\n📝 ĐỀ XUẤT LỆNH CHI TIẾT (Vốn $20, rủi ro tối đa 2% = $0.40):")
            
            # Determine Stop Loss:
            # Below the sweep low or lowest low of last 20 candles - atr * 0.2
            recent_lows = df_5m['low'].iloc[-20:].min()
            sl_level = recent_lows - atr_5m * 0.5
            # Ensure SL is below EMA200
            if sl_level > ema200 * 0.998:
                sl_level = min(sl_level, ema200 * 0.998)
                
            risk_pct = (price - sl_level) / price * 100
            
            # TPs based on ATR
            tp1 = price + 1.0 * atr_5m
            tp2 = price + 2.0 * atr_5m
            tp3 = price + 3.5 * atr_5m
            
            rr1 = (tp1 - price) / (price - sl_level) if (price - sl_level) > 0 else 0
            rr2 = (tp2 - price) / (price - sl_level) if (price - sl_level) > 0 else 0
            
            # Position Sizing
            risk_usd = 0.40  # 2% of $20
            risk_per_token = price - sl_level
            if risk_per_token > 0:
                pos_size = risk_usd / risk_per_token
                pos_usd = pos_size * price
                leverage = pos_usd / 20.0
                
                print(f"   👉 HƯỚNG: LONG")
                print(f"   👉 ENTRY 1 (Market): ${price:.6f}")
                print(f"   👉 ENTRY 2 (Limit tại EMA34): ${ema34_close:.6f}")
                print(f"   👉 STOP LOSS (Cứng): ${sl_level:.6f} (-{risk_pct:.2f}%)")
                print(f"   👉 TAKE PROFIT 1 (Chốt 40%, dời SL về Entry): ${tp1:.6f} (R:R 1:{rr1:.2f})")
                print(f"   👉 TAKE PROFIT 2 (Chốt 30%): ${tp2:.6f} (R:R 1:{rr2:.2f})")
                print(f"   👉 TAKE PROFIT 3 (Trailing 30%): ${tp3:.6f}")
                print(f"   👉 QUẢN LÝ VỐN:")
                print(f"      • Khối lượng (Size): {pos_size:.4f} token (~${pos_usd:.2f})")
                print(f"      • Đòn bẩy khuyên dùng: {leverage:.1f}x (hoặc làm tròn ~{max(1, round(leverage))}x)")
                print(f"      • Target lợi nhuận TP2: +${pos_size * (tp2 - price):.2f}")
            else:
                print("   ❌ Không tính toán được SL hợp lý.")
                
    except Exception as e:
        print(f"❌ Lỗi phân tích: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(analyze_coins())
