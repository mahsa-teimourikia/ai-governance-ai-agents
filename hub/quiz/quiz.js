import { lessons, checks } from "../lessons.js";
const mount = document.querySelector("#quiz");
let answers = {};
function render(show = false) {
  let totalQuestions = 0;
  let correctAnswers = 0;
  const items = lessons.map((lesson, n) => {
    const courseChecks = checks[lesson.id] || [];
    if (courseChecks.length === 0) return "";
    let lessonHTML = `<article class="quiz-card"><p class="eyebrow">${lesson.level.toUpperCase()} · ${lesson.title}</p>`;
    
    courseChecks.forEach((q, qIdx) => {
        totalQuestions++;
        const key = `${lesson.id}-${qIdx}`;
        const picked = answers[key];
        if (show && picked === q.answer) correctAnswers++;
        
        lessonHTML += `<h2 style="margin-top:15px; font-size:1.2rem;">Q. ${q.question}</h2>
        ${q.choices.map((choice, i) => `<label class="quiz-choice ${show ? (i === q.answer ? "correct" : picked === i ? "incorrect" : "") : ""}"><input type="radio" name="${key}" value="${i}" ${picked === i ? "checked" : ""}> ${choice}</label>`).join("")}
        ${show ? `<p class="feedback">${picked === q.answer ? "Correct. " : "Review this: "}${q.explanation}</p>` : ""}`;
    });
    lessonHTML += `</article>`;
    return lessonHTML;
  }).join("");
  
  const score = show ? `<div class="score"><h2>${correctAnswers} / ${totalQuestions}</h2><p>Use the explanations to revisit the related lesson in the Hub.</p><a class="button" href="../">Return to the Learning Hub ↗</a></div>` : "";
  mount.innerHTML = `${items}<button class="button" id="grade">Grade my knowledge check</button>${score}`;
  mount.querySelectorAll("input").forEach(input => input.onchange = () => { answers[input.name] = Number(input.value); });
  mount.querySelector("#grade").onclick = () => render(true);
}
render();
