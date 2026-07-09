"""
Test — Coinglass internal API endpoints (XHR calls from browser)
"""
import asyncio
import aiohttp
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.coinglass.com/",
    "Origin": "https://www.coinglass.com",
}

async def test():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        endpoints = [
            # Possible internal APIs that the Coinglass frontend calls
            ("Liq Coin List", "https://cglapi.com/api/futures/liquidation/coin-list?ex=&range=24h"),
            ("Liq Detail", "https://cglapi.com/api/futures/liquidation/detail?symbol=BTC&range=24h"),
            ("Liq History", "https://cglapi.com/api/futures/liquidation/history?symbol=BTC&timeType=2"),
            ("Liq Aggregated", "https://cglapi.com/api/futures/liquidation/aggregated-heatmap/model1?symbol=BTC&range=3d"),
            ("Liq Heatmap", "https://cglapi.com/api/futures/liquidation/heatmap/model1?exchange=Binance&symbol=BTCUSDT&range=3d"),
            
            # Try open-api v3
            ("V3 Liq", "https://open-api-v3.coinglass.com/api/futures/liquidation/info?symbol=BTC&timeType=2"),
            
            # Try CGLapi public
            ("CGL Liq Info", "https://cglapi.com/api/futures/liquidation/info?symbol=BTC&timeType=2"),
            ("CGL L/S Ratio", "https://cglapi.com/api/futures/longShort/global?symbol=BTC&timeType=4"),
            ("CGL OI", "https://cglapi.com/api/futures/openInterest/chart?symbol=BTC&timeType=4&currency=USD"),
            
            # Try fapi
            ("FAPI Liq", "https://fapi.coinglass.com/api/futures/liquidation/coin-list?ex=&range=24h"),
            ("FAPI L/S", "https://fapi.coinglass.com/api/futures/longShort/global?symbol=BTC&timeType=4"),
            ("FAPI OI", "https://fapi.coinglass.com/api/futures/openInterest/chart?symbol=BTC&timeType=4"),
            ("FAPI Liq Order", "https://fapi.coinglass.com/api/futures/liquidation/order?symbol=BTC&timeType=2"),
            ("FAPI Liq Detail", "https://fapi.coinglass.com/api/futures/liquidation/detail?symbol=BTC&range=24h"),
        ]
        
        for name, url in endpoints:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    status = resp.status
                    if status == 200:
                        try:
                            data = await resp.json()
                            code = data.get("code", "?")
                            success = data.get("success", "?")
                            preview = json.dumps(data, indent=2)[:600]
                            print(f"✅ {name} [{status}] code={code} success={success}")
                            print(f"   {preview}\n")
                        except:
                            text = await resp.text()
                            print(f"⚠️ {name} [{status}] Not JSON: {text[:200]}\n")
                    else:
                        text = await resp.text()
                        print(f"❌ {name} [{status}]: {text[:200]}\n")
            except Exception as e:
                print(f"❌ {name}: {e}\n")


asyncio.run(test())
