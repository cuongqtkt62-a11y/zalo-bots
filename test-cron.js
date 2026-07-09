import { join } from 'path';
import { readFileSync, existsSync } from 'fs';

const p1 = './bich-bot/data/approved_groups.json';
const p2 = './cuong-bot/data/approved_groups.json';

console.log("Bich groups:", existsSync(p1) ? JSON.parse(readFileSync(p1)).length : "not found");
console.log("Cuong groups:", existsSync(p2) ? JSON.parse(readFileSync(p2)).length : "not found");
