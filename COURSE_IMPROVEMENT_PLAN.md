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
| 7 | Tool & MCP Governance | Tool discovery, MCP authorization, confused-deputy defense, schema/output validation, gateway controls | Merged in PR #19 |
| 8 | Human Oversight & Bounded Autonomy | Meaningful approval, receipt integrity, queues, expiry, concurrency, fatigue and progressive autonomy | Implemented in PR #21 |
| 9 | Data, RAG & Memory Governance | Authorization-before-retrieval, provenance/freshness, injection defense, scoped memory lifecycle | Implemented in PR #22 |
| 10 | Multi-Agent Governance & Delegation | Capability attenuation, handoff contracts, shared-state integrity, budgets and coordination tax | Implemented in PR #24 |
| 11 | Guardrails & Agent Security | Defense in depth, OWASP agentic threats, sandboxing, deterministic enforcement and containment | Implemented in PR #25 |
| 12 | Agent Red Teaming & Adversarial Testing | Threat-led campaigns, PyRIT/custom harnesses, reproducible attacks, severity and regression gates | Implemented in PR #26 |
| 13 | Observability as Governance Evidence | OpenTelemetry semantics, evidence integrity, privacy, trace completeness and outcome verification | Implemented in PR #27 |
| 14 | Agent Evaluation & Continuous Governance | Labelled datasets, trajectory and safety metrics, slicing, uncertainty, release decisions | Implemented in PR #28 |
| 15 | Governance Control Plane Architecture | Registry, distributed policy/evidence planes, lifecycle state, resilience and multi-tenant isolation | Implemented; PR pending |
| 16 | Enterprise Agent Governance Operating Model | Intake, ownership, supply chain, change control, recertification, incidents and exceptions | Planned |
| 17 | Capstone: Governed Autonomous Enterprise Agent | Integrated realistic system, failure/recovery drills, architecture comparison and operational evidence | Planned |

## Course 8 claim-to-proof map

### Course 8 audit decisions

- **Retain:** the autonomy ladder, risk-based routing, exact-action approval,
  separation of duties, pause/redirect/terminate concepts, reviewer-fatigue
  discussion, framework comparison, EU AI Act and ISO context, and accessible
  diagrams.
- **Deepen:** hard-denial precedence, authoritative reviewer context, distinct
  people and roles, typed durable state, optimistic concurrency, fact and policy
  versioning, atomic task budgets, ambiguous-effect reconciliation, outcome
  verification, metric populations, and the limitations of HITL primitives.
- **Consolidate:** replace duplicated mutable notebook logic with one tested
  `lab.py` imported by a guided, credential-free notebook.
- **Repair:** remove runtime package installs, random identifiers, wall-clock
  dependence, caller-owned reviewer dictionaries, raw approval booleans,
  mutable post-approval actions, non-atomic budgets, fabricated result checks,
  and outdated OpenAI documentation links.
- **Add:** real OpenAI and Microsoft approval descriptors, restart-safe
  checkpoints, pause/resume revalidation, concurrency and failure injection,
  a universal-HITL baseline, ten labelled routing cases, 42 focused invariant
  tests, Hub lab navigation, judgment checkpoints, and a production extension.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Human attention is routed without making denials approvable | Thesis and five-route policy | `route_action` evaluates trusted context, facts and envelope | Ten labelled cases; baseline overrides all four denials, candidate overrides none |
| Approval binds the exact consequence | Exact-action approval and pre-effect revalidation | Immutable action digest, approval request, policy/fact versions | Mutation, changed route, stale facts, expiry, and policy-change tests |
| Review authority is independent and atomic | Reviewer identity, quorum and durable-state sections | Authenticated reviewer context, distinct role slots, version transitions | Self-review, wrong tenant/role, duplicate role, rejection, and concurrent response tests |
| Operators can intervene before effects | Pause, redirect, terminate and revoke section | Versioned pause/resume/redirect/terminate methods | Stale resume, unauthorized operator, and terminal-state tests |
| External uncertainty is reconciled and verified | Execution and outcome sections | Idempotent adapter, reconciliation, exact effect comparison | Before/after commit and mismatched-effect injection tests |
| Framework examples use current common SDKs | Framework boundary and references | Real `needs_approval` and `approval_mode` descriptors | Tests inspect installed OpenAI and Microsoft tool objects |
| Oversight metrics have honest scope | Reviewer-quality section | Typed event population and exact counts | Deterministic latency, approval, disagreement and concentration assertions |

