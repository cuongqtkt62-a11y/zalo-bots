import fs from 'fs';
import { Zalo } from 'zca-js';

async function test() {
  try {
    const creds = JSON.parse(fs.readFileSync('zalo-credentials-cuong.json', 'utf-8'));
    const zalo = new Zalo({ selfListen: true });
    const api = await zalo.login({
      cookie: creds.cookies,
      imei: creds.imei,
      userAgent: creds.userAgent,
    });
    console.log("✅ LOGIN SUCCESS");
    
    // The bot's own ID
    const myId = "620730323173745711";
    
    try {
      await api.sendMessage("Test sending to Cloud của tôi", myId);
      console.log("✅ SENT SUCCESSFULLY");
    } catch (e) {
      console.error("❌ FAILED TO SEND:", e.message, e.code);
    }
    
    process.exit(0);
  } catch (err) {
    console.error("❌ LOGIN FAILED:", err.message);
    process.exit(1);
  }
}
test();
