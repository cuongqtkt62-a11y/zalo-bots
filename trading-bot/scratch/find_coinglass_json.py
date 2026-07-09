import requests
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

url = "https://www.coinglass.com/LiquidationData"
resp = requests.get(url, headers=HEADERS)
print("Status:", resp.status_code)
html = resp.text

# Extract __NEXT_DATA__
start = html.find('__NEXT_DATA__')
if start > -1:
    json_start = html.find('>', start) + 1
    json_end = html.find('</script>', json_start)
    json_str = html[json_start:json_end].strip()
    try:
        data = json.loads(json_str)
        print("NEXT_DATA Keys:", list(data.keys()))
        props = data.get('props', {})
        print("props keys:", list(props.keys()))
        page_props = props.get('pageProps', {})
        print("pageProps keys:", list(page_props.keys()))
        # Check other keys
        for k, v in page_props.items():
            print(f"pageProps[{k}] type: {type(v)}")
            if isinstance(v, dict):
                print(f"  keys: {list(v.keys())[:10]}")
    except Exception as e:
        print("Error parsing NEXT_DATA:", e)

# Find all script tags containing json-like data using regex
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\nFound {len(scripts)} script tags.")
for i, s in enumerate(scripts):
    s_strip = s.strip()
    if not s_strip:
        continue
    if 'liquidation' in s_strip.lower() or 'totalVolUsd' in s_strip or 'longVolUsd' in s_strip:
        print(f"\nScript {i} matches keywords (len={len(s_strip)})")
        print(s_strip[:500])
