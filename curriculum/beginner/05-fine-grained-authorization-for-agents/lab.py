"""Deterministic fine-grained authorization lab for Course 5.

The module models a procurement-agent Policy Decision Point (PDP), Policy
Enforcement Point (PEP), authoritative relationship/attribute data, approval
receipts, atomic call limits, idempotent effects, and decision evidence.  It is
credential-free and intentionally keeps external policy engines behind explicit
adapters so the same invariants can be reused with OpenFGA, Cedar, or OPA.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from threading import Lock
from typing import Callable

from openfga_sdk.client.models import ClientCheckRequest, ClientTuple
from pydantic import BaseModel, ConfigDict, Field, model_validator


REFERENCE_TIME = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "procurement-authz-2026-09"
AUTONOMOUS_LIMIT_CENTS = 500_000
DECISION_TTL = timedelta(seconds=30)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonicalize(value: object) -> object:
    if isinstance(value, BaseModel):
        return _canonicalize(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {str(key): _canonicalize(child) for key, child in value.items()}
    if isinstance(value, (set, frozenset)):
        normalized = [_canonicalize(child) for child in value]
        return sorted(
            normalized,
            key=lambda child: json.dumps(
                child, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ),
        )
    if isinstance(value, (list, tuple)):
        return [_canonicalize(child) for child in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def stable_digest(value: object) -> str:
    payload = json.dumps(
        _canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DecisionOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


class TaskState(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    REVOKED = "revoked"


class EffectStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    APPLIED = "applied"
    UNKNOWN = "unknown"


class TrustedIdentityContext(FrozenModel):
    subject_id: str
    actor_id: str
    workload_id: str
    tenant_id: str
    task_id: str
    authenticated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def interval_is_valid(self) -> "TrustedIdentityContext":
        if self.valid_until <= self.authenticated_at:
            raise ValueError("identity context must have a positive lifetime")
        return self


class ActionProposal(FrozenModel):
    operation_id: str = Field(pattern=r"^OP-[A-Z0-9-]+$")
    action: str
    resource_id: str
    amount_cents: int = Field(ge=0)
    vendor_id: str
    country: str = Field(min_length=2, max_length=2)


class TaskGrant(FrozenModel):
    task_id: str
    tenant_id: str
    subject_id: str
    actor_id: str
    allowed_actions: frozenset[str]
    allowed_resources: frozenset[str]
    allowed_vendor_ids: frozenset[str]
    max_amount_cents: int = Field(ge=0)
    max_calls: int = Field(ge=1)
    valid_from: datetime
    valid_until: datetime
    state: TaskState
    version: str

    @model_validator(mode="after")
    def grant_is_bounded(self) -> "TaskGrant":
        if not self.allowed_actions or not self.allowed_resources:
            raise ValueError("task grant must name actions and resources")
        if self.valid_until <= self.valid_from:
            raise ValueError("task grant must have a positive lifetime")
        return self


class ResourceRecord(FrozenModel):
    resource_id: str
    tenant_id: str
    authorized_users: frozenset[str]
    active: bool
    version: str


class VendorRecord(FrozenModel):
    vendor_id: str
    tenant_id: str
    approved: bool
    sanctioned: bool
    allowed_countries: frozenset[str]
    version: str


class RiskAssessment(FrozenModel):
    operation_id: str
    proposal_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    score_basis_points: int = Field(ge=0, le=10_000)
    assessed_at: datetime
    valid_until: datetime
    version: str

    @model_validator(mode="after")
    def assessment_is_currentable(self) -> "RiskAssessment":
        if self.valid_until <= self.assessed_at:
            raise ValueError("risk assessment must have a positive lifetime")
        return self


class ApprovalReceipt(FrozenModel):
    approval_id: str = Field(pattern=r"^APR-[A-Z0-9-]+$")
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tenant_id: str
    task_id: str
    subject_id: str
    actor_id: str
    approver_id: str
    approver_role: str
    policy_version: str
    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def approval_is_bounded(self) -> "ApprovalReceipt":
        if self.expires_at <= self.issued_at:
            raise ValueError("approval must have a positive lifetime")
        return self


class AuthorizationDecision(FrozenModel):
    decision_id: str
    outcome: DecisionOutcome
    reason_codes: tuple[str, ...]
    operation_id: str
    request_digest: str
    resolved_input_digest: str
    policy_version: str
    authorization_epoch: int
    evidence_versions: tuple[str, ...]
    valid_until: datetime
    remaining_calls: int
    replayed_decision: bool = False


class AuditEvent(FrozenModel):
    decision_id: str
    operation_id: str
    subject_id: str
    actor_id: str
    workload_id: str
    tenant_id: str
    task_id: str
    action: str
    resource_id: str
    request_digest: str
    resolved_input_digest: str
    outcome: DecisionOutcome
    reason_codes: tuple[str, ...]
    policy_version: str
    authorization_epoch: int
    evidence_versions: tuple[str, ...]
    observed_at: datetime


class EffectResult(FrozenModel):
    effect_id: str | None
    operation_id: str
    status: EffectStatus
    proposal_digest: str


class EnforcementResult(FrozenModel):
    decision: AuthorizationDecision
    effect: EffectResult


def authorization_request_digest(
    identity: TrustedIdentityContext, proposal: ActionProposal
) -> str:
    return stable_digest({"identity": identity, "proposal": proposal})


def issue_demo_approval(
    identity: TrustedIdentityContext,
    proposal: ActionProposal,
    *,
    now: datetime,
) -> ApprovalReceipt:
    """Issue a deterministic, request-bound teaching approval."""

    return ApprovalReceipt(
        approval_id="APR-MANAGER-001",
        request_digest=authorization_request_digest(identity, proposal),
        tenant_id=identity.tenant_id,
        task_id=identity.task_id,
        subject_id=identity.subject_id,
        actor_id=identity.actor_id,
        approver_id="human:procurement-manager",
        approver_role="ProcurementManager",
        policy_version=POLICY_VERSION,
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )


class AuthorizationRepository:
    """Authoritative in-memory teaching store with atomic decision consumption."""

    def __init__(
        self,
        *,
        grants: tuple[TaskGrant, ...],
        resources: tuple[ResourceRecord, ...],
        vendors: tuple[VendorRecord, ...],
        risks: tuple[RiskAssessment, ...],
    ) -> None:
        self._lock = Lock()
        self._grants = {item.task_id: item for item in grants}
        self._resources = {item.resource_id: item for item in resources}
        self._vendors = {item.vendor_id: item for item in vendors}
        self._risks = {item.operation_id: item for item in risks}
        self._call_counts = {item.task_id: 0 for item in grants}
        self._consumed_approvals: set[str] = set()
        self._operations: dict[tuple[str, str], tuple[str, AuthorizationDecision]] = {}
        self._audit: list[AuditEvent] = []
        self._authorization_epoch = 1
        self._available = True

    @property
    def audit_events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._audit)

    @property
    def authorization_epoch(self) -> int:
        with self._lock:
            return self._authorization_epoch

    def set_available(self, available: bool) -> None:
        with self._lock:
            self._available = available

    def replace_vendor(self, vendor: VendorRecord) -> None:
        """Apply an authoritative vendor change and invalidate prior previews."""

        with self._lock:
            self._vendors[vendor.vendor_id] = vendor
            self._authorization_epoch += 1

    def close_task(self, task_id: str) -> None:
        with self._lock:
            grant = self._grants[task_id]
            self._grants[task_id] = grant.model_copy(
                update={"state": TaskState.CLOSED, "version": f"{grant.version}-closed"}
            )
            self._authorization_epoch += 1

    def _decision(
        self,
        *,
        identity: TrustedIdentityContext,
        proposal: ActionProposal,
        now: datetime,
        outcome: DecisionOutcome,
        reasons: tuple[str, ...],
        request_digest: str,
        resolved_input_digest: str,
        evidence_versions: tuple[str, ...],
        valid_until: datetime,
        remaining_calls: int,
    ) -> AuthorizationDecision:
        decision_material = {
            "request_digest": request_digest,
            "resolved_input_digest": resolved_input_digest,
            "outcome": outcome,
            "reasons": reasons,
            "policy": POLICY_VERSION,
            "epoch": self._authorization_epoch,
        }
        return AuthorizationDecision(
            decision_id=f"DEC-{stable_digest(decision_material)[:16].upper()}",
            outcome=outcome,
            reason_codes=reasons,
            operation_id=proposal.operation_id,
            request_digest=request_digest,
            resolved_input_digest=resolved_input_digest,
            policy_version=POLICY_VERSION,
            authorization_epoch=self._authorization_epoch,
            evidence_versions=evidence_versions,
            valid_until=valid_until,
            remaining_calls=remaining_calls,
        )

    def _evaluate_unlocked(
        self,
        identity: TrustedIdentityContext,
        proposal: ActionProposal,
        *,
        approval: ApprovalReceipt | None,
        now: datetime,
        consume: bool,
    ) -> AuthorizationDecision:
        request_digest = authorization_request_digest(identity, proposal)
        if not self._available:
            return self._decision(
                identity=identity,
                proposal=proposal,
                now=now,
                outcome=DecisionOutcome.DENY,
                reasons=("pdp_unavailable_fail_closed",),
                request_digest=request_digest,
                resolved_input_digest=stable_digest({"available": False}),
                evidence_versions=(),
                valid_until=now,
                remaining_calls=0,
            )

        grant = self._grants.get(identity.task_id)
        resource = self._resources.get(proposal.resource_id)
        vendor = self._vendors.get(proposal.vendor_id)
        risk = self._risks.get(proposal.operation_id)
        evidence_versions = tuple(
            item
            for item in (
                f"task:{grant.version}" if grant else None,
                f"resource:{resource.version}" if resource else None,
                f"vendor:{vendor.version}" if vendor else None,
                f"risk:{risk.version}" if risk else None,
            )
            if item is not None
        )
        resolved = {
            "identity": identity,
            "proposal": proposal,
            "grant": grant,
            "resource": resource,
            "vendor": vendor,
            "risk": risk,
            "policy_version": POLICY_VERSION,
            "authorization_epoch": self._authorization_epoch,
        }
        resolved_input_digest = stable_digest(resolved)
        valid_until_candidates = [identity.valid_until, now + DECISION_TTL]
        if grant:
            valid_until_candidates.append(grant.valid_until)
        if risk:
            valid_until_candidates.append(risk.valid_until)
        valid_until = min(valid_until_candidates)
        call_count = self._call_counts.get(identity.task_id, 0)
        remaining_calls = max((grant.max_calls if grant else 0) - call_count, 0)

        denials: list[str] = []
        escalations: list[str] = []
        if not (identity.authenticated_at <= now < identity.valid_until):
            denials.append("identity_context_not_current")
        if grant is None:
            denials.append("task_grant_not_found")
        else:
            if grant.state is not TaskState.ACTIVE:
                denials.append("task_not_active")
            if not (grant.valid_from <= now < grant.valid_until):
                denials.append("task_grant_not_current")
            bindings = (
                (grant.tenant_id, identity.tenant_id, "task_tenant_mismatch"),
                (grant.subject_id, identity.subject_id, "task_subject_mismatch"),
                (grant.actor_id, identity.actor_id, "task_actor_mismatch"),
            )
            denials.extend(code for expected, actual, code in bindings if expected != actual)
            if proposal.action not in grant.allowed_actions:
                denials.append("action_not_granted_to_task")
            if proposal.resource_id not in grant.allowed_resources:
                denials.append("resource_not_granted_to_task")
            if proposal.vendor_id not in grant.allowed_vendor_ids:
                denials.append("vendor_not_granted_to_task")
            if proposal.amount_cents > grant.max_amount_cents:
                denials.append("amount_exceeds_task_limit")
            if call_count >= grant.max_calls:
                denials.append("task_call_limit_exhausted")

        if resource is None:
            denials.append("resource_not_found")
        else:
            if resource.tenant_id != identity.tenant_id:
                denials.append("resource_tenant_mismatch")
            if identity.subject_id not in resource.authorized_users:
                denials.append("user_not_authorized_for_resource")
            if not resource.active:
                denials.append("resource_not_active")

        if vendor is None:
            denials.append("vendor_not_found")
        else:
            if vendor.tenant_id != identity.tenant_id:
                denials.append("vendor_tenant_mismatch")
            if not vendor.approved:
                denials.append("vendor_not_approved")
            if vendor.sanctioned:
                denials.append("vendor_sanctioned")
            if proposal.country not in vendor.allowed_countries:
                denials.append("country_not_allowed_for_vendor")

        if risk is None:
            denials.append("current_risk_assessment_missing")
        else:
            if risk.proposal_digest != stable_digest(proposal):
                denials.append("risk_assessment_proposal_mismatch")
            if not (risk.assessed_at <= now < risk.valid_until):
                denials.append("risk_assessment_not_current")
            if risk.score_basis_points >= 8_000:
                denials.append("risk_above_hard_limit")
            elif risk.score_basis_points >= 5_000:
                escalations.append("risk_requires_approval")

        if proposal.amount_cents > AUTONOMOUS_LIMIT_CENTS:
            escalations.append("amount_requires_approval")

        if escalations and not denials:
            if approval is None:
                outcome = DecisionOutcome.ESCALATE
            else:
                approval_checks = {
                    "approval_request_mismatch": approval.request_digest != request_digest,
                    "approval_tenant_mismatch": approval.tenant_id != identity.tenant_id,
                    "approval_task_mismatch": approval.task_id != identity.task_id,
                    "approval_subject_mismatch": approval.subject_id != identity.subject_id,
                    "approval_actor_mismatch": approval.actor_id != identity.actor_id,
                    "approval_wrong_role": approval.approver_role != "ProcurementManager",
                    "approval_wrong_policy_version": approval.policy_version != POLICY_VERSION,
                    "approval_not_current": not (approval.issued_at <= now < approval.expires_at),
                    "approval_already_consumed": approval.approval_id
                    in self._consumed_approvals,
                }
                denials.extend(code for code, failed in approval_checks.items() if failed)
                outcome = DecisionOutcome.DENY if denials else DecisionOutcome.ALLOW
        elif denials:
            outcome = DecisionOutcome.DENY
        else:
            outcome = DecisionOutcome.ALLOW

        if outcome is DecisionOutcome.DENY:
            reasons = tuple(sorted(set(denials)))
        elif outcome is DecisionOutcome.ESCALATE:
            reasons = tuple(sorted(set(escalations)))
        elif escalations:
            reasons = ("approved_exception_and_all_hard_constraints_satisfied",)
        else:
            reasons = ("all_authorization_constraints_satisfied",)

        if consume and outcome is DecisionOutcome.ALLOW and grant is not None:
            self._call_counts[grant.task_id] = call_count + 1
            remaining_calls = max(grant.max_calls - call_count - 1, 0)
            if approval is not None:
                self._consumed_approvals.add(approval.approval_id)

        return self._decision(
            identity=identity,
            proposal=proposal,
            now=now,
            outcome=outcome,
            reasons=reasons,
            request_digest=request_digest,
            resolved_input_digest=resolved_input_digest,
            evidence_versions=evidence_versions,
            valid_until=valid_until,
            remaining_calls=remaining_calls,
        )

    def preview(
        self,
        identity: TrustedIdentityContext,
        proposal: ActionProposal,
        *,
        approval: ApprovalReceipt | None = None,
        now: datetime,
    ) -> AuthorizationDecision:
        with self._lock:
            return self._evaluate_unlocked(
                identity, proposal, approval=approval, now=now, consume=False
            )

    def authorize_and_consume(
        self,
        identity: TrustedIdentityContext,
        proposal: ActionProposal,
        *,
        approval: ApprovalReceipt | None = None,
        now: datetime,
    ) -> AuthorizationDecision:
        request_digest = authorization_request_digest(identity, proposal)
        operation_key = (identity.tenant_id, proposal.operation_id)
        with self._lock:
            previous = self._operations.get(operation_key)
            if previous:
                previous_digest, previous_decision = previous
                if previous_digest == request_digest:
                    return previous_decision.model_copy(update={"replayed_decision": True})
                collision = self._decision(
                    identity=identity,
                    proposal=proposal,
                    now=now,
                    outcome=DecisionOutcome.DENY,
                    reasons=("operation_id_reused_with_different_request",),
                    request_digest=request_digest,
                    resolved_input_digest=stable_digest({"collision": True}),
                    evidence_versions=(),
                    valid_until=now,
                    remaining_calls=0,
                )
                self._record_unlocked(identity, proposal, collision, now)
                return collision

            decision = self._evaluate_unlocked(
                identity, proposal, approval=approval, now=now, consume=True
            )
            transient = decision.reason_codes == ("pdp_unavailable_fail_closed",)
            if decision.outcome is not DecisionOutcome.ESCALATE and not transient:
                self._operations[operation_key] = (request_digest, decision)
            self._record_unlocked(identity, proposal, decision, now)
            return decision

    def _record_unlocked(
        self,
        identity: TrustedIdentityContext,
        proposal: ActionProposal,
        decision: AuthorizationDecision,
        now: datetime,
    ) -> None:
        self._audit.append(
            AuditEvent(
                decision_id=decision.decision_id,
                operation_id=proposal.operation_id,
                subject_id=identity.subject_id,
                actor_id=identity.actor_id,
                workload_id=identity.workload_id,
                tenant_id=identity.tenant_id,
                task_id=identity.task_id,
                action=proposal.action,
                resource_id=proposal.resource_id,
                request_digest=decision.request_digest,
                resolved_input_digest=decision.resolved_input_digest,
                outcome=decision.outcome,
                reason_codes=decision.reason_codes,
                policy_version=decision.policy_version,
                authorization_epoch=decision.authorization_epoch,
                evidence_versions=decision.evidence_versions,
                observed_at=now,
            )
        )


class InMemoryProcurementAdapter:
    """Observable teaching effect adapter, not a production procurement API."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._results: dict[str, EffectResult] = {}

    @property
    def applied_count(self) -> int:
        with self._lock:
            return len(self._results)

    def result_for(self, operation_id: str) -> EffectResult | None:
        with self._lock:
            return self._results.get(operation_id)

    def apply(self, proposal: ActionProposal) -> EffectResult:
        with self._lock:
            existing = self._results.get(proposal.operation_id)
            if existing:
                return existing
            result = EffectResult(
                effect_id=f"PO-{stable_digest(proposal)[:12].upper()}",
                operation_id=proposal.operation_id,
                status=EffectStatus.APPLIED,
                proposal_digest=stable_digest(proposal),
            )
            self._results[proposal.operation_id] = result
            return result


