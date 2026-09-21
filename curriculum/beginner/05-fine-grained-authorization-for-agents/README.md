# Module 5 — Fine-Grained Authorization for Agents

> **Course:** Enterprise AI Agent Governance: From Principles to Runtime Control
>
> **Audience:** AI/agent engineers, IAM and security engineers, cloud architects, platform engineers, and governance architects
>
> **Recommended duration:** 6 hours theory + 4–5 hours practical lab
>
> **Scenario:** Enterprise Procurement Agent

---

## Learning objectives

By the end of this module, you should be able to:

1. explain why authentication, consent, OAuth scopes, roles, and model instructions are not request-level authorization;
2. compare RBAC, ABAC, ReBAC, contextual, and task-based authorization;
3. design separate Policy Decision Points (PDPs) and Policy Enforcement Points (PEPs);
4. implement default deny and explicit `ALLOW`, `DENY`, and `ESCALATE` outcomes;
5. require both user/resource authority and task/agent authority;
6. obtain tenant, identity, relationships, vendor status, risk, and lifecycle state from authoritative sources;
7. distinguish hard prohibitions from approval-eligible constraints;
8. map agent authorization to OpenFGA, Cedar, OPA/Rego, Amazon Verified Permissions, and Amazon Bedrock AgentCore Policy;
9. close time-of-check/time-of-use, cache, retry, concurrency, and policy-outage gaps;
10. preserve policy, input, source-version, decision, and effect evidence without logging secrets;
11. test positive, negative, boundary, mutation, stale-state, outage, and concurrency cases; and
12. assess emerging policy-synthesis and agent-authorization research without presenting preprints as standards.

> **Core principle:** The model proposes an action. Trusted application code resolves authority, decides, enforces, executes, verifies, and records it.

## Course thesis

A production agent must not inherit a user's broad capability. Learners should
be able to combine authenticated identity, user/resource relationships,
task/agent authority, current business attributes, explicit policy, and
effect-bound enforcement into a decision that is narrow, observable,
short-lived, and safe under retries and concurrency.

## Prerequisites

- Modules 1–4, especially trusted human/agent/workload identity and delegated authority;
- Python data modeling and unit-test fundamentals;
- basic OAuth, API gateway, and least-privilege concepts; and
- familiarity with relationships such as user → department and task → resource.

No cloud account, API key, OpenFGA server, OPA process, or Cedar runtime is
required for the canonical path.

## Success criteria

You should be able to:

1. identify which question belongs to RBAC, ABAC, ReBAC, task authorization, approval, or effect execution;
2. prove separately that the user may access a resource and that the task/agent may perform the action;
3. distinguish hard denial from approval-eligible escalation;
4. bind approval, risk, decisions, retries, and evidence to the exact request;
5. reauthorize immediately before an effect and atomically consume call or approval budgets;
6. select and compose OpenFGA, Cedar/Verified Permissions, and OPA without duplicating sources of truth; and
7. report forbidden access, false denials, missed escalation, and outage behavior with explicit populations.

## Scope and trust boundary

The lab is a deterministic teaching system. It uses real Pydantic contracts and
real OpenFGA Python SDK request objects, but its local relationship/attribute
repository, Cedar text, Rego text, and procurement adapter are not live
services. The model may propose action arguments. Only trusted application code
may supply identity, tenant, role, relationships, grant state, vendor status,
risk evidence, approval validity, policy version, call counts, and execution
outcomes.

## Claim-to-proof map

