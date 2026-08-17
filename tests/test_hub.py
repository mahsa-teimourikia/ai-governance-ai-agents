"""Static checks for the GitHub Pages learning experience."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_every_course_topic_is_present_in_hub():
    lessons = (ROOT / "hub" / "lessons.js").read_text()
    lesson_ids = re.findall(r'id:\s*"([^"]+)"', lessons)
    assert len(lesson_ids) == 17
    assert len(set(lesson_ids)) == 17
    for level in ("beginner", "intermediate", "advanced"):
        assert (ROOT / "curriculum" / level).is_dir()

def test_quiz_has_comprehensive_questions():
    questions = (ROOT / "hub" / "quiz" / "questions.js").read_text()
    question_ids = re.findall(r'id:\s*"([^"]+)"', questions)
    assert len(question_ids) == 34
    assert len(set(question_ids)) == 34

def test_js_modules_are_valid_syntax():
    # Only tests files that don't depend heavily on DOM being present or can parse without DOM
    # (Since `app.js` runs document.addEventListener, we skip it here as it requires a DOM).
    for file_path in ["lessons.js", "quiz/questions.js"]:
        source = (ROOT / "hub" / file_path).read_text()
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", source],
            cwd=ROOT / "hub" if "quiz" not in file_path else ROOT / "hub" / "quiz",
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{file_path} failed: {result.stderr}"
