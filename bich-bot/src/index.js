// ============================================================
// index.js — Zalo AI Assistant (Personal Account)
// ============================================================
// Bot chính — kết nối Zalo cá nhân qua zca-js,
// lắng nghe tin nhắn và phản hồi bằng AI.
//
// Trợ Lý cô Lưu Bích — 9 Skills đầy đủ:
//   Skill 01: New Friend Onboarding
//   Skill 02: Existing Contact Nurturing (Cron 09:00)
//   Skill 03: Follow-up Engine (Cron 08:30)
//   Skill 04: Group Invitation Verification
//   Skill 05: Group Care Manager (Cron 08:00/12:00/19:00)
//   Skill 06: Community Content Creator (Cron 19:00 T3/T5)
//   Skill 07: Lead Classification (Realtime)
//   Skill 08: Daily CEO Briefing (Cron 08:00 + #baocao)
//   Skill 09: Escalation to Human (Realtime)
//
// Cách chạy:
//   1. Lần đầu: node src/login.js (scan QR)
//   2. Sau đó: npm start
// ============================================================

import { Zalo, ThreadType, FriendEventType, GroupEventType } from 'zca-js';
import { readFileSync, existsSync, unlinkSync, statSync, writeFileSync } from 'fs';
import { dirname } from 'path';
import { fileURLToPath } from 'url';
import path from 'path';
import axios from 'axios';
import cron from 'node-cron';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

import config from './config.js';
import logger from './logger.js';
import aiEngine from './ai-engine.js';
import dataStore from './data-store.js';
import { sendEscalationAlert, sendConnectionAlert } from './telegram-alert.js';
import { createCard } from './image-generator.js';
import { getScenarioForToday, getScenarioById, weeklySchedule } from './content-scenarios.js';
import { createYouTubeVideo } from './video-creator.js';

const STARTUP_TIME = Date.now();

// ── Rate Limiter ─────────────────────────────────────────
const userMessageTimestamps = {};
function isRateLimited(userId) {
  const now = Date.now();
  if (!userMessageTimestamps[userId]) {
    userMessageTimestamps[userId] = [];
  }
  const timestamps = userMessageTimestamps[userId];
  
  // Xóa timestamps cũ hơn 1 phút
  while (timestamps.length > 0 && timestamps[0] < now - 60000) {
    timestamps.shift();
  }
  return timestamps.length >= config.rateLimit.maxMessagesPerMinute;
}

