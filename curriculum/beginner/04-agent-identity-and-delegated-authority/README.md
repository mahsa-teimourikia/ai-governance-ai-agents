# Module 4 — Agent Identity & Delegated Authority

> **Course:** Enterprise AI Agent Governance: From Principles to Runtime Control  
> **Audience:** AI engineers, IAM/security engineers, cloud architects, platform teams, agent developers, governance practitioners  
> **Recommended duration:** 5–6 hours theory + 4 hours practical lab  
> **Scenario:** Enterprise Procurement Agent

---

## Learning objectives

By the end of this module, you should be able to:

1. Distinguish **human identity, agent identity, workload identity, delegation, and authorization**.
2. Explain why an agent should not reuse a human's broad access token or a shared service account.
3. Design an explicit **authority chain** from user → agent → task → sub-agent/tool.
4. Apply **least privilege, zero standing privilege, task-scoped authorization, expiry, call limits, audience restriction, and revocation**.
5. Understand current NIST work on **software and AI agent identity and authorization**.
6. Explain the role of **SPIFFE/SPIRE** for workload identity.
7. Explain how **OAuth 2.0 Token Exchange (RFC 8693)** supports delegation and impersonation patterns.
8. Apply current OAuth security guidance from **RFC 9700**.
9. Compare **OpenFGA, Cedar, OPA, Amazon Verified Permissions, and AgentCore Policy**.
10. Implement a signed **delegation envelope** and validate identity, task, resource, audience, expiry, and call limits.
11. Model **task-scoped authorization** and narrower sub-agent delegation.
12. Produce auditable identity/delegation evidence.

> **Core principle:** Authentication tells us who the actor is. Authorization decides what that actor may do under the current delegated authority.

## Course thesis

A learner should be able to bind an authenticated human, a versioned logical
agent, and an attested workload to one approved task; issue only narrow derived
authority; enforce and atomically consume it at the action boundary; attenuate
sub-agent grants; and explain how to replace the teaching components with a
production identity, authorization, revocation, and evidence stack.

## Prerequisites

- [Module 1 — From AI Governance to Agent Governance](../01-from-ai-governance-to-agent-governance/README.md), especially the model/application authority boundary.
- [Module 2 — Agent Risk Modeling and Autonomy Classification](../02-agent-risk-modeling-and-autonomy-classification/README.md), especially capability and impact boundaries.
- [Module 3 — Standards, Regulation, and Governance Operating Model](../03-standards-regulation-and-governance-operating-model/README.md), especially evidence-bound release controls.
- Basic Python, JSON, HTTP, public-key signatures, OAuth/OIDC terminology, and API authorization concepts.

## Success criteria

You have completed this course when you can:

1. trace the source of truth for the human, agent version, workload, tenant, task, intent, and requested action;
2. reject a validly signed token when its audience, resource, task, lifecycle state, or current trusted context is wrong;
3. demonstrate that an identical uncertain retry is idempotent while a changed request using the same operation ID is denied;
4. prove that concurrent consumers cannot exceed a one-call grant;
5. show that every child grant is equal or narrower across action, resource, vendor, amount, call count, lifetime, audience transition, and delegation depth; and
6. report the numerator and denominator for forbidden actions allowed and valid actions denied.

## Non-goals and trust boundary

This course does not build an OAuth authorization server, deploy SPIRE, provide
a production token profile, prove legal non-repudiation, or replace an IAM
architecture review. The signed JWT is public deterministic test material. It
makes claims and failure modes visible; it is not a credential to copy into a
production system.

```text
model / agent → proposes actor intent and an operation
trusted application → authenticates, binds, authorizes, consumes, executes, verifies, records
```

Prompt text, an agent name, a SPIFFE-shaped string, a schema-valid object, and a
valid JWT signature are all inputs. None independently grants authority.

## Claim-to-proof map