| Promise | Prose | Executable proof | Negative/evaluation proof |
|---|---|---|---|
| A role or OAuth scope is insufficient | Sections 1–3 | `unsafe_role_only_authorize` baseline | Baseline permits all seven forbidden evaluation cases |
| User and task/agent authority are independent | Sections 6–8 | repository plus OpenFGA dual checks | Wrong actor, user/resource, task/resource, and cross-tenant tests |
| Context comes from authoritative state | Section 7 | versioned resource, vendor, risk, task, and identity records | Missing, stale, mismatched, unapproved, sanctioned, and high-risk tests |
| Approval is narrow | Section 14 | request-bound, expiring, single-use `ApprovalReceipt` | Mutated, expired, wrong-role, reused, and hard-deny tests |
| Authorization and execution remain separate | Sections 4 and 16 | PDP decision, PEP, and observable adapter | Deny/escalate never invoke; unknown outcomes are not called success |
| Retries and call limits are safe | Sections 15–16 | operation ledger and atomic grant consumption | Mutation collision, idempotent retry, and eight-worker race |
| Tool choices preserve the invariant | Sections 8–12 | OpenFGA SDK objects plus Cedar/Rego artifacts | Request-shape and policy-artifact tests; no live-engine claim |
| Evaluation exposes safety errors | Section 18 | ten labelled cases and baseline comparison | forbidden-allowed, false-denial, and missed-escalation denominators |

---

# 1. Why coarse permissions fail for agents

A credential might contain `purchase.write`, while the user's actual intent is:

> Create one purchase order for approved laptops, from vendor ACME, for the
> Data & AI department, below CAD 5,000, during Task 123.

The credential describes a potential API capability. It does not prove the
exact user, task, agent, resource, vendor, amount, risk, lifecycle state, or
approval. An agent that receives broad capability can accidentally or
adversarially exercise far more authority than the task requires.

Current OpenFGA guidance models this as zero standing task authority: agents or
tasks receive narrow grants, optionally bounded by session, agent, expiry, or
call count. These constraints supplement—not replace—the underlying user's
resource authority.

---

# 2. Authorization models

![Authorization models](assets/01-rbac-abac-rebac-contextual.svg)

| Model | Main question | Procurement example | Limitation alone |
|---|---|---|---|
| RBAC | What can this organizational role generally do? | Procurement managers may create POs | A role is usually too broad for one task/resource |
| ABAC | Do principal/resource/request attributes satisfy a rule? | amount ≤ CAD 5,000 and country is CA | Attribute provenance and freshness remain application responsibilities |
| ReBAC | What relationship links this principal and resource? | user is buyer for department; task is granted department access | Dynamic amount/risk logic can become awkward |
| Contextual | What is true for this request now? | current risk, vendor status, task state, time | Context must be trusted and consistently supplied |
| Task-based | What narrow authority exists for this task/session/agent? | Task 123 may call `purchase_order:create` twice | Must still intersect with user authority and business policy |

Most enterprise systems compose these models. Do not force every concern into
one role, relationship graph, or policy language.

---

# 3. Authentication, consent, scope, authorization, approval, and execution

- **Authentication:** who are the human, logical agent, and workload?
- **Consent:** what may the application request from a user or provider?
- **OAuth scope:** what class of API capability can a token potentially invoke?
- **Authorization:** may this principal perform this action on this resource now?
- **Approval:** did an authorized reviewer accept this exact proposal under a defined policy?
- **Execution:** did the target system apply the authorized effect, once, with the intended arguments?

None implies all the others. A valid JWT can still be unauthorized. A human
approval cannot create cross-tenant authority. An `ALLOW` decision is not an
effect receipt.

---

# 4. PDP and PEP architecture

![PDP and PEP architecture](assets/02-pdp-pep-authorization.svg)

The **PDP** evaluates normalized policy input and returns an observable decision.
The **PEP** intercepts the action, authenticates its PDP channel, supplies trusted
context, enforces the decision, atomically consumes bounded authority, invokes
the effect adapter, and persists the result.

```text
model proposes typed action
        ↓
PEP resolves authenticated identity and operation ID
        ↓
authoritative relationship + attribute lookup
        ↓
PDP: ALLOW / DENY / ESCALATE + reasons + versions + expiry
        ↓
PEP consumes one-use/quota state
        ↓
idempotent effect adapter
        ↓
verified effect / denied / escalation / unknown outcome
```

