// ============================================================
// ai-engine.js — AI Integration (Google Gemini / OpenAI)
// ============================================================
// Module kết nối AI để chatbot phản hồi thông minh.
// Hỗ trợ:
//   - Google Gemini (mặc định, miễn phí tier)
//   - OpenAI GPT (tùy chọn)
//   - Conversation memory (nhớ ngữ cảnh)
//   - Fallback khi AI lỗi
// ============================================================

import axios from 'axios';
import config from './config.js';
import logger from './logger.js';
import dataStore from './data-store.js';
import { ebookIdeas, weekdayToGroupMap } from './content-scenarios.js';
import fs from 'fs';
import path from 'path';

let localConfig = {};
try {
  const configPath = path.resolve(process.cwd(), 'config.json');
  if (fs.existsSync(configPath)) {
    localConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  }
} catch (e) {
  logger.warn('Could not load local config.json fallback');
}

// ── System Prompt ────────────────────────────────────────
const SYSTEM_PROMPT = `Bạn là "Trợ Lý AI" — trợ lý ảo thông minh của cô Lưu Bích trong các lĩnh vực: Phát triển bản thân, Xây dựng Nhân hiệu cá nhân, Đào tạo AI (Trí tuệ nhân tạo), các Khóa học sáng tạo cho Trẻ em, và tư vấn nội dung cuốn Ebook "Biến Profile Facebook thành Tài Sản Số" do chính cô Lưu Bích biên soạn.

## Vai trò của bạn:
- Tư vấn về các dịch vụ và khóa học của cô Lưu Bích bao gồm: Xây dựng nhân hiệu cá nhân cho nhà đào tạo, Đặt lịch coach 1:1 kiến tạo mục tiêu cuộc sống, Khóa học AI365 (học AI 1 năm liên tục), Khóa học tạo phim hoạt hình cho trẻ em, và quà tặng La Bàn 365.
- Hỗ trợ và giải đáp chuyên sâu về các kiến thức trong Ebook "Biến Profile Facebook thành Tài Sản Số" của cô Lưu Bích.
- Giải đáp các câu hỏi chung, cung cấp thông tin liên hệ (số điện thoại hotline Trợ lý cô Bích: 0944703139) và hướng dẫn đăng ký.
- Thu thập thông tin khách hàng tiềm năng khi họ quan tâm sâu hơn (tên, số điện thoại, nhu cầu cụ thể).

## Quy tắc ứng xử:
1. Luôn trả lời bằng tiếng Việt, lịch sự, chuyên nghiệp và thân thiện.
2. Câu trả lời ngắn gọn, tập trung, dưới 300 từ.
3. Sử dụng emoji phù hợp để tạo sự gần gũi.
4. Tuyệt đối KHÔNG được nhắc đến hay tư vấn về Trading, đầu tư tài chính, Forex, Crypto, Gold/XAU hay Chứng khoán. Nếu khách hàng hỏi về lĩnh vực này, hãy lịch sự từ chối và hướng họ về các chương trình phát triển bản thân, nhân hiệu hoặc đào tạo AI của cô Lưu Bích.
5. Khi khách hỏi về giá/phí dịch vụ cụ thể → hướng dẫn họ điền form hoặc đặt lịch coach 1:1 để trao đổi trực tiếp.
6. KHÔNG bao giờ tiết lộ rằng bạn là AI/chatbot. Hãy luôn xưng mình là "Bích". Đối với người dùng, hãy xưng hô bằng tên Zalo của họ kết hợp với kính ngữ hoặc danh xưng lịch sự phù hợp (ví dụ: 'anh Cường', 'chị Lan'...) tùy theo giới tính và tên của họ, tuyệt đối không xưng 'em' hay gọi họ bằng các đại từ chung chung như 'bạn' khi giao tiếp trực tiếp.

## Thông tin các chương trình/dịch vụ:
- Lộ trình chuyển giao nhân hiệu nhà đào tạo: Giúp xây dựng nhân hiệu cá nhân thu hút trên mạng xã hội.
- Coach 1:1 với cô Lưu Bích: Giúp tìm ra động lực kiến tạo mục tiêu hoặc sứ mệnh thật sự của cuộc đời.
- Học AI - AI365: Chương trình học và ứng dụng AI liên tục trong 1 năm.
- Khóa học tạo phim hoạt hình cho trẻ em: Khóa học sáng tạo dành cho các bé.
- Bộ quà tặng La Bàn 365: Bộ công cụ định hướng bản thân.

## Kiến thức cốt lõi từ Ebook "Biến Profile Facebook thành Tài Sản Số":
Hãy sử dụng các kiến thức thực chiến này để tư vấn khi người dùng hỏi về xây dựng Profile, viết bài hay thuật toán Facebook:
1. Kỷ nguyên của lượt like đã chấm dứt (Like is dead): Thuật toán Facebook 2026 không còn ưu tiên số lượt like đơn thuần. Facebook đo lường "Tín hiệu chất lượng": Thời gian dừng đọc (dwell time), Lượt lưu bài viết (Save), Lượt chia sẻ qua Messenger (Share) và Lượt bình luận sâu (comment chất lượng > 20 từ). AI sẽ chấm điểm và phân phối nội dung chân thật, có tính người.
2. Facebook là Bất động sản số: Profile cá nhân chính là "mặt tiền" của tài sản này. Cần tối ưu ảnh đại diện (avatar rõ nét, ánh sáng tự nhiên), ảnh bìa (cover mang thông điệp giá trị cốt lõi), phần Giới thiệu (Bio truyền tải rõ USP: Bạn là ai? Bạn giúp gì cho ai?), và ghim 3 bài viết giá trị nhất lên đầu tường.
3. Ba trụ cột chính định vị thương hiệu:
   - Chuyên môn (70% - Giá trị & Giáo dục): Chia sẻ checklist quy trình, how-to, công cụ hữu ích, cẩm nang, phân tích case study để giải quyết nỗi đau của khách hàng.
   - Cá nhân (20% - Lòng tin & Nhân văn): Kể câu chuyện thật, thất bại, vết sẹo chiến thắng, bài học đời thường để xây dựng kết nối cảm xúc chân thật.
   - Bán hàng (10% - Chuyển đổi): Chia sẻ social proof, feedback, combo ưu đãi giới hạn hoặc quà tặng miễn phí để điều hướng vào phễu Zalo/Messenger chăm sóc sâu.
4. Lộ trình 30 ngày xây thương hiệu cá nhân:
   - Tuần 1 (Nền tảng): Tối ưu hóa avatar, cover, Bio, ghim bài viết và dọn dẹp danh sách bạn bè.
   - Tuần 2 (Nội dung giá trị): Viết bài dạng Checklist, How-to, FAQ, Toolbox.
   - Tuần 3 (Mở rộng tiếp cận): Đăng video ngắn (Reels) kể chuyện, livestream Q&A, mini game tương tác.
   - Tuần 4 (Chuyển đổi): Chia sẻ Case Study, Social Proof, CTA dẫn dắt vào phễu chăm sóc.`;