class PolicyEnforcementPoint:
    def __init__(
        self,
        repository: AuthorizationRepository,
        adapter: InMemoryProcurementAdapter,
    ) -> None:
        self._repository = repository
        self._adapter = adapter

    def execute(
        self,
        identity: TrustedIdentityContext,
        proposal: ActionProposal,
        *,
        approval: ApprovalReceipt | None = None,
        now: datetime,
    ) -> EnforcementResult:
        decision = self._repository.authorize_and_consume(
            identity, proposal, approval=approval, now=now
        )
        if decision.outcome is not DecisionOutcome.ALLOW:
            return EnforcementResult(
                decision=decision,
                effect=EffectResult(
                    effect_id=None,
                    operation_id=proposal.operation_id,
                    status=EffectStatus.NOT_ATTEMPTED,
                    proposal_digest=stable_digest(proposal),
                ),
            )
        if decision.replayed_decision:
            previous = self._adapter.result_for(proposal.operation_id)
            return EnforcementResult(
                decision=decision,
                effect=previous
                or EffectResult(
                    effect_id=None,
                    operation_id=proposal.operation_id,
                    status=EffectStatus.UNKNOWN,
                    proposal_digest=stable_digest(proposal),
                ),
            )
        return EnforcementResult(decision=decision, effect=self._adapter.apply(proposal))


