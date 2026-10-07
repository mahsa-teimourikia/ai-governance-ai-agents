import { lessons, checks } from "../lessons.js";

const mount = document.querySelector("#quiz");
const questionCount = Object.values(checks).reduce(
  (total, items) => total + items.length,
  0,
);
document.querySelector("#question-count").textContent = questionCount;
const levels = ["All", ...new Set(lessons.map((lesson) => lesson.level))];
let level = "All";
let answers = {};

function render(show = false) {
  let totalQuestions = 0;
  let correctAnswers = 0;
  const visibleLessons =
    level === "All"
      ? lessons
      : lessons.filter((lesson) => lesson.level === level);
  const items = visibleLessons.map((lesson) => {
    const courseChecks = checks[lesson.id] || [];
    if (courseChecks.length === 0) return "";
    let lessonHTML = `<article class="quiz-card"><p class="eyebrow">${lesson.level.toUpperCase()} · ${lesson.title}</p>`;

    courseChecks.forEach((question, questionIndex) => {
      totalQuestions++;
      const key = `${lesson.id}-${questionIndex}`;
      const picked = answers[key];
      if (show && picked === question.answer) correctAnswers++;

      lessonHTML += `<h2 style="margin-top:15px; font-size:1.2rem;">Q. ${question.question}</h2>
        <div class="choices">
        ${question.choices.map((choice, index) => `<label class="quiz-choice ${show ? (index === question.answer ? "correct" : picked === index ? "incorrect" : "") : ""}"><input type="radio" name="${key}" value="${index}" ${picked === index ? "checked" : ""}> ${choice}</label>`).join("")}
        </div>
        ${show ? `<p class="feedback">${picked === question.answer ? "Correct. " : "Review this: "}${question.explanation}</p>` : ""}`;
    });
    lessonHTML += `</article>`;
    return lessonHTML;
  });

  const filterButtons = levels
    .map(
      (value) =>
        `<button class="${level === value ? "active" : ""}" data-quiz-level="${value}">${value}</button>`,
    )
    .join("");
  const score = show
    ? `<div class="score"><h2>${correctAnswers} / ${totalQuestions}</h2><p>Use the explanations to revisit the related lesson in the Hub.</p><a class="button" href="../">Return to the Learning Hub ↗</a></div>`
    : "";

  mount.innerHTML = `<div class="filters" aria-label="Filter quiz by course level">${filterButtons}</div><p class="progress">${totalQuestions} questions in this view</p>${items.join("")}<button class="button" id="grade">Grade this view</button>${score}`;
  mount.querySelectorAll("[data-quiz-level]").forEach((button) => {
    button.onclick = () => {
      level = button.dataset.quizLevel;
      render(false);
    };
  });
  mount.querySelectorAll("input").forEach((input) => {
    input.onchange = () => {
      answers[input.name] = Number(input.value);
    };
  });
  mount.querySelector("#grade").onclick = () => render(true);
}

render();
