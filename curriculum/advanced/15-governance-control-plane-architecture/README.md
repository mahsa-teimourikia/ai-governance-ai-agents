# Module 15 — Governance Control Plane Architecture

> **Course:** Enterprise AI Agent Governance: From Principles to Runtime Control  
> **Audience:** AI architects, agent engineers, security architects, IAM/platform teams, governance leaders, SRE, enterprise architects  
> **Recommended duration:** 10 hours theory + 8 hours practical lab  
> **Scenario:** Design and prototype a vendor-neutral governance control plane for an enterprise procurement-agent ecosystem.

## Course thesis

A governance control plane is not a dashboard and not a policy engine renamed.
It is the trusted architecture that turns authenticated identity, delegated
authority, versioned policy, human decisions, and system state into enforced
actions and verified outcomes. The agent may propose an action; it must not
assert its own principal, approve itself, mint its own authority, or bypass the
enforcement point.

> **Core principle:** Reasoning can be probabilistic. Authority should be
> explicit, bounded, short-lived, attributable, and enforceable.

## Prerequisites

- Courses 4–8: identity, delegated authority, policy, tools/MCP, and approval;
- Courses 10–14: multi-agent delegation, security, red teaming, evidence, and evaluation;
- working knowledge of Python, typed data models, API gateways, and distributed-systems failure modes.

The canonical lab is deterministic and credential-free. It makes no model,
network, cloud, shell, or business-system call.

## Success criteria

You have completed this module when you can:

- draw the trust boundaries among the agent runtime, management, decision, enforcement, evidence, identity, and business systems;
- explain which facts come from trusted ingress and which are untrusted model proposals;
- prevent tenant crossing, authority widening, approval replay, stale policy use, and duplicate effects;
- choose strong consistency, bounded stale reads, or fail-closed behavior for each state transition;
- compose policy, relationship authorization, workload identity, gateway, OAuth/MCP, and telemetry products without transferring architectural accountability to them; and
- demonstrate a linked proposal → decision → approval → effect → verified-outcome evidence chain.

## Non-goals

The course does not claim its in-memory HMACs, registry, or evidence chain are a
production security boundary. It does not benchmark vendor latency, certify a
product, make a synthetic scenario suite proof of production safety, or imply
that OpenTelemetry records are automatically audit evidence. Production
systems need managed keys, durable stores, access control, retention,
replication, recovery, monitoring, and independent assurance.

## Learning objectives

Learners will be able to:

- explain why agent governance requires architectural enforcement, not only policies and prompts;
- separate reasoning, authority and execution;
- distinguish management, decision, enforcement and evidence responsibilities;
- design agent registration, identity and lifecycle controls;
- represent delegated authority as explicit machine-readable context;
- evaluate actions using identity, authority, purpose, data, risk and policy;
- implement ALLOW / DENY / ESCALATE / CONSTRAIN decisions;
- place policy enforcement points at tools, APIs, MCP servers, agents and data boundaries;
- design fail-closed behavior and break-glass paths;
- integrate human approvals without creating rubber-stamp workflows;
- externalize policy using policy-as-code patterns;
- create action-bound authorization and approval tokens;
- propagate governance context through multi-agent workflows;
- record decision evidence and action lineage;
- connect observability, evaluation and security feedback to policy updates;
- design for latency, availability, caching and degraded operation;
- avoid turning the control plane into a single point of failure;
- evaluate build-vs-buy and vendor-neutral integration patterns.

![Control plane](assets/01-governance-control-plane.svg)

---

## 1. Why a governance control plane?

Enterprise agents combine models with:

```text
data
memory
tools
APIs
MCP servers
other agents
credentials
business systems
```

When controls remain scattered across prompts, service accounts, application code and tool integrations, organizations cannot consistently answer:

```text
Which agents exist?
Who owns them?
What may each agent do?
On whose authority?
Under what conditions?
Which policy applied?
What actually happened?
```

A governance control plane creates a shared architecture for those answers.

