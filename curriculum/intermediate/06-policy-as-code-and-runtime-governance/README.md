# Module 6 — Policy-as-Code & Runtime Governance

> **Course:** Enterprise AI Agent Governance: From Principles to Runtime Control
> **Audience:** AI engineers, security engineers, platform teams, cloud architects, governance and risk teams
> **Recommended duration:** 6 hours theory + 5 hours practical lab
> **Scenario:** Enterprise Procurement Agent
> **Source review date:** 21 September 2026

---

## Course thesis

An agent may propose an action, but it must not supply its own authority, policy facts, approval, or proof of execution. A trusted application resolves authoritative inputs, a versioned policy decision point evaluates every required domain, and a non-bypassable enforcement point performs and verifies the effect. Policy-as-Code is therefore a **control lifecycle**, not merely a policy-language file.

```text
model proposal
    ↓
authenticated context + authoritative facts
    ↓
versioned PDP decision (DENY > ESCALATE > ALLOW)
    ↓
non-bypassable PEP
    ↓
idempotent effect + verified receipt + minimized evidence
```

## Prerequisites

Before starting, you should be able to:

- distinguish a user, workload/agent, task, action, and resource;
- explain default deny and fine-grained authorization from Course 5;
- read basic Python and JSON;
- recognize that model output and retrieved text are untrusted inputs;
- run `uv` and `pytest` from the repository root.

No cloud account, policy-engine server, API key, or notebook package installation is required.

## Success criteria

You have completed the course when you can:

1. identify the PDP, PEP, control plane, data plane, authoritative resolvers, effect adapter, and evidence store in an architecture;
2. explain why syntax/schema checks, semantic tests, mutation tests, shadow comparison, canary release, and rollback answer different questions;
3. implement a composed decision in which hard denial dominates escalation and allow;
4. prove that untrusted model claims, missing facts, stale facts, engine outages, and direct effect calls cannot produce a state-changing effect;
5. define the numerator and denominator for false permits, forbidden-not-denied cases, false denials, missed escalations, and decision flips;
6. select an appropriate boundary and toolchain for OPA/Rego, Cedar, Verified Permissions, AgentCore Policy, or application code.

## Scope and non-goals

This course teaches engine-independent runtime-governance invariants and maps them to common tools. The local evaluator is an educational reference implementation, **not** a substitute for OPA, Cedar, Amazon Verified Permissions, or AgentCore Policy. The notebook does not claim to execute those external engines. It does not teach every language feature, cloud deployment topology, or legal interpretation of a governance obligation.

## Claim-to-proof map

| Claim | Executable proof |
|---|---|
| model claims are proposals, not facts | sanctioned-vendor test with positive model claims still denies |
| composition is deterministic | all four domains execute; hard `DENY` precedes `ESCALATE`, then `ALLOW` |
| policy releases are controlled | immutable versions, schema/static validation, shadow, deterministic canary, promotion gate, rollback |
| policy outages fail closed | unavailable control plane produces no effect |
| the effect path is non-bypassable | adapter rejects calls without the gateway capability |
| evidence is attributable and minimized | decision carries bundle version/revision/digest and fact versions, not raw subject/vendor values |
| the lab improves on a baseline | labelled 10-case corpus reports exact safety populations and errors |

## Learning objectives

By the end of this module, you should be able to:

1. Explain the transition from governance documents to **executable runtime controls**.
2. Distinguish **authorization policy, business policy, safety policy, risk policy, and approval policy**.
3. Design a runtime governance **Policy Enforcement Point (PEP)** and **Policy Decision Point (PDP)**.
4. Implement deterministic **ALLOW / DENY / ESCALATE** decisions outside LLM reasoning.
5. Treat policies as code: **version, review, validate, test, deploy, observe, and roll back**.
6. Use **Cedar** and **OPA/Rego** for runtime policy.
7. Compare current **OPA/Rego, Cedar, Amazon Verified Permissions, and AgentCore Policy/Dogwood** capabilities and boundaries.
8. Validate policies against schemas and test semantic behavior—not just syntax.
9. Implement **risk-based approval routing**.
10. Prevent **gateway bypass**, stale policy, fail-open behavior, and policy/context injection.
11. Design policy decision logs as **governance evidence**.
12. Build a practical continuous-governance loop.

> **Core principle:** Reasoning may be probabilistic. Runtime authority and control decisions should be deterministic.

---

# 1. From governance documents to executable controls

Traditional governance often looks like:

```text
Policy document
    ↓
Architecture review
    ↓
Deployment approval
```