A tool description, system prompt, model guardrail, or schema validator is not a
PEP. Authorization must happen before the effect.

---

# 5. Default deny and decision semantics

No matching permit means `DENY`. Treat these outcomes distinctly:

- `ALLOW`: every hard constraint passes; the PEP may attempt the exact effect.
- `DENY`: a hard boundary fails; the operation is terminal unless inputs or policy legitimately change under a new operation.
- `ESCALATE`: a policy-defined soft requirement needs trusted review; no effect runs yet.

Policy unavailability must not silently become allow. A state-changing action
should normally fail closed. A read-only fallback is acceptable only when its
data scope, staleness budget, and failure policy are explicit and tested.

---

# 6. Dual authorization

![Dual authorization](assets/03-dual-authorization-context.svg)

For delegated work, require an intersection:

```text
user can access resource
AND
task may perform action on resource
AND
calling agent is bound to task
AND
current business constraints pass
```

The user check prevents a task grant from manufacturing access the user never
had. The task check prevents the agent from exercising the user's entire access
footprint. The actor binding prevents another agent from borrowing a valid task.

---

# 7. Authoritative input and provenance

| Input | Typical source | Evidence to retain |
|---|---|---|
| human, actor, workload, tenant | IdP, workload identity, agent registry | IDs, authentication time, expiry, version |
| user/resource relationship | application DB or relationship engine | model ID, tuple/source version, consistency token if used |
| task grant and lifecycle | task/delegation service | grant version, state, limits, expiry |
| resource ownership/state | system of record | resource and tenant version |
| vendor approval/sanctions/country | vendor master/compliance service | record version and observation time |
| risk | trusted risk service | exact proposal digest, score, model/rule version, expiry |
| approval | workflow/approval service | request digest, approver authority, policy version, state |
| policy | policy control plane | policy/schema/bundle/model version and deployment epoch |

Model output, prompt text, retrieved content, tool descriptions, and client
booleans such as `vendor_approved=true` are untrusted proposals. Resolve them
from trusted state or deny.

---

# 8. OpenFGA for relationships and task authority

OpenFGA is a strong fit for first-class users/agents/tasks, resource hierarchy,
delegation, reverse queries, and task/session/agent-scoped access. Current task
guidance describes expiration and call-count conditions, actor binding,
narrower sub-agent tasks, and tuple cleanup.

The lab constructs real `ClientCheckRequest` and `ClientTuple` objects for two
separate checks:

```text
user:user-123 --user_can_create--> department:data-ai
task:TASK-PO-123 --task_can_create--> department:data-ai
                                  AND calling agent is bound to task
```

Illustrative model:

```text
type user
type task
type agent
  relations
    define task: [task]
type department
  relations
    define user_creator: [user]
    define task_creator: [task]
    define calling_agent: [agent]
    define user_can_create: user_creator
    define task_can_create: task_creator and task from calling_agent
```

For production, pin a model ID, define consistency requirements, protect tuple
writes as consequential operations, clean up task tuples, test list/check
semantics, and decide which runtime facts may safely be contextual tuples.
Contextual tuples are request-local; they are not automatically trustworthy.

---

# 9. Cedar and managed Cedar services

Cedar evaluates `principal`, `action`, `resource`, context, entities, policies,
and schema. It supports `permit` and `forbid`; an applicable forbid wins over
permits. Schemas and validation catch classes of authoring error, but do not
prove that organizational intent was translated correctly.

Use Cedar for application authorization when principal/action/resource/context
semantics and analysis are valuable. Amazon Verified Permissions provides
managed Cedar policy stores and authorization APIs. Amazon Bedrock AgentCore
Policy applies Cedar-compatible policy to Gateway tool invocations and exposes
authorization/listing operations. Validate the exact service schema, identity
mapping, tool identifier, deployment mode, and logging behavior you use.

