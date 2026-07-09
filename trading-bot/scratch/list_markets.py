import asyncio
import ccxt.async_support as ccxt

async def check():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    await exchange.load_markets()
    
    # Print exchange name
    print(f"Exchange: {exchange.id}")
    
    # List keys of markets that contain XAU, PAXG, or GOLD
    for sym, m in exchange.markets.items():
        if 'XAU' in sym or 'PAXG' in sym or 'GOLD' in sym:
            print(f"Symbol: {sym} | ID: {m['id']} | Base: {m['base']} | Quote: {m['quote']}")
            
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(check())
