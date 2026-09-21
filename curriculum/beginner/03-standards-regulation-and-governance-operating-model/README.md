# Module 3 — Standards, Regulation & Governance Operating Model

> **Course:** Enterprise AI Agent Governance: From Principles to Runtime Control  
> **Audience:** AI governance leads, architects, AI engineers, security/privacy teams, legal/compliance partners, model risk teams, internal audit, technical leaders  
> **Recommended duration:** 5–6 hours theory + 3–4 hours practical lab  
> **Scenario:** Enterprise Procurement Agent  
> **Important:** This module is educational and technical. It is **not legal advice**.

---

## Learning objectives

By the end of this module, you should be able to:

1. Explain the different roles of **NIST AI RMF, NIST GenAI Profile, ISO/IEC 42001, ISO/IEC 42005, ISO/IEC 23894, the EU AI Act, OWASP Agentic Security, and NIST OSCAL**.
2. Build an enterprise governance operating model that connects **business ownership, governance, engineering, security/privacy/legal, and assurance**.
3. Create an **AI/agent system inventory** suitable for risk classification and audit.
4. Map standards and regulatory requirements into a reusable **control library**.
5. Build a **RACI / accountability model**.
6. Design **risk-based governance stage gates** rather than one universal approval process.
7. Define **evidence requirements** for each control.
8. Use **change triggers and periodic recertification** to keep governance current.
9. Understand the current 2026 EU AI Act implementation timeline at a high level and separate **legal applicability analysis** from internal engineering controls.
10. Use **OSCAL and compliance-as-code** concepts to make controls more machine-readable, versionable, and auditable.
11. Produce a practical governance package for the Procurement Agent: inventory, applicability profile, control crosswalk, RACI, approval record, exception log, and evidence plan.

> **Core principle:** Standards define expectations. An operating model turns those expectations into ownership, controls, evidence, decisions, and continuous governance.

---

## Module thesis

After this module, a learner should be able to translate external expectations
and internal policy into a versioned inventory, accountable operating model,
claim-bounded control crosswalk, current evidence package, defensible release
decision, and material-change recertification workflow—without confusing an
internal risk tier or framework mapping with legal compliance.

## Prerequisites

- [Module 1 — From AI Governance to Agent Governance](../01-from-ai-governance-to-agent-governance/README.md).
- [Module 2 — Agent Risk Modeling & Autonomy Classification](../02-agent-risk-modeling-and-autonomy-classification/README.md).
- Basic Python, API, risk-register, and software-delivery literacy.
- No legal database, cloud account, GRC platform, model credential, or paid ISO
  text is required for the canonical lab.

## Success criteria

You have completed the module when you can:

- explain what NIST AI RMF, ISO/IEC 42001, ISO/IEC 42005, ISO/IEC 23894,
  ISO/IEC 42006, regulation, OWASP, and OSCAL do—and do not do;
- route a regulatory question without fabricating a legal classification;
- select internal controls from observable system facts and describe mappings as
  `supports`, not `satisfies`;
- bind every accepted evidence item and gate request to the exact system version;
- block one missing required artifact instead of averaging it away; and
- identify which changes require targeted or full recertification.

## Non-goals and boundaries

This course does not provide legal advice, reproduce paid standards, certify an
AIMS, implement a universal control catalog, or authorize a real deployment.
The included controls and thresholds are versioned teaching policy. A production
organization must adapt them to its sector, jurisdictions, risk appetite,
affected people, contractual duties, and authenticated decision authority.

---

## Course audit and claim-to-proof map

This revision retains the standards landscape, three-lines model, inventory, crosswalk, stage gates, RACI, exception, recertification, OSCAL, and procurement scenario. It replaces the notebook-only prototype with one reusable, tested [`lab.py`](lab.py) imported by the notebook.

