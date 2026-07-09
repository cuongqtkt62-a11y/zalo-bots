import { EdgeTTS } from 'node-edge-tts';
async function test() {
  const tts = new EdgeTTS({
    voice: 'vi-VN-HoaiMyNeural',
    lang: 'vi-VN'
  });
  try {
    await tts.ttsPromise('Xin chào các bạn.', 'test-out.mp3');
    console.log('Success!');
  } catch (err) {
    console.error('Edge TTS Error:', err);
  }
}
test();
