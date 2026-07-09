#!/bin/sh
set -e

echo "🚀 Starting Hugging Face Deployment Entrypoint..."

# 1. Tải dữ liệu từ GitHub Gist
node gist-sync.js download || true

# 2. Start PM2 services (bots and health check server)

# 3. Start PM2 services in the background
npx -y pm2 start ecosystem.config.cjs
npx -y pm2 logs &

# 4. Chạy vòng lặp upload dữ liệu lên Gist mỗi 30 giây
node gist-sync.js watch
