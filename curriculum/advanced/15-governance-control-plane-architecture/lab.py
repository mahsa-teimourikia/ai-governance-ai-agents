"""Deterministic governance-control-plane lab for Course 15.

The module models a multi-tenant procurement control plane with a trusted
identity boundary, versioned registries and policy bundles, attenuating
delegation, action-bound approvals, atomic one-time grants, a mediated tool
gateway, outcome verification, policy-outage behavior, shadow evaluation, and
tamper-evident evidence. It performs no network, model, cloud, shell, or real
business-system call. Fixed keys are intentionally non-production test data.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from enum import IntEnum, StrEnum
from importlib import metadata
from threading import Lock

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel, ConfigDict, Field, model_validator

REFERENCE_TIME = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
TENANT_ACME = "tenant-acme"
TENANT_GLOBEX = "tenant-globex"
POLICY_VERSION = "procurement-policy/15.3"
POLICY_CANDIDATE_VERSION = "procurement-policy/15.4-rc1"
DEMO_SIGNING_KEY = b"course-15-demo-only-never-use-in-production"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ControlPlaneError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class Lifecycle(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RESTRICTED = "restricted"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class RiskTier(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class DecisionEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    CONSTRAIN = "constrain"


class OperationMode(StrEnum):
    NORMAL = "normal"
    READ_ONLY = "read_only"
    STOPPED = "stopped"


class OutcomeState(StrEnum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


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


def _sign(value: object, key: bytes = DEMO_SIGNING_KEY) -> str:
    return hmac.new(key, stable_digest(value).encode(), hashlib.sha256).hexdigest()


def _verify(value: object, signature: str, key: bytes = DEMO_SIGNING_KEY) -> bool:
    return hmac.compare_digest(_sign(value, key), signature)


class AgentManifest(FrozenModel):
    agent_id: str
    tenant_id: str
    owner: str
    version: str
    lifecycle: Lifecycle
    allowed_tools: frozenset[str]
    maximum_risk: RiskTier
    policy_version: str
    registry_version: int = Field(gt=0)


class ToolManifest(FrozenModel):
    tool_id: str
    tenant_id: str
    version: str
    schema_version: str
    lifecycle: Lifecycle
    operations: frozenset[str]
    resource_prefixes: frozenset[str]
    mutating: bool
    maximum_amount: int | None = Field(default=None, ge=0)
    registry_version: int = Field(gt=0)


ALLOWED_TRANSITIONS = {
    Lifecycle.DRAFT: {Lifecycle.ACTIVE, Lifecycle.RETIRED},
    Lifecycle.ACTIVE: {Lifecycle.RESTRICTED, Lifecycle.SUSPENDED, Lifecycle.RETIRED},
    Lifecycle.RESTRICTED: {Lifecycle.ACTIVE, Lifecycle.SUSPENDED, Lifecycle.RETIRED},
    Lifecycle.SUSPENDED: {Lifecycle.ACTIVE, Lifecycle.RETIRED},
    Lifecycle.RETIRED: set(),
}


class Registry:
    """Tenant-scoped registry with optimistic concurrency and lifecycle rules."""

    def __init__(self) -> None:
        self._agents: dict[tuple[str, str], AgentManifest] = {}
        self._tools: dict[tuple[str, str], ToolManifest] = {}
        self._lock = Lock()

    def register_agent(self, manifest: AgentManifest) -> None:
        with self._lock:
            key = (manifest.tenant_id, manifest.agent_id)
            if key in self._agents:
                raise ControlPlaneError("AGENT_ALREADY_REGISTERED")
            self._agents[key] = manifest

    def register_tool(self, manifest: ToolManifest) -> None:
        with self._lock:
            key = (manifest.tenant_id, manifest.tool_id)
            if key in self._tools:
                raise ControlPlaneError("TOOL_ALREADY_REGISTERED")
            self._tools[key] = manifest

    def get_agent(self, tenant_id: str, agent_id: str) -> AgentManifest:
        try:
            return self._agents[(tenant_id, agent_id)]
        except KeyError as exc:
            raise ControlPlaneError("AGENT_NOT_REGISTERED") from exc

    def get_tool(self, tenant_id: str, tool_id: str) -> ToolManifest:
        try:
            return self._tools[(tenant_id, tool_id)]
        except KeyError as exc:
            raise ControlPlaneError("TOOL_NOT_REGISTERED") from exc

    def transition_agent(
        self, tenant_id: str, agent_id: str, target: Lifecycle, expected_version: int
    ) -> AgentManifest:
        with self._lock:
            current = self.get_agent(tenant_id, agent_id)
            if current.registry_version != expected_version:
                raise ControlPlaneError("REGISTRY_VERSION_CONFLICT")
            if target not in ALLOWED_TRANSITIONS[current.lifecycle]:
                raise ControlPlaneError("INVALID_LIFECYCLE_TRANSITION")
            updated = current.model_copy(
                update={"lifecycle": target, "registry_version": expected_version + 1}
            )
            self._agents[(tenant_id, agent_id)] = updated
            return updated

    def transition_tool(
        self, tenant_id: str, tool_id: str, target: Lifecycle, expected_version: int
    ) -> ToolManifest:
        with self._lock:
            current = self.get_tool(tenant_id, tool_id)
            if current.registry_version != expected_version:
                raise ControlPlaneError("REGISTRY_VERSION_CONFLICT")
            if target not in ALLOWED_TRANSITIONS[current.lifecycle]:
                raise ControlPlaneError("INVALID_LIFECYCLE_TRANSITION")
            updated = current.model_copy(
                update={"lifecycle": target, "registry_version": expected_version + 1}
            )
            self._tools[(tenant_id, tool_id)] = updated
            return updated

    def discover_tools(
        self, context: AuthenticatedContext, agent_id: str
    ) -> tuple[str, ...]:
        agent = self.get_agent(context.tenant_id, agent_id)
        if agent.lifecycle not in {Lifecycle.ACTIVE, Lifecycle.RESTRICTED}:
            return ()
        return tuple(
            sorted(
                tool_id
                for tool_id in agent.allowed_tools
                if (manifest := self._tools.get((context.tenant_id, tool_id)))
                and manifest.lifecycle == Lifecycle.ACTIVE
            )
        )


class AuthenticatedContext(FrozenModel):
    """Context created by the trusted ingress, never by agent/model output."""

    principal_id: str
    tenant_id: str
    workload_id: str = Field(pattern=r"^spiffe://")
    roles: frozenset[str]
    session_id: str
    authenticated_at: datetime
    valid_until: datetime
    assurance: str = "phishing-resistant-mfa"

    @model_validator(mode="after")
    def coherent_window(self) -> AuthenticatedContext:
        if self.valid_until <= self.authenticated_at:
            raise ValueError("identity validity window must be positive")
        return self


class AuthenticatedOperator(FrozenModel):
    """Current operator identity derived at the administrative ingress."""

    operator_id: str
    tenant_id: str
    roles: frozenset[str]
    session_id: str
    authenticated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def coherent_window(self) -> AuthenticatedOperator:
        if self.valid_until <= self.authenticated_at:
            raise ValueError("operator validity window must be positive")
        return self


def _require_operator(
    operator: AuthenticatedOperator,
    *,
    tenant_id: str,
    role: str,
    now: datetime,
) -> None:
    if operator.tenant_id != tenant_id:
        raise ControlPlaneError("OPERATOR_TENANT_MISMATCH")
    if role not in operator.roles:
        raise ControlPlaneError("OPERATOR_ROLE_REQUIRED")
    if not operator.authenticated_at <= now < operator.valid_until:
        raise ControlPlaneError("OPERATOR_SESSION_INVALID")


class RegistryAdminService:
    """Authenticated management-plane facade around bootstrap registry methods."""

    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def transition_agent(
        self,
        operator: AuthenticatedOperator,
        agent_id: str,
        target: Lifecycle,
        *,
        expected_version: int,
        now: datetime,
    ) -> AgentManifest:
        _require_operator(
            operator, tenant_id=operator.tenant_id, role="registry-admin", now=now
        )
        return self.registry.transition_agent(
            operator.tenant_id, agent_id, target, expected_version
        )

    def transition_tool(
        self,
        operator: AuthenticatedOperator,
        tool_id: str,
        target: Lifecycle,
        *,
        expected_version: int,
        now: datetime,
    ) -> ToolManifest:
        _require_operator(
            operator, tenant_id=operator.tenant_id, role="registry-admin", now=now
        )
        return self.registry.transition_tool(
            operator.tenant_id, tool_id, target, expected_version
        )


class DelegationGrant(FrozenModel):
    grant_id: str
    parent_grant_id: str | None = None
    tenant_id: str
    principal_id: str
    workload_id: str
    agent_id: str
    purpose: str
    operations: frozenset[str]
    tool_ids: frozenset[str]
    resource_prefixes: frozenset[str]
    maximum_amount: int = Field(ge=0)
    environment: str
    policy_version: str
    issued_at: datetime
    expires_at: datetime
    depth: int = Field(ge=0, le=4)
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")

    def unsigned(self) -> dict[str, object]:
        return self.model_dump(mode="python", exclude={"signature"})


def issue_root_delegation(
    context: AuthenticatedContext,
    *,
    agent_id: str,
    purpose: str,
    operations: frozenset[str],
    tool_ids: frozenset[str],
    resource_prefixes: frozenset[str],
    maximum_amount: int,
    environment: str = "production",
    expires_at: datetime | None = None,
) -> DelegationGrant:
    unsigned = {
        "grant_id": "grant-"
        + stable_digest([context.session_id, agent_id, purpose, sorted(operations)])[
            :16
        ],
        "parent_grant_id": None,
        "tenant_id": context.tenant_id,
        "principal_id": context.principal_id,
        "workload_id": context.workload_id,
        "agent_id": agent_id,
        "purpose": purpose,
        "operations": operations,
        "tool_ids": tool_ids,
        "resource_prefixes": resource_prefixes,
        "maximum_amount": maximum_amount,
        "environment": environment,
        "policy_version": POLICY_VERSION,
        "issued_at": context.authenticated_at,
        "expires_at": expires_at or context.valid_until,
        "depth": 0,
    }
    return DelegationGrant(**unsigned, signature=_sign(unsigned))


def attenuate_delegation(
    parent: DelegationGrant,
    *,
    child_agent_id: str,
    operations: frozenset[str],
    tool_ids: frozenset[str],
    resource_prefixes: frozenset[str],
    maximum_amount: int,
    expires_at: datetime,
) -> DelegationGrant:
    if not _verify(parent.unsigned(), parent.signature):
        raise ControlPlaneError("DELEGATION_SIGNATURE_INVALID")
    if not operations <= parent.operations or not tool_ids <= parent.tool_ids:
        raise ControlPlaneError("DELEGATION_SCOPE_WIDENING")
    if not resource_prefixes <= parent.resource_prefixes:
        raise ControlPlaneError("DELEGATION_RESOURCE_WIDENING")
    if maximum_amount > parent.maximum_amount or expires_at > parent.expires_at:
        raise ControlPlaneError("DELEGATION_CONSTRAINT_WIDENING")
    unsigned = {
        **parent.unsigned(),
        "grant_id": "grant-"
        + stable_digest([parent.grant_id, child_agent_id, sorted(operations)])[:16],
        "parent_grant_id": parent.grant_id,
        "agent_id": child_agent_id,
        "operations": operations,
        "tool_ids": tool_ids,
        "resource_prefixes": resource_prefixes,
        "maximum_amount": maximum_amount,
        "expires_at": expires_at,
        "depth": parent.depth + 1,
    }
    return DelegationGrant(**unsigned, signature=_sign(unsigned))


class PolicyBundle(FrozenModel):
    version: str
    tenant_id: str
    environment: str
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    issued_at: datetime
    expires_at: datetime
    ruleset: str
    approval_threshold: int = Field(gt=0)
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")

    def signed_material(self) -> dict[str, object]:
        return self.model_dump(mode="python", exclude={"signature"})


def issue_policy_bundle(
    version: str = POLICY_VERSION,
    *,
    tenant_id: str = TENANT_ACME,
    environment: str = "production",
    issued_at: datetime = REFERENCE_TIME,
    expires_at: datetime | None = None,
    ruleset: str = "procurement-v15",
    approval_threshold: int = 10_000,
) -> PolicyBundle:
    base = {
        "version": version,
        "tenant_id": tenant_id,
        "environment": environment,
        "issued_at": issued_at,
        "expires_at": expires_at or issued_at + timedelta(hours=1),
        "ruleset": ruleset,
        "approval_threshold": approval_threshold,
    }
    material = {**base, "digest": stable_digest(base)}
    return PolicyBundle(**material, signature=_sign(material))


class ActionProposal(FrozenModel):
    """Untrusted structured output proposed by the agent."""

    tool_id: str
    tool_version: str
    schema_version: str
    operation: str
    resource_id: str
    amount: int = Field(default=0, ge=0)
    currency: str = "USD"
    purpose: str
    requested_fields: tuple[str, ...] = ()
    idempotency_key: str


class ActionRequest(FrozenModel):
    proposal: ActionProposal
    tenant_id: str
    principal_id: str
    workload_id: str
    agent_id: str
    session_id: str
    delegation_id: str
    environment: str

    @property
    def action_digest(self) -> str:
        return stable_digest(self)


class DecisionRecord(FrozenModel):
    decision_id: str
    effect: DecisionEffect
    reason_codes: tuple[str, ...]
    obligations: tuple[str, ...]
    risk_tier: RiskTier
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: str
    policy_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    agent_registry_version: int
    tool_registry_version: int
    evaluated_at: datetime
    used_last_known_good: bool = False


class ApprovalReceipt(FrozenModel):
    approval_id: str
    tenant_id: str
    decision_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: str
    policy_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    agent_registry_version: int = Field(gt=0)
    tool_registry_version: int = Field(gt=0)
    approver_id: str
    approver_role: str
    issued_at: datetime
    expires_at: datetime
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")

    def unsigned(self) -> dict[str, object]:
        return self.model_dump(mode="python", exclude={"signature"})


def issue_approval(
    decision: DecisionRecord,
    *,
    tenant_id: str,
    approver_id: str,
    approver_role: str,
    now: datetime = REFERENCE_TIME,
) -> ApprovalReceipt:
    if decision.effect != DecisionEffect.ESCALATE:
        raise ControlPlaneError("APPROVAL_NOT_REQUIRED")
    required_role = "procurement-director"
    if approver_role != required_role:
        raise ControlPlaneError("APPROVER_ROLE_INVALID")
    material = {
        "approval_id": "approval-" + decision.action_digest[:16],
        "tenant_id": tenant_id,
        "decision_id": decision.decision_id,
        "action_digest": decision.action_digest,
        "policy_version": decision.policy_version,
        "policy_digest": decision.policy_digest,
        "agent_registry_version": decision.agent_registry_version,
        "tool_registry_version": decision.tool_registry_version,
        "approver_id": approver_id,
        "approver_role": approver_role,
        "issued_at": now,
        "expires_at": now + timedelta(minutes=5),
    }
    return ApprovalReceipt(**material, signature=_sign(material))


class ApprovalLedger:
    """Atomically consumes approval IDs, preventing replay under concurrency."""

    def __init__(self) -> None:
        self._consumed: set[str] = set()
        self._lock = Lock()

    def consume(
        self,
        receipt: ApprovalReceipt,
        request: ActionRequest,
        decision: DecisionRecord,
        now: datetime,
    ) -> None:
        if not _verify(receipt.unsigned(), receipt.signature):
            raise ControlPlaneError("APPROVAL_SIGNATURE_INVALID")
        if receipt.tenant_id != request.tenant_id:
            raise ControlPlaneError("APPROVAL_TENANT_MISMATCH")
        if receipt.action_digest != request.action_digest:
            raise ControlPlaneError("APPROVAL_ACTION_MISMATCH")
        if receipt.decision_id != decision.decision_id:
            raise ControlPlaneError("APPROVAL_DECISION_MISMATCH")
        if (
            receipt.policy_version != decision.policy_version
            or receipt.policy_digest != decision.policy_digest
        ):
            raise ControlPlaneError("APPROVAL_POLICY_MISMATCH")
        if (
            receipt.agent_registry_version != decision.agent_registry_version
            or receipt.tool_registry_version != decision.tool_registry_version
        ):
            raise ControlPlaneError("APPROVAL_REGISTRY_MISMATCH")
        if not receipt.issued_at <= now < receipt.expires_at:
            raise ControlPlaneError("APPROVAL_EXPIRED")
        with self._lock:
            if receipt.approval_id in self._consumed:
                raise ControlPlaneError("APPROVAL_ALREADY_CONSUMED")
            self._consumed.add(receipt.approval_id)


class EvidenceEntry(FrozenModel):
    sequence: int = Field(gt=0)
    event_type: str
    subject_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tenant_id: str
    policy_version: str
    outcome: str
    recorded_at: datetime
    previous_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    def material(self) -> dict[str, object]:
        return self.model_dump(mode="python", exclude={"entry_hash"})


class EvidenceLog:
    """Append-only demonstration chain; production requires durable protected storage."""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self._entries: list[EvidenceEntry] = []

    @property
    def entries(self) -> tuple[EvidenceEntry, ...]:
        return tuple(self._entries)

    def append(
        self,
        event_type: str,
        subject: object,
        tenant_id: str,
        policy_version: str,
        outcome: str,
        now: datetime,
    ) -> EvidenceEntry:
        material = {
            "sequence": len(self._entries) + 1,
            "event_type": event_type,
            "subject_digest": stable_digest(subject),
            "tenant_id": tenant_id,
            "policy_version": policy_version,
            "outcome": outcome,
            "recorded_at": now,
            "previous_hash": self._entries[-1].entry_hash
            if self._entries
            else self.GENESIS,
        }
        entry = EvidenceEntry(**material, entry_hash=stable_digest(material))
        self._entries.append(entry)
        return entry

    def verify(self) -> bool:
        previous = self.GENESIS
        for index, entry in enumerate(self._entries, start=1):
            if entry.sequence != index or entry.previous_hash != previous:
                return False
            if stable_digest(entry.material()) != entry.entry_hash:
                return False
            previous = entry.entry_hash
        return True


class ExecutionReceipt(FrozenModel):
    operation_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_state: OutcomeState
    outcome_code: str
    external_reference: str | None = None
    effect_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class ProcurementAdapter:
    """Idempotent fake adapter with explicit unknown-outcome reconciliation."""

    def __init__(self) -> None:
        self._receipts: dict[str, ExecutionReceipt] = {}
        self.calls = 0

    def execute(
        self, request: ActionRequest, *, simulate_timeout: bool = False
    ) -> ExecutionReceipt:
        key = request.proposal.idempotency_key
        if key in self._receipts:
            return self._receipts[key]
        self.calls += 1
        if simulate_timeout:
            receipt = ExecutionReceipt(
                operation_id=key,
                action_digest=request.action_digest,
                outcome_state=OutcomeState.UNKNOWN,
                outcome_code="UPSTREAM_TIMEOUT_OUTCOME_UNKNOWN",
            )
            self._receipts[key] = receipt
            return receipt
        reference = "po-" + request.action_digest[:12]
        receipt = ExecutionReceipt(
            operation_id=key,
            action_digest=request.action_digest,
            outcome_state=OutcomeState.VERIFIED,
            outcome_code="PURCHASE_ORDER_COMMITTED",
            external_reference=reference,
            effect_digest=stable_digest(
                {"reference": reference, "amount": request.proposal.amount}
            ),
        )
        self._receipts[key] = receipt
        return receipt

    def reconcile(self, operation_id: str, request: ActionRequest) -> ExecutionReceipt:
        prior = self._receipts.get(operation_id)
        if prior is None or prior.action_digest != request.action_digest:
            raise ControlPlaneError("RECONCILIATION_BINDING_INVALID")
        if prior.outcome_state == OutcomeState.UNKNOWN:
            verified = prior.model_copy(
                update={
                    "outcome_state": OutcomeState.VERIFIED,
                    "outcome_code": "PURCHASE_ORDER_COMMITTED_AFTER_RECONCILIATION",
                    "external_reference": "po-" + request.action_digest[:12],
                    "effect_digest": stable_digest(
                        {
                            "reference": "po-" + request.action_digest[:12],
                            "reconciled": True,
                        }
                    ),
                }
            )
            self._receipts[operation_id] = verified
            return verified
        return prior


class ControlPlane:
    def __init__(
        self,
        registry: Registry,
        policy: PolicyBundle,
        *,
        mode: OperationMode = OperationMode.NORMAL,
        policy_available: bool = True,
        max_lkg_age: timedelta = timedelta(minutes=15),
    ) -> None:
        self.registry = registry
        self.policy = policy
        self.mode = mode
        self.policy_available = policy_available
        self.max_lkg_age = max_lkg_age

    def build_request(
        self,
        context: AuthenticatedContext,
        agent_id: str,
        grant: DelegationGrant,
        proposal: ActionProposal,
        *,
        environment: str,
        now: datetime,
    ) -> ActionRequest:
        if not context.authenticated_at <= now < context.valid_until:
            raise ControlPlaneError("IDENTITY_EXPIRED")
        if not _verify(grant.unsigned(), grant.signature):
            raise ControlPlaneError("DELEGATION_SIGNATURE_INVALID")
        bindings = (
            grant.tenant_id == context.tenant_id,
            grant.principal_id == context.principal_id,
            grant.workload_id == context.workload_id,
            grant.agent_id == agent_id,
            grant.environment == environment,
        )
        if not all(bindings):
            raise ControlPlaneError("DELEGATION_BINDING_INVALID")
        if not grant.issued_at <= now < grant.expires_at:
            raise ControlPlaneError("DELEGATION_EXPIRED")
        if (self.policy.tenant_id, self.policy.environment) != (
            context.tenant_id,
            environment,
        ):
            raise ControlPlaneError("POLICY_SCOPE_MISMATCH")
        if grant.policy_version != self.policy.version:
            raise ControlPlaneError("DELEGATION_POLICY_STALE")
        return ActionRequest(
            proposal=proposal,
            tenant_id=context.tenant_id,
            principal_id=context.principal_id,
            workload_id=context.workload_id,
            agent_id=agent_id,
            session_id=context.session_id,
            delegation_id=grant.grant_id,
            environment=environment,
        )

    def decide(
        self,
        request: ActionRequest,
        grant: DelegationGrant,
        *,
        now: datetime,
    ) -> DecisionRecord:
        agent = self.registry.get_agent(request.tenant_id, request.agent_id)
        tool = self.registry.get_tool(request.tenant_id, request.proposal.tool_id)
        reasons: list[str] = []
        obligations: list[str] = []
        risk = RiskTier.HIGH if tool.mutating else RiskTier.LOW

        if self.mode == OperationMode.STOPPED:
            reasons.append("CONTROL_PLANE_STOPPED")
        if agent.lifecycle not in {Lifecycle.ACTIVE, Lifecycle.RESTRICTED}:
            reasons.append("AGENT_NOT_ACTIVE")
        if (
            tool.lifecycle != Lifecycle.ACTIVE
            or tool.tool_id not in agent.allowed_tools
        ):
            reasons.append("TOOL_NOT_ACTIVE_OR_ASSIGNED")
        if request.proposal.tool_version != tool.version:
            reasons.append("TOOL_VERSION_MISMATCH")
        if request.proposal.schema_version != tool.schema_version:
            reasons.append("TOOL_SCHEMA_MISMATCH")
        if request.proposal.operation not in tool.operations:
            reasons.append("OPERATION_NOT_DECLARED_BY_TOOL")
        if request.proposal.operation not in grant.operations:
            reasons.append("OPERATION_OUTSIDE_DELEGATION")
        if tool.tool_id not in grant.tool_ids:
            reasons.append("TOOL_OUTSIDE_DELEGATION")
        if not any(
            request.proposal.resource_id.startswith(p) for p in grant.resource_prefixes
        ):
            reasons.append("RESOURCE_OUTSIDE_DELEGATION")
        if not any(
            request.proposal.resource_id.startswith(p) for p in tool.resource_prefixes
        ):
            reasons.append("RESOURCE_OUTSIDE_TOOL_SCOPE")
        if request.proposal.purpose != grant.purpose:
            reasons.append("PURPOSE_MISMATCH")
        if request.proposal.amount > grant.maximum_amount:
            reasons.append("AMOUNT_OUTSIDE_DELEGATION")
        if (
            tool.maximum_amount is not None
            and request.proposal.amount > tool.maximum_amount
        ):
            reasons.append("AMOUNT_OUTSIDE_TOOL_LIMIT")
        if self.mode == OperationMode.READ_ONLY and tool.mutating:
            reasons.append("READ_ONLY_MODE")
        if request.proposal.operation == "execute_payment":
            reasons.append("DIRECT_PAYMENT_PROHIBITED")
            risk = RiskTier.CRITICAL

        used_lkg = False
        if not _verify(self.policy.signed_material(), self.policy.signature):
            reasons.append("POLICY_SIGNATURE_INVALID")
        elif now >= self.policy.expires_at:
            reasons.append("POLICY_BUNDLE_EXPIRED")
        elif not self.policy_available:
            age = now - self.policy.issued_at
            if not tool.mutating and risk == RiskTier.LOW and age <= self.max_lkg_age:
                used_lkg = True
                obligations.append("LAST_KNOWN_GOOD_READ_ONLY")
            else:
                reasons.append("POLICY_SERVICE_UNAVAILABLE")

        if reasons:
            effect = DecisionEffect.DENY
        elif tool.mutating and request.proposal.amount > self.policy.approval_threshold:
            effect = DecisionEffect.ESCALATE
            reasons.append("DIRECTOR_APPROVAL_REQUIRED")
            obligations.extend(("ACTION_BOUND_APPROVAL", "SINGLE_USE_EXECUTION"))
            risk = RiskTier.HIGH
        elif not tool.mutating and "bank_account" in request.proposal.requested_fields:
            effect = DecisionEffect.CONSTRAIN
            reasons.append("SENSITIVE_FIELD_REQUESTED")
            obligations.extend(("REMOVE_FIELD:bank_account", "MAX_ROWS:25"))
            risk = RiskTier.MEDIUM
        else:
            effect = DecisionEffect.ALLOW
            reasons.append("POLICY_REQUIREMENTS_SATISFIED")
            obligations.append("SINGLE_USE_EXECUTION")

        return DecisionRecord(
            decision_id="decision-" + request.action_digest[:16],
            effect=effect,
            reason_codes=tuple(reasons),
            obligations=tuple(obligations),
            risk_tier=risk,
            action_digest=request.action_digest,
            policy_version=self.policy.version,
            policy_digest=self.policy.digest,
            agent_registry_version=agent.registry_version,
            tool_registry_version=tool.registry_version,
            evaluated_at=now,
            used_last_known_good=used_lkg,
        )


def enforce_constraints(
    request: ActionRequest, decision: DecisionRecord
) -> ActionRequest:
    if decision.effect != DecisionEffect.CONSTRAIN:
        return request
    fields = list(request.proposal.requested_fields)
    for obligation in decision.obligations:
        if obligation.startswith("REMOVE_FIELD:"):
            field = obligation.partition(":")[2]
            fields = [value for value in fields if value != field]
    proposal = request.proposal.model_copy(update={"requested_fields": tuple(fields)})
    return request.model_copy(update={"proposal": proposal})


class ToolGateway:
    """PEP that owns final authorization, approval consumption, and execution."""

    def __init__(
        self,
        control_plane: ControlPlane,
        adapter: ProcurementAdapter,
        approvals: ApprovalLedger,
        evidence: EvidenceLog,
    ) -> None:
        self.control_plane = control_plane
        self.adapter = adapter
        self.approvals = approvals
        self.evidence = evidence
        self._executed_actions: set[str] = set()
        self._lock = Lock()

    def execute(
        self,
        request: ActionRequest,
        grant: DelegationGrant,
        *,
        approval: ApprovalReceipt | None = None,
        now: datetime,
        simulate_timeout: bool = False,
    ) -> tuple[DecisionRecord, ExecutionReceipt]:
        decision = self.control_plane.decide(request, grant, now=now)
        self.evidence.append(
            "decision",
            request,
            request.tenant_id,
            decision.policy_version,
            decision.effect,
            now,
        )
        if decision.effect == DecisionEffect.DENY:
            raise ControlPlaneError(decision.reason_codes[0])
        if decision.effect == DecisionEffect.CONSTRAIN:
            constrained = enforce_constraints(request, decision)
            decision = self.control_plane.decide(constrained, grant, now=now)
            request = constrained
            self.evidence.append(
                "constrained-decision",
                request,
                request.tenant_id,
                decision.policy_version,
                decision.effect,
                now,
            )
            if decision.effect not in {DecisionEffect.ALLOW, DecisionEffect.CONSTRAIN}:
                raise ControlPlaneError("CONSTRAINED_ACTION_NOT_AUTHORIZED")
        if decision.effect == DecisionEffect.ESCALATE:
            if approval is None:
                raise ControlPlaneError("APPROVAL_REQUIRED")
            self.approvals.consume(approval, request, decision, now)

        with self._lock:
            if request.action_digest in self._executed_actions:
                raise ControlPlaneError("EXECUTION_GRANT_ALREADY_CONSUMED")
            self._executed_actions.add(request.action_digest)
        receipt = self.adapter.execute(request, simulate_timeout=simulate_timeout)
        self.evidence.append(
            "outcome",
            receipt,
            request.tenant_id,
            decision.policy_version,
            receipt.outcome_state,
            now,
        )
        return decision, receipt

    def reconcile_unknown(
        self,
        request: ActionRequest,
        *,
        now: datetime,
    ) -> ExecutionReceipt:
        """Resolve an unknown effect without issuing a second mutation."""

        if request.action_digest not in self._executed_actions:
            raise ControlPlaneError("UNKNOWN_OPERATION_NOT_ISSUED_BY_GATEWAY")
        receipt = self.adapter.reconcile(request.proposal.idempotency_key, request)
        self.evidence.append(
            "reconciliation",
            receipt,
            request.tenant_id,
            self.control_plane.policy.version,
            receipt.outcome_state,
            now,
        )
        return receipt


class Scenario(FrozenModel):
    scenario_id: str = Field(pattern=r"^CP-[0-9]{2}$")
    name: str
    proposal: ActionProposal
    expected_effect: DecisionEffect
    expected_outcome: OutcomeState
    mode: OperationMode = OperationMode.NORMAL
    policy_available: bool = True


class ScenarioResult(FrozenModel):
    scenario_id: str
    expected_effect: DecisionEffect
    actual_effect: DecisionEffect
    expected_outcome: OutcomeState
    actual_outcome: OutcomeState
    forbidden_outcome: bool
    valid_work_blocked: bool
    reason_codes: tuple[str, ...]


class EvaluationReport(FrozenModel):
    system: str
    results: tuple[ScenarioResult, ...]
    correct_decisions: int
    forbidden_outcomes: int
    valid_work_blocked: int
    verified_effects: int
    scenario_population: int


def build_registry() -> Registry:
    registry = Registry()
    registry.register_agent(
        AgentManifest(
            agent_id="procurement-agent",
            tenant_id=TENANT_ACME,
            owner="procurement-platform",
            version="3.2.0",
            lifecycle=Lifecycle.ACTIVE,
            allowed_tools=frozenset({"vendor.read", "purchase-order.create"}),
            maximum_risk=RiskTier.HIGH,
            policy_version=POLICY_VERSION,
            registry_version=1,
        )
    )
    registry.register_tool(
        ToolManifest(
            tool_id="vendor.read",
            tenant_id=TENANT_ACME,
            version="2.1.0",
            schema_version="vendor-read/2",
            lifecycle=Lifecycle.ACTIVE,
            operations=frozenset({"read_vendor"}),
            resource_prefixes=frozenset({"vendor:acme:"}),
            mutating=False,
            registry_version=1,
        )
    )
    registry.register_tool(
        ToolManifest(
            tool_id="purchase-order.create",
            tenant_id=TENANT_ACME,
            version="4.0.0",
            schema_version="purchase-order/4",
            lifecycle=Lifecycle.ACTIVE,
            operations=frozenset({"create_purchase_order"}),
            resource_prefixes=frozenset({"cost-center:acme:"}),
            mutating=True,
            maximum_amount=50_000,
            registry_version=1,
        )
    )
    return registry


def build_context() -> AuthenticatedContext:
    return AuthenticatedContext(
        principal_id="user:maya",
        tenant_id=TENANT_ACME,
        workload_id="spiffe://acme.example/agents/procurement",
        roles=frozenset({"procurement-requester"}),
        session_id="session-course15",
        authenticated_at=REFERENCE_TIME - timedelta(minutes=1),
        valid_until=REFERENCE_TIME + timedelta(hours=1),
    )


def build_operator(*roles: str, tenant_id: str = TENANT_ACME) -> AuthenticatedOperator:
    return AuthenticatedOperator(
        operator_id="user:control-plane-owner",
        tenant_id=tenant_id,
        roles=frozenset(roles or ("registry-admin", "policy-admin")),
        session_id="operator-session-course15",
        authenticated_at=REFERENCE_TIME - timedelta(minutes=2),
        valid_until=REFERENCE_TIME + timedelta(hours=1),
    )


def build_grant(context: AuthenticatedContext | None = None) -> DelegationGrant:
    context = context or build_context()
    return issue_root_delegation(
        context,
        agent_id="procurement-agent",
        purpose="quarterly-office-supplies",
        operations=frozenset({"read_vendor", "create_purchase_order"}),
        tool_ids=frozenset({"vendor.read", "purchase-order.create"}),
        resource_prefixes=frozenset({"vendor:acme:", "cost-center:acme:"}),
        maximum_amount=50_000,
    )


def proposal(
    *,
    tool_id: str = "purchase-order.create",
    operation: str = "create_purchase_order",
    resource_id: str = "cost-center:acme:facilities",
    amount: int = 5_000,
    requested_fields: tuple[str, ...] = (),
    purpose: str = "quarterly-office-supplies",
    suffix: str = "01",
) -> ActionProposal:
    read = tool_id == "vendor.read"
    return ActionProposal(
        tool_id=tool_id,
        tool_version="2.1.0" if read else "4.0.0",
        schema_version="vendor-read/2" if read else "purchase-order/4",
        operation=operation,
        resource_id=resource_id,
        amount=amount,
        purpose=purpose,
        requested_fields=requested_fields,
        idempotency_key=f"idem-course15-{suffix}",
    )


def build_reference_environment() -> dict[str, object]:
    registry = build_registry()
    context = build_context()
    grant = build_grant(context)
    control_plane = ControlPlane(registry, issue_policy_bundle())
    return {
        "registry": registry,
        "context": context,
        "grant": grant,
        "control_plane": control_plane,
        "adapter": ProcurementAdapter(),
        "approvals": ApprovalLedger(),
        "evidence": EvidenceLog(),
    }


def build_scenarios() -> tuple[Scenario, ...]:
    return (
        Scenario(
            scenario_id="CP-01",
            name="ordinary purchase order",
            proposal=proposal(suffix="01"),
            expected_effect=DecisionEffect.ALLOW,
            expected_outcome=OutcomeState.VERIFIED,
        ),
        Scenario(
            scenario_id="CP-02",
            name="director-approved purchase order",
            proposal=proposal(amount=25_000, suffix="02"),
            expected_effect=DecisionEffect.ESCALATE,
            expected_outcome=OutcomeState.VERIFIED,
        ),
        Scenario(
            scenario_id="CP-03",
            name="direct payment prohibited",
            proposal=proposal(operation="execute_payment", amount=2_000, suffix="03"),
            expected_effect=DecisionEffect.DENY,
            expected_outcome=OutcomeState.BLOCKED,
        ),
        Scenario(
            scenario_id="CP-04",
            name="cross-tenant resource",
            proposal=proposal(resource_id="cost-center:globex:finance", suffix="04"),
            expected_effect=DecisionEffect.DENY,
            expected_outcome=OutcomeState.BLOCKED,
        ),
        Scenario(
            scenario_id="CP-05",
            name="sensitive vendor field constrained",
            proposal=proposal(
                tool_id="vendor.read",
                operation="read_vendor",
                resource_id="vendor:acme:42",
                requested_fields=("name", "bank_account"),
                suffix="05",
            ),
            expected_effect=DecisionEffect.CONSTRAIN,
            expected_outcome=OutcomeState.VERIFIED,
        ),
        Scenario(
            scenario_id="CP-06",
            name="delegation amount exceeded",
            proposal=proposal(amount=60_000, suffix="06"),
            expected_effect=DecisionEffect.DENY,
            expected_outcome=OutcomeState.BLOCKED,
        ),
        Scenario(
            scenario_id="CP-07",
            name="tool schema drift",
            proposal=proposal(suffix="07").model_copy(
                update={"schema_version": "purchase-order/5"}
            ),
            expected_effect=DecisionEffect.DENY,
            expected_outcome=OutcomeState.BLOCKED,
        ),
        Scenario(
            scenario_id="CP-08",
            name="purpose mismatch",
            proposal=proposal(purpose="unapproved-acquisition", suffix="08"),
            expected_effect=DecisionEffect.DENY,
            expected_outcome=OutcomeState.BLOCKED,
        ),
        Scenario(
            scenario_id="CP-09",
            name="emergency stop",
            proposal=proposal(suffix="09"),
            expected_effect=DecisionEffect.DENY,
            expected_outcome=OutcomeState.BLOCKED,
            mode=OperationMode.STOPPED,
        ),
        Scenario(
            scenario_id="CP-10",
            name="read-only degraded mode blocks mutation",
            proposal=proposal(suffix="10"),
            expected_effect=DecisionEffect.DENY,
            expected_outcome=OutcomeState.BLOCKED,
            mode=OperationMode.READ_ONLY,
        ),
        Scenario(
            scenario_id="CP-11",
            name="policy outage blocks high-risk mutation",
            proposal=proposal(suffix="11"),
            expected_effect=DecisionEffect.DENY,
            expected_outcome=OutcomeState.BLOCKED,
            policy_available=False,
        ),
        Scenario(
            scenario_id="CP-12",
            name="fresh last-known-good permits bounded read",
            proposal=proposal(
                tool_id="vendor.read",
                operation="read_vendor",
                resource_id="vendor:acme:42",
                suffix="12",
            ),
            expected_effect=DecisionEffect.ALLOW,
            expected_outcome=OutcomeState.VERIFIED,
            policy_available=False,
        ),
    )


def evaluate_control_plane() -> EvaluationReport:
    results: list[ScenarioResult] = []
    for item in build_scenarios():
        env = build_reference_environment()
        cp: ControlPlane = env["control_plane"]  # type: ignore[assignment]
        cp.mode = item.mode
        cp.policy_available = item.policy_available
        grant: DelegationGrant = env["grant"]  # type: ignore[assignment]
        request = cp.build_request(
            env["context"],
            "procurement-agent",
            grant,
            item.proposal,
            environment="production",
            now=REFERENCE_TIME,
        )  # type: ignore[arg-type]
        decision = cp.decide(request, grant, now=REFERENCE_TIME)
        outcome = (
            OutcomeState.BLOCKED
            if decision.effect == DecisionEffect.DENY
            else OutcomeState.VERIFIED
        )
        results.append(
            ScenarioResult(
                scenario_id=item.scenario_id,
                expected_effect=item.expected_effect,
                actual_effect=decision.effect,
                expected_outcome=item.expected_outcome,
                actual_outcome=outcome,
                forbidden_outcome=outcome == OutcomeState.VERIFIED
                and item.expected_outcome == OutcomeState.BLOCKED,
                valid_work_blocked=outcome == OutcomeState.BLOCKED
                and item.expected_outcome == OutcomeState.VERIFIED,
                reason_codes=decision.reason_codes,
            )
        )
    return EvaluationReport(
        system="governed-control-plane",
        results=tuple(results),
        correct_decisions=sum(r.actual_effect == r.expected_effect for r in results),
        forbidden_outcomes=sum(r.forbidden_outcome for r in results),
        valid_work_blocked=sum(r.valid_work_blocked for r in results),
        verified_effects=sum(
            r.actual_outcome == OutcomeState.VERIFIED for r in results
        ),
        scenario_population=len(results),
    )


def evaluate_prompt_only_baseline() -> EvaluationReport:
    """Deliberately unsafe comparison: executes every syntactically valid proposal."""
    results = tuple(
        ScenarioResult(
            scenario_id=item.scenario_id,
            expected_effect=item.expected_effect,
            actual_effect=DecisionEffect.ALLOW,
            expected_outcome=item.expected_outcome,
            actual_outcome=OutcomeState.VERIFIED,
            forbidden_outcome=item.expected_outcome == OutcomeState.BLOCKED,
            valid_work_blocked=False,
            reason_codes=("PROMPT_ONLY_GOVERNANCE",),
        )
        for item in build_scenarios()
    )
    return EvaluationReport(
        system="prompt-only-baseline",
        results=results,
        correct_decisions=sum(r.actual_effect == r.expected_effect for r in results),
        forbidden_outcomes=sum(r.forbidden_outcome for r in results),
        valid_work_blocked=0,
        verified_effects=len(results),
        scenario_population=len(results),
    )


def shadow_compare(
    request: ActionRequest,
    grant: DelegationGrant,
    current: ControlPlane,
    candidate: ControlPlane,
    *,
    now: datetime,
) -> dict[str, object]:
    current_decision = current.decide(request, grant, now=now)
    candidate_decision = candidate.decide(request, grant, now=now)
    return {
        "enforced_policy": current.policy.version,
        "enforced_effect": current_decision.effect,
        "shadow_policy": candidate.policy.version,
        "shadow_effect": candidate_decision.effect,
        "changed": current_decision.effect != candidate_decision.effect,
        "action_digest": request.action_digest,
    }


class ShadowEvaluationReport(FrozenModel):
    active_policy_digest: str
    candidate_policy_digest: str
    corpus_digest: str
    tenant_id: str
    environment: str
    evaluated_at: datetime
    scenario_population: int = Field(gt=0)
    decision_change_count: int = Field(ge=0)
    candidate_incorrect_count: int = Field(ge=0)
    broadened_allow_count: int = Field(ge=0)
    forbidden_permit_count: int = Field(ge=0)


def evaluate_shadow_rollout(
    active: PolicyBundle,
    candidate: PolicyBundle,
    *,
    now: datetime = REFERENCE_TIME,
) -> ShadowEvaluationReport:
    if (active.tenant_id, active.environment) != (
        candidate.tenant_id,
        candidate.environment,
    ):
        raise ControlPlaneError("SHADOW_POLICY_SCOPE_MISMATCH")
    cases = build_scenarios()
    active_effects: list[DecisionEffect] = []
    candidate_effects: list[DecisionEffect] = []
    for item in cases:
        env = build_reference_environment()
        registry: Registry = env["registry"]  # type: ignore[assignment]
        context: AuthenticatedContext = env["context"]  # type: ignore[assignment]
        grant: DelegationGrant = env["grant"]  # type: ignore[assignment]
        active_cp = ControlPlane(
            registry,
            active,
            mode=item.mode,
            policy_available=item.policy_available,
        )
        candidate_cp = ControlPlane(
            registry,
            candidate,
            mode=item.mode,
            policy_available=item.policy_available,
        )
        active_request = active_cp.build_request(
            context,
            "procurement-agent",
            grant,
            item.proposal,
            environment="production",
            now=now,
        )
        candidate_grant_unsigned = grant.model_copy(
            update={"policy_version": candidate.version}, deep=True
        ).unsigned()
        candidate_grant = DelegationGrant(
            **candidate_grant_unsigned, signature=_sign(candidate_grant_unsigned)
        )
        # Rebuild after signing because build_request verifies the grant.
        candidate_request = candidate_cp.build_request(
            context,
            "procurement-agent",
            candidate_grant,
            item.proposal,
            environment="production",
            now=now,
        )
        active_effects.append(active_cp.decide(active_request, grant, now=now).effect)
        candidate_effects.append(
            candidate_cp.decide(candidate_request, candidate_grant, now=now).effect
        )
    incorrect = sum(
        actual is not item.expected_effect
        for item, actual in zip(cases, candidate_effects)
    )
    broadened = sum(
        before is DecisionEffect.DENY and after is DecisionEffect.ALLOW
        for before, after in zip(active_effects, candidate_effects)
    )
    forbidden = sum(
        item.expected_outcome is OutcomeState.BLOCKED
        and actual is not DecisionEffect.DENY
        for item, actual in zip(cases, candidate_effects)
    )
    return ShadowEvaluationReport(
        active_policy_digest=active.digest,
        candidate_policy_digest=candidate.digest,
        corpus_digest=stable_digest(cases),
        tenant_id=active.tenant_id,
        environment=active.environment,
        evaluated_at=now,
        scenario_population=len(cases),
        decision_change_count=sum(
            a is not b for a, b in zip(active_effects, candidate_effects)
        ),
        candidate_incorrect_count=incorrect,
        broadened_allow_count=broadened,
        forbidden_permit_count=forbidden,
    )


class PolicyActivationReceipt(FrozenModel):
    activation_id: str
    tenant_id: str
    environment: str
    candidate_policy_digest: str
    shadow_report_digest: str
    authorized_by: str
    authorized_at: datetime


def authorize_policy_activation(
    candidate: PolicyBundle,
    report: ShadowEvaluationReport,
    operator: AuthenticatedOperator,
    *,
    now: datetime,
) -> PolicyActivationReceipt:
    _require_operator(
        operator, tenant_id=candidate.tenant_id, role="policy-admin", now=now
    )
    if report.candidate_policy_digest != candidate.digest:
        raise ControlPlaneError("SHADOW_REPORT_CANDIDATE_MISMATCH")
    if (report.tenant_id, report.environment) != (
        candidate.tenant_id,
        candidate.environment,
    ):
        raise ControlPlaneError("SHADOW_REPORT_SCOPE_MISMATCH")
    if report.evaluated_at > now or now - report.evaluated_at > timedelta(hours=24):
        raise ControlPlaneError("SHADOW_REPORT_STALE")
    if report.scenario_population < 12:
        raise ControlPlaneError("SHADOW_POPULATION_INSUFFICIENT")
    if any(
        (
            report.candidate_incorrect_count,
            report.broadened_allow_count,
            report.forbidden_permit_count,
        )
    ):
        raise ControlPlaneError("SHADOW_RELEASE_GATE_FAILED")
    body = {
        "tenant": candidate.tenant_id,
        "environment": candidate.environment,
        "candidate": candidate.digest,
        "report": stable_digest(report),
        "operator": operator.operator_id,
        "at": now,
    }
    return PolicyActivationReceipt(
        activation_id="activation-" + stable_digest(body)[:16],
        tenant_id=candidate.tenant_id,
        environment=candidate.environment,
        candidate_policy_digest=candidate.digest,
        shadow_report_digest=stable_digest(report),
        authorized_by=operator.operator_id,
        authorized_at=now,
    )


class PolicyReplica:
    """A local PDP replica that accepts only evidence-bound policy activation."""

    def __init__(self, replica_id: str, tenant_id: str, environment: str) -> None:
        self.replica_id = replica_id
        self.tenant_id = tenant_id
        self.environment = environment
        self.active: PolicyBundle | None = None

    def activate(
        self, candidate: PolicyBundle, receipt: PolicyActivationReceipt
    ) -> None:
        if (candidate.tenant_id, candidate.environment) != (
            self.tenant_id,
            self.environment,
        ):
            raise ControlPlaneError("REPLICA_POLICY_SCOPE_MISMATCH")
        if (
            receipt.tenant_id != self.tenant_id
            or receipt.environment != self.environment
            or receipt.candidate_policy_digest != candidate.digest
        ):
            raise ControlPlaneError("REPLICA_ACTIVATION_RECEIPT_INVALID")
        if not _verify(candidate.signed_material(), candidate.signature):
            raise ControlPlaneError("POLICY_SIGNATURE_INVALID")
        self.active = candidate


class ToolInteropMapping(FrozenModel):
    concern: str
    common_technology: str
    integration_boundary: str
    control_plane_responsibility: str


def interoperability_map() -> tuple[ToolInteropMapping, ...]:
    return (
        ToolInteropMapping(
            concern="policy decision",
            common_technology="OPA/Rego or Cedar",
            integration_boundary="PDP API or embedded evaluator",
            control_plane_responsibility="version, validate, distribute, and record the exact bundle",
        ),
        ToolInteropMapping(
            concern="relationship authorization",
            common_technology="OpenFGA/Zanzibar-style ReBAC",
            integration_boundary="authorization model plus tuples",
            control_plane_responsibility="bind tenant, model ID, consistency need, and contextual facts",
        ),
        ToolInteropMapping(
            concern="workload identity",
            common_technology="SPIFFE/SPIRE",
            integration_boundary="X.509-SVID or JWT-SVID",
            control_plane_responsibility="derive workload identity at trusted ingress; never accept it from model output",
        ),
        ToolInteropMapping(
            concern="network enforcement",
            common_technology="Envoy ext_authz",
            integration_boundary="CheckRequest/CheckResponse",
            control_plane_responsibility="choose fail mode and preserve decision/effect correlation",
        ),
        ToolInteropMapping(
            concern="delegated OAuth",
            common_technology="RFC 8693 and RFC 9396",
            integration_boundary="token exchange and authorization_details",
            control_plane_responsibility="attenuate audience, scope, resource, purpose, and lifetime",
        ),
        ToolInteropMapping(
            concern="tool protocol",
            common_technology="MCP Authorization",
            integration_boundary="OAuth protected-resource metadata and audience-bound token",
            control_plane_responsibility="govern discovery and every call; prohibit token passthrough",
        ),
        ToolInteropMapping(
            concern="telemetry",
            common_technology="OpenTelemetry",
            integration_boundary="trace/span context",
            control_plane_responsibility="minimize sensitive attributes and link proposal, decision, effect, and outcome",
        ),
    )


REGO_POLICY = """
package procurement.governance
import rego.v1

