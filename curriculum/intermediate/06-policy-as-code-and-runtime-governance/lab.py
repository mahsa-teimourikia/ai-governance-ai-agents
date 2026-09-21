"""Deterministic policy-as-code and runtime-governance lab for Course 6.

The lab models a small enterprise procurement policy control plane and a
non-bypassable runtime gateway.  It deliberately separates model proposals,
trusted application facts, policy decisions, release state, and verified
effects.  Everything runs locally without credentials; production engine
examples are emitted as artifacts rather than contacted over the network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
from threading import Lock
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator


REFERENCE_TIME = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
SCHEMA_VERSION = "procurement-input/v1"
REQUIRED_DOMAINS = frozenset({"authorization", "business", "risk", "safety"})


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical(value: object) -> object:
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {str(key): _canonical(child) for key, child in value.items()}
    if isinstance(value, (set, frozenset)):
        values = [_canonical(child) for child in value]
        return sorted(values, key=lambda child: json.dumps(child, sort_keys=True))
    if isinstance(value, (tuple, list)):
        return [_canonical(child) for child in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def stable_digest(value: object) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Outcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


class ReleaseStage(str, Enum):
    DRAFT = "draft"
    SHADOW = "shadow"
    CANARY = "canary"
    ACTIVE = "active"
    RETIRED = "retired"


class EffectStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    APPLIED = "applied"
    UNKNOWN = "unknown"


class AuthenticatedContext(FrozenModel):
    subject_id: str
    workload_id: str
    tenant_id: str
    task_id: str
    authenticated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def positive_lifetime(self) -> "AuthenticatedContext":
        if self.valid_until <= self.authenticated_at:
            raise ValueError("authenticated context must have a positive lifetime")
        return self


class ActionProposal(FrozenModel):
    operation_id: str = Field(pattern=r"^OP-[A-Z0-9-]+$")
    action: str
    vendor_id: str
    amount_cents: int = Field(ge=0)
    country: str = Field(min_length=2, max_length=2)
    data_classification: str = "internal"
    destination: str = "procurement-system"
    # These fields are untrusted model assertions and are never policy facts.
    model_claimed_approval: bool = False
    model_claimed_vendor_safe: bool = False


class TrustedFacts(FrozenModel):
    operation_id: str
    proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tenant_id: str
    authorization_permitted: bool
    authorization_version: str
    vendor_approved: bool
    vendor_sanctioned: bool
    vendor_version: str
    risk_basis_points: int = Field(ge=0, le=10_000)
    risk_version: str
    observed_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def positive_lifetime(self) -> "TrustedFacts":
        if self.valid_until <= self.observed_at:
            raise ValueError("trusted facts must have a positive lifetime")
        return self


class PolicyRules(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    supported_actions: frozenset[str] = frozenset({"purchase_order:create"})
    allowed_countries: frozenset[str] = frozenset({"CA", "US"})
    approval_threshold_cents: int = Field(default=500_000, ge=0)
    hard_amount_limit_cents: int = Field(default=2_000_000, ge=0)
    risk_escalation_basis_points: int = Field(default=5_000, ge=0, le=10_000)
    risk_deny_basis_points: int = Field(default=8_000, ge=0, le=10_000)
    external_destinations: frozenset[str] = frozenset({"external-webhook"})
    restricted_classifications: frozenset[str] = frozenset({"restricted", "secret"})


class PolicyBundle(FrozenModel):
    version: str
    revision: str
    stage: ReleaseStage
    rules: PolicyRules
    required_domains: frozenset[str] = REQUIRED_DOMAINS
    created_at: datetime = REFERENCE_TIME

    @property
    def digest(self) -> str:
        return stable_digest(
            {
                "version": self.version,
                "revision": self.revision,
                "rules": self.rules,
                "required_domains": self.required_domains,
            }
        )


class ValidationFinding(FrozenModel):
    code: str
    message: str


class ValidationReport(FrozenModel):
    bundle_version: str
    bundle_digest: str
    valid: bool
    findings: tuple[ValidationFinding, ...]


class DomainDecision(FrozenModel):
    domain: str
    outcome: Outcome
    reason_codes: tuple[str, ...]


class CompositeDecision(FrozenModel):
    outcome: Outcome
    reason_codes: tuple[str, ...]
    domain_decisions: tuple[DomainDecision, ...]
    bundle_version: str
    bundle_revision: str
    bundle_digest: str
    input_digest: str


class RuntimeDecision(FrozenModel):
    decision_id: str
    tenant_id: str
    operation_id: str
    enforced: CompositeDecision
    shadow: CompositeDecision | None
    rollout_stage: ReleaseStage
    evidence_versions: tuple[str, ...]
    decided_at: datetime
    replayed: bool = False


class EffectResult(FrozenModel):
    effect_id: str | None
    tenant_id: str
    operation_id: str
    status: EffectStatus
    proposal_digest: str


class EnforcementResult(FrozenModel):
    decision: RuntimeDecision
    effect: EffectResult


class DecisionAuditEvent(FrozenModel):
    """Privacy-aware observable evidence, not a dump of raw policy inputs."""

    decision_id: str
    tenant_id: str
    operation_id: str
    request_digest: str
    outcome: Outcome
    reason_codes: tuple[str, ...]
    bundle_version: str
    bundle_revision: str
    bundle_digest: str
    rollout_stage: ReleaseStage
    shadow_outcome: Outcome | None
    evidence_versions: tuple[str, ...]
    decided_at: datetime


class EvaluationCase(FrozenModel):
    name: str
    context: AuthenticatedContext
    proposal: ActionProposal
    facts: TrustedFacts | None
    expected: Outcome


class EvaluationSummary(FrozenModel):
    case_count: int
    expected_allow_count: int
    expected_deny_count: int
    expected_escalate_count: int
    baseline_correct_count: int
    candidate_correct_count: int
    forbidden_case_count: int
    baseline_forbidden_allowed_count: int
    candidate_forbidden_allowed_count: int
    legitimate_case_count: int
    baseline_false_denial_count: int
    candidate_false_denial_count: int
    escalation_case_count: int
    baseline_missed_escalation_count: int
    candidate_missed_escalation_count: int


class ShadowMetrics(FrozenModel):
    active_bundle_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_bundle_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluation_corpus_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_count: int
    disagreement_count: int
    decision_flip_rate: float
    incorrect_case_count: int
    false_permit_count: int
    forbidden_not_denied_count: int
    false_denial_count: int
    missed_escalation_count: int


def validate_bundle(bundle: PolicyBundle) -> ValidationReport:
    """Perform deterministic schema/static checks before a release can advance."""

    findings: list[ValidationFinding] = []
    rules = bundle.rules
    if rules.schema_version != SCHEMA_VERSION:
        findings.append(
            ValidationFinding(
                code="schema_version_mismatch",
                message=f"expected {SCHEMA_VERSION}, got {rules.schema_version}",
            )
        )
    if not rules.supported_actions:
        findings.append(
            ValidationFinding(
                code="no_supported_actions", message="at least one action is required"
            )
        )
    missing = REQUIRED_DOMAINS - bundle.required_domains
    if missing:
        findings.append(
            ValidationFinding(
                code="required_domain_missing",
                message=f"missing domains: {', '.join(sorted(missing))}",
            )
        )
    if rules.approval_threshold_cents >= rules.hard_amount_limit_cents:
        findings.append(
            ValidationFinding(
                code="amount_thresholds_unsatisfiable",
                message="approval threshold must be below the hard amount limit",
            )
        )
    if rules.risk_escalation_basis_points >= rules.risk_deny_basis_points:
        findings.append(
            ValidationFinding(
                code="risk_thresholds_unsatisfiable",
                message="risk escalation threshold must be below the deny threshold",
            )
        )
    return ValidationReport(
        bundle_version=bundle.version,
        bundle_digest=bundle.digest,
        valid=not findings,
        findings=tuple(findings),
    )


def resolve_input_digest(
    context: AuthenticatedContext,
    proposal: ActionProposal,
    facts: TrustedFacts | None,
) -> str:
    return stable_digest({"context": context, "proposal": proposal, "facts": facts})


def _domain(domain: str, outcome: Outcome, *reasons: str) -> DomainDecision:
    return DomainDecision(domain=domain, outcome=outcome, reason_codes=tuple(reasons))


def evaluate_policy(
    bundle: PolicyBundle,
    context: AuthenticatedContext,
    proposal: ActionProposal,
    facts: TrustedFacts | None,
    *,
    now: datetime,
) -> CompositeDecision:
    """Evaluate every required domain and compose DENY > ESCALATE > ALLOW."""

    rules = bundle.rules
    domains: list[DomainDecision] = []

    auth_reasons: list[str] = []
    if not (context.authenticated_at <= now < context.valid_until):
        auth_reasons.append("identity_context_not_current")
    if facts is None:
        auth_reasons.append("trusted_facts_missing")
    else:
        if facts.operation_id != proposal.operation_id:
            auth_reasons.append("facts_operation_mismatch")
        if facts.proposal_digest != stable_digest(proposal):
            auth_reasons.append("facts_proposal_mismatch")
        if facts.tenant_id != context.tenant_id:
            auth_reasons.append("facts_tenant_mismatch")
        if not (facts.observed_at <= now < facts.valid_until):
            auth_reasons.append("trusted_facts_not_current")
        if not facts.authorization_permitted:
            auth_reasons.append("authorization_denied")
    domains.append(
        _domain(
            "authorization",
            Outcome.DENY if auth_reasons else Outcome.ALLOW,
            *(auth_reasons or ["trusted_authorization_satisfied"]),
        )
    )

    business_reasons: list[str] = []
    if proposal.action not in rules.supported_actions:
        business_reasons.append("unsupported_action")
    if proposal.country not in rules.allowed_countries:
        business_reasons.append("country_not_allowed")
    if proposal.amount_cents > rules.hard_amount_limit_cents:
        business_reasons.append("hard_amount_limit_exceeded")
    if facts is not None:
        if not facts.vendor_approved:
            business_reasons.append("vendor_not_approved")
        if facts.vendor_sanctioned:
            business_reasons.append("vendor_sanctioned")
    domains.append(
        _domain(
            "business",
            Outcome.DENY if business_reasons else Outcome.ALLOW,
            *(business_reasons or ["business_constraints_satisfied"]),
        )
    )

    risk_denials: list[str] = []
    risk_escalations: list[str] = []
    if facts is not None and facts.risk_basis_points >= rules.risk_deny_basis_points:
        risk_denials.append("risk_hard_limit_reached")
    elif facts is not None and facts.risk_basis_points >= rules.risk_escalation_basis_points:
        risk_escalations.append("risk_requires_approval")
    if proposal.amount_cents > rules.approval_threshold_cents:
        risk_escalations.append("amount_requires_approval")
    risk_outcome = (
        Outcome.DENY
        if risk_denials
        else Outcome.ESCALATE
        if risk_escalations
        else Outcome.ALLOW
    )
    domains.append(
        _domain(
            "risk",
            risk_outcome,
            *(risk_denials or risk_escalations or ["risk_within_autonomous_bounds"]),
        )
    )

    safety_reasons: list[str] = []
    if (
        proposal.destination in rules.external_destinations
        and proposal.data_classification in rules.restricted_classifications
    ):
        safety_reasons.append("restricted_data_external_destination")
    domains.append(
        _domain(
            "safety",
            Outcome.DENY if safety_reasons else Outcome.ALLOW,
            *(safety_reasons or ["data_destination_allowed"]),
        )
    )

    present = {item.domain for item in domains}
    if missing := bundle.required_domains - present:
        domains.append(
            _domain("composition", Outcome.DENY, *[f"domain_missing:{x}" for x in sorted(missing)])
        )
    if any(item.outcome is Outcome.DENY for item in domains):
        outcome = Outcome.DENY
    elif any(item.outcome is Outcome.ESCALATE for item in domains):
        outcome = Outcome.ESCALATE
    else:
        outcome = Outcome.ALLOW
    reasons = tuple(
        sorted(
            {
                reason
                for item in domains
                if item.outcome is outcome
                for reason in item.reason_codes
            }
        )
    )
    return CompositeDecision(
        outcome=outcome,
        reason_codes=reasons,
        domain_decisions=tuple(domains),
        bundle_version=bundle.version,
        bundle_revision=bundle.revision,
        bundle_digest=bundle.digest,
        input_digest=resolve_input_digest(context, proposal, facts),
    )


def unsafe_first_match_baseline(
    context: AuthenticatedContext,
    proposal: ActionProposal,
    facts: TrustedFacts | None,
) -> Outcome:
    """Deliberately unsafe baseline: broad allow runs before deny/escalate rules."""

    if context.workload_id.startswith("agent:procurement"):
        return Outcome.ALLOW
    if facts is None or facts.vendor_sanctioned:
        return Outcome.DENY
    if proposal.amount_cents > 500_000:
        return Outcome.ESCALATE
    return Outcome.DENY


class PolicyControlPlane:
    """Thread-safe teaching registry with explicit promotion and rollback."""

    def __init__(
        self,
        initial: PolicyBundle,
        *,
        release_corpus_digest: str | None = None,
    ) -> None:
        report = validate_bundle(initial)
        if not report.valid:
            raise ValueError("initial bundle is invalid")
        self._lock = Lock()
        active = initial.model_copy(update={"stage": ReleaseStage.ACTIVE})
        self._bundles = {active.version: active}
        self._active_version = active.version
        self._candidate_version: str | None = None
        self._canary_percent = 0
        self._available = True
        self._release_corpus_digest = (
            release_corpus_digest or stable_digest(labelled_cases())
        )

    def set_available(self, available: bool) -> None:
        with self._lock:
            self._available = available

    def snapshot(self) -> tuple[PolicyBundle, PolicyBundle | None, int]:
        with self._lock:
            if not self._available:
                raise RuntimeError("policy_control_plane_unavailable")
            active = self._bundles[self._active_version]
            candidate = (
                self._bundles[self._candidate_version]
                if self._candidate_version is not None
                else None
            )
            return active, candidate, self._canary_percent

    def register(self, bundle: PolicyBundle) -> ValidationReport:
        report = validate_bundle(bundle)
        with self._lock:
            if bundle.version in self._bundles:
                raise ValueError("policy version already exists; versions are immutable")
            if report.valid:
                self._bundles[bundle.version] = bundle.model_copy(
                    update={"stage": ReleaseStage.DRAFT}
                )
        return report

    def start_shadow(self, version: str) -> None:
        with self._lock:
            if self._candidate_version is not None:
                raise ValueError("another candidate is already in rollout")
            candidate = self._bundles[version]
            if candidate.stage is not ReleaseStage.DRAFT:
                raise ValueError("only a validated draft can enter shadow")
            self._bundles[version] = candidate.model_copy(
                update={"stage": ReleaseStage.SHADOW}
            )
            self._candidate_version = version
            self._canary_percent = 0

    def start_canary(self, version: str, percent: int) -> None:
        if not 1 <= percent <= 99:
            raise ValueError("canary percent must be between 1 and 99")
        with self._lock:
            if self._candidate_version != version:
                raise ValueError("candidate must complete shadow registration first")
            candidate = self._bundles[version]
            if candidate.stage is not ReleaseStage.SHADOW:
                raise ValueError("only a shadow candidate can enter canary")
            self._bundles[version] = candidate.model_copy(
                update={"stage": ReleaseStage.CANARY}
            )
            self._canary_percent = percent

    def promote(self, version: str, metrics: ShadowMetrics) -> None:
        if metrics.request_count <= 0:
            raise ValueError("release gate requires a non-empty labelled corpus")
        if (
            metrics.incorrect_case_count
            or metrics.forbidden_not_denied_count
            or metrics.missed_escalation_count
        ):
            raise ValueError("release gate failed: safety regression detected")
        with self._lock:
            if self._candidate_version != version:
                raise ValueError("only the current candidate can be promoted")
            previous = self._bundles[self._active_version]
            candidate = self._bundles[version]
            if candidate.stage is not ReleaseStage.CANARY:
                raise ValueError("candidate must pass shadow and canary before promotion")
            if metrics.active_bundle_digest != previous.digest:
                raise ValueError("release evidence is not bound to the active bundle")
            if metrics.candidate_bundle_digest != candidate.digest:
                raise ValueError("release evidence is not bound to the candidate bundle")
            if metrics.evaluation_corpus_digest != self._release_corpus_digest:
                raise ValueError("release evidence is not bound to the approved corpus")
            self._bundles[previous.version] = previous.model_copy(
                update={"stage": ReleaseStage.RETIRED}
            )
            self._bundles[version] = candidate.model_copy(
                update={"stage": ReleaseStage.ACTIVE}
            )
            self._active_version = version
            self._candidate_version = None
            self._canary_percent = 0

    def rollback(self, version: str) -> None:
        with self._lock:
            if version not in self._bundles:
                raise KeyError(version)
            current = self._bundles[self._active_version]
            target = self._bundles[version]
            if target.stage is not ReleaseStage.RETIRED:
                raise ValueError("rollback target must be a previously active bundle")
            if not validate_bundle(target).valid:
                raise ValueError("rollback target no longer validates")
            self._bundles[current.version] = current.model_copy(
                update={"stage": ReleaseStage.RETIRED}
            )
            self._bundles[version] = target.model_copy(
                update={"stage": ReleaseStage.ACTIVE}
            )
            self._active_version = version
            self._candidate_version = None
            self._canary_percent = 0


def _in_canary(operation_id: str, percent: int) -> bool:
    cohort = int(hashlib.sha256(operation_id.encode()).hexdigest()[:8], 16) % 100
    return cohort < percent


class RuntimeGateway:
    """PDP + PEP boundary; model code can propose but cannot invoke effects directly."""

    def __init__(self, control_plane: PolicyControlPlane, adapter: "ProcurementAdapter"):
        self._control_plane = control_plane
        self._adapter = adapter
        self._lock = Lock()
        self._audit_lock = Lock()
        self._decisions: dict[tuple[str, str], tuple[str, RuntimeDecision]] = {}
        self._audit_events: list[DecisionAuditEvent] = []
        self._permit = object()

    @property
    def audit_events(self) -> tuple[DecisionAuditEvent, ...]:
        with self._audit_lock:
            return tuple(self._audit_events)

    def decide(
        self,
        context: AuthenticatedContext,
        proposal: ActionProposal,
        facts: TrustedFacts | None,
        *,
        now: datetime,
    ) -> RuntimeDecision:
        request_digest = resolve_input_digest(context, proposal, facts)
        try:
            active, candidate, canary_percent = self._control_plane.snapshot()
        except RuntimeError:
            fail_bundle = PolicyBundle(
                version="unavailable",
                revision="none",
                stage=ReleaseStage.ACTIVE,
                rules=PolicyRules(),
            )
            fail = CompositeDecision(
                outcome=Outcome.DENY,
                reason_codes=("policy_control_plane_unavailable_fail_closed",),
                domain_decisions=(),
                bundle_version=fail_bundle.version,
                bundle_revision=fail_bundle.revision,
                bundle_digest=fail_bundle.digest,
                input_digest=request_digest,
            )
            decision = self._runtime_decision(
                context, proposal, facts, fail, None, now
            )
            self._record(decision)
            return decision

        active_decision = evaluate_policy(active, context, proposal, facts, now=now)
        candidate_decision = (
            evaluate_policy(candidate, context, proposal, facts, now=now)
            if candidate is not None
            else None
        )
        enforced = active_decision
        shadow = candidate_decision
        stage = ReleaseStage.ACTIVE
        if (
            candidate is not None
            and candidate.stage is ReleaseStage.CANARY
            and _in_canary(proposal.operation_id, canary_percent)
        ):
            enforced, shadow, stage = candidate_decision, active_decision, ReleaseStage.CANARY
        elif candidate is not None:
            stage = candidate.stage
        decision = self._runtime_decision(
            context, proposal, facts, enforced, shadow, now, stage
        )
        self._record(decision)
        return decision

    def _runtime_decision(
        self,
        context: AuthenticatedContext,
        proposal: ActionProposal,
        facts: TrustedFacts | None,
        enforced: CompositeDecision,
        shadow: CompositeDecision | None,
        now: datetime,
        stage: ReleaseStage = ReleaseStage.ACTIVE,
    ) -> RuntimeDecision:
        evidence = ()
        if facts is not None:
            evidence = (
                f"authorization:{facts.authorization_version}",
                f"vendor:{facts.vendor_version}",
                f"risk:{facts.risk_version}",
            )
        material = {
            "operation": proposal.operation_id,
            "decision": enforced,
            "shadow": shadow,
            "time": now,
        }
        return RuntimeDecision(
            decision_id=f"DEC-{stable_digest(material)[:16].upper()}",
            tenant_id=context.tenant_id,
            operation_id=proposal.operation_id,
            enforced=enforced,
            shadow=shadow,
            rollout_stage=stage,
            evidence_versions=evidence,
            decided_at=now,
        )

    def _record(self, decision: RuntimeDecision) -> None:
        event = DecisionAuditEvent(
            decision_id=decision.decision_id,
            tenant_id=decision.tenant_id,
            operation_id=decision.operation_id,
            request_digest=decision.enforced.input_digest,
            outcome=decision.enforced.outcome,
            reason_codes=decision.enforced.reason_codes,
            bundle_version=decision.enforced.bundle_version,
            bundle_revision=decision.enforced.bundle_revision,
            bundle_digest=decision.enforced.bundle_digest,
            rollout_stage=decision.rollout_stage,
            shadow_outcome=(
                decision.shadow.outcome if decision.shadow is not None else None
            ),
            evidence_versions=decision.evidence_versions,
            decided_at=decision.decided_at,
        )
        with self._audit_lock:
            self._audit_events.append(event)

    def execute(
        self,
        context: AuthenticatedContext,
        proposal: ActionProposal,
        facts: TrustedFacts | None,
        *,
        now: datetime,
    ) -> EnforcementResult:
        request_digest = resolve_input_digest(context, proposal, facts)
        key = (context.tenant_id, proposal.operation_id)
        with self._lock:
            previous = self._decisions.get(key)
            if previous:
                previous_digest, decision = previous
                if previous_digest != request_digest:
                    collision = decision.model_copy(
                        update={
                            "enforced": decision.enforced.model_copy(
                                update={
                                    "outcome": Outcome.DENY,
                                    "reason_codes": (
                                        "operation_id_reused_with_different_request",
                                    ),
                                    "input_digest": request_digest,
                                }
                            )
                        }
                    )
                    self._record(collision)
                    return EnforcementResult(
                        decision=collision,
                        effect=_not_attempted(context, proposal),
                    )
                replay = decision.model_copy(update={"replayed": True})
                self._record(replay)
                return EnforcementResult(
                    decision=replay,
                    effect=self._adapter.result_for(
                        context.tenant_id, proposal.operation_id
                    )
                    or EffectResult(
                        effect_id=None,
                        tenant_id=context.tenant_id,
                        operation_id=proposal.operation_id,
                        status=EffectStatus.UNKNOWN,
                        proposal_digest=stable_digest(proposal),
                    ),
                )

            decision = self.decide(context, proposal, facts, now=now)
            if decision.enforced.outcome is not Outcome.ALLOW:
                return EnforcementResult(
                    decision=decision, effect=_not_attempted(context, proposal)
                )
            self._decisions[key] = (request_digest, decision)
            effect = self._adapter.apply(
                context.tenant_id, proposal, permit=self._permit
            )
            return EnforcementResult(decision=decision, effect=effect)


def _not_attempted(
    context: AuthenticatedContext, proposal: ActionProposal
) -> EffectResult:
    return EffectResult(
        effect_id=None,
        tenant_id=context.tenant_id,
        operation_id=proposal.operation_id,
        status=EffectStatus.NOT_ATTEMPTED,
        proposal_digest=stable_digest(proposal),
    )


class ProcurementAdapter:
    """Observable effect adapter that accepts only its paired gateway capability."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._results: dict[tuple[str, str], EffectResult] = {}
        self._authorized_permit: object | None = None

    def bind(self, gateway: RuntimeGateway) -> None:
        if self._authorized_permit is not None:
            raise RuntimeError("adapter is already bound")
        self._authorized_permit = gateway._permit

    @property
    def applied_count(self) -> int:
        with self._lock:
            return len(self._results)

    def result_for(self, tenant_id: str, operation_id: str) -> EffectResult | None:
        with self._lock:
            return self._results.get((tenant_id, operation_id))

    def apply(
        self,
        tenant_id: str,
        proposal: ActionProposal,
        *,
        permit: object | None = None,
    ) -> EffectResult:
        if permit is None or permit is not self._authorized_permit:
            raise PermissionError("direct effect path rejected; use RuntimeGateway")
        with self._lock:
            key = (tenant_id, proposal.operation_id)
            existing = self._results.get(key)
            if existing:
                return existing
            result = EffectResult(
                effect_id=f"PO-{stable_digest({'tenant': tenant_id, 'proposal': proposal})[:12].upper()}",
                tenant_id=tenant_id,
                operation_id=proposal.operation_id,
                status=EffectStatus.APPLIED,
                proposal_digest=stable_digest(proposal),
            )
            self._results[key] = result
            return result


