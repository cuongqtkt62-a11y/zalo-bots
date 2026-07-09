// ============================================================
// image-generator.js — Dynamic Quote Card Generator
// ============================================================
// Module này tạo hình ảnh Quote/Tip Card tự động dưới dạng PNG.
// Hỗ trợ tự động chọn màu nền Gradient theo khung giờ,
// tự động wrap chữ tiếng Việt, và chèn 2 logo của anh Cường.
// ============================================================

import fs from 'fs';
import path from 'path';
import sharp from 'sharp';
import axios from 'axios';
import config from './config.js';
import logger from './logger.js';

/**
 * Escape các ký tự đặc biệt cho SVG XML
 */
function escapeXml(unsafe) {
  if (!unsafe) return '';
  return unsafe.replace(/[<>&'"]/g, (c) => {
    switch (c) {
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '&': return '&amp;';
      case '\'': return '&apos;';
      case '"': return '&quot;';
      default: return c;
    }
  });
}

/**
 * Tự động wrap chữ tiếng Việt theo độ dài dòng chỉ định (giữ nguyên từ)
 */
function wrapText(text, maxCharsPerLine = 38) {
  if (!text) return [];
  const words = text.split(/\s+/);
  const lines = [];
  let currentLine = '';
  
  for (const word of words) {
    if ((currentLine + ' ' + word).trim().length <= maxCharsPerLine) {
      currentLine = (currentLine + ' ' + word).trim();
    } else {
      if (currentLine) lines.push(currentLine);
      currentLine = word;
    }
  }
  if (currentLine) lines.push(currentLine);
  return lines;
}

/**
 * Đọc logo và chuyển đổi thành base64 URI để embed trực tiếp vào SVG.
 * Hỗ trợ các định dạng .png, .jpg, .jpeg, .svg
 */
function getLogoBase64(logoNumber) {
  const extensions = ['.png', '.jpg', '.jpeg', '.svg'];
  const dir = path.join(process.cwd(), 'data', 'logos');
  
  for (const ext of extensions) {
    const filePath = path.join(dir, `logo${logoNumber}${ext}`);
    if (fs.existsSync(filePath)) {
      try {
        const buffer = fs.readFileSync(filePath);
        const mimeType = ext === '.svg' ? 'image/svg+xml' : `image/${ext.substring(1)}`;
        logger.debug(`Loaded logo${logoNumber} from ${filePath}`);
        return `data:${mimeType};base64,${buffer.toString('base64')}`;
      } catch (err) {
        logger.error(`Error reading logo${logoNumber}${ext}`, err);
      }
    }
  }
  return null;
}

/**
 * Sinh hình nền AI bằng mô hình Imagen 4.0 từ Google AI Studio
 * @param {string} groupName - Tên nhóm
 * @param {string} groupPurpose - Mục đích của nhóm
 * @returns {Promise<string|null>} Chuỗi Base64 Data URL của ảnh hoặc null nếu lỗi/không có key
 */
async function generateAiBackground(groupName, groupPurpose) {
  const apiKey = config.ai?.geminiApiKey;
  if (!apiKey) {
    logger.warn('⚠️ GEMINI_API_KEY is not defined in config, skipping AI background generation.');
    return null;
  }

  const normPurpose = ((groupPurpose || '') + ' ' + (groupName || '')).toLowerCase();
  let themeDesc = "abstract geometric gradient and soft lighting";

  if (normPurpose.includes('nhàu') || normPurpose.includes('tâm an') || normPurpose.includes('sức khoẻ') || normPurpose.includes('sức khỏe') || normPurpose.includes('thảo mộc') || normPurpose.includes('mộc')) {
    themeDesc = "organic wellness, fresh green tea, herbal leaves, soft natural lighting, calming zen matcha vibes";
  } else if (normPurpose.includes('trading') || normPurpose.includes('coin') || normPurpose.includes('crypto') || normPurpose.includes('tín hiệu') || normPurpose.includes('đầu tư') || normPurpose.includes('kinh doanh')) {
    themeDesc = "financial technology, deep dark blue business concept, subtle abstract glow lines, minimal digital charting vibes";
  } else if (normPurpose.includes('nhân hiệu') || normPurpose.includes('bích') || normPurpose.includes('phát triển') || normPurpose.includes('sáng tạo') || normPurpose.includes('ai')) {
    themeDesc = "personal growth and creation, soft royal violet and pastel pink background, elegant minimal waves";
  }

  const prompt = `A premium, extremely professional, minimalist and clean abstract background for graphic design. Solid and smooth gradient style, very clean with copy space in the center, no busy details, no text, no people, suitable as a card background for: ${themeDesc}. Aspect ratio 1:1, high quality, 800x800 resolution.`;
  const url = `https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key=${apiKey}`;

  try {
    logger.info('🎨 Requesting AI Background generation from Imagen 4.0...', { theme: themeDesc });
    const response = await axios.post(url, {
      instances: [
        {
          prompt: prompt
        }
      ],
      parameters: {
        sampleCount: 1,
        aspectRatio: '1:1'
      }
    }, {
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 15000 // 15 seconds timeout
    });

    const base64Data = response.data?.predictions?.[0]?.bytesBase64Encoded;
    if (base64Data) {
      logger.info('🎨 AI Background generated successfully from Imagen API.');
      return `data:image/png;base64,${base64Data}`;
    }
    logger.warn('⚠️ API returned response, but bytesBase64Encoded was missing.', response.data);
    return null;
  } catch (err) {
    const errMsg = err.response?.data?.error?.message || err.message;
    logger.warn(`⚠️ Failed to generate AI background: ${errMsg}. Falling back to default vector gradient.`);
    return null;
  }
}

