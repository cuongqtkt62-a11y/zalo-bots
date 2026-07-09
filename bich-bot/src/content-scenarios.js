// ============================================================
// content-scenarios.js — Kịch bản viết bài cho cô Bích
// ============================================================
// 20 kịch bản chia theo 5 nhóm nội dung, dựa trên Ebook
// "Biến Profile Facebook thành Tài Sản Số" — Lưu Phan Ngọc Bích.
//
// Lịch đăng bài theo thứ:
//   T2: Giá trị & Giáo dục (KB 1,2,3)
//   T3: Tương tác & Thảo luận (KB 12,13,14)
//   T4: Giá trị & Giáo dục (KB 4,5,15)
//   T5: Viral & Reels (KB 6,7,8)
//   T6: Lòng tin & Nhân văn (KB 9,10,11)
//   T7: Bán hàng & Chuyển đổi (KB 16,17,18)
//   CN: Bán hàng nhẹ + Tương tác (KB 19,20)
// ============================================================

const scenarios = [
  // ── NHÓM 1: TRAO GIÁ TRỊ & GIÁO DỤC ──────────────────
  {
    id: 1,
    group: 'Giá trị & Giáo dục',
    title: 'CHECKLIST — 5 bước biến Profile thành tài sản số',
    content: `Facebook là bất động sản số. Các anh/chị đang để nó hoang hay đang khai thác?

Đây là 5 bước Bích đã áp dụng để Profile sinh tiền:

✅ Bước 1: Tối ưu ảnh đại diện & ảnh bìa — "mặt tiền" bất động sản số
✅ Bước 2: Viết Bio rõ ràng — "Tôi là ai? Tôi giúp gì cho bạn?"
✅ Bước 3: Thiết lập 3 trụ cột: Chuyên môn — Cá nhân — Bán hàng
✅ Bước 4: Đăng bài đều, ưu tiên khung giờ vàng 19:00-21:00
✅ Bước 5: Tương tác có chủ đích — bình luận chất lượng trên 20 từ

💡 Lưu lại. Làm theo. Từng bước.

Các anh/chị đang ở bước nào? Comment số thứ tự 👇`
  },
  {
    id: 2,
    group: 'Giá trị & Giáo dục',
    title: 'HOW-TO — Tối ưu Profile Facebook trong 30 phút',
    content: `30 PHÚT = 1 PROFILE CHUYÊN NGHIỆP

Thuật toán 2026 đã thay đổi. Kỷ nguyên "like" chấm dứt. Facebook ưu tiên tín hiệu chất lượng: thời gian đọc, lượt Save, comment sâu.

Làm ngay:

⏱️ Phút 1-5: Đổi ảnh đại diện — điện thoại + ánh sáng tự nhiên, không cần studio
⏱️ Phút 6-10: Viết lại phần Giới thiệu — ghi rõ USP
⏱️ Phút 11-15: Cập nhật ảnh bìa — thông điệp giá trị cốt lõi
⏱️ Phút 16-20: Ghim 3 bài viết quan trọng nhất
⏱️ Phút 21-25: Dọn danh sách bạn bè — ưu tiên khách hàng tiềm năng
⏱️ Phút 26-30: Đăng bài đầu tiên theo công thức AIDA

Muốn Bích review Profile? Comment "REVIEW" 👇`
  },
  {
    id: 3,
    group: 'Giá trị & Giáo dục',
    title: 'XU HƯỚNG — Facebook 2026: AI & Tín hiệu mới',
    content: `3 thay đổi thuật toán Facebook 2026 — không biết sẽ tụt hậu:

1️⃣ AI chấm điểm nội dung
Facebook giờ dùng AI để "chấm điểm" bài viết. Bài có giá trị thật → đẩy reach. Bài spam → ẩn.

2️⃣ Tín hiệu có ý nghĩa > Like
Comment trên 20 từ, lượt Save, Share qua Messenger — đây mới là thứ thuật toán đo lường.

3️⃣ Công nghệ + Nhân văn = Thắng
AI bão hòa → người dùng khao khát "tính người". Ai kết hợp công nghệ + sự chân thật sẽ bùng nổ.

📌 Lưu lại. Đây là nền tảng chiến lược cả năm.

Thay đổi nào ảnh hưởng nhất đến các anh/chị? 💬`
  },
  {
    id: 4,
    group: 'Giá trị & Giáo dục',
    title: 'BỘ CÔNG CỤ — 5 tool Bích dùng mỗi ngày',
    content: `5 công cụ miễn phí — dùng hàng ngày — tạo nội dung Facebook hiệu quả:

🔹 Canva — Thiết kế ảnh bìa, infographic, template
🔹 ChatGPT/AI — Brainstorm ý tưởng, viết outline
🔹 CapCut — Chỉnh Reels chuyên nghiệp trên điện thoại
🔹 Meta Business Suite — Lên lịch, theo dõi insight
🔹 Google Trends — Nắm xu hướng, tạo content theo trend

💡 Mẹo: Không cần dùng hết. Chọn 2-3 cái, dùng thật sâu.

Các anh/chị đang dùng tool nào? Có gì hay chia sẻ thêm 👇`
  },
  {
    id: 5,
    group: 'Giá trị & Giáo dục',
    title: 'THỬ THÁCH — 30 ngày xây thương hiệu cá nhân',
    content: `30 ngày. Mỗi ngày 1 hành động. Profile thành tài sản số.

📅 Tuần 1: NỀN TẢNG
- Ngày 1: Ảnh đại diện
- Ngày 2: Viết Bio
- Ngày 3: Ảnh bìa
- Ngày 4: Ghim 3 bài chất lượng
- Ngày 5: Xác định 3 trụ cột nội dung
- Ngày 6: Lên lịch đăng bài
- Ngày 7: Bài đầu tiên + tương tác 30 phút

📅 Tuần 2: NỘI DUNG GIÁ TRỊ
Checklist, How-to, Infographic, FAQ

📅 Tuần 3: MỞ RỘNG REACH
Reels, Livestream Q&A, Thử thách cộng đồng

📅 Tuần 4: CHUYỂN ĐỔI
Case Study, Social Proof, CTA, Phễu khách hàng

💪 Tham gia? Comment "THAM GIA" — Bích đồng hành từng ngày!`
  },

  // ── NHÓM 2: VIRAL & KHÁM PHÁ ──────────────────────────
  {
    id: 6,
    group: 'Viral & Khám phá',
    title: 'REELS KỂ CHUYỆN — Từ 0 đến thương hiệu cá nhân',
    content: `❌ "Tôi từng nghĩ Facebook chỉ để lướt chơi..."

Bích từng lướt Facebook vô định. Like vài bài. Hết.

Đến khi nhận ra: Profile = bất động sản số. Và Bích đang để nó hoang phí.

🔄 Thay đổi:
- Tối ưu Profile thành "mặt tiền" chuyên nghiệp
- Đăng bài có chiến lược theo 3 trụ cột
- Tương tác có chủ đích — không "thả tim" vô nghĩa

Kết quả? Profile bắt đầu sinh tiền.

📌 Các anh/chị muốn biết chi tiết? Nhắn "CHI TIẾT" cho Bích!`
  },
  {
    id: 7,
    group: 'Viral & Khám phá',
    title: 'PATTERN INTERRUPT — 3 sai lầm chết người khi dùng Facebook kiếm tiền',
    content: `🚫 DỪNG LẠI! 3 điều này đang giết chết Facebook của các anh/chị!

Sai lầm 1: Đăng bán hàng liên tục → thuật toán phạt
➡️ Sửa: 70% giá trị — 20% tương tác — 10% bán

Sai lầm 2: Chỉ ảnh sản phẩm, không kể chuyện
➡️ Sửa: Dùng AIDA/PAS — bán mà "không bán"

Sai lầm 3: Bỏ qua Reels
➡️ Sửa: Tối thiểu 2-3 Reels/tuần kèm trend audio

Từng mắc lỗi nào? Comment "SỬA SAI" 👇`
  },
  {
    id: 8,
    group: 'Viral & Khám phá',
    title: 'MEME NGÀNH — Ngày xưa vs. Bây giờ',
    content: `NGÀY XƯA vs. BÂY GIỜ — kinh doanh trên Facebook:

🔸 Xưa: Đăng 1 bài → nghìn người thấy
🔸 Giờ: Đăng 1 bài → tự like chính mình 😭

🔸 Xưa: Chụp ảnh + ghi giá = bán
🔸 Giờ: Storytelling + Reels + phễu + thương hiệu...

🔸 Xưa: "Inbox giá ạ?"
🔸 Giờ: "Xem bài review + video unboxing bên dưới ạ!" 😄

Tag anh/chị nào đang "khóc" vì reach tụt 😆👇`
  },

  // ── NHÓM 3: LÒNG TIN & NHÂN VĂN ──────────────────────
  {
    id: 9,
    group: 'Lòng tin & Nhân văn',
    title: 'LỜI TỰ SỰ — Nỗi sợ lớn nhất khi bắt đầu',
    content: `Khi mới xây thương hiệu cá nhân, Bích sợ.

Sợ người ta đánh giá. Sợ viết chẳng ai đọc. Sợ bị nói "khoe khoang".

Nhưng sự thật: Tài sản số không tự sinh lời nếu không xây từng viên gạch đầu tiên.

Bích bắt đầu từ bài viết nhỏ. Kiến thức thật. Câu chuyện thật. Từ từ, đúng người tìm đến.

"Đừng đợi hoàn hảo. Bắt đầu để trở nên hoàn hảo."

Các anh/chị từng sợ như vậy không? 💬`
  },
  {
    id: 10,
    group: 'Lòng tin & Nhân văn',
    title: 'VẾT SẸO CHIẾN THẮNG — Lần thất bại đau nhất',
    content: `Có giai đoạn Bích đầu tư cả tuần viết nội dung — reach bằng 0. Vài lượt tương tác. Tự hỏi: "Mình sai ở đâu?"

Thay vì bỏ cuộc → dừng lại, phân tích:
- Nội dung có giải quyết đúng "nỗi đau" khách hàng?
- Profile đã đủ chuyên nghiệp tạo niềm tin?
- Tương tác có đúng cách?

Sửa sai → mọi thứ thay đổi.

Vết sẹo đó = bài học quý nhất.

Các anh/chị đã bao giờ muốn bỏ cuộc? Chia sẻ đi — cùng đẩy nhau lên 💪`
  },
  {
    id: 11,
    group: 'Lòng tin & Nhân văn',
    title: 'GIÁ TRỊ CỐT LÕI — Tại sao Bích làm việc này?',
    content: `Nhiều anh/chị hỏi: "Sao chia sẻ nhiều kiến thức miễn phí vậy?"

Đơn giản: Bích tin mỗi người đều có thể biến cái tên mình thành thương hiệu đáng giá.

Bích đã đi qua hành trình đó. Profile bình thường → thương hiệu cá nhân tạo thu nhập thật.

🎯 Mục đích: Giúp các anh/chị xây tài sản số bền vững — không chỉ tiền ngắn hạn, mà giá trị dài hạn.

Cảm ơn các anh/chị đã đồng hành ❤️`
  },

  // ── NHÓM 4: TƯƠNG TÁC & THẢO LUẬN ────────────────────
  {
    id: 12,
    group: 'Tương tác & Thảo luận',
    title: '4W1H — Các anh/chị đang ở đâu?',
    content: `Hành trình biến Profile thành tài sản số — các anh/chị đang ở đâu?

🔹 1: Mới bắt đầu, chưa biết làm gì
🔹 2: Đã tối ưu Profile, chưa biết viết nội dung
🔹 3: Đăng bài đều nhưng reach thấp
🔹 4: Có kết quả, muốn scale up

Comment số thứ tự — Bích tư vấn riêng từng giai đoạn 🎯`
  },
  {
    id: 13,
    group: 'Tương tác & Thảo luận',
    title: 'TRƯNG CẦU — Tuần tới học gì?',
    content: `Tuần tới Bích chia sẻ sâu 1 trong 3 chủ đề. Các anh/chị chọn:

🅰️ Viết bài theo AIDA — bán mà không cần "bán"
🅱️ Chiến lược Reels 2026 — video tiếp cận hàng nghìn người lạ
🅲️ Phễu khách hàng — Facebook → Zalo/Messenger → Chốt đơn

Comment A, B hoặc C — nhiều vote nhất thắng 🏆`
  },
  {
    id: 14,
    group: 'Tương tác & Thảo luận',
    title: 'NỖI ĐAU — Khó khăn lớn nhất là gì?',
    content: `Xây thương hiệu cá nhân trên Facebook — khó nhất là gì?

- 😰 Không biết viết gì?
- 😢 Viết rồi chẳng ai đọc?
- 🤷 Không biết bắt đầu từ đâu?
- 😓 Ngại thể hiện trên mạng?
- 💸 Chưa biết chuyển tương tác thành tiền?

Chia sẻ thật. Bích đọc từng comment và sẽ có bài giải đáp riêng ❤️`
  },
  {
    id: 15,
    group: 'Tương tác & Thảo luận',
    title: 'AI — Các anh/chị dùng AI thế nào?',
    content: `2026 — không dùng AI = tụt hậu. Dùng sai = nguy hiểm hơn.

Bích thấy nhiều anh/chị dùng AI viết bài nhưng bài nào cũng "giống nhau như đúc" — mất bản sắc.

💡 Cách dùng đúng:
- AI brainstorm ý tưởng → viết lại bằng giọng của MÌNH
- AI phân tích xu hướng → chọn lọc theo ngách của MÌNH
- AI tạo outline → thêm câu chuyện thật của MÌNH

Nguyên tắc: AI hỗ trợ. KHÔNG thay thế con người.

Các anh/chị đang dùng AI làm gì? 👇`
  },

  // ── NHÓM 5: BÁN HÀNG & CHUYỂN ĐỔI ────────────────────
  {
    id: 16,
    group: 'Bán hàng & Chuyển đổi',
    title: 'CASE STUDY — Câu chuyện thành công thật',
    content: `❌ VẤN ĐỀ:
Chị [tên] — kinh doanh mỹ phẩm online. Đăng 3-4 bài/ngày, reach thấp, không đơn. Profile "nghiệp dư".

😰 HỆ QUẢ:
Gần bỏ cuộc. Đầu tư thời gian không kết quả. Quảng cáo đốt tiền, khách không tin.

✅ GIẢI PHÁP:
Áp dụng "Biến Profile thành Tài Sản Số":
- Tối ưu Profile theo 3 trụ cột
- Công thức nội dung 70-20-10
- Phễu Facebook → Zalo chăm sóc

🎯 KẾT QUẢ: 30 ngày → reach tăng 300%, đơn hàng x2

Muốn Bích tư vấn lộ trình riêng? Comment "TÔI MUỐN" 🚀`
  },
  {
    id: 17,
    group: 'Bán hàng & Chuyển đổi',
    title: 'ƯU ĐÃI — Ebook "Biến Profile thành Tài Sản Số"',
    content: `Ebook "Biến Profile Facebook thành Tài Sản Số" — 140 trang thực chiến.

📖 Bên trong:
✅ Lộ trình 30 ngày xây thương hiệu
✅ 100 ý tưởng nội dung Fanpage 2026
✅ Chiến lược thuật toán Facebook mới nhất
✅ Cẩm nang mở khóa & bảo vệ tài khoản
✅ Mô hình AIDA/PAS bán hàng hiệu quả

🔥 Ưu đãi riêng cho thành viên nhóm.

👉 Comment "EBOOK" hoặc nhắn tin Bích để nhận.`
  },
  {
    id: 18,
    group: 'Bán hàng & Chuyển đổi',
    title: 'TƯ VẤN 1-1 — Review Profile miễn phí',
    content: `REVIEW PROFILE MIỄN PHÍ — 10 SUẤT DUY NHẤT

Cuối tuần này Bích review Profile cho 10 anh/chị đầu tiên:

🔍 Ảnh đại diện & ảnh bìa — đã tối ưu chưa?
🔍 Bio — truyền tải đúng giá trị chưa?
🔍 Nội dung — đúng chiến lược 3 trụ cột?
🔍 Những điểm cần cải thiện NGAY

📌 Comment "REVIEW" → Bích inbox riêng.
⚡ 10 suất — hết là hết.`
  },
  {
    id: 19,
    group: 'Bán hàng & Chuyển đổi',
    title: 'BÁN KHÓA HỌC — Đóng gói chất xám thành tài sản',
    content: `Mỗi ngày dành 2-3 tiếng trên Facebook. Thời gian đó tạo ra bao nhiêu tiền?

Chỉ thay đổi CÁCH SỬ DỤNG — cùng 2-3 tiếng đó tạo thu nhập thụ động.

Bích đã giúp hàng trăm anh/chị biến Profile thành cỗ máy kiếm tiền. Lộ trình 30 ngày, từng bước cụ thể, ai cũng làm được.

🚀 Khóa học "Xây dựng cỗ máy kiếm tiền trên Facebook" sắp khai giảng!

Comment "ĐĂNG KÝ" → nhận thông tin + ưu đãi early bird.`
  },
  {
    id: 20,
    group: 'Bán hàng & Chuyển đổi',
    title: 'PHỄU — Nhóm Zalo VIP',
    content: `Học trên nhóm Facebook bị loãng? Bích có giải pháp.

Nhóm Zalo VIP — dành riêng cho ai muốn:

✅ Hỗ trợ 1-1 — Bích trả lời trực tiếp
✅ Tài liệu độc quyền — Template, checklist, kịch bản
✅ Cộng đồng chất lượng — kết nối đúng người
✅ Cập nhật nhanh nhất — xu hướng & thuật toán mới

Comment "ZALO" → Bích gửi link.
📌 Giới hạn số lượng để đảm bảo chất lượng.`
  },
];

