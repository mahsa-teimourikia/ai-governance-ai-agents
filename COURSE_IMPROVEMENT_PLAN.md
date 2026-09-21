# Course improvement plan

This plan turns the 17-module curriculum into a sequence of independently
teachable, executable, and reviewable course increments. A module is considered
revised only when its lesson, reusable lab, notebook, tests, checkpoint, Hub
entry, sources, and learner navigation agree.

## Course thesis

A graduate of the path should be able to explain, implement, evaluate, and
productionize an enterprise agent-governance system in which models propose
actions while trusted application controls authenticate, authorize, approve,
execute, verify, and record consequential effects.

## Quality gates for every module

Each course pass will:

1. audit the existing lesson, notebook, assets, adjacent modules, Hub entry,
   checkpoint, dependencies, and tests;
2. verify changing claims against primary standards, research, and official
   project documentation;
3. preserve strong material and repair duplication, unsupported claims, broken
   paths, unsafe examples, and disconnected exercises;
4. deliver one credential-free vertical slice with typed contracts, observable
   decisions, representative failure injection, explicit evaluation
   denominators, and a production upgrade path;
5. compare the taught architecture with a simpler baseline and explain the
   technology-selection trade-offs;
6. test the material's central invariants and run the notebook top-to-bottom;
   and
7. perform a final claim-versus-code review after validation passes.

## Ordered roadmap

| Order | Module | Improvement focus | Status |
|---:|---|---|---|
| 1 | From AI Governance to Agent Governance | System/action boundary, runtime PEP, bound approvals, idempotency, evidence, architecture baseline | Implemented and locally validated |
| 2 | Agent Risk Modeling & Autonomy Classification | Transparent risk dimensions, FMEA/abuse cases, calibrated control profiles, sensitivity analysis | Next |
| 3 | Standards, Regulation & Governance Operating Model | Current NIST/ISO/EU/OWASP crosswalk, evidence artifacts, accountable RACI and lifecycle gates | Planned |
| 4 | Agent Identity & Delegated Authority | Authenticated workload identity, OAuth token exchange, attenuation, revocation, non-repudiation | Planned |
| 5 | Fine-Grained Authorization for Agents | RBAC/ABAC/ReBAC comparison, OpenFGA/Cedar/OPA selection, dual user/task authorization | Planned |
| 6 | Policy-as-Code & Runtime Governance | PDP/PEP separation, Rego/Cedar policy tests, versioning, fail-closed and cached-decision trade-offs | Planned |
| 7 | Tool & MCP Governance | Tool discovery, MCP authorization, confused-deputy defense, schema/output validation, gateway controls | Planned |
| 8 | Human Oversight & Bounded Autonomy | Meaningful approval, receipt integrity, queues, expiry, concurrency, fatigue and progressive autonomy | Planned |
| 9 | Data, RAG & Memory Governance | Authorization-before-retrieval, provenance/freshness, injection defense, scoped memory lifecycle | Planned |
| 10 | Multi-Agent Governance & Delegation | Capability attenuation, handoff contracts, shared-state integrity, budgets and coordination tax | Planned |
| 11 | Guardrails & Agent Security | Defense in depth, OWASP agentic threats, sandboxing, deterministic enforcement and containment | Planned |
| 12 | Agent Red Teaming & Adversarial Testing | Threat-led campaigns, PyRIT/custom harnesses, reproducible attacks, severity and regression gates | Planned |
| 13 | Observability as Governance Evidence | OpenTelemetry semantics, evidence integrity, privacy, trace completeness and outcome verification | Planned |
| 14 | Agent Evaluation & Continuous Governance | Labelled datasets, trajectory and safety metrics, slicing, uncertainty, release decisions | Planned |
| 15 | Governance Control Plane Architecture | Registry, distributed policy/evidence planes, lifecycle state, resilience and multi-tenant isolation | Planned |
| 16 | Enterprise Agent Governance Operating Model | Intake, ownership, supply chain, change control, recertification, incidents and exceptions | Planned |
| 17 | Capstone: Governed Autonomous Enterprise Agent | Integrated realistic system, failure/recovery drills, architecture comparison and operational evidence | Planned |

## Course 1 claim-to-proof map

### Course 1 audit decisions

- **Retain:** the system-not-model mental model, information/action-risk
  distinction, design-time/runtime split, governance-surface map, complementary
  NIST/ISO/OWASP framing, procurement scenario, and existing accessible SVGs.
- **Deepen:** architecture selection, current-state classification, approval
  integrity, retry semantics, evidence fields, metric definitions, production
  limitations, and exercises requiring implementation and judgment.
- **Consolidate:** replace the README's aspirational notebook specification and
  the notebook's duplicated embedded implementation with one tested `lab.py`
  imported by the guided notebook.
- **Repair:** remove the reusable approval Boolean, prevent receipt replay and
  proposal alteration, prevent idempotency-key reuse for changed requests,
  derive authority from authenticated context, replace optional network calls
  in the canonical path, and add real top-to-bottom notebook execution.
- **Add:** a direct-tool architecture baseline, labelled evaluation dataset,
  explicit metric populations, cross-tenant and injection failures, a
  technology landscape, September 2026 research snapshot, focused invariant
  tests, Hub lab navigation, and CI triggers for all curriculum artifacts.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Model output does not grant authority | Lesson mental model and trust boundary | `GovernanceGateway.evaluate` uses authenticated context and a task grant | Spoofed identity and prompt-injection tests |
| Consequential actions require runtime control | Design/runtime and PDP/PEP sections | `GovernanceGateway.execute` mediates every adapter call | Out-of-scope vendor and expired-grant tests |
| Approval is a governed artifact | Approval-integrity section | Proposal-digest-bound `ApprovalReceipt` and atomic store | Altered, expired, and replayed receipts fail closed |
| Retries do not duplicate effects | Production and failure sections | Idempotency ledger keyed to action digest | Same-action retry and changed-action conflict tests |
| Evidence supports review without hidden reasoning | Observability section | Structured `EvidenceEvent` with reason and policy version | Notebook reconstructs decisions from evidence |
| Governance improves outcomes on the teaching fixture | Evaluation section | Labelled scenario dataset and architecture comparison | Explicit populations and forbidden-outcome rate |