## Course 9 claim-to-proof map

### Course 9 audit decisions

- **Retain:** the data/RAG/session/memory distinctions, metadata propagation,
  identity-aware retrieval, relevance-versus-trust framing, poisoning defense,
  memory write gate, TTL/correction/deletion lifecycle, multi-agent boundary,
  governance metrics, procurement scenario, and existing diagrams.
- **Deepen:** tenant partitioning before ranking, group/purpose/clearance/trust
  filters, administrative bypasses, citations with exact digests, honest limits
  of injection detection, storage-enforced memory scope, source/subject deletion
  receipts, hosted-vector eventual consistency, and filtered ANN recall.
- **Consolidate:** move ingestion, chunking, retrieval, evidence, context,
  memory policy, lifecycle, fixtures, and evaluation into one deterministic
  `lab.py` imported by the notebook and tests.
- **Repair:** remove runtime package installation, UUIDs, wall-clock behavior,
  mutable global stores, post-retrieval access filtering, implicit durable
  writes, retained deleted values, synthetic dataframe metrics, and optional
  framework prose that did not create or test artifacts.
- **Add:** real OpenAI `SQLiteSession` and LangGraph `InMemoryStore` artifacts,
  source-version tombstones, cache eviction, content scrubbing, correction
  lineage, eight labelled retrieval cases, 48 focused tests, Hub navigation,
  judgment checkpoints, and a Course 9 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Security metadata survives derivation | Metadata and provenance sections | typed source/chunk contracts and deterministic digests | Missing access metadata and same-version mutation fail ingestion |
| Authorization precedes relevance | Authorized-retrieval and storage sections | tenant partition plus group/purpose/clearance/trust/freshness candidates feed TF-IDF | Cross-tenant, wrong-purpose, wrong-group, low-clearance, and stale tests return no scored result |
| Retrieved instructions remain untrusted data | Poisoning and context sections | indicator evidence, quarantine, delimiters, non-instruction contract | Highly relevant poisoned passage wins the baseline but never enters governed context |
| Memory cannot create authority | Memory-gate section | typed candidate categories and three-way decision | Authority, secret, restricted, procedural, and untrusted candidates cannot become durable memory |
| Memory scope and lifecycle are enforceable | Namespace, TTL, correction, and deletion sections | tenant/subject/purpose/task filters, expiry, supersession, source refs | Cross-scope reads fail; source/subject deletion scrubs values and invalidates results |
| Framework coverage is genuine and scoped | OpenAI and LangGraph sections | real in-memory SDK session/store with governed namespace | Tests show routing artifacts while prose rejects namespace strings as sufficient authorization |
| Evaluation names its populations | Evaluation section | eight labelled cases and exact exposure counts | Global baseline is 3/8 with cross-tenant/instruction/stale exposures; governed path is 8/8 with zero |

## Course 10 claim-to-proof map

### Course 10 audit decisions

- **Retain:** authority-chain and orchestration-pattern diagrams, delegation
  attenuation, manager/handoff distinctions, context minimization, confused-
  deputy framing, aggregate budgets, global halt, revocation, disagreement,
  audit reconstruction, and the procurement scenario.
- **Deepen:** authenticated human/agent identities, task and role intersection,
  tool-resource pairs, vendor scope, lineage versions, proposal-bound approval,
  operation mutation, worker leases, atomic task budgets, application-owned
  terminal state, evidence-bound disagreement, and coordination tax.
- **Consolidate:** replace mutable notebook globals with one typed deterministic
  `lab.py` imported by the guided notebook and 43 focused tests.
