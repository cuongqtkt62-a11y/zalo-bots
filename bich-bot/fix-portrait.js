import fs from 'fs';
import sharp from 'sharp';
import { bichPortraitBase64 } from './src/bich-portrait.js';

async function processImage() {
  console.log('Processing image...');
  // Tách data URI
  const base64Data = bichPortraitBase64.replace(/^data:image\/\w+;base64,/, '');
  const buffer = Buffer.from(base64Data, 'base64');
  
  // Crop thành hình tròn hoàn hảo, nền trong suốt
  const size = 380; // Kích thước vuông
  const circleSvg = `<svg width="${size}" height="${size}"><circle cx="${size/2}" cy="${size/2}" r="${size/2}" /></svg>`;

  const croppedBuffer = await sharp(buffer)
    .resize(size, size, { fit: 'cover', position: 'center' })
    .composite([{
      input: Buffer.from(circleSvg),
      blend: 'dest-in'
    }])
    .png()
    .toBuffer();

  console.log('Image processed. Size:', croppedBuffer.length);
  
  const newBase64 = `export const bichPortraitBase64 = "data:image/png;base64,${croppedBuffer.toString('base64')}";\n`;
  
  fs.writeFileSync('./src/bich-portrait.js', newBase64);
  console.log('Saved to src/bich-portrait.js');
}

processImage().catch(console.error);
