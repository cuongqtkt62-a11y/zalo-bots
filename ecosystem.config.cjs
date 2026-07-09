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

// Bỏ chặn Render vì chúng ta đã chính thức di dời sang Render 24/7
module.exports = {
  apps: zaloBots
};
