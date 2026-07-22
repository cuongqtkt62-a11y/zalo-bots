const zaloBots = [
  {
    name: "zalo-assistant-bich",
    script: "src/index.js",
    cwd: "./bich-bot",
    interpreter: "node",
    instances: 1,
    exec_mode: "fork",
    autorestart: true,
    cron_restart: "15 * * * *",
    watch: false,
    max_memory_restart: "1G",
    env: {
      NODE_ENV: "production",
      NODE_OPTIONS: "--dns-result-order=ipv4first",
      ZALO_CREDENTIALS_PATH: "./zalo-credentials.json",
      ZALO_ACCOUNT_NAME: "Cô Lưu Bích",
      AI_PROVIDER: "gemini"
    }
  },
  {
    name: "zalo-assistant-cuong",
    script: "src/index.js",
    cwd: "./cuong-bot",
    interpreter: "node",
    instances: 1,
    exec_mode: "fork",
    autorestart: true,
    cron_restart: "15 * * * *",
    watch: false,
    max_memory_restart: "1G",
    env: {
      NODE_ENV: "production",
      NODE_OPTIONS: "--dns-result-order=ipv4first",
      ZALO_CREDENTIALS_PATH: "./zalo-credentials-cuong.json",
      ZALO_ACCOUNT_NAME: "Trợ Lý Cường",
      AI_PROVIDER: "gemini"
    }
  },
  {
    name: "health-server",
    script: "server.js",
    cwd: "./",
    interpreter: "node",
    instances: 1,
    exec_mode: "fork",
    autorestart: true,
    watch: false,
    max_memory_restart: "200M"
  }
];

// NẾU CHẠY TRÊN RENDER (BỊ NHẦM DOCKER), CHỈ CHẠY HEALTH SERVER ĐỂ KHÔNG ĐỤNG ĐỘ VỚI HUGGING FACE
const isRender = !!process.env.RENDER;
const activeApps = isRender ? [zaloBots[2]] : zaloBots;

module.exports = {
  apps: activeApps
};