| Course promise | Prose | Executable proof | Negative evidence |
|---|---|---|---|
| Identity comes from trusted state | Sections 2–5 | `bind_trusted_context` | wrong tenant, trust domain, selector, binding, and expiry tests |
| Authority is intent-bound and narrow | Sections 7–11 | `build_root_grant` | action, resource, vendor, amount, and call amplification tests |
| Tokens are verified, not merely decoded | Sections 7–8 | `verify_training_token` | tampering, algorithm/header, issuer, audience, and time tests |
| One-use limits survive concurrency | Sections 17 and 21 | `GrantLedger.authorize_and_consume` | eight-consumer race test permits exactly one |
| Delegation attenuates and revokes by lineage | Section 11 | `attenuate_grant` and `GrantLedger.revoke` | multi-dimension amplification and revoked-ancestor tests |
| Evidence is useful but bounded | Section 20 | structured `AuditEvent` with digests | raw token excluded; event does not claim the external effect occurred |

---

# 1. Why agent identity is now a governance problem

Traditional enterprise systems already distinguish human identities, service identities, and workloads.

Agentic AI combines several of them:

```text
Human intent
  ↓
Agent identity
  ↓
Workload identity
  ↓
Delegated task authority
  ↓
Tool / API action
```

An enterprise needs to reconstruct:

- which human or business process initiated the task,
- which agent/version acted,
- which workload executed it,
- which authority was delegated,
- which resource and action were authorized,
- whether the grant was still valid,
- whether a sub-agent inherited more access than intended.

NIST's February 2026 concept paper on agent identity and authorization highlights **identification, authorization, auditing, non-repudiation, and prompt-injection controls** for software and AI agents. It was an initial public-draft concept paper with a comment period that closed on April 2, 2026—not a normative standard or final deployment profile. NIST also launched its AI Agent Standards Initiative in February 2026.

Primary reading:

- https://www.nist.gov/news-events/news/2026/02/new-concept-paper-identity-and-authority-software-agents
- https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd
- https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative

![Identity and authority chain](assets/01-identity-authority-chain.svg)

---

# 2. Identity, authentication, delegation, and authorization are different

## Identity

A stable identifier for an actor.

Examples:

```text
human:user-123
agent:procurement-v1
spiffe://enterprise.example/prod/procurement-agent
```

## Authentication

Evidence that an actor really controls the claimed identity.

Examples:

- OIDC login,
- mTLS certificate,
- SPIFFE X.509-SVID,
- JWT-SVID,
- signed client assertion.

## Delegation

A principal grants another actor constrained authority to act on its behalf.

Example:

```text
User
  ↓ delegates
Procurement Agent
  ↓ may
Create one PO
  ↓ constrained to
Data & AI department
Approved vendors
Maximum $5,000
30-minute lifetime
```

## Authorization

A runtime decision:

> Can this principal perform this action on this resource in this context?

Cedar expresses this as:

**Principal + Action + Resource + Context**

OpenFGA models authorization through relationships, tasks, tuples, and conditions.

## Consent and approval

Consent records what a user agreed an application may request. Business approval
records that an authorized reviewer accepted a particular consequential action.
Neither is the same as the resource server's current authorization decision.

| Concept | Question | Typical evidence |
|---|---|---|
| Identity | Who is named? | stable principal ID |
| Authentication | Who proved control now? | OIDC session, passkey, SVID, mTLS |
| Consent | What did the user allow the client to request? | authorization grant/consent record |
| Delegation | Who may act for whom, within what bounds? | subject/actor plus constrained grant |
| Authorization | May this exact action execute now? | PDP decision enforced by a PEP |
| Approval | Did an authorized person accept this exact proposal? | bound, expiring, single-use receipt |

---

# 3. Identity is not authorization

Knowing:

```text
agent = procurement-v1
```

does not answer:

```text
May procurement-v1 create a $25,000 purchase order?
```

Authorization may depend on:

- delegating user,
- task,
- department,
- resource,
- vendor,
- amount,
- time,
- risk level,
- approval state.

> **Identity is input to authorization, not a substitute for authorization.**

---

# 4. Preserve the authority chain

A safe enterprise pattern is:

![Identity and authority chain](assets/01-identity-authority-chain.svg)

Each hop should preserve:

- subject/delegator,
- agent identity,
- workload identity,
- task,
- permissions,
- resources,
- limits,
- expiry,
- provenance.

Authority should normally become **narrower downstream**.

---

# 5. Workload identity with SPIFFE / SPIRE

SPIFFE defines standards for portable workload identity.

Core concepts:

- **SPIFFE ID** — workload identity name,
- **SVID** — verifiable identity document,
- **Workload API** — runtime mechanism for workloads to obtain identity.

