// ============================================================
// content-scenarios.js — Kịch bản cộng đồng cho Cường Assistant
// ============================================================
// Kịch bản tập trung vào Kiến thức Trading, SMC, FVG và Bot Tín hiệu.
// Tỷ lệ chuẩn: 70% Kiến thức, 20% Tương tác, 10% Bán hàng (Bot).
// ============================================================

const scenarios = [
  // ── LOẠI 1: KIẾN THỨC TRADING (70%) ──────────────────────
  {
    id: 1,
    group: 'Kiến thức',
    title: 'Kiến thức SMC: Fair Value Gap (FVG)',
    content: `📊 [CHIA SẺ KIẾN THỨC] — Chủ đề: Fair Value Gap (FVG)

Trong phương pháp SMC, FVG (Khoảng trống giá) là một trong những vùng cản quan trọng nhất. Nó xuất hiện khi có sự chênh lệch lớn giữa phe mua và phe bán, tạo ra một khoảng trống giữa râu nến thứ 1 và râu nến thứ 3.

💡 Mẹo giao dịch: Giá thường có xu hướng quay lại "lấp đầy" (mitigate) vùng FVG này trước khi tiếp tục xu hướng chính. Đừng vội vàng vào lệnh khi giá đang chạy mạnh, hãy kiên nhẫn đợi giá hồi về FVG!

Cả nhà có thường dùng FVG làm điểm vào lệnh không? Có câu hỏi gì thêm cứ trao đổi nhé! 🙏`
  },
  {
    id: 2,
    group: 'Kiến thức',
    title: 'Kiến thức SMC: Order Block (OB)',
    content: `📊 [CHIA SẺ KIẾN THỨC] — Chủ đề: Order Block (OB)

Order Block là cây nến giảm cuối cùng trước một đợt tăng mạnh (hoặc nến tăng cuối cùng trước đợt giảm mạnh). Đây là nơi các tổ chức lớn (Smart Money) gom hàng.

💡 Lưu ý: Không phải OB nào cũng hoạt động. Một OB uy tín cần phải:
1. Phá vỡ cấu trúc (BOS/CHOCH).
2. Tạo ra sự mất cân bằng (có FVG đi kèm).
3. Nằm ở vùng Discount (nếu mua) hoặc Premium (nếu bán).

Cả nhà có câu hỏi gì thêm cứ trao đổi nhé! 🙏`
  },
  {
    id: 3,
    group: 'Kiến thức',
    title: 'Kiến thức SMC: Thanh khoản (Liquidity)',
    content: `📊 [CHIA SẺ KIẾN THỨC] — Chủ đề: Thanh khoản (Liquidity)

"Nếu bạn không nhìn thấy thanh khoản, bạn chính là thanh khoản." 

Smart Money luôn cần thanh khoản để khớp các lệnh khổng lồ của họ. Thanh khoản thường nằm ở đâu?
- Đỉnh/đáy cũ (Equal Highs / Equal Lows).
- Đường Trendline.
- Phiên Á (Asian Range).

💡 Hãy kiên nhẫn chờ giá quét thanh khoản (Liquidity Sweep) trước khi tìm kiếm cơ hội vào lệnh theo hướng ngược lại!

Cả nhà có câu hỏi gì thêm cứ trao đổi nhé! 🙏`
  },
  {
    id: 4,
    group: 'Kiến thức',
    title: 'Kiến thức Trading: Quản lý vốn',
    content: `📊 [CHIA SẺ KIẾN THỨC] — Chủ đề: Quản lý vốn & Tâm lý

Bạn có thể có phương pháp giao dịch tốt nhất thế giới, nhưng nếu không quản lý vốn, tài khoản vẫn sẽ cháy.

💡 Quy tắc 1-2%:
Chỉ rủi ro tối đa 1-2% tài khoản cho MỖI lệnh giao dịch. Nếu tài khoản bạn $1000, một lệnh thua chỉ nên mất $10-$20. Điều này giúp bạn sống sót qua những chuỗi lệnh thua liên tiếp (Drawdown).

Thà bảo vệ vốn còn hơn cố gắng kiếm lợi nhuận lớn trong một lệnh. Cả nhà có câu hỏi gì thêm cứ trao đổi nhé! 🙏`
  },
  {
    id: 5,
    group: 'Kiến thức',
    title: 'Kiến thức SMC: CHoCH vs BOS',
    content: `📊 [CHIA SẺ KIẾN THỨC] — Chủ đề: Phân biệt CHoCH và BOS

Nhiều trader nhầm lẫn giữa CHoCH (Change of Character) và BOS (Break of Structure).
- BOS: Là sự tiếp diễn của xu hướng hiện tại (Giá phá đỉnh cũ để tạo đỉnh mới cao hơn trong xu hướng tăng).
- CHoCH: Là tín hiệu cảnh báo ĐẢO CHIỀU xu hướng (Giá phá đáy gần nhất trong xu hướng tăng).

💡 CHoCH chỉ thực sự có giá trị khi nó xảy ra tại các vùng cản quan trọng (HTF POI). Đừng bắt mọi CHoCH bạn thấy!

Cả nhà có câu hỏi gì thêm cứ trao đổi nhé! 🙏`
  },
  {
    id: 6,
    group: 'Kiến thức',
    title: 'Kiến thức SMC: Premium & Discount',
    content: `📊 [CHIA SẺ KIẾN THỨC] — Chủ đề: Vùng Premium & Discount

Trong SMC, chúng ta luôn muốn MUA ở giá rẻ (Discount) và BÁN ở giá cao (Premium). 
Kéo Fibonacci từ đáy lên đỉnh của một con sóng. 
- Mức > 50% là vùng Premium (Chỉ canh BÁN).
- Mức < 50% là vùng Discount (Chỉ canh MUA).

💡 Đừng bao giờ mua khi giá đang ở vùng Premium! Hãy kiên nhẫn đợi giá hồi về Discount. 

Cả nhà có câu hỏi gì thêm cứ trao đổi nhé! 🙏`
  },
  {
    id: 7,
    group: 'Kiến thức',
    title: 'Kiến thức Trading: Đường EMA',
    content: `📊 [CHIA SẺ KIẾN THỨC] — Chủ đề: Kết hợp EMA trong giao dịch

Dù phương pháp SMC tập trung vào hành động giá (Price Action), nhưng kết hợp EMA (như EMA 34, 89) sẽ giúp xác định xu hướng nhanh hơn.

💡 Nếu giá nằm trên EMA 89 và EMA 89 hướng lên → Cấu trúc tăng, chỉ tìm kiếm lệnh MUA.
Sự giao cắt của EMA kết hợp cùng với việc phá vỡ cấu trúc (BOS) sẽ cho tỷ lệ thắng rất cao.

Cả nhà có câu hỏi gì thêm cứ trao đổi nhé! 🙏`
  },

  // ── LOẠI 2: TƯƠNG TÁC / QUIZ (20%) ──────────────────────
  {
    id: 8,
    group: 'Tương tác',
    title: 'Câu hỏi tương tác: Lựa chọn setup',
    content: `🤔 CÂU HỎI CUỐI TUẦN:
Nếu được chọn 1 setup duy nhất để giao dịch cả năm, cả nhà sẽ chọn setup nào? 
(Ví dụ: Giao dịch theo FVG, theo Order Block, theo phân kỳ, hay giao cắt EMA...)

Comment bên dưới để cùng thảo luận nhé! 👇`
  },
  {
    id: 9,
    group: 'Tương tác',
    title: 'Mini Quiz: FVG',
    content: `🧩 QUIZ NHANH VỀ SMC: 
FVG (Fair Value Gap) hình thành từ bao nhiêu cây nến?

A. 2 nến liên tiếp.
B. 3 nến liên tiếp.
C. 4 nến liên tiếp.

Trả lời bên dưới, tối nay em sẽ nhắn đáp án vào nhóm nhé! 🎁`
  },

  // ── LOẠI 3: SẢN PHẨM / BOT TÍN HIỆU (10%) ────────────────
  {
    id: 10,
    group: 'Sản phẩm',
    title: 'Giới thiệu Bot tín hiệu SMC',
    content: `🔔 Chia sẻ nhanh: 

Tuần qua Bot tín hiệu SMC & 4EMA của team đã quét được rất nhiều setup chất lượng (tỷ lệ Winrate cao) trên Binance và Forex. Bot chạy hoàn toàn tự động 24/7 và báo tín hiệu qua Telegram.

Bạn nào muốn nhận tín hiệu thử thì đăng ký tại: https://opc-dau-tu.vercel.app
Hoàn toàn miễn phí trải nghiệm! 🚀`
  }
];

// Lịch đăng bài theo thứ trong tuần: Thứ 3 và Thứ 5 (Tỷ lệ 7:2:1)
// T3 và T5 sẽ xoay vòng mảng này để đăng bài
const contentSchedule = [1, 2, 8, 3, 4, 10, 5, 6, 9, 7];

const rotationData = {
  currentIndex: 0
};

/**
 * Lấy kịch bản cho ngày hôm nay và tự động tịnh tiến index.
 */
function getScenarioForToday() {
  const scenarioId = contentSchedule[rotationData.currentIndex % contentSchedule.length];
  rotationData.currentIndex++;
  
  return scenarios.find(s => s.id === scenarioId);
}

function getScenarioById(id) {
  return scenarios.find(s => s.id === id);
}

export { getScenarioForToday, getScenarioById, scenarios };
export default scenarios;
