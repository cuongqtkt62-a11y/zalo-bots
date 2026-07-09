import asyncio
import aiohttp

YAHOO_SYMBOLS = {
    "s_and_p_500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow_jones": "^DJI",
    "vn_index": "^VNINDEX",
    "dxy_usd_index": "DX-Y.NYB",
    "gold_xau": "GC=F",
    "oil_wti": "CL=F",
    "us_10y_treasury": "^TNX",
    "nikkei_225": "^N225",
    "hang_seng": "^HSI",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

async def fetch_yahoo_fallback():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        result = {}
        for name, symbol in YAHOO_SYMBOLS.items():
            try:
                # Add a sleep to prevent rate limiting
                await asyncio.sleep(1.2)
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
                async with session.get(url) as resp:
                    print(f"Symbol {symbol}: status {resp.status}")
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    chart = data.get("chart", {}).get("result", [{}])[0]
                    meta = chart.get("meta", {})
                    price = meta.get("regularMarketPrice", 0)
                    prev = meta.get("previousClose", 0) or meta.get("chartPreviousClose", 0)
                    change_pct = ((price - prev) / prev * 100) if prev else 0

                    result[YAHOO_SYMBOLS[name]] = {
                        "price": price,
                        "change_pct": change_pct,
                        "change": price - prev,
                        "name": name,
                    }
            except Exception as e:
                print(f"Error for {symbol}: {e}")
        return result

async def main():
    res = await fetch_yahoo_fallback()
    print("Result:")
    import pprint
    pprint.pprint(res)

asyncio.run(main())