---

## 2. Control plane vs agent runtime

The agent runtime is responsible for capabilities such as:

```text
planning
reasoning
retrieval
memory
delegation
tool selection
```

The governance control plane is responsible for constraints such as:

```text
identity
authority
authorization
policy
risk
approval
data boundaries
evidence
```

Do not make the same probabilistic component both propose and independently authorize its own action.

---

## 3. Control plane vs data/action plane

Borrow a useful pattern from distributed systems.

### Control plane

Defines and coordinates:

```text
agents
policies
permissions
risk rules
registrations
versions
approval requirements
```

### Action/data plane

Actually executes:

```text
tool calls
API mutations
database changes
payments
messages
agent-to-agent calls
```

Controls should be centrally governable while enforcement can be distributed near the action.

---

## 4. Four architectural responsibilities

![Planes](assets/03-control-plane-separation.svg)

### Management

```text
agent registry
ownership
versions
lifecycle
tool registry
policy distribution
```

### Decision

```text
identity
authorization
risk
policy evaluation
approval routing
```

### Enforcement

```text
tool gateway
API proxy
MCP boundary
data access
agent gateway
```

### Evidence

```text
decision logs
traces
action lineage
evaluation
security events
audit
```

---

## 5. Agent registry

A production control plane needs a durable registry.

Example:

```yaml
agent_id: procurement-agent
version: 14
owner: procurement-platform
purpose: purchase-order-assistance
risk_tier: high
runtime: langgraph
allowed_tools:
  - vendor.read
  - po.prepare
  - po.create
max_autonomy: bounded
policy_bundle: procurement-v7
```

Identity must survive beyond an individual process invocation.

---

## 6. Tool registry

Register tools with governance metadata:

```yaml
tool: payment.execute
risk: critical
data_classification: restricted
reversible: false
required_permission: payment.execute
approval: multi_party
max_amount: 500000
```

The control plane should not infer tool consequence solely from a tool name.

---

## 7. Principal model

A decision may involve several principals:

```text
human principal
agent identity
service/workload identity
delegating agent
tenant
organization
```

Treat the acting agent and the authority source as separate concepts.

---

## 8. Delegated authority

Represent authority explicitly:

```json
{
  "delegator": "user:42",
  "delegate": "agent:procurement",
  "purpose": "purchase approved equipment",
  "permissions": ["vendor.read", "po.create"],
  "constraints": {"max_amount": 15000},
  "expires_at": "..."
}
```

Authority should normally attenuate as it is delegated.

---

## 9. Governance context envelope

Every consequential action should carry normalized context:

```text
principal
agent
delegation
purpose
requested action
resource
tool
data classification
risk
environment
session/workflow
```

This prevents every tool from inventing its own governance vocabulary.

---

## 10. Runtime decision pipeline

![Decision pipeline](assets/02-runtime-decision-pipeline.svg)

A practical decision:

```text
Who is acting?
↓
What authority exists?
↓
What is being requested?
↓
What data/resource is involved?
↓
Which policy applies?
↓
What is the risk?
↓
ALLOW / DENY / ESCALATE / CONSTRAIN
```

---

## 11. Beyond allow/deny

Agent governance benefits from richer decisions.

### ALLOW
Execute as proposed.

### DENY
Block.

### ESCALATE
Require human/stronger approval.

### CONSTRAIN
Execute with reduced scope.

Examples:

```text
reduce amount
remove sensitive fields
use read-only tool
limit destination
require sandbox
disable delegation
```

---

## 12. Policy decision point

The PDP evaluates policy using structured input.

Example:

```json
{
  "subject": {...},
  "action": {...},
  "resource": {...},
  "delegation": {...},
  "risk": {...},
  "environment": {...}
}
```

Return a structured decision with reasons—not merely `true`.

---

## 13. Policy enforcement points

Place PEPs where consequence occurs:

```text
tool gateway
API gateway
MCP server
database proxy
agent-to-agent gateway
message/email gateway
filesystem
cloud-control API
```

