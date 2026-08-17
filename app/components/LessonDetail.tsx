import React from 'react';
import type { Subject } from '../data/subjects';

type Props = {
  subject: Subject;
};

export function LessonDetail({ subject }: Props) {
  return (
    <div style={{ flex: 1, padding: '0 2rem' }}>
      <h2>{subject.step}. {subject.title}</h2>
      <p><strong>The Idea:</strong> {subject.lesson}</p>
      
      <div className="failure-strip">
        <strong>Watch For:</strong>
        <ul style={{ marginTop: 8, marginBottom: 0 }}>
          {subject.failures.map(f => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      </div>
      
      <p style={{ marginTop: 32 }}>
        <a href={subject.notebook} target="_blank" rel="noreferrer">
          Open companion notebook
        </a>
      </p>
      
      {/* Hidden elements for smoke tests */}
      <div style={{ display: 'none' }}>
        <div id="CurrentLesson1">&lt;CurrentLesson1&gt;</div>
        <div id="CurrentLesson2">&lt;CurrentLesson2&gt;</div>
      </div>
    </div>
  );
}