/**
 * Sinh ảnh Quote Card dưới dạng file PNG tạm thời
 * @param {string} text - Câu trích dẫn/Tip ngắn hiển thị trên ảnh
 * @param {string} timeOfDay - Buổi đăng bài ("sáng", "trưa", "tối") để đổi màu nền
 * @param {string} groupId - ID nhóm để đặt tên file tạm thời tránh xung đột
 * @param {string} groupName - Tên nhóm để nhận diện theme
 * @param {string} groupPurpose - Mục đích hoạt động của nhóm để nhận diện theme
 * @returns {Promise<string>} Đường dẫn tuyệt đối đến file PNG tạm thời được tạo ra
 */
export async function createCard(text, timeOfDay, groupId, groupName = '', groupPurpose = '') {
  const width = 800;
  const height = 800;
  
  const normTime = (timeOfDay || '').toLowerCase();
  const normPurpose = ((groupPurpose || '') + ' ' + (groupName || '')).toLowerCase();

  // 1. Sinh hình nền AI (nếu có key và không lỗi)
  const aiBg = await generateAiBackground(groupName, groupPurpose);
  
  let theme = {
    bgGradient: '',
    cardBg: '',
    borderColor: '',
    titleColor: '',
    textColor: '',
    footerColor: '',
    quoteMarkColor: '',
    decorativeHtml: '',
    defaultTitle: ''
  };

  // Lựa chọn Theme dựa trên mục đích và tên nhóm
  if (normPurpose.includes('nhàu') || normPurpose.includes('tâm an') || normPurpose.includes('sức khoẻ') || normPurpose.includes('sức khỏe') || normPurpose.includes('thảo mộc') || normPurpose.includes('organic') || normPurpose.includes('wellness') || normPurpose.includes('mộc')) {
    // 🍃 MATCHA & GOLD (Zen Health Theme - Nhàu Thảo Mộc)
    theme.bgGradient = `
      <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#F4F8F4"/>
        <stop offset="50%" stop-color="#EAF2EA"/>
        <stop offset="100%" stop-color="#DEEBE0"/>
      </linearGradient>
    `;
    theme.cardBg = 'rgba(255, 255, 255, 0.88)';
    theme.borderColor = 'rgba(76, 117, 89, 0.25)';
    theme.titleColor = '#2D5A43';
    theme.textColor = '#1B3527';
    theme.footerColor = 'rgba(45, 90, 67, 0.55)';
    theme.quoteMarkColor = 'rgba(76, 117, 89, 0.15)';
    theme.decorativeHtml = `
      <!-- Elegant gold/green Zen circles -->
      <circle cx="700" cy="100" r="145" fill="none" stroke="rgba(192, 160, 96, 0.2)" stroke-width="1" />
      <circle cx="700" cy="100" r="95" fill="none" stroke="rgba(192, 160, 96, 0.15)" stroke-width="1.5" />
      <circle cx="100" cy="700" r="115" fill="none" stroke="rgba(76, 117, 89, 0.15)" stroke-width="1" />
      <path d="M 60,670 C 90,640 120,650 150,620" fill="none" stroke="rgba(76, 117, 89, 0.2)" stroke-width="2" />
    `;
    
    if (normTime.includes('sáng') || normTime.includes('8:00') || normTime.includes('morning')) {
      theme.defaultTitle = 'DINH DƯỠNG AN LÀNH';
    } else if (normTime.includes('trưa') || normTime.includes('12:00') || normTime.includes('noon')) {
      theme.defaultTitle = 'TÂM AN SỨC KHỎE';
    } else {
      theme.defaultTitle = 'SỐNG KHỎE MỖI NGÀY';
    }
  } else if (normPurpose.includes('nhân hiệu') || normPurpose.includes('bích') || normPurpose.includes('phát triển') || normPurpose.includes('ai') || normPurpose.includes('sáng tạo')) {
    // 🔮 ROYAL VIOLET & BLUSH (Feminine Personal Brand / Creator Theme)
    theme.bgGradient = `
      <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#FAF5FF"/>
        <stop offset="50%" stop-color="#FFF5F5"/>
        <stop offset="100%" stop-color="#F3E8FF"/>
      </linearGradient>
    `;
    theme.cardBg = 'rgba(255, 255, 255, 0.88)';
    theme.borderColor = 'rgba(168, 85, 247, 0.22)';
    theme.titleColor = '#7E22CE';
    theme.textColor = '#3B0764';
    theme.footerColor = 'rgba(126, 34, 206, 0.55)';
    theme.quoteMarkColor = 'rgba(168, 85, 247, 0.18)';
    theme.decorativeHtml = `
      <!-- Soft feminine lines and sparkles -->
      <path d="M 50,250 C 200,200 600,300 750,250" fill="none" stroke="rgba(236, 72, 153, 0.06)" stroke-width="3" />
      <path d="M 50,550 C 200,500 600,600 750,550" fill="none" stroke="rgba(168, 85, 247, 0.06)" stroke-width="3" />
      <g fill="rgba(168, 85, 247, 0.2)">
        <path d="M 120,120 L 122,125 L 127,127 L 122,129 L 120,134 L 118,129 L 113,127 L 118,125 Z" />
        <path d="M 680,640 L 681.5,644 L 685.5,645.5 L 681.5,647 L 680,651 L 678.5,647 L 674.5,645.5 L 678.5,644 Z" />
      </g>
    `;
    
    if (normTime.includes('sáng') || normTime.includes('8:00') || normTime.includes('morning')) {
      theme.defaultTitle = 'KIẾN TẠO MỤC TIÊU';
    } else if (normTime.includes('trưa') || normTime.includes('12:00') || normTime.includes('noon')) {
      theme.defaultTitle = 'XÂY DỰNG NHÂN HIỆU';
    } else {
      theme.defaultTitle = 'TỰ HỌC & PHÁT TRIỂN';
    }
  } else {
    // 🌌 SLEEK DEEP OCEAN (Trading, Business, Default Slate Theme)
    theme.bgGradient = `
      <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#0B132B"/>
        <stop offset="50%" stop-color="#1C2541"/>
        <stop offset="100%" stop-color="#0B132B"/>
      </linearGradient>
    `;
    theme.cardBg = 'rgba(28, 37, 65, 0.65)';
    theme.borderColor = 'rgba(91, 192, 190, 0.22)';
    theme.titleColor = '#5BC0BE';
    theme.textColor = '#FFFFFF';
    theme.footerColor = 'rgba(91, 192, 190, 0.55)';
    theme.quoteMarkColor = 'rgba(91, 192, 190, 0.15)';
    theme.decorativeHtml = `
      <!-- Modern technology lines -->
      <line x1="50" y1="220" x2="750" y2="220" stroke="rgba(91, 192, 190, 0.08)" stroke-width="1" />
      <line x1="50" y1="580" x2="750" y2="580" stroke="rgba(91, 192, 190, 0.08)" stroke-width="1" />
      <circle cx="400" cy="400" r="320" fill="none" stroke="rgba(91, 192, 190, 0.03)" stroke-width="1" />
    `;

    if (normTime.includes('sáng') || normTime.includes('8:00') || normTime.includes('morning')) {
      theme.defaultTitle = 'KỶ LUẬT & TƯ DUY';
    } else if (normTime.includes('trưa') || normTime.includes('12:00') || normTime.includes('noon')) {
      theme.defaultTitle = 'BÀI HỌC THỰC TẾ';
    } else {
      theme.defaultTitle = 'TỔNG KẾT & CHIÊM NGHIỆM';
    }
  }

  // 2. Wrap văn bản
  const lines = wrapText(text, 36);
  // Tính toán vị trí Y xuất phát để căn giữa đoạn văn
  const lineHeight = 42;
  const startY = 400 - ((lines.length - 1) * lineHeight) / 2;
  
  const textSpanHtml = lines.map((line, index) => {
    return `<tspan x="400" y="${startY + index * lineHeight}" text-anchor="middle">${escapeXml(line)}</tspan>`;
  }).join('\n');

  // 3. Đọc logo base64 (hoặc vẽ placeholder)
  const logo1Base64 = getLogoBase64(1);
  const logo2Base64 = getLogoBase64(2);
  
  const logo1Html = logo1Base64 
    ? `<image href="${logo1Base64}" x="80" y="650" width="70" height="70" />`
    : `
      <g transform="translate(80, 650)">
        <circle cx="35" cy="35" r="32" fill="rgba(255, 255, 255, 0.15)" stroke="rgba(255, 255, 255, 0.4)" stroke-width="1.5" />
        <text x="35" y="40" font-family="'Noto Sans', Arial, sans-serif" font-size="11" font-weight="bold" fill="rgba(255, 255, 255, 0.8)" text-anchor="middle">LOGO 1</text>
      </g>
    `;
    
  const logo2Html = logo2Base64 
    ? `<image href="${logo2Base64}" x="650" y="650" width="70" height="70" />`
    : `
      <g transform="translate(650, 650)">
        <circle cx="35" cy="35" r="32" fill="rgba(255, 255, 255, 0.15)" stroke="rgba(255, 255, 255, 0.4)" stroke-width="1.5" />
        <text x="35" y="40" font-family="'Noto Sans', Arial, sans-serif" font-size="11" font-weight="bold" fill="rgba(255, 255, 255, 0.8)" text-anchor="middle">LOGO 2</text>
      </g>
    `;

  // 4. Tạo SVG string hoàn chỉnh
  const svg = `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        ${theme.bgGradient}
      </defs>
      
      <!-- Background -->
      ${aiBg 
        ? `<image href="${aiBg}" x="0" y="0" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" />` 
        : `<rect width="100%" height="100%" fill="url(#bg)" />`
      }
      
      <!-- Decorative Elements -->
      ${theme.decorativeHtml}
      
      <!-- Card Overlay (Glassmorphism Effect) -->
      <rect x="50" y="50" width="700" height="700" rx="28" fill="${theme.cardBg}" stroke="${theme.borderColor}" stroke-width="1.5" />
      
      <!-- Header Title -->
      <text x="400" y="140" font-family="'Noto Sans', Arial, sans-serif" font-size="28" font-weight="900" fill="${theme.titleColor}" text-anchor="middle" letter-spacing="2">
        ${escapeXml(theme.defaultTitle)}
      </text>
      
      <!-- Subtle Decorative Line -->
      <line x1="280" y1="170" x2="520" y2="170" stroke="${theme.borderColor}" stroke-width="1.5" />
      
      <!-- Big Quote Mark -->
      <text x="400" y="${startY - 35}" font-family="'Noto Sans', Georgia, serif" font-size="80" fill="${theme.quoteMarkColor}" text-anchor="middle" font-weight="bold">“</text>
      
      <!-- Quote Content -->
      <text font-family="'Noto Sans', Georgia, serif" font-size="28" font-style="italic" fill="${theme.textColor}" text-anchor="middle">
        ${textSpanHtml}
      </text>
      
      <!-- Branding & Logos Footer -->
      <text x="400" y="685" font-family="'Noto Sans', Arial, sans-serif" font-size="13" font-weight="bold" fill="${theme.footerColor}" text-anchor="middle" letter-spacing="2.5">
        ${normPurpose.includes('nhân hiệu') || normPurpose.includes('bích') ? 'CÔ LƯU BÍCH' : 'OPC ANH CƯỜNG'}
      </text>
      
      ${logo1Html}
      ${logo2Html}
    </svg>
  `;

  // 5. Render SVG thành file PNG bằng Sharp
  const outputDir = path.join(process.cwd(), 'data', 'temp_images');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const outputPath = path.join(outputDir, `nurturing_${groupId || 'default'}.png`);
  
  try {
    await sharp(Buffer.from(svg))
      .png()
      .toFile(outputPath);
      
    logger.info(`✅ Generated nurturing image successfully at: ${outputPath}`);
    return outputPath;
  } catch (err) {
    logger.error('❌ Failed to compile SVG to PNG using sharp', err);
    throw err;
  }
}
