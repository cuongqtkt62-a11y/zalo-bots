import { Zalo, ThreadType } from 'zca-js';
import { readFileSync, statSync, existsSync, unlinkSync } from 'fs';
import path from 'path';
import config from '../config.js';

async function testPostImage() {
  const credPath = config.zalo.credentialsPath;
  const credentials = JSON.parse(readFileSync(credPath, 'utf-8'));
  const zca = new Zalo({ cookie: credentials.cookie, imei: credentials.imei, userAgent: credentials.userAgent, secretKey: credentials.secretKey });
  const api = await zca.loginCookie();
  const targetGroupId = "986005107155112476";
  const tempImagePath = path.resolve('../data/logos/logo1.png');

  console.log('📤 Đang gửi ảnh bằng FILE PATH STRING...');
  try {
    await api.sendMessage({ msg: "Test image using FILE PATH", attachments: [tempImagePath] }, targetGroupId, ThreadType.Group);
    console.log('✅ Gửi FILE PATH thành công!');
  } catch (err) {
    console.error('❌ Gửi FILE PATH thất bại:', err);
  }

  process.exit(0);
}
testPostImage().catch(err => console.error('Lỗi:', err));