---

# 10. OPA and Rego

OPA is a general-purpose policy decision engine over structured input. It fits
application, infrastructure, gateway, and cross-cutting policy, with bundles,
discovery, status, decision logs, and multiple deployment patterns.

Rego can express a default-deny structured decision:

```rego
package agentauthz
import rego.v1

default decision := {"outcome": "deny", "reasons": ["default_deny"]}
```

Production concerns include bundle signing and rollout, API authentication,
decision-path contracts, partial evaluation/Wasm trade-offs, availability,
latency, and masking sensitive input fields in decision logs. The canonical lab
does not call a live OPA server; its Rego artifact is an integration blueprint.

---

# 11. Tool selection and composition

![Authorization tool landscape](assets/04-authorization-tool-landscape.svg)

| Need | Strong fit | Watch for |
|---|---|---|
| graph relationships, hierarchy, list authorized objects | OpenFGA | model/tuple lifecycle, consistency, runtime attributes |
| principal/action/resource/context policy and analysis | Cedar / Verified Permissions | entity completeness, schema evolution, service-specific mapping |
| arbitrary structured policy across domains | OPA/Rego | broad input contracts, bundle rollout, decision-log privacy |
| managed policy at AgentCore Gateway | AgentCore Policy | supported identity/tool schema, Gateway coupling, service maturity |
| simple stable rule in one service | typed application code | duplication, governance, and future complexity |

Composition may be appropriate—for example OpenFGA for relationships and Cedar
or Rego for dynamic business constraints—but define one owner for final
composition, timeout/deny behavior, version evidence, and disagreement. Two PDPs
do not automatically create stronger security.

The reproducible environment was reviewed on September 21, 2026 with Pydantic
2.13.4, OpenFGA Python SDK 0.10.4, and `opa-python-client` 2.0.5. Upstream
snapshots included Cedar CLI 4.13.0 and OPA 1.20.0. Revalidate release notes and
compatibility before upgrading.

---

# 12. Enterprise request, decision, and effect contracts

The model proposes only business arguments:

```json
{
  "operation_id": "OP-PO-001",
  "action": "purchase_order:create",
  "resource_id": "department:data-ai",
  "amount_cents": 450000,
  "vendor_id": "vendor:acme",
  "country": "CA"
}
```

Trusted code adds identity and resolved state. A decision records:

```json
{
  "outcome": "allow",
  "reason_codes": ["all_authorization_constraints_satisfied"],
  "request_digest": "...",
  "resolved_input_digest": "...",
  "policy_version": "procurement-authz-2026-09",
  "authorization_epoch": 1,
  "evidence_versions": ["task:...", "resource:...", "vendor:...", "risk:..."],
  "valid_until": "...",
  "remaining_calls": 1
}
```

An effect record separately reports `not_attempted`, `applied`, or `unknown`.
Never infer execution success from a policy decision.

---

# 13. Hard denies, escalation, and precedence

Hard denies include cross-tenant access, unauthorized resource relationships,
wrong actor/task, inactive or expired task, sanctioned/unapproved vendor,
country prohibition, amount above task maximum, stale/mismatched risk evidence,
and exhausted call budget.

Approval-eligible examples include an amount above an autonomous threshold or a
moderate-risk band when policy explicitly permits review. Compute hard denies
first. A valid approval may satisfy only the named soft requirement; it cannot
erase a hard deny.

---

# 14. Approval as a constrained authorization input

A consequential approval should be a trusted, single-use receipt bound to:

- tenant, subject, actor, task, exact action/resource/arguments, and request digest;
- approver identity and authorized role;
- policy version, issue time, expiry, and state; and
- an atomic consumption record.

The model cannot create or edit this receipt. A changed proposal requires a new
approval. An `ESCALATE` decision must never invoke the effect while review is
pending.

---