SPIRE is a maintained CNCF implementation that performs node/workload
attestation and issues SVIDs. A registration entry maps a SPIFFE ID to selectors
that an attestor can verify. The Workload API normally identifies a local caller
through platform evidence such as process and workload metadata; the workload
does not earn an identity merely by submitting a desired SPIFFE ID.

Primary sources:

- https://spiffe.io/docs/latest/spiffe-specs/spiffe/
- https://spiffe.io/docs/latest/spiffe-specs/spiffe_workload_api/
- https://spiffe.io/docs/latest/spire-about/spire-concepts/

A workload identity can prove:

> This request came from the attested procurement-agent workload.

It still does not prove:

> This workload is allowed to spend $25,000.

That second question belongs to authorization.

The current SPIFFE specification set also includes X.509-SVID, JWT-SVID,
federation, Workload Endpoint, Workload API, and newer workload-identity-token
work. Choose X.509-SVID/mTLS when direct workload-to-workload authentication is
the goal; use a JWT-SVID only where its bearer-style and audience semantics fit.
Do not treat either SVID type as a business authorization policy.

---

# 6. Avoid broad human-token forwarding

A common shortcut is:

> Give the agent the user's access token.

Problems:

- excessive scope,
- long lifetime,
- weak attribution,
- unsafe reuse,
- difficult revocation,
- sub-agent leakage,
- confused-deputy risk.

A better pattern derives narrower authority for the agent/task.

![Task-scoped authorization](assets/03-task-scoped-authorization.svg)

---

# 7. OAuth 2.0 Token Exchange — RFC 8693

RFC 8693 defines a Security Token Service pattern for exchanging one token for another and explicitly supports **impersonation and delegation**.

Conceptually:

```text
User token
+
Agent identity
   ↓
Authorization Server / STS
   ↓
Narrow task token
```

A new token can be restricted by:

- audience,
- scope,
- lifetime,
- downstream service,
- actor/subject relationship.

Primary source:

https://datatracker.ietf.org/doc/rfc8693/

The practical lesson is **authority attenuation**: derive less authority than the original principal holds.

That attenuation is an application/authorization-server invariant, not a
guarantee supplied by RFC 8693. The RFC defines the exchange protocol and
actor/subject representation, while token syntax, trust model, revocation
propagation, one-time use, and proof-of-possession policy remain deployment
responsibilities. An exchange does not automatically invalidate its input
tokens or tightly link later revocation to the output token.

Prefer delegation over impersonation when downstream systems must retain the
agent's distinct identity. Impersonation can make the actor indistinguishable
from the subject inside the delegated rights context and weakens attribution.

---

# 8. OAuth security — RFC 9700

RFC 9700 is the current IETF Best Current Practice for OAuth 2.0 Security.

Agent systems should pay particular attention to:

- token leakage,
- audience confusion,
- bearer-token misuse,
- short-lived access,
- secure redirect/client patterns where relevant,
- sender-constrained token strategies where appropriate,
- deprecated/insecure OAuth patterns.

Related stable specifications fill specific gaps:

| Specification | Relevant contribution | What it does not solve |
|---|---|---|
| RFC 8707 | names a target resource during authorization/token requests | resource-level business authorization |
| RFC 8725 | JWT validation best current practices | delegation semantics or revocation |
| RFC 9068 | interoperable JWT access-token profile | proof of possession or narrow business intent by itself |
| RFC 9396 | structured rich authorization details | enforcement, lifecycle, or attenuation by itself |
| RFC 9449 | DPoP sender-constrains OAuth tokens to a key | malware using the key or authorization-policy errors |

For high-value effects, audience/resource restriction and short expiry reduce
exposure but do not replace sender constraint, server-side lifecycle state,
idempotent execution, or outcome verification.

Primary source:

https://datatracker.ietf.org/doc/rfc9700/

---

# 9. Task-scoped authorization

OpenFGA's current guidance includes task-based authorization for agents.

Pattern:

1. agent has no standing permissions,
2. create a task,
3. associate required resource permissions with the task,
4. assign the agent to the task,
5. check access in task context,
6. delete task-related tuples after completion.

For sub-agents, OpenFGA documents two patterns:

- share the task,
- create a **narrower task**.

Primary source:

https://openfga.dev/docs/modeling/agents/task-based-authorization

