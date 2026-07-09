"""
Configuration — VSA × ICT × Sonic R Trading System
Hợp nhất: Sonic R (4 EMA) + SMC (Stop Hunt / FVG) + VSA (Volume)
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # Binance
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

    # Symbols
    SCAN_ALL_SYMBOLS = os.getenv("SCAN_ALL_SYMBOLS", "true").lower() == "true"
    SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "BTC/USDT").split(",")]
    MIN_VOLUME_24H = float(os.getenv("MIN_VOLUME_24H", "10000000"))
    MAX_SYMBOLS_PER_SCAN = int(os.getenv("MAX_SYMBOLS_PER_SCAN", "50"))

    # Timeframes
    TIMEFRAME_ENTRY = os.getenv("TIMEFRAME_ENTRY", "5m")
    TIMEFRAME_CONTEXT = os.getenv("TIMEFRAME_CONTEXT", "4h")
    TIMEFRAME_DAILY = os.getenv("TIMEFRAME_DAILY", "1d")

    # ═══════════════════════════════════════
    # SONIC R — 4 EMA SYSTEM
    # ═══════════════════════════════════════
    DRAGON_PERIOD = 34          # Dragon Band (EMA High/Close/Low 34)
    EMA_TREND = 89              # Trend Line (cam)
    EMA_LONG_TREND = 200        # Long Trend (tím)
    EMA_SUPER_TREND = 610       # Super Trend (trắng)

    # ═══════════════════════════════════════
    # SONIC R DETECTION PARAMETERS
    # ═══════════════════════════════════════
    EMA_SQUEEZE_THRESHOLD_PCT = float(os.getenv("EMA_SQUEEZE_THRESHOLD_PCT", "2.0"))     # 4 EMA spread < 2.0% = squeeze (siết chặt so với 3.5% cũ)
    DRAGON_NARROW_THRESHOLD_PCT = float(os.getenv("DRAGON_NARROW_THRESHOLD_PCT", "1.2"))   # Dragon band width < 1.2% = narrow
    MIN_ATR_PCT = float(os.getenv("MIN_ATR_PCT", "0.15"))                                 # Bỏ qua coin chết/ít thanh khoản nếu ATR 5m < 0.15%
    MAX_EMA_SPREAD_PCT = float(os.getenv("MAX_EMA_SPREAD_PCT", "6.0"))                    # Max EMA spread % cho nén hợp lệ (>6% = không nén thực sự)
    MAX_PRICE_DISTANCE_FROM_EMA_PCT = float(os.getenv("MAX_PRICE_DISTANCE_PCT", "1.2"))  # Max khoảng cách giá → cụm EMA 89/200/610 (>1.2% = quá xa, entry muộn)
    SQUEEZE_LOOKBACK_CANDLES = int(os.getenv("SQUEEZE_LOOKBACK_CANDLES", "5"))            # Số nến lookback để xác nhận squeeze gần đây (5 nến = 25 phút trên 5m)
    DRAGON_MIN_SLOPE = 0.001            # Min slope to confirm trending
    PULLBACK_ZONE_PCT = 0.3             # Price within ±0.3% of EMA = touch
    DRAGON_SLOPE_LOOKBACK = 5           # Candles to measure slope

    # ═══════════════════════════════════════
    # LIQUIDITY SWEEP / STOP HUNT (ICT)
    # ═══════════════════════════════════════
    SWING_LOOKBACK = int(os.getenv("SWING_LOOKBACK", "7"))          # Candles to detect swing H/L
    SWEEP_LOOKBACK_CANDLES = int(os.getenv("SWEEP_LOOKBACK", "20")) # Candles to check for stop hunt
    SWEEP_MIN_WICK_PCT = float(os.getenv("SWEEP_MIN_WICK_PCT", "0.1"))  # Min wick beyond swing level (%)

    # ═══════════════════════════════════════
    # REJECTION CANDLE (VSA)
    # ═══════════════════════════════════════
    MIN_WICK_RATIO = float(os.getenv("MIN_WICK_RATIO", "0.5"))     # Wick ≥ 50% of candle range
    MIN_VOLUME_RATIO = float(os.getenv("MIN_VOLUME_RATIO", "1.2")) # Volume ≥ 1.2x average

    # ═══════════════════════════════════════
    # TECHNICAL INDICATORS
    # ═══════════════════════════════════════
    ATR_PERIOD = 14
    RSI_PERIOD = 14
    VOLUME_AVG_PERIOD = 34
    VOLUME_SPIKE_MULTIPLIER = 1.5

    # ═══════════════════════════════════════
    # FVG E-BOOK SCORING (3 Loại + IFVG)
    # ═══════════════════════════════════════
    FVG_CONSOLIDATION_SCORE = int(os.getenv("FVG_CONSOLIDATION_SCORE", "35"))   # Điểm cho Consolidation FVG (cao nhất — E-Book)
    FVG_BREAKAWAY_SCORE = int(os.getenv("FVG_BREAKAWAY_SCORE", "25"))           # Điểm cho Breakaway FVG (momentum mạnh)
    FVG_REJECT_SCORE = int(os.getenv("FVG_REJECT_SCORE", "10"))                 # Điểm cho Reject FVG (yếu nhất)
    FVG_IFVG_BONUS = int(os.getenv("FVG_IFVG_BONUS", "15"))                    # Bonus Inverse FVG (tín hiệu cực mạnh)
    FVG_IFVG_LOOKBACK = int(os.getenv("FVG_IFVG_LOOKBACK", "30"))              # Lookback nến cho IFVG detection
    FVG_REBALANCE_ENTRY_SCORE = int(os.getenv("FVG_REBALANCE_ENTRY_SCORE", "10"))  # Bonus khi giá rebalance vào FVG zone

    # ═══════════════════════════════════════
    # RISK MANAGEMENT — VỐN $20, MỤC TIÊU $250/NGÀY
    # ═══════════════════════════════════════
    ACCOUNT_BALANCE = float(os.getenv("ACCOUNT_BALANCE", "20"))
    MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", "2"))
    MIN_RR_RATIO = float(os.getenv("MIN_RR_RATIO", "2.0"))    # R:R tối thiểu 1:2
    MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "50"))         # Đòn bẩy tối đa cho phép
    DAILY_PROFIT_TARGET = float(os.getenv("DAILY_PROFIT_TARGET", "250"))
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "10"))   # $10 max loss / ngày với vốn $20
    MAX_CONSECUTIVE_LOSSES = 2

    # ═══════════════════════════════════════
    # TP PHÂN TẦNG (SCALING OUT)
    # ═══════════════════════════════════════
    TP1_ATR_MULT = float(os.getenv("TP1_ATR_MULT", "1.0"))     # TP1 = 1x ATR
    TP2_ATR_MULT = float(os.getenv("TP2_ATR_MULT", "2.0"))     # TP2 = 2x ATR
    TP3_ATR_MULT = float(os.getenv("TP3_ATR_MULT", "3.5"))     # TP3 = 3.5x ATR (trailing)
    SL_ATR_MULT = float(os.getenv("SL_ATR_MULT", "1.5"))       # SL backup = 1.5x ATR
    TP1_CLOSE_PCT = float(os.getenv("TP1_CLOSE_PCT", "0.4"))   # Chốt 40% tại TP1
    TP2_CLOSE_PCT = float(os.getenv("TP2_CLOSE_PCT", "0.3"))   # Chốt 30% tại TP2
    TP3_CLOSE_PCT = float(os.getenv("TP3_CLOSE_PCT", "0.3"))   # Chốt 30% trailing

    # ═══════════════════════════════════════
    # CONFLUENCE SCORING
    # ═══════════════════════════════════════
    MIN_CONFLUENCE_SCORE = int(os.getenv("MIN_CONFLUENCE_SCORE", "35"))  # Điểm tối thiểu

    # Signal Management
    SIGNAL_COOLDOWN_SECONDS = int(os.getenv("SIGNAL_COOLDOWN_SECONDS", "1800"))
    SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))
    TRADE_DIRECTION = os.getenv("TRADE_DIRECTION", "BOTH").upper()  # LONG_ONLY / SHORT_ONLY / BOTH

    @classmethod
    def validate(cls):
        errors = []
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN chưa được cấu hình")
        if not cls.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_CHAT_ID chưa được cấu hình")
        if cls.TRADE_DIRECTION not in ("LONG_ONLY", "SHORT_ONLY", "BOTH"):
            errors.append("TRADE_DIRECTION phải là LONG_ONLY, SHORT_ONLY hoặc BOTH")
        if cls.MAX_LEVERAGE < 1 or cls.MAX_LEVERAGE > 125:
            errors.append("MAX_LEVERAGE phải từ 1 đến 125")
        if errors:
            raise ValueError("Lỗi cấu hình:\n" + "\n".join(errors))
