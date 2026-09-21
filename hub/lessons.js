export const lessons = [
  {
    "id": "b1",
    "level": "Beginner",
    "step": 1,
    "title": "From AI Governance to Agent Governance",
    "summary": "Move from model review to enforceable runtime control over agent actions.",
    "outcome": "Map the complete agent system, enforce its consequence boundary, and evaluate the control with labelled cases.",
    "material": "curriculum/beginner/01-from-ai-governance-to-agent-governance/README.md",
    "notebook": "curriculum/beginner/01-from-ai-governance-to-agent-governance/01_from_ai_governance_to_agent_governance.ipynb",
    "lab": "curriculum/beginner/01-from-ai-governance-to-agent-governance/lab.py",
    "run": "make course-01",
    "refs": [
      {
        "title": "NIST AI Risk Management Framework 1.0",
        "path": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10"
      },
      {
        "title": "https://airc.nist.gov/airmf-resources/airmf/5-sec-core/",
        "path": "https://airc.nist.gov/airmf-resources/airmf/5-sec-core/"
      },
      {
        "title": "https://airc.nist.gov/airmf-resources/playbook/",
        "path": "https://airc.nist.gov/airmf-resources/playbook/"
      },
      {
        "title": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
        "path": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence"
      },
      {
        "title": "NIST AI Agent Standards Initiative",
        "path": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative"
      },
      {
        "title": "NIST NCCoE: Software and AI Agent Identity and Authorization",
        "path": "https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd"
      },
      {
        "title": "NIST AI 800-5: Security Considerations for AI Agents",
        "path": "https://www.nist.gov/publications/summary-analysis-responses-request-information-regarding-security-considerations-ai"
      },
      {
        "title": "https://www.iso.org/standard/42001",
        "path": "https://www.iso.org/standard/42001"
      },
      {
        "title": "https://genai.owasp.org/initiatives/agentic-security-initiative/",
        "path": "https://genai.owasp.org/initiatives/agentic-security-initiative/"
      },
      {
        "title": "OWASP Top 10 for Agentic Applications 2026",
        "path": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"
      },
      {
        "title": "OpenFGA: Task-Based Authorization for Agents",
        "path": "https://openfga.dev/docs/modeling/agents/task-based-authorization"
      },
      {
        "title": "OpenAI Agents SDK: Human-in-the-Loop",
        "path": "https://openai.github.io/openai-agents-python/human_in_the_loop/"
      },
      {
        "title": "https://airc.nist.gov/airmf-resources/playbook/govern/",
        "path": "https://airc.nist.gov/airmf-resources/playbook/govern/"
      },
      {
        "title": "https://airc.nist.gov/airmf-resources/playbook/map/",
        "path": "https://airc.nist.gov/airmf-resources/playbook/map/"
      }
    ]
  },
  {
    "id": "b2",
    "level": "Beginner",
    "step": 2,
    "title": "Agent Risk Modeling and Autonomy Classification",
    "summary": "Classify autonomy and risk without hiding assumptions behind false precision.",
    "outcome": "Build evidence-aware scenarios, inspect blast radius, and translate inherent risk into defensible control and review requirements.",
    "material": "curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/README.md",
    "notebook": "curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/02_agent_risk_modeling_and_autonomy_classification.ipynb",
    "lab": "curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/lab.py",
    "run": "make course-02",
    "refs": [
      {
        "title": "NIST AI Risk Management Framework",
        "path": "https://www.nist.gov/itl/ai-risk-management-framework"
      },
      {
        "title": "https://airc.nist.gov/airmf-resources/airmf/",
        "path": "https://airc.nist.gov/airmf-resources/airmf/"
      },
      {
        "title": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
        "path": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence"
      },
      {
        "title": "https://www.iso.org/standard/77304.html",
        "path": "https://www.iso.org/standard/77304.html"
      },
      {
        "title": "NIST AI 100-2e2025: Adversarial ML Taxonomy",
        "path": "https://csrc.nist.gov/pubs/ai/100/2/e2025/final"
      },
      {
        "title": "OWASP Top 10 for Agentic Applications 2026",
        "path": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"
      },
      {
        "title": "https://genai.owasp.org/initiatives/agentic-security-initiative/",
        "path": "https://genai.owasp.org/initiatives/agentic-security-initiative/"
      },
      {
        "title": "MITRE ATLAS",
        "path": "https://atlas.mitre.org/"
      },
      {
        "title": "NIST AI 800-5: Security Considerations for AI Agents",
        "path": "https://www.nist.gov/publications/summary-analysis-responses-request-information-regarding-security-considerations-ai"
      },
      {
        "title": "NetworkX documentation",
        "path": "https://networkx.org/documentation/stable/"
      },
      {
        "title": "PyRIT documentation",
        "path": "https://azure.github.io/PyRIT/"
      }
    ]
  },
  {
    "id": "b3",
    "level": "Beginner",
    "step": 3,
    "title": "Standards Regulation and Governance Operating Model",
    "summary": "Turn NIST, ISO, EU, OWASP, and OSCAL inputs into owned controls, current evidence, specialist review, and lifecycle decisions.",
    "outcome": "Build and test a version-bound governance package with accountable RACI, exact evidence gates, bounded exceptions, and change-triggered recertification.",
    "material": "curriculum/beginner/03-standards-regulation-and-governance-operating-model/README.md",
    "notebook": "curriculum/beginner/03-standards-regulation-and-governance-operating-model/03_standards_regulation_and_governance_operating_model.ipynb",
    "lab": "curriculum/beginner/03-standards-regulation-and-governance-operating-model/lab.py",
    "run": "make course-03",
    "refs": [
      {
        "title": "NIST AI Risk Management Framework",
        "path": "https://www.nist.gov/itl/ai-risk-management-framework"
      },
      {
        "title": "NIST AI RMF crosswalks",
        "path": "https://airc.nist.gov/airmf-resources/crosswalks/"
      },
      {
        "title": "NIST AI RMF Generative AI Profile",
        "path": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence"
      },
      {
        "title": "NIST OSCAL",
        "path": "https://pages.nist.gov/OSCAL/"
      },
      {
        "title": "ISO/IEC 42001:2023",
        "path": "https://www.iso.org/standard/42001"
      },
      {
        "title": "ISO/IEC 42005:2025",
        "path": "https://www.iso.org/standard/42005"
      },
      {
        "title": "ISO/IEC 42006:2025",
        "path": "https://www.iso.org/standard/42006"
      },
      {
        "title": "ISO/IEC 23894:2023",
        "path": "https://www.iso.org/standard/77304.html"
      },
      {
        "title": "European Commission AI Act FAQ",
        "path": "https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act"
      },
      {
        "title": "European Commission AI Act overview and timeline",
        "path": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"
      },
      {
        "title": "European Commission AI Act enforcement",
        "path": "https://digital-strategy.ec.europa.eu/en/policies/enforcement-ai-act"
      },
      {
        "title": "European Commission AI Act standardisation",
        "path": "https://digital-strategy.ec.europa.eu/en/policies/ai-act-standardisation"
      },
      {
        "title": "OWASP Agentic Security Initiative",
        "path": "https://genai.owasp.org/initiatives/agentic-security-initiative/"
      },
      {
        "title": "OWASP Top 10 for Agentic Applications 2026",
        "path": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"
      },
      {
        "title": "NIST AI 100-2e2025: Adversarial ML Taxonomy",
        "path": "https://csrc.nist.gov/pubs/ai/100/2/e2025/final"
      },
      {
        "title": "MITRE ATLAS",
        "path": "https://atlas.mitre.org/"
      },
      {
        "title": "NIST OSCAL release notes",
        "path": "https://pages.nist.gov/OSCAL/about/blog/"
      },
      {
        "title": "Compliance Trestle",
        "path": "https://github.com/oscal-compass/compliance-trestle"
      },
      {
        "title": "Compliance Trestle releases",
        "path": "https://github.com/oscal-compass/compliance-trestle/releases"
      },
      {
        "title": "IIA Three Lines statements",
        "path": "https://www.theiia.org/en/resources/statements-of-position"
      }
    ]
  },
  {
    "id": "b4",
    "level": "Beginner",
    "step": 4,
    "title": "Agent Identity and Delegated Authority",
    "summary": "Bind authenticated humans, versioned logical agents, and attested workloads to narrow task authority that is verified, atomically consumed, attenuated, revoked, and evidenced.",
    "outcome": "Implement and test an intent-bound delegated-authority chain with strict token validation, trusted context, idempotent operations, concurrency-safe call limits, and descendant revocation.",
    "material": "curriculum/beginner/04-agent-identity-and-delegated-authority/README.md",
    "notebook": "curriculum/beginner/04-agent-identity-and-delegated-authority/04_agent_identity_and_delegated_authority.ipynb",
    "lab": "curriculum/beginner/04-agent-identity-and-delegated-authority/lab.py",
    "run": "make course-04",
    "refs": [
      {
        "title": "NIST NCCoE: Software and AI Agent Identity and Authorization",
        "path": "https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd"
      },
      {
        "title": "NIST AI Agent Standards Initiative",
        "path": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative"
      },
      {
        "title": "OpenFGA authorization for agents",
        "path": "https://openfga.dev/docs/modeling/agents"
      },
      {
        "title": "OpenFGA task-based authorization",
        "path": "https://openfga.dev/docs/modeling/agents/task-based-authorization"
      },
      {
        "title": "OpenFGA Python SDK",
        "path": "https://openfga.dev/docs/getting-started/install-sdk"
      },
      {
        "title": "SPIFFE standards",
        "path": "https://spiffe.io/docs/latest/spiffe-specs/spiffe/"
      },
      {
        "title": "SPIFFE Workload API",
        "path": "https://spiffe.io/docs/latest/spiffe-specs/spiffe_workload_api/"
      },
      {
        "title": "SPIRE concepts",
        "path": "https://spiffe.io/docs/latest/spire-about/spire-concepts/"
      },
      {
        "title": "RFC 8693: OAuth 2.0 Token Exchange",
        "path": "https://datatracker.ietf.org/doc/rfc8693/"
      },
      {
        "title": "RFC 9700: OAuth 2.0 Security Best Current Practice",
        "path": "https://datatracker.ietf.org/doc/rfc9700/"
      },
      {
        "title": "RFC 8707: OAuth 2.0 Resource Indicators",
        "path": "https://datatracker.ietf.org/doc/rfc8707/"
      },
      {
        "title": "RFC 8725: JSON Web Token Best Current Practices",
        "path": "https://datatracker.ietf.org/doc/rfc8725/"
      },
      {
        "title": "RFC 9068: JWT Profile for OAuth 2.0 Access Tokens",
        "path": "https://datatracker.ietf.org/doc/rfc9068/"
      },
      {
        "title": "RFC 9396: OAuth 2.0 Rich Authorization Requests",
        "path": "https://datatracker.ietf.org/doc/rfc9396/"
      },
      {
        "title": "RFC 9449: OAuth 2.0 Demonstrating Proof of Possession",
        "path": "https://datatracker.ietf.org/doc/rfc9449/"
      },
      {
        "title": "IETF WIMSE working group",
        "path": "https://datatracker.ietf.org/wg/wimse/"
      },
      {
        "title": "IETF draft: AI Identity Management System",
        "path": "https://datatracker.ietf.org/doc/draft-ietf-wimse-aims/"
      },
      {
        "title": "Cedar authorization documentation",
        "path": "https://docs.cedarpolicy.com/"
      },
      {
        "title": "Amazon Verified Permissions",
        "path": "https://docs.aws.amazon.com/verifiedpermissions/"
      },
      {
        "title": "Amazon Bedrock AgentCore Policy",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html"
      },
      {
        "title": "Open Policy Agent documentation",
        "path": "https://www.openpolicyagent.org/docs/policy-language"
      },
      {
        "title": "PyJWT documentation",
        "path": "https://pyjwt.readthedocs.io/"
      }
    ]
  },
  {
    "id": "b5",
    "level": "Beginner",
    "step": 5,
    "title": "Fine Grained Authorization for Agents",
    "summary": "Compose user/resource relationships, task/agent authority, current attributes, narrow approvals, and effect-bound enforcement into one observable decision.",
    "outcome": "Implement and test a default-deny procurement PDP/PEP with OpenFGA request mappings, Cedar/Rego artifacts, atomic limits, idempotency, and explicit safety metrics.",
    "material": "curriculum/beginner/05-fine-grained-authorization-for-agents/README.md",
    "notebook": "curriculum/beginner/05-fine-grained-authorization-for-agents/05_fine_grained_authorization_for_agents.ipynb",
    "lab": "curriculum/beginner/05-fine-grained-authorization-for-agents/lab.py",
    "run": "make course-05",
    "refs": [
      {
        "title": "NIST Role-Based Access Control",
        "path": "https://csrc.nist.gov/projects/role-based-access-control"
      },
      {
        "title": "NIST SP 800-162 Attribute-Based Access Control",
        "path": "https://csrc.nist.gov/pubs/sp/800/162/upd2/final"
      },
      {
        "title": "Zanzibar authorization system paper",
        "path": "https://www.usenix.org/conference/atc19/presentation/pang"
      },
      {
        "title": "OpenFGA authorization for agents",
        "path": "https://openfga.dev/docs/modeling/agents"
      },
      {
        "title": "OpenFGA task-based authorization",
        "path": "https://openfga.dev/docs/modeling/agents/task-based-authorization"
      },
      {
        "title": "OpenFGA agents as principals",
        "path": "https://openfga.dev/docs/modeling/agents/agents-as-principals"
      },
      {
        "title": "Cedar Policy Language",
        "path": "https://docs.cedarpolicy.com/"
      },
      {
        "title": "Open Policy Agent documentation",
        "path": "https://www.openpolicyagent.org/docs"
      },
      {
        "title": "OPA Rego policy language",
        "path": "https://www.openpolicyagent.org/docs/policy-language"
      },
      {
        "title": "Amazon Verified Permissions",
        "path": "https://docs.aws.amazon.com/verifiedpermissions/"
      },
      {
        "title": "Amazon Bedrock AgentCore Policy",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html"
      },
      {
        "title": "AutoCedar research paper",
        "path": "https://arxiv.org/abs/2607.03656"
      },
      {
        "title": "Prose2Policy research paper",
        "path": "https://arxiv.org/abs/2603.15799"
      },
      {
        "title": "FAVA research paper",
        "path": "https://arxiv.org/abs/2607.27267"
      }
    ]
  },
  {
    "id": "i1",
    "level": "Intermediate",
    "step": 6,
    "title": "Policy as Code and Runtime Governance",
    "summary": "Turn governance requirements into tested, versioned runtime controls without letting model claims become authority.",
    "outcome": "Build and evaluate a non-bypassable procurement policy control plane with trusted inputs, layered decisions, safe rollout, rollback, tenant-safe effects, and auditable evidence.",
    "material": "curriculum/intermediate/06-policy-as-code-and-runtime-governance/README.md",
    "notebook": "curriculum/intermediate/06-policy-as-code-and-runtime-governance/06_policy_as_code_and_runtime_governance.ipynb",
    "lab": "curriculum/intermediate/06-policy-as-code-and-runtime-governance/lab.py",
    "run": "make course-06",
    "refs": [
      {
        "title": "Cedar Policy Language reference",
        "path": "https://docs.cedarpolicy.com/"
      },
      {
        "title": "Cedar authorization semantics",
        "path": "https://docs.cedarpolicy.com/auth/authorization.html"
      },
      {
        "title": "Cedar policy validation",
        "path": "https://docs.cedarpolicy.com/policies/validation.html"
      },
      {
        "title": "Open Policy Agent documentation",
        "path": "https://www.openpolicyagent.org/docs"
      },
      {
        "title": "Rego policy language",
        "path": "https://www.openpolicyagent.org/docs/policy-language"
      },
      {
        "title": "OPA policy testing",
        "path": "https://www.openpolicyagent.org/docs/policy-testing"
      },
      {
        "title": "OPA policy bundles and signing",
        "path": "https://www.openpolicyagent.org/docs/management-bundles"
      },
      {
        "title": "OPA decision logs",
        "path": "https://www.openpolicyagent.org/docs/management-decision-logs"
      },
      {
        "title": "Amazon Bedrock AgentCore Policy",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html"
      },
      {
        "title": "AgentCore Policy core concepts and Dogwood",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html"
      },
      {
        "title": "AgentCore policy generation validation",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-generation-validation.html"
      },
      {
        "title": "Amazon Verified Permissions",
        "path": "https://docs.aws.amazon.com/verifiedpermissions/"
      }
    ]
  },
  {
    "id": "i2",
    "level": "Intermediate",
    "step": 7,
    "title": "Tool and MCP Governance",
    "summary": "Tools as capability boundaries.",
    "outcome": "MCP trust boundaries.",
    "material": "curriculum/intermediate/07-tool-and-mcp-governance/README.md",
    "notebook": "curriculum/intermediate/07-tool-and-mcp-governance/07_tool_and_mcp_governance.ipynb",
    "refs": [
      {
        "title": "https://blog.modelcontextprotocol.io/posts/2026-07-28/",
        "path": "https://blog.modelcontextprotocol.io/posts/2026-07-28/"
      },
      {
        "title": "https://modelcontextprotocol.io/specification/2026-07-28",
        "path": "https://modelcontextprotocol.io/specification/2026-07-28"
      },
      {
        "title": "https://owasp.org/www-project-mcp-top-10/",
        "path": "https://owasp.org/www-project-mcp-top-10/"
      },
      {
        "title": "https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure",
        "path": "https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure"
      },
      {
        "title": "https://www.nist.gov/publications/summary-analysis-responses-request-information-regarding-security-considerations-ai",
        "path": "https://www.nist.gov/publications/summary-analysis-responses-request-information-regarding-security-considerations-ai"
      },
      {
        "title": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html"
      },
      {
        "title": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html"
      },
      {
        "title": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-security-best-practices.html",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-security-best-practices.html"
      },
      {
        "title": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-http-passthrough.html",
        "path": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-http-passthrough.html"
      }
    ]
  },
  {
    "id": "i3",
    "level": "Intermediate",
    "step": 8,
    "title": "Human Oversight and Bounded Autonomy",
    "summary": "HITL vs HOTL.",
    "outcome": "Meaningful human control.",
    "material": "curriculum/intermediate/08-human-oversight-and-bounded-autonomy/README.md",
    "notebook": "curriculum/intermediate/08-human-oversight-and-bounded-autonomy/08_human_oversight_and_bounded_autonomy.ipynb",
    "refs": [
      {
        "title": "https://openai.github.io/openai-agents-python/human_in_the_loop/",
        "path": "https://openai.github.io/openai-agents-python/human_in_the_loop/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/running_agents/",
        "path": "https://openai.github.io/openai-agents-python/running_agents/"
      },
      {
        "title": "https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop",
        "path": "https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop"
      },
      {
        "title": "https://learn.microsoft.com/en-us/agent-framework/integrations/ag-ui/human-in-the-loop",
        "path": "https://learn.microsoft.com/en-us/agent-framework/integrations/ag-ui/human-in-the-loop"
      },
      {
        "title": "https://www.iso.org/standard/42001",
        "path": "https://www.iso.org/standard/42001"
      },
      {
        "title": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
        "path": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
      },
      {
        "title": "https://genai.owasp.org/resource/state-of-agentic-ai-security-and-governance/",
        "path": "https://genai.owasp.org/resource/state-of-agentic-ai-security-and-governance/"
      },
      {
        "title": "https://owasp.org/APTS/standard/3_Human_Oversight/",
        "path": "https://owasp.org/APTS/standard/3_Human_Oversight/"
      }
    ]
  },
  {
    "id": "i4",
    "level": "Intermediate",
    "step": 9,
    "title": "Data RAG and Memory Governance",
    "summary": "Authorized retrieval.",
    "outcome": "Memory poisoning mitigation.",
    "material": "curriculum/intermediate/09-data-rag-and-memory-governance/README.md",
    "notebook": "curriculum/intermediate/09-data-rag-and-memory-governance/09_data_rag_and_memory_governance.ipynb",
    "refs": [
      {
        "title": "https://openai.github.io/openai-agents-python/sessions/",
        "path": "https://openai.github.io/openai-agents-python/sessions/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/sandbox/memory/",
        "path": "https://openai.github.io/openai-agents-python/sandbox/memory/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/running_agents/",
        "path": "https://openai.github.io/openai-agents-python/running_agents/"
      },
      {
        "title": "https://docs.langchain.com/oss/python/langgraph/memory",
        "path": "https://docs.langchain.com/oss/python/langgraph/memory"
      },
      {
        "title": "https://www.nist.gov/news-events/news/2026/01/caisi-issues-request-information-about-securing-ai-agent-systems",
        "path": "https://www.nist.gov/news-events/news/2026/01/caisi-issues-request-information-about-securing-ai-agent-systems"
      },
      {
        "title": "https://www.nist.gov/itl/ai-risk-management-framework",
        "path": "https://www.nist.gov/itl/ai-risk-management-framework"
      },
      {
        "title": "https://genai.owasp.org/",
        "path": "https://genai.owasp.org/"
      },
      {
        "title": "https://www.iso.org/standard/42001",
        "path": "https://www.iso.org/standard/42001"
      }
    ]
  },
  {
    "id": "i5",
    "level": "Intermediate",
    "step": 10,
    "title": "Multi Agent Governance and Delegation",
    "summary": "Recursive delegation.",
    "outcome": "Agent-to-agent boundaries.",
    "material": "curriculum/intermediate/10-multi-agent-governance-and-delegation/README.md",
    "notebook": "curriculum/intermediate/10-multi-agent-governance-and-delegation/10_multi_agent_governance_and_delegation.ipynb",
    "refs": [
      {
        "title": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative",
        "path": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative"
      },
      {
        "title": "https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure",
        "path": "https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/multi_agent/",
        "path": "https://openai.github.io/openai-agents-python/multi_agent/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/handoffs/",
        "path": "https://openai.github.io/openai-agents-python/handoffs/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/tools/",
        "path": "https://openai.github.io/openai-agents-python/tools/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/tracing/",
        "path": "https://openai.github.io/openai-agents-python/tracing/"
      },
      {
        "title": "https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/",
        "path": "https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/"
      },
      {
        "title": "https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/handoff",
        "path": "https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/handoff"
      },
      {
        "title": "https://owasp.org/APTS/standard/appendix/Multi_Agent_Coordination.html",
        "path": "https://owasp.org/APTS/standard/appendix/Multi_Agent_Coordination.html"
      },
      {
        "title": "https://owasp.org/APTS/standard/appendix/Authority_Delegation_Matrix_Template.html",
        "path": "https://owasp.org/APTS/standard/appendix/Authority_Delegation_Matrix_Template.html"
      }
    ]
  },
  {
    "id": "i6",
    "level": "Intermediate",
    "step": 11,
    "title": "Guardrails and Agent Security",
    "summary": "Prompt injection and indirect injection.",
    "outcome": "Goal hijacking.",
    "material": "curriculum/intermediate/11-guardrails-and-agent-security/README.md",
    "notebook": "curriculum/intermediate/11-guardrails-and-agent-security/11_guardrails_and_agent_security.ipynb",
    "refs": [
      {
        "title": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/",
        "path": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"
      },
      {
        "title": "https://genai.owasp.org/resource/state-of-agentic-ai-security-and-governance/",
        "path": "https://genai.owasp.org/resource/state-of-agentic-ai-security-and-governance/"
      },
      {
        "title": "https://genai.owasp.org/initiatives/agentic-security-initiative/",
        "path": "https://genai.owasp.org/initiatives/agentic-security-initiative/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/guardrails/",
        "path": "https://openai.github.io/openai-agents-python/guardrails/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/ref/tool_guardrails/",
        "path": "https://openai.github.io/openai-agents-python/ref/tool_guardrails/"
      },
      {
        "title": "https://openai.github.io/openai-guardrails-python/",
        "path": "https://openai.github.io/openai-guardrails-python/"
      },
      {
        "title": "https://learn.microsoft.com/en-us/agent-framework/agents/safety",
        "path": "https://learn.microsoft.com/en-us/agent-framework/agents/safety"
      },
      {
        "title": "https://learn.microsoft.com/en-us/agent-framework/agents/security",
        "path": "https://learn.microsoft.com/en-us/agent-framework/agents/security"
      },
      {
        "title": "https://learn.microsoft.com/en-us/agent-framework/agents/middleware/termination",
        "path": "https://learn.microsoft.com/en-us/agent-framework/agents/middleware/termination"
      },
      {
        "title": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative",
        "path": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative"
      }
    ]
  },
  {
    "id": "i7",
    "level": "Intermediate",
    "step": 12,
    "title": "Agent Red Teaming and Adversarial Testing",
    "summary": "Attack surface discovery.",
    "outcome": "Continuous red teaming.",
    "material": "curriculum/intermediate/12-agent-red-teaming-and-adversarial-testing/README.md",
    "notebook": "curriculum/intermediate/12-agent-red-teaming-and-adversarial-testing/12_agent_red_teaming_and_adversarial_testing.ipynb",
    "refs": [
      {
        "title": "https://genai.owasp.org/initiatives/ai-red-teaming-initiative/",
        "path": "https://genai.owasp.org/initiatives/ai-red-teaming-initiative/"
      },
      {
        "title": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/",
        "path": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"
      },
      {
        "title": "https://learn.microsoft.com/en-us/security/ai-red-team/",
        "path": "https://learn.microsoft.com/en-us/security/ai-red-team/"
      },
      {
        "title": "https://github.com/Azure/PyRIT",
        "path": "https://github.com/Azure/PyRIT"
      },
      {
        "title": "https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/run-scans-ai-red-teaming-agent",
        "path": "https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/run-scans-ai-red-teaming-agent"
      },
      {
        "title": "https://github.com/NVIDIA/garak",
        "path": "https://github.com/NVIDIA/garak"
      },
      {
        "title": "https://docs.garak.ai/",
        "path": "https://docs.garak.ai/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/tracing/",
        "path": "https://openai.github.io/openai-agents-python/tracing/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/",
        "path": "https://openai.github.io/openai-agents-python/"
      }
    ]
  },
  {
    "id": "a1",
    "level": "Advanced",
    "step": 13,
    "title": "Observability as Governance Evidence",
    "summary": "Why standard logs are insufficient.",
    "outcome": "Evidence retention.",
    "material": "curriculum/advanced/13-observability-as-goveernance-evidence/README.md",
    "notebook": "curriculum/advanced/13-observability-as-goveernance-evidence/13_observability_as_goveernance_evidence.ipynb",
    "refs": [
      {
        "title": "https://opentelemetry.io/blog/2026/genai-observability/",
        "path": "https://opentelemetry.io/blog/2026/genai-observability/"
      },
      {
        "title": "https://opentelemetry.io/docs/specs/semconv/",
        "path": "https://opentelemetry.io/docs/specs/semconv/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/tracing/",
        "path": "https://openai.github.io/openai-agents-python/tracing/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/ref/tracing/",
        "path": "https://openai.github.io/openai-agents-python/ref/tracing/"
      },
      {
        "title": "https://docs.langchain.com/langsmith/observability",
        "path": "https://docs.langchain.com/langsmith/observability"
      },
      {
        "title": "https://arize.com/docs/phoenix",
        "path": "https://arize.com/docs/phoenix"
      }
    ]
  },
  {
    "id": "a2",
    "level": "Advanced",
    "step": 14,
    "title": "Agent Evaluation and Continuous Governance",
    "summary": "Task success and trajectory quality.",
    "outcome": "Evaluation metrics.",
    "material": "curriculum/advanced/14-agent-evaluation-and-continuous-governance/README.md",
    "notebook": "curriculum/advanced/14-agent-evaluation-and-continuous-governance/14_agent_evaluation_and_continuous_governance.ipynb",
    "refs": [
      {
        "title": "https://www.nist.gov/itl/ai-risk-management-framework",
        "path": "https://www.nist.gov/itl/ai-risk-management-framework"
      },
      {
        "title": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
        "path": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence"
      },
      {
        "title": "https://airc.nist.gov/",
        "path": "https://airc.nist.gov/"
      },
      {
        "title": "https://www.nist.gov/programs-projects/generative-artificial-intelligence-evaluation-program-genai",
        "path": "https://www.nist.gov/programs-projects/generative-artificial-intelligence-evaluation-program-genai"
      },
      {
        "title": "https://www.nist.gov/publications/challenges-monitoring-deployed-ai-systems-center-ai-standards-and-innovation",
        "path": "https://www.nist.gov/publications/challenges-monitoring-deployed-ai-systems-center-ai-standards-and-innovation"
      },
      {
        "title": "https://openai.com/index/introducing-agentkit/",
        "path": "https://openai.com/index/introducing-agentkit/"
      },
      {
        "title": "https://openai.github.io/openai-agents-python/",
        "path": "https://openai.github.io/openai-agents-python/"
      },
      {
        "title": "https://docs.langchain.com/langsmith/evaluation",
        "path": "https://docs.langchain.com/langsmith/evaluation"
      },
      {
        "title": "https://arize.com/docs/phoenix/evaluation",
        "path": "https://arize.com/docs/phoenix/evaluation"
      },
      {
        "title": "https://opentelemetry.io/blog/2026/genai-observability/",
        "path": "https://opentelemetry.io/blog/2026/genai-observability/"
      },
      {
        "title": "https://opentelemetry.io/docs/specs/semconv/",
        "path": "https://opentelemetry.io/docs/specs/semconv/"
      }
    ]
  },
  {
    "id": "a3",
    "level": "Advanced",
    "step": 15,
    "title": "Governance Control Plane Architecture",
    "summary": "Governance system of record.",
    "outcome": "Control plane vs data plane.",
    "material": "curriculum/advanced/15-governance-control-plane-architecture/README.md",
    "notebook": "curriculum/advanced/15-governance-control-plane-architecture/15_governance_control_plane_architecture.ipynb",
    "refs": [
      {
        "title": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative",
        "path": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative"
      },
      {
        "title": "https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd",
        "path": "https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd"
      },
      {
        "title": "https://www.openpolicyagent.org/docs/policy-language",
        "path": "https://www.openpolicyagent.org/docs/policy-language"
      },
      {
        "title": "https://www.openpolicyagent.org/docs/http-api-authorization",
        "path": "https://www.openpolicyagent.org/docs/http-api-authorization"
      },
      {
        "title": "https://www.openpolicyagent.org/docs/security",
        "path": "https://www.openpolicyagent.org/docs/security"
      },
      {
        "title": "https://opentelemetry.io/blog/2026/genai-observability/",
        "path": "https://opentelemetry.io/blog/2026/genai-observability/"
      },
      {
        "title": "https://opentelemetry.io/docs/specs/semconv/",
        "path": "https://opentelemetry.io/docs/specs/semconv/"
      },
      {
        "title": "https://arxiv.org/abs/2606.12320",
        "path": "https://arxiv.org/abs/2606.12320"
      }
    ]
  },
  {
    "id": "a4",
    "level": "Advanced",
    "step": 16,
    "title": "Enterprise Agent Governance Operating Model",
    "summary": "Ownership and onboarding.",
    "outcome": "Recertification and incident response.",
    "material": "curriculum/advanced/16-enterprise-agent-governance-operating-model/README.md",
    "notebook": "curriculum/advanced/16-enterprise-agent-governance-operating-model/16_enterprise_agent_governance_operating_model.ipynb",
    "refs": []
  },
  {
    "id": "a5",
    "level": "Advanced",
    "step": 17,
    "title": "Capstone Governed Autonomous Enterprise Agent",
    "summary": "Full production architecture.",
    "outcome": "Trade-offs.",
    "material": "curriculum/advanced/17-capstone-governed-autonomous-enterprise-agent/README.md",
    "notebook": "curriculum/advanced/17-capstone-governed-autonomous-enterprise-agent/17_capstone_governed_autonomous_enterprise_agent.ipynb",
    "refs": [
      {
        "title": "https://www.nist.gov/itl/ai-risk-management-framework",
        "path": "https://www.nist.gov/itl/ai-risk-management-framework"
      },
      {
        "title": "https://www.nist.gov/itl/ai-risk-management-framework/",
        "path": "https://www.nist.gov/itl/ai-risk-management-framework/"
      },
      {
        "title": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative",
        "path": "https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative"
      },
      {
        "title": "https://owasp.org/www-project-top-10-for-agentic-applications/",
        "path": "https://owasp.org/www-project-top-10-for-agentic-applications/"
      },
      {
        "title": "https://opentelemetry.io/docs/specs/semconv/gen-ai/",
        "path": "https://opentelemetry.io/docs/specs/semconv/gen-ai/"
      },
      {
        "title": "https://openssf.org/",
        "path": "https://openssf.org/"
      }
    ]
  }
];

