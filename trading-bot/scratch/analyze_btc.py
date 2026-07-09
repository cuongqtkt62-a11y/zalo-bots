import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

async def analyze_btc():
    fetcher = MarketDataFetcher()
    symbol = 'BTC/USDT'
    
    print("--- Phân Tích BTC ---")
    try:
        # Fetch 4h for macro trend
        df_4h = await fetcher.fetch_ohlcv(symbol, '4h', limit=50)
        # Fetch 1h for medium trend
        df_1h = await fetcher.fetch_ohlcv(symbol, '1h', limit=50)
        # Fetch 15m for short trend
        df_15m = await fetcher.fetch_ohlcv(symbol, '15m', limit=50)
        
        for tf, df in [('4h', df_4h), ('1h', df_1h), ('15m', df_15m)]:
            if df.empty:
                continue
            df = TechnicalIndicators.calculate_all(df)
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            close = last_row['close']
            rsi = last_row['rsi']
            ema34 = last_row['dragon_close']
            ema89 = last_row['ema_89']
            
            trend = "Tăng" if close > ema34 else "Giảm"
            if close > ema34 and ema34 > ema89:
                trend = "Tăng mạnh (Bullish)"
            elif close < ema34 and ema34 < ema89:
                trend = "Giảm mạnh (Bearish)"
            elif close > ema34 and close < ema89:
                trend = "Phục hồi"
            elif close < ema34 and close > ema89:
                trend = "Điều chỉnh"
                
            print(f"[{tf}] Giá: {close:.2f} | RSI: {rsi:.2f} | Trend: {trend}")
            print(f"     EMA34: {ema34:.2f} | EMA89: {ema89:.2f}")
            
            recent_low = df['low'].tail(20).min()
            recent_high = df['high'].tail(20).max()
            print(f"     Hỗ trợ gần nhất: {recent_low:.2f} | Kháng cự: {recent_high:.2f}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(analyze_btc())
