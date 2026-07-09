import asyncio
import pandas as pd
from market_data import MarketDataFetcher

async def calculate_range():
    fetcher = MarketDataFetcher()
    symbol = "XAU/USDT:USDT" # Gold futures on Binance
    
    try:
        await fetcher.exchange.load_markets()
        
        # Fetch daily OHLCV data for the last 100 days
        df = await fetcher.fetch_ohlcv(symbol, "1d", limit=100)
        
        if df.empty:
            print("❌ Không lấy được dữ liệu XAU/USDT:USDT từ Binance Futures.")
            # Fallback to PAXG/USDT
            symbol = "PAXG/USDT:USDT"
            df = await fetcher.fetch_ohlcv(symbol, "1d", limit=100)
            
        if df.empty:
            print("❌ Không lấy được dữ liệu PAXG/USDT:USDT từ Binance Futures.")
            return

        print(f"📊 Đã lấy thành công {len(df)} nến ngày của {symbol}")
        
        # Calculate daily range (High - Low)
        df['daily_range'] = df['high'] - df['low']
        df['daily_range_pct'] = (df['daily_range'] / df['close']) * 100
        
        # Compute averages
        avg_range_10 = df['daily_range'].tail(10).mean()
        avg_range_30 = df['daily_range'].tail(30).mean()
        avg_range_100 = df['daily_range'].mean()
        
        avg_range_pct_10 = df['daily_range_pct'].tail(10).mean()
        avg_range_pct_30 = df['daily_range_pct'].tail(30).mean()
        avg_range_pct_100 = df['daily_range_pct'].mean()
        
        max_range_100 = df['daily_range'].max()
        max_range_day = df['daily_range'].idxmax()
        min_range_100 = df['daily_range'].min()
        min_range_day = df['daily_range'].idxmin()
        
        last_close = df['close'].iloc[-1]
        
        print("\n=== KẾT QUẢ PHÂN TÍCH BIÊN ĐỘ DAO ĐỘNG HÀNG NGÀY CỦA XAU/USD ===")
        print(f"💰 Giá XAU hiện tại: {last_close:,.2f} USD")
        print("-" * 50)
        print(f"📈 Dao động trung bình 10 ngày qua: {avg_range_10:.2f} USD/ngày ({avg_range_pct_10:.2f}%)")
        print(f"📈 Dao động trung bình 30 ngày qua: {avg_range_30:.2f} USD/ngày ({avg_range_pct_30:.2f}%)")
        print(f"📈 Dao động trung bình 100 ngày qua: {avg_range_100:.2f} USD/ngày ({avg_range_pct_100:.2f}%)")
        print("-" * 50)
        print(f"🔥 Dao động lớn nhất (100 ngày): {max_range_100:.2f} USD vào ngày {max_range_day.strftime('%Y-%m-%d')}")
        print(f"❄️ Dao động nhỏ nhất (100 ngày): {min_range_100:.2f} USD vào ngày {min_range_day.strftime('%Y-%m-%d')}")
        print("================================================================")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(calculate_range())
