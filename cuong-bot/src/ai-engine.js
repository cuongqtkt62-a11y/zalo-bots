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
import { getNhauScenario } from './nhau-tam-an-scenarios.js';
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
const ASSISTANT_PHONE = config.zalo.assistantPhone || '0559668977';

const SYSTEM_PROMPT = `Bạn là "Trợ Lý AI" — trợ lý ảo thông minh của anh Cường (OPC Cường) trong các lĩnh vực: Trading (giao dịch tài chính), Hệ thống Giao dịch SMC-4EMA, VSA-ICT-H5, Trading Bot tín hiệu 24/7 và Tự động hóa doanh nghiệp một người (OPC).

## Vai trò của bạn:
- Tư vấn về các khóa học, tài liệu và phương pháp giao dịch của anh Cường bao gồm: SMC-4EMA, VSA-ICT-H5.
- Hướng dẫn đăng ký nhận tín hiệu từ Trading Bot và hỗ trợ kết nối Telegram bot.
- Giới thiệu về quy trình và mô hình vận hành Doanh nghiệp một người (OPC) tích hợp AI Automation.
- Giải đáp các thắc mắc chung về trading, cung cấp thông tin liên hệ và hướng dẫn tham gia.
- Thu thập thông tin khách hàng tiềm năng khi họ muốn đăng ký học hoặc nhận tín hiệu bot (tên, số điện thoại, nhu cầu cụ thể).

## Thông tin liên hệ & Đường link đăng ký:
- Số điện thoại trợ lý anh Cường: ${ASSISTANT_PHONE}
- Khi khách hàng muốn liên hệ trực tiếp, hãy cung cấp số điện thoại này.
- Khi khách hàng hỏi về các dự án, khóa học, hoặc muốn đăng ký, BẮT BUỘC gửi ĐÚNG 1 trong 3 đường link chính thức sau tùy theo nhu cầu:
  1. Kinh doanh Nhàu Tâm An: https://opc-kinh-doanh.vercel.app
  2. Đầu tư (Trading & Bot 24/7): https://opc-dau-tu.vercel.app
  3. Tự động hoá Zalo (Doanh nghiệp 1 người - OPC): https://cuongopc.netlify.app/

## Quy tắc ứng xử:
1. Luôn trả lời bằng tiếng Việt, lịch sự, chuyên nghiệp, tự tin và thân thiện.
2. Câu trả lời ngắn gọn, tập trung, dưới 300 từ.
3. Sử dụng emoji phù hợp để tạo sự gần gũi.
4. Trả lời cởi mở và chuyên sâu về Trading, kỹ thuật SMC, FVG, EMA Dragon, VSA. Khác với trợ lý cô Bích, bạn ĐƯỢC PHÉP tư vấn về các khóa học và kiến thức trading của anh Cường. Tuy nhiên, hãy lưu ý rằng bạn chỉ cung cấp thông tin tham khảo kỹ thuật, không phải lời khuyên đầu tư tài chính trực tiếp.
5. Khi khách hỏi về giá/phí dịch vụ cụ thể hoặc muốn chuyển giao hệ thống → hướng dẫn họ điền form đăng ký hoặc đặt lịch hẹn trao đổi trực tiếp với anh Cường.
6. KHÔNG bao giờ tiết lộ rằng bạn là AI/chatbot. Hãy xưng là "em" (trợ lý của anh Cường).`;

class AIEngine {
  constructor() {
    this.provider = config.ai.provider;
  }