A policy that cannot stop the action is advisory, not enforcement.

---

## 14. OPA and policy-as-code

Open Policy Agent is a mature general-purpose policy engine using Rego.

It is useful for:

```text
fine-grained authorization
context-aware API decisions
central policy distribution
policy testing
decision logging
```

OPA supports externalized authorization where services ask the policy engine whether a request should execute.

The architecture matters more than the specific engine: policies should be versioned, testable and independent of agent prompts.

---

## 15. Risk engine

Authorization alone is not enough.

A user may technically have permission while the requested action is unusual or high impact.

Risk inputs can include:

```text
impact
amount
data sensitivity
novelty
confidence
irreversibility
anomaly score
destination
delegation depth
```

Policy can then combine authority with contextual risk.

---

## 16. Human approval router

Approval logic belongs in the control architecture.

Example:

```text
$40 reimbursement
→ ALLOW

$2,000 unusual expense
→ ESCALATE to reviewer

$25,000 vendor payment
→ manager approval

$500,000 irreversible payment
→ multi-party approval
```

Bind approval to the exact proposed action.

---

## 17. Action binding

A generic approval flag is unsafe.

Instead bind:

```text
tool
arguments
resource
amount
destination
policy version
expiry
```

using a signed or hashed action representation.

If the action changes, re-authorize it.

---

## 18. Tool gateway

A tool gateway can provide:

```text
tool discovery filtering
identity propagation
authorization
argument validation
risk evaluation
approval
rate limiting
DLP
execution
result classification
audit
```

This is especially useful when multiple agent frameworks use the same enterprise tools.

---

## 19. MCP governance

MCP expands the agent/tool ecosystem.

Govern:

```text
server identity
tool registration
tool provenance
capabilities
credentials
authorization
arguments
results
data egress
version/change
```

Do not assume discovery implies permission.

---

## 20. Agent-to-agent governance

For multi-agent calls, propagate:

```text
caller identity
delegator
purpose
scope
permissions
constraints
parent delegation
trace/evidence ID
```

The receiving agent must independently validate authority.

---

## 21. Data governance integration

The control plane should consume enterprise classification:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

Policy can combine:

```text
agent permission
+
user authority
+
data classification
+
purpose
+
destination
```

---

## 22. Guardrails

Guardrails remain useful for:

```text
input/output validation
content safety
PII detection
schema enforcement
prompt-injection signals
```

But guardrails do not replace authorization.

A classifier saying an action looks safe does not grant authority.

---

## 23. Credential architecture

Avoid handing broad long-lived credentials to agents.

Prefer:

```text
workload identity
short-lived credentials
scoped tokens
token exchange
just-in-time access
capability attenuation
```

The control plane should help connect identity to least-privilege execution.

---

## 24. Fail closed vs fail open

For consequential actions:

```text
policy engine unavailable
→ usually fail closed
```

For low-risk read-only functions, carefully designed cached decisions or degraded modes may be appropriate.

Define this explicitly by risk tier.

---

## 25. Availability architecture

A centralized governance architecture must not become a fragile bottleneck.

Consider:

```text
local/sidecar enforcement
policy bundles
decision caching
regional replicas
timeouts
circuit breakers
degraded-mode policy
```

OPA, for example, supports policy/data bundles that can be distributed to policy instances.

---

## 26. Caching

Cache only when decision context is stable enough.

Cache key may include:

```text
agent
principal
permission
resource
policy version
delegation
risk class
```

Never reuse a cached approval for a materially different action.

---

## 27. Decision evidence

Each decision should emit:

```json
{
  "decision_id": "d-123",
  "decision": "ESCALATE",
  "agent": "procurement:v14",
  "policy": "procurement-v7",
  "reason_codes": ["HIGH_VALUE", "NEW_VENDOR"],
  "risk_tier": "HIGH",
  "authority": "delegation-882"
}
```

