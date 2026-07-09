"""
News Sources & API Endpoints — Nhịp Đập Thị Trường
Cấu hình nguồn tin RSS, API endpoints, và keywords phân loại
"""

# ═══════════════════════════════════════
# RSS FEEDS — TIN TỨC VĨ MÔ / VI MÔ
# ═══════════════════════════════════════

MACRO_MICRO_FEEDS = {
    "international": [
        {
            "name": "Reuters Business",
            "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
            "lang": "en",
            "category": "macro",
        },
        {
            "name": "CNBC Top News",
            "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
            "lang": "en",
            "category": "macro",
        },
        {
            "name": "MarketWatch Top Stories",
            "url": "http://feeds.marketwatch.com/marketwatch/topstories/",
            "lang": "en",
            "category": "macro",
        },
        {
            "name": "Yahoo Finance",
            "url": "https://finance.yahoo.com/news/rssindex",
            "lang": "en",
            "category": "macro",
        },
        {
            "name": "Investing.com News",
            "url": "https://www.investing.com/rss/news.rss",
            "lang": "en",
            "category": "macro",
        },
    ],
    "vietnam": [
        {
            "name": "CafeF",
            "url": "https://cafef.vn/rss/trang-chu.rss",
            "lang": "vi",
            "category": "macro",
        },
        {
            "name": "VnExpress Kinh Doanh",
            "url": "https://vnexpress.net/rss/kinh-doanh.rss",
            "lang": "vi",
            "category": "macro",
        },
        {
            "name": "VnExpress Thế Giới",
            "url": "https://vnexpress.net/rss/the-gioi.rss",
            "lang": "vi",
            "category": "geopolitics",
        },
        {
            "name": "CafeF Vĩ Mô",
            "url": "https://cafef.vn/rss/vi-mo-dau-tu.rss",
            "lang": "vi",
            "category": "macro",
        },
    ],
}

# ═══════════════════════════════════════
# RSS FEEDS — CHÍNH TRỊ / QUÂN SỰ
# ═══════════════════════════════════════

GEOPOLITICS_FEEDS = [
    {
        "name": "Reuters World",
        "url": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best",
        "lang": "en",
    },
    {
        "name": "BBC News World",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "lang": "en",
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "lang": "en",
    },
    {
        "name": "AP News",
        "url": "https://rsshub.app/apnews/topics/world-news",
        "lang": "en",
    },
]

# ═══════════════════════════════════════
# KEYWORDS — PHÂN LOẠI TIN TỨC
# ═══════════════════════════════════════

MACRO_KEYWORDS = [
    # Chính sách tiền tệ
    "fed", "interest rate", "lãi suất", "rate cut", "rate hike", "fomc",
    "monetary policy", "chính sách tiền tệ", "ecb", "boj", "pboc",
    # Kinh tế vĩ mô
    "gdp", "cpi", "inflation", "lạm phát", "unemployment", "thất nghiệp",
    "pmi", "nonfarm", "trade war", "thương mại", "tariff", "thuế quan",
    "recession", "suy thoái", "stimulus", "kích thích",
    # Tài chính
    "treasury", "bond", "trái phiếu", "yield", "lợi suất",
    "dollar", "usd", "dxy", "forex",
    # Hàng hóa
    "oil", "dầu", "gold", "vàng", "commodity", "hàng hóa",
    # Chứng khoán
    "s&p", "nasdaq", "dow jones", "vn-index", "vnindex", "chứng khoán",
    "stock market", "bull market", "bear market",
    # Crypto
    "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain",
    "sec", "etf", "binance", "coinbase",
    # Việt Nam
    "nhnn", "ngân hàng nhà nước", "sở giao dịch", "hose", "hnx",
]

