.PHONY: setup setup-contributor test course-01 course-02 course-03 clean

setup:
	uv venv
	uv pip install -e .

setup-contributor:
	uv venv
	uv pip install -e '.[contributor]'

test:
	uv run pytest

course-01:
	uv run python scripts/execute-notebooks.py curriculum/beginner/01-from-ai-governance-to-agent-governance/01_from_ai_governance_to_agent_governance.ipynb
	uv run pytest -q tests/test_module01_governance.py tests/test_notebooks.py::test_course_01_notebook_executes_top_to_bottom

course-02:
	uv run python scripts/execute-notebooks.py curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/02_agent_risk_modeling_and_autonomy_classification.ipynb
	uv run pytest -q tests/test_module02_risk_modeling.py tests/test_notebooks.py::test_course_02_notebook_executes_top_to_bottom

course-03:
	uv run python scripts/execute-notebooks.py curriculum/beginner/03-standards-regulation-and-governance-operating-model/03_standards_regulation_and_governance_operating_model.ipynb
	uv run pytest -q tests/test_module03_governance_operating_model.py tests/test_notebooks.py::test_course_03_notebook_executes_top_to_bottom

clean:
	rm -rf .venv
