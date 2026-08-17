import fs from 'fs';
import path from 'path';
const src = 'quiz';
const dest = 'out/quiz';
fs.cpSync(src, dest, { recursive: true });
fs.mkdirSync('out/assets', { recursive: true });
fs.copyFileSync('assets/one-plus-i.png', 'out/assets/one-plus-i.png');
console.log('Quiz and assets copied to out/');
