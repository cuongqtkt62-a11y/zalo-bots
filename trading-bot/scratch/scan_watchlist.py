import sys
import os
import asyncio
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_scanner import SignalScanner

logging.getLogger().setLevel(logging.CRITICAL)

tokens = [
    "ARKM", "FET", "NIL", "RENDER", "WLD", "GRASS", "PYTH", "VIRTUAL", 
    "TAO", "IO", "IOTX", "AR", "PHA", "ATH", "JASMY", "AKT", "FLUX", 
    "GRT", "LINK", "FIL"
]

async def scan():
    scanner = SignalScanner()
    
    found_signals = []
    
    try:
        for token in tokens:
            symbol = f"{token}/USDT"
            try:
                signal = await scanner.scan_symbol(symbol)
                if signal:
                    found_signals.append(signal)
            except Exception as e:
                pass
                
        if not found_signals:
            print("🛑 KHÔNG CÓ LỆNH: Thị trường hiện tại chưa đủ điều kiện cho các đồng coin trong Watchlist.")
        else:
            print(f"🔥 BÁO CÁO LỆNH: TÌM THẤY {len(found_signals)} CƠ HỘI!\n")
            for s in found_signals:
                print(f"✅ Lệnh: {s.direction} {s.symbol}")
                print(f"   Grade: {s.grade} | Score: {s.confluence_score}/10")
                print(f"   💵 Entry: {s.entry_price}")
                print(f"   💰 Take Profit: {s.take_profit}")
                print(f"   🛡️ Stop Loss: {s.stop_loss}")
                print(f"   📝 Chi tiết: {s.trigger_detail.replace(chr(10), ' | ')}")
                print("-" * 50)
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(scan())
