import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]


def execute_notebook(path: Path, monkeypatch):
    document = json.loads(path.read_text(encoding="utf-8"))
    namespace = {"__name__": "__main__"}
    monkeypatch.chdir(ROOT)
    sys.modules.pop("lab", None)
    module_path = str(path.parent)
    if module_path in sys.path:
        sys.path.remove(module_path)
    sys.path.insert(0, module_path)
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


def test_course_03_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the third fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/beginner/03-standards-regulation-and-governance-operating-model"
        / "03_standards_regulation_and_governance_operating_model.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_04_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the fourth fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/beginner/04-agent-identity-and-delegated-authority"
        / "04_agent_identity_and_delegated_authority.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_05_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the fifth fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/beginner/05-fine-grained-authorization-for-agents"
        / "05_fine_grained_authorization_for_agents.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_06_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the sixth fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/intermediate/06-policy-as-code-and-runtime-governance"
        / "06_policy_as_code_and_runtime_governance.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_07_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the seventh fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/intermediate/07-tool-and-mcp-governance"
        / "07_tool_and_mcp_governance.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_08_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the eighth fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/intermediate/08-human-oversight-and-bounded-autonomy"
        / "08_human_oversight_and_bounded_autonomy.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_09_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the ninth fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/intermediate/09-data-rag-and-memory-governance"
        / "09_data_rag_and_memory_governance.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_10_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the tenth fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/intermediate/10-multi-agent-governance-and-delegation"
        / "10_multi_agent_governance_and_delegation.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_11_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the eleventh fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/intermediate/11-guardrails-and-agent-security"
        / "11_guardrails_and_agent_security.ipynb"
    )
    execute_notebook(path, monkeypatch)


def test_course_12_notebook_executes_top_to_bottom(monkeypatch):
    """Execute the twelfth fully audited notebook without a Jupyter server."""

    path = (
        ROOT
        / "curriculum/intermediate/12-agent-red-teaming-and-adversarial-testing"
        / "12_agent_red_teaming_and_adversarial_testing.ipynb"
    )
    execute_notebook(path, monkeypatch)