def unsafe_role_only_authorize(role: str, proposal: ActionProposal) -> bool:
    """Deliberately unsafe baseline: role and coarse action only."""

    permissions = {"ProcurementManager": {"purchase_order:create", "vendor:read"}}
    return proposal.action in permissions.get(role, set())


OPENFGA_MODEL = """
model
  schema 1.1
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
""".strip()


def openfga_dual_check_requests(
    identity: TrustedIdentityContext, proposal: ActionProposal
) -> tuple[ClientCheckRequest, ClientCheckRequest]:
    """Build real OpenFGA SDK requests without making a network call."""

    user_check = ClientCheckRequest(
        user=identity.subject_id.replace("human:", "user:"),
        relation="user_can_create",
        object=proposal.resource_id,
    )
    task_check = ClientCheckRequest(
        user=f"task:{identity.task_id}",
        relation="task_can_create",
        object=proposal.resource_id,
        contextual_tuples=[
            ClientTuple(
                user=identity.actor_id,
                relation="calling_agent",
                object=proposal.resource_id,
            )
        ],
    )
    return user_check, task_check


CEDAR_POLICY = """
forbid (principal, action, resource)
when { context.vendorSanctioned || context.riskBasisPoints >= 8000 };

permit (
  principal is Agent,
  action == Action::"CreatePurchaseOrder",
  resource is Department
)
when {
  context.userAuthorized &&
  context.taskAuthorized &&
  context.vendorApproved &&
  context.countryAllowed &&
  context.amountCents <= context.taskMaxAmountCents
};
""".strip()


