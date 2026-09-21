# AI Governance for Agents

A comprehensive curriculum for transitioning from AI model governance to Autonomous Agent governance. This repository hosts the learning hub, an initial knowledge check quiz, and deterministic Jupyter notebooks for every module in the curriculum.

🚀 **[Access the Learning Hub](https://mahsa-teimourikia.github.io/ai-governance-ai-agents/)** | 📝 **[Take the Initial Knowledge Quiz](https://mahsa-teimourikia.github.io/ai-governance-ai-agents/quiz/)**

The curriculum is being deepened one module at a time. See the
**[course improvement plan](COURSE_IMPROVEMENT_PLAN.md)** for quality gates,
claim-to-proof expectations, current status, and the ordered roadmap.

## Quickstart

### Prerequisites
- Node.js >= 18
- Python 3.11+
- `uv` package manager

### Environment Setup

Run the following command to set up both the Python and Node.js environments:
```bash
make setup-contributor
```

### Viewing the Learning Hub locally

Simply open `hub/index.html` in your web browser. No local development server is required for the hub!

### Running Tests

```bash
make test
```

To run the fully audited Course 1 or Course 2 lab and focused invariant tests:

```bash
make course-01
make course-02
```

## Curriculum Structure

The curriculum is structured into three continuous tracks representing the maturity of Autonomous Agent Governance, mapped directly into the Jupyter notebooks inside the `curriculum/` folder.

### 🟢 Beginner Track
*Foundations of agent governance, risk tiering, and basic policy controls.*
- **01. From AI Governance to Agent Governance**
- **02. Agent Risk Modeling & Autonomy Classification**
- **03. Standards, Regulation & Governance Operating Model**
- **04. Agent Identity & Delegated Authority**
- **05. Fine-Grained Authorization for Agents**

### 🟡 Intermediate Track
*Advanced tooling, human-in-the-loop, and multi-agent coordination.*
- **06. Policy-as-Code & Runtime Governance**
- **07. Tool & MCP Governance**
- **08. Human Oversight & Bounded Autonomy**
- **09. Data, RAG & Memory Governance**
- **10. Multi-Agent Governance & Delegation**
- **11. Guardrails & Agent Security**
- **12. Agent Red Teaming & Adversarial Testing**

### 🔴 Advanced Track
*Full enterprise integration, continuous evaluation, and control plane architecture.*
- **13. Observability as Governance Evidence**
- **14. Agent Evaluation & Continuous Governance**
- **15. Governance Control Plane Architecture**
- **16. Enterprise Agent Governance Operating Model**
- **17. Capstone: Governed Autonomous Enterprise Agent**

## Repository Layout

- **`curriculum/`**: Contains deep-dive lessons, notebooks, topic assets, and—beginning with the audited modules—reusable labs.
- **`hub/`**: The static Learning Hub, lesson registry, checkpoints, progress tracking, and full knowledge quiz deployed by GitHub Pages.
- **`tests/`**: Repository and course-specific validation, including runtime invariants and top-to-bottom notebook execution for audited modules.
- **`.github/workflows/`**: Automated CI/CD pipelines including notebook parsing, Python testing, and GitHub Pages deployment.

## Contributing
See the `setup-contributor` flow above to get started. All notebooks are validated for `nbformat == 4` and must pass execution checks.