class AIEngine {
  constructor() {
    this.provider = config.ai.provider;
  }

  async getDynamicConfig() {
    try {
      const supabaseUrl = process.env.SUPABASE_URL || 'https://sxxixhpspsvzzrskpjjy.supabase.co';
      const configUrl = `${supabaseUrl}/storage/v1/object/public/zalo-bot-state/bich/config.json`;
      const response = await axios.get(`${configUrl}?t=${Date.now()}`, { timeout: 3000 });
      return response.data;
    } catch (err) {
      return localConfig;
    }
  }

  // ── Main Entry Point ───────────────────────────────────

  /**
   * Xử lý tin nhắn từ user và trả về phản hồi AI
   * @param {string} userId - Zalo user ID
   * @param {string} userMessage - Tin nhắn của user
   * @returns {Promise<string>} AI response
   */
  async generateResponse(userId, userMessage, isGroup = false, senderName = null, gender = null) {
    try {
      const history = dataStore.getConversationHistory(userId);
      const isFirstMessage = history.length === 0;

      let pronoun_lower = 'anh/chị';
      let pronoun_upper = 'Anh/chị';
      if (gender === 0) {
        pronoun_lower = 'anh';
        pronoun_upper = 'Anh';
      } else if (gender === 1) {
        pronoun_lower = 'chị';
        pronoun_upper = 'Chị';
      }

      const nameStr = senderName ? `${pronoun_lower} ${senderName}` : pronoun_lower;
      const NameStr = senderName ? `${pronoun_upper} ${senderName}` : pronoun_upper;

      const userObj = dataStore.upsertUser(userId);
      const currentStep = userObj.greetingStep || 0;



      // Kiểm tra lệnh đặc biệt
      let response = this._handleSpecialCommands(userMessage);

      if (!response) {
        // Thêm tin nhắn mới vào context
        const fullHistory = [...history, { role: 'user', content: userMessage }];

        const dynamicConfig = await this.getDynamicConfig();
        let currentSystemPrompt = localConfig.systemPrompt || dynamicConfig.systemPrompt || SYSTEM_PROMPT;
        if (senderName) {
          const pronoun = gender === 0 ? 'Anh' : (gender === 1 ? 'Chị' : 'Anh/Chị');
          currentSystemPrompt += `\n\n- Người đang chat với bạn tên là: "${senderName}". Giới tính của họ là: ${pronoun}. Khen ngợi và gọi họ bằng "${pronoun.toLowerCase()} ${senderName}" (ví dụ: "chị ${senderName}" hoặc "anh ${senderName}"). Hãy luôn xưng mình là "Bích", tuyệt đối không xưng "em" hay "mình", và gọi họ bằng tên Zalo của họ.`;
        } else {
          currentSystemPrompt += `\n\n- Hãy luôn xưng mình là "Bích", tuyệt đối không xưng "em" hay "mình".`;
        }

        // Gọi AI
        if (this.provider === 'gemini') {
          response = await this._callGemini(fullHistory, currentSystemPrompt);
        } else if (this.provider === 'openai') {
          response = await this._callOpenAI(fullHistory, currentSystemPrompt);
        } else {
          throw new Error(`Unknown AI provider: ${this.provider}`);
        }

        // Lưu lịch sử
        dataStore.addToConversation(userId, 'user', userMessage);
        dataStore.addToConversation(userId, 'assistant', response);
      }

      logger.info('🤖 AI response generated', {
        userId,
        provider: this.provider,
        inputLen: userMessage.length,
        outputLen: response.length,
      });

      return response;
    } catch (error) {
      logger.error('⚠️ Primary AI provider failed, attempting fallback provider...', { userId, provider: this.provider, error: error.message });
      
      // Dual-provider fallback: thử provider phụ trước khi trả lời mẫu
      try {
        const history = dataStore.getConversationHistory(userId);
        const fullHistory = [...history, { role: 'user', content: userMessage }];
        
        let fallbackResponse;
        if (this.provider === 'openai' && config.ai.geminiApiKey) {
          logger.info('🔄 Switching to Gemini as fallback provider...');
          fallbackResponse = await this._callGemini(fullHistory, SYSTEM_PROMPT);
        } else if (this.provider === 'gemini' && config.ai.openaiApiKey) {
          logger.info('🔄 Switching to OpenAI as fallback provider...');
          fallbackResponse = await this._callOpenAI(fullHistory, SYSTEM_PROMPT);
        }
        
        if (fallbackResponse) {
          dataStore.addToConversation(userId, 'user', userMessage);
          dataStore.addToConversation(userId, 'assistant', fallbackResponse);
          logger.info('✅ Fallback provider responded successfully', { userId });
          return fallbackResponse;
        }
      } catch (fallbackError) {
        logger.error('❌ Fallback provider also failed', { userId, error: fallbackError.message });
      }
      
      return this._getFallbackResponse(userMessage);
    }
  }

