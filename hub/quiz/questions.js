export const questions = [
  // Module 1
  {
    id: "b1-1",
    category: "01 - From AI Governance to Agent Governance",
    prompt: "What is the fundamental difference between AI Model Governance and Autonomous Agent Governance?",
    options: ["Shift from Information Risk to Action Risk", "Shift from structured data to unstructured data", "Shift from cloud to on-premise", "Shift from manual to automated training"],
    correct: [0],
    explanation: "Model governance focuses on what the AI says (Information Risk), while agent governance focuses on what the AI does (Action Risk).",
    source: { label: "From AI Governance", url: "../curriculum/beginner/01-from-ai-governance-to-agent-governance/01_from_ai_governance_to_agent_governance.ipynb" }
  },
  {
    id: "b1-2",
    category: "01 - From AI Governance to Agent Governance",
    prompt: "In the context of agent governance, what is 'Governance-by-design'?",
    options: ["Writing policies after deployment", "Embedding controls into the agent's architecture directly", "Using manual human approval for every action", "Relying strictly on model alignment"],
    correct: [1],
    explanation: "Governance-by-design means building authorization, observability, and guardrails directly into the agent architecture.",
    source: { label: "From AI Governance", url: "../curriculum/beginner/01-from-ai-governance-to-agent-governance/01_from_ai_governance_to_agent_governance.ipynb" }
  },
  // Module 2
  {
    id: "b2-1",
    category: "02 - Agent Risk Modeling and Autonomy Classification",
    prompt: "What are the key dimensions used to calculate an agent's autonomy risk tier?",
    options: ["Cost, Speed, Accuracy, Latency", "Impact, Access, Irreversibility, Uncertainty", "Parameters, Context Window, Training Data", "User count, Database size, API calls"],
    correct: [1],
    explanation: "Risk is calculated based on the potential Impact, the Access the agent has, whether actions are Irreversible, and the level of Uncertainty.",
    source: { label: "Risk Modeling", url: "../curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/02_agent_risk_modeling_and_autonomy_classification.ipynb" }
  },
  {
    id: "b2-2",
    category: "02 - Agent Risk Modeling and Autonomy Classification",
    prompt: "What is a 'blast radius' in agent risk modeling?",
    options: ["The physical distance a server covers", "The maximum possible negative impact if the agent acts maliciously or fails", "The speed at which the agent executes tools", "The number of users interacting with the agent"],
    correct: [1],
    explanation: "Blast radius refers to the worst-case scenario boundaries of an agent's failure or misuse.",
    source: { label: "Risk Modeling", url: "../curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/02_agent_risk_modeling_and_autonomy_classification.ipynb" }
  },
  // Module 3
  {
    id: "b3-1",
    category: "03 - Standards Regulation and Governance Operating Model",
    prompt: "How does the ISO/IEC 42001 framework map to agent governance?",
    options: ["By enforcing specific code libraries", "By providing a PDCA (Plan, Do, Check, Act) lifecycle for continuous improvement", "By banning autonomous agents", "By focusing solely on data privacy"],
    correct: [1],
    explanation: "ISO 42001 provides a management system framework based on continuous improvement (Plan-Do-Check-Act).",
    source: { label: "Standards & Regulation", url: "../curriculum/beginner/03-standards-regulation-and-governance-operating-model/03_standards_regulation_and_governance_operating_model.ipynb" }
  },
  {
    id: "b3-2",
    category: "03 - Standards Regulation and Governance Operating Model",
    prompt: "Why is an AI inventory critical for an enterprise agent operating model?",
    options: ["To track agent versions, capabilities, and approved scopes", "To charge users for API calls", "To store training data", "To bypass compliance checks"],
    correct: [0],
    explanation: "An inventory ensures visibility into what agents are deployed, what they can do, and who owns them.",
    source: { label: "Standards & Regulation", url: "../curriculum/beginner/03-standards-regulation-and-governance-operating-model/03_standards_regulation_and_governance_operating_model.ipynb" }
  },
  // Module 4
  {
    id: "b4-1",
    category: "04 - Agent Identity and Delegated Authority",
    prompt: "What does it mean for an agent to have a 'Workload Identity'?",
    options: ["The agent uses the user's password", "The agent has no identity", "The agent acts as a principal with its own credentials, rather than impersonating the user indefinitely", "The agent is treated as an anonymous guest"],
    correct: [2],
    explanation: "Workload Identity allows the agent to authenticate itself to services securely without hardcoded human credentials.",
    source: { label: "Agent Identity", url: "../curriculum/beginner/04-agent-identity-and-delegated-authority/04_agent_identity_and_delegated_authority.ipynb" }
  },
  {
    id: "b4-2",
    category: "04 - Agent Identity and Delegated Authority",
    prompt: "What is the principle of 'Task-scoped credentials'?",
    options: ["Issuing short-lived tokens restricted to the exact permissions needed for a specific task", "Giving the agent full admin access permanently", "Using the same API key for all users", "Requiring a password for every single API call"],
    correct: [0],
    explanation: "Task-scoped credentials adhere to the principle of least privilege, reducing the risk if the token is compromised.",
    source: { label: "Agent Identity", url: "../curriculum/beginner/04-agent-identity-and-delegated-authority/04_agent_identity_and_delegated_authority.ipynb" }
  },
  // Module 5
  {
    id: "b5-1",
    category: "05 - Fine Grained Authorization for Agents",
    prompt: "What is the difference between RBAC and ReBAC in agent authorization?",
    options: ["They are the same thing", "ReBAC allows permissions based on relationships between resources, while RBAC is role-based", "RBAC is faster than ReBAC", "ReBAC relies on user passwords"],
    correct: [1],
    explanation: "Relationship-Based Access Control (ReBAC) provides finer granularity by evaluating graph relationships, unlike static Role-Based Access Control (RBAC).",
    source: { label: "Authorization", url: "../curriculum/beginner/05-fine-grained-authorization-for-agents/05_fine_grained_authorization_for_agents.ipynb" }
  },
  {
    id: "b5-2",
    category: "05 - Fine Grained Authorization for Agents",
    prompt: "What is 'Zero Standing Privilege' for an agent?",
    options: ["The agent has no permissions by default and must request just-in-time access for operations", "The agent cannot be audited", "The agent has read-only access permanently", "The agent is blocked from all APIs"],
    correct: [0],
    explanation: "ZSP ensures that agents do not hold dormant, highly-privileged access that attackers could exploit.",
    source: { label: "Authorization", url: "../curriculum/beginner/05-fine-grained-authorization-for-agents/05_fine_grained_authorization_for_agents.ipynb" }
  },
  // Module 6
  {
    id: "i1-1",
    category: "06 - Policy as Code and Runtime Governance",
    prompt: "In a Policy-as-Code architecture, what is the role of the Policy Enforcement Point (PEP)?",
    options: ["To write the policy", "To intercept requests and enforce the decision made by the Policy Decision Point (PDP)", "To log errors", "To train the model"],
    correct: [1],
    explanation: "The PEP is the gateway that blocks or allows actions based on the PDP's evaluation of the policy.",
    source: { label: "Policy as Code", url: "../curriculum/intermediate/06-policy-as-code-and-runtime-governance/06_policy_as_code_and_runtime_governance.ipynb" }
  },
  {
    id: "i1-2",
    category: "06 - Policy as Code and Runtime Governance",
    prompt: "Why should runtime policies default to 'deny'?",
    options: ["To ensure any unspecified or novel agent actions are blocked by default", "To save cloud costs", "To prevent the agent from starting", "To force users to write more code"],
    correct: [0],
    explanation: "Default deny ensures that unexpected or hallucinated tool calls are stopped before causing harm.",
    source: { label: "Policy as Code", url: "../curriculum/intermediate/06-policy-as-code-and-runtime-governance/06_policy_as_code_and_runtime_governance.ipynb" }
  },
  // Module 7
  {
    id: "i2-1",
    category: "07 - Tool and MCP Governance",
    prompt: "How does the Model Context Protocol (MCP) aid in tool governance?",
    options: ["It trains the LLM faster", "It provides a standardized, secure boundary between the agent and external tools", "It generates code automatically", "It removes the need for authorization"],
    correct: [1],
    explanation: "MCP standardizes tool integration, making it easier to enforce authorization boundaries between the agent and the tools.",
    source: { label: "Tool Governance", url: "../curriculum/intermediate/07-tool-and-mcp-governance/07_tool_and_mcp_governance.ipynb" }
  },
  {
    id: "i2-2",
    category: "07 - Tool and MCP Governance",
    prompt: "Why is schema validation critical for tool governance?",
    options: ["To make the code look clean", "To prevent the agent from passing malformed or malicious arguments to backend systems", "To increase API latency", "To translate languages"],
    correct: [1],
    explanation: "Agents can hallucinate arguments; schema validation acts as a strict typing boundary before execution.",
    source: { label: "Tool Governance", url: "../curriculum/intermediate/07-tool-and-mcp-governance/07_tool_and_mcp_governance.ipynb" }
  },
  // Module 8
  {
    id: "i3-1",
    category: "08 - Human Oversight and Bounded Autonomy",
    prompt: "What is the main drawback of 'Human-in-the-loop' for every single agent action?",
    options: ["It is too secure", "Approval fatigue, where humans blindly approve actions without scrutiny", "It uses too much memory", "The agent gets confused"],
    correct: [1],
    explanation: "If humans are bombarded with approvals, they stop verifying, rendering the control ineffective.",
    source: { label: "Human Oversight", url: "../curriculum/intermediate/08-human-oversight-and-bounded-autonomy/08_human_oversight_and_bounded_autonomy.ipynb" }
  },
  {
    id: "i3-2",
    category: "08 - Human Oversight and Bounded Autonomy",
    prompt: "What defines 'Meaningful human control'?",
    options: ["Clicking 'OK' as fast as possible", "The human has the context, time, and capability to override or alter the agent's proposed action", "The human writes the code", "The human trains the model"],
    correct: [1],
    explanation: "Meaningful control requires the human to actually understand the consequence of the action they are approving.",
    source: { label: "Human Oversight", url: "../curriculum/intermediate/08-human-oversight-and-bounded-autonomy/08_human_oversight_and_bounded_autonomy.ipynb" }
  },
  // Module 9
  {
    id: "i4-1",
    category: "09 - Data RAG and Memory Governance",
    prompt: "What is 'Memory poisoning' in an agent context?",
    options: ["When the server runs out of RAM", "When an attacker injects malicious instructions into the agent's long-term storage to manipulate future actions", "When the agent forgets user preferences", "When data is stored unencrypted"],
    correct: [1],
    explanation: "If an agent retrieves manipulated past memories, it can be tricked into executing malicious payloads indefinitely.",
    source: { label: "Memory Governance", url: "../curriculum/intermediate/09-data-rag-and-memory-governance/09_data_rag_and_memory_governance.ipynb" }
  },
  {
    id: "i4-2",
    category: "09 - Data RAG and Memory Governance",
    prompt: "How do you securely enforce RAG authorization?",
    options: ["By hiding secret documents", "By ensuring the vector database filters retrieved documents based on the calling user's ACLs", "By asking the LLM not to read them", "By using a smaller context window"],
    correct: [1],
    explanation: "The database itself must enforce authorization (e.g., using metadata filters) before the data ever reaches the LLM.",
    source: { label: "Memory Governance", url: "../curriculum/intermediate/09-data-rag-and-memory-governance/09_data_rag_and_memory_governance.ipynb" }
  },
  // Module 10
  {
    id: "i5-1",
    category: "10 - Multi Agent Governance and Delegation",
    prompt: "What is the 'Confused Deputy' problem in multi-agent systems?",
    options: ["When an agent doesn't know its prompt", "When a malicious user tricks a privileged agent into misusing its authority on their behalf", "When two agents talk in a loop", "When an agent fails to respond"],
    correct: [1],
    explanation: "A confused deputy has high privileges but is tricked by a lower-privilege entity into executing an unauthorized action.",
    source: { label: "Multi-Agent Governance", url: "../curriculum/intermediate/10-multi-agent-governance-and-delegation/10_multi_agent_governance_and_delegation.ipynb" }
  },
  {
    id: "i5-2",
    category: "10 - Multi Agent Governance and Delegation",
    prompt: "How do delegation envelopes prevent privilege amplification?",
    options: ["They stop agents from talking to each other", "They cryptographically bound the permissions that can be passed from a parent agent to a sub-agent", "They encrypt the prompt", "They increase the context window"],
    correct: [1],
    explanation: "Delegation envelopes ensure a sub-agent cannot gain more permissions than its parent intended to delegate.",
    source: { label: "Multi-Agent Governance", url: "../curriculum/intermediate/10-multi-agent-governance-and-delegation/10_multi_agent_governance_and_delegation.ipynb" }
  },
  // Module 11
  {
    id: "i6-1",
    category: "11 - Guardrails and Agent Security",
    prompt: "What is the difference between direct prompt injection and indirect prompt injection?",
    options: ["Indirect injection uses SQL", "Indirect injection comes from external data sources like websites or documents, not the user", "Direct injection is harder to detect", "They are the same"],
    correct: [1],
    explanation: "Agents are highly vulnerable to indirect injection because they autonomously fetch external, untrusted content.",
    source: { label: "Agent Security", url: "../curriculum/intermediate/11-guardrails-and-agent-security/11_guardrails_and_agent_security.ipynb" }
  },
  {
    id: "i6-2",
    category: "11 - Guardrails and Agent Security",
    prompt: "What is the primary purpose of an input 'Guardrail' in agent security?",
    options: ["To format the text nicely", "To intercept and block unsafe inputs or outputs before they reach the model or the user", "To route the request to the fastest model", "To track API usage"],
    correct: [1],
    explanation: "Guardrails act as a semantic firewall, independent of the main model, to detect anomalies.",
    source: { label: "Agent Security", url: "../curriculum/intermediate/11-guardrails-and-agent-security/11_guardrails_and_agent_security.ipynb" }
  },
  // Module 12
  {
    id: "i7-1",
    category: "12 - Agent Red Teaming and Adversarial Testing",
    prompt: "What is the objective of continuous agent red teaming?",
    options: ["To break the production server", "To proactively discover vulnerabilities as the agent's tools, models, and environments evolve", "To train new developers", "To test UI responsiveness"],
    correct: [1],
    explanation: "Agents operate in dynamic environments; continuous red teaming ensures new attack paths are found before exploitation.",
    source: { label: "Red Teaming", url: "../curriculum/intermediate/12-agent-red-teaming-and-adversarial-testing/12_agent_red_teaming_and_adversarial_testing.ipynb" }
  },
  {
    id: "i7-2",
    category: "12 - Agent Red Teaming and Adversarial Testing",
    prompt: "How does an adversarial trajectory differ from a standard prompt attack?",
    options: ["It involves multiple steps and tool uses to incrementally bypass defenses and achieve a malicious goal", "It uses only one prompt", "It targets the database directly", "It is done manually"],
    correct: [0],
    explanation: "Agent attacks are often multi-turn trajectories where the attacker uses the agent's own tools against it over time.",
    source: { label: "Red Teaming", url: "../curriculum/intermediate/12-agent-red-teaming-and-adversarial-testing/12_agent_red_teaming_and_adversarial_testing.ipynb" }
  },
  // Module 13
  {
    id: "a1-1",
    category: "13 - Observability as Governance Evidence",
    prompt: "Why are standard text logs insufficient for agent observability?",
    options: ["They take up too much disk space", "They lack the hierarchical context of trajectories, tool calls, and reasoning steps", "They are too hard to read", "They are not encrypted"],
    correct: [1],
    explanation: "Agents execute complex, nested workflows. Traces (like OpenTelemetry) are required to reconstruct the exact chain of events.",
    source: { label: "Observability", url: "../curriculum/advanced/13-observability-as-goveernance-evidence/13_observability_as_goveernance_evidence.ipynb" }
  },
  {
    id: "a1-2",
    category: "13 - Observability as Governance Evidence",
    prompt: "What role does OpenTelemetry play in governance evidence?",
    options: ["It encrypts data", "It provides a standardized way to trace execution paths across distributed agent components", "It acts as the PEP", "It stores passwords"],
    correct: [1],
    explanation: "OpenTelemetry allows enterprises to capture structured spans for LLM calls, tool executions, and policy decisions.",
    source: { label: "Observability", url: "../curriculum/advanced/13-observability-as-goveernance-evidence/13_observability_as_goveernance_evidence.ipynb" }
  },
  // Module 14
  {
    id: "a2-1",
    category: "14 - Agent Evaluation and Continuous Governance",
    prompt: "What is the purpose of an 'LLM-as-judge' in continuous evaluation?",
    options: ["To arrest hackers", "To automatically score the quality, safety, or compliance of an agent's outputs against a rubric", "To decide which model to use", "To generate code"],
    correct: [1],
    explanation: "LLM-as-judge allows scalable, automated evaluation of subjective agent behaviors during CI/CD.",
    source: { label: "Agent Evaluation", url: "../curriculum/advanced/14-agent-evaluation-and-continuous-governance/14_agent_evaluation_and_continuous_governance.ipynb" }
  },
  {
    id: "a2-2",
    category: "14 - Agent Evaluation and Continuous Governance",
    prompt: "Why is 'cost per successful task' a key governance metric?",
    options: ["To maximize API usage", "It measures the efficiency of the agent's autonomy and whether the token usage justifies the business value", "To punish developers", "To lower server costs"],
    correct: [1],
    explanation: "Agents can get stuck in loops or use excessive tokens. This metric ties autonomous behavior directly to ROI.",
    source: { label: "Agent Evaluation", url: "../curriculum/advanced/14-agent-evaluation-and-continuous-governance/14_agent_evaluation_and_continuous_governance.ipynb" }
  },
  // Module 15
  {
    id: "a3-1",
    category: "15 - Governance Control Plane Architecture",
    prompt: "In a Governance Control Plane, what is the difference between the control plane and the data plane?",
    options: ["They are identical", "The control plane manages policies and configurations, while the data plane executes the agent's actions", "The control plane is for testing only", "The data plane stores policies"],
    correct: [1],
    explanation: "Separating the planes ensures that governance administrators can change policies without altering the agent's code.",
    source: { label: "Control Plane Architecture", url: "../curriculum/advanced/15-governance-control-plane-architecture/15_governance_control_plane_architecture.ipynb" }
  },
  {
    id: "a3-2",
    category: "15 - Governance Control Plane Architecture",
    prompt: "What is an 'evidence store' used for?",
    options: ["To store training data", "To immutably record policy decisions, approvals, and trajectories for audit purposes", "To cache API responses", "To store user profiles"],
    correct: [1],
    explanation: "An evidence store provides undeniable proof of the agent's behavior and the governance controls that were applied.",
    source: { label: "Control Plane Architecture", url: "../curriculum/advanced/15-governance-control-plane-architecture/15_governance_control_plane_architecture.ipynb" }
  },
  // Module 16
  {
    id: "a4-1",
    category: "16 - Enterprise Agent Governance Operating Model",
    prompt: "What is the purpose of an 'Agent System Card'?",
    options: ["To give the agent a badge", "To document the agent's intended use, capabilities, risk tier, and known limitations for stakeholders", "To track GPU usage", "To format outputs"],
    correct: [1],
    explanation: "System cards create transparency, ensuring users and risk teams understand the boundaries of the agent.",
    source: { label: "Operating Model", url: "../curriculum/advanced/16-enterprise-agent-governance-operating-model/16_enterprise_agent_governance_operating_model.ipynb" }
  },
  {
    id: "a4-2",
    category: "16 - Enterprise Agent Governance Operating Model",
    prompt: "Why is a recertification process necessary for enterprise agents?",
    options: ["To generate more paperwork", "To ensure the agent still complies with policies after model updates or environment changes", "To change the agent's name", "To delete old logs"],
    correct: [1],
    explanation: "Agents degrade or drift as backend APIs or underlying LLMs change. Periodic recertification ensures continued safety.",
    source: { label: "Operating Model", url: "../curriculum/advanced/16-enterprise-agent-governance-operating-model/16_enterprise_agent_governance_operating_model.ipynb" }
  },
  // Module 17
  {
    id: "a5-1",
    category: "17 - Capstone Governed Autonomous Enterprise Agent",
    prompt: "In a production enterprise agent, what is the trade-off between strict policy enforcement and agent capability?",
    options: ["Strict policies make the agent run faster", "Strict policies reduce risk but may block the agent from completing complex or novel tasks", "There is no trade-off", "Strict policies increase token usage"],
    correct: [1],
    explanation: "Governance must balance safety with utility; overly strict policies degrade the autonomous value of the agent.",
    source: { label: "Capstone", url: "../curriculum/advanced/17-capstone-governed-autonomous-enterprise-agent/17_capstone_governed_autonomous_enterprise_agent.ipynb" }
  },
  {
    id: "a5-2",
    category: "17 - Capstone Governed Autonomous Enterprise Agent",
    prompt: "What is the ultimate goal of governed autonomous enterprise agents?",
    options: ["To replace all human workers", "To safely scale AI action-taking while maintaining verifiable compliance and human accountability", "To write more code", "To eliminate the need for authorization"],
    correct: [1],
    explanation: "Governed autonomy allows businesses to delegate tasks securely without losing control or compliance.",
    source: { label: "Capstone", url: "../curriculum/advanced/17-capstone-governed-autonomous-enterprise-agent/17_capstone_governed_autonomous_enterprise_agent.ipynb" }
  }
];
