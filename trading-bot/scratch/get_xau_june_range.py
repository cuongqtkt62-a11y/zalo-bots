import asyncio
import pandas as pd
from market_data import MarketDataFetcher

async def list_june_details():
    fetcher = MarketDataFetcher()
    symbol = "XAU/USDT:USDT" # Gold futures on Binance
    
    try:
        await fetcher.exchange.load_markets()
        
        # Fetch daily OHLCV data for the last 30 days to cover all of June
        df = await fetcher.fetch_ohlcv(symbol, "1d", limit=30)
        
        if df.empty:
            # Fallback to PAXG/USDT
            symbol = "PAXG/USDT:USDT"
            df = await fetcher.fetch_ohlcv(symbol, "1d", limit=30)
            
        if df.empty:
            print("❌ Không lấy được dữ liệu.")
            return

        # Calculate daily range
        df['daily_range'] = df['high'] - df['low']
        df['daily_range_pct'] = (df['daily_range'] / df['close']) * 100
        
        # Filter for June 2026
        df_june = df[df.index >= '2026-06-01']
        
        if df_june.empty:
            print("❌ Không tìm thấy dữ liệu từ ngày 01/06/2026.")
            return
            
        print("\n| Ngày | Giá Mở Cửa (Open) | Giá Cao Nhất (High) | Giá Thấp Nhất (Low) | Giá Đóng Cửa (Close) | Biên Độ (USD) | Biên Độ (%) |")
        print("|---|---|---|---|---|---|---|")
        
        for date, row in df_june.iterrows():
            print(f"| {date.strftime('%Y-%m-%d')} | {row['open']:,.2f} | {row['high']:,.2f} | {row['low']:,.2f} | {row['close']:,.2f} | **{row['daily_range']:.2f} USD** | {row['daily_range_pct']:.2f}% |")
            
        avg_range = df_june['daily_range'].mean()
        avg_pct = df_june['daily_range_pct'].mean()
        print(f"\n👉 **Trung bình từ đầu tháng 6 đến nay:** **{avg_range:.2f} USD/ngày** ({avg_pct:.2f}%)")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(list_june_details())
