// ============================================================
// index.js — Zalo AI Assistant (Personal Account)
// ============================================================
// Bot chính — kết nối Zalo cá nhân qua zca-js,
// lắng nghe tin nhắn và phản hồi bằng AI.
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
import { startOrderMonitor } from './order-monitor.js';
import { createYouTubeVideo } from './video-creator.js';
import { getScenarioForToday } from './content-scenarios.js';

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
  console.log('║       🤖 ZALO AI ASSISTANT — STARTING...                 ║');
  console.log('║       Trợ Lý Ảo cho Doanh Nghiệp OPC                    ║');
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
    
    // Start order monitor
    startOrderMonitor(api);
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
      logger.info('📩 Raw message event received:', {
        type: message.type,
        threadId: message.threadId,
        isSelf: message.isSelf,
        content: message.data?.content,
      });

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

      // ── Group Entry Approval Command (Skill 04) ───────
      if (userMessage.startsWith('#duyet ')) {
        if (!isAdmin) {
          logger.warn('🚫 Non-admin tried to execute #duyet', { threadId, senderId });
          return;
        }
        const cmdParts = userMessage.substring('#duyet '.length).trim().split(/\s+/);
        const targetGroupId = cmdParts[0];
        const purpose = userMessage.substring('#duyet '.length + targetGroupId.length).trim() || 
                        'Chia sẻ kiến thức, thảo luận về Kinh Doanh và Đầu Tư Thong Dong cùng anh Cường.';
        
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
          const welcomeMsg = `Chào cả nhà,\nEm là trợ lý của anh Cường\nRất biết ơn cả nhà đồng hành cùng nhau ạ !`;
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
          await api.sendMessage(`❌ Anh/chị không có quyền sử dụng chức năng tạo video.\n[Debug] ID: ${threadIdStr} - ${senderId} | Admins: ${adminIds.join(', ')}`, threadId, message.type);
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
              // Thêm timeout 5 phút cho việc upload lên Zalo
              const uploadPromise = api.sendMessage({ msg: "", attachments: [result.videoPath] }, threadId, message.type);
              const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('Zalo Upload Timeout - Zalo server không phản hồi')), 300000));
              await Promise.race([uploadPromise, timeoutPromise]);
              
              // Xóa file sau khi gửi thành công
              unlinkSync(result.videoPath);
            } catch (err) {
              logger.error('Lỗi upload file video lên Zalo', err);
              
              // Tạo link tải trực tiếp từ server
              const relativePath = result.videoPath.split('/cloud-deployment/')[1] || result.videoPath.split('/app/')[1] || `cuong-bot/scratch/video_temps/${require('path').basename(result.videoPath)}`;
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

      // ── Manual CEO Briefing Command (Skill 08) ────────
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
          `📊 <b>BÁO CÁO CEO TRỰC TIẾP</b> 📊\n` +
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
          await api.sendMessage(`✅ Báo cáo CEO đã được gửi vào Inbox của anh!`, threadId, message.type);
        } catch (err) {
          logger.error('Failed to send manual report to Telegram', err);
          await api.sendMessage(`❌ Lỗi gửi báo cáo: ${err.message}`, threadId, message.type);
        }
        return;
      }

      // ── Test Nurturing Post Command (Skill 05 Test) ─────
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
          
          const nurturingData = await aiEngine.generateGroupNurturingPost(groupName, group.purpose, timeOfDay);
          tempImagePath = await createCard(nurturingData.quote, timeOfDay, threadId, groupName, group.purpose);

          const imageBuffer = readFileSync(tempImagePath);
          const stats = statSync(tempImagePath);
          const attachment = {
            data: imageBuffer,
            filename: `nurturing_${threadId}.png`,
            metadata: {
              totalSize: stats.size,
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

      // Nếu là tin nhắn nhóm, ta CHỈ xử lý nếu nhóm đã được duyệt và bot được nhắc tên (mention)
      if (message.type === ThreadType.Group) {
        // Quyền Admin lấy ID nhóm nhanh
        if (isAdmin && userMessage.toLowerCase() === '#id') {
          await api.sendMessage(`🆔 ID của nhóm này là: ${threadId}`, threadId, ThreadType.Group);
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
            await api.sendMessage('✅ Đã cấp phép cho nhóm này! Trợ lý AI đã sẵn sàng hoạt động.', threadId, message.type);
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

        // Kiểm tra xem bot có được nhắc tên trực tiếp không
        const botUserId = api.getOwnId();
        const mentions = message.data?.mentions || [];
        const isMentioned = mentions.some(m => m.uid === botUserId);

        const nameKeywords = ['cường assistant', 'trợ lý của anh cường', 'trợ lý cường', 'trợ lý của cường', 'anh cường ơi'];
        const containsKeyword = nameKeywords.some(kw => userMessage.toLowerCase().includes(kw));

        if (!isMentioned && !containsKeyword) {
          return; // Bỏ qua nếu không được nhắc tên
        }

        logger.info('💬 Mentioned in group, generating AI response...', { threadId, userMessage });

        dataStore.upsertUser(threadId, groupName);
        dataStore.logMessage(threadId, 'incoming', userMessage);

        // Sinh phản hồi từ AI Engine
        const senderName = message.data?.senderName || message.data?.displayName || null;
        const aiResponse = await aiEngine.generateResponse(threadId, userMessage, true, senderName);

        // Delay ngẫu nhiên để tự nhiên hơn (1.5 - 4 giây)
        const replyDelay = randomDelay();
        await delay(replyDelay);

        // Chia tin nhắn dài thành nhiều phần (Zalo giới hạn ~2000 ký tự)
        const parts = splitMessage(aiResponse, 2000);

        for (const part of parts) {
          try {
            await api.sendMessage(part, threadId, ThreadType.Group);
            messageTimestamps.push(Date.now());

            if (parts.length > 1) {
              await delay(500); // Delay giữa các phần
            }
          } catch (sendError) {
            logger.error('❌ Failed to send message to group', {
              threadId,
              error: sendError.message,
            });
          }
        }

        // Log outgoing
        dataStore.logMessage(threadId, 'outgoing', aiResponse);

        logger.info('✅ Group reply sent', {
          threadId,
          responseLength: aiResponse.length,
          delay: `${Math.round(replyDelay)}ms`,
        });

        return; // Kết thúc xử lý đối với nhóm
      }

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

      // Cố gắng tự động chấp nhận kết bạn nếu người này nhắn tin (fallback nếu friend_event bị xịt)
      try {
        await api.acceptFriendRequest(userId.toString());
      } catch(e) {
        // Bỏ qua lỗi nếu đã là bạn bè hoặc không có lời mời
      }

      // ── Lead Scoring ─────────────────────────────────
      let scoreChange = 1;
      let scoreReason = 'Gửi tin nhắn';

      const lowerMsg = userMessage.toLowerCase();
      const highIntentKeywords = ['khóa học', 'học trading', 'giá', 'phí', 'đăng ký',
        'bao nhiêu', 'tham gia', 'mentor', 'khoá học', 'dạy', 'đào tạo'];

      if (highIntentKeywords.some(kw => lowerMsg.includes(kw))) {
        scoreChange = 5;
        scoreReason = `Quan tâm: "${userMessage.substring(0, 50)}"`;
      }

      // Detect phone number
      const phoneRegex = /0\d{9,10}/;
      if (phoneRegex.test(userMessage)) {
        scoreChange = 10;
        scoreReason = `Gửi SĐT: ${userMessage.match(phoneRegex)[0]}`;
      }

      dataStore.updateLeadScore(userId, scoreChange, scoreReason);

      // ── Escalation to Human (Skill 09) ─────────────────
      let escalationIntent = null;
      if (lowerMsg.includes('hợp tác') || lowerMsg.includes('dự án') || lowerMsg.includes('kết hợp') || lowerMsg.includes('partner') || lowerMsg.includes('hợp tác kinh doanh')) {
        escalationIntent = 'Hợp tác';
      } else if (lowerMsg.includes('đầu tư') || lowerMsg.includes('invest') || lowerMsg.includes('góp vốn') || lowerMsg.includes('quỹ')) {
        escalationIntent = 'Đầu tư';
      } else if (lowerMsg.includes('khiếu nại') || lowerMsg.includes('lỗi') || lowerMsg.includes('hỏng') || lowerMsg.includes('không chạy') || lowerMsg.includes('bị lỗi') || lowerMsg.includes('hoàn tiền')) {
        escalationIntent = 'Khiếu nại/Lỗi';
      } else if (lowerMsg.includes('đăng ký học') || lowerMsg.includes('mua khóa học') || lowerMsg.includes('mua khoá học') || lowerMsg.includes('đăng ký bot') || lowerMsg.includes('mua bot') || lowerMsg.includes('học phí') || lowerMsg.includes('phí bot') || lowerMsg.includes('chuyển khoản') || lowerMsg.includes('thanh toán')) {
        escalationIntent = 'Mua hàng/Đăng ký';
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

      // ── Lead Classification (Skill 07) ─────────────────
      const userObj = dataStore.getUser(userId);
      if (userObj) {
        if (escalationIntent === 'Hợp tác' || escalationIntent === 'Đầu tư') {
          if (!userObj.tags.includes('Đối tác')) {
            userObj.tags.push('Đối tác');
            dataStore.updateLeadScore(userId, 5, 'Phân loại: Đối tác');
          }
        } else if (escalationIntent === 'Mua hàng/Đăng ký') {
          if (!userObj.tags.includes('Khách hàng tiềm năng')) {
            userObj.tags.push('Khách hàng tiềm năng');
            dataStore.updateLeadScore(userId, 10, 'Phân loại: Khách hàng tiềm năng');
          }
        } else if (escalationIntent === 'Khiếu nại/Lỗi') {
          if (!userObj.tags.includes('Khách hàng hiện tại')) {
            userObj.tags.push('Khách hàng hiện tại');
            dataStore.updateLeadScore(userId, 5, 'Phân loại: Khách hàng hiện tại (khiếu nại/báo lỗi)');
          }
        } else if (lowerMsg.includes('quảng cáo') || lowerMsg.includes('bán hàng') || lowerMsg.includes('chào sản phẩm') || lowerMsg.includes('vay vốn') || lowerMsg.includes('tuyển dụng')) {
          if (!userObj.tags.includes('Spam')) {
            userObj.tags.push('Spam');
            dataStore.updateLeadScore(userId, -10, 'Phân loại: Spam quảng cáo');
          }
        }
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

  // ── Auto greeting when a friend is added ────────────────
  api.listener.on('friend_event', async (event) => {
    try {
      logger.info('👤 Friend event received', { type: event.type, threadId: event.threadId });
      
      // Tự động chấp nhận lời mời kết bạn mới
      if (event.type === FriendEventType.REQUEST) {
        const userId = (event.data?.fromUid || event.threadId)?.toString();
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

        const greeting = `Dạ em chào anh/chị,\nEm là trợ lý AI của anh Cường.\nRất vui được kết nối và hỗ trợ anh/chị ạ!`;

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

  // ── Auto greeting when bot is added to a Zalo Group ─────
  api.listener.on('group_event', async (event) => {
    try {
      logger.info('👥 Group event received', { type: event.type, isSelf: event.isSelf, threadId: event.threadId });
      if (event.type === GroupEventType.JOIN) {
        const groupId = event.threadId;

        // ── Group entry verification (Skill 04) ─────────
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
            `🤖 YÊU CẦU DUYỆT VÀO NHÓM 🤖\n\n` +
            `👥 Bot vừa được mời tham gia vào nhóm Zalo mới:\n` +
            `• Tên Nhóm: ${groupName}\n` +
            `• ID Nhóm: ${groupId}\n\n` +
            `💬 Để duyệt và cho phép bot hoạt động trong nhóm này, anh vui lòng copy cú pháp dưới đây và gửi lại cho em:\n` +
            `#duyet ${groupId}`;
          
          const admin1 = config.zalo.adminId.split(',')[0];
          try {
            await api.sendMessage(alertText, admin1);
            logger.info('✅ Sent group verification request to Admin Zalo Inbox');
          } catch (e) {
            logger.error('❌ Failed to send verification request to Zalo Admin', e);
          }
          return;
        }

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
        const greeting = `Chào cả nhà,\nEm là trợ lý của anh Cường\nRất biết ơn cả nhà đồng hành cùng nhau ạ !`;

        // Delay ngẫu nhiên để tự nhiên hơn (1.5 - 3 giây)
        const replyDelay = 1500 + Math.random() * 1500;
        await delay(replyDelay);

        await api.sendMessage(greeting, groupId, ThreadType.Group);
        logger.info('✅ Group welcome greeting sent successfully', { groupId });

        // Ghi nhận vào DB/Lịch sử trò chuyện và cập nhật step lập tức
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
        await sendConnectionAlert(api, { botName: 'Anh Cường', errorMsg: `Zalo bị ngắt kết nối (Mã: ${code}, Lý do: ${reason}). Có thể do đăng nhập đè.` });
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
      await sendConnectionAlert(api, { botName: 'Anh Cường', errorMsg: `Bot đã thử reconnect ${MAX_RECONNECT_ATTEMPTS} lần thất bại. Cần restart thủ công.` });
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
      await sendConnectionAlert(api, { botName: 'Anh Cường', errorMsg: `Lỗi kết nối Zalo: ${errMsg}` });
    }
  });

  // ── Start listener ─────────────────────────────────────
  api.listener.start();

  // ── Daily CEO Briefing (Skill 08) ───────────────────────
  // Chạy lúc 08:00 sáng hàng ngày: '0 8 * * *'
  let isBriefingRunning = false;
  cron.schedule('0 8 * * *', async () => {
    if (isBriefingRunning) {
      logger.info('⏰ CEO Briefing is already running, skipping duplicate trigger.');
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
      logger.info('✅ [Kháng Crash] CEO Briefing đã gửi hôm nay rồi. Bỏ qua.');
      return;
    }
    if (Date.now() - (briefingSession.lastRunAt || 0) < 65000) {
      logger.info('⏰ CEO Briefing vừa kích hoạt trong 65s. Bỏ qua.');
      return;
    }
    briefingSession = { date: briefingDateStr, sent: false, lastRunAt: Date.now() };
    writeFileSync(briefingSessionFile, JSON.stringify(briefingSession));

    isBriefingRunning = true;
    try {
      logger.info('⏰ Running Daily CEO Briefing job...');
      const stats = dataStore.getDailyStats();
      
      // Get leads and partners added today
      const today = new Date().toISOString().split('T')[0];
      const activeLeads = Object.values(dataStore.users).filter(u => u.lastContact.startsWith(today) && u.leadScore > 0);
      const leadsList = activeLeads.map(l => `• <b>${l.displayName}</b> (Score: ${l.leadScore}, Tags: ${l.tags.join(', ') || 'Chưa gắn'})`).join('\n') || '• Không có Lead mới tương tác.';

      const reportMsg = 
        `📊 <b>BÁO CÁO CEO MỖI SÁNG</b> 📊\n` +
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
      briefingSession.sent = true;
      writeFileSync(briefingSessionFile, JSON.stringify(briefingSession));
      logger.info('📤 Daily CEO Briefing sent successfully');
    } catch (err) {
      logger.error('❌ Failed to run Daily CEO Briefing', { error: err.message });
    } finally {
      setTimeout(() => { isBriefingRunning = false; }, 65000);
    }
  }, { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // ── Daily Group Nurturing (Skill 04) ────────────────────
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
            logger.warn('Failed to fetch group info from API during nurturing schedule, using local storage name', { groupId: group.id, error: err.message });
          }

          // Sinh bài đăng AI chứa { post, quote } — truyền group.id để tránh trùng lặp
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

          // Tránh delay cho nhóm cuối cùng
          if (i < groups.length - 1) {
            const isTesting = process.env.NODE_ENV === 'test';
            const delayBetweenGroups = isTesting 
              ? (2000 + Math.random() * 2000) 
              : (180000 + Math.random() * 120000); // 3 - 5 phút (180s - 300s)
            
            logger.info(`⏳ Waiting ${Math.round(delayBetweenGroups / 1000)}s before posting to the next group...`);
            await delay(delayBetweenGroups);
          }
        } catch (groupError) {
          const errMsg = groupError.message || String(groupError);
          logger.error(`❌ Failed to send nurturing post to group ${group.id}`, { error: errMsg });
          if (errMsg.includes('zpw_sek') || errMsg.includes('cookie') || errMsg.includes('login') || errMsg.includes('auth')) {
            await sendConnectionAlert(api, { botName: 'Anh Cường', errorMsg: `Lỗi gửi bài đăng nhóm (session expired): ${errMsg}` });
          }
          // Đảm bảo dọn dẹp ảnh tạm thời nếu gặp lỗi giữa chừng
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

  // Chạy lúc 08:01 sáng hàng ngày (lệch 1 phút sau CEO Briefing để tránh conflict)
  cron.schedule('1 8 * * *', () => runGroupNurturing('Buổi sáng (8:00)'), { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });
  
  // Chạy lúc 12:00 trưa hàng ngày
  cron.schedule('0 12 * * *', () => runGroupNurturing('Buổi trưa (12:00)'), { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // Chạy lúc 19:00 tối hàng ngày
  cron.schedule('0 19 * * *', () => runGroupNurturing('Buổi tối (19:00)'), { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // ── SKILL 03: Follow-Up Engine ──────────────────────────
  let isFollowUpRunning = false;
  cron.schedule('30 8 * * *', async () => {
    if (isFollowUpRunning) return;
    const sessionFile = path.join(__dirname, '../data/followup_session.json');
    const todayStr = new Date().toISOString().split('T')[0];
    let sessionData = {};
    if (existsSync(sessionFile)) {
      try { sessionData = JSON.parse(readFileSync(sessionFile, 'utf8')); } catch(e){}
    }
    if (sessionData.date === todayStr && sessionData.sent) return;
    if (Date.now() - (sessionData.lastRunAt || 0) < 65000) return;
    
    sessionData = { date: todayStr, sent: false, lastRunAt: Date.now() };
    writeFileSync(sessionFile, JSON.stringify(sessionData));
    isFollowUpRunning = true;

    try {
      logger.info('⏰ Running Follow-Up Engine (Skill 03)...');
      const allUsers = Object.values(dataStore.users);
      const now = Date.now();
      
      const leads = allUsers.filter(u => {
        if (!u.lastContact || (u.leadScore || 0) < 10) return false;
        const lastContactTime = new Date(u.lastContact).getTime();
        const daysSinceContact = (now - lastContactTime) / (1000 * 3600 * 24);
        return daysSinceContact >= 2 && daysSinceContact <= 5;
      });

      if (leads.length > 0) {
        let msg = `📌 <b>GỢI Ý FOLLOW-UP HÔM NAY</b>\n\n`;
        leads.forEach((l, idx) => {
          msg += `<b>${idx+1}️⃣ ${l.displayName}</b> — Score: ${l.leadScore}\n`;
          msg += `   Lần cuối: ${l.lastContact.split('T')[0]}\n`;
          msg += `   SĐT: ${l.phone || 'Chưa cung cấp'}\n`;
          msg += `   Tags: ${(l.tags || []).join(', ') || 'None'}\n\n`;
        });
        msg += `💡 <i>Sếp có thể chủ động nhắn tin Zalo cho các lead này để tăng tỷ lệ chốt sale! (Bot KHÔNG tự động gửi tin cho các lead này)</i>`;
        
        await sendConnectionAlert(api, { botName: 'Anh Cường (Follow Up)', errorMsg: msg });
      }
      
      sessionData.sent = true;
      writeFileSync(sessionFile, JSON.stringify(sessionData));
    } catch(err) {
      logger.error('❌ Failed Follow Up Engine', { error: err.message });
    } finally {
      setTimeout(() => { isFollowUpRunning = false; }, 65000);
    }
  }, { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });

  // ── SKILL 02: Existing Contact Nurturing ────────────────
  let isPersonalNurturingRunning = false;
  cron.schedule('0 9 * * *', async () => {
    if (isPersonalNurturingRunning) return;
    const sessionFile = path.join(__dirname, '../data/personal_nurture_session.json');
    const todayStr = new Date().toISOString().split('T')[0];
    let sessionData = {};
    if (existsSync(sessionFile)) {
      try { sessionData = JSON.parse(readFileSync(sessionFile, 'utf8')); } catch(e){}
    }
    if (sessionData.date === todayStr && sessionData.sent) return;
    if (Date.now() - (sessionData.lastRunAt || 0) < 65000) return;
    
    sessionData = { date: todayStr, sent: false, lastRunAt: Date.now() };
    writeFileSync(sessionFile, JSON.stringify(sessionData));
    isPersonalNurturingRunning = true;

    try {
      logger.info('⏰ Running Personal Nurturing (Skill 02)...');
      const allUsers = Object.values(dataStore.users);
      const now = Date.now();
      
      const targets = allUsers.filter(u => {
        if (!u.lastContact || (u.leadScore || 0) === 0 || (u.tags || []).includes('Spam')) return false;
        const lastContactTime = new Date(u.lastContact).getTime();
        const daysSinceContact = (now - lastContactTime) / (1000 * 3600 * 24);
        
        const lastNurturedTime = u.lastNurtured ? new Date(u.lastNurtured).getTime() : 0;
        const daysSinceNurture = (now - lastNurturedTime) / (1000 * 3600 * 24);
        
        return daysSinceContact >= 7 && daysSinceNurture >= 30;
      });

      const selected = targets.slice(0, 3);
      if (selected.length > 0) {
        logger.info(`Sending nurturing to ${selected.length} users...`);
        for (let i = 0; i < selected.length; i++) {
          const u = selected[i];
          const templates = [
            `Chào ${u.displayName}, lâu rồi không gặp! 😊\nEm vừa cập nhật thêm tài liệu mới về Trading và Doanh nghiệp 1 người. Nếu quan tâm, anh/chị nhắn em chia sẻ thêm nhé!`,
            `Chào ${u.displayName}, dạo này công việc và trading của anh/chị thế nào rồi ạ? 📈\nNếu cần hỗ trợ gì, cứ nhắn em nhé!`,
            `Chào ${u.displayName}! Bot tín hiệu bên em vừa có các cập nhật mới cực kỳ hay. Anh/chị muốn em giới thiệu qua không ạ? 🤖`
          ];
          const msg = templates[i % templates.length];
          
          await api.sendMessage(msg, u.id);
          dataStore.setNurtured(u.id);
          logger.info(`✅ Nurtured ${u.displayName} (${u.id})`);
          
          if (i < selected.length - 1) {
            await new Promise(res => setTimeout(res, 5 * 60 * 1000));
          }
        }
      }
      
      sessionData.sent = true;
      writeFileSync(sessionFile, JSON.stringify(sessionData));
    } catch(err) {
      logger.error('❌ Failed Personal Nurturing', { error: err.message });
    } finally {
      setTimeout(() => { isPersonalNurturingRunning = false; }, 65000);
    }
  }, { scheduled: true, timezone: "Asia/Ho_Chi_Minh" });


  console.log('\n╔══════════════════════════════════════════════════════════╗');
  console.log('║       🎉 BOT IS RUNNING!                                 ║');
  console.log('╠══════════════════════════════════════════════════════════╣');
  console.log(`║  AI Provider:  ${config.ai.provider.padEnd(39)}║`);
  console.log(`║  Rate Limit:   ${config.rateLimit.maxMessagesPerMinute} msg/min                             ║`);
  console.log(`║  Reply Delay:  ${config.rateLimit.minDelay}-${config.rateLimit.maxDelay}ms                            ║`);
  console.log('║                                                          ║');
  console.log('║  Commands: #menu #khoa_hoc #phan_tich #tu_van #faq       ║');
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
