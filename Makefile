.PHONY: setup setup-contributor test course-01 course-02 course-03 course-04 course-05 course-06 course-07 course-08 course-09 course-10 clean

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

course-04:
	uv run python scripts/execute-notebooks.py curriculum/beginner/04-agent-identity-and-delegated-authority/04_agent_identity_and_delegated_authority.ipynb
	uv run pytest -q tests/test_module04_agent_identity.py tests/test_notebooks.py::test_course_04_notebook_executes_top_to_bottom

course-05:
	uv run python scripts/execute-notebooks.py curriculum/beginner/05-fine-grained-authorization-for-agents/05_fine_grained_authorization_for_agents.ipynb
	uv run pytest -q tests/test_module05_fine_grained_authorization.py tests/test_notebooks.py::test_course_05_notebook_executes_top_to_bottom

course-06:
	uv run python scripts/execute-notebooks.py curriculum/intermediate/06-policy-as-code-and-runtime-governance/06_policy_as_code_and_runtime_governance.ipynb
	uv run pytest -q tests/test_module06_runtime_policy.py tests/test_notebooks.py::test_course_06_notebook_executes_top_to_bottom

course-07:
	uv run python scripts/execute-notebooks.py curriculum/intermediate/07-tool-and-mcp-governance/07_tool_and_mcp_governance.ipynb
	uv run pytest -q tests/test_module07_tool_mcp_governance.py tests/test_notebooks.py::test_course_07_notebook_executes_top_to_bottom

course-08:
	uv run python scripts/execute-notebooks.py curriculum/intermediate/08-human-oversight-and-bounded-autonomy/08_human_oversight_and_bounded_autonomy.ipynb
	uv run pytest -q tests/test_module08_human_oversight.py tests/test_notebooks.py::test_course_08_notebook_executes_top_to_bottom

course-09:
	uv run python scripts/execute-notebooks.py curriculum/intermediate/09-data-rag-and-memory-governance/09_data_rag_and_memory_governance.ipynb
	uv run pytest -q tests/test_module09_data_rag_memory.py tests/test_notebooks.py::test_course_09_notebook_executes_top_to_bottom

course-10:
	uv run python scripts/execute-notebooks.py curriculum/intermediate/10-multi-agent-governance-and-delegation/10_multi_agent_governance_and_delegation.ipynb
	uv run pytest -q tests/test_module10_multi_agent_governance.py tests/test_notebooks.py::test_course_10_notebook_executes_top_to_bottom

clean:
	rm -rf .venv