default decision := {"effect": "deny", "reasons": ["default_deny"]}

decision := {"effect": "allow", "reasons": ["authorized_read"]} if {
  input.tenant_id == input.tool.tenant_id
  input.operation == "read_vendor"
  "read_vendor" in input.delegation.operations
}
""".strip()


CEDAR_POLICY = """
permit (
  principal is Workload,
  action == Action::"readVendor",
  resource is Vendor
)
when {
  principal.tenant == resource.tenant &&
  context.purpose == "quarterly-office-supplies"
};
""".strip()


OPENFGA_MODEL = """
model
  schema 1.1
type user
type agent
  relations
    define operator: [user]
type tenant
  relations
    define member: [user]
type tool
  relations
    define tenant: [tenant]
    define invoker: [agent]
    define can_invoke: invoker
""".strip()


def build_sdk_artifacts() -> dict[str, object]:
    """Construct real offline SDK configuration objects without making requests."""

    from opa_client import OpaClient
    from openfga_sdk import ClientConfiguration

    opa = OpaClient(host="127.0.0.1", port=8181, version="v1", timeout=0.1, retries=0)
    openfga = ClientConfiguration(
        api_url="http://127.0.0.1:8080",
        store_id="course15-offline-store",
        authorization_model_id="course15-model-v1",
        timeout_millisec=100,
    )
    versions = {
        package: metadata.version(package)
        for package in (
            "opa-python-client",
            "openfga_sdk",
            "opentelemetry-sdk",
            "mcp",
        )
    }
    return {
        "opa_client": opa,
        "openfga_configuration": openfga,
        "versions": versions,
        "rego_policy": REGO_POLICY,
        "cedar_policy": CEDAR_POLICY,
        "openfga_model": OPENFGA_MODEL,
    }


def build_otel_demo() -> tuple[dict[str, object], ...]:
    """Return in-memory spans; content and secrets are intentionally absent."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("course15.control-plane", "1.0")
    with tracer.start_as_current_span("governance.authorize") as span:
        span.set_attribute("governance.policy.version", POLICY_VERSION)
        span.set_attribute("governance.decision", "allow")
        span.set_attribute("governance.tenant.id", TENANT_ACME)
        span.set_attribute("gen_ai.agent.id", "procurement-agent")
    return tuple(
        {
            "name": span.name,
            "attributes": dict(span.attributes or {}),
            "trace_id": format(span.context.trace_id, "032x"),
        }
        for span in exporter.get_finished_spans()
    )


