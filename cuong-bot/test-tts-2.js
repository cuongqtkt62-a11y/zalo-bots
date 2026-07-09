import { EdgeTTS } from 'node-edge-tts';
async function test() {
  const text = "Trong kinh doanh, nếu bạn liên tục hạ mình và thỏa hiệp vô điều kiện, bạn sẽ đánh mất không chỉ lợi nhuận, mà còn cả vị thế của chính mình.";
  const sentences = text.split(/[,.!?]+/g);
  console.log('sentences:', sentences);
  for (let i = 0; i < sentences.length; i++) {
    const sentence = sentences[i].trim();
    if (!sentence) continue;
    const tts = new EdgeTTS({ voice: 'vi-VN-HoaiMyNeural', lang: 'vi-VN' });
    const chunkPath = `chunk_test_${i}.mp3`;
    console.log(`Generating chunk ${i}: ${sentence}...`);
    try {
      await Promise.race([
        tts.ttsPromise(sentence, chunkPath),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Edge TTS Timeout')), 10000))
      ]);
      console.log(`Chunk ${i} success`);
    } catch(err) {
      console.error(`Chunk ${i} error:`, err.message);
    }
  }
}
test();