- **Repair:** remove runtime package installation, UUID/wall-clock dependence,
  independent non-atomic counters, unchecked tool/resource recombination,
  role-name authorization, fabricated successful effects, and outdated OpenAI
  SDK documentation links. Effect receipts are now explicitly simulated.
- **Add:** real credential-free OpenAI manager/handoff objects and a Microsoft
  `HandoffBuilder` workflow, A2A 1.0 coverage, context quarantine, single-use
  approvals, budget and parallelism races, eight labelled evaluation cases,
  Hub lab navigation, judgment checkpoints, and a Course 10 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Child authority never exceeds parent, task, or role | Attenuation and delegation-contract sections | task authority, profiles, immutable grant lineage and pair scopes | tool/resource/pair/vendor/spend/call/purpose/expiry/depth tests |
| Handoff routing is not authority | Four-transfer and handoff sections | sender/recipient/grant-bound envelope with typed context digest | tamper, excessive field, clearance and instruction-quarantine tests |
| A privileged specialist cannot become a confused deputy | Consequence-boundary section | requester grant must appear in executor lineage with tool authority | sibling research request is denied; eight-case evaluation |
| Human approval binds the final high-impact proposal | Proposal-bound approval section | digest-, lineage-, policy-, task- and grant-bound receipt | missing, mutated, unauthorized, consumed and replay cases |
| Shared risks have shared atomic controls | Budget/parallelism section | task ledger, per-grant calls and expiring worker leases under one lock | six-way spend race and four-way lease race stay within limits |
| Pause, termination and revocation stop the next effect | Lifecycle section | application state machine plus descendant revocation | paused/revoked/terminal late-worker tests |
| Framework examples are real but not policy | Technology and framework sections | OpenAI `Agent`/`as_tool`/`handoff`; Microsoft `HandoffBuilder` workflow | objects construct offline while all effects remain in the control plane |
| Evaluation names the exact population | Evaluation section | one allowed and seven forbidden cases | baseline 3/8 correct with five forbidden allows; governed 8/8 with zero |

## Course 11 claim-to-proof map

### Course 11 audit decisions

- **Retain:** defense-in-depth, OWASP agentic risks, trust and information-flow
  boundaries, injection, tool/identity security, SSRF, code isolation, memory,
  multi-agent security, anomaly response, incident response, and four diagrams.
- **Deepen:** authenticated current-policy authority, tenant/task-bound content,
  exact tool-resource pairs, integrity/confidentiality flows, resolve-to-connect
  egress tickets, proposal-bound single-use approval, atomic aggregate budgets,
  operator-owned containment, honest detector metrics, and trajectory outcomes.
- **Consolidate:** replace mutable notebook-only demonstrations with one typed,
  deterministic `lab.py` imported by the notebook and focused tests.
- **Repair:** remove runtime installs, mutable globals, regex-only enforcement,
  unscoped context, agent-callable kill switches, misleading allow audit events
  on budget denial, unsafe URL checks, and fabricated external effects.
- **Add:** real offline OpenAI Agents SDK input/output/function-tool guardrails
  and approval, an OpenAI Guardrails registry check, experimental Microsoft
  FIDES labels/configuration, 65 invariant tests, 12 labelled trajectories,
  Hub navigation/checkpoints, and a Course 11 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Detection cannot manufacture authority | Signal/decision/enforcement model | authenticated context, current `TaskGrant`, typed proposal | spoofed actor, stale policy, wrong tenant/task/tool/resource/vendor tests |
