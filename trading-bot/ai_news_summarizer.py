import aiohttp
import logging
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

HF_API_URL = 'https://cuongnguyenchi-zalo-bots.hf.space'

PROMPT = """Hãy đọc toàn bộ nội dung của trang web tôi cung cấp. Sau đó, tóm tắt lại theo 3 ý cực kỳ ngắn gọn:
1. Tin tức chính là gì?
2. Ảnh hưởng tích cực (Bull) hay tiêu cực (Bear) đến thị trường?
3. Nhận định chiến lược (Cần làm gì tiếp theo?).
Trình bày rõ ràng, súc tích để tôi dễ dàng đọc hiểu và đưa ra quyết định giao dịch."""

async def fetch_and_clean_html(url: str) -> str:
    """Fetch HTML from URL and clean it to extract main text."""
    try:
        async with aiohttp.ClientSession() as session:
            # Dùng User-Agent cơ bản để chống bị chặn bởi một số trang web
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                
                soup = BeautifulSoup(html, "html.parser")
                
                # Loại bỏ các thẻ không cần thiết
                for script in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
                    script.extract()
                
                text = soup.get_text(separator=' ')
                # Dọn dẹp khoảng trắng
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Giới hạn text (Gemini context window lớn nhưng cũng nên cắt bớt nếu quá dài)
                return text[:20000]
    except Exception as e:
        logger.error(f"Lỗi khi tải URL {url}: {e}")
        return None

async def summarize_news(url: str) -> str:
    """Đọc URL và gửi qua Gemini Proxy để tóm tắt."""
    text = await fetch_and_clean_html(url)
    if not text:
        return f"❌ Không thể truy cập hoặc đọc nội dung từ đường link:\n{url}"
    
    proxy_url = f"{HF_API_URL}/proxy/gemini/v1beta/models/gemini-2.5-flash:generateContent"
    
    body = {
        "system_instruction": {"parts": [{"text": "Bạn là một chuyên gia phân tích tài chính sắc bén, am hiểu thị trường Crypto và Forex."}]},
        "contents": [{"role": "user", "parts": [{"text": f"{PROMPT}\n\nNội dung bài báo:\n{text}"}]}],
        "generationConfig": {"temperature": 0.5}
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(proxy_url, json=body, timeout=30) as response:
                if response.status != 200:
                    err_msg = await response.text()
                    logger.error(f"Lỗi gọi Gemini Proxy: {err_msg}")
                    return f"❌ Lỗi khi phân tích AI (HTTP {response.status})."
                
                data = await response.json()
                if not data.get("candidates") or not data["candidates"][0].get("content"):
                    return "❌ Dữ liệu trả về từ AI bị rỗng."
                
                return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Lỗi kết nối Gemini Proxy: {e}")
        return f"❌ Lỗi kết nối AI: {e}"
