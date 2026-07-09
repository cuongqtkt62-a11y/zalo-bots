// ============================================================
// image-generator.js — Advanced AI Graphic Designer (Satori Engine)
// ============================================================

import fs from 'fs';
import path from 'path';
import axios from 'axios';
import logger from './logger.js';
import config from './config.js';

// Satori Engine
import satori from 'satori';
import { html } from 'satori-html';
import { Resvg } from '@resvg/resvg-js';

// Assets
import { bichPortraitBase64 } from './bich-portrait.js';
import { greatVibesFontBase64 } from './font-great-vibes.js';
import { playfairFontBase64 } from './font-playfair.js';

/**
 * Sinh hình nền AI bằng mô hình Imagen 4.0 từ Google AI Studio
 */
async function generateAiBackground(groupName, groupPurpose, styleType) {
  const apiKey = config.ai?.geminiApiKey;
  if (!apiKey) {
    logger.warn('⚠️ GEMINI_API_KEY is not defined, skipping AI background.');
    return null;
  }

  const normPurpose = ((groupPurpose || '') + ' ' + (groupName || '')).toLowerCase();
  let themeDesc = "soft pastel background with delicate floral line art and golden circles, elegant, minimalist";
  
  if (styleType === 2) {
    themeDesc = "bold vivid color splash, high contrast abstract art, modern editorial background, energetic and clean";
  } else if (styleType === 3) {
    themeDesc = "cinematic deep space gradient, dark minimalist background with soft glowing orbs, professional luxury vibe";
  }

  const prompt = `A premium, extremely professional, elegant minimalist abstract background for graphic design. Clean with copy space in the center, no busy details, no text, no people, suitable as a quote card background for: ${themeDesc}. Aspect ratio 1:1, high quality.`;
  const url = `https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key=${apiKey}`;

  try {
    logger.info('🎨 Requesting AI Background from Imagen 4.0...', { styleType });
    const response = await axios.post(url, {
      instances: [{ prompt }],
      parameters: { sampleCount: 1, aspectRatio: '1:1' }
    }, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 15000
    });

    const base64Data = response.data?.predictions?.[0]?.bytesBase64Encoded;
    if (base64Data) {
      return `data:image/png;base64,${base64Data}`;
    }
    return null;
  } catch (err) {
    logger.warn(`⚠️ Failed to generate AI background. Falling back to default.`);
    return null;
  }
}

/**
 * Sinh ảnh Graphic Design
 */