| Course promise | Executable proof | Negative or evaluation proof |
|---|---|---|
| Legal applicability remains separate from internal risk | `build_applicability_record` routes named specialist reviews and preserves methodology sources | An EU deployment with an incomplete EU AI Act review returns `specialist_review_required` |
| Crosswalks support rather than establish compliance | Every `FrameworkMapping` is source-linked and fixed to the relationship `supports` | `GateDecision` rejects any claim that the internal gate establishes legal compliance |
| Evidence is exact and current | `assess_evidence` binds artifacts to system, version, control requirement, result, age, and validity | Wrong-version, failed, expired, future-dated, and unrequired evidence is rejected with reason codes |
| Accountability is testable | `RACIEntry` requires exactly one accountable role and at least one responsible role | Duplicate or missing activities and ambiguous accountability fail validation |
| One missing critical artifact cannot be averaged away | `evaluate_gate` requires every selected-control evidence item | Removing one of eleven required items blocks the release despite high aggregate completeness |
| Exceptions are bounded | `ExceptionRecord` requires separation of requester and accepter, evidence, compensation, remediation, and expiry | Expired, wrongly bound, unknown, and non-exception-eligible control exceptions fail |
| Material changes trigger scoped recertification | `assess_change` reports exact triggers, scopes, and full-review need | Jurisdiction, authority, and affected-group expansion force full reassessment |
| Machine-readable exchange is honestly scoped | Governance package schema plus `oscal_component_projection` | Projection is labelled non-conformant and requires official OSCAL validation |

The canonical path is deterministic, credential-free, and uses synthetic data. It does not install packages, call a model, make a legal determination, write generated files into the repository, or claim certification.

---

# 1. Why enterprises need an operating model

A governance framework alone does not govern an AI system.

A policy document does not:

- register an agent,
- identify its owner,
- classify its autonomy,
- determine which controls apply,
- collect evidence,
- block a high-risk release,
- assign an exception,
- recertify the system after a material change.

An enterprise operating model translates governance concepts into a **repeatable system of work**.

A practical governance loop is:

```text
Register
  ↓
Classify
  ↓
Assess
  ↓
Select Controls
  ↓
Implement
  ↓
Collect Evidence
  ↓
Approve / Reject / Exception
  ↓
Monitor
  ↓
Reassess / Recertify
```

![Governance lifecycle and stage gates](assets/03-governance-lifecycle-stage-gates.svg)

---

# 2. Standards and regulation solve different problems

Do not treat every framework as interchangeable.

![Standards and regulation landscape](assets/01-standards-regulation-landscape.svg)

## NIST AI Risk Management Framework

NIST AI RMF is a voluntary, cross-sector risk-management framework structured around:

- **GOVERN**
- **MAP**
- **MEASURE**
- **MANAGE**

As of August 2026, NIST states that **AI RMF 1.0 is being revised**.

Use it for:

- risk reasoning,
- governance outcomes,
- lifecycle risk management,
- organizational roles,
- measurement and treatment.

Primary source:

https://www.nist.gov/itl/ai-risk-management-framework

## NIST Generative AI Profile — NIST AI 600-1

Use the GenAI Profile to extend AI RMF with risks and actions that are especially relevant to generative AI.

Primary source:

https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence

## ISO/IEC 42001:2023

ISO/IEC 42001 specifies requirements for establishing, implementing, maintaining, and continually improving an **Artificial Intelligence Management System (AIMS)**.

ISO describes it as an organization-wide management system using a Plan-Do-Check-Act approach.

Use it for:

- governance structure,
- accountability,
- policies/objectives,
- lifecycle processes,
- risk/opportunity management,
- continual improvement,
- management-system assurance.

Primary source:

https://www.iso.org/standard/42001

## ISO/IEC 42005:2025

ISO/IEC 42005 provides guidance for **AI system impact assessment** across the lifecycle, focusing on impacts on individuals, groups, and society.

Use it when a technical risk register is not enough and you need to examine broader impacts.

Primary source:

https://www.iso.org/standard/42005

## ISO/IEC 42006:2025

ISO/IEC 42006 specifies additional requirements for bodies that audit and
certify an ISO/IEC 42001 artificial intelligence management system. It explains
the assurance context for credible AIMS certification, but it does not turn an
internal control mapping or a product test into certification.

Primary source:

https://www.iso.org/standard/42006

## ISO/IEC 23894:2023

ISO/IEC 23894 provides guidance on AI-related risk management.

