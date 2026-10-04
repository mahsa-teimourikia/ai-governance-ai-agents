"""Deterministic enterprise agent-governance operating model for Course 16.

The lab models a multi-tenant procurement-agent portfolio from registration to
retirement.  It demonstrates risk-based control baselines, version-bound
evidence, separation of duties, signed release approvals, CycloneDX AI/ML-BOM
export, material-change routing, expiring exceptions, incident containment,
recertification, and portfolio evaluation.  It makes no model, network, shell,
cloud, or business-system call.  Fixed keys are educational test data only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from enum import IntEnum, StrEnum
from importlib.metadata import version as package_version
from threading import Lock
from uuid import NAMESPACE_URL, uuid5

from cyclonedx.model import HashAlgorithm, HashType, Property
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.output.json import JsonV1Dot7
from pydantic import BaseModel, ConfigDict, Field, model_validator

REFERENCE_TIME = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
TENANT_ACME = "tenant-acme"
TENANT_GLOBEX = "tenant-globex"
POLICY_VERSION = "enterprise-agent-governance/16.1"
DEMO_SIGNING_KEY = b"course-16-demo-key-never-use-in-production"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GovernanceError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class RiskTier(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class Lifecycle(StrEnum):
    DRAFT = "draft"
    REGISTERED = "registered"
    ASSESSING = "assessing"
    VALIDATING = "validating"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    RECERTIFICATION_DUE = "recertification_due"
    RESTRICTED = "restricted"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class DependencyKind(StrEnum):
    MODEL = "model"
    LIBRARY = "library"
    CONTAINER = "container"
    TOOL = "tool"
    MCP_SERVER = "mcp_server"
    DATA = "data"
    API = "api"
    AGENT = "agent"


class EvidenceStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


class Decision(StrEnum):
    PASS = "pass"
    BLOCK = "block"
    REVIEW = "review"


class ChangeClass(IntEnum):
    NON_MATERIAL = 1
    MATERIAL = 2
    MAJOR = 3
    CRITICAL = 4


class IncidentSeverity(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class IncidentStatus(StrEnum):
    OPEN = "open"
    CONTAINED = "contained"
    RECOVERY_REVIEW = "recovery_review"
    CLOSED = "closed"


class OperatorRole(StrEnum):
    PORTFOLIO_REGISTRAR = "portfolio_registrar"
    GOVERNANCE_OPERATOR = "governance_operator"
    PRODUCT_OWNER = "product_owner"
    BUSINESS_OWNER = "business_owner"
    TECHNICAL_OWNER = "technical_owner"
    AI_RISK = "ai_risk"
    SECURITY_ASSURANCE = "security_assurance"
    EXECUTIVE_RISK = "executive_risk"
    INCIDENT_COMMANDER = "incident_commander"
    INTERNAL_AUDIT = "internal_audit"


class Dependency(FrozenModel):
    dependency_id: str = Field(min_length=3)
    kind: DependencyKind
    version: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    third_party: bool
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    license_id: str = Field(min_length=1)
    approved: bool
    review_expires_at: datetime | None = None
    capabilities: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def third_party_review_is_explicit(self) -> Dependency:
        if self.third_party and self.review_expires_at is None:
            raise ValueError("third-party dependencies need a review expiry")
        return self


class AgentCard(FrozenModel):
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    business_owner_id: str = Field(min_length=1)
    technical_owner_id: str = Field(min_length=1)
    data_owner_id: str = Field(min_length=1)
    purpose: str = Field(min_length=12)
    intended_users: frozenset[str] = Field(min_length=1)
    prohibited_uses: frozenset[str] = Field(min_length=1)
    autonomy: int = Field(ge=0, le=3)
    impact: int = Field(ge=1, le=4)
    access: int = Field(ge=1, le=4)
    irreversibility: int = Field(ge=1, le=4)
    data_sensitivity: int = Field(ge=1, le=4)
    external_actions: bool
    permissions: frozenset[str]
    dependencies: tuple[Dependency, ...]
    regulatory_scopes: frozenset[str]
    policy_version: str
    prompt_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    deployment_environment: str

    @model_validator(mode="after")
    def owners_and_dependencies_are_unambiguous(self) -> AgentCard:
        if (
            len({self.business_owner_id, self.technical_owner_id, self.data_owner_id})
            < 2
        ):
            raise ValueError(
                "business, technical, and data ownership cannot collapse to one identity"
            )
        dependency_ids = [item.dependency_id for item in self.dependencies]
        if len(dependency_ids) != len(set(dependency_ids)):
            raise ValueError("dependency IDs must be unique")
        if self.external_actions and not self.permissions:
            raise ValueError(
                "an agent with external actions needs explicit permissions"
            )
        return self


class AuthenticatedOperator(FrozenModel):
    operator_id: str
    tenant_id: str
    roles: frozenset[OperatorRole]
    authenticated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def validity_window_is_positive(self) -> AuthenticatedOperator:
        if self.valid_until <= self.authenticated_at:
            raise ValueError("operator validity window must be positive")
        return self


class RiskAssessment(FrozenModel):
    tenant_id: str
    agent_id: str
    agent_version: str
    manifest_digest: str
    tier: RiskTier
    reason_codes: tuple[str, ...]
    assessed_at: datetime
    policy_version: str


class EvidenceArtifact(FrozenModel):
    evidence_id: str
    tenant_id: str
    agent_id: str
    agent_version: str
    manifest_digest: str
    control_id: str
    producer_id: str
    assessor_id: str
    status: EvidenceStatus
    source_uri: str
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    policy_version: str
    generated_at: datetime
    expires_at: datetime
    signature: str

    @model_validator(mode="after")
    def evidence_is_independently_assessed_and_freshly_ordered(
        self,
    ) -> EvidenceArtifact:
        if self.producer_id == self.assessor_id:
            raise ValueError("producer and assessor must be different")
        if self.expires_at <= self.generated_at:
            raise ValueError("evidence expiry must follow generation")
        return self


class ApprovalReceipt(FrozenModel):
    receipt_id: str
    release_id: str
    tenant_id: str
    agent_id: str
    agent_version: str
    manifest_digest: str
    risk_tier: RiskTier
    approver_id: str
    approver_role: OperatorRole
    policy_version: str
    package_digest: str
    constraints: frozenset[str]
    issued_at: datetime
    expires_at: datetime
    signature: str


class ExceptionRecord(FrozenModel):
    exception_id: str
    tenant_id: str
    agent_id: str
    agent_version: str
    manifest_digest: str
    control_id: str
    reason: str = Field(min_length=12)
    compensating_controls: frozenset[str] = Field(min_length=1)
    owner_id: str
    risk_acceptor_id: str
    risk_acceptor_role: OperatorRole
    policy_version: str
    exit_plan: str = Field(min_length=12)
    approved_at: datetime
    expires_at: datetime
    signature: str

    @model_validator(mode="after")
    def exception_is_bounded(self) -> ExceptionRecord:
        if self.expires_at <= self.approved_at:
            raise ValueError("exception must expire after approval")
        return self


class ChangeAssessment(FrozenModel):
    change_class: ChangeClass
    changed_dimensions: tuple[str, ...]
    invalidated_controls: frozenset[str]
    route: str
    suspend_before_review: bool


class GateResult(FrozenModel):
    decision: Decision
    release_id: str
    manifest_digest: str
    policy_version: str
    reason_codes: tuple[str, ...]
    required_controls: frozenset[str]
    accepted_controls: frozenset[str]
    required_approval_roles: frozenset[OperatorRole]
    accepted_approval_roles: frozenset[OperatorRole]


class RecertificationResult(FrozenModel):
    decision: Decision
    reason_codes: tuple[str, ...]
    next_review_at: datetime | None


class Incident(FrozenModel):
    incident_id: str
    alert_id: str
    tenant_id: str
    agent_id: str
    severity: IncidentSeverity
    kind: str
    source_id: str
    source_digest: str
    status: IncidentStatus
    opened_at: datetime
    contained_at: datetime | None = None
    evidence_ids: tuple[str, ...] = ()
    containment_actions: tuple[str, ...] = ()
    remediation_evidence_id: str | None = None
    closed_at: datetime | None = None


class RegistryRecord(FrozenModel):
    card: AgentCard
    lifecycle: Lifecycle
    record_version: int = Field(gt=0)
    registered_at: datetime
    last_changed_at: datetime
    last_recertified_at: datetime | None = None
    next_recertification_at: datetime | None = None


class Scenario(FrozenModel):
    scenario_id: str
    card: AgentCard
    evidence: tuple[EvidenceArtifact, ...]
    approvals: tuple[ApprovalReceipt, ...]
    exceptions: tuple[ExceptionRecord, ...] = ()
    expected: Decision
    label: str


def _canonical(value: object) -> object:
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {str(key): _canonical(child) for key, child in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_canonical(child) for child in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_canonical(child) for child in value), key=str)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, (StrEnum, IntEnum)):
        return value.value
    return value


def stable_digest(value: object) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def sha256_id(value: object) -> str:
    return f"sha256:{stable_digest(value)}"


def manifest_digest(card: AgentCard) -> str:
    return sha256_id(card)


def _receipt_payload(receipt: ApprovalReceipt | dict[str, object]) -> dict[str, object]:
    data = (
        receipt.model_dump(mode="python")
        if isinstance(receipt, ApprovalReceipt)
        else dict(receipt)
    )
    data.pop("signature", None)
    return data


def _sign_receipt(payload: dict[str, object]) -> str:
    digest = stable_digest(payload).encode()
    return hmac.new(DEMO_SIGNING_KEY, digest, hashlib.sha256).hexdigest()


def _signed_payload(record: BaseModel) -> dict[str, object]:
    payload = record.model_dump(mode="python")
    payload.pop("signature", None)
    return payload


def _signature_valid(record: BaseModel) -> bool:
    signature = getattr(record, "signature", "")
    return hmac.compare_digest(_sign_receipt(_signed_payload(record)), signature)


def build_operator(
    role: OperatorRole,
    operator_id: str | None = None,
    tenant_id: str = TENANT_ACME,
    now: datetime = REFERENCE_TIME,
) -> AuthenticatedOperator:
    return AuthenticatedOperator(
        operator_id=operator_id or f"operator-{role.value}",
        tenant_id=tenant_id,
        roles=frozenset({role}),
        authenticated_at=now - timedelta(minutes=5),
        valid_until=now + timedelta(hours=1),
    )


def authenticate(
    operator: AuthenticatedOperator, tenant_id: str, now: datetime
) -> None:
    if operator.tenant_id != tenant_id:
        raise GovernanceError("OPERATOR_TENANT_MISMATCH")
    if not (operator.authenticated_at <= now < operator.valid_until):
        raise GovernanceError("OPERATOR_SESSION_INVALID")


def require_role(
    operator: AuthenticatedOperator,
    role: OperatorRole,
    tenant_id: str,
    now: datetime,
) -> None:
    authenticate(operator, tenant_id, now)
    if role not in operator.roles:
        raise GovernanceError(f"ROLE_REQUIRED:{role.value}")


def classify_risk(card: AgentCard, now: datetime = REFERENCE_TIME) -> RiskAssessment:
    reasons: list[str] = []
    if card.autonomy == 3 and card.irreversibility >= 3:
        tier = RiskTier.CRITICAL
        reasons.append("AUTONOMOUS_IRREVERSIBLE_AUTHORITY")
    elif card.impact == 4 and card.external_actions:
        tier = RiskTier.CRITICAL
        reasons.append("SEVERE_EXTERNAL_IMPACT")
    elif card.external_actions or card.autonomy >= 2 or card.access >= 3:
        tier = RiskTier.HIGH
        reasons.append("CONSEQUENTIAL_OR_PRIVILEGED_AGENT")
    elif card.data_sensitivity >= 3 or card.autonomy == 1 or card.impact >= 3:
        tier = RiskTier.MODERATE
        reasons.append("SENSITIVE_OR_ASSISTIVE_AGENT")
    else:
        tier = RiskTier.LOW
        reasons.append("BOUNDED_READ_ONLY_AGENT")
    if any(item.third_party for item in card.dependencies):
        reasons.append("THIRD_PARTY_DEPENDENCY")
        tier = max(tier, RiskTier.MODERATE)
    if card.regulatory_scopes:
        reasons.append("REGULATED_SCOPE")
        tier = max(tier, RiskTier.HIGH)
    return RiskAssessment(
        tenant_id=card.tenant_id,
        agent_id=card.agent_id,
        agent_version=card.version,
        manifest_digest=manifest_digest(card),
        tier=tier,
        reason_codes=tuple(reasons),
        assessed_at=now,
        policy_version=card.policy_version,
    )


CONTROL_BASELINES: dict[RiskTier, frozenset[str]] = {
    RiskTier.LOW: frozenset(
        {"agent_card", "ownership", "dependency_inventory", "basic_evaluation"}
    ),
    RiskTier.MODERATE: frozenset(
        {
            "agent_card",
            "ownership",
            "dependency_inventory",
            "impact_assessment",
            "threat_model",
            "evaluation",
            "monitoring",
        }
    ),
    RiskTier.HIGH: frozenset(
        {
            "agent_card",
            "ownership",
            "dependency_inventory",
            "impact_assessment",
            "threat_model",
            "authorization_review",
            "evaluation",
            "red_team",
            "monitoring",
            "kill_switch",
            "incident_plan",
            "third_party_review",
        }
    ),
    RiskTier.CRITICAL: frozenset(
        {
            "agent_card",
            "ownership",
            "dependency_inventory",
            "impact_assessment",
            "enhanced_threat_model",
            "authorization_review",
            "independent_evaluation",
            "enhanced_red_team",
            "continuous_monitoring",
            "kill_switch",
            "incident_exercise",
            "third_party_review",
            "independent_assurance",
        }
    ),
}

APPROVAL_ROLES: dict[RiskTier, frozenset[OperatorRole]] = {
    RiskTier.LOW: frozenset({OperatorRole.PRODUCT_OWNER}),
    RiskTier.MODERATE: frozenset({OperatorRole.BUSINESS_OWNER, OperatorRole.AI_RISK}),
    RiskTier.HIGH: frozenset(
        {
            OperatorRole.BUSINESS_OWNER,
            OperatorRole.AI_RISK,
            OperatorRole.SECURITY_ASSURANCE,
        }
    ),
    RiskTier.CRITICAL: frozenset(
        {
            OperatorRole.BUSINESS_OWNER,
            OperatorRole.AI_RISK,
            OperatorRole.SECURITY_ASSURANCE,
            OperatorRole.EXECUTIVE_RISK,
        }
    ),
}

NON_WAIVABLE_CONTROLS = frozenset(
    {"ownership", "kill_switch", "incident_exercise", "independent_assurance"}
)


def supply_chain_findings(
    card: AgentCard, now: datetime = REFERENCE_TIME
) -> tuple[str, ...]:
    findings: list[str] = []
    for item in card.dependencies:
        prefix = item.dependency_id
        if not item.approved:
            findings.append(f"DEPENDENCY_NOT_APPROVED:{prefix}")
        if (
            item.third_party
            and item.review_expires_at
            and item.review_expires_at <= now
        ):
            findings.append(f"THIRD_PARTY_REVIEW_EXPIRED:{prefix}")
        if item.kind == DependencyKind.MCP_SERVER and not item.capabilities:
            findings.append(f"MCP_CAPABILITIES_NOT_DECLARED:{prefix}")
    return tuple(sorted(findings))


def accepted_evidence_controls(
    card: AgentCard,
    records: Iterable[EvidenceArtifact],
    now: datetime = REFERENCE_TIME,
) -> tuple[frozenset[str], tuple[str, ...]]:
    accepted: set[str] = set()
    reasons: list[str] = []
    card_digest = manifest_digest(card)
    for item in records:
        if not _signature_valid(item):
            reasons.append(f"EVIDENCE_SIGNATURE_INVALID:{item.evidence_id}")
        elif item.tenant_id != card.tenant_id or item.agent_id != card.agent_id:
            reasons.append(f"EVIDENCE_SCOPE_MISMATCH:{item.evidence_id}")
        elif item.agent_version != card.version or item.manifest_digest != card_digest:
            reasons.append(f"EVIDENCE_VERSION_MISMATCH:{item.evidence_id}")
        elif item.policy_version != card.policy_version:
            reasons.append(f"EVIDENCE_POLICY_MISMATCH:{item.evidence_id}")
        elif not (item.generated_at <= now < item.expires_at):
            reasons.append(f"EVIDENCE_NOT_CURRENT:{item.evidence_id}")
        elif item.status != EvidenceStatus.PASS:
            reasons.append(f"EVIDENCE_NOT_PASSING:{item.evidence_id}")
        else:
            accepted.add(item.control_id)
    return frozenset(accepted), tuple(sorted(reasons))


def release_package_digest(
    card: AgentCard,
    tier: RiskTier,
    release_id: str,
    evidence: Iterable[EvidenceArtifact],
    exceptions: Iterable[ExceptionRecord] = (),
) -> str:
    evidence_items = sorted(
        (_canonical(item) for item in evidence),
        key=lambda item: str(item["evidence_id"]),
    )
    exception_items = sorted(
        (_canonical(item) for item in exceptions),
        key=lambda item: str(item["exception_id"]),
    )
    return sha256_id(
        {
            "release_id": release_id,
            "tenant_id": card.tenant_id,
            "agent_id": card.agent_id,
            "agent_version": card.version,
            "manifest_digest": manifest_digest(card),
            "risk_tier": tier,
            "policy_version": card.policy_version,
            "required_controls": CONTROL_BASELINES[tier],
            "evidence": evidence_items,
            "exceptions": exception_items,
        }
    )


class ApprovalLedger:
    """Issues and atomically consumes exact-release, role-bound approvals."""

    def __init__(self) -> None:
        self._consumed: set[str] = set()
        self._lock = Lock()

    def issue(
        self,
        operator: AuthenticatedOperator,
        card: AgentCard,
        tier: RiskTier,
        release_id: str,
        role: OperatorRole,
        constraints: frozenset[str],
        now: datetime = REFERENCE_TIME,
        ttl: timedelta = timedelta(days=30),
        package_digest: str | None = None,
    ) -> ApprovalReceipt:
        authenticate(operator, card.tenant_id, now)
        if role not in operator.roles:
            raise GovernanceError("APPROVER_ROLE_NOT_AUTHENTICATED")
        if role not in APPROVAL_ROLES[tier]:
            raise GovernanceError("APPROVER_ROLE_NOT_REQUIRED")
        if operator.operator_id in {
            card.technical_owner_id,
            card.data_owner_id,
        } and role in {
            OperatorRole.AI_RISK,
            OperatorRole.SECURITY_ASSURANCE,
            OperatorRole.EXECUTIVE_RISK,
        }:
            raise GovernanceError("SEPARATION_OF_DUTIES_VIOLATION")
        payload: dict[str, object] = {
            "receipt_id": f"approval-{stable_digest((release_id, package_digest, role.value, operator.operator_id))[:16]}",
            "release_id": release_id,
            "tenant_id": card.tenant_id,
            "agent_id": card.agent_id,
            "agent_version": card.version,
            "manifest_digest": manifest_digest(card),
            "risk_tier": tier,
            "approver_id": operator.operator_id,
            "approver_role": role,
            "policy_version": card.policy_version,
            "package_digest": package_digest
            or sha256_id((release_id, manifest_digest(card), card.policy_version)),
            "constraints": constraints,
            "issued_at": now,
            "expires_at": now + ttl,
        }
        return ApprovalReceipt(**payload, signature=_sign_receipt(payload))

    def validate(
        self,
        receipt: ApprovalReceipt,
        card: AgentCard,
        tier: RiskTier,
        release_id: str,
        now: datetime = REFERENCE_TIME,
        package_digest: str | None = None,
    ) -> None:
        if not hmac.compare_digest(
            _sign_receipt(_receipt_payload(receipt)), receipt.signature
        ):
            raise GovernanceError("APPROVAL_SIGNATURE_INVALID")
        expected = (
            receipt.tenant_id == card.tenant_id
            and receipt.agent_id == card.agent_id
            and receipt.agent_version == card.version
            and receipt.manifest_digest == manifest_digest(card)
            and receipt.risk_tier == tier
            and receipt.policy_version == card.policy_version
            and receipt.release_id == release_id
            and receipt.package_digest == (package_digest or receipt.package_digest)
        )
        if not expected:
            raise GovernanceError("APPROVAL_SCOPE_MISMATCH")
        if not (receipt.issued_at <= now < receipt.expires_at):
            raise GovernanceError("APPROVAL_EXPIRED")
        if receipt.approver_role not in APPROVAL_ROLES[tier]:
            raise GovernanceError("APPROVAL_ROLE_INVALID")

    def consume_bundle(
        self,
        receipts: Iterable[ApprovalReceipt],
        card: AgentCard,
        tier: RiskTier,
        release_id: str,
        now: datetime = REFERENCE_TIME,
        package_digest: str | None = None,
    ) -> None:
        bundle = tuple(receipts)
        for receipt in bundle:
            self.validate(receipt, card, tier, release_id, now, package_digest)
        roles = {item.approver_role for item in bundle}
        if roles != set(APPROVAL_ROLES[tier]):
            raise GovernanceError("APPROVAL_ROLE_SET_INCOMPLETE")
        if len({item.approver_id for item in bundle}) != len(bundle):
            raise GovernanceError("APPROVER_IDENTITIES_NOT_DISTINCT")
        with self._lock:
            ids = {item.receipt_id for item in bundle}
            if ids & self._consumed:
                raise GovernanceError("APPROVAL_ALREADY_CONSUMED")
            self._consumed.update(ids)


def gate_release(
    card: AgentCard,
    evidence: Iterable[EvidenceArtifact],
    approvals: Iterable[ApprovalReceipt],
    release_id: str,
    ledger: ApprovalLedger,
    exceptions: Iterable[ExceptionRecord] = (),
    now: datetime = REFERENCE_TIME,
    consume: bool = False,
) -> GateResult:
    assessment = classify_risk(card, now)
    required = CONTROL_BASELINES[assessment.tier]
    evidence_items = tuple(evidence)
    exception_items = tuple(exceptions)
    package_digest = release_package_digest(
        card, assessment.tier, release_id, evidence_items, exception_items
    )
    accepted, evidence_reasons = accepted_evidence_controls(card, evidence_items, now)
    reasons = list(evidence_reasons) + list(supply_chain_findings(card, now))
    active_exceptions: set[str] = set()
    for item in exception_items:
        if (
            _signature_valid(item)
            and item.tenant_id == card.tenant_id
            and item.agent_id == card.agent_id
            and item.agent_version == card.version
            and item.manifest_digest == manifest_digest(card)
            and item.policy_version == card.policy_version
            and item.approved_at <= now < item.expires_at
            and item.control_id not in NON_WAIVABLE_CONTROLS
        ):
            active_exceptions.add(item.control_id)
        else:
            reasons.append(f"EXCEPTION_INVALID:{item.exception_id}")
    missing = required - accepted - active_exceptions
    reasons.extend(f"CONTROL_MISSING:{item}" for item in sorted(missing))
    valid_roles: set[OperatorRole] = set()
    valid_receipts: list[ApprovalReceipt] = []
    for receipt in approvals:
        try:
            ledger.validate(
                receipt,
                card,
                assessment.tier,
                release_id,
                now,
                package_digest,
            )
        except GovernanceError as exc:
            reasons.append(exc.code)
        else:
            valid_roles.add(receipt.approver_role)
            valid_receipts.append(receipt)
    missing_roles = APPROVAL_ROLES[assessment.tier] - valid_roles
    reasons.extend(
        f"APPROVAL_MISSING:{item.value}" for item in sorted(missing_roles, key=str)
    )
    decision = Decision.BLOCK if reasons else Decision.PASS
    if consume and decision == Decision.PASS:
        ledger.consume_bundle(
            valid_receipts,
            card,
            assessment.tier,
            release_id,
            now,
            package_digest,
        )
    return GateResult(
        decision=decision,
        release_id=release_id,
        manifest_digest=manifest_digest(card),
        policy_version=card.policy_version,
        reason_codes=tuple(sorted(set(reasons))),
        required_controls=required,
        accepted_controls=accepted,
        required_approval_roles=APPROVAL_ROLES[assessment.tier],
        accepted_approval_roles=frozenset(valid_roles),
    )


def manual_checklist_baseline(
    card: AgentCard,
    evidence: Iterable[EvidenceArtifact],
    approvals: Iterable[ApprovalReceipt],
    **_: object,
) -> Decision:
    """Intentionally weak comparator: checks presence, not scope, freshness, or integrity."""
    return (
        Decision.PASS
        if card.business_owner_id and tuple(evidence) and tuple(approvals)
        else Decision.BLOCK
    )


def create_exception(
    operator: AuthenticatedOperator,
    card: AgentCard,
    control_id: str,
    reason: str,
    compensating_controls: frozenset[str],
    exit_plan: str,
    now: datetime = REFERENCE_TIME,
    ttl: timedelta = timedelta(days=14),
) -> ExceptionRecord:
    authenticate(operator, card.tenant_id, now)
    if (
        OperatorRole.AI_RISK not in operator.roles
        and OperatorRole.EXECUTIVE_RISK not in operator.roles
    ):
        raise GovernanceError("RISK_ACCEPTOR_ROLE_REQUIRED")
    if control_id in NON_WAIVABLE_CONTROLS:
        raise GovernanceError("CONTROL_NOT_WAIVABLE")
    if ttl <= timedelta(0) or ttl > timedelta(days=90):
        raise GovernanceError("EXCEPTION_TTL_OUT_OF_RANGE")
    payload: dict[str, object] = {
        "exception_id": f"exception-{stable_digest((card.agent_id, card.version, control_id, now))[:16]}",
        "tenant_id": card.tenant_id,
        "agent_id": card.agent_id,
        "agent_version": card.version,
        "manifest_digest": manifest_digest(card),
        "control_id": control_id,
        "reason": reason,
        "compensating_controls": compensating_controls,
        "owner_id": card.business_owner_id,
        "risk_acceptor_id": operator.operator_id,
        "risk_acceptor_role": next(iter(operator.roles)),
        "policy_version": card.policy_version,
        "exit_plan": exit_plan,
        "approved_at": now,
        "expires_at": now + ttl,
    }
    return ExceptionRecord(**payload, signature=_sign_receipt(payload))


CHANGE_IMPACTS: dict[str, tuple[ChangeClass, frozenset[str]]] = {
    "business_owner_id": (
        ChangeClass.MATERIAL,
        frozenset({"ownership", "impact_assessment"}),
    ),
    "technical_owner_id": (
        ChangeClass.MATERIAL,
        frozenset({"ownership", "threat_model"}),
    ),
    "data_owner_id": (
        ChangeClass.MATERIAL,
        frozenset({"ownership", "impact_assessment"}),
    ),
    "purpose": (
        ChangeClass.MAJOR,
        frozenset({"impact_assessment", "evaluation", "approval"}),
    ),
    "intended_users": (
        ChangeClass.MATERIAL,
        frozenset({"impact_assessment", "evaluation"}),
    ),
    "prohibited_uses": (
        ChangeClass.MATERIAL,
        frozenset({"impact_assessment", "evaluation"}),
    ),
    "autonomy": (
        ChangeClass.MAJOR,
        frozenset({"threat_model", "authorization_review", "evaluation", "approval"}),
    ),
    "impact": (ChangeClass.MAJOR, frozenset({"impact_assessment", "approval"})),
    "access": (
        ChangeClass.MAJOR,
        frozenset({"authorization_review", "threat_model", "approval"}),
    ),
    "irreversibility": (
        ChangeClass.CRITICAL,
        frozenset({"kill_switch", "incident_plan", "approval"}),
    ),
    "data_sensitivity": (
        ChangeClass.MAJOR,
        frozenset({"impact_assessment", "threat_model", "approval"}),
    ),
    "external_actions": (
        ChangeClass.CRITICAL,
        frozenset({"authorization_review", "kill_switch", "approval"}),
    ),
    "permissions": (
        ChangeClass.MAJOR,
        frozenset({"authorization_review", "threat_model", "approval"}),
    ),
    "dependencies": (
        ChangeClass.MAJOR,
        frozenset(
            {"dependency_inventory", "threat_model", "evaluation", "third_party_review"}
        ),
    ),
    "regulatory_scopes": (
        ChangeClass.CRITICAL,
        frozenset({"impact_assessment", "independent_assurance", "approval"}),
    ),
    "policy_version": (
        ChangeClass.MAJOR,
        frozenset({"authorization_review", "evaluation", "approval"}),
    ),
    "prompt_digest": (ChangeClass.MATERIAL, frozenset({"evaluation", "red_team"})),
    "deployment_environment": (
        ChangeClass.MAJOR,
        frozenset({"threat_model", "monitoring", "approval"}),
    ),
}


def assess_change(before: AgentCard, after: AgentCard) -> ChangeAssessment:
    if before.tenant_id != after.tenant_id or before.agent_id != after.agent_id:
        raise GovernanceError("CHANGE_IDENTITY_MISMATCH")
    if before.version == after.version:
        raise GovernanceError("CHANGED_CARD_REQUIRES_NEW_VERSION")
    ignored = {"version"}
    changed = tuple(
        sorted(
            name
            for name in AgentCard.model_fields
            if name not in ignored and getattr(before, name) != getattr(after, name)
        )
    )
    if not changed:
        classification = ChangeClass.NON_MATERIAL
        invalidated = frozenset()
    else:
        classification = max(CHANGE_IMPACTS[name][0] for name in changed)
        invalidated = frozenset().union(*(CHANGE_IMPACTS[name][1] for name in changed))
    routes = {
        ChangeClass.NON_MATERIAL: "AUTOMATED_REGRESSION",
        ChangeClass.MATERIAL: "TARGETED_REASSESSMENT",
        ChangeClass.MAJOR: "RECERTIFY_AND_REAPPROVE",
        ChangeClass.CRITICAL: "SUSPEND_AND_FULL_REVIEW",
    }
    return ChangeAssessment(
        change_class=classification,
        changed_dimensions=changed,
        invalidated_controls=invalidated,
        route=routes[classification],
        suspend_before_review=classification == ChangeClass.CRITICAL,
    )


ALLOWED_TRANSITIONS: dict[Lifecycle, frozenset[Lifecycle]] = {
    Lifecycle.DRAFT: frozenset({Lifecycle.REGISTERED}),
    Lifecycle.REGISTERED: frozenset(
        {Lifecycle.ASSESSING, Lifecycle.SUSPENDED, Lifecycle.RETIRED}
    ),
    Lifecycle.ASSESSING: frozenset(
        {Lifecycle.VALIDATING, Lifecycle.SUSPENDED, Lifecycle.RETIRED}
    ),
    Lifecycle.VALIDATING: frozenset(
        {Lifecycle.PENDING_APPROVAL, Lifecycle.ASSESSING, Lifecycle.SUSPENDED}
    ),
    Lifecycle.PENDING_APPROVAL: frozenset(
        {Lifecycle.APPROVED, Lifecycle.VALIDATING, Lifecycle.SUSPENDED}
    ),
    Lifecycle.APPROVED: frozenset({Lifecycle.ACTIVE, Lifecycle.SUSPENDED}),
    Lifecycle.ACTIVE: frozenset(
        {
            Lifecycle.RECERTIFICATION_DUE,
            Lifecycle.RESTRICTED,
            Lifecycle.SUSPENDED,
            Lifecycle.RETIRED,
        }
    ),
    Lifecycle.RECERTIFICATION_DUE: frozenset(
        {Lifecycle.ACTIVE, Lifecycle.SUSPENDED, Lifecycle.RETIRED}
    ),
    Lifecycle.RESTRICTED: frozenset(
        {Lifecycle.ACTIVE, Lifecycle.SUSPENDED, Lifecycle.RETIRED}
    ),
    Lifecycle.SUSPENDED: frozenset({Lifecycle.ASSESSING, Lifecycle.RETIRED}),
    Lifecycle.RETIRED: frozenset(),
}


class GovernanceRegistry:
    """Tenant-scoped lifecycle registry with optimistic concurrency."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], RegistryRecord] = {}
        self._lock = Lock()

    def register(
        self, card: AgentCard, now: datetime = REFERENCE_TIME
    ) -> RegistryRecord:
        key = (card.tenant_id, card.agent_id)
        with self._lock:
            if key in self._records:
                raise GovernanceError("AGENT_ALREADY_REGISTERED")
            record = RegistryRecord(
                card=card,
                lifecycle=Lifecycle.REGISTERED,
                record_version=1,
                registered_at=now,
                last_changed_at=now,
            )
            self._records[key] = record
            return record

    def get(self, tenant_id: str, agent_id: str) -> RegistryRecord:
        try:
            return self._records[(tenant_id, agent_id)]
        except KeyError as exc:
            raise GovernanceError("AGENT_NOT_REGISTERED") from exc

    def transition(
        self,
        tenant_id: str,
        agent_id: str,
        target: Lifecycle,
        expected_version: int,
        now: datetime = REFERENCE_TIME,
    ) -> RegistryRecord:
        with self._lock:
            current = self.get(tenant_id, agent_id)
            if current.record_version != expected_version:
                raise GovernanceError("REGISTRY_VERSION_CONFLICT")
            if target not in ALLOWED_TRANSITIONS[current.lifecycle]:
                raise GovernanceError("INVALID_LIFECYCLE_TRANSITION")
            updated = current.model_copy(
                update={
                    "lifecycle": target,
                    "record_version": expected_version + 1,
                    "last_changed_at": now,
                }
            )
            self._records[(tenant_id, agent_id)] = updated
            return updated

    def replace_card(
        self,
        card: AgentCard,
        expected_version: int,
        now: datetime = REFERENCE_TIME,
    ) -> tuple[RegistryRecord, ChangeAssessment]:
        with self._lock:
            current = self.get(card.tenant_id, card.agent_id)
            if current.record_version != expected_version:
                raise GovernanceError("REGISTRY_VERSION_CONFLICT")
            change = assess_change(current.card, card)
            lifecycle = (
                Lifecycle.SUSPENDED
                if change.suspend_before_review
                else Lifecycle.ASSESSING
            )
            updated = current.model_copy(
                update={
                    "card": card,
                    "lifecycle": lifecycle,
                    "record_version": expected_version + 1,
                    "last_changed_at": now,
                }
            )
            self._records[(card.tenant_id, card.agent_id)] = updated
            return updated, change