export async function createCard(nurturingData, timeOfDay, groupId, groupName = '', groupPurpose = '') {
  const width = 1080;
  const height = 1080;

  // Xử lý đầu vào
  let cursiveText = nurturingData?.cursive_quote || "Trao đi giá trị để";
  let highlightText = nurturingData?.highlight_quote || "LÀM CHỦ CUỘC ĐỜI";

  if (typeof nurturingData === 'string') {
    highlightText = nurturingData;
    cursiveText = "Trao đi giá trị để";
  }

  // Chọn style ngẫu nhiên (1, 2, 3)
  // Hardcoded to 3 because the new avatar is a circular crop
  const styleType = 3;
  const aiBg = await generateAiBackground(groupName, groupPurpose, styleType);

  let bgCss = aiBg 
    ? `background-image: url(${aiBg}); background-size: 100% 100%;` 
    : `background: linear-gradient(to bottom right, #FDFBF7, #E6F0E9);`;

  let htmlMarkup = '';

  // Dữ liệu font
  const fonts = [];
  if (greatVibesFontBase64) {
    fonts.push({
      name: 'Great Vibes',
      data: Buffer.from(greatVibesFontBase64.replace(/^data:font\/(ttf|woff|woff2);base64,/, ''), 'base64'),
      weight: 400,
      style: 'normal',
    });
  }
  if (playfairFontBase64) {
    fonts.push({
      name: 'Playfair Display',
      data: Buffer.from(playfairFontBase64.replace(/^data:font\/(ttf|woff|woff2);base64,/, ''), 'base64'),
      weight: 700,
      style: 'normal',
    });
  }

  // --- STYLE 1: Cổ Điển Sang Trọng (Ảnh phải, Chữ trái mờ) ---
  if (styleType === 1) {
    htmlMarkup = html`
      <div style="display: flex; flex-direction: row; width: ${width}px; height: ${height}px; ${bgCss}">
        
        <!-- Khung chữ bên trái -->
        <div style="display: flex; flex-direction: column; width: 600px; height: 100%; padding: 80px 40px; justify-content: center; align-items: center; z-index: 10;">
          <div style="display: flex; flex-direction: column; background: rgba(255, 255, 255, 0.85); padding: 50px; border-radius: 30px; border: 2px solid #C29B4A; align-items: center; text-align: center;">
            <span style="font-family: 'Great Vibes'; font-size: 75px; color: #36594C; text-align: center; line-height: 1.2;">
              ${cursiveText}
            </span>
            <div style="display: flex; align-items: center; justify-content: center; width: 100%; padding: 20px 0; margin-top: 20px;">
              <span style="font-family: 'Playfair Display'; font-size: 65px; color: #C29B4A; text-align: center; text-transform: uppercase; letter-spacing: 2px;">
                ${highlightText}
              </span>
            </div>
            <span style="font-family: 'Great Vibes'; font-size: 60px; color: #36594C; margin-top: 20px;">
              chính mình
            </span>
          </div>
        </div>

        <!-- Chân dung bên phải -->
        <div style="display: flex; width: 500px; height: 100%; position: absolute; right: -20px; bottom: 0;">
          ${bichPortraitBase64 ? 
            html`<img src="${bichPortraitBase64}" style="width: 100%; height: 100%; object-fit: cover;" />` : 
            html`<span></span>`}
        </div>

      </div>
    `;
  }
  
  // --- STYLE 2: Hiện Đại Phá Cách (Chân dung góc trái dưới, Quote lớn) ---
  else if (styleType === 2) {
    htmlMarkup = html`
      <div style="display: flex; flex-direction: column; width: ${width}px; height: ${height}px; ${bgCss} padding: 100px;">
        
        <!-- Dấu ngoặc kép mờ khổng lồ -->
        <div style="position: absolute; top: 50px; left: 80px; font-family: 'Playfair Display'; font-size: 400px; color: rgba(194, 155, 74, 0.15); line-height: 1;">
          "
        </div>

        <!-- Khung chữ -->
        <div style="display: flex; flex-direction: column; width: 850px; z-index: 10; margin-top: 150px;">
          <span style="font-family: 'Great Vibes'; font-size: 80px; color: #1E293B;">
            ${cursiveText}
          </span>
          <span style="font-family: 'Playfair Display'; font-size: 85px; color: #C29B4A; text-transform: uppercase; margin-top: 30px; line-height: 1.1;">
            ${highlightText}
          </span>
          <div style="display: flex; margin-top: 40px; border-bottom: 5px solid #C29B4A; width: 150px;"></div>
        </div>

        <!-- Chân dung bên phải dưới -->
        <div style="display: flex; position: absolute; right: 0; bottom: 0; width: 550px; height: 750px;">
          ${bichPortraitBase64 ? 
            html`<img src="${bichPortraitBase64}" style="width: 100%; height: 100%; object-fit: contain;" />` : 
            html`<span></span>`}
        </div>

      </div>
    `;
  }

  // --- STYLE 3: Trung Tâm Điện Ảnh (Avatar tròn, Chữ căn giữa) ---
  else {
    if (!aiBg) {
      bgCss = `background: linear-gradient(to bottom right, #0F172A, #020617);`; // Fallback tối sang trọng
    }

    htmlMarkup = html`
      <div style="display: flex; flex-direction: column; width: ${width}px; height: ${height}px; ${bgCss} align-items: center; justify-content: center; padding: 60px;">
        
        <img src="${bichPortraitBase64}" style="width: 380px; height: 380px; margin-bottom: 40px; object-fit: contain;" />

        <!-- Khung chữ tối màu sang trọng -->
        <div style="display: flex; flex-direction: column; align-items: center; background: rgba(0,0,0,0.4); padding: 50px 90px; border-radius: 50px; border: 2px solid rgba(253, 224, 71, 0.3);">
          <span style="font-family: 'Great Vibes'; font-size: 75px; color: #FDE047; margin-bottom: 25px;">
            ${cursiveText}
          </span>
          <span style="font-family: 'Playfair Display'; font-size: 65px; color: #FFFFFF; text-align: center; text-transform: uppercase; letter-spacing: 4px; line-height: 1.2;">
            ${highlightText}
          </span>
        </div>

        <!-- Chữ ký -->
        <span style="font-family: 'Great Vibes'; font-size: 55px; color: rgba(253, 224, 71, 0.6); position: absolute; bottom: 60px;">
          Lưu Bích
        </span>

      </div>
    `;
  }

  // Render HTML sang SVG bằng Satori
  const svg = await satori(htmlMarkup, {
    width: width,
    height: height,
    fonts: fonts
  });

  // Render SVG sang PNG bằng Resvg
  const resvg = new Resvg(svg, {
    fitTo: { mode: 'width', value: width },
  });
  
  const pngData = resvg.render();
  const pngBuffer = pngData.asPng();

  const outputDir = path.join(process.cwd(), 'data', 'temp_images');
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
  
  const outputPath = path.join(outputDir, `nurturing_${groupId || 'default'}.png`);
  
  try {
    fs.writeFileSync(outputPath, pngBuffer);
    logger.info(`✅ Generated AI Graphic Designer image (Style ${styleType}) at: ${outputPath}`);
    return outputPath;
  } catch (err) {
    logger.error('❌ Failed to save PNG', err);
    throw err;
  }
}
