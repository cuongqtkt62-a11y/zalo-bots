// ============================================================
// change-name.js — Thay đổi biệt danh Zalo
// ============================================================
import { Zalo } from 'zca-js';
import { readFileSync, existsSync } from 'fs';
import config from './config.js';
import logger from './logger.js';

async function changeName() {
  const credPath = config.zalo.credentialsPath;

  if (!existsSync(credPath)) {
    console.error('❌ File credentials không tồn tại. Hãy đăng nhập trước.');
    process.exit(1);
  }

  const credentials = JSON.parse(readFileSync(credPath, 'utf-8'));
  const zalo = new Zalo();

  logger.info('🔌 Connecting to Zalo...');
  const api = await zalo.login({
    cookie: credentials.cookies,
    imei: credentials.imei,
    userAgent: credentials.userAgent,
  });

  logger.info('ℹ️ Fetching current account info...');
  const res = await api.fetchAccountInfo();
  
  if (!res || !res.profile) {
    logger.error('❌ Failed to fetch account info', res);
    process.exit(1);
  }

  const currentInfo = res.profile;
  logger.info('👤 Current account info loaded', {
    name: currentInfo.displayName || currentInfo.zaloName,
    dob: currentInfo.sdob,
    gender: currentInfo.gender,
  });

  const newName = 'Lưu Bích Assistant';
  logger.info(`✍️ Changing name to: "${newName}"...`);

  try {
    const updateRes = await api.updateProfile({
      profile: {
        name: newName,
        dob: '1985-04-23',
        gender: currentInfo.gender || 0,
      },
      biz: currentInfo.biz || null
    });

    logger.info('✅ Profile updated successfully!', updateRes);
    console.log(`\n🎉 Đã đổi tên biệt danh Zalo thành công thành: "${newName}"!\n`);
  } catch (error) {
    logger.error('❌ Failed to update profile name', { error: error.message });
  }

  process.exit(0);
}

changeName().catch(console.error);
