import axios from 'axios';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { exec } from 'child_process';
import util from 'util';
import ffmpegInstaller from '@ffmpeg-installer/ffmpeg';
import * as googleTTS from 'google-tts-api';
import { EdgeTTS } from 'node-edge-tts';
import config from './config.js';
import logger from './logger.js';
import { OpenAI } from 'openai';
import { bgmBase64 } from './bgm-base64.js';

let localConfig = {};
try {
  const configPath = path.resolve(process.cwd(), 'config.json');
  if (fs.existsSync(configPath)) {
    localConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  }
} catch (e) {
  logger.warn('Could not load local config.json fallback');
}

async function getDynamicConfig() {
  try {
    const supabaseUrl = process.env.SUPABASE_URL || 'https://sxxixhpspsvzzrskpjjy.supabase.co';
    const configUrl = `${supabaseUrl}/storage/v1/object/public/zalo-bot-state/bich/config.json`;
    const response = await axios.get(`${configUrl}?t=${Date.now()}`, { timeout: 3000 });
    return response.data;
  } catch (err) {
    return localConfig;
  }
}

const execPromise = util.promisify(exec);

const assetsDir = path.join(process.cwd(), 'assets');
if (!fs.existsSync(assetsDir)) {
  fs.mkdirSync(assetsDir, { recursive: true });
}
const bgmPath = path.join(assetsDir, 'cinematic-bgm.mp3');
if (!fs.existsSync(bgmPath)) {
  logger.info('Khôi phục cinematic-bgm.mp3 từ Base64...');
  fs.writeFileSync(bgmPath, Buffer.from(bgmBase64, 'base64'));
}

/**
 * 1. Sinh kịch bản bằng AI
 */
