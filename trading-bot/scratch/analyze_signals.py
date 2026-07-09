import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators

# List of Grade A+ Score 100 symbols from user summary
candidates = [
    "SLX/USDT:USDT",
    "JASMY/USDT:USDT",
    "LA/USDT:USDT",
    "XPIN/USDT:USDT",
    "MMT/USDT:USDT",
    "TAO/USDT:USDT",
    "MEME/USDT:USDT",
    "PHA/USDT:USDT",
    "AXL/USDT:USDT",
    "PYTH/USDT:USDT",
    "ASR/USDT:USDT",
    "TRUMP/USDT:USDT",
    "RESOLV/USDT:USDT"
]

async def analyze():
    fetcher = MarketDataFetcher()
    indicators = TechnicalIndicators()
    
    print("=== Analyzing Candidate Signals ===")
    results = []
    
    # Load markets first
    await fetcher.exchange.load_markets()
    
    for symbol in candidates:
        # Check if symbol exists on exchange
        if symbol not in fetcher.exchange.markets:
            print(f"⚠️ {symbol} not found on exchange.")
            continue
            
        try:
            # 1. Fetch current ticker details (24h volume & price change)
            ticker = await fetcher.fetch_ticker(symbol)
            vol_24h = ticker.get('volume_24h', 0)
            change_24h = ticker.get('change_24h', 0)
            current_price = ticker.get('last', 0)
            
            # 2. Fetch Daily and 4h data for bias check
            df_daily = await fetcher.fetch_ohlcv(symbol, '1d', limit=100)
            df_4h = await fetcher.fetch_ohlcv(symbol, '4h', limit=100)
            
            if df_daily.empty or df_4h.empty:
                continue
                
            df_daily = indicators.calculate_all(df_daily)
            df_4h = indicators.calculate_all(df_4h)
            
            last_d = df_daily.iloc[-1]
            last_4h = df_4h.iloc[-1]
            
            # Determine Daily and 4h trend alignment
            # Bullish stack: EMA 34 > EMA 89 > EMA 200
            d_stack = last_d.get('dragon_close', 0) > last_d.get('ema_89', 0) > last_d.get('ema_200', 0)
            h4_stack = last_4h.get('dragon_close', 0) > last_4h.get('ema_89', 0) > last_4h.get('ema_200', 0)
            
            # Count alignment score
            trend_score = 0
            if d_stack: trend_score += 50
            if h4_stack: trend_score += 50
            
            results.append({
                'symbol': symbol,
                'volume_24h_m': vol_24h / 1e6,
                'change_24h': change_24h,
                'price': current_price,
                'daily_bullish': d_stack,
                'h4_bullish': h4_stack,
                'trend_score': trend_score
            })
            
        except Exception as e:
            print(f"Error checking {symbol}: {e}")
            
    await fetcher.close()
    
    # Sort results by trend alignment and volume
    results.sort(key=lambda x: (x['trend_score'], x['volume_24h_m']), reverse=True)
    
    print("\n🔍 Candidate Analysis Results (Sorted by Probability):")
    print(f"{'Symbol':<15} | {'Vol 24h':<10} | {'24h Change':<10} | {'Daily Bullish':<13} | {'H4 Bullish':<10} | {'Trend Score':<10}")
    print("-" * 85)
    for r in results:
        print(f"{r['symbol']:<15} | ${r['volume_24h_m']:>7.2f}M | {r['change_24h']:>9.2f}% | {str(r['daily_bullish']):<13} | {str(r['h4_bullish']):<10} | {r['trend_score']:>10}")

if __name__ == "__main__":
    asyncio.run(analyze())
