import asyncio
import aiohttp

async def test():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    # 1. Test DXY from Yahoo Finance API (v8 chart)
    print("Fetching DXY from Yahoo Finance API (v8)...")
    async with aiohttp.ClientSession(headers=headers) as session:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1d&range=2d"
        try:
            async with session.get(url) as resp:
                print(f"Yahoo status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    prev = meta.get("previousClose") or meta.get("chartPreviousClose")
                    change = ((price - prev) / prev * 100) if prev else 0
                    print(f"DXY: {price:.2f} ({change:+.2f}%)")
                else:
                    text = await resp.text()
                    print(f"Yahoo error: {text[:300]}")
        except Exception as e:
            print(f"Yahoo exception: {e}")

    # 2. Test BTC Dominance from CoinGecko
    print("\nFetching BTC Dominance from CoinGecko...")
    async with aiohttp.ClientSession(headers=headers) as session:
        url = "https://api.coingecko.com/api/v3/global"
        try:
            async with session.get(url) as resp:
                print(f"CoinGecko status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    btc_d = data.get("data", {}).get("market_cap_percentage", {}).get("btc", 0)
                    print(f"BTC Dominance: {btc_d:.2f}%")
                else:
                    text = await resp.text()
                    print(f"CoinGecko error: {text[:300]}")
        except Exception as e:
            print(f"CoinGecko exception: {e}")

if __name__ == "__main__":
    asyncio.run(test())
