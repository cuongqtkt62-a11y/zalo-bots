const fs = require('fs');
async function run() {
  const mod = await import('./src/bich-portrait.js');
  const base64Data = mod.bichPortraitBase64.replace(/^data:image\/\w+;base64,/, '');
  fs.writeFileSync('/Users/mac/Desktop/test-bich-raw.png', Buffer.from(base64Data, 'base64'));
}
run();
