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
| 1 | From AI Governance to Agent Governance | System/action boundary, runtime PEP, bound approvals, idempotency, evidence, architecture baseline | Merged in PR #9 |
| 2 | Agent Risk Modeling & Autonomy Classification | Transparent risk dimensions, failure/threat separation, evidence-bound residual risk, graph deltas | Merged in PR #10 |
| 3 | Standards, Regulation & Governance Operating Model | Current NIST/ISO/EU/OWASP crosswalk, evidence artifacts, accountable RACI and lifecycle gates | Merged in PR #11 |
| 4 | Agent Identity & Delegated Authority | Authenticated workload identity, OAuth token exchange, attenuation, revocation, evidence limits | Merged in PR #12 |
| 5 | Fine-Grained Authorization for Agents | RBAC/ABAC/ReBAC comparison, OpenFGA/Cedar/OPA selection, dual user/task authorization | Merged in PR #13; evidence follow-up in PR #14 |
| 6 | Policy-as-Code & Runtime Governance | PDP/PEP separation, Rego/Cedar policy tests, versioning, fail-closed and cached-decision trade-offs | Merged in PR #16; release-evidence follow-up in PR #17 |
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

## Course 2 claim-to-proof map

### Course 2 audit decisions

- **Retain:** the multidimensional risk model, capability-level assessment,
  autonomy taxonomy, FMEA concepts, failure/attack distinction, procurement
  scenario, OWASP/MITRE sources, NetworkX graph idea, and existing SVGs.
- **Deepen:** evidence quality, uncertainty, explicit risk gates, control-claim
  scope, stale evidence, architecture deltas, disposition ownership, method/tool
  comparison, and state-of-the-art/open-problem framing.
- **Consolidate:** move contracts, classification, graph analysis, evidence
  validation, control profiles, and labelled evaluation into one tested `lab.py`
  imported by the notebook.
- **Repair:** remove arbitrary weighted risk decimals, additive fictional control-
  effectiveness percentages, normalized blast-radius scores, random Monte Carlo
  outputs presented without empirical distributions, automatic residual-risk
  reduction, notebook package installation, live API paths, and file writes.
- **Add:** an explicit false-precision baseline, exact reachability facts,
  scenario-specific mitigation claims, tested/current evidence gates, expired and
  wrong-scenario failure cases, three-case labelled evaluation, production
  upgrades, focused tests, and Hub navigation.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Autonomy is observable authority, not a framework label | Autonomy model | `classify_autonomy` uses state-change, approval, planning, delegation, and termination signals | Same-autonomy/different-impact test |
| One decimal must not hide risk shape | Scoring pitfalls and lab baseline | Explicit `RiskDimensions` and versioned gate rules | Two vectors share an average but require different reasoning |
| Failure and attack require distinct analysis | FMEA plus OWASP/NIST/ATLAS sections | Typed `ScenarioKind` and separate fixtures | Scenario-kind regression test |
| Blast radius should be inspectable | Graph-analysis section | NetworkX returns reachable, writable, severe, cross-zone, and delegated facts | Removing payment reachability changes exact graph facts |
| Controls reduce risk only with evidence | Residual-risk section | `MitigationClaim` plus scenario-bound `ControlEvidence` | Documented, expired, stale, and wrong-scenario evidence is rejected |
| Fixture results have explicit scope | Evaluation section | Three labelled cases with numerator and denominator | Exact evaluation-report assertion |

## Course 3 claim-to-proof map

### Course 3 audit decisions

- **Retain:** the standards-versus-regulation distinction, current EU timeline,
  three-lines model, enterprise inventory, control crosswalk, stage gates, RACI,
  exceptions, recertification, OSCAL introduction, procurement scenario, and
  existing SVGs.
- **Deepen:** claim-bounded crosswalk semantics, specialist applicability
  routing, exact evidence populations, system/version binding, evidence
  freshness, non-waivable controls, independent assurance, and change scope.
- **Consolidate:** move inventory, control selection, reviews, RACI, evidence,
  gate, exception, recertification, package, and OSCAL projection logic into one
  tested `lab.py` imported by the notebook.
- **Repair:** remove notebook package installation, random IDs, `date.today`,
  generated repository files, average evidence thresholds, automatic legal
  classification, and an outdated Compliance Trestle/OSCAL version claim.
- **Add:** a spreadsheet baseline comparison, immutable Pydantic contracts,
  digest-bound gate request and decision, rejected-evidence reasons, five
  labelled gate cases, focused tests, Hub lab navigation, and a Course 3 CI
  target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Legal applicability stays separate from internal risk | EU AI Act and inventory sections | `build_applicability_record` routes named specialist reviews | Pending EU review produces `specialist_review_required` |
