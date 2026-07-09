import os
import urllib.parse
import html as html_lib
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import feedparser

from news_sources import (
    MACRO_MICRO_FEEDS,
    GEOPOLITICS_FEEDS,
    GOOGLE_NEWS_FEEDS,
    MACRO_KEYWORDS,
    GEOPOLITICS_KEYWORDS,
    COINGECKO_ENDPOINTS,
    YAHOO_FINANCE_QUOTES,
    YAHOO_SYMBOLS,
    COINGLASS_BASE,
    MAX_NEWS_PER_SECTION,
    MAX_GEOPOLITICS_NEWS,
    NEWS_MAX_AGE_HOURS,
    TELEGRAM_MAX_MESSAGE_LENGTH,
)

logger = logging.getLogger(__name__)

# Timeout cho mỗi HTTP request
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

# User-Agent giả lập trình duyệt
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _esc(text: str) -> str:
    """Escape HTML entities cho Telegram"""
    return html_lib.escape(str(text)) if text else ""


class MarketPulse:
    """Tạo bản tin 'Nhịp Đập Thị Trường' mỗi giờ chẵn"""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self.coinglass_api_key = os.getenv("COINGLASS_API_KEY")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=REQUEST_TIMEOUT,
                headers=HEADERS,
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _translate_text(self, text: str, target_lang: str = "vi") -> str:
        """Dịch text sang tiếng Việt bằng Google Translate API miễn phí"""
        if not text:
            return ""
        session = await self._get_session()
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    translated = "".join(item[0] for item in data[0] if item[0])
                    return translated
                return text
        except Exception as e:
            logger.debug(f"Translation failed: {e}")
            return text

    # ═══════════════════════════════════════════════════════════
    # PUBLIC — Tạo bản tin
    # ═══════════════════════════════════════════════════════════

    async def generate_pulse(self) -> list[str]:
        """
        Tạo bản tin Nhịp Đập Thị Trường.
        Trả về list các message (vì Telegram giới hạn 4096 chars).
        """
        now = datetime.now()
        # Giờ chẵn tiếp theo
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        next_hour_str = next_hour.strftime("%H:00")
        date_str = now.strftime("%H:%M — %d/%m/%Y")

        # Fetch song song tất cả dữ liệu
        results = await asyncio.gather(
            self._fetch_macro_micro_news(),
            self._fetch_geopolitical_news(),
            self._fetch_global_money_flow(),
            self._fetch_btc_liquidation(),
            return_exceptions=True,
        )

        macro_news = results[0] if not isinstance(results[0], Exception) else []
        geo_news = results[1] if not isinstance(results[1], Exception) else []
        money_flow = results[2] if not isinstance(results[2], Exception) else {}
        btc_liq = results[3] if not isinstance(results[3], Exception) else {}

        # Log lỗi nếu có
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                section_names = ["Tin vĩ mô", "Chính trị", "Dòng tiền", "Thanh lý BTC"]
                logger.error(f"❌ Lỗi fetch {section_names[i]}: {r}")

        # Build message sections
        messages = []

        # ── Header ──
        header = (
            f"{'━' * 30}\n"
            f"🫀 <b>NHỊP ĐẬP THỊ TRƯỜNG</b>\n"
            f"🕐 {date_str}\n"
            f"{'━' * 30}"
        )

        # ── Phần 1: Tin vĩ mô / vi mô ──
        section1 = self._format_macro_news(macro_news)

        # ── Phần 2: Chính trị / quân sự ──
        section2 = self._format_geo_news(geo_news)

        # ── Phần 3: Dòng tiền toàn cầu ──
        section3 = self._format_money_flow(money_flow)

        # ── Phần 4: Thanh lý BTC ──
        section4 = self._format_btc_liquidation(btc_liq)

        # ── Footer ──
        footer = (
            f"{'━' * 30}\n"
            f"🫀 <i>Nhịp đập thị trường — Cập nhật mỗi giờ</i>\n"
            f"📍 <i>Bản tin tiếp theo: {next_hour_str}</i>\n"
            f"{'━' * 30}"
        )

        # Ghép thành tin nhắn, chia nếu quá dài
        full_message = "\n\n".join([header, section1, section2, section3, section4, footer])

        if len(full_message) <= TELEGRAM_MAX_MESSAGE_LENGTH:
            messages.append(full_message)
        else:
            # Chia thành 2 tin nhắn: (header + tin tức) và (dòng tiền + thanh lý)
            msg1 = "\n\n".join([header, section1, section2])
            msg2_header = (
                f"{'━' * 30}\n"
                f"🫀 <b>NHỊP ĐẬP THỊ TRƯỜNG (tt.)</b>\n"
                f"{'━' * 30}"
            )
            msg2 = "\n\n".join([msg2_header, section3, section4, footer])

            # Nếu msg1 vẫn quá dài, cắt thêm
            if len(msg1) > TELEGRAM_MAX_MESSAGE_LENGTH:
                messages.append("\n\n".join([header, section1]))
                messages.append("\n\n".join([
                    f"{'━' * 30}\n🌐 <b>TT. NHỊP ĐẬP</b>\n{'━' * 30}",
                    section2
                ]))
            else:
                messages.append(msg1)

            if len(msg2) > TELEGRAM_MAX_MESSAGE_LENGTH:
                messages.append("\n\n".join([msg2_header, section3]))
                messages.append("\n\n".join([
                    f"{'━' * 30}\n📊 <b>TT. NHỊP ĐẬP</b>\n{'━' * 30}",
                    section4, footer
                ]))
            else:
                messages.append(msg2)

        return messages

    # ═══════════════════════════════════════════════════════════
    # FETCH — Tin vĩ mô / vi mô
    # ═══════════════════════════════════════════════════════════

    async def _fetch_macro_micro_news(self) -> list[dict]:
        """Fetch tin tức vĩ mô & vi mô từ RSS feeds và Google News"""
        all_news = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_MAX_AGE_HOURS)

        # Cấu hình feeds tĩnh truyền thống
        feeds_to_fetch = (
            MACRO_MICRO_FEEDS.get("international", [])
            + MACRO_MICRO_FEEDS.get("vietnam", [])
        )

        # Thêm feeds động từ Google News RSS
        google_news_intl = {
            "name": "Google News Int",
            "url": GOOGLE_NEWS_FEEDS["macro"],
            "lang": "en",
            "category": "macro"
        }
        google_news_vn = {
            "name": "Google News VN",
            "url": GOOGLE_NEWS_FEEDS["vietnam"],
            "lang": "vi",
            "category": "macro"
        }
        feeds_to_fetch.extend([google_news_intl, google_news_vn])

        tasks = [self._fetch_rss_feed(feed) for feed in feeds_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for feed_info, result in zip(feeds_to_fetch, results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Lỗi RSS {feed_info['name']}: {result}")
                continue
            for entry in result:
                # Lọc theo thời gian (Google News có pubDate rất mới)
                pub_date = entry.get("published_parsed")
                if pub_date:
                    try:
                        pub_dt = datetime(*pub_date[:6], tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue
                    except (TypeError, ValueError):
                        pass

                # Tính điểm relevance dựa trên keywords
                title = entry.get("title", "").lower()
                summary = entry.get("summary", "").lower()
                text = f"{title} {summary}"

                score = sum(1 for kw in MACRO_KEYWORDS if kw in text)
                
                # Google News RSS cho vĩ mô thì mặc định có điểm tối thiểu
                if "Google News" in feed_info["name"]:
                    score += 1

                if score > 0:
                    all_news.append({
                        "title": entry.get("title", "N/A"),
                        "link": entry.get("link", ""),
                        "source": entry.get("source", {}).get("name") if isinstance(entry.get("source"), dict) else feed_info["name"],
                        "lang": feed_info["lang"],
                        "score": score,
                        "category": "macro",
                    })

        # Sắp xếp theo điểm, lấy top
        all_news.sort(key=lambda x: x["score"], reverse=True)

        # Tách quốc tế và Việt Nam
        intl_raw = [n for n in all_news if n["lang"] == "en"][:MAX_NEWS_PER_SECTION]
        vn_raw = [n for n in all_news if n["lang"] == "vi"][:MAX_NEWS_PER_SECTION]

        # Dịch song song tin quốc tế sang tiếng Việt để tối ưu tốc độ
        async def translate_item(item):
            # Cắt bỏ tên nguồn ở cuối (ví dụ " - Reuters") trước khi dịch nếu có
            raw_title = item["title"]
            source_suffix_match = re.search(r'\s+-\s+[^-]+$', raw_title)
            if source_suffix_match:
                title_to_translate = raw_title[:source_suffix_match.start()]
                source_name = raw_title[source_suffix_match.end():]
            else:
                title_to_translate = raw_title
                source_name = ""

            translated = await self._translate_text(title_to_translate)
            item["title"] = translated
            return item

        import re
        translation_tasks = [translate_item(n) for n in intl_raw]
        intl_translated = await asyncio.gather(*translation_tasks)

        return intl_translated + vn_raw

    async def _fetch_rss_feed(self, feed_info: dict) -> list[dict]:
        """Fetch và parse một RSS feed"""
        session = await self._get_session()
        try:
            async with session.get(feed_info["url"]) as resp:
                if resp.status != 200:
                    return []
                content = await resp.text()
                parsed = feedparser.parse(content)
                return parsed.entries[:15]  # Max 15 entries mỗi feed
        except Exception as e:
            logger.debug(f"RSS fetch error {feed_info['name']}: {e}")
            return []

    # ═══════════════════════════════════════════════════════════
    # FETCH — Chính trị / Quân sự
    # ═══════════════════════════════════════════════════════════

    async def _fetch_geopolitical_news(self) -> list[dict]:
        """Fetch tin chính trị & quân sự và dịch sang tiếng Việt"""
        all_news = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_MAX_AGE_HOURS)

        # Cấu hình feeds tĩnh truyền thống
        feeds_to_fetch = list(GEOPOLITICS_FEEDS)

        # Thêm feeds động từ Google News RSS
        google_news_geo = {
            "name": "Google News Geo",
            "url": GOOGLE_NEWS_FEEDS["geopolitics"],
            "lang": "en"
        }
        feeds_to_fetch.append(google_news_geo)

        tasks = [self._fetch_rss_feed(feed) for feed in feeds_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for feed_info, result in zip(feeds_to_fetch, results):
            if isinstance(result, Exception):
                continue
            for entry in result:
                pub_date = entry.get("published_parsed")
                if pub_date:
                    try:
                        pub_dt = datetime(*pub_date[:6], tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue
                    except (TypeError, ValueError):
                        pass

                title = entry.get("title", "").lower()
                summary = entry.get("summary", "").lower()
                text = f"{title} {summary}"

                score = sum(1 for kw in GEOPOLITICS_KEYWORDS if kw in text)
                
                if "Google News" in feed_info["name"]:
                    score += 1

                if score > 0:
                    all_news.append({
                        "title": entry.get("title", "N/A"),
                        "link": entry.get("link", ""),
                        "source": entry.get("source", {}).get("name") if isinstance(entry.get("source"), dict) else feed_info["name"],
                        "score": score,
                    })

        all_news.sort(key=lambda x: x["score"], reverse=True)
        top_news = all_news[:MAX_GEOPOLITICS_NEWS]

        # Dịch toàn bộ tin chính trị sang tiếng Việt
        import re
        async def translate_geo(item):
            raw_title = item["title"]
            source_suffix_match = re.search(r'\s+-\s+[^-]+$', raw_title)
            if source_suffix_match:
                title_to_translate = raw_title[:source_suffix_match.start()]
            else:
                title_to_translate = raw_title
            
            translated = await self._translate_text(title_to_translate)
            item["title"] = translated
            return item

        geo_translation_tasks = [translate_geo(n) for n in top_news]
        top_news_translated = await asyncio.gather(*geo_translation_tasks)

        return top_news_translated

    # ═══════════════════════════════════════════════════════════
    # FETCH — Dòng tiền toàn cầu
    # ═══════════════════════════════════════════════════════════

    async def _fetch_global_money_flow(self) -> dict:
        """Fetch dữ liệu dòng tiền: vàng, CK, crypto, DXY..."""
        data = {}

        # Fetch song song: Yahoo Finance + CoinGecko
        yahoo_task = self._fetch_yahoo_quotes()
        coingecko_task = self._fetch_coingecko_data()

        yahoo_data, gecko_data = await asyncio.gather(
            yahoo_task, coingecko_task, return_exceptions=True
        )

        if not isinstance(yahoo_data, Exception):
            data["yahoo"] = yahoo_data
        else:
            logger.error(f"❌ Yahoo Finance error: {yahoo_data}")
            data["yahoo"] = {}

        if not isinstance(gecko_data, Exception):
            data["crypto"] = gecko_data
        else:
            logger.error(f"❌ CoinGecko error: {gecko_data}")
            data["crypto"] = {}

        # Phân tích dòng tiền
        data["analysis"] = self._analyze_money_flow(data)

        return data

    async def _fetch_yahoo_quotes(self) -> dict:
        """Fetch giá từ Yahoo Finance (bỏ qua v7 và gọi trực tiếp v8 fallback)"""
        return await self._fetch_yahoo_fallback()

    async def _fetch_yahoo_fallback(self) -> dict:
        """Fallback: Fetch Yahoo Finance qua v8 API với delay tránh 429"""
        session = await self._get_session()
        result = {}

        for name, symbol in YAHOO_SYMBOLS.items():
            try:
                # Add delay to avoid rate limiting (429)
                await asyncio.sleep(1.2)
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(f"Yahoo fallback status {resp.status} for {symbol}")
                        continue
                    data = await resp.json()
                    chart = data.get("chart", {}).get("result", [{}])[0]
                    meta = chart.get("meta", {})
                    price = meta.get("regularMarketPrice", 0)
                    prev = meta.get("previousClose", 0) or meta.get("chartPreviousClose", 0)
                    change_pct = ((price - prev) / prev * 100) if prev else 0

                    result[YAHOO_SYMBOLS[name]] = {
                        "price": price,
                        "change_pct": change_pct,
                        "change": price - prev,
                        "name": name,
                    }
            except Exception as e:
                logger.warning(f"Yahoo fallback error for {symbol}: {e}")
                continue

        return result

    async def _fetch_coingecko_data(self) -> dict:
        """Fetch dữ liệu crypto từ CoinGecko"""
        session = await self._get_session()
        result = {}

        # Global data
        try:
            async with session.get(COINGECKO_ENDPOINTS["global"]) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    gdata = data.get("data", {})
                    result["total_market_cap"] = gdata.get("total_market_cap", {}).get("usd", 0)
                    result["total_volume"] = gdata.get("total_volume", {}).get("usd", 0)
                    result["btc_dominance"] = gdata.get("market_cap_percentage", {}).get("btc", 0)
                    result["eth_dominance"] = gdata.get("market_cap_percentage", {}).get("eth", 0)
                    result["market_cap_change_24h"] = gdata.get("market_cap_change_percentage_24h_usd", 0)
        except Exception as e:
            logger.warning(f"CoinGecko global error: {e}")

        # BTC price
        try:
            async with session.get(COINGECKO_ENDPOINTS["btc_price"]) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    btc = data.get("bitcoin", {})
                    result["btc_price"] = btc.get("usd", 0)
                    result["btc_change_24h"] = btc.get("usd_24h_change", 0)
                    result["btc_market_cap"] = btc.get("usd_market_cap", 0)
        except Exception as e:
            logger.warning(f"CoinGecko BTC error: {e}")

        # ETH price
        try:
            async with session.get(COINGECKO_ENDPOINTS["eth_price"]) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    eth = data.get("ethereum", {})
                    result["eth_price"] = eth.get("usd", 0)
                    result["eth_change_24h"] = eth.get("usd_24h_change", 0)
        except Exception as e:
            logger.warning(f"CoinGecko ETH error: {e}")

        return result

    # ═══════════════════════════════════════════════════════════
    # FETCH — Vùng thanh lý BTC (Coinglass & Binance Depth)
    # ═══════════════════════════════════════════════════════════

    async def _fetch_binance_depth_clusters(self) -> dict:
        """Quét Binance Futures depth để tìm tường mua/bán (limit=1000)"""
        session = await self._get_session()
        result = {"bids": [], "asks": []}
        try:
            # 1. Lấy giá hiện tại
            url_ticker = "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT"
            async with session.get(url_ticker) as resp:
                if resp.status != 200:
                    return result
                ticker_data = await resp.json()
                current_price = float(ticker_data.get("lastPrice", 0))
                if current_price <= 0:
                    return result
                result["btc_price"] = current_price

            # 2. Lấy order book depth
            url_depth = "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=1000"
            async with session.get(url_depth) as resp:
                if resp.status != 200:
                    return result
                depth_data = await resp.json()
                bids = depth_data.get("bids", [])
                asks = depth_data.get("asks", [])

                # Gom nhóm bids/asks vào các vùng $100
                bid_buckets = {}
                ask_buckets = {}

                for price_str, qty_str in bids:
                    price = float(price_str)
                    qty = float(qty_str)
                    val_usd = price * qty
                    
                    # Chỉ lấy bids bên dưới giá hiện tại
                    if price < current_price:
                        bucket = int(price // 100) * 100
                        bid_buckets[bucket] = bid_buckets.get(bucket, 0) + val_usd

                for price_str, qty_str in asks:
                    price = float(price_str)
                    qty = float(qty_str)
                    val_usd = price * qty
                    
                    # Chỉ lấy asks bên trên giá hiện tại
                    if price > current_price:
                        bucket = int(price // 100) * 100
                        ask_buckets[bucket] = ask_buckets.get(bucket, 0) + val_usd

                # Sắp xếp và lấy top 3 vùng lớn nhất
                sorted_bids = sorted(bid_buckets.items(), key=lambda x: x[1], reverse=True)[:3]
                sorted_asks = sorted(ask_buckets.items(), key=lambda x: x[1], reverse=True)[:3]

                # Sắp xếp lại theo giá để hiển thị tăng dần cho bids và giảm dần cho asks
                result["bids"] = sorted(sorted_bids, key=lambda x: x[0], reverse=True)
                result["asks"] = sorted(sorted_asks, key=lambda x: x[0])
        except Exception as e:
            logger.warning(f"Error fetching Binance depth: {e}")
        return result

    async def _fetch_btc_liquidation(self) -> dict:
        """Fetch dữ liệu thanh lý BTC từ Coinglass (nếu có key) và Binance Futures depth"""
        session = await self._get_session()
        result = {}

        # 1. Thử Coinglass V4 API (nếu có API Key)
        if self.coinglass_api_key:
            try:
                url = "https://open-api-v4.coinglass.com/api/futures/liquidation/exchange-list?symbol=BTC"
                headers = {
                    "CG-API-KEY": self.coinglass_api_key,
                    "accept": "application/json"
                }
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == "0" and data.get("data"):
                            total_long = 0
                            total_short = 0
                            total_all = 0
                            for item in data["data"]:
                                total_long += item.get("longVolUsd", 0)
                                total_short += item.get("shortVolUsd", 0)
                                total_all += item.get("totalVolUsd", 0)
                            
                            result["total_liq_24h"] = total_all
                            result["long_liq_24h"] = total_long
                            result["short_liq_24h"] = total_short
                            result["source"] = "coinglass_api"
            except Exception as e:
                logger.warning(f"Coinglass V4 API error: {e}")

        # 2. Quét order book depth của Binance Futures để tìm các tường lệnh lớn
        depth_data = await self._fetch_binance_depth_clusters()
        result.update(depth_data)

        # 3. Lấy thêm các thông số Binance: OI, L/S Ratio, Funding
        try:
            # Lấy OI
            url = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["open_interest"] = float(data.get("openInterest", 0))

            # Lấy Long/Short ratio từ Binance
            url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=1"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        latest = data[0]
                        result["long_ratio"] = float(latest.get("longAccount", 0)) * 100
                        result["short_ratio"] = float(latest.get("shortAccount", 0)) * 100
                        result["long_short_ratio"] = float(latest.get("longShortRatio", 0))

            # Lấy Funding Rate từ Binance
            url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        result["funding_rate"] = float(data[0].get("fundingRate", 0))
        except Exception as e:
            logger.warning(f"Error fetching Binance supplementary metrics: {e}")

        return result

    # ═══════════════════════════════════════════════════════════
    # ANALYZE — Phân tích dòng tiền
    # ═══════════════════════════════════════════════════════════

    def _analyze_money_flow(self, data: dict) -> str:
        """Phân tích dòng tiền đang chảy vào đâu"""
        yahoo = data.get("yahoo", {})
        crypto = data.get("crypto", {})

        inflows = []   # Tài sản có dòng tiền vào
        outflows = []  # Tài sản có dòng tiền ra

        # Kiểm tra từng loại tài sản
        assets = {
            "Vàng": yahoo.get("GC=F", {}).get("change_pct", 0),
            "S&P 500": yahoo.get("^GSPC", {}).get("change_pct", 0),
            "Nasdaq": yahoo.get("^IXIC", {}).get("change_pct", 0),
            "Dow Jones": yahoo.get("^DJI", {}).get("change_pct", 0),
            "Dầu WTI": yahoo.get("CL=F", {}).get("change_pct", 0),
            "USD (DXY)": yahoo.get("DX-Y.NYB", {}).get("change_pct", 0),
        }

        btc_change = crypto.get("btc_change_24h", 0)
        if btc_change:
            assets["Crypto (BTC)"] = btc_change

        for name, change in assets.items():
            if change > 0.3:
                inflows.append((name, change))
            elif change < -0.3:
                outflows.append((name, change))

        inflows.sort(key=lambda x: x[1], reverse=True)
        outflows.sort(key=lambda x: x[1])

        parts = []
        if inflows:
            in_str = ", ".join([f"{n}(+{c:.1f}%)" for n, c in inflows[:3]])
            parts.append(f"Tiền đang chảy VÀO: {in_str}")
        if outflows:
            out_str = ", ".join([f"{n}({c:.1f}%)" for n, c in outflows[:3]])
            parts.append(f"Tiền đang chảy RA: {out_str}")

        if not parts:
            return "Dòng tiền đang phân tán, chưa có xu hướng rõ ràng"

        return " | ".join(parts)

    # ═══════════════════════════════════════════════════════════
    # FORMAT — Định dạng bản tin
    # ═══════════════════════════════════════════════════════════

    def _format_macro_news(self, news: list[dict]) -> str:
        """Format phần tin vĩ mô / vi mô"""
        lines = [f"{'─' * 30}", f"📰 <b>TIN VĨ MÔ & VI MÔ</b>", f"{'─' * 30}"]

        intl = [n for n in news if n.get("lang") == "en"]
        vn = [n for n in news if n.get("lang") == "vi"]

        if intl:
            lines.append("🌍 <b>Quốc tế:</b>")
            for n in intl[:MAX_NEWS_PER_SECTION]:
                title = _esc(n["title"][:100])
                source = _esc(n["source"])
                lines.append(f"• {title} <i>({source})</i>")
        else:
            lines.append("🌍 <i>Chưa có tin quốc tế nổi bật trong 1h qua</i>")

        if vn:
            lines.append(f"\n🇻🇳 <b>Việt Nam:</b>")
            for n in vn[:MAX_NEWS_PER_SECTION]:
                title = _esc(n["title"][:100])
                source = _esc(n["source"])
                lines.append(f"• {title} <i>({source})</i>")
        else:
            lines.append("🇻🇳 <i>Chưa có tin VN nổi bật trong 1h qua</i>")

        return "\n".join(lines)

    def _format_geo_news(self, news: list[dict]) -> str:
        """Format phần chính trị / quân sự"""
        lines = [f"{'─' * 30}", f"🌐 <b>CHÍNH TRỊ & QUÂN SỰ</b>", f"{'─' * 30}"]

        if news:
            for n in news[:MAX_GEOPOLITICS_NEWS]:
                title = _esc(n["title"][:120])
                source = _esc(n["source"])
                lines.append(f"• {title} <i>({source})</i>")
        else:
            lines.append("<i>Không có tin chính trị/quân sự nổi bật trong 1h qua</i>")

        return "\n".join(lines)

    def _format_money_flow(self, data: dict) -> str:
        """Format phần dòng tiền toàn cầu"""
        lines = [f"{'─' * 30}", f"💰 <b>DÒNG TIỀN TOÀN CẦU</b>", f"{'─' * 30}"]

        yahoo = data.get("yahoo", {})
        crypto = data.get("crypto", {})

        # Mapping display
        display_map = [
            ("GC=F", "🥇 Vàng XAU", "$", ","),
            ("^GSPC", "📈 S&P 500", "", ","),
            ("^IXIC", "📊 Nasdaq", "", ","),
            ("^DJI", "📉 Dow Jones", "", ","),
            ("DX-Y.NYB", "💵 DXY (USD)", "", ""),
            ("CL=F", "🛢️ Dầu WTI", "$", ""),
            ("^TNX", "📄 US 10Y", "", "%"),
            ("^N225", "🇯🇵 Nikkei 225", "", ","),
            ("^HSI", "🇭🇰 Hang Seng", "", ","),
        ]

        for symbol, label, prefix, suffix in display_map:
            q = yahoo.get(symbol, {})
            price = q.get("price", 0)
            change = q.get("change_pct", 0)
            if price:
                emoji = "🟢" if change >= 0 else "🔴"
                arrow = "← TIỀN VÀO" if change > 0.5 else ("← TIỀN RA" if change < -0.5 else "")
                if suffix == "%":
                    lines.append(
                        f"{emoji} {label}: {price:.2f}% ({change:+.2f}%) {arrow}"
                    )
                else:
                    lines.append(
                        f"{emoji} {label}: {prefix}{price:,.2f} ({change:+.2f}%) {arrow}"
                    )

        # Crypto
        btc_price = crypto.get("btc_price", 0)
        btc_change = crypto.get("btc_change_24h", 0)
        eth_price = crypto.get("eth_price", 0)
        eth_change = crypto.get("eth_change_24h", 0)
        btc_dom = crypto.get("btc_dominance", 0)
        total_mcap = crypto.get("total_market_cap", 0)

        if btc_price:
            emoji = "🟢" if btc_change >= 0 else "🔴"
            arrow = "← TIỀN VÀO" if btc_change > 1 else ("← TIỀN RA" if btc_change < -1 else "")
            lines.append(f"{emoji} ₿ BTC: ${btc_price:,.0f} ({btc_change:+.1f}%) {arrow}")
        if eth_price:
            emoji = "🟢" if eth_change >= 0 else "🔴"
            lines.append(f"{emoji} Ξ ETH: ${eth_price:,.0f} ({eth_change:+.1f}%)")
        if btc_dom:
            lines.append(f"📊 BTC Dominance: {btc_dom:.1f}%")
        if total_mcap:
            lines.append(f"💎 Tổng Crypto Market: ${total_mcap / 1e12:.2f}T")

        # Phân tích nhận định
        analysis = data.get("analysis", "")
        if analysis:
            lines.append(f"\n💡 <b>Nhận định:</b> {_esc(analysis)}")

        return "\n".join(lines)

    def _format_btc_liquidation(self, data: dict) -> str:
        """Format phần thanh lý BTC"""
        lines = [f"{'─' * 30}", f"📊 <b>VÙNG THANH LÝ BTC</b>", f"{'─' * 30}"]

        price = data.get("btc_price", 0)
        oi = data.get("open_interest", 0)
        fr = data.get("funding_rate", 0)
        long_r = data.get("long_ratio", 0)
        short_r = data.get("short_ratio", 0)
        source = data.get("source", "")

        if price:
            lines.append(f"💰 BTC Price: ${price:,.0f}")
        if oi:
            lines.append(f"📦 Open Interest: {oi:,.2f} BTC")
        if long_r and short_r:
            lines.append(f"📊 Long/Short Ratio: {long_r:.1f}% / {short_r:.1f}%")
            if long_r > 55:
                lines.append("⚠️ <b>Phe Long đông → Cẩn thận Long Squeeze</b>")
            elif short_r > 55:
                lines.append("⚠️ <b>Phe Short đông → Cẩn thận Short Squeeze</b>")

        if source == "coinglass_api":
            total = data.get("total_liq_24h", 0)
            long_liq = data.get("long_liq_24h", 0)
            short_liq = data.get("short_liq_24h", 0)

            if total:
                lines.append(f"\n💥 <b>Tổng thanh lý toàn thị trường (24H):</b>")
                lines.append(f"• 🟢 Long bị thanh lý: ${long_liq / 1e6:,.1f}M USD")
                lines.append(f"• 🔴 Short bị thanh lý: ${short_liq / 1e6:,.1f}M USD")
                if long_liq > short_liq * 1.5:
                    lines.append("👉 <i>Phe Long bị quét mạnh hơn, thị trường đang chịu áp lực giảm.</i>")
                elif short_liq > long_liq * 1.5:
                    lines.append("👉 <i>Phe Short bị quét mạnh hơn, thị trường có lực đẩy lên.</i>")
        else:
            lines.append("\n<i>💡 Để xem tổng tiền thanh lý 24h toàn thị trường, hãy thêm COINGLASS_API_KEY vào .env</i>")

        # Hiển thị tường lệnh Binance Depth
        bids = data.get("bids", [])
        asks = data.get("asks", [])

        if bids:
            lines.append("\n🎯 <b>Tường mua / Cản Long cá mập (MM) chờ sẵn:</b>")
            for idx, (bucket, val) in enumerate(bids):
                label = " (Cản mạnh nhất)" if idx == 0 else ""
                lines.append(f"• Vùng ${bucket:,.0f} - ${bucket+100:,.0f}: ${val/1e6:.1f}M USD{label}")
            lines.append("<i>>>> Nếu giá rơi về các vùng này, Long sẽ bị quét thanh lý mạnh và lệnh được MM hấp thụ.</i>")

        if asks:
            lines.append("\n🎯 <b>Tường bán / Cản Short cá mập (MM) chờ sẵn:</b>")
            for idx, (bucket, val) in enumerate(asks):
                label = " (Cản mạnh nhất)" if idx == 0 else ""
                lines.append(f"• Vùng ${bucket:,.0f} - ${bucket+100:,.0f}: ${val/1e6:.1f}M USD{label}")
            lines.append("<i>>>> Nếu giá pump lên các vùng này, Short sẽ bị ép cắt lỗ/thanh lý hàng loạt.</i>")

        if fr:
            fr_pct = fr * 100
            if fr > 0.01:
                label = "Phe Long trả phí cao → Quá nóng"
            elif fr > 0:
                label = "Phe Long trả phí → Bullish nhẹ"
            elif fr < -0.01:
                label = "Phe Short trả phí cao → Quá bi"
            else:
                label = "Phe Short trả phí → Bearish nhẹ"
            lines.append(f"\n💸 Funding Rate: {fr_pct:.4f}% ({label})")

        return "\n".join(lines)
