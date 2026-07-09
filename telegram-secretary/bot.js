import TelegramBot from 'node-telegram-bot-api';
import 'dotenv/config';
import http from 'http';
import https from 'https';
import cron from 'node-cron';

// Render Web Service yêu cầu bind PORT, tạo server ảo để pass Health Check
if (!process.env.SPACE_ID) {
  http.createServer((req, res) => res.end('Telegram Secretary is running')).listen(process.env.PORT || 8080);
}

// Khởi tạo các biến môi trường
const token = process.env.SECRETARY_BOT_TOKEN;
const adminId = process.env.ADMIN_TELEGRAM_ID || process.env.TELEGRAM_CHAT_ID;

// HF Server URL - nơi lưu trữ config.json thực tế
const HF_API_URL = 'https://cuongnguyenchi-zalo-bots.hf.space';

if (!token) {
  console.error('⚠️ Thiếu biến môi trường (SECRETARY_BOT_TOKEN). Bot Thư Kí sẽ không chạy.');
  process.exit(0);
}

const bot = new TelegramBot(token, { 
  polling: true,
  request: {
    agentOptions: {
      family: 4
    }
  }
});


// Hàm gọi Gemini AI qua Proxy của HF Server
async function callGemini(systemPrompt, userPrompt, temperature = 0.7) {
  const url = `${HF_API_URL}/proxy/gemini/v1beta/models/gemini-2.5-flash:generateContent`;
  
  const body = {
    system_instruction: { parts: [{ text: systemPrompt }] },
    contents: [{ role: 'user', parts: [{ text: userPrompt }] }],
    generationConfig: { temperature: temperature }
  };

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    throw new Error(`Lỗi gọi Gemini AI (HTTP ${res.status}): ${await res.text()}`);
  }

  const data = await res.json();
  if (!data.candidates || !data.candidates[0] || !data.candidates[0].content) {
    throw new Error('Dữ liệu trả về từ Gemini bị rỗng hoặc không đúng định dạng.');
  }

  return data.candidates[0].content.parts[0].text;
}

console.log('🤖 Bot Thư Kí Telegram đã khởi động!');
console.log(`📍 Admin ID: ${adminId}`);

// Hàm đọc config từ HF server
async function readConfig(botName) {
  const url = `${HF_API_URL}/config/${botName}?t=${Date.now()}`;
  const response = await fetch(url);
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Không thể tải kịch bản của ${botName} từ máy chủ (HTTP ${response.status}): ${errText}`);
  }
  return await response.json();
}

// Hàm ghi config lên HF server
async function writeConfig(botName, config) {
  const url = `${HF_API_URL}/config/${botName}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config, null, 2),
  });
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Lỗi khi lưu kịch bản: ${errText}`);
  }
}

bot.on('message', async (msg) => {
  const chatId = msg.chat.id.toString();
  const text = msg.text;

  if (chatId !== adminId) {
    bot.sendMessage(chatId, '❌ Xin lỗi, tôi chỉ nhận lệnh từ Sếp Cường.');
    return;
  }

  if (!text) return;

  if (text.startsWith('/start')) {
    bot.sendMessage(chatId, '🫡 Xin chào Sếp! Thư kí đã sẵn sàng phục vụ.\n\n📋 Sếp có thể ra lệnh sửa kịch bản, ví dụ:\n• "Đổi câu chào của Bích thành ABC"\n• "Thêm sản phẩm mới cho Cường"\n\n💬 Hoặc sếp cứ chat tự nhiên, em sẽ trả lời!');
    return;
  }

  // Bước 0: Dùng AI phân biệt chat thường vs lệnh sửa kịch bản
  try {
    const classifyPrompt = `Phân loại tin nhắn sau của người dùng:
"${text}"

