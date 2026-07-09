"""
Technical Indicators — VSA × ICT × Sonic R System
Hợp nhất: Sonic R (4 EMA) + SMC (Swing/Stop Hunt/FVG) + VSA (Volume)

Modules:
  - Sonic R EMA System (Dragon Band + 89 + 200 + 610)
  - Dragon Slope & Squeeze Detection
  - Swing Point Detection (HH/HL/LH/LL)
  - Liquidity Sweep / Stop Hunt (Spring / Upthrust)
  - Fair Value Gap (FVG) Detection
  - Rejection Candle at EMA Zone (VSA)
  - Volume Analysis + RSI + ATR + MACD
"""
import pandas as pd
import numpy as np
from config import Config
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Unified Indicator Engine — VSA × ICT × Sonic R"""

    # ═══════════════════════════════════════
    # CORE EMA SYSTEM (SONIC R)
    # ═══════════════════════════════════════

    @staticmethod
    def calculate_sonic_r_emas(df: pd.DataFrame) -> pd.DataFrame:
        """Hệ 4 EMA Sonic R + Dragon Band"""
        p = Config.DRAGON_PERIOD
        df['dragon_high'] = df['high'].ewm(span=p, adjust=False).mean()
        df['dragon_close'] = df['close'].ewm(span=p, adjust=False).mean()
        df['dragon_low'] = df['low'].ewm(span=p, adjust=False).mean()
        df['dragon_mid'] = (df['dragon_high'] + df['dragon_low']) / 2
        df['dragon_width'] = (df['dragon_high'] - df['dragon_low']) / df['close'] * 100

        df['ema_89'] = df['close'].ewm(span=Config.EMA_TREND, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=Config.EMA_LONG_TREND, adjust=False).mean()
        df['ema_610'] = df['close'].ewm(span=Config.EMA_SUPER_TREND, adjust=False).mean()
        return df

    # ═══════════════════════════════════════
    # DRAGON SLOPE
    # ═══════════════════════════════════════

    @staticmethod
    def calculate_dragon_slope(df: pd.DataFrame) -> pd.DataFrame:
        """Dragon slope — flat = no trade"""
        lb = Config.DRAGON_SLOPE_LOOKBACK
        df['dragon_slope'] = df['dragon_close'].pct_change(lb)
        df['dragon_slope_abs'] = df['dragon_slope'].abs()
        df['dragon_trending'] = df['dragon_slope_abs'] > Config.DRAGON_MIN_SLOPE
        df['dragon_direction'] = np.where(
            df['dragon_slope'] > Config.DRAGON_MIN_SLOPE, 'UP',
            np.where(df['dragon_slope'] < -Config.DRAGON_MIN_SLOPE, 'DOWN', 'FLAT')
        )
        return df

    # ═══════════════════════════════════════
    # EMA SQUEEZE — GIÁ NÉN TẠI CỤM SONIC R
    # ═══════════════════════════════════════

    @staticmethod
    def detect_ema_squeeze(df: pd.DataFrame) -> pd.DataFrame:
        """Phát hiện giá nén tại cụm EMA Sonic R (Điều kiện ①)"""
        # Loại bỏ EMA 610 ra khỏi spread nén vì EMA 610 là đường vĩ mô dài hạn,
        # chỉ cần Dragon (34), EMA 89 và EMA 200 hội tụ chặt là đủ điều kiện nén.
        ema_cols = ['dragon_close', 'ema_89', 'ema_200']
        ema_max = df[ema_cols].max(axis=1)
        ema_min = df[ema_cols].min(axis=1)
        df['ema_spread_pct'] = (ema_max - ema_min) / df['close'] * 100

        df['dragon_89_spread'] = abs(df['dragon_close'] - df['ema_89']) / df['close'] * 100

        # 4 EMA hội tụ
        df['ema_squeeze'] = df['ema_spread_pct'] < Config.EMA_SQUEEZE_THRESHOLD_PCT
        # Dragon band thu hẹp
        df['dragon_narrow'] = df['dragon_width'] < Config.DRAGON_NARROW_THRESHOLD_PCT
        # Golden squeeze = cả hai
        df['golden_squeeze'] = df['ema_squeeze'] & df['dragon_narrow']

        # Giá nằm trong/gần cụm EMA
        df['price_in_ema_cluster'] = (
            (df['low'] <= df[ema_cols].max(axis=1)) &
            (df['high'] >= df[ema_cols].min(axis=1))
        )

        # Giá chạm Dragon band
        df['price_in_dragon'] = (
            (df['low'] <= df['dragon_high']) &
            (df['high'] >= df['dragon_low'])
        )

        # Giá chạm EMA 89
        threshold = df['ema_89'] * (Config.PULLBACK_ZONE_PCT / 100)
        df['touch_ema89'] = (
            (df['low'] <= df['ema_89'] + threshold) &
            (df['high'] >= df['ema_89'] - threshold)
        )

        # Giá chạm EMA 200
        threshold200 = df['ema_200'] * (Config.PULLBACK_ZONE_PCT / 100)
        df['touch_ema200'] = (
            (df['low'] <= df['ema_200'] + threshold200) &
            (df['high'] >= df['ema_200'] - threshold200)
        )

        return df

    # ═══════════════════════════════════════
    # EMA ORDER — TREND ALIGNMENT
    # ═══════════════════════════════════════

    @staticmethod
    def detect_ema_order(df: pd.DataFrame) -> pd.DataFrame:
        """Xác định thứ tự EMA — trend alignment"""
        df['full_bullish_order'] = (
            (df['close'] > df['dragon_close']) &
            (df['dragon_close'] > df['ema_89']) &
            (df['ema_89'] > df['ema_200']) &
            (df['ema_200'] > df['ema_610'])
        )
        df['partial_bullish_order'] = (
            (df['close'] > df['dragon_close']) &
            (df['dragon_close'] > df['ema_89'])
        )
        df['full_bearish_order'] = (
            (df['close'] < df['dragon_close']) &
            (df['dragon_close'] < df['ema_89']) &
            (df['ema_89'] < df['ema_200']) &
            (df['ema_200'] < df['ema_610'])
        )
        df['partial_bearish_order'] = (
            (df['close'] < df['dragon_close']) &
            (df['dragon_close'] < df['ema_89'])
        )
        return df

    # ═══════════════════════════════════════
    # SWING POINTS — HH / HL / LH / LL
    # ═══════════════════════════════════════

    @staticmethod
    def detect_swing_points(df: pd.DataFrame) -> pd.DataFrame:
        """Phát hiện Swing High/Low cho Liquidity Sweep (Điều kiện ③)"""
        sl = Config.SWING_LOOKBACK
        n = len(df)
        swing_high = pd.Series(np.nan, index=df.index)
        swing_low = pd.Series(np.nan, index=df.index)

        for i in range(sl, n - sl):
            # Swing High
            is_sh = True
            for j in range(1, sl + 1):
                if df['high'].iloc[i] < df['high'].iloc[i - j] or df['high'].iloc[i] < df['high'].iloc[i + j]:
                    is_sh = False
                    break
            if is_sh:
                swing_high.iloc[i] = df['high'].iloc[i]

            # Swing Low
            is_sl = True
            for j in range(1, sl + 1):
                if df['low'].iloc[i] > df['low'].iloc[i - j] or df['low'].iloc[i] > df['low'].iloc[i + j]:
                    is_sl = False
                    break
            if is_sl:
                swing_low.iloc[i] = df['low'].iloc[i]

        df['swing_high'] = swing_high
        df['swing_low'] = swing_low
        return df

    # ═══════════════════════════════════════
    # LIQUIDITY SWEEP / STOP HUNT (ICT)
    # "No Stop Hunt — No Trade"
    # ═══════════════════════════════════════

    @staticmethod
    def detect_liquidity_sweep(df: pd.DataFrame) -> pd.DataFrame:
        """Phát hiện giá đã quét thanh khoản (Spring / Upthrust) (Điều kiện ③)

        Spring (LONG): Giá đâm xuống dưới swing low gần nhất rồi rút chân lên
        Upthrust (SHORT): Giá đâm lên trên swing high gần nhất rồi rút râu xuống
        """
        lookback = Config.SWEEP_LOOKBACK_CANDLES
        n = len(df)
        sweep_low = pd.Series(False, index=df.index)
        sweep_high = pd.Series(False, index=df.index)
        sweep_low_level = pd.Series(np.nan, index=df.index)
        sweep_high_level = pd.Series(np.nan, index=df.index)

        for i in range(lookback, n):
            # Tìm swing low trong window (từ i-1 ngược về i-lookback)
            for j in range(i - 1, i - lookback - 1, -1):
                sl_val = df['swing_low'].iloc[j]
                if not np.isnan(sl_val):
                    # Spring: low hiện tại đâm xuống dưới swing low nhưng close lại trên
                    if df['low'].iloc[i] < sl_val and df['close'].iloc[i] > sl_val:
                        # Kiểm tra xem có nến nào ở giữa đã quét/phá vỡ mức swing low này chưa
                        already_swept = False
                        for k in range(j + 1, i):
                            if df['low'].iloc[k] < sl_val:
                                already_swept = True
                                break
                        if not already_swept:
                            sweep_low.iloc[i] = True
                            sweep_low_level.iloc[i] = sl_val
                            break

            # Tìm swing high trong window (từ i-1 ngược về i-lookback)
            for j in range(i - 1, i - lookback - 1, -1):
                sh_val = df['swing_high'].iloc[j]
                if not np.isnan(sh_val):
                    # Upthrust: high hiện tại đâm lên trên swing high nhưng close lại dưới
                    if df['high'].iloc[i] > sh_val and df['close'].iloc[i] < sh_val:
                        # Kiểm tra xem có nến nào ở giữa đã quét/phá vỡ mức swing high này chưa
                        already_swept = False
                        for k in range(j + 1, i):
                            if df['high'].iloc[k] > sh_val:
                                already_swept = True
                                break
                        if not already_swept:
                            sweep_high.iloc[i] = True
                            sweep_high_level.iloc[i] = sh_val
                            break

        df['sweep_low'] = sweep_low        # Spring detected (bullish)
        df['sweep_high'] = sweep_high      # Upthrust detected (bearish)
        df['sweep_low_level'] = sweep_low_level
        df['sweep_high_level'] = sweep_high_level
        return df

    # ═══════════════════════════════════════
    # FAIR VALUE GAP (FVG) — E-BOOK EDITION
    # 3 Loại: Breakaway / Consolidation / Reject
    # + Inverse FVG (IFVG) + Quality Score
    # ═══════════════════════════════════════

    # FVG Type constants
    FVG_NONE = "NONE"
    FVG_BREAKAWAY = "BREAKAWAY"         # 3 nến cùng màu, momentum mạnh — có thể chạy tiếp không pullback
    FVG_CONSOLIDATION = "CONSOLIDATION" # Nến 3 nhỏ ngược chiều — khả năng valid CAO NHẤT
    FVG_REJECT = "REJECT"               # Nến 3 lớn ngược chiều — khả năng valid THẤP NHẤT

    @staticmethod
    def _classify_fvg_type(c1_open, c1_close, c2_open, c2_close, c2_high, c2_low,
                           c3_open, c3_close, c3_high, c3_low, direction: str) -> str:
        """Phân loại FVG theo E-Book (dựa trên Candle 3)

        Theo E-Book:
        - Candle 1: bất kỳ, bỏ qua
        - Candle 2: luôn là nến mạnh nhất, tạo gap (nến lớn nhất)
        - Candle 3: QUYẾT ĐỊNH loại FVG

        Args:
            direction: 'BULL' hoặc 'BEAR' — hướng của FVG (hướng Candle 2 di chuyển)
        """
        c2_body = abs(c2_close - c2_open)
        c3_body = abs(c3_close - c3_open)
        c3_range = c3_high - c3_low

        # Xác định màu nến
        c2_bullish = c2_close > c2_open
        c3_bullish = c3_close > c3_open

        # Candle 3 cùng chiều hay ngược chiều với Candle 2?
        if direction == "BULL":
            same_direction = c3_bullish  # Nến 3 cũng xanh
        else:  # BEAR
            same_direction = not c3_bullish  # Nến 3 cũng đỏ

        # Tỷ lệ thân nến 3 so với nến 2
        body_ratio = c3_body / c2_body if c2_body > 0 else 0

        if same_direction:
            # 3 nến cùng chiều → BREAKAWAY (momentum mạnh)
            return TechnicalIndicators.FVG_BREAKAWAY
        else:
            # Nến 3 ngược chiều
            if body_ratio < 0.5:
                # Nến 3 nhỏ (< 50% nến 2) → CONSOLIDATION (tốt nhất, giá sẽ pullback rồi tiếp)
                return TechnicalIndicators.FVG_CONSOLIDATION
            else:
                # Nến 3 lớn (≥ 50% nến 2) → REJECT (yếu nhất, có thể phá vỡ FVG)
                return TechnicalIndicators.FVG_REJECT

    @staticmethod
    def detect_fvg(df: pd.DataFrame) -> pd.DataFrame:
        """Phát hiện Fair Value Gap — E-Book Edition

        FVG được hình thành bởi 3 cây nến:
        - Gap nằm giữa bấc nến thứ nhất (candle[i-2]) và bấc nến thứ ba (candle[i])
        - FVG Bullish: candle[i-2].low > candle[i].high (gap hướng lên)
        - FVG Bearish: candle[i-2].high < candle[i].low (gap hướng xuống)

        Phân loại 3 loại FVG (theo E-Book):
        - BREAKAWAY: 3 nến cùng màu → momentum mạnh, có thể chạy tiếp không pullback
        - CONSOLIDATION: Nến 3 nhỏ ngược chiều → khả năng valid CAO NHẤT, giá sẽ pullback
        - REJECT: Nến 3 lớn ngược chiều → khả năng valid THẤP NHẤT, có thể breakout
        """
        n = len(df)
        fvg_bull = pd.Series(False, index=df.index)
        fvg_bear = pd.Series(False, index=df.index)
        fvg_bull_top = pd.Series(np.nan, index=df.index)
        fvg_bull_bottom = pd.Series(np.nan, index=df.index)
        fvg_bear_top = pd.Series(np.nan, index=df.index)
        fvg_bear_bottom = pd.Series(np.nan, index=df.index)
        # E-Book columns mới
        fvg_bull_type = pd.Series(TechnicalIndicators.FVG_NONE, index=df.index)
        fvg_bear_type = pd.Series(TechnicalIndicators.FVG_NONE, index=df.index)
        fvg_bull_quality = pd.Series(0, index=df.index, dtype=int)
        fvg_bear_quality = pd.Series(0, index=df.index, dtype=int)

        for i in range(2, n):
            c1_open, c1_close = df['open'].iloc[i - 2], df['close'].iloc[i - 2]
            c2_open, c2_close = df['open'].iloc[i - 1], df['close'].iloc[i - 1]
            c2_high, c2_low = df['high'].iloc[i - 1], df['low'].iloc[i - 1]
            c3_open, c3_close = df['open'].iloc[i], df['close'].iloc[i]
            c3_high, c3_low = df['high'].iloc[i], df['low'].iloc[i]

            # ── Bullish FVG: candle[i-2].high < candle[i].low (with min size) ──
            gap_size = df['low'].iloc[i] - df['high'].iloc[i - 2]
            if gap_size > 0 and gap_size >= df['atr'].iloc[i] * 0.15:
                fvg_bull.iloc[i] = True
                fvg_bull_top.iloc[i] = df['low'].iloc[i]
                fvg_bull_bottom.iloc[i] = df['high'].iloc[i - 2]

                fvg_type = TechnicalIndicators._classify_fvg_type(
                    c1_open, c1_close, c2_open, c2_close, c2_high, c2_low,
                    c3_open, c3_close, c3_high, c3_low, "BULL"
                )
                fvg_bull_type.iloc[i] = fvg_type

                # Tính Quality Score (0-100)
                gap_size = df['low'].iloc[i] - df['high'].iloc[i - 2]
                c2_body = abs(c2_close - c2_open)
                c2_range = c2_high - c2_low
                # Nến 2 thân dài so với range = momentum rõ ràng
                body_dominance = c2_body / c2_range if c2_range > 0 else 0
                # Volume nến 2 so với trung bình
                vol_ratio = df['volume_ratio'].iloc[i - 1] if 'volume_ratio' in df.columns else 1.0

                quality = 30  # base
                if fvg_type == TechnicalIndicators.FVG_CONSOLIDATION:
                    quality += 35  # Tốt nhất theo E-Book
                elif fvg_type == TechnicalIndicators.FVG_BREAKAWAY:
                    quality += 25
                elif fvg_type == TechnicalIndicators.FVG_REJECT:
                    quality += 10
                if body_dominance > 0.7:
                    quality += 15  # Nến 2 thân dài rõ ràng
                elif body_dominance > 0.5:
                    quality += 10
                if vol_ratio > 1.5:
                    quality += 15  # Volume mạnh
                elif vol_ratio > 1.2:
                    quality += 10
                fvg_bull_quality.iloc[i] = min(quality, 100)

            # ── Bearish FVG: candle[i-2].low > candle[i].high (with min size) ──
            gap_size = df['low'].iloc[i - 2] - df['high'].iloc[i]
            if gap_size > 0 and gap_size >= df['atr'].iloc[i] * 0.15:
                fvg_bear.iloc[i] = True
                fvg_bear_top.iloc[i] = df['low'].iloc[i - 2]
                fvg_bear_bottom.iloc[i] = df['high'].iloc[i]

                fvg_type = TechnicalIndicators._classify_fvg_type(
                    c1_open, c1_close, c2_open, c2_close, c2_high, c2_low,
                    c3_open, c3_close, c3_high, c3_low, "BEAR"
                )
                fvg_bear_type.iloc[i] = fvg_type

                # Tính Quality Score (0-100)
                gap_size = df['low'].iloc[i - 2] - df['high'].iloc[i]
                c2_body = abs(c2_close - c2_open)
                c2_range = c2_high - c2_low
                body_dominance = c2_body / c2_range if c2_range > 0 else 0
                vol_ratio = df['volume_ratio'].iloc[i - 1] if 'volume_ratio' in df.columns else 1.0

                quality = 30
                if fvg_type == TechnicalIndicators.FVG_CONSOLIDATION:
                    quality += 35
                elif fvg_type == TechnicalIndicators.FVG_BREAKAWAY:
                    quality += 25
                elif fvg_type == TechnicalIndicators.FVG_REJECT:
                    quality += 10
                if body_dominance > 0.7:
                    quality += 15
                elif body_dominance > 0.5:
                    quality += 10
                if vol_ratio > 1.5:
                    quality += 15
                elif vol_ratio > 1.2:
                    quality += 10
                fvg_bear_quality.iloc[i] = min(quality, 100)

        df['fvg_bullish'] = fvg_bull
        df['fvg_bearish'] = fvg_bear
        df['fvg_bull_top'] = fvg_bull_top
        df['fvg_bull_bottom'] = fvg_bull_bottom
        df['fvg_bear_top'] = fvg_bear_top
        df['fvg_bear_bottom'] = fvg_bear_bottom
        # E-Book columns mới
        df['fvg_bull_type'] = fvg_bull_type
        df['fvg_bear_type'] = fvg_bear_type
        df['fvg_bull_quality'] = fvg_bull_quality
        df['fvg_bear_quality'] = fvg_bear_quality
        return df

    @staticmethod
    def detect_inverse_fvg(df: pd.DataFrame) -> pd.DataFrame:
        """Phát hiện Inverse FVG (IFVG) — E-Book Edition

        Inverse FVG xảy ra khi:
        1. FVG trước đó bị breakout (giá phá vỡ qua FVG zone)
        2. Sự thay đổi đột ngột về momentum tạo ra FVG ngược chiều
        3. Thường xảy ra khi thị trường đi ngang (sideway) hoặc quét thanh khoản

        IFVG không khác nhiều so với FVG thông thường, nhưng là tín hiệu cực mạnh
        vì xác nhận sự thay đổi cấu trúc thị trường.
        """
        n = len(df)
        ifvg_bull = pd.Series(False, index=df.index)
        ifvg_bear = pd.Series(False, index=df.index)

        # Lookback để tìm FVG gốc bị phá vỡ
        lookback = getattr(Config, 'FVG_IFVG_LOOKBACK', 30)

        for i in range(lookback, n):
            # ── Bullish IFVG: Bearish FVG cũ bị breakout lên + Bullish FVG mới xuất hiện ──
            if df['fvg_bullish'].iloc[i]:
                # Tìm bearish FVG gần nhất trong lookback đã bị breakout
                for j in range(i - 1, max(i - lookback, 1), -1):
                    if df['fvg_bearish'].iloc[j]:
                        bear_fvg_bottom = df['fvg_bear_bottom'].iloc[j]
                        # Kiểm tra giá đã phá vỡ qua bearish FVG cũ (close > fvg_bear_top)
                        bear_fvg_top = df['fvg_bear_top'].iloc[j]
                        if not np.isnan(bear_fvg_top) and df['close'].iloc[i] > bear_fvg_top:
                            ifvg_bull.iloc[i] = True
                            break

            # ── Bearish IFVG: Bullish FVG cũ bị breakout xuống + Bearish FVG mới xuất hiện ──
            if df['fvg_bearish'].iloc[i]:
                for j in range(i - 1, max(i - lookback, 1), -1):
                    if df['fvg_bullish'].iloc[j]:
                        bull_fvg_top = df['fvg_bull_top'].iloc[j]
                        bull_fvg_bottom = df['fvg_bull_bottom'].iloc[j]
                        if not np.isnan(bull_fvg_bottom) and df['close'].iloc[i] < bull_fvg_bottom:
                            ifvg_bear.iloc[i] = True
                            break

        df['ifvg_bullish'] = ifvg_bull
        df['ifvg_bearish'] = ifvg_bear
        return df

    @staticmethod
    def detect_fvg_rebalance(df: pd.DataFrame) -> pd.DataFrame:
        """Kiểm tra giá đã quay lại fill (rebalance) FVG chưa — E-Book Edition

        Theo E-Book: FVG hoạt động như NAM CHÂM
        - Giá sẽ pullback về FVG zone để rebalance
        - Khi FVG đã balance, giá sẽ tiếp tục xu hướng
        - Nếu giá tiếp tục hướng di chuyển sau rebalance → FVG là Valid

        Column mới:
        - fvg_bull_rebalanced: True nếu giá đã quay lại chạm vùng Bullish FVG
        - fvg_bear_rebalanced: True nếu giá đã quay lại chạm vùng Bearish FVG
        - fvg_bull_active_zone_top/bottom: Vùng FVG bullish gần nhất chưa fill
        - fvg_bear_active_zone_top/bottom: Vùng FVG bearish gần nhất chưa fill
        """
        n = len(df)
        # Active FVG zones (chưa bị fill)
        active_bull_top = pd.Series(np.nan, index=df.index)
        active_bull_bottom = pd.Series(np.nan, index=df.index)
        active_bear_top = pd.Series(np.nan, index=df.index)
        active_bear_bottom = pd.Series(np.nan, index=df.index)
        # Rebalance flags
        bull_rebalanced = pd.Series(False, index=df.index)
        bear_rebalanced = pd.Series(False, index=df.index)

        # Track active FVG zones (FIFO, tối đa 5 zone mỗi loại)
        active_bull_zones = []  # [(top, bottom, idx)]
        active_bear_zones = []

        max_active = 5

        for i in range(n):
            # Thêm FVG mới vào active zones
            if df['fvg_bullish'].iloc[i]:
                top = df['fvg_bull_top'].iloc[i]
                bottom = df['fvg_bull_bottom'].iloc[i]
                if not np.isnan(top) and not np.isnan(bottom):
                    active_bull_zones.append((top, bottom, i))
                    if len(active_bull_zones) > max_active:
                        active_bull_zones.pop(0)

            if df['fvg_bearish'].iloc[i]:
                top = df['fvg_bear_top'].iloc[i]
                bottom = df['fvg_bear_bottom'].iloc[i]
                if not np.isnan(top) and not np.isnan(bottom):
                    active_bear_zones.append((top, bottom, i))
                    if len(active_bear_zones) > max_active:
                        active_bear_zones.pop(0)

            # Kiểm tra rebalance: giá chạm vào FVG zone
            low_i = df['low'].iloc[i]
            high_i = df['high'].iloc[i]

            # Bullish FVG rebalance: giá pullback xuống chạm vùng FVG (giá giảm về zone)
            remaining_bull = []
            for top, bottom, idx in active_bull_zones:
                if i > idx and low_i <= top:  # Giá đã chạm vùng FVG
                    bull_rebalanced.iloc[i] = True
                    # Zone đã fill → xóa khỏi active
                else:
                    remaining_bull.append((top, bottom, idx))
            active_bull_zones = remaining_bull

            # Bearish FVG rebalance: giá pullback lên chạm vùng FVG (giá tăng lên zone)
            remaining_bear = []
            for top, bottom, idx in active_bear_zones:
                if i > idx and high_i >= bottom:  # Giá đã chạm vùng FVG
                    bear_rebalanced.iloc[i] = True
                else:
                    remaining_bear.append((top, bottom, idx))
            active_bear_zones = remaining_bear

            # Ghi nhận FVG zone gần nhất đang active (chưa fill)
            if active_bull_zones:
                active_bull_top.iloc[i] = active_bull_zones[-1][0]
                active_bull_bottom.iloc[i] = active_bull_zones[-1][1]
            if active_bear_zones:
                active_bear_top.iloc[i] = active_bear_zones[-1][0]
                active_bear_bottom.iloc[i] = active_bear_zones[-1][1]

        df['fvg_bull_rebalanced'] = bull_rebalanced
        df['fvg_bear_rebalanced'] = bear_rebalanced
        df['fvg_bull_active_top'] = active_bull_top
        df['fvg_bull_active_bottom'] = active_bull_bottom
        df['fvg_bear_active_top'] = active_bear_top
        df['fvg_bear_active_bottom'] = active_bear_bottom
        return df

    # ═══════════════════════════════════════
    # REJECTION CANDLE AT EMA ZONE (VSA)
    # ═══════════════════════════════════════

    @staticmethod
    def detect_rejection_candles(df: pd.DataFrame) -> pd.DataFrame:
        """Phát hiện nến đảo chiều / rút chân tại cụm EMA (Điều kiện ②)"""
        body = abs(df['close'] - df['open'])
        full_range = df['high'] - df['low']
        safe_range = full_range.replace(0, np.nan)
        upper_wick = df['high'] - df[['close', 'open']].max(axis=1)
        lower_wick = df[['close', 'open']].min(axis=1) - df['low']
        is_bullish = df['close'] > df['open']
        is_bearish = df['close'] < df['open']

        # Wick ratios
        df['lower_wick_ratio'] = (lower_wick / safe_range).fillna(0)
        df['upper_wick_ratio'] = (upper_wick / safe_range).fillna(0)
        df['body_ratio'] = (body / safe_range).fillna(0)

        # Volume ratio
        df['volume_ratio'] = df['volume'] / df['volume_avg']

        min_wick = Config.MIN_WICK_RATIO
        min_vol = Config.MIN_VOLUME_RATIO

        # === SPRING (Bullish Rejection) ===
        # Nến xanh + râu dưới dài + volume OK
        df['is_spring'] = (
            is_bullish &
            (df['lower_wick_ratio'] >= min_wick) &
            (df['volume_ratio'] >= min_vol) &
            (full_range > 0)
        )

        # === UPTHRUST (Bearish Rejection) ===
        # Nến đỏ + râu trên dài + volume OK
        df['is_upthrust'] = (
            is_bearish &
            (df['upper_wick_ratio'] >= min_wick) &
            (df['volume_ratio'] >= min_vol) &
            (full_range > 0)
        )

        # Hammer / Shooting Star (strict wick ratio & ATR range checks)
        min_wick = Config.MIN_WICK_RATIO
        df['is_hammer'] = (
            (lower_wick >= body * 2) &
            (df['lower_wick_ratio'] >= min_wick) &
            (df['close'] > df['low'] + full_range * 0.6) &
            (full_range >= df['atr'] * 0.5)
        )
        df['is_shooting_star'] = (
            (upper_wick >= body * 2) &
            (df['upper_wick_ratio'] >= min_wick) &
            (df['close'] < df['low'] + full_range * 0.4) &
            (full_range >= df['atr'] * 0.5)
        )

        # Engulfing
        prev_bearish = df['close'].shift(1) < df['open'].shift(1)
        df['is_bull_engulfing'] = (
            is_bullish & prev_bearish &
            (df['close'] > df['open'].shift(1)) &
            (df['open'] < df['close'].shift(1))
        )
        prev_bullish = df['close'].shift(1) > df['open'].shift(1)
        df['is_bear_engulfing'] = (
            is_bearish & prev_bullish &
            (df['close'] < df['open'].shift(1)) &
            (df['open'] > df['close'].shift(1))
        )

        # Any bullish reversal at EMA zone
        at_ema = df['price_in_dragon'] | df['touch_ema89'] | df['touch_ema200']
        df['bullish_reversal_at_ema'] = (
            (df['is_spring'] | df['is_hammer'] | df['is_bull_engulfing']) & at_ema
        )

        # Any bearish reversal at EMA zone
        df['bearish_reversal_at_ema'] = (
            (df['is_upthrust'] | df['is_shooting_star'] | df['is_bear_engulfing']) & at_ema
        )

        return df

    # ═══════════════════════════════════════
    # STANDARD INDICATORS
    # ═══════════════════════════════════════

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
        if period is None:
            period = Config.ATR_PERIOD
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=period).mean()
        return df

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
        if period is None:
            period = Config.RSI_PERIOD
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        return df

    @staticmethod
    def calculate_volume_analysis(df: pd.DataFrame) -> pd.DataFrame:
        avg_period = Config.VOLUME_AVG_PERIOD
        df['volume_avg'] = df['volume'].rolling(window=avg_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_avg']
        df['ultra_high_vol'] = df['volume_ratio'] >= Config.VOLUME_SPIKE_MULTIPLIER
        df['low_volume'] = df['volume_ratio'] < 0.5
        return df

    # ═══════════════════════════════════════
    # MASTER CALCULATION
    # ═══════════════════════════════════════

    @classmethod
    def calculate_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Tính toán tất cả indicators VSA × ICT × Sonic R"""
        if df.empty:
            return df

        # 1. Volume (cần trước rejection candle)
        df = cls.calculate_volume_analysis(df)
        # 2. Sonic R EMAs
        df = cls.calculate_sonic_r_emas(df)
        df = cls.calculate_dragon_slope(df)
        # 3. Standard indicators
        df = cls.calculate_atr(df)
        df = cls.calculate_rsi(df)
        df = cls.calculate_macd(df)
        # 4. EMA squeeze & touch detection
        df = cls.detect_ema_squeeze(df)
        df = cls.detect_ema_order(df)
        # 5. Swing points
        df = cls.detect_swing_points(df)
        # 6. Liquidity sweep / Stop Hunt
        df = cls.detect_liquidity_sweep(df)
        # 7. FVG — E-Book Edition (3 loại + Quality Score)
        df = cls.detect_fvg(df)
        # 7b. Inverse FVG (IFVG) — phát hiện FVG bị breakout
        df = cls.detect_inverse_fvg(df)
        # 7c. FVG Rebalance — kiểm tra giá đã fill FVG chưa (nam châm)
        df = cls.detect_fvg_rebalance(df)
        # 8. Rejection candles at EMA zone (depends on touch detection & volume)
        df = cls.detect_rejection_candles(df)

        return df
