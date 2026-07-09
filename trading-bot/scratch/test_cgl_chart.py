import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.coinglass.com/",
    "Origin": "https://www.coinglass.com"
}

# Test different parameter combinations
combinations = [
    {"symbol": "BTC"},
    {"symbol": "BTC", "timeType": 2},
    {"symbol": "BTC", "timeType": 1},
    {"symbol": "BTC", "range": "24h"},
    {"symbol": "BTC", "timeType": 2, "exchange": "Binance"},
    {"symbol": "BTC", "timeType": 2, "exName": "Binance"},
    {"symbol": "BTCUSDT", "timeType": 2},
]

for params in combinations:
    url = "https://fapi.coinglass.com/api/futures/liquidation/chart"
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        data = resp.json()
        print(f"Params: {params}")
        print(f"Keys in response: {list(data.keys())}")
        if 'data' in data or 'result' in data:
            print("Data found!")
            print(f"Data snippet: {json.dumps(data, indent=2)[:400]}\n")
        else:
            print(f"Response: {json.dumps(data)}\n")
    except Exception as e:
        print(f"Failed for {params}: {e}\n")