Do not invent a precise risk score when the underlying evidence only supports a
category or rule match. Keep blocked attempts distinct from completed harmful
effects, and attach the verified business outcome rather than accepting the
agent's claim that a call succeeded.

This connects the architecture to Module 13.

---

## 28. Observability integration

OpenTelemetry's GenAI semantic conventions help standardize runtime telemetry around model and agent operations.

Add organization-specific governance metadata such as:

```text
governance.decision.id
governance.policy.version
governance.risk.tier
governance.delegation.id
governance.approval.id
```

Avoid leaking sensitive content into traces.

---

## 29. Evaluation integration

The control plane should consume evaluation evidence.

Examples:

```text
security regression
→ disable tool

quality regression
→ lower autonomy

approval bypass discovered
→ block release

new attack pattern
→ update policy
```

This connects Module 14 directly to runtime governance.

---

## 30. Security integration

Feed control-plane events into:

```text
SIEM
SOC
DLP
identity analytics
fraud/anomaly systems
incident response
```

Agent governance should extend enterprise security architecture, not create an isolated island.

---

## 31. Governance loop

![Governance loop](assets/04-governance-control-loop.svg)

```text
Register
→ Authorize
→ Enforce
→ Observe
→ Evaluate
→ Update
```

This is the operational form of continuous governance.

---

## 32. Policy versioning

Every decision should be attributable to a policy version.

Support:

```text
Git/version control
review
tests
promotion
rollback
effective dates
decision logs
```

A governance incident should be reproducible against the policy active at that time.

---

## 33. Shadow policy evaluation

Before activating a new policy:

```text
production request
→ current policy → enforce
→ candidate policy → observe only
```

Compare decisions.

This reduces policy rollout risk.

---

## 34. Control-plane testing

Test:

```text
identity spoofing
delegation escalation
stale authorization
policy outage
approval replay
tool mutation
MCP tool change
data-classification change
multi-agent propagation
decision latency
evidence completeness
```

---

## 35. Correctness invariants

Useful architectural invariants:

### No action without identity
Every consequential action has an attributable agent/workload.

### No authority amplification
Delegation cannot create permissions the parent did not possess.

### No execution before authorization
The enforcement point must mediate the action.

### Approval binds to action
Changing consequential parameters invalidates approval.

### Every decision is reconstructable
Decision, policy, authority and outcome are linked.

### Every side effect is idempotent or reconciled
A timeout is an unknown outcome, not proof of failure. Reconcile the operation
key before retrying a consequential action.

### Control state is tenant- and environment-scoped
An identifier match across tenants or development and production never implies
shared authority.

---

## 35A. Consistency boundaries and failure semantics

Not all control-plane data needs the same consistency model.

| State | Required behavior | Why |
|---|---|---|
| Approval consumption | atomic, strongly consistent, one time | two gateways must not spend one approval |
| Execution grant | atomic, exact-action, short lived | prevents replay and argument mutation |
| Lifecycle suspension / kill switch | rapidly convergent with fail-closed enforcement for consequential actions | a stopped agent must not continue from stale state |
| Delegation parent and attenuation | validate the signed chain and expiry at use | a child must not widen inherited authority |
| Policy bundle | signed, versioned, integrity checked | a decision must identify the exact evaluated policy |
| Low-risk read bundle | bounded last-known-good may be acceptable | availability can be preserved inside an explicit stale-time budget |
| High-risk mutation during policy outage | fail closed | stale permission must not create a new external effect |
| Business effect | idempotency key plus outcome reconciliation | network ambiguity must not duplicate an order or payment |
| Evidence | append-only ordering plus durable protected persistence | reconstruction depends on linkage and integrity |

Cache keys need every fact capable of changing the answer: tenant,
environment, principal, workload, agent and tool versions, action and resource,
delegation, policy digest, risk tier, and relevant context. Do not cache
approvals as general decisions.

## 35B. Threat model

The design assumes the model, prompt, retrieved content, tool descriptions, and
agent-supplied arguments can be hostile. It also considers:

- a caller forging its tenant, principal, role, workload identity, or delegation;
- a child agent widening tool, resource, amount, purpose, environment, or lifetime;
- a compromised registry or policy distribution path serving stale or modified state;
- approval mutation, replay, cross-tenant use, and concurrent double consumption;
- schema drift between discovery and execution;
- a policy or identity dependency outage;
- an external system committing an action before a timeout reaches the gateway;
- evidence containing secrets or being modified after the event; and
- a model remembering a hidden tool and attempting to call it after suspension.

The lab demonstrates controls for these paths. Managed signing keys, replicated
datastores, production network identity, external policy engines, and actual
business APIs remain explicit integration work.

## 35C. Common technologies and the responsibility they do not remove

| Concern | Common technology or method | Useful boundary | What the control-plane owner still decides |
|---|---|---|---|
| General policy | OPA/Rego | bundle distribution and PDP API/sidecar | schemas, lifecycle, bundle trust, obligations, fail mode, and decision evidence |
| Analyzable authorization | Cedar | PARC request, entities, schema-validated policy | authentication, entity provenance, request construction, enforcement, and version rollout |
| Relationship authorization | OpenFGA / Zanzibar-style ReBAC | model, tuples, contextual facts, consistency choice | tenant model, tuple writers, freshness requirements, and effect mediation |
| Workload identity | SPIFFE/SPIRE | attested SPIFFE ID and SVID | trust domains, workload registration, identity-to-agent binding, and authorization |
| Network enforcement | Envoy `ext_authz` | `CheckRequest`/`CheckResponse` before the upstream | request attributes, failure mode, mutation policy, and outcome linkage |
| Delegation | OAuth token exchange (RFC 8693), rich authorization requests (RFC 9396), resource indicators (RFC 8707) | audience-, resource-, and purpose-scoped tokens | attenuation policy, token lifetime, downstream exchange, and revocation strategy |
| Tool protocol | MCP Authorization | OAuth protected-resource discovery and audience-bound access token | tool discovery policy, per-call business authorization, and prohibition on token passthrough |
| Evidence and operations | OpenTelemetry | trace and span context across components | data minimization, access, retention, integrity, sampling, and audit qualification |

These technologies overlap but are not interchangeable. A policy engine is not
an identity provider, an identity is not permission, a protocol token is not a
business approval, a trace is not automatically evidence, and an ALLOW is not a
verified external outcome.

---

## 36. NIST direction in 2026

NIST launched the **AI Agent Standards Initiative** in February 2026, explicitly focusing on interoperable and secure agents, open protocol ecosystems, and research into agent security and identity.

NIST's NCCoE also published an **initial public draft** concept paper on applying
identity and authorization standards to software and AI agents. It calls out
identification, authorization, auditing, non-repudiation and prompt-injection
mitigation as areas for a proposed practice guide. Treat it as active standards
work, not as a completed normative architecture.

This reinforces a central architectural direction:

> Agent identity and delegated authorization are becoming infrastructure concerns, not merely application features.

---

## 37. Emerging reference architectures

The term **agentic control plane** is increasingly used in enterprise architecture.

Treat vendor architectures as implementations of a broader pattern rather than a universal standard.

The portable primitives are:

```text
registry
identity
authority
policy
risk
enforcement
approval
evidence
evaluation
lifecycle
```

---

## 38. Build vs buy

### Build
Useful when:

```text
unique policies
specialized high-risk workflows
existing IAM/policy infrastructure
strong platform team
```

### Buy
Useful when:

```text
rapid standardization
many frameworks
cross-enterprise inventory
managed integrations
governance operations
```

Most large enterprises will likely use a hybrid architecture.

---

## 39. Avoid the mega-gateway anti-pattern

Do not force every model token and low-risk operation through one synchronous governance service.

Govern at meaningful boundaries:

```text
identity issuance
delegation
sensitive retrieval
tool execution
external communication
agent handoff
high-impact mutation
```

