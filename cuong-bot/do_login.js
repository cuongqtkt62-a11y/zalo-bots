import { Zalo } from 'zca-js';
import { writeFileSync, existsSync, unlinkSync, copyFileSync } from 'fs';

if (existsSync('qr.png')) unlinkSync('qr.png');

const credentialsPath = './zalo-credentials-cuong.json';
const api = new Zalo({ credentials: credentialsPath }, { selfListen: false });

console.log('Logging in...');
api.login();

// Watch for qr.png to be created
const interval = setInterval(() => {
  if (existsSync('qr.png')) {
    console.log('QR Code generated! Copying to artifacts...');
    copyFileSync('qr.png', '/Users/mac/.gemini/antigravity-ide/brain/7c855322-e4ff-4dbf-a007-1c87f6f8135d/local_cuong_qr.png');
    clearInterval(interval);
  }
}, 500);
