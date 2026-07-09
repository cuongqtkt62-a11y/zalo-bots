// ============================================================
// order-monitor.js — Google Sheets Order Monitoring System
// ============================================================
// Module này tự động theo dõi các đơn hàng mới phát sinh từ
// file Google Sheets và gửi thông báo trực tiếp cho Admin qua Zalo.
// ============================================================

import fs from 'fs';
import path from 'path';
import axios from 'axios';
import cron from 'node-cron';
import config from './config.js';
import logger from './logger.js';

const STATE_FILE = path.join(process.cwd(), 'data', 'order_monitor_state.json');
const SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/1RWhk7C7DvhchIOs6pAJwbr-AmPir_duQ01m9fQuLcgs/export?format=csv';

/**
 * Trình phân tích cú pháp CSV tự viết (tránh cài thêm thư viện phụ thuộc)
 * Hỗ trợ các trường chứa dấu phẩy bên trong dấu nháy kép.
 */
function parseCsv(csvText) {
  const lines = [];
  let row = [""];
  let inQuotes = false;
  
  for (let i = 0; i < csvText.length; i++) {
    const char = csvText[i];
    const nextChar = csvText[i + 1];
    
    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        row[row.length - 1] += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      row.push('');
    } else if ((char === '\r' || char === '\n') && !inQuotes) {
      if (char === '\r' && nextChar === '\n') {
        i++;
      }
      lines.push(row);
      row = [''];
    } else {
      row[row.length - 1] += char;
    }
  }
  if (row.length > 1 || row[0] !== '') {
    lines.push(row);
  }
  return lines;
}

/**
 * Phân tích định dạng ngày từ Google Sheets "DD/MM/YYYY HH:mm:ss" sang Date
 */
function parseDate(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return new Date(0);
  const parts = dateStr.trim().split(/\s+/);
  if (parts.length < 2) return new Date(0);
  
  const dateParts = parts[0].split('/');
  const timeParts = parts[1].split(':');
  if (dateParts.length < 3 || timeParts.length < 2) return new Date(0);
  
  const day = parseInt(dateParts[0], 10);
  const month = parseInt(dateParts[1], 10) - 1; // 0-indexed
  const year = parseInt(dateParts[2], 10);
  
  const hour = parseInt(timeParts[0], 10);
  const minute = parseInt(timeParts[1], 10);
  const second = timeParts[2] ? parseInt(timeParts[2], 10) : 0;
  
  return new Date(year, month, day, hour, minute, second);
}

/**
 * Lưu trạng thái giám sát
 */
function saveState(state) {
  try {
    const dir = path.dirname(STATE_FILE);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
    logger.debug('💾 Order monitor state saved successfully');
  } catch (error) {
    logger.error('❌ Failed to save order monitor state', error);
  }
}

/**
 * Tải trạng thái giám sát
 */
function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const raw = fs.readFileSync(STATE_FILE, 'utf-8');
      return JSON.parse(raw);
    }
  } catch (error) {
    logger.warn('⚠️ Failed to load order monitor state, using default', error);
  }
  return { lastProcessedTimestamp: null };
}

/**
 * Kiểm tra các đơn hàng mới phát sinh
 */
