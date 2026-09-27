"""Deterministic human-oversight and bounded-autonomy lab for Course 8.

The model proposes a procurement action. Trusted application code classifies
the action, stores a durable approval request, authenticates reviewers,
enforces separation of duties and quorum, consumes approval exactly once,
reserves a task budget, executes, and verifies the external effect.

The module is credential-free and deterministic. It also creates real tool
descriptors with the installed OpenAI Agents SDK and Microsoft Agent Framework
without making a model or network call.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
from statistics import median
from threading import Lock
from typing import Iterable

from agent_framework import tool as microsoft_tool
from agents import function_tool
from pydantic import BaseModel, ConfigDict, Field, model_validator


REFERENCE_TIME = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical(value: object) -> object:
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {str(key): _canonical(child) for key, child in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical(child) for child in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_canonical(child) for child in value), key=str)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def stable_digest(value: object) -> str:
    raw = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class Route(str, Enum):
    AUTO_ALLOW = "auto_allow"
    VERIFY = "verify"
    APPROVE = "approve"
    MULTI_APPROVE = "multi_approve"
    DENY = "deny"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    PAUSED = "paused"
    TERMINATED = "terminated"
    FAILED = "failed"


class ReviewChoice(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class AuthenticatedContext(FrozenModel):
    subject_id: str
    workload_id: str
    tenant_id: str
    task_id: str
    authenticated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def valid_lifetime(self) -> "AuthenticatedContext":
        if self.valid_until <= self.authenticated_at:
            raise ValueError("authentication lifetime must be positive")
        return self


class ReviewerContext(FrozenModel):
    reviewer_id: str
    tenant_id: str
    roles: frozenset[str]
    authenticated_at: datetime
    valid_until: datetime


class OperatorContext(FrozenModel):
    operator_id: str
    tenant_id: str
    roles: frozenset[str]


class ActionProposal(FrozenModel):
    operation_id: str = Field(pattern=r"^OP-[A-Z0-9-]+$")
    tool_name: str
    vendor_id: str = Field(pattern=r"^VEN-[0-9]{3}$")
    amount_cents: int = Field(gt=0)
    currency: str = "CAD"
    reversible: bool = True
    data_sensitivity: int = Field(default=1, ge=0, le=4)
    novelty_basis_points: int = Field(default=0, ge=0, le=10_000)
    anomaly_basis_points: int = Field(default=0, ge=0, le=10_000)
    # Model assertions remain untrusted and never satisfy application policy.
    model_claimed_risk: str | None = None
    model_claimed_approved: bool = False


class TrustedFacts(FrozenModel):
    tenant_id: str
    approved_vendors: frozenset[str]
    sanctioned_vendors: frozenset[str]
    task_remaining_cents: int = Field(ge=0)
    incident_mode: str = "normal"
    source_version: str
    observed_at: datetime
    valid_until: datetime


class AutonomyEnvelope(FrozenModel):
    policy_version: str
    workload_id: str
    allowed_tools: frozenset[str]
    auto_limit_cents: int = 100_000
    verify_limit_cents: int = 250_000
    single_approval_limit_cents: int = 1_000_000
    hard_limit_cents: int = 5_000_000
    task_spend_limit_cents: int = 6_000_000
    task_action_limit: int = 6
    valid_until: datetime


class OversightDecision(FrozenModel):
    route: Route
    reason_codes: tuple[str, ...]
    risk_basis_points: int
    action_digest: str
    policy_version: str
    facts_version: str | None


class ApprovalRequest(FrozenModel):
    request_id: str
    action_digest: str
    tenant_id: str
    subject_id: str
    workload_id: str
    task_id: str
    operation_id: str
    tool_name: str
    amount_cents: int
    vendor_id: str
    policy_version: str
    facts_version: str
    required_roles: frozenset[str]
    quorum: int = Field(ge=1)
    created_at: datetime
    expires_at: datetime


class ReviewDecision(FrozenModel):
    reviewer_id: str
    reviewer_role: str
    choice: ReviewChoice
    request_id: str
    action_digest: str
    decided_at: datetime


class VerificationReceipt(FrozenModel):
    verification_id: str
    action_digest: str
    tenant_id: str
    source_version: str
    verified_at: datetime
    expires_at: datetime


class WorkflowRecord(FrozenModel):
    workflow_id: str
    tenant_id: str
    subject_id: str
    workload_id: str
    task_id: str
    action: ActionProposal
    route: Route
    policy_version: str
    facts_version: str
    status: WorkflowStatus
    version: int
    approval: ApprovalRequest | None = None
    verification: VerificationReceipt | None = None
    decisions: tuple[ReviewDecision, ...] = ()
    terminal_reason: str | None = None
    effect_id: str | None = None
    paused_from: WorkflowStatus | None = None


class EffectReceipt(FrozenModel):
    effect_id: str | None
    tenant_id: str
    operation_id: str
    vendor_id: str
    amount_cents: int
    currency: str
    status: str


class ExecutionResult(FrozenModel):
    workflow: WorkflowRecord
    effect: EffectReceipt | None
    verified: bool
    reason_code: str


class EvaluationCase(FrozenModel):
    name: str
    context: AuthenticatedContext
    action: ActionProposal
    facts: TrustedFacts
    expected: Route


class EvaluationSummary(FrozenModel):
    case_count: int
    expected_auto_count: int
    expected_verify_count: int
    expected_single_count: int
    expected_multi_count: int
    expected_deny_count: int
    baseline_correct_count: int
    candidate_correct_count: int
    baseline_human_review_count: int
    candidate_human_review_count: int
    baseline_hard_denial_overridden_count: int
    candidate_hard_denial_overridden_count: int


class ReviewEvent(FrozenModel):
    reviewer_id: str
    expected_choice: ReviewChoice
    actual_choice: ReviewChoice
    latency_seconds: float = Field(ge=0)


class ReviewerMetrics(FrozenModel):
    event_count: int
    approval_count: int
    approval_rate: float
    median_latency_seconds: float
    fast_approval_count: int
    disagreement_count: int
    busiest_reviewer_count: int


class ControlError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def risk_basis_points(action: ActionProposal) -> int:
    """Transparent triage signal; hard policy remains independent of this score."""

    impact = min(action.amount_cents * 10_000 // 5_000_000, 10_000)
    irreversibility = 10_000 if not action.reversible else 0
    sensitivity = action.data_sensitivity * 2_500
    return min(
        10_000,
        (35 * impact + 20 * irreversibility + 15 * sensitivity
         + 15 * action.novelty_basis_points + 15 * action.anomaly_basis_points) // 100,
    )


def route_action(
    context: AuthenticatedContext,
    action: ActionProposal,
    facts: TrustedFacts | None,
    envelope: AutonomyEnvelope,
    now: datetime = REFERENCE_TIME,
) -> OversightDecision:
    digest = stable_digest(action)
    score = risk_basis_points(action)

    def decision(route: Route, *reasons: str) -> OversightDecision:
        return OversightDecision(
            route=route,
            reason_codes=tuple(reasons),
            risk_basis_points=score,
            action_digest=digest,
            policy_version=envelope.policy_version,
            facts_version=facts.source_version if facts else None,
        )

    if context.valid_until < now or context.authenticated_at > now:
        return decision(Route.DENY, "AUTHENTICATION_STALE")
    if envelope.valid_until < now or context.workload_id != envelope.workload_id:
        return decision(Route.DENY, "AUTONOMY_ENVELOPE_INVALID")
    if action.tool_name not in envelope.allowed_tools:
        return decision(Route.DENY, "TOOL_OUTSIDE_ENVELOPE")
    if action.currency != "CAD":
        return decision(Route.DENY, "CURRENCY_NOT_ALLOWED")
    if facts is None or facts.valid_until < now or facts.observed_at > now:
        return decision(Route.DENY, "TRUSTED_FACTS_STALE")
    if facts.tenant_id != context.tenant_id:
        return decision(Route.DENY, "TENANT_BINDING_MISMATCH")
    if action.vendor_id in facts.sanctioned_vendors:
        return decision(Route.DENY, "VENDOR_SANCTIONED")
    if action.vendor_id not in facts.approved_vendors:
        return decision(Route.DENY, "VENDOR_NOT_APPROVED")
    if action.amount_cents > facts.task_remaining_cents:
        return decision(Route.DENY, "TASK_BUDGET_EXCEEDED")
    if action.amount_cents > envelope.hard_limit_cents:
        return decision(Route.DENY, "HARD_AMOUNT_LIMIT")
    if facts.incident_mode == "critical":
        return decision(Route.DENY, "CRITICAL_INCIDENT_STOP")
    if not action.reversible:
        return decision(Route.MULTI_APPROVE, "IRREVERSIBLE_ACTION")
    if facts.incident_mode == "elevated":
        return decision(Route.APPROVE, "ELEVATED_INCIDENT")
    if action.amount_cents <= envelope.auto_limit_cents and score < 3_000:
        return decision(Route.AUTO_ALLOW, "LOW_RISK_INSIDE_ENVELOPE")
    if action.amount_cents <= envelope.verify_limit_cents and score < 5_000:
        return decision(Route.VERIFY, "ADDITIONAL_VERIFICATION")
    if action.amount_cents <= envelope.single_approval_limit_cents:
        return decision(Route.APPROVE, "MANAGER_APPROVAL_REQUIRED")
    return decision(Route.MULTI_APPROVE, "MANAGER_AND_FINANCE_REQUIRED")


def unsafe_universal_hitl(_: EvaluationCase) -> Route:
    """Baseline anti-pattern: every action can be overridden by one approval."""

    return Route.APPROVE


class EffectAdapter:
    def __init__(self, capability: object):
        self._capability = capability
        self._effects: dict[tuple[str, str], EffectReceipt] = {}
        self.mismatch_next = False
        self.failure_mode_next: str | None = None

    def execute(self, capability: object, tenant_id: str, action: ActionProposal) -> EffectReceipt:
        if capability is not self._capability:
            raise PermissionError("effect adapter requires the oversight gateway capability")
        key = (tenant_id, action.operation_id)
        if key in self._effects:
            return self._effects[key]
        if self.failure_mode_next == "before_commit":
            self.failure_mode_next = None
            return EffectReceipt(
                effect_id=None,
                tenant_id=tenant_id,
                operation_id=action.operation_id,
                vendor_id=action.vendor_id,
                amount_cents=action.amount_cents,
                currency=action.currency,
                status="not_found",
            )
        amount = action.amount_cents + 1 if self.mismatch_next else action.amount_cents
        self.mismatch_next = False
        receipt = EffectReceipt(
            effect_id="EF-" + stable_digest({"tenant": tenant_id, "operation": action.operation_id})[:16],
            tenant_id=tenant_id,
            operation_id=action.operation_id,
            vendor_id=action.vendor_id,
            amount_cents=amount,
            currency=action.currency,
            status="created",
        )
        self._effects[key] = receipt
        if self.failure_mode_next == "after_commit":
            self.failure_mode_next = None
            return receipt.model_copy(update={"status": "unknown"})
        return receipt

    def reconcile(self, tenant_id: str, operation_id: str) -> EffectReceipt | None:
        """Read by idempotency key before any retry after an ambiguous outcome."""

        return self._effects.get((tenant_id, operation_id))


def verify_effect(action: ActionProposal, effect: EffectReceipt) -> bool:
    return (
        effect.operation_id == action.operation_id
        and effect.vendor_id == action.vendor_id
        and effect.amount_cents == action.amount_cents
        and effect.currency == action.currency
        and effect.status == "created"
    )


class OversightSystem:
    """In-memory teaching control plane with atomic versioned transitions."""

    def __init__(self, envelope: AutonomyEnvelope):
        self.envelope = envelope
        self._records: dict[str, WorkflowRecord] = {}
        self._spent: dict[tuple[str, str], int] = defaultdict(int)
        self._actions: dict[tuple[str, str], int] = defaultdict(int)
        self._lock = Lock()
        self._capability = object()
        self.adapter = EffectAdapter(self._capability)

    def get(self, workflow_id: str) -> WorkflowRecord:
        return self._records[workflow_id]

    def propose(
        self,
        context: AuthenticatedContext,
        action: ActionProposal,
        facts: TrustedFacts,
        now: datetime = REFERENCE_TIME,
    ) -> WorkflowRecord:
        decision = route_action(context, action, facts, self.envelope, now)
        workflow_id = "WF-" + stable_digest(
            {"tenant": context.tenant_id, "task": context.task_id, "operation": action.operation_id}
        )[:16]
        if workflow_id in self._records:
            existing = self._records[workflow_id]
            if stable_digest(existing.action) != decision.action_digest:
                raise ControlError("OPERATION_MUTATION")
            return existing
        approval = None
        status = WorkflowStatus.READY if decision.route is Route.AUTO_ALLOW else WorkflowStatus.PENDING
        terminal = None
        if decision.route is Route.DENY:
            status, terminal = WorkflowStatus.REJECTED, decision.reason_codes[0]
        elif decision.route in {Route.APPROVE, Route.MULTI_APPROVE}:
            roles = frozenset({"manager"}) if decision.route is Route.APPROVE else frozenset({"manager", "finance"})
            approval = ApprovalRequest(
                request_id="AR-" + stable_digest({"workflow": workflow_id, "action": decision.action_digest})[:16],
                action_digest=decision.action_digest,
                tenant_id=context.tenant_id,
                subject_id=context.subject_id,
                workload_id=context.workload_id,
                task_id=context.task_id,
                operation_id=action.operation_id,
                tool_name=action.tool_name,
                amount_cents=action.amount_cents,
                vendor_id=action.vendor_id,
                policy_version=self.envelope.policy_version,
                facts_version=facts.source_version,
                required_roles=roles,
                quorum=len(roles),
                created_at=now,
                expires_at=now + timedelta(hours=4),
            )
        record = WorkflowRecord(
            workflow_id=workflow_id,
            tenant_id=context.tenant_id,
            subject_id=context.subject_id,
            workload_id=context.workload_id,
            task_id=context.task_id,
            action=action,
            route=decision.route,
            policy_version=self.envelope.policy_version,
            facts_version=facts.source_version,
            status=status,
            version=1,
            approval=approval,
            terminal_reason=terminal,
        )
        self._records[workflow_id] = record
        return record

    def verify(
        self,
        workflow_id: str,
        expected_version: int,
        facts: TrustedFacts,
        now: datetime = REFERENCE_TIME,
    ) -> WorkflowRecord:
        """Apply a trusted additional check; model/user assertions cannot satisfy it."""

        with self._lock:
            record = self._records[workflow_id]
            if record.version != expected_version:
                raise ControlError("VERSION_CONFLICT")
            if record.route is not Route.VERIFY or record.status is not WorkflowStatus.PENDING:
                raise ControlError("WORKFLOW_NOT_VERIFIABLE")
            if facts.valid_until < now or facts.observed_at > now:
                raise ControlError("TRUSTED_FACTS_STALE")
            if facts.tenant_id != record.tenant_id:
                raise ControlError("TENANT_BINDING_MISMATCH")
            if (
                record.action.vendor_id not in facts.approved_vendors
                or record.action.vendor_id in facts.sanctioned_vendors
            ):
                raise ControlError("VERIFICATION_FAILED")
            receipt = VerificationReceipt(
                verification_id="VR-" + stable_digest(
                    {"workflow": workflow_id, "facts": facts.source_version}
                )[:16],
                action_digest=stable_digest(record.action),
                tenant_id=record.tenant_id,
                source_version=facts.source_version,
                verified_at=now,
                expires_at=min(now + timedelta(minutes=10), facts.valid_until),
            )
            updated = record.model_copy(update={
                "verification": receipt,
                "status": WorkflowStatus.READY,
                "version": record.version + 1,
                "facts_version": facts.source_version,
            })
            self._records[workflow_id] = updated
            return updated

    def review(
        self,
        workflow_id: str,
        expected_version: int,
        reviewer: ReviewerContext,
        choice: ReviewChoice,
        now: datetime = REFERENCE_TIME,
    ) -> WorkflowRecord:
        with self._lock:
            record = self._records[workflow_id]
            if record.version != expected_version:
                raise ControlError("VERSION_CONFLICT")
            if record.status is not WorkflowStatus.PENDING or record.approval is None:
                raise ControlError("WORKFLOW_NOT_REVIEWABLE")
            request = record.approval
            if reviewer.valid_until < now or reviewer.authenticated_at > now:
                raise ControlError("REVIEWER_AUTHENTICATION_STALE")
            if reviewer.tenant_id != record.tenant_id:
                raise ControlError("REVIEWER_TENANT_MISMATCH")
            if reviewer.reviewer_id == record.subject_id:
                raise ControlError("SEPARATION_OF_DUTIES")
            if request.expires_at < now:
                expired = record.model_copy(update={
                    "status": WorkflowStatus.EXPIRED,
                    "version": record.version + 1,
                    "terminal_reason": "APPROVAL_EXPIRED",
                })
                self._records[workflow_id] = expired
                return expired
            used = {decision.reviewer_id for decision in record.decisions}
            if reviewer.reviewer_id in used:
                raise ControlError("DUPLICATE_REVIEW")
            eligible = sorted(request.required_roles.intersection(reviewer.roles))
            if not eligible:
                raise ControlError("REVIEWER_NOT_AUTHORIZED")
            already_filled = {decision.reviewer_role for decision in record.decisions}
            available = [role for role in eligible if role not in already_filled]
            if not available:
                raise ControlError("REVIEW_ROLE_ALREADY_FILLED")
            decision = ReviewDecision(
                reviewer_id=reviewer.reviewer_id,
                reviewer_role=available[0],
                choice=choice,
                request_id=request.request_id,
                action_digest=request.action_digest,
                decided_at=now,
            )
            decisions = record.decisions + (decision,)
            if choice is ReviewChoice.REJECT:
                status, reason = WorkflowStatus.REJECTED, "HUMAN_REJECTED"
            else:
                approved_roles = {
                    item.reviewer_role for item in decisions if item.choice is ReviewChoice.APPROVE
                }
                complete = request.required_roles.issubset(approved_roles) and len(approved_roles) >= request.quorum
                status, reason = (WorkflowStatus.READY, None) if complete else (WorkflowStatus.PENDING, None)
            updated = record.model_copy(update={
                "decisions": decisions,
                "status": status,
                "version": record.version + 1,
                "terminal_reason": reason,
            })
            self._records[workflow_id] = updated
            return updated

    def redirect(
        self,
        workflow_id: str,
        expected_version: int,
        operator: OperatorContext,
        replacement: ActionProposal,
        context: AuthenticatedContext,
        facts: TrustedFacts,
        now: datetime = REFERENCE_TIME,
    ) -> WorkflowRecord:
        with self._lock:
            record = self._records[workflow_id]
            if record.version != expected_version:
                raise ControlError("VERSION_CONFLICT")
            if operator.tenant_id != record.tenant_id or "oversight_operator" not in operator.roles:
                raise ControlError("OPERATOR_NOT_AUTHORIZED")
            if record.status not in {WorkflowStatus.PENDING, WorkflowStatus.READY}:
                raise ControlError("WORKFLOW_NOT_REDIRECTABLE")
            routed = route_action(context, replacement, facts, self.envelope, now)
            if routed.route is Route.DENY:
                raise ControlError(routed.reason_codes[0])
            roles = frozenset({"manager"}) if routed.route is Route.APPROVE else frozenset({"manager", "finance"})
            needs_review = routed.route in {Route.APPROVE, Route.MULTI_APPROVE}
            approval = ApprovalRequest(
                request_id="AR-" + stable_digest({"workflow": workflow_id, "action": routed.action_digest})[:16],
                action_digest=routed.action_digest,
                tenant_id=record.tenant_id,
                subject_id=record.subject_id,
                workload_id=record.workload_id,
                task_id=record.task_id,
                operation_id=replacement.operation_id,
                tool_name=replacement.tool_name,
                amount_cents=replacement.amount_cents,
                vendor_id=replacement.vendor_id,
                policy_version=self.envelope.policy_version,
                facts_version=facts.source_version,
                required_roles=roles,
                quorum=len(roles),
                created_at=now,
                expires_at=now + timedelta(hours=4),
            ) if needs_review else None
            requires_gate = routed.route in {Route.VERIFY, Route.APPROVE, Route.MULTI_APPROVE}
            updated = record.model_copy(update={
                "action": replacement,
                "route": routed.route,
                "status": WorkflowStatus.PENDING if requires_gate else WorkflowStatus.READY,
                "version": record.version + 1,
                "approval": approval,
                "verification": None,
                "decisions": (),
                "facts_version": facts.source_version,
                "terminal_reason": None,
            })
            self._records[workflow_id] = updated
            return updated

    def pause(
        self,
        workflow_id: str,
        expected_version: int,
        operator: OperatorContext,
    ) -> WorkflowRecord:
        """Stop the next effect; an effect already executing cannot be recalled."""

        with self._lock:
            record = self._records[workflow_id]
            if record.version != expected_version:
                raise ControlError("VERSION_CONFLICT")
            if operator.tenant_id != record.tenant_id or "oversight_operator" not in operator.roles:
                raise ControlError("OPERATOR_NOT_AUTHORIZED")
            if record.status not in {WorkflowStatus.PENDING, WorkflowStatus.READY}:
                raise ControlError("WORKFLOW_NOT_PAUSABLE")
            updated = record.model_copy(update={
                "status": WorkflowStatus.PAUSED,
                "paused_from": record.status,
                "version": record.version + 1,
            })
            self._records[workflow_id] = updated
            return updated

    def resume(
        self,
        workflow_id: str,
        expected_version: int,
        operator: OperatorContext,
        context: AuthenticatedContext,
        facts: TrustedFacts,
        now: datetime = REFERENCE_TIME,
    ) -> WorkflowRecord:
        """Resume only after current hard controls and the original route still hold."""

        with self._lock:
            record = self._records[workflow_id]
            if record.version != expected_version:
                raise ControlError("VERSION_CONFLICT")
            if operator.tenant_id != record.tenant_id or "oversight_operator" not in operator.roles:
                raise ControlError("OPERATOR_NOT_AUTHORIZED")
            if record.status is not WorkflowStatus.PAUSED or record.paused_from is None:
                raise ControlError("WORKFLOW_NOT_PAUSED")
            current = route_action(context, record.action, facts, self.envelope, now)
            if current.route is Route.DENY:
                raise ControlError(current.reason_codes[0])
            if current.route is not record.route or facts.source_version != record.facts_version:
                raise ControlError("OVERSIGHT_REEVALUATION_REQUIRED")
            updated = record.model_copy(update={
                "status": record.paused_from,
                "paused_from": None,
                "version": record.version + 1,
            })
            self._records[workflow_id] = updated
            return updated

    def terminate(
        self,
        workflow_id: str,
        expected_version: int,
        operator: OperatorContext,
    ) -> WorkflowRecord:
        with self._lock:
            record = self._records[workflow_id]
            if record.version != expected_version:
                raise ControlError("VERSION_CONFLICT")
            if operator.tenant_id != record.tenant_id or "oversight_operator" not in operator.roles:
                raise ControlError("OPERATOR_NOT_AUTHORIZED")
            if record.status in {WorkflowStatus.COMPLETED, WorkflowStatus.EXECUTING}:
                raise ControlError("TERMINATION_TOO_LATE")
            updated = record.model_copy(update={
                "status": WorkflowStatus.TERMINATED,
                "version": record.version + 1,
                "terminal_reason": "OPERATOR_TERMINATED",
            })
            self._records[workflow_id] = updated
            return updated

    def execute(
        self,
        workflow_id: str,
        expected_version: int,
        context: AuthenticatedContext,
        facts: TrustedFacts,
        now: datetime = REFERENCE_TIME,
    ) -> ExecutionResult:
        with self._lock:
            record = self._records[workflow_id]
            if record.version != expected_version:
                raise ControlError("VERSION_CONFLICT")
            if record.status is not WorkflowStatus.READY:
                raise ControlError("WORKFLOW_NOT_READY")
            if (
                context.tenant_id != record.tenant_id
                or context.subject_id != record.subject_id
                or context.workload_id != record.workload_id
                or context.task_id != record.task_id
            ):
                raise ControlError("EXECUTION_CONTEXT_MISMATCH")
            current = route_action(context, record.action, facts, self.envelope, now)
            if self.envelope.policy_version != record.policy_version:
                raise ControlError("POLICY_CHANGED")
            if current.route is Route.DENY:
                raise ControlError(current.reason_codes[0])
            if current.route is not record.route:
                raise ControlError("OVERSIGHT_ROUTE_CHANGED")
            if facts.source_version != record.facts_version:
                raise ControlError("TRUSTED_FACTS_CHANGED")
            if record.approval:
                if record.approval.expires_at < now:
                    raise ControlError("APPROVAL_EXPIRED")
                if record.approval.action_digest != stable_digest(record.action):
                    raise ControlError("ACTION_CHANGED_AFTER_APPROVAL")
                approved_roles = {
                    decision.reviewer_role
                    for decision in record.decisions
                    if decision.choice is ReviewChoice.APPROVE
                }
                if not record.approval.required_roles.issubset(approved_roles):
                    raise ControlError("APPROVAL_QUORUM_MISSING")
            if record.route is Route.VERIFY:
                if record.verification is None:
                    raise ControlError("VERIFICATION_MISSING")
                if record.verification.expires_at < now:
                    raise ControlError("VERIFICATION_EXPIRED")
                if record.verification.action_digest != stable_digest(record.action):
                    raise ControlError("ACTION_CHANGED_AFTER_VERIFICATION")
            key = (record.tenant_id, record.task_id)
            if self._actions[key] + 1 > self.envelope.task_action_limit:
                raise ControlError("ACTION_BUDGET_EXCEEDED")
            if self._spent[key] + record.action.amount_cents > self.envelope.task_spend_limit_cents:
                raise ControlError("SPEND_BUDGET_EXCEEDED")
            self._actions[key] += 1
            self._spent[key] += record.action.amount_cents
            executing = record.model_copy(update={
                "status": WorkflowStatus.EXECUTING,
                "version": record.version + 1,
            })
            self._records[workflow_id] = executing

        effect = self.adapter.execute(self._capability, record.tenant_id, record.action)
        if effect.status == "unknown":
            reconciled = self.adapter.reconcile(record.tenant_id, record.action.operation_id)
            if reconciled is not None:
                effect = reconciled
        verified = verify_effect(record.action, effect)
        with self._lock:
            latest = self._records[workflow_id]
            final = latest.model_copy(update={
                "status": WorkflowStatus.COMPLETED if verified else WorkflowStatus.FAILED,
                "version": latest.version + 1,
                "terminal_reason": None if verified else "OUTCOME_MISMATCH",
                "effect_id": effect.effect_id,
            })
            self._records[workflow_id] = final
        return ExecutionResult(
            workflow=final,
            effect=effect,
            verified=verified,
            reason_code="OUTCOME_VERIFIED" if verified else "OUTCOME_MISMATCH",
        )

    def budget_usage(self, context: AuthenticatedContext) -> tuple[int, int]:
        key = (context.tenant_id, context.task_id)
        return self._actions[key], self._spent[key]

    def checkpoint(self) -> str:
        """Serialize workflow and budget state for delayed human review or restart."""

        with self._lock:
            return json.dumps(
                {
                    "records": {
                        key: value.model_dump(mode="json")
                        for key, value in sorted(self._records.items())
                    },
                    "spent": [
                        [tenant, task, value]
                        for (tenant, task), value in sorted(self._spent.items())
                    ],
                    "actions": [
                        [tenant, task, value]
                        for (tenant, task), value in sorted(self._actions.items())
                    ],
                },
                sort_keys=True,
            )

    @classmethod
    def restore(cls, envelope: AutonomyEnvelope, checkpoint: str) -> "OversightSystem":
        """Restore typed state; pending reviews are visible through normal ``get``."""

        payload = json.loads(checkpoint)
        system = cls(envelope)
        system._records = {
            key: WorkflowRecord.model_validate(value)
            for key, value in payload["records"].items()
        }
        for tenant, task, value in payload["spent"]:
            system._spent[(tenant, task)] = value
        for tenant, task, value in payload["actions"]:
            system._actions[(tenant, task)] = value
        return system


def reviewer_metrics(events: Iterable[ReviewEvent], fast_threshold_seconds: float = 2.0) -> ReviewerMetrics:
    rows = tuple(events)
    if not rows:
        raise ValueError("review event population must not be empty")
    counts = Counter(event.reviewer_id for event in rows)
    approvals = sum(event.actual_choice is ReviewChoice.APPROVE for event in rows)
    return ReviewerMetrics(
        event_count=len(rows),
        approval_count=approvals,
        approval_rate=approvals / len(rows),
        median_latency_seconds=median(event.latency_seconds for event in rows),
        fast_approval_count=sum(
            event.actual_choice is ReviewChoice.APPROVE
            and event.latency_seconds < fast_threshold_seconds
            for event in rows
        ),
        disagreement_count=sum(
            event.expected_choice is not event.actual_choice for event in rows
        ),
        busiest_reviewer_count=max(counts.values()),
    )


@function_tool(needs_approval=True)
def openai_create_po(vendor_id: str, amount_cents: int) -> str:
    """Teaching descriptor only; production execution stays behind the gateway."""

    return f"proposal only: {vendor_id}:{amount_cents}"


@microsoft_tool(approval_mode="always_require")
def microsoft_create_po(vendor_id: str, amount_cents: int) -> str:
    """Teaching descriptor only; production execution stays behind the gateway."""

    return f"proposal only: {vendor_id}:{amount_cents}"


def sample_context(**changes: object) -> AuthenticatedContext:
    return AuthenticatedContext(
        subject_id="usr-requester-1042",
        workload_id="procurement-agent",
        tenant_id="tenant-north",
        task_id="task-office-renewal",
        authenticated_at=REFERENCE_TIME - timedelta(minutes=2),
        valid_until=REFERENCE_TIME + timedelta(minutes=15),
    ).model_copy(update=changes)


def sample_facts(**changes: object) -> TrustedFacts:
    return TrustedFacts(
        tenant_id="tenant-north",
        approved_vendors=frozenset({"VEN-101", "VEN-202"}),
        sanctioned_vendors=frozenset({"VEN-999"}),
        task_remaining_cents=5_000_000,
        source_version="procurement-facts/8471",
        observed_at=REFERENCE_TIME - timedelta(minutes=1),
        valid_until=REFERENCE_TIME + timedelta(minutes=10),
    ).model_copy(update=changes)


def sample_envelope(**changes: object) -> AutonomyEnvelope:
    return AutonomyEnvelope(
        policy_version="oversight-policy/2026-09-27",
        workload_id="procurement-agent",
        allowed_tools=frozenset({"procurement.create_po"}),
        valid_until=REFERENCE_TIME + timedelta(days=30),
    ).model_copy(update=changes)


def sample_action(**changes: object) -> ActionProposal:
    return ActionProposal(
        operation_id="OP-1001",
        tool_name="procurement.create_po",
        vendor_id="VEN-101",
        amount_cents=50_000,
    ).model_copy(update=changes)


def sample_reviewer(role: str = "manager", **changes: object) -> ReviewerContext:
    return ReviewerContext(
        reviewer_id=f"usr-{role}-2001",
        tenant_id="tenant-north",
        roles=frozenset({role}),
        authenticated_at=REFERENCE_TIME - timedelta(minutes=1),
        valid_until=REFERENCE_TIME + timedelta(minutes=30),
    ).model_copy(update=changes)


def labelled_evaluation() -> tuple[EvaluationCase, ...]:
    context, facts = sample_context(), sample_facts()
    return (
        EvaluationCase(name="routine reversible", context=context, action=sample_action(), facts=facts, expected=Route.AUTO_ALLOW),
        EvaluationCase(name="verification band", context=context, action=sample_action(operation_id="OP-1002", amount_cents=200_000), facts=facts, expected=Route.VERIFY),
        EvaluationCase(name="manager approval", context=context, action=sample_action(operation_id="OP-1003", amount_cents=600_000), facts=facts, expected=Route.APPROVE),
        EvaluationCase(name="dual approval", context=context, action=sample_action(operation_id="OP-1004", amount_cents=2_000_000), facts=facts, expected=Route.MULTI_APPROVE),
        EvaluationCase(name="irreversible", context=context, action=sample_action(operation_id="OP-1005", amount_cents=100_000, reversible=False), facts=facts, expected=Route.MULTI_APPROVE),
        EvaluationCase(name="sanctioned vendor", context=context, action=sample_action(operation_id="OP-1006", vendor_id="VEN-999"), facts=facts, expected=Route.DENY),
        EvaluationCase(name="unapproved vendor", context=context, action=sample_action(operation_id="OP-1007", vendor_id="VEN-303"), facts=facts, expected=Route.DENY),
        EvaluationCase(name="hard limit", context=context, action=sample_action(operation_id="OP-1008", amount_cents=5_500_000), facts=facts.model_copy(update={"task_remaining_cents": 6_000_000}), expected=Route.DENY),
        EvaluationCase(name="critical incident", context=context, action=sample_action(operation_id="OP-1009"), facts=facts.model_copy(update={"incident_mode": "critical"}), expected=Route.DENY),
        EvaluationCase(name="elevated incident", context=context, action=sample_action(operation_id="OP-1010"), facts=facts.model_copy(update={"incident_mode": "elevated"}), expected=Route.APPROVE),
    )


def run_evaluation() -> EvaluationSummary:
    cases = labelled_evaluation()
    envelope = sample_envelope()
    baseline = [unsafe_universal_hitl(case) for case in cases]
    candidate = [route_action(case.context, case.action, case.facts, envelope).route for case in cases]
    expected = [case.expected for case in cases]
    denies = [index for index, route in enumerate(expected) if route is Route.DENY]
    human_routes = {Route.APPROVE, Route.MULTI_APPROVE}
    return EvaluationSummary(
        case_count=len(cases),
        expected_auto_count=expected.count(Route.AUTO_ALLOW),
        expected_verify_count=expected.count(Route.VERIFY),
        expected_single_count=expected.count(Route.APPROVE),
        expected_multi_count=expected.count(Route.MULTI_APPROVE),
        expected_deny_count=expected.count(Route.DENY),
        baseline_correct_count=sum(got is want for got, want in zip(baseline, expected)),
        candidate_correct_count=sum(got is want for got, want in zip(candidate, expected)),
        baseline_human_review_count=sum(route in human_routes for route in baseline),
        candidate_human_review_count=sum(route in human_routes for route in candidate),
        baseline_hard_denial_overridden_count=sum(baseline[index] is Route.APPROVE for index in denies),
        candidate_hard_denial_overridden_count=sum(candidate[index] is not Route.DENY for index in denies),
    )
