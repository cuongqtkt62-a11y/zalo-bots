import requests
import json

def test():
    # Yahoo Finance chart API for spot Gold (XAU/USD)
    url = "https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD=X?interval=1d&range=1mo"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        r = requests.get(url, headers=headers)
        print(f"Status Code: {r.status_code}")
        data = r.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]
        closes = quotes['close']
        highs = quotes['high']
        lows = quotes['low']
        opens = quotes['open']
        
        print(f"Fetched {len(timestamps)} days of Gold spot data from Yahoo Finance.")
        print(f"Last date timestamp close: {closes[-1]:.2f}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
