import fs from 'fs';
const b64 = fs.readFileSync('compressed-bgm.mp3').toString('base64');
fs.writeFileSync('cuong-bot/src/bgm-base64.js', `export const bgmBase64 = "${b64}";\n`);
fs.writeFileSync('bich-bot/src/bgm-base64.js', `export const bgmBase64 = "${b64}";\n`);
console.log('Done generating compressed base64 files.');
