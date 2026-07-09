import asyncio
import ccxt.async_support as ccxt

async def check():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    
    # We can turn on verbose mode to see the actual URLs being called!
    exchange.verbose = True
    
    try:
        await exchange.load_markets()
        print("\n--- FETCHING TICKER FOR XAU/USDT:USDT ---")
        ticker = await exchange.fetch_ticker('XAU/USDT:USDT')
        print(ticker)
        
        print("\n--- FETCHING OHLCV FOR XAU/USDT:USDT ---")
        ohlcv = await exchange.fetch_ohlcv('XAU/USDT:USDT', '1d', limit=2)
        print(ohlcv)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(check())
