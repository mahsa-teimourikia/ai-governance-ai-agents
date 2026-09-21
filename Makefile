.PHONY: setup setup-contributor test course-01 clean

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

clean:
	rm -rf .venv