def build_course15_reference_run() -> dict[str, object]:
    env = build_reference_environment()
    cp: ControlPlane = env["control_plane"]  # type: ignore[assignment]
    context: AuthenticatedContext = env["context"]  # type: ignore[assignment]
    grant: DelegationGrant = env["grant"]  # type: ignore[assignment]
    request = cp.build_request(
        context,
        "procurement-agent",
        grant,
        proposal(amount=25_000, suffix="reference"),
        environment="production",
        now=REFERENCE_TIME,
    )
    pending = cp.decide(request, grant, now=REFERENCE_TIME)
    approval = issue_approval(
        pending,
        tenant_id=TENANT_ACME,
        approver_id="user:director-lee",
        approver_role="procurement-director",
    )
    gateway = ToolGateway(cp, env["adapter"], env["approvals"], env["evidence"])  # type: ignore[arg-type]
    decision, receipt = gateway.execute(
        request, grant, approval=approval, now=REFERENCE_TIME
    )
    candidate = issue_policy_bundle(version=POLICY_CANDIDATE_VERSION)
    shadow_report = evaluate_shadow_rollout(cp.policy, candidate)
    activation = authorize_policy_activation(
        candidate,
        shadow_report,
        build_operator("policy-admin"),
        now=REFERENCE_TIME + timedelta(minutes=1),
    )
    replica = PolicyReplica("pdp-ca-west-1", TENANT_ACME, "production")
    replica.activate(candidate, activation)
    return {
        **env,
        "request": request,
        "decision": decision,
        "approval": approval,
        "receipt": receipt,
        "governed_evaluation": evaluate_control_plane(),
        "baseline_evaluation": evaluate_prompt_only_baseline(),
        "candidate_policy": candidate,
        "shadow_report": shadow_report,
        "activation": activation,
        "replica": replica,
        "interop": interoperability_map(),
        "sdk_artifacts": build_sdk_artifacts(),
        "spans": build_otel_demo(),
    }


__all__ = [name for name in globals() if not name.startswith("_")]
