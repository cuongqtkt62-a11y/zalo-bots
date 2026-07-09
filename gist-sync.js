import { existsSync, writeFileSync, mkdirSync, readFileSync } from 'fs';
import { dirname } from 'path';
import crypto from 'crypto';
import 'dotenv/config';

const gistToken = process.env.GITHUB_GIST_TOKEN;
const GIST_DESC = '[Zalo Bot State] DO NOT DELETE';

if (!gistToken) {
  console.warn('⚠️ CẢNH BÁO: Thiếu GITHUB_GIST_TOKEN. Tính năng đồng bộ Cloud sẽ bị vô hiệu hóa.');
}

const filesToSync = [
  // Bích Bot dynamic state
  { local: './bich-bot/zalo-credentials.json', remote: 'bich_zalo-credentials.json' },
  { local: './bich-bot/data/users.json', remote: 'bich_users.json' },
  { local: './bich-bot/data/approved_groups.json', remote: 'bich_approved_groups.json' },
  { local: './bich-bot/data/nurturing_history.json', remote: 'bich_nurturing_history.json' },

  // Cường Bot dynamic state
  { local: './cuong-bot/zalo-credentials-cuong.json', remote: 'cuong_zalo-credentials-cuong.json' },
  { local: './cuong-bot/data/users.json', remote: 'cuong_users.json' },
  { local: './cuong-bot/data/approved_groups.json', remote: 'cuong_approved_groups.json' },
  { local: './cuong-bot/data/nurturing_history.json', remote: 'cuong_nurturing_history.json' },
  { local: './cuong-bot/data/order_monitor_state.json', remote: 'cuong_order_monitor_state.json' }
];

const lastHashes = {};

function getFileHash(filePath) {
  if (!existsSync(filePath)) return null;
  try {
    const content = readFileSync(filePath);
    return crypto.createHash('md5').update(content).digest('hex');
  } catch (err) {
    return null;
  }
}

// 1. Tự động tìm hoặc tạo Gist
async function getOrCreateGist() {
  if (!gistToken) return null;
  const headers = {
    'Authorization': `Bearer ${gistToken}`,
    'Accept': 'application/vnd.github.v3+json',
    'X-GitHub-Api-Version': '2022-11-28'
  };

  try {
    // Tìm Gist
    const res = await fetch('https://api.github.com/gists', { headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const gists = await res.json();
    const existing = gists.find(g => g.description === GIST_DESC);
    
    if (existing) {
      console.log(`✅ Tìm thấy Gist lưu trữ: ${existing.id}`);
      return existing.id;
    }

    // Không có thì tạo mới
    console.log('🚀 Đang tạo Gist lưu trữ mới...');
    const createRes = await fetch('https://api.github.com/gists', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        description: GIST_DESC,
        public: false,
        files: {
          "README.md": { content: "Nơi lưu trữ trạng thái của Zalo Bot. Tuyệt đối không xóa!" }
        }
      })
    });
    const created = await createRes.json();
    console.log(`✅ Đã tạo Gist mới: ${created.id}`);
    return created.id;
  } catch (err) {
    console.error('❌ Lỗi khi tìm/tạo Gist:', err.message);
    return null;
  }
}

async function downloadFiles() {
  const gistId = await getOrCreateGist();
  if (!gistId) return;

  console.log('🔄 Downloading state files from GitHub Gist...');
  try {
    const res = await fetch(`https://api.github.com/gists/${gistId}`, {
      headers: { 'Authorization': `Bearer ${gistToken}` }
    });
    const gist = await res.json();

    for (const item of filesToSync) {
      const fileData = gist.files[item.remote];
      if (fileData && fileData.content) {
        const dir = dirname(item.local);
        if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
        writeFileSync(item.local, fileData.content);
        lastHashes[item.local] = getFileHash(item.local);
        console.log(`✅ Downloaded: ${item.remote} -> ${item.local}`);
      }
    }
  } catch (err) {
    console.error(`❌ Failed to download from Gist:`, err.message);
  }
}

async function uploadFiles() {
  const gistId = await getOrCreateGist();
  if (!gistId) return;

  const filesToUpdate = {};
  let changed = false;

  for (const item of filesToSync) {
    if (!existsSync(item.local)) continue;
    
    const currentHash = getFileHash(item.local);
    if (lastHashes[item.local] === currentHash) continue; // Bỏ qua nếu không đổi

    try {
      const content = readFileSync(item.local, 'utf-8');
      filesToUpdate[item.remote] = { content };
      lastHashes[item.local] = currentHash;
      changed = true;
      console.log(`📤 Chuẩn bị upload: ${item.local}`);
    } catch (err) {
      console.error(`❌ Failed to read ${item.local}:`, err.message);
    }
  }

  if (changed) {
    try {
      const res = await fetch(`https://api.github.com/gists/${gistId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${gistToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ files: filesToUpdate })
      });
      if (res.ok) {
        console.log(`🎉 Đã đồng bộ ${Object.keys(filesToUpdate).length} file lên Gist thành công!`);
      } else {
        console.error(`❌ Lỗi upload Gist (HTTP ${res.status}):`, await res.text());
      }
    } catch (err) {
      console.error(`❌ Lỗi kết nối khi upload Gist:`, err.message);
    }
  }
}

async function watchLoop() {
  console.log('👀 Starting periodic Gist sync watcher (every 30 seconds)...');
  
  try {
    await uploadFiles();
  } catch (err) {
    console.error('❌ Error during initial Gist upload sync:', err.message);
  }

  while (true) {
    try {
      await uploadFiles();
    } catch (err) {
      console.error('❌ Error during background Gist upload sync:', err.message);
    }
    await new Promise(resolve => setTimeout(resolve, 30000));
  }
}

const command = process.argv[2];
if (command === 'download') {
  downloadFiles();
} else if (command === 'upload') {
  uploadFiles();
} else if (command === 'watch') {
  watchLoop();
} else {
  console.log('Usage: node gist-sync.js [download|upload|watch]');
  process.exit(1);
}