| Provenance and labels constrain flows | threat-model and IFC sections | tenant/task-bound `ContentEnvelope`, integrity/confidentiality checks | cross-tenant context, low-integrity purchase and confidential egress denied |
| Outbound paths are constrained | egress, DLP and sandbox sections | resolution-bound `EgressTicket`, output release gate, command manifest | alternate IP, private DNS, rebinding, secret, path and shell-composition tests |
| Approval and retries do not widen authority | approval/idempotency sections | exact expiring receipt and operation ledger | mutation, expiry, consumption, replay and changed-operation tests |
| Shared autonomy has atomic limits | budget section | locked call/spend reservation before simulated effect | six-worker race commits four CAD 1,200 orders and records two denials |
| Containment is independent of the agent | incident-response section | current, scoped `security_operator` methods | agent, cross-tenant and future-session operators cannot pause a run |
| Framework examples are real but bounded | tools and framework sections | real SDK/Guardrails/FIDES objects construct offline | tests inspect exact hooks while application policy owns every effect |
| Metrics name exact populations | evaluation section | 8 detector and 12 trajectory cases | baseline allows 8/9 dangerous cases; governed path allows 0/9 |

## Course 15 claim-to-proof map

### Course 15 audit decisions

- **Retain:** the management/decision/enforcement/evidence separation, registry,
  delegated-authority, policy-as-code, tool/MCP gateway, approval, outage,
  shadow-policy, governance-loop, build-vs-buy, and four-diagram foundations.
- **Deepen:** authenticated administrative operations, tenant/environment policy
  scope, signed delegation and policy integrity, optimistic lifecycle updates,
  exact decision and registry-version binding, atomic approval and execution
  consumption, verified outcomes, bounded last-known-good reads, shadow release
  evidence, replica activation, and threat/consistency models.
- **Consolidate:** replace 24 mutable notebook demonstrations with one tested
  deterministic `lab.py`, an eight-code-cell guided notebook, 70 focused
  invariant tests, and a top-to-bottom notebook execution test.
- **Repair:** remove runtime installs, random identifiers, mutable global
  execution lists, caller-owned identity fields, approval flags, unbound policy
  hashes, blind retries, prompt-only enforcement claims, and unqualified risk
  scores.
- **Add:** a 12-case prompt-only versus governed evaluation, authenticated
  registry facade, tool lifecycle transitions, exact policy activation receipts,
  tenant-bound local replicas, real offline OPA/OpenFGA SDK objects, Rego/Cedar/
  OpenFGA artifacts, real in-memory OpenTelemetry spans, versioned diagram
  specifications, current MCP/OAuth/SPIFFE/Envoy guidance, Hub checkpoints, and a
  Course 15 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Models propose but never grant authority | trust-boundary and principal sections | trusted context plus signed delegation produces the request | forged identity/grant, tenant, workload, purpose and environment bindings fail |
| Lifecycle changes are governed | management and registry sections | authenticated operator facade plus optimistic versions | wrong role/tenant, expired session, stale version and retired reactivation fail |
| Delegation attenuates | delegated-authority section | signed root/child grants narrow tool, operation, resource, amount and lifetime | every widening dimension and tampered signature fail |
| Decisions bind exact control state | decision and evidence sections | action, policy digest, registry versions, reasons and obligations travel together | schema/tool/policy mutation and inactive state deny |
| Approval cannot become reusable authority | approval/action-binding sections | exact decision/policy/registry receipt and atomic consumption | mutation, expiry, role, tampering, replay and concurrent use fail |
| Effects remain single and knowable | enforcement and consistency sections | idempotency, single-use gateway and reconciliation | denied actions make zero calls; changed-action reconciliation and duplicate execution fail |
| Outage behavior is risk-aware | availability and caching sections | fresh last-known-good read with explicit evidence | mutation, stale bundle, read-only and stopped modes fail closed |
| Policy rollout is governed | versioning and shadow sections | 12-case report, activation receipt and scoped replica | regression, stale/small/mismatched evidence and cross-tenant replica fail |
| Common technologies remain bounded | technology-selection section | real OPA/OpenFGA configs, policy artifacts and OTel span | no network, credentials, framework-owned authorization or raw sensitive telemetry |
| Evaluation names exact populations | practical/evaluation sections | 12 labelled allow/deny/escalate/constrain/outage cases | prompt-only baseline permits 8 forbidden outcomes; governed path permits 0 |

