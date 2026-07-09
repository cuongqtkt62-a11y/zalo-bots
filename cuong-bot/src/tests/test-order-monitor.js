// ============================================================
// test-order-monitor.js — Test Google Sheets Order Monitor
// ============================================================
import fs from 'fs';
import path from 'path';
import axios from 'axios';
import dotenv from 'dotenv';

// Load .env
dotenv.config({ path: path.join(process.cwd(), '.env') });

const STATE_FILE = path.join(process.cwd(), 'data', 'order_monitor_state.json');

// Mock API
const mockApi = {
  sendMessage: async (msg, adminId) => {
    console.log(`\n✉️ [MOCK ZALO SEND TO ${adminId}]:`);
    console.log(msg);
    console.log('--------------------------------------');
  }
};

async function runTest() {
  console.log('🧪 Bắt đầu kiểm thử Order Monitor...');

  // Sao lưu file state cũ nếu có
  let backupState = null;
  if (fs.existsSync(STATE_FILE)) {
    backupState = fs.readFileSync(STATE_FILE, 'utf-8');
    console.log('- Đã sao lưu file state hiện tại.');
  }

  try {
    // 1. Tạo state giả lập (lấy mốc thời gian ngày 12/06/2026 để test lọc đơn hàng mới sau mốc này)
    const testState = {
      lastProcessedTimestamp: '12/06/2026 04:00:00'
    };
    fs.writeFileSync(STATE_FILE, JSON.stringify(testState, null, 2));
    console.log(`- Đã thiết lập test state với lastProcessedTimestamp: ${testState.lastProcessedTimestamp}`);

    // 2. Import module giám sát động để chạy thử
    // (Dùng dynamic import để load config & state mới ghi)
    const { startOrderMonitor } = await import('../order-monitor.js');

    // Chạy kiểm thử thủ công (gọi hàm start và để nó tự fetch)
    startOrderMonitor(mockApi);

    // Chờ 8 giây để axios fetch và in kết quả ra console
    console.log('⏳ Đang fetch Google Sheets và xử lý dữ liệu...');
    await new Promise(r => setTimeout(r, 8000));

  } finally {
    // Khôi phục lại state ban đầu để tránh làm hỏng tiến trình chạy thật
    if (backupState) {
      fs.writeFileSync(STATE_FILE, backupState);
      console.log('- Đã khôi phục lại file state gốc.');
    } else if (fs.existsSync(STATE_FILE)) {
      fs.unlinkSync(STATE_FILE);
      console.log('- Đã dọn dẹp file test state.');
    }
    console.log('🧪 TEST HOÀN TẤT!');
    process.exit(0);
  }
}

runTest().catch(console.error);
