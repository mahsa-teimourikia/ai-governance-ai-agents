import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]


def execute_notebook(path: Path, monkeypatch):
    document = json.loads(path.read_text(encoding="utf-8"))
    namespace = {"__name__": "__main__"}
    monkeypatch.chdir(ROOT)
    sys.modules.pop("lab", None)
    for index, cell in enumerate(document["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        exec(compile(source, f"{path.name}:cell-{index}", "exec"), namespace)


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
    execute_notebook(path, monkeypatch)


def test_course_02_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the second fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification"
        / "02_agent_risk_modeling_and_autonomy_classification.ipynb"
    )
    execute_notebook(path, monkeypatch)
