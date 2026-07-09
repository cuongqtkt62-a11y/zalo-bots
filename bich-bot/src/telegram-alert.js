// ============================================================
// alert.js — Gửi thông báo khẩn qua Zalo Admin
// ============================================================
import config from './config.js';
import logger from './logger.js';

export async function sendEscalationAlert(api, { senderName, threadId, message, intent }) {
  const admin1 = config.zalo.adminId.split(',')[0];
  if (!admin1) return false;

  const formattedText = 
    `🚨 <b>ESCALATION ALERT (TRỢ LÝ CÔ BÍCH)</b> 🚨\n\n` +
    `👤 <b>Khách hàng:</b> ${senderName || 'Ẩn danh'}\n` +
    `🆔 <b>Zalo ID:</b> ${threadId}\n` +
    `🎯 <b>Nhận diện:</b> ${intent.toUpperCase()}\n\n` +
    `💬 <b>Tin nhắn:</b>\n"${message}"\n\n` +
    `⚠️ Vui lòng vào app Zalo (TK cô Bích) để hỗ trợ khách hàng ngay nhé anh Cường!`;

  try {
    await api.sendMessage(formattedText, admin1);
    logger.info('📤 Escalation alert sent to Zalo Admin successfully');
    return true;
  } catch (error) {
    logger.error('❌ Failed to send Zalo escalation alert', { error: error.message });
    return false;
  }
}

export async function sendConnectionAlert(api, { botName, errorMsg }) {
  const admin1 = config.zalo.adminId.split(',')[0];
  if (!admin1) return false;

  const formattedText = 
    `⚠️ <b>CẢNH BÁO MẤT KẾT NỐI (TRỢ LÝ ${botName.toUpperCase()})</b> ⚠️\n\n` +
    `🤖 <b>Tên trợ lý:</b> Trợ lý ${botName}\n` +
    `❌ <b>Chi tiết lỗi:</b> ${errorMsg}\n\n` +
    `❗ Phiên đăng nhập Zalo đã bị ngắt kết nối hoặc hết hạn (có thể do đăng nhập đè Zalo Web ở nơi khác hoặc hết hạn cookie).\n` +
    `👉 Vui lòng quét lại mã QR để khôi phục hoạt động cho Trợ lý ${botName}!`;

  try {
    await api.sendMessage(formattedText, admin1);
    logger.info(`📤 Connection alert sent to Zalo Admin successfully for Trợ lý ${botName}`);
    return true;
  } catch (error) {
    logger.error('❌ Failed to send Zalo connection alert', { error: error.message });
    return false;
  }
}

export default { sendEscalationAlert, sendConnectionAlert };
