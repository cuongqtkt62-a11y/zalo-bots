import asyncio
import pandas as pd
import numpy as np
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner

async def main():
    fetcher = MarketDataFetcher()
    scanner = SignalScanner()
    symbol = 'MYX/USDT:USDT'
    
    try:
        # Fetch 800 candles (exactly like the bot)
        print("Fetching 800 candles from exchange...")
        df = await fetcher.fetch_ohlcv(symbol, '5m', limit=800)
        if df.empty:
            print("No data fetched for MYX/USDT:USDT")
            return
            
        print("Calculating indicators...")
        indicators = TechnicalIndicators()
        df = indicators.calculate_all(df)
        
        # Convert index to Vietnam timezone (+7) for easy matching
        df.index = df.index + pd.Timedelta(hours=7)
        
        print("\nScanning historically for the last 50 candles...")
        found = False
        for j in range(len(df) - 50, len(df) + 1):
            sub_df = df.iloc[:j]
            if len(sub_df) < 650:
                continue
                
            # Create a copy with UTC index for the scanner
            sub_df_utc = sub_df.copy()
            sub_df_utc.index = sub_df_utc.index - pd.Timedelta(hours=7)
            
            # Check setup with BULLISH and NEUTRAL bias
            for bias in ["BULLISH", "NEUTRAL"]:
                signal = scanner._check_confluence_setup(sub_df_utc, symbol, bias)
                if signal:
                    sig_ts = pd.to_datetime(signal.timestamp) + pd.Timedelta(hours=7)
                    print(f"\n=============================================")
                    print(f"✅ SIGNAL FOUND AT CANDLE: {sig_ts} (VN Time)")
                    print(f"=============================================")
                    print(f"Bias: {bias} | Setup: {signal.setup_type} | Grade: {signal.grade} | Score: {signal.confluence_score}")
                    print(f"Plan:")
                    print(f"  ▶️ Entry: {signal.entry_price:.5f}")
                    print(f"  🛑 SL: {signal.stop_loss:.5f}")
                    print(f"  🎯 TP1: {signal.tp1:.5f}")
                    print(f"  🎯 TP2: {signal.tp2:.5f}")
                    print(f"  🎯 TP3: {signal.tp3:.5f}")
                    print(f"  📐 R:R: 1:{signal.risk_reward:.1f} | ATR: {signal.atr_value:.5f}")
                    print(f"  📦 Lot: {signal.lot_size_suggestion:.4f} | Leverage: {signal.leverage_suggestion}x")
                    print(f"Trigger Details:\n{signal.trigger_detail}")
                    print(f"Squeeze Details: {signal.squeeze_detail}")
                    print(f"=============================================\n")
                    found = True
                    break
                    
        if not found:
            print("No signal detected in the historical scan.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await fetcher.close()
        await scanner.data_fetcher.close()

if __name__ == '__main__':
    asyncio.run(main())