# 15. TOCTOU, caching, and consistency

A preview is not an execution permit. If a vendor is suspended, a task closes,
or policy changes between preview and invocation, the PEP must observe current
state immediately before the effect.

A safe cache key needs more than principal/action/resource:

- tenant, subject, actor/workload, task, request digest, and operation ID;
- policy/schema/model version and authorization-data epoch;
- relationship, resource, vendor, risk, and approval versions;
- decision TTL, identity/task expiry, and revocation SLO; and
- effect sensitivity and reversibility.

Do not blindly cache permits for writes. A narrow read cache may be reasonable
when its staleness budget, invalidation, consistency mode, and failure behavior
are explicit and tested.

---

# 16. Retries, concurrency, effects, and outages

Use a stable logical operation ID across uncertain retries, plus per-attempt
telemetry in production. Bind the operation to an exact request digest. An
identical retry should return the persisted result without applying the effect
again; changed arguments under the same ID are a collision and must be denied.

Validation and consumption of call limits or approvals must be atomic. The lab
runs eight concurrent operations against a one-call task and allows exactly one.
Its in-process lock is a teaching mechanism; production needs a transactional
shared store, durable reservation state, crash recovery, and multi-region
consistency design.

If a network timeout occurs after effect submission, the outcome is `unknown`,
not failed and not successful. Reconcile the target system using the same
idempotency key before retrying. A PDP outage fails closed for writes; the same
operation may be retried after the transient dependency recovers.

---

# 17. Audit, privacy, and operations

Record observable evidence rather than hidden reasoning:

- request/run/operation, subject, actor, workload, tenant, task, action, and resource IDs;
- request and resolved-input digests;
- policy/model/schema/bundle and source-data versions;
- outcome, reason codes, expiry, remaining budget, and authorization epoch;
- approval ID/state when relevant; and
- effect status, external receipt, attempts, latency, and errors.

Do not log bearer tokens, credentials, raw prompts, unnecessary personal data,
or sensitive vendor/risk inputs. OPA decision logs support masking; equivalent
privacy controls are needed for every engine. Define owners and SLOs for PDP
availability, p95/p99 latency, tuple/policy propagation, revocation, cache
invalidation, and denied-action investigation.

---

# 18. Testing and evaluation

| Test class | Representative proof |
|---|---|
| positive/boundary | valid purchase and exactly CAD 5,000 autonomous amount |
| identity/isolation | wrong actor, wrong tenant, unauthorized user/resource |
| task relationships | action, resource, vendor, lifecycle, amount, and call budget |
| authoritative context | vendor approval/sanctions/country and exact current risk evidence |
| approval | missing, mutated, expired, wrong role, hard-deny override, consumption |
| retries/effects | identical retry, altered collision, persisted effect, unknown outcome |
| concurrency | eight operations competing for one call permit |
| time/change | stale identity/task/risk and vendor change before execution |
| dependency failure | PDP outage blocks effect and can recover |
| adapters | OpenFGA SDK shape and default-deny Cedar/Rego artifacts |

The canonical ten-case evaluation includes two allowed, seven forbidden, and
one escalation case. It compares the role-only baseline with the fine-grained
PDP and reports:

| Metric | Population | Numerator | Required direction |
|---|---|---|---|
| decision correctness | all 10 cases | expected equals actual | higher |
| forbidden actions allowed | 7 forbidden cases | returned `ALLOW` | zero |
| false denials | 2 legitimate cases | not `ALLOW` | lower |
| missed escalation | 1 escalation case | not `ESCALATE` | zero |
| one-call race | 8 concurrent operations | effects applied | exactly one |

These tests prove deterministic implementation invariants, not production
security effectiveness. Add engine parity, schema/model migration, consistency,
load, chaos, penetration, and real outcome reconciliation before release.

Policy mutation testing is valuable: remove the vendor check, widen an amount
comparison, change an intersection to a union, or drop a hard `forbid`; the
corpus should fail for the specific widened access.

