import asyncio
from signal_scanner import SignalScanner
from config import Config

async def main():
    scanner = SignalScanner()
    try:
        print("Scanning ZAMA...")
        signal = await scanner.scan_symbol("ZAMA/USDT:USDT")
        if signal:
            print("="*60)
            print(f"SYMBOL: {signal.symbol}")
            print(f"DIRECTION: {signal.direction}")
            print(f"GRADE: {signal.grade}")
            print(f"SETUP TYPE: {signal.setup_type}")
            print(f"SCORE: {signal.confluence_score}")
            print(f"ENTRY: {signal.entry_price}")
            print(f"SL: {signal.stop_loss}")
            print(f"TP1: {signal.tp1}")
            print(f"TP2: {signal.tp2}")
            print(f"TP3: {signal.tp3}")
            print(f"R:R: {signal.risk_reward}")
            print(f"LOT SIZE: {signal.lot_size_suggestion}")
            print(f"LEVERAGE: {signal.leverage_suggestion}")
            print(f"ATR: {signal.atr_value}")
            print(f"TRIGGER DETAIL:\n{signal.trigger_detail}")
            print(f"SQUEEZE DETAIL: {signal.squeeze_detail}")
            print("="*60)
        else:
            print("No signal found for ZAMA at this candle.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
