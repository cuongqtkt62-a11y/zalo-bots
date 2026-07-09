// ============================================================
// data-store.js — JSON-based Data Store (thay thế PostgreSQL)
// ============================================================
// Lưu trữ đơn giản bằng JSON files, không cần database server.
// Phù hợp cho giai đoạn 1 (Zalo cá nhân, lượng nhỏ).
// Khi scale lên Zalo OA → chuyển sang PostgreSQL.
// ============================================================

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import logger from './logger.js';

const DATA_DIR = './data';

class DataStore {
  constructor() {
    // Đảm bảo thư mục data tồn tại
    if (!existsSync(DATA_DIR)) {
      mkdirSync(DATA_DIR, { recursive: true });
    }

    this.usersFile = join(DATA_DIR, 'users.json');
    this.messagesFile = join(DATA_DIR, 'messages.json');
    this.conversationsFile = join(DATA_DIR, 'conversations.json');
    this.statsFile = join(DATA_DIR, 'stats.json');
    this.approvedGroupsFile = join(DATA_DIR, 'approved_groups.json');
    this.nurturingHistoryFile = join(DATA_DIR, 'nurturing_history.json');
    this.processedMsgIdsFile = join(DATA_DIR, 'processed_msg_ids.json');

    // Cờ báo hiệu liệu file processed_msg_ids có tồn tại trên đĩa cứng không (tức là không phải Docker Rebuild)
    this.hasPersistentMsgIds = existsSync(this.processedMsgIdsFile);

    // Load hoặc khởi tạo data
    this.users = this._load(this.usersFile, {});
    this.messages = this._load(this.messagesFile, []);
    this.conversations = this._load(this.conversationsFile, {});
    this.approvedGroups = this._load(this.approvedGroupsFile, []);
    this.nurturingHistory = this._load(this.nurturingHistoryFile, []);
    
    const msgIdArray = this._load(this.processedMsgIdsFile, []);
    this.processedMsgIds = new Set(msgIdArray);

    this.stats = this._load(this.statsFile, {
      totalMessages: 0,
      totalUsers: 0,
      startDate: new Date().toISOString(),
    });

    // Backfill greetingStep for existing users on startup
    let needsSave = false;
    for (const userId of Object.keys(this.users)) {
      if (this.users[userId].greetingStep === undefined) {
        const sent = (this.messages || []).filter(m => m.userId === userId && m.direction === 'outgoing');
        let step = 0;
        if (sent.some(m => m.content.includes('Thông tin lớp học bên dưới') || m.content.includes('Link học bên dưới'))) {
          step = 3;
        } else if (sent.some(m => m.content.includes('muốn tìm hiểu thêm thông tin gì cứ nhắn em'))) {
          step = 2;
        } else if (sent.some(m => m.content.includes('Em là trợ lý của anh Cường'))) {
          step = 1;
        }
        this.users[userId].greetingStep = step;
        needsSave = true;
      }
    }
    if (needsSave) {
      this._saveAll();
    }

    // Auto-save mỗi 30 giây
    setInterval(() => this._saveAll(), 30000);
  }

  // ── Deduplication Cache Management ─────────────────────
  
  isMsgProcessed(msgId) {
    return this.processedMsgIds.has(msgId);
  }

  markMsgProcessed(msgId) {
    this.processedMsgIds.add(msgId);
    if (this.processedMsgIds.size > 1000) {
      const iter = this.processedMsgIds.values();
      this.processedMsgIds.delete(iter.next().value);
    }
  }

  hasPersistentCache() {
    return this.hasPersistentMsgIds;
  }

  // ── User Management ────────────────────────────────────