---

# 19. State of the art — September 2026 snapshot

## Established practice

- externalize or rigorously isolate authorization from model reasoning;
- use authenticated identity, default deny, least privilege, short-lived task authority, and PEP enforcement;
- model relationships with OpenFGA/Zanzibar-style systems when graph queries dominate;
- model contextual application policy with Cedar/Verified Permissions or structured policy with OPA/Rego;
- version and test policy, schema/model, authoritative data, and rollout artifacts; and
- separate decision evidence from verified effect evidence.

## Current agent-specific practice

OpenFGA now publishes dedicated first-party, third-party/tool, task, RAG, MCP,
and agents-as-principals patterns. AgentCore Policy applies Cedar-compatible
policy at Gateway tool invocation. These patterns increasingly treat task,
session, agent, tool, and target resource as distinct authorization dimensions.

## Emerging research—not standards

- **AutoCedar** proposes verifier-guided Cedar synthesis from reviewed intent atoms.
- **Prose2Policy** proposes a natural-language-to-Rego pipeline with schema, lint, compile, and behavioral-test stages.
- **FAVA** proposes evidence-backed permission graphs and formal runtime authorization for dynamic agent traces.

These are 2026 research preprints. Their reported evaluations do not establish
interoperable standards, production fitness, or a substitute for organizational
intent review, independent tests, and runtime enforcement.

## Open problems

- portable intent and permission representations across organizations and agent chains;
- revocation and consistency across relationship, attribute, approval, and tool systems;
- safe policy synthesis when source prose is incomplete or contradictory;
- authorization for dynamic data flow and derived artifacts;
- composing several PDPs without disagreement or availability gaps; and
- proving that authorized arguments match the eventual external effect.

---

# 20. Practical lab and notebook

[Run the guided notebook](05_fine_grained_authorization_for_agents.ipynb) or
inspect the tested reusable implementation in [`lab.py`](lab.py).

From the repository root:

```bash
make course-05
```

The lab implements:

- a deliberately unsafe role-only baseline;
- typed identity, action, task, resource, vendor, risk, approval, decision, audit, and effect contracts;
- dual user/resource and task/agent authorization;
- authoritative versioned context with hard-deny and escalation precedence;
- exact request-bound, expiring, single-use approval;
- immediate PEP reauthorization and authorization epochs;
- atomic call consumption, operation/request binding, and idempotent effect replay;
- fail-closed but retryable PDP outage behavior;
- real OpenFGA SDK check and contextual-tuple objects;
- illustrative OpenFGA, Cedar, and Rego policy artifacts with honest live-engine boundaries;
- ten labelled comparison cases and explicit safety denominators; and
- 31 focused invariant checks plus notebook execution coverage.

The default path uses Pydantic and `openfga_sdk`. It prints the installed
`opa-python-client` version for the extension path but does not contact OPA.
Live OpenFGA, Cedar, OPA, Verified Permissions, and AgentCore integrations must
reuse the same invariant corpus and prove semantic parity.

---

# 21. Production blueprint

1. Define canonical typed request, decision, approval, audit, and effect contracts.
2. Derive identity and tenant from authenticated state.
3. Inventory authoritative relationship and attribute owners with freshness SLOs.
4. Select the minimum engine combination and one final composition owner.
5. Pin policy/schema/model versions and protect policy/tuple writes.
6. Build a PEP that cannot be bypassed by alternate tool or API paths.
7. Reauthorize immediately before writes and atomically reserve bounded authority.
8. Use stable idempotency keys and reconcile unknown outcomes.
9. Roll out policy with shadow comparison, mutation/regression tests, metrics, and rollback.
10. Monitor denials, false denials, latency, propagation, outages, and verified effects.

---

# 22. Anti-patterns

