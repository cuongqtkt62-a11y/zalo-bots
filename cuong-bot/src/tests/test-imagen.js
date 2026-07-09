import { createCard } from '../image-generator.js';

async function testCreateCardIntegration() {
  console.log('🧪 Testing createCard integration with AI Background generation...');
  const text = 'Kỷ luật là cầu nối giữa mục tiêu và thành tựu thực tế. Hãy giữ vững kỷ luật mỗi ngày!';
  const timeOfDay = 'Buổi sáng (8:00)';
  const groupId = 'test-group-id';
  const groupName = 'NHÀ QUẢNG BÁ 365 (Nhàu Tâm An)';
  const groupPurpose = 'Chăm sóc sức khỏe chủ động, thảo luận về sản phẩm nhàu thảo mộc và sống lành mạnh.';

  try {
    const outputPath = await createCard(text, timeOfDay, groupId, groupName, groupPurpose);
    console.log(`✅ Integration test completed!`);
    console.log(`💾 Saved card to: ${outputPath}`);
  } catch (err) {
    console.error(`❌ Integration test failed:`, err);
  }
}

testCreateCardIntegration();
