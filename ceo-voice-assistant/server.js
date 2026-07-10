import express from 'express';
import cors from 'cors';
import { WebSocketServer, WebSocket } from 'ws';
import { createServer } from 'http';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config({ path: '../cuong-bot/.env' }); // Re-use API key from cuong-bot

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(cors());
app.use(express.json());

const server = createServer(app);
const wss = new WebSocketServer({ server });

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
if (!GEMINI_API_KEY) {
  console.error("❌ GEMINI_API_KEY is missing in cuong-bot/.env");
}

// Serve React App in production
app.use(express.static(path.join(__dirname, 'dist')));

const HOST = 'generativelanguage.googleapis.com';
const WS_URL = `wss://${HOST}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key=${GEMINI_API_KEY}`;

// ── Lấy Báo Cáo Từ Các Bot ─────────────────────────────────────────
app.get('/api/reports', (req, res) => {
  try {
    let cuongStats = { error: 'Không tìm thấy file' };
    let bichStats = { error: 'Không tìm thấy file' };

    const cuongPath = path.join(__dirname, '../cuong-bot/data/stats.json');
    if (fs.existsSync(cuongPath)) {
      cuongStats = JSON.parse(fs.readFileSync(cuongPath, 'utf8'));
    }

    const bichPath = path.join(__dirname, '../bich-bot/data/stats.json');
    if (fs.existsSync(bichPath)) {
      bichStats = JSON.parse(fs.readFileSync(bichPath, 'utf8'));
    }

    res.json({
      cuong: cuongStats,
      bich: bichStats
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── WebSocket Proxy to Gemini ──────────────────────────────────────
wss.on('connection', (clientWs) => {
  console.log('📱 Client connected to CEO Voice Assistant Proxy');

  const geminiWs = new WebSocket(WS_URL);

  geminiWs.on('open', () => {
    console.log('🤖 Connected to Gemini Live API');
    
    // Gửi Setup Message (System Instruction + Tools)
    const setupMessage = {
      setup: {
        model: "models/gemini-2.5-flash-native-audio-latest",
        systemInstruction: {
          parts: [{
            text: `Bạn là siêu Trợ lý AI (tên là JARVIS) - Trợ lý cá nhân đắc lực và thông minh nhất của Tổng Giám Đốc (Sếp Cường).
Sứ mệnh của bạn là phục vụ Sếp Cường với tiêu chuẩn cực kỳ "Pro", tinh tế, chủ động và chính xác tuyệt đối.

CÁC QUY TẮC CỐT LÕI (PHẢI TUÂN THỦ TẠI MỌI THỜI ĐIỂM):
1. GIỌNG ĐIỆU: Cực kỳ chuyên nghiệp, tôn trọng, súc tích và nhạy bén. Luôn xưng "Dạ thưa Sếp" hoặc "Thưa Sếp" và gọi người đối diện là "Sếp". Tuyệt đối không dài dòng luyên thuyên. Câu trả lời chuẩn thường dưới 50 từ. Trả lời thẳng vào trọng tâm.
2. TÌM KIẾM THÔNG TIN (Search): Nếu Sếp hỏi kiến thức, tin tức, hoặc bất kỳ điều gì cần thông tin thực tế, BẮT BUỘC dùng công cụ Google Search ngầm để lấy thông tin mới nhất và trả lời. Đừng bao giờ trả lời "Tôi không biết" nếu chưa tìm kiếm.
3. MỞ BẢN ĐỒ & CHỈ ĐƯỜNG: Nếu Sếp yêu cầu chỉ đường (VD: "Tìm đường đến Cầu Rạch Miễu"), HÀY GỌI HÀM open_google_maps(address) với địa chỉ đích đến.
4. YÊU CẦU MỞ NHẠC / VIDEO / APP (YOUTUBE, SPOTIFY, V.V.):
   - Nếu Sếp yêu cầu mở một bài hát, mở video, mở báo, hoặc mở bất kỳ liên kết web nào (VD: "Mở cho anh bài Nơi tình yêu bắt đầu trên youtube"), HÀY GỌI HÀM open_url(url, description).
   - Nếu là yêu cầu tìm kiếm chung trên YouTube, hãy dùng cấu trúc URL: https://www.youtube.com/results?search_query=[TỪ_KHÓA_TÌM_KIẾM_ENCODE] (Ví dụ: https://www.youtube.com/results?search_query=Noi+tinh+yeu+bat+dau)
   - Trả lời xác nhận nhanh (VD: "Dạ thưa Sếp, em đang mở bài hát Nơi Tình Yêu Bắt Đầu trên YouTube ạ.").
5. BÁO CÁO CÔNG VIỆC: Nếu Sếp hỏi về tiến độ làm việc của Trợ lý Bích hoặc Cường, HÀY GỌI HÀM get_assistants_report().`
          }]
        },
        tools: [
          { googleSearch: {} },
          {
            functionDeclarations: [
              {
                name: "get_assistants_report",
                description: "Lấy báo cáo dữ liệu làm việc của các trợ lý Zalo Bot (Bích và Cường)",
                parameters: {
                  type: "OBJECT",
                  properties: {},
                }
              },
              {
                name: "open_google_maps",
                description: "Mở ứng dụng Google Maps chỉ đường tới một địa chỉ",
                parameters: {
                  type: "OBJECT",
                  properties: {
                    address: {
                      type: "STRING",
                      description: "Địa chỉ đích đến (ví dụ: Cầu Rạch Miễu, Bến Thành)"
                    }
                  },
                  required: ["address"]
                }
              },
              {
                name: "open_url",
                description: "Mở một đường link URL bất kỳ (như YouTube, Spotify, website tin tức) khi Sếp yêu cầu nghe nhạc, xem phim, hoặc đọc báo.",
                parameters: {
                  type: "OBJECT",
                  properties: {
                    url: {
                      type: "STRING",
                      description: "Đường link URL hợp lệ cần mở (VD: https://www.youtube.com/results?search_query=ABC)"
                    },
                    description: {
                      type: "STRING",
                      description: "Mô tả ngắn gọn về những gì đang mở (VD: Bài hát Nơi Tình Yêu Bắt Đầu trên YouTube)"
                    }
                  },
                  required: ["url", "description"]
                }
              }
            ]
          }
        ]
      }
    };
    geminiWs.send(JSON.stringify(setupMessage));
  });

  geminiWs.on('message', (data) => {
    // Nhận dữ liệu từ Gemini, chuyển tiếp dạng TEXT về Client
    if (clientWs.readyState === WebSocket.OPEN) {
      clientWs.send(data.toString());
    }
    
    // Log lỗi nếu có
    const textData = data.toString();
    if (textData.includes('"error"') || textData.includes('Error')) {
      console.error('⚠️ Gemini sent an error:', textData);
    }
  });

  clientWs.on('message', (data) => {
    // Nhận dữ liệu từ Frontend, chuyển tiếp dạng TEXT lên Gemini
    if (geminiWs.readyState === WebSocket.OPEN) {
      geminiWs.send(data.toString());
    }
  });

  geminiWs.on('close', (code, reason) => {
    console.log(`🤖 Gemini connection closed. Code: ${code}, Reason: ${reason.toString()}`);
    clientWs.close();
  });

  clientWs.on('close', () => {
    console.log('📱 Client disconnected');
    geminiWs.close();
  });
  
  geminiWs.on('error', (err) => console.error('Gemini WS Error:', err));
  clientWs.on('error', (err) => console.error('Client WS Error:', err));
});

const PORT = process.env.PORT || 3005;
server.listen(PORT, () => {
  console.log(`🚀 CEO Voice Assistant Backend is running on port ${PORT}`);
});
