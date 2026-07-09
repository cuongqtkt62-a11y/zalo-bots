import asyncio
import ccxt.async_support as ccxt

async def find():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        await exchange.load_markets()
        print("=== Binance Futures Symbols containing 'XAU', 'GOLD', or 'PAXG' ===")
        for s in exchange.symbols:
            if 'XAU' in s or 'GOLD' in s or 'PAXG' in s:
                print(f"Futures: {s}")
                
        # Also check spot just in case
        spot_exchange = ccxt.binance({'options': {'defaultType': 'spot'}})
        await spot_exchange.load_markets()
        print("\n=== Binance Spot Symbols containing 'XAU', 'GOLD', or 'PAXG' ===")
        for s in spot_exchange.symbols:
            if 'XAU' in s or 'GOLD' in s or 'PAXG' in s:
                print(f"Spot: {s}")
                
        await exchange.close()
        await spot_exchange.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(find())
