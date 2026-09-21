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


def test_course_01_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the first fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/beginner/01-from-ai-governance-to-agent-governance"
        / "01_from_ai_governance_to_agent_governance.ipynb"
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    namespace = {"__name__": "__main__"}
    monkeypatch.chdir(ROOT)

    for index, cell in enumerate(document["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        exec(compile(source, f"{path.name}:cell-{index}", "exec"), namespace)