// Lịch đăng bài theo thứ trong tuần (0=CN, 1=T2, ... 6=T7)
const weeklySchedule = {
  0: [19, 20],         // Chủ Nhật: Bán hàng nhẹ + Tương tác
  1: [1, 2, 3],        // Thứ Hai:  Giá trị & Giáo dục
  2: [12, 13, 14],     // Thứ Ba:   Tương tác & Thảo luận
  3: [4, 5, 15],       // Thứ Tư:   Giá trị & Giáo dục
  4: [6, 7, 8],        // Thứ Năm:  Viral & Reels
  5: [9, 10, 11],      // Thứ Sáu:  Lòng tin & Nhân văn
  6: [16, 17, 18],     // Thứ Bảy:  Bán hàng & Chuyển đổi
};

// Lưu index xoay vòng cho mỗi ngày trong tuần (tránh lặp)
const rotationIndex = {};

/**
 * Lấy kịch bản phù hợp cho ngày hôm nay.
 * Xoay vòng qua danh sách kịch bản của ngày đó.
 * @returns {{ id: number, group: string, title: string, content: string }}
 */
function getScenarioForToday() {
  const dayOfWeek = new Date().getDay(); // 0=CN, 1=T2...
  const scenarioIds = weeklySchedule[dayOfWeek];
  
  if (!rotationIndex[dayOfWeek]) {
    rotationIndex[dayOfWeek] = 0;
  }
  
  const idx = rotationIndex[dayOfWeek] % scenarioIds.length;
  const scenarioId = scenarioIds[idx];
  
  // Tăng index cho lần gọi tiếp theo
  rotationIndex[dayOfWeek]++;
  
  return scenarios.find(s => s.id === scenarioId);
}