![Task-scoped authorization](assets/03-task-scoped-authorization.svg)

---

# 10. Delegation envelope

A useful application abstraction is:

![Delegation envelope](assets/02-delegation-envelope.svg)

Example:

```json
{
  "subject": "human:user-123",
  "actor": "agent:procurement-v1",
  "workload": "spiffe://enterprise.example/prod/procurement-agent",
  "task": "task-123",
  "audience": "procurement-api",
  "permissions": ["purchase_order:create"],
  "resources": ["department:data-ai"],
  "constraints": {
    "max_amount_cents": 500000,
    "approved_vendors": ["vendor-acme"],
    "max_calls": 1
  },
  "intent_digest": "sha256-of-approved-task-intent",
  "policy_version": "delegation-policy-2026-09",
  "issued_at": "2026-09-20T12:00:00Z",
  "expires_at": "2026-09-20T12:30:00Z",
  "parent_grant_id": null,
  "depth": 0,
  "max_depth": 1
}
```

This is useful as a mental/application model.

The grant must be derived from trusted application state. Do not accept its
`subject`, `actor`, `workload`, `tenant`, `task`, or policy version from a model
message or tool argument. Validate the signature and header, then independently
check current server-side registration, revocation, task state, and request
context.

For production, use a standards-based identity provider / STS and external authorization system rather than inventing a proprietary security-token protocol.

---

# 11. Sub-agent authority attenuation

Suppose the Procurement Agent can:

```text
vendor:read
purchase_order:create
supplier:email
```

A Research Agent only needs:

```text
vendor:read
```

The child grant should be a **subset across every authority dimension**:

```text
actions_child       ⊆ actions_parent
resources_child     ⊆ resources_parent
vendors_child       ⊆ vendors_parent
amount_child        ≤ amount_parent
calls_child         ≤ calls_parent
expiry_child        ≤ expiry_parent
depth_child         ≤ max_depth_parent
audience transition ∈ explicitly allowed downstream services
subject / tenant / task / intent digest remain bound
```

Changing the logical actor and workload is expected for a sub-agent, but both
must be separately registered and authenticated. A shorter list of actions is
not enough if the child simultaneously widens the resource, vendor, lifetime,
or audience.

Never let delegation accidentally amplify privilege.

---

# 12. OpenFGA

OpenFGA is a fine-grained authorization system inspired by Zanzibar.

Its current documentation includes:

- agents as principals,
- task-based authorization,
- delegated permissions,
- contextual tuples,
- conditions,
- cleanup/revocation after task completion.

Python SDK:

```bash
pip install openfga_sdk
```

Official docs:

- https://openfga.dev/docs/modeling/agents
- https://openfga.dev/docs/modeling/agents/task-based-authorization
- https://openfga.dev/docs/getting-started/install-sdk

OpenFGA is particularly useful for relationship-rich questions:

> Is this agent assigned to this task, and does the task grant access to this resource?

---

# 13. Cedar

Cedar is an authorization policy language designed around:

```text
Principal
Action
Resource
Context
```

It supports fine-grained policy decisions and separates authorization logic from application logic.

Primary sources:

- https://cedarpolicy.com/
- https://docs.cedarpolicy.com/
- https://docs.cedarpolicy.com/auth/authorization.html

Example:

```cedar
permit (
  principal == Agent::"procurement-v1",
  action == Action::"CreatePurchaseOrder",
  resource
)
when {
  context.task == "task-123" &&
  context.amount <= 5000 &&
  context.vendorApproved == true
};
```

---

# 14. Amazon Verified Permissions and AgentCore Policy

Amazon Verified Permissions is a managed authorization service using Cedar.

AgentCore Policy also uses Cedar for runtime agent/tool policy evaluation.

These are useful concrete enterprise examples of:

```text
Agent proposes tool call
  ↓
Policy Enforcement Point
  ↓
Authorization engine
  ↓
ALLOW / DENY
```

Sources:

- https://docs.aws.amazon.com/verifiedpermissions/
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-create-policies.html

---

# 15. Technology landscape and selection

No single library supplies authenticated identity, OAuth delegation, fine-grained
authorization, atomic consumption, revocation, execution, and audit evidence.
Select components by layer and keep one enforcement contract at the side-effect
boundary.

