import ccxt
import pandas as pd

def fetch_derivatives_data():
    exchange = ccxt.binance({
        'options': {'defaultType': 'future'},
    })
    
    symbol = 'BTC/USDT'
    
    try:
        # 1. Funding Rate
        funding = exchange.fetch_funding_rate(symbol)
        funding_rate = funding['fundingRate'] * 100  # to percentage
        
        # 2. Open Interest
        oi = exchange.fetch_open_interest(symbol)
        open_interest = oi['openInterestAmount'] if 'openInterestAmount' in oi else oi['baseVolume']
        
        # 3. Fetch current price to calculate nominal OI
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        oi_usd = open_interest * price if open_interest else 0
        
        # Binance has specific endpoints for Long/Short ratio but ccxt might not expose them directly easily without implicit API.
        # Let's use implicit API to get long/short ratio
        # /futures/data/globalLongShortAccountRatio
        ls_ratio_data = exchange.fapiDataGetGlobalLongShortAccountRatio({
            'symbol': 'BTCUSDT',
            'period': '1h',
            'limit': 1
        })
        
        ls_ratio = float(ls_ratio_data[0]['longShortRatio'])
        long_pct = float(ls_ratio_data[0]['longAccount']) * 100
        short_pct = float(ls_ratio_data[0]['shortAccount']) * 100
        
        print(f"Price: {price}")
        print(f"Funding Rate: {funding_rate:.4f}%")
        print(f"Open Interest (BTC): {open_interest:.2f} BTC")
        print(f"Open Interest (USD): ${oi_usd:,.2f}")
        print(f"Long/Short Ratio (1h): {ls_ratio:.4f}")
        print(f"Long %: {long_pct:.2f}% | Short %: {short_pct:.2f}%")
        
    except Exception as e:
        print(f"Error fetching derivatives data: {e}")

if __name__ == "__main__":
    fetch_derivatives_data()
