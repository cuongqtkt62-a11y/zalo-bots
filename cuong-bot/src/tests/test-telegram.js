// ============================================================
// test-telegram.js — Kiểm thử gửi thông báo qua Telegram
// ============================================================
import { sendEscalationAlert } from '../telegram-alert.js';

async function runTest() {
  console.log('🧪 Bắt đầu test gửi thông báo sang Telegram...');
  
  const testPayload = {
    senderName: 'Khách hàng Demo',
    threadId: '1234567890',
    message: 'Chào bạn, mình muốn đăng ký mua bot tín hiệu SMC 24/7 và hỏi học phí lớp SMC-4EMA.',
    intent: 'Mua hàng/Đăng ký',
  };

  const success = await sendEscalationAlert(testPayload);
  
  if (success) {
    console.log('✅ TEST THÀNH CÔNG! Hãy kiểm tra Telegram để xem tin nhắn.');
  } else {
    console.error('❌ TEST THẤT BẠI! Vui lòng kiểm tra file cấu hình .env hoặc log lỗi ở trên.');
  }
}

runTest();
