// ============================================================
// test-send-msg.js — Kiểm tra gửi tin nhắn từ bot tới user
// ============================================================
import { Zalo } from 'zca-js';
import { readFileSync, existsSync } from 'fs';
import config from '../config.js';

async function testSend() {
  const credPath = config.zalo.credentialsPath;
  if (!existsSync(credPath)) {
    console.error('❌ File credentials không tồn tại!');
    return;
  }

  const credentials = JSON.parse(readFileSync(credPath, 'utf-8'));
  console.log('🔌 Đang kết nối Zalo...');
  const zalo = new Zalo({ selfListen: true });
  
  try {
    const api = await zalo.login({
      cookie: credentials.cookies,
      imei: credentials.imei,
      userAgent: credentials.userAgent,
    });
    console.log('✅ Đã đăng nhập thành công!');
    
    const targetUserId = '7923561941510836137'; // ID Zalo của anh Cường
    console.log(`💬 Đang gửi tin nhắn thử tới ID: ${targetUserId}...`);
    
    await api.sendMessage('🤖 Đây là tin nhắn kiểm tra hệ thống kết nối Zalo. Nếu anh thấy tin nhắn này, nghĩa là kết nối vẫn hoạt động!', targetUserId);
    console.log('✅ GỬI TIN NHẮN THÀNH CÔNG! Hãy kiểm tra Zalo của anh.');
  } catch (err) {
    console.error('❌ GỬI TIN NHẮN THẤT BẠI:', err.message);
  }
}

testSend();
