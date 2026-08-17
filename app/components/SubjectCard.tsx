import React from 'react';
import type { Subject } from '../data/subjects';

type Props = {
  subject: Subject;
  selected: boolean;
  onClick: () => void;
};

export function SubjectCard({ subject, selected, onClick }: Props) {
  const badgeClass = subject.level === 'Beginner' ? 'mint' 
                   : subject.level === 'Intermediate' ? 'gold' 
                   : 'coral';

  return (
    <div className={`subject-card ${selected ? 'selected' : ''}`} onClick={onClick}>
      <div style={{ marginBottom: 8 }}>
        <span className={badgeClass}>{subject.level}</span>
      </div>
      <h3 style={{ margin: '0 0 8px 0' }}>{subject.step}. {subject.title}</h3>
      <p style={{ margin: 0, fontSize: '0.9em', color: 'var(--muted)' }}>
        {subject.description}
      </p>
    </div>
  );
}
