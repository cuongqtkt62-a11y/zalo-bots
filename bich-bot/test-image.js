import { createCard } from './src/image-generator.js';
async function test() {
  await createCard({cursive_quote: 'Trao đi giá trị để', highlight_quote: 'LÀM CHỦ CUỘC ĐỜI'}, 'Buổi sáng', 'test', 'Test Group', 'Purpose');
}
test();