Autonomous systems require another layer:

```text
Agent proposes action
    ↓
Runtime policy
    ↓
ALLOW / DENY / ESCALATE
    ↓
Tool executes—or does not
```

The key change is not replacing governance documents. It is translating selected rules into controls that can be enforced at the moment of consequence.

![Runtime governance loop](assets/01-runtime-governance-loop.svg)

---

# 2. What Policy-as-Code means

Policy-as-Code represents governance rules in machine-evaluable artifacts.

Examples:

```text
A procurement agent may create a PO up to $5,000
only for an approved vendor.
```

becomes:

```text
IF action == create_po
AND amount <= 5000
AND vendor.approved == true
THEN ALLOW
```

A higher-risk rule:

```text
IF amount > 5000
AND amount <= 25000
THEN ESCALATE(manager)
```

A prohibition:

```text
IF vendor.sanctioned == true
THEN DENY
```

The benefit is **consistent, testable enforcement**.

---

# 3. Not every governance rule belongs in code

Separate:

### Principles

Broad expectations such as fairness or accountability.

### Standards

Enterprise requirements and control objectives.

### Policies

Rules that define permitted/prohibited behavior.

### Executable controls

Rules precise enough to evaluate at runtime.

### Evidence

Logs and measurements proving the control operated.

Do not force ambiguous governance principles directly into brittle Boolean rules.

---

# 4. Layer runtime controls

![Layered runtime policy](assets/03-layered-runtime-policy.svg)

A consequential action may pass through:

1. **Identity** — who is acting?
2. **Authorization** — may this principal perform the action?
3. **Business policy** — does it satisfy enterprise rules?
4. **Risk policy** — is approval/escalation required?
5. **Safety/data policy** — does it violate content, privacy, or data controls?

Authorization is necessary, but not the whole governance decision.

---

# 5. Runtime governance architecture

![Runtime enforcement architecture](assets/04-runtime-enforcement-architecture.svg)

The enterprise pattern is:

```text
Agent
  ↓
Governance Gateway / PEP
  ↓
Policy Engine / PDP
  ↓
ALLOW / DENY / ESCALATE
  ↓
Tool / API
```

A critical design property is **non-bypassability**.

AWS's current AgentCore security guidance makes the same architectural point: a gateway can apply policy, guardrails, interceptors, and observability outside the agent, but those controls only protect the system if callers cannot bypass the gateway and invoke the runtime directly.

---

# 6. Policy Decision Point vs Policy Enforcement Point

## PDP

Evaluates policy.

Examples:

- Cedar evaluator
- OPA
- Amazon Verified Permissions
- AgentCore Policy

## PEP

Intercepts and enforces.

Examples:

- gateway
- MCP proxy
- API middleware
- tool wrapper
- service mesh boundary

The PEP should not ask the LLM whether its own action is permitted.

---

# 7. Cedar

Cedar is an authorization policy language built around:

```text
Principal
Action
Resource
Context
```

Current Cedar documentation emphasizes decoupling authorization logic from application business logic and validating policies against schemas before use.

Example:

```cedar
permit (
  principal is Agent,
  action == Action::"CreatePurchaseOrder",
  resource
)
when {
  context.amount <= 5000 &&
  context.vendorApproved == true
};

forbid (
  principal,
  action == Action::"CreatePurchaseOrder",
  resource
)
when {
  context.sanctionedVendor == true
};
```

Primary references:

- https://docs.cedarpolicy.com/
- https://docs.cedarpolicy.com/auth/authorization.html
- https://docs.cedarpolicy.com/policies/validation.html

---

# 8. Cedar decision semantics

Cedar is default deny:

```text
no applicable permit → DENY
```

and applicable `forbid` policies override permits.

This is useful for hard enterprise boundaries:

```text
permit ordinary procurement
forbid sanctioned vendors
```

A broad permit should not defeat a critical prohibition.

---

# 9. Schema validation

Policy syntax being valid does not mean policy behavior is correct.

Cedar schemas describe expected:

- entity types,
- actions,
- principal/resource types,
- context structure.

Current Cedar guidance recommends validating policies before they are used for authorization and re-reviewing policies when schemas change.

Treat schema changes like API contract changes.

---

# 10. OPA / Rego

Open Policy Agent is a general policy engine.

Pattern:

```text
Application / gateway
       ↓
structured input
       ↓
OPA
       ↓
decision
```

Rego can express runtime rules across:

- agent tools,
- workflow state,
- deployment configuration,
- data access,
- security constraints.

