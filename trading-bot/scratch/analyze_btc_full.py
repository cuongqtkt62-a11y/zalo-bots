import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from config import Config
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def main():
    fetcher = MarketDataFetcher()
    symbol = "BTC/USDT:USDT"
    binance_symbol = "BTCUSDT"
    
    print(f"{'='*65}")
    print(f"🔍 PHÂN TÍCH CHUYÊN SÂU BTC (BITCOIN)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*65}")
    
    try:
        await fetcher.exchange.load_markets()
        
        # 1. Ticker + 24h
        ticker = await fetcher.fetch_ticker(symbol)
        price = ticker.get('last', 0)
        change_24h = ticker.get('change_24h', 0)
        volume_24h = ticker.get('volume_24h', 0)
        
        print(f"\n1. THỊ TRƯỜNG HIỆN TẠI:")
        print(f"   • Giá: ${price:,.2f}")
        print(f"   • 24h: {change_24h:+.2f}%")
        print(f"   • Volume 24h: ${volume_24h:,.2f}")
        
        # 2. Derivatives
        funding = await fetcher.fetch_funding_rate(symbol)
        oi = await fetcher.fetch_open_interest(symbol)
        oi_usd = oi * price
        fr = funding.get('funding_rate', 0) * 100
        
        print(f"\n2. DERIVATIVES:")
        print(f"   • Funding Rate: {fr:.4f}%")
        print(f"   • Open Interest: {oi:,.2f} BTC (~${oi_usd:,.0f})")
        
        # Long/Short ratio
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # L/S Account Ratio
            url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={binance_symbol}&period=1h&limit=1"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        lr = float(data[0]['longAccount']) * 100
                        sr = float(data[0]['shortAccount']) * 100
                        ratio = float(data[0]['longShortRatio'])
                        print(f"   • L/S Ratio (1h): {ratio:.2f} (Long {lr:.1f}% vs Short {sr:.1f}%)")
            
            # L/S Account Ratio 4h
            url4 = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={binance_symbol}&period=4h&limit=1"
            async with session.get(url4) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        lr4 = float(data[0]['longAccount']) * 100
                        sr4 = float(data[0]['shortAccount']) * 100
                        print(f"   • L/S Ratio (4h): {float(data[0]['longShortRatio']):.2f} (Long {lr4:.1f}% vs Short {sr4:.1f}%)")
            
            # Top trader L/S
            url_top = f"https://fapi.binance.com/futures/data/topLongShortPositionRatio?symbol={binance_symbol}&period=1h&limit=1"
            async with session.get(url_top) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        print(f"   • Top Trader L/S (1h): {float(data[0]['longShortRatio']):.2f} (Long {float(data[0]['longAccount'])*100:.1f}% vs Short {float(data[0]['shortAccount'])*100:.1f}%)")
            
            # Order book depth clusters
            url_depth = "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=1000"
            async with session.get(url_depth) as resp:
                if resp.status == 200:
                    depth = await resp.json()
                    bids = depth.get('bids', [])
                    asks = depth.get('asks', [])
                    bid_buckets = {}
                    ask_buckets = {}
                    for p, q in bids:
                        p, q = float(p), float(q)
                        if p < price:
                            b = int(p // 500) * 500
                            bid_buckets[b] = bid_buckets.get(b, 0) + p * q
                    for p, q in asks:
                        p, q = float(p), float(q)
                        if p > price:
                            b = int(p // 500) * 500
                            ask_buckets[b] = ask_buckets.get(b, 0) + p * q
                    
                    top_bids = sorted(bid_buckets.items(), key=lambda x: x[1], reverse=True)[:3]
                    top_asks = sorted(ask_buckets.items(), key=lambda x: x[1], reverse=True)[:3]
                    
                    print(f"\n   📊 Tường mua lớn nhất (Support Walls):")
                    for b, v in sorted(top_bids, key=lambda x: x[0], reverse=True):
                        print(f"      ${b:,.0f}-${b+500:,.0f}: ${v/1e6:.2f}M")
                    print(f"   📊 Tường bán lớn nhất (Resistance Walls):")
                    for b, v in sorted(top_asks, key=lambda x: x[0]):
                        print(f"      ${b:,.0f}-${b+500:,.0f}: ${v/1e6:.2f}M")
        
        # 3. Multi-timeframe
        timeframes = {'D1': ('1d', 100), 'H4': ('4h', 150), 'H1': ('1h', 200), '15m': ('15m', 300)}
        
        print(f"\n3. XU HƯỚNG ĐA KHUNG THỜI GIAN:")
        for name, (tf, lim) in timeframes.items():
            df = await fetcher.fetch_ohlcv(symbol, tf, limit=lim)
            if df.empty:
                continue
            df = TechnicalIndicators.calculate_all(df)
            l = df.iloc[-1]
            
            if l.get('full_bullish_order'):
                trend = "🟢 BULLISH MẠNH (Full Order)"
            elif l.get('partial_bullish_order'):
                trend = "🟢 BULLISH (Partial)"
            elif l.get('full_bearish_order'):
                trend = "🔴 BEARISH MẠNH (Full Order)"
            elif l.get('partial_bearish_order'):
                trend = "🔴 BEARISH (Partial)"
            else:
                trend = "⚪ NEUTRAL"
            
            rsi = l.get('rsi', 0)
            vr = l.get('volume_ratio', 0)
            macd_hist = l.get('macd_histogram', 0)
            
            print(f"   • {name:3s}: {trend}")
            print(f"         RSI={rsi:.1f} | Vol={vr:.2f}x | MACD Hist={'🟢' if macd_hist > 0 else '🔴'} {macd_hist:.2f}")
            print(f"         Dragon={l.get('dragon_close',0):,.2f} | EMA89={l.get('ema_89',0):,.2f} | EMA200={l.get('ema_200',0):,.2f} | EMA610={l.get('ema_610',0):,.2f}")
            
            if name in ('15m', 'H1'):
                sp = l.get('ema_spread_pct', 0)
                print(f"         EMA Spread: {sp:.2f}% {'🔥 NÉN' if l.get('ema_squeeze') else ''}")
        
        # 4. Entry 5m detail
        print(f"\n4. CHI TIẾT KHUNG 5M (ENTRY):")
        df5 = await fetcher.fetch_ohlcv(symbol, '5m', limit=300)
        if not df5.empty:
            df5 = TechnicalIndicators.calculate_all(df5)
            l5 = df5.iloc[-1]
            
            rsi5 = l5.get('rsi', 0)
            atr5 = l5.get('atr', 0)
            spread5 = l5.get('ema_spread_pct', 0)
            dw5 = l5.get('dragon_width', 0)
            
            sq5 = df5['ema_squeeze'].iloc[-15:].any()
            dn5 = df5['dragon_narrow'].iloc[-15:].any()
            pne = l5.get('price_in_ema_cluster') or l5.get('price_in_dragon') or l5.get('touch_ema89') or l5.get('touch_ema200')
            c1 = (sq5 or dn5) and pne
            
            bull_rev = df5['bullish_reversal_at_ema'].iloc[-5:].any()
            bear_rev = df5['bearish_reversal_at_ema'].iloc[-5:].any()
            sweep_lo = df5['sweep_low'].iloc[-20:].any()
            sweep_hi = df5['sweep_high'].iloc[-20:].any()
            fvg_b = df5['fvg_bullish'].iloc[-10:].any()
            fvg_s = df5['fvg_bearish'].iloc[-10:].any()
            
            print(f"   • RSI: {rsi5:.1f} | ATR: ${atr5:,.2f}")
            print(f"   • EMA Spread: {spread5:.2f}% | Dragon Width: {dw5:.2f}%")
            print(f"   • [1] Nén EMA & Giá gần: {'✅' if c1 else '❌'} (Squeeze={sq5}, Narrow={dn5}, PriceNear={pne})")
            print(f"   • [2] Reversal: Bull={'🟢' if bull_rev else '❌'} | Bear={'🔴' if bear_rev else '❌'}")
            print(f"   • [3] Sweep: Low={'🟢' if sweep_lo else '❌'} | High={'🔴' if sweep_hi else '❌'}")
            print(f"   • [4] FVG: Bull={'🟢' if fvg_b else '❌'} | Bear={'🔴' if fvg_s else '❌'}")
            
            # Scoring
            d1_df = await fetcher.fetch_ohlcv(symbol, '1d', limit=50)
            h4_df = await fetcher.fetch_ohlcv(symbol, '4h', limit=100)
            d1_df = TechnicalIndicators.calculate_all(d1_df)
            h4_df = TechnicalIndicators.calculate_all(h4_df)
            
            d1t = "BULLISH" if d1_df.iloc[-1].get('partial_bullish_order') else "BEARISH" if d1_df.iloc[-1].get('partial_bearish_order') else "NEUTRAL"
            h4t = "BULLISH" if h4_df.iloc[-1].get('partial_bullish_order') else "BEARISH" if h4_df.iloc[-1].get('partial_bearish_order') else "NEUTRAL"
            
            sL = sS = 0
            if d1t == "BULLISH": sL += 15
            if h4t == "BULLISH": sL += 15
            if d1t == "BEARISH": sS += 15
            if h4t == "BEARISH": sS += 15
            if sq5 or dn5: sL += 10; sS += 10
            if pne: sL += 10; sS += 10
            if bull_rev: sL += 25
            if bear_rev: sS += 25
            if sweep_lo: sL += 20
            if sweep_hi: sS += 20
            if fvg_b: sL += 10
            if fvg_s: sS += 10
            
            print(f"\n5. KHUYẾN NGHỊ:")
            print(f"   • Bias: D1={d1t} | H4={h4t}")
            print(f"   • Score: LONG={sL} | SHORT={sS} (Min: 35)")
            
            if sL >= 35 and d1t != "BEARISH":
                sl = price - 1.5 * atr5
                tp1 = price + 1.0 * atr5
                tp2 = price + 2.0 * atr5
                tp3 = price + 3.5 * atr5
                rr = (tp2 - price) / (price - sl) if (price - sl) > 0 else 0
                print(f"\n   🟢 CANH MUA (LONG)")
                print(f"      Entry: ${price:,.2f} | SL: ${sl:,.2f} (-{(price-sl)/price*100:.2f}%)")
                print(f"      TP1: ${tp1:,.2f} | TP2: ${tp2:,.2f} (R:R 1:{rr:.1f}) | TP3: ${tp3:,.2f}")
            elif sS >= 35 and d1t != "BULLISH":
                sl = price + 1.5 * atr5
                tp1 = price - 1.0 * atr5
                tp2 = price - 2.0 * atr5
                tp3 = price - 3.5 * atr5
                rr = (price - tp2) / (sl - price) if (sl - price) > 0 else 0
                print(f"\n   🔴 CANH BÁN (SHORT)")
                print(f"      Entry: ${price:,.2f} | SL: ${sl:,.2f} (+{(sl-price)/price*100:.2f}%)")
                print(f"      TP1: ${tp1:,.2f} | TP2: ${tp2:,.2f} (R:R 1:{rr:.1f}) | TP3: ${tp3:,.2f}")
            else:
                print(f"\n   ⚪ ĐỨNG NGOÀI — Tín hiệu chưa đủ mạnh")
                
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
