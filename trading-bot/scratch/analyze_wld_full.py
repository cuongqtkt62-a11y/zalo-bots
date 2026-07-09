import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from config import Config
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    symbol = "WLD/USDT:USDT"
    binance_symbol = "WLDUSDT"
    
    print(f"============================================================")
    print(f"🔍 BẮT ĐẦU PHÂN TÍCH CHUYÊN SÂU WLD (WORLDCOIN)")
    print(f"📅 Thời gian thực hiện: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"============================================================")
    
    try:
        # Load exchange markets
        await fetcher.exchange.load_markets()
        
        # 1. Fetch current price & 24h ticker info
        ticker = await fetcher.fetch_ticker(symbol)
        if not ticker:
            # Fallback to WLD/USDT without :USDT
            symbol = "WLD/USDT"
            ticker = await fetcher.fetch_ticker(symbol)
            
        price = ticker.get('last', 0)
        change_24h = ticker.get('change_24h', 0)
        volume_24h = ticker.get('volume_24h', 0)
        
        print(f"\n1. THÔNG TIN THỊ TRƯỜNG HIỆN TẠI (WLD Futures):")
        print(f"   • Giá hiện tại: ${price:.4f}")
        print(f"   • Thay đổi 24h: {change_24h:+.2f}%")
        print(f"   • Khối lượng giao dịch 24h: ${volume_24h:,.2f}")
        
        # 2. Fetch Derivatives Data (Funding Rate, OI, Long/Short Ratio)
        funding = await fetcher.fetch_funding_rate(symbol)
        oi_tokens = await fetcher.fetch_open_interest(symbol)
        oi_usd = oi_tokens * price
        
        funding_rate_pct = funding.get('funding_rate', 0) * 100
        print(f"\n2. DỮ LIỆU PHÁI SINH (DERIVATIVES):")
        print(f"   • Funding Rate: {funding_rate_pct:.4f}%")
        print(f"   • Open Interest (OI): {oi_tokens:,.2f} WLD (~${oi_usd:,.2f})")
        
        # Fetch Long/Short ratios for 1h, 4h, and 1d
        try:
            ls_1h = await fetcher.exchange.fapiDataGetGlobalLongShortAccountRatio({
                'symbol': binance_symbol,
                'period': '1h',
                'limit': 1
            })
            ls_4h = await fetcher.exchange.fapiDataGetGlobalLongShortAccountRatio({
                'symbol': binance_symbol,
                'period': '4h',
                'limit': 1
            })
            
            if ls_1h:
                ratio = float(ls_1h[0]['longShortRatio'])
                long_p = float(ls_1h[0]['longAccount']) * 100
                short_p = float(ls_1h[0]['shortAccount']) * 100
                print(f"   • Tỷ lệ Long/Short Account (1h): {ratio:.2f} (Long {long_p:.1f}% vs Short {short_p:.1f}%)")
            if ls_4h:
                ratio_4h = float(ls_4h[0]['longShortRatio'])
                long_p_4h = float(ls_4h[0]['longAccount']) * 100
                short_p_4h = float(ls_4h[0]['shortAccount']) * 100
                print(f"   • Tỷ lệ Long/Short Account (4h): {ratio_4h:.2f} (Long {long_p_4h:.1f}% vs Short {short_p_4h:.1f}%)")
        except Exception as e:
            print(f"   ⚠️ Lỗi lấy tỷ lệ Long/Short: {e}")
            
        # 3. Timeframe Context Analysis (D1, H4, H1, 15m)
        timeframes = {
            'D1': ('1d', 100),
            'H4': ('4h', 150),
            'H1': ('1h', 200),
            '15m': ('15m', 300)
        }
        
        print(f"\n3. PHÂN TÍCH XU HƯỚNG CÁC KHUNG THỜI GIAN LỚN:")
        for name, (tf_code, limit) in timeframes.items():
            df = await fetcher.fetch_ohlcv(symbol, tf_code, limit=limit)
            if df.empty:
                print(f"   • Khung {name}: Không lấy được dữ liệu.")
                continue
            df = TechnicalIndicators.calculate_all(df)
            last_row = df.iloc[-1]
            
            # Trend determination
            if last_row.get('full_bullish_order', False):
                trend = "BULLISH TĂNG MẠNH (Full Order)"
            elif last_row.get('partial_bullish_order', False):
                trend = "BULLISH TĂNG NHẸ (Partial Order)"
            elif last_row.get('full_bearish_order', False):
                trend = "BEARISH GIẢM MẠNH (Full Order)"
            elif last_row.get('partial_bearish_order', False):
                trend = "BEARISH GIẢM NHẸ (Partial Order)"
            else:
                trend = "NEUTRAL (Đi ngang / Chưa rõ xu hướng)"
                
            rsi = last_row.get('rsi', 0)
            vol_ratio = last_row.get('volume_ratio', 0)
            
            # EMA levels for context
            ema89 = last_row.get('ema_89', 0)
            ema200 = last_row.get('ema_200', 0)
            ema610 = last_row.get('ema_610', 0)
            dragon_close = last_row.get('dragon_close', 0)
            
            print(f"   • Khung {name:3s}: Trend = {trend}")
            print(f"            RSI = {rsi:.1f} | Volume Ratio = {vol_ratio:.2f}x")
            print(f"            Dragon Close: {dragon_close:.4f} | EMA89: {ema89:.4f} | EMA200: {ema200:.4f} | EMA610: {ema610:.4f}")
            
            # Squeeze info for lower timeframes
            if name in ('15m', 'H1'):
                spread = last_row.get('ema_spread_pct', 0)
                is_sq = last_row.get('ema_squeeze', False)
                print(f"            EMA Spread %: {spread:.2f}% {'🔥 NÉN CHẶT' if is_sq else ''}")
                
        # 4. Entry Timeframe Detailed Analysis (5m - H5)
        print(f"\n4. CHI TIẾT ĐIỂM VÀO LỆNH KHUNG 5M (ENTRY TIMEFRAME):")
        df_5m = await fetcher.fetch_ohlcv(symbol, '5m', limit=300)
        if df_5m.empty:
            print("   ⚠️ Không thể tải dữ liệu 5m.")
        else:
            df_5m = TechnicalIndicators.calculate_all(df_5m)
            last_5m = df_5m.iloc[-1]
            
            rsi_5m = last_5m.get('rsi', 0)
            atr_5m = last_5m.get('atr', 0)
            ema34_close = last_5m.get('dragon_close', 0)
            ema89 = last_5m.get('ema_89', 0)
            ema200 = last_5m.get('ema_200', 0)
            ema610 = last_5m.get('ema_610', 0)
            
            # Condition 1: Squeeze & Compression
            has_squeeze_5m = df_5m['ema_squeeze'].iloc[-15:].any()
            has_narrow_5m = df_5m['dragon_narrow'].iloc[-15:].any()
            price_near_ema_5m = (
                last_5m.get('price_in_ema_cluster', False) or
                last_5m.get('price_in_dragon', False) or
                last_5m.get('touch_ema89', False) or
                last_5m.get('touch_ema200', False)
            )
            cond1_comp = (has_squeeze_5m or has_narrow_5m) and price_near_ema_5m
            ema_spread = last_5m.get('ema_spread_pct', 0)
            dragon_width = last_5m.get('dragon_width', 0)
            
            # Condition 2: Reversal Candles
            has_bull_reversal_5m = df_5m['bullish_reversal_at_ema'].iloc[-5:].any()
            has_bear_reversal_5m = df_5m['bearish_reversal_at_ema'].iloc[-5:].any()
            
            # Specific reversal details
            last_reversal_bull = "Không có"
            for idx in range(-1, -6, -1):
                if df_5m['bullish_reversal_at_ema'].iloc[idx]:
                    row = df_5m.iloc[idx]
                    pattern_type = []
                    if row.get('is_spring'): pattern_type.append("Spring")
                    if row.get('is_hammer'): pattern_type.append("Hammer")
                    if row.get('is_bull_engulfing'): pattern_type.append("Engulfing")
                    last_reversal_bull = f"{'+'.join(pattern_type)} ở nến cách đây {abs(idx)-1} cây (Vol: {row['volume_ratio']:.1f}x)"
                    break
                    
            last_reversal_bear = "Không có"
            for idx in range(-1, -6, -1):
                if df_5m['bearish_reversal_at_ema'].iloc[idx]:
                    row = df_5m.iloc[idx]
                    pattern_type = []
                    if row.get('is_upthrust'): pattern_type.append("Upthrust")
                    if row.get('is_shooting_star'): pattern_type.append("Shooting Star")
                    if row.get('is_bear_engulfing'): pattern_type.append("Engulfing")
                    last_reversal_bear = f"{'+'.join(pattern_type)} ở nến cách đây {abs(idx)-1} cây (Vol: {row['volume_ratio']:.1f}x)"
                    break
            
            # Condition 3: Sweep Liquidity
            has_sweep_low_5m = df_5m['sweep_low'].iloc[-20:].any()
            has_sweep_high_5m = df_5m['sweep_high'].iloc[-20:].any()
            
            sweep_low_level = np.nan
            if has_sweep_low_5m:
                sweep_candles = df_5m.iloc[-20:]
                sweep_idx = sweep_candles[sweep_candles['sweep_low'] == True].index
                if len(sweep_idx) > 0:
                    sweep_low_level = df_5m.loc[sweep_idx, 'sweep_low_level'].iloc[-1]
                    
            sweep_high_level = np.nan
            if has_sweep_high_5m:
                sweep_candles = df_5m.iloc[-20:]
                sweep_idx = sweep_candles[sweep_candles['sweep_high'] == True].index
                if len(sweep_idx) > 0:
                    sweep_high_level = df_5m.loc[sweep_idx, 'sweep_high_level'].iloc[-1]
            
            # Condition 4: FVG
            has_fvg_bull_5m = df_5m['fvg_bullish'].iloc[-10:].any()
            has_fvg_bear_5m = df_5m['fvg_bearish'].iloc[-10:].any()
            
            print(f"   • RSI 5m: {rsi_5m:.1f} | ATR 5m: {atr_5m:.5f}")
            print(f"   • Squeeze / Narrow trạng thái: Squeeze={last_5m.get('ema_squeeze', False)} ({ema_spread:.2f}%) | Narrow={last_5m.get('dragon_narrow', False)} ({dragon_width:.2f}%)")
            print(f"   • [Cond 1] Trạng thái nén & Giá gần EMA: {'✅ ĐẠT' if cond1_comp else '❌ CHƯA ĐẠT'}")
            print(f"   • [Cond 2] Nến rút râu / đảo chiều tại EMA (lùi 5 nến):")
            print(f"     - LONG (Bullish Reversal): {'🟢 CÓ' if has_bull_reversal_5m else '❌ KHÔNG'} -> Chi tiết: {last_reversal_bull}")
            print(f"     - SHORT (Bearish Reversal): {'🔴 CÓ' if has_bear_reversal_5m else '❌ KHÔNG'} -> Chi tiết: {last_reversal_bear}")
            print(f"   • [Cond 3] Quét thanh khoản (Stop Hunt lùi 20 nến):")
            print(f"     - Spring (Sweep Low): {'🟢 CÓ' if has_sweep_low_5m else '❌ KHÔNG'} -> Level: {f'${sweep_low_level:.4f}' if not np.isnan(sweep_low_level) else 'N/A'}")
            print(f"     - Upthrust (Sweep High): {'🔴 CÓ' if has_sweep_high_5m else '❌ KHÔNG'} -> Level: {f'${sweep_high_level:.4f}' if not np.isnan(sweep_high_level) else 'N/A'}")
            print(f"   • [Cond 4] Fair Value Gap (FVG lùi 10 nến):")
            print(f"     - Bullish FVG: {'🟢 CÓ' if has_fvg_bull_5m else '❌ KHÔNG'}")
            print(f"     - Bearish FVG: {'🔴 CÓ' if has_fvg_bear_5m else '❌ KHÔNG'}")
            
            # 5. Trading Proposals
            print(f"\n5. PHƯƠNG ÁN GIAO DỊCH ĐỀ XUẤT:")
            
            # Check bias from D1 & H4
            d1_df = await fetcher.fetch_ohlcv(symbol, '1d', limit=50)
            h4_df = await fetcher.fetch_ohlcv(symbol, '4h', limit=100)
            d1_df = TechnicalIndicators.calculate_all(d1_df)
            h4_df = TechnicalIndicators.calculate_all(h4_df)
            
            d1_trend = "BULLISH" if d1_df.iloc[-1].get('partial_bullish_order', False) else "BEARISH" if d1_df.iloc[-1].get('partial_bearish_order', False) else "NEUTRAL"
            h4_trend = "BULLISH" if h4_df.iloc[-1].get('partial_bullish_order', False) else "BEARISH" if h4_df.iloc[-1].get('partial_bearish_order', False) else "NEUTRAL"
            
            print(f"   • Xu hướng chủ đạo: D1 = {d1_trend} | H4 = {h4_trend}")
            
            # Simple scoring
            score_long = 0
            score_short = 0
            
            if d1_trend == "BULLISH": score_long += 15
            if h4_trend == "BULLISH": score_long += 15
            if d1_trend == "BEARISH": score_short += 15
            if h4_trend == "BEARISH": score_short += 15
            
            if has_squeeze_5m or has_narrow_5m:
                score_long += 10
                score_short += 10
            if price_near_ema_5m:
                score_long += 10
                score_short += 10
                
            if has_bull_reversal_5m: score_long += 25
            if has_bear_reversal_5m: score_short += 25
            
            if has_sweep_low_5m: score_long += 20
            if has_sweep_high_5m: score_short += 20
            
            if has_fvg_bull_5m: score_long += 10
            if has_fvg_bear_5m: score_short += 10
            
            print(f"   • Điểm tín hiệu (Confluence Score): LONG = {score_long} | SHORT = {score_short} (Min để xem xét: 35)")
            
            if score_long >= 35 and d1_trend != "BEARISH":
                # Entry long calculation
                recent_lows = df_5m['low'].iloc[-20:].min()
                sl_level = recent_lows - atr_5m * 0.5
                if sl_level > ema200 * 0.998:
                    sl_level = min(sl_level, ema200 * 0.998)
                    
                risk_pct = (price - sl_level) / price * 100
                tp1 = price + 1.0 * atr_5m
                tp2 = price + 2.0 * atr_5m
                tp3 = price + 3.5 * atr_5m
                
                rr1 = (tp1 - price) / (price - sl_level) if (price - sl_level) > 0 else 0
                rr2 = (tp2 - price) / (price - sl_level) if (price - sl_level) > 0 else 0
                
                print(f"\n   🟢 KHUYẾN NGHỊ: CANH MUA (LONG)")
                print(f"      - Entry: ${price:.4f} (hoặc Limit tại Dragon Close: ${ema34_close:.4f})")
                print(f"      - Stop Loss: ${sl_level:.4f} (-{risk_pct:.2f}%)")
                print(f"      - Take Profit 1: ${tp1:.4f} (R:R 1:{rr1:.2f})")
                print(f"      - Take Profit 2: ${tp2:.4f} (R:R 1:{rr2:.2f})")
                print(f"      - Take Profit 3: ${tp3:.4f}")
                
            elif score_short >= 35 and d1_trend != "BULLISH":
                # Entry short calculation
                recent_highs = df_5m['high'].iloc[-20:].max()
                sl_level = recent_highs + atr_5m * 0.5
                if sl_level < ema200 * 1.002:
                    sl_level = max(sl_level, ema200 * 1.002)
                    
                risk_pct = (sl_level - price) / price * 100
                tp1 = price - 1.0 * atr_5m
                tp2 = price - 2.0 * atr_5m
                tp3 = price - 3.5 * atr_5m
                
                rr1 = (price - tp1) / (sl_level - price) if (sl_level - price) > 0 else 0
                rr2 = (price - tp2) / (sl_level - price) if (sl_level - price) > 0 else 0
                
                print(f"\n   🔴 KHUYẾN NGHỊ: CANH BÁN (SHORT)")
                print(f"      - Entry: ${price:.4f} (hoặc Limit tại Dragon Close: ${ema34_close:.4f})")
                print(f"      - Stop Loss: ${sl_level:.4f} (+{risk_pct:.2f}%)")
                print(f"      - Take Profit 1: ${tp1:.4f} (R:R 1:{rr1:.2f})")
                print(f"      - Take Profit 2: ${tp2:.4f} (R:R 1:{rr2:.2f})")
                print(f"      - Take Profit 3: ${tp3:.4f}")
            else:
                print(f"\n   ⚪ KHUYẾN NGHỊ: ĐỨNG NGOÀI THEO DÕI (NEUTRAL)")
                print(f"      - Lý do: Tín hiệu chưa đủ mạnh hoặc ngược xu hướng lớn (D1).")
                
    except Exception as e:
        print(f"❌ Lỗi thực thi phân tích: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        
if __name__ == "__main__":
    asyncio.run(main())