def demo_context(**updates: object) -> AuthenticatedContext:
    values = {
        "subject_id": "human:buyer-123",
        "workload_id": "agent:procurement-v2",
        "tenant_id": "tenant:oneplusi",
        "task_id": "TASK-PO-123",
        "authenticated_at": REFERENCE_TIME - timedelta(minutes=1),
        "valid_until": REFERENCE_TIME + timedelta(minutes=15),
    }
    values.update(updates)
    return AuthenticatedContext(**values)


def demo_proposal(**updates: object) -> ActionProposal:
    values = {
        "operation_id": "OP-PO-001",
        "action": "purchase_order:create",
        "vendor_id": "vendor:acme",
        "amount_cents": 250_000,
        "country": "CA",
        "data_classification": "internal",
        "destination": "procurement-system",
    }
    values.update(updates)
    return ActionProposal(**values)


def demo_facts(proposal: ActionProposal, **updates: object) -> TrustedFacts:
    values = {
        "operation_id": proposal.operation_id,
        "proposal_digest": stable_digest(proposal),
        "tenant_id": "tenant:oneplusi",
        "authorization_permitted": True,
        "authorization_version": "authz-v12",
        "vendor_approved": True,
        "vendor_sanctioned": False,
        "vendor_version": "vendor-v31",
        "risk_basis_points": 2_000,
        "risk_version": "risk-v9",
        "observed_at": REFERENCE_TIME - timedelta(seconds=5),
        "valid_until": REFERENCE_TIME + timedelta(minutes=5),
    }
    values.update(updates)
    return TrustedFacts(**values)


