.PHONY: setup setup-contributor serve-hub validate test course-01 course-02 course-03 course-04 course-05 course-06 course-07 course-08 course-09 course-10 course-11 course-12 course-13 course-14 course-15 course-16 course-17 clean

setup:
	uv sync --locked

setup-contributor:
	uv sync --locked --extra contributor

serve-hub:
	uv run --locked python -m http.server 8000 --directory hub

validate:
	uv lock --check
	uv pip check
	node --check hub/lessons.js
	node --check hub/app.js
	node --check hub/quiz/quiz.js
	node scripts/validate-learning-links.mjs
	uv run --locked pytest

test:
	uv run --locked pytest

course-01:
	uv run --locked python scripts/execute-notebooks.py curriculum/beginner/01-from-ai-governance-to-agent-governance/01_from_ai_governance_to_agent_governance.ipynb
	uv run --locked pytest -q tests/test_module01_governance.py tests/test_notebooks.py::test_course_01_notebook_executes_top_to_bottom

course-02:
	uv run --locked python scripts/execute-notebooks.py curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/02_agent_risk_modeling_and_autonomy_classification.ipynb
	uv run --locked pytest -q tests/test_module02_risk_modeling.py tests/test_notebooks.py::test_course_02_notebook_executes_top_to_bottom

course-03:
	uv run --locked python scripts/execute-notebooks.py curriculum/beginner/03-standards-regulation-and-governance-operating-model/03_standards_regulation_and_governance_operating_model.ipynb
	uv run --locked pytest -q tests/test_module03_governance_operating_model.py tests/test_notebooks.py::test_course_03_notebook_executes_top_to_bottom

course-04:
	uv run --locked python scripts/execute-notebooks.py curriculum/beginner/04-agent-identity-and-delegated-authority/04_agent_identity_and_delegated_authority.ipynb
	uv run --locked pytest -q tests/test_module04_agent_identity.py tests/test_notebooks.py::test_course_04_notebook_executes_top_to_bottom

course-05:
	uv run --locked python scripts/execute-notebooks.py curriculum/beginner/05-fine-grained-authorization-for-agents/05_fine_grained_authorization_for_agents.ipynb
	uv run --locked pytest -q tests/test_module05_fine_grained_authorization.py tests/test_notebooks.py::test_course_05_notebook_executes_top_to_bottom

course-06:
	uv run --locked python scripts/execute-notebooks.py curriculum/intermediate/06-policy-as-code-and-runtime-governance/06_policy_as_code_and_runtime_governance.ipynb
	uv run --locked pytest -q tests/test_module06_runtime_policy.py tests/test_notebooks.py::test_course_06_notebook_executes_top_to_bottom

course-07:
	uv run --locked python scripts/execute-notebooks.py curriculum/intermediate/07-tool-and-mcp-governance/07_tool_and_mcp_governance.ipynb
	uv run --locked pytest -q tests/test_module07_tool_mcp_governance.py tests/test_notebooks.py::test_course_07_notebook_executes_top_to_bottom

course-08:
	uv run --locked python scripts/execute-notebooks.py curriculum/intermediate/08-human-oversight-and-bounded-autonomy/08_human_oversight_and_bounded_autonomy.ipynb
	uv run --locked pytest -q tests/test_module08_human_oversight.py tests/test_notebooks.py::test_course_08_notebook_executes_top_to_bottom

course-09:
	uv run --locked python scripts/execute-notebooks.py curriculum/intermediate/09-data-rag-and-memory-governance/09_data_rag_and_memory_governance.ipynb
	uv run --locked pytest -q tests/test_module09_data_rag_memory.py tests/test_notebooks.py::test_course_09_notebook_executes_top_to_bottom

course-10:
	uv run --locked python scripts/execute-notebooks.py curriculum/intermediate/10-multi-agent-governance-and-delegation/10_multi_agent_governance_and_delegation.ipynb
	uv run --locked pytest -q tests/test_module10_multi_agent_governance.py tests/test_notebooks.py::test_course_10_notebook_executes_top_to_bottom

course-11:
	uv run --locked python scripts/execute-notebooks.py curriculum/intermediate/11-guardrails-and-agent-security/11_guardrails_and_agent_security.ipynb
	uv run --locked pytest -q tests/test_module11_guardrails_security.py tests/test_notebooks.py::test_course_11_notebook_executes_top_to_bottom

course-12:
	uv run --locked python scripts/execute-notebooks.py curriculum/intermediate/12-agent-red-teaming-and-adversarial-testing/12_agent_red_teaming_and_adversarial_testing.ipynb
	uv run --locked pytest -q tests/test_module12_agent_red_teaming.py tests/test_notebooks.py::test_course_12_notebook_executes_top_to_bottom

course-13:
	uv run --locked python scripts/execute-notebooks.py curriculum/advanced/13-observability-as-governance-evidence/13_observability_as_governance_evidence.ipynb
	uv run --locked pytest -q tests/test_module13_observability_evidence.py tests/test_notebooks.py::test_course_13_notebook_executes_top_to_bottom

course-14:
	uv run --locked python scripts/execute-notebooks.py curriculum/advanced/14-agent-evaluation-and-continuous-governance/14_agent_evaluation_and_continuous_governance.ipynb
	uv run --locked pytest -q tests/test_module14_agent_evaluation.py tests/test_notebooks.py::test_course_14_notebook_executes_top_to_bottom

course-15:
	uv run --locked python scripts/execute-notebooks.py curriculum/advanced/15-governance-control-plane-architecture/15_governance_control_plane_architecture.ipynb
	uv run --locked pytest -q tests/test_module15_governance_control_plane.py tests/test_notebooks.py::test_course_15_notebook_executes_top_to_bottom

course-16:
	uv run --locked python scripts/execute-notebooks.py curriculum/advanced/16-enterprise-agent-governance-operating-model/16_enterprise_agent_governance_operating_model.ipynb
	uv run --locked pytest -q tests/test_module16_enterprise_operating_model.py tests/test_notebooks.py::test_course_16_notebook_executes_top_to_bottom

course-17:
	uv run --locked python scripts/execute-notebooks.py curriculum/advanced/17-capstone-governed-autonomous-enterprise-agent/17_capstone_governed_autonomous_enterprise_agent.ipynb
	uv run --locked pytest -q tests/test_module17_governed_enterprise_capstone.py tests/test_notebooks.py::test_course_17_notebook_executes_top_to_bottom

clean:
	rm -rf .venv