class RegistryAdminService:
    """Authenticated management boundary in front of the persistence adapter."""

    def __init__(self, registry: GovernanceRegistry) -> None:
        self.registry = registry

    def register(
        self,
        operator: AuthenticatedOperator,
        card: AgentCard,
        now: datetime = REFERENCE_TIME,
    ) -> RegistryRecord:
        require_role(operator, OperatorRole.PORTFOLIO_REGISTRAR, card.tenant_id, now)
        return self.registry.register(card, now)

    def transition(
        self,
        operator: AuthenticatedOperator,
        tenant_id: str,
        agent_id: str,
        target: Lifecycle,
        expected_version: int,
        *,
        gate: GateResult | None = None,
        now: datetime = REFERENCE_TIME,
    ) -> RegistryRecord:
        require_role(operator, OperatorRole.GOVERNANCE_OPERATOR, tenant_id, now)
        record = self.registry.get(tenant_id, agent_id)
        if target in {Lifecycle.APPROVED, Lifecycle.ACTIVE} and (
            gate is None
            or gate.decision != Decision.PASS
            or gate.manifest_digest != manifest_digest(record.card)
            or gate.policy_version != record.card.policy_version
        ):
            raise GovernanceError("PASSING_BOUND_GATE_REQUIRED")
        return self.registry.transition(
            tenant_id, agent_id, target, expected_version, now
        )

    def replace_card(
        self,
        operator: AuthenticatedOperator,
        card: AgentCard,
        expected_version: int,
        now: datetime = REFERENCE_TIME,
    ) -> tuple[RegistryRecord, ChangeAssessment]:
        require_role(operator, OperatorRole.GOVERNANCE_OPERATOR, card.tenant_id, now)
        return self.registry.replace_card(card, expected_version, now)


