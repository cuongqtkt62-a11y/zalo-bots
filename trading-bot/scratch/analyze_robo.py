import asyncio
import pandas as pd
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'ROBO/USDT:USDT'
    try:
        df_raw = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        
        df_raw_vn = df_raw.copy()
        df_raw_vn.index = df_raw_vn.index + pd.Timedelta(hours=7)
        
        # We look around 21:50 to 22:15 VN time
        target_indices = df_raw_vn.loc['2026-06-09 21:50:00':'2026-06-09 22:15:00'].index
        
        print("--- Real-time Simulation of ROBO/USDT ---")
        for ts_vn in target_indices:
            ts_utc = ts_vn - pd.Timedelta(hours=7)
            idx = df_raw.index.get_loc(ts_utc)
            sub_df_raw = df_raw.iloc[:idx+1].copy()
            
            indicators = TechnicalIndicators()
            sub_df = indicators.calculate_all(sub_df_raw)
            
            last = sub_df.iloc[-1]
            last_ts_vn = sub_df.index[-1] + pd.Timedelta(hours=7)
            
            # Check setup
            for bias in ["BULLISH", "NEUTRAL"]:
                sig = scanner._check_confluence_setup(sub_df, symbol, bias)
                if sig:
                    print(f"\n=============================================")
                    print(f"✅ SIGNAL DETECTED AT {last_ts_vn} (VN Time) Bias={bias}")
                    print(f"=============================================")
                    print(f"Setup: {sig.setup_type} | Grade: {sig.grade} | Score: {sig.confluence_score}")
                    print(f"Plan:")
                    print(f"  ▶️ Entry: {sig.entry_price:.5f}")
                    print(f"  🛑 SL: {sig.stop_loss:.5f}")
                    print(f"  🎯 TP1: {sig.tp1:.5f} | TP2: {sig.tp2:.5f} | TP3: {sig.tp3:.5f}")
                    print(f"Trigger Details:\n{sig.trigger_detail}")
                    print(f"Squeeze Details: {sig.squeeze_detail}")
                    print(f"=============================================\n")
            
            close = last['close']
            open_val = last['open']
            low = last['low']
            high = last['high']
            ema34 = last['dragon_close']
            ema89 = last['ema_89']
            ema200 = last['ema_200']
            ema610 = last['ema_610']
            sweep_low = last['sweep_low']
            bull_reversal = last['bullish_reversal_at_ema']
            spread = last['ema_spread_pct']
            vol_ratio = last['volume_ratio']
            
            print(f"{last_ts_vn} | Close: {close:.5f} | Open: {open_val:.5f} | L: {low:.5f} | H: {high:.5f}")
            print(f"             | E34: {ema34:.5f} | E89: {ema89:.5f} | E200: {ema200:.5f} | E610: {ema610:.5f}")
            print(f"             | sweep_low: {sweep_low} | bull_rev: {bull_reversal} | spread: {spread:.2f}% | vol_ratio: {vol_ratio:.2f}")
            
            # Check trend details
            is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
            if ema89 < ema200:
                is_trending_long = False
            is_above_dragon = close > last.get('dragon_low', 0)
            print(f"             | is_trending_long: {is_trending_long} | is_above_dragon: {is_above_dragon}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