export const checks = {
  "b1": [
    {
      "question": "Two applications use the same model, but only one can issue refunds. Why does the second need a stronger governance architecture?",
      "choices": [
        "Its tools and delegated authority can create state changes, so policy must be enforced at the consequence boundary",
        "Refund text uses more tokens than ordinary responses",
        "The model becomes deterministic when connected to a payment API",
        "A larger system prompt provides the missing authorization"
      ],
      "answer": 0,
      "explanation": "Governance follows the complete capability chain. The same model has a different blast radius when a trusted application gives it state-changing tools and authority."
    },
    {
      "question": "A manager approved a $12,000 purchase order, but the agent changes the vendor before execution. What should the enforcement point do?",
      "choices": [
        "Execute because the amount did not change",
        "Ask the agent whether the change is safe",
        "Reject the old receipt and require approval for the new proposal digest",
        "Reuse the receipt if the same model produced both proposals"
      ],
      "answer": 2,
      "explanation": "Consequential approval must bind the exact action, target, tenant, task, policy version, and proposal digest. Any material change invalidates it."
    },
    {
      "question": "Which evaluation result most directly shows whether unauthorized side effects occurred in the labelled negative cases?",
      "choices": [
        "Average model confidence",
        "Forbidden outcomes divided by all cases labelled DENY or approval-required without a receipt",
        "The total number of policy log lines",
        "The percentage of responses containing the word ALLOW"
      ],
      "answer": 1,
      "explanation": "The forbidden outcome rate measures actual prohibited effects over the relevant negative/boundary population; blocked attempts and model confidence are different quantities."
    }
  ],
  "b2": [
    {
      "question": "A sandbox agent and a payment agent have the same autonomy level. Why can their risk tiers differ?",
      "choices": [
        "Autonomy is only one dimension; impact, privilege, irreversibility, scope, likelihood, and evidence differ",
        "Payment agents always use larger language models",
        "Sandbox agents cannot make planning decisions",
        "Risk tiers are determined by framework name"
      ],
      "answer": 0,
      "explanation": "Autonomy describes independent authority, not total risk. Consequence, access, reversibility, exposure, blast radius, uncertainty, and evidence shape treatment."
    },
    {
      "question": "A risk register says runtime policy is 18% effective but cites only a design document. How should residual risk be treated?",
      "choices": [
        "Reduce the score by exactly 18%",
        "Let the agent estimate a more precise percentage",
        "Do not grant operating-effectiveness credit until current scenario-specific tests or observations support the claim",
        "Delete the inherent-risk assessment"
      ],
      "answer": 2,
      "explanation": "Documented design intent is useful but does not prove that a control operates against the relevant scenario. Residual-risk reduction needs scoped, current evidence."
    },
    {
      "question": "Which blast-radius result is most useful for an architecture decision?",
      "choices": [
        "An unexplained normalized score of 0.73",
        "A list of exact reachable and writable assets, severe resources, trust-zone crossings, delegated hops, and the delta after removing a capability",
        "The average number of graph nodes in unrelated systems",
        "A model-generated statement that the graph is safe"
      ],
      "answer": 1,
      "explanation": "Exact graph facts are inspectable and actionable: reviewers can see which capability or edge creates exposure and verify the effect of an architectural treatment."
    }
  ],
  "b3": [
    {
      "question": "What does an internal-control crosswalk prove about an external framework or regulation?",
      "choices": [
        "That one internal control automatically establishes compliance",
        "That the control contributes evidence to a cited expectation, subject to its stated limits",
        "That legal review is no longer required",
        "That every framework is interchangeable"
      ],
      "answer": 1,
      "explanation": "A crosswalk organizes claims and evidence. It must preserve sources and limitations and cannot by itself establish legal compliance, framework conformance, or certification."
    },
    {
      "question": "Why can a high internal agent-risk tier not determine the EU AI Act classification?",
      "choices": [
        "Risk and regulation use different reviewed criteria, roles, jurisdictions, and sources",
        "The EU AI Act applies only to model providers",
        "Autonomy always makes a system legally high-risk",
        "Internal risk tiers are legally binding"
      ],
      "answer": 0,
      "explanation": "The application may route an applicability review, but a named specialist owns the legal interpretation. Internal engineering risk remains a separate, connected record."
    },
    {
      "question": "Why does the Course 3 gate check each evidence requirement instead of an average completeness score?",
      "choices": [
        "Averages make audit reports too long",
        "One missing non-waivable artifact must block even when most other evidence is complete",
        "Every artifact has the same risk significance",
        "The model should choose which missing evidence to ignore"
      ],
      "answer": 1,
      "explanation": "Exact, current, version-bound requirements prevent a high aggregate percentage from masking missing authorization, assurance, or other critical evidence."
    }
  ],
  "b4": [
    {
      "question": "A request contains a valid SPIFFE-shaped workload string and a correctly signed task token. What must happen before a purchase is authorized?",
      "choices": [
        "Trust both values because their formats are valid",
        "Ask the language model whether the workload is legitimate",
        "Bind current attestation and the registered agent/workload relationship, then evaluate task, audience, resource, lifecycle, and request constraints",
        "Check only whether the token has not expired"
      ],
      "answer": 2,
      "explanation": "A SPIFFE ID is a name, and a signature establishes token integrity under a key. Trusted application state must still prove the current workload binding and authorize the exact operation."
    },
    {
      "question": "Eight workers concurrently use a grant with max_calls=1 and different operation IDs. Which result demonstrates correct consumption?",
      "choices": [
        "All eight pass because the signature is valid",
        "Exactly one passes because validation and consumption are atomic",
        "The first four pass because half the workers are trusted",
        "The language model chooses which requests count"
      ],
      "answer": 1,
      "explanation": "A check-then-increment race can overspend a one-use grant. The authoritative store must validate and consume in one transaction or equivalent atomic operation."
    },
    {
      "question": "A research sub-agent receives fewer actions but a broader resource set and longer expiry than its parent. Is the delegation attenuated?",
      "choices": [
        "Yes, because only the action list matters",
        "Yes, if both agents use the same model",
        "No; every authority dimension must remain equal or narrower and the child must preserve subject, tenant, task, intent, and lineage bindings",
        "No, but a model-generated approval can repair it"
      ],
      "answer": 2,
      "explanation": "Permission-only narrowing is incomplete. Resources, vendors, amount, calls, lifetime, audience transitions, and delegation depth can each amplify authority."
    }
  ],
  "b5": [
    {
      "question": "A user may create purchase orders for Department A, and a task grant allows the procurement agent to create purchase orders only for Department B. What should dual authorization return for Department A?",
      "choices": [
        "Allow because the user has authority",
        "Allow because either check is sufficient",
        "Deny because user authority and task authority must both cover the same resource",
        "Ask the model to choose the broader resource"
      ],
      "answer": 2,
      "explanation": "The checks are an intersection. A valid user relationship does not widen a task grant, and a task grant does not create user authority."
    },
    {
      "question": "A preview returned ALLOW, but the vendor was suspended before the tool invocation. What should the PEP do?",
      "choices": [
        "Reuse the preview because it was previously valid",
        "Reauthorize against current versions immediately before the effect and deny",
        "Execute, then remove the audit row",
        "Let the model estimate whether the suspension matters"
      ],
      "answer": 1,
      "explanation": "A preview is not an execution permit. Reauthorization closes the time-of-check/time-of-use gap and observes the current vendor state."
    },
    {
      "question": "A manager approves a CAD 6,000 purchase, but the vendor is sanctioned. How should policy combine the approval and hard restriction?",
      "choices": [
        "Allow because human approval overrides policy",
        "Escalate repeatedly until another manager approves",
        "Deny because approval may satisfy a soft threshold but cannot override a hard prohibition",
        "Allow if the agent explains its reasoning"
      ],
      "answer": 2,
      "explanation": "Approval is a narrow policy input, not universal authority. Sanctions, tenant isolation, and task bounds remain hard denies."
    }
  ],
  "i1": [
    {
      "question": "A candidate bundle passes syntax and schema validation but changes one labelled sanctioned-vendor case from DENY to ESCALATE. What should the release gate do?",
      "choices": [
        "Promote because ESCALATE is safer than ALLOW",
        "Block promotion because a hard denial escaped, even though the candidate remains default-deny",
        "Promote only for administrators",
        "Ask the model whether the changed decision is reasonable"
      ],
      "answer": 1,
      "explanation": "A hard-deny case becoming any non-DENY outcome is a safety regression. Static validity does not prove semantic equivalence or acceptable behavior."
    },
    {
      "question": "During shadow rollout, the candidate returns DENY while the active bundle returns ALLOW. Which result may the PEP enforce?",
      "choices": [
        "The candidate result because it is stricter",
        "Whichever result the agent prefers",
        "Only the active result; the candidate result is comparison evidence until an authorized promotion",
        "Both results in alternating requests"
      ],
      "answer": 2,
      "explanation": "Shadow evaluation must not change effects. The active bundle remains authoritative until the release lifecycle promotes the exact validated candidate."
    },
    {
      "question": "A valid allow decision was cached, then trusted vendor facts expired before execution. What is the safest PEP behavior?",
      "choices": [
        "Execute because the decision was once valid",
        "Re-resolve current authoritative facts and re-evaluate before the effect; deny if freshness cannot be established",
        "Let the model refresh the approval field",
        "Execute and repair the audit log later"
      ],
      "answer": 1,
      "explanation": "Policy correctness depends on both policy and current inputs. Consequential effects require fresh trusted facts and immediate enforcement, not a stale cached allow."
    }
  ],
  "i2": [
    {
      "question": "How does the Model Context Protocol (MCP) aid in tool governance?",
      "choices": [
        "It trains the LLM faster",
        "It provides a standardized, secure boundary between the agent and external tools",
        "It generates code automatically",
        "It removes the need for authorization"
      ],
      "answer": 1,
      "explanation": "MCP standardizes tool integration, making it easier to enforce authorization boundaries between the agent and the tools."
    },
    {
      "question": "Why is schema validation critical for tool governance?",
      "choices": [
        "To make the code look clean",
        "To prevent the agent from passing malformed or malicious arguments to backend systems",
        "To increase API latency",
        "To translate languages"
      ],
      "answer": 1,
      "explanation": "Agents can hallucinate arguments; schema validation acts as a strict typing boundary before execution."
    },
    {
      "question": "What is a key benefit of using allowlists for agent tools?",
      "choices": [
        "It restricts the agent strictly to a predefined set of safe actions, rejecting any hallucinated tool names",
        "It guarantees 100% accuracy",
        "It makes the model run faster",
        "It replaces the need for an LLM"
      ],
      "answer": 0,
      "explanation": "Allowlists are a basic but powerful guardrail to prevent the agent from calling unauthorized or hallucinated tools."
    }
  ],
  "i3": [
    {
      "question": "What is the main drawback of 'Human-in-the-loop' for every single agent action?",
      "choices": [
        "It is too secure",
        "Approval fatigue, where humans blindly approve actions without scrutiny",
        "It uses too much memory",
        "The agent gets confused"
      ],
      "answer": 1,
      "explanation": "If humans are bombarded with approvals, they stop verifying, rendering the control ineffective."
    },
    {
      "question": "What defines 'Meaningful human control'?",
      "choices": [
        "Clicking 'OK' as fast as possible",
        "The human has the context, time, and capability to override or alter the agent's proposed action",
        "The human writes the code",
        "The human trains the model"
      ],
      "answer": 1,
      "explanation": "Meaningful control requires the human to actually understand the consequence of the action they are approving."
    },
    {
      "question": "What is a 'Risk-based approval engine'?",
      "choices": [
        "An engine that randomly approves tasks",
        "A system that dynamically determines if human approval is required based on the sensitivity or blast radius of the proposed action",
        "A fast LLM",
        "A firewall configuration"
      ],
      "answer": 1,
      "explanation": "Instead of hardcoding HITL, a risk-based engine allows low-risk tasks to be HOTL, reserving HITL only for high-risk operations."
    }
  ],
  "i4": [
    {
      "question": "What is 'Memory poisoning' in an agent context?",
      "choices": [
        "When the server runs out of RAM",
        "When an attacker injects malicious instructions into the agent's long-term storage to manipulate future actions",
        "When the agent forgets user preferences",
        "When data is stored unencrypted"
      ],
      "answer": 1,
      "explanation": "If an agent retrieves manipulated past memories, it can be tricked into executing malicious payloads indefinitely."
    },
    {
      "question": "How do you securely enforce RAG authorization?",
      "choices": [
        "By hiding secret documents",
        "By ensuring the vector database filters retrieved documents based on the calling user's ACLs",
        "By asking the LLM not to read them",
        "By using a smaller context window"
      ],
      "answer": 1,
      "explanation": "The database itself must enforce authorization (e.g., using metadata filters) before the data ever reaches the LLM."
    },
    {
      "question": "Why is data provenance important for RAG governance?",
      "choices": [
        "It tells you the price of the data",
        "It allows auditors to trace exactly which source document led the agent to make a specific decision",
        "It encrypts the data",
        "It increases retrieval speed"
      ],
      "answer": 1,
      "explanation": "Provenance ensures accountability; if an agent gives bad advice, administrators can identify the offending source material."
    }
  ],
  "i5": [
    {
      "question": "What is the 'Confused Deputy' problem in multi-agent systems?",
      "choices": [
        "When an agent doesn't know its prompt",
        "When a malicious user tricks a privileged agent into misusing its authority on their behalf",
        "When two agents talk in a loop",
        "When an agent fails to respond"
      ],
      "answer": 1,
      "explanation": "A confused deputy has high privileges but is tricked by a lower-privilege entity into executing an unauthorized action."
    },
    {
      "question": "How do delegation envelopes prevent privilege amplification?",
      "choices": [
        "They stop agents from talking to each other",
        "They cryptographically bound the permissions that can be passed from a parent agent to a sub-agent",
        "They encrypt the prompt",
        "They increase the context window"
      ],
      "answer": 1,
      "explanation": "Delegation envelopes ensure a sub-agent cannot gain more permissions than its parent intended to delegate."
    },
    {
      "question": "What is a Capability Token in multi-agent orchestration?",
      "choices": [
        "A cryptocurrency",
        "An unforgeable token granting a specific sub-agent the right to execute a narrow task",
        "The token limit of the LLM",
        "A badge for humans"
      ],
      "answer": 1,
      "explanation": "Capability tokens embody the principle of least privilege, issuing strict rights only when needed for multi-agent workflows."
    }
  ],
  "i6": [
    {
      "question": "What is the difference between direct prompt injection and indirect prompt injection?",
      "choices": [
        "Indirect injection uses SQL",
        "Indirect injection comes from external data sources like websites or documents, not the user",
        "Direct injection is harder to detect",
        "They are the same"
      ],
      "answer": 1,
      "explanation": "Agents are highly vulnerable to indirect injection because they autonomously fetch external, untrusted content."
    },
    {
      "question": "What is the primary purpose of an input 'Guardrail' in agent security?",
      "choices": [
        "To format the text nicely",
        "To intercept and block unsafe inputs or outputs before they reach the model or the user",
        "To route the request to the fastest model",
        "To track API usage"
      ],
      "answer": 1,
      "explanation": "Guardrails act as a semantic firewall, independent of the main model, to detect anomalies."
    },
    {
      "question": "How do layered defenses protect against prompt injection?",
      "choices": [
        "By banning all prompts",
        "By using multiple independent mechanisms, like input scanners, output monitors, and strict schema enforcement, to catch attacks",
        "By relying solely on the LLM's safety tuning",
        "By limiting the context window to 10 tokens"
      ],
      "answer": 1,
      "explanation": "No single defense is foolproof. Layered defenses (defense in depth) assume one layer will fail and rely on the next layer."
    }
  ],
  "i7": [
    {
      "question": "What is the objective of continuous agent red teaming?",
      "choices": [
        "To break the production server",
        "To proactively discover vulnerabilities as the agent's tools, models, and environments evolve",
        "To train new developers",
        "To test UI responsiveness"
      ],
      "answer": 1,
      "explanation": "Agents operate in dynamic environments; continuous red teaming ensures new attack paths are found before exploitation."
    },
    {
      "question": "How does an adversarial trajectory differ from a standard prompt attack?",
      "choices": [
        "It involves multiple steps and tool uses to incrementally bypass defenses and achieve a malicious goal",
        "It uses only one prompt",
        "It targets the database directly",
        "It is done manually"
      ],
      "answer": 0,
      "explanation": "Agent attacks are often multi-turn trajectories where the attacker uses the agent's own tools against it over time."
    },
    {
      "question": "What is the role of an automated attack harness in red teaming?",
      "choices": [
        "To format logs",
        "To systematically generate and execute adversarial payloads against the agent without manual human effort",
        "To encrypt passwords",
        "To scale the cloud servers"
      ],
      "answer": 1,
      "explanation": "Tools like PyRIT automate the generation of adversarial prompts, enabling continuous security testing at scale."
    }
  ],
  "a1": [
    {
      "question": "Why are standard text logs insufficient for agent observability?",
      "choices": [
        "They take up too much disk space",
        "They lack the hierarchical context of trajectories, tool calls, and reasoning steps",
        "They are too hard to read",
        "They are not encrypted"
      ],
      "answer": 1,
      "explanation": "Agents execute complex, nested workflows. Traces (like OpenTelemetry) are required to reconstruct the exact chain of events."
    },
    {
      "question": "What role does OpenTelemetry play in governance evidence?",
      "choices": [
        "It encrypts data",
        "It provides a standardized way to trace execution paths across distributed agent components",
        "It acts as the PEP",
        "It stores passwords"
      ],
      "answer": 1,
      "explanation": "OpenTelemetry allows enterprises to capture structured spans for LLM calls, tool executions, and policy decisions."
    },
    {
      "question": "Why must governance evidence be retained immutably?",
      "choices": [
        "To prevent attackers or compromised agents from deleting logs to cover up unauthorized actions",
        "To save on database costs",
        "To speed up queries",
        "To comply with CSS standards"
      ],
      "answer": 0,
      "explanation": "If an agent is compromised, the attacker could attempt to delete its tracks. Immutable evidence ensures non-repudiation."
    }
  ],
  "a2": [
    {
      "question": "What is the purpose of an 'LLM-as-judge' in continuous evaluation?",
      "choices": [
        "To arrest hackers",
        "To automatically score the quality, safety, or compliance of an agent's outputs against a rubric",
        "To decide which model to use",
        "To generate code"
      ],
      "answer": 1,
      "explanation": "LLM-as-judge allows scalable, automated evaluation of subjective agent behaviors during CI/CD."
    },
    {
      "question": "Why is 'cost per successful task' a key governance metric?",
      "choices": [
        "To maximize API usage",
        "It measures the efficiency of the agent's autonomy and whether the token usage justifies the business value",
        "To punish developers",
        "To lower server costs"
      ],
      "answer": 1,
      "explanation": "Agents can get stuck in loops or use excessive tokens. This metric ties autonomous behavior directly to ROI."
    },
    {
      "question": "What is a deterministic evaluator in continuous agent testing?",
      "choices": [
        "An LLM judging another LLM",
        "An evaluation script that checks exact code execution outcomes, like database state changes, rather than relying on an LLM judge",
        "A human reviewer",
        "A random number generator"
      ],
      "answer": 1,
      "explanation": "Deterministic evaluators verify the actual effects of the agent's actions on the environment using traditional software assertions."
    }
  ],
  "a3": [
    {
      "question": "In a Governance Control Plane, what is the difference between the control plane and the data plane?",
      "choices": [
        "They are identical",
        "The control plane manages policies and configurations, while the data plane executes the agent's actions",
        "The control plane is for testing only",
        "The data plane stores policies"
      ],
      "answer": 1,
      "explanation": "Separating the planes ensures that governance administrators can change policies without altering the agent's code."
    },
    {
      "question": "What is an 'evidence store' used for?",
      "choices": [
        "To store training data",
        "To immutably record policy decisions, approvals, and trajectories for audit purposes",
        "To cache API responses",
        "To store user profiles"
      ],
      "answer": 1,
      "explanation": "An evidence store provides undeniable proof of the agent's behavior and the governance controls that were applied."
    },
    {
      "question": "What happens when an agent enters 'Read-only mode' via the control plane?",
      "choices": [
        "The agent is deleted",
        "The agent can still process inputs and query data, but the PEP blocks all state-changing tool executions",
        "The agent refuses to answer",
        "The database becomes read-only for all humans"
      ],
      "answer": 1,
      "explanation": "Read-only mode allows investigation of anomalous behavior while preventing the agent from causing further harm."
    }
  ],
  "a4": [
    {
      "question": "What is the purpose of an 'Agent System Card'?",
      "choices": [
        "To give the agent a badge",
        "To document the agent's intended use, capabilities, risk tier, and known limitations for stakeholders",
        "To track GPU usage",
        "To format outputs"
      ],
      "answer": 1,
      "explanation": "System cards create transparency, ensuring users and risk teams understand the boundaries of the agent."
    },
    {
      "question": "Why is a recertification process necessary for enterprise agents?",
      "choices": [
        "To generate more paperwork",
        "To ensure the agent still complies with policies after model updates or environment changes",
        "To change the agent's name",
        "To delete old logs"
      ],
      "answer": 1,
      "explanation": "Agents degrade or drift as backend APIs or underlying LLMs change. Periodic recertification ensures continued safety."
    },
    {
      "question": "What role does 'Governance-as-code' play in agent onboarding?",
      "choices": [
        "It prevents onboarding",
        "It automates the validation of required security controls and documentation before the agent is allowed to deploy",
        "It allows developers to skip testing",
        "It generates marketing material"
      ],
      "answer": 1,
      "explanation": "Governance-as-code replaces manual spreadsheets with automated CI/CD checks for risk tiers, policy attachments, and required tests."
    }
  ],
  "a5": [
    {
      "question": "In a production enterprise agent, what is the trade-off between strict policy enforcement and agent capability?",
      "choices": [
        "Strict policies make the agent run faster",
        "Strict policies reduce risk but may block the agent from completing complex or novel tasks",
        "There is no trade-off",
        "Strict policies increase token usage"
      ],
      "answer": 1,
      "explanation": "Governance must balance safety with utility; overly strict policies degrade the autonomous value of the agent."
    },
    {
      "question": "What is the ultimate goal of governed autonomous enterprise agents?",
      "choices": [
        "To replace all human workers",
        "To safely scale AI action-taking while maintaining verifiable compliance and human accountability",
        "To write more code",
        "To eliminate the need for authorization"
      ],
      "answer": 1,
      "explanation": "Governed autonomy allows businesses to delegate tasks securely without losing control or compliance."
    },
    {
      "question": "Why is continuous monitoring essential for a production enterprise agent?",
      "choices": [
        "To track user IP addresses",
        "Because the underlying models, APIs, and threat landscape constantly evolve, invalidating point-in-time assessments",
        "To reduce API costs",
        "Because it looks good on a dashboard"
      ],
      "answer": 1,
      "explanation": "Unlike static software, agent behavior is highly variable. Continuous monitoring detects policy violations or goal drift immediately."
    }
  ]
};
