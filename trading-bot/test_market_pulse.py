"""
Test script — Gửi thử bản tin Nhịp Đập Thị Trường
"""
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
)

from market_pulse import MarketPulse
from telegram_notifier import TelegramNotifier


async def main():
    print("🫀 Bắt đầu tạo bản tin Nhịp Đập Thị Trường...\n")

    pulse = MarketPulse()
    notifier = TelegramNotifier()

    try:
        messages = await pulse.generate_pulse()

        print(f"✅ Tạo xong {len(messages)} tin nhắn\n")
        for i, msg in enumerate(messages, 1):
            print(f"{'='*60}")
            print(f"TIN NHẮN {i} ({len(msg)} chars):")
            print(f"{'='*60}")
            # In ra bản text (bỏ HTML tags để đọc dễ hơn)
            import re
            plain = re.sub(r'<[^>]+>', '', msg)
            print(plain)
            print()

        # Gửi qua Telegram
        print("📤 Đang gửi qua Telegram...")
        await notifier.send_market_pulse(messages)
        print("✅ Đã gửi thành công!")

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await pulse.close()


if __name__ == "__main__":
    asyncio.run(main())
