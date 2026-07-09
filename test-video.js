import { createYouTubeVideo } from './cuong-bot/src/video-creator.js';
async function test() {
  console.log("Starting video test...");
  try {
    const result = await createYouTubeVideo("câu nói hay về thành công");
    console.log("Result:", result);
  } catch (err) {
    console.error("Error:", err);
  }
}
test();