def stable_bundle() -> PolicyBundle:
    return PolicyBundle(
        version="procurement-policy-1.0.0",
        revision="git:6a0f1c2",
        stage=ReleaseStage.ACTIVE,
        rules=PolicyRules(),
    )


def build_demo_gateway(
    bundle: PolicyBundle | None = None,
) -> tuple[PolicyControlPlane, RuntimeGateway, ProcurementAdapter]:
    control_plane = PolicyControlPlane(bundle or stable_bundle())
    adapter = ProcurementAdapter()
    gateway = RuntimeGateway(control_plane, adapter)
    adapter.bind(gateway)
    return control_plane, gateway, adapter


def labelled_cases() -> tuple[EvaluationCase, ...]:
    def case(
        name: str,
        expected: Outcome,
        *,
        context_updates: dict[str, object] | None = None,
        proposal_updates: dict[str, object] | None = None,
        fact_updates: dict[str, object] | None = None,
        missing_facts: bool = False,
    ) -> EvaluationCase:
        context = demo_context(**(context_updates or {}))
        proposal = demo_proposal(operation_id=f"OP-{name.upper().replace('_', '-')}", **(proposal_updates or {}))
        facts = None if missing_facts else demo_facts(proposal, **(fact_updates or {}))
        return EvaluationCase(name=name, context=context, proposal=proposal, facts=facts, expected=expected)

    return (
        case("safe_small", Outcome.ALLOW),
        case("safe_boundary", Outcome.ALLOW, proposal_updates={"amount_cents": 500_000}),
        case("sanctioned", Outcome.DENY, fact_updates={"vendor_sanctioned": True}),
        case("unapproved", Outcome.DENY, fact_updates={"vendor_approved": False}),
        case("authz_denied", Outcome.DENY, fact_updates={"authorization_permitted": False}),
        case("facts_missing", Outcome.DENY, missing_facts=True),
        case("hard_amount", Outcome.DENY, proposal_updates={"amount_cents": 2_000_001}),
        case(
            "data_egress",
            Outcome.DENY,
            proposal_updates={"data_classification": "restricted", "destination": "external-webhook"},
        ),
        case("amount_approval", Outcome.ESCALATE, proposal_updates={"amount_cents": 500_001}),
        case("risk_approval", Outcome.ESCALATE, fact_updates={"risk_basis_points": 5_000}),
    )