| Technology | Strong fit | Limits / selection test |
|---|---|---|
| SPIFFE/SPIRE | portable workload identity, attestation, rotation, federation | identity foundation, not business authorization; requires control-plane operations |
| OAuth/OIDC authorization server or STS | user sessions, consent, token issuance/exchange | product/profile support varies; confirm RFC 8693 semantics and revocation behavior |
| PyJWT | explicit Python JWT signing and verification | low-level; application owns safe claim/header validation and key lifecycle |
| Authlib | broader OAuth/OIDC client/server protocol support in Python | more machinery; still requires deployment-specific policy and secure configuration |
| OpenFGA + official SDKs | relationships, delegated tasks, resource membership, reverse queries | tuple/model lifecycle and contextual business constraints still need design |
| Cedar / Amazon Verified Permissions | principal/action/resource/context decisions and policy analysis | entity/schema quality, request context, and PEP enforcement remain application responsibilities |
| OPA/Rego | general structured policy across APIs, admission, and workflows | less specialized for graph relationship queries; bundle/cache/failure semantics matter |
| Cloud workload identity | managed cloud-to-cloud identity and short-lived federation | portability and cross-cloud semantics vary; still not task intent |
| OpenTelemetry | correlated identity, policy, grant, operation, and outcome evidence | telemetry is observable evidence, not authorization or non-repudiation by itself |

The repository's reproducible environment validated **Pydantic 2.13.4, PyJWT
2.13.0, cryptography 50.0.0, and OpenFGA Python SDK 0.10.4** on September 20,
2026. PyJWT 2.14.0 was available on PyPI at review time; the course intentionally
uses the repository lock rather than silently changing dependencies. SPIRE
1.15.3 and Cedar CLI 4.13.0 were the latest upstream releases checked during the
same review. Versions are snapshots, not compatibility promises—pin, test, and
review release/security notes in your deployment.

They can be layered.

Example:

```text
OpenFGA:
Is this agent assigned to Task T?

Cedar:
May this assigned agent create this PO for this amount/vendor?

OPA:
Does the wider workflow satisfy enterprise policy?
```

### Selection heuristics

- Start with the existing enterprise identity provider and workload platform;
  do not introduce a novel agent identity protocol without a real gap.
- Choose OpenFGA when relationship traversal and questions such as “what can
  this task see?” dominate.
- Choose Cedar/Verified Permissions when typed principal/action/resource/context
  policy and analyzability dominate.
- Choose OPA when one general policy engine already governs heterogeneous
  infrastructure and application decisions.
- Layer engines only when each owns a documented decision. Define aggregation,
  timeout, cache, version, and fail-closed semantics; two `ALLOW` strings do not
  automatically form one safe authorization.

---

# 16. Technology stack

![Agent identity and authorization technology stack](assets/04-agent-identity-technology-stack.svg)

A mature enterprise stack may combine:

```text
SPIFFE / cloud workload identity
        ↓
OIDC / OAuth 2.0
        ↓
Token exchange / delegation
        ↓
OpenFGA / Cedar / OPA
        ↓
Gateway / enforcement point
        ↓
OpenTelemetry / audit
```

## Enforcement sequence

For a state-changing request, a defensible sequence is:

1. authenticate the human session and workload through their native channels;
2. resolve the logical agent/version and tenant from a governed registry;
3. bind the current task and approved intent;
4. verify token type, exact algorithm, key, issuer, audience/resource, times,
   subject/actor/workload, and authorization details;
5. check current grant registration, lineage, revocation, task state, and policy
   version;
6. evaluate action/resource/context authorization;
7. atomically consume the operation/grant allowance;
8. call an idempotent effect adapter with the same logical operation ID;
9. verify the external outcome and persist a terminal result; and
10. record privacy-minimized evidence without bearer tokens or secrets.

An authorization service outage is not an implicit allow. Define fail-closed
behavior for consequential actions and separately risk-assess any degraded
read-only mode.

---

# 17. Security properties of delegated authority

Good delegated authority should be:

- **narrow** — minimal permissions/resources,
- **short-lived** — minutes rather than months,
- **audience-bound** — usable only by intended service,
- **task-bound** — linked to business intent,
- **revocable** — task completion or incident removes access,
- **non-amplifying** — sub-agent grants are equal or narrower,
- **observable** — every use creates evidence,
- **replay-resistant** where required — sender constraints, idempotency, and server state,
- **atomically consumable** — concurrent checks cannot all spend a one-call grant,
- **lineage-aware** — revoking an ancestor invalidates descendants, and
- **version-bound** — agent and policy changes invalidate stale assumptions.

Do not conflate a token `jti` with an effect idempotency key. The grant identifies
authority; an operation ID identifies one logical side effect across uncertain
retries. A repeated operation with identical arguments may return the saved
result, while the same operation ID with changed arguments must be denied.

---

# 18. Confused-deputy risk

A confused deputy occurs when a component with authority is tricked into using that authority for another principal/resource.

Example:

```text
Finance user
  ↓
Procurement Agent
  ↓
Uses Data & AI procurement grant
  ↓
Attempts Finance purchase
```

Even if the agent is authenticated, the resource/task mismatch must be denied.

---

# 19. Anti-patterns

## Shared superuser service account

Weak attribution and excessive privilege.

## Human-token forwarding

Transfers too much authority.

## Long-lived API keys in prompts/memory

Credential leakage.

## Scope-only authorization

Often too coarse for resource/amount/context rules.

## Child agent inherits parent permissions

Privilege amplification.

## Authorization determined by the LLM

The actor cannot be the sole authority over its own privileges.

## Decode without strict verification

Reading JWT claims without pinning token type, algorithm, issuer, key, audience,
required claims, and time converts attacker-controlled data into apparent
identity.

## Check then increment

Checking a call count and incrementing it in separate operations permits races.
Consume consequential one-use or quota-limited authority in one transaction.

## Successful authorization equals successful effect

An `ALLOW` decision proves only that the request passed the policy point at that
time. It does not prove the external system applied the effect, applied it once,
or applied exactly the requested arguments.

---

# 20. Audit evidence and the limits of non-repudiation

For sensitive actions, preserve:

- subject,
- agent/actor,
- workload,
- task,
- grant ID,
- parent grant,
- token audience,
- authorization model/policy version,
- resource,
- action,
- constraints,
- authorization result,
- expiry,
- approval,
- execution result,
- timestamp.

This enables governance, incident response, and audit.

Preserve an exact request or proposal digest, token digest rather than the raw
bearer token, decision ID and reason codes, identity and policy versions, logical
operation ID, attempt IDs, and the verified external outcome. Protect logs with
access control, retention, integrity monitoring, and clock synchronization.

A signed token and an audit row do **not** automatically establish legal or
technical non-repudiation. The conclusion also depends on key custody,
authentication strength, attribution, log integrity, administrator controls,
time evidence, evidence retention, and the applicable legal/contractual
context. Say precisely what the evidence demonstrates.

---

# 21. Failure lifecycle, revocation, and recovery

Short-lived grants reduce the window of misuse but do not provide immediate
revocation. A production design needs an explicit lifecycle:

```text
requested → issued → active → consumed / expired / revoked / task-closed
                                  ↓
                         descendant grants invalid
```

Plan for:

- human or agent disablement, workload de-registration, agent-version retirement, and key rollover;
- parent revocation and task closure propagating to descendants;
- revocation events delayed or lost between regions;
- cached allow decisions outliving policy or identity state;
- concurrent consumption at multiple enforcement replicas;
- crash after authorization but before result persistence;
- external timeout after an effect may already have happened; and
- reconciliation before retrying an unknown outcome.

Revocation latency is an SLO with a measured population and unit—for example,
time from authoritative revoke commit to denial at every relevant PEP. “We have
a deny list” is not the measurement.

---

# 22. Evaluation and release evidence

The canonical lab evaluates seven labelled cases: two allowed cases (normal and
exact-boundary) and five forbidden/lifecycle cases (amount, vendor, resource,
revoked grant, and closed task). Its metrics are:

| Metric | Population | Numerator | Direction |
|---|---|---|---|
| Decision accuracy | all 7 labelled cases | decisions matching labels | higher is better |
| Forbidden actions allowed | 5 forbidden cases | forbidden cases returning `ALLOW` | zero required |
| False denials | 2 legitimate cases | legitimate cases returning `DENY` | lower is better |
| Concurrent one-call successes | 8 simultaneous unique operations | operations returning `ALLOW` | exactly 1 |