| Crosswalks do not claim compliance | Control-crosswalk and OSCAL sections | `FrameworkMapping.relationship` is fixed to `supports` | Gate model forbids `legal_compliance_established=true` |
| Evidence is scoped and current | Evidence and stage-gate sections | `assess_evidence` checks system/version/result/age/validity | Wrong-version, failed, expired, and future evidence is rejected |
| Accountability is enforceable | RACI and three-lines sections | Typed `RACIEntry` and complete-activity validation | Multiple accountable roles and missing activities fail |
| Critical gaps cannot be averaged away | Stage-gate section and notebook baseline | Exact requirement population and decision reason codes | One missing item blocks despite high aggregate completeness |
| Exceptions are bounded | Exception section | `ExceptionRecord` plus eligibility and expiry checks | Authorization exceptions and expired records are refused |
| Change triggers recertification | Change-management section | `assess_change` returns exact triggers and review scopes | Expanded authority, jurisdiction, and affected groups require full review |
| Machine-readable artifacts remain honest | OSCAL section | Package JSON Schema and OSCAL 1.2.3 teaching projection | Projection is labelled non-conformant and requires official validation |

## Course 4 claim-to-proof map

### Course 4 audit decisions

- **Retain:** the human/agent/workload distinction, identity-versus-authorization
  boundary, SPIFFE/SPIRE introduction, RFC 8693 and RFC 9700 coverage, task
  authority, OpenFGA/Cedar/OPA comparison, confused-deputy example,
  procurement scenario, and existing SVGs.
- **Deepen:** authenticated source-of-truth binding, delegation versus
  impersonation, strict JWT validation, sender constraint, operation
  idempotency, atomic consumption, complete attenuation, revocation lineage,
  evidence semantics, method/tool selection, and emerging WIMSE work.
- **Consolidate:** move all reusable identity, grant, verification, attenuation,
  ledger, evidence, and evaluation logic into one tested `lab.py` imported by
  the canonical notebook.
- **Repair:** remove notebook package installation, UUIDs, wall-clock behavior,
  generated RSA keys, mutable global authorization state, non-atomic call-count
  checks, a vague optional live SDK cell, permission-only attenuation, and the
  implication that a signed log automatically proves non-repudiation.
- **Add:** a scope-only unsafe baseline, registered workload selectors,
  deterministic Ed25519 teaching tokens, intent digests, actor/policy versions,
  exact context binding, thread-safe operation consumption, descendant
  revocation, seven labelled cases, focused concurrency/security tests, Hub lab
  navigation, accessible diagram descriptions, and a Course 4 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Identity derives from trusted state | Identity and workload sections | `bind_trusted_context` resolves registered principals and selectors | Cross-tenant, stale, untrusted-domain, and mismatched-workload tests |
| A signed token is not sufficient authority | OAuth/JWT and enforcement sections | `verify_training_token` then `GrantLedger.authorize_and_consume` | Tampering, wrong header/algorithm, audience, time, task, resource, and amount tests |
| Delegation cannot exceed approved intent | Grant and attenuation sections | `build_root_grant` binds `TaskIntent` digest and constraints | Action, resource, vendor, amount, call, lifetime, audience, and depth amplification tests |
| One-call authority survives concurrency and retries | Security properties and lifecycle sections | locked consumption plus operation/request digest ledger | Eight concurrent operations permit exactly one; altered retry is denied |
| Parent revocation invalidates descendants | Revocation lifecycle section | lineage traversal in `GrantLedger` | Revoked ancestor blocks child use and new child issuance |
| Audit evidence has explicit limits | Evidence section | `AuditEvent` records identities, versions, reasons, and digests | Raw bearer token is absent; prose distinguishes authorization from actual effect |
| Metrics expose safety errors | Evaluation section | seven-case `run_evaluation` summary | Exact forbidden and legitimate populations plus race-test denominator |

## Course 5 claim-to-proof map

### Course 5 audit decisions

- **Retain:** the RBAC/ABAC/ReBAC/contextual comparison, PDP/PEP boundary,
  dual user/task authorization, OpenFGA/Cedar/OPA selection guidance, managed
  AWS options, TOCTOU/cache discussion, procurement scenario, and research
  pointers.
- **Deepen:** authoritative attribute provenance, hard deny versus escalation,
  request-bound approval, decision/effect separation, atomic call consumption,
  idempotent retries, outage recovery, consistency/version evidence, explicit
  evaluation populations, and live-engine integration boundaries.
- **Consolidate:** place reusable identity, relationship, attribute, policy,
  approval, PEP, effect, evidence, SDK-request, and evaluation behavior in one
  deterministic `lab.py` imported by the notebook and focused tests.