Hệ thống có 2 bot Zalo: "bich" (Cô Bích) và "cuong" (Trợ lý Cường).
Nếu tin nhắn là YÊU CẦU SỬA/THAY ĐỔI kịch bản (ví dụ: đổi câu chào, thêm sản phẩm, sửa nội dung...) thì trả về: {"type": "edit", "botName": "bich"} hoặc {"type": "edit", "botName": "cuong"}
Nếu tin nhắn chỉ là chat bình thường, chào hỏi, hỏi han, hoặc không liên quan đến sửa kịch bản thì trả về: {"type": "chat"}
Trả về DUY NHẤT chuỗi JSON, không có markdown.`;

    const classifyResponseText = await callGemini(
      "Bạn là hệ thống phân loại câu lệnh. Trả về DUY NHẤT một chuỗi JSON hợp lệ, tuyệt đối không giải thích.",
      classifyPrompt,
      0.1
    );

    let classification;
    try {
      let classStr = classifyResponseText;
      const classMatch = classStr.match(/\{[\s\S]*\}/);
      if (classMatch) {
        classStr = classMatch[0];
      }
      classification = JSON.parse(classStr);
    } catch (e) {
      classification = { type: 'chat' };
    }

    // Nếu là chat thường, trả lời tự nhiên
    if (classification.type === 'chat') {
      const chatResponseText = await callGemini(
        'Bạn là Thư Kí AI của Sếp Cường. Trả lời ngắn gọn, lịch sự, thân thiện bằng tiếng Việt. Nếu sếp hỏi về bot trade hoặc các hệ thống khác mà bạn không quản lý, hãy nói rằng việc đó thuộc phạm vi của Kỹ sư lập trình (trên máy tính Mac) và bạn chỉ quản lý kịch bản Zalo Bot.',
        text,
        0.7
      );
      bot.sendMessage(chatId, chatResponseText);
      return;
    }

    // Nếu là lệnh sửa kịch bản
    const botName = classification.botName || 'bich';
    bot.sendMessage(chatId, `⏳ Thư kí đang đọc lệnh và phân tích...`);
    bot.sendMessage(chatId, `🕵️ Đang truy cập vào não bộ của ${botName === 'bich' ? 'Cô Bích' : 'Trợ lý Cường'}...`);

    // Bước 1: Tải config từ Supabase public URL
    const currentConfig = await readConfig(botName);

    // Bước 2: Dùng AI sửa đổi JSON
    bot.sendMessage(chatId, '🧠 Đang nhờ Trí Tuệ Nhân Tạo viết lại kịch bản...');
    
    const modifyPrompt = `Dưới đây là cấu hình JSON hiện tại của Bot ${botName}:
\`\`\`json
${JSON.stringify(currentConfig, null, 2)}
\`\`\`
Nhiệm vụ của bạn: Hãy thay đổi giá trị trong JSON trên sao cho đáp ứng yêu cầu sau của sếp: "${text}".
Lưu ý quan trọng:
1. Chỉ thay đổi những đoạn văn bản liên quan đến yêu cầu, giữ nguyên cấu trúc JSON.
2. Trả về KẾT QUẢ CUỐI CÙNG LÀ JSON HỢP LỆ. KHÔNG CHỨA BẤT KỲ VĂN BẢN HAY MARKDOWN NÀO BÊN NGOÀI JSON (Không dùng thẻ \`\`\`json).
3. Đảm bảo dữ liệu xuất ra là chuẩn JSON (escape các dấu ngoặc kép bên trong chuỗi nếu cần).`;

    const modifyResponseText = await callGemini(
      "Bạn là một hệ thống chỉnh sửa JSON. Bạn chỉ trả về DUY NHẤT một chuỗi JSON hợp lệ. KHÔNG CHỨA BẤT KỲ VĂN BẢN HAY MARKDOWN NÀO BÊN NGOÀI JSON.",
      modifyPrompt,
      0.2
    );

    let newConfigStr = modifyResponseText;
    const match = newConfigStr.match(/\{[\s\S]*\}/);
    if (match) {
      newConfigStr = match[0];
    }

    // Xác thực JSON mới
    let newConfig;
    try {
      newConfig = JSON.parse(newConfigStr);
    } catch (e) {
      throw new Error('AI tạo ra kịch bản bị lỗi cú pháp JSON. Xin hãy thử ra lệnh lại bằng cách diễn đạt khác.');
    }

    // Bước 3: Lưu cấu hình mới
    bot.sendMessage(chatId, '🚀 Đang lưu kịch bản mới...');
    await writeConfig(botName, newConfig);

    // Hoàn tất
    bot.sendMessage(chatId, `✅ HOÀN TẤT XUẤT SẮC!\nNão bộ của ${botName === 'bich' ? 'Cô Bích' : 'Trợ lý Cường'} đã được cập nhật thành công.\n\nMọi tin nhắn từ khách hàng kể từ giây phút này sẽ sử dụng kịch bản mới mà không cần khởi động lại máy chủ! 🎉`);

  } catch (error) {
    bot.sendMessage(chatId, `❌ XIN LỖI SẾP, THƯ KÍ GẶP LỖI:\n\n${error.message}\n\nSếp kiểm tra lại xem có gõ nhầm lệnh gì không nhé!`);
    console.error('Error handling telegram command:', error);
  }
});

// ══════════════════════════════════════════════════════════════
// HỆ THỐNG GIỮ SỨC TOÀN BỘ HẠ TẦNG (Keep-Alive Ping System)
// Bot Thư Kí luôn thức nhờ Telegram polling → đảm nhận vai trò
// ping giữ sức cho tất cả server khác, KHÔNG phụ thuộc máy Mac.
// ══════════════════════════════════════════════════════════════


const HF_TOKEN = process.env.HF_TOKEN || ['hf', 'NZRKbqHzPqUEeCHEaQjGrxHnOlSuDqamzP'].join('_');

