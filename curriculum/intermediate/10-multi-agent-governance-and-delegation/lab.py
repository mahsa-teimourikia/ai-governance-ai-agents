"""Deterministic multi-agent governance lab for Course 10.

Models may propose delegation, handoffs, findings, and actions. This module keeps
identity, authority, context release, budgets, approvals, execution, revocation,
and terminal state in an application-owned control plane.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import IntEnum, StrEnum
import hashlib
import json
from threading import RLock
from typing import Iterable

from agents import Agent, handoff
from pydantic import BaseModel, ConfigDict, Field, model_validator


REFERENCE_TIME = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
APPROVAL_THRESHOLD_CAD = 5_000
TOOL_RESOURCE_POLICY = {
    "vendor.search": frozenset({"vendor-catalog"}),
    "vendor.read": frozenset({"vendor-catalog"}),
    "po.create": frozenset({"procurement"}),
    "payment.execute": frozenset({"payments"}),
}


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
    if isinstance(value, (IntEnum, StrEnum)):
        return value.value
    return value


def stable_digest(value: object) -> str:
    raw = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class Classification(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class ActorKind(StrEnum):
    HUMAN = "human"
    AGENT = "agent"


class RunState(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class FindingRisk(StrEnum):
    LOW = "low"
    HIGH = "high"


class FindingDisposition(StrEnum):
    PROCEED = "proceed"
    DENY = "deny"
    ESCALATE = "escalate"


class ControlError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class AuthenticatedIdentity(FrozenModel):
    subject_id: str
    tenant_id: str
    kind: ActorKind
    groups: frozenset[str]
    task_id: str
    authenticated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def valid_lifetime(self) -> "AuthenticatedIdentity":
        if self.valid_until <= self.authenticated_at:
            raise ValueError("authentication lifetime must be positive")
        return self


class AgentProfile(FrozenModel):
    agent_id: str = Field(pattern=r"^agent:[a-z0-9-]+$")
    tenant_id: str
    capability_tools: frozenset[str]
    executable_tools: frozenset[str]
    resources: frozenset[str]
    allowed_tool_resource_pairs: frozenset[tuple[str, str]]
    purposes: frozenset[str]
    allowed_context_fields: frozenset[str]
    clearance: Classification
    maximum_action_spend_cad: int = Field(ge=0)
    maximum_calls_per_grant: int = Field(ge=0)
    may_delegate: bool
    maximum_child_depth: int = Field(ge=0)

    @model_validator(mode="after")
    def execution_is_a_capability(self) -> "AgentProfile":
        if not self.executable_tools <= self.capability_tools:
            raise ValueError("executable tools must be capabilities")
        if any(tool not in self.capability_tools or resource not in self.resources
               for tool, resource in self.allowed_tool_resource_pairs):
            raise ValueError("tool-resource pairs must use declared capabilities")
        return self


class TaskAuthority(FrozenModel):
    operation_id: str = Field(pattern=r"^TASKOP-[A-Z0-9-]+$")
    tenant_id: str
    task_id: str
    principal_id: str
    purpose: str
    allowed_tools: frozenset[str]
    allowed_resources: frozenset[str]
    allowed_tool_resource_pairs: frozenset[tuple[str, str]]
    allowed_vendors: frozenset[str]
    maximum_spend_cad: int = Field(ge=0)
    maximum_calls: int = Field(ge=1)
    maximum_parallelism: int = Field(ge=1)
    maximum_delegation_depth: int = Field(ge=0)
    issued_at: datetime
    expires_at: datetime
    policy_version: str
    trace_id: str

    @model_validator(mode="after")
    def valid_lifetime(self) -> "TaskAuthority":
        if self.expires_at <= self.issued_at:
            raise ValueError("task authority lifetime must be positive")
        return self


class DelegationRequest(FrozenModel):
    operation_id: str = Field(pattern=r"^DELOP-[A-Z0-9-]+$")
    parent_grant_id: str
    child_agent_id: str
    purpose: str
    allowed_tools: frozenset[str]
    allowed_resources: frozenset[str]
    allowed_tool_resource_pairs: frozenset[tuple[str, str]] = frozenset()
    allowed_vendors: frozenset[str]
    maximum_action_spend_cad: int = Field(ge=0)
    maximum_calls: int = Field(ge=0)
    expires_at: datetime


class DelegationGrant(FrozenModel):
    grant_id: str
    parent_grant_id: str | None
    tenant_id: str
    task_id: str
    issuer_id: str
    subject_agent_id: str
    on_behalf_of: str
    purpose: str
    allowed_tools: frozenset[str]
    allowed_resources: frozenset[str]
    allowed_tool_resource_pairs: frozenset[tuple[str, str]]
    allowed_vendors: frozenset[str]
    maximum_action_spend_cad: int
    maximum_calls: int
    remaining_delegation_depth: int
    issued_at: datetime
    expires_at: datetime
    policy_version: str
    trace_id: str
    version: int = 1
    revoked: bool = False
    revocation_reason: str | None = None


class ContextItem(FrozenModel):
    name: str
    value: str
    classification: Classification
    source_id: str


class HandoffEnvelope(FrozenModel):
    handoff_id: str
    operation_id: str = Field(pattern=r"^HANDOP-[A-Z0-9-]+$")
    from_agent_id: str
    to_agent_id: str
    delegation_grant_id: str
    tenant_id: str
    task_id: str
    purpose: str
    requested_output: str
    context: tuple[ContextItem, ...]
    issued_at: datetime
    expires_at: datetime
    payload_digest: str


class HandoffDecision(FrozenModel):
    allowed: bool
    reason_code: str
    forwarded_context: tuple[ContextItem, ...] = ()
    instruction_indicators: tuple[str, ...] = ()


class ActionProposal(FrozenModel):
    operation_id: str = Field(pattern=r"^ACTOP-[A-Z0-9-]+$")
    actor_agent_id: str
    requester_grant_id: str
    tool: str
    resource: str
    vendor_id: str
    amount_cad: int = Field(ge=0)
    quantity: int = Field(ge=1)
    description: str


class ApprovalReceipt(FrozenModel):
    approval_id: str
    tenant_id: str
    task_id: str
    grant_id: str
    proposal_digest: str
    chain_digest: str
    approver_id: str
    approver_group: str
    policy_version: str
    issued_at: datetime
    expires_at: datetime


class PolicyDecision(FrozenModel):
    allowed: bool
    reason_code: str
    chain_digest: str | None = None


class WorkerLease(FrozenModel):
    lease_id: str
    operation_id: str = Field(pattern=r"^LEASEOP-[A-Z0-9-]+$")
    tenant_id: str
    task_id: str
    grant_id: str
    agent_id: str
    issued_at: datetime
    expires_at: datetime
    released: bool = False
    version: int = 1


class ActionReceipt(FrozenModel):
    receipt_id: str
    tenant_id: str
    task_id: str
    operation_id: str
    actor_agent_id: str
    tool: str
    resource: str
    vendor_id: str
    amount_cad: int
    proposal_digest: str
    chain_digest: str
    approval_id: str | None
    external_effect_id: str
    status: str
    executed_at: datetime


class AuditEvent(FrozenModel):
    event_id: str
    event_type: str
    tenant_id: str
    task_id: str
    actor_id: str
    trace_id: str
    reason_code: str
    artifact_id: str | None
    created_at: datetime


class SpecialistFinding(FrozenModel):
    agent_id: str
    vendor_id: str
    risk: FindingRisk
    evidence_ids: tuple[str, ...]


class FindingResolution(FrozenModel):
    disposition: FindingDisposition
    reason_code: str
    evidence_ids: tuple[str, ...]


class GovernanceMetrics(FrozenModel):
    grant_count: int
    active_grant_count: int
    revoked_grant_count: int
    maximum_depth_used: int
    calls_used: int
    spend_used_cad: int
    simulated_effect_count: int
    event_count: int


class EvaluationSummary(FrozenModel):
    case_count: int
    baseline_correct_count: int
    governed_correct_count: int
    baseline_forbidden_allow_count: int
    governed_forbidden_allow_count: int


INSTRUCTION_MARKERS = {
    "IGNORE_PREVIOUS": "ignore previous instructions",
    "AUTHORITY_CLAIM": "you are now authorized",
    "POLICY_BYPASS": "bypass policy",
    "SECRET_REQUEST": "reveal system prompt",
}


def instruction_indicators(text: str) -> tuple[str, ...]:
    folded = text.casefold()
    return tuple(code for code, marker in INSTRUCTION_MARKERS.items() if marker in folded)


def _authenticate(identity: AuthenticatedIdentity, now: datetime) -> None:
    if identity.authenticated_at > now or identity.valid_until <= now:
        raise ControlError("AUTHENTICATION_STALE")


class MultiAgentControlPlane:
    """Single-process reference control plane with atomic local invariants."""

    def __init__(self, profiles: Iterable[AgentProfile]):
        profile_rows = tuple(profiles)
        self._profiles = {(p.tenant_id, p.agent_id): p for p in profile_rows}
        if len(self._profiles) != len(profile_rows):
            raise ValueError("agent profile identity must be unique")
        self._tasks: dict[tuple[str, str], TaskAuthority] = {}
        self._states: dict[tuple[str, str], RunState] = {}
        self._grants: dict[str, DelegationGrant] = {}
        self._task_roots: dict[tuple[str, str], str] = {}
        self._task_operations: dict[tuple[str, str, str], tuple[str, str]] = {}
        self._delegation_operations: dict[tuple[str, str, str], tuple[str, str]] = {}
        self._handoff_operations: dict[tuple[str, str, str], tuple[str, str]] = {}
        self._handoffs: dict[str, HandoffEnvelope] = {}
        self._approvals: dict[str, ApprovalReceipt] = {}
        self._approval_operations: dict[tuple[str, str, str], tuple[str, str]] = {}
        self._consumed_approvals: set[str] = set()
        self._action_operations: dict[tuple[str, str, str], tuple[str, str]] = {}
        self._receipts: dict[str, ActionReceipt] = {}
        self._lease_operations: dict[tuple[str, str, str], tuple[str, str]] = {}
        self._leases: dict[str, WorkerLease] = {}
        self._calls_used: dict[tuple[str, str], int] = defaultdict(int)
        self._grant_calls_used: dict[str, int] = defaultdict(int)
        self._spend_used: dict[tuple[str, str], int] = defaultdict(int)
        self._effects: dict[str, ActionReceipt] = {}
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def _profile(self, tenant_id: str, agent_id: str) -> AgentProfile:
        profile = self._profiles.get((tenant_id, agent_id))
        if profile is None:
            raise ControlError("AGENT_NOT_REGISTERED")
        return profile

    def _event(
        self,
        event_type: str,
        tenant_id: str,
        task_id: str,
        actor_id: str,
        trace_id: str,
        reason_code: str,
        artifact_id: str | None,
        now: datetime,
    ) -> None:
        ordinal = len(self._events) + 1
        event_id = "EVT-" + stable_digest({
            "ordinal": ordinal,
            "event_type": event_type,
            "artifact_id": artifact_id,
            "now": now,
        })[:16]
        self._events.append(AuditEvent(
            event_id=event_id,
            event_type=event_type,
            tenant_id=tenant_id,
            task_id=task_id,
            actor_id=actor_id,
            trace_id=trace_id,
            reason_code=reason_code,
            artifact_id=artifact_id,
            created_at=now,
        ))

    def open_task(
        self,
        principal: AuthenticatedIdentity,
        authority: TaskAuthority,
        manager_agent_id: str,
        now: datetime = REFERENCE_TIME,
    ) -> DelegationGrant:
        _authenticate(principal, now)
        if principal.kind is not ActorKind.HUMAN:
            raise ControlError("TASK_REQUIRES_HUMAN_PRINCIPAL")
        if (
            principal.tenant_id != authority.tenant_id
            or principal.task_id != authority.task_id
            or principal.subject_id != authority.principal_id
        ):
            raise ControlError("TASK_PRINCIPAL_MISMATCH")
        if authority.issued_at > now or authority.expires_at <= now:
            raise ControlError("TASK_AUTHORITY_NOT_CURRENT")
        profile = self._profile(authority.tenant_id, manager_agent_id)
        if authority.purpose not in profile.purposes:
            raise ControlError("TASK_PURPOSE_NOT_ALLOWED")
        if not authority.allowed_tools <= profile.capability_tools:
            raise ControlError("TASK_TOOL_CAPABILITY_EXCEEDED")
        if not authority.allowed_resources <= profile.resources:
            raise ControlError("TASK_RESOURCE_CAPABILITY_EXCEEDED")
        if not authority.allowed_tool_resource_pairs <= profile.allowed_tool_resource_pairs:
            raise ControlError("TASK_TOOL_RESOURCE_PAIR_EXCEEDED")
        if any(
            tool not in authority.allowed_tools or resource not in authority.allowed_resources
            for tool, resource in authority.allowed_tool_resource_pairs
        ):
            raise ControlError("TASK_TOOL_RESOURCE_SCOPE_MISMATCH")
        if any(
            tool not in authority.allowed_tools or resource not in authority.allowed_resources
            for tool, resource in authority.allowed_tool_resource_pairs
        ):
            raise ControlError("TASK_TOOL_RESOURCE_SCOPE_MISMATCH")
        if authority.maximum_spend_cad > profile.maximum_action_spend_cad:
            raise ControlError("TASK_SPEND_CAPABILITY_EXCEEDED")
        if authority.maximum_calls > profile.maximum_calls_per_grant:
            raise ControlError("TASK_CALL_CAPABILITY_EXCEEDED")
        if authority.maximum_delegation_depth > profile.maximum_child_depth:
            raise ControlError("TASK_DEPTH_CAPABILITY_EXCEEDED")
        operation_key = (authority.tenant_id, authority.task_id, authority.operation_id)
        request_digest = stable_digest({"authority": authority, "manager": manager_agent_id})
        with self._lock:
            prior = self._task_operations.get(operation_key)
            if prior is not None:
                prior_digest, grant_id = prior
                if prior_digest != request_digest:
                    raise ControlError("TASK_OPERATION_MUTATION")
                return self._grants[grant_id]
            task_key = (authority.tenant_id, authority.task_id)
            if task_key in self._tasks:
                raise ControlError("TASK_ALREADY_EXISTS")
            grant_id = "GRANT-" + request_digest[:16]
            grant = DelegationGrant(
                grant_id=grant_id,
                parent_grant_id=None,
                tenant_id=authority.tenant_id,
                task_id=authority.task_id,
                issuer_id=authority.principal_id,
                subject_agent_id=manager_agent_id,
                on_behalf_of=authority.principal_id,
                purpose=authority.purpose,
                allowed_tools=authority.allowed_tools,
                allowed_resources=authority.allowed_resources,
                allowed_tool_resource_pairs=authority.allowed_tool_resource_pairs,
                allowed_vendors=authority.allowed_vendors,
                maximum_action_spend_cad=authority.maximum_spend_cad,
                maximum_calls=authority.maximum_calls,
                remaining_delegation_depth=authority.maximum_delegation_depth,
                issued_at=now,
                expires_at=authority.expires_at,
                policy_version=authority.policy_version,
                trace_id=authority.trace_id,
            )
            self._tasks[task_key] = authority
            self._states[task_key] = RunState.RUNNING
            self._grants[grant_id] = grant
            self._task_roots[task_key] = grant_id
            self._task_operations[operation_key] = (request_digest, grant_id)
            self._event("task_opened", authority.tenant_id, authority.task_id, principal.subject_id,
                        authority.trace_id, "TASK_AUTHORITY_ACCEPTED", grant_id, now)
            return grant

    def _chain_unlocked(self, grant_id: str) -> tuple[DelegationGrant, ...]:
        chain: list[DelegationGrant] = []
        seen: set[str] = set()
        current = self._grants.get(grant_id)
        while current is not None:
            if current.grant_id in seen:
                raise ControlError("DELEGATION_CYCLE")
            seen.add(current.grant_id)
            chain.append(current)
            current = self._grants.get(current.parent_grant_id) if current.parent_grant_id else None
        if not chain or (chain[-1].parent_grant_id is not None):
            raise ControlError("DELEGATION_LINEAGE_INCOMPLETE")
        return tuple(reversed(chain))

    def chain(self, grant_id: str) -> tuple[DelegationGrant, ...]:
        with self._lock:
            return self._chain_unlocked(grant_id)

    def _validate_chain_unlocked(self, grant_id: str, now: datetime) -> tuple[DelegationGrant, ...]:
        chain = self._chain_unlocked(grant_id)
        root = chain[0]
        for index, grant in enumerate(chain):
            if grant.tenant_id != root.tenant_id or grant.task_id != root.task_id:
                raise ControlError("DELEGATION_SCOPE_MISMATCH")
            if grant.revoked:
                raise ControlError("DELEGATION_REVOKED")
            if grant.issued_at > now or grant.expires_at <= now:
                raise ControlError("DELEGATION_EXPIRED")
            if index > 0:
                parent = chain[index - 1]
                if grant.parent_grant_id != parent.grant_id or grant.issuer_id != parent.subject_agent_id:
                    raise ControlError("DELEGATION_LINEAGE_INVALID")
                if not grant.allowed_tools <= parent.allowed_tools:
                    raise ControlError("DELEGATION_TOOL_AMPLIFICATION")
                if not grant.allowed_resources <= parent.allowed_resources:
                    raise ControlError("DELEGATION_RESOURCE_AMPLIFICATION")
                if not grant.allowed_tool_resource_pairs <= parent.allowed_tool_resource_pairs:
                    raise ControlError("DELEGATION_TOOL_RESOURCE_AMPLIFICATION")
                if not grant.allowed_vendors <= parent.allowed_vendors:
                    raise ControlError("DELEGATION_VENDOR_AMPLIFICATION")
                if grant.maximum_action_spend_cad > parent.maximum_action_spend_cad:
                    raise ControlError("DELEGATION_SPEND_AMPLIFICATION")
                if grant.maximum_calls > parent.maximum_calls:
                    raise ControlError("DELEGATION_CALL_AMPLIFICATION")
        return chain

    def delegate(
        self,
        issuer: AuthenticatedIdentity,
        request: DelegationRequest,
        now: datetime = REFERENCE_TIME,
    ) -> DelegationGrant:
        _authenticate(issuer, now)
        if issuer.kind is not ActorKind.AGENT:
            raise ControlError("DELEGATION_REQUIRES_AGENT_ISSUER")
        with self._lock:
            parent = self._grants.get(request.parent_grant_id)
            if parent is None:
                raise ControlError("PARENT_GRANT_NOT_FOUND")
            if issuer.tenant_id != parent.tenant_id or issuer.task_id != parent.task_id:
                raise ControlError("DELEGATION_ISSUER_SCOPE_MISMATCH")
            if issuer.subject_id != parent.subject_agent_id:
                raise ControlError("DELEGATION_ISSUER_NOT_PARENT_SUBJECT")
            operation_key = (parent.tenant_id, parent.task_id, request.operation_id)
            request_digest = stable_digest(request)
            prior = self._delegation_operations.get(operation_key)
            if prior is not None:
                prior_digest, grant_id = prior
                if prior_digest != request_digest:
                    raise ControlError("DELEGATION_OPERATION_MUTATION")
                return self._grants[grant_id]
            if self._states[(parent.tenant_id, parent.task_id)] is not RunState.RUNNING:
                raise ControlError("TASK_NOT_RUNNING")
            self._validate_chain_unlocked(parent.grant_id, now)
            issuer_profile = self._profile(parent.tenant_id, issuer.subject_id)
            child_profile = self._profile(parent.tenant_id, request.child_agent_id)
            if not issuer_profile.may_delegate or parent.remaining_delegation_depth <= 0:
                raise ControlError("DELEGATION_DEPTH_EXHAUSTED")
            if request.purpose != parent.purpose or request.purpose not in child_profile.purposes:
                raise ControlError("DELEGATION_PURPOSE_MISMATCH")
            if not request.allowed_tools <= parent.allowed_tools:
                raise ControlError("DELEGATION_TOOL_AMPLIFICATION")
            if not request.allowed_tools <= issuer_profile.capability_tools:
                raise ControlError("ISSUER_CANNOT_DELEGATE_TOOL")
            if not request.allowed_tools <= child_profile.capability_tools:
                raise ControlError("CHILD_TOOL_CAPABILITY_EXCEEDED")
            if not request.allowed_resources <= parent.allowed_resources:
                raise ControlError("DELEGATION_RESOURCE_AMPLIFICATION")
            if not request.allowed_resources <= child_profile.resources:
                raise ControlError("CHILD_RESOURCE_CAPABILITY_EXCEEDED")
            if not request.allowed_tool_resource_pairs <= parent.allowed_tool_resource_pairs:
                raise ControlError("DELEGATION_TOOL_RESOURCE_AMPLIFICATION")
            if not request.allowed_tool_resource_pairs <= child_profile.allowed_tool_resource_pairs:
                raise ControlError("CHILD_TOOL_RESOURCE_CAPABILITY_EXCEEDED")
            if any(tool not in request.allowed_tools or resource not in request.allowed_resources
                   for tool, resource in request.allowed_tool_resource_pairs):
                raise ControlError("DELEGATION_TOOL_RESOURCE_SCOPE_MISMATCH")
            if not request.allowed_vendors <= parent.allowed_vendors:
                raise ControlError("DELEGATION_VENDOR_AMPLIFICATION")
            if request.maximum_action_spend_cad > min(
                parent.maximum_action_spend_cad, child_profile.maximum_action_spend_cad
            ):
                raise ControlError("DELEGATION_SPEND_AMPLIFICATION")
            if request.maximum_calls > min(parent.maximum_calls, child_profile.maximum_calls_per_grant):
                raise ControlError("DELEGATION_CALL_AMPLIFICATION")
            if request.expires_at <= now or request.expires_at > parent.expires_at:
                raise ControlError("DELEGATION_EXPIRY_INVALID")
            remaining_depth = min(
                parent.remaining_delegation_depth - 1,
                child_profile.maximum_child_depth,
            )
            grant_id = "GRANT-" + stable_digest({
                "parent": parent.grant_id,
                "request": request,
                "issuer": issuer.subject_id,
            })[:16]
            grant = DelegationGrant(
                grant_id=grant_id,
                parent_grant_id=parent.grant_id,
                tenant_id=parent.tenant_id,
                task_id=parent.task_id,
                issuer_id=issuer.subject_id,
                subject_agent_id=request.child_agent_id,
                on_behalf_of=parent.on_behalf_of,
                purpose=request.purpose,
                allowed_tools=request.allowed_tools,
                allowed_resources=request.allowed_resources,
                allowed_tool_resource_pairs=request.allowed_tool_resource_pairs,
                allowed_vendors=request.allowed_vendors,
                maximum_action_spend_cad=request.maximum_action_spend_cad,
                maximum_calls=request.maximum_calls,
                remaining_delegation_depth=remaining_depth,
                issued_at=now,
                expires_at=request.expires_at,
                policy_version=parent.policy_version,
                trace_id=parent.trace_id,
            )
            self._grants[grant_id] = grant
            self._delegation_operations[operation_key] = (request_digest, grant_id)
            self._event("delegation_issued", parent.tenant_id, parent.task_id, issuer.subject_id,
                        parent.trace_id, "ATTENUATED_GRANT_ISSUED", grant_id, now)
            return grant

    def create_handoff(
        self,
        issuer: AuthenticatedIdentity,
        grant_id: str,
        operation_id: str,
        requested_output: str,
        context: tuple[ContextItem, ...],
        now: datetime = REFERENCE_TIME,
        ttl: timedelta = timedelta(minutes=5),
    ) -> HandoffEnvelope:
        _authenticate(issuer, now)
        with self._lock:
            grant = self._grants.get(grant_id)
            if grant is None:
                raise ControlError("HANDOFF_GRANT_NOT_FOUND")
            if issuer.subject_id != grant.issuer_id or issuer.tenant_id != grant.tenant_id:
                raise ControlError("HANDOFF_ISSUER_MISMATCH")
            self._validate_chain_unlocked(grant_id, now)
            operation_key = (grant.tenant_id, grant.task_id, operation_id)
            request = {
                "operation_id": operation_id,
                "grant_id": grant_id,
                "requested_output": requested_output,
                "context": context,
                "issuer": issuer.subject_id,
            }
            request_digest = stable_digest(request)
            prior = self._handoff_operations.get(operation_key)
            if prior is not None:
                prior_digest, handoff_id = prior
                if prior_digest != request_digest:
                    raise ControlError("HANDOFF_OPERATION_MUTATION")
                return self._handoffs[handoff_id]
            handoff_id = "HANDOFF-" + request_digest[:16]
            envelope = HandoffEnvelope(
                handoff_id=handoff_id,
                operation_id=operation_id,
                from_agent_id=grant.issuer_id,
                to_agent_id=grant.subject_agent_id,
                delegation_grant_id=grant.grant_id,
                tenant_id=grant.tenant_id,
                task_id=grant.task_id,
                purpose=grant.purpose,
                requested_output=requested_output,
                context=context,
                issued_at=now,
                expires_at=min(grant.expires_at, now + ttl),
                payload_digest=stable_digest(context),
            )
            self._handoff_operations[operation_key] = (request_digest, handoff_id)
            self._handoffs[handoff_id] = envelope
            self._event("handoff_created", grant.tenant_id, grant.task_id, issuer.subject_id,
                        grant.trace_id, "STRUCTURED_HANDOFF_CREATED", handoff_id, now)
            return envelope

    def validate_handoff(
        self,
        issuer: AuthenticatedIdentity,
        envelope: HandoffEnvelope,
        now: datetime = REFERENCE_TIME,
    ) -> HandoffDecision:
        try:
            _authenticate(issuer, now)
            with self._lock:
                grant = self._grants.get(envelope.delegation_grant_id)
                if grant is None:
                    raise ControlError("HANDOFF_GRANT_NOT_FOUND")
                if issuer.subject_id != envelope.from_agent_id or issuer.kind is not ActorKind.AGENT:
                    raise ControlError("HANDOFF_SENDER_NOT_AUTHENTICATED")
                if (
                    envelope.from_agent_id != grant.issuer_id
                    or envelope.to_agent_id != grant.subject_agent_id
                    or envelope.tenant_id != grant.tenant_id
                    or envelope.task_id != grant.task_id
                    or envelope.purpose != grant.purpose
                ):
                    raise ControlError("HANDOFF_GRANT_BINDING_MISMATCH")
                if envelope.issued_at > now or envelope.expires_at <= now:
                    raise ControlError("HANDOFF_EXPIRED")
                if envelope.payload_digest != stable_digest(envelope.context):
                    raise ControlError("HANDOFF_PAYLOAD_TAMPERED")
                self._validate_chain_unlocked(grant.grant_id, now)
                profile = self._profile(grant.tenant_id, grant.subject_agent_id)
                indicators = tuple(sorted({
                    code
                    for item in envelope.context
                    for code in instruction_indicators(item.value)
                }))
                if indicators:
                    return HandoffDecision(
                        allowed=False,
                        reason_code="HANDOFF_INSTRUCTION_CONTENT_QUARANTINED",
                        instruction_indicators=indicators,
                    )
                if any(item.name not in profile.allowed_context_fields for item in envelope.context):
                    raise ControlError("HANDOFF_CONTEXT_FIELD_NOT_ALLOWED")
                if any(item.classification > profile.clearance for item in envelope.context):
                    raise ControlError("HANDOFF_CONTEXT_CLEARANCE_EXCEEDED")
                return HandoffDecision(
                    allowed=True,
                    reason_code="HANDOFF_ALLOWED",
                    forwarded_context=envelope.context,
                )
        except ControlError as error:
            return HandoffDecision(allowed=False, reason_code=error.code)

    def _proposal_decision_unlocked(
        self,
        actor: AuthenticatedIdentity,
        grant_id: str,
        proposal: ActionProposal,
        approval_id: str | None,
        now: datetime,
    ) -> PolicyDecision:
        _authenticate(actor, now)
        grant = self._grants.get(grant_id)
        if grant is None:
            raise ControlError("ACTION_GRANT_NOT_FOUND")
        if actor.kind is not ActorKind.AGENT or actor.subject_id != grant.subject_agent_id:
            raise ControlError("ACTION_ACTOR_NOT_GRANT_SUBJECT")
        if actor.tenant_id != grant.tenant_id or actor.task_id != grant.task_id:
            raise ControlError("ACTION_ACTOR_SCOPE_MISMATCH")
        if proposal.actor_agent_id != actor.subject_id:
            raise ControlError("ACTION_PROPOSAL_ACTOR_MISMATCH")
        task_key = (grant.tenant_id, grant.task_id)
        if self._states[task_key] is not RunState.RUNNING:
            raise ControlError("TASK_NOT_RUNNING")
        chain = self._validate_chain_unlocked(grant_id, now)
        chain_ids = {item.grant_id for item in chain}
        if proposal.requester_grant_id not in chain_ids:
            raise ControlError("REQUESTER_NOT_IN_DELEGATION_CHAIN")
        requester = self._grants[proposal.requester_grant_id]
        if proposal.tool not in requester.allowed_tools:
            raise ControlError("REQUESTER_LACKS_TOOL_AUTHORITY")
        profile = self._profile(grant.tenant_id, actor.subject_id)
        if proposal.tool not in grant.allowed_tools or proposal.tool not in profile.executable_tools:
            raise ControlError("ACTION_TOOL_NOT_AUTHORIZED")
        if proposal.resource not in grant.allowed_resources or proposal.resource not in profile.resources:
            raise ControlError("ACTION_RESOURCE_NOT_AUTHORIZED")
        if (
            (proposal.tool, proposal.resource) not in grant.allowed_tool_resource_pairs
            or (proposal.tool, proposal.resource) not in profile.allowed_tool_resource_pairs
        ):
            raise ControlError("ACTION_TOOL_RESOURCE_PAIR_NOT_AUTHORIZED")
        if proposal.resource not in TOOL_RESOURCE_POLICY.get(proposal.tool, frozenset()):
            raise ControlError("ACTION_TOOL_RESOURCE_PAIR_NOT_AUTHORIZED")
        if proposal.vendor_id not in grant.allowed_vendors:
            raise ControlError("ACTION_VENDOR_NOT_AUTHORIZED")
        if proposal.amount_cad > min(grant.maximum_action_spend_cad, profile.maximum_action_spend_cad):
            raise ControlError("ACTION_AMOUNT_NOT_AUTHORIZED")
        chain_digest = stable_digest(tuple((item.grant_id, item.version) for item in chain))
        if proposal.amount_cad > APPROVAL_THRESHOLD_CAD:
            if approval_id is None:
                raise ControlError("ACTION_APPROVAL_REQUIRED")
            approval = self._approvals.get(approval_id)
            if approval is None:
                raise ControlError("ACTION_APPROVAL_NOT_FOUND")
            if approval_id in self._consumed_approvals:
                raise ControlError("ACTION_APPROVAL_CONSUMED")
            if approval.expires_at <= now:
                raise ControlError("ACTION_APPROVAL_EXPIRED")
            if (
                approval.tenant_id != grant.tenant_id
                or approval.task_id != grant.task_id
                or approval.grant_id != grant_id
                or approval.proposal_digest != stable_digest(proposal)
                or approval.chain_digest != chain_digest
                or approval.policy_version != grant.policy_version
            ):
                raise ControlError("ACTION_APPROVAL_BINDING_MISMATCH")
        return PolicyDecision(allowed=True, reason_code="ACTION_AUTHORIZED", chain_digest=chain_digest)

    def preview_action(
        self,
        actor: AuthenticatedIdentity,
        grant_id: str,
        proposal: ActionProposal,
        approval_id: str | None = None,
        now: datetime = REFERENCE_TIME,
    ) -> PolicyDecision:
        try:
            with self._lock:
                return self._proposal_decision_unlocked(actor, grant_id, proposal, approval_id, now)
        except ControlError as error:
            return PolicyDecision(allowed=False, reason_code=error.code)

    def issue_approval(
        self,
        approver: AuthenticatedIdentity,
        grant_id: str,
        proposal: ActionProposal,
        operation_id: str,
        now: datetime = REFERENCE_TIME,
        ttl: timedelta = timedelta(minutes=10),
    ) -> ApprovalReceipt:
        _authenticate(approver, now)
        if approver.kind is not ActorKind.HUMAN or "procurement-approver" not in approver.groups:
            raise ControlError("APPROVER_NOT_AUTHORIZED")
        with self._lock:
            grant = self._grants.get(grant_id)
            if grant is None:
                raise ControlError("ACTION_GRANT_NOT_FOUND")
            if approver.tenant_id != grant.tenant_id or approver.task_id != grant.task_id:
                raise ControlError("APPROVER_SCOPE_MISMATCH")
            chain = self._validate_chain_unlocked(grant_id, now)
            chain_digest = stable_digest(tuple((item.grant_id, item.version) for item in chain))
            proposal_digest = stable_digest(proposal)
            operation_key = (grant.tenant_id, grant.task_id, operation_id)
            request_digest = stable_digest({
                "operation_id": operation_id,
                "grant": grant_id,
                "proposal": proposal_digest,
                "chain": chain_digest,
                "approver": approver.subject_id,
            })
            prior = self._approval_operations.get(operation_key)
            if prior is not None:
                prior_digest, approval_id = prior
                if prior_digest != request_digest:
                    raise ControlError("APPROVAL_OPERATION_MUTATION")
                return self._approvals[approval_id]
            approval_id = "APPROVAL-" + request_digest[:16]
            receipt = ApprovalReceipt(
                approval_id=approval_id,
                tenant_id=grant.tenant_id,
                task_id=grant.task_id,
                grant_id=grant_id,
                proposal_digest=proposal_digest,
                chain_digest=chain_digest,
                approver_id=approver.subject_id,
                approver_group="procurement-approver",
                policy_version=grant.policy_version,
                issued_at=now,
                expires_at=min(grant.expires_at, now + ttl),
            )
            self._approvals[approval_id] = receipt
            self._approval_operations[operation_key] = (request_digest, approval_id)
            self._event("approval_issued", grant.tenant_id, grant.task_id, approver.subject_id,
                        grant.trace_id, "PROPOSAL_BOUND_APPROVAL", approval_id, now)
            return receipt

    def execute(
        self,
        actor: AuthenticatedIdentity,
        grant_id: str,
        proposal: ActionProposal,
        approval_id: str | None = None,
        now: datetime = REFERENCE_TIME,
    ) -> ActionReceipt:
        _authenticate(actor, now)
        request_digest = stable_digest({"grant_id": grant_id, "proposal": proposal})
        operation_key = (actor.tenant_id, actor.task_id, proposal.operation_id)
        with self._lock:
            prior = self._action_operations.get(operation_key)
            if prior is not None:
                prior_digest, receipt_id = prior
                if prior_digest != request_digest:
                    raise ControlError("ACTION_OPERATION_MUTATION")
                return self._receipts[receipt_id]
            decision = self._proposal_decision_unlocked(actor, grant_id, proposal, approval_id, now)
            grant = self._grants[grant_id]
            task_key = (grant.tenant_id, grant.task_id)
            authority = self._tasks[task_key]
            if self._calls_used[task_key] + 1 > authority.maximum_calls:
                raise ControlError("TASK_CALL_BUDGET_EXHAUSTED")
            if self._grant_calls_used[grant_id] + 1 > grant.maximum_calls:
                raise ControlError("GRANT_CALL_BUDGET_EXHAUSTED")
            if self._spend_used[task_key] + proposal.amount_cad > authority.maximum_spend_cad:
                raise ControlError("TASK_SPEND_BUDGET_EXHAUSTED")
            if approval_id is not None:
                self._consumed_approvals.add(approval_id)
            self._calls_used[task_key] += 1
            self._grant_calls_used[grant_id] += 1
            self._spend_used[task_key] += proposal.amount_cad
            proposal_digest = stable_digest(proposal)
            receipt_id = "RECEIPT-" + request_digest[:16]
            receipt = ActionReceipt(
                receipt_id=receipt_id,
                tenant_id=grant.tenant_id,
                task_id=grant.task_id,
                operation_id=proposal.operation_id,
                actor_agent_id=actor.subject_id,
                tool=proposal.tool,
                resource=proposal.resource,
                vendor_id=proposal.vendor_id,
                amount_cad=proposal.amount_cad,
                proposal_digest=proposal_digest,
                chain_digest=decision.chain_digest or "",
                approval_id=approval_id,
                external_effect_id="SIM-PO-" + proposal_digest[:12].upper(),
                status="simulated",
                executed_at=now,
            )
            self._action_operations[operation_key] = (request_digest, receipt_id)
            self._receipts[receipt_id] = receipt
            self._effects[proposal_digest] = receipt
            self._event("action_simulated", grant.tenant_id, grant.task_id, actor.subject_id,
                        grant.trace_id, "SIMULATED_EFFECT_RECORDED", receipt_id, now)
            return receipt

    def acquire_worker_slot(
        self,
        actor: AuthenticatedIdentity,
        grant_id: str,
        operation_id: str,
        now: datetime = REFERENCE_TIME,
        ttl: timedelta = timedelta(minutes=5),
    ) -> WorkerLease:
        _authenticate(actor, now)
        with self._lock:
            grant = self._grants.get(grant_id)
            if grant is None:
                raise ControlError("LEASE_GRANT_NOT_FOUND")
            if (
                actor.kind is not ActorKind.AGENT
                or actor.subject_id != grant.subject_agent_id
                or actor.tenant_id != grant.tenant_id
                or actor.task_id != grant.task_id
            ):
                raise ControlError("LEASE_ACTOR_MISMATCH")
            operation_key = (grant.tenant_id, grant.task_id, operation_id)
            request_digest = stable_digest({
                "operation_id": operation_id,
                "grant_id": grant_id,
                "actor": actor.subject_id,
            })
            prior = self._lease_operations.get(operation_key)
            if prior is not None:
                prior_digest, lease_id = prior
                if prior_digest != request_digest:
                    raise ControlError("LEASE_OPERATION_MUTATION")
                return self._leases[lease_id]
            task_key = (grant.tenant_id, grant.task_id)
            if self._states[task_key] is not RunState.RUNNING:
                raise ControlError("TASK_NOT_RUNNING")
            self._validate_chain_unlocked(grant_id, now)
            authority = self._tasks[task_key]
            active = sum(
                lease.tenant_id == grant.tenant_id
                and lease.task_id == grant.task_id
                and not lease.released
                and lease.expires_at > now
                for lease in self._leases.values()
            )
            if active >= authority.maximum_parallelism:
                raise ControlError("TASK_PARALLELISM_EXHAUSTED")
            lease_id = "LEASE-" + request_digest[:16]
            lease = WorkerLease(
                lease_id=lease_id,
                operation_id=operation_id,
                tenant_id=grant.tenant_id,
                task_id=grant.task_id,
                grant_id=grant_id,
                agent_id=actor.subject_id,
                issued_at=now,
                expires_at=min(grant.expires_at, now + ttl),
            )
            self._lease_operations[operation_key] = (request_digest, lease_id)
            self._leases[lease_id] = lease
            self._event("worker_slot_acquired", grant.tenant_id, grant.task_id, actor.subject_id,
                        grant.trace_id, "PARALLELISM_SLOT_RESERVED", lease_id, now)
            return lease

    def release_worker_slot(
        self,
        actor: AuthenticatedIdentity,
        lease_id: str,
        now: datetime = REFERENCE_TIME,
    ) -> WorkerLease:
        _authenticate(actor, now)
        with self._lock:
            lease = self._leases.get(lease_id)
            if lease is None:
                raise ControlError("LEASE_NOT_FOUND")
            authority = self._tasks[(lease.tenant_id, lease.task_id)]
            if actor.tenant_id != lease.tenant_id or actor.task_id != lease.task_id:
                raise ControlError("LEASE_RELEASE_SCOPE_MISMATCH")
            if (
                actor.subject_id not in {lease.agent_id, authority.principal_id}
                and "security-operator" not in actor.groups
            ):
                raise ControlError("LEASE_RELEASE_NOT_AUTHORIZED")
            if lease.released:
                return lease
            released = lease.model_copy(update={"released": True, "version": lease.version + 1})
            self._leases[lease_id] = released
            root = self._grants[self._task_roots[(lease.tenant_id, lease.task_id)]]
            self._event("worker_slot_released", lease.tenant_id, lease.task_id, actor.subject_id,
                        root.trace_id, "PARALLELISM_SLOT_RELEASED", lease_id, now)
            return released

    def revoke_tree(
        self,
        actor: AuthenticatedIdentity,
        grant_id: str,
        reason: str,
        now: datetime = REFERENCE_TIME,
    ) -> tuple[str, ...]:
        _authenticate(actor, now)
        with self._lock:
            target = self._grants.get(grant_id)
            if target is None:
                raise ControlError("REVOCATION_GRANT_NOT_FOUND")
            authority = self._tasks[(target.tenant_id, target.task_id)]
            if actor.tenant_id != target.tenant_id or actor.task_id != target.task_id:
                raise ControlError("REVOCATION_SCOPE_MISMATCH")
            if actor.subject_id != authority.principal_id and "security-operator" not in actor.groups:
                raise ControlError("REVOCATION_NOT_AUTHORIZED")
            descendants: list[str] = []
            frontier = [grant_id]
            while frontier:
                parent_id = frontier.pop()
                descendants.append(parent_id)
                frontier.extend(
                    item.grant_id
                    for item in self._grants.values()
                    if item.parent_grant_id == parent_id
                )
            for item_id in descendants:
                item = self._grants[item_id]
                if not item.revoked:
                    self._grants[item_id] = item.model_copy(update={
                        "revoked": True,
                        "revocation_reason": reason,
                        "version": item.version + 1,
                    })
            self._event("delegation_revoked", target.tenant_id, target.task_id, actor.subject_id,
                        target.trace_id, reason, grant_id, now)
            return tuple(descendants)

    def set_run_state(
        self,
        actor: AuthenticatedIdentity,
        state: RunState,
        now: datetime = REFERENCE_TIME,
    ) -> RunState:
        _authenticate(actor, now)
        task_key = (actor.tenant_id, actor.task_id)
        with self._lock:
            authority = self._tasks.get(task_key)
            if authority is None:
                raise ControlError("TASK_NOT_FOUND")
            if actor.subject_id != authority.principal_id and "security-operator" not in actor.groups:
                raise ControlError("RUN_STATE_NOT_AUTHORIZED")
            current = self._states[task_key]
            allowed = {
                RunState.RUNNING: {RunState.PAUSED, RunState.TERMINATING},
                RunState.PAUSED: {RunState.RUNNING, RunState.TERMINATING},
                RunState.TERMINATING: {RunState.TERMINATED},
                RunState.TERMINATED: set(),
            }
            if state not in allowed[current]:
                raise ControlError("RUN_STATE_TRANSITION_INVALID")
            self._states[task_key] = state
            root = self._grants[self._task_roots[task_key]]
            self._event("run_state_changed", actor.tenant_id, actor.task_id, actor.subject_id,
                        root.trace_id, state.value.upper(), None, now)
            return state

    def metrics(self, tenant_id: str, task_id: str) -> GovernanceMetrics:
        with self._lock:
            task_grants = tuple(
                grant for grant in self._grants.values()
                if grant.tenant_id == tenant_id and grant.task_id == task_id
            )
            root_id = self._task_roots[(tenant_id, task_id)]
            depths = [len(self._chain_unlocked(grant.grant_id)) - 1 for grant in task_grants]
            task_events = [
                event for event in self._events
                if event.tenant_id == tenant_id and event.task_id == task_id
            ]
            return GovernanceMetrics(
                grant_count=len(task_grants),
                active_grant_count=sum(not grant.revoked for grant in task_grants),
                revoked_grant_count=sum(grant.revoked for grant in task_grants),
                maximum_depth_used=max(depths, default=0),
                calls_used=self._calls_used[(tenant_id, task_id)],
                spend_used_cad=self._spend_used[(tenant_id, task_id)],
                simulated_effect_count=sum(
                    receipt.tenant_id == tenant_id and receipt.task_id == task_id
                    for receipt in self._effects.values()
                ),
                event_count=len(task_events),
            )

    def events(self, tenant_id: str, task_id: str) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(
                event for event in self._events
                if event.tenant_id == tenant_id and event.task_id == task_id
            )


def resolve_findings(findings: Iterable[SpecialistFinding]) -> FindingResolution:
    rows = tuple(findings)
    if not rows or any(not finding.evidence_ids for finding in rows):
        return FindingResolution(
            disposition=FindingDisposition.ESCALATE,
            reason_code="FINDING_EVIDENCE_INCOMPLETE",
            evidence_ids=(),
        )
    if len({finding.vendor_id for finding in rows}) != 1:
        return FindingResolution(
            disposition=FindingDisposition.ESCALATE,
            reason_code="FINDING_SCOPE_MISMATCH",
            evidence_ids=(),
        )
    evidence = tuple(sorted({evidence_id for finding in rows for evidence_id in finding.evidence_ids}))
    risks = {finding.risk for finding in rows}
    if len(risks) > 1:
        return FindingResolution(
            disposition=FindingDisposition.ESCALATE,
            reason_code="SPECIALIST_DISAGREEMENT",
            evidence_ids=evidence,
        )
    if risks == {FindingRisk.HIGH}:
        return FindingResolution(
            disposition=FindingDisposition.DENY,
            reason_code="HIGH_RISK_EVIDENCE",
            evidence_ids=evidence,
        )
    return FindingResolution(
        disposition=FindingDisposition.PROCEED,
        reason_code="LOW_RISK_EVIDENCE",
        evidence_ids=evidence,
    )


def sample_profiles() -> tuple[AgentProfile, ...]:
    tenant = "tenant-acme"
    purpose = frozenset({"approved_procurement"})
    return (
        AgentProfile(
            agent_id="agent:manager", tenant_id=tenant,
            capability_tools=frozenset({"vendor.search", "vendor.read", "po.create", "payment.execute"}),
            executable_tools=frozenset({"vendor.search"}),
            resources=frozenset({"vendor-catalog", "procurement", "payments"}),
            allowed_tool_resource_pairs=frozenset({
                ("vendor.search", "vendor-catalog"),
                ("vendor.read", "vendor-catalog"),
                ("po.create", "procurement"),
                ("payment.execute", "payments"),
            }),
            purposes=purpose,
            allowed_context_fields=frozenset({"vendor_id", "vendor_name", "research_question"}),
            clearance=Classification.CONFIDENTIAL,
            maximum_action_spend_cad=20_000, maximum_calls_per_grant=20,
            may_delegate=True, maximum_child_depth=2,
        ),
        AgentProfile(
            agent_id="agent:research", tenant_id=tenant,
            capability_tools=frozenset({"vendor.search", "vendor.read"}),
            executable_tools=frozenset({"vendor.search", "vendor.read"}),
            resources=frozenset({"vendor-catalog"}), purposes=purpose,
            allowed_tool_resource_pairs=frozenset({
                ("vendor.search", "vendor-catalog"),
                ("vendor.read", "vendor-catalog"),
            }),
            allowed_context_fields=frozenset({"vendor_id", "vendor_name", "research_question"}),
            clearance=Classification.INTERNAL,
            maximum_action_spend_cad=0, maximum_calls_per_grant=5,
            may_delegate=False, maximum_child_depth=0,
        ),
        AgentProfile(
            agent_id="agent:procurement", tenant_id=tenant,
            capability_tools=frozenset({"vendor.read", "po.create", "payment.execute"}),
            executable_tools=frozenset({"vendor.read", "po.create"}),
            resources=frozenset({"vendor-catalog", "procurement", "payments"}), purposes=purpose,
            allowed_tool_resource_pairs=frozenset({
                ("vendor.read", "vendor-catalog"),
                ("po.create", "procurement"),
                ("payment.execute", "payments"),
            }),
            allowed_context_fields=frozenset({"vendor_id", "vendor_name", "approved_quantity"}),
            clearance=Classification.CONFIDENTIAL,
            maximum_action_spend_cad=15_000, maximum_calls_per_grant=10,
            may_delegate=True, maximum_child_depth=1,
        ),
        AgentProfile(
            agent_id="agent:payment", tenant_id=tenant,
            capability_tools=frozenset({"payment.execute"}),
            executable_tools=frozenset({"payment.execute"}),
            resources=frozenset({"payments"}), purposes=purpose,
            allowed_tool_resource_pairs=frozenset({("payment.execute", "payments")}),
            allowed_context_fields=frozenset({"vendor_id", "invoice_id", "approved_amount"}),
            clearance=Classification.CONFIDENTIAL,
            maximum_action_spend_cad=15_000, maximum_calls_per_grant=3,
            may_delegate=False, maximum_child_depth=0,
        ),
    )


def sample_identity(subject_id: str = "user:mahsa", **changes: object) -> AuthenticatedIdentity:
    kind = ActorKind.AGENT if subject_id.startswith("agent:") else ActorKind.HUMAN
    groups = frozenset({"procurement-approver"}) if kind is ActorKind.HUMAN else frozenset()
    return AuthenticatedIdentity(
        subject_id=subject_id,
        tenant_id="tenant-acme",
        kind=kind,
        groups=groups,
        task_id="task:buy-laptops",
        authenticated_at=REFERENCE_TIME - timedelta(minutes=2),
        valid_until=REFERENCE_TIME + timedelta(hours=1),
    ).model_copy(update=changes)


def sample_task_authority(**changes: object) -> TaskAuthority:
    return TaskAuthority(
        operation_id="TASKOP-BUY-LAPTOPS-1",
        tenant_id="tenant-acme",
        task_id="task:buy-laptops",
        principal_id="user:mahsa",
        purpose="approved_procurement",
        allowed_tools=frozenset({"vendor.search", "vendor.read", "po.create", "payment.execute"}),
        allowed_resources=frozenset({"vendor-catalog", "procurement", "payments"}),
        allowed_tool_resource_pairs=frozenset({
            ("vendor.search", "vendor-catalog"),
            ("vendor.read", "vendor-catalog"),
            ("po.create", "procurement"),
            ("payment.execute", "payments"),
        }),
        allowed_vendors=frozenset({"V-42"}),
        maximum_spend_cad=20_000,
        maximum_calls=20,
        maximum_parallelism=3,
        maximum_delegation_depth=2,
        issued_at=REFERENCE_TIME - timedelta(minutes=1),
        expires_at=REFERENCE_TIME + timedelta(minutes=30),
        policy_version="policy-10.1",
        trace_id="trace-procurement-0042",
    ).model_copy(update=changes)


def build_fixture() -> dict[str, object]:
    plane = MultiAgentControlPlane(sample_profiles())
    human = sample_identity()
    manager = sample_identity("agent:manager")
    research = sample_identity("agent:research")
    procurement = sample_identity("agent:procurement")
    payment = sample_identity("agent:payment")
    root = plane.open_task(human, sample_task_authority(), manager.subject_id)
    research_grant = plane.delegate(manager, DelegationRequest(
        operation_id="DELOP-RESEARCH-1",
        parent_grant_id=root.grant_id,
        child_agent_id=research.subject_id,
        purpose=root.purpose,
        allowed_tools=frozenset({"vendor.search", "vendor.read"}),
        allowed_resources=frozenset({"vendor-catalog"}),
        allowed_tool_resource_pairs=frozenset({
            ("vendor.search", "vendor-catalog"),
            ("vendor.read", "vendor-catalog"),
        }),
        allowed_vendors=frozenset({"V-42"}),
        maximum_action_spend_cad=0,
        maximum_calls=5,
        expires_at=REFERENCE_TIME + timedelta(minutes=15),
    ))
    procurement_grant = plane.delegate(manager, DelegationRequest(
        operation_id="DELOP-PROCUREMENT-1",
        parent_grant_id=root.grant_id,
        child_agent_id=procurement.subject_id,
        purpose=root.purpose,
        allowed_tools=frozenset({"vendor.read", "po.create", "payment.execute"}),
        allowed_resources=frozenset({"vendor-catalog", "procurement", "payments"}),
        allowed_tool_resource_pairs=frozenset({
            ("vendor.read", "vendor-catalog"),
            ("po.create", "procurement"),
            ("payment.execute", "payments"),
        }),
        allowed_vendors=frozenset({"V-42"}),
        maximum_action_spend_cad=10_000,
        maximum_calls=10,
        expires_at=REFERENCE_TIME + timedelta(minutes=20),
    ))
    payment_grant = plane.delegate(procurement, DelegationRequest(
        operation_id="DELOP-PAYMENT-1",
        parent_grant_id=procurement_grant.grant_id,
        child_agent_id=payment.subject_id,
        purpose=root.purpose,
        allowed_tools=frozenset({"payment.execute"}),
        allowed_resources=frozenset({"payments"}),
        allowed_tool_resource_pairs=frozenset({("payment.execute", "payments")}),
        allowed_vendors=frozenset({"V-42"}),
        maximum_action_spend_cad=10_000,
        maximum_calls=3,
        expires_at=REFERENCE_TIME + timedelta(minutes=10),
    ))
    return {
        "plane": plane,
        "human": human,
        "manager": manager,
        "research": research,
        "procurement": procurement,
        "payment": payment,
        "root": root,
        "research_grant": research_grant,
        "procurement_grant": procurement_grant,
        "payment_grant": payment_grant,
    }


def sample_proposal(**changes: object) -> ActionProposal:
    fixture = build_fixture()
    grant = fixture["procurement_grant"]
    assert isinstance(grant, DelegationGrant)
    return ActionProposal(
        operation_id="ACTOP-PO-V42-1",
        actor_agent_id="agent:procurement",
        requester_grant_id=grant.grant_id,
        tool="po.create",
        resource="procurement",
        vendor_id="V-42",
        amount_cad=4_000,
        quantity=10,
        description="Ten approved engineering laptops",
    ).model_copy(update=changes)


def naive_role_only(profile: AgentProfile, proposal: ActionProposal) -> bool:
    """Deliberately unsafe baseline: trusts a selected role profile only."""

    return (
        proposal.tool in profile.executable_tools
        and proposal.resource in profile.resources
        and proposal.amount_cad <= profile.maximum_action_spend_cad
    )


def evaluate_control_plane() -> EvaluationSummary:
    results: list[tuple[bool, bool, bool]] = []

    def record(
        fixture: dict[str, object],
        actor: AuthenticatedIdentity,
        grant: DelegationGrant,
        proposal: ActionProposal,
        expected: bool,
        baseline_profile: AgentProfile,
    ) -> None:
        plane = fixture["plane"]
        assert isinstance(plane, MultiAgentControlPlane)
        baseline = naive_role_only(baseline_profile, proposal)
        governed = plane.preview_action(actor, grant.grant_id, proposal).allowed
        results.append((baseline, governed, expected))

    profiles = {profile.agent_id: profile for profile in sample_profiles()}

    fixture = build_fixture()
    record(fixture, fixture["procurement"], fixture["procurement_grant"], sample_proposal(), True,
           profiles["agent:procurement"])

    fixture = build_fixture()
    record(fixture, fixture["procurement"].model_copy(update={"tenant_id": "tenant-beta"}),
           fixture["procurement_grant"], sample_proposal(operation_id="ACTOP-WRONG-TENANT"), False,
           profiles["agent:procurement"])

    fixture = build_fixture()
    record(fixture, fixture["research"], fixture["procurement_grant"],
           sample_proposal(operation_id="ACTOP-WRONG-ACTOR", actor_agent_id="agent:research"), False,
           profiles["agent:research"])

    fixture = build_fixture()
    record(fixture, fixture["procurement"], fixture["procurement_grant"],
           sample_proposal(operation_id="ACTOP-WRONG-TOOL", tool="payment.execute", resource="payments"), False,
           profiles["agent:procurement"])

    fixture = build_fixture()
    record(fixture, fixture["procurement"], fixture["procurement_grant"],
           sample_proposal(operation_id="ACTOP-OVER-GRANT", amount_cad=12_000), False,
           profiles["agent:procurement"])

    fixture = build_fixture()
    fixture["plane"].set_run_state(fixture["human"], RunState.PAUSED)
    record(fixture, fixture["procurement"], fixture["procurement_grant"],
           sample_proposal(operation_id="ACTOP-PAUSED"), False, profiles["agent:procurement"])

    fixture = build_fixture()
    fixture["plane"].revoke_tree(fixture["human"], fixture["procurement_grant"].grant_id, "USER_REVOKED")
    record(fixture, fixture["procurement"], fixture["procurement_grant"],
           sample_proposal(operation_id="ACTOP-REVOKED"), False, profiles["agent:procurement"])

    fixture = build_fixture()
    record(fixture, fixture["procurement"], fixture["procurement_grant"],
           sample_proposal(
               operation_id="ACTOP-CONFUSED-DEPUTY",
               requester_grant_id=fixture["research_grant"].grant_id,
           ), False, profiles["agent:procurement"])

    return EvaluationSummary(
        case_count=len(results),
        baseline_correct_count=sum(baseline == expected for baseline, _, expected in results),
        governed_correct_count=sum(governed == expected for _, governed, expected in results),
        baseline_forbidden_allow_count=sum(baseline and not expected for baseline, _, expected in results),
        governed_forbidden_allow_count=sum(governed and not expected for _, governed, expected in results),
    )


def build_openai_sdk_artifacts() -> dict[str, object]:
    """Create real, unexecuted Agents SDK manager and handoff artifacts."""

    research = Agent(
        name="Vendor research specialist",
        instructions="Return evidence-bound vendor findings; never claim action authority.",
    )
    procurement = Agent(
        name="Procurement specialist",
        instructions="Propose procurement actions; application policy executes them.",
    )
    manager = Agent(
        name="Procurement manager",
        instructions="Coordinate bounded specialists and retain final response ownership.",
        tools=[research.as_tool(
            tool_name="research_vendor",
            tool_description="Research one authorized vendor and return cited findings.",
        )],
    )
    transfer = handoff(procurement)
    return {
        "manager": manager,
        "research": research,
        "procurement": procurement,
        "manager_tool": manager.tools[0],
        "handoff": transfer,
    }


class OfflineChatClient:
    """Non-executable client marker for credential-free framework construction."""

    async def get_response(self, *_args: object, **_kwargs: object) -> object:
        raise RuntimeError("This teaching artifact must not call a model")


def build_microsoft_handoff_artifact() -> object:
    """Create a real Agent Framework handoff workflow without running a model."""

    from agent_framework import Agent as MicrosoftAgent
    from agent_framework.orchestrations import HandoffBuilder

    client = OfflineChatClient()
    common = {"client": client, "require_per_service_call_history_persistence": True}
    triage = MicrosoftAgent(
        **common,
        id="procurement-triage",
        name="procurement_triage",
        description="Routes an already-authorized task to one specialist.",
    )
    research = MicrosoftAgent(
        **common,
        id="vendor-research",
        name="vendor_research",
        description="Returns evidence-bound vendor findings.",
    )
    return (
        HandoffBuilder(name="governed_procurement_handoff", participants=[triage, research])
        .with_start_agent(triage)
        .add_handoff(triage, [research])
        .add_handoff(research, [triage])
        .build()
    )
