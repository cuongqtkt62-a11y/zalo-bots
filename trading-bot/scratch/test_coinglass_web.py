"""
Test — Extract liquidation data từ Coinglass web page (__NEXT_DATA__)
"""
import asyncio
import aiohttp
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.5",
}


async def test_coinglass_web():
    """Extract liquidation data from Coinglass web"""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # 1. LiquidationData page
        print("=" * 60)
        print("1. Testing /LiquidationData")
        print("=" * 60)
        url = "https://www.coinglass.com/vi/LiquidationData"
        try:
            async with session.get(url) as resp:
                text = await resp.text()
                # Extract __NEXT_DATA__
                start = text.find('__NEXT_DATA__')
                if start > -1:
                    # Find the JSON
                    json_start = text.find('>', start) + 1
                    json_end = text.find('</script>', json_start)
                    json_str = text[json_start:json_end].strip()
                    data = json.loads(json_str)
                    
                    # Navigate to props
                    page_props = data.get("props", {}).get("pageProps", {})
                    print(f"   Keys in pageProps: {list(page_props.keys())[:20]}")
                    
                    # Print some data
                    for key in page_props:
                        val = page_props[key]
                        if isinstance(val, (list, dict)):
                            preview = json.dumps(val, indent=2)[:500]
                            print(f"\n   📊 {key}:")
                            print(f"   {preview}")
                        else:
                            print(f"   {key}: {val}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # 2. Pro Liquidation Map page
        print("\n" + "=" * 60)
        print("2. Testing /pro/futures/LiquidationMap")
        print("=" * 60)
        url = "https://www.coinglass.com/pro/futures/LiquidationMap"
        try:
            async with session.get(url) as resp:
                text = await resp.text()
                start = text.find('__NEXT_DATA__')
                if start > -1:
                    json_start = text.find('>', start) + 1
                    json_end = text.find('</script>', json_start)
                    json_str = text[json_start:json_end].strip()
                    data = json.loads(json_str)
                    page_props = data.get("props", {}).get("pageProps", {})
                    print(f"   Keys in pageProps: {list(page_props.keys())[:20]}")
                    for key in page_props:
                        val = page_props[key]
                        if isinstance(val, (list, dict)):
                            preview = json.dumps(val, indent=2)[:800]
                            print(f"\n   📊 {key}:")
                            print(f"   {preview}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # 3. Liquidation page (general)
        print("\n" + "=" * 60)
        print("3. Testing /Liquidation")
        print("=" * 60)
        url = "https://www.coinglass.com/Liquidation"
        try:
            async with session.get(url) as resp:
                text = await resp.text()
                start = text.find('__NEXT_DATA__')
                if start > -1:
                    json_start = text.find('>', start) + 1
                    json_end = text.find('</script>', json_start)
                    json_str = text[json_start:json_end].strip()
                    data = json.loads(json_str)
                    page_props = data.get("props", {}).get("pageProps", {})
                    print(f"   Keys in pageProps: {list(page_props.keys())[:20]}")
                    for key in page_props:
                        val = page_props[key]
                        if isinstance(val, (list, dict)):
                            preview = json.dumps(val, indent=2)[:800]
                            print(f"\n   📊 {key}:")
                            print(f"   {preview}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


asyncio.run(test_coinglass_web())