def summarize_evaluation(bundle: PolicyBundle, cases: Iterable[EvaluationCase]) -> EvaluationSummary:
    samples = tuple(cases)
    baseline = [unsafe_first_match_baseline(x.context, x.proposal, x.facts) for x in samples]
    candidate = [
        evaluate_policy(bundle, x.context, x.proposal, x.facts, now=REFERENCE_TIME).outcome
        for x in samples
    ]
    expected = [x.expected for x in samples]
    forbidden = [i for i, value in enumerate(expected) if value is Outcome.DENY]
    legitimate = [i for i, value in enumerate(expected) if value is Outcome.ALLOW]
    escalations = [i for i, value in enumerate(expected) if value is Outcome.ESCALATE]
    return EvaluationSummary(
        case_count=len(samples),
        expected_allow_count=len(legitimate),
        expected_deny_count=len(forbidden),
        expected_escalate_count=len(escalations),
        baseline_correct_count=sum(a is b for a, b in zip(baseline, expected)),
        candidate_correct_count=sum(a is b for a, b in zip(candidate, expected)),
        forbidden_case_count=len(forbidden),
        baseline_forbidden_allowed_count=sum(baseline[i] is Outcome.ALLOW for i in forbidden),
        candidate_forbidden_allowed_count=sum(candidate[i] is Outcome.ALLOW for i in forbidden),
        legitimate_case_count=len(legitimate),
        baseline_false_denial_count=sum(baseline[i] is Outcome.DENY for i in legitimate),
        candidate_false_denial_count=sum(candidate[i] is Outcome.DENY for i in legitimate),
        escalation_case_count=len(escalations),
        baseline_missed_escalation_count=sum(baseline[i] is not Outcome.ESCALATE for i in escalations),
        candidate_missed_escalation_count=sum(candidate[i] is not Outcome.ESCALATE for i in escalations),
    )


