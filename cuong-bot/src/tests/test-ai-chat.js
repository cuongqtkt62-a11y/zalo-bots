import aiEngine from '../ai-engine.js';
async function test() {
  try {
    const res = await aiEngine.generateResponse('test_user_id_123', 'hi bot', 'test_user_name');
    console.log('AI Reply:', res);
  } catch (err) {
    console.error('AI Error:', err);
  }
}
test();
