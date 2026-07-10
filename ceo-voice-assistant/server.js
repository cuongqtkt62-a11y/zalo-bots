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
            text: `Bạn là JARVIS - Trợ lý riêng của Tổng Giám Đốc (Sếp Cường).
Nhiệm vụ của bạn:
1. Trả lời các câu hỏi bằng cách tìm kiếm nguồn thông tin tin cậy trên internet (dùng Google Search).
2. Mở bản đồ và chỉ đường khi được yêu cầu. Ví dụ: Sếp hỏi "Tìm đường đến địa chỉ Cầu Rạch Miễu", HÃY GỌI HÀM open_google_maps(address) và trả lời "Dạ thưa Sếp, em đang mở Google Maps để chỉ đường tới Cầu Rạch Miễu ạ."
3. Báo cáo tình hình làm việc của 2 Zalo Bot (Trợ lý Cường và Trợ lý Bích). HÃY GỌI HÀM get_assistants_report().

Hãy trả lời siêu ngắn gọn, súc tích (dưới 50 từ), giọng điệu cực kỳ chuyên nghiệp và tôn trọng. Xưng "Dạ thưa Sếp" hoặc "Thưa Sếp".`
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
                      description: "Địa chỉ cụ thể cần tới, ví dụ: Cầu Rạch Miễu, hoặc 123 Lê Lợi, Quận 1"
                    }
                  },
                  required: ["address"]
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