def recertify(
    record: RegistryRecord,
    evidence: Iterable[EvidenceArtifact],
    approvals: Iterable[ApprovalReceipt],
    open_incidents: Iterable[Incident],
    exceptions: Iterable[ExceptionRecord],
    now: datetime = REFERENCE_TIME,
) -> RecertificationResult:
    card = record.card
    tier = classify_risk(card, now).tier
    evidence_items = tuple(evidence)
    exception_items = tuple(exceptions)
    accepted, evidence_reasons = accepted_evidence_controls(card, evidence_items, now)
    reasons = list(evidence_reasons) + list(supply_chain_findings(card, now))
    reasons.extend(
        f"CONTROL_MISSING:{item}" for item in sorted(CONTROL_BASELINES[tier] - accepted)
    )
    if any(item.status != IncidentStatus.CLOSED for item in open_incidents):
        reasons.append("OPEN_INCIDENT")
    for item in exception_items:
        if item.expires_at <= now:
            reasons.append(f"EXCEPTION_EXPIRED:{item.exception_id}")
    valid_roles: set[OperatorRole] = set()
    ledger = ApprovalLedger()
    release_id = f"recertification:{card.agent_id}:{card.version}"
    package_digest = release_package_digest(
        card, tier, release_id, evidence_items, exception_items
    )
    for approval in approvals:
        try:
            ledger.validate(
                approval,
                card,
                tier,
                release_id,
                now,
                package_digest,
            )
        except GovernanceError:
            continue
        valid_roles.add(approval.approver_role)
    if valid_roles != set(APPROVAL_ROLES[tier]):
        reasons.append("RECERTIFICATION_APPROVALS_INCOMPLETE")
    interval = {
        RiskTier.LOW: timedelta(days=365),
        RiskTier.MODERATE: timedelta(days=180),
        RiskTier.HIGH: timedelta(days=90),
        RiskTier.CRITICAL: timedelta(days=30),
    }[tier]
    return RecertificationResult(
        decision=Decision.PASS if not reasons else Decision.REVIEW,
        reason_codes=tuple(sorted(set(reasons))),
        next_review_at=now + interval if not reasons else None,
    )


