import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.coinglass.com/",
    "Origin": "https://www.coinglass.com"
}

endpoints = [
    "https://fapi.coinglass.com/api/futures/liquidation/coin/list",
    "https://fapi.coinglass.com/api/futures/liquidation/coins",
    "https://fapi.coinglass.com/api/futures/liquidation/daily",
    "https://fapi.coinglass.com/api/futures/liquidation/main",
    "https://fapi.coinglass.com/api/futures/liquidation/aggregated",
    "https://fapi.coinglass.com/api/futures/liquidation/summary",
    "https://fapi.coinglass.com/api/futures/liquidation/total",
    "https://fapi.coinglass.com/api/futures/liquidation/chart",
    "https://fapi.coinglass.com/api/futures/liquidation/chart/total",
    "https://fapi.coinglass.com/api/futures/liquidation/history/chart",
    "https://fapi.coinglass.com/api/futures/liquidation/list",
]

for url in endpoints:
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ {url}:")
            print(f"   Response: {json.dumps(data, indent=2)[:500]}\n")
        else:
            print(f"❌ {url} status {resp.status_code}")
    except Exception as e:
        print(f"💥 {url} failed: {e}")
