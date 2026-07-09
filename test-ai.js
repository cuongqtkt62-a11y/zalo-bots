import aiEngine from './cuong-bot/src/ai-engine.js';
import dataStore from './cuong-bot/src/data-store.js';

async function test() {
  dataStore.upsertUser = () => ({ greetingStep: 99 }); // skip greeting
  try {
    const res = await aiEngine.generateResponse('test_user_1', 'hi em');
    console.log("AI Response:", res);
  } catch (err) {
    console.error("Test Error:", err);
  }
}
test();
