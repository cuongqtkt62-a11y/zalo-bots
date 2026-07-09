import asyncio
import logging
import sys
from config import Config
from signal_scanner import SignalScanner

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test():
    print("Initializing Config & SignalScanner...")
    scanner = SignalScanner()
    try:
        # Fetch some symbols
        print("Fetching top symbols...")
        symbols = await scanner.data_fetcher.get_symbol_names(20)
        print(f"Top symbols for test: {symbols[:5]}")
        
        found_any = False
        for target_symbol in symbols:
            print(f"Scanning symbol: {target_symbol}...")
            
            df = await scanner.data_fetcher.fetch_ohlcv(target_symbol, Config.TIMEFRAME_ENTRY, limit=300)
            if df.empty:
                print(f"❌ Failed to fetch data for {target_symbol}")
                continue
                
            # Run scan_symbol
            signal = await scanner.scan_symbol(target_symbol)
            if signal:
                print(f"🎯 🎯 Signal Found for {target_symbol}: {signal.grade} {signal.direction} | Score: {signal.confluence_score}")
                print(f"Details:\n{signal.trigger_detail}\n")
                found_any = True
                break
        
        if not found_any:
            print("ℹ️ Scanned top 20 symbols. No active signal found (market conditions not met).")
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scanner.data_fetcher.close()
        print("Exchange connection closed.")

if __name__ == "__main__":
    asyncio.run(test())
