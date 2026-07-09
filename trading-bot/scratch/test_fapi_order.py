import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.coinglass.com/",
    "Origin": "https://www.coinglass.com"
}

url = "https://fapi.coinglass.com/api/futures/liquidation/order?symbol=BTC&timeType=2&pageSize=5&pageNum=1"
try:
    resp = requests.get(url, headers=HEADERS)
    print("Status:", resp.status_code)
    data = resp.json()
    print("Keys in response:", list(data.keys()))
    print("Full response:", json.dumps(data, indent=2))
except Exception as e:
    print("Error:", e)
