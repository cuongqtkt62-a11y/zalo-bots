// ============================================================
// test-post-image.js — Zalo Posting Test Script
// ============================================================
// Lệnh chạy:
//   1. Tạm dừng bot chính (nếu đang chạy)
//   2. node src/tests/test-post-image.js
// ============================================================

import { Zalo, ThreadType } from 'zca-js';
import { readFileSync, existsSync, unlinkSync, statSync } from 'fs';
import path from 'path';
import config from '../config.js';
import logger from '../logger.js';
import aiEngine from '../ai-engine.js';
import dataStore from '../data-store.js';
import { createCard } from '../image-generator.js';

async function testPostImage() {
  console.log('🏁 Khởi động test đăng bài chăm sóc kèm ảnh...');

  const credPath = config.zalo.credentialsPath;
  if (!existsSync(credPath)) {
    console.error('❌ Không tìm thấy credentials! Hãy chạy npm run login trước.');
    process.exit(1);
  }

  // Lấy danh sách nhóm đã duyệt
  const groups = dataStore.getApprovedGroups();
  
  let targetGroup = null;
  if (process.argv[2]) {
    const argId = process.argv[2].trim();
    const matched = groups.find(g => g.id === argId);
    if (matched) {
      targetGroup = matched;
    } else {
      console.warn(`⚠️ Không tìm thấy ID ${argId} trong danh sách nhóm đã duyệt. Sử dụng cấu hình tạm thời...`);
      targetGroup = {
        id: argId,
        name: "NHÀ QUẢNG BÁ 365 (Nhàu Tâm An)",
        purpose: "Kinh doanh sản phẩm Nhàu Thảo Mộc Tâm An dựa trên nền tảng chăm sóc sức khoẻ chủ động"
      };
    }
  } else {
    if (groups.length === 0) {
      console.error('❌ Không có nhóm nào được duyệt trong database! Hãy duyệt ít nhất 1 nhóm trước.');
      process.exit(1);
    }
    targetGroup = groups[0];
  }

  console.log(`🎯 Nhóm thử nghiệm: "${targetGroup.name}" (${targetGroup.id})`);
  console.log(`💬 Mục đích: "${targetGroup.purpose}"`);

  // Load credentials
  const credentials = JSON.parse(readFileSync(credPath, 'utf-8'));
  
  console.log('🔌 Đang kết nối tới Zalo...');
  const zalo = new Zalo();
  const api = await zalo.login({
    cookie: credentials.cookies,
    imei: credentials.imei,
    userAgent: credentials.userAgent,
  });
  console.log('✅ Đã kết nối thành công!');

  try {
    const timeOfDay = 'Buổi trưa (12:00)';
    console.log(`🤖 Đang sinh bài đăng AI cho ${timeOfDay}...`);
    
    const nurturingData = await aiEngine.generateGroupNurturingPost(targetGroup.name, targetGroup.purpose, timeOfDay);
    console.log('\n--- BÀI VIẾT TỪ AI ---');
    console.log(nurturingData.post);
    console.log('----------------------');
    console.log(`Quote card text: "${nurturingData.quote}"`);

    console.log('🎨 Đang tạo ảnh Quote Card...');
    const tempImagePath = await createCard(nurturingData.quote, timeOfDay, targetGroup.id);
    console.log(`✅ Đã tạo ảnh tạm: ${tempImagePath}`);

    // Đọc ảnh thành Buffer và truyền kèm metadata để tránh lỗi imageMetadataGetter của zca-js
    const imageBuffer = readFileSync(tempImagePath);
    const stats = statSync(tempImagePath);
    const attachment = {
      data: imageBuffer,
      filename: `nurturing_${targetGroup.id}.png`,
      metadata: {
        totalSize: stats.size,
        width: 800,
        height: 800
      }
    };

    console.log('📤 Đang gửi bài viết kèm ảnh lên Zalo...');
    const msgObject = {
      msg: nurturingData.post,
      attachments: [attachment]
    };

    await api.sendMessage(msgObject, targetGroup.id, ThreadType.Group);
    console.log('✅ Đã gửi thành công!');

    // Xóa ảnh tạm
    if (tempImagePath && existsSync(tempImagePath)) {
      unlinkSync(tempImagePath);
      console.log('🧹 Đã dọn dẹp ảnh tạm thời.');
    }

  } catch (err) {
    console.error('❌ Thất bại:', err);
  } finally {
    // Đóng listener và giải phóng tài nguyên
    if (api && api.listener) {
      api.listener.stop();
    }
    console.log('🏁 Kết thúc kiểm thử.');
    process.exit(0);
  }
}

testPostImage().catch(err => console.error('💥 Lỗi nghiêm trọng:', err));
