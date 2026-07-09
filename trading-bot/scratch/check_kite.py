import asyncio
import ccxt.async_support as ccxt

async def check():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    try:
        await exchange.load_markets()
        tickers = await exchange.fetch_tickers()
        
        # Look for KITE
        kite_symbol = None
        for symbol in tickers.keys():
            if 'KITE' in symbol:
                kite_symbol = symbol
                break
                
        if kite_symbol:
            ticker = tickers[kite_symbol]
            vol_24h = ticker.get('quoteVolume', 0)
            print(f"Symbol: {kite_symbol}")
            print(f"Price: {ticker.get('last')}")
            print(f"24h Vol (USD): {vol_24h:,.2f}")
        else:
            print("KITE/USDT is not found in Binance Futures symbols!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(check())
