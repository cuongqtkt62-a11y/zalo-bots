// ============================================================
// login.js — Đăng nhập Zalo bằng QR Code
// ============================================================
// Chạy file này 1 LẦN DUY NHẤT để đăng nhập:
//   node src/login.js
//
// Sau khi scan QR thành công, credentials sẽ được lưu vào
// file zalo-credentials.json để dùng cho các lần chạy sau.
// ============================================================

import { Zalo, LoginQRCallbackEventType } from 'zca-js';
import { writeFileSync } from 'fs';
import config from './config.js';
import logger from './logger.js';

async function login() {
  console.log('\n╔══════════════════════════════════════════════════════════╗');
  console.log('║       🔐 ĐĂNG NHẬP ZALO — SCAN QR CODE                  ║');
  console.log('╠══════════════════════════════════════════════════════════╣');
  console.log('║  1. Mở app Zalo trên điện thoại                        ║');
  console.log('║  2. Vào Cài đặt > Tài khoản & Bảo mật                  ║');
  console.log('║  3. Chọn "Đăng nhập bằng mã QR"                        ║');
  console.log('║  4. Scan mã QR hiện ra bên dưới                        ║');
  console.log('╚══════════════════════════════════════════════════════════╝\n');

  try {
    let credentials = null;
    const zalo = new Zalo();
    const api = await zalo.loginQR({}, async (event) => {
      if (event.type === LoginQRCallbackEventType.QRCodeGenerated) {
        await event.actions.saveToFile();
      } else if (event.type === LoginQRCallbackEventType.GotLoginInfo) {
        credentials = {
          cookies: event.data.cookie,
          imei: event.data.imei,
          userAgent: event.data.userAgent,
          loginTime: new Date().toISOString(),
        };
      }
    });

    if (!credentials) {
      // Fallback
      const ctx = api.getContext();
      if (ctx && ctx.cookie) {
        credentials = {
          cookies: ctx.cookie.serializeSync().cookies,
          imei: ctx.imei,
          userAgent: ctx.userAgent,
          loginTime: new Date().toISOString(),
        };
      }
    }

    if (!credentials) {
      throw new Error('Không lấy được session đăng nhập từ Zalo. Vui lòng quét lại.');
    }

    const credPath = config.zalo.credentialsPath;
    writeFileSync(credPath, JSON.stringify(credentials, null, 2));

    logger.info(`✅ Đăng nhập thành công!`);
    logger.info(`📁 Credentials đã lưu tại: ${credPath}`);
    console.log('\n🎉 Bạn có thể chạy bot bằng lệnh: npm start\n');

  } catch (error) {
    logger.error('❌ Đăng nhập thất bại', { error: error.message });
    console.error('\n❌ Lỗi:', error.message);
    console.log('💡 Hãy thử lại. Đảm bảo app Zalo trên điện thoại đang mở.\n');
    process.exit(1);
  }
}

login();