async function generateScriptAndSEO(prompt) {
  logger.info('🧠 Đang lên kịch bản đa cảnh và chuẩn bị SEO...');
  let systemPrompt = `Bạn là một Đạo diễn Video xuất sắc. Nhiệm vụ của bạn là nhận chủ đề từ người dùng và trả về một kịch bản hoàn chỉnh chia thành nhiều phân cảnh (scenes) kèm metadata SEO.

Tùy bối cảnh, hãy xác định xem video nên là màn hình ngang (horizontal - dài) hay dọc (vertical - short).

Trọng tâm:
- Phải chuẩn SEO YouTube.
- Kịch bản đọc (script) bắt buộc phải đủ dài (tối thiểu 100 đến 150 từ tổng cộng). Hãy chia đều vào 3 đến 6 phân cảnh (scenes).
- Mỗi phân cảnh sẽ có 1 câu thoại và 1 broll_query.
- Phải trả về JSON DUY NHẤT (không có markdown).
Cấu trúc JSON:
{
  "seo": {
    "title": "Tiêu đề video (dưới 60 ký tự)",
    "description": "Mô tả video chứa từ khóa chính",
    "tags": ["tag1", "tag2"],
    "filename": "ten-file.mp4"
  },
  "format": "horizontal" | "vertical",
  "scenes": [
    {
      "text": "Câu thoại của phân cảnh này (đọc mất khoảng 3-5 giây).",
      "broll_query": "Một từ khóa tiếng Anh ĐƠN GIẢN NHẤT tìm video nền khớp với câu thoại. (CHỈ 1 HOẶC 2 TỪ, KHÔNG DÙNG DẤU PHẨY. Ví dụ: 'nature', 'business', 'ocean')"
    }
  ]
}`;

  const dynamicConfig = await getDynamicConfig();
  if (dynamicConfig && dynamicConfig.videoPrompt) {
    systemPrompt = dynamicConfig.videoPrompt;
  }

  const apiKey = config.ai.geminiApiKey;
  if (!apiKey) throw new Error('GEMINI_API_KEY not configured');
  const model = config.ai.geminiModel || 'gemini-1.5-flash';
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

  const response = await axios.post(url, {
    system_instruction: { parts: [{ text: systemPrompt }] },
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.7 },
  }, {
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,
  });

  let content = response.data.candidates[0].content.parts[0].text.trim();
  content = content.replace(/^```json/, '').replace(/^```/, '').replace(/```$/, '');
  
  try {
    return JSON.parse(content);
  } catch (e) {
    logger.warn('JSON parse failed, attempting to sanitize string: ' + e.message);
    // Thay thế tất cả ký tự điều khiển (xuống dòng, tab) thành khoảng trắng để parse không bị lỗi
    let sanitized = content.replace(/[\n\r\t]/g, ' ');
    return JSON.parse(sanitized);
  }
}

/**
 * 2. Tạo Audio bằng Microsoft Edge TTS (Miễn phí, Giọng Nam Miền Tây)
 * Cập nhật: Cắt nhỏ câu để tránh lỗi Timeout của EdgeTTS với đoạn text quá dài.
 */
async function generateAudio(text, outputPath) {
  logger.info('🎙️ Đang tạo Audio (Microsoft Edge TTS - Giọng Nam Miền Tây - NamMinh)...');
  try {
    // Tách text thành các câu nhỏ dựa trên dấu chấm, phẩy, chấm hỏi, chấm than để tránh Timeout
    const sentences = text.split(/[,.!?;\n]+/).filter(s => s.trim().length > 0);
    const chunkFiles = [];
    const tempDir = path.dirname(outputPath);
    const sessionId = path.basename(outputPath, '.mp3').split('_')[1] || 'temp';

    for (let i = 0; i < sentences.length; i++) {
      const sentence = sentences[i].trim();
      if (!sentence) continue;
      const tts = new EdgeTTS({
        voice: 'vi-VN-HoaiMyNeural', // Giọng Nữ ấm áp
        lang: 'vi-VN'
      });
      const chunkPath = path.join(tempDir, `chunk_${sessionId}_${i}.mp3`);
      
      // Thêm timeout 30s cho TTS để tránh treo vĩnh viễn
      await Promise.race([
        tts.ttsPromise(sentence, chunkPath),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Edge TTS Timeout')), 30000))
      ]);
      
      chunkFiles.push(chunkPath);
    }

    if (chunkFiles.length === 1) {
      // Nếu chỉ có 1 chunk thì đổi tên luôn
      fs.renameSync(chunkFiles[0], outputPath);
    } else if (chunkFiles.length > 1) {
      // Ghép nối các file mp3 lại bằng FFmpeg
      const concatListPath = path.join(tempDir, `concat_${sessionId}.txt`);
      // Lưu ý: định dạng file list của FFmpeg cần dùng escape đúng chuẩn
      const concatContent = chunkFiles.map(f => `file '${path.basename(f)}'`).join('\n');
      fs.writeFileSync(concatListPath, concatContent);

      const ffmpegPath = ffmpegInstaller.path;
      // Dạy ffmpeg chạy ở thư mục tempDir để dễ parse tên file
      const cmd = `"${ffmpegPath}" -y -f concat -safe 0 -i "${path.basename(concatListPath)}" -c copy "${path.basename(outputPath)}"`;
      
      await execPromise(cmd, { cwd: tempDir, maxBuffer: 1024 * 1024 * 50 });

      // Clean up chunk files
      chunkFiles.forEach(f => { if (fs.existsSync(f)) fs.unlinkSync(f); });
      if (fs.existsSync(concatListPath)) fs.unlinkSync(concatListPath);
    }
    
    logger.info('✅ Đã lưu Audio: ' + outputPath);
  } catch (error) {
    logger.error('Lỗi Edge TTS', error);
    throw new Error('Không thể tạo Audio miễn phí.');
  }
}

/**
 * 3. Tải B-roll từ Pexels (Free, Không cần Visa)
 */
async function downloadBroll(query, format, outputPath, isRetry = false) {
  query = (query || "abstract").toString().trim();
  if (!query) query = "abstract";
  
  logger.info(`🎥 Đang tìm B-roll trên Pexels (Free) cho từ khóa: ${query}...`);
  if (!config.videoCreator.pexelsApiKey) {
    throw new Error('Chưa cấu hình Pexels API Key trong config.js. API này tạo miễn phí tại pexels.com/api');
  }

  const orientation = format === 'vertical' ? 'portrait' : 'landscape';
  try {
    const res = await axios.get(`https://api.pexels.com/videos/search`, {
      params: { query, orientation, per_page: 1 },
      headers: { Authorization: config.videoCreator.pexelsApiKey }
    });

    if (res.data.videos && res.data.videos.length > 0) {
      const videoFile = res.data.videos[0].video_files.find(f => f.quality === 'hd') || res.data.videos[0].video_files[0];
      const videoUrl = videoFile.link;
      
      logger.info('📥 Đang tải video B-roll...');
      const response = await axios({
        url: videoUrl,
        method: 'GET',
        responseType: 'stream',
        timeout: 60000 // 60s timeout
      });

      const writeStream = fs.createWriteStream(outputPath);
      response.data.pipe(writeStream);
      await new Promise((resolve, reject) => {
        writeStream.on('finish', resolve);
        writeStream.on('error', reject);
        response.data.on('error', reject);
        // Timeout 2 phút cho việc tải broll
        setTimeout(() => reject(new Error('Pexels Download Timeout')), 120000);
      });
      logger.info('✅ Đã lưu Video B-roll: ' + outputPath);
    } else {
      if (!isRetry) {
        logger.warn(`Không tìm thấy B-roll cho "${query}". Thử lại với từ khóa mặc định...`);
        return downloadBroll("abstract", format, outputPath, true);
      }
      throw new Error('Không tìm thấy video nào trên Pexels.');
    }
  } catch (error) {
    logger.error('Lỗi Pexels', error);
    if (error.message === 'Không tìm thấy video nào trên Pexels.') {
      throw error;
    }
    throw new Error('Không thể tải B-roll từ Pexels: ' + (error.response?.data?.error || error.message));
  }
}