Use it to integrate AI risk into broader organizational risk-management practices.

Primary source:

https://www.iso.org/standard/77304.html

## OWASP Agentic Security

Use OWASP for practical agentic threat categories, abuse cases, and security controls.

Primary source:

https://genai.owasp.org/initiatives/agentic-security-initiative/

## NIST OSCAL

OSCAL is a NIST-led initiative for machine-readable control-based information using JSON, YAML, and XML.

NIST describes uses including:

- machine-readable control catalogs,
- control baselines,
- system implementation information,
- assessment plans/results,
- automation of control monitoring and assessment.

Primary source:

https://pages.nist.gov/OSCAL/

---

# 3. Current EU AI Act context — September 2026

The EU AI Act is **law**, not merely a best-practice framework.

For an enterprise course, teach two distinct questions:

### Regulatory applicability

- Is the organization a provider, deployer, importer, distributor, or another relevant role?
- Does the system fall into a prohibited, high-risk, transparency, GPAI, or other category?
- Which jurisdiction and dates apply?
- Which documentation, quality, monitoring, transparency, oversight, or conformity obligations apply?

### Internal control implementation

- Which technical and process controls will the organization use to meet those duties?
- What evidence proves the control operates?

Do not confuse the legal classification with the internal risk tier.

## Current high-level timeline

According to the European Commission guidance checked on **20 September 2026**:

- prohibited practices, definitions, and AI literacy provisions have applied since **2 February 2025**;
- governance rules and GPAI obligations became applicable on **2 August 2025**;
- the Act became generally applicable on **2 August 2026**, including enforcement powers and transparency duties for certain AI systems;
- the additional prohibition covering specified non-consensual intimate material and child sexual abuse material applies from **2 December 2026**;
- following the 2026 AI Omnibus, rules for certain high-risk AI systems are scheduled for **2 December 2027**;
- rules for high-risk AI embedded in regulated physical products are scheduled for **2 August 2028**.

The regulatory landscape continues to evolve. The application must store the source and methodology date, route the question to a named specialist, and require a fresh review instead of hard-coding this timeline as legal logic.

Primary sources:

- https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act
- https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- https://digital-strategy.ec.europa.eu/en/policies/enforcement-ai-act
- https://digital-strategy.ec.europa.eu/en/policies/ai-act-standardisation

### Practical lesson

A governance system needs to store:

```text
internal risk tier
+
regulatory applicability
+
standards/control profile
```

as separate but connected fields.

---

# 4. Build a governance operating model, not a governance committee

A scalable operating model has clear layers.

![Governance operating model](assets/02-governance-operating-model.svg)

## Board / executive accountability

Responsibilities:

- define AI risk appetite,
- approve major policy,
- assign accountable executives,
- approve material exceptions.

## AI governance function

Responsibilities:

- maintain AI policy,
- define risk methodology,
- maintain control library,
- manage inventory,
- coordinate governance decisions,
- maintain evidence requirements.

## Business / product owner

Responsibilities:

- own purpose and business outcome,
- identify affected users,
- accept business risk,
- fund controls,
- maintain use-case validity.

## AI engineering / platform

Responsibilities:

- implement architecture and controls,
- maintain technical evidence,
- instrument monitoring,
- manage models/tools/data.

## Security / privacy / legal / compliance

Responsibilities vary by system:

- security threat modeling,
- privacy assessment,
- regulatory interpretation,
- data governance,
- contractual/supplier controls.

## Independent assurance / audit

Responsibilities:

- independently evaluate process/control effectiveness,
- test evidence,
- challenge assumptions,
- support certification or audit.

---

# 5. Three lines of accountability — adapted pragmatically

Many enterprises use a three-lines model.

A practical AI interpretation:

### First line — builders and owners

They own and operate the system.

They do **not** outsource risk ownership to the governance team.

### Second line — governance, risk, security, privacy, compliance

They define/challenge policy and risk expectations, provide specialist oversight, and monitor adherence.

### Third line — internal audit / independent assurance

They independently assess whether governance and controls work as intended.

Avoid one common failure:

> The AI governance team becomes the owner of every AI risk.

That weakens accountability.