async function checkForNewOrders(api, isStartupInit = false) {
  try {
    logger.debug('🔄 Checking Google Sheets for new orders...');
    const response = await axios.get(SHEET_CSV_URL, { timeout: 15000 });
    if (response.status !== 200) {
      logger.warn(`⚠️ Failed to fetch sheet CSV, status code: ${response.status}`);
      return;
    }

    const csvText = response.data;
    const rows = parseCsv(csvText);
    
    // Skip header row
    if (rows.length <= 1) return;
    const orderRows = rows.slice(1).filter(r => r.length > 2 && r[0] && r[0].trim());

    const state = loadState();
    
    // Khởi tạo trạng thái (hoặc update đồng bộ lần đầu) để tránh spam đơn cũ do file state bị stale trên cloud
    if (!state.lastProcessedTimestamp || isStartupInit) {
      let maxTime = new Date(0);
      let latestTimestampStr = null;
      
      for (const row of orderRows) {
        const time = parseDate(row[0]);
        if (time > maxTime) {
          maxTime = time;
          latestTimestampStr = row[0];
        }
      }
      
      if (latestTimestampStr) {
        const latestTime = parseDate(latestTimestampStr);
        const stateTime = state.lastProcessedTimestamp ? parseDate(state.lastProcessedTimestamp) : new Date(0);
        
        // Nếu sheet có đơn mới hơn state cũ (do HF reset data), thì update state bằng thời gian mới nhất
        if (latestTime > stateTime || !state.lastProcessedTimestamp) {
          state.lastProcessedTimestamp = latestTimestampStr;
          saveState(state);
          logger.info(`✨ Order monitor initialized (Silent). Marked existing orders as processed up to: ${latestTimestampStr}`);
        } else {
          logger.info(`✨ Order monitor silent init: State is already up to date (${state.lastProcessedTimestamp}).`);
        }
      }
      return;
    }

    // Lọc ra các đơn hàng mới (có timestamp lớn hơn lastProcessedTimestamp)
    const lastTime = parseDate(state.lastProcessedTimestamp);
    const newOrders = [];

    for (const row of orderRows) {
      const time = parseDate(row[0]);
      if (time > lastTime) {
        newOrders.push({
          timestampStr: row[0],
          time,
          name: row[1] || 'Không rõ',
          phone: row[2] || 'Không rõ',
          quantity: row[5] || 'Không rõ',
          address: row[6] || 'Không rõ',
          referrer: row[4] || 'Không có',
          notes: row[9] || 'Không có'
        });
      }
    }

    if (newOrders.length === 0) {
      logger.debug('No new orders found.');
      return;
    }

    // Sắp xếp các đơn hàng mới theo thứ tự thời gian tăng dần để gửi tin nhắn đúng trình tự
    newOrders.sort((a, b) => a.time - b.time);

    logger.info(`🔔 Found ${newOrders.length} new orders! Sending notifications...`);
    const adminIds = (config.zalo.adminId || '').split(',').map(id => id.trim()).filter(Boolean);

    if (adminIds.length === 0) {
      logger.warn('⚠️ No ADMIN_ZALO_ID configured. Cannot send order notifications.');
      return;
    }

    for (const order of newOrders) {
      const msg = 
        `🔔 BÁO CÁO ĐƠN HÀNG PHÁT SINH 🔔\n\n` +
        `Tên khách hàng: ${order.name}\n` +
        `Số điện thoại: ${order.phone}\n` +
        `Địa chỉ giao hàng: ${order.address}\n` +
        `Số lượng: ${order.quantity}`;

      for (const adminId of adminIds) {
        try {
          await api.sendMessage(msg, adminId);
          logger.info(`✉️ Sent order notification of "${order.name}" to admin ${adminId}`);
          // Tránh gửi quá dồn dập
          await new Promise(r => setTimeout(r, 1000));
        } catch (sendErr) {
          logger.error(`❌ Failed to send order notification to admin ${adminId}`, sendErr);
        }
      }
      
      // Cập nhật trạng thái từng đơn hàng đã gửi thành công
      state.lastProcessedTimestamp = order.timestampStr;
      saveState(state);
    }

  } catch (error) {
    logger.error('❌ Error in checkForNewOrders', { error: error.message });
  }
}

/**
 * Bắt đầu giám sát đơn hàng
 */
export function startOrderMonitor(api) {
  logger.info('🛠️ Starting Google Sheets Order Monitor...');
  
  const STARTUP_TIME = Date.now();
  let isChecking = false;
  let startupInitialized = false;

  async function safeCheck() {
    // Bỏ qua kiểm tra thực tế trong 90 giây đầu, NHƯNG phải chạy chế độ silent init 1 lần để sync thời gian
    if (Date.now() - STARTUP_TIME < 90000) {
      if (!startupInitialized) {
        startupInitialized = true;
        logger.info('⏰ Order monitor: Running silent initialization to prevent old order spam...');
        try {
          await checkForNewOrders(api, true); // true = isStartupInit
        } catch (err) {
          logger.error('Error in order monitor silent init', { error: err.message });
        }
      } else {
        logger.info('⏰ Order monitor: Skipping check during startup grace period (90s).');
      }
      return;
    }
    // Khóa chống chạy đè
    if (isChecking) {
      logger.info('⏰ Order monitor: Already checking, skipping duplicate trigger.');
      return;
    }
    isChecking = true;
    try {
      await checkForNewOrders(api);
    } catch (err) {
      logger.error('Error in order monitor check', { error: err.message });
    } finally {
      isChecking = false;
    }
  }

  // Khởi chạy kiểm tra ngay lần đầu (sẽ bị bảo vệ bởi grace period)
  safeCheck();

  // Chạy định kỳ mỗi 5 phút: '*/5 * * * *'
  cron.schedule('*/5 * * * *', safeCheck);
}
