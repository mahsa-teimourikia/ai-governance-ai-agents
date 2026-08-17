import { lessons } from './lessons.js';

document.addEventListener('DOMContentLoaded', () => {
  const cardsContainer = document.getElementById('cards');
  const workspace = document.getElementById('workspace');

  function renderCards() {
    cardsContainer.innerHTML = '';
    lessons.forEach(lesson => {
      const el = document.createElement('div');
      el.className = 'card';
      el.innerHTML = `
        <span class="pill ${lesson.level.toLowerCase()}">${lesson.level}</span>
        <h3>${lesson.step}. ${lesson.title}</h3>
        <p>${lesson.description}</p>
      `;
      el.addEventListener('click', () => renderWorkspace(lesson, el));
      cardsContainer.appendChild(el);
    });
  }

  function renderWorkspace(lesson, cardEl) {
    document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
    if(cardEl) cardEl.classList.add('active');

    workspace.innerHTML = `
      <div class="workspace-header">
        <button class="active">Learn</button>
        <button>Notebook</button>
      </div>
      <div class="workspace-content">
        <h2>${lesson.step}. ${lesson.title}</h2>
        <p><strong>The Idea:</strong> ${lesson.lesson}</p>
        <br><br>
        <a class="button" href="${lesson.notebook}" target="_blank">Open Notebook ↗</a>
      </div>
    `;
    workspace.scrollIntoView({ behavior: 'smooth' });
  }

  renderCards();
});
