import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'SENT/USDT:USDT'
    try:
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        df.index = df.index + pd.Timedelta(hours=7) # VN Time
        
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        # We look around 16:35 to 16:45
        target_df = df.loc['2026-06-09 16:20:00':'2026-06-09 16:45:00'].copy()
        
        print("--- Technical State for SENT/USDT ---")
        for ts, row in target_df.iterrows():
            sub_df = df.loc[:ts].copy()
            sub_df_utc = sub_df.copy()
            sub_df_utc.index = sub_df_utc.index - pd.Timedelta(hours=7)
            
            # Check bias
            for bias in ["BULLISH", "NEUTRAL"]:
                sig = scanner._check_confluence_setup(sub_df_utc, symbol, bias)
                if sig:
                    print(f"!!! SIGNAL FOUND at {ts} (Bias={bias}) | Setup={sig.setup_type} | Score={sig.confluence_score}")
            
            close = row['close']
            low = row['low']
            high = row['high']
            open_val = row['open']
            ema34 = row['dragon_close']
            ema89 = row['ema_89']
            ema200 = row['ema_200']
            ema610 = row['ema_610']
            sweep_low = row['sweep_low']
            bull_reversal = row['bullish_reversal_at_ema']
            spread = row['ema_spread_pct']
            vol_ratio = row['volume_ratio']
            
            print(f"{ts} | Close: {close:.4f} | Open: {open_val:.4f} | L: {low:.4f} | H: {high:.4f}")
            print(f"             | E34: {ema34:.4f} | E89: {ema89:.4f} | E200: {ema200:.4f} | E610: {ema610:.4f}")
            print(f"             | sweep_low: {sweep_low} | bull_rev: {bull_reversal} | spread: {spread:.2f}% | vol_ratio: {vol_ratio:.2f}")
            
            # Check trend details
            is_trending_long = row.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
            if ema89 < ema200:
                is_trending_long = False
            is_above_dragon = close > row.get('dragon_low', 0)
            print(f"             | is_trending_long: {is_trending_long} | is_above_dragon: {is_above_dragon} (dragon_low={row.get('dragon_low', 0):.4f})")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