## Course 14 claim-to-proof map

### Course 14 audit decisions

- **Retain:** the outcome-and-trajectory framing, evaluation layers, oracle
  pyramid, golden/boundary/adversarial/regression datasets, offline-shadow-
  canary-production lifecycle, change triggers, risk-tier gates, slicing,
  judge calibration, production feedback loop, NIST lifecycle alignment and
  four diagrams.
- **Deepen:** case provenance and digests, evaluator ownership/versioning,
  deterministic consequence oracles, approval/effect/recovery evidence, exact
  metric populations, attempted-versus-blocked-versus-unsafe distinctions,
  valid-work blocks, Wilson uncertainty, same-case McNemar comparison, blind
  judge calibration and position swaps, evidence-bound gates, reviewed incident
  curation and canary rules.
- **Consolidate:** replace 28 disconnected mutable notebook demonstrations with
  one typed deterministic `lab.py`, an eight-code-cell guided notebook, 66
  focused invariant tests, and a top-to-bottom notebook execution test.
- **Repair:** remove runtime installs, random state, fabricated dataframe
  metrics, an unsafe normal-approximation interval, aggregate scores that mask
  critical failures, scalar-only release inputs, unauthenticated production
  case creation, drift-as-defect claims, and obsolete OpenAI Evals guidance.
- **Add:** a 16-case procurement suite, baseline/candidate target vectors, exact
  outcome/tool/policy/approval/effect/tenant evaluation, paired exact comparison,
  evidence-time and freshness checks, calibrated-judge review routing,
  change-suite selection, reviewed production-derived cases, drift/canary
  decisions, real in-memory OpenTelemetry and unstarted OpenAI trace artifacts,
  current Inspect AI/Promptfoo/LangSmith/Phoenix/Langfuse/DeepEval boundaries,
  versioned diagram specifications, accessible diagrams, Hub checkpoints and a
  Course 14 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Comparisons bind the same evidence | dataset/evaluator governance sections | dataset digest, complete target vector, evaluator version and report digest | split leakage, duplicate IDs, mismatched datasets/case populations and tampered reports fail |
| Outcomes and trajectories remain separate | five-layer and deterministic-evaluator sections | typed trace events and independent tool/policy/terminal/approval/effect/tenant checks | unknown outcome, approval mismatch and cross-tenant paths fail |
| Safety cannot hide in an average | metric and release-gate sections | forbidden-outcome and critical-violation hard gates | baseline fails despite five successful cases |
| Metrics name exact populations | metric-contract and uncertainty sections | exact numerators/denominators, risk slices, Wilson interval and cost per successful task | empty/invalid populations fail and small perfect samples retain uncertainty |
| Judges are governed controls | judge-calibration section | blind human labels, macro F1, kappa, false accepts and order consistency | missing, weak, non-blind, mixed-version or false-accept calibration blocks |
| Production feedback is authorized and minimized | production-derived case section | provenance-linked sanitized candidate plus current tenant-bound owner review | email/API-key content and expired, cross-tenant or unauthorized promotion fail |
| Drift is not a defect verdict | drift section | minimum-window rate assessment marked signal-only | small windows cannot alert |
| Evaluation constrains deployment | release and canary sections | requested/authorized stage on approve/constrain/block plus separate canary decision | 16 clean cases approve shadow, premature production is constrained to canary, and critical canary events roll back |
| Common tooling remains bounded | current-tool and interoperability sections | manifests plus real offline OTel and unstarted OpenAI trace artifacts | no credentials, network, raw prompts or framework-owned release authority |

## Course 13 claim-to-proof map

### Course 13 audit decisions

- **Retain:** trajectory-not-answer framing; identity, intent, context,
  authority, decision and outcome evidence; traces/metrics/logs; policy,
  approval, delegation, retrieval, memory, tool and effect coverage; privacy,
  sampling, integrity, access, incident/audit packages, and four diagrams.
