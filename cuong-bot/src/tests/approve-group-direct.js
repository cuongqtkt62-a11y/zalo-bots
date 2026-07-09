// ============================================================
// approve-group-direct.js — Duyệt nhóm và gửi lời chào trực tiếp
// ============================================================
import { Zalo, ThreadType } from 'zca-js';
import { readFileSync, existsSync } from 'fs';
import config from '../config.js';
import dataStore from '../data-store.js';

async function runDirectApproval() {
  const targetGroupId = '5865555305749841620';
  const groupName = 'Test trợ lý Cường';
  const purpose = 'Các công việc về trợ lý cho sếp';

  console.log('📦 1. Đang lưu thông tin duyệt nhóm vào database...');
  dataStore.approveGroup(targetGroupId, groupName, purpose);
  dataStore.upsertUser(targetGroupId, groupName);
  dataStore.setGreetingStep(targetGroupId, 1);
  console.log('✅ Đã lưu vào database thành công!');

  console.log('🔌 2. Đang kết nối Zalo để gửi lời chào trực tiếp...');
  const credPath = config.zalo.credentialsPath;
  if (!existsSync(credPath)) {
    console.error('❌ File credentials không tồn tại!');
    return;
  }

  const credentials = JSON.parse(readFileSync(credPath, 'utf-8'));
  const zalo = new Zalo({ selfListen: false });

  try {
    const api = await zalo.login({
      cookie: credentials.cookies,
      imei: credentials.imei,
      userAgent: credentials.userAgent,
    });
    console.log('✅ Đăng nhập thành công!');

    const welcomeMsg = `Chào cả nhà,\nEm là trợ lý của anh Cường\nRất biết ơn cả nhà đồng hành cùng nhau ạ !`;
    console.log(`💬 Đang gửi lời chào vào nhóm "${groupName}" (${targetGroupId})...`);
    
    await api.sendMessage(welcomeMsg, targetGroupId, ThreadType.Group);
    dataStore.logMessage(targetGroupId, 'outgoing', welcomeMsg);
    dataStore.addToConversation(targetGroupId, 'assistant', welcomeMsg);
    
    console.log('✅ GỬI LỜI CHÀO THÀNH CÔNG!');
  } catch (err) {
    console.error('❌ Gửi lời chào thất bại:', err.message);
  } finally {
    dataStore.close();
    process.exit(0);
  }
}

runDirectApproval();
