"""
MiroFish Correlation Analyzer — Geopolitical & Commodity Impact Engine
Đánh giá mức độ ảnh hưởng của tin tức địa chính trị (Iran, Hormuz) 
lên giá Dầu (WTI/Brent), Vàng (XAU) và đề xuất chiến lược giao dịch hợp lưu.
"""

import asyncio
import os
import re
import aiohttp
import feedparser
from datetime import datetime, timezone, timedelta
from news_sources import YAHOO_FINANCE_QUOTES, YAHOO_SYMBOLS, GOOGLE_NEWS_FEEDS
from market_data import MarketDataFetcher

# Các nguồn RSS chuyên sâu cho Trung Đông & Năng lượng
RSS_GEOPOLITICS = [
    {"name": "Al Jazeera Middle East", "url": "https://www.aljazeera.com/xml/rss/middle-east.xml"},
    {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best"},
    {"name": "Google News Geopolitics", "url": GOOGLE_NEWS_FEEDS["geopolitics"]},
]

# Keywords liên quan đến Iran, Hormuz và Dầu khí
KEYWORDS_OSINT = {
    "iran_israel": ["iran", "israel", "tehran", "tel aviv", "beirut", "hezbollah", "lebanon", "yemen", "houthis"],
    "military": ["missile", "tên lửa", "attack", "tấn công", "strike", "không kích", "drone", "bombardment", "war", "chiến tranh", "military", "quân sự"],
    "shipping_choke": ["hormuz", "strait", "eo biển", "gulf", "red sea", "biển đỏ", "blockade", "cấm vận", "tanker", "tàu dầu", "shipping"],
    "energy": ["brent", "wti", "crude", "oil", "dầu thô", "dầu brent", "refinery", "nhà máy lọc dầu", "supply disruption"]
}

class MiroFishAnalyzer:
    def __init__(self):
        self._session = None
        self.fetcher = MarketDataFetcher()

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
        await self.fetcher.close()

    async def _translate_text(self, text: str) -> str:
        """Dịch tiêu đề sang tiếng Việt"""
        if not text:
            return ""
        session = await self._get_session()
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=vi&dt=t&q={aiohttp.helpers.quote(text)}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return "".join(item[0] for item in data[0] if item[0])
                return text
        except Exception:
            return text

    async def _fetch_rss(self, url: str) -> list:
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    parsed = feedparser.parse(content)
                    return parsed.entries[:10]
                return []
        except Exception:
            return []

    async def _fetch_commodity_prices(self) -> dict:
        """Fetch giá trị thực tế của Gold, Oil, DXY từ Yahoo Finance"""
        session = await self._get_session()
        result = {}
        # Các ticker cần quét
        symbols_to_fetch = {
            "Gold": YAHOO_SYMBOLS["gold_xau"],
            "Oil WTI": YAHOO_SYMBOLS["oil_wti"],
            "DXY": YAHOO_SYMBOLS["dxy_usd_index"]
        }
        
        for name, symbol in symbols_to_fetch.items():
            try:
                await asyncio.sleep(1.5)  # Tránh rate limiting (1.5s delay)
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        chart = data.get("chart", {}).get("result", [{}])[0]
                        meta = chart.get("meta", {})
                        price = meta.get("regularMarketPrice", 0)
                        prev = meta.get("previousClose", 0) or meta.get("chartPreviousClose", 0)
                        change_pct = ((price - prev) / prev * 100) if prev else 0
                        result[name] = {
                            "price": price,
                            "change_pct": change_pct,
                            "change": price - prev
                        }
            except Exception:
                result[name] = {"price": 0, "change_pct": 0, "change": 0}
        return result

    async def analyze_geopolitics(self) -> dict:
        """OSINT quét tin tức và tính toán điểm số địa chính trị"""
        all_entries = []
        # Chạy fetch song song
        tasks = [self._fetch_rss(feed["url"]) for feed in RSS_GEOPOLITICS]
        results = await asyncio.gather(*tasks)
        
        for feed_info, entries in zip(RSS_GEOPOLITICS, results):
            for entry in entries:
                all_entries.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "source": feed_info["name"]
                })

        # Quét keyword và phân tích
        critical_news = []
        matches_count = {k: 0 for k in KEYWORDS_OSINT.keys()}
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=6) # Lọc tin trong 6 giờ gần nhất

        for item in all_entries:
            text = f"{item['title']} {item['summary']}".lower()
            
            # Đếm số lượng keywords khớp
            matched_categories = []
            for category, keywords in KEYWORDS_OSINT.items():
                category_matches = sum(1 for kw in keywords if kw in text)
                if category_matches > 0:
                    matches_count[category] += category_matches
                    matched_categories.append(category)
            
            # Nếu tin này chứa ít nhất 2 nhóm từ khóa quan trọng (ví dụ: Iran + Tên lửa, hoặc Hormuz + Tàu dầu)
            if len(matched_categories) >= 2:
                critical_news.append(item)

        # Trả về kết quả phân tích OSINT
        return {
            "critical_news": critical_news[:5], # Lấy top 5 tin cực kỳ quan trọng
            "matches_count": matches_count
        }

    async def run_mirofish_analysis(self) -> str:
        """Tích hợp OSINT + Phân tích giá cả để tính toán MiroFish Index"""
        print("🚀 Đang chạy hệ thống phân tích MiroFish...")
        
        # 1. Fetch dữ liệu song song
        prices_task = self._fetch_commodity_prices()
        geo_task = self.analyze_geopolitics()
        
        prices, geo = await asyncio.gather(prices_task, geo_task)
        
        # 2. Tính toán MiroFish Index (0–100)
        index_score = 0
        reasons = []
        
        # A. Điểm số từ Tin tức OSINT (Max 35 điểm)
        news_score = 0
        critical_count = len(geo["critical_news"])
        news_score += min(15, critical_count * 5) # 5 điểm cho mỗi tin tức cực kỳ nguy hiểm
        
        # Điểm trọng số theo từ khóa nóng
        total_keywords_matched = sum(geo["matches_count"].values())
        news_score += min(20, total_keywords_matched * 0.5)
        
        index_score += news_score
        reasons.append(f"OSINT Geopolitical Score: {news_score:.1f}/35")
        
        # B. Điểm số từ Giá Dầu WTI (Max 25 điểm)
        oil_change = prices.get("Oil WTI", {}).get("change_pct", 0)
        oil_score = 0
        if oil_change > 0:
            oil_score = min(25, oil_change * 10) # Mỗi 1% tăng = 10 điểm
            index_score += oil_score
        reasons.append(f"Oil Price Volatility Score: {oil_score:.1f}/25")

        # C. Điểm số từ Giá Vàng XAU (Max 25 điểm)
        gold_change = prices.get("Gold", {}).get("change_pct", 0)
        gold_score = 0
        if gold_change > 0:
            gold_score = min(25, gold_change * 12) # Mỗi 1% tăng = 12 điểm
            index_score += gold_score
        reasons.append(f"Gold Price Volatility Score: {gold_score:.1f}/25")

        # D. Điểm số tương quan vĩ mô (Max 15 điểm)
        dxy_change = prices.get("DXY", {}).get("change_pct", 0)
        macro_score = 0
        # Nếu DXY và Gold cùng tăng (bất thường, chỉ xảy ra trong khủng hoảng cực đại)
        if dxy_change > 0.1 and gold_change > 0.2:
            macro_score = 15
            index_score += macro_score
            reasons.append("🔥 Cảnh báo: DXY và Gold ĐỒNG THỜI tăng (Risk-OFF tối thượng)")
        elif dxy_change > 0:
            macro_score = 5
            index_score += macro_score
            reasons.append("USD Index tăng tạo áp lực tỷ giá")
            
        index_score = min(100, index_score)
        
        # 3. Phân cấp mức độ rủi ro (MiroFish Risk Level)
        if index_score >= 75:
            risk_level = "🔴 CỰC ĐOAN (CRITICAL SHOCK)"
            action_plan = (
                "🚨 **KHỦNG HOẢNG NĂNG LƯỢNG & ĐỊA CHÍNH TRỊ**\n"
                "• **XAU/USD:** Tuyệt đối không SHORT cản tàu. Ưu tiên LONG theo cụm EMA34/89 trên khung M15/H1. Đặt mục tiêu TP xa hơn thông thường.\n"
                "• **Dầu WTI:** Lực mua gom bùng nổ do lo ngại nghẽn eo biển Hormuz. Canh LONG theo xu hướng.\n"
                "• **Crypto/Altcoins (ZEN, SUI, JASMY, PEOPLE):** **Hạ 50-70% quy mô lệnh Futures** và nới rộng SL vì có nguy cơ cao xảy ra hiện tượng thanh lý chéo (Margin Call) từ chứng khoán sập."
            )
        elif index_score >= 50:
            risk_level = "🟠 CAO (HIGH GEOPOLITICAL RISK)"
            action_plan = (
                "⚠️ **CĂNG THẲNG LEO THANG**\n"
                "• **XAU/USD:** Ưu tiên canh LONG khi giá test lại dải Dragon hoặc FVG Discount của khung H5.\n"
                "• **Dầu WTI:** Có biến động mạnh, ưu tiên Long thuận xu hướng ngắn hạn.\n"
                "• **Crypto:** Giảm đòn bẩy gợi ý xuống còn 1/2. Hạn chế giữ lệnh qua đêm."
            )
        elif index_score >= 30:
            risk_level = "🟡 TRUNG BÌNH (NEUTRAL-WARY)"
            action_plan = (
                "🔔 **THỊ TRƯỜNG DÈ CHỪNG**\n"
                "• Theo dõi sát các mốc hỗ trợ và kháng cự ngang. Tránh FOMO.\n"
                "• Giao dịch bình thường theo tín hiệu chỉ báo, nhưng thắt chặt SL."
            )
        else:
            risk_level = "🟢 THẤP (NORMAL / RISK-ON)"
            action_plan = (
                "✅ **THỊ TRƯỜNG ỔN ĐỊNH**\n"
                "• Giao dịch hoàn toàn theo bộ quy tắc kỹ thuật tiêu chuẩn của hệ thống VSA x ICT x H5."
            )

        # 4. Format Report
        report_lines = [
            f"{'=' * 60}",
            f"🎣 **HỆ THỐNG PHÂN TÍCH MIROFISH — CORRELATION ENGINE**",
            f"📅 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{'=' * 60}",
            f"\n📊 **CHỈ SỐ MIROFISH INDEX: {index_score:.1f}/100**",
            f"⚠️ Mức độ rủi ro: {risk_level}",
            f"\n🧩 **Yếu tố tác động:**"
        ]
        
        for r in reasons:
            report_lines.append(f"  • {r}")
            
        report_lines.extend([
            f"\n💵 **Giá cả hàng hóa & tương quan:**",
            f"  • Vàng XAU: ${prices.get('Gold', {}).get('price', 0):,.2f} ({prices.get('Gold', {}).get('change_pct', 0):+.2f}%)",
            f"  • Dầu WTI: ${prices.get('Oil WTI', {}).get('price', 0):,.2f} ({prices.get('Oil WTI', {}).get('change_pct', 0):+.2f}%)",
            f"  • Chỉ số DXY: {prices.get('DXY', {}).get('price', 0):.2f} ({prices.get('DXY', {}).get('change_pct', 0):+.2f}%)",
        ])
        
        if geo["critical_news"]:
            report_lines.append(f"\n📰 **Tin tức OSINT trọng điểm (Đã dịch tự động):**")
            for idx, item in enumerate(geo["critical_news"], 1):
                translated_title = await self._translate_text(item["title"])
                report_lines.append(f"  {idx}. {translated_title} ({item['source']})")
        else:
            report_lines.append(f"\n📰 **Tin tức OSINT:** Không phát hiện tin tức từ khóa đặc biệt nguy hiểm.")
            
        report_lines.extend([
            f"\n🎯 **KHUYẾN NGHỊ HÀNH ĐỘNG CHO ANH CƯỜNG:**",
            action_plan,
            f"{'=' * 60}"
        ])
        
        return "\n".join(report_lines)

async def main():
    analyzer = MiroFishAnalyzer()
    try:
        report = await analyzer.run_mirofish_analysis()
        print(report)
        
        # Save to scratch folder for history
        os.makedirs("scratch", exist_ok=True)
        filename = f"scratch/mirofish_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✅ Đã lưu báo cáo MiroFish tại: {filename}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await analyzer.close()

if __name__ == "__main__":
    asyncio.run(main())
