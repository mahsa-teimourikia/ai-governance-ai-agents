import json
from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_every_course_notebook_is_valid():
    notebooks = sorted((ROOT / "curriculum").glob("**/*.ipynb"))
    assert len(notebooks) >= 17
    for path in notebooks:
        with open(path, "r", encoding="utf-8") as f:
            document = json.load(f)
        assert "cells" in document
        assert len(document["cells"]) >= 1