Use distributed enforcement and centrally managed policy.

---

## 40. Avoid prompt-only governance

Bad:

```text
SYSTEM:
Never spend more than $10,000.
```

Better:

```text
agent proposes payment
↓
control plane evaluates amount + authority + risk
↓
gateway enforces decision
```

Prompts influence behavior.

Enforcement controls authority.

---

## 41. Practical notebook

`15_governance_control_plane_architecture.ipynb`

The notebook imports the reusable [`lab.py`](lab.py) implementation and walks
through a realistic multi-tenant procurement control plane. It builds and tests:

- tenant-scoped, versioned agent and tool registries with authenticated administrative lifecycle transitions and optimistic concurrency;
- a trusted `AuthenticatedContext` whose principal and SPIFFE-style workload identity never come from model output;
- signed root and child delegation with strict attenuation of tools, operations, resources, amount, environment, purpose, lifetime, and depth;
- signed, versioned, tenant- and environment-scoped policy bundles;
- typed untrusted action proposals and trusted action requests;
- ALLOW, DENY, ESCALATE, and CONSTRAIN decisions with exact reason codes and obligations;
- action-bound, role-checked, expiring approvals bound to the exact decision, policy digest, and agent/tool registry revisions, with atomic single-use consumption under concurrency;
- a gateway that owns final authorization, constraint application, execution, and outcome recording;
- idempotent effects, unknown-outcome reconciliation, and single-use execution grants;
- normal, read-only, stopped, fail-closed, and bounded last-known-good modes;
- corpus-bound shadow policy evaluation, an authenticated activation gate, and scope-checked local policy replicas that cannot change the enforced decision before activation;
- append-only hash-linked evidence containing digests rather than raw prompt or secret content;
- in-memory OpenTelemetry spans with minimized governance metadata;
- an interoperability map across OPA, Cedar, OpenFGA, SPIFFE, Envoy, OAuth, MCP, and OpenTelemetry, plus real offline OPA/OpenFGA SDK configuration artifacts and Rego/Cedar/OpenFGA policy-model examples; and
- 12 labelled scenarios comparing a prompt-only baseline with the governed path.

Run the complete lab and its focused invariant suite:

```bash
make course-15
```

The tests are the executable claims. They include negative and concurrency
paths, not only a happy-path demonstration.

### Claim-to-proof map

| Claim | Executable proof |
|---|---|
| Delegation cannot amplify authority | forged signature and tool/operation/resource/amount widening tests |
| Suspended agents lose capability | lifecycle transition, discovery filtering, and decision-time denial tests |
| Administrative state changes are authorized | current tenant-bound operator, role, lifecycle, and optimistic-concurrency tests |
| Approval binds to one exact decision state | mutation, policy/registry version, wrong role, expiry, replay, and concurrent double-consumption tests |
| Denial prevents an external effect | gateway denial tests assert adapter call count remains zero |
| Unknown outcomes do not cause blind retry | timeout receipt and reconciliation binding tests |
| Outage behavior is risk-aware | bounded last-known-good read and fail-closed mutation tests |
| Candidate policy cannot silently become authority | exact shadow population, regression gate, activation receipt, and cross-tenant replica tests |
| Evidence is linked and tamper evident | sequence, previous-hash, content-minimization, and mutation tests |
| Common SDK boundaries are real but offline | installed OPA/OpenFGA configurations, policy artifacts, package versions, and in-memory OpenTelemetry tests |
| Governance improves the fixture without hiding friction | exact decision, forbidden-outcome, and valid-work-blocked counts |

---

## 42. Enterprise checklist