class IncidentService:
    """Admits trusted alerts and changes registry state during containment."""

    def __init__(
        self, registry: GovernanceRegistry, trusted_sources: frozenset[str]
    ) -> None:
        self.registry = registry
        self.trusted_sources = trusted_sources
        self._incidents: dict[str, Incident] = {}
        self._alerts: dict[str, str] = {}

    def admit(
        self,
        alert_id: str,
        source_id: str,
        source_digest: str,
        tenant_id: str,
        agent_id: str,
        kind: str,
        severity: IncidentSeverity,
        now: datetime = REFERENCE_TIME,
    ) -> Incident:
        if source_id not in self.trusted_sources:
            raise GovernanceError("ALERT_SOURCE_NOT_TRUSTED")
        if not source_digest.startswith("sha256:") or len(source_digest) != 71:
            raise GovernanceError("ALERT_DIGEST_INVALID")
        if alert_id in self._alerts:
            return self._incidents[self._alerts[alert_id]]
        self.registry.get(tenant_id, agent_id)
        incident_id = f"incident-{stable_digest((alert_id, source_digest))[:16]}"
        incident = Incident(
            incident_id=incident_id,
            alert_id=alert_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            severity=severity,
            kind=kind,
            source_id=source_id,
            source_digest=source_digest,
            status=IncidentStatus.OPEN,
            opened_at=now,
        )
        self._alerts[alert_id] = incident_id
        self._incidents[incident_id] = incident
        return incident

    def contain(
        self,
        incident_id: str,
        operator: AuthenticatedOperator,
        evidence_ids: tuple[str, ...],
        now: datetime = REFERENCE_TIME,
    ) -> Incident:
        incident = self._incidents[incident_id]
        authenticate(operator, incident.tenant_id, now)
        if OperatorRole.INCIDENT_COMMANDER not in operator.roles:
            raise GovernanceError("INCIDENT_COMMANDER_ROLE_REQUIRED")
        if not evidence_ids:
            raise GovernanceError("INCIDENT_EVIDENCE_REQUIRED")
        record = self.registry.get(incident.tenant_id, incident.agent_id)
        if record.lifecycle not in {Lifecycle.SUSPENDED, Lifecycle.RETIRED}:
            self.registry.transition(
                incident.tenant_id,
                incident.agent_id,
                Lifecycle.SUSPENDED,
                record.record_version,
                now,
            )
        actions = ("REVOKE_DELEGATED_AUTHORITY", "DISABLE_AGENT", "PRESERVE_TRAJECTORY")
        updated = incident.model_copy(
            update={
                "status": IncidentStatus.CONTAINED,
                "contained_at": now,
                "evidence_ids": evidence_ids,
                "containment_actions": actions,
            }
        )
        self._incidents[incident_id] = updated
        return updated

    def request_recovery(
        self,
        incident_id: str,
        operator: AuthenticatedOperator,
        remediation_evidence_id: str,
        now: datetime = REFERENCE_TIME,
    ) -> Incident:
        incident = self._incidents[incident_id]
        authenticate(operator, incident.tenant_id, now)
        if OperatorRole.SECURITY_ASSURANCE not in operator.roles:
            raise GovernanceError("SECURITY_ASSURANCE_ROLE_REQUIRED")
        if incident.status != IncidentStatus.CONTAINED:
            raise GovernanceError("INCIDENT_NOT_CONTAINED")
        updated = incident.model_copy(
            update={
                "status": IncidentStatus.RECOVERY_REVIEW,
                "remediation_evidence_id": remediation_evidence_id,
            }
        )
        self._incidents[incident_id] = updated
        return updated

    def close(
        self,
        incident_id: str,
        operator: AuthenticatedOperator,
        now: datetime = REFERENCE_TIME,
    ) -> Incident:
        incident = self._incidents[incident_id]
        authenticate(operator, incident.tenant_id, now)
        if OperatorRole.AI_RISK not in operator.roles:
            raise GovernanceError("AI_RISK_ROLE_REQUIRED")
        if (
            incident.status != IncidentStatus.RECOVERY_REVIEW
            or not incident.remediation_evidence_id
        ):
            raise GovernanceError("RECOVERY_EVIDENCE_REQUIRED")
        updated = incident.model_copy(
            update={"status": IncidentStatus.CLOSED, "closed_at": now}
        )
        self._incidents[incident_id] = updated
        return updated