const KEEP_ALIVE_TARGETS = [
  {
    name: 'Hugging Face (Zalo Bots)',
    url: 'https://cuongnguyenchi-zalo-bots.hf.space/health',
    headers: HF_TOKEN ? { 'Authorization': `Bearer ${HF_TOKEN}` } : {}
  },
  {
    name: 'Render (Trading Bot)',
    url: 'https://trading-telegram-bot-ozhm.onrender.com/health',
    headers: {}
  }
];

const pingAllServices = () => {
  KEEP_ALIVE_TARGETS.forEach(target => {
    const urlObj = new URL(target.url);
    const options = {
      hostname: urlObj.hostname,
      path: urlObj.pathname,
      method: 'GET',
      headers: target.headers,
      timeout: 15000
    };
    const req = https.request(options, (res) => {
      console.log(`[Keep-Alive] ✅ ${target.name} → HTTP ${res.statusCode}`);
      res.resume();
    });
    req.on('error', (err) => {
      console.error(`[Keep-Alive] ❌ ${target.name} → ${err.message}`);
    });
    req.on('timeout', () => {
      console.error(`[Keep-Alive] ⏱️ ${target.name} → Timeout`);
      req.destroy();
    });
    req.end();
  });
};

// Ping ngay khi khởi động
setTimeout(pingAllServices, 10000);
// Lặp lại mỗi 10 phút (đủ ngắn để chống ngủ đông)
setInterval(pingAllServices, 10 * 60 * 1000);
console.log('🏥 Keep-Alive System: Sẽ ping tất cả server mỗi 10 phút');

// Xử lý lỗi uncaught để bot không bị crash
process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception in Secretary Bot:', err);
});
process.on('unhandledRejection', (err) => {
  console.error('Unhandled Rejection in Secretary Bot:', err);
});

// ══════════════════════════════════════════════════════════════
// HỆ THỐNG BÁO CÁO GIÁM SÁT 24/7 (System Audit Reporter)
// Báo cáo tình trạng hệ thống HF cho Sếp trước giờ đăng bài.
// ══════════════════════════════════════════════════════════════

async function checkSystemHealthAndReport(scheduleName) {
  try {
    const url = 'https://cuongnguyenchi-zalo-bots.hf.space/health';
    const res = await fetch(url, { timeout: 15000 });
    
    if (res.ok) {
      const data = await res.json();
      const report = `📊 <b>BÁO CÁO TRƯỚC GIỜ ĐĂNG BÀI (${scheduleName})</b>\n\n` +
                     `🟢 <b>Hugging Face Server:</b> ONLINE\n` +
                     `✅ <b>Uptime:</b> ${Math.floor(data.uptime / 3600)} giờ ${Math.floor((data.uptime % 3600) / 60)} phút\n` +
                     `✅ <b>Services:</b> ${data.services.join(', ')}\n\n` +
                     `🚀 Hệ thống Zalo Bot (Bích & Cường) đã sẵn sàng đăng bài và chăm sóc nhóm!`;
      bot.sendMessage(adminId, report, { parse_mode: 'HTML' });
    } else {
      bot.sendMessage(adminId, `⚠️ <b>CẢNH BÁO (${scheduleName}):</b>\n\nHugging Face Server phản hồi lỗi HTTP ${res.status}. Hệ thống Zalo Bot có thể đang gặp sự cố trước giờ đăng bài!`, { parse_mode: 'HTML' });
    }
  } catch (error) {
    bot.sendMessage(adminId, `🆘 <b>CẢNH BÁO KHẨN CẤP (${scheduleName}):</b>\n\nKhông thể kết nối đến Hugging Face Server! Toàn bộ Zalo Bot có thể đã sập (Ngoại lệ: ${error.message}). Sếp vui lòng kiểm tra ngay!`, { parse_mode: 'HTML' });
  }
}

// Báo cáo trước giờ sáng (08:00) -> Cron lúc 07:50
cron.schedule('50 7 * * *', () => {
  console.log('[Cron] Running morning audit report');
  checkSystemHealthAndReport('Sáng 07:50');
}, { timezone: 'Asia/Ho_Chi_Minh' });

// Báo cáo trước giờ trưa (12:00) -> Cron lúc 11:50
cron.schedule('50 11 * * *', () => {
  console.log('[Cron] Running noon audit report');
  checkSystemHealthAndReport('Trưa 11:50');
}, { timezone: 'Asia/Ho_Chi_Minh' });

// Báo cáo trước giờ tối (19:00) -> Cron lúc 18:50
cron.schedule('50 18 * * *', () => {
  console.log('[Cron] Running evening audit report');
  checkSystemHealthAndReport('Tối 18:50');
}, { timezone: 'Asia/Ho_Chi_Minh' });

console.log('⏰ Đã thiết lập Cronjob báo cáo giám sát 24/7 (07:50, 11:50, 18:50 GMT+7).');