GEOPOLITICS_KEYWORDS = [
    # Quân sự
    "war", "chiến tranh", "military", "quân sự", "missile", "tên lửa",
    "nuclear", "hạt nhân", "nato", "invasion", "xâm lược",
    "troops", "army", "navy", "air force", "drone",
    # Địa chính trị
    "sanctions", "trừng phạt", "embargo", "cấm vận",
    "conflict", "xung đột", "tension", "căng thẳng",
    "geopolitical", "địa chính trị", "diplomatic", "ngoại giao",
    # Khu vực nóng
    "ukraine", "russia", "taiwan", "đài loan", "china", "trung quốc",
    "iran", "israel", "gaza", "palestine", "north korea", "triều tiên",
    "south china sea", "biển đông", "middle east", "trung đông",
    "hormuz", "strait of hormuz", "eo biển hormuz", "eo biển",
    "brent", "crude", "crude oil", "dầu brent", "dầu thô", "brent oil",
    # Chính trị
    "election", "bầu cử", "coup", "đảo chính",
    "protest", "biểu tình", "summit", "hội nghị",
]

# ═══════════════════════════════════════
# API ENDPOINTS — DỮ LIỆU TÀI CHÍNH
# ═══════════════════════════════════════

# CoinGecko (free, no API key needed, 10-30 req/min)
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_ENDPOINTS = {
    "global": f"{COINGECKO_BASE}/global",
    "btc_price": f"{COINGECKO_BASE}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_market_cap=true",
    "eth_price": f"{COINGECKO_BASE}/simple/price?ids=ethereum&vs_currencies=usd&include_24hr_change=true",
    "trending": f"{COINGECKO_BASE}/search/trending",
}

# Yahoo Finance (free via query endpoints)
YAHOO_FINANCE_QUOTES = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_SYMBOLS = {
    "s_and_p_500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow_jones": "^DJI",
    "dxy_usd_index": "DX-Y.NYB",
    "gold_xau": "GC=F",
    "oil_wti": "CL=F",
    "us_10y_treasury": "^TNX",
    "nikkei_225": "^N225",
    "hang_seng": "^HSI",
}

# Google News RSS feeds with search filters
GOOGLE_NEWS_FEEDS = {
    "macro": "https://news.google.com/rss/search?q=FED+OR+inflation+OR+PMI+OR+monetary+when:4h&hl=en-US&gl=US&ceid=US:en",
    "geopolitics": "https://news.google.com/rss/search?q=war+OR+conflict+OR+military+OR+sanctions+when:4h&hl=en-US&gl=US&ceid=US:en",
    "vietnam": "https://news.google.com/rss/search?q=l%C3%A3i+su%E1%BA%A5t+OR+l%E1%BA%B1m+ph%C3%A1t+OR+t%E1%BB%B7+gi%C3%A1+when:4h&hl=vi&gl=VN&ceid=VN:vi",
}

# Coinglass (public endpoints — may be rate limited)
COINGLASS_BASE = "https://open-api.coinglass.com/public/v2"
COINGLASS_ENDPOINTS = {
    "liquidation_map": f"{COINGLASS_BASE}/liquidation_map?symbol=BTC&range=12h",
    "liquidation_info": f"{COINGLASS_BASE}/liquidation_info?symbol=BTC&time_type=2",
    "long_short_ratio": f"{COINGLASS_BASE}/long_short_ratio?symbol=BTC&time_type=2",
    "funding_rates": f"{COINGLASS_BASE}/funding_rate?symbol=BTC",
}

# Fallback: Coinglass web scraping selectors
COINGLASS_WEB = {
    "liquidation_map_url": "https://www.coinglass.com/vi/LiquidationData",
    "liquidation_chart_url": "https://www.coinglass.com/vi/pro/futures/LiquidationMap",
}

# ═══════════════════════════════════════
# FORMAT — CẤU HÌNH HIỂN THỊ
# ═══════════════════════════════════════

MAX_NEWS_PER_SECTION = 5          # Tối đa 5 tin mỗi mục
MAX_GEOPOLITICS_NEWS = 4          # Tối đa 4 tin chính trị
NEWS_MAX_AGE_HOURS = 2            # Chỉ lấy tin trong 2 giờ gần nhất
TELEGRAM_MAX_MESSAGE_LENGTH = 4096  # Giới hạn Telegram
