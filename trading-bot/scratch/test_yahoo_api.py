import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime

async def test_yahoo():
    async with aiohttp.ClientSession(headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }) as session:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=5m&range=5d"
        async with session.get(url) as resp:
            data = await resp.json()
            if 'chart' in data and data['chart']['result']:
                res = data['chart']['result'][0]
                timestamps = res['timestamp']
                quote = res['indicators']['quote'][0]
                
                df = pd.DataFrame({
                    'timestamp': pd.to_datetime(timestamps, unit='s'),
                    'open': quote['open'],
                    'high': quote['high'],
                    'low': quote['low'],
                    'close': quote['close'],
                    'volume': quote['volume']
                })
                print("5m data fetched successfully!")
                print(df.tail())
                print(f"Total rows: {len(df)}")
            else:
                print(f"Error fetching data: {data}")

asyncio.run(test_yahoo())
