import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { checks, lessons } from "../hub/lessons.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const tracked = execFileSync("git", ["ls-files"], {
  cwd: root,
  encoding: "utf8",
})
  .trim()
  .split("\n")
  .filter(Boolean);
const trackedSet = new Set(tracked);
const errors = [];
let localLinkCount = 0;

function report(message) {
  errors.push(message);
}

function validateExternalUrl(value, label) {
  try {
    const parsed = new URL(value);
    if (!["https:", "http:"].includes(parsed.protocol)) {
      report(`${label}: unsupported external protocol ${parsed.protocol}`);
    }
  } catch {
    report(`${label}: invalid external URL ${value}`);
  }
}

function validateLocalTarget(baseDirectory, target, label) {
  if (!target || target.startsWith("#")) return;
  if (/^(https?:|mailto:|tel:|data:)/i.test(target)) return;

  const withoutFragment = target.split("#", 1)[0].split("?", 1)[0];
  if (!withoutFragment) return;

  let decoded;
  try {
    decoded = decodeURIComponent(withoutFragment);
  } catch {
    report(`${label}: invalid URL encoding in ${target}`);
    return;
  }

  const destination = resolve(baseDirectory, decoded);
  const relativeToRoot = relative(root, destination);
  if (relativeToRoot.startsWith("..")) {
    report(`${label}: local target escapes the repository: ${target}`);
    return;
  }

  if (!existsSync(destination)) {
    report(`${label}: missing local target ${target}`);
    return;
  }
  localLinkCount += 1;
}

function validateMarkup(source, baseDirectory, label) {
  const markdownLink = /!?\[[^\]]*\]\(([^)\s]+)(?:\s+["'][^)]*["'])?\)/g;
  const htmlLink = /(?:href|src)=["']([^"']+)["']/g;
  for (const pattern of [markdownLink, htmlLink]) {
    for (const match of source.matchAll(pattern)) {
      validateLocalTarget(baseDirectory, match[1], label);
    }
  }
}

const markdownFiles = tracked.filter((path) => path.endsWith(".md"));
for (const path of markdownFiles) {
  validateMarkup(
    readFileSync(resolve(root, path), "utf8"),
    dirname(resolve(root, path)),
    path,
  );
}

const notebookFiles = tracked.filter((path) => path.endsWith(".ipynb"));
for (const path of notebookFiles) {
  const notebook = JSON.parse(readFileSync(resolve(root, path), "utf8"));
  for (const [index, cell] of notebook.cells.entries()) {
    if (cell.cell_type === "markdown") {
      validateMarkup(
        cell.source.join(""),
        dirname(resolve(root, path)),
        `${path}:cell-${index}`,
      );
    }
  }
}

for (const path of tracked.filter(
  (item) => item.startsWith("hub/") && item.endsWith(".html"),
)) {
  validateMarkup(
    readFileSync(resolve(root, path), "utf8"),
    dirname(resolve(root, path)),
    path,
  );
}

if (lessons.length !== 17) {
  report(`lesson registry: expected 17 lessons, found ${lessons.length}`);
}
const lessonIds = new Set();
const lessonSteps = new Set();
const questions = new Set();
let questionCount = 0;

for (const lesson of lessons) {
  if (lessonIds.has(lesson.id)) report(`lesson registry: duplicate id ${lesson.id}`);
  if (lessonSteps.has(lesson.step)) {
    report(`lesson registry: duplicate step ${lesson.step}`);
  }
  lessonIds.add(lesson.id);
  lessonSteps.add(lesson.step);

  for (const field of [
    "id",
    "level",
    "step",
    "title",
    "summary",
    "outcome",
    "material",
    "notebook",
    "lab",
    "run",
    "refs",
  ]) {
    if (!lesson[field]) report(`lesson ${lesson.id}: missing ${field}`);
  }

  for (const field of ["material", "lab"]) {
    if (lesson[field]) {
      validateLocalTarget(root, lesson[field], `lesson ${lesson.id}.${field}`);
    }
  }
  const notebooks = Array.isArray(lesson.notebook)
    ? lesson.notebook.map((item) => item.path)
    : [lesson.notebook];
  for (const notebook of notebooks.filter(Boolean)) {
    validateLocalTarget(root, notebook, `lesson ${lesson.id}.notebook`);
  }
  for (const [index, reference] of (lesson.refs || []).entries()) {
    const target = reference.path || reference;
    if (/^https?:/i.test(target)) {
      validateExternalUrl(target, `lesson ${lesson.id}.refs[${index}]`);
    } else {
      validateLocalTarget(root, target, `lesson ${lesson.id}.refs[${index}]`);
    }
  }

  const courseChecks = checks[lesson.id] || [];
  if (courseChecks.length < 3) {
    report(`lesson ${lesson.id}: expected at least 3 checkpoint questions`);
  }
  for (const [index, check] of courseChecks.entries()) {
    questionCount += 1;
    const label = `lesson ${lesson.id} question ${index + 1}`;
    if (!check.question?.trim()) report(`${label}: missing question text`);
    if (questions.has(check.question)) report(`${label}: duplicate question text`);
    questions.add(check.question);
    if (!Array.isArray(check.choices) || check.choices.length < 3) {
      report(`${label}: expected at least 3 choices`);
    }
    if (
      !Number.isInteger(check.answer) ||
      check.answer < 0 ||
      check.answer >= check.choices.length
    ) {
      report(`${label}: answer index is outside the choices`);
    }
    if (!check.explanation?.trim()) report(`${label}: missing explanation`);
  }
}

for (const key of Object.keys(checks)) {
  if (!lessonIds.has(key)) report(`checkpoint registry: unknown lesson id ${key}`);
}

const courseReadmes = tracked.filter((path) =>
  /^curriculum\/(beginner|intermediate|advanced)\/[^/]+\/README\.md$/.test(
    path,
  ),
);
for (const readme of courseReadmes) {
  const directory = dirname(readme);
  const notebooks = tracked.filter(
    (path) => dirname(path) === directory && path.endsWith(".ipynb"),
  );
  if (!trackedSet.has(`${directory}/lab.py`)) {
    report(`${directory}: missing tracked lab.py`);
  }
  if (notebooks.length !== 1) {
    report(`${directory}: expected one tracked notebook, found ${notebooks.length}`);
  }
  if (!lessons.some((lesson) => lesson.material === readme)) {
    report(`${directory}: missing from lesson registry`);
  }
}

if (errors.length) {
  console.error(
    `Learning-material validation failed with ${errors.length} issue(s):`,
  );
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  console.log(
    `Validated ${lessons.length} lessons, ${questionCount} checkpoint questions, ${notebookFiles.length} notebooks, and ${localLinkCount} local links.`,
  );
}
