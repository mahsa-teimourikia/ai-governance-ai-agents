# AI Governance for Agents

A comprehensive curriculum for transitioning from AI model governance to autonomous-agent governance. This repository hosts the complete 17-course Learning Hub, a 55-question knowledge check, and deterministic Jupyter notebooks for every module.

🚀 **[Access the Learning Hub](https://mahsa-teimourikia.github.io/ai-governance-ai-agents/)** | 📝 **[Take the 55-question Knowledge Check](https://mahsa-teimourikia.github.io/ai-governance-ai-agents/quiz/)**

The curriculum was improved and validated one module at a time. See the
**[course improvement plan](COURSE_IMPROVEMENT_PLAN.md)** for quality gates,
claim-to-proof expectations, and the completed review record.

## Quickstart

### Prerequisites
- Node.js >= 18
- Python 3.11+
- `uv` package manager

### Environment Setup

Use Python 3.11, 3.12, or 3.13 and install
[uv](https://docs.astral.sh/uv/getting-started/installation/). The supported
range is enforced in project metadata and tested in CI.

Install the exact Python environment recorded in `uv.lock`:
```bash
make setup-contributor
```

Node.js is used only for dependency-free Learning Hub validation; there is no
separate JavaScript package installation.

### Viewing the Learning Hub locally

Serve the Hub locally so browser module imports use HTTP rather than the
restricted `file://` protocol:

```bash
make serve-hub
```

Then open [http://localhost:8000](http://localhost:8000).

### Running Tests

```bash
make validate
```

This verifies the lock file and installed packages, validates Hub JavaScript,
checks every tracked local curriculum link and quiz record, and runs the full
Python and notebook test suite. `make test` runs only the Python tests.

### Dependency policy

`pyproject.toml` declares only libraries imported by the tracked labs, with
compatibility bounds around fast-moving SDKs. `uv.lock` records the exact tested
environment, and setup, CI, tests, and course targets all enforce that lock.
Inspect the current direct versions with:

```bash
uv tree --locked --depth 1
```

When intentionally refreshing dependencies, run `uv lock --upgrade`, reinstall
with `make setup-contributor`, and require `make validate` to pass before
committing the new lock.

To run any fully audited Course 1–17 lab and its focused invariant tests:

```bash
make course-01
make course-02
make course-03
make course-04
make course-05
make course-06
make course-07
make course-08
make course-09
make course-10
make course-11
make course-12
make course-13
make course-14
make course-15
make course-16
make course-17
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