- Is every agent registered and owned?
- Are agent versions distinguishable?
- Are tools registered with consequence metadata?
- Is agent identity separate from user authority?
- Is delegated authority explicit?
- Does authority attenuate?
- Is purpose propagated?
- Are consequential actions mediated?
- Are policies externalized and versioned?
- Is risk evaluated separately from permission?
- Are approvals action-bound?
- Can decisions constrain instead of only allow/deny?
- Are MCP tools governed?
- Are agent-to-agent calls authorized?
- Is data classification integrated?
- Are credentials short-lived and scoped?
- Is fail-open/closed behavior defined by risk?
- Can the control plane survive outages?
- Are policies cached safely?
- Is every decision evidenced?
- Is evaluation connected to control updates?
- Can policy changes be shadow-tested?
- Can incidents reconstruct identity → authority → decision → action → outcome?

---

## 43. Primary references

### Standards and public-sector direction

1. [NIST — AI Agent Standards Initiative (February 2026)](https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure)
2. [NIST NCCoE — Accelerating the Adoption of Software and AI Agent Identity and Authorization, initial public draft](https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd)
3. [RFC 8693 — OAuth 2.0 Token Exchange](https://www.rfc-editor.org/rfc/rfc8693.html)
4. [RFC 8707 — Resource Indicators for OAuth 2.0](https://www.rfc-editor.org/info/rfc8707/)
5. [RFC 9396 — OAuth 2.0 Rich Authorization Requests](https://www.rfc-editor.org/rfc/rfc9396.html)

### Authorization and policy systems

6. [Open Policy Agent — Policy Language](https://www.openpolicyagent.org/docs/policy-language)
7. [Open Policy Agent — Bundles](https://www.openpolicyagent.org/docs/management-bundles)
8. [Open Policy Agent — Decision Logs](https://www.openpolicyagent.org/docs/management-decision-logs)
9. [Cedar — Authorization model and PARC requests](https://docs.cedarpolicy.com/auth/authorization.html)
10. [Cedar — Schema-based policy validation](https://docs.cedarpolicy.com/policies/validation.html)
11. [OpenFGA — Core concepts](https://openfga.dev/docs/concepts)
12. [OpenFGA — Contextual tuples](https://openfga.dev/docs/interacting/contextual-tuples)
13. [OpenFGA — Organization-context authorization](https://openfga.dev/docs/modeling/organization-context-authorization)
14. [Google Research — Zanzibar: Google's Consistent, Global Authorization System](https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/)

### Identity, gateways, tools, and evidence

15. [SPIFFE — Core identity concepts](https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/)
16. [SPIFFE — Workload API specification](https://spiffe.io/docs/latest/spiffe-specs/spiffe_workload_api/)
17. [Envoy — External authorization architecture](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/security/ext_authz_filter.html)
18. [Model Context Protocol — Authorization specification (2026-07-28)](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/authorization/index.mdx)
19. [Model Context Protocol — Enterprise-managed authorization extension](https://github.com/modelcontextprotocol/ext-auth/blob/main/specification/stable/enterprise-managed-authorization.mdx)
20. [OpenTelemetry — Semantic conventions](https://opentelemetry.io/docs/specs/semconv/)
21. [OpenTelemetry — GenAI agent and framework spans (development status)](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)

### Source interpretation notes

- OPA bundles are distributed state; decide which revision and freshness are acceptable for each action class.
- Cedar schemas validate policies and request structure separately from evaluation; the application still owns trusted request construction.
- OpenFGA contextual tuples are ephemeral request context, not a durable replacement for authoritative relationship state.
- SPIFFE authenticates workloads; it does not decide business authorization.
- Envoy `failure_mode_allow` is an architectural risk choice, and its default is fail closed.
- MCP authorization protects the transport and token audience; a server still needs per-tool and per-resource business authorization.
- The dedicated OpenTelemetry GenAI conventions are still marked development. Pin the version you emit and treat content attributes as sensitive opt-in data.

---

## 44. Key takeaway

> **The governance control plane is the architecture that converts organizational authority and policy into enforceable runtime decisions around autonomous action.**

The goal is not one giant governance product.

The goal is a **coherent control architecture** in which identity, authority, policy, risk, approval, enforcement, evidence and evaluation work together.
