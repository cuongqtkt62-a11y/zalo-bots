// ============================================================
// test-image.js — Image Generation Test Script
// ============================================================
// Lệnh chạy: node src/tests/test-image.js
// Script này sinh ảnh mẫu với các buổi khác nhau để kiểm tra
// xem dải màu, chữ có bị tràn và logo có hoạt động không.
// ============================================================

import fs from 'fs';
import path from 'path';
import { createCard } from '../image-generator.js';

async function testImageGen() {
  console.log('🏁 Khởi động test sinh ảnh Quote/Tip Card...\n');

  // Đảm bảo có thư mục data/logos để test
  const logosDir = path.join(process.cwd(), 'data', 'logos');
  if (!fs.existsSync(logosDir)) {
    fs.mkdirSync(logosDir, { recursive: true });
  }

  const testCases = [
    {
      text: "Kỷ luật thép là chìa khóa mở ra cánh cửa tự do tài chính. Giao dịch thong dong, tâm lý vững vàng.",
      timeOfDay: "Buổi sáng (8:00)",
      groupId: "morning_test"
    },
    {
      text: "Tip SMC: Fair Value Gap (FVG) xuất hiện khi phe mua/phe bán đẩy giá quá mạnh tạo khoảng trống thanh khoản.",
      timeOfDay: "Buổi trưa (12:00)",
      groupId: "noon_test"
    },
    {
      text: "Hãy tắt máy tính và dành thời gian cho gia đình. Một ngày giao dịch hiệu quả bắt đầu từ giấc ngủ ngon tối nay.",
      timeOfDay: "Buổi tối (19:00)",
      groupId: "night_test"
    }
  ];

  for (const tc of testCases) {
    console.log(`➡️  Đang tạo ảnh cho: ${tc.timeOfDay}...`);
    try {
      const filePath = await createCard(tc.text, tc.timeOfDay, tc.groupId);
      console.log(`✅ Thành công! Ảnh được lưu tại: ${filePath}`);
      console.log(`   Kích thước file: ${fs.statSync(filePath).size} bytes\n`);
    } catch (err) {
      console.error(`❌ Thất bại khi sinh ảnh cho ${tc.timeOfDay}:`, err);
    }
  }

  console.log('🎉 Đã hoàn thành test sinh ảnh! Vui lòng kiểm tra các file ảnh kết quả trong thư mục data/temp_images/');
}

testImageGen().catch(err => console.error('💥 Lỗi không mong muốn:', err));
