"""
Signal Scanner — Sonic R System
3 Setup chính:
  A+ — GOLDEN SETUP: 4 EMA Squeeze Breakout
  A  — DRAGON BOUNCE: Pullback to EMA zone
  B  — DEEP PULLBACK: Chạm EMA 200/610 trong EMA hội tụ
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from config import Config
import logging

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    symbol: str = ""
    direction: str = ""        # LONG / SHORT
    setup_type: str = ""       # GOLDEN_SQUEEZE / DRAGON_BOUNCE / DEEP_PULLBACK
    grade: str = ""            # A+ / A / B
    entry_price: float = 0.0
    stop_loss: float = 0.0
    tp1: float = 0.0
    tp2: float = 0.0
    tp3: float = 0.0
    risk_reward: float = 0.0
    lot_size_suggestion: float = 0.0
    leverage_suggestion: int = 10
    atr_value: float = 0.0

    # EMA Status
    dragon_slope: str = ""     # UP / DOWN / FLAT
    ema_spread_pct: float = 0.0
    dragon_width_pct: float = 0.0
    ema_order: str = ""        # FULL_BULL / PARTIAL_BULL / NONE / PARTIAL_BEAR / FULL_BEAR

    # Checklist details
    trend_detail: str = ""
    squeeze_detail: str = ""
    touch_detail: str = ""
    trigger_detail: str = ""
    volume_detail: str = ""

    # FVG E-Book details
    fvg_type: str = ""             # BREAKAWAY / CONSOLIDATION / REJECT / NONE
    fvg_quality: int = 0           # FVG Quality Score 0-100
    fvg_is_ifvg: bool = False      # True nếu là Inverse FVG (tín hiệu cực mạnh)
    fvg_is_rebalance: bool = False # True nếu giá đang rebalance vào FVG zone
    fvg_zone_top: float = 0.0      # Đỉnh vùng FVG active
    fvg_zone_bottom: float = 0.0   # Đáy vùng FVG active

    confluence_score: int = 0
    timestamp: str = ""

    @property
    def is_valid(self) -> bool:
        return self.grade in ("A+", "A", "B") and self.risk_reward >= Config.MIN_RR_RATIO


class SignalScanner:
    def __init__(self):
        self.data_fetcher = MarketDataFetcher()
        self.indicators = TechnicalIndicators()

    async def scan_symbol(self, symbol: str) -> Optional[TradingSignal]:
        """Quét 1 symbol theo Sonic R — Tối ưu hóa số lượng API requests"""
        try:
            # 1. Chỉ lấy dữ liệu Entry (5m) trước để kiểm tra setup (800 nến để EMA 610 warmup chính xác)
            df_entry = await self.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)

            if df_entry.empty or len(df_entry) < 100:
                return None

            # Discard the last unclosed candle to prevent false signals/repainting
            df_entry = df_entry.iloc[:-1]

            # Tính indicators cho khung Entry
            df_entry = self.indicators.calculate_all(df_entry)

            # Kiểm tra nhanh xem có nén, rút chân và quét thanh khoản hay không (bias="NEUTRAL" để kiểm tra tiềm năng)
            temp_signal = self._check_confluence_setup(df_entry, symbol, bias="NEUTRAL")
            if not temp_signal:
                return None

            # 2. Nếu có setup tiềm năng, lúc này mới xác định bias lớn D1/H4 (dùng cache 15 phút)
            context = await self._get_cached_context_data(symbol)

            # Lấy thêm Funding Rate & Open Interest Change (chỉ khi có setup tiềm năng để tối ưu API)
            funding_data = await self.data_fetcher.fetch_funding_rate(symbol)
            oi_change = await self.data_fetcher.fetch_open_interest_change_pct(symbol, period="5m", limit=6)

            context['funding_rate'] = funding_data.get('funding_rate', 0.0)
            context['oi_change_pct'] = oi_change

            # 3. Chạy lại check_confluence thực sự với bias chuẩn và các bộ lọc nâng cao
            signal = self._check_confluence_setup(df_entry, symbol, context)

            if signal and signal.is_valid:
                # Thêm thông tin context
                signal.timestamp = str(df_entry.index[-1])
                last = df_entry.iloc[-1]
                signal.dragon_slope = str(last.get('dragon_direction', 'FLAT'))
                signal.ema_spread_pct = float(last.get('ema_spread_pct', 0))
                signal.dragon_width_pct = float(last.get('dragon_width', 0))

                if last.get('full_bullish_order', False):
                    signal.ema_order = "FULL_BULL"
                elif last.get('partial_bullish_order', False):
                    signal.ema_order = "PARTIAL_BULL"
                elif last.get('full_bearish_order', False):
                    signal.ema_order = "FULL_BEAR"
                elif last.get('partial_bearish_order', False):
                    signal.ema_order = "PARTIAL_BEAR"
                else:
                    signal.ema_order = "TANGLED"

                logger.info(
                    f"✅ {signal.grade} {signal.setup_type}: {symbol} {signal.direction} | "
                    f"R:R 1:{signal.risk_reward:.1f} | Score {signal.confluence_score}"
                )
                return signal

            return None

        except Exception as e:
            logger.error(f"Lỗi quét {symbol}: {e}", exc_info=True)
            return None

    async def _get_cached_context_data(self, symbol: str) -> dict:
        """Lấy bối cảnh D1/H4 (xu hướng, Premium/Discount) với bộ nhớ cache 15 phút"""
        import time
        now = time.time()

        if not hasattr(self, '_context_cache'):
            self._context_cache = {}

        if symbol in self._context_cache:
            context, cached_time = self._context_cache[symbol]
            if now - cached_time < 900:  # 15 phút
                return context

        # Fetch mới khi cache hết hạn
        df_context = await self.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_CONTEXT, limit=300)
        df_daily = await self.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_DAILY, limit=200)

        if not df_context.empty:
            df_context = self.indicators.calculate_all(df_context)
        if not df_daily.empty:
            df_daily = self.indicators.calculate_all(df_daily)

        bias = self._determine_bias(df_daily, df_context)

        # Tính toán Premium / Discount zone
        # Khung H4 (Context)
        h4_high = float(df_context['high'].iloc[-40:].max()) if not df_context.empty else 0.0
        h4_low = float(df_context['low'].iloc[-40:].min()) if not df_context.empty else 0.0
        h4_mid = (h4_high + h4_low) / 2

        # Khung Daily
        daily_high = float(df_daily['high'].iloc[-20:].max()) if not df_daily.empty else 0.0
        daily_low = float(df_daily['low'].iloc[-20:].min()) if not df_daily.empty else 0.0
        daily_mid = (daily_high + daily_low) / 2

        context = {
            'bias': bias,
            'h4_high': h4_high,
            'h4_low': h4_low,
            'h4_mid': h4_mid,
            'daily_high': daily_high,
            'daily_low': daily_low,
            'daily_mid': daily_mid
        }
        self._context_cache[symbol] = (context, now)
        return context

    def _determine_bias(self, df_daily: pd.DataFrame, df_h4: pd.DataFrame) -> str:
        """Xác định xu hướng từ D1/H4 — H4 làm chủ đạo (Primary Context), D1 bổ trợ.
        Yêu cầu nghiêm ngặt thứ tự các đường EMA: 
        - BULLISH: dragon_close > ema_89 > ema_200
        - BEARISH: dragon_close < ema_89 < ema_200
        """
        bias = "NEUTRAL"

        # H4 bias (khung Context - đại diện cho xu hướng trung hạn trực tiếp)
        if not df_h4.empty and 'dragon_close' in df_h4.columns and 'ema_89' in df_h4.columns and 'ema_200' in df_h4.columns:
            last = df_h4.iloc[-1]
            if last['dragon_close'] > last['ema_89'] and last['ema_89'] > last['ema_200']:
                bias = "BULLISH"
            elif last['dragon_close'] < last['ema_89'] and last['ema_89'] < last['ema_200']:
                bias = "BEARISH"

        # Nếu H4 neutral, kiểm tra Daily (D1)
        if bias == "NEUTRAL" and not df_daily.empty and 'dragon_close' in df_daily.columns and 'ema_89' in df_daily.columns and 'ema_200' in df_daily.columns:
            last = df_daily.iloc[-1]
            if last['dragon_close'] > last['ema_89'] and last['ema_89'] > last['ema_200']:
                bias = "BULLISH"
            elif last['dragon_close'] < last['ema_89'] and last['ema_89'] < last['ema_200']:
                bias = "BEARISH"

        return bias

    # ═══════════════════════════════════════
    # SETUP HỢP NHẤT VSA × ICT × SONIC R (4 ĐIỀU KIỆN HỢP LƯU)
    # ═══════════════════════════════════════

    def _check_confluence_setup(self, df: pd.DataFrame, symbol: str, bias) -> Optional[TradingSignal]:
        """
        Setup hợp nhất VSA x ICT x Sonic R:
        4 Điều kiện hợp lưu:
        1. Giá nén tại cụm Sonic R (BẮT BUỘC)
        2. Nến đảo chiều / rút chân tại cụm Sonic R (BẮT BUỘC)
        3. Giá đã quét xong thanh khoản đáy/đỉnh gần nhất (BẮT BUỘC)
        4. Fair Value Gap - FVG (BONUS)
        """
        if len(df) < 50:
            return None

        if isinstance(bias, dict):
            context = bias
            bias = context.get('bias', 'NEUTRAL')
        else:
            context = {}

        last = df.iloc[-1]
        recent = df.iloc[-20:]  # Lookback cho sweep & squeeze

        # Khởi tạo các flag điều kiện
        cond1_compression = False
        direction = None
        confluence_score = 0
        checklist_details = []
        
        # Hard filter: Bỏ qua các coin "chết" hoặc thanh khoản quá kém (ATR < 0.15%)
        # Các coin này có EMA phẳng lì, dễ gây false signal do một vài tick nhỏ
        atr_pct = last.get('atr', 0) / last['close'] * 100
        if atr_pct < getattr(Config, 'MIN_ATR_PCT', 0.15):
            logger.debug(f"Bỏ qua {symbol} — ATR quá thấp {atr_pct:.4f}% < {getattr(Config, 'MIN_ATR_PCT', 0.15)}% (coin chết/ít thanh khoản)")
            return None

        # Hard filter: Bỏ qua các coin mới list chưa đủ nến để vẽ EMA 610
        if pd.isna(last.get('ema_610', None)):
            logger.debug(f"Bỏ qua {symbol} — Coin quá mới, chưa đủ dữ liệu tính EMA 610")
            return None

        # =========================================================================
        # KIỂM TRA ĐIỀU KIỆN 1: GIÁ NÉN HOẶC XU HƯỚNG MẠNH (SONIC R COMPRESSION OR TREND)
        # =========================================================================
        sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES  # 5 nến (25 phút trên 5m)
        has_squeeze = df['ema_squeeze'].iloc[-sq_lb:].any()
        has_narrow = df['dragon_narrow'].iloc[-sq_lb:].any()
        current_spread = last.get('ema_spread_pct', 100)

        # Bỏ qua Dragon (EMA 34) ra khỏi tính toán vì Dragon luôn bám sát giá,
        # và bỏ qua EMA 610 vì đường này cực dài hạn, dễ kéo trung bình lệch xa trong xu hướng mạnh
        ema_cluster_center = (last['ema_89'] + last['ema_200']) / 2
        price_distance_pct = abs(last['close'] - ema_cluster_center) / ema_cluster_center * 100
        price_distance_abs = abs(last['close'] - ema_cluster_center)
        
        # Bỏ qua nếu giá xa hơn MAX % HOẶC xa hơn 3.0 lần ATR (chống nến to trên chart ít thanh khoản)
        if price_distance_pct > Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT or price_distance_abs > 3.0 * last.get('atr', price_distance_abs):
            logger.debug(
                f"Bỏ qua {symbol} — giá {last['close']:.4f} đã xa cụm EMA(89/200/610) "
                f"(Pct: {price_distance_pct:.2f}%, ATR x: {price_distance_abs/last.get('atr', 1):.1f}) (entry muộn)"
            )
            return None

        # 1.2 Giá hiện tại nằm trong hoặc gần cụm EMA (chạm Dragon Band hoặc EMA 89/200)
        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )

        is_strong_trend_long = (
            last['dragon_close'] > last['ema_89'] and 
            last['ema_89'] > last['ema_200']
        )
        is_strong_trend_short = (
            last['dragon_close'] < last['ema_89'] and 
            last['ema_89'] < last['ema_200']
        )

        if has_squeeze and price_near_ema and current_spread <= Config.MAX_EMA_SPREAD_PCT:
            cond1_compression = True
            confluence_score += 25
            checklist_details.append(f"✅ Nén Sonic R: 4 EMA Hội Tụ ({current_spread:.1f}%)")
            if has_narrow:
                checklist_details.append("✅ Dragon Band thu hẹp")
                confluence_score += 5
        elif has_narrow and price_near_ema and current_spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2:
            cond1_compression = True
            confluence_score += 20
            checklist_details.append(f"⚠️ Nén Sonic R: Chỉ Dragon Band thu hẹp, EMA Spread {current_spread:.1f}%")
        elif (is_strong_trend_long or is_strong_trend_short) and price_near_ema:
            # Cho phép bỏ qua điều kiện nén nếu xu hướng đã hình thành cực đẹp (Dragon Bounce / Pullback)
            cond1_compression = True
            confluence_score += 20
            checklist_details.append(f"📈 Xu hướng Sonic R mạnh (Dragon > 89 > 200) — Pullback Setup")
        else:
            return None


        # =========================================================================
        # XÁC ĐỊNH HƯỚNG GIAO DỰA TRÊN XU HƯỚNG LỚN (BIAS D1/H4) VÀ CẤU HÌNH
        # =========================================================================
        trade_dir = getattr(Config, 'TRADE_DIRECTION', 'BOTH')

        # Quyết định hướng quét
        check_long = False
        check_short = False

        # Cho phép quét cả hai hướng để phát hiện Stop Hunt ngược xu hướng lớn (áp dụng cho tất cả các symbol)
        if trade_dir == "LONG_ONLY":
            check_long = True
        elif trade_dir == "SHORT_ONLY":
            check_short = True
        else:  # BOTH
            check_long = True
            check_short = True

        # =========================================================================
        # KIỂM TRA ĐIỀU KIỆN 2 & 3 CHO CẢ HAI HƯỚNG LONG / SHORT
        # =========================================================================

        # LONG SCAN
        long_satisfied = False
        long_score_bonus = 0
        long_checklist = []
        long_sl = 0.0
        long_setup_type = "CONFLUENCE_SETUP"

        if check_long:
            # Điều kiện 2 & 3: Rút chân đảo chiều tại cụm Sonic R và có Stop Hunt (quét thanh khoản đáy) xuất hiện gần đây
            sweep_lookback = 35
            has_reversal_with_sweep = False
            rev_indices = []
            # Cho phép quét ngược 10 nến gần nhất để tìm nến đảo chiều (tăng từ 2 nến)
            # Điều này giúp khớp các setup mà giá tích lũy hoặc pullback về FVG vài nến trước khi vượt EMA34
            for idx in range(-1, -11, -1):
                if df['bullish_reversal_at_ema'].iloc[idx]:
                    rev_indices.append(idx)

            if rev_indices:
                for rev_idx in rev_indices:
                    # HỆ THỐNG KỶ LUẬT: Nếu giá đã từng đóng cửa dưới đáy của nến đảo chiều này, nến đảo chiều bị vô hiệu hóa
                    rev_candle_low = df['low'].iloc[rev_idx]
                    if (df['close'].iloc[rev_idx:] < rev_candle_low).any():
                        continue

                    # Quét ngược từ nến reversal trở về trước để tìm sweep_low
                    for idx in range(rev_idx, rev_idx - sweep_lookback, -1):
                        if df['sweep_low'].iloc[idx]:
                            sweep_candle_low = df['low'].iloc[idx]
                            # Kiểm tra khoảng cách sweep → entry: nếu > 4x ATR thì sweep quá xa, bỏ qua
                            sweep_distance = abs(last['close'] - sweep_candle_low)
                            if sweep_distance > 4.0 * last.get('atr', 0):
                                logger.debug(f"Bỏ qua {symbol} LONG: Sweep Low quá xa entry ({sweep_distance/last.get('atr',1):.1f}x ATR)")
                                continue
                            # Không có nến nào đóng cửa dưới mức low của nến quét thanh khoản này kể từ nến sweep cho đến hiện tại
                            closed_below = (df['close'].iloc[idx:] < sweep_candle_low).any()
                            if not closed_below:
                                has_reversal_with_sweep = True
                                break
                    if has_reversal_with_sweep:
                        break

            # Điều kiện 1.3: Squeeze Breakout (Không cần Stop Hunt)
            # Squeeze phải là NÉN THỰC SỰ, không chỉ Dragon narrow khi EMA quá rộng
            has_recent_squeeze = df['ema_squeeze'].iloc[-5:-1].any()
            if not has_recent_squeeze:
                # Dragon narrow chỉ được thay thế khi EMA spread tương đối hẹp (giống logic cond1_compression)
                has_recent_squeeze = (
                    df['dragon_narrow'].iloc[-5:-1].any() and
                    df['ema_spread_pct'].iloc[-5:-1].min() <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2
                )
            # Nến breakout thân xanh dài, volume lớn đóng cửa trên Dragon High
            # + giá breakout vẫn gần cụm EMA 89/200/610 (bỏ Dragon vì luôn bám sát giá)
            bo_ema_center = (df['ema_89'].iloc[-1] + df['ema_200'].iloc[-1] + df['ema_610'].iloc[-1]) / 3
            breakout_distance_pct = abs(df['close'].iloc[-1] - bo_ema_center) / bo_ema_center * 100
            breakout_distance_abs = abs(df['close'].iloc[-1] - bo_ema_center)
            
            is_breakout_candle = (
                (df['close'].iloc[-1] > df['dragon_high'].iloc[-1]) &
                (df['close'].iloc[-1] > df['ema_89'].iloc[-1]) &
                (df['close'].iloc[-1] > df['ema_200'].iloc[-1]) &
                (df['close'].iloc[-1] > df['open'].iloc[-1]) &
                ((df['close'].iloc[-1] - df['open'].iloc[-1]) > 0.5 * (df['high'].iloc[-1] - df['low'].iloc[-1])) &
                (df['volume_ratio'].iloc[-1] >= 1.2) &
                (breakout_distance_pct <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5) &  # Breakout cho phép xa hơn 1.5x
                (breakout_distance_abs <= 2.5 * df['atr'].iloc[-1])                        # Không vượt quá 2.5 ATR
            )
            # Kiểm tra tính toàn vẹn của xu hướng: Không có nến nào đóng cửa dưới EMA 200 trong 12 nến gần nhất
            no_trend_violation = not (df['close'].iloc[-12:] < df['ema_200'].iloc[-12:]).any()
            has_squeeze_breakout = has_recent_squeeze and is_breakout_candle and no_trend_violation

            # Lọc điều kiện xu hướng Dragon và vị thế đóng cửa nến
            is_trending_long = last.get('dragon_direction', 'FLAT') in ('UP', 'FLAT')
            is_above_dragon = last['close'] > last.get('dragon_close', 0)

            # Chặn Premium/Discount H4 cho LONG: Chỉ LONG ở vùng Discount (giá <= H4 Mid)
            h4_mid = context.get('h4_mid', 0.0)
            if h4_mid > 0.0 and last['close'] > h4_mid:
                is_trending_long = False
                logger.debug(f"Bỏ qua {symbol} LONG: Giá {last['close']:.4f} > H4 Mid {h4_mid:.4f} (Vùng Premium, cấm LONG)")

            # Chặn đánh ngược trend cho LONG:
            # BẮT BUỘC: EMA34 (Dragon) > EMA89 > EMA200 (thứ tự tăng = xu hướng tăng)
            # Nếu Dragon nằm dưới EMA 89/200 thì KHÔNG LONG được dù EMAs có hội tụ
            if (
                last['dragon_close'] <= last['ema_89'] or
                last['ema_89'] <= last['ema_200']
            ):
                is_trending_long = False
                logger.debug(f"Bỏ qua {symbol} LONG: EMA34({last['dragon_close']:.4f}) < EMA89({last['ema_89']:.4f}) hoặc EMA89 < EMA200({last['ema_200']:.4f}) — sai thứ tự EMA")
            elif not has_squeeze_breakout:
                # Kiểm tra thêm: giá phải nằm trên cụm EMA
                if (
                    last['close'] <= last['dragon_close'] or
                    last['close'] <= last['ema_89'] or
                    last['close'] <= last['ema_200']
                ):
                    is_trending_long = False

            # HỆ THỐNG KỶ LUẬT: Cho phép đánh ngược trend (Bắt đáy/Spring) khi có Stop Hunt (áp dụng cho tất cả các coin)
            # NHƯNG từ ngày 13/06/2026, thứ tự EMA PHẢI BẮT BUỘC đúng: EMA34 > EMA89 > EMA200
            has_correct_ema_order = (
                last['dragon_close'] > last['ema_89'] and 
                last['ema_89'] > last['ema_200']
            )
            if has_reversal_with_sweep and has_correct_ema_order:
                is_trending_long = True
                is_above_dragon = True


            if has_reversal_with_sweep and not cond1_compression:
                logger.debug(f"Bỏ qua {symbol} LONG: Có Sweep nhưng EMAs không nén chặt (Spread: {current_spread:.2f}%)")

            if ((has_reversal_with_sweep and cond1_compression) or has_squeeze_breakout) and is_trending_long and is_above_dragon:
                long_satisfied = True

                if has_squeeze_breakout:
                    long_setup_type = "SQUEEZE_BREAKOUT"
                    long_checklist.append("🚀 Breakout nén chặt Sonic R (Không cần Stop Hunt)")
                    long_score_bonus += 30
                    if last['volume_ratio'] >= 1.5:
                        long_score_bonus += 15
                        long_checklist.append("⭐ Volume breakout cực mạnh (≥ 1.5x)")
                    else:
                        long_checklist.append("✅ Volume breakout đạt chuẩn (≥ 1.2x)")

                    # SL dưới đáy cụm nén (5 nến gần nhất)
                    long_sl = df['low'].iloc[-5:].min() - last.get('atr', 0) * 0.2
                else:
                    # Phân loại Setup Type cho lệnh Pullback
                    is_squeezed = has_squeeze or (has_narrow and current_spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2)
                    if not is_squeezed and is_strong_trend_long:
                        if last['low'] <= last['dragon_high'] and last['high'] >= last['dragon_low']:
                            long_setup_type = "DRAGON_BOUNCE"
                            long_checklist.append("🐉 Dragon Bounce — Pullback về dải rồng trong xu hướng mạnh")
                        else:
                            long_setup_type = "DEEP_PULLBACK"
                            long_checklist.append("📉 Deep Pullback — Pullback sâu về EMA89/200 trong xu hướng mạnh")
                    else:
                        long_setup_type = "CONFLUENCE_SETUP"
                        long_checklist.append("✅ Nến đảo chiều LONG đồng thời quét thanh khoản ĐÁY (Stop Hunt)")


                    # Điểm điều kiện 2
                    long_score_bonus += 20
                    recent_rejections = df.iloc[-3:]
                    if (recent_rejections['lower_wick_ratio'] >= 0.6).any():
                        long_score_bonus += 20
                        long_checklist.append("⭐ Râu nến dưới dài ≥ 60%")

                    # Volume rejection >= 1.5x
                    if (recent_rejections['volume_ratio'] >= 1.5).any():
                        long_score_bonus += 10
                        long_checklist.append("⭐ Volume rejection mạnh (≥ 1.5x)")
                    elif (recent_rejections['volume_ratio'] >= 1.2).any():
                        long_checklist.append("✅ Volume rejection đạt chuẩn (≥ 1.2x)")

                    # Điểm điều kiện 3
                    long_score_bonus += 20

                # Tìm SL
                sweep_candles = df.iloc[-20:]
                sweep_idx = sweep_candles[sweep_candles['sweep_low'] == True].index
                atr = last.get('atr', 0)
                if long_sl == 0.0:
                    if len(sweep_idx) > 0:
                        sl_base = df.loc[sweep_idx, 'low'].min()
                    else:
                        sl_base = sweep_candles['low'].min()
                    long_sl = sl_base - atr * 0.2

                # Điều kiện 4: Fair Value Gap — E-Book Edition (3 Loại + IFVG + Rebalance)
                fvg_lookback = df.iloc[-10:]
                has_fvg_bullish = fvg_lookback['fvg_bullish'].any()
                if has_fvg_bullish:
                    # Tìm FVG bullish gần nhất trong 10 nến
                    fvg_idx = fvg_lookback[fvg_lookback['fvg_bullish']].index[-1]
                    fvg_type_val = df.loc[fvg_idx, 'fvg_bull_type']
                    fvg_quality_val = int(df.loc[fvg_idx, 'fvg_bull_quality'])

                    # Chấm điểm theo loại FVG (E-Book)
                    fvg_type_labels = {
                        'CONSOLIDATION': ('📗 Consolidation', Config.FVG_CONSOLIDATION_SCORE),
                        'BREAKAWAY': ('📘 Breakaway', Config.FVG_BREAKAWAY_SCORE),
                        'REJECT': ('📙 Reject', Config.FVG_REJECT_SCORE),
                    }
                    label, score = fvg_type_labels.get(fvg_type_val, ('📘 FVG', 15))
                    long_score_bonus += score
                    long_checklist.append(f"🔥 Bullish FVG {label} (Quality: {fvg_quality_val}/100)")

                    # Lưu FVG info cho signal
                    long_fvg_type = fvg_type_val
                    long_fvg_quality = fvg_quality_val
                    long_fvg_zone_top = float(df.loc[fvg_idx, 'fvg_bull_top'])
                    long_fvg_zone_bottom = float(df.loc[fvg_idx, 'fvg_bull_bottom'])

                    # Bonus: Inverse FVG (tín hiệu cực mạnh)
                    if fvg_lookback['ifvg_bullish'].any():
                        long_score_bonus += Config.FVG_IFVG_BONUS
                        long_checklist.append("⚡ Inverse FVG (IFVG) — Xác nhận đổi cấu trúc")
                        long_fvg_is_ifvg = True
                    else:
                        long_fvg_is_ifvg = False

                    # Bonus: Giá đang rebalance vào FVG zone
                    if last.get('fvg_bull_rebalanced', False):
                        long_score_bonus += Config.FVG_REBALANCE_ENTRY_SCORE
                        long_checklist.append("🧲 Giá rebalance vào FVG zone (Nam châm)")
                        long_fvg_is_rebalance = True
                    else:
                        long_fvg_is_rebalance = False
                else:
                    long_fvg_type = ""
                    long_fvg_quality = 0
                    long_fvg_zone_top = 0.0
                    long_fvg_zone_bottom = 0.0
                    long_fvg_is_ifvg = False
                    long_fvg_is_rebalance = False

        # SHORT SCAN
        short_satisfied = False
        short_score_bonus = 0
        short_checklist = []
        short_sl = 0.0
        short_setup_type = "CONFLUENCE_SETUP"

        if check_short:
            # Điều kiện 2 & 3: Rút râu đảo chiều tại cụm Sonic R và có Stop Hunt (quét thanh khoản đỉnh) xuất hiện gần đây
            sweep_lookback = 35
            has_reversal_with_sweep = False
            rev_indices = []
            # Cho phép quét ngược 10 nến gần nhất để tìm nến đảo chiều (tăng từ 2 nến)
            for idx in range(-1, -11, -1):
                if df['bearish_reversal_at_ema'].iloc[idx]:
                    rev_indices.append(idx)

            if rev_indices:
                for rev_idx in rev_indices:
                    # HỆ THỐNG KỶ LUẬT: Nếu giá đã từng đóng cửa trên đỉnh của nến đảo chiều này, nến đảo chiều bị vô hiệu hóa
                    rev_candle_high = df['high'].iloc[rev_idx]
                    if (df['close'].iloc[rev_idx:] > rev_candle_high).any():
                        continue

                    # Quét ngược từ nến reversal trở về trước để tìm sweep_high
                    for idx in range(rev_idx, rev_idx - sweep_lookback, -1):
                        if df['sweep_high'].iloc[idx]:
                            sweep_candle_high = df['high'].iloc[idx]
                            # Kiểm tra khoảng cách sweep → entry: nếu > 4x ATR thì sweep quá xa, bỏ qua
                            sweep_distance = abs(sweep_candle_high - last['close'])
                            if sweep_distance > 4.0 * last.get('atr', 0):
                                logger.debug(f"Bỏ qua {symbol} SHORT: Sweep High quá xa entry ({sweep_distance/last.get('atr',1):.1f}x ATR)")
                                continue
                            # Không có nến nào đóng cửa trên mức high của nến quét thanh khoản này kể từ nến sweep cho đến hiện tại
                            closed_above = (df['close'].iloc[idx:] > sweep_candle_high).any()
                            if not closed_above:
                                has_reversal_with_sweep = True
                                break
                    if has_reversal_with_sweep:
                        break

            # Điều kiện 1.3: Squeeze Breakout (Không cần Stop Hunt)
            # Squeeze phải xảy ra sát nến breakout (trong vòng 5 nến gần nhất) để tránh bẫy giá sau biến động mạnh
            has_recent_squeeze = df['ema_squeeze'].iloc[-5:-1].any()
            if not has_recent_squeeze:
                has_recent_squeeze = (
                    df['dragon_narrow'].iloc[-5:-1].any() and
                    df['ema_spread_pct'].iloc[-5:-1].min() <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2
                )
            # Tính khoảng cách giá breakout so với cụm EMA 89/200/610 (bỏ Dragon)
            short_bo_center = (df['ema_89'].iloc[-1] + df['ema_200'].iloc[-1] + df['ema_610'].iloc[-1]) / 3
            short_bo_distance = abs(df['close'].iloc[-1] - short_bo_center) / short_bo_center * 100
            short_bo_dist_abs = abs(df['close'].iloc[-1] - short_bo_center)
            
            # Nến breakout thân đỏ dài, volume lớn đóng cửa dưới Dragon Low
            # + giá breakout vẫn gần cụm EMA
            is_breakout_candle = (
                (df['close'].iloc[-1] < df['dragon_low'].iloc[-1]) &
                (df['close'].iloc[-1] < df['ema_89'].iloc[-1]) &
                (df['close'].iloc[-1] < df['ema_200'].iloc[-1]) &
                (df['close'].iloc[-1] < df['open'].iloc[-1]) &
                ((df['open'].iloc[-1] - df['close'].iloc[-1]) > 0.5 * (df['high'].iloc[-1] - df['low'].iloc[-1])) &
                (df['volume_ratio'].iloc[-1] >= 1.2) &
                (short_bo_distance <= Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT * 1.5) &
                (short_bo_dist_abs <= 2.5 * df['atr'].iloc[-1])
            )
            # Kiểm tra tính toàn vẹn của xu hướng: Không có nến nào đóng cửa trên EMA 200 trong 12 nến gần nhất
            no_trend_violation = not (df['close'].iloc[-12:] > df['ema_200'].iloc[-12:]).any()
            has_squeeze_breakout = has_recent_squeeze and is_breakout_candle and no_trend_violation

            # Lọc điều kiện xu hướng Dragon và vị thế đóng cửa nến
            is_trending_short = last.get('dragon_direction', 'FLAT') in ('DOWN', 'FLAT')
            is_below_dragon = last['close'] < last.get('dragon_close', 0)

            # Chặn Premium/Discount H4 cho SHORT: Chỉ SHORT ở vùng Premium (giá >= H4 Mid)
            h4_mid = context.get('h4_mid', 0.0)
            if h4_mid > 0.0 and last['close'] < h4_mid:
                is_trending_short = False
                logger.debug(f"Bỏ qua {symbol} SHORT: Giá {last['close']:.4f} < H4 Mid {h4_mid:.4f} (Vùng Discount, cấm SHORT)")

            # Chặn đánh ngược trend cho SHORT:
            # BẮT BUỘC: EMA34 (Dragon) < EMA89 < EMA200 (thứ tự giảm = xu hướng giảm)
            # Nếu Dragon nằm trên EMA 89/200 thì KHÔNG SHORT được dù EMAs có hội tụ
            if (
                last['dragon_close'] >= last['ema_89'] or
                last['ema_89'] >= last['ema_200']
            ):
                is_trending_short = False
                logger.debug(f"Bỏ qua {symbol} SHORT: EMA34({last['dragon_close']:.4f}) > EMA89({last['ema_89']:.4f}) hoặc EMA89 > EMA200({last['ema_200']:.4f}) — sai thứ tự EMA")
            elif not has_squeeze_breakout:
                # Kiểm tra thêm: giá phải nằm dưới cụm EMA
                if (
                    last['close'] >= last['dragon_close'] or
                    last['close'] >= last['ema_89'] or
                    last['close'] >= last['ema_200']
                ):
                    is_trending_short = False

            # HỆ THỐNG KỶ LUẬT: Cho phép đánh ngược trend (Bắt đỉnh/Upthrust) khi có Stop Hunt (áp dụng cho tất cả các coin)
            # NHƯNG từ ngày 13/06/2026, thứ tự EMA PHẢI BẮT BUỘC đúng: EMA34 < EMA89 < EMA200
            has_correct_ema_order = (
                last['dragon_close'] < last['ema_89'] and 
                last['ema_89'] < last['ema_200']
            )
            if has_reversal_with_sweep and has_correct_ema_order:
                is_trending_short = True
                is_below_dragon = True


            if has_reversal_with_sweep and not cond1_compression:
                logger.debug(f"Bỏ qua {symbol} SHORT: Có Sweep nhưng EMAs không nén chặt (Spread: {current_spread:.2f}%)")

            if ((has_reversal_with_sweep and cond1_compression) or has_squeeze_breakout) and is_trending_short and is_below_dragon:
                short_satisfied = True

                if has_squeeze_breakout:
                    short_setup_type = "SQUEEZE_BREAKOUT"
                    short_checklist.append("🚀 Breakout nén chặt Sonic R (Không cần Stop Hunt)")
                    short_score_bonus += 30
                    if last['volume_ratio'] >= 1.5:
                        short_score_bonus += 15
                        short_checklist.append("⭐ Volume breakout cực mạnh (≥ 1.5x)")
                    else:
                        short_checklist.append("✅ Volume breakout đạt chuẩn (≥ 1.2x)")

                    # SL trên đỉnh cụm nén (5 nến gần nhất)
                    short_sl = df['high'].iloc[-5:].max() + last.get('atr', 0) * 0.2
                else:
                    # Phân loại Setup Type cho lệnh Pullback
                    is_squeezed = has_squeeze or (has_narrow and current_spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2)
                    if not is_squeezed and is_strong_trend_short:
                        if last['low'] <= last['dragon_high'] and last['high'] >= last['dragon_low']:
                            short_setup_type = "DRAGON_BOUNCE"
                            short_checklist.append("🐉 Dragon Bounce — Pullback về dải rồng trong xu hướng mạnh")
                        else:
                            short_setup_type = "DEEP_PULLBACK"
                            short_checklist.append("📉 Deep Pullback — Pullback sâu về EMA89/200 trong xu hướng mạnh")
                    else:
                        short_setup_type = "CONFLUENCE_SETUP"
                        short_checklist.append("✅ Nến đảo chiều SHORT đồng thời quét thanh khoản ĐỈNH (Stop Hunt)")

                    # Điểm điều kiện 2
                    short_score_bonus += 20
                    recent_rejections = df.iloc[-3:]
                    if (recent_rejections['upper_wick_ratio'] >= 0.6).any():
                        short_score_bonus += 20
                        short_checklist.append("⭐ Râu nến trên dài ≥ 60%")

                    # Volume rejection >= 1.5x
                    if (recent_rejections['volume_ratio'] >= 1.5).any():
                        short_score_bonus += 10
                        short_checklist.append("⭐ Volume rejection mạnh (≥ 1.5x)")
                    elif (recent_rejections['volume_ratio'] >= 1.2).any():
                        short_checklist.append("✅ Volume rejection đạt chuẩn (≥ 1.2x)")

                    # Điểm điều kiện 3
                    short_score_bonus += 20

                # Tìm SL
                sweep_candles = df.iloc[-20:]
                sweep_idx = sweep_candles[sweep_candles['sweep_high'] == True].index
                atr = last.get('atr', 0)
                if short_sl == 0.0:
                    if len(sweep_idx) > 0:
                        sl_base = df.loc[sweep_idx, 'high'].max()
                    else:
                        sl_base = sweep_candles['high'].max()
                    short_sl = sl_base + atr * 0.2

                # Điều kiện 4: Fair Value Gap — E-Book Edition (3 Loại + IFVG + Rebalance)
                fvg_lookback = df.iloc[-10:]
                has_fvg_bearish = fvg_lookback['fvg_bearish'].any()
                if has_fvg_bearish:
                    fvg_idx = fvg_lookback[fvg_lookback['fvg_bearish']].index[-1]
                    fvg_type_val = df.loc[fvg_idx, 'fvg_bear_type']
                    fvg_quality_val = int(df.loc[fvg_idx, 'fvg_bear_quality'])

                    fvg_type_labels = {
                        'CONSOLIDATION': ('📗 Consolidation', Config.FVG_CONSOLIDATION_SCORE),
                        'BREAKAWAY': ('📘 Breakaway', Config.FVG_BREAKAWAY_SCORE),
                        'REJECT': ('📙 Reject', Config.FVG_REJECT_SCORE),
                    }
                    label, score = fvg_type_labels.get(fvg_type_val, ('📘 FVG', 15))
                    short_score_bonus += score
                    short_checklist.append(f"🔥 Bearish FVG {label} (Quality: {fvg_quality_val}/100)")

                    short_fvg_type = fvg_type_val
                    short_fvg_quality = fvg_quality_val
                    short_fvg_zone_top = float(df.loc[fvg_idx, 'fvg_bear_top'])
                    short_fvg_zone_bottom = float(df.loc[fvg_idx, 'fvg_bear_bottom'])

                    if fvg_lookback['ifvg_bearish'].any():
                        short_score_bonus += Config.FVG_IFVG_BONUS
                        short_checklist.append("⚡ Inverse FVG (IFVG) — Xác nhận đổi cấu trúc")
                        short_fvg_is_ifvg = True
                    else:
                        short_fvg_is_ifvg = False

                    if last.get('fvg_bear_rebalanced', False):
                        short_score_bonus += Config.FVG_REBALANCE_ENTRY_SCORE
                        short_checklist.append("🧲 Giá rebalance vào FVG zone (Nam châm)")
                        short_fvg_is_rebalance = True
                    else:
                        short_fvg_is_rebalance = False
                else:
                    short_fvg_type = ""
                    short_fvg_quality = 0
                    short_fvg_zone_top = 0.0
                    short_fvg_zone_bottom = 0.0
                    short_fvg_is_ifvg = False
                    short_fvg_is_rebalance = False

        # Lựa chọn hướng giao dịch thỏa mãn
        if long_satisfied and short_satisfied:
            if bias == "BULLISH":
                direction = "LONG"
            elif bias == "BEARISH":
                direction = "SHORT"
            else:
                direction = "LONG" if long_score_bonus >= short_score_bonus else "SHORT"
        elif long_satisfied:
            direction = "LONG"
        elif short_satisfied:
            direction = "SHORT"
        else:
            # Không thỏa mãn cả 3 điều kiện bắt buộc
            return None

        # Thiết lập các giá trị cuối cùng dựa trên hướng được chọn
        if direction == "LONG":
            confluence_score += long_score_bonus
            checklist_details.extend(long_checklist)
            stop_loss = long_sl
            setup_type = long_setup_type
            # FVG E-Book details
            chosen_fvg_type = long_fvg_type
            chosen_fvg_quality = long_fvg_quality
            chosen_fvg_zone_top = long_fvg_zone_top
            chosen_fvg_zone_bottom = long_fvg_zone_bottom
            chosen_fvg_is_ifvg = long_fvg_is_ifvg
            chosen_fvg_is_rebalance = long_fvg_is_rebalance
        else:
            confluence_score += short_score_bonus
            checklist_details.extend(short_checklist)
            stop_loss = short_sl
            setup_type = short_setup_type
            chosen_fvg_type = short_fvg_type
            chosen_fvg_quality = short_fvg_quality
            chosen_fvg_zone_top = short_fvg_zone_top
            chosen_fvg_zone_bottom = short_fvg_zone_bottom
            chosen_fvg_is_ifvg = short_fvg_is_ifvg
            chosen_fvg_is_rebalance = short_fvg_is_rebalance

        # Bias cùng hướng → cộng điểm, ngược hướng → trừ điểm
        if (direction == "LONG" and bias == "BULLISH") or (direction == "SHORT" and bias == "BEARISH"):
            confluence_score += 5
            checklist_details.append("✅ Đồng thuận xu hướng lớn D1/H4")
        elif (direction == "LONG" and bias == "BEARISH") or (direction == "SHORT" and bias == "BULLISH"):
            confluence_score -= 15
            checklist_details.append("⚠️ NGƯỢC xu hướng D1/H4 — giảm 15 điểm")
        elif bias == "NEUTRAL":
            checklist_details.append("⚠️ Xu hướng D1/H4 chưa rõ ràng (NEUTRAL)")

        # 🧪 Phân tích Funding Rate & Open Interest (Sentiment/Dòng tiền)
        funding_rate = context.get('funding_rate', 0.0)
        oi_change_pct = context.get('oi_change_pct', 0.0)

        # Chặn Funding Rate nguy hiểm (Block hoặc hạ điểm)
        if direction == "LONG":
            if funding_rate > 0.0005:  # > 0.05%
                confluence_score -= 15
                checklist_details.append(f"⚠️ Funding Rate quá nóng ({funding_rate*100:.4f}%): -15 điểm")
            elif funding_rate < 0.0:
                confluence_score += 10
                checklist_details.append(f"🔥 Funding Rate âm ({funding_rate*100:.4f}%): +10 điểm")
            else:
                checklist_details.append(f"📊 Funding Rate: {funding_rate*100:.4f}%")

            if oi_change_pct > 2.0:
                confluence_score += 15
                checklist_details.append(f"🔥 Open Interest tăng mạnh ({oi_change_pct:+.1f}%): +15 điểm")
            elif oi_change_pct < -2.0:
                confluence_score -= 10
                checklist_details.append(f"⚠️ Open Interest giảm ({oi_change_pct:+.1f}%): -10 điểm")
            else:
                checklist_details.append(f"📊 Biến động OI: {oi_change_pct:+.1f}%")

        elif direction == "SHORT":
            if funding_rate < -0.0005:  # < -0.05%
                confluence_score -= 15
                checklist_details.append(f"⚠️ Funding Rate âm sâu ({funding_rate*100:.4f}%): -15 điểm")
            elif funding_rate > 0.0002:  # > 0.02%
                confluence_score += 10
                checklist_details.append(f"🔥 Funding Rate dương cao ({funding_rate*100:.4f}%): +10 điểm")
            else:
                checklist_details.append(f"📊 Funding Rate: {funding_rate*100:.4f}%")

            if oi_change_pct > 2.0:
                confluence_score += 15
                checklist_details.append(f"🔥 Open Interest tăng mạnh ({oi_change_pct:+.1f}%): +15 điểm")
            elif oi_change_pct < -2.0:
                confluence_score -= 10
                checklist_details.append(f"⚠️ Open Interest giảm ({oi_change_pct:+.1f}%): -10 điểm")
            else:
                checklist_details.append(f"📊 Biến động OI: {oi_change_pct:+.1f}%")

        confluence_score = min(confluence_score, 100)

        # Lọc theo điểm số tối thiểu
        # Khi bias NEUTRAL (sideway), yêu cầu điểm cao hơn
        min_required = Config.MIN_CONFLUENCE_SCORE
        if bias == "NEUTRAL":
            min_required = max(min_required, 50)  # Sideway → cần ít nhất 50 điểm

        if confluence_score < min_required:
            logger.debug(f"Bỏ qua {symbol} {direction} vì điểm confluence {confluence_score} < {min_required} (bias={bias})")
            return None

        # Phân loại Grade dựa trên điểm số
        if confluence_score >= 70:
            grade = "A+"
        elif confluence_score >= 50:
            grade = "A"
        else:
            grade = "B"

        # Tính toán TP/SL và R:R
        atr = last.get('atr', 0)
        entry_price = last['close']

        # Check SL hợp lệ
        if direction == "LONG" and stop_loss >= entry_price:
            stop_loss = entry_price - Config.SL_ATR_MULT * atr
        elif direction == "SHORT" and stop_loss <= entry_price:
            stop_loss = entry_price + Config.SL_ATR_MULT * atr

        # Tính toán các mức TP phân tầng
        if direction == "LONG":
            tp1 = entry_price + Config.TP1_ATR_MULT * atr
            tp2 = entry_price + Config.TP2_ATR_MULT * atr
            tp3 = entry_price + Config.TP3_ATR_MULT * atr
        else:
            tp1 = entry_price - Config.TP1_ATR_MULT * atr
            tp2 = entry_price - Config.TP2_ATR_MULT * atr
            tp3 = entry_price - Config.TP3_ATR_MULT * atr

        # Đo lường R:R tối thiểu (đo SL đến TP2 có đạt 1:2 không theo hệ thống của anh Cường)
        risk = abs(entry_price - stop_loss)
        min_risk = atr * 1.0  # SL tối thiểu 1.0x ATR để tránh râu nến quá nhỏ gây nhiễu
        if risk < min_risk:
            if direction == "LONG":
                stop_loss = entry_price - atr * 1.2
            else:
                stop_loss = entry_price + atr * 1.2
            risk = abs(entry_price - stop_loss)

        reward = abs(tp2 - entry_price)
        risk_reward = reward / risk if risk > 0 else 0

        # Nếu R:R không đạt tối thiểu (1:2), tự động tăng mục tiêu TP theo Risk thực tế (Phương án A)
        if risk_reward < Config.MIN_RR_RATIO:
            tp1 = entry_price + 1.0 * risk if direction == "LONG" else entry_price - 1.0 * risk
            tp2 = entry_price + 2.0 * risk if direction == "LONG" else entry_price - 2.0 * risk
            tp3 = entry_price + 3.5 * risk if direction == "LONG" else entry_price - 3.5 * risk
            reward = abs(tp2 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            checklist_details.append(f"📐 Tự động điều chỉnh khoảng cách TP theo Risk thực tế (R:R 1:2.0)")

        # Nếu R:R vẫn không đạt tối thiểu (1:2), bỏ kèo
        if risk_reward < Config.MIN_RR_RATIO:
            logger.debug(f"Bỏ qua {symbol} {direction} vì R:R 1:{risk_reward:.2f} < 1:{Config.MIN_RR_RATIO}")
            return None

        # Đề xuất leverage dựa trên Grade
        if grade == "A+":
            leverage_suggestion = min(50, Config.MAX_LEVERAGE)
        elif grade == "A":
            leverage_suggestion = min(30, Config.MAX_LEVERAGE)
        else:
            leverage_suggestion = min(15, Config.MAX_LEVERAGE)

        # Tính position size (Quy tắc 2%)
        risk_amount = Config.ACCOUNT_BALANCE * (Config.MAX_RISK_PERCENT / 100)
        lot_size_suggestion = risk_amount / risk if risk > 0 else 0

        # Build signal object
        signal = TradingSignal(
            symbol=symbol,
            direction=direction,
            setup_type=setup_type,
            grade=grade,
            entry_price=entry_price,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            risk_reward=risk_reward,
            lot_size_suggestion=lot_size_suggestion,
            leverage_suggestion=leverage_suggestion,
            atr_value=atr,
            confluence_score=confluence_score,
            trigger_detail="\n".join(checklist_details),
            squeeze_detail=f"EMA Spread: {last.get('ema_spread_pct', 0):.2f}% | Dragon Width: {last.get('dragon_width', 0):.2f}%",
            # FVG E-Book details
            fvg_type=chosen_fvg_type,
            fvg_quality=chosen_fvg_quality,
            fvg_is_ifvg=chosen_fvg_is_ifvg,
            fvg_is_rebalance=chosen_fvg_is_rebalance,
            fvg_zone_top=chosen_fvg_zone_top,
            fvg_zone_bottom=chosen_fvg_zone_bottom,
        )


        return signal

    async def _get_hot_symbols(self) -> list:
        """Lấy danh sách các đồng coin có dòng tiền mạnh nhất (Money Flow Score cao nhất)"""
        import time
        now = time.time()
        
        # Tránh quét trùng lặp khi tiến trình trước chưa hoàn thành
        if getattr(self, '_is_updating_hot_symbols', False):
            if hasattr(self, '_hot_symbols_cache') and self._hot_symbols_cache:
                return self._hot_symbols_cache
            try:
                return await self.data_fetcher.get_symbol_names(Config.MAX_SYMBOLS_PER_SCAN)
            except Exception:
                return Config.SYMBOLS
        
        # Cập nhật danh sách hot symbols mỗi 15 phút (900 giây)
        if not hasattr(self, '_hot_symbols_cache') or not self._hot_symbols_cache or (now - getattr(self, '_last_hot_symbols_update', 0) > 900):
            try:
                self._is_updating_hot_symbols = True
                logger.info("🔥 Đang quét xếp hạng dòng tiền (Ecosystem Money Flow) để lọc coin tiềm năng...")
                from ecosystem_scanner import EcosystemScanner
                eco_scanner = EcosystemScanner()
                # Quét nhanh danh sách tất cả các cặp
                results = await eco_scanner.scan_all()
                await eco_scanner.close()
                
                # Lọc lấy các coin có score >= 35 (hạ xuống 35 để quét rộng hơn đối với các coin cap nhỏ)
                hot_results = [r['full_symbol'] for r in results if r['score'] >= 35]
                if len(hot_results) < 30:
                    hot_results = [r['full_symbol'] for r in results[:40]]
                
                self._hot_symbols_cache = hot_results[:Config.MAX_SYMBOLS_PER_SCAN]  # Giới hạn theo cấu hình
                self._last_hot_symbols_update = now
                logger.info(f"✅ Đã cập nhật danh sách {len(self._hot_symbols_cache)} coin có dòng tiền mạnh nhất!")
            except Exception as e:
                logger.error(f"❌ Lỗi quét xếp hạng dòng tiền: {e}")
                # Fallback về danh sách volume lớn thông thường
                try:
                    self._hot_symbols_cache = await self.data_fetcher.get_symbol_names(Config.MAX_SYMBOLS_PER_SCAN)
                    self._last_hot_symbols_update = now
                except Exception:
                    self._hot_symbols_cache = Config.SYMBOLS
                    self._last_hot_symbols_update = now
            finally:
                self._is_updating_hot_symbols = False
                    
        return self._hot_symbols_cache

    # ═══════════════════════════════════════
    # SCAN ALL
    # ═══════════════════════════════════════

    async def scan_all(self, on_signal_found=None) -> list:
        """Quét tất cả symbols song song với Chunking — Tránh tràn RAM (OOM) trên Render"""
        import asyncio
        import gc
        signals = []

        if Config.SCAN_ALL_SYMBOLS:
            symbols = await self._get_hot_symbols()
            # Đảm bảo XAU/USDT luôn được quét
            xau_symbol = "XAU/USDT:USDT"
            if xau_symbol not in symbols:
                symbols = list(symbols) + [xau_symbol]
            logger.info(f"🌐 Quét {len(symbols)} cặp USDT Futures dòng tiền mạnh song song (bằng Chunking)...")
        else:
            symbols = list(Config.SYMBOLS)
            xau_symbol = "XAU/USDT:USDT"
            if xau_symbol not in symbols:
                symbols.append(xau_symbol)

        total = len(symbols)

        async def worker(symbol, index):
            try:
                signal = await self.scan_symbol(symbol)
                if signal and signal.is_valid:
                    signals.append(signal)
                    logger.info(
                        f"   🎯 {signal.grade} {symbol} {signal.direction} | "
                        f"{signal.setup_type} | R:R 1:{signal.risk_reward:.1f}"
                    )
                    if on_signal_found:
                        await on_signal_found(signal)
            except Exception as e:
                logger.debug(f"   Bỏ qua {symbol}: {e}")
            finally:
                if index % 20 == 0 or index == total:
                    logger.info(f"   Tiến độ quét: {index}/{total}...")

        # Chạy song song các tasks theo Chunk 20 mã
        chunk_size = 20
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            tasks = [worker(sym, i + idx + 1) for idx, sym in enumerate(chunk)]
            await asyncio.gather(*tasks)
            # Dọn rác RAM ngay lập tức sau mỗi 20 mã để chống tràn bộ nhớ (OOM)
            gc.collect()

        logger.info(f"📊 Hoàn tất: {total} cặp → {len(signals)} tín hiệu")
        return signals
