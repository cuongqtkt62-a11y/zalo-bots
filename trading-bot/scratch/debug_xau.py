import asyncio
import logging
from config import Config
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from signal_scanner import SignalScanner

# Cấu hình log để hiện thị debug
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def debug_xau():
    scanner = SignalScanner()
    fetcher = scanner.data_fetcher
    
    print("Bắt đầu quét XAU/USDT:USDT...")
    signal = await scanner.scan_symbol("XAU/USDT:USDT")
    
    if signal:
        print("\n🎯 TÍN HIỆU TÌM THẤY:")
        print(f"Coin: {signal.symbol}")
        print(f"Loại: {signal.setup_type}")
        print(f"Hướng: {signal.direction}")
        print(f"Hợp lưu: {signal.confluence_score}")
        print(f"R:R: 1:{signal.risk_reward}")
        print(f"Entry: {signal.entry_price}, TP: {signal.take_profit}, SL: {signal.stop_loss}")
    else:
        print("\n❌ KHÔNG CÓ TÍN HIỆU HỢP LỆ")
    
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(debug_xau())
