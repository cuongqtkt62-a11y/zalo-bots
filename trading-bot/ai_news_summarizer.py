import httpx
from bs4 import BeautifulSoup
import logging
from config import Config

logger = logging.getLogger(__name__)

class AINewsSummarizer:
    def __init__(self):
        # Tái sử dụng Gemini API Proxy từ cấu hình Zalo (nếu có) hoặc gọi thẳng
        self.api_key = Config.GEMINI_API_KEY
        # Ở Trading Bot, GEMINI_API_KEY được đặt trong config
        # API Proxy của Zalo (Cloudflare Worker)
        self.gemini_proxy_url = "https://gemini-proxy.bichbot.workers.dev/v1beta/models/gemini-2.5-flash:generateContent"

    async def fetch_article_text(self, url: str) -> str:
        """Tải trang web và bóc tách nội dung chữ"""
        try:
            # Giả lập Browser để không bị block
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Xóa các thẻ script, style, header, footer, nav
            for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'iframe', 'noscript']):
                tag.decompose()
                
            # Lấy text
            text = soup.get_text(separator=' ', strip=True)
            # Rút ngắn nếu quá dài (Gemini flash xử lý tốt nhưng tiết kiệm token)
            return text[:15000] 
        except Exception as e:
            logger.error(f"Error fetching article from {url}: {e}")
            return ""

    async def analyze_with_ai(self, content: str) -> str:
        """Gửi content cho AI để phân tích"""
        if not content:
            return "❌ Không thể đọc được nội dung từ đường link này. Trang web có thể yêu cầu đăng nhập hoặc chặn Bot."
            
        system_prompt = """Bạn là một chuyên gia Trading hơn 20 năm kinh nghiệm về thị trường Vàng và Crypto, đồng thời là một nhà phân tích vĩ mô sắc bén. Khi tôi cung cấp dữ liệu, hãy tự động phân loại và xử lý theo 1 trong 2 trường hợp sau:

TRƯỜNG HỢP 1: NẾU TÔI YÊU CẦU PHÂN TÍCH KÈO / BIỂU ĐỒ HOẶC COIN
Hãy phân tích tâm lý Futures (Funding rate, Open Interest) và bối cảnh Smart Money (VSA, FVG, Thanh khoản).
Sau đó cho tôi điểm vào lệnh (Entry), Chốt lời (TP) và Cắt lỗ (SL) chuẩn nhất.

TRƯỜNG HỢP 2: NẾU TÔI CUNG CẤP MỘT BÀI BÁO HOẶC TIN TỨC HOẶC LINK
Hãy đọc toàn bộ nội dung. Sau đó, tóm tắt lại theo 3 ý cực kỳ ngắn gọn:
1. Tin tức chính là gì?
2. Ảnh hưởng tích cực (Bull) hay tiêu cực (Bear) đến thị trường Vàng/Crypto?
3. Nhận định chiến lược (Cần làm gì tiếp theo?).

LUÔN TRÌNH BÀY: Rõ ràng, súc tích, dứt khoát để tôi có thể chốt ngay quyết định giao dịch! Trình bày bằng Markdown, sử dụng emoji phù hợp (🟢 cho Bull/Long, 🔴 cho Bear/Short, ⚠️ cho Cảnh báo)."""

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"Nội dung bài báo:\n\n{content}"}]
                }
            ],
            "systemInstruction": {
                "role": "system",
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 800
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
                resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                resp.raise_for_status()
                data = resp.json()
                
                return data['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"Error analyzing with Gemini: {e}")
            return "❌ Lỗi xử lý AI. Vui lòng thử lại sau."
