import { lessons, checks } from "./lessons.js";

const base = "https://github.com/mahsa-teimourikia/ai-governance-ai-agents/blob/main/";
const filters = document.querySelector("#filters");
const cards = document.querySelector("#cards");
const workspace = document.querySelector("#workspace");
let level = "All";
let selected = lessons[0];
let tab = "learn";
let completed = JSON.parse(localStorage.getItem("course-hub-progress") || "[]");
const link = (path) => path.startsWith("http") ? path : base + path;

function renderFilters() {
  filters.innerHTML = ["All", "Beginner", "Intermediate", "Advanced", "Enterprise"].map((value) => `<button class="${level === value ? "active" : ""}" data-level="${value}">${value}</button>`).join("");
  filters.querySelectorAll("button").forEach((button) => button.onclick = () => { level = button.dataset.level; renderFilters(); renderCards(); });
}

function renderCards() {
  const visible = level === "All" ? lessons : lessons.filter((lesson) => lesson.level === level);
  cards.innerHTML = `<p class="progress">${completed.length}/${lessons.length} lessons complete</p>` + visible.map((lesson) => `<button class="card ${selected.id === lesson.id ? "selected" : ""}" data-id="${lesson.id}"><span class="pill">${lesson.level} · ${lesson.step}</span><h3>${lesson.title} ${completed.includes(lesson.id) ? "✓" : ""}</h3><p>${lesson.summary}</p></button>`).join("");
  cards.querySelectorAll(".card").forEach((card) => card.onclick = () => { selected = lessons.find((lesson) => lesson.id === card.dataset.id); tab = "learn"; renderCards(); renderWorkspace(); workspace.scrollIntoView({ behavior: "smooth" }); });
}

function renderWorkspace() {
  const courseChecks = checks[selected.id] || [];
  
  let learnBody = `<p class="outcome">${selected.outcome}</p><p>Read the in-depth theory, trade-offs, failure modes, and cited sources before opening the executable notebook.</p><a class="button" href="${link(selected.material)}" target="_blank">Read lesson ↗</a>`;
  
  let notebookBody = `<p class="outcome">The notebook is the practical learning artifact: deterministic fixtures, implementation, assertions, an experiment, and reflection live together.</p><p>It runs without an API key or external side effects. Use <code>make notebooks</code> to execute every course notebook locally.</p>`;
  if (Array.isArray(selected.notebook)) {
      notebookBody += selected.notebook.map(nb => `<a class="button" style="display:block; margin-bottom: 8px;" href="${link(nb.path)}" target="_blank">Open ${nb.title} ↗</a>`).join("");
  } else {
      notebookBody += `<a class="button" href="${link(selected.notebook)}" target="_blank">Open self-contained notebook ↗</a>`;
  }
  
  let checkBody = `<p class="outcome">Knowledge Check</p>`;
  courseChecks.forEach((c, idx) => {
      checkBody += `<div class="quiz-item" style="margin-bottom:20px;">
          <p style="margin-bottom:10px;"><strong>Q${idx+1}:</strong> ${c.question}</p>
          <div class="choices" data-quiz="${idx}" style="margin-bottom:10px;">
              ${c.choices.map((choice, index) => `<button data-choice="${index}">${choice}</button>`).join("")}
          </div>
          <p id="feedback-${idx}" class="feedback"></p>
      </div>`;
  });
  checkBody += `<a href="quiz/">Take the full quiz ↗</a>`;

  const body = tab === "learn" ? learnBody : tab === "notebook" ? notebookBody : checkBody;
  
  workspace.innerHTML = `<div class="workspace-head"><div><p class="eyebrow">LESSON ${selected.step} · ${selected.level.toUpperCase()}</p><h2>${selected.title}</h2></div><span class="pill">${selected.level}</span></div><div class="lesson-tabs"><button data-tab="learn" class="${tab === "learn" ? "active" : ""}">01 / Learn</button><button data-tab="notebook" class="${tab === "notebook" ? "active" : ""}">02 / Notebook</button><button data-tab="checkpoint" class="${tab === "checkpoint" ? "active" : ""}">03 / Checkpoint</button></div><div class="lesson-grid"><article>${body}<br/><br/><button class="complete" id="complete">${completed.includes(selected.id) ? "Completed ✓" : "Mark lesson complete"}</button></article><aside><p class="eyebrow">SOURCES</p>${selected.refs.map((ref) => `<a class="source" href="${link(ref.path || ref)}" target="_blank">${ref.title || ref} ↗</a>`).join("")}</aside></div>`;
  
  workspace.querySelectorAll("[data-tab]").forEach((button) => button.onclick = () => { tab = button.dataset.tab; renderWorkspace(); });
  
  if (tab === "checkpoint") {
      workspace.querySelectorAll(".choices").forEach(choiceGroup => {
          const quizIdx = choiceGroup.dataset.quiz;
          const check = courseChecks[quizIdx];
          choiceGroup.querySelectorAll("[data-choice]").forEach((button) => button.onclick = () => { 
              const correct = Number(button.dataset.choice) === check.answer; 
              workspace.querySelector(`#feedback-${quizIdx}`).textContent = `${correct ? "Correct. " : "Not quite. "}${check.explanation}`; 
          });
      });
  }
  
  workspace.querySelector("#complete").onclick = () => { completed = completed.includes(selected.id) ? completed.filter((id) => id !== selected.id) : [...completed, selected.id]; localStorage.setItem("course-hub-progress", JSON.stringify(completed)); renderCards(); renderWorkspace(); };
}

renderFilters(); renderCards(); renderWorkspace();
