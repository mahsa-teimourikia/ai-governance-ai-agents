import React, { useState } from 'react';
import { subjects } from './data/subjects';
import { SubjectCard } from './components/SubjectCard';
import { LessonDetail } from './components/LessonDetail';

export default function Page() {
  const [selected, setSelected] = useState(subjects[0].id);
  const active = subjects.find(s => s.id === selected)!;

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem' }}>
      <h1>Build answers</h1>
      <nav style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <a href="#" style={{ fontWeight: 'bold' }}>FIELD GUIDE</a>
      </nav>
      
      <div style={{ display: 'flex', gap: '2rem' }}>
        <div style={{ width: '350px', height: '80vh', overflowY: 'auto', paddingRight: '1rem' }}>
          {subjects.map(s => (
            <SubjectCard 
              key={s.id} 
              subject={s} 
              selected={selected === s.id} 
              onClick={() => setSelected(s.id)} 
            />
          ))}
        </div>
        
        <LessonDetail subject={active} />
      </div>
      
      <footer>
        <p>Learning with One+i · responsible AI, real-world impact</p>
        <a href="https://oneplusi.io" target="_blank" rel="noreferrer">ONE+i · RESPONSIBLE AI ↗</a>
      </footer>
    </div>
  );
}
