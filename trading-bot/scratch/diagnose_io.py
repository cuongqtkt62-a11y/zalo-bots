import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'IO/USDT:USDT'
    try:
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=1000)
        df.index = df.index + pd.Timedelta(hours=7) # VN Time
        
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        # We target the area around 09:30 to 11:30
        target_df = df.loc['2026-06-09 09:30:00':'2026-06-09 11:30:00'].copy()
        
        print(f"--- Technical details for targeted range ---")
        for ts, row in target_df.iterrows():
            # Run scanner check manually for this candle
            sub_df = df.loc[:ts].copy()
            # Convert back to UTC for scanner
            sub_df_utc = sub_df.copy()
            sub_df_utc.index = sub_df_utc.index - pd.Timedelta(hours=7)
            
            # Let's inspect what happens inside the check confluence setup
            # 1. Check bias
            # For checking, we test both BULLISH and NEUTRAL bias
            for bias in ["BULLISH", "NEUTRAL"]:
                sig = scanner._check_confluence_setup(sub_df_utc, symbol, bias)
                if sig:
                    print(f"!!! SIGNAL FOUND at {ts} (Bias={bias}) | Setup={sig.setup_type} | Score={sig.confluence_score}")
            
            # Let's print the features:
            # - close, low, high, volume
            # - ema_34_close, ema_89, ema_200, ema_610
            # - sweep_low, bullish_reversal_at_ema
            # - ema_spread_pct, cond1_compression
            # Let's print out the raw conditions
            close = row['close']
            low = row['low']
            high = row['high']
            ema34 = row['dragon_close']
            ema89 = row['ema_89']
            ema200 = row['ema_200']
            ema610 = row['ema_610']
            sweep_low = row['sweep_low']
            bull_reversal = row['bullish_reversal_at_ema']
            spread = row['ema_spread_pct']
            vol_ratio = row['volume_ratio']
            
            print(f"{ts} | Close: {close:.4f} | L: {low:.4f} | H: {high:.4f} | E34: {ema34:.4f} | E89: {ema89:.4f} | E200: {ema200:.4f} | E610: {ema610:.4f}")
            print(f"             | sweep_low: {sweep_low} | bull_rev: {bull_reversal} | spread: {spread:.2f}% | vol_ratio: {vol_ratio:.2f}")
            
            # Let's check trend filter block
            # For LONG: close > ema89 and close > ema200 and dragon_close > ema89 and ema89 > ema200
            # Let's evaluate this condition:
            is_above_89_200 = close > ema89 and close > ema200
            is_dragon_above_89 = ema34 > ema89
            is_89_above_200 = ema89 > ema200
            trend_ok = is_above_89_200 and is_dragon_above_89 and is_89_above_200
            print(f"             | Trend check: above_89_200={is_above_89_200}, dragon_above_89={is_dragon_above_89}, 89_above_200={is_89_above_200} -> Trend_OK={trend_ok}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
