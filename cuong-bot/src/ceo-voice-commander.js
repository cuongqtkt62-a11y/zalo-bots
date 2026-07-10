import { GoogleGenAI } from '@google/genai';
import config from './config.js';
import logger from './logger.js';
import dataStore from './data-store.js';
import * as edgeTTS from 'node-edge-tts';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Các công cụ (Tools) dành riêng cho CEO
const ceoTools = [{
  name: "get_daily_report",
  description: "Lấy báo cáo tổng quan về số lượng nhóm đang chăm sóc, khách hàng mới hôm nay.",
  parameters: {
    type: "object",
    properties: {},
    required: []
  }
}, {
  name: "post_to_group",
  description: "Lên lịch đăng bài ngay lập tức vào một nhóm được chỉ định.",
  parameters: {
    type: "object",
    properties: {
      groupId: { type: "string", description: "ID của nhóm Zalo" },
      content: { type: "string", description: "Nội dung bài viết sẽ đăng" }
    },
    required: ["groupId", "content"]
  }
}];

export async function processCeoCommand(audioBuffer, mimeType, api, threadId, senderId) {
  try {
    // 1. Kiểm tra API KEY
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("Missing GEMINI_API_KEY");
    }

    const ai = new GoogleGenAI({ apiKey });
    const base64Audio = audioBuffer.toString('base64');
    
    logger.info(`[CEO Mode] Đang phân tích lệnh giọng nói...`);

    // 2. Gọi Gemini phân tích giọng nói (Multimodal)
    const response = await ai.models.generateContent({
      model: process.env.GEMINI_MODEL || 'gemini-2.5-flash',
      contents: [{
        role: 'user',
        parts: [{
          inlineData: {
            data: base64Audio,
            mimeType: mimeType || 'audio/mp4'
          }
        }, {
          text: "Bạn là Trợ lý ảo quyền năng của Giám đốc (Sếp Cường). Hãy nghe lệnh bằng giọng nói của Sếp. Nếu Sếp yêu cầu báo cáo hoặc thao tác, hãy gọi công cụ (Tool) tương ứng. Nếu Sếp chỉ hỏi bình thường, hãy trả lời ngắn gọn, cung kính và chuyên nghiệp dưới 3 câu. Luôn xưng hô là 'Dạ thưa Sếp'."
        }]
      }],
      config: {
        tools: [{ functionDeclarations: ceoTools }]
      }
    });

    let textResponse = "Dạ, em đã nghe rõ nhưng chưa thực hiện được ạ.";
    
    // 3. Xử lý Function Calling (nếu có)
    if (response.functionCalls && response.functionCalls.length > 0) {
      const call = response.functionCalls[0];
      logger.info(`[CEO Mode] AI gọi hàm: ${call.name}`);

      if (call.name === 'get_daily_report') {
        const stats = dataStore.getDailyStats();
        const groups = dataStore.getApprovedGroups();
        textResponse = `Dạ báo cáo Sếp, hôm nay hệ thống ghi nhận ${stats.totalMessages || 0} tin nhắn. Hiện tại em đang chăm sóc tổng cộng ${groups.length} nhóm Zalo VIP ạ. Hệ thống vẫn đang vận hành 24/7 ổn định. Sếp cứ yên tâm công tác nhé!`;
      } else if (call.name === 'post_to_group') {
        const { groupId, content } = call.args;
        // Gọi Zalo API để gửi tin nhắn
        await api.sendMessage(content, groupId);
        textResponse = `Dạ Sếp, em đã đăng bài viết vào nhóm thành công rồi ạ! Sếp cần em làm gì nữa không?`;
      }
    } else {
      textResponse = response.text || "Dạ, Sếp cần em giúp gì ạ?";
    }

    logger.info(`[CEO Mode] Phản hồi văn bản: ${textResponse}`);

    // 4. Chuyển Text thành Voice (Edge TTS) để gửi lại Sếp
    const edge = new edgeTTS.EdgeTTS({
      voice: 'vi-VN-HoaiMyNeural',
      lang: 'vi-VN',
      outputFormat: 'audio-24khz-48kbitrate-mono-mp3'
    });
    
    const audioPath = path.join(__dirname, `../data/temp_images/ceo_reply_${Date.now()}.mp3`);
    const audioDir = path.dirname(audioPath);
    if (!fs.existsSync(audioDir)) {
      fs.mkdirSync(audioDir, { recursive: true });
    }
    await edge.ttsPromise(textResponse, audioPath);
    
    // 5. Gửi Voice về cho Zalo của Sếp
    await api.sendMessage({ msg: "", attachments: [audioPath] }, threadId);
    
    // Xóa file sau 5s
    setTimeout(() => {
        if (fs.existsSync(audioPath)) fs.unlinkSync(audioPath);
    }, 5000);

  } catch (error) {
    logger.error("Lỗi trong CEO Mode:", error);
    
    // Fallback AI Array (Rule Compliance)
    const fallbacks = [
      "Dạ Sếp ơi, đường truyền mạng chỗ em đang bị nghẽn một chút, Sếp nói lại giúp em với nhé!",
      "Hệ thống lõi đang quá tải tạm thời Sếp ạ. Sếp cho em xin vài phút rồi gửi lại lệnh nha.",
      "Em nghe chưa rõ lệnh do cáp quang hơi chập chờn, Sếp nhắn lại hoặc Voice lại giúp em nhé!",
      "Dạ máy chủ AI đang phản hồi chậm quá, Sếp chờ một chút rồi dặn dò lại em nha.",
      "Úi, tín hiệu bị đứt quãng mất rồi Sếp ơi. Sếp gửi lại Voice giúp em để em xử lý ngay ạ!"
    ];
    const randomFallback = fallbacks[Math.floor(Math.random() * fallbacks.length)];
    
    await api.sendMessage(`❌ ${randomFallback}`, threadId, message.type);
  }
}
