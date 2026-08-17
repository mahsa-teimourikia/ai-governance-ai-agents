import fs from 'fs';

const bundleName = fs.readdirSync('out/assets').find(f => f.endsWith('.js'));
if (!bundleName) throw new Error('No JS bundle found');
const bundle = fs.readFileSync('out/assets/' + bundleName, 'utf8');

if (!bundle.includes('Build answers')) throw new Error('Smoke test failed: Missing Build answers');
if (!bundle.includes('FIELD GUIDE')) throw new Error('Smoke test failed: Missing FIELD GUIDE');
if (!bundle.includes('<CurrentLesson1>')) throw new Error('Smoke test failed: Missing CurrentLesson1');

if (!fs.existsSync('out/quiz/index.html')) throw new Error('Quiz not copied');
if (!fs.existsSync('out/assets/one-plus-i.png')) throw new Error('Logo missing');

console.log('Pages smoke test passed!');
