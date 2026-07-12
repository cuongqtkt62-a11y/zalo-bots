
### 4.5 — HỆ THỐNG KÍCH THÍCH CHỐNG NGỦ ĐÔNG (KEEP-ALIVE)
Do dịch vụ Web (Free) của Render sẽ tự động Sleep sau 15 phút nếu không có traffic, chúng ta sử dụng **GitHub Actions** (`.github/workflows/keep-alive.yml`) để tự động Ping vào các URL của Render mỗi 10 phút.
- **Hoàn toàn tự động**: Chỉ cần lệnh `git push`, GitHub Actions sẽ chạy ngầm 24/7 trên hạ tầng của Microsoft Azure.
- Không cần dùng UptimeRobot hay thủ công.
