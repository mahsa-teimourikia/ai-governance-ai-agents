export type Subject = {
  id: string;
  level: "Beginner" | "Intermediate" | "Advanced";
  step: string;
  title: string;
  description: string;
  time: string;
  outcome: string;
  lesson: string;
  exercise: string;
  failures: string[];
  notebook: string;
  refs: string[];
  code: string;
  quiz: { q: string; options: string[]; answer: number[] }[];
};

export const subjects: Subject[] = [
  {
    id: "b1", level: "Beginner", step: "01", title: "From AI Governance to Agent Governance",
    description: "Understand the shift from models to autonomous agents.", time: "60 min", outcome: "Map governance boundaries.",
    lesson: "Governance must shift from information risk to action risk.", exercise: "Build a simple agent.",
    failures: ["Ignoring autonomy levels", "Missing human oversight"], notebook: "curriculum/beginner/01-from-ai-governance-to-agent-governance/01_from_ai_governance_to_agent_governance.ipynb",
    refs: [], code: "agent = Agent()", quiz: [{ q: "What is the main shift?", options: ["Info to Action risk", "Models to data"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "b2", level: "Beginner", step: "02", title: "Agent Risk Modeling and Autonomy Classification",
    description: "Autonomy levels and impact.", time: "60 min", outcome: "Classify risk tiers.",
    lesson: "Autonomy levels dictate required controls.", exercise: "Build an agent risk classifier.",
    failures: ["Blast radius underestimated"], notebook: "curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/02_agent_risk_modeling_and_autonomy_classification.ipynb",
    refs: [], code: "classify_risk()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "b3", level: "Beginner", step: "03", title: "Standards Regulation and Governance Operating Model",
    description: "NIST, ISO, OWASP.", time: "60 min", outcome: "Generate governance evidence pack.",
    lesson: "Frameworks provide structural assurance.", exercise: "Map controls.",
    failures: ["Missing evidence"], notebook: "curriculum/beginner/03-standards-regulation-and-governance-operating-model/03_standards_regulation_and_governance_operating_model.ipynb",
    refs: [], code: "map_controls()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "b4", level: "Beginner", step: "04", title: "Agent Identity and Delegated Authority",
    description: "Agent as principal.", time: "60 min", outcome: "Delegation and impersonation.",
    lesson: "Agents need identity.", exercise: "Implement delegated identity.",
    failures: ["Broad permissions"], notebook: "curriculum/beginner/04-agent-identity-and-delegated-authority/04_agent_identity_and_delegated_authority.ipynb",
    refs: [], code: "delegate_auth()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "b5", level: "Beginner", step: "05", title: "Fine Grained Authorization for Agents",
    description: "Task-based authorization.", time: "60 min", outcome: "Zero standing privilege.",
    lesson: "Authz is context dependent.", exercise: "Implement a procurement agent.",
    failures: ["Confused deputy"], notebook: "curriculum/beginner/05-fine-grained-authorization-for-agents/05_fine_grained_authorization_for_agents.ipynb",
    refs: [], code: "check_authz()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "i1", level: "Intermediate", step: "06", title: "Policy as Code and Runtime Governance",
    description: "Separating reasoning from authority.", time: "60 min", outcome: "Policy versioning.",
    lesson: "PDP/PEP architecture.", exercise: "Enforce thresholds.",
    failures: ["Bypass controls"], notebook: "curriculum/intermediate/06-policy-as-code-and-runtime-governance/06_policy_as_code_and_runtime_governance.ipynb",
    refs: [], code: "enforce_policy()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "i2", level: "Intermediate", step: "07", title: "Tool and MCP Governance",
    description: "Tools as capability boundaries.", time: "60 min", outcome: "Tool allowlists.",
    lesson: "MCP trust boundaries.", exercise: "Build an MCP server.",
    failures: ["Tool poisoning"], notebook: "curriculum/intermediate/07-tool-and-mcp-governance/07_tool_and_mcp_governance.ipynb",
    refs: [], code: "validate_tool()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "i3", level: "Intermediate", step: "08", title: "Human Oversight and Bounded Autonomy",
    description: "HITL vs HOTL.", time: "60 min", outcome: "Reversibility.",
    lesson: "Meaningful human control.", exercise: "Approval routing.",
    failures: ["Approval fatigue"], notebook: "curriculum/intermediate/08-human-oversight-and-bounded-autonomy/08_human_oversight_and_bounded_autonomy.ipynb",
    refs: [], code: "request_approval()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "i4", level: "Intermediate", step: "09", title: "Data RAG and Memory Governance",
    description: "Authorized retrieval.", time: "60 min", outcome: "Data lineage.",
    lesson: "Memory poisoning mitigation.", exercise: "Secure RAG agent.",
    failures: ["Cross-user leakage"], notebook: "curriculum/intermediate/09-data-rag-and-memory-governance/09_data_rag_and_memory_governance.ipynb",
    refs: [], code: "secure_rag()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "i5", level: "Intermediate", step: "10", title: "Multi Agent Governance and Delegation",
    description: "Recursive delegation.", time: "60 min", outcome: "Authority propagation.",
    lesson: "Agent-to-agent boundaries.", exercise: "Agent identity chains.",
    failures: ["Privilege amplification"], notebook: "curriculum/intermediate/10-multi-agent-governance-and-delegation/10_multi_agent_governance_and_delegation.ipynb",
    refs: [], code: "delegate_task()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "i6", level: "Intermediate", step: "11", title: "Guardrails and Agent Security",
    description: "Prompt injection and indirect injection.", time: "60 min", outcome: "Layered defenses.",
    lesson: "Goal hijacking.", exercise: "Attack an agent and mitigate.",
    failures: ["Data exfiltration"], notebook: "curriculum/intermediate/11-guardrails-and-agent-security/11_guardrails_and_agent_security.ipynb",
    refs: [], code: "apply_guardrails()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "i7", level: "Intermediate", step: "12", title: "Agent Red Teaming and Adversarial Testing",
    description: "Attack surface discovery.", time: "60 min", outcome: "Threat scenarios.",
    lesson: "Continuous red teaming.", exercise: "Automated attack campaign.",
    failures: ["Security regression"], notebook: "curriculum/intermediate/12-agent-red-teaming-and-adversarial-testing/12_agent_red_teaming_and_adversarial_testing.ipynb",
    refs: [], code: "red_team()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "a1", level: "Advanced", step: "13", title: "Observability as Governance Evidence",
    description: "Why standard logs are insufficient.", time: "60 min", outcome: "Traces and trajectories.",
    lesson: "Evidence retention.", exercise: "Instrument an agent.",
    failures: ["Missing provenance"], notebook: "curriculum/advanced/13-observability-as-goveernance-evidence/13_observability_as_goveernance_evidence.ipynb",
    refs: [], code: "instrument()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "a2", level: "Advanced", step: "14", title: "Agent Evaluation and Continuous Governance",
    description: "Task success and trajectory quality.", time: "60 min", outcome: "Autonomy rate.",
    lesson: "Evaluation metrics.", exercise: "Build an eval suite.",
    failures: ["Cost overrides"], notebook: "curriculum/advanced/14-agent-evaluation-and-continuous-governance/14_agent_evaluation_and_continuous_governance.ipynb",
    refs: [], code: "evaluate()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "a3", level: "Advanced", step: "15", title: "Governance Control Plane Architecture",
    description: "Governance system of record.", time: "60 min", outcome: "Enforcement points.",
    lesson: "Control plane vs data plane.", exercise: "Miniature control plane.",
    failures: ["Split brain"], notebook: "curriculum/advanced/15-governance-control-plane-architecture/15_governance_control_plane_architecture.ipynb",
    refs: [], code: "control_plane()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "a4", level: "Advanced", step: "16", title: "Enterprise Agent Governance Operating Model",
    description: "Ownership and onboarding.", time: "60 min", outcome: "Change management.",
    lesson: "Recertification and incident response.", exercise: "Onboarding workflow.",
    failures: ["Orphaned agents"], notebook: "curriculum/advanced/16-enterprise-agent-governance-operating-model/16_enterprise_agent_governance_operating_model.ipynb",
    refs: [], code: "onboard()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  },
  {
    id: "a5", level: "Advanced", step: "17", title: "Capstone Governed Autonomous Enterprise Agent",
    description: "Full production architecture.", time: "60 min", outcome: "Full stack from the course.",
    lesson: "Trade-offs.", exercise: "Capstone project.",
    failures: ["System failure"], notebook: "curriculum/advanced/17-capstone-governed-autonomous-enterprise-agent/17_capstone_governed_autonomous_enterprise_agent.ipynb",
    refs: [], code: "capstone()", quiz: [{ q: "Q1", options: ["A", "B"], answer: [0] }, { q: "Q2", options: ["A", "B"], answer: [0] }]
  }
];
