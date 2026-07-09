"""
Telegram Notifier — Sonic R Edition
Format mới với Grade (A+/A/B), setup type, EMA status
"""
import asyncio
import html
import re
from telegram import Bot
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from signal_scanner import TradingSignal
from config import Config
import logging

logger = logging.getLogger(__name__)


def escape(text: str) -> str:
    """Escape HTML special chars"""
    return html.escape(str(text)) if text else ""


def format_price(val: float) -> str:
    """Định dạng giá động theo độ lớn của giá trị"""
    if val is None or val == 0:
        return "0.00"
    abs_val = abs(val)
    if abs_val >= 100:
        return f"{val:,.2f}"
    elif abs_val >= 1:
        return f"{val:,.4f}"
    elif abs_val >= 0.01:
        return f"{val:,.5f}"
    else:
        return f"{val:,.7f}"


class TelegramNotifier:
    def __init__(self):
        # Tăng kích thước connection pool và kéo dài timeout để tránh lỗi Pool timeout khi có nhiều tín hiệu đồng thời
        request = HTTPXRequest(
            connection_pool_size=50,
            read_timeout=15.0,
            write_timeout=15.0,
            connect_timeout=10.0
        )
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN, request=request)
        self.chat_id = Config.TELEGRAM_CHAT_ID

    async def send_signal(self, signal: TradingSignal):
        message = self._format_signal_message(signal)
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_notification=False,
            )
            logger.info(f"📤 Đã gửi {signal.grade} {signal.symbol} {signal.direction}")
        except Exception as e:
            logger.error(f"❌ Lỗi gửi HTML: {e}")
            try:
                plain = self._format_signal_plain(signal)
                await self.bot.send_message(chat_id=self.chat_id, text=plain)
                logger.info(f"📤 Đã gửi plain text cho {signal.symbol}")
            except Exception as e2:
                logger.error(f"❌ Lỗi gửi plain text: {e2}")

    async def send_urgent_signal(self, signal: TradingSignal, attempt: int, total: int):
        """Gửi lặp lại tín hiệu A+ với cảnh báo khẩn cấp"""
        reminder_msg = (
            f"🚨🚨🚨 <b>NHẮC LẠI LẦN {attempt}/{total}</b> 🚨🚨🚨\n\n"
            f"⭐ <b>TÍN HIỆU A+ — ĐỪNG BỎ LỠ!</b>\n"
            f"{'━' * 30}\n"
            f"{'🟢' if signal.direction == 'LONG' else '🔴'} <b>{signal.direction} {escape(signal.symbol)}</b>\n"
            f"🎯 Score: {signal.confluence_score}/100\n"
            f"▶️ Entry: {format_price(signal.entry_price)}\n"
            f"🛑 SL: {format_price(signal.stop_loss)}\n"
            f"🎯 TP1: {format_price(signal.tp1)} | TP2: {format_price(signal.tp2)}\n"
            f"📐 R:R 1:{signal.risk_reward:.1f} | Leverage: {signal.leverage_suggestion}x\n\n"
            f"⚠️ <b>KỶ LUẬT:</b> SL ngay | TP1→hòa vốn | KHÔNG gồng"
        )
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=reminder_msg,
                parse_mode=ParseMode.HTML,
                disable_notification=False,
            )
            logger.info(f"🚨 Đã gửi nhắc lại A+ lần {attempt}/{total}: {signal.symbol} {signal.direction}")
        except Exception as e:
            logger.error(f"❌ Lỗi gửi nhắc lại A+: {e}")

    async def send_signal_summary(self, signals: list):
        """Gửi tóm tắt tín hiệu A+ trong 4 tiếng qua"""
        if not signals:
            return

        lines = []
        for s in signals:
            dir_emoji = "🟢" if s['direction'] == 'LONG' else "🔴"
            lines.append(
                f"{dir_emoji} <b>{escape(s['symbol'])}</b> {s['direction']} | "
                f"Grade {s['grade']} | Score {s.get('score', '?')} | "
                f"Lúc {s['time'].strftime('%H:%M')}"
            )

        msg = (
            f"📋 <b>TÓM TẮT TÍN HIỆU 4 TIẾNG QUA</b>\n"
            f"{'━' * 30}\n\n"
            + "\n".join(lines) + "\n\n"
            f"💡 <i>Kiểm tra Telegram để xem chi tiết từng tín hiệu</i>"
        )
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_notification=False,
            )
            logger.info(f"📋 Đã gửi tóm tắt {len(signals)} tín hiệu")
        except Exception as e:
            logger.error(f"❌ Lỗi gửi tóm tắt: {e}")

    async def send_status(self, message: str):
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"❌ Lỗi gửi status: {e}")
            try:
                plain = re.sub(r'<[^>]+>', '', message)
                await self.bot.send_message(chat_id=self.chat_id, text=plain)
            except Exception:
                pass

    def _format_signal_message(self, signal: TradingSignal) -> str:
        dir_emoji = "🟢" if signal.direction == "LONG" else "🔴"

        # Grade emoji
        grade_map = {
            "A+": "⭐ A+",
            "A": "🔵 A",
            "B": "🟡 B",
        }
        grade_label = grade_map.get(signal.grade, signal.grade)

        # Setup label
        setup_map = {
            "CONFLUENCE_SETUP": "Sonic R × ICT Confluence",
            "SQUEEZE_BREAKOUT": "🚀 Squeeze Breakout",
        }
        setup_label = setup_map.get(signal.setup_type, "Sonic R × ICT Confluence")

        # SL/TP percentages
        sl_pct = abs(signal.entry_price - signal.stop_loss) / signal.entry_price * 100 if signal.entry_price else 0
        tp1_pct = abs(signal.tp1 - signal.entry_price) / signal.entry_price * 100 if signal.entry_price else 0
        tp2_pct = abs(signal.tp2 - signal.entry_price) / signal.entry_price * 100 if signal.entry_price else 0
        tp3_pct = abs(signal.tp3 - signal.entry_price) / signal.entry_price * 100 if signal.entry_price else 0
        risk_amount = Config.ACCOUNT_BALANCE * (Config.MAX_RISK_PERCENT / 100)

        # EMA Order emoji
        ema_order_map = {
            "FULL_BULL": "📈 Full Bullish (P>D>89>200>610)",
            "PARTIAL_BULL": "📈 Partial Bullish (P>D>89)",
            "FULL_BEAR": "📉 Full Bearish (P<D<89<200<610)",
            "PARTIAL_BEAR": "📉 Partial Bearish (P<D<89)",
            "TANGLED": "↔️ Tangled (xoắn)",
        }
        ema_order_label = ema_order_map.get(signal.ema_order, signal.ema_order)

        trigger = escape(signal.trigger_detail)
        sym = escape(signal.symbol)
        escaped_ema_order = escape(ema_order_label)

        msg = (
            f"{'━' * 30}\n"
            f"{dir_emoji} <b>TÍN HIỆU {signal.direction}</b> — {sym}\n"
            f"{'━' * 30}\n\n"
            f"<b>Grade:</b> {grade_label}\n"
            f"<b>Setup:</b> {setup_label}\n"
            f"🎯 <b>Score:</b> {signal.confluence_score}/100\n\n"
            f"{'─' * 30}\n"
            f"📊 <b>SONIC R STATUS</b>\n"
            f"{'─' * 30}\n"
            f"<b>Dragon:</b> {signal.dragon_slope} | Width: {signal.dragon_width_pct:.2f}%\n"
            f"<b>EMA Spread:</b> {signal.ema_spread_pct:.2f}%\n"
            f"<b>EMA Order:</b> {escaped_ema_order}\n\n"
            f"{'─' * 30}\n"
            f"🎯 <b>TRIGGER</b>\n"
            f"{'─' * 30}\n"
            f"{trigger}\n\n"
        )

        # FVG E-Book section (chỉ hiện khi có FVG data)
        if signal.fvg_type:
            fvg_type_labels = {
                'CONSOLIDATION': '📗 Consolidation (Tốt nhất)',
                'BREAKAWAY': '📘 Breakaway (Momentum mạnh)',
                'REJECT': '📙 Reject (Cẩn thận)',
            }
            fvg_label = fvg_type_labels.get(signal.fvg_type, signal.fvg_type)
            fvg_dir = "Bullish" if signal.direction == "LONG" else "Bearish"

            msg += (
                f"{'─' * 30}\n"
                f"📊 <b>FVG E-BOOK</b>\n"
                f"{'─' * 30}\n"
                f"<b>Loại:</b> {fvg_label}\n"
                f"<b>Hướng:</b> {fvg_dir} FVG\n"
                f"<b>Quality:</b> {signal.fvg_quality}/100\n"
            )
            if signal.fvg_zone_top > 0 and signal.fvg_zone_bottom > 0:
                msg += f"<b>FVG Zone:</b> {format_price(signal.fvg_zone_bottom)} → {format_price(signal.fvg_zone_top)}\n"
            if signal.fvg_is_ifvg:
                msg += "⚡ <b>Inverse FVG (IFVG)</b> — Đổi cấu trúc!\n"
            if signal.fvg_is_rebalance:
                msg += "🧲 <b>Rebalance Entry</b> — Giá đang fill FVG\n"
            msg += "\n"

        msg += (
            f"{'─' * 30}\n"
            f"💰 <b>KẾ HOẠCH</b>\n"
            f"{'─' * 30}\n"
            f"▶️ Entry: {format_price(signal.entry_price)}\n"
            f"🛑 SL: {format_price(signal.stop_loss)} (-{sl_pct:.2f}%)\n"
            f"🎯 TP1: {format_price(signal.tp1)} (+{tp1_pct:.2f}%) → Dời SL về Entry\n"
            f"🎯 TP2: {format_price(signal.tp2)} (+{tp2_pct:.2f}%)\n"
            f"🎯 TP3: {format_price(signal.tp3)} (+{tp3_pct:.2f}%) trailing\n\n"
            f"📐 R:R 1:{signal.risk_reward:.1f} | ATR {format_price(signal.atr_value)}\n"
            f"📦 Lot: {signal.lot_size_suggestion:,.4f} | Leverage: {signal.leverage_suggestion}x\n"
            f"💵 Risk ${risk_amount:.2f} | Balance ${Config.ACCOUNT_BALANCE:,.0f}\n\n"
            f"⚠️ <b>KỶ LUẬT:</b> SL ngay | TP1→hòa vốn | KHÔNG gồng"
        )
        return msg

    def _format_signal_plain(self, signal: TradingSignal) -> str:
        """Fallback plain text"""
        dir_emoji = "🟢" if signal.direction == "LONG" else "🔴"
        sl_pct = abs(signal.entry_price - signal.stop_loss) / signal.entry_price * 100 if signal.entry_price else 0

        return (
            f"{dir_emoji} TÍN HIỆU {signal.direction} — {signal.symbol}\n"
            f"Grade: {signal.grade} | {signal.setup_type}\n"
            f"Score: {signal.confluence_score}/100 | R:R 1:{signal.risk_reward:.1f}\n\n"
            f"Entry: {format_price(signal.entry_price)}\n"
            f"SL: {format_price(signal.stop_loss)} (-{sl_pct:.2f}%)\n"
            f"TP1: {format_price(signal.tp1)} | TP2: {format_price(signal.tp2)} | TP3: {format_price(signal.tp3)}\n\n"
            f"Leverage: {signal.leverage_suggestion}x\n"
            f"⚠️ Đặt SL ngay | TP1 hit → dời SL về Entry"
        )

    async def send_ai_report(self, html_report: str):
        """Gửi báo cáo AI Convergence Scanner"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=html_report,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            logger.info("📤 Đã gửi báo cáo AI Convergence Scanner")
        except Exception as e:
            logger.error(f"❌ Lỗi gửi báo cáo AI Convergence: {e}")
            try:
                plain = re.sub(r'<[^>]+>', '', html_report)
                await self.bot.send_message(chat_id=self.chat_id, text=plain)
            except Exception:
                pass

    async def send_market_pulse(self, messages: list):
        """Gửi bản tin Nhịp Đập Thị Trường (có thể nhiều tin nhắn)"""
        for i, msg in enumerate(messages):
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                    disable_notification=(i > 0),  # Chỉ notify tin nhắn đầu
                )
                if i < len(messages) - 1:
                    await asyncio.sleep(0.5)  # Tránh rate limit
            except Exception as e:
                logger.error(f"❌ Lỗi gửi Market Pulse msg {i+1}: {e}")
                try:
                    plain = re.sub(r'<[^>]+>', '', msg)
                    await self.bot.send_message(chat_id=self.chat_id, text=plain)
                except Exception:
                    pass
        logger.info(f"📤 Đã gửi bản tin Nhịp Đập Thị Trường ({len(messages)} tin nhắn)")


