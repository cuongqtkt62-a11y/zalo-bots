"""
Test script — Debug dòng tiền + Coinglass liquidation
"""
import asyncio
import aiohttp
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

async def test_yahoo_finance():
    """Test Yahoo Finance API"""
    print("=" * 60)
    print("📊 TEST YAHOO FINANCE")
    print("=" * 60)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # Test v7 quotes
        symbols = "^GSPC,^IXIC,^DJI,GC=F,CL=F,DX-Y.NYB,^TNX"
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}"
        print(f"\n1. Testing v7 API: {url}")
        try:
            async with session.get(url) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    quotes = data.get("quoteResponse", {}).get("result", [])
                    for q in quotes:
                        print(f"   ✅ {q['symbol']}: ${q.get('regularMarketPrice', 'N/A')} ({q.get('regularMarketChangePercent', 'N/A'):+.2f}%)")
                else:
                    text = await resp.text()
                    print(f"   ❌ Error: {text[:300]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        # Test v8 chart API (fallback)
        print(f"\n2. Testing v8 chart API (fallback):")
        for name, symbol in [("S&P 500", "^GSPC"), ("Gold", "GC=F"), ("DXY", "DX-Y.NYB")]:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                        price = meta.get("regularMarketPrice", 0)
                        prev = meta.get("previousClose", 0) or meta.get("chartPreviousClose", 0)
                        change = ((price - prev) / prev * 100) if prev else 0
                        print(f"   ✅ {name} ({symbol}): ${price:,.2f} ({change:+.2f}%)")
                    else:
                        print(f"   ❌ {name}: Status {resp.status}")
            except Exception as e:
                print(f"   ❌ {name}: {e}")

        # Test v6 quote (another alternative)
        print(f"\n3. Testing v6 API:")
        url = f"https://query2.finance.yahoo.com/v6/finance/quote?symbols=^GSPC,GC=F"
        try:
            async with session.get(url) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Data: {json.dumps(data, indent=2)[:500]}")
                else:
                    text = await resp.text()
                    print(f"   Response: {text[:300]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        # Test yfinance scrape endpoint
        print(f"\n4. Testing Yahoo Finance scrape (crumb-based):")
        try:
            # First get crumb
            async with session.get("https://finance.yahoo.com/quote/^GSPC/") as resp:
                if resp.status == 200:
                    print(f"   ✅ Yahoo Finance web accessible")
                else:
                    print(f"   Status: {resp.status}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")


async def test_coinglass():
    """Test Coinglass endpoints"""
    print("\n" + "=" * 60)
    print("📊 TEST COINGLASS LIQUIDATION")
    print("=" * 60)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # Test V2 public (old)
        print("\n1. Testing V2 public API:")
        endpoints = [
            ("Liquidation Info", "https://open-api.coinglass.com/public/v2/liquidation_info?symbol=BTC&time_type=2"),
            ("Long/Short Ratio", "https://open-api.coinglass.com/public/v2/long_short_ratio?symbol=BTC&time_type=2"),
        ]
        for name, url in endpoints:
            try:
                async with session.get(url) as resp:
                    print(f"   {name}: Status {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   Response: {json.dumps(data, indent=2)[:400]}")
            except Exception as e:
                print(f"   ❌ {name}: {e}")

        # Test Coinglass web scraping approach
        print("\n2. Testing Coinglass web data:")
        try:
            url = "https://www.coinglass.com/vi/LiquidationData"
            async with session.get(url) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    text = await resp.text()
                    print(f"   Page length: {len(text)} chars")
                    # Check if there's useful JSON data embedded
                    if '__NEXT_DATA__' in text:
                        print("   ✅ Found __NEXT_DATA__ (Next.js SSR data)")
                    else:
                        print("   ❌ No embedded data found")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        # Test Binance liquidation endpoint
        print("\n3. Testing Binance Force Orders (recent liquidations):")
        try:
            url = "https://fapi.binance.com/fapi/v1/allForceOrders?symbol=BTCUSDT&limit=20"
            async with session.get(url) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        total_long_liq = sum(float(o['origQty']) * float(o['price']) for o in data if o['side'] == 'SELL')
                        total_short_liq = sum(float(o['origQty']) * float(o['price']) for o in data if o['side'] == 'BUY')
                        print(f"   ✅ Got {len(data)} recent liquidations")
                        print(f"   Long Liq (SELL): ${total_long_liq:,.2f}")
                        print(f"   Short Liq (BUY): ${total_short_liq:,.2f}")
                        for o in data[:5]:
                            side = "🟢 Long→Liq" if o['side'] == 'SELL' else "🔴 Short→Liq"
                            print(f"     {side} @ ${float(o['price']):,.2f} | Qty: {o['origQty']} BTC | {o['time']}")
                    else:
                        print("   No recent liquidations")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        # Test Binance order book depth for liquidation estimation
        print("\n4. Testing Binance Order Book (depth) for liquidity clusters:")
        try:
            url = "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=20"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bids = data.get('bids', [])[:10]
                    asks = data.get('asks', [])[:10]
                    print(f"   Top 5 Bids (support/long liq zones):")
                    for b in bids[:5]:
                        print(f"     ${float(b[0]):,.2f} | Vol: {float(b[1]):.3f} BTC (${float(b[0])*float(b[1]):,.0f})")
                    print(f"   Top 5 Asks (resistance/short liq zones):")
                    for a in asks[:5]:
                        print(f"     ${float(a[0]):,.2f} | Vol: {float(a[1]):.3f} BTC (${float(a[0])*float(a[1]):,.0f})")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        # Test Binance top trader L/S position ratio
        print("\n5. Testing Binance Top Trader L/S Position Ratio:")
        try:
            url = "https://fapi.binance.com/futures/data/topLongShortPositionRatio?symbol=BTCUSDT&period=1h&limit=3"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for d in data:
                        print(f"   L/S Ratio: {d['longShortRatio']} | Long: {float(d['longAccount'])*100:.1f}% | Short: {float(d['shortAccount'])*100:.1f}%")
        except Exception as e:
            print(f"   ❌ Exception: {e}")


async def test_alternative_finance_apis():
    """Test alternative free finance APIs"""
    print("\n" + "=" * 60)
    print("📊 TEST ALTERNATIVE FINANCE APIs")
    print("=" * 60)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # Test Investing.com AJAX endpoints
        print("\n1. Testing Google Finance:")
        for symbol in ["BTC-USD", ".INX", "GC=F"]:
            try:
                url = f"https://www.google.com/finance/quote/{symbol}"
                async with session.get(url) as resp:
                    print(f"   {symbol}: Status {resp.status}")
            except Exception as e:
                print(f"   ❌ {symbol}: {e}")

        # Finnhub free tier
        print("\n2. Testing Finnhub (no key):")
        try:
            url = "https://finnhub.io/api/v1/quote?symbol=AAPL&token=demo"
            async with session.get(url) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Data: {data}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")


async def main():
    await test_yahoo_finance()
    await test_coinglass()
    await test_alternative_finance_apis()


if __name__ == "__main__":
    asyncio.run(main())
