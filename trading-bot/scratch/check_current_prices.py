import asyncio
import ccxt.async_support as ccxt
import pandas as pd

async def check_prices():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        symbols = [
            "BTC/USDT",
            "NEAR/USDT",
            "RENDER/USDT",
            "WLD/USDT",
            "ARKM/USDT",
            "LINK/USDT",
            "TAO/USDT"
        ]
        
        # Load markets
        await exchange.load_markets()
        
        # Fetch tickers
        print("Fetching current prices from Binance Futures...")
        tickers = await exchange.fetch_tickers([s + ":USDT" for s in symbols])
        
        print("\n=== COMPARISON OF PRICES (Report vs Current June 13) ===")
        print(f"{'Token':<10} | {'Report Price (June 9)':<25} | {'Current Price (June 13)':<25} | {'Change':<10}")
        print("-" * 80)
        
        report_prices = {
            "BTC/USDT": 61600.0,
            "NEAR/USDT": 1.83,
            "RENDER/USDT": 2.0, # (mentioned as oversold, let's see current)
            "WLD/USDT": 0.4399,
            "ARKM/USDT": 1.0, # (RSI 16)
            "LINK/USDT": 7.5530,
            "TAO/USDT": 216.0 # (from previous TAO debug around ~220)
        }
        
        for sym in symbols:
            ccxt_sym = sym + ":USDT"
            current_price = tickers.get(ccxt_sym, {}).get('last', 0)
            rep_price = report_prices.get(sym, 0)
            
            if rep_price > 0 and current_price > 0:
                change = (current_price / rep_price - 1) * 100
                print(f"{sym:<10} | {rep_price:<25.4f} | {current_price:<25.4f} | {change:>+7.1f}%")
            else:
                print(f"{sym:<10} | {'N/A':<25} | {current_price:<25.4f} | {'N/A':<10}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(check_prices())
