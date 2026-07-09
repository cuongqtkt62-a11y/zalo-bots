#!/bin/bash
# ============================================
# 🚀 SCRIPT TỰ ĐỘNG CÀI ĐẶT BOT TRADING
# Chạy trên VPS Ubuntu (Oracle Cloud)
# ============================================

set -e

echo "============================================"
echo "🚀 BẮT ĐẦU CÀI ĐẶT TRADING BOT"
echo "============================================"

# 1. Cập nhật hệ thống
echo ""
echo "📦 Bước 1/5: Cập nhật hệ thống..."
sudo apt update -y && sudo apt upgrade -y

# 2. Cài Python
echo ""
echo "🐍 Bước 2/5: Cài đặt Python 3..."
sudo apt install python3 python3-pip python3-venv -y

echo "   Python version: $(python3 --version)"

# 3. Cài đặt thư viện
echo ""
echo "📚 Bước 3/5: Cài đặt thư viện Python..."
cd ~/trading-telegram-bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Test nhanh
echo ""
echo "🧪 Bước 4/5: Test kết nối..."
python3 -c "
from config import Config
Config.validate()
print('   ✅ Cấu hình OK')
print(f'   📊 Symbols: {Config.SYMBOLS}')
print(f'   💰 Vốn: \${Config.ACCOUNT_BALANCE}')
"

# 5. Tạo systemd service
echo ""
echo "⚙️ Bước 5/5: Cài đặt chạy 24/7..."

CURRENT_USER=$(whoami)
BOT_DIR=$(pwd)

sudo tee /etc/systemd/system/trading-bot.service > /dev/null <<EOF
[Unit]
Description=VSA-ICT-H5 Trading Signal Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot

# Đợi 5 giây rồi kiểm tra
sleep 5

echo ""
echo "============================================"
echo "✅ CÀI ĐẶT HOÀN TẤT!"
echo "============================================"
echo ""

if sudo systemctl is-active --quiet trading-bot; then
    echo "🟢 Bot đang chạy 24/7!"
    echo ""
    echo "📱 Kiểm tra Telegram — sẽ nhận được tin nhắn khởi động"
    echo ""
    echo "📋 Các lệnh quản lý:"
    echo "   Xem trạng thái:    sudo systemctl status trading-bot"
    echo "   Xem log:           sudo journalctl -u trading-bot -f"
    echo "   Dừng bot:          sudo systemctl stop trading-bot"
    echo "   Khởi động lại:     sudo systemctl restart trading-bot"
    echo ""
    echo "🎯 Bot sẽ TỰ KHỞI ĐỘNG lại khi VPS reboot hoặc bot bị lỗi"
else
    echo "🔴 Bot chưa chạy. Kiểm tra lỗi bằng:"
    echo "   sudo journalctl -u trading-bot -n 50"
fi

echo ""
echo "============================================"