- **Deepen:** authenticated producers, trusted application context, tenant and
  schema binding, minimization before export, keyed pseudonyms, causal
  completeness, exact-action approval/outcome links, access receipts, legal
  hold, tail retention, integrity assumptions and evidence release gates.
- **Consolidate:** replace 22 mutable notebook code cells with one deterministic
  `lab.py`, a guided eight-code-cell notebook, 64 focused invariant tests, and
  a top-to-bottom notebook execution test.
- **Repair:** remove runtime installs, global mutable event lists, raw direct
  identifiers/content, regex-only safety, unauthenticated reads, optimistic
  sampling, unsigned evidence packages and claims that traces/hashes alone
  prove authorization, completeness, outcome or non-repudiation.
- **Add:** real in-memory OpenTelemetry spans, real unstarted OpenAI Agents SDK
  objects, current OpenTelemetry/OpenInference/Phoenix/LangSmith/OpenAI tool
  boundaries, a Collector design artifact, accessible diagrams, Hub judgment
  checkpoints, corrected course paths and a Course 13 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Evidence originates at a trusted boundary | trust-model and metadata sections | authenticated tenant/service producer and application-owned context | expired, wrong-role, wrong-service and cross-tenant producers fail |
| Data is minimized before export | privacy and telemetry section | per-event allowlists, references, keyed pseudonyms and residual redaction | prompts/nested values fail; emails/secrets are removed |
| Trajectories are causally complete | trace/completeness sections | one root, continuous sequence, parent/time links and risk-tier event sets | missing parent/outcome, gap, duplicate, second-root and reversal tests |
| Decisions bind to consequences | approval/tool/outcome sections | canonical action digests and explicit approval/tool/outcome links | changed action and unverified/mislinked outcome block the gate |
| Integrity claims are bounded | integrity section | per-trace event chain, HMAC verification, chained custody receipts and authenticated minimized package | event, chain, package and key tampering fail verification |
| Evidence use is governed | access/retention sections | role/purpose/tenant reads, receipts, break-glass and legal hold | invalid role/purpose/tenant/reason/hold manager fail |
| Metrics and retention name populations | metrics/sampling sections | exact completeness denominators and deterministic tail decisions | empty/misaligned populations and invalid sample rate fail |
| Real tools remain bounded | current tools and practical sections | in-memory OTel spans, unstarted SDK traces and Collector artifact | no credentials, raw content, network or default exporter used |

## Course 12 claim-to-proof map

### Course 12 audit decisions

- **Retain:** system-not-model red-team framing, rules of engagement, threat
  hypotheses, broad agentic attack surface, manual/automated distinction,
  PyRIT and garak orientation, trajectory evidence, remediation, regression,
  CI cadence, exercises, and four existing diagrams.
- **Deepen:** target/version authorization, campaign budgets and emergency stop,
  artifact provenance and mutation lineage, consequence-based deterministic
  oracles, explicit indeterminate outcomes, honest metric denominators,
  legitimate controls, release gates, and finding ownership/lifecycle.
- **Consolidate:** replace 71 mutable notebook cells with one deterministic
  `lab.py` imported by a guided notebook, 45 focused invariant tests, and a
  top-to-bottom notebook execution test.
- **Repair:** remove runtime package installs, mutable globals, label-leaking
  toy evaluation, fake defense-stage mappings, attack-only ASR, direct status
  closure, stale framework guidance, and raw attack payloads in reports.
- **Add:** a 16-case procurement corpus, bounded Unicode mutations, vulnerable
  and hardened version comparison, digest-bound evidence, optimistic finding
  transitions, Promptfoo and current tool manifests, real offline OpenAI Agents
  SDK trace objects, Hub checkpoints, and a Course 12 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Campaigns stay authorized and contained | ROE, safety and environment sections | typed ROE, current operator and security-owner stop | production/external/cross-tenant/out-of-window/over-budget cases fail |
