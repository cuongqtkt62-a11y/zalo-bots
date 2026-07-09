import asyncio
import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def get_xau_details():
    symbol = "XAU/USDT:USDT"
    print(f"🔍 ĐANG TRUY XUẤT DỮ LIỆU KỸ THUẬT CHI TIẾT CHO: {symbol}")
    
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    
    try:
        await fetcher.exchange.load_markets()
        
        # 1. Fetch Ticker
        ticker = await fetcher.fetch_ticker(symbol)
        price = ticker.get('last', 0)
        change_24h = ticker.get('change_24h', 0)
        print(f"💵 Giá hiện tại: ${price:.2f} | Thay đổi 24h: {change_24h:+.2f}%")
        
        # 2. Daily Analysis
        df_daily = await fetcher.fetch_ohlcv(symbol, '1d', limit=50)
        if not df_daily.empty:
            df_daily = TechnicalIndicators.calculate_all(df_daily)
            last_d1 = df_daily.iloc[-1]
            rsi_d1 = last_d1.get('rsi', 0)
            ema34_d1 = last_d1.get('dragon_close', 0)
            ema89_d1 = last_d1.get('ema_89', 0)
            ema200_d1 = last_d1.get('ema_200', 0)
            ema610_d1 = last_d1.get('ema_610', 0)
            d1_trend = "BULLISH" if last_d1.get('partial_bullish_order', False) else "BEARISH" if last_d1.get('partial_bearish_order', False) else "NEUTRAL"
            
            print("\n📅 Khung Daily (D1):")
            print(f"   • Trend: {d1_trend} | RSI: {rsi_d1:.1f}")
            print(f"   • EMA34 (Dragon): ${ema34_d1:.2f} | EMA89: ${ema89_d1:.2f}")
            print(f"   • EMA200: ${ema200_d1:.2f} | EMA610: ${ema610_d1:.2f}")
            
        # 3. H4 Analysis
        df_h4 = await fetcher.fetch_ohlcv(symbol, '4h', limit=100)
        if not df_h4.empty:
            df_h4 = TechnicalIndicators.calculate_all(df_h4)
            last_h4 = df_h4.iloc[-1]
            rsi_h4 = last_h4.get('rsi', 0)
            ema34_h4 = last_h4.get('dragon_close', 0)
            ema89_h4 = last_h4.get('ema_89', 0)
            ema200_h4 = last_h4.get('ema_200', 0)
            ema610_h4 = last_h4.get('ema_610', 0)
            h4_trend = "BULLISH" if last_h4.get('partial_bullish_order', False) else "BEARISH" if last_h4.get('partial_bearish_order', False) else "NEUTRAL"
            
            print("\n⏳ Khung H4:")
            print(f"   • Trend: {h4_trend} | RSI: {rsi_h4:.1f} | Vol Ratio: {last_h4.get('volume_ratio', 0):.2f}x")
            print(f"   • EMA34 (Dragon): ${ema34_h4:.2f} | EMA89: ${ema89_h4:.2f}")
            print(f"   • EMA200: ${ema200_h4:.2f} | EMA610: ${ema610_h4:.2f}")
            
        # 4. Entry 5m Analysis
        df_5m = await fetcher.fetch_ohlcv(symbol, '5m', limit=300)
        if not df_5m.empty:
            df_5m = TechnicalIndicators.calculate_all(df_5m)
            last_5m = df_5m.iloc[-1]
            rsi_5m = last_5m.get('rsi', 0)
            atr_5m = last_5m.get('atr', 0)
            ema34_5m = last_5m.get('dragon_close', 0)
            ema89_5m = last_5m.get('ema_89', 0)
            ema200_5m = last_5m.get('ema_200', 0)
            ema610_5m = last_5m.get('ema_610', 0)
            
            # Cond 1: Squeeze/Narrow
            has_squeeze_5m = df_5m['ema_squeeze'].iloc[-15:].any()
            has_narrow_5m = df_5m['dragon_narrow'].iloc[-15:].any()
            current_spread_5m = last_5m.get('ema_spread_pct', 0)
            
            # Cond 2: Reversal candle
            has_bull_rev = df_5m['bullish_reversal_at_ema'].iloc[-5:].any()
            has_bear_rev = df_5m['bearish_reversal_at_ema'].iloc[-5:].any()
            
            # Cond 3: Stop Hunt
            has_sweep_low = df_5m['sweep_low'].iloc[-20:].any()
            has_sweep_high = df_5m['sweep_high'].iloc[-20:].any()
            
            # Cond 4: FVG
            has_fvg_bull = df_5m['fvg_bullish'].iloc[-10:].any()
            has_fvg_bear = df_5m['fvg_bearish'].iloc[-10:].any()
            
            print("\n⚡ Khung H5 (5m) - Điểm Bóp Cò:")
            print(f"   • RSI 5m: {rsi_5m:.1f} | ATR 5m: ${atr_5m:.2f}")
            print(f"   • Sonic R EMAs: EMA34=${ema34_5m:.2f} | EMA89=${ema89_5m:.2f} | EMA200=${ema200_5m:.2f}")
            print(f"   • [Cond 1] Nén Sonic R (4 EMA Spread/Dragon Narrow): {'✅ THỎA MÃN' if (has_squeeze_5m or has_narrow_5m) else '❌ CHƯA NÉN CHẶT'}")
            print(f"     (Ema spread: {current_spread_5m:.2f}% | Dragon width: {last_5m.get('dragon_width', 0):.2f}%)")
            print(f"   • [Cond 2] Nến đảo chiều tại EMA: LONG={'✅' if has_bull_rev else '⏳'} | SHORT={'✅' if has_bear_rev else '⏳'}")
            print(f"   • [Cond 3] Stop Hunt (Quét thanh khoản): LONG (Spring)={'✅' if has_sweep_low else '❌'} | SHORT (Upthrust)={'✅' if has_sweep_high else '❌'}")
            print(f"   • [Cond 4] Fair Value Gap (FVG): Bullish FVG={'🔥' if has_fvg_bull else '❌'} | Bearish FVG={'🔥' if has_fvg_bear else '❌'}")
            
            # Determine potential direction and orders
            bias = scanner._determine_bias(df_daily, df_h4)
            print(f"\n🎯 Bias Xu Hướng Tổng Hợp: {bias}")
            
            # Suggesting setups
            print("\n📝 KỊCH BẢN ENTRY ĐỀ XUẤT CHO ANH CƯỜNG:")
            if bias == "BULLISH" or bias == "NEUTRAL":
                # Long Scenario
                recent_lows = df_5m['low'].iloc[-20:].min()
                sl_long = recent_long_sl = recent_lows - atr_5m * 0.5
                tp1_long = price + 1.5 * atr_5m
                tp2_long = price + 3.0 * atr_5m
                print(f"   👉 Kịch bản LONG (nếu có Stop Hunt quét đáy):")
                print(f"      • Vùng Entry tối ưu: ${price:.2f} (hoặc đợi test lại cụm EMA34 ở ${ema34_5m:.2f})")
                print(f"      • Stop Loss: ${sl_long:.2f} (Dưới đáy gần nhất - 0.5x ATR)")
                print(f"      • Take Profit 1: ${tp1_long:.2f} (RR ~1:1, chốt 50% dời SL về entry)")
                print(f"      • Take Profit 2: ${tp2_long:.2f} (RR ~1:2)")
            
            if bias == "BEARISH" or bias == "NEUTRAL":
                # Short Scenario
                recent_highs = df_5m['high'].iloc[-20:].max()
                sl_short = recent_highs + atr_5m * 0.5
                tp1_short = price - 1.5 * atr_5m
                tp2_short = price - 3.0 * atr_5m
                print(f"   👉 Kịch bản SHORT (nếu có Stop Hunt quét đỉnh):")
                print(f"      • Vùng Entry tối ưu: ${price:.2f} (hoặc đợi test lại cụm EMA34 ở ${ema34_5m:.2f})")
                print(f"      • Stop Loss: ${sl_short:.2f} (Trên đỉnh gần nhất + 0.5x ATR)")
                print(f"      • Take Profit 1: ${tp1_short:.2f} (RR ~1:1, chốt 50% dời SL về entry)")
                print(f"      • Take Profit 2: ${tp2_short:.2f} (RR ~1:2)")
                
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(get_xau_details())