  upsertUser(userId, displayName = null) {
    if (!this.users[userId]) {
      // Backfill greetingStep from sent messages if any exist
      const sent = (this.messages || []).filter(m => m.userId === userId && m.direction === 'outgoing');
      let step = 0;
      if (sent.some(m => m.content.includes('Thông tin lớp học bên dưới') || m.content.includes('Link học bên dưới'))) {
        step = 3;
      } else if (sent.some(m => m.content.includes('muốn tìm hiểu thêm thông tin gì cứ nhắn em'))) {
        step = 2;
      } else if (sent.some(m => m.content.includes('Em là trợ lý của anh Cường'))) {
        step = 1;
      }

      this.users[userId] = {
        id: userId,
        displayName: displayName || 'Unknown',
        firstContact: new Date().toISOString(),
        lastContact: new Date().toISOString(),
        messageCount: 0,
        leadScore: 0,
        leadNotes: [],
        tags: [],
        greetingStep: step,
      };
      this.stats.totalUsers++;
      logger.info('👤 New user tracked', { userId, displayName, greetingStep: step });
    } else {
      if (displayName) this.users[userId].displayName = displayName;
      this.users[userId].lastContact = new Date().toISOString();
      
      // Ensure greetingStep is backfilled if not present
      if (this.users[userId].greetingStep === undefined) {
        const sent = (this.messages || []).filter(m => m.userId === userId && m.direction === 'outgoing');
        let step = 0;
        if (sent.some(m => m.content.includes('Thông tin lớp học bên dưới') || m.content.includes('Link học bên dưới'))) {
          step = 3;
        } else if (sent.some(m => m.content.includes('muốn tìm hiểu thêm thông tin gì cứ nhắn em'))) {
          step = 2;
        } else if (sent.some(m => m.content.includes('Em là trợ lý của anh Cường'))) {
          step = 1;
        }
        this.users[userId].greetingStep = step;
      }
    }
    this.users[userId].messageCount++;
    return this.users[userId];
  }

  setGreetingStep(userId, step) {
    if (this.users[userId]) {
      this.users[userId].greetingStep = step;
      this._saveAll(); // Save instantly to prevent data loss
      logger.debug('💾 Instant saved greetingStep', { userId, step });
    }
  }

  getUser(userId) {
    return this.users[userId] || null;
  }

  updateLeadScore(userId, scoreChange, reason) {
    if (!this.users[userId]) return;
    this.users[userId].leadScore = (this.users[userId].leadScore || 0) + scoreChange;
    this.users[userId].leadNotes.push({
      date: new Date().toISOString(),
      change: scoreChange,
      reason,
    });
    logger.debug('🎯 Lead score updated', {
      userId,
      newScore: this.users[userId].leadScore,
      reason,
    });
  }

  getTopLeads(limit = 10) {
    return Object.values(this.users)
      .sort((a, b) => (b.leadScore || 0) - (a.leadScore || 0))
      .slice(0, limit);
  }

  // ── Message Logging ────────────────────────────────────

  logMessage(userId, direction, content, messageType = 'text') {
    const entry = {
      userId,
      direction, // 'incoming' | 'outgoing'
      content: content.substring(0, 500), // Giới hạn lưu
      messageType,
      timestamp: new Date().toISOString(),
    };

    this.messages.push(entry);
    this.stats.totalMessages++;

    // Giữ tối đa 10000 messages (tránh file quá lớn)
    if (this.messages.length > 10000) {
      this.messages = this.messages.slice(-5000);
    }
  }

  // ── Conversation History (cho AI context) ──────────────

  getConversationHistory(userId) {
    return this.conversations[userId] || [];
  }

  addToConversation(userId, role, content) {
    if (!this.conversations[userId]) {
      this.conversations[userId] = [];
    }
    this.conversations[userId].push({ role, content });

    // Giữ tối đa 10 tin nhắn gần nhất
    if (this.conversations[userId].length > 10) {
      this.conversations[userId] = this.conversations[userId].slice(-10);
    }
  }

  clearConversation(userId) {
    delete this.conversations[userId];
  }

  // ── Statistics ─────────────────────────────────────────

  getDailyStats() {
    const today = new Date().toISOString().split('T')[0];
    const todayMessages = this.messages.filter(m =>
      m.timestamp.startsWith(today)
    );

    const uniqueUsers = new Set(todayMessages.map(m => m.userId)).size;
    const incoming = todayMessages.filter(m => m.direction === 'incoming').length;
    const outgoing = todayMessages.filter(m => m.direction === 'outgoing').length;

    return {
      date: today,
      uniqueUsers,
      totalMessages: todayMessages.length,
      incoming,
      outgoing,
      totalUsersAllTime: Object.keys(this.users).length,
      totalMessagesAllTime: this.stats.totalMessages,
    };
  }