These deterministic tests prove implementation invariants, not production
security effectiveness. A release evaluation should add:

- wrong tenant, actor version, workload binding, trust domain, issuer, key, and policy version;
- tampered, wrong-algorithm, wrong-audience, not-yet-valid, expired, and sender-mismatch tokens;
- altered operation replay, grant replay, revoked ancestors, task closure, and depth exhaustion;
- distributed concurrency, authorization-store outage, stale cache, key rotation, and clock skew;
- allow/deny rates sliced by tenant, action, resource, grant type, agent version, and PEP; and
- verified external outcomes, duplicates, unknown outcomes, cost, and latency.

Report safety violations separately from blocked attempts. A denied attack is a
control success, not a successful attack outcome. Do not average away one
forbidden action behind many easy allowed cases.

---

# 23. State of the art — September 2026 snapshot

## Established practice

- Separate human, application/client, logical service/agent, and workload identity.
- Use short-lived credentials, explicit audience/resource, least privilege, strong OAuth/JWT validation, and external policy enforcement.
- Use SPIFFE/SPIRE or managed workload identity to replace static workload secrets where operationally appropriate.
- Model relationship-rich authorization with systems such as OpenFGA and contextual policy with Cedar/Verified Permissions or OPA.

## Current agent-specific practice

- NIST's February 2026 NCCoE concept paper and AI Agent Standards Initiative frame software/AI-agent identity, authorization, audit, non-repudiation, and prompt-injection questions. The concept paper is exploratory, not a finalized control standard.
- OpenFGA documents agents as principals, task-scoped authority, agent/task binding, expiration/call conditions, sub-agent choices, and tuple cleanup.
- Rich authorization details, token exchange, resource indicators, and sender-constrained access tokens can be composed, but deployment profiles must specify their semantics and enforcement.

## Emerging standards work—do not label as an RFC

The IETF WIMSE working group has active Internet-Drafts for workload identity
architecture, identifiers, credentials, proof tokens, mTLS, HTTP signatures,
and practices. On September 15, 2026, the group adopted
`draft-ietf-wimse-aims-00`, *AI Identity Management System*, replacing the
now-archived `draft-klrc-aiagent-auth`. Other 2026 drafts explore attenuating
tokens, delegation chains, scope aggregation, actor profiles, and agent
consent. Internet-Drafts can change or expire and do not have RFC consensus
status.

## Open problems

- interoperable, multi-hop intent representation and provable monotonic attenuation;
- revocation and status propagation across organizational and agent-to-agent boundaries;
- binding human intent without exposing sensitive prompts or treating model summaries as authority;
- portable proof-of-possession and remote-attestation signals for agents spanning execution environments;
- policy composition when identity, relationship, contextual, tool, and approval engines disagree; and
- evidence semantics that distinguish authorization, attempted execution, actual effect, and user/business outcome.

---

# 24. Practical lab and notebook

[Run the guided notebook](04_agent_identity_and_delegated_authority.ipynb) or
inspect the tested reusable implementation in [`lab.py`](lab.py).

From the repository root:

```bash
make course-04
```

The lab implements:

- agent/user/workload identity contracts,
- signed JWT delegation envelope,
- strict header/signature/issuer/audience/time verification,
- trusted subject/actor-version/workload/tenant/task binding,
- intent-bound action/resource/vendor/amount/call constraints,
- atomic call-limited grants and idempotent operation retry,
- task and lineage revocation,
- multi-dimensional sub-agent authority attenuation,
- OAuth token-exchange request modeling,
- OpenFGA and Cedar architecture examples without pretending to run a live engine,
- concurrency, confused-deputy, tampering, replay, and amplification tests,
- audit evidence,
- explicit evaluation populations and regression tests.

Libraries:

- **Pydantic**
- **PyJWT**
- **cryptography**
- **openfga_sdk**

The default path makes no network calls and needs no identity provider, SPIRE
installation, policy server, cloud account, or API key. Live integrations are
production extensions and must reuse the same invariant tests.

---

# 25. Best practices

- Give agents explicit identities.
- Preserve the human/business delegator.
- Separate logical agent and runtime workload identity.
- Prefer short-lived task authority.
- Scope audience, action, resource, amount, and lifetime.
- Enforce zero standing privilege where practical.
- Revoke authority on task completion.
- Attenuate permissions for sub-agents.
- Keep authorization outside LLM reasoning.
- Test expired, replayed, wrong-audience, wrong-resource, and over-scoped cases.
- Record every delegation and authorization decision.

