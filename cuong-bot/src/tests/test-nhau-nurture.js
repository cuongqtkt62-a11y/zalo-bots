// ============================================================
// test-nhau-nurture.js — Test sinh bài đăng chăm sóc cho nhóm Nhàu Tâm An
// ============================================================
import dotenv from 'dotenv';
import path from 'path';

// Load .env from parent directory
dotenv.config({ path: path.join(process.cwd(), '.env') });

import aiEngine from '../ai-engine.js';

async function run() {
  const groupName = 'NHÀ QUẢNG BÁ 365 (Nhàu Tâm An)';
  const groupPurpose = 'Kinh doanh sản phẩm Nhàu Thảo Mộc Tâm An dựa trên nền tảng chăm sóc sức khoẻ chủ động';

  console.log('🧪 Đang test sinh bài viết Buổi sáng...');
  const morning = await aiEngine.generateGroupNurturingPost(groupName, groupPurpose, 'Buổi sáng (8:00)');
  console.log('\n--- BUỔI SÁNG ---');
  console.log('Quote Card:', morning.quote);
  console.log('Post Content:\n', morning.post);
  console.log('-----------------\n');

  console.log('🧪 Đang test sinh bài viết Buổi trưa...');
  const noon = await aiEngine.generateGroupNurturingPost(groupName, groupPurpose, 'Buổi trưa (12:00)');
  console.log('\n--- BUỔI TRƯA ---');
  console.log('Quote Card:', noon.quote);
  console.log('Post Content:\n', noon.post);
  console.log('-----------------\n');

  console.log('🧪 Đang test sinh bài viết Buổi tối...');
  const evening = await aiEngine.generateGroupNurturingPost(groupName, groupPurpose, 'Buổi tối (19:00)');
  console.log('\n--- BUỔI TỐI ---');
  console.log('Quote Card:', evening.quote);
  console.log('Post Content:\n', evening.post);
  console.log('-----------------\n');
}

run().catch(console.error);
