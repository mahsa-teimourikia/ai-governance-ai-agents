"""Evidence-bound governance operating model for Course 3.

The module is intentionally deterministic and credential-free.  It demonstrates
how a trusted application can route specialist reviews, select internal controls,
validate scoped evidence, and make an internal release-gate decision.  It does
not make legal determinations or claim certification/compliance.
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum, IntEnum
import hashlib
import json
from typing import Iterable, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTROL_PROFILE_VERSION = "agent-governance-controls-2026-09"
METHODOLOGY_SNAPSHOT = date(2026, 9, 20)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RiskTier(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class AutonomyLevel(IntEnum):
    INFORMATIONAL = 0
    ASSISTED = 1
    BOUNDED = 2
    HIGH = 3


class LifecycleStatus(str, Enum):
    DRAFT = "draft"
    ASSESSMENT = "assessment"
    APPROVED = "approved"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class EvidenceResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class ReviewDomain(str, Enum):
    SECURITY = "security"
    PRIVACY = "privacy"
    IMPACT_ASSESSMENT = "impact_assessment"
    EU_AI_ACT = "eu_ai_act"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class GateOutcome(str, Enum):
    APPROVED_INTERNAL_RELEASE = "approved_internal_release"
    BLOCKED = "blocked"
    SPECIALIST_REVIEW_REQUIRED = "specialist_review_required"


class ChangeTrigger(str, Enum):
    MODEL = "model_change"
    CAPABILITY = "capability_change"
    DATA = "data_scope_change"
    AUTONOMY = "autonomy_change"
    MEMORY = "memory_change"
    DELEGATION = "delegation_change"
    JURISDICTION = "jurisdiction_change"
    TRANSACTION_LIMIT = "transaction_limit_change"
    AFFECTED_GROUP = "affected_group_change"


class Capability(FrozenModel):
    capability_id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    description: str = Field(min_length=1)
    mutates_state: bool
    external_communication: bool = False
    privileged_access: bool = False
    irreversible: bool = False
    financial_limit_usd: int = Field(default=0, ge=0)


class AgentSystemRecord(FrozenModel):
    system_id: str = Field(pattern=r"^SYS-[A-Z0-9-]+$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    intended_use: tuple[str, ...]
    prohibited_use: tuple[str, ...]
    business_owner: str = Field(min_length=1)
    technical_owner: str = Field(min_length=1)
    autonomy: AutonomyLevel
    internal_risk_tier: RiskTier
    model_ids: tuple[str, ...]
    capabilities: tuple[Capability, ...]
    data_classes: frozenset[str]
    jurisdictions: frozenset[str]
    affected_groups: tuple[str, ...]
    memory_enabled: bool = False
    subagents_enabled: bool = False
    status: LifecycleStatus = LifecycleStatus.ASSESSMENT

    @model_validator(mode="after")
    def inventory_is_usable(self) -> "AgentSystemRecord":
        if not self.intended_use or not self.prohibited_use:
            raise ValueError("inventory requires intended and prohibited uses")
        if not self.model_ids:
            raise ValueError("inventory requires at least one model identifier")
        if not self.capabilities:
            raise ValueError("inventory requires at least one capability")
        capability_ids = [item.capability_id for item in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("capability identifiers must be unique")
        if not self.jurisdictions:
            raise ValueError("inventory requires at least one jurisdiction")
        return self


def stable_digest(value: object) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def system_digest(system: AgentSystemRecord) -> str:
    return stable_digest(system)


class FrameworkMapping(FrozenModel):
    framework: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    relationship: str = Field(default="supports", pattern=r"^supports$")
    source_url: str = Field(pattern=r"^https://")


class EvidenceRequirement(FrozenModel):
    requirement_id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    description: str = Field(min_length=1)
    maximum_age_days: int = Field(gt=0, le=730)


class Control(FrozenModel):
    control_id: str = Field(pattern=r"^AG-[A-Z]+-[0-9]{3}$")
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    all_of_tags: frozenset[str]
    evidence_requirements: tuple[EvidenceRequirement, ...]
    owner_role: str = Field(min_length=1)
    exception_eligible: bool
    mappings: tuple[FrameworkMapping, ...]

    @model_validator(mode="after")
    def evidence_requirements_are_unique(self) -> "Control":
        requirement_ids = [item.requirement_id for item in self.evidence_requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("evidence requirement identifiers must be unique per control")
        return self


def system_tags(system: AgentSystemRecord) -> frozenset[str]:
    tags = {"all_ai_systems"}
    if system.autonomy >= AutonomyLevel.ASSISTED:
        tags.add("agentic_system")
    if any(item.mutates_state for item in system.capabilities):
        tags.add("state_changing")
    if any(item.external_communication for item in system.capabilities):
        tags.add("external_communication")
    if any(item.privileged_access for item in system.capabilities):
        tags.add("privileged_access")
    if any(item.financial_limit_usd > 0 for item in system.capabilities):
        tags.add("financial_action")
    if system.internal_risk_tier >= RiskTier.HIGH:
        tags.add("high_risk")
    if system.memory_enabled:
        tags.add("memory")
    if system.subagents_enabled:
        tags.add("delegation")
    if system.data_classes & {"personal", "sensitive", "regulated"}:
        tags.add("sensitive_data")
    return frozenset(tags)


def _mapping(framework: str, reference: str, source_url: str) -> FrameworkMapping:
    return FrameworkMapping(framework=framework, reference=reference, source_url=source_url)


def control_library() -> tuple[Control, ...]:
    nist = "https://www.nist.gov/itl/ai-risk-management-framework"
    iso_42001 = "https://www.iso.org/standard/42001"
    iso_42005 = "https://www.iso.org/standard/42005"
    owasp = "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"
    return (
        Control(
            control_id="AG-INV-001",
            title="Versioned AI system inventory",
            objective="Maintain purpose, ownership, scope, architecture, capabilities, data, and lifecycle state.",
            all_of_tags=frozenset({"all_ai_systems"}),
            evidence_requirements=(
                EvidenceRequirement(requirement_id="owner_attestation", description="Owner attests the current intended use and boundaries.", maximum_age_days=180),
                EvidenceRequirement(requirement_id="architecture_record", description="Architecture record matches the assessed system version.", maximum_age_days=180),
            ),
            owner_role="AI Governance",
            exception_eligible=False,
            mappings=(
                _mapping("NIST AI RMF 1.0", "GOVERN and MAP outcomes", nist),
                _mapping("ISO/IEC 42001:2023", "AIMS context, roles, planning, and operation", iso_42001),
            ),
        ),
        Control(
            control_id="AG-RSK-001",
            title="Agent risk and impact assessment",
            objective="Document operational, adversarial, human, organizational, and societal impacts and treatments.",
            all_of_tags=frozenset({"agentic_system"}),
            evidence_requirements=(
                EvidenceRequirement(requirement_id="risk_assessment", description="Current inherent/residual risk assessment.", maximum_age_days=120),
                EvidenceRequirement(requirement_id="impact_screen", description="Impact-assessment routing and affected-group record.", maximum_age_days=120),
            ),
            owner_role="Business Owner",
            exception_eligible=False,
            mappings=(
                _mapping("NIST AI RMF 1.0", "MAP, MEASURE, and MANAGE outcomes", nist),
                _mapping("ISO/IEC 42005:2025", "AI system impact assessment", iso_42005),
            ),
        ),
        Control(
            control_id="AG-AUTH-001",
            title="Runtime authorization for state change",
            objective="Prevent actions outside authenticated and delegated authority at the tool boundary.",
            all_of_tags=frozenset({"state_changing"}),
            evidence_requirements=(
                EvidenceRequirement(requirement_id="authorization_tests", description="Allow/deny tests cover action, resource, tenant, and limits.", maximum_age_days=90),
                EvidenceRequirement(requirement_id="denied_action_trace", description="A trace demonstrates a forbidden action was blocked.", maximum_age_days=90),
            ),
            owner_role="Security Architecture",
            exception_eligible=False,
            mappings=(
                _mapping("NIST AI RMF 1.0", "MANAGE outcomes", nist),
                _mapping("OWASP Agentic Top 10 2026", "Tool misuse and identity/privilege abuse", owasp),
            ),
        ),
        Control(
            control_id="AG-HUM-001",
            title="Risk-based human oversight",
            objective="Bind material or irreversible actions to authorized, informed, reviewable human decisions.",
            all_of_tags=frozenset({"high_risk"}),
            evidence_requirements=(
                EvidenceRequirement(requirement_id="approval_integrity_tests", description="Altered, expired, and replayed approvals fail closed.", maximum_age_days=90),
                EvidenceRequirement(requirement_id="oversight_runbook", description="Named operators can pause, escalate, and recover the system.", maximum_age_days=180),
            ),
            owner_role="Business Owner",
            exception_eligible=False,
            mappings=(
                _mapping("NIST AI RMF 1.0", "GOVERN and MANAGE outcomes", nist),
                _mapping("ISO/IEC 42001:2023", "Operational control and human oversight", iso_42001),
            ),
        ),
        Control(
            control_id="AG-OBS-001",
            title="Governance traceability",
            objective="Reconstruct system version, policy decision, evidence, actions, outcomes, and terminal state.",
            all_of_tags=frozenset({"agentic_system"}),
            evidence_requirements=(
                EvidenceRequirement(requirement_id="trace_sample", description="Trace sample contains required identifiers and reason codes.", maximum_age_days=30),
                EvidenceRequirement(requirement_id="retention_policy", description="Retention and access rules cover governance evidence.", maximum_age_days=365),
            ),
            owner_role="AI Platform",
            exception_eligible=True,
            mappings=(
                _mapping("NIST AI RMF 1.0", "MEASURE and MANAGE outcomes", nist),
                _mapping("ISO/IEC 42001:2023", "Monitoring, measurement, and documented information", iso_42001),
            ),
        ),
        Control(
            control_id="AG-ASR-001",
            title="Independent high-risk assurance",
            objective="Provide objective challenge of high-risk evidence and unresolved findings before release.",
            all_of_tags=frozenset({"high_risk"}),
            evidence_requirements=(
                EvidenceRequirement(requirement_id="independent_assurance_report", description="Independent review records scope, tests, findings, and disposition.", maximum_age_days=120),
            ),
            owner_role="Independent Assurance",
            exception_eligible=False,
            mappings=(
                _mapping("ISO/IEC 42001:2023", "Internal audit and management review", iso_42001),
                _mapping("ISO/IEC 42006:2025", "AIMS audit and certification-body context", "https://www.iso.org/standard/42006"),
            ),
        ),
    )


def select_controls(system: AgentSystemRecord, library: Iterable[Control]) -> tuple[Control, ...]:
    tags = system_tags(system)
    selected = [control for control in library if control.all_of_tags.issubset(tags)]
    return tuple(sorted(selected, key=lambda item: item.control_id))


class SpecialistReview(FrozenModel):
    domain: ReviewDomain
    status: ReviewStatus
    reviewer: str | None = None
    basis_refs: tuple[str, ...]
    notes: tuple[str, ...]

    @model_validator(mode="after")
    def completed_review_has_reviewer(self) -> "SpecialistReview":
        if not self.basis_refs:
            raise ValueError("a specialist review requires at least one basis reference")
        if self.status is ReviewStatus.COMPLETED and not self.reviewer:
            raise ValueError("a completed specialist review requires a reviewer")
        if self.status is ReviewStatus.PENDING and self.reviewer:
            raise ValueError("a pending specialist review cannot name a completing reviewer")
        return self


class ApplicabilityRecord(FrozenModel):
    record_id: str = Field(pattern=r"^APP-[A-Z0-9-]+$")
    system_id: str
    system_version: str
    methodology_snapshot: date
    valid_until: date
    reviews: tuple[SpecialistReview, ...]
    disclaimer: str = "Routing record only; it does not constitute legal advice or a legal classification."

    @model_validator(mode="after")
    def review_set_is_bounded(self) -> "ApplicabilityRecord":
        if self.valid_until < self.methodology_snapshot:
            raise ValueError("applicability validity cannot precede its methodology snapshot")
        domains = [item.domain for item in self.reviews]
        if len(domains) != len(set(domains)):
            raise ValueError("applicability review domains must be unique")
        return self

def required_review_domains(system: AgentSystemRecord) -> tuple[ReviewDomain, ...]:
    domains: set[ReviewDomain] = set()
    tags = system_tags(system)
    if tags & {"state_changing", "privileged_access", "external_communication", "memory", "delegation"}:
        domains.add(ReviewDomain.SECURITY)
    if "sensitive_data" in tags:
        domains.add(ReviewDomain.PRIVACY)
    if system.internal_risk_tier >= RiskTier.HIGH or system.affected_groups:
        domains.add(ReviewDomain.IMPACT_ASSESSMENT)
    if "EU" in system.jurisdictions:
        domains.add(ReviewDomain.EU_AI_ACT)
    return tuple(sorted(domains, key=lambda item: item.value))


def build_applicability_record(
    system: AgentSystemRecord,
    *,
    completed_by: Mapping[ReviewDomain, str],
    as_of: date,
) -> ApplicabilityRecord:
    source_by_domain = {
        ReviewDomain.SECURITY: ("https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/",),
        ReviewDomain.PRIVACY: ("organization privacy policy and applicable privacy law",),
        ReviewDomain.IMPACT_ASSESSMENT: ("https://www.iso.org/standard/42005",),
        ReviewDomain.EU_AI_ACT: ("https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",),
    }
    reviews: list[SpecialistReview] = []
    for domain in required_review_domains(system):
        reviewer = completed_by.get(domain)
        reviews.append(
            SpecialistReview(
                domain=domain,
                status=ReviewStatus.COMPLETED if reviewer else ReviewStatus.PENDING,
                reviewer=reviewer,
                basis_refs=source_by_domain[domain],
                notes=(
                    "Application code routes the question; the named specialist owns interpretation and conclusion.",
                ),
            )
        )
    return ApplicabilityRecord(
        record_id=f"APP-{system.system_id.removeprefix('SYS-')}-{system.version.replace('.', '-')}",
        system_id=system.system_id,
        system_version=system.version,
        methodology_snapshot=as_of,
        valid_until=as_of + timedelta(days=90),
        reviews=tuple(reviews),
    )


def pending_review_domains(record: ApplicabilityRecord) -> tuple[ReviewDomain, ...]:
    return tuple(item.domain for item in record.reviews if item.status is ReviewStatus.PENDING)


class EvidenceItem(FrozenModel):
    evidence_id: str = Field(pattern=r"^EV-[A-Z0-9-]+$")
    system_id: str
    system_version: str
    control_id: str
    requirement_id: str
    result: EvidenceResult
    artifact_uri: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    produced_on: date
    valid_until: date
    producer: str = Field(min_length=1)
    environment: str = Field(min_length=1)

    @model_validator(mode="after")
    def validity_window_is_ordered(self) -> "EvidenceItem":
        if self.valid_until < self.produced_on:
            raise ValueError("valid_until cannot precede produced_on")
        return self


class EvidenceAssessment(FrozenModel):
    system_id: str
    system_version: str
    control_profile_version: str
    assessed_on: date
    required_requirement_keys: tuple[str, ...]
    required_count: int
    satisfied_count: int
    missing_requirements: tuple[str, ...]
    rejected_evidence: tuple[str, ...]
    accepted_evidence_ids: tuple[str, ...]

    @model_validator(mode="after")
    def counts_match_requirement_population(self) -> "EvidenceAssessment":
        if len(self.required_requirement_keys) != len(set(self.required_requirement_keys)):
            raise ValueError("required evidence keys must be unique")
        if self.required_count != len(self.required_requirement_keys):
            raise ValueError("required_count must match the named requirement population")
        if not set(self.missing_requirements).issubset(self.required_requirement_keys):
            raise ValueError("missing requirements must belong to the named population")
        if self.satisfied_count != self.required_count - len(set(self.missing_requirements)):
            raise ValueError("satisfied_count must match the exact missing requirement set")
        if len(self.accepted_evidence_ids) != len(set(self.accepted_evidence_ids)):
            raise ValueError("accepted evidence identifiers must be unique")
        return self


def assess_evidence(
    system: AgentSystemRecord,
    controls: Iterable[Control],
    evidence: Iterable[EvidenceItem],
    *,
    as_of: date,
) -> EvidenceAssessment:
    evidence = tuple(evidence)
    evidence_ids = [item.evidence_id for item in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("evidence identifiers must be unique")

    requirements: dict[tuple[str, str], EvidenceRequirement] = {}
    for control in controls:
        for requirement in control.evidence_requirements:
            requirements[(control.control_id, requirement.requirement_id)] = requirement

    satisfied: set[tuple[str, str]] = set()
    accepted_ids: list[str] = []
    rejected: list[str] = []
    for item in evidence:
        key = (item.control_id, item.requirement_id)
        reason: str | None = None
        requirement = requirements.get(key)
        if item.system_id != system.system_id or item.system_version != system.version:
            reason = "wrong_system_or_version"
        elif requirement is None:
            reason = "not_required_by_profile"
        elif item.result is not EvidenceResult.PASS:
            reason = "failed_test_or_assessment"
        elif item.produced_on > as_of:
            reason = "future_dated"
        elif item.valid_until < as_of:
            reason = "expired"
        elif (as_of - item.produced_on).days > requirement.maximum_age_days:
            reason = "older_than_control_policy"
        if reason:
            rejected.append(f"{item.evidence_id}:{reason}")
            continue
        satisfied.add(key)
        accepted_ids.append(item.evidence_id)

    missing = tuple(
        f"{control_id}:{requirement_id}"
        for control_id, requirement_id in sorted(set(requirements) - satisfied)
    )
    requirement_keys = tuple(
        f"{control_id}:{requirement_id}" for control_id, requirement_id in sorted(requirements)
    )
    return EvidenceAssessment(
        system_id=system.system_id,
        system_version=system.version,
        control_profile_version=CONTROL_PROFILE_VERSION,
        assessed_on=as_of,
        required_requirement_keys=requirement_keys,
        required_count=len(requirements),
        satisfied_count=len(satisfied),
        missing_requirements=missing,
        rejected_evidence=tuple(sorted(rejected)),
        accepted_evidence_ids=tuple(sorted(accepted_ids)),
    )


class RACIEntry(FrozenModel):
    activity: str = Field(min_length=1)
    accountable: tuple[str, ...]
    responsible: tuple[str, ...]
    consulted: tuple[str, ...] = ()
    informed: tuple[str, ...] = ()

    @model_validator(mode="after")
    def ownership_is_unambiguous(self) -> "RACIEntry":
        if len(self.accountable) != 1:
            raise ValueError("each activity requires exactly one accountable role")
        if not self.responsible:
            raise ValueError("each activity requires at least one responsible role")
        return self


def validate_raci(entries: Iterable[RACIEntry], required_activities: Iterable[str]) -> tuple[str, ...]:
    entries = tuple(entries)
    activities = [entry.activity for entry in entries]
    if len(activities) != len(set(activities)):
        raise ValueError("RACI activities must be unique")
    missing = sorted(set(required_activities) - set(activities))
    if missing:
        raise ValueError(f"RACI is missing activities: {missing}")
    return tuple(sorted(activities))


class GateRequest(FrozenModel):
    request_id: str = Field(pattern=r"^GATE-[A-Z0-9-]+$")
    system_id: str
    system_version: str
    system_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_profile_version: str
    target_environment: str = Field(min_length=1)


class GateDecision(FrozenModel):
    request_id: str
    system_id: str
    system_version: str
    system_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_environment: str
    applicability_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_assessment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: GateOutcome
    reason_codes: tuple[str, ...]
    required_control_ids: tuple[str, ...]
    accepted_evidence_ids: tuple[str, ...]
    pending_reviews: tuple[ReviewDomain, ...]
    decided_on: date
    policy_version: str
    decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    legal_compliance_established: bool = False

    @model_validator(mode="after")
    def internal_gate_never_claims_legal_compliance(self) -> "GateDecision":
        if self.legal_compliance_established:
            raise ValueError("this internal gate cannot establish legal compliance")
        return self


def evaluate_gate(
    request: GateRequest,
    system: AgentSystemRecord,
    controls: Iterable[Control],
    applicability: ApplicabilityRecord,
    evidence_assessment: EvidenceAssessment,
    *,
    as_of: date,
) -> GateDecision:
    controls = tuple(controls)
    required_control_ids = tuple(sorted(control.control_id for control in controls))
    expected_control_ids = tuple(
        control.control_id for control in select_controls(system, control_library())
    )
    required_requirement_keys = tuple(
        sorted(
            f"{control.control_id}:{requirement.requirement_id}"
            for control in controls
            for requirement in control.evidence_requirements
        )
    )
    reasons: list[str] = []
    pending: tuple[ReviewDomain, ...] = ()
    if not controls:
        reasons.append("empty_control_profile")
    if len(required_control_ids) != len(set(required_control_ids)):
        reasons.append("duplicate_control_ids")
    if required_control_ids != expected_control_ids:
        reasons.append("control_profile_coverage_mismatch")
    if request.system_id != system.system_id or request.system_version != system.version:
        reasons.append("request_system_binding_mismatch")
    if request.system_digest != system_digest(system):
        reasons.append("request_digest_mismatch")
    if request.control_profile_version != CONTROL_PROFILE_VERSION:
        reasons.append("control_profile_version_mismatch")
    if applicability.system_id != system.system_id or applicability.system_version != system.version:
        reasons.append("applicability_binding_mismatch")
    expected_domains = set(required_review_domains(system))
    recorded_domains = {review.domain for review in applicability.reviews}
    if recorded_domains != expected_domains:
        reasons.append("applicability_review_coverage_mismatch")
    if applicability.methodology_snapshot > as_of:
        reasons.append("future_applicability_methodology")
    if evidence_assessment.system_id != system.system_id or evidence_assessment.system_version != system.version:
        reasons.append("evidence_assessment_binding_mismatch")
    if evidence_assessment.control_profile_version != request.control_profile_version:
        reasons.append("evidence_control_profile_version_mismatch")
    if evidence_assessment.required_requirement_keys != required_requirement_keys:
        reasons.append("evidence_population_mismatch")
    if evidence_assessment.assessed_on != as_of:
        reasons.append("evidence_assessment_date_mismatch")
    if reasons:
        outcome = GateOutcome.BLOCKED
    else:
        reviews_by_domain = {item.domain: item for item in applicability.reviews}
        pending_set = {
            domain
            for domain in required_review_domains(system)
            if domain not in reviews_by_domain or reviews_by_domain[domain].status is ReviewStatus.PENDING
        }
        if applicability.methodology_snapshot > as_of or applicability.valid_until < as_of:
            reasons.append("applicability_review_not_current")
            pending_set.update(required_review_domains(system))
        pending = tuple(sorted(pending_set, key=lambda item: item.value))
        if pending:
            reasons.extend(f"pending_specialist_review:{item.value}" for item in pending)
            outcome = GateOutcome.SPECIALIST_REVIEW_REQUIRED
        elif evidence_assessment.missing_requirements:
            reasons.extend(f"missing_evidence:{item}" for item in evidence_assessment.missing_requirements)
            outcome = GateOutcome.BLOCKED
        elif any(item.endswith(":failed_test_or_assessment") for item in evidence_assessment.rejected_evidence):
            reasons.extend(
                f"blocking_evidence:{item}"
                for item in evidence_assessment.rejected_evidence
                if item.endswith(":failed_test_or_assessment")
            )
            outcome = GateOutcome.BLOCKED
        else:
            reasons.append("all_internal_release_requirements_satisfied")
            outcome = GateOutcome.APPROVED_INTERNAL_RELEASE

    decision_material = {
        "request_id": request.request_id,
        "system_id": system.system_id,
        "system_version": system.version,
        "system_digest": request.system_digest,
        "target_environment": request.target_environment,
        "applicability_digest": stable_digest(applicability),
        "evidence_assessment_digest": stable_digest(evidence_assessment),
        "outcome": outcome.value,
        "reason_codes": reasons,
        "required_control_ids": required_control_ids,
        "accepted_evidence_ids": list(evidence_assessment.accepted_evidence_ids),
        "pending_reviews": [item.value for item in pending],
        "decided_on": as_of.isoformat(),
        "policy_version": CONTROL_PROFILE_VERSION,
    }
    return GateDecision(
        request_id=request.request_id,
        system_id=system.system_id,
        system_version=system.version,
        system_digest=request.system_digest,
        target_environment=request.target_environment,
        applicability_digest=stable_digest(applicability),
        evidence_assessment_digest=stable_digest(evidence_assessment),
        outcome=outcome,
        reason_codes=tuple(reasons),
        required_control_ids=required_control_ids,
        accepted_evidence_ids=evidence_assessment.accepted_evidence_ids,
        pending_reviews=pending,
        decided_on=as_of,
        policy_version=CONTROL_PROFILE_VERSION,
        decision_digest=stable_digest(decision_material),
    )


class ExceptionRecord(FrozenModel):
    exception_id: str = Field(pattern=r"^EX-[A-Z0-9-]+$")
    system_id: str
    system_version: str
    control_id: str
    rationale: str = Field(min_length=1)
    compensating_controls: tuple[str, ...]
    requester: str = Field(min_length=1)
    risk_acceptor: str = Field(min_length=1)
    issued_on: date
    expires_on: date
    remediation_plan: str = Field(min_length=1)
    evidence_ids: tuple[str, ...]

    @model_validator(mode="after")
    def exception_is_bounded(self) -> "ExceptionRecord":
        if self.expires_on <= self.issued_on:
            raise ValueError("exception expiry must be after issuance")
        if self.requester == self.risk_acceptor:
            raise ValueError("exception requester and risk acceptor must be different roles")
        if not self.compensating_controls or not self.evidence_ids:
            raise ValueError("exception requires compensating controls and evidence")
        return self


def evaluate_exception(
    exception: ExceptionRecord,
    system: AgentSystemRecord,
    controls: Iterable[Control],
    *,
    accepted_evidence_ids: Iterable[str] = (),
    as_of: date,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    controls_by_id = {item.control_id: item for item in controls}
    control = controls_by_id.get(exception.control_id)
    if exception.system_id != system.system_id or exception.system_version != system.version:
        reasons.append("exception_binding_mismatch")
    if control is None:
        reasons.append("control_not_in_profile")
    elif not control.exception_eligible:
        reasons.append("control_not_exception_eligible")
    if exception.expires_on < as_of:
        reasons.append("exception_expired")
    if not set(exception.evidence_ids).issubset(set(accepted_evidence_ids)):
        reasons.append("unverified_compensating_evidence")
    return not reasons, tuple(reasons)


class SystemSnapshot(FrozenModel):
    version: str
    model_ids: frozenset[str]
    capability_fingerprints: frozenset[str]
    data_classes: frozenset[str]
    autonomy: AutonomyLevel
    memory_enabled: bool
    subagents_enabled: bool
    jurisdictions: frozenset[str]
    max_transaction_usd: int
    affected_groups: frozenset[str]


def snapshot(system: AgentSystemRecord) -> SystemSnapshot:
    return SystemSnapshot(
        version=system.version,
        model_ids=frozenset(system.model_ids),
        capability_fingerprints=frozenset(stable_digest(item) for item in system.capabilities),
        data_classes=system.data_classes,
        autonomy=system.autonomy,
        memory_enabled=system.memory_enabled,
        subagents_enabled=system.subagents_enabled,
        jurisdictions=system.jurisdictions,
        max_transaction_usd=max(item.financial_limit_usd for item in system.capabilities),
        affected_groups=frozenset(system.affected_groups),
    )


class ChangeAssessment(FrozenModel):
    triggers: tuple[ChangeTrigger, ...]
    reassessment_scopes: tuple[str, ...]
    full_reassessment_required: bool


def assess_change(before: SystemSnapshot, after: SystemSnapshot) -> ChangeAssessment:
    triggers: set[ChangeTrigger] = set()
    scopes: set[str] = set()
    full = False
    if before.model_ids != after.model_ids:
        triggers.add(ChangeTrigger.MODEL)
        scopes.update({"model evaluation", "safety evaluation", "cost and latency regression"})
    if before.capability_fingerprints != after.capability_fingerprints:
        triggers.add(ChangeTrigger.CAPABILITY)
        scopes.update({"authorization", "threat model", "tool governance", "runtime policy"})
    if before.data_classes != after.data_classes:
        triggers.add(ChangeTrigger.DATA)
        scopes.update({"privacy", "data governance", "access control"})
    if before.autonomy != after.autonomy:
        triggers.add(ChangeTrigger.AUTONOMY)
        scopes.update({"agent risk", "human oversight", "approval architecture"})
        full = full or after.autonomy > before.autonomy
    if before.memory_enabled != after.memory_enabled:
        triggers.add(ChangeTrigger.MEMORY)
        scopes.update({"memory governance", "retention", "subject and tenant isolation"})
    if before.subagents_enabled != after.subagents_enabled:
        triggers.add(ChangeTrigger.DELEGATION)
        scopes.update({"delegation risk", "agent identity", "authority attenuation"})
    if before.jurisdictions != after.jurisdictions:
        triggers.add(ChangeTrigger.JURISDICTION)
        scopes.add("legal and regulatory applicability")
        full = full or bool(after.jurisdictions - before.jurisdictions)
    if before.max_transaction_usd != after.max_transaction_usd:
        triggers.add(ChangeTrigger.TRANSACTION_LIMIT)
        scopes.update({"financial risk", "approval thresholds", "risk appetite"})
        full = full or after.max_transaction_usd > before.max_transaction_usd
    if before.affected_groups != after.affected_groups:
        triggers.add(ChangeTrigger.AFFECTED_GROUP)
        scopes.update({"impact assessment", "stakeholder consultation"})
        full = True
    return ChangeAssessment(
        triggers=tuple(sorted(triggers, key=lambda item: item.value)),
        reassessment_scopes=tuple(sorted(scopes)),
        full_reassessment_required=full,
    )


class GovernancePackage(FrozenModel):
    schema_version: str = "oneplusi-governance-package-1.0"
    methodology_snapshot: date
    system: AgentSystemRecord
    applicability: ApplicabilityRecord
    controls: tuple[Control, ...]
    evidence_assessment: EvidenceAssessment
    decision: GateDecision

    def package_digest(self) -> str:
        return stable_digest(self)


GOVERNANCE_PACKAGE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "schema_version",
        "methodology_snapshot",
        "system",
        "applicability",
        "controls",
        "evidence_assessment",
        "decision",
    ],
    "properties": {
        "schema_version": {"const": "oneplusi-governance-package-1.0"},
        "system": {
            "type": "object",
            "required": ["system_id", "version", "business_owner", "technical_owner", "capabilities"],
        },
        "controls": {"type": "array", "minItems": 1},
        "evidence_assessment": {
            "type": "object",
            "required": [
                "control_profile_version",
                "required_requirement_keys",
                "required_count",
                "satisfied_count",
                "missing_requirements",
            ],
        },
        "decision": {
            "type": "object",
            "required": [
                "system_id",
                "system_version",
                "system_digest",
                "target_environment",
                "applicability_digest",
                "evidence_assessment_digest",
                "outcome",
                "reason_codes",
                "decision_digest",
                "legal_compliance_established",
            ],
        },
    },
}


def oscal_component_projection(system: AgentSystemRecord, controls: Iterable[Control]) -> dict[str, object]:
    """Return a teaching projection; validate with official OSCAL tooling before exchange."""

    return {
        "format": "teaching-projection-not-oscal-conformant",
        "target_oscal_version": "1.2.3",
        "system_id": system.system_id,
        "system_version": system.version,
        "component_definition_projection": [
            {
                "control_id": control.control_id,
                "description": control.objective,
                "responsible_role": control.owner_role,
                "external_mappings": [mapping.model_dump(mode="json") for mapping in control.mappings],
            }
            for control in controls
        ],
        "validation_required": "Validate a real OSCAL artifact against the official schema or Compliance Trestle.",
    }


def demo_system(*, include_eu: bool = False, version: str = "1.0.0") -> AgentSystemRecord:
    jurisdictions = {"CA", "EU"} if include_eu else {"CA"}
    return AgentSystemRecord(
        system_id="SYS-PROCUREMENT-01",
        version=version,
        name="Enterprise Procurement Agent",
        purpose="Prepare and create routine purchase orders for approved vendors.",
        intended_use=("Approved catalogue search", "Purchase orders up to USD 25,000"),
        prohibited_use=("Vendor onboarding", "Direct payment", "Sanctions override"),
        business_owner="VP Procurement",
        technical_owner="AI Platform Lead",
        autonomy=AutonomyLevel.BOUNDED,
        internal_risk_tier=RiskTier.HIGH,
        model_ids=("enterprise-llm-v1",),
        capabilities=(
            Capability(
                capability_id="catalog_search",
                description="Search the approved vendor catalogue",
                mutates_state=False,
            ),
            Capability(
                capability_id="supplier_email",
                description="Send bounded supplier clarification requests",
                mutates_state=True,
                external_communication=True,
                irreversible=True,
            ),
            Capability(
                capability_id="create_purchase_order",
                description="Create a purchase order after runtime authorization",
                mutates_state=True,
                privileged_access=True,
                irreversible=True,
                financial_limit_usd=25_000,
            ),
        ),
        data_classes=frozenset({"internal", "confidential"}),
        jurisdictions=frozenset(jurisdictions),
        affected_groups=("procurement staff", "suppliers"),
        memory_enabled=True,
        subagents_enabled=True,
    )


def demo_raci() -> tuple[RACIEntry, ...]:
    return (
        RACIEntry(activity="Define intended use", accountable=("Business Owner",), responsible=("Product Manager",), consulted=("AI Governance",)),
        RACIEntry(activity="Implement controls", accountable=("Technical Owner",), responsible=("AI Engineering",), consulted=("Security",)),
        RACIEntry(activity="Assess applicability", accountable=("Legal/Compliance",), responsible=("Legal/Compliance",), consulted=("AI Governance",)),
        RACIEntry(activity="Approve internal release", accountable=("Business Owner",), responsible=("AI Governance",), consulted=("Security", "Legal/Compliance")),
        RACIEntry(activity="Independent assurance", accountable=("Internal Audit",), responsible=("Independent Assurance",), informed=("Board Risk Committee",)),
    )


def demo_evidence(
    system: AgentSystemRecord,
    controls: Iterable[Control],
    *,
    as_of: date,
) -> tuple[EvidenceItem, ...]:
    items: list[EvidenceItem] = []
    counter = 1
    for control in controls:
        for requirement in control.evidence_requirements:
            evidence_id = f"EV-{counter:03d}"
            artifact_uri = f"evidence://{system.system_id}/{system.version}/{control.control_id}/{requirement.requirement_id}"
            items.append(
                EvidenceItem(
                    evidence_id=evidence_id,
                    system_id=system.system_id,
                    system_version=system.version,
                    control_id=control.control_id,
                    requirement_id=requirement.requirement_id,
                    result=EvidenceResult.PASS,
                    artifact_uri=artifact_uri,
                    artifact_digest=stable_digest({"uri": artifact_uri, "fixture": "course-03"}),
                    produced_on=as_of,
                    valid_until=as_of + timedelta(days=365),
                    producer=f"{control.owner_role} evidence pipeline",
                    environment="staging",
                )
            )
            counter += 1
    return tuple(items)


def demo_completed_reviews(system: AgentSystemRecord) -> dict[ReviewDomain, str]:
    return {domain: f"{domain.value} specialist" for domain in required_review_domains(system)}


def build_demo_package(*, include_eu: bool = False, as_of: date = METHODOLOGY_SNAPSHOT) -> GovernancePackage:
    system = demo_system(include_eu=include_eu)
    controls = select_controls(system, control_library())
    completed = demo_completed_reviews(system)
    applicability = build_applicability_record(system, completed_by=completed, as_of=as_of)
    evidence = demo_evidence(system, controls, as_of=as_of)
    assessment = assess_evidence(system, controls, evidence, as_of=as_of)
    request = GateRequest(
        request_id="GATE-PROCUREMENT-01",
        system_id=system.system_id,
        system_version=system.version,
        system_digest=system_digest(system),
        control_profile_version=CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    decision = evaluate_gate(request, system, controls, applicability, assessment, as_of=as_of)
    return GovernancePackage(
        methodology_snapshot=as_of,
        system=system,
        applicability=applicability,
        controls=controls,
        evidence_assessment=assessment,
        decision=decision,
    )


def evaluation_report() -> dict[str, float | int]:
    as_of = METHODOLOGY_SNAPSHOT
    package = build_demo_package(as_of=as_of)
    system = package.system
    controls = package.controls
    evidence = demo_evidence(system, controls, as_of=as_of)

    cases: list[tuple[str, GateOutcome, tuple[EvidenceItem, ...], ApplicabilityRecord, GateRequest]] = []
    base_request = GateRequest(
        request_id="GATE-EVAL-BASE",
        system_id=system.system_id,
        system_version=system.version,
        system_digest=system_digest(system),
        control_profile_version=CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    complete_applicability = build_applicability_record(
        system, completed_by=demo_completed_reviews(system), as_of=as_of
    )
    cases.append(("complete", GateOutcome.APPROVED_INTERNAL_RELEASE, evidence, complete_applicability, base_request))
    cases.append(("missing", GateOutcome.BLOCKED, evidence[:-1], complete_applicability, base_request))
    expired = tuple(item.model_copy(update={"valid_until": date(2026, 9, 19)}) for item in evidence)
    cases.append(("expired", GateOutcome.BLOCKED, expired, complete_applicability, base_request))
    pending_applicability = build_applicability_record(system, completed_by={}, as_of=as_of)
    cases.append(("pending_review", GateOutcome.SPECIALIST_REVIEW_REQUIRED, evidence, pending_applicability, base_request))
    altered_request = base_request.model_copy(update={"request_id": "GATE-EVAL-ALTERED", "system_digest": "0" * 64})
    cases.append(("altered", GateOutcome.BLOCKED, evidence, complete_applicability, altered_request))

    correct = 0
    for _, expected, case_evidence, case_applicability, request in cases:
        assessment = assess_evidence(system, controls, case_evidence, as_of=as_of)
        actual = evaluate_gate(request, system, controls, case_applicability, assessment, as_of=as_of)
        correct += int(actual.outcome is expected)
    return {"correct": correct, "cases": len(cases), "decision_accuracy": correct / len(cases)}
