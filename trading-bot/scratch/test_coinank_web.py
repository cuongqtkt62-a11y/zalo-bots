import requests
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

url = "https://coinank.com/"
try:
    resp = requests.get(url, headers=HEADERS)
    print("Status:", resp.status_code)
    html = resp.text
    print("HTML Length:", len(html))
    
    # Check if there is next data or initial state
    start = html.find('__NEXT_DATA__')
    if start > -1:
        json_start = html.find('>', start) + 1
        json_end = html.find('</script>', json_start)
        json_str = html[json_start:json_end].strip()
        data = json.loads(json_str)
        print("NEXT_DATA Keys:", list(data.keys()))
        props = data.get('props', {})
        page_props = props.get('pageProps', {})
        print("pageProps keys:", list(page_props.keys()))
        # Check if there's any liquidation data in pageProps
        for k, v in page_props.items():
            print(f"  pageProps[{k}] type: {type(v)}")
    else:
        # Check if there is other json data
        print("No NEXT_DATA found")
except Exception as e:
    print("Error:", e)