/**
 * Lấy kịch bản theo ID cụ thể.
 * @param {number} id
 * @returns {{ id: number, group: string, title: string, content: string } | undefined}
 */
function getScenarioById(id) {
  return scenarios.find(s => s.id === id);
}

/**
 * Lấy tất cả kịch bản.
 * @returns {Array}
 */
function getAllScenarios() {
  return scenarios;
}

// 100 ý tưởng viết bài từ Ebook "Biến Profile Facebook thành Tài Sản Số"
const ebookIdeas = {
  1: [ // Nhóm 1: Giá trị & Giáo dục (T2, T4)
    "1. Checklist quy trình thực chiến: Danh sách các bước để giải quyết một vấn đề cụ thể.",
    "2. Ebook chuyên sâu: Tóm tắt các chương hay nhất của một tài sản số bạn đang sở hữu.",
    "3. Hướng dẫn (How-to): Video ngắn (Reels) hướng dẫn sử dụng một công cụ/mẹo nhỏ.",
    "4. Tóm tắt sách/phim: Những bài học rút ra áp dụng được vào công việc.",
    "5. Infographic kiến thức: Hình ảnh hóa các số liệu hoặc quy trình phức tạp.",
    "6. Bộ công cụ (Toolbox): Chia sẻ các website, phần mềm hoặc ứng dụng bạn sử dụng hàng ngày.",
    "7. Phân tích Case Study: Kể lại quá trình thành công (hoặc thất bại) của một dự án thực tế.",
    "8. Giải đáp FAQs: Tổng hợp những câu hỏi khách hàng thường gặp nhất và trả lời chi tiết.",
    "9. Mẹo tiết kiệm thời gian: Cách AI hoặc một quy trình mới giúp bạn làm việc nhanh hơn.",
    "10. Tài liệu miễn phí (Freebie): Tặng template, file thiết kế hoặc mã giảm giá độc quyền cho Fan.",
    "11. Chia sẻ bài viết từ Blog: Dẫn dắt người xem từ Facebook sang nội dung sâu hơn trên website.",
    "12. Top 10 đề xuất: Danh sách những người nổi tiếng, cuốn sách hoặc sản phẩm đáng theo dõi trong ngành.",
    "13. Phân tích xu hướng thị trường: Cập nhật những thay đổi mới nhất năm 2026.",
    "14. Hướng dẫn khắc phục lỗi: Cách xử lý các vấn đề kỹ thuật phổ biến.",
    "15. Bài viết dài (Long-form): Phân tích sâu sắc về một chủ đề nhằm tối ưu Thời gian dừng (Dwell Time).",
    "16. Mẫu lời chào/kịch bản: Chia sẻ các mẫu câu giao tiếp hiệu quả với khách hàng.",
    "17. Chia sẻ kiến thức từ chuyên gia: Phỏng vấn hoặc trích dẫn ý kiến từ những người có tầm ảnh hưởng.",
    "18. Quy tắc 'Nên và Không nên': Những sai lầm cần tránh trong lĩnh vực bạn đang làm.",
    "19. Hướng dẫn tự làm (DIY): Các dự án nhỏ mà Fan có thể thực hành ngay tại nhà.",
    "20. Tóm tắt sự kiện: Những điểm chính từ các buổi hội thảo hoặc livestream chuyên môn."
  ],
  2: [ // Nhóm 2: Viral & Khám phá (T5)
    "21. Reels kể chuyện (90s): Sử dụng vòng lặp (loop) để người xem xem lại nhiều lần.",
    "22. Phá vỡ khuôn mẫu (Pattern Interrupt): Bắt đầu video bằng một câu Hook giật gân trong 3 giây đầu.",
    "23. Video hậu trường hài hước: Những khoảnh khắc 'vỡ kịch bản' của đội ngũ.",
    "24. Thử thách 30 ngày: Khởi xướng một hành trình thay đổi thói quen cùng cộng đồng.",
    "25. Nội dung theo Trend Audio: Sử dụng các đoạn nhạc đang thịnh hành trên Reels.",
    "26. Phản ứng (Reaction Video): Thể hiện quan điểm trước một tin tức nóng hổi.",
    "27. Video biến hình (Before/After): Sự thay đổi trước và sau khi sử dụng giải pháp của bạn.",
    "28. Kể chuyện bằng hình ảnh (Visual Storytelling): Sử dụng phụ đề chạy chữ sinh động để giữ chân người xem.",
    "29. Meme ngành: Những hình ảnh chế hài hước về nỗi đau của người làm nghề.",
    "30. Livestream Q&A: Giải đáp trực tiếp các thắc mắc của người xem để tăng tương tác có ý nghĩa.",
    "31. Mini game nhanh: Đoán hình, đuổi hình bắt chữ nhận quà ngay.",
    "32. Video trải nghiệm thực tế (Unboxing): Đập hộp sản phẩm mới một cách chân thực nhất.",
    "33. So sánh sản phẩm: Đặt hai sản phẩm cạnh nhau để phân tích ưu nhược điểm.",
    "34. Cảm hứng mỗi sáng: Những câu slogan hoặc câu nói truyền động lực, khích lệ.",
    "35. Nội dung theo mùa: Các bài viết liên quan đến lễ hội hoặc sự kiện thời sự.",
    "36. Chia sẻ hình ảnh du lịch/văn phòng: Tạo cảm giác gần gũi về môi trường làm việc.",
    "37. Video hướng dẫn nhanh (30s): Một mẹo nhỏ cực kỳ dễ thực hiện.",
    "38. Bình luận về một bộ phim hot: Gắn kết các bài học kinh doanh vào kịch bản phim.",
    "39. Chia sẻ tài liệu độc quyền: Chỉ dành cho những người chia sẻ bài viết qua tin nhắn.",
    "40. Tổ chức cuộc thi ảnh: Khuyến khích người dùng đăng ảnh có liên quan đến thương hiệu."
  ],
  3: [ // Nhóm 3: Lòng tin & Nhân văn (T6)
    "41. Kể về một thất bại: Bài học xương máu mà bạn đã trải qua.",
    "42. Quan điểm cá nhân (Thought Leadership): Thể hiện góc nhìn riêng biệt về một vấn đề gây tranh luận.",
    "43. Ngày làm việc của tôi: Chia sẻ lịch trình thực tế để tạo sự tin tưởng.",
    "44. Giới thiệu đội ngũ: Hình ảnh hằng ngày của các thành viên trong nhóm.",
    "45. Lời cảm ơn khách hàng: Công nhận sự nhiệt tình và ủng hộ từ các Fan cứng.",
    "46. Giá trị cốt lõi: Tại sao bạn lại làm công việc hiện tại? Mục đích cao cả là gì.",
    "47. Hoạt động từ thiện: Chia sẻ các chiến dịch đóng góp cộng đồng mà bạn tham gia.",
    "48. Chia sẻ về gia đình: Những khoảnh khắc đời thường chứng minh bạn là một con người thật.",
    "49. Kỷ niệm ngày thành lập: Nhìn lại hành trình từ những ngày đầu tiên.",
    "50. Phỏng vấn thành viên: Để nhân viên chia sẻ về văn hóa công ty.",
    "51. Lời tự sự (Confession): Những trăn trở về nghề nghiệp hoặc cuộc sống.",
    "52. Review chân thực: Đánh giá một sản phẩm khác mà bạn thực sự yêu thích.",
    "53. Chia sẻ về sở thích: Đọc sách, thể thao hoặc du lịch để kết nối cảm xúc.",
    "54. Cam kết chất lượng: Giải thích quy trình kiểm soát sản phẩm/dịch vụ nghiêm ngặt.",
    "55. Vết sẹo chiến thắng: Kể về cách bạn vượt qua một cuộc khủng hoảng.",
    "56. Chia sẻ thư tay khách hàng: Những phản hồi tình cảm nhất từ người mua.",
    "57. Gặp gỡ nhà chuyên môn: Hình ảnh giao lưu với những người giỏi trong ngành.",
    "58. Tại sao tôi thích Facebook: Kể về cách nền tảng này giúp doanh nghiệp của bạn phát triển.",
    "59. Hành trình thay đổi diện mạo: Từ một văn phòng nhỏ đến mặt tiền đẳng cấp.",
    "60. Lời hứa với cộng đồng: Mục tiêu phục vụ khách hàng trong năm tới."
  ],
  4: [ // Nhóm 4: Tương tác & Thảo luận (T3)
    "61. Câu hỏi 4W1H: Đặt câu hỏi Cái gì, Khi nào, Tại sao, Ở đâu và Như thế nào?.",
    "62. Trưng cầu ý kiến: Hỏi Fan về màu sắc hoặc tính năng sản phẩm sắp ra mắt.",
    "63. Điền vào chỗ trống: Bài đăng bị thiếu một phần thông tin để người xem tham gia.",
    "64. Câu hỏi trắc nghiệm: Yêu cầu Fan tìm câu trả lời trên website của bạn.",
    "65. Thảo luận về một 'Huyền thoại': Nhận diện 10 cái tên lớn trong ngành và bình luận về họ.",
    "66. Đặt câu hỏi 'Có' hoặc 'Không': Kích thích tương tác nhanh.",
    "67. Hỏi về nỗi đau của Fan: Họ đang gặp khó khăn gì nhất lúc này?.",
    "68. Chia sẻ quan điểm trái chiều: 'Tôi tin rằng [X] không hiệu quả', bạn nghĩ sao?.",
    "69. Yêu cầu phụ đề cho ảnh: Đăng một bức ảnh thú vị và nhờ Fan đặt tiêu đề.",
    "70. Hỏi về địa điểm: Đăng ảnh một nơi bạn vừa đến và đố Fan biết đó là đâu.",
    "71. Tag người bạn: 'Hãy tag người bạn cần biết mẹo này ngay!'.",
    "72. Hỏi về mong muốn tương lai: 'Nếu có một điều ước cho công việc, bạn ước gì?'.",
    "73. Thảo luận về xu hướng AI: Bạn đang dùng AI làm gì mỗi ngày?.",
    "74. Bình chọn sản phẩm yêu thích: Đưa ra 2 lựa chọn và hỏi Fan thích cái nào hơn.",
    "75. Chia sẻ ngày đặc biệt: Nhấn mạnh lý do cụ thể tại sao ngày hôm nay lại quan trọng.",
    "76. Hỏi về trải nghiệm sử dụng: 'Bạn cảm thấy thế nào sau 1 tuần dùng thử?'.",
    "77. Yêu cầu đánh giá: Mời Fan viết review trực tiếp trên tường.",
    "78. Thảo luận về công cụ tìm kiếm: Fan thường tìm thấy bạn qua từ khóa nào?.",
    "79. Hỏi về các câu lạc bộ: Fan đang tham gia hội nhóm nào trên Facebook?.",
    "80. Phản hồi bình luận bằng video: Trả lời một thắc mắc hay bằng một đoạn video ngắn."
  ],
  5: [ // Nhóm 5: Bán hàng & Chuyển đổi (T7, CN)
    "81. Câu chuyện khách hàng thành công (Case Study): Mô tả nỗi đau cũ và sự chuyển hóa sau khi dùng dịch vụ.",
    "82. Feedback/Social Proof: Ảnh chụp màn hình tin nhắn khách khen ngợi.",
    "83. Ưu đãi giới hạn (Scarcity): Chỉ còn 6 suất khuyến mãi cuối cùng trong hôm nay.",
    "84. Flash Sale giờ vàng: Đăng bài vào các khung giờ người dùng online đông nhất (ví dụ: 19:00 - 21:00).",
    "85. Combo tiết kiệm: Giới thiệu bộ sản phẩm đi kèm với giá ưu đãi.",
    "86. Demo sản phẩm thực tế: Livestream trình diễn tính năng vượt trội.",
    "87. Quy trình đóng gói đơn hàng: Video cho thấy sự chỉn chu khi sản phẩm đến tay khách.",
    "88. So sánh giá trị: Tại sao sản phẩm của bạn đáng giá hơn đối thủ?.",
    "89. Bán bằng nhận thức: Giải thích tại sao khách hàng cần giải pháp này ngay bây giờ.",
    "90. Mời tham gia hệ thống phễu: Điều hướng khách từ Fanpage vào Group Zalo hoặc Messenger để được chăm sóc sâu.",
    "91. Giới thiệu sản phẩm sắp ra mắt: Tiết lộ một đoạn văn ngắn hoặc hình ảnh mờ ảo (teaser).",
    "92. Chương trình 'Mua 1 tặng 1' (BOGO): Kêu gọi hành động mua ngay.",
    "93. Gắn thẻ sản phẩm (Product Tag): Giúp khách hàng mua ngay trong ứng dụng thông qua liên kết với sàn TMĐT.",
    "94. Bài viết review Affiliate: Quay video trải nghiệm thực tế và gắn link mua hàng.",
    "95. Chứng thực từ người nổi tiếng (KOC/KOL): Chia sẻ video họ nói về thương hiệu của bạn.",
    "96. Cách thức sử dụng khác thường: Những công dụng bất ngờ của sản phẩm bạn đang bán.",
    "97. Bán khóa học/Ebook chuyên môn: Đóng gói chất xám thành tài sản số sinh lời.",
    "98. Hỗ trợ buổi quyên góp: Trích một phần doanh thu cho hoạt động thiện nguyện.",
    "99. Tư vấn trực tiếp 1-1: Kêu gọi comment để nhận lộ trình giải quyết vấn đề miễn phí.",
    "100. Nút kêu gọi hành động (CTA): Sử dụng các nút 'Gửi tin nhắn' để chốt đơn nhanh chóng."
  ]
};

// Ánh xạ thứ trong tuần sang nhóm ý tưởng Ebook (0 = Chủ Nhật, 1 = Thứ Hai, ..., 6 = Thứ Bảy)
const weekdayToGroupMap = {
  0: 5, // Chủ Nhật: Bán hàng & Chuyển đổi
  1: 1, // Thứ Hai: Giá trị & Giáo dục
  2: 4, // Thứ Ba: Tương tác & Thảo luận
  3: 1, // Thứ Tư: Giá trị & Giáo dục
  4: 2, // Thứ Năm: Viral & Reels
  5: 3, // Thứ Sáu: Lòng tin & Nhân văn
  6: 5  // Thứ Bảy: Bán hàng & Chuyển đổi
};

export { getScenarioForToday, getScenarioById, getAllScenarios, weeklySchedule, ebookIdeas, weekdayToGroupMap };
export default scenarios;