REGO_POLICY = """
package agentauthz

import rego.v1

default decision := {"outcome": "deny", "reasons": ["default_deny"]}

decision := {"outcome": "allow", "reasons": ["all_constraints_satisfied"]} if {
  input.user_authorized
  input.task_authorized
  input.vendor.approved
  not input.vendor.sanctioned
  input.amount_cents <= input.task_max_amount_cents
  input.risk_basis_points < 5000
}
""".strip()


def demo_identity(*, actor_id: str = "agent:procurement-v1", tenant_id: str = "tenant:oneplusi") -> TrustedIdentityContext:
    return TrustedIdentityContext(
        subject_id="human:user-123",
        actor_id=actor_id,
        workload_id="spiffe://example.com/prod/procurement",
        tenant_id=tenant_id,
        task_id="TASK-PO-123",
        authenticated_at=REFERENCE_TIME - timedelta(minutes=2),
        valid_until=REFERENCE_TIME + timedelta(minutes=20),
    )


def demo_proposal(
    *,
    operation_id: str = "OP-PO-001",
    amount_cents: int = 450_000,
    resource_id: str = "department:data-ai",
    vendor_id: str = "vendor:acme",
    country: str = "CA",
) -> ActionProposal:
    return ActionProposal(
        operation_id=operation_id,
        action="purchase_order:create",
        resource_id=resource_id,
        amount_cents=amount_cents,
        vendor_id=vendor_id,
        country=country,
    )