function randomDelay() {
  const { minDelay, maxDelay } = config.rateLimit;
  return minDelay + Math.random() * (maxDelay - minDelay);
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Main Bot ─────────────────────────────────────────────

async function startBot() {
  console.log('\n╔══════════════════════════════════════════════════════════╗');
  console.log('║       🤖 ZALO AI ASSISTANT — TRỢ LÝ CÔ LƯU BÍCH       ║');
  console.log('║       9 Skills — Full Automation                         ║');
  console.log('╚══════════════════════════════════════════════════════════╝\n');

  // ── Step 1: Load credentials ───────────────────────────
  const credPath = config.zalo.credentialsPath;

  if (!existsSync(credPath)) {
    console.error('❌ Chưa đăng nhập Zalo!');
    console.error('   Chạy lệnh sau để đăng nhập: npm run login');
    process.exit(1);
  }

  let credentials;
  try {
    credentials = JSON.parse(readFileSync(credPath, 'utf-8'));
    logger.info('📁 Loaded credentials', { loginTime: credentials.loginTime });
  } catch (error) {
    console.error('❌ File credentials bị lỗi. Hãy đăng nhập lại: npm run login');
    process.exit(1);
  }

  // ── Step 2: Connect to Zalo ────────────────────────────
  logger.info('🔌 Connecting to Zalo...');

  const zalo = new Zalo({ selfListen: true });

  let api;
  try {
    api = await zalo.login({
      cookie: credentials.cookies,
      imei: credentials.imei,
      userAgent: credentials.userAgent,
    });
    logger.info('✅ Connected to Zalo successfully!');
  } catch (error) {
    logger.error('❌ Failed to connect to Zalo', { error: error.message });
    console.error('\n❌ Không thể kết nối Zalo. Có thể credentials đã hết hạn.');
    console.error('   Hãy đăng nhập lại: npm run login\n');
    process.exit(1);
  }

  // ── Step 3: Listen for messages ────────────────────────
  logger.info('👂 Listening for messages...');

  api.listener.on('message', async (message) => {
    try {
      // Chỉ xử lý tin nhắn cá nhân và tin nhắn nhóm
      if (message.type !== ThreadType.User && message.type !== ThreadType.Group) {
        return;
      }

      // ── Smart Grace Period ──────────────────────────────
      // Chỉ bỏ qua tin nhắn 15s đầu tiên nếu ổ cứng KHÔNG có file lưu lịch sử.
      // (Xảy ra khi Hugging Face Docker Rebuild bị mất dữ liệu).
      // Nếu là PM2 restart bình thường, dataStore sẽ có Persistent Cache -> Không cần chờ 15s!
      if (!dataStore.hasPersistentCache() && (Date.now() - STARTUP_TIME < 15000)) {
        return;
      }

      // Chống dội tin nhắn (duplicate) lưu trên ổ cứng
      const msgId = message.data?.msgId || message.data?.cliMsgId;
      if (msgId) {
        if (dataStore.isMsgProcessed(msgId)) return;
        dataStore.markMsgProcessed(msgId);
      }

      // Chỉ xử lý tin nhắn text
      const content = message.data.content;
      if (typeof content !== 'string' || !content.trim()) {
        return;
      }

      // Bỏ qua tin nhắn do chính bot gửi (ngoại trừ các lệnh bắt đầu bằng '#')
      if (message.isSelf && !content.trim().startsWith('#')) {
        return;
      }

      const threadId = message.threadId;
      const userMessage = content.trim();

      // Kiểm tra quyền Admin (Chỉ có chính bot gửi hoặc tài khoản Admin chỉ định mới dùng được các lệnh bắt đầu bằng '#')
      const senderId = String(message.data?.senderId || message.data?.uid || message.data?.uidFrom || '');
      const threadIdStr = String(threadId);
      const adminIds = ['690136550523054881', '6114894381239760462'];
      const isAdmin = message.isSelf || 
                      adminIds.includes(threadIdStr) || 
                      adminIds.includes(senderId);

      // ══════════════════════════════════════════════════════
      // SKILL 04 — GROUP INVITATION VERIFICATION (Admin Commands)
      // ══════════════════════════════════════════════════════

      if (userMessage.startsWith('#duyet ')) {
        if (!isAdmin) {
          logger.warn('🚫 Non-admin tried to execute #duyet', { threadId, senderId });
          return;
        }
        const cmdParts = userMessage.substring('#duyet '.length).trim().split(/\s+/);
        const targetGroupId = cmdParts[0];
        const purpose = userMessage.substring('#duyet '.length + targetGroupId.length).trim() || 
                        'Chia sẻ kiến thức về Phát triển bản thân, Nhân hiệu cá nhân và Ứng dụng AI cùng cô Lưu Bích.';
        
        if (targetGroupId) {
          let groupName = 'Group Chat';
          try {
            const groupInfoRes = await api.getGroupInfo(targetGroupId);
            if (groupInfoRes?.gridInfoMap?.[targetGroupId]?.name) {
              groupName = groupInfoRes.gridInfoMap[targetGroupId].name;
            }
          } catch (err) {
            logger.warn('Failed to fetch group info from API in #duyet command', err);
          }

          dataStore.approveGroup(targetGroupId, groupName, purpose);
          const welcomeMsg = `Chào cả nhà,\nBích rất biết ơn cả nhà đã đồng hành cùng Bích ạ !`;
          try {
            await api.sendMessage(welcomeMsg, targetGroupId, ThreadType.Group);
            logger.info('✅ Approved group welcome greeting sent successfully', { targetGroupId });
            dataStore.upsertUser(targetGroupId, groupName);
            dataStore.logMessage(targetGroupId, 'outgoing', welcomeMsg);
            dataStore.addToConversation(targetGroupId, 'assistant', welcomeMsg);
            dataStore.setGreetingStep(targetGroupId, 1);
            
            await api.sendMessage(`✅ Đã duyệt nhóm "${groupName}" thành công!\n🎯 Mục đích hoạt động: "${purpose}"\n🤖 Bot đã bắt đầu Greeting Step 1.`, threadId, message.type);
          } catch (err) {
            logger.error('Failed to send welcome to approved group', err);
            await api.sendMessage(`❌ Duyệt nhóm lưu database thành công nhưng lỗi gửi tin chào mừng: ${err.message}`, threadId, message.type);
          }
          return;
        }
      }

      if (userMessage.startsWith('#mucdich ')) {
        if (!isAdmin) {
          logger.warn('🚫 Non-admin tried to execute #mucdich', { threadId, senderId });
          return;
        }
        const cmdParts = userMessage.substring('#mucdich '.length).trim().split(/\s+/);
        const targetGroupId = cmdParts[0];
        const newPurpose = userMessage.substring('#mucdich '.length + targetGroupId.length).trim();
        
        if (targetGroupId && newPurpose) {
          const group = dataStore.getApprovedGroup(targetGroupId);
          if (!group) {
            await api.sendMessage(`❌ Nhóm này chưa được duyệt hoạt động. Hãy duyệt trước bằng cú pháp: #duyet ${targetGroupId}`, threadId, message.type);
            return;
          }
          
          let groupName = group.name;
          try {
            const groupInfoRes = await api.getGroupInfo(targetGroupId);
            if (groupInfoRes?.gridInfoMap?.[targetGroupId]?.name) {
              groupName = groupInfoRes.gridInfoMap[targetGroupId].name;
            }
          } catch (err) {
            logger.warn('Failed to fetch group info from API', err);
          }
          
          dataStore.approveGroup(targetGroupId, groupName, newPurpose);
          await api.sendMessage(`✅ Đã cập nhật mục đích hoạt động cho nhóm "${groupName}" thành:\n💬 "${newPurpose}"`, threadId, message.type);
        } else {
          await api.sendMessage(`❌ Sai cú pháp! Vui lòng dùng: #mucdich [groupId] [mục đích mới]`, threadId, message.type);
        }
        return;
      }

      // ── Video Creation Command (YouTube Automation) ───────
      if (userMessage.startsWith('#taovideo ')) {
        if (!isAdmin) {
          logger.warn('🚫 Non-admin tried to execute #taovideo', { threadId, senderId });
          await api.sendMessage(`❌ Anh/chị không có quyền sử dụng chức năng tạo video.`, threadId, message.type);
          return;
        }
        
        const videoPrompt = userMessage.substring('#taovideo '.length).trim();
        if (!videoPrompt) {
          await api.sendMessage(`❌ Cú pháp: #taovideo [chủ đề/nội dung]`, threadId, message.type);
          return;
        }

        // Gửi tin nhắn Async
        await api.sendMessage(`🎬 Đang xử lý kịch bản và dựng video cho chủ đề:\n"${videoPrompt}"\n\n⏳ Quá trình này có thể mất vài phút. Trợ lý sẽ gửi link ngay khi xong nhé!`, threadId, message.type);

        // Chạy ngầm Video Creator (OPC)
        createYouTubeVideo(videoPrompt).then(async (result) => {
          if (result.success) {
            const successMsg = 
              `✅ VIDEO CỦA ANH ĐÃ HOÀN TẤT! ✅\n\n` +
              `📑 Bộ thông tin chuẩn SEO YouTube:\n` +
              `• Tiêu đề: ${result.seo.title}\n` +
              `• Mô tả:\n${result.seo.description}\n` +
              `• Tags: ${result.seo.tags.join(', ')}\n\n` +
              `🚀 Đang gửi file video cho anh tải về (chờ 1 xíu Zalo upload nhé)...`;
              
            await api.sendMessage(successMsg, threadId, message.type);

            // Đính kèm File Video để anh tải trực tiếp (OPC Style)
            try {
              const videoBuffer = readFileSync(result.videoPath);
              const stats = statSync(result.videoPath);
              const attachment = {
                data: videoBuffer,
                filename: result.seo.filename || 'video-youtube.mp4',
                metadata: {
                  totalSize: stats.size
                }
              };
              
              // Thêm timeout 5 phút cho việc upload lên Zalo
              const uploadPromise = api.sendMessage({ msg: "", attachments: [result.videoPath] }, threadId, message.type);
              const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('Zalo Upload Timeout - Zalo server không phản hồi')), 300000));
              await Promise.race([uploadPromise, timeoutPromise]);
              
              // Xóa file sau khi gửi thành công
              unlinkSync(result.videoPath);
            } catch (err) {
              logger.error('Lỗi upload file video lên Zalo', err);
              
              // Tạo link tải trực tiếp từ server
              const relativePath = result.videoPath.split('/cloud-deployment/')[1] || result.videoPath.split('/app/')[1] || `bich-bot/scratch/video_temps/${require('path').basename(result.videoPath)}`;
              const downloadLink = `https://cuongnguyenchi-zalo-bots.hf.space/download?file=${relativePath}`;
              
              await api.sendMessage(`⚠️ Zalo từ chối upload trực tiếp file video dung lượng lớn.\n\n📥 Sếp bấm vào link này để tải video tốc độ cao từ máy chủ Cloud nhé:\n${downloadLink}\n\n(Link sẽ tự hủy sau 1 giờ)`, threadId, message.type);
              
              // Hẹn giờ xóa file sau 1 tiếng để sếp kịp tải
              setTimeout(() => {
                try {
                  if (require('fs').existsSync(result.videoPath)) require('fs').unlinkSync(result.videoPath);
                } catch(e) {}
              }, 3600000);
            }

          } else {
            await api.sendMessage(`❌ Quá trình tạo video thất bại: ${result.error}`, threadId, message.type);
          }
        }).catch(err => {
          logger.error('Lỗi ngầm khi tạo video', err);
        });

        return;
      }

      // ══════════════════════════════════════════════════════
      // SKILL 08 — MANUAL CEO BRIEFING (#baocao)
      // ══════════════════════════════════════════════════════

      if (userMessage.toLowerCase() === '#baocao') {
        if (!isAdmin) {
          logger.warn('🚫 Non-admin tried to execute #baocao', { threadId, senderId });
          return;
        }
        const stats = dataStore.getDailyStats();
        const today = new Date().toISOString().split('T')[0];
        const activeLeads = Object.values(dataStore.users).filter(u => u.lastContact.startsWith(today) && u.leadScore > 0);
        const leadsList = activeLeads.map(l => `• <b>${l.displayName}</b> (Score: ${l.leadScore}, Tags: ${l.tags.join(', ') || 'Chưa gắn'})`).join('\n') || '• Không có Lead mới tương tác.';

        const reportMsg = 
          `📊 <b>BÁO CÁO CEO TRỰC TIẾP (TRỢ LÝ CÔ BÍCH)</b> 📊\n` +
          `📅 Ngày: <b>${stats.date}</b>\n` +
          `━━━━━━━━━━━━━━━━━━━\n\n` +
          `👥 <b>Tương tác trong ngày:</b>\n` +
          `• Số khách hàng chat: <b>${stats.uniqueUsers} người</b>\n` +
          `• Tổng số tin nhắn: <b>${stats.totalMessages} tin</b>\n` +
          `  - Tin gửi đến Zalo: <b>${stats.incoming} tin</b>\n` +
          `  - Bot phản hồi: <b>${stats.outgoing} tin</b>\n\n` +
          `🎯 <b>Khách hàng tiềm năng & Đối tác hoạt động:</b>\n` +
          `${leadsList}\n\n` +
          `📈 <b>Tổng số khách hàng tích lũy:</b> <b>${stats.totalUsersAllTime} người</b>\n` +
          `💬 <b>Tổng số tin nhắn tích lũy:</b> <b>${stats.totalMessagesAllTime} tin</b>\n\n` +
          `🚀 <i>Hệ thống hoạt động bình thường!</i>`;

        try {
          const admin1 = config.zalo.adminId.split(',')[0];
          await api.sendMessage(reportMsg, admin1);
          await api.sendMessage(`✅ Báo cáo CEO (TRỢ LÝ CÔ BÍCH) đã được gửi vào Inbox của anh!`, threadId, message.type);
        } catch (err) {
          logger.error('Failed to send manual report to Telegram', err);
          await api.sendMessage(`❌ Lỗi gửi báo cáo: ${err.message}`, threadId, message.type);
        }
        return;
      }

      // ══════════════════════════════════════════════════════
      // SKILL 06 — COMMUNITY CONTENT CREATOR (#kichban)
      // ══════════════════════════════════════════════════════

      if (userMessage.toLowerCase().startsWith('#kichban')) {
        if (!isAdmin) {
          logger.warn('🚫 Non-admin tried to execute #kichban', { threadId, senderId });
          return;
        }

        const parts = userMessage.split(/\s+/);
        const approvedGroups = dataStore.getApprovedGroups();
        const defaultGroupId = approvedGroups.length > 0 ? approvedGroups[0].id : null;
        
        let targetGroupId = defaultGroupId;
        let isAI = false;
        let scenarioIdStr = null;

        if (parts[1] && parts[1].toLowerCase() === 'ai') {
          isAI = true;
          targetGroupId = parts[2] || defaultGroupId;
        } else {
          targetGroupId = parts[1] || defaultGroupId;
          scenarioIdStr = parts[2];
        }

        if (!targetGroupId) {
          await api.sendMessage(`❌ Chưa có nhóm nào được duyệt. Hãy dùng lệnh #duyet <GroupId> trước.`, threadId, message.type);
          return;
        }

        if (!dataStore.isGroupApproved(targetGroupId)) {
          await api.sendMessage(`❌ Nhóm ${targetGroupId} chưa được duyệt! Dùng #duyet trước.`, threadId, message.type);
          return;
        }

        try {
          if (isAI) {
            await api.sendMessage(`⏳ Đang sinh bài viết bằng AI dựa trên Ebook...`, threadId, message.type);
            const dayOfWeek = new Date().getDay();
            const result = await aiEngine.generateDynamicScenarioPost(dayOfWeek);
            const postMsg = `💡 [GỢI Ý VIẾT BÀI THEO EBOOK]\n📌 Ý tưởng: ${result.idea}\n━━━━━━━━━━━━━━━━━━━\n\n${result.content}`;
            
            await api.sendMessage(postMsg, targetGroupId, ThreadType.Group);
            dataStore.logMessage(targetGroupId, 'outgoing', postMsg);
            
            logger.info(`✅ Skill 06: Sent AI-generated scenario (Idea: ${result.idea}) to group ${targetGroupId}`);
            await api.sendMessage(`✅ Đã tạo và gửi kịch bản AI (Ý tưởng: ${result.idea}) vào nhóm ${targetGroupId}!`, threadId, message.type);
          } else {
            let scenario;
            if (scenarioIdStr) {
              scenario = getScenarioById(parseInt(scenarioIdStr));
              if (!scenario) {
                await api.sendMessage(`❌ Không tìm thấy kịch bản #${scenarioIdStr}. ID hợp lệ: 1-20.`, threadId, message.type);
                return;
              }
            } else {
              const lastId = dataStore.getLastScenarioId();
              const nextId = (lastId % 20) + 1;
              scenario = getScenarioById(nextId);
            }

            await api.sendMessage(scenario.content, targetGroupId, ThreadType.Group);
            dataStore.logMessage(targetGroupId, 'outgoing', scenario.content);
            logger.info(`✅ Skill 06: Sent scenario #${scenario.id} to group ${targetGroupId}`, { title: scenario.title });
            await api.sendMessage(`✅ Đã gửi kịch bản #${scenario.id} "${scenario.title}" vào nhóm ${targetGroupId}!`, threadId, message.type);
            if (!scenarioIdStr) {
              dataStore.setLastScenarioId(scenario.id);
            }
          }
        } catch (err) {
          logger.error('Failed to send scenario to group', err);
          await api.sendMessage(`❌ Lỗi gửi kịch bản: ${err.message}`, threadId, message.type);
        }
        return;
      }

      // ══════════════════════════════════════════════════════
      // SKILL 05 — TEST CARE COMMAND (#testcare)
      // ══════════════════════════════════════════════════════

      if (userMessage.toLowerCase() === '#testcare') {
        if (!isAdmin) {
          logger.warn('🚫 Non-admin tried to execute #testcare', { threadId, senderId });
          return;
        }
        
        const isGroup = message.type === ThreadType.Group;
        if (!isGroup) {
          await api.sendMessage(`❌ Lệnh #testcare chỉ chạy được từ trong nhóm đã duyệt!`, threadId, message.type);
          return;
        }

        if (userMessage === '#duyetnhomnay') {
        if (!isAdmin) {
          await api.sendMessage('❌ Bạn không có quyền duyệt nhóm.', threadId, message.type);
          return;
        }
        if (message.type === ThreadType.Group) {
          let groupName = 'Nhóm mới';
          try {
            const groupInfoRes = await api.getGroupInfo(threadId);
            if (groupInfoRes?.gridInfoMap?.[threadId]?.name) {
              groupName = groupInfoRes.gridInfoMap[threadId].name;
            }
          } catch (e) {}
          
          dataStore.approveGroup(threadId, groupName, 'Admin duyệt trực tiếp');
          dataStore.upsertUser(threadId, groupName);
          await api.sendMessage('✅ Đã cấp phép cho nhóm này! Cô Lưu Bích đã sẵn sàng hoạt động.', threadId, message.type);
        } else {
          await api.sendMessage('⚠️ Lệnh này chỉ dùng được trong nhóm.', threadId, message.type);
        }
        return;
      }

      if (!dataStore.isGroupApproved(threadId)) {
          await api.sendMessage(`❌ Nhóm này chưa được duyệt! Hãy duyệt nhóm trước bằng lệnh #duyet.`, threadId, message.type);
          return;
        }

        await api.sendMessage(`🔄 Đang thử nghiệm sinh nội dung và đăng ảnh Quote Card cho nhóm này...`, threadId, message.type);
        
        let tempImagePath = null;
        try {
          let groupName = 'Group Chat';
          try {
            const groupInfoRes = await api.getGroupInfo(threadId);
            if (groupInfoRes?.gridInfoMap?.[threadId]?.name) {
              groupName = groupInfoRes.gridInfoMap[threadId].name;
            }
          } catch (err) {
            logger.warn('Failed to fetch group info in #testcare', err);
          }

          const group = dataStore.getApprovedGroup(threadId);
          const timeOfDay = 'Buổi sáng (8:00)'; // Giả lập buổi sáng để test
          
          const nurturingData = await aiEngine.generateGroupNurturingPost(groupName, group.purpose, timeOfDay, group.id);
          tempImagePath = await createCard(nurturingData, timeOfDay, group.id, groupName, group.purpose);

          const imageBuffer = readFileSync(tempImagePath);
          const imgStats = statSync(tempImagePath);
          const attachment = {
            data: imageBuffer,
            filename: `nurturing_${threadId}.png`,
            metadata: {
              totalSize: imgStats.size,
              width: 800,
              height: 800
            }
          };

          const msgObject = {
            msg: nurturingData.post,
            attachments: [attachment]
          };

          await api.sendMessage(msgObject, threadId, ThreadType.Group);
          
          if (tempImagePath && existsSync(tempImagePath)) {
            unlinkSync(tempImagePath);
          }
          
          await api.sendMessage(`✅ Thử nghiệm hoàn tất thành công!`, threadId, message.type);
        } catch (err) {
          logger.error('Failed in #testcare execution', err);
          if (tempImagePath && existsSync(tempImagePath)) {
            unlinkSync(tempImagePath);
          }
          await api.sendMessage(`❌ Thử nghiệm thất bại: ${err.message}`, threadId, message.type);
        }
        return;
      }

      logger.info('💬 Message received', {
        threadId,
        type: message.type === ThreadType.Group ? 'Group' : 'User',
        message: userMessage.substring(0, 100),
      });

      // ══════════════════════════════════════════════════════
      // GROUP MESSAGE HANDLING (Skill 04 — chỉ nhóm đã duyệt)
      // ══════════════════════════════════════════════════════

      if (message.type === ThreadType.Group) {
        // Quyền Admin lấy ID nhóm nhanh
        if (isAdmin && userMessage.toLowerCase() === '#id') {
          await api.sendMessage(`🆔 ID của nhóm này là: ${threadId}`, threadId, message.type);
          return;
        }

        if (userMessage === '#duyetnhomnay') {
        if (!isAdmin) {
          await api.sendMessage('❌ Bạn không có quyền duyệt nhóm.', threadId, message.type);
          return;
        }
        if (message.type === ThreadType.Group) {
          let groupName = 'Nhóm mới';
          try {
            const groupInfoRes = await api.getGroupInfo(threadId);
            if (groupInfoRes?.gridInfoMap?.[threadId]?.name) {
              groupName = groupInfoRes.gridInfoMap[threadId].name;
            }
          } catch (e) {}
          
          dataStore.approveGroup(threadId, groupName, 'Admin duyệt trực tiếp');
          dataStore.upsertUser(threadId, groupName);
          await api.sendMessage('✅ Đã cấp phép cho nhóm này! Cô Lưu Bích đã sẵn sàng hoạt động.', threadId, message.type);
        } else {
          await api.sendMessage('⚠️ Lệnh này chỉ dùng được trong nhóm.', threadId, message.type);
        }
        return;
      }

      if (!dataStore.isGroupApproved(threadId)) {
          logger.debug('👥 Ignored message from unapproved group', { threadId });
          return;
        }

        // Cập nhật tên nhóm thực tế nếu có
        let groupName = 'Group Chat';
        try {
          const groupInfoRes = await api.getGroupInfo(threadId);
          if (groupInfoRes?.gridInfoMap?.[threadId]?.name) {
            groupName = groupInfoRes.gridInfoMap[threadId].name;
          }
        } catch (err) {
          logger.warn('Failed to fetch group info in message listener', err);
        }

        const groupObj = dataStore.upsertUser(threadId, groupName);
        const currentStep = groupObj.greetingStep || 0;

        if (currentStep < 2) {
          const greeting2 = `Cả nhà muốn tìm hiểu thêm thông tin gì cứ nhắn em`;
          
          // Delay ngẫu nhiên để tự nhiên hơn (1.5 - 3 giây)
          const replyDelay = 1500 + Math.random() * 1500;
          await delay(replyDelay);

          await api.sendMessage(greeting2, threadId, ThreadType.Group);
          logger.info('✅ Group welcome greeting 2 sent successfully', { groupId: threadId });

          // Lưu lịch sử nhóm và cập nhật step lập tức
          dataStore.logMessage(threadId, 'outgoing', greeting2);
          dataStore.addToConversation(threadId, 'assistant', greeting2);
          dataStore.setGreetingStep(threadId, 2);
        } else if (currentStep === 2) {
          const greeting3 = `Thông tin lớp học bên dưới:\n` +
            `MỚI NHẤT: Khoá học tạo phim hoạt hình cho trẻ em: https://forms.gle/JLGRTW6FoTCffdvm6\n\n` +
            `Nếu bạn muốn xây nhân hiệu cá nhân trên MXH?\n` +
            `Nếu bạn mong muốn tìm ra động lực kiếm tạo mục tiêu hay sứ mệnh thật sự của mình? \n` +
            `Xin mời bạn dành chút thời gian cho Bích Bích nhé!\n` +
            ` ✅ Đặt lịch coach 1:1 với Bích: \n` +
            `https://cohenvoituonglai.lovable.app \n\n` +
            `✅ Lộ trình chuyển giao nhân hiệu nhà đào tạo:\n` +
            `https://luuphanngocbich.com/nhanhieunhadaotao \n\n` +
            `✅ Học AI - 1 năm học AI liên tục cùng AI365 \n` +
            `https://ai365global.lovable.app\n\n` +
            `✅ Bộ quà tặng La Bàn 365: \n` +
            `https://luuphanngocbich.com/laban365/\n\n` +
            `✅ Thông tin thêm về Lưu Bích:\n` +
            `https://luuphanngocbich.com/\n` +
            `==================\n` +
            `Biết ơn các bạn đã ghé thăm trang cá nhân của Bích Bích!`;

          // Delay ngẫu nhiên để tự nhiên hơn (1.5 - 3 giây)
          const replyDelay = 1500 + Math.random() * 1500;
          await delay(replyDelay);

          await api.sendMessage(greeting3, threadId, ThreadType.Group);
          logger.info('✅ Group welcome greeting 3 sent successfully', { groupId: threadId });

          // Lưu lịch sử nhóm và cập nhật step lập tức
          dataStore.logMessage(threadId, 'outgoing', greeting3);
          dataStore.addToConversation(threadId, 'assistant', greeting3);
          dataStore.setGreetingStep(threadId, 3);
        }
        return; // Luôn kết thúc đối với nhóm (không chạy tiếp xuống AI)
      }

      // ══════════════════════════════════════════════════════
      // PERSONAL MESSAGE HANDLING
      // ══════════════════════════════════════════════════════

      const userId = threadId;

      // Rate limiting
      if (isRateLimited(userId)) {
        logger.warn('⚠️ Rate limited, skipping response', { userId });
        return;
      }

      // Track user
      let senderName = message.data.senderName || message.data.displayName || null;
      dataStore.upsertUser(userId, senderName);
      dataStore.logMessage(userId, 'incoming', userMessage);

      // ══════════════════════════════════════════════════════
      // SKILL 07 — LEAD CLASSIFICATION (Realtime)
      // ══════════════════════════════════════════════════════

      let scoreChange = 1;
      let scoreReason = 'Gửi tin nhắn';

      const lowerMsg = userMessage.toLowerCase();
      
      // Từ khóa tùy chỉnh cho cô Bích (không Trading)
      const highIntentKeywords = ['khóa học', 'đăng ký', 'giá', 'phí', 'học phí',
        'bao nhiêu', 'tham gia', 'khoá học', 'đào tạo', 'coach', 'nhân hiệu',
        'ai365', 'hoạt hình', 'la bàn', 'lộ trình'];

      if (highIntentKeywords.some(kw => lowerMsg.includes(kw))) {
        scoreChange = 5;
        scoreReason = `Quan tâm: "${userMessage.substring(0, 50)}"`;
      }

      // Detect phone number → Lead nóng (+10)
      const phoneRegex = /0\d{9,10}/;
      if (phoneRegex.test(userMessage)) {
        scoreChange = 10;
        scoreReason = `Gửi SĐT: ${userMessage.match(phoneRegex)[0]}`;
      }

      dataStore.updateLeadScore(userId, scoreChange, scoreReason);

      // ── Lead Classification Tags ──────────────────────
      const userObj = dataStore.getUser(userId);
      if (userObj) {
        // 🎯 Khách hàng tiềm năng
        if (lowerMsg.includes('đăng ký') || lowerMsg.includes('học phí') || lowerMsg.includes('mua') || 
            lowerMsg.includes('chuyển khoản') || lowerMsg.includes('thanh toán') || lowerMsg.includes('giá')) {
          if (!userObj.tags.includes('Khách hàng tiềm năng')) {
            userObj.tags.push('Khách hàng tiềm năng');
            dataStore.updateLeadScore(userId, 10, 'Phân loại: Khách hàng tiềm năng');
          }
        }
        // 👤 Khách hàng hiện tại
        else if (lowerMsg.includes('khiếu nại') || lowerMsg.includes('lỗi') || lowerMsg.includes('hoàn tiền') || 
                 lowerMsg.includes('không vào được') || lowerMsg.includes('bị lỗi') || lowerMsg.includes('hỏng')) {
          if (!userObj.tags.includes('Khách hàng hiện tại')) {
            userObj.tags.push('Khách hàng hiện tại');
            dataStore.updateLeadScore(userId, 5, 'Phân loại: Khách hàng hiện tại (khiếu nại/báo lỗi)');
          }
        }
        // 🤝 Đối tác
        else if (lowerMsg.includes('hợp tác') || lowerMsg.includes('dự án') || lowerMsg.includes('kết hợp') || 
                 lowerMsg.includes('partner') || lowerMsg.includes('mời giảng')) {
          if (!userObj.tags.includes('Đối tác')) {
            userObj.tags.push('Đối tác');
            dataStore.updateLeadScore(userId, 5, 'Phân loại: Đối tác');
          }
        }
        // 📞 Lead nóng (SĐT)
        else if (phoneRegex.test(userMessage)) {
          if (!userObj.tags.includes('Lead nóng')) {
            userObj.tags.push('Lead nóng');
          }
        }
        // 💬 Quan tâm (Coach, AI365, Nhân hiệu, Hoạt hình, La Bàn 365)
        else if (lowerMsg.includes('coach') || lowerMsg.includes('ai365') || lowerMsg.includes('nhân hiệu') || 
                 lowerMsg.includes('hoạt hình') || lowerMsg.includes('la bàn') || lowerMsg.includes('bích')) {
          if (!userObj.tags.includes('Quan tâm')) {
            userObj.tags.push('Quan tâm');
            dataStore.updateLeadScore(userId, 5, 'Phân loại: Quan tâm');
          }
        }
        // 🚫 Spam
        else if (lowerMsg.includes('quảng cáo') || lowerMsg.includes('vay vốn') || lowerMsg.includes('tuyển dụng') || 
                 lowerMsg.includes('chào dịch vụ') || lowerMsg.includes('seo')) {
          if (!userObj.tags.includes('Spam')) {
            userObj.tags.push('Spam');
            dataStore.updateLeadScore(userId, -10, 'Phân loại: Spam quảng cáo');
          }
        }
      }

      // ══════════════════════════════════════════════════════
      // SKILL 09 — ESCALATION TO HUMAN (Realtime)
      // ══════════════════════════════════════════════════════

      let escalationIntent = null;
      if (lowerMsg.includes('hợp tác') || lowerMsg.includes('dự án') || lowerMsg.includes('kết hợp') || 
          lowerMsg.includes('partner') || lowerMsg.includes('mời giảng') || lowerMsg.includes('co-brand')) {
        escalationIntent = 'Hợp tác';
      } else if (lowerMsg.includes('đặt lịch coach') || lowerMsg.includes('coach 1:1') || lowerMsg.includes('khai vấn')) {
        escalationIntent = 'Coach 1:1';
      } else if (lowerMsg.includes('đăng ký học') || lowerMsg.includes('đăng ký lớp') || lowerMsg.includes('học phí') || 
                 lowerMsg.includes('chuyển khoản') || lowerMsg.includes('thanh toán') || lowerMsg.includes('giá khóa')) {
        escalationIntent = 'Mua hàng/Đăng ký';
      } else if (lowerMsg.includes('khiếu nại') || lowerMsg.includes('lỗi') || lowerMsg.includes('không vào được') || 
                 lowerMsg.includes('hoàn tiền') || lowerMsg.includes('bị lỗi') || lowerMsg.includes('hỏng')) {
        escalationIntent = 'Khiếu nại/Lỗi';
      }

      if (escalationIntent) {
        logger.info(`🚨 Escalation detected: "${escalationIntent}". Forwarding to Telegram...`);
        // Send alert asynchronously so it doesn't block the AI response
        sendEscalationAlert(api, {
          senderName,
          threadId: userId,
          message: userMessage,
          intent: escalationIntent
        }).catch(err => logger.error('Error sending escalation alert', err));
      }

      // ── Generate AI Response ─────────────────────────
      let userGender = null;
      try {
        const profileInfo = await api.getUserInfo(userId);
        if (profileInfo) {
          const values = Object.values(profileInfo);
          const dataObj = values.find(v => v && typeof v === 'object');
          if (dataObj) {
            if (typeof dataObj.gender === 'number') userGender = dataObj.gender;
            if (!senderName && dataObj.displayName) {
              senderName = dataObj.displayName;
              dataStore.upsertUser(userId, senderName); // Update store with real name
            }
          } else {
            if (typeof profileInfo.gender === 'number') userGender = profileInfo.gender;
            if (!senderName && profileInfo.displayName) {
              senderName = profileInfo.displayName;
              dataStore.upsertUser(userId, senderName);
            }
          }
        }
      } catch (err) {
        logger.error('Failed to get profile for gender: ' + err.message);
      }
      const aiResponse = await aiEngine.generateResponse(userId, userMessage, false, senderName, userGender);

      // Delay ngẫu nhiên để tự nhiên hơn (không reply ngay lập tức)
      const replyDelay = randomDelay();
      logger.debug(`⏳ Waiting ${Math.round(replyDelay)}ms before replying...`);
      await delay(replyDelay);

      // ── Send Reply ───────────────────────────────────
      // Chia tin nhắn dài thành nhiều phần (Zalo giới hạn ~2000 ký tự)
      const parts = splitMessage(aiResponse, 2000);

      for (const part of parts) {
        try {
          await api.sendMessage(part, userId);
          if (!userMessageTimestamps[userId]) userMessageTimestamps[userId] = [];
          userMessageTimestamps[userId].push(Date.now());

          if (parts.length > 1) {
            await delay(500); // Delay giữa các phần
          }
        } catch (sendError) {
          logger.error('❌ Failed to send message', {
            userId,
            error: sendError.message,
          });
        }
      }

      // Log outgoing
      dataStore.logMessage(userId, 'outgoing', aiResponse);

      logger.info('✅ Reply sent', {
        userId,
        responseLength: aiResponse.length,
        delay: `${Math.round(replyDelay)}ms`,
      });

    } catch (error) {
      logger.error('❌ Error handling message', {
        error: error.message,
        stack: error.stack,
      });
    }
  });

  // ══════════════════════════════════════════════════════════
  // SKILL 01 — NEW FRIEND ONBOARDING (Auto greeting)
  // ══════════════════════════════════════════════════════════

  api.listener.on('friend_event', async (event) => {
    try {
      logger.info('👤 Friend event received', { type: event.type, threadId: event.threadId });
      
      // Tự động chấp nhận lời mời kết bạn mới
      if (event.type === FriendEventType.REQUEST) {
        const userId = event.data?.fromUid || event.threadId;
        logger.info('👤 Friend request received, auto-accepting...', { userId });
        try {
          await api.acceptFriendRequest(userId);
          logger.info('✅ Friend request accepted successfully', { userId });
        } catch (err) {
          logger.error('❌ Failed to accept friend request', { userId, error: err.message });
        }
      }

      if (event.type === FriendEventType.ADD) {
        const userId = event.threadId;
        logger.info('👤 New friend added, sending auto greeting', { userId });

        const greeting = `Dạ Bích chào bạn,\nRất biết ơn bạn đã kết bạn cùng Bích ạ !`;

        // Delay ngẫu nhiên để tự nhiên hơn (1.5 - 3 giây)
        const replyDelay = 1500 + Math.random() * 1500;
        await delay(replyDelay);

        await api.sendMessage(greeting, userId);
        logger.info('✅ Auto greeting sent to new friend successfully', { userId });

        // Ghi nhận vào DB/Lịch sử trò chuyện và cập nhật step lập tức
        dataStore.upsertUser(userId, null);
        dataStore.logMessage(userId, 'outgoing', greeting);
        dataStore.addToConversation(userId, 'assistant', greeting);
        dataStore.setGreetingStep(userId, 1);
      }
    } catch (err) {
      logger.error('❌ Failed to handle friend_event greeting', { error: err.message });
    }
  });

  // ══════════════════════════════════════════════════════════
  // SKILL 04 — GROUP INVITATION VERIFICATION (Group event)
  // ══════════════════════════════════════════════════════════

  api.listener.on('group_event', async (event) => {
    try {
      logger.info('👥 Group event received', { type: event.type, isSelf: event.isSelf, threadId: event.threadId });
      if (event.type === GroupEventType.JOIN) {
        const groupId = event.threadId;

        // Kiểm tra nhóm đã được duyệt chưa
        if (!dataStore.isGroupApproved(groupId)) {
          logger.info('👥 Bot added to pending group, awaiting verification', { groupId });
          
          let groupName = 'Nhóm mới';
          try {
            const groupInfoRes = await api.getGroupInfo(groupId);
            if (groupInfoRes?.gridInfoMap?.[groupId]?.name) {
              groupName = groupInfoRes.gridInfoMap[groupId].name;
            }
          } catch (err) {
            logger.warn('Failed to fetch group name during group_event', err);
          }

          const alertText = 
            `🤖 YÊU CẦU DUYỆT VÀO NHÓM (TRỢ LÝ CÔ BÍCH) 🤖\n\n` +
            `👥 Bot vừa được mời tham gia vào nhóm Zalo mới:\n` +
            `• Tên Nhóm: ${groupName}\n` +
            `• ID Nhóm: ${groupId}\n\n` +
            `💬 Để duyệt nhóm, anh copy cú pháp dưới đây và ghi thêm MỤC ĐÍCH NHÓM ở cuối rồi gửi lại cho em nhé:\n` +
            `#duyet ${groupId} [Ghi mục đích nhóm vào đây]`;
          
          const admin1 = config.zalo.adminId.split(',')[0];
          try {
            await api.sendMessage(alertText, admin1);
            logger.info('✅ Sent group verification request to Admin Zalo Inbox');
          } catch (e) {
            logger.error('❌ Failed to send verification request to Zalo Admin', e);
          }
          return;
        }

        // Nhóm đã duyệt → gửi greeting
        let groupName = 'Group Chat';
        try {
          const groupInfoRes = await api.getGroupInfo(groupId);
          if (groupInfoRes?.gridInfoMap?.[groupId]?.name) {
            groupName = groupInfoRes.gridInfoMap[groupId].name;
          }
        } catch (err) {
          logger.warn('Failed to fetch group name during welcome', err);
        }

        logger.info('👥 Bot added to an approved group, sending welcome greeting', { groupId, groupName });
        const greeting = `Chào cả nhà,\nBích rất biết ơn cả nhà đã đồng hành cùng Bích ạ !`;

        // Delay ngẫu nhiên để tự nhiên hơn (1.5 - 3 giây)
        const replyDelay = 1500 + Math.random() * 1500;
        await delay(replyDelay);

        await api.sendMessage(greeting, groupId, ThreadType.Group);
        logger.info('✅ Group welcome greeting sent successfully', { groupId });

        // Ghi nhận vào DB
        const groupObj = dataStore.getApprovedGroup(groupId);
        dataStore.approveGroup(groupId, groupName, groupObj?.purpose);
        dataStore.upsertUser(groupId, groupName);
        dataStore.logMessage(groupId, 'outgoing', greeting);
        dataStore.addToConversation(groupId, 'assistant', greeting);
        dataStore.setGreetingStep(groupId, 1);
      }
    } catch (err) {
      logger.error('❌ Failed to handle group_event greeting', { error: err.message });
    }
  });

  // ── Listener Event Handlers ────────────────────────────
  let isReconnecting = false;
  let reconnectAttempts = 0;
  const MAX_RECONNECT_ATTEMPTS = 5;

  api.listener.on('closed', async (code, reason) => {
    logger.warn('🔌 Listener connection closed', { code, reason });

    if (code === 1000 || code === 3000 || code === 3003) {
      if (code === 3000 || code === 3003) {
        await sendConnectionAlert(api, { botName: 'Cô Lưu Bích', errorMsg: `Zalo bị ngắt kết nối (Mã: ${code}, Lý do: ${reason}). Có thể do đăng nhập đè.` });
      }
      logger.error(`🔌 Bị Zalo đá văng (Code ${code}: ${reason}). Chờ 15s rồi kết nối lại Listener...`);
      // KHÔNG ĐƯỢC process.exit(1) ở đây vì sẽ tạo vòng lặp vô tận khi PM2 restart liên tục!
      await delay(15000);
      try {
        api.listener.start();
        logger.info('✅ Listener reconnected successfully sau khi bị đá văng');
      } catch (err) {
        logger.error('❌ Failed to reconnect listener sau khi bị đá văng', { error: err.message });
      }
      return;
    }

    if (isReconnecting) return;

    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      logger.error(`❌ Đã thử reconnect ${MAX_RECONNECT_ATTEMPTS} lần thất bại. Dừng reconnect.`);
      await sendConnectionAlert(api, { botName: 'Cô Lưu Bích', errorMsg: `Bot đã thử reconnect ${MAX_RECONNECT_ATTEMPTS} lần thất bại. Cần restart thủ công.` });
      reconnectAttempts = 0;
      return;
    }

    isReconnecting = true;
    reconnectAttempts++;
    const backoffDelay = Math.min(10000 * Math.pow(2, reconnectAttempts - 1), 300000); // 10s, 20s, 40s, 80s, 160s (max 5 phút)
    logger.info(`🔄 Connection dropped abnormally. Reconnect attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} in ${Math.round(backoffDelay / 1000)}s...`);
    await delay(backoffDelay);
    try {
      api.listener.start();
      logger.info('✅ Listener reconnected successfully');
      isReconnecting = false;
      reconnectAttempts = 0; // Reset counter on success
    } catch (err) {
      logger.error('❌ Failed to reconnect listener', { error: err.message });
      isReconnecting = false;
      // Trigger closed event again to schedule another attempt
      api.listener.emit('closed', code, 'Reconnect retry failed: ' + err.message);
    }
  });

  api.listener.on('error', async (error) => {
    const errMsg = error.message || String(error);
    logger.error('⚠️ Listener encountered an error', { error: errMsg });
    if (errMsg.includes('zpw_sek') || errMsg.includes('cookie') || errMsg.includes('login') || errMsg.includes('auth')) {
      await sendConnectionAlert(api, { botName: 'Cô Lưu Bích', errorMsg: `Lỗi kết nối Zalo: ${errMsg}` });
    }
  });

  // ── Start listener ─────────────────────────────────────
  api.listener.start();

  // ══════════════════════════════════════════════════════════
  // SKILL 08 — DAILY CEO BRIEFING (Cron 08:00)
  // ══════════════════════════════════════════════════════════

  let isBriefingRunning = false;
  cron.schedule('0 8 * * *', async () => {
    if (isBriefingRunning) {
      logger.info('⏰ CEO Briefing (Bích) already running, skipping duplicate trigger.');
      return;
    }
    // Khóa File + Khóa 65s
    const briefingDateStr = new Date().toISOString().split('T')[0];
    const briefingSessionFile = path.join(__dirname, '../data/briefing_session.json');
    let briefingSession = {};
    if (existsSync(briefingSessionFile)) {
      try { briefingSession = JSON.parse(readFileSync(briefingSessionFile, 'utf8')); } catch (e) {}
    }
    if (briefingSession.date === briefingDateStr && briefingSession.sent) {
      logger.info('✅ [Kháng Crash] CEO Briefing (Bích) đã gửi hôm nay rồi. Bỏ qua.');
      return;
    }
    if (Date.now() - (briefingSession.lastRunAt || 0) < 65000) {
      logger.info('⏰ CEO Briefing (Bích) vừa kích hoạt trong 65s. Bỏ qua.');
      return;
    }
    briefingSession = { date: briefingDateStr, sent: false, lastRunAt: Date.now() };
    writeFileSync(briefingSessionFile, JSON.stringify(briefingSession));

    isBriefingRunning = true;
    try {
      logger.info('⏰ Running Daily CEO Briefing job (TRỢ LÝ CÔ BÍCH)...');
      const stats = dataStore.getDailyStats();
      
      const today = new Date().toISOString().split('T')[0];
      const activeLeads = Object.values(dataStore.users).filter(u => u.lastContact.startsWith(today) && u.leadScore > 0);
      const leadsList = activeLeads.map(l => `• <b>${l.displayName}</b> (Score: ${l.leadScore}, Tags: ${l.tags.join(', ') || 'Chưa gắn'})`).join('\n') || '• Không có Lead mới tương tác.';

      const reportMsg = 
        `📊 <b>BÁO CÁO CEO MỖI SÁNG (TRỢ LÝ CÔ BÍCH)</b> 📊\n` +
        `📅 Ngày: <b>${stats.date}</b>\n` +
        `━━━━━━━━━━━━━━━━━━━\n\n` +
        `👥 <b>Tương tác trong ngày:</b>\n` +
        `• Số khách hàng chat: <b>${stats.uniqueUsers} người</b>\n` +
        `• Tổng số tin nhắn: <b>${stats.totalMessages} tin</b>\n` +
        `  - Tin gửi đến Zalo: <b>${stats.incoming} tin</b>\n` +
        `  - Bot phản hồi: <b>${stats.outgoing} tin</b>\n\n` +
        `🎯 <b>Khách hàng tiềm năng & Đối tác hoạt động:</b>\n` +
        `${leadsList}\n\n` +
        `📈 <b>Tổng số khách hàng tích lũy:</b> <b>${stats.totalUsersAllTime} người</b>\n` +
        `💬 <b>Tổng số tin nhắn tích lũy:</b> <b>${stats.totalMessagesAllTime} tin</b>\n\n` +
        `🚀 <i>Chúc anh Cường một ngày làm việc tràn đầy năng lượng!</i>`;

      const admin1 = config.zalo.adminId.split(',')[0];
      await api.sendMessage(reportMsg, admin1);
      // Ghi nhận thành công vào ổ cứng
      briefingSession.sent = true;
      writeFileSync(briefingSessionFile, JSON.stringify(briefingSession));
      logger.info('📤 Daily CEO Briefing (CÔ BÍCH) sent successfully');
    } catch (err) {
      logger.error('❌ Failed to run Daily CEO Briefing', { error: err.message });
    } finally {
      setTimeout(() => { isBriefingRunning = false; }, 65000);
    }
  }, { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // ══════════════════════════════════════════════════════════
  // SKILL 05 — GROUP CARE MANAGER (Cron 08:00/12:00/19:00)
  // ══════════════════════════════════════════════════════════

  let isNurturingRunning = false;
  async function runGroupNurturing(timeOfDay) {
    if (isNurturingRunning) {
      logger.info('⏰ Nurturing is already running, skipping this trigger to prevent duplicate posts.');
      return;
    }

    // --- LỚP KHÓA 1 & 2: KHÓA THỜI GIAN VÀ KHÓA Ổ CỨNG (SESSION) ---
    const dateStr = new Date().toISOString().split('T')[0];
    const sessionFile = path.join(__dirname, '../data/nurturing_session.json');
    let sessionData = {};
    if (existsSync(sessionFile)) {
      try { sessionData = JSON.parse(readFileSync(sessionFile, 'utf8')); } catch (e) {}
    }
    
    // Reset session nếu chuyển sang ca mới hoặc ngày mới
    if (sessionData.timeOfDay !== timeOfDay || sessionData.date !== dateStr) {
      sessionData = {
        date: dateStr,
        timeOfDay: timeOfDay,
        completedGroups: [],
        lastRunStartedAt: 0
      };
    }

    // Lớp khóa thời gian kháng Crash (65s)
    if (Date.now() - sessionData.lastRunStartedAt < 65000) {
      logger.info('⏰ Vừa mới kích hoạt trong vòng 65s qua. Bỏ qua để chống spam sập nguồn.');
      return;
    }
    sessionData.lastRunStartedAt = Date.now();
    writeFileSync(sessionFile, JSON.stringify(sessionData));

    isNurturingRunning = true;
    try {
      let rawGroups = dataStore.getApprovedGroups();
      
      // Lớp 3: Khử trùng lặp ID (Deduplication) để chống lỗi mảng
      const groups = [];
      const seenIds = new Set();
      for (const g of rawGroups) {
        if (!seenIds.has(g.id)) {
          seenIds.add(g.id);
          groups.push(g);
        }
      }
      
      if (groups.length === 0) {
        logger.info('⏰ No approved groups to send nurturing posts.');
        return;
      }

      logger.info(`⏰ Starting group nurturing posts for ${timeOfDay} to ${groups.length} groups...`);
      for (let i = 0; i < groups.length; i++) {
        const group = groups[i];

        // Lớp 4: Kháng Crash - Bỏ qua nếu đã gửi thành công trong ca này!
        if (sessionData.completedGroups.includes(group.id)) {
          logger.info(`✅ [Kháng Crash] Đã gửi cho nhóm ${group.id} trong ca này rồi. Bỏ qua chống spam.`);
          continue;
        }

        let tempImagePath = null;
        try {
          let groupName = group.name;
          try {
            const groupInfoRes = await api.getGroupInfo(group.id);
            if (groupInfoRes?.gridInfoMap?.[group.id]?.name) {
              groupName = groupInfoRes.gridInfoMap[group.id].name;
              dataStore.approveGroup(group.id, groupName, group.purpose);
            }
          } catch (err) {
            logger.warn('Failed to fetch group info from API during nurturing schedule', { groupId: group.id, error: err.message });
          }

          // Check if this group is "Làm chủ AI"
          const isLamChuAi = groupName && groupName.toLowerCase().includes('làm chủ ai');

          // "Làm chủ AI" group only receives posts once daily at 10:00 AM.
          // Other groups receive posts at 8:01, 12:00, and 19:00.
          if (timeOfDay === 'Buổi sáng (10:00)') {
            if (!isLamChuAi) {
              logger.info(`⏰ Skipping group "${groupName}" (${group.id}) for 10:00 AM nurturing schedule.`);
              continue;
            }
          } else {
            if (isLamChuAi) {
              logger.info(`⏰ Skipping group "${groupName}" (${group.id}) for standard ${timeOfDay} nurturing schedule.`);
              continue;
            }
          }

          // Sinh bài đăng AI chứa { post, quote } — truyền groupId để AI tránh trùng bài cũ
          const nurturingData = await aiEngine.generateGroupNurturingPost(groupName, group.purpose, timeOfDay, group.id);
          
          // Tạo Quote/Tip card tương ứng
          tempImagePath = await createCard(nurturingData.quote, timeOfDay, group.id, groupName, group.purpose);

          // Gửi tin nhắn kèm ảnh lên Zalo nhóm bằng đường dẫn file để zca-js tự upload
          const msgObject = {
            msg: nurturingData.post,
            attachments: [tempImagePath]
          };

          await api.sendMessage(msgObject, group.id, ThreadType.Group);
          logger.info(`✅ Sent nurturing post and image card to group "${groupName}" (${group.id}) successfully`, { timeOfDay });
          
          // Đánh dấu thành công vào ổ đĩa NGAY LẬP TỨC để kháng Crash
          if (!sessionData.completedGroups.includes(group.id)) {
            sessionData.completedGroups.push(group.id);
            writeFileSync(sessionFile, JSON.stringify(sessionData));
          }

          dataStore.logMessage(group.id, 'outgoing', nurturingData.post);
          // Lưu lịch sử bài post để lần sau AI tránh trùng
          dataStore.logNurturingPost(group.id, nurturingData.post, nurturingData.quote, timeOfDay);

          // Dọn dẹp ảnh tạm thời
          if (tempImagePath && existsSync(tempImagePath)) {
            unlinkSync(tempImagePath);
            logger.debug(`Cleaned up temp image: ${tempImagePath}`);
          }

          // Delay 3-5 phút giữa các nhóm (tránh spam)
          if (i < groups.length - 1) {
            const isTesting = process.env.NODE_ENV === 'test';
            const delayBetweenGroups = isTesting 
              ? (2000 + Math.random() * 2000) 
              : (180000 + Math.random() * 120000); // 3 - 5 phút
            
            logger.info(`⏳ Waiting ${Math.round(delayBetweenGroups / 1000)}s before posting to the next group...`);
            await delay(delayBetweenGroups);
          }
        } catch (groupError) {
          const errMsg = groupError.message || String(groupError);
          logger.error(`❌ Failed to send nurturing post to group ${group.id}`, { error: errMsg });
          if (errMsg.includes('zpw_sek') || errMsg.includes('cookie') || errMsg.includes('login') || errMsg.includes('auth')) {
            await sendConnectionAlert({ botName: 'Cô Lưu Bích', errorMsg: `Lỗi gửi bài đăng nhóm (session expired): ${errMsg}` });
          }
          try {
            if (tempImagePath && existsSync(tempImagePath)) {
              unlinkSync(tempImagePath);
            }
          } catch (cleanupErr) {
            logger.warn(`Failed to clean up temp image in catch block`, cleanupErr);
          }
        }
      }
    } catch (err) {
      logger.error('❌ Failed to run group nurturing scheduler', { error: err.message });
    } finally {
      logger.info(`✅ Group nurturing for ${timeOfDay} finished.`);
      // Đợi hết 1 phút (65s) rồi mới mở khóa RAM, để dập tắt hoàn toàn Cron spam
      setTimeout(() => {
        isNurturingRunning = false;
      }, 65000);
    }
  }

  // Chạy lúc 08:01 sáng hàng ngày (lệch 1 phút sau CEO Briefing 08:00 để tránh conflict)
  cron.schedule('1 8 * * *', () => runGroupNurturing('Buổi sáng (8:00)'), { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });
  
  // Chạy lúc 12:00 trưa hàng ngày
  cron.schedule('0 12 * * *', () => runGroupNurturing('Buổi trưa (12:00)'), { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // Chạy lúc 10:00 sáng hàng ngày (riêng cho nhóm Làm chủ AI)
  cron.schedule('0 10 * * *', () => runGroupNurturing('Buổi sáng (10:00)'), { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // Chạy lúc 19:00 tối hàng ngày
  cron.schedule('0 19 * * *', () => runGroupNurturing('Buổi tối (19:00)'), { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });



  // ══════════════════════════════════════════════════════════
  // SKILL 03 — FOLLOW-UP ENGINE (Cron 08:30)
  // ══════════════════════════════════════════════════════════

  let isFollowUpRunning = false;
  cron.schedule('30 8 * * *', async () => {
    if (isFollowUpRunning) {
      logger.info('⏰ Follow-up Engine already running, skipping duplicate trigger.');
      return;
    }
    // Khóa File + Khóa 65s
    const fuDateStr = new Date().toISOString().split('T')[0];
    const fuSessionFile = path.join(__dirname, '../data/followup_session.json');
    let fuSession = {};
    if (existsSync(fuSessionFile)) {
      try { fuSession = JSON.parse(readFileSync(fuSessionFile, 'utf8')); } catch (e) {}
    }
    if (fuSession.date === fuDateStr && fuSession.sent) {
      logger.info('✅ [Kháng Crash] Follow-up Engine đã gửi hôm nay rồi. Bỏ qua.');
      return;
    }
    if (Date.now() - (fuSession.lastRunAt || 0) < 65000) {
      logger.info('⏰ Follow-up Engine vừa kích hoạt trong 65s. Bỏ qua.');
      return;
    }
    fuSession = { date: fuDateStr, sent: false, lastRunAt: Date.now() };
    writeFileSync(fuSessionFile, JSON.stringify(fuSession));

    isFollowUpRunning = true;
    try {
      logger.info('⏰ Running Follow-up Engine job...');
      const now = new Date();
      const users = Object.values(dataStore.users);
      
      const followUpLeads = users.filter(u => {
        if (!u.leadScore || u.leadScore < 10) return false;
        if (u.tags?.includes('Spam')) return false;
        
        const lastContact = new Date(u.lastContact);
        const daysSince = (now - lastContact) / (1000 * 60 * 60 * 24);
        return daysSince >= 2 && daysSince <= 5;
      });

      if (followUpLeads.length === 0) {
        logger.info('📋 No leads to follow up today.');
        return;
      }

      let reportText = `📌 <b>GỢI Ý FOLLOW-UP HÔM NAY (TRỢ LÝ CÔ BÍCH)</b>\n\n`;
      
      followUpLeads.forEach((lead, idx) => {
        const daysSince = Math.round((now - new Date(lead.lastContact)) / (1000 * 60 * 60 * 24));
        const tags = lead.tags?.join(', ') || 'Chưa gắn';
        reportText += `${idx + 1}️⃣ <b>${lead.displayName}</b> — Score: ${lead.leadScore}\n`;
        reportText += `   Lần cuối: ${daysSince} ngày trước\n`;
        reportText += `   Tags: ${tags}\n\n`;
      });

      reportText += `⚠️ <i>Anh Cường tự quyết định có nhắn hay không. Bot KHÔNG tự gửi tin follow-up cho khách.</i>`;

      const admin1 = config.zalo.adminId.split(',')[0];
      await api.sendMessage(reportText, admin1);
      fuSession.sent = true;
      writeFileSync(fuSessionFile, JSON.stringify(fuSession));
      logger.info(`📤 Follow-up suggestions sent to Zalo Admin (${followUpLeads.length} leads)`);
    } catch (err) {
      logger.error('❌ Failed to run Follow-up Engine', { error: err.message });
    } finally {
      setTimeout(() => { isFollowUpRunning = false; }, 65000);
    }
  }, { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // ══════════════════════════════════════════════════════════
  // SKILL 02 — EXISTING CONTACT NURTURING (Cron 09:00)
  // ══════════════════════════════════════════════════════════

  let isNurturingContactRunning = false;
  cron.schedule('0 9 * * *', async () => {
    if (isNurturingContactRunning) {
      logger.info('⏰ Contact Nurturing already running, skipping duplicate trigger.');
      return;
    }
    // Khóa File + Khóa 65s
    const ncDateStr = new Date().toISOString().split('T')[0];
    const ncSessionFile = path.join(__dirname, '../data/contact_nurturing_session.json');
    let ncSession = {};
    if (existsSync(ncSessionFile)) {
      try { ncSession = JSON.parse(readFileSync(ncSessionFile, 'utf8')); } catch (e) {}
    }
    if (ncSession.date === ncDateStr && ncSession.sent) {
      logger.info('✅ [Kháng Crash] Contact Nurturing đã gửi hôm nay rồi. Bỏ qua.');
      return;
    }
    if (Date.now() - (ncSession.lastRunAt || 0) < 65000) {
      logger.info('⏰ Contact Nurturing vừa kích hoạt trong 65s. Bỏ qua.');
      return;
    }
    ncSession = { date: ncDateStr, sent: false, lastRunAt: Date.now() };
    writeFileSync(ncSessionFile, JSON.stringify(ncSession));

    isNurturingContactRunning = true;
    try {
      logger.info('⏰ Running Existing Contact Nurturing job...');
      const now = new Date();
      const users = Object.values(dataStore.users);
      
      const nurtureTargets = users.filter(u => {
        if (!u.leadScore || u.leadScore <= 0) return false;
        if (u.tags?.includes('Spam')) return false;
        if (!u.displayName || u.displayName === 'Unknown') return false;
        if (!u.id) return false;
        
        const lastContact = new Date(u.lastContact);
        const daysSince = (now - lastContact) / (1000 * 60 * 60 * 24);
        if (daysSince < 7) return false;
        
        if (u.lastNurtured) {
          const lastNurtured = new Date(u.lastNurtured);
          const daysSinceNurture = (now - lastNurtured) / (1000 * 60 * 60 * 24);
          if (daysSinceNurture < 30) return false;
        }
        
        return true;
      });

      const selectedTargets = nurtureTargets.slice(0, 3);

      if (selectedTargets.length === 0) {
        logger.info('📋 No contacts to nurture today.');
        return;
      }

      logger.info(`📤 Nurturing ${selectedTargets.length} contacts...`);

      const templates = [
        (name) => `Chào ${name}, lâu rồi không gặp anh/chị! 😊\nEm vừa cập nhật thêm tài liệu ứng dụng AI/Nhân hiệu.\nNếu anh/chị quan tâm, em chia sẻ thêm nhé!`,
        (name) => `Chào ${name}, anh/chị dạo này thế nào rồi ạ? Lớp học AI365 hoặc phim hoạt hình cho bé vẫn đang rất sôi nổi đấy ạ.\nNếu cần hỗ trợ gì, cứ nhắn em nhé!`,
        (name) => `Chào ${name}! Lộ trình coach 1:1 kiến tạo mục tiêu của cô Lưu Bích vừa cập nhật một số điểm định hướng mới.\nAnh/chị muốn em giới thiệu qua không? 🗺️`,
      ];

      for (let i = 0; i < selectedTargets.length; i++) {
        const user = selectedTargets[i];
        try {
          const template = templates[Math.floor(Math.random() * templates.length)];
          const nurtureMsg = template(user.displayName || 'anh/chị');

          if (i > 0) {
            const nurtureDelay = 300000 + Math.random() * 300000;
            logger.info(`⏳ Waiting ${Math.round(nurtureDelay / 1000)}s before nurturing next contact...`);
            await delay(nurtureDelay);
          }

          await api.sendMessage(nurtureMsg, user.id);
          
          user.lastNurtured = now.toISOString();
          dataStore.logMessage(user.id, 'outgoing', nurtureMsg);
          
          logger.info(`✅ Nurture message sent to ${user.displayName}`, { userId: user.id });
        } catch (err) {
          logger.error(`❌ Failed to nurture ${user.displayName}`, { userId: user.id, error: err.message });
        }
      }
      ncSession.sent = true;
      writeFileSync(ncSessionFile, JSON.stringify(ncSession));
    } catch (err) {
      logger.error('❌ Failed to run Nurturing job', { error: err.message });
    } finally {
      setTimeout(() => { isNurturingContactRunning = false; }, 65000);
    }
  }, { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // ══════════════════════════════════════════════════════════
  // DISPLAY STARTUP INFO
  // ══════════════════════════════════════════════════════════

  console.log('\n╔══════════════════════════════════════════════════════════╗');
  console.log('║       🎉 BOT IS RUNNING — TRỢ LÝ CÔ LƯU BÍCH!         ║');
  console.log('╠══════════════════════════════════════════════════════════╣');
  console.log(`║  AI Provider:  ${config.ai.provider.padEnd(39)}║`);
  console.log(`║  Rate Limit:   ${config.rateLimit.maxMessagesPerMinute} msg/min                             ║`);
  console.log(`║  Reply Delay:  ${config.rateLimit.minDelay}-${config.rateLimit.maxDelay}ms                            ║`);
  console.log('║                                                          ║');
  console.log('║  Admin Commands:                                         ║');
  console.log('║    #id #baocao #testcare                                 ║');
  console.log('║    #duyet [groupId] [mục đích]                           ║');
  console.log('║    #mucdich [groupId] [mục đích mới]                     ║');
  console.log('║    #kichban [groupId] [scenarioId]                       ║');
  console.log('║    #kichban ai [groupId] (AI sinh bài đăng)              ║');
  console.log('║  User Commands:                                          ║');
  console.log('║    #menu #khoa_hoc #tu_van #faq                          ║');
  console.log('║                                                          ║');
  console.log('║  Cron Schedule:                                          ║');
  console.log('║    08:00 CEO Briefing                                    ║');
  console.log('║    08:01 Group Care (sáng)                               ║');
  console.log('║    08:30 Follow-up Engine                                ║');
  console.log('║    09:00 Contact Nurturing                               ║');
  console.log('║    10:00 Làm chủ AI Group Care                           ║');
  console.log('║    12:00 Group Care (trưa)                               ║');
  console.log('║    19:00 Group Care (tối) & Content Creator (T3, T5)     ║');
  console.log('║                                                          ║');
  console.log('║  Press Ctrl+C to stop                                    ║');
  console.log('╚══════════════════════════════════════════════════════════╝\n');

  // ── Periodic Stats Log ─────────────────────────────────
  setInterval(() => {
    const stats = dataStore.getDailyStats();
    logger.info('📊 Stats', stats);
  }, 3600000); // Mỗi 1 giờ
}

// ── Utilities ────────────────────────────────────────────

function splitMessage(text, maxLen) {
  if (text.length <= maxLen) return [text];

  const parts = [];
  let remaining = text;
  while (remaining.length > 0) {
    if (remaining.length <= maxLen) {
      parts.push(remaining);
      break;
    }
    let splitAt = remaining.lastIndexOf('\n', maxLen);
    if (splitAt === -1 || splitAt < maxLen * 0.5) {
      splitAt = remaining.lastIndexOf(' ', maxLen);
    }
    if (splitAt === -1) splitAt = maxLen;

    parts.push(remaining.substring(0, splitAt));
    remaining = remaining.substring(splitAt).trimStart();
  }
  return parts;
}

// ── Graceful Shutdown & Error Handling ───────────────────

process.on('SIGTERM', () => {
  logger.info('🛑 Shutting down (SIGTERM)...');
  dataStore.close();
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('🛑 Shutting down (SIGINT/Ctrl+C)...');
  dataStore.close();
  process.exit(0);
});

process.on('SIGHUP', () => {
  logger.warn('⚠️ Received SIGHUP (Terminal closed). Attempting to keep running or log termination...');
  dataStore.close();
  process.exit(0);
});

process.on('uncaughtException', (err) => {
  logger.error('💥 Uncaught Exception!', { error: err.message, stack: err.stack });
  dataStore.close();
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('💥 Unhandled Rejection!', { reason: String(reason) });
});

// ── Start ────────────────────────────────────────────────
startBot().catch(error => {
  logger.error('💥 Fatal error in startBot', { error: error.message, stack: error.stack });
  dataStore.close();
  process.exit(1);
});
