import { lessons } from '../hub/lessons.js';
import { questions } from '../hub/quiz/questions.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const outLessons = lessons.map(l => {
    const nbPath = l.notebook.replace('../', '');
    const materialPath = nbPath.split('/').slice(0, -1).join('/') + '/README.md';
    return {
        id: l.id,
        level: l.level,
        step: parseInt(l.step, 10),
        title: l.title,
        summary: l.description,
        outcome: l.lesson,
        material: materialPath,
        notebook: nbPath,
        refs: []
    };
});

const checks = {};
questions.forEach(q => {
    const lessonId = q.id.split('-')[0];
    if (!checks[lessonId]) checks[lessonId] = [];
    checks[lessonId].push({
        question: q.prompt,
        choices: q.options,
        answer: q.correct[0],
        explanation: q.explanation
    });
});

const content = `export const lessons = ${JSON.stringify(outLessons, null, 2)};\n\nexport const checks = ${JSON.stringify(checks, null, 2)};\n`;

fs.writeFileSync(path.join(__dirname, '../hub/lessons.js'), content, 'utf8');
console.log('Successfully wrote new lessons.js');