- trusting role names, scopes, task IDs, or `approved=true` from the model;
- checking task access without checking the delegating user's resource access;
- checking a task but not binding the calling agent;
- placing authorization only in prompt instructions or tool descriptions;
- treating schema-valid context as authoritative;
- allowing policy timeout or malformed output to fall through to execution;
- caching a write permit across policy or source-version changes;
- accepting human approval as an override for tenant, sanctions, or hard task limits;
- incrementing a quota after the effect without atomic reservation;
- retrying an unknown effect with a new idempotency key;
- calling a mocked policy artifact “OpenFGA/Cedar/OPA validation”; and
- measuring blocked attacks as successful attacks or omitting false denials.

---

# 23. Exercises and review questions

1. Add a second authorized user and prove a task delegated by one user cannot borrow the other's resource relationship.
2. Add session-scoped and agent-scoped OpenFGA grants; compare blast radius and cleanup with task-scoped grants.
3. Add a moderate-risk approval path while preserving the hard high-risk deny.
4. Replace the lock with SQLite transactions and design crash recovery between reservation and effect.
5. Implement an unknown-effect reconciliation adapter that never duplicates a purchase order.
6. Run the Cedar and Rego artifacts in real local engines and prove parity with all focused cases.
7. Design a safe read-decision cache and demonstrate invalidation on policy epoch and relationship version changes.
8. Add policy mutations and identify which test kills each mutation.
9. Define SLOs for decision latency, availability, revocation propagation, and false-denial investigation.

Review questions:

- Why is a valid scope or role not sufficient for one agent tool invocation?
- Which data belongs in relationships, entity attributes, request context, and approval receipts?
- Why are user and task checks an intersection rather than alternatives?
- What does a decision receipt prove, and what remains unknown until the effect is verified?
- When can a cached decision be reused safely?
- How do you preserve fail-closed behavior without making a transient outage permanently poison an idempotency key?

---

# 24. Primary and official references

1. [OpenFGA — Authorization for Agents](https://openfga.dev/docs/modeling/agents)
2. [OpenFGA — Task-Based Authorization](https://openfga.dev/docs/modeling/agents/task-based-authorization)
3. [OpenFGA — Agents as Principals](https://openfga.dev/docs/modeling/agents/agents-as-principals)
4. [OpenFGA — Contextual Tuples](https://openfga.dev/docs/interacting/contextual-tuples)
5. [OpenFGA Python SDK releases](https://github.com/openfga/python-sdk/releases)
6. [Cedar Policy Language](https://docs.cedarpolicy.com/)
7. [Cedar authorization semantics](https://docs.cedarpolicy.com/auth/authorization.html)
8. [Cedar policy validation](https://docs.cedarpolicy.com/policies/validation.html)
9. [Cedar releases](https://github.com/cedar-policy/cedar/releases)
10. [Open Policy Agent documentation](https://www.openpolicyagent.org/docs)
11. [OPA Rego policy language](https://www.openpolicyagent.org/docs/policy-language)
12. [OPA decision logs and masking](https://www.openpolicyagent.org/docs/management-decision-logs)
13. [OPA releases](https://github.com/open-policy-agent/opa/releases)
14. [Amazon Verified Permissions](https://docs.aws.amazon.com/verifiedpermissions/)
15. [Amazon Bedrock AgentCore Policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html)
16. [AgentCore Policy core concepts](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html)
17. [AgentCore Policy permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-permissions.html)
18. [AutoCedar research preprint](https://arxiv.org/abs/2607.03656)
19. [Prose2Policy research preprint](https://arxiv.org/abs/2603.15799)
20. [FAVA research preprint](https://arxiv.org/abs/2607.27267)

---

# 25. Next module

## Module 6 — Policy-as-Code & Runtime Governance

Next, the curriculum expands from authorization into the broader runtime policy
lifecycle: policy packaging, validation, rollout, enforcement, observability,
exceptions, and continuous governance.