- **Repair:** remove runtime package installation, wall-clock and random IDs,
  notebook-only mutable policy state, file writes, optional network calls that
  hide failures, boolean approval, and fabricated purchase success.
- **Add:** a deliberately unsafe role-only baseline, current OpenFGA SDK request
  objects, ten labelled comparison cases, stale-state reauthorization, an
  eight-worker call-budget race, unknown-outcome handling, accessible diagrams,
  a judgment-focused Hub checkpoint, and a Course 5 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Role/scope is not sufficient | Models and boundary sections | unsafe role-only baseline | Baseline allows all seven forbidden evaluation cases |
| User and task authority are independent | Dual authorization section | local relationship evaluator and OpenFGA SDK checks | Wrong actor, resource, subject, and tenant tests |
| Context is authoritative and current | Source-of-truth section | versioned task/resource/vendor/risk records | Missing, stale, mismatched, sanctioned, and high-risk tests |
| Approval is narrow | Approval section | exact request-bound single-use receipt | Mutation, expiry, role, reuse, and hard-deny tests |
| PEP protects effects | PDP/PEP and TOCTOU sections | immediate re-evaluation and observable adapter | Deny/escalate do not invoke; changed vendor blocks execution |
| Retries and budgets do not widen authority | Caching/retry sections | operation ledger and locked consumption | Mutated replay, idempotent effect, unknown outcome, concurrency tests |
| Evaluation semantics are explicit | Evaluation section | ten-case baseline/PDP comparison | Forbidden-allowed, false-denial, and missed-escalation populations |

## Course 6 claim-to-proof map

### Course 6 audit decisions

- **Retain:** the governance-document-to-runtime-control progression, layered
  policy domains, PDP/PEP distinction, Cedar and Rego introductions,
  risk-based escalation, policy lifecycle, shadow/canary deployment, drift,
  AgentCore example, procurement scenario, and existing diagrams.
- **Deepen:** trusted input provenance, immutable bundle digests, schema versus
  semantic validation, signed distribution, release-evidence binding,
  forbidden-to-escalation regressions, stable canary cohorts, known-good
  rollback, tenant-safe idempotency, unknown effects, minimized audit evidence,
  and OPA/AgentCore operational boundaries.
- **Consolidate:** move policy contracts, composition, control-plane lifecycle,
  gateway/adapter enforcement, evaluation, engine artifacts, and metrics into
  one deterministic `lab.py` imported by the notebook and tests.
- **Repair:** remove notebook package installation, UUIDs, wall-clock values,
  file writes, optional live-network calls, mutable notebook-only policy state,
  fabricated purchase success, and unbound release metrics.
- **Add:** an unsafe first-match baseline, ten labelled cases, semantic mutation
  killing, exact shadow metrics, content/corpus digests, non-bypassable effects,
  eight-worker retry testing, cross-tenant operation isolation, fail-closed
  outages, unknown-effect reconciliation, judgment checkpoints, and a Course 6
  CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Model claims are not policy facts | Thesis and trusted-context sections | `ActionProposal` is separate from `TrustedFacts` | Positive model claims cannot override a sanctioned-vendor deny |
| Layered decisions compose deterministically | Policy-composition section | `evaluate_policy` evaluates authorization, business, risk, and safety | Hard denials dominate simultaneous escalation conditions |
| Static validity is not semantic safety | Testing and automated-reasoning sections | `validate_bundle`, labelled corpus, and `shadow_metrics` | Hard-limit mutation passes static checks but is killed by `forbidden_not_denied` |
| Releases are exact and reversible | Lifecycle and deployment sections | immutable registry, digest-bound metrics, shadow, canary, promote, rollback | Wrong bundle evidence, skipped stages, invalid drafts, and never-active rollback targets fail |
| PEP protects real effects | Architecture and failure sections | `RuntimeGateway` capability plus `ProcurementAdapter` receipt | Outage, deny, escalate, direct bypass, altered replay, and unknown outcome do not create a new effect |
| Retries and tenants remain isolated | Runtime-evidence section | tenant/operation ledger and locked adapter | Eight concurrent retries create one effect; identical operation IDs across tenants remain distinct |
| Evidence is observable but minimized | Runtime-policy-evidence section | `DecisionAuditEvent` stores digests, versions, outcomes, and reasons | Raw vendor and subject records are absent from decision evidence |
| Metrics name their populations | Policy-testing section | ten-case `EvaluationSummary` and `ShadowMetrics` | Exact hard-deny, legitimate-allow, escalation, incorrect, and decision-flip denominators |
