"""Static checks for the GitHub Pages learning experience."""

import re
import subprocess
from pathlib import Path

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
    assert len(questions) == 51

def test_js_modules_are_valid_syntax():
    # Only tests files that don't depend heavily on DOM being present
    for file_path in ["lessons.js"]:
        source = (ROOT / "hub" / file_path).read_text()
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", source],
            cwd=ROOT / "hub",
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{file_path} failed: {result.stderr}"