def export_cyclonedx(card: AgentCard) -> dict[str, object]:
    kind_map = {
        DependencyKind.MODEL: ComponentType.MACHINE_LEARNING_MODEL,
        DependencyKind.LIBRARY: ComponentType.LIBRARY,
        DependencyKind.CONTAINER: ComponentType.CONTAINER,
        DependencyKind.DATA: ComponentType.DATA,
        DependencyKind.TOOL: ComponentType.APPLICATION,
        DependencyKind.MCP_SERVER: ComponentType.APPLICATION,
        DependencyKind.API: ComponentType.APPLICATION,
        DependencyKind.AGENT: ComponentType.APPLICATION,
    }
    components = []
    for item in card.dependencies:
        components.append(
            Component(
                name=item.dependency_id,
                version=item.version,
                type=kind_map[item.kind],
                bom_ref=f"urn:course16:{card.tenant_id}:{item.dependency_id}:{item.version}",
                hashes=[
                    HashType(
                        alg=HashAlgorithm.SHA_256,
                        content=item.digest.removeprefix("sha256:"),
                    )
                ],
                properties=[
                    Property(name="course16:provider", value=item.provider),
                    Property(
                        name="course16:third-party", value=str(item.third_party).lower()
                    ),
                    Property(name="course16:license", value=item.license_id),
                    Property(
                        name="course16:approved", value=str(item.approved).lower()
                    ),
                ],
            )
        )
    serial = uuid5(NAMESPACE_URL, f"{card.tenant_id}/{card.agent_id}/{card.version}")
    output = JsonV1Dot7(
        Bom(components=components, serial_number=serial, version=1)
    ).output_as_string()
    return json.loads(output)


