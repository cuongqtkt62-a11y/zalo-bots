import yfinance as yf
import pandas as pd

def fetch_yfinance(ticker, interval, limit=800):
    period = '60d' if interval in ['5m', '15m'] else '1y'
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    
    if df.empty:
        print(f"Empty dataframe for {ticker} {interval}")
        return df

    # Drop multi-index columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    df.reset_index(inplace=True)
    
    # Rename columns to match binance
    rename_map = {
        'Datetime': 'timestamp',
        'Date': 'timestamp',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # Ensure timezone naive UTC for consistency
    if df['timestamp'].dt.tz is not None:
        df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
        
    df.set_index('timestamp', inplace=True)
    return df.tail(limit)

df_5m = fetch_yfinance("GC=F", "5m")
print("5m:")
print(df_5m.tail())

df_1d = fetch_yfinance("GC=F", "1d")
print("1d:")
print(df_1d.tail())