def shadow_metrics(
    active: PolicyBundle, candidate: PolicyBundle, cases: Iterable[EvaluationCase]
) -> ShadowMetrics:
    samples = tuple(cases)
    active_results = [
        evaluate_policy(active, x.context, x.proposal, x.facts, now=REFERENCE_TIME).outcome
        for x in samples
    ]
    candidate_results = [
        evaluate_policy(candidate, x.context, x.proposal, x.facts, now=REFERENCE_TIME).outcome
        for x in samples
    ]
    expected = [x.expected for x in samples]
    disagreements = sum(a is not b for a, b in zip(active_results, candidate_results))
    return ShadowMetrics(
        active_bundle_digest=active.digest,
        candidate_bundle_digest=candidate.digest,
        evaluation_corpus_digest=stable_digest(samples),
        request_count=len(samples),
        disagreement_count=disagreements,
        decision_flip_rate=disagreements / len(samples) if samples else 0.0,
        incorrect_case_count=sum(
            actual is not wanted
            for actual, wanted in zip(candidate_results, expected)
        ),
        false_permit_count=sum(
            actual is Outcome.ALLOW and wanted is Outcome.DENY
            for actual, wanted in zip(candidate_results, expected)
        ),
        forbidden_not_denied_count=sum(
            wanted is Outcome.DENY and actual is not Outcome.DENY
            for actual, wanted in zip(candidate_results, expected)
        ),
        false_denial_count=sum(
            actual is Outcome.DENY and wanted is Outcome.ALLOW
            for actual, wanted in zip(candidate_results, expected)
        ),
        missed_escalation_count=sum(
            wanted is Outcome.ESCALATE and actual is not Outcome.ESCALATE
            for actual, wanted in zip(candidate_results, expected)
        ),
    )


