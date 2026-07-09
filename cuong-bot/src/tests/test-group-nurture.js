// ============================================================
// test-group-nurture.js — Kiểm thử tính năng Group Care & AI Nurture
// ============================================================
import dataStore from '../data-store.js';
import aiEngine from '../ai-engine.js';

async function runTest() {
  console.log('🧪 1. Kiểm thử lưu trữ thông tin nhóm...');
  const testGroupId = 'test-group-id-123';
  const groupName = 'Nhóm Học Viên Trading SMC Cường';
  const purpose = 'Thảo luận và phân tích biểu đồ theo phương pháp SMC-4EMA.';

  // Xóa nhóm cũ nếu có để đảm bảo test sạch
  if (dataStore.approvedGroups) {
    dataStore.approvedGroups = dataStore.approvedGroups.filter(g => g !== testGroupId && g?.id !== testGroupId);
  }

  // Phê duyệt nhóm mới
  dataStore.approveGroup(testGroupId, groupName, purpose);

  // Lấy lại thông tin
  const isApproved = dataStore.isGroupApproved(testGroupId);
  const groupInfo = dataStore.getApprovedGroup(testGroupId);

  console.log(`- Trạng thái duyệt nhóm: ${isApproved ? '✅ ĐÃ DUYỆT' : '❌ CHƯA DUYỆT'}`);
  console.log(`- Thông tin nhóm đã lưu:`, JSON.stringify(groupInfo, null, 2));

  if (!isApproved || groupInfo.name !== groupName || groupInfo.purpose !== purpose) {
    console.error('❌ Kiểm thử lưu trữ Thất bại!');
    return;
  }
  console.log('✅ Kiểm thử lưu trữ thông tin nhóm thành công!\n');

  console.log('🧪 2. Kiểm thử sinh bài đăng chăm sóc bằng AI...');
  console.log('Đang kết nối API AI (Gemini/OpenAI) để sinh bài viết buổi sáng...');

  const start = Date.now();
  const postMorning = await aiEngine.generateGroupNurturingPost(groupName, purpose, 'Buổi sáng (8:00)');
  console.log(`Thời gian phản hồi AI: ${((Date.now() - start) / 1000).toFixed(2)}s`);
  console.log('\n--- BÀI VIẾT MẪU BUỔI SÁNG ---');
  console.log(postMorning);
  console.log('------------------------------\n');

  console.log('Đang kết nối API AI để sinh bài viết buổi tối...');
  const postEvening = await aiEngine.generateGroupNurturingPost(groupName, purpose, 'Buổi tối (19:00)');
  console.log('\n--- BÀI VIẾT MẪU BUỔI TỐI ---');
  console.log(postEvening);
  console.log('-----------------------------\n');

  // Dọn dẹp data test
  if (dataStore.approvedGroups) {
    dataStore.approvedGroups = dataStore.approvedGroups.filter(g => g !== testGroupId && g?.id !== testGroupId);
    dataStore._saveAll();
  }

  console.log('✅ TEST HOÀN TẤT!');
}

runTest().catch(err => {
  console.error('💥 Đã xảy ra lỗi khi test:', err);
});
