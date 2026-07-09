import ccxt
import pandas as pd
import numpy as np

def get_rsi(series, period=14):
    delta = series.diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    roll_up1 = up.ewm(span=period).mean()
    roll_down1 = down.abs().ewm(span=period).mean()
    rs = roll_up1 / roll_down1
    return 100.0 - (100.0 / (1.0 + rs))

def analyze():
    exchange = ccxt.binance()
    for tf in ['4h', '1h', '15m']:
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', tf, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema34'] = df['close'].ewm(span=34, adjust=False).mean()
        df['ema89'] = df['close'].ewm(span=89, adjust=False).mean()
        df['rsi'] = get_rsi(df['close'])
        
        last = df.iloc[-1]
        print(f"[{tf}] Price: {last['close']:.2f} | RSI: {last['rsi']:.2f} | EMA34: {last['ema34']:.2f} | EMA89: {last['ema89']:.2f} | Support: {df['low'].tail(20).min():.2f} | Resist: {df['high'].tail(20).max():.2f}")

if __name__ == "__main__":
    analyze()
