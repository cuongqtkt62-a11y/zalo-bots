"""
Trading Signal Bot — Sonic R System
4 EMA: Dragon(34) + Trend(89) + Long(200) + Super(610)
3 Setup: A+ Golden Squeeze | A Dragon Bounce | B Deep Pullback

Features:
  - Signal deduplication (30 phút cooldown)
  - Daily P&L tracking
  - Auto-stop khi thua quá limit
  - Bản tin 7h sáng / 20h tối
  - Heartbeat mỗi 6 tiếng
"""
import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import Config
from signal_scanner import SignalScanner
from telegram_notifier import TelegramNotifier
from market_bulletin import MarketBulletin
from market_pulse import MarketPulse
from ai_convergence_scanner import AIDePINScanner
from mirofish_analyzer import MiroFishAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger("TradingBot")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("ccxt").setLevel(logging.WARNING)


class TradingBot:
    def __init__(self):
        self.scanner = SignalScanner()
        self.notifier = TelegramNotifier()
        self.scheduler = AsyncIOScheduler()
        self.scan_count = 0
        self.total_signals_found = 0
        self.start_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5

        # Signal deduplication
        self.sent_signals = {}  # {symbol: (direction, setup_type, timestamp)}

        # Daily tracking
        self.daily_signals = []
        self.last_reset_date = None

        # A+ Reminder queue: [(signal, remaining_attempts, next_send_time)]
        self.pending_reminders = []

    def _reset_daily_if_needed(self):
        """Reset tracking mỗi ngày mới"""
        today = datetime.now().date()
        if self.last_reset_date != today:
            self.daily_signals = []
            self.sent_signals = {}  # Reset cooldown mỗi ngày
            self.last_reset_date = today
            logger.info("📅 Ngày mới — reset tracking")

    def _should_send_signal(self, signal) -> bool:
        """Kiểm tra trước khi gửi tín hiệu — chống trùng"""
        now = datetime.now()
        key = signal.symbol

        # 1. Dedup — đã gửi cho symbol này chưa?
        if key in self.sent_signals:
            last_dir, last_type, last_time = self.sent_signals[key]
            elapsed = (now - last_time).total_seconds()
            if elapsed < Config.SIGNAL_COOLDOWN_SECONDS:
                if last_dir == signal.direction:
                    logger.debug(
                        f"⏳ Bỏ qua {key} {signal.direction} — "
                        f"còn {Config.SIGNAL_COOLDOWN_SECONDS - elapsed:.0f}s cooldown"
                    )
                    return False

        return True

    def _record_signal_sent(self, signal):
        """Ghi nhận tín hiệu đã gửi"""
        self.sent_signals[signal.symbol] = (
            signal.direction,
            signal.setup_type,
            datetime.now()
        )
        self.daily_signals.append({
            'symbol': signal.symbol,
            'direction': signal.direction,
            'grade': signal.grade,
            'setup': signal.setup_type,
            'score': signal.confluence_score,
            'time': datetime.now(),
        })

    async def _process_reminders(self):
        """Xử lý hàng đợi nhắc lại A+ — gửi nếu đã đến giờ"""
        now = datetime.now()
        still_pending = []
        for signal, remaining, next_time in self.pending_reminders:
            if now >= next_time and remaining > 0:
                attempt = 4 - remaining  # 1, 2, 3
                await self.notifier.send_urgent_signal(signal, attempt, 3)
                remaining -= 1
                if remaining > 0:
                    still_pending.append((signal, remaining, now + timedelta(minutes=5)))
            elif remaining > 0:
                still_pending.append((signal, remaining, next_time))
        self.pending_reminders = still_pending

    async def scan_and_notify(self):
        self.scan_count += 1
        self._reset_daily_if_needed()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"🔍 Quét lần #{self.scan_count} — {now}")

        # Xử lý nhắc lại A+ trước
        await self._process_reminders()

        try:
            async def on_signal(signal):
                if self._should_send_signal(signal):
                    self.total_signals_found += 1
                    self._record_signal_sent(signal)
                    logger.info(
                        f"🎯 GỬI NGAY: {signal.grade} {signal.symbol} {signal.direction} | "
                        f"{signal.setup_type} | Score: {signal.confluence_score}"
                    )
                    await self.notifier.send_signal(signal)

                    # Nếu A+ → lên lịch nhắc lại 3 lần, mỗi lần cách 5 phút
                    if signal.grade == "A+":
                        logger.info(f"🚨 A+ detected! Lên lịch nhắc lại 3 lần cho {signal.symbol}")
                        self.pending_reminders.append(
                            (signal, 3, datetime.now() + timedelta(minutes=5))
                        )

            signals = await self.scanner.scan_all(on_signal_found=on_signal)
            self.consecutive_errors = 0

            if not signals:
                logger.info(f"⏳ Quét {self.scan_count}: Chưa có setup Sonic R. Chờ tiếp...")

        except Exception as e:
            self.consecutive_errors += 1
            logger.error(f"❌ Lỗi quét lần #{self.scan_count}: {e}")

            if self.consecutive_errors == self.max_consecutive_errors:
                await self.notifier.send_status(
                    f"⚠️ <b>Cảnh báo Bot</b>\n\n"
                    f"Lỗi liên tục {self.consecutive_errors} lần.\n"
                    f"Lỗi gần nhất: {str(e)[:300]}\n\n"
                    f"Bot sẽ tiếp tục thử..."
                )

            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.warning("🔄 Tạo lại kết nối exchange...")
                try:
                    await self.scanner.data_fetcher.close()
                    self.scanner = SignalScanner()
                    self.consecutive_errors = 0
                except Exception:
                    pass

    async def send_heartbeat(self):
        """Gửi heartbeat mỗi 6 tiếng"""
        uptime = time.time() - self.start_time
        hours = int(uptime // 3600)
        mins = int((uptime % 3600) // 60)

        daily_count = len(self.daily_signals)
        grades = {}
        for s in self.daily_signals:
            g = s['grade']
            grades[g] = grades.get(g, 0) + 1
        grade_str = " | ".join([f"{k}: {v}" for k, v in sorted(grades.items())]) if grades else "Chưa có"

        await self.notifier.send_status(
            f"💚 <b>Bot Sonic R đang hoạt động</b>\n\n"
            f"⏱️ Uptime: {hours}h {mins}m\n"
            f"🔍 Đã quét: {self.scan_count} lần\n"
            f"🎯 Tín hiệu hôm nay: {daily_count} ({grade_str})\n"
            f"📊 Chế độ: Quét {Config.MAX_SYMBOLS_PER_SCAN} cặp Futures\n\n"
            f"<i>Sonic R — Dragon(34) + 89 + 200 + 610 🐉</i>"
        )

    async def send_4h_summary(self):
        """Gửi tóm tắt tín hiệu mỗi 4 tiếng — nhấn mạnh A+ chưa xem"""
        now = datetime.now()
        cutoff = now - timedelta(hours=4)

        # Lọc tín hiệu trong 4 tiếng qua
        recent_signals = [s for s in self.daily_signals if s['time'] >= cutoff]

        if not recent_signals:
            logger.info("📋 Không có tín hiệu nào trong 4 tiếng qua, bỏ qua tóm tắt")
            return

        await self.notifier.send_signal_summary(recent_signals)
        logger.info(f"📋 Đã gửi tóm tắt {len(recent_signals)} tín hiệu trong 4 tiếng qua")

    async def send_daily_bulletin(self):
        """Gửi bản tin thị trường 7h sáng & 20h tối"""
        now = datetime.now()
        session = "SÁNG" if now.hour < 12 else "TỐI"
        logger.info(f"📰 Đang tạo bản tin {session}...")

        try:
            bulletin = MarketBulletin(self.scanner.data_fetcher)
            message = await bulletin.generate_bulletin()
            await self.notifier.send_status(message)
            logger.info(f"📰 Đã gửi bản tin {session}")
        except Exception as e:
            logger.error(f"❌ Lỗi tạo bản tin: {e}")

    async def send_market_pulse(self):
        """Gửi bản tin Nhịp Đập Thị Trường mỗi giờ chẵn"""
        now = datetime.now()
        logger.info(f"🫀 Đang tạo bản tin Nhịp Đập Thị Trường {now.strftime('%H:00')}...")

        pulse = MarketPulse()
        try:
            messages = await pulse.generate_pulse()
            await self.notifier.send_market_pulse(messages)
            logger.info(f"🫀 Đã gửi bản tin Nhịp Đập Thị Trường {now.strftime('%H:00')}")
        except Exception as e:
            logger.error(f"❌ Lỗi tạo bản tin Nhịp Đập: {e}")
        finally:
            await pulse.close()

    async def send_daily_ai_report(self):
        """Gửi báo cáo AI Convergence Scanner định kỳ"""
        logger.info("🤖 Đang tạo báo cáo AI Convergence Scanner...")
        try:
            ai_scanner = AIDePINScanner()
            results = await ai_scanner.scan_all()
            html_report = ai_scanner.generate_html_report(results)
            await self.notifier.send_ai_report(html_report)
            await ai_scanner.close()
            logger.info("🤖 Đã gửi báo cáo AI Convergence Scanner")
        except Exception as e:
            logger.error(f"❌ Lỗi tạo báo cáo AI: {e}")

    async def send_macro_report(self):
        """Gửi báo cáo vĩ mô & chiến lược dòng tiền AI + Crypto"""
        logger.info("📊 Đang tạo báo cáo vĩ mô & dòng tiền...")
        try:
            from macro_monitor import MacroMonitor
            monitor = MacroMonitor()
            await monitor.run_monitor(send_telegram=True)
            await monitor.close()
            logger.info("📊 Đã gửi báo cáo vĩ mô và dòng tiền")
        except Exception as e:
            logger.error(f"❌ Lỗi tạo báo cáo vĩ mô: {e}")


    async def run_mirofish_scanner(self):
        """Chạy phân tích MiroFish định kỳ mỗi 5 phút"""
        logger.info("🎣 Đang chạy phân tích MiroFish (5 phút)...")
        analyzer = MiroFishAnalyzer()
        try:
            report = await analyzer.run_mirofish_analysis()
            await self.notifier.send_status(report)
            logger.info("🎣 Đã gửi báo cáo MiroFish qua Telegram")
        except Exception as e:
            logger.error(f"❌ Lỗi chạy phân tích MiroFish: {e}")
        finally:
            await analyzer.close()

    async def start(self):
        self.start_time = time.time()

        logger.info("=" * 60)
        logger.info("🐉 SONIC R TRADING BOT — Dragon(34) + 89 + 200 + 610")
        logger.info("=" * 60)

        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"❌ {e}")
            sys.exit(1)

        scan_mode = "🌐 TẤT CẢ Binance Futures" if Config.SCAN_ALL_SYMBOLS else ', '.join(Config.SYMBOLS)
        logger.info(f"📊 Chế độ: {scan_mode}")
        logger.info(f"🧭 Hướng giao dịch: {Config.TRADE_DIRECTION}")
        logger.info(f"⏱️ Chu kỳ quét: {Config.SCAN_INTERVAL_SECONDS}s")
        logger.info(f"🐉 EMA: Dragon(34) | Trend(89) | Long(200) | Super(610)")
        logger.info(f"🎯 Setup: VSA × ICT × Sonic R Confluence")
        logger.info(f"💰 Target: ${Config.DAILY_PROFIT_TARGET}/ngày | Risk {Config.MAX_RISK_PERCENT}%")
        logger.info(f"🛡️ R:R tối thiểu: 1:{Config.MIN_RR_RATIO}")
        logger.info(f"⏳ Signal cooldown: {Config.SIGNAL_COOLDOWN_SECONDS}s")

        await self.notifier.send_status(
            "🐉 <b>VSA × ICT × Sonic R Bot đã khởi động</b>\n\n"
            f"🌐 Quét TẤT CẢ cặp USDT Futures\n"
            f"🧭 Hướng giao dịch: <b>{Config.TRADE_DIRECTION}</b>\n"
            f"🔢 Top {Config.MAX_SYMBOLS_PER_SCAN} cặp | Chu kỳ {Config.SCAN_INTERVAL_SECONDS}s\n"
            f"💰 Vốn ${Config.ACCOUNT_BALANCE:,.0f} | Risk {Config.MAX_RISK_PERCENT}% | R:R ≥ 1:{Config.MIN_RR_RATIO}\n\n"
            "<b>📊 Hệ thống EMA:</b>\n"
            "🔵 Dragon Band: EMA 34 (High/Close/Low)\n"
            "🟠 Trend: EMA 89\n"
            "🟣 Long Trend: EMA 200\n"
            "⚪ Super Trend: EMA 610\n\n"
            "<b>🎯 Setup Hợp Nhất:</b>\n"
            "⭐ Sonic R × ICT Confluence (4 điều kiện hợp lưu):\n"
            "1. Giá nén tại cụm Sonic R\n"
            "2. Nến đảo chiều / rút chân tại cụm Sonic R\n"
            "3. Giá đã quét xong thanh khoản đáy/đỉnh gần nhất\n"
            "4. Fair Value Gap (FVG) - Entry đẹp tuyệt đối\n\n"
            "<i>VSA × ICT × Sonic R System 🐉</i>"
        )

        # Quét lần đầu (Chạy nền để không chặn Scheduler khởi động)
        asyncio.create_task(self.scan_and_notify())

        # Quét real-time
        self.scheduler.add_job(
            self.scan_and_notify,
            'interval',
            seconds=Config.SCAN_INTERVAL_SECONDS,
            id='signal_scanner',
            name='Sonic R Scanner',
            misfire_grace_time=60,
        )

        # Bản tin SÁNG 7:00
        self.scheduler.add_job(
            self.send_daily_bulletin,
            CronTrigger(hour=7, minute=0, timezone='Asia/Ho_Chi_Minh'),
            id='bulletin_morning',
            name='Bản tin sáng 7:00',
            misfire_grace_time=300,
        )

        # Bản tin TỐI 20:00
        self.scheduler.add_job(
            self.send_daily_bulletin,
            CronTrigger(hour=20, minute=0, timezone='Asia/Ho_Chi_Minh'),
            id='bulletin_evening',
            name='Bản tin tối 20:00',
            misfire_grace_time=300,
        )

        # Heartbeat mỗi 6 tiếng
        self.scheduler.add_job(
            self.send_heartbeat,
            'interval',
            hours=6,
            id='heartbeat',
            name='Heartbeat',
        )

        # Tóm tắt tín hiệu mỗi 4 tiếng (6h, 10h, 14h, 18h, 22h)
        self.scheduler.add_job(
            self.send_4h_summary,
            'interval',
            hours=4,
            id='signal_summary_4h',
            name='Tóm tắt 4 tiếng',
            misfire_grace_time=300,
        )

        # Nhịp Đập Thị Trường — mỗi giờ chẵn
        self.scheduler.add_job(
            self.send_market_pulse,
            CronTrigger(minute=0, timezone='Asia/Ho_Chi_Minh'),
            id='market_pulse_hourly',
            name='Nhịp Đập Thị Trường (mỗi giờ)',
            misfire_grace_time=300,
        )

        # Báo cáo AI Convergence (8:00 và 20:30)
        self.scheduler.add_job(
            self.send_daily_ai_report,
            CronTrigger(hour=8, minute=0, timezone='Asia/Ho_Chi_Minh'),
            id='ai_report_morning',
            name='Báo cáo AI Sáng 8:00',
            misfire_grace_time=300,
        )
        self.scheduler.add_job(
            self.send_daily_ai_report,
            CronTrigger(hour=20, minute=30, timezone='Asia/Ho_Chi_Minh'),
            id='ai_report_evening',
            name='Báo cáo AI Tối 20:30',
            misfire_grace_time=300,
        )

        # Báo cáo Vĩ mô & Chiến lược dòng tiền AI (8:15 và 20:45)
        self.scheduler.add_job(
            self.send_macro_report,
            CronTrigger(hour=8, minute=15, timezone='Asia/Ho_Chi_Minh'),
            id='macro_report_morning',
            name='Báo cáo Vĩ mô Sáng 8:15',
            misfire_grace_time=300,
        )
        self.scheduler.add_job(
            self.send_macro_report,
            CronTrigger(hour=20, minute=45, timezone='Asia/Ho_Chi_Minh'),
            id='macro_report_evening',
            name='Báo cáo Vĩ mô Tối 20:45',
            misfire_grace_time=300,
        )


        # # Quét địa chính trị & hàng hóa MiroFish mỗi 5 phút đúng khung giờ chẵn (15:00, 15:05, 15:10...)
        # self.scheduler.add_job(
        #     self.run_mirofish_scanner,
        #     CronTrigger(minute='*/5'),
        #     id='mirofish_scanner_5m',
        #     name='MiroFish 5m Scanner',
        #     misfire_grace_time=60,
        # )

        self.scheduler.start()
        logger.info("✅ Bot đang chạy. Nhịp Đập mỗi giờ, Bản tin 7h & 20h, AI Report 8h & 20h30. Ctrl+C để dừng.")

        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Đang dừng bot...")
            self.scheduler.shutdown()
            await self.scanner.data_fetcher.close()
            await self.notifier.send_status("🛑 <b>Sonic R Bot đã dừng</b>")
            logger.info("👋 Bot đã dừng.")


async def main():
    bot = TradingBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