Example:

```rego
package agent.governance

default allow := false

allow if {
  input.action == "create_po"
  input.vendor.approved
  input.amount <= 5000
}
```

Primary references:

- https://www.openpolicyagent.org/docs
- https://www.openpolicyagent.org/docs/policy-language
- https://www.openpolicyagent.org/docs/policy-testing

OPA can evaluate through REST, its Go APIs/SDK, WebAssembly, or compiled intermediate representation. Its management APIs support bundle distribution, status, discovery, decision logs, health, and Prometheus metrics. OPA documentation is explicit that OPA supplies the policy engine and management protocols, not a complete policy-control-plane service; teams must build or adopt the surrounding release service.

For production Rego development, combine:

```text
opa fmt / opa check --strict       format and compile
opa test --coverage               semantic tests and coverage
Regal                             linting and language-server feedback
signed OPA bundles                versioned distribution and verification
status + decision logs            rollout health and runtime evidence
Conftest                          Rego assertions over structured configuration
```

Conftest is most useful when the governed object is configuration—Terraform plans, Kubernetes manifests, YAML, or JSON. It is not by itself the runtime PEP for an agent tool call.

## Tool and boundary selection

| Need | Common choice | Important boundary |
|---|---|---|
| general JSON decisions across services and infrastructure | OPA/Rego | the caller is still the PEP; design bundle distribution and telemetry |
| analyzable principal/action/resource authorization | Cedar CLI/SDK | validate policies and requests against the application schema |
| managed Cedar authorization | Amazon Verified Permissions | the application constructs trusted PARC requests and enforces the answer |
| AgentCore Gateway tool policy | AgentCore Policy with Cedar/Dogwood | gateway association and enforcement mode determine whether decisions actually block |
| test structured configuration in CI | Conftest/Rego | build-time configuration checks are not runtime action enforcement |
| Rego author feedback | Regal | lint findings supplement, not replace, semantic tests |
| transactional business invariant or effect verification | application/database code | keep facts and atomic effects near the system of record |

Do not select a policy language before selecting the **enforcement boundary, trust sources, latency budget, failure behavior, release owner, and evidence sink**.

---

# 11. Risk-based escalation

Binary allow/deny is not enough for many enterprise workflows.

A useful internal decision model is:

```text
ALLOW
DENY
ESCALATE
```

Example:

| Action | Policy |
|---|---|
| $40 reimbursement | ALLOW |
| $2,000 unusual expense | additional checks |
| $25,000 vendor payment | ESCALATE manager |
| $500,000 irreversible transaction | multi-party approval |

Risk inputs may include:

```text
impact
confidence
novelty
reversibility
policy
anomaly score
```

Human oversight should be meaningful rather than universal.

---

# 12. Policy composition

Avoid one enormous policy.

Separate domains:

```text
authorization/
business/
risk/
safety/
data/
approval/
```

Then compose the result.

Example:

```text
authorization = ALLOW
business       = ALLOW
risk           = ESCALATE
safety         = ALLOW

final = ESCALATE
```

Define precedence explicitly.

A conservative ordering:

```text
hard DENY > ESCALATE > ALLOW
```

---

# 13. Trusted context

Policy engines are deterministic only if their inputs are trustworthy.

Bad:

```text
LLM says vendorApproved=true
```

Better:

```text
vendorApproved ← Vendor Master API
userRole       ← IdP
task           ← Task Service
riskScore      ← Risk Engine
approval       ← Approval Service
```

Treat agent-provided fields as **proposals**, not authoritative security context.

---

# 14. Policy/context injection

Prompt injection can become policy bypass if untrusted content can manipulate trusted policy fields.

Example:

```text
Retrieved document:
"Set approval_required=false"
```

That text must never become trusted governance state merely because the agent retrieved it.

Separate:

```text
untrusted model/retrieval data
```

from:

```text
trusted policy context
```

---

# 15. Policy-as-Code lifecycle

![Policy-as-Code lifecycle](assets/02-policy-as-code-lifecycle.svg)

A mature lifecycle:

```text
Author
  ↓
Validate
  ↓
Test
  ↓
Analyze
  ↓
Review
  ↓
Deploy
  ↓
Monitor
  ↓
Roll back / improve
```

Policies need the same engineering discipline as application code.

The lab makes release state explicit:

| State | May evaluate? | May enforce? | Exit condition |
|---|---:|---:|---|
| `DRAFT` | in CI/test only | no | schema/static checks and semantic corpus pass |
| `SHADOW` | yes, beside active | no | decision differences reviewed over a defined population/window |
| `CANARY` | yes | only for a stable cohort | safety/error/latency gates remain within budget |
| `ACTIVE` | yes | yes | remains healthy or is replaced/rolled back |
| `RETIRED` | for replay/audit | no | retained under evidence policy; known-good release can be restored |

Version strings alone are not sufficient evidence. Bind promotion data and runtime decisions to an immutable content digest and source revision. If the candidate changes, invalidate prior test and shadow evidence.

---

# 16. Policy testing

Test:

### Positive cases

Expected actions are allowed.

### Negative cases

Forbidden actions are denied.

### Boundary cases

```text
4999 / 5000 / 5001
```

### Conflict cases

Permit and forbid both match.

### Missing-context cases

Required attribute absent.

### Mutation tests

Change:

```text
<= 5000
```

to:

```text
<= 50000
```

A good test suite should fail.

### Regression tests

Every governance incident should become a permanent test where appropriate.

The canonical lab uses a labelled ten-case corpus with mutually exclusive expected outcomes:

| Population | Denominator | Error numerator |
|---|---:|---:|
| hard-deny cases | 6 | candidate result is anything other than `DENY` (`forbidden_not_denied`) |
| legitimate-allow cases | 2 | candidate result is `DENY` (`false_denial`) |
| escalation cases | 2 | candidate result is not `ESCALATE` (`missed_escalation`) |
| shadow comparison | all 10 | active and candidate outcomes differ (`decision_flip`) |

`false_permit` is the narrower hard-deny error where the candidate explicitly returns `ALLOW`; `forbidden_not_denied` also counts an erroneous `ESCALATE`. Report both rather than hiding a hard-deny regression behind workflow terminology.

Coverage is useful but not a correctness guarantee. A line can execute without asserting the right behavior; optimized evaluators can also skip paths. Pair coverage with labelled semantic cases, boundaries, conflicts, missing context, property checks, and deliberately introduced mutations.

---

# 17. Static analysis and automated reasoning

Modern policy systems increasingly analyze policies before deployment.

AgentCore Policy currently documents:

- Cedar schema generation from gateway tool definitions,
- policy validation,
- automated analysis,
- detection of policies that are overly permissive, overly restrictive, or unsatisfiable,
- natural-language policy authoring that generates candidate Cedar policies and validates/analyzes them.

This is an important state-of-the-art direction:

> AI can help author policy, but deterministic validation and reasoning should constrain the generated result.

---

# 18. Natural-language policy generation

Example requirement:

> Procurement agents may create purchase orders under $5,000 for approved vendors.

An LLM can generate candidate Cedar/Rego.

But production flow should be:

```text
Natural-language requirement
       ↓
Candidate policy
       ↓
Schema validation
       ↓
Static analysis
       ↓
Behavioral tests
       ↓
Human review
       ↓
Deployment
```

Do not deploy generated policy because it “looks right.”

---

# 19. Deployment strategies

Avoid changing critical policy globally without staged rollout.

Useful patterns:

### Shadow mode

Evaluate new policy but do not enforce.

Compare:

```text
current decision
candidate decision
```

### Canary

Apply to limited agents/tools/users.

### Progressive rollout

Increase coverage gradually.

### Version pinning

Associate workloads with known policy versions.

### Fast rollback

Restore previous known-good policy.

A release gate should bind to:

- active and candidate bundle digests;
- evaluation-corpus digest and sample count;
- safety error counts and decision-flip rate;
- evaluation errors/incomplete results;
- latency and resource budgets;
- required observation window and approver;
- rollback target and owner.

Shadow mode must never change the returned enforcement decision. Canary assignment must be stable for the chosen cohort key. Rollback must atomically restore a known-good bundle rather than reconstructing policy by hand.

---

# 20. Decision drift

A policy can remain unchanged while behavior changes because:

- agent tool arguments change,
- data changes,
- risk scores shift,
- schemas evolve,
- identity claims change,
- new tools appear.

Monitor distributions such as:

```text
deny rate
escalation rate
policy match rate
tool/action frequency
amount distribution
missing context
unknown actions
```

Governance drift is broader than model drift.

---

# 21. Runtime policy evidence

Every consequential decision should record:

```text
request ID
agent identity
delegating user
task
tool/action
resource
trusted context
policy version
matched policies
decision
reason
approval
execution result
timestamp
```