/**
 * 4. Lắp ráp Video bằng FFmpeg cục bộ (100% Free)
 */
async function getAudioDuration(audioPath) {
  const ffmpegPath = ffmpegInstaller.path;
  try {
    await execPromise(`"${ffmpegPath}" -i "${audioPath}"`);
  } catch (error) {
    if (error.stderr) {
      const match = error.stderr.match(/Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})/);
      if (match) {
        const hours = parseInt(match[1], 10);
        const minutes = parseInt(match[2], 10);
        const seconds = parseInt(match[3], 10);
        const ms = parseInt(match[4], 10);
        return hours * 3600 + minutes * 60 + seconds + ms / 100;
      }
    }
  }
  return 30; // Mặc định 30 giây nếu không lấy được
}

async function processScene(scene, index, format, tempDir, sessionId) {
  logger.info(`🎬 Đang xử lý Phân cảnh ${index + 1}...`);
  const audioPath = path.join(tempDir, `scene_audio_${sessionId}_${index}.mp3`);
  const rawVideoPath = path.join(tempDir, `scene_rawvideo_${sessionId}_${index}.mp4`);
  const processedVideoPath = path.join(tempDir, `scene_video_${sessionId}_${index}.mp4`);
  
  // 1. Tạo Audio cho phân cảnh
  await generateAudio(scene.text, audioPath);
  
  // 2. Đo thời lượng
  const duration = await getAudioDuration(audioPath);
  
  // 3. Tải B-roll
  await downloadBroll(scene.broll_query, format, rawVideoPath);
  
  // 4. Chuẩn hóa & Cắt/Lặp video khớp thời lượng audio
  const scaleFilter = format === 'vertical' 
    ? 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1' 
    : 'scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1';
    
  const ffmpegPath = ffmpegInstaller.path;
  const cmd = `"${ffmpegPath}" -y -stream_loop -1 -i "${rawVideoPath}" -vf "${scaleFilter},fps=30,format=yuv420p" -c:v libx264 -preset ultrafast -t ${duration} -an "${processedVideoPath}"`;
  
  // Timeout 5 phút cho FFmpeg (phân cảnh thường rất ngắn)
  await execPromise(cmd, { maxBuffer: 1024 * 1024 * 50, timeout: 300000 });
  
  // Xóa video thô
  if (fs.existsSync(rawVideoPath)) fs.unlinkSync(rawVideoPath);
  
  return { audio: audioPath, video: processedVideoPath };
}