def build_audit_package(
    record: RegistryRecord,
    assessment: RiskAssessment,
    gate: GateResult,
    evidence: Iterable[EvidenceArtifact],
    approvals: Iterable[ApprovalReceipt],
    exceptions: Iterable[ExceptionRecord] = (),
    incidents: Iterable[Incident] = (),
    now: datetime = REFERENCE_TIME,
) -> dict[str, object]:
    if gate.manifest_digest != manifest_digest(record.card):
        raise GovernanceError("AUDIT_GATE_MANIFEST_MISMATCH")
    if assessment.manifest_digest != manifest_digest(record.card):
        raise GovernanceError("AUDIT_ASSESSMENT_MANIFEST_MISMATCH")
    payload: dict[str, object] = {
        "schema": "governance.oneplusi.io/audit-package/v1",
        "generated_at": now,
        "registry_record": record,
        "risk_assessment": assessment,
        "release_gate": gate,
        "evidence": tuple(evidence),
        "approvals": tuple(approvals),
        "exceptions": tuple(exceptions),
        "incidents": tuple(incidents),
    }
    package_digest = sha256_id(payload)
    return {
        "package": _canonical(payload),
        "package_digest": package_digest,
        "signature": _sign_receipt({"package_digest": package_digest}),
    }


def verify_audit_package(package: dict[str, object]) -> bool:
    body = package.get("package")
    package_digest = package.get("package_digest")
    signature = package.get("signature")
    if not isinstance(package_digest, str) or not isinstance(signature, str):
        return False
    return package_digest == sha256_id(body) and hmac.compare_digest(
        signature, _sign_receipt({"package_digest": package_digest})
    )


def build_interoperability_artifacts(card: AgentCard) -> dict[str, object]:
    """Build real offline CycloneDX, Sigstore-policy, SLSA and OTel artifacts."""

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
    from sigstore.verify.policy import Identity

    sigstore_identity = {
        "identity": "https://github.com/acme/agents/.github/workflows/release.yml@refs/heads/main",
        "issuer": "https://token.actions.githubusercontent.com",
    }
    sigstore_policy = Identity(
        identity=sigstore_identity["identity"], issuer=sigstore_identity["issuer"]
    )
    slsa_statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": f"{card.agent_id}:{card.version}",
                "digest": {"sha256": manifest_digest(card).removeprefix("sha256:")},
            }
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://governance.oneplusi.io/AgentRelease/v1",
                "externalParameters": {"promptDigest": card.prompt_digest},
                "resolvedDependencies": [
                    {
                        "uri": f"urn:dependency:{item.dependency_id}:{item.version}",
                        "digest": {"sha256": item.digest.removeprefix("sha256:")},
                    }
                    for item in card.dependencies
                ],
            },
            "runDetails": {"builder": {"id": "https://github.com/acme/agents/actions"}},
        },
    }
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("course16.governance")
    with tracer.start_as_current_span("governance.release_gate") as span:
        span.set_attribute("governance.agent.id", card.agent_id)
        span.set_attribute("governance.agent.version", card.version)
        span.set_attribute("governance.policy.version", card.policy_version)
        span.set_attribute("governance.manifest.digest", manifest_digest(card))
    spans = exporter.get_finished_spans()
    return {
        "versions": {
            "cyclonedx-python-lib": package_version("cyclonedx-python-lib"),
            "sigstore": package_version("sigstore"),
            "opentelemetry-sdk": package_version("opentelemetry-sdk"),
            "pydantic": package_version("pydantic"),
        },
        "cyclonedx_bom": export_cyclonedx(card),
        "sigstore_identity_policy": sigstore_policy,
        "sigstore_identity": sigstore_identity,
        "slsa_statement": slsa_statement,
        "otel_spans": tuple(
            {
                "name": item.name,
                "attributes": dict(item.attributes or {}),
                "trace_id": f"{item.context.trace_id:032x}",
            }
            for item in spans
        ),
    }


