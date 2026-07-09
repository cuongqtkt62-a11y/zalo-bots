import requests

def check():
    urls = [
        "https://fapi.binance.com/fapi/v1/ticker/price?symbol=XAUUSDT",
        "https://api.binance.com/api/v3/ticker/price?symbol=XAUUSDT",
        "https://fapi.binance.com/fapi/v1/ticker/price?symbol=PAXGUSDT",
        "https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT",
    ]
    for url in urls:
        try:
            r = requests.get(url)
            print(f"URL: {url} | Status: {r.status_code} | Response: {r.text}")
        except Exception as e:
            print(f"URL: {url} | Error: {e}")

if __name__ == "__main__":
    check()