  approveGroup(groupId, name = 'Group Chat', purpose = 'Chia sẻ kiến thức, thảo luận về Kinh Doanh và Đầu Tư Thong Dong cùng anh Cường.') {
    if (!this.approvedGroups) {
      this.approvedGroups = [];
    }
    const index = this.approvedGroups.findIndex(g => (typeof g === 'string' && g === groupId) || (g && g.id === groupId));
    const groupData = {
      id: groupId,
      name: name || 'Group Chat',
      purpose: purpose || 'Chia sẻ kiến thức, thảo luận về Kinh Doanh và Đầu Tư Thong Dong cùng anh Cường.',
      approvedAt: new Date().toISOString()
    };
    if (index === -1) {
      this.approvedGroups.push(groupData);
    } else {
      const oldGroup = this.approvedGroups[index];
      const oldPurpose = typeof oldGroup === 'string' ? null : oldGroup?.purpose;
      groupData.purpose = purpose || oldPurpose || 'Chia sẻ kiến thức, thảo luận về Kinh Doanh và Đầu Tư Thong Dong cùng anh Cường.';
      this.approvedGroups[index] = groupData;
    }
    this._saveAll();
    logger.info('👥 Group approved/updated in dataStore', { groupId, name: groupData.name, purpose: groupData.purpose });
  }

  isGroupApproved(groupId) {
    if (!this.approvedGroups) return false;
    return this.approvedGroups.some(g => (typeof g === 'string' && g === groupId) || (g && g.id === groupId));
  }

  getApprovedGroup(groupId) {
    if (!this.approvedGroups) return null;
    const group = this.approvedGroups.find(g => (typeof g === 'string' && g === groupId) || (g && g.id === groupId));
    if (!group) return null;
    if (typeof group === 'string') {
      return { id: group, name: 'Group Chat', purpose: 'Chia sẻ kiến thức, thảo luận về Kinh Doanh và Đầu Tư Thong Dong cùng anh Cường.' };
    }
    return group;
  }

  getApprovedGroups() {
    if (!this.approvedGroups) return [];
    return this.approvedGroups.map(g => {
      if (typeof g === 'string') {
        return { id: g, name: 'Group Chat', purpose: 'Chia sẻ kiến thức, thảo luận về Kinh Doanh và Đầu Tư Thong Dong cùng anh Cường.' };
      }
      return g;
    });
  }

  // ── Persistence ────────────────────────────────────────

  _load(filePath, defaultValue) {
    try {
      if (existsSync(filePath)) {
        const raw = readFileSync(filePath, 'utf-8');
        return JSON.parse(raw);
      }
    } catch (error) {
      logger.warn(`Failed to load ${filePath}, using default`, { error: error.message });
    }
    return defaultValue;
  }

  _save(filePath, data) {
    try {
      writeFileSync(filePath, JSON.stringify(data, null, 2));
    } catch (error) {
      logger.error(`Failed to save ${filePath}`, { error: error.message });
    }
  }

  _saveAll() {
    this._save(this.usersFile, this.users);
    this._save(this.messagesFile, this.messages);
    this._save(this.conversationsFile, this.conversations);
    this._save(this.statsFile, this.stats);
    this._save(this.approvedGroupsFile, this.approvedGroups);
    this._save(this.nurturingHistoryFile, this.nurturingHistory);
    this._save(this.processedMsgIdsFile, Array.from(this.processedMsgIds));
  }

  // ── Nurturing Post History (chống trùng nội dung) ─────

  logNurturingPost(groupId, post, quote, timeOfDay) {
    this.nurturingHistory.push({
      groupId,
      post: post.substring(0, 200), // Lưu 200 ký tự đầu để so sánh
      quote,
      timeOfDay,
      date: new Date().toISOString().split('T')[0],
      timestamp: new Date().toISOString(),
    });

    // Giữ tối đa 100 bài gần nhất
    if (this.nurturingHistory.length > 100) {
      this.nurturingHistory = this.nurturingHistory.slice(-100);
    }
  }

  getRecentNurturingPosts(groupId, limit = 10) {
    return this.nurturingHistory
      .filter(p => p.groupId === groupId)
      .slice(-limit);
  }

  // Gọi khi shutdown
  close() {
    this._saveAll();
    logger.info('💾 Data saved to disk');
  }
}

export default new DataStore();
