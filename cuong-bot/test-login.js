import fs from 'fs';
import { Zalo } from 'zca-js';

async function test() {
  try {
    const creds = JSON.parse(fs.readFileSync('zalo-credentials-cuong.json', 'utf-8'));
    const zalo = new Zalo({ selfListen: true });
    await zalo.login({
      cookie: creds.cookies,
      imei: creds.imei,
      userAgent: creds.userAgent,
    });
    console.log("✅ LOGIN SUCCESS");
    process.exit(0);
  } catch (err) {
    console.error("❌ LOGIN FAILED:", err.message);
    process.exit(1);
  }
}
test();
