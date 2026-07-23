#!/bin/sh
set -e

echo "🚀 Starting Zalo AI Monolith..."

# 1. Tải dữ liệu từ GitHub Gist
node gist-sync.js download || true

# 2. Khởi động vòng lặp đồng bộ Gist ngầm
node gist-sync.js watch &

# 3. Khởi động toàn bộ hệ thống bằng Monolith
node monolith.js