---

# 6. The AI / Agent System Inventory

You cannot govern what you cannot identify.

An enterprise inventory should capture more than:

```text
Name: Procurement Agent
Model: GPT-X
```

Recommended fields:

## Ownership

- system ID
- business owner
- technical owner
- governance owner
- support team

## Purpose

- intended use
- users
- affected parties
- prohibited/out-of-scope use

## Technical architecture

- models
- agent framework
- retrieval sources
- memory
- tools/APIs
- sub-agents
- deployment environment

## Authority

- autonomy level
- agent identity
- delegated authority
- write capabilities
- financial limits
- human approval requirements

## Data

- data classifications
- personal/sensitive data
- data residency
- external transfers

## Risk

- internal risk tier
- impact assessment
- threat model
- residual risk

## Regulation

- jurisdictions
- organization role
- AI Act applicability
- sector obligations

## Lifecycle

- version
- approval status
- approval date
- next review
- material-change triggers
- incidents/exceptions

---

# 7. Control libraries

A control library turns abstract requirements into reusable expectations.

Example:

```yaml
control_id: AG-AUTH-001
title: Runtime authorization for state-changing tools
objective: >
  Prevent an agent from executing a state-changing capability
  outside delegated authority.
applies_when:
  - agent_can_mutate_state
implementation_examples:
  - policy_engine
  - task_scoped_authorization
evidence:
  - policy_test_results
  - denied_action_trace
owner: security_architecture
```

A mature control should define:

- stable ID,
- objective,
- applicability,
- implementation guidance,
- test method,
- evidence,
- frequency,
- owner,
- mapped standards/regulations.

---

# 8. Control crosswalks

Crosswalks reduce duplicate work.

One internal control may support several frameworks.

Example:

| Internal control | NIST AI RMF | ISO 42001 theme | EU AI Act concern |
|---|---|---|---|
| Agent inventory | GOVERN | Context / system governance | documentation / role identification |
| Risk assessment | MAP/MANAGE | risk management | risk-management obligations |
| Human oversight | GOVERN/MANAGE | operational control | human oversight |
| Traceability | MEASURE | monitoring/evidence | record keeping |
| Runtime authorization | MANAGE | operational control | security / control effectiveness |

**Important:** A crosswalk is an engineering/governance aid. It is not a legal opinion that one control automatically establishes regulatory compliance.

---

# 9. Governance stage gates

Do not use one approval process for every AI system.

Suggested lifecycle:

## Gate 0 — Intake

Minimum:

- owner,
- purpose,
- architecture sketch,
- initial autonomy.

## Gate 1 — Classification

Determine:

- internal risk tier,
- impact-assessment need,
- regulatory review need,
- agent/autonomy profile.

## Gate 2 — Design review

Validate:

- control architecture,
- security/privacy design,
- human oversight,
- data/tool boundaries.

## Gate 3 — Pre-production assurance

Require:

- evaluation results,
- policy tests,
- security tests,
- evidence completeness,
- open-risk acceptance.

## Gate 4 — Production approval

Decision:

```text
APPROVE
APPROVE_WITH_CONDITIONS
REJECT
EXCEPTION_REQUIRED
```

## Gate 5 — Ongoing governance

Monitor:

- incidents,
- policy violations,
- drift,
- autonomy,
- cost,
- security findings,
- control failures.

---

# 10. RACI for agent governance

A RACI prevents invisible ownership gaps.

Example:

| Activity | Business Owner | AI Eng | AI Governance | Security | Legal/Privacy | Audit |
|---|---|---|---|---|---|---|
| Define purpose | A/R | C | C | I | C | I |
| Architecture | C | A/R | C | C | I | I |
| Risk classification | A | C | R | C | C | I |
| Security threat model | I | C | C | A/R | I | I |
| Production approval | A | C | R | C | C | I |
| Runtime monitoring | A | R | C | C | I | I |
| Independent assurance | I | I | I | I | I | A/R |

Tailor this to organizational structure.

---

# 11. Exceptions and risk acceptance

Not every control gap blocks deployment.

But exceptions must be explicit.

An exception should contain:

- missing control,
- rationale,
- risk,
- compensating control,
- accountable risk accepter,
- expiration date,
- remediation plan,
- evidence,
- review trigger.

Never allow:

```text
“temporary exception”
```

to silently become permanent architecture.

---

# 12. Change management and recertification

A system may remain approved while its risk changes underneath it.

Material-change triggers can include:

- new model,
- materially different model version,
- new tool/API,
- new data class,
- new country/jurisdiction,
- new autonomy,
- new memory,
- new agent delegation,
- higher transaction limit,
- new affected user population,
- major incident,
- material evaluation regression.

Use risk-based reassessment:

```text
Small change → targeted regression
Major capability change → partial/full recertification
```

---

# 13. Evidence as a first-class artifact

A control without evidence is difficult to assure.

Evidence examples:

### Design evidence

- architecture,
- data-flow diagram,
- threat model,
- impact assessment.

### Implementation evidence

- policy files,
- IaC configuration,
- access-control model,
- tool registry.

### Test evidence

- evaluation report,
- red-team findings,
- policy tests,
- authorization tests.

### Runtime evidence

- traces,
- policy decisions,
- approval records,
- incidents,
- monitoring metrics.

### Governance evidence

- approval decision,
- exceptions,
- RACI,
- control attestations,
- recertification record.

---

# 14. Governance-as-code and OSCAL

![Compliance-as-code evidence flow](assets/04-compliance-as-code-evidence.svg)

NIST OSCAL provides machine-readable formats for control catalogs, profiles, implementation descriptions, and assessment information.

It is especially relevant when governance content currently lives across:

- spreadsheets,
- Word documents,
- tickets,
- wikis,
- email approvals.

OSCAL can help create a standards-based representation that tools can exchange.

## Compliance Trestle

The OSCAL Compass **compliance-trestle** project is an actively developed open-source compliance-as-code platform. As of the course snapshot, its current release is **v5.1.0** and its documentation reports OSCAL 1.2.1 support; NIST's current OSCAL patch release is **v1.2.3**. Version-pin the selected toolchain, test compatibility, and review security advisories before resolving remote or untrusted OSCAL imports.

Project:

https://github.com/oscal-compass/compliance-trestle

Install:

```bash
pip install "compliance-trestle>=5,<6"
```

Trestle is useful for:

- OSCAL document management,
- schema validation,
- human-friendly Markdown authoring,
- Git workflows,
- CI/CD integration.

### Important

Do not force every AI governance concept directly into a security-control schema.

Use OSCAL where structured control/evidence exchange adds value, while maintaining AI-specific inventory and risk metadata where needed.

---

# 15. Governance metrics

Useful operating-model metrics include:

## Inventory

- % systems registered,
- % with named owner,
- % with current risk tier.

## Review efficiency

- median time to approval,
- backlog,
- % requiring rework.

## Control health

- evidence completeness,
- overdue tests,
- open high-risk findings,
- exception age.

## Runtime governance

- policy violations,
- escalations,
- unauthorized action attempts,
- autonomy rate,
- incidents.

## Recertification

- overdue reviews / approved systems due for review,
- systems changed without reassessment / materially changed systems,
- expired exceptions / open exceptions.

Every metric needs a named population, numerator, denominator, unit, time
window, direction, owner, and decision it informs. For example:

```text
current evidence rate
= current passing required evidence items
  / all required evidence items for the selected cohort and profile version
```

Do not combine design documents, passing tests, runtime observations, and failed
artifacts into an unexplained “evidence score.” Keep counts and failure reasons
visible.

Avoid optimizing only for:

> “number of approved AI use cases.”

Fast approval with weak evidence is not mature governance.

---

# 16. Practical enterprise scenario

For the Procurement Agent, the module produces:

1. system inventory record,
2. owner/RACI,
3. autonomy and internal risk tier,
4. simplified regulatory applicability record,
5. control profile,
6. framework crosswalk,
7. evidence plan,
8. gate decision,
9. exception record,
10. recertification triggers.

The practical notebook implements these artifacts as structured data.

---

# 17. Practical lab and notebook

Notebook:

[`03_standards_regulation_and_governance_operating_model.ipynb`](03_standards_regulation_and_governance_operating_model.ipynb)

Canonical tools:

- **Pydantic** — immutable, typed inventory, controls, reviews, evidence, RACI, gate, exception, change, and package contracts.
- **jsonschema** — machine-readable governance-package validation.
- **OSCAL 1.2.3 concepts** — a deliberately non-conformant teaching projection that learners can promote to an officially validated component definition.
- **Compliance Trestle 5.x** — optional production extension for Git/CI-oriented OSCAL workflows.

The course intentionally does not need an LLM SDK. Structured extraction may assist intake in production, but a human owner must verify every resulting governance field.

The notebook imports [`lab.py`](lab.py) and demonstrates:

- AI inventory,
- specialist applicability-review router,
- RACI,
- control library,
- standard/regulatory crosswalk,
- stage-gate decision,
- exception process,
- material-change detector,
- exact evidence requirement populations rather than one completeness average,
- machine-readable package validation and an honestly labelled OSCAL projection,
- five labelled governance-gate cases with an explicit denominator.

Run the focused course gate:

```bash
make course-03
```

Production upgrades include persistent identity and workflow state, signed evidence provenance, official OSCAL schema validation, GRC and ticket integrations, retention/access controls, notification and appeal workflows, and organization-specific legal and assurance review.

## 17.1 Technology and method landscape

| Need | Common method or tool | Strength | Limitation / selection criterion |
|---|---|---|---|
| Enterprise AI risk outcomes | NIST AI RMF 1.0 and Playbook | Flexible, rights-preserving, cross-sector lifecycle | AI RMF 1.0 is under revision; pin profiles, mappings, and methodology dates |
| AI management system | ISO/IEC 42001:2023 | Organization-wide AIMS and continual improvement | Certification is scope-specific and does not establish product safety |
| Risk and impact | ISO/IEC 23894:2023; ISO/IEC 42005:2025 | Integrates AI risk and lifecycle effects on people and society | Requires organization-specific context and stakeholder evidence |
| Assurance | IIA Three Lines; RACI/RASCI; ISO/IEC 42006:2025 | Separates ownership, challenge, and independent assurance | A matrix cannot prove real authority, competence, or independence |
| Agent security | OWASP Agentic Top 10 2026; MITRE ATLAS; NIST AI 100-2 | Current threat language and test ideas | A taxonomy mapping is not evidence that a control operates |
| Structured contracts | Pydantic; JSON Schema | Typed, versioned, testable governance artifacts | Schema-valid content can still be false, stale, or unauthorized |
| Control exchange | OSCAL 1.2.3; Compliance Trestle 5.x | Machine-readable catalog, profile, implementation, and assessment workflows | Model/tool versions differ; validate against the selected official schema |
| Enterprise workflow | GRC/IRM and AI-governance platforms | Portfolio inventory, workflow, attestations, issues, dashboards | Prefer exportability, APIs, evidence provenance, identity integration, and version binding over lock-in |
| Delivery integration | Git, CI/CD, artifact stores, ticketing, policy services | Generates evidence close to engineering work | CI success alone is neither production approval nor legal compliance |

Use the smallest stack that preserves authority, provenance, and lifecycle
state. A spreadsheet can support discovery workshops; a registry and workflow
engine are usually necessary once multiple teams, versions, jurisdictions, and
recertification events must be coordinated.

---

# 18. Best practices

- Separate **legal applicability** from internal risk classification.
- Store both in the governance record.
- Make the business owner accountable for purpose and risk.
- Reuse controls through a central library.
- Use specialist reviews only when triggered by risk.
- Keep control evidence versioned.
- Make exceptions expire.
- Trigger reassessment on material change.
- Move from documents toward structured governance artifacts.
- Treat regulation as changing input: verify dates and guidance continuously.
- Do not claim that a framework mapping automatically equals legal compliance.

---

# 19. Anti-patterns

## Framework shopping

> “Which one framework covers everything?”

None does.

## Spreadsheet-only governance

Works at small scale; becomes difficult to version, crosswalk, and audit.

## Governance owns the product risk

Business/system owners should remain accountable.