def build_demo_environment(
    *,
    identity: TrustedIdentityContext | None = None,
    proposal: ActionProposal | None = None,
    max_calls: int = 2,
    vendor_approved: bool = True,
    vendor_sanctioned: bool = False,
    risk_basis_points: int = 2_500,
    resource_tenant: str = "tenant:oneplusi",
    authorized_users: frozenset[str] = frozenset({"human:user-123"}),
    additional_proposals: tuple[ActionProposal, ...] = (),
) -> tuple[
    TrustedIdentityContext,
    ActionProposal,
    AuthorizationRepository,
    PolicyEnforcementPoint,
    InMemoryProcurementAdapter,
]:
    identity = identity or demo_identity()
    proposal = proposal or demo_proposal()
    grant = TaskGrant(
        task_id="TASK-PO-123",
        tenant_id="tenant:oneplusi",
        subject_id="human:user-123",
        actor_id="agent:procurement-v1",
        allowed_actions=frozenset({"purchase_order:create", "vendor:read"}),
        allowed_resources=frozenset({"department:data-ai"}),
        allowed_vendor_ids=frozenset({"vendor:acme"}),
        max_amount_cents=1_000_000,
        max_calls=max_calls,
        valid_from=REFERENCE_TIME - timedelta(minutes=5),
        valid_until=REFERENCE_TIME + timedelta(minutes=15),
        state=TaskState.ACTIVE,
        version="grant-v3",
    )
    resource = ResourceRecord(
        resource_id=proposal.resource_id,
        tenant_id=resource_tenant,
        authorized_users=authorized_users,
        active=True,
        version="resource-v7",
    )
    vendor = VendorRecord(
        vendor_id=proposal.vendor_id,
        tenant_id="tenant:oneplusi",
        approved=vendor_approved,
        sanctioned=vendor_sanctioned,
        allowed_countries=frozenset({"CA", "US"}),
        version="vendor-v11",
    )
    risks = tuple(
        RiskAssessment(
            operation_id=item.operation_id,
            proposal_digest=stable_digest(item),
            score_basis_points=risk_basis_points,
            assessed_at=REFERENCE_TIME - timedelta(seconds=10),
            valid_until=REFERENCE_TIME + timedelta(minutes=2),
            version=f"risk-v5-{index}",
        )
        for index, item in enumerate((proposal, *additional_proposals), start=1)
    )
    repository = AuthorizationRepository(
        grants=(grant,), resources=(resource,), vendors=(vendor,), risks=risks
    )
    adapter = InMemoryProcurementAdapter()
    pep = PolicyEnforcementPoint(repository, adapter)
    return identity, proposal, repository, pep, adapter