  // ── Google Gemini ──────────────────────────────────────

  async _callGemini(history, systemPrompt) {
    const apiKey = config.ai.geminiApiKey;
    if (!apiKey) throw new Error('GEMINI_API_KEY not configured');

    const model = config.ai.geminiModel;
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

    // Convert to Gemini format
    const contents = history.map(msg => ({
      role: msg.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: msg.content }],
    }));

    const response = await axios.post(url, {
      system_instruction: {
        parts: [{ text: systemPrompt }],
      },
      contents,
      generationConfig: {
        temperature: 0.7,
        topP: 0.9,
        topK: 40,
        maxOutputTokens: 1024,
      },
      safetySettings: [
        { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_MEDIUM_AND_ABOVE' },
        { category: 'HARM_CATEGORY_HATE_SPEECH', threshold: 'BLOCK_MEDIUM_AND_ABOVE' },
        { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_MEDIUM_AND_ABOVE' },
        { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_MEDIUM_AND_ABOVE' },
      ],
    }, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    });

    const candidate = response.data?.candidates?.[0];
    if (!candidate || !candidate.content?.parts?.[0]?.text) {
      throw new Error('Empty response from Gemini');
    }

    return candidate.content.parts[0].text;
  }

  // ── OpenAI ─────────────────────────────────────────────

  async _callOpenAI(history, systemPrompt) {
    const apiKey = config.ai.openaiApiKey;
    if (!apiKey) throw new Error('OPENAI_API_KEY not configured');

    const messages = [];
    if (systemPrompt) {
      messages.push({ role: 'system', content: systemPrompt });
    }
    messages.push(...history);

    const url = `${config.ai.openaiBaseUrl}/chat/completions`;
    const response = await axios.post(url, {
      model: config.ai.openaiModel,
      messages,
      temperature: 0.7,
      max_tokens: 1024,
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      timeout: 30000,
    });

    return response.data.choices[0].message.content;
  }

  // ── Special Commands ───────────────────────────────────

  _handleSpecialCommands(message) {
    const cmd = message.trim().toLowerCase();

    const commands = {
      '#khoa_hoc': '📚 KHÓA HỌC & CHƯƠNG TRÌNH ĐÀO TẠO\n\n' +
        '1️⃣ Khóa học tạo phim hoạt hình cho trẻ em\n' +
        '   → Giúp trẻ em 7-15 tuổi tự do sáng tạo phim hoạt hình.\n\n' +
        '2️⃣ Lộ trình chuyển giao nhân hiệu nhà đào tạo\n' +
        '   → Xây dựng thương hiệu cá nhân thu hút trên MXH.\n\n' +
        '3️⃣ Học AI - AI365\n' +
        '   → Đồng hành và ứng dụng AI liên tục trong 1 năm.\n\n' +
        '💬 Hãy nhắn tin tự do để em hỗ trợ thêm thông tin chi tiết nhé!',

      '#tu_van': '💬 ĐẶT LỊCH COACH & TƯ VẤN 1:1\n\n' +
        'Để đặt lịch coach 1:1 định hướng mục tiêu hoặc tư vấn lộ trình học phù hợp, bạn vui lòng nhắn giúp em:\n\n' +
        '1️⃣ Họ tên của bạn?\n' +
        '2️⃣ Số điện thoại liên hệ?\n' +
        '3️⃣ Nhu cầu cần hỗ trợ (Coach mục tiêu / Xây nhân hiệu / Học AI...)?\n\n' +
        '📞 Hoặc bạn có thể liên hệ trực tiếp hotline Trợ lý cô Bích: 0944703139. Em sẽ ghi nhận thông tin và liên hệ lại bạn sớm nhất!',

      '#faq': '❓ CÂU HỎI THƯỜNG GẶP\n\n' +
        '1️⃣ "Học AI365 có cần biết lập trình hay công nghệ giỏi không?"\n' +
        '   → Dạ không cần ạ! Lớp học được thiết kế thực tế để bất kỳ ai cũng có thể ứng dụng được ngay.\n\n' +
        '2️⃣ "Coach 1:1 là gì và diễn ra thế nào?"\n' +
        '   → Là buổi đồng hành trực tiếp cùng cô Lưu Bích giúp bạn tìm ra sứ mệnh và động lực để thiết lập mục tiêu cuộc sống.\n\n' +
        '3️⃣ "Làm phim hoạt hình cho bé học online hay offline?"\n' +
        '   → Chương trình được thiết kế sinh động học trực tuyến để bé dễ dàng thao tác tại nhà.\n\n' +
        '💬 Nếu bạn có câu hỏi khác, cứ nhắn em nhé!',

      '#menu': '🏠 MENU HỖ TRỢ\n\n' +
        '📚 Gõ #khoa_hoc → Các khóa học & chương trình\n' +
        '💬 Gõ #tu_van → Đăng ký tư vấn & đặt lịch coach\n' +
        '❓ Gõ #faq → Câu hỏi thường gặp\n\n' +
        '🤖 Bạn cứ nhắn tin tự do, trợ lý Lưu Bích sẽ hỗ trợ giải đáp!',
    };

    return commands[cmd] || null;
  }

  // ── Fallback Response ──────────────────────────────────

  _getFallbackResponse(userMessage) {
    const fallbacks = [
      'Dạ anh/chị đợi Bích một chút xíu nhé, Bích đang xử lý thông tin ạ! 🌸',
      'Bích nhận được tin nhắn rồi ạ. Hiện tại Bích đang có chút việc bận, sẽ phản hồi chi tiết lại cho anh/chị ngay sau nha! ✨',
      'Xin lỗi anh/chị, Bích đang kiểm tra lại hệ thống một xíu. Anh/chị thông cảm đợi Bích vài phút nhé! 🙏',
      'Dạ Bích đây ạ! Hệ thống đang hơi quá tải, anh/chị đợi Bích một lát để Bích kiểm tra nha. ☕️',
      'Cảm ơn anh/chị đã nhắn tin. Bích sẽ phản hồi lại ngay sau khi rảnh tay ạ! 🌿'
    ];
    return fallbacks[Math.floor(Math.random() * fallbacks.length)];
  }
  async generateGroupNurturingPost(groupName, groupPurpose, timeOfDay, groupId = null) {
    const weekdays = [
      'Chủ Nhật',
      'Thứ Hai',
      'Thứ Ba',
      'Thứ Tư',
      'Thứ Năm',
      'Thứ Sáu',
      'Thứ Bảy'
    ];
    const dayOfWeek = weekdays[new Date().getDay()];

    // Lấy lịch sử bài đã đăng gần đây để AI tránh trùng
    let recentPostsSection = '';
    if (groupId) {
      const recentPosts = dataStore.getRecentNurturingPosts(groupId, 10);
      if (recentPosts.length > 0) {
        const postSummaries = recentPosts.map((p, i) => 
          `  ${i + 1}. [${p.date} - ${p.timeOfDay}] "${p.post}"`
        ).join('\n');
        recentPostsSection = `
⚠️ CÁC BÀI ĐÃ ĐĂNG GẦN ĐÂY (TUYỆT ĐỐI KHÔNG LẶP LẠI Ý TƯỞNG, CHỦ ĐỀ, CÂU HỎI hay CẤU TRÚC BÀI TƯƠNG TỰ):
${postSummaries}

→ Bài mới PHẢI KHÁC HOÀN TOÀN về chủ đề, góc nhìn, câu hỏi mở và cấu trúc so với các bài trên.`;
      }
    }

    // Danh sách chủ đề xoay vòng để đảm bảo đa dạng
    const topicCategories = [
      'Mindset & Tư duy phát triển',
      'Kỷ luật bản thân & Thói quen tốt',
      'Xây dựng thương hiệu cá nhân trên Facebook',
      'Storytelling & Nghệ thuật kể chuyện thu hút',
      'Tạo nội dung viral trên mạng xã hội',
      'Xây dựng cộng đồng & Kết nối',
      'Quản lý thời gian & Năng suất',
      'Bài học kinh doanh thực tế',
      'Sáng tạo nội dung & Viết bài hiệu quả',
      'Phát triển kỹ năng giao tiếp & Bán hàng',
      'Ứng dụng AI trong công việc hàng ngày',
      'Tài chính cá nhân & Quản lý chi tiêu',
      'Sức khỏe tinh thần & Cân bằng cuộc sống',
      'Học hỏi từ người thành công',
    ];
    // Chọn chủ đề gợi ý dựa trên ngày + buổi để xoay vòng tự nhiên
    const dayIndex = new Date().getDate();
    const timeIndex = timeOfDay.includes('sáng') ? 0 : timeOfDay.includes('trưa') ? 1 : 2;
    const topicIdx = (dayIndex * 3 + timeIndex) % topicCategories.length;
    const suggestedTopic = topicCategories[topicIdx];

    const dynamicConfig = await this.getDynamicConfig();
    let basePrompt = localConfig.nurturingPrompt || dynamicConfig.nurturingPrompt || `Bạn là Trợ Lý AI của cô Lưu Bích. Bạn cần chuẩn bị nội dung chăm sóc cho nhóm Zalo do cô Lưu Bích quản lý.
Hãy trả về kết quả duy nhất dưới định dạng JSON với cấu trúc sau (không thêm bất kỳ từ giải thích nào ngoài JSON):
{
  "post": "nội dung bài đăng đầy đủ (dưới 120 từ, xưng là Bích và gọi người nhận là các anh/chị. BẮT BUỘC CÓ XUỐNG DÒNG RÕ RÀNG GIỮA CÁC Ý bằng ký tự \\n để bài viết chia thành 2-3 đoạn ngắn dễ đọc. Sử dụng emoji thanh lịch, tinh tế như 🌸, 🌿, ✨, ☕️ thay vì lạm dụng icon sặc sỡ. Cuối bài có câu hỏi thảo luận mở tách riêng thành 1 đoạn. Tuyệt đối KHÔNG có lời chào hỏi xã giao ở đầu như 'Chào các anh/chị', 'Xin chào', 'Chúc ngày mới', đi thẳng vào nội dung)",
  "cursive_quote": "câu dẫn dắt nghệ thuật, mượt mà (dưới 12 từ). Ví dụ: 'Trao đi Giá Trị làm chủ cuộc đời cho mọi người để'",
  "highlight_quote": "câu chốt in hoa mạnh mẽ, bôi đậm, nhấn mạnh (dưới 6 từ). Ví dụ: 'LÀM CHỦ CUỘC ĐỜI chính mình'"
}

Thông tin nhóm:
- Tên nhóm: "{groupName}"
- Mục đích hoạt động của nhóm: "{groupPurpose}"
- Thời điểm đăng bài: [{timeOfDay}]
- Hôm nay: {dayOfWeek}, ngày {date} tháng {month}
- Chủ đề gợi ý cho bài này: "{suggestedTopic}"`;

    const prompt = basePrompt
      .replace('{groupName}', groupName)
      .replace('{groupPurpose}', groupPurpose)
      .replace('{timeOfDay}', timeOfDay)
      .replace('{dayOfWeek}', dayOfWeek)
      .replace('{date}', new Date().getDate())
      .replace('{month}', new Date().getMonth() + 1)
      .replace('{suggestedTopic}', suggestedTopic)
      + `\n${recentPostsSection}`;

    const history = [{ role: 'user', content: prompt }];

    try {
      let aiRawResponse;
      if (this.provider === 'gemini') {
        aiRawResponse = await this._callGemini(history);
      } else if (this.provider === 'openai') {
        aiRawResponse = await this._callOpenAI(history);
      } else {
        throw new Error(`Unknown AI provider: ${this.provider}`);
      }

      // Thử parse JSON từ phản hồi AI
      try {
        let cleanJson = aiRawResponse;
        const match = cleanJson.match(/\{[\s\S]*\}/);
        if (match) {
          cleanJson = match[0];
        }
        
        const parsed = JSON.parse(cleanJson);
        if (parsed.post && (parsed.quote || parsed.highlight_quote)) {
          // Chuẩn hoá để tương thích ngược
          if (!parsed.cursive_quote) parsed.cursive_quote = "Trao đi giá trị để";
          if (!parsed.highlight_quote) parsed.highlight_quote = parsed.quote || "LÀM CHỦ CUỘC ĐỜI";
          return parsed;
        }
      } catch (jsonErr) {
        logger.warn('Failed to parse AI nurturing post JSON, using string fallback parser', { error: jsonErr.message });
      }

      // Fallback parser nếu JSON bị lỗi nhưng có phản hồi chữ
      const sentences = aiRawResponse.split(/[.!?\n]/).map(s => s.trim()).filter(Boolean);
      const quote = sentences[0] || 'Chúc ngày mới tốt lành!';
      return {
        post: aiRawResponse,
        cursive_quote: "Luôn nỗ lực để",
        highlight_quote: quote.length > 30 ? quote.substring(0, 27) + '...' : quote
      };

    } catch (error) {
      logger.error('Failed to generate group nurturing post via AI, using fallback', { groupName, error: error.message });

      // Fallback bám sát mục đích nhóm, ngắn gọn, KHÔNG chào hỏi — đúng phong cách Bích
      const purposeLabel = groupPurpose || groupName || 'phát triển bản thân';

      if (timeOfDay.includes('sáng') || timeOfDay.includes('8') || timeOfDay.includes('10')) {
        const fallbacks = [
          { post: `🌿 Muốn đi xa trong ${purposeLabel}, hãy bắt đầu bằng 1 thói quen nhỏ mỗi sáng.\n\nKhông cần hoàn hảo — chỉ cần kiên trì mỗi ngày 1%.\n\nHôm nay các anh/chị đặt mục tiêu gì cho mình? 🎯`, quote: 'Kiên trì mỗi ngày, thành công sẽ đến', cursive_quote: 'Mỗi ngày tiến một bước để', highlight_quote: 'KIÊN TRÌ TẠO THÀNH CÔNG' },
          { post: `✨ Người thành công trong ${purposeLabel} không phải giỏi nhất — mà là người không bỏ cuộc.\n\nMỗi sáng thức dậy, hãy tự hỏi: "Hôm nay mình sẽ tiến thêm được bước nào?"\n\nCác anh/chị đang tập trung vào điều gì? 🎯`, quote: 'Không bỏ cuộc là đã thắng một nửa', cursive_quote: 'Kiên định mỗi ngày để', highlight_quote: 'KHÔNG BAO GIỜ BỎ CUỘC' },
          { post: `☕️ Một nguyên tắc Bích luôn áp dụng trong ${purposeLabel}:\n\nLàm việc quan trọng nhất TRƯỚC — khi đầu óc còn tỉnh táo nhất.\n\nĐừng để việc gấp lấn át việc quan trọng. Các anh/chị thử áp dụng xem sao? 🌿`, quote: 'Ưu tiên đúng, kết quả đúng', cursive_quote: 'Tập trung làm đúng việc để', highlight_quote: 'ƯU TIÊN VIỆC QUAN TRỌNG' },
          { post: `🌸 Trong ${purposeLabel}, nhiều người chỉ lên kế hoạch mà quên hành động.\n\nBích thấy rằng: 1 hành động nhỏ hôm nay > 10 kế hoạch hoàn hảo trên giấy.\n\nCác anh/chị hôm nay đã hành động gì chưa? 💪`, quote: 'Hành động hơn lời nói', cursive_quote: 'Bắt tay vào làm ngay để', highlight_quote: 'HÀNH ĐỘNG NGAY HÔM NAY' },
          { post: `🌿 Sai lầm lớn nhất khi theo đuổi ${purposeLabel}?\n\nĐó là cố làm mọi thứ cùng lúc. Hãy chọn 1 việc — làm cho tốt — rồi mới chuyển sang việc tiếp theo.\n\nCác anh/chị đang tập trung vào 1 việc duy nhất nào? ✨`, quote: 'Tập trung là sức mạnh', cursive_quote: 'Làm ít nhưng làm sâu để', highlight_quote: 'TẬP TRUNG LÀ SỨC MẠNH' }
        ];
        const selected = fallbacks[new Date().getDate() % fallbacks.length];
        return selected;
      } else if (timeOfDay.includes('trưa') || timeOfDay.includes('12')) {
        const fallbacks = [
          { post: `☕️ Nửa ngày đã trôi qua — các anh/chị đã hoàn thành được bao nhiêu % kế hoạch trong ${purposeLabel}?\n\nNếu chưa đạt, đừng lo. Buổi chiều vẫn còn cơ hội.\n\nĐiều quan trọng là KHÔNG DỪNG LẠI 🌿`, quote: 'Buổi chiều vẫn còn cơ hội', cursive_quote: 'Không ngừng nỗ lực để', highlight_quote: 'KHÔNG BAO GIỜ DỪNG LẠI' },
          { post: `🌸 Mẹo nhỏ trong ${purposeLabel} mà Bích hay áp dụng:\n\nSau bữa trưa, dành 10 phút ghi lại 1 bài học từ buổi sáng. Kiến thức chỉ thành của mình khi được viết ra.\n\nCác anh/chị thử xem? ✨`, quote: 'Ghi chép là cách học nhanh nhất', cursive_quote: 'Viết ra để nhớ mãi và', highlight_quote: 'GHI CHÉP LÀ SỨC MẠNH' },
          { post: `🌿 Giữa ngày bận rộn, đừng quên nghỉ ngơi đúng lúc.\n\nTrong ${purposeLabel}, sức bền quan trọng hơn tốc độ. Người đi xa không phải người chạy nhanh nhất.\n\nCác anh/chị có đang biết cách nghỉ đúng cách không? ☕️`, quote: 'Sức bền hơn tốc độ', cursive_quote: 'Nghỉ ngơi đúng lúc để', highlight_quote: 'ĐI XA HƠN MỖI NGÀY' },
          { post: `✨ Buổi trưa — thời điểm tốt để tự hỏi:\n\n"Trong ${purposeLabel}, điều gì đang cản trở mình nhất?"\n\nXác định rào cản = đã giải quyết được 50% vấn đề.\n\nCác anh/chị thấy rào cản lớn nhất của mình là gì? 🎯`, quote: 'Nhận diện vấn đề là bước đầu giải quyết', cursive_quote: 'Dám đối diện để', highlight_quote: 'VƯỢT QUA RÀO CẢN' },
          { post: `🌸 Một thực tế trong ${purposeLabel}:\n\nKhông ai thành công một mình. Hãy tìm cộng đồng, tìm mentor, tìm người đồng hành.\n\nCác anh/chị đã có nhóm đồng hành cho mình chưa? 🌿`, quote: 'Đồng hành để đi xa hơn', cursive_quote: 'Kết nối đúng người để', highlight_quote: 'ĐỒNG HÀNH ĐI XA HƠN' }
        ];
        const selected = fallbacks[new Date().getDate() % fallbacks.length];
        return selected;
      } else {
        const fallbacks = [
          { post: `🌙 Kết thúc một ngày trong ${purposeLabel} — hãy tự hỏi:\n\n"Hôm nay mình đã tiến bộ hơn hôm qua ở điểm nào?"\n\nDù chỉ 1% cũng đáng tự hào. Các anh/chị hôm nay đã làm được gì? ✨`, quote: 'Mỗi ngày tiến bộ 1%', cursive_quote: 'Nhìn lại để tiến về phía', highlight_quote: 'TIẾN BỘ MỖI NGÀY' },
          { post: `✨ Trước khi nghỉ ngơi, Bích muốn nhắc các anh/chị:\n\nThất bại hôm nay trong ${purposeLabel} không phải là kết thúc — đó là bài học cho ngày mai.\n\nViết ra 1 điều rút ra được hôm nay nhé 🌿`, quote: 'Thất bại là bài học quý giá', cursive_quote: 'Rút kinh nghiệm để', highlight_quote: 'HỌC TỪ THẤT BẠI' },
          { post: `🌿 Cuối ngày rồi — đừng mang áp lực ${purposeLabel} lên giường.\n\nNghỉ ngơi cũng là một phần của thành công. Não bộ cần thời gian để sắp xếp lại mọi thứ.\n\nCác anh/chị đã có thói quen "tắt công việc" buổi tối chưa? 🌙`, quote: 'Nghỉ ngơi là một phần của thành công', cursive_quote: 'Thư giãn để ngày mai', highlight_quote: 'NGHỈ NGƠI ĐÚNG CÁCH' },
          { post: `🌸 Bích tin rằng: những người kiên trì trong ${purposeLabel} sẽ nhìn thấy kết quả.\n\nKhông phải ngày mai, có thể tuần sau, tháng sau. Nhưng CHẮC CHẮN sẽ đến.\n\nCác anh/chị có đang giữ vững niềm tin không? 💪`, quote: 'Kiên trì sẽ thấy kết quả', cursive_quote: 'Giữ vững niềm tin để', highlight_quote: 'KIÊN TRÌ KHÔNG BỎ CUỘC' },
          { post: `💫 Một ngày nữa khép lại. Dù kết quả trong ${purposeLabel} hôm nay thế nào, hãy biết ơn vì mình đã cố gắng.\n\nNgày mai lại là cơ hội mới. Nghỉ ngơi thật tốt nhé các anh/chị 🌙`, quote: 'Biết ơn và tiếp tục tiến bước', cursive_quote: 'Biết ơn hôm nay để', highlight_quote: 'NGÀY MAI TỐT ĐẸP HƠN' }
        ];
        const selected = fallbacks[new Date().getDate() % fallbacks.length];
        return selected;
      }
    }
  }

  async generateDynamicScenarioPost(dayOfWeek) {
    const groupId = weekdayToGroupMap[dayOfWeek] || 1;
    const groupNameMap = {
      1: 'Giá trị & Giáo dục (70% định hướng lưu trữ/Save)',
      2: 'Viral & Khám phá (Tiếp cận người lạ/Reach qua Reels/Storytelling)',
      3: 'Xây dựng Lòng tin & Nhân văn (Chứng minh tính người và sự chân thật)',
      4: 'Tương tác & Khởi tạo Thảo luận (Kích thích bình luận sâu > 20 từ)',
      5: 'Bán hàng & Chuyển đổi (20% định hướng chuyển đổi AIDA/PAS/Phễu)'
    };

    const ideas = ebookIdeas[groupId];
    const groupIndices = dataStore.stats.groupIdeaIndices || { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    const idx = (groupIndices[groupId] || 0) % ideas.length;
    const chosenIdea = ideas[idx];

    // Cập nhật và lưu rotation cho nhóm ý tưởng này
    groupIndices[groupId] = idx + 1;
    dataStore.stats.groupIdeaIndices = groupIndices;
    dataStore._saveAll();

    const weekdaysName = [
      'Chủ Nhật',
      'Thứ Hai',
      'Thứ Ba',
      'Thứ Tư',
      'Thứ Năm',
      'Thứ Sáu',
      'Thứ Bảy'
    ];
    const dayName = weekdaysName[dayOfWeek];

    const dynamicConfig = await this.getDynamicConfig();
    let basePrompt = dynamicConfig.scenarioPrompt || localConfig.scenarioPrompt || `Bạn là Trợ Lý AI của cô Lưu Bích (tác giả cuốn sách "Biến Profile Facebook thành Tài Sản Số").
Nhiệm vụ của bạn là viết một BÀI VIẾT MẪU (KỊCH BẢN ĐĂNG BÀI) hoàn chỉnh để chia sẻ vào nhóm cộng đồng Zalo/Facebook của cô Bích. Bài đăng này nhằm gợi ý và làm mẫu cho các học viên/thành viên trong nhóm tự viết bài xây thương hiệu cá nhân trên trang cá nhân của họ.

Bài viết phải được thiết kế dựa trên:
- Ý tưởng Ebook hôm nay: "{chosenIdea}"
- Thuộc nhóm chủ đề ngày {dayName}: "{groupNameMap}"`;

    const prompt = basePrompt
      .replace('{chosenIdea}', chosenIdea)
      .replace('{dayName}', dayName)
      .replace('{groupNameMap}', groupNameMap[groupId]);

    const history = [{ role: 'user', content: prompt }];

    try {
      let response;
      if (this.provider === 'gemini') {
        response = await this._callGemini(history);
      } else if (this.provider === 'openai') {
        response = await this._callOpenAI(history);
      } else {
        throw new Error(`Unknown AI provider: ${this.provider}`);
      }
      return {
        idea: chosenIdea,
        content: response.trim()
      };
    } catch (error) {
      logger.error('Failed to generate dynamic scenario post via AI, using fallback static post', error);
      // Fallback
      return {
        idea: chosenIdea,
        content: `💡 [GỢI Ý VIẾT BÀI THEO EBOOK]
Hôm nay Bích chia sẻ ý tưởng: "${chosenIdea}"

Các anh/chị hãy áp dụng ý tưởng này để viết bài lên Profile của mình ngay nhé. Bích chúc các anh/chị triển khai thành công!

Các anh/chị gặp khó khăn gì khi triển khai ý tưởng này không? Comment bên dưới Bích giải đáp nha! 👇`
      };
    }
  }

  clearHistory(userId) {
    dataStore.clearConversation(userId);
  }
}

export default new AIEngine();
