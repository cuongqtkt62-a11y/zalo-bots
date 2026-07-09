// ============================================================
// config.js — Centralized Configuration
// ============================================================

import 'dotenv/config';

const config = {
  // Server
  nodeEnv: process.env.NODE_ENV || 'development',

  // Zalo (zca-js) — Không cần App ID / Secret Key
  // Đăng nhập bằng QR Code, credentials lưu vào file
  zalo: {
    credentialsPath: process.env.ZALO_CREDENTIALS_PATH || './zalo-credentials.json',
    // Tên tài khoản (để hiển thị log)
    accountName: process.env.ZALO_ACCOUNT_NAME || 'Trợ Lý AI',
    // Bỏ qua process.env.ADMIN_ZALO_ID bị sai trên HF, fix cứng luôn ID của anh Cường
    adminId: '690136550523054881,6114894381239760462',
    // Số điện thoại trợ lý anh Cường
    assistantPhone: process.env.ASSISTANT_PHONE || '',
  },

  // AI Engine
  ai: {
    provider: process.env.AI_PROVIDER || 'gemini',
    geminiApiKey: process.env.GEMINI_API_KEY,
    geminiModel: process.env.GEMINI_MODEL || 'gemini-2.5-flash',
    openaiApiKey: process.env.OPENAI_API_KEY,
    openaiBaseUrl: process.env.OPENAI_BASE_URL || 'https://api.groq.com/openai/v1',
    openaiModel: process.env.OPENAI_MODEL || 'llama-3.3-70b-versatile',
    maxConversationHistory: 10,
  },

  // Database (optional — có thể chạy không cần DB với SQLite-like JSON file)
  db: {
    enabled: process.env.DB_ENABLED === 'true',
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    name: process.env.DB_NAME || 'zalo_assistant',
    user: process.env.DB_USER || 'zalo_admin',
    password: process.env.DB_PASSWORD || 'changeme',
  },

  // n8n (optional)
  n8n: {
    enabled: process.env.N8N_ENABLED === 'true',
    webhookUrl: process.env.N8N_WEBHOOK_URL || 'http://localhost:5678/webhook',
  },

  // Rate limiting — tránh bị Zalo phát hiện bot
  rateLimit: {
    minDelay: parseInt(process.env.MIN_REPLY_DELAY || '1000', 10),   // ms tối thiểu trước khi reply
    maxDelay: parseInt(process.env.MAX_REPLY_DELAY || '3000', 10),   // ms tối đa
    maxMessagesPerMinute: parseInt(process.env.MAX_MSG_PER_MIN || '10', 10),
  },

  // Telegram Notification (Skill 09)
  telegram: {
    botToken: process.env.TELEGRAM_BOT_TOKEN,
    chatId: process.env.TELEGRAM_CHAT_ID,
  },

  // Video Creator (OPC)
  videoCreator: {
    pexelsApiKey: process.env.PEXELS_API_KEY,
    fptApiKey: process.env.FPT_AI_KEY,
  },
};

// Validate AI key
if (!config.ai.geminiApiKey && !config.ai.openaiApiKey) {
  console.warn('⚠️  Chưa cấu hình API key cho AI (GEMINI_API_KEY hoặc OPENAI_API_KEY)');
  console.warn('   Chatbot sẽ chỉ phản hồi bằng các câu trả lời mẫu (fallback).');
}

export default config;
