import fs from 'fs';
import sharp from 'sharp';

async function run() {
  const mod = await import('./src/bich-portrait.js');
  const base64Data = mod.bichPortraitBase64.replace(/^data:image\/\w+;base64,/, '');
  const buffer = Buffer.from(base64Data, 'base64');
  
  // Original size is 416x364. Center is 208, 182.
  // We want a 300x300 circle.
  const size = 300;
  const circleSvg = `<svg width="${size}" height="${size}"><circle cx="${size/2}" cy="${size/2}" r="${size/2}" /></svg>`;

  const croppedBuffer = await sharp(buffer)
    .extract({ left: Math.floor((416 - size) / 2), top: Math.floor((364 - size) / 2), width: size, height: size })
    .composite([{
      input: Buffer.from(circleSvg),
      blend: 'dest-in'
    }])
    .png()
    .toBuffer();

  const newBase64 = `export const bichPortraitBase64 = "data:image/png;base64,${croppedBuffer.toString('base64')}";\n`;
  fs.writeFileSync('./src/bich-portrait.js', newBase64);
  fs.writeFileSync('/Users/mac/Desktop/test-bich-cropped.png', croppedBuffer);
  console.log('Saved to src/bich-portrait.js and test-bich-cropped.png');
}
run();
