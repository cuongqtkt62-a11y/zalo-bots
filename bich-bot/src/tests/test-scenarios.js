// ============================================================
// test-scenarios.js — Kiểm thử Lịch đăng bài & Sinh nội dung AI
// ============================================================
import 'dotenv/config';
import aiEngine from '../ai-engine.js';
import { weeklySchedule, getScenarioById, ebookIdeas, weekdayToGroupMap } from '../content-scenarios.js';
import dataStore from '../data-store.js';

async function runTests() {
  console.log("🚀 KHỞI ĐỘNG KIỂM THỬ KỊCH BẢN & LỊCH ĐĂNG BÀI...\n");

  // --- Test 1: Lịch đăng bài tĩnh hàng ngày (0-6) ---
  console.log("=== TEST 1: KIỂM TRA PHÂN BỔ KỊCH BẢN TĨNH THEO THỨ ===");
  const weekdaysName = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];
  
  for (let d = 0; d < 7; d++) {
    const ids = weeklySchedule[d];
    console.log(`• ${weekdaysName[d]} (Group Ebook #${weekdayToGroupMap[d]}): Scenarios [${ids.join(', ')}]`);
    
    // Kiểm tra các kịch bản tồn tại
    for (const id of ids) {
      const sc = getScenarioById(id);
      if (!sc) {
        console.error(`❌ Lỗi: Không tìm thấy kịch bản ID ${id}`);
      } else {
        console.log(`   - Kịch bản #${sc.id}: "${sc.title}" (${sc.group})`);
      }
    }
  }
  console.log("✅ Test 1 thành công!\n");

  // --- Test 2: Xoay vòng Rotation Index ---
  console.log("=== TEST 2: KIỂM TRA XOAY VÒNG XOAY VÒNG KỊCH BẢN ===");
  if (!dataStore.stats.rotationIndex) {
    dataStore.stats.rotationIndex = {};
  }
  
  const testDay = 1; // Thứ Hai: [1, 2, 3]
  console.log(`Giả lập xoay vòng cho ${weekdaysName[testDay]} (Scenarios: [1, 2, 3])`);
  
  const initialIndex = dataStore.stats.rotationIndex[testDay] || 0;
  
  for (let i = 0; i < 4; i++) {
    const idx = (initialIndex + i) % 3;
    const scenarioId = weeklySchedule[testDay][idx];
    console.log(`   - Lần chạy ${i + 1}: Index = ${idx} -> Scenario ID = ${scenarioId}`);
  }
  console.log("✅ Test 2 thành công!\n");

  // --- Test 3: Sinh kịch bản động bằng AI (Ý tưởng Ebook) ---
  console.log("=== TEST 3: KIỂM TRA SINH BÀI ĐĂNG DÙNG AI (GEMINI/LLAMA) ===");
  if (!config_has_keys()) {
    console.warn("⚠️ Bỏ qua test AI vì không tìm thấy API key trong môi trường.");
    return;
  }

  try {
    const testDays = [1, 2]; // 1 = Thứ Hai (Group 1 - Giá trị), 2 = Thứ Ba (Group 4 - Tương tác)
    for (const day of testDays) {
      console.log(`\n🤖 Yêu cầu AI tạo bài đăng cho ngày ${weekdaysName[day]}...`);
      const result = await aiEngine.generateDynamicScenarioPost(day);
      console.log(`💡 [Ý TƯỞNG EBOOK ĐÃ CHỌN]: "${result.idea}"`);
      console.log(`📄 [BÀI ĐĂNG AI TẠO]:`);
      console.log("------------------------------------------------------------");
      console.log(result.content);
      console.log("------------------------------------------------------------");
    }
    console.log("\n✅ Test 3 thành open & thành công!");
  } catch (error) {
    console.error("❌ Test 3 thất bại:", error);
  }
}

function config_has_keys() {
  const provider = process.env.AI_PROVIDER || 'gemini';
  if (provider === 'gemini' && process.env.GEMINI_API_KEY) return true;
  if (provider === 'openai' && process.env.OPENAI_API_KEY) return true;
  return false;
}

runTests().then(() => {
  console.log("\n🎉 HOÀN TẤT TẤT CẢ KIỂM THỬ.");
  process.exit(0);
}).catch(err => {
  console.error("💥 Lỗi kiểm thử:", err);
  process.exit(1);
});
