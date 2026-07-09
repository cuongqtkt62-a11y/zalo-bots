import asyncio
import aiohttp
import json

async def test_binance_depth():
    url = "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=1000"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                bids = data.get('bids', [])
                asks = data.get('asks', [])
                
                # We want to find the price levels with the highest volume.
                # Since prices are precise, we can group them into $100 buckets, or $50 buckets.
                # Let's group into $100 buckets.
                bid_buckets = {}
                ask_buckets = {}
                
                for price_str, qty_str in bids:
                    price = float(price_str)
                    qty = float(qty_str)
                    val_usd = price * qty
                    bucket = int(price // 100) * 100
                    bid_buckets[bucket] = bid_buckets.get(bucket, 0) + val_usd
                    
                for price_str, qty_str in asks:
                    price = float(price_str)
                    qty = float(qty_str)
                    val_usd = price * qty
                    bucket = int(price // 100) * 100
                    ask_buckets[bucket] = ask_buckets.get(bucket, 0) + val_usd
                
                # Sort buckets
                sorted_bids = sorted(bid_buckets.items(), key=lambda x: x[1], reverse=True)
                sorted_asks = sorted(ask_buckets.items(), key=lambda x: x[1], reverse=True)
                
                print("Top 5 Bid Clusters (Buy Walls / Long Liq Zones):")
                for bucket, val in sorted_bids[:5]:
                    print(f"  Vùng ${bucket} - ${bucket+100}: ${val/1e6:.2f}M USD")
                    
                print("\nTop 5 Ask Clusters (Sell Walls / Short Liq Zones):")
                for bucket, val in sorted_asks[:5]:
                    print(f"  Vùng ${bucket} - ${bucket+100}: ${val/1e6:.2f}M USD")
            else:
                print("Status code:", resp.status)

asyncio.run(test_binance_depth())