Prefer identifiers, digests, reason codes, and evidence versions over copying raw prompts, personal data, credentials, or entire system-of-record responses. An `executed: true` field is not effect evidence. Record an idempotency key and a receipt returned by the target system; represent timeouts as **unknown outcome** until reconciliation proves what happened.

For a decision metric, state the population. “Deny rate” is uninterpretable without the agent/tool/tenant, policy version, time window, and whether evaluation was active, shadow, canary, incomplete, or failed.

This evidence supports:

- audit,
- incident reconstruction,
- policy debugging,
- compliance,
- continuous improvement.

---

# 22. Failure modes

## Fail open

```text
PDP unavailable → execute
```

Dangerous for state changes.

## Gateway bypass

Agent reaches tool directly.

## Stale cached decisions

Revoked authority remains effective.

## Policy shadowing

Broad permit unintentionally defeats intended restriction.

## Context poisoning

Untrusted model output becomes trusted policy input.

## Policy/schema mismatch

Policy remains deployed after action/schema changes.

## Approval as superuser

Human approval bypasses hard enterprise prohibition.

---

# 23. State of the art and open problems

## Established practice

- default deny and explicit forbid precedence;
- schema/type validation before policy activation;
- semantic test corpora with positive, negative, boundary, missing-input, and conflict cases;
- immutable/versioned policy artifacts, staged rollout, telemetry, and rollback;
- policy evaluation outside the model and enforcement at a non-bypassable boundary;
- decision evidence tied to the exact policy and resolved input.

## Emerging practice

- automated reasoning for overly broad, ineffective, or unsatisfiable policies;
- policy-level shadow modes and decision-flip metrics;
- natural-language-to-policy authoring with generated code treated as an untrusted candidate;
- session-history/temporal policies for sequencing, frequency, and cumulative-value constraints;
- guardrail signals used as typed policy inputs rather than free-form model judgments.

## Research and engineering frontier

- proving equivalence or safe refinement across policy versions;
- synthesizing complete policies from prose without silently changing intent;
- generating adversarial and counterexample-driven semantic tests;
- composing authorization, safety, risk, temporal, and business policy without ambiguous precedence;
- governing session history across multi-hop, cross-account, and third-party components;
- privacy-preserving decision evidence and long-term reproducibility as external facts change;
- safe degradation when policy, identity, approval, or risk services are partially unavailable.

No current natural-language authoring workflow removes the need for schema validation, semantic tests, release review, and monitored enforcement.

---

# 24. AgentCore Policy as a current implementation pattern

Amazon Bedrock AgentCore Policy currently provides a concrete runtime-governance architecture:

```text
Agent
  ↓
AgentCore Gateway
  ↓
Policy Engine
  ↓
Cedar evaluation
  ↓
Tool
```

Current documented capabilities include:

- interception of gateway tool requests,
- deterministic policy enforcement outside agent code,
- default deny,
- forbid-wins semantics,
- Cedar policies,
- identity/tool-input conditions,
- schema validation,
- automated policy analysis,
- natural-language authoring,
- policy decision logging and metrics through CloudWatch,
- engine-level `LOG_ONLY` versus `ENFORCE`,
- per-policy `LOG_ONLY` versus `ACTIVE` for side-by-side shadow evaluation,
- Dogwood temporal policies that are compatible with Cedar and can depend on earlier events in a policy session.

Current AgentCore documentation distinguishes two similarly named controls. Engine-level `LOG_ONLY` means no policy can block a gateway action. Policy-level `LOG_ONLY` evaluates a single candidate beside active policies but excludes it from the enforced answer. Restrict `UpdateGateway`: a principal able to change the engine to `LOG_ONLY` or remove its policy association can disable enforcement.

Dogwood temporal rules currently support patterns such as “approval occurred earlier,” bounded counts, and bounded sums within a session. The caller supplies the session ID; history is scoped to that session and authenticated principal. Updating temporal policy invalidates active temporal sessions rather than evaluating old history under new rules. Session-local rate limits are not global limits: a caller can start a new session, so account-wide budgets still require authoritative application state.

Primary sources:

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-test-a-policy.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-temporal.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-security-best-practices.html

---

# 25. Practical lab and notebook

Canonical files:

- `lab.py` — typed deterministic implementation;
- `06_policy_as_code_and_runtime_governance.ipynb` — guided experiments importing `lab.py`;
- `tests/test_module06_runtime_policy.py` — focused negative, lifecycle, and evidence tests.

Run from the repository root:

```bash
make course-06
```

or:

```bash
uv run python scripts/execute-notebooks.py \
  curriculum/intermediate/06-policy-as-code-and-runtime-governance/06_policy_as_code_and_runtime_governance.ipynb
uv run pytest -q tests/test_module06_runtime_policy.py
```

The lab implements:

- canonical governance request,
- layered authorization/business/risk/safety policies,
- ALLOW/DENY/ESCALATE composition,
- deterministic PEP,
- trusted vs untrusted context,
- Cedar policy examples,
- Rego policy,
- exact OPA JSON-boundary and illustrative Rego/Cedar artifacts,
- policy versioning,
- policy test matrix,
- mutation testing,
- shadow deployment,
- decision-diff analysis,
- policy rollout,
- fail-closed behavior,
- gateway-bypass test,
- decision evidence and governance metrics.

The notebook does **not** install packages at runtime, contact a live OPA server, or require cloud credentials. A production-upgrade exercise asks learners to substitute a real engine adapter while keeping the same invariants and labelled corpus.

---

# 26. Best practices

- Put enforcement outside model reasoning.
- Force consequential traffic through the PEP.
- Default deny.
- Separate policy domains.
- Use authoritative context.
- Validate policies against schemas.
- Test semantic behavior.
- Version every policy deployment.
- Use shadow/canary rollout.
- Monitor decision drift.
- Fail closed for high-impact actions.
- Preserve decision evidence.
- Make rollback fast.
- Convert incidents into regression tests.
- Treat AI-generated policy as candidate code requiring verification.
- Bind release evidence to bundle and corpus digests.
- Distinguish shadow output from the enforced result.
- Use idempotency keys and target-system receipts for effects.
- Minimize policy logs and protect the evidence pipeline.
- Keep global budgets and transactional invariants in authoritative systems of record.

---

# 27. Primary references

1. Cedar Policy Language
   https://docs.cedarpolicy.com/

2. Cedar Authorization
   https://docs.cedarpolicy.com/auth/authorization.html

3. Cedar Policy Validation
   https://docs.cedarpolicy.com/policies/validation.html

4. Open Policy Agent
   https://www.openpolicyagent.org/docs

5. Rego
   https://www.openpolicyagent.org/docs/policy-language

6. OPA Policy Testing
   https://www.openpolicyagent.org/docs/policy-testing

7. OPA Integration and Management Architecture
   https://www.openpolicyagent.org/docs/integration
   https://www.openpolicyagent.org/docs/management-introduction

8. OPA Policy Bundles and Signing
   https://www.openpolicyagent.org/docs/management-bundles

9. OPA Decision Logs
   https://www.openpolicyagent.org/docs/management-decision-logs

10. OPA Status Service
   https://www.openpolicyagent.org/docs/management-status

11. Regal documentation
    https://www.openpolicyagent.org/projects/regal

12. Conftest documentation
    https://www.conftest.dev/

13. Amazon Bedrock AgentCore Policy
   https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html

14. AgentCore Policy Core Concepts and Validation Analysis
   https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html
   https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-validation-overview.html

15. AgentCore Policy Generation Validation
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-generation-validation.html

16. AgentCore Enforcement and Shadow Modes
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-enforcement-modes.html
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-test-a-policy.html

17. AgentCore Temporal Policies and Sessions
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-temporal.html
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-session-based-temporal.html

18. AgentCore Runtime Security Best Practices
   https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-security-best-practices.html

19. Amazon Verified Permissions Concepts and Policy Stores
    https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/what-is-avp.html
    https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/policy-stores.html

## Tool-version snapshot used for this review

Versions are a reproducibility snapshot, not evergreen recommendations:

- OPA `v1.20.2`, released 3 September 2026;
- Regal `v0.42.0`, released 16 July 2026;
- Conftest `v0.70.1`, released 19 September 2026;
- Cedar CLI `v4.13.0`, released 15 September 2026;
- local Pydantic `2.13.4`.

Release records: https://github.com/open-policy-agent/opa/releases,
https://github.com/open-policy-agent/regal/releases,
https://github.com/open-policy-agent/conftest/releases, and
https://github.com/cedar-policy/cedar/releases.

Recheck upstream release notes and compatibility before adopting these versions
in production.

---

# 28. Next module

## Module 7 — Tool & Action Governance

Next:

```text
Agent
 ↓
Tool contract
 ↓
Parameter constraints
 ↓
Authorization + policy
 ↓
Approval
 ↓
Execution
 ↓
Compensation / rollback
 ↓
Evidence
```

The focus shifts from the policy engine itself to governing the **consequence boundary**: tools, APIs, MCP servers, side effects, and irreversible actions.