| Attack evidence is reproducible | dataset, mutation and evidence sections | artifact, trajectory, corpus and ROE digests plus target version | tamper, duplicate ID, changed corpus and wrong target version tests |
| Oracles inspect effects rather than claims | oracle and trajectory sections | typed proposals, decisions, effects, memory and stop events | canary, payment, memory, SSRF, command, approval and runaway assertions |
| Errors do not inflate safety | metrics and gate sections | explicit `INDETERMINATE` outcome and multi-condition release gate | target error and missing evidence block release/closure |
| Metrics name exact populations | ASR/control-bypass sections | 12 attacks and four legitimate controls | baseline ASR 12/12; hardened ASR 0/12 with 4/4 controls preserved |
| Findings close only after verified repair | triage/remediation/regression sections | deduplicated versioned registry and transition receipts | stale update, same-version, mismatched and failing regression tests |
| Common tooling is current and bounded | PyRIT, garak, Promptfoo, Foundry and OpenAI sections | current manifests, local Promptfoo config and real trace objects | optional scanners remain unexecuted and limitations are explicit |

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

## Course 7 claim-to-proof map

### Course 7 audit decisions

- **Retain:** the consequence-boundary thesis, MCP trust-chain model, risk
  tiers, governance contract, schema-versus-semantics distinction, poisoning,
  confused-deputy, credentials, SSRF, gateway, lifecycle, supply-chain, and
  enterprise checklist coverage.
- **Deepen:** the final 2026-07-28 protocol snapshot; OAuth issuer,
  resource/audience, metadata, scope, and transport semantics; official SDK
  selection; tool manifest attestation; output validation; atomic budgets;
  unknown effects; and the distinction between final specifications, stable
  extensions, roadmaps, and proposals.
- **Consolidate:** move contracts, registry, approval, budgets, gateway,
  effect adapter, network validation, fixtures, and evaluation into one
  deterministic `lab.py` imported by the notebook and tests.
- **Repair:** remove runtime installation, random and wall-clock values,
  caller-supplied trusted context, description-driven authorization, fabricated
  purchase success, mutable notebook-only limits, reusable approval flags, and
  optional network paths from the canonical lab.
- **Add:** official MCP SDK descriptors, manifest drift and revocation tests,
  closed input and output schemas, exact single-use approval, concurrent budget
  proof, tenant-safe idempotency, unknown-effect reconciliation, capability-
  protected effects, resolved-address SSRF defenses, a nine-case labelled
  comparison, judgment checkpoints, and a Course 7 CI target.

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| Discovery metadata is not authority | MCP trust-chain, description, and discovery sections | `ToolContract`, `ToolRegistry`, SDK `Tool`, manifest digest | Description drift, cached-manifest, revocation, and unregistered-tool tests |
| Model claims are not trusted facts | Thesis and parameter-governance sections | `ToolProposal` is separate from authenticated context and `TrustedFacts` | Claimed role/approval cannot override vendor, workload, tenant, freshness, or hard limits |
| Schema and semantics both constrain calls | Schema and parameter sections | Draft 2020-12 input/output validation plus vendor/task policy | Extra-field injection, bad currency, unapproved vendor, amount, and invalid-output tests |
| Approval grants one exact action | Approval section | digest-, context-, manifest-, policy-, role-, and time-bound receipt store | Expired, wrong-role, cross-tenant, altered, and replayed receipts fail |
| Retries and volume do not widen authority | Rate, idempotency, and failure sections | locked budget ledger and tenant/operation ledger | Twelve-worker race, mutated retry, and cross-tenant operation tests |
| Effects are protected and observable | Gateway, credential, error, and evidence sections | gateway capability, brokered credential simulation, effect receipt | Direct bypass, unknown-before/after-commit, and malformed output tests |
| URL tools enforce network intent | SSRF section | allowlist plus HTTPS/credential/port and resolved-address checks | Localhost, link-local, private, IPv6-local, mixed-answer, and redirect-hop exercises |
| Evaluation names its populations | Testing and notebook sections | nine labelled cases and `EvaluationSummary` | Exact forbidden-allowed and missed-escalation counts expose the schema-only baseline |