def make_dependency(
    dependency_id: str,
    kind: DependencyKind,
    version: str,
    *,
    third_party: bool = False,
    approved: bool = True,
    capabilities: frozenset[str] = frozenset(),
    review_expires_at: datetime | None = None,
) -> Dependency:
    return Dependency(
        dependency_id=dependency_id,
        kind=kind,
        version=version,
        provider="external-provider" if third_party else "acme-platform",
        third_party=third_party,
        digest=sha256_id((dependency_id, version)),
        license_id="LicenseRef-Commercial" if third_party else "Apache-2.0",
        approved=approved,
        review_expires_at=(review_expires_at or REFERENCE_TIME + timedelta(days=180))
        if third_party
        else None,
        capabilities=capabilities,
    )


def build_procurement_card(
    *,
    tenant_id: str = TENANT_ACME,
    version: str = "3.2.0",
    permissions: frozenset[str] | None = None,
    dependencies: tuple[Dependency, ...] | None = None,
    external_actions: bool = True,
    regulatory_scopes: frozenset[str] = frozenset(),
) -> AgentCard:
    return AgentCard(
        tenant_id=tenant_id,
        agent_id="procurement-agent",
        version=version,
        business_owner_id="owner-procurement",
        technical_owner_id="owner-ai-engineering",
        data_owner_id="owner-procurement-data",
        purpose="Prepare bounded purchase orders for approved enterprise vendors",
        intended_users=frozenset({"procurement-analyst"}),
        prohibited_uses=frozenset({"vendor-creation", "unapproved-vendor-payment"}),
        autonomy=2,
        impact=3,
        access=3,
        irreversibility=2,
        data_sensitivity=2,
        external_actions=external_actions,
        permissions=permissions or frozenset({"vendor.read", "purchase-order.create"}),
        dependencies=dependencies
        or (
            make_dependency(
                "foundation-model-x", DependencyKind.MODEL, "2026-09", third_party=True
            ),
            make_dependency(
                "procurement-mcp",
                DependencyKind.MCP_SERVER,
                "1.4.2",
                capabilities=frozenset({"vendor.read", "purchase-order.create"}),
            ),
            make_dependency("vendor-master", DependencyKind.DATA, "2026.10.01"),
        ),
        regulatory_scopes=regulatory_scopes,
        policy_version=POLICY_VERSION,
        prompt_digest=sha256_id("procurement-system-prompt-v12"),
        deployment_environment="production-ca",
    )


def make_evidence(
    card: AgentCard,
    control_id: str,
    *,
    evidence_id: str | None = None,
    status: EvidenceStatus = EvidenceStatus.PASS,
    expires_at: datetime | None = None,
    tenant_id: str | None = None,
    version: str | None = None,
    bound_digest: str | None = None,
    policy_version: str | None = None,
) -> EvidenceArtifact:
    identifier = evidence_id or f"evidence-{control_id}"
    payload: dict[str, object] = {
        "evidence_id": identifier,
        "tenant_id": tenant_id or card.tenant_id,
        "agent_id": card.agent_id,
        "agent_version": version or card.version,
        "manifest_digest": bound_digest or manifest_digest(card),
        "control_id": control_id,
        "producer_id": f"producer-{control_id}",
        "assessor_id": f"assessor-{control_id}",
        "status": status,
        "source_uri": f"evidence://course16/{identifier}",
        "artifact_digest": sha256_id((identifier, control_id, status.value)),
        "policy_version": policy_version or card.policy_version,
        "generated_at": REFERENCE_TIME - timedelta(days=1),
        "expires_at": expires_at or REFERENCE_TIME + timedelta(days=90),
    }
    return EvidenceArtifact(**payload, signature=_sign_receipt(payload))


def complete_evidence(
    card: AgentCard, tier: RiskTier | None = None
) -> tuple[EvidenceArtifact, ...]:
    selected = tier or classify_risk(card).tier
    return tuple(
        make_evidence(card, control) for control in sorted(CONTROL_BASELINES[selected])
    )


def complete_approvals(
    card: AgentCard,
    release_id: str,
    ledger: ApprovalLedger,
    tier: RiskTier | None = None,
    evidence: Iterable[EvidenceArtifact] | None = None,
    exceptions: Iterable[ExceptionRecord] = (),
    now: datetime = REFERENCE_TIME,
) -> tuple[ApprovalReceipt, ...]:
    selected = tier or classify_risk(card, now).tier
    evidence_items = (
        tuple(evidence) if evidence is not None else complete_evidence(card, selected)
    )
    exception_items = tuple(exceptions)
    package_digest = release_package_digest(
        card, selected, release_id, evidence_items, exception_items
    )
    receipts = []
    for role in sorted(APPROVAL_ROLES[selected], key=str):
        operator = build_operator(
            role,
            operator_id=f"independent-{role.value}",
            tenant_id=card.tenant_id,
            now=now,
        )
        receipts.append(
            ledger.issue(
                operator,
                card,
                selected,
                release_id,
                role,
                frozenset({"approved-vendors-only", "maximum-po-cad-15000"}),
                now,
                package_digest=package_digest,
            )
        )
    return tuple(receipts)