---

# 26. Primary and official references

1. [NIST — Software and AI Agent Identity and Authorization](https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd)
2. [NIST AI Agent Standards Initiative](https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative)
3. [OpenFGA task-based authorization](https://openfga.dev/docs/modeling/agents/task-based-authorization)
4. [OpenFGA Python SDK](https://openfga.dev/docs/getting-started/install-sdk)
5. [SPIFFE](https://spiffe.io/docs/latest/spiffe-specs/spiffe/)
6. [SPIFFE Workload API](https://spiffe.io/docs/latest/spiffe-specs/spiffe_workload_api/)
7. [SPIRE concepts](https://spiffe.io/docs/latest/spire-about/spire-concepts/)
8. [OAuth 2.0 Token Exchange — RFC 8693](https://datatracker.ietf.org/doc/rfc8693/)
9. [OAuth 2.0 Security BCP — RFC 9700](https://datatracker.ietf.org/doc/rfc9700/)
10. [OAuth 2.0 Resource Indicators — RFC 8707](https://datatracker.ietf.org/doc/rfc8707/)
11. [JSON Web Token Best Current Practices — RFC 8725](https://datatracker.ietf.org/doc/rfc8725/)
12. [JWT Profile for OAuth 2.0 Access Tokens — RFC 9068](https://datatracker.ietf.org/doc/rfc9068/)
13. [OAuth 2.0 Rich Authorization Requests — RFC 9396](https://datatracker.ietf.org/doc/rfc9396/)
14. [OAuth 2.0 Demonstrating Proof of Possession — RFC 9449](https://datatracker.ietf.org/doc/rfc9449/)
15. [IETF WIMSE working group and active documents](https://datatracker.ietf.org/wg/wimse/)
16. [IETF active draft — AI Identity Management System](https://datatracker.ietf.org/doc/draft-ietf-wimse-aims/)
17. [Cedar](https://docs.cedarpolicy.com/)
18. [Cedar security guidance (official documentation source)](https://github.com/cedar-policy/cedar-docs/blob/main/docs/collections/_other/security.md)
19. [Amazon Verified Permissions](https://docs.aws.amazon.com/verifiedpermissions/)
20. [Amazon Bedrock AgentCore Policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html)
21. [OPA policy documentation](https://www.openpolicyagent.org/docs/policy-language)
22. [PyJWT usage and API documentation](https://pyjwt.readthedocs.io/)
23. [OpenFGA Python SDK releases](https://github.com/openfga/python-sdk/releases)
24. [SPIRE releases](https://github.com/spiffe/spire/releases)
25. [Cedar releases](https://github.com/cedar-policy/cedar/releases)

---

# 27. Exercises and review questions

1. Add `supplier:email` to an approved intent and prove that the intent, grant,
   and request must all name it before the PEP allows it.
2. Break one SPIFFE selector. Identify whether failure belongs to identity,
   delegation, authorization, or execution.
3. Add a second child level and prove both depth and ancestor revocation.
4. Replace the in-process lock with SQLite. Design the transaction and crash
   recovery for one-call consumption.
5. Decide whether a real scenario needs OpenFGA, Cedar/OPA, both, or neither;
   identify the owner of each decision and the fail-closed behavior.
6. Map the teaching grant to RFC 9396 authorization details and evaluate DPoP
   or mTLS sender constraint.
7. Add labelled key-rotation, stale-cache, cross-tenant, and unknown-effect
   cases with explicit denominators.

Review questions:

- Why can a cryptographically valid token still be unauthorized?
- What evidence distinguishes a logical agent version from its running workload?
- Which dimensions must attenuate when a sub-agent receives authority?
- Why must call-limit consumption and effect idempotency be separate but coordinated?
- What exactly does an audit decision event prove, and what does it not prove?

---

# 28. Next module

## Module 5 — Fine-Grained Authorization for Agents

Next we go deeper into:

```text
RBAC
  ↓
ABAC
  ↓
ReBAC
  ↓
Task-scoped authorization
  ↓
Contextual policy
  ↓
Runtime enforcement
```