class EvaluationRow(FrozenModel):
    case: str
    expected: DecisionOutcome
    baseline_actual: DecisionOutcome
    actual: DecisionOutcome
    baseline_correct: bool
    correct: bool
    reason_codes: tuple[str, ...]


class EvaluationSummary(FrozenModel):
    rows: tuple[EvaluationRow, ...]
    case_count: int
    baseline_correct_count: int
    correct_count: int
    forbidden_case_count: int
    baseline_forbidden_allowed_count: int
    forbidden_allowed_count: int
    legitimate_case_count: int
    baseline_false_denial_count: int
    false_denial_count: int
    escalation_case_count: int
    baseline_missed_escalation_count: int


def run_evaluation() -> EvaluationSummary:
    cases: tuple[
        tuple[str, DecisionOutcome, Callable[[], tuple[TrustedIdentityContext, ActionProposal, AuthorizationRepository]]],
        ...,
    ] = (
        (
            "allowed_purchase",
            DecisionOutcome.ALLOW,
            lambda: build_demo_environment()[:3],
        ),
        (
            "autonomous_boundary",
            DecisionOutcome.ALLOW,
            lambda: build_demo_environment(proposal=demo_proposal(amount_cents=500_000))[:3],
        ),
        (
            "approval_required",
            DecisionOutcome.ESCALATE,
            lambda: build_demo_environment(proposal=demo_proposal(amount_cents=600_000))[:3],
        ),
        (
            "wrong_agent",
            DecisionOutcome.DENY,
            lambda: build_demo_environment(identity=demo_identity(actor_id="agent:other"))[:3],
        ),
        (
            "cross_tenant_resource",
            DecisionOutcome.DENY,
            lambda: build_demo_environment(resource_tenant="tenant:other")[:3],
        ),
        (
            "wrong_resource",
            DecisionOutcome.DENY,
            lambda: build_demo_environment(proposal=demo_proposal(resource_id="department:finance"))[:3],
        ),
        (
            "unapproved_vendor",
            DecisionOutcome.DENY,
            lambda: build_demo_environment(vendor_approved=False)[:3],
        ),
        (
            "sanctioned_vendor",
            DecisionOutcome.DENY,
            lambda: build_demo_environment(vendor_sanctioned=True)[:3],
        ),
        (
            "amount_above_task_limit",
            DecisionOutcome.DENY,
            lambda: build_demo_environment(proposal=demo_proposal(amount_cents=1_000_001))[:3],
        ),
        (
            "high_risk",
            DecisionOutcome.DENY,
            lambda: build_demo_environment(risk_basis_points=8_000)[:3],
        ),
    )
    rows: list[EvaluationRow] = []
    for case, expected, factory in cases:
        identity, proposal, repository = factory()
        actual_decision = repository.preview(identity, proposal, now=REFERENCE_TIME)
        baseline_actual = (
            DecisionOutcome.ALLOW
            if unsafe_role_only_authorize("ProcurementManager", proposal)
            else DecisionOutcome.DENY
        )
        rows.append(
            EvaluationRow(
                case=case,
                expected=expected,
                baseline_actual=baseline_actual,
                actual=actual_decision.outcome,
                baseline_correct=baseline_actual is expected,
                correct=actual_decision.outcome is expected,
                reason_codes=actual_decision.reason_codes,
            )
        )
    legitimate = [row for row in rows if row.expected is DecisionOutcome.ALLOW]
    forbidden = [row for row in rows if row.expected is DecisionOutcome.DENY]
    escalations = [row for row in rows if row.expected is DecisionOutcome.ESCALATE]
    return EvaluationSummary(
        rows=tuple(rows),
        case_count=len(rows),
        baseline_correct_count=sum(row.baseline_correct for row in rows),
        correct_count=sum(row.correct for row in rows),
        forbidden_case_count=len(forbidden),
        baseline_forbidden_allowed_count=sum(
            row.baseline_actual is DecisionOutcome.ALLOW for row in forbidden
        ),
        forbidden_allowed_count=sum(row.actual is DecisionOutcome.ALLOW for row in forbidden),
        legitimate_case_count=len(legitimate),
        baseline_false_denial_count=sum(
            row.baseline_actual is not DecisionOutcome.ALLOW for row in legitimate
        ),
        false_denial_count=sum(row.actual is not DecisionOutcome.ALLOW for row in legitimate),
        escalation_case_count=len(escalations),
        baseline_missed_escalation_count=sum(
            row.baseline_actual is not DecisionOutcome.ESCALATE for row in escalations
        ),
    )