def build_scenarios() -> tuple[Scenario, ...]:
    release_id = "release-course16-eval"
    valid = build_procurement_card()
    evidence = complete_evidence(valid)
    approvals = complete_approvals(
        valid, release_id, ApprovalLedger(), evidence=evidence
    )

    def approvals_for(
        card: AgentCard,
        records: tuple[EvidenceArtifact, ...],
        exceptions: tuple[ExceptionRecord, ...] = (),
        *,
        now: datetime = REFERENCE_TIME,
    ) -> tuple[ApprovalReceipt, ...]:
        return complete_approvals(
            card,
            release_id,
            ApprovalLedger(),
            evidence=records,
            exceptions=exceptions,
            now=now,
        )

    stale = list(evidence)
    stale[0] = make_evidence(valid, stale[0].control_id, expires_at=REFERENCE_TIME)
    stale_evidence = tuple(stale)
    wrong_version = valid.model_copy(update={"version": "3.3.0"})
    unapproved_dependency = make_dependency(
        "procurement-mcp",
        DependencyKind.MCP_SERVER,
        "1.5.0",
        approved=False,
        capabilities=frozenset(
            {"vendor.read", "purchase-order.create", "vendor.create"}
        ),
    )
    drifted = build_procurement_card(
        version="3.3.0",
        permissions=frozenset(
            {"vendor.read", "purchase-order.create", "vendor.create"}
        ),
        dependencies=(
            valid.dependencies[0],
            unapproved_dependency,
            valid.dependencies[2],
        ),
    )
    drifted_evidence = complete_evidence(drifted)
    missing_control = evidence[1:]
    wrong_tenant = list(evidence)
    wrong_tenant[0] = make_evidence(
        valid, wrong_tenant[0].control_id, tenant_id=TENANT_GLOBEX
    )
    wrong_tenant_evidence = tuple(wrong_tenant)
    old_policy = list(evidence)
    old_policy[0] = make_evidence(
        valid, old_policy[0].control_id, policy_version="old-policy/15"
    )
    old_policy_evidence = tuple(old_policy)
    forged = list(evidence)
    forged[0] = forged[0].model_copy(update={"signature": "0" * 64})
    forged_evidence = tuple(forged)
    tampered_approval = approvals[0].model_copy(
        update={"constraints": frozenset({"unbounded"})}
    )
    expired_approvals = approvals_for(
        valid, evidence, now=REFERENCE_TIME - timedelta(days=31)
    )
    expired_vendor = make_dependency(
        "foundation-model-x",
        DependencyKind.MODEL,
        "2026-09",
        third_party=True,
        review_expires_at=REFERENCE_TIME,
    )
    expired_vendor_card = build_procurement_card(
        version="3.3.0",
        dependencies=(expired_vendor, valid.dependencies[1], valid.dependencies[2]),
    )
    expired_vendor_evidence = complete_evidence(expired_vendor_card)
    exception_evidence = tuple(
        item for item in evidence if item.control_id != "red_team"
    )
    exception = create_exception(
        build_operator(OperatorRole.AI_RISK, "risk-acceptor"),
        valid,
        "red_team",
        "Independent testing is delayed by a bounded vendor scheduling issue.",
        frozenset({"reduced-autonomy", "enhanced-monitoring"}),
        "Complete independent red-team testing within fourteen days.",
    )
    exception_approvals = approvals_for(valid, exception_evidence, (exception,))
    return (
        Scenario(
            scenario_id="valid-release",
            card=valid,
            evidence=evidence,
            approvals=approvals,
            expected=Decision.PASS,
            label="valid",
        ),
        Scenario(
            scenario_id="valid-bounded-exception",
            card=valid,
            evidence=exception_evidence,
            approvals=exception_approvals,
            exceptions=(exception,),
            expected=Decision.PASS,
            label="valid",
        ),
        Scenario(
            scenario_id="stale-evidence",
            card=valid,
            evidence=stale_evidence,
            approvals=approvals_for(valid, stale_evidence),
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="version-mismatch",
            card=wrong_version,
            evidence=evidence,
            approvals=approvals,
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="supply-chain-drift",
            card=drifted,
            evidence=drifted_evidence,
            approvals=approvals_for(drifted, drifted_evidence),
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="missing-independent-approval",
            card=valid,
            evidence=evidence,
            approvals=approvals[:-1],
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="forged-evidence",
            card=valid,
            evidence=forged_evidence,
            approvals=approvals_for(valid, forged_evidence),
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="missing-required-control",
            card=valid,
            evidence=missing_control,
            approvals=approvals_for(valid, missing_control),
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="cross-tenant-evidence",
            card=valid,
            evidence=wrong_tenant_evidence,
            approvals=approvals_for(valid, wrong_tenant_evidence),
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="stale-policy-evidence",
            card=valid,
            evidence=old_policy_evidence,
            approvals=approvals_for(valid, old_policy_evidence),
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="tampered-approval",
            card=valid,
            evidence=evidence,
            approvals=(tampered_approval,) + approvals[1:],
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="expired-approval",
            card=valid,
            evidence=evidence,
            approvals=expired_approvals,
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="expired-third-party-review",
            card=expired_vendor_card,
            evidence=expired_vendor_evidence,
            approvals=approvals_for(expired_vendor_card, expired_vendor_evidence),
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="exception-tampering",
            card=valid,
            evidence=exception_evidence,
            approvals=exception_approvals,
            exceptions=(exception.model_copy(update={"signature": "0" * 64}),),
            expected=Decision.BLOCK,
            label="unsafe",
        ),
        Scenario(
            scenario_id="policy-bound-approval-package",
            card=valid,
            evidence=evidence + (make_evidence(valid, "optional_new_evidence"),),
            approvals=approvals,
            expected=Decision.BLOCK,
            label="unsafe",
        ),
    )


def evaluate_operating_model(scenarios: Iterable[Scenario]) -> dict[str, object]:
    rows = []
    for scenario in scenarios:
        release_id = "release-course16-eval"
        baseline = manual_checklist_baseline(
            scenario.card, scenario.evidence, scenario.approvals
        )
        governed = gate_release(
            scenario.card,
            scenario.evidence,
            scenario.approvals,
            release_id,
            ApprovalLedger(),
            scenario.exceptions,
        ).decision
        rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "label": scenario.label,
                "expected": scenario.expected.value,
                "baseline": baseline.value,
                "governed": governed.value,
            }
        )
    total = len(rows)
    unsafe = [row for row in rows if row["label"] == "unsafe"]
    valid = [row for row in rows if row["label"] == "valid"]
    baseline_correct = sum(row["baseline"] == row["expected"] for row in rows)
    governed_correct = sum(row["governed"] == row["expected"] for row in rows)
    blocked_unsafe = sum(row["governed"] == Decision.BLOCK.value for row in unsafe)
    passed_valid = sum(row["governed"] == Decision.PASS.value for row in valid)
    return {
        "rows": rows,
        "metrics": {
            "baseline_decision_correctness": {
                "numerator": baseline_correct,
                "denominator": total,
                "value": baseline_correct / total,
            },
            "governed_decision_correctness": {
                "numerator": governed_correct,
                "denominator": total,
                "value": governed_correct / total,
            },
            "unsafe_release_prevention": {
                "numerator": blocked_unsafe,
                "denominator": len(unsafe),
                "value": blocked_unsafe / len(unsafe),
            },
            "valid_release_pass_rate": {
                "numerator": passed_valid,
                "denominator": len(valid),
                "value": passed_valid / len(valid),
            },
        },
    }


def portfolio_metrics(
    records: Iterable[RegistryRecord], now: datetime = REFERENCE_TIME
) -> dict[str, object]:
    items = tuple(records)
    total = len(items)
    high_critical = sum(
        classify_risk(item.card, now).tier >= RiskTier.HIGH for item in items
    )
    third_party = sum(
        any(dep.third_party for dep in item.card.dependencies) for item in items
    )
    overdue = sum(
        item.next_recertification_at is not None and item.next_recertification_at <= now
        for item in items
    )
    active = sum(item.lifecycle == Lifecycle.ACTIVE for item in items)
    denominator = total or 1
    return {
        "population": "registered agent records in the supplied portfolio snapshot",
        "as_of": now.isoformat(),
        "total_agents": total,
        "high_or_critical": {
            "numerator": high_critical,
            "denominator": total,
            "rate": high_critical / denominator,
        },
        "third_party_exposed": {
            "numerator": third_party,
            "denominator": total,
            "rate": third_party / denominator,
        },
        "recertification_overdue": {
            "numerator": overdue,
            "denominator": total,
            "rate": overdue / denominator,
        },
        "active": {
            "numerator": active,
            "denominator": total,
            "rate": active / denominator,
        },
    }


def build_course16_reference_run() -> dict[str, object]:
    card = build_procurement_card()
    assessment = classify_risk(card)
    ledger = ApprovalLedger()
    release_id = "release-course16-reference"
    evidence = complete_evidence(card, assessment.tier)
    approvals = complete_approvals(card, release_id, ledger, assessment.tier)
    gate = gate_release(card, evidence, approvals, release_id, ledger, consume=True)
    registry = GovernanceRegistry()
    admin = RegistryAdminService(registry)
    registered = admin.register(build_operator(OperatorRole.PORTFOLIO_REGISTRAR), card)
    bom = export_cyclonedx(card)
    audit = build_audit_package(registered, assessment, gate, evidence, approvals)
    interoperability = build_interoperability_artifacts(card)
    evaluation = evaluate_operating_model(build_scenarios())
    return {
        "card": card,
        "assessment": assessment,
        "gate": gate,
        "registered": registered,
        "bom": bom,
        "audit": audit,
        "interoperability": interoperability,
        "evaluation": evaluation,
    }
