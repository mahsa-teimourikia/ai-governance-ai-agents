"""Static checks for the GitHub Pages learning experience."""

import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parents[1]


def test_every_course_topic_is_present_in_hub():
    lessons = (ROOT / "hub" / "lessons.js").read_text()
    # Find all "id": "b1" inside the lessons array.
    lesson_ids = re.findall(r'"id":\s*"([^"]+)"', lessons)
    assert len(lesson_ids) == 17
    assert len(set(lesson_ids)) == 17
    for level in ("beginner", "intermediate", "advanced"):
        assert (ROOT / "curriculum" / level).is_dir()


def test_quiz_has_comprehensive_questions():
    lessons = (ROOT / "hub" / "lessons.js").read_text()
    # Count occurrences of "question": "..."
    questions = re.findall(r'"question":\s*"([^"]+)"', lessons)
    assert len(questions) == 55
    assert len(set(questions)) == len(questions)


def test_learning_registry_quizzes_and_local_links_are_valid():
    result = subprocess.run(
        ["node", "scripts/validate-learning-links.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "17 lessons, 55 checkpoint questions, 17 notebooks" in result.stdout


def test_hub_copy_matches_the_completed_curriculum():
    hub = (ROOT / "hub" / "index.html").read_text()
    app = (ROOT / "hub" / "app.js").read_text()
    quiz = (ROOT / "hub" / "quiz" / "index.html").read_text()
    quiz_app = (ROOT / "hub" / "quiz" / "quiz.js").read_text()
    assert "complete, evidence-led curriculum" in hub
    assert "17 PUBLISHED LESSONS" in hub
    assert '"Enterprise"' not in app
    assert 'id="question-count">55<' in quiz
    assert "Object.values(checks)" in quiz_app
    assert "data-quiz-level" in quiz_app


def test_js_modules_are_valid_syntax():
    for file_path in ["lessons.js", "app.js", "quiz/quiz.js"]:
        result = subprocess.run(
            ["node", "--check", file_path],
            cwd=ROOT / "hub",
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{file_path} failed: {result.stderr}"


def test_every_course_diagram_has_accessible_text():
    diagrams = sorted((ROOT / "curriculum").glob("**/*.svg"))
    assert len(diagrams) >= 69
    namespace = "{http://www.w3.org/2000/svg}"
    for path in diagrams:
        root = ET.parse(path).getroot()
        title = root.find(f"{namespace}title")
        description = root.find(f"{namespace}desc")
        assert title is not None and (title.text or "").strip(), f"{path} lacks a title"
        assert description is not None and (description.text or "").strip(), (
            f"{path} lacks a description"
        )