## Same approval for every system

Creates both bottlenecks and under-governance.

## Evidence collected at audit time

Evidence should be produced by engineering and runtime processes continuously.

## Permanent exceptions

Every exception needs owner, expiration, and remediation.

## Regulation hard-coded forever

Regulatory dates, standards, and guidance evolve.

---

# 20. State of the art — September 2026 snapshot

## Established practice

The durable foundation is not agent-specific: management systems, enterprise
risk management, impact assessment, Three Lines accountability, separation of
duties, internal controls, evidence retention, audit, change management, and
incident response. NIST AI RMF 1.0 remains a widely used voluntary structure,
while NIST states that it is being revised. ISO/IEC 42001:2023 supplies the AIMS
requirements; ISO/IEC 23894:2023 and ISO/IEC 42005:2025 deepen risk and impact;
ISO/IEC 42006:2025 addresses bodies auditing and certifying an AIMS.

## Current implementation direction

Organizations are moving from document-only assessments toward versioned system
inventories, reusable control libraries, policy-linked delivery gates, evidence
APIs, continuous control monitoring, and machine-readable exchange. NIST OSCAL
1.2.3 is the current official release at this snapshot. Compliance Trestle's v5
line is actively developed, while its documented OSCAL compatibility must be
checked against the chosen NIST release rather than assumed.

The EU AI Act is now in its staged application and enforcement period. The 2026
AI Omnibus changed dates and some duties, illustrating why regulatory content
needs source snapshots, effective dates, named owners, and recertification—not
hard-coded notebook logic. OWASP's 2026 agentic work adds a practical security
layer for systems that plan, call tools, use memory, and delegate.

## Research frontier and open problems

Open problems include interoperable AI inventory schemas, trustworthy exchange
of control evidence across organizations, automated change-impact analysis,
authorization of governance actions themselves, evidence freshness semantics,
assurance of adaptive and multi-agent systems, mapping control effectiveness to
real-world outcomes, and measuring governance latency without rewarding weak
review. Automated regulatory reasoning remains especially sensitive: tools may
retrieve and route sources, but accountable specialists must own interpretation.

---

# 21. Primary references

## NIST

- AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- AI Resource Center: https://airc.nist.gov/
- AI RMF crosswalks: https://airc.nist.gov/airmf-resources/crosswalks/
- GenAI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- OSCAL: https://pages.nist.gov/OSCAL/

## ISO

- ISO/IEC 42001:2023: https://www.iso.org/standard/42001
- ISO/IEC 42005:2025: https://www.iso.org/standard/42005
- ISO/IEC 42006:2025: https://www.iso.org/standard/42006
- ISO/IEC 23894:2023: https://www.iso.org/standard/77304.html

## EU

- AI Act navigation FAQ: https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act
- AI Act overview/timeline: https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- Enforcement: https://digital-strategy.ec.europa.eu/en/policies/enforcement-ai-act
- Standardisation: https://digital-strategy.ec.europa.eu/en/policies/ai-act-standardisation

## Agent security

- OWASP Agentic Security Initiative: https://genai.owasp.org/initiatives/agentic-security-initiative/
- OWASP Top 10 for Agentic Applications 2026: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- NIST AI 100-2e2025 adversarial ML taxonomy: https://csrc.nist.gov/pubs/ai/100/2/e2025/final
- MITRE ATLAS: https://atlas.mitre.org/

## Compliance-as-code

- OSCAL: https://pages.nist.gov/OSCAL/
- OSCAL v1.2.3 release note: https://pages.nist.gov/OSCAL/about/blog/
- Compliance Trestle: https://github.com/oscal-compass/compliance-trestle
- Compliance Trestle releases: https://github.com/oscal-compass/compliance-trestle/releases

## Accountability

- IIA Statements of Position / Three Lines: https://www.theiia.org/en/resources/statements-of-position

---

# 22. Next module

## Module 4 — Agent Identity & Delegated Authority

The next module moves from governance organization to technical identity:

```text
Human identity
  ↓
Delegated authority
  ↓
Agent identity
  ↓
Task scope
  ↓
Resource/tool access
  ↓
Revocation + audit
```
