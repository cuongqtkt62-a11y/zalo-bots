import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def analyze():
    fetcher = MarketDataFetcher()
    symbol = "BTC/USDT:USDT" # Binance Futures
    print("==================================================")
    print("🔍 PHÂN TÍCH BTC/USDT THEO HỆ THỐNG VSA × ICT × SONIC R")
    print("==================================================")
    
    timeframes = ['1d', '4h', '1h', '15m']
    
    try:
        # Load markets
        await fetcher.exchange.load_markets()
        
        # Funding rate and OI
        funding = await fetcher.fetch_funding_rate(symbol)
        oi = await fetcher.fetch_open_interest(symbol)
        ticker = await fetcher.fetch_ticker(symbol)
        
        print(f"💰 Giá hiện tại: {ticker.get('last', 0):,.2f} USD ({ticker.get('change_24h', 0):+.2f}%)")
        print(f"🧠 Funding Rate: {funding.get('funding_rate', 0):.4%}")
        print(f"📊 Open Interest: {oi:,.2f} BTC")
        print("-" * 50)
        
        for tf in timeframes:
            df = await fetcher.fetch_ohlcv(symbol, tf, limit=800)
            if df.empty:
                print(f"⚠️ Không lấy được dữ liệu cho khung {tf}")
                continue
                
            df = TechnicalIndicators.calculate_all(df)
            last = df.iloc[-1]
            
            print(f"📬 [Khung {tf.upper()}]")
            print(f"   • Price: {last['close']:,.2f} | RSI: {last['rsi']:.2f}")
            
            # Sonic R EMAs
            print(f"   • EMA34 Dragon Close: {last.get('dragon_close', 0):,.2f}")
            print(f"   • EMA89: {last.get('ema_89', 0):,.2f} | EMA200: {last.get('ema_200', 0):,.2f} | EMA610: {last.get('ema_610', 0):,.2f}")
            
            # Trend Order
            order = "Tangled"
            if last.get('full_bullish_order', False):
                order = "Full Bullish 📈"
            elif last.get('partial_bullish_order', False):
                order = "Partial Bullish 📈"
            elif last.get('full_bearish_order', False):
                order = "Full Bearish 📉"
            elif last.get('partial_bearish_order', False):
                order = "Partial Bearish 📉"
            print(f"   • EMA Order: {order}")
            
            # Dragon Slope / Trend direction
            dragon_dir = last.get('dragon_direction', 'FLAT')
            dragon_emoji = "📈" if dragon_dir == 'UP' else ("📉" if dragon_dir == 'DOWN' else "↔️")
            print(f"   • Dragon Trend: {dragon_dir} {dragon_emoji} (Slope: {last.get('dragon_slope', 0):.5f})")
            
            # Squeeze / Narrow
            squeeze_status = []
            if last.get('ema_squeeze', False):
                squeeze_status.append(f"EMA Squeeze ({last.get('ema_spread_pct', 0):.2f}%)")
            if last.get('dragon_narrow', False):
                squeeze_status.append(f"Dragon Narrow ({last.get('dragon_width', 0):.3f}%)")
            if last.get('golden_squeeze', False):
                squeeze_status.append("Golden Squeeze ⭐")
            
            if squeeze_status:
                print(f"   • Squeeze: {', '.join(squeeze_status)}")
            else:
                print(f"   • Spread: {last.get('ema_spread_pct', 0):.2f}%")
                
            # Patterns / Signals (Checking last 5 candles)
            signals = []
            recent_df = df.tail(5)
            if recent_df['sweep_low'].any():
                signals.append("Spring (Sweep Low) 🟢")
            if recent_df['sweep_high'].any():
                signals.append("Upthrust (Sweep High) 🔴")
            if recent_df['bullish_reversal_at_ema'].any():
                signals.append("Bull Reversal at EMA 🟢")
            if recent_df['bearish_reversal_at_ema'].any():
                signals.append("Bear Reversal at EMA 🔴")
            if recent_df['fvg_bullish'].any():
                signals.append("Bull FVG 🟢")
            if recent_df['fvg_bearish'].any():
                signals.append("Bear FVG 🔴")
                
            if signals:
                print(f"   • Recent Signals (last 5 candles): {', '.join(signals)}")
                
            # Support/Resistance
            recent_low = df['low'].tail(20).min()
            recent_high = df['high'].tail(20).max()
            print(f"   • Hỗ trợ (20 candles): {recent_low:,.2f} | Kháng cự (20 candles): {recent_high:,.2f}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(analyze())