def mutated_bundle() -> PolicyBundle:
    """A security regression used to prove the semantic corpus kills mutations."""

    base = stable_bundle()
    return base.model_copy(
        update={
            "version": "procurement-policy-1.1.0-mutant",
            "revision": "git:badc0de",
            "stage": ReleaseStage.DRAFT,
            "rules": base.rules.model_copy(
                update={"hard_amount_limit_cents": 9_999_999_999}
            ),
        }
    )


REGO_ARTIFACT = """
package procurement.runtime
import rego.v1

default decision := {"outcome": "deny", "reasons": ["default_deny"]}

decision := {"outcome": "deny", "reasons": ["vendor_sanctioned"]} if {
  input.facts.vendor_sanctioned
}

decision := {"outcome": "allow", "reasons": ["all_domains_allow"]} if {
  input.facts.authorization_permitted
  input.facts.vendor_approved
  not input.facts.vendor_sanctioned
  input.proposal.amount_cents <= data.policy.approval_threshold_cents
}
""".strip()


CEDAR_ARTIFACT = """
forbid (principal, action, resource)
when { context.vendorSanctioned || context.riskBasisPoints >= 8000 };

permit (
  principal is Agent,
  action == Action::"CreatePurchaseOrder",
  resource is ProcurementSystem
)
when {
  context.authorizationPermitted &&
  context.vendorApproved &&
  context.amountCents <= 500000
};
""".strip()


def opa_input(
    context: AuthenticatedContext, proposal: ActionProposal, facts: TrustedFacts
) -> dict[str, object]:
    """Return the exact JSON boundary a production OPA adapter would submit."""

    return _canonical({"context": context, "proposal": proposal, "facts": facts})