/**
 * Hàm Orchestrator Đa Cảnh
 */
export async function createYouTubeVideo(prompt) {
  const sessionId = crypto.randomBytes(4).toString('hex');
  const tempDir = path.join(process.cwd(), 'scratch', 'video_temps');
  if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });

  const finalPath = path.join(tempDir, `final_${sessionId}.mp4`);
  let segments = [];

  try {
    // 1. Sinh kịch bản Đa cảnh
    const scriptData = await generateScriptAndSEO(prompt);
    
    // 2. Xử lý từng phân cảnh tuần tự để không làm quá tải CPU
    for (let i = 0; i < scriptData.scenes.length; i++) {
      const seg = await processScene(scriptData.scenes[i], i, scriptData.format, tempDir, sessionId);
      segments.push(seg);
    }
    
    // 3. Ghép tất cả các đoạn video và audio lại
    const concatVideoList = path.join(tempDir, `concat_video_${sessionId}.txt`);
    const concatAudioList = path.join(tempDir, `concat_audio_${sessionId}.txt`);
    
    fs.writeFileSync(concatVideoList, segments.map(s => `file '${path.basename(s.video)}'`).join('\n'));
    fs.writeFileSync(concatAudioList, segments.map(s => `file '${path.basename(s.audio)}'`).join('\n'));
    
    const mergedVideoPath = path.join(tempDir, `merged_video_${sessionId}.mp4`);
    const mergedAudioPath = path.join(tempDir, `merged_audio_${sessionId}.mp3`);
    
    const ffmpegPath = ffmpegInstaller.path;
    await execPromise(`"${ffmpegPath}" -y -f concat -safe 0 -i "${path.basename(concatVideoList)}" -c copy "${path.basename(mergedVideoPath)}"`, { cwd: tempDir, maxBuffer: 1024 * 1024 * 50, timeout: 300000 });
    await execPromise(`"${ffmpegPath}" -y -f concat -safe 0 -i "${path.basename(concatAudioList)}" -c copy "${path.basename(mergedAudioPath)}"`, { cwd: tempDir, maxBuffer: 1024 * 1024 * 50, timeout: 120000 });
    
    // 4. Mix cuối cùng với Nhạc nền (Audio Ducking)
    const bgmPath = path.join(process.cwd(), 'assets', 'cinematic-bgm.mp3');
    // -c:v copy an toàn vì merged_video đã được chuẩn hóa x264 trước đó
    const finalCmd = `"${ffmpegPath}" -y -i "${mergedVideoPath}" -i "${mergedAudioPath}" -stream_loop -1 -i "${bgmPath}" -filter_complex "[1:a]volume=1.0[a1]; [2:a]volume=0.15[a2]; [a1][a2]amix=inputs=2:duration=first[a]" -map 0:v:0 -map "[a]" -c:v copy -c:a aac "${finalPath}"`;
    await execPromise(finalCmd, { maxBuffer: 1024 * 1024 * 50, timeout: 300000 });

    // 5. Dọn dẹp File Rác
    segments.forEach(s => {
      if (fs.existsSync(s.audio)) fs.unlinkSync(s.audio);
      if (fs.existsSync(s.video)) fs.unlinkSync(s.video);
    });
    if (fs.existsSync(concatVideoList)) fs.unlinkSync(concatVideoList);
    if (fs.existsSync(concatAudioList)) fs.unlinkSync(concatAudioList);
    if (fs.existsSync(mergedVideoPath)) fs.unlinkSync(mergedVideoPath);
    if (fs.existsSync(mergedAudioPath)) fs.unlinkSync(mergedAudioPath);

    return {
      success: true,
      videoPath: finalPath,
      seo: scriptData.seo
    };
  } catch (error) {
    logger.error('Lỗi hệ thống Video Đa cảnh', error);
    // Dọn dẹp khẩn cấp
    segments.forEach(s => {
      if (fs.existsSync(s.audio)) fs.unlinkSync(s.audio);
      if (fs.existsSync(s.video)) fs.unlinkSync(s.video);
    });
    if (fs.existsSync(finalPath)) fs.unlinkSync(finalPath);
    return { success: false, error: error.message };
  }
}
