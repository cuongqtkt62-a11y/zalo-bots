import asyncio
import ccxt.async_support as ccxt

async def test():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    symbols = ['XAU/USDT:USDT', 'XAUT/USDT:USDT', 'PAXG/USDT:USDT', 'XAUT/USDT', 'PAXG/USDT']
    for s in symbols:
        try:
            print(f"\nTesting symbol: {s}")
            ohlcv = await exchange.fetch_ohlcv(s, '1h', limit=5)
            print(f"  SUCCESS! Fetched {len(ohlcv)} candles. Last close: {ohlcv[-1][4]}")
        except Exception as e:
            print(f"  FAILED: {e}")
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(test())