  async getDynamicConfig() {
    try {
      const supabaseUrl = process.env.SUPABASE_URL || 'https://sxxixhpspsvzzrskpjjy.supabase.co';
      const configUrl = `${supabaseUrl}/storage/v1/object/public/zalo-bot-state/cuong/config.json`;
      // Thêm cache buster để luôn lấy bản mới nhất
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


      if (!isGroup) {
        const userObj = dataStore.upsertUser(userId);
        const currentStep = userObj.greetingStep || 0;


      }

      // Kiểm tra lệnh đặc biệt
      let response = this._handleSpecialCommands(userMessage);

      if (!response) {
        // Thêm tin nhắn mới vào context
        const fullHistory = [...history, { role: 'user', content: userMessage }];

        const dynamicConfig = await this.getDynamicConfig();
        let systemPrompt = dynamicConfig.systemPrompt || localConfig.systemPrompt || SYSTEM_PROMPT;
        if (isGroup) {
          const groupInfo = dataStore.getApprovedGroup(userId);
          if (groupInfo) {
            systemPrompt += `\n\n## Ngữ cảnh nhóm Zalo hiện tại:\n- Tên nhóm: "${groupInfo.name}"\n- Mục đích hoạt động: "${groupInfo.purpose}"\n- Bạn đang trả lời tin nhắn trong nhóm chat này. Hãy trả lời ngắn gọn, thân thiện, xưng "em" (trợ lý của anh Cường) và gọi cả nhà là "cả nhà".`;
          }
        }
        
        let currentSystemPrompt = systemPrompt;
        if (senderName) {
          const pronoun = gender === 0 ? 'Anh' : (gender === 1 ? 'Chị' : 'Anh/Chị');
          currentSystemPrompt += `\n\n- Người đang chat với bạn tên là: "${senderName}". Giới tính của họ là: ${pronoun}. Hãy xưng hô khéo léo và gọi tên họ trong câu trả lời để tạo sự thân thiện.`;
        }

        // Bơm Kịch bản Onboarding (SKILL 01)
        if (!isGroup) {
          const userObj = dataStore.upsertUser(userId);
          const currentStep = userObj.greetingStep || 0;
          if (currentStep < 3) {
            currentSystemPrompt += `\n\n## KỊCH BẢN ONBOARDING (QUAN TRỌNG):
Bạn ĐANG trong quá trình Onboarding khách mới (Bước hiện tại: ${currentStep + 1}/3). Bạn PHẢI tuân thủ các bước sau:
- Bước 1 (Nếu chưa chào): Chào hỏi, giới thiệu bạn là trợ lý AI của anh Cường.
- Bước 2 (Khách đã chào lại): Gợi mở nhu cầu (Kinh doanh hay Đầu tư?).
- Bước 3 (Khách đã chia sẻ): Cung cấp đúng đường link hệ thống (Kinh doanh: opc-kinh-doanh.vercel.app | Đầu tư: opc-dau-tu.vercel.app | Zalo: cuongopc.netlify.app).
Hãy phản hồi CỰC KỲ NGẮN GỌN (1-2 câu) đúng với Bước ${currentStep + 1} và chờ khách trả lời, KHÔNG nói tràn lan các bước tiếp theo!`;
            // Cập nhật step
            dataStore.setGreetingStep(userId, currentStep + 1);
          }
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

  async _callGemini(history, customSystemPrompt = SYSTEM_PROMPT) {
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
        parts: [{ text: customSystemPrompt }],
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

  async _callOpenAI(history, customSystemPrompt = SYSTEM_PROMPT) {
    const apiKey = config.ai.openaiApiKey;
    if (!apiKey) throw new Error('OPENAI_API_KEY not configured');

    const messages = [];
    if (customSystemPrompt) {
      messages.push({ role: 'system', content: customSystemPrompt });
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
        '1️⃣ Khóa học Trading SMC-4EMA & VSA-ICT-H5\n' +
        '   → Hệ thống hóa kiến thức giao dịch từ cơ bản đến nâng cao.\n\n' +
        '2️⃣ Đăng ký nhận tín hiệu Trading Bot\n' +
        '   → Nhận cảnh báo setup Sonic R × FVG × SMC thời gian thực qua Telegram.\n\n' +
        '3️⃣ Chuyển giao quy trình Doanh nghiệp một người (OPC)\n' +
        '   → Ứng dụng AI và RPA tự động hóa vận hành doanh nghiệp tối giản.\n\n' +
        '💬 Hãy nhắn tin tự do để em hỗ trợ thêm thông tin chi tiết nhé!',

      '#tu_van': '💬 ĐẶT LỊCH HẸN & ĐĂNG KÝ HỌC\n\n' +
        'Để đăng ký khóa học hoặc nhận tư vấn từ anh Cường, bạn vui lòng để lại thông tin:\n\n' +
        '1️⃣ Họ tên của bạn?\n' +
        '2️⃣ Số điện thoại liên hệ?\n' +
        '3️⃣ Nhu cầu cần hỗ trợ (Học Trading / Nhận tín hiệu Bot / Tự động hóa OPC)?\n\n' +
        '📞 Em sẽ ghi nhận thông tin và liên hệ lại bạn sớm nhất!',

      '#faq': '❓ CÂU HỎI THƯỜNG GẶP\n\n' +
        '1️⃣ "Trading Bot quét những thị trường nào?"\n' +
        '   → Bot quét toàn bộ các cặp USDT Futures trên sàn Binance theo thời gian thực.\n\n' +
        '2️⃣ "Hệ thống SMC-4EMA có phù hợp với người mới không?"\n' +
        '   → Dạ có! Lộ trình hướng dẫn chi tiết từ cơ bản, cách quản trị rủi ro trước khi vào lệnh thực tế.\n\n' +
        '3️⃣ "Làm sao để kết nối nhận tín hiệu?"\n' +
        '   → Bạn chỉ cần đăng ký qua form, trợ lý sẽ add bạn vào nhóm Telegram nhận tín hiệu trực tiếp.\n\n' +
        '💬 Nếu bạn có câu hỏi khác, cứ nhắn em nhé!',

      '#menu': '🏠 MENU HỖ TRỢ\n\n' +
        '📚 Gõ #khoa_hoc → Các chương trình đào tạo & Bot\n' +
        '💬 Gõ #tu_van → Đăng ký tư vấn & đặt lịch hẹn\n' +
        '❓ Gõ #faq → Câu hỏi thường gặp\n\n' +
        '🤖 Bạn cứ nhắn tin tự do, trợ lý anh Cường sẽ hỗ trợ giải đáp!',
    };

    return commands[cmd] || null;
  }

  // ── Fallback Response ──────────────────────────────────

  _getFallbackResponse(userMessage) {
    const fallbacks = [
      'Dạ anh/chị đợi em một chút nhé, hệ thống đang xử lý thông tin ạ! ⏳',
      'Em nhận được tin nhắn rồi ạ. Hiện tại em đang bận chút xíu, sẽ phản hồi chi tiết lại cho anh/chị ngay sau nha! ✨',
      'Xin lỗi anh/chị, em đang kiểm tra lại dữ liệu một chút. Anh/chị thông cảm đợi em vài phút nhé! 🙏',
      'Dạ trợ lý AI đây ạ! Hệ thống đang hơi nghẽn mạng, anh/chị đợi em một lát để em kiểm tra nha. ☕️',
      'Cảm ơn anh/chị đã nhắn tin. Em sẽ phản hồi lại ngay sau khi rảnh tay ạ! 🌿'
    ];
    return fallbacks[Math.floor(Math.random() * fallbacks.length)];
  }

  async generateGroupNurturingPost(groupName, groupPurpose, timeOfDay, groupId = null) {
    const normPurpose = ((groupPurpose || '') + ' ' + (groupName || '')).toLowerCase();
    const isHealthGroup = normPurpose.includes('nhàu') || normPurpose.includes('tâm an') || normPurpose.includes('sức khoẻ') || normPurpose.includes('sức khóa') || normPurpose.includes('thảo mộc') || normPurpose.includes('mộc');

    if (isHealthGroup) {
      const staticScenario = getNhauScenario(timeOfDay);
      if (staticScenario) {
        logger.info(`🌿 Skill 05: Using static Nhàu Tâm An scenario for ${timeOfDay} to group "${groupName}"`);
        return {
          post: staticScenario.post,
          quote: staticScenario.quote
        };
      }
    }

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

    // Danh sách chủ đề xoay vòng cho Trợ lý anh Cường (Trading, Mindset, Doanh nghiệp 1 người)
    const topicCategories = [
      'Kỷ luật Trading & Quản lý cảm xúc',
      'Quản lý vốn & Tỷ lệ R:R trong giao dịch',
      'Hệ thống SMC-4EMA (SMC kết hợp EMA)',
      'Phân tích kỹ thuật VSA (Volume Spread Analysis)',
      'Ứng dụng AI & Tự động hóa doanh nghiệp một người',
      'Quản lý thời gian & Năng suất tối đa',
      'Tư duy đầu tư dài hạn & Bảo vệ vốn',
      'Mẹo sử dụng Trading Bot tín hiệu hiệu quả',
      'Thiết lập mục tiêu và Kế hoạch tuần',
      'Học hỏi từ các lệnh thua (Thấu hiểu thị trường)',
      'Tầm quan trọng của Trading Journal (Nhật ký giao dịch)',
      'Cân bằng cuộc sống & Tâm lý giao dịch an lành',
    ];
    const dayIndex = new Date().getDate();
    const timeIndex = timeOfDay.includes('sáng') ? 0 : timeOfDay.includes('trưa') ? 1 : 2;
    const topicIdx = (dayIndex * 3 + timeIndex) % topicCategories.length;
    const suggestedTopic = topicCategories[topicIdx];

    const dynamicConfig = await this.getDynamicConfig();
    let basePrompt = dynamicConfig.nurturingPrompt || localConfig.nurturingPrompt || `Bạn là Trợ Lý AI của anh Cường. Bạn cần chuẩn bị nội dung chăm sóc cho nhóm Zalo do anh Cường quản lý.
Hãy trả về kết quả duy nhất dưới định dạng JSON với cấu trúc sau (không thêm bất kỳ từ giải thích nào ngoài JSON):
{
  "post": "nội dung bài đăng đầy đủ",
  "quote": "câu trích dẫn ngắn gọn"
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
        if (parsed.post && parsed.quote) {
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
        quote: quote.length > 50 ? quote.substring(0, 47) + '...' : quote
      };

    } catch (error) {
      logger.error('Failed to generate group nurturing post via AI, using fallback', { groupName, error: error.message });
      if (timeOfDay.includes('sáng') || timeOfDay.includes('8')) {
        const fallbacks = [
          { post: `☀️ Chúc cả nhà ngày mới tràn đầy năng lượng và làm việc, giao dịch hiệu quả nhé ạ! Hy vọng hôm nay mọi người sẽ có nhiều kết quả tốt đẹp và luôn giữ vững kỷ luật. Cả nhà mình đã lên kế hoạch cho ngày hôm nay chưa ạ?`, quote: `Giữ vững kỷ luật, ngày mới thành công!` },
          { post: `🌸 Chào buổi sáng cả nhà! Một ngày mới lại bắt đầu, Cường mong rằng mỗi anh/chị đều mang trong mình một ý chí mạnh mẽ để hoàn thành mọi mục tiêu đã đề ra. Cùng chia sẻ năng lượng tích cực vào nhóm nhé! ✨`, quote: `Bắt đầu ngày mới với niềm tin và năng lượng!` },
          { post: `🌿 Sáng nay thức dậy, điều đầu tiên các anh/chị nghĩ đến là gì? Cường chúc cả nhà một buổi sáng thật trong lành, công việc hanh thông và có những quyết định sáng suốt nhé! ☀️`, quote: `Ngày mới hanh thông, công việc thuận lợi!` },
          { post: `☕️ Một ly cà phê sáng và một mục tiêu rõ ràng sẽ giúp ngày mới hiệu quả hơn bao giờ hết. Cường chúc các anh/chị một ngày làm việc năng suất và tràn đầy niềm vui! 🌸`, quote: `Hành động kiên định, kết quả xứng đáng!` },
          { post: `✨ Khởi đầu ngày mới với nụ cười và sự quyết tâm nhé các anh/chị ơi! Đừng quên ghi xuống 3 việc quan trọng nhất cần làm hôm nay để luôn đi đúng hướng ạ. Chúc cả nhà ngày mới tuyệt vời! 🎯`, quote: `Tập trung mục tiêu, chinh phục thành công!` }
        ];
        return fallbacks[new Date().getDate() % fallbacks.length];
      } else if (timeOfDay.includes('trưa') || timeOfDay.includes('12')) {
        const fallbacks = [
          { post: `☕️ Chúc cả nhà buổi trưa thong dong và vui vẻ nhé ạ! Mọi người nửa ngày qua công việc hay giao dịch thế nào rồi, cùng chia sẻ chút niềm vui vào nhóm nhé!`, quote: `Nghỉ ngơi nhẹ nhàng, hồi phục năng lượng.` },
          { post: `🌸 Buổi trưa là khoảng thời gian tuyệt vời để F5 lại tinh thần. Cường chúc các anh/chị có một bữa trưa ngon miệng và nghỉ ngơi thật thoải mái nhé! ✨`, quote: `Nạp lại năng lượng, sẵn sàng bứt phá.` },
          { post: `🌿 Đã quá nửa ngày rồi, các anh/chị hãy tạm gác lại công việc, hít thở sâu và thư giãn nhé. Một chút nghỉ ngơi sẽ giúp buổi chiều làm việc hiệu quả hơn rất nhiều ạ! ☀️`, quote: `Thư giãn tinh thần, hiệu quả công việc cao.` },
          { post: `🥗 Cả nhà đã dùng bữa trưa chưa ạ? Một bữa ăn ngon và 15 phút chợp mắt sẽ giúp buổi chiều chúng ta bùng nổ năng lượng đó ạ. Chúc anh/chị buổi trưa an lành!`, quote: `Sức khỏe là vàng, nghỉ ngơi hợp lý.` },
          { post: `✨ Giờ nghỉ trưa đến rồi! Cường chúc mọi người có những phút giây thư giãn thật thoải mái để xốc lại tinh thần cho phiên làm việc buổi chiều nhé. 🌟`, quote: `Tái tạo năng lượng, sẵn sàng chiến đấu!` }
        ];
        return fallbacks[new Date().getDate() % fallbacks.length];
      } else {
        const fallbacks = [
          { post: `🌙 Cuối ngày rồi, cả nhà mình hôm nay thế nào ạ? Đừng quên dành thời gian review lại công việc/lệnh giao dịch và nghỉ ngơi thật tốt nhé. Mọi người hôm nay có điều gì tâm đắc nhất muốn chia sẻ không ạ?`, quote: `Review lại ngày cũ, sẵn sàng cho ngày mới.` },
          { post: `✨ Một ngày nữa lại khép lại. Cường hy vọng các anh/chị đã có một ngày thật ý nghĩa. Hãy thư giãn và tận hưởng buổi tối bình yên bên gia đình nhé! 🌸`, quote: `Tận hưởng bình yên, nạp lại năng lượng.` },
          { post: `🌿 Cảm ơn các anh/chị vì những nỗ lực trong suốt ngày hôm nay. Hãy để mọi muộn phiền lại phía sau và có một giấc ngủ thật ngon nhé. Chúc cả nhà ngủ ngon! 🌙`, quote: `Ngủ ngon và mơ đẹp, chào đón ngày mai.` },
          { post: `🌟 Đêm muộn rồi, Cường chúc cả nhà nghỉ ngơi dưỡng sức thật tốt. Những vất vả hôm nay chắc chắn sẽ là hạt mầm cho thành công ngày mai!`, quote: `Khép lại ngày dài, chào đón tương lai.` },
          { post: `💫 Trước khi đi ngủ, hãy tự thưởng cho mình một nụ cười vì đã hoàn thành xuất sắc ngày hôm nay nhé các anh/chị. Cường chúc cả nhà một đêm an giấc!`, quote: `Nụ cười hôm nay, năng lượng ngày mai.` }
        ];
        return fallbacks[new Date().getDate() % fallbacks.length];
      }
    }
  }

  clearHistory(userId) {
    dataStore.clearConversation(userId);
  }
}

export default new AIEngine();
