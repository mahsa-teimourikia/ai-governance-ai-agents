"""Deterministic Tool and MCP governance lab for Course 7.

The scenario is an enterprise procurement agent that discovers tools through
MCP-shaped descriptors and invokes them only through a non-bypassable gateway.
The model proposes; trusted application code validates identity, registry
attestation, schemas, business facts, approval receipts and budgets before a
capability-bearing adapter may create an effect.

The module is local, credential-free and deterministic.  It uses the installed
official ``mcp`` SDK's ``Tool`` type, but does not start a network server.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import ipaddress
import json
from threading import Lock
from typing import Any, Callable, Iterable
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from mcp.types import Tool
from pydantic import BaseModel, ConfigDict, Field, model_validator


REFERENCE_TIME = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "tool-gateway/2026-09-21"
MCP_ISSUER = "https://idp.example.test"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical(value: object) -> object:
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="python", by_alias=True))
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (set, frozenset, tuple, list)):
        values = [_canonical(v) for v in value]
        return sorted(values, key=lambda v: json.dumps(v, sort_keys=True)) if isinstance(value, (set, frozenset)) else values
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def stable_digest(value: object) -> str:
    encoded = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


class Outcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


class EffectStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    APPLIED = "applied"
    UNKNOWN = "unknown"
    COMPENSATED = "compensated"


class AuthenticatedContext(FrozenModel):
    subject_id: str
    workload_id: str
    tenant_id: str
    task_id: str
    authenticated_at: datetime
    valid_until: datetime
    # Claims below are trusted only after normal signature and issuer validation.
    token_issuer: str = MCP_ISSUER
    token_resource: str = "mcp://procurement-prod"
    scopes: frozenset[str] = frozenset(
        {"tools:procurement.create_po", "tools:procurement.cancel_po"}
    )

    @model_validator(mode="after")
    def positive_lifetime(self) -> "AuthenticatedContext":
        if self.valid_until <= self.authenticated_at:
            raise ValueError("authentication lifetime must be positive")
        return self


class ToolProposal(FrozenModel):
    operation_id: str = Field(pattern=r"^OP-[A-Z0-9-]+$")
    server_id: str
    tool_name: str
    arguments: dict[str, Any]
    observed_manifest_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    # Explicitly untrusted model assertions; policy never treats these as facts.
    model_claimed_approved: bool = False
    model_claimed_role: str | None = None


class TrustedFacts(FrozenModel):
    tenant_id: str
    approved_vendor_ids: frozenset[str]
    task_amount_limit_cents: int = Field(ge=0)
    source_version: str
    observed_at: datetime
    valid_until: datetime


class ToolContract(FrozenModel):
    server_id: str
    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    owner: str
    risk_tier: str
    allowed_workloads: frozenset[str]
    max_autonomous_cents: int | None = None
    hard_limit_cents: int | None = None
    approval_roles: frozenset[str] = frozenset()
    reversible: bool = False
    compensation_tool: str | None = None
    version: str = "1.0.0"
    status: str = "active"
    review_expires_at: datetime
    required_scope: str = "tools:procurement.create_po"

    @property
    def manifest_digest(self) -> str:
        return stable_digest(
            {
                "server_id": self.server_id,
                "name": self.name,
                "title": self.title,
                "description": self.description,
                "input_schema": self.input_schema,
                "output_schema": self.output_schema,
                "version": self.version,
            }
        )


class ApprovalReceipt(FrozenModel):
    receipt_id: str
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tenant_id: str
    subject_id: str
    workload_id: str
    task_id: str
    tool_name: str
    manifest_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: str
    approver_id: str
    approver_role: str
    issued_at: datetime
    expires_at: datetime


class ToolDecision(FrozenModel):
    decision_id: str
    outcome: Outcome
    reason_codes: tuple[str, ...]
    request_digest: str
    policy_version: str = POLICY_VERSION
    manifest_digest: str | None = None
    facts_version: str | None = None
    decided_at: datetime


class EffectReceipt(FrozenModel):
    effect_id: str | None
    tenant_id: str
    operation_id: str
    tool_name: str
    request_digest: str
    status: EffectStatus
    backend_version: str = "procurement-api/v3"


class GatewayResult(FrozenModel):
    decision: ToolDecision
    effect: EffectReceipt
    output: dict[str, Any] | None = None


class EvidenceEvent(FrozenModel):
    decision_id: str
    tenant_id: str
    subject_id: str
    workload_id: str
    task_id: str
    operation_id: str
    tool_name: str
    request_digest: str
    manifest_digest: str | None
    outcome: Outcome
    reason_codes: tuple[str, ...]
    policy_version: str
    facts_version: str | None
    effect_status: EffectStatus
    occurred_at: datetime


class EvaluationCase(FrozenModel):
    name: str
    context: AuthenticatedContext
    proposal: ToolProposal
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
    escalation_case_count: int
    baseline_missed_escalation_count: int
    candidate_missed_escalation_count: int


class AuthorizationChallenge(FrozenModel):
    """Minimal HTTP challenge shape from the MCP authorization specification."""

    status_code: int
    www_authenticate: str


def authorization_challenge(
    resource_metadata_url: str, *, insufficient_scope: bool = False
) -> AuthorizationChallenge:
    error = "insufficient_scope" if insufficient_scope else "invalid_token"
    return AuthorizationChallenge(
        status_code=403 if insufficient_scope else 401,
        www_authenticate=(
            f'Bearer error="{error}", '
            f'resource_metadata="{resource_metadata_url}"'
        ),
    )


class ToolRegistry:
    """Approved catalog; discovery is convenience, call-time validation is authority."""

    def __init__(self, contracts: Iterable[ToolContract]):
        self._contracts = {(c.server_id, c.name): c for c in contracts}

    def get(self, server_id: str, tool_name: str) -> ToolContract | None:
        return self._contracts.get((server_id, tool_name))

    def discover(self, context: AuthenticatedContext, now: datetime) -> tuple[Tool, ...]:
        return tuple(
            to_mcp_tool(c)
            for c in self._contracts.values()
            if c.status == "active"
            and c.review_expires_at >= now
            and context.workload_id in c.allowed_workloads
        )

    def replace(self, contract: ToolContract) -> None:
        self._contracts[(contract.server_id, contract.name)] = contract

    def revoke(self, server_id: str, tool_name: str) -> None:
        current = self._contracts[(server_id, tool_name)]
        self.replace(current.model_copy(update={"status": "revoked"}))


def to_mcp_tool(contract: ToolContract) -> Tool:
    """Create a real official-SDK descriptor without running a server."""

    return Tool(
        name=contract.name,
        title=contract.title,
        description=contract.description,
        inputSchema=contract.input_schema,
        outputSchema=contract.output_schema,
        annotations={"readOnlyHint": contract.risk_tier == "T0"},
        _meta={
            "governance/manifestDigest": contract.manifest_digest,
            "governance/riskTier": contract.risk_tier,
            "governance/owner": contract.owner,
        },
    )


class ApprovalStore:
    def __init__(self):
        self._receipts: dict[str, ApprovalReceipt] = {}
        self._consumed: set[str] = set()
        self._lock = Lock()

    def add(self, receipt: ApprovalReceipt) -> None:
        self._receipts[receipt.receipt_id] = receipt

    def consume(
        self,
        receipt_id: str | None,
        *,
        context: AuthenticatedContext,
        proposal: ToolProposal,
        request_digest: str,
        contract: ToolContract,
        now: datetime,
    ) -> str | None:
        if receipt_id is None:
            return "APPROVAL_REQUIRED"
        with self._lock:
            receipt = self._receipts.get(receipt_id)
            if receipt is None:
                return "APPROVAL_UNKNOWN"
            if receipt_id in self._consumed:
                return "APPROVAL_REPLAYED"
            bindings_match = (
                receipt.request_digest == request_digest
                and receipt.tenant_id == context.tenant_id
                and receipt.subject_id == context.subject_id
                and receipt.workload_id == context.workload_id
                and receipt.task_id == context.task_id
                and receipt.tool_name == proposal.tool_name
                and receipt.manifest_digest == contract.manifest_digest
                and receipt.policy_version == POLICY_VERSION
            )
            if not bindings_match:
                return "APPROVAL_BINDING_MISMATCH"
            if receipt.expires_at < now or receipt.issued_at > now:
                return "APPROVAL_EXPIRED"
            if receipt.approver_role not in contract.approval_roles:
                return "APPROVER_ROLE_INVALID"
            self._consumed.add(receipt_id)
            return None


class BudgetLedger:
    """Atomic per-tenant/task reservation closes check-then-increment races."""

    def __init__(self, call_limit: int = 10, spend_limit_cents: int = 2_000_000):
        self.call_limit = call_limit
        self.spend_limit_cents = spend_limit_cents
        self._calls: dict[tuple[str, str], int] = defaultdict(int)
        self._spend: dict[tuple[str, str], int] = defaultdict(int)
        self._lock = Lock()

    def reserve(self, context: AuthenticatedContext, amount_cents: int) -> str | None:
        key = (context.tenant_id, context.task_id)
        with self._lock:
            if self._calls[key] + 1 > self.call_limit:
                return "CALL_BUDGET_EXCEEDED"
            if self._spend[key] + amount_cents > self.spend_limit_cents:
                return "SPEND_BUDGET_EXCEEDED"
            self._calls[key] += 1
            self._spend[key] += amount_cents
        return None

    def usage(self, context: AuthenticatedContext) -> tuple[int, int]:
        key = (context.tenant_id, context.task_id)
        return self._calls[key], self._spend[key]


class UnknownEffect(RuntimeError):
    pass


class ProcurementAdapter:
    """Backend simulator that requires a gateway-owned, unforgeable object."""

    def __init__(self, capability: object):
        self._capability = capability
        self._effects: dict[tuple[str, str], EffectReceipt] = {}
        self._outputs: dict[tuple[str, str], dict[str, Any]] = {}
        self.failure_mode: str | None = None
        self.last_credential_used = False

    def execute(
        self,
        capability: object,
        context: AuthenticatedContext,
        proposal: ToolProposal,
        request_digest: str,
    ) -> tuple[EffectReceipt, dict[str, Any]]:
        if capability is not self._capability:
            raise PermissionError("adapter invocation must pass through the gateway")
        key = (context.tenant_id, proposal.operation_id)
        if key in self._effects:
            return self._effects[key], self._outputs[key]
        if self.failure_mode == "before_commit":
            raise UnknownEffect("backend timed out before effect status was known")
        self.last_credential_used = True  # brokered internally; never returned or logged
        effect_id = "EF-" + stable_digest({"tenant": key[0], "operation": key[1]})[:16]
        if proposal.tool_name == "procurement.cancel_po":
            original_operation = str(proposal.arguments["original_operation_id"])
            original = self._effects.get((context.tenant_id, original_operation))
            if original is None or original.tool_name != "procurement.create_po":
                raise UnknownEffect("original tenant-scoped effect could not be established")
            receipt = EffectReceipt(
                effect_id=effect_id,
                tenant_id=context.tenant_id,
                operation_id=proposal.operation_id,
                tool_name=proposal.tool_name,
                request_digest=request_digest,
                status=EffectStatus.COMPENSATED,
            )
            output = {
                "effect_id": effect_id,
                "status": "cancelled",
                "tenant_id": context.tenant_id,
                "compensates_effect_id": original.effect_id,
            }
            self._effects[key], self._outputs[key] = receipt, output
            return receipt, output
        receipt = EffectReceipt(
            effect_id=effect_id,
            tenant_id=context.tenant_id,
            operation_id=proposal.operation_id,
            tool_name=proposal.tool_name,
            request_digest=request_digest,
            status=EffectStatus.APPLIED,
        )
        output = {"effect_id": effect_id, "status": "created", "tenant_id": context.tenant_id}
        self._effects[key], self._outputs[key] = receipt, output
        if self.failure_mode == "after_commit":
            raise UnknownEffect("backend committed before transport timed out")
        return receipt, output

    def reconcile(self, tenant_id: str, operation_id: str) -> tuple[EffectReceipt, dict[str, Any]] | None:
        key = (tenant_id, operation_id)
        if key not in self._effects:
            return None
        return self._effects[key], self._outputs[key]


class ToolGateway:
    def __init__(
        self,
        registry: ToolRegistry,
        approvals: ApprovalStore | None = None,
        budgets: BudgetLedger | None = None,
    ):
        self.registry = registry
        self.approvals = approvals or ApprovalStore()
        self.budgets = budgets or BudgetLedger()
        self._capability = object()
        self.adapter = ProcurementAdapter(self._capability)
        self.evidence: list[EvidenceEvent] = []
        self._idempotency: dict[tuple[str, str], tuple[str, GatewayResult]] = {}
        self._lock = Lock()

    @staticmethod
    def request_digest(context: AuthenticatedContext, proposal: ToolProposal) -> str:
        return stable_digest(
            {
                "tenant_id": context.tenant_id,
                "subject_id": context.subject_id,
                "workload_id": context.workload_id,
                "task_id": context.task_id,
                "operation_id": proposal.operation_id,
                "server_id": proposal.server_id,
                "tool_name": proposal.tool_name,
                "arguments": proposal.arguments,
                "manifest_digest": proposal.observed_manifest_digest,
            }
        )

    def _decision(
        self,
        outcome: Outcome,
        reasons: Iterable[str],
        digest: str,
        now: datetime,
        contract: ToolContract | None = None,
        facts: TrustedFacts | None = None,
    ) -> ToolDecision:
        return ToolDecision(
            decision_id="TD-" + stable_digest({"request": digest, "outcome": outcome, "reasons": tuple(reasons)})[:16],
            outcome=outcome,
            reason_codes=tuple(reasons),
            request_digest=digest,
            manifest_digest=contract.manifest_digest if contract else None,
            facts_version=facts.source_version if facts else None,
            decided_at=now,
        )

    def evaluate(
        self,
        context: AuthenticatedContext,
        proposal: ToolProposal,
        facts: TrustedFacts | None,
        now: datetime = REFERENCE_TIME,
        approval_receipt_id: str | None = None,
        consume_approval: bool = False,
        reserve_budget: bool = False,
    ) -> ToolDecision:
        digest = self.request_digest(context, proposal)
        contract = self.registry.get(proposal.server_id, proposal.tool_name)
        if contract is None:
            return self._decision(Outcome.DENY, ("TOOL_NOT_REGISTERED",), digest, now)
        if contract.status != "active" or contract.review_expires_at < now:
            return self._decision(Outcome.DENY, ("TOOL_NOT_ACTIVE",), digest, now, contract)
        if proposal.observed_manifest_digest != contract.manifest_digest:
            return self._decision(Outcome.DENY, ("MANIFEST_ATTESTATION_FAILED",), digest, now, contract)
        if context.valid_until < now or context.authenticated_at > now:
            return self._decision(Outcome.DENY, ("AUTHENTICATION_STALE",), digest, now, contract)
        if context.token_issuer != MCP_ISSUER:
            return self._decision(Outcome.DENY, ("TOKEN_ISSUER_UNTRUSTED",), digest, now, contract)
        if context.token_resource != contract.server_id:
            return self._decision(Outcome.DENY, ("TOKEN_RESOURCE_MISMATCH",), digest, now, contract)
        if contract.required_scope not in context.scopes:
            return self._decision(Outcome.DENY, ("TOKEN_SCOPE_INSUFFICIENT",), digest, now, contract)
        if context.workload_id not in contract.allowed_workloads:
            return self._decision(Outcome.DENY, ("WORKLOAD_NOT_AUTHORIZED",), digest, now, contract)
        errors = sorted(Draft202012Validator(contract.input_schema).iter_errors(proposal.arguments), key=lambda e: list(e.path))
        if errors:
            return self._decision(Outcome.DENY, ("INPUT_SCHEMA_INVALID",), digest, now, contract)
        if facts is None or facts.valid_until < now or facts.observed_at > now:
            return self._decision(Outcome.DENY, ("TRUSTED_FACTS_STALE",), digest, now, contract, facts)
        if facts.tenant_id != context.tenant_id:
            return self._decision(Outcome.DENY, ("TENANT_BINDING_MISMATCH",), digest, now, contract, facts)

        amount = int(proposal.arguments.get("amount_cents", 0))
        vendor = proposal.arguments.get("vendor_id")
        if vendor is not None and vendor not in facts.approved_vendor_ids:
            return self._decision(Outcome.DENY, ("VENDOR_NOT_APPROVED",), digest, now, contract, facts)
        if amount > facts.task_amount_limit_cents:
            return self._decision(Outcome.DENY, ("TASK_AMOUNT_LIMIT_EXCEEDED",), digest, now, contract, facts)
        if contract.hard_limit_cents is not None and amount > contract.hard_limit_cents:
            return self._decision(Outcome.DENY, ("TOOL_HARD_LIMIT_EXCEEDED",), digest, now, contract, facts)
        if contract.max_autonomous_cents is not None and amount > contract.max_autonomous_cents:
            if not consume_approval:
                return self._decision(Outcome.ESCALATE, ("APPROVAL_REQUIRED",), digest, now, contract, facts)
            approval_error = self.approvals.consume(
                approval_receipt_id,
                context=context,
                proposal=proposal,
                request_digest=digest,
                contract=contract,
                now=now,
            )
            if approval_error:
                outcome = Outcome.ESCALATE if approval_error == "APPROVAL_REQUIRED" else Outcome.DENY
                return self._decision(outcome, (approval_error,), digest, now, contract, facts)
        if reserve_budget:
            budget_error = self.budgets.reserve(context, amount)
            if budget_error:
                return self._decision(Outcome.DENY, (budget_error,), digest, now, contract, facts)
        return self._decision(Outcome.ALLOW, ("ALL_CONTROLS_SATISFIED",), digest, now, contract, facts)

    def invoke(
        self,
        context: AuthenticatedContext,
        proposal: ToolProposal,
        facts: TrustedFacts | None,
        now: datetime = REFERENCE_TIME,
        approval_receipt_id: str | None = None,
    ) -> GatewayResult:
        digest = self.request_digest(context, proposal)
        key = (context.tenant_id, proposal.operation_id)
        with self._lock:
            replay = self._idempotency.get(key)
            if replay:
                old_digest, result = replay
                if old_digest != digest:
                    decision = self._decision(Outcome.DENY, ("IDEMPOTENCY_MUTATION",), digest, now)
                    return self._finish(context, proposal, decision, None, now)
                return result

            decision = self.evaluate(
                context,
                proposal,
                facts,
                now,
                approval_receipt_id,
                consume_approval=True,
                reserve_budget=True,
            )
            if decision.outcome is not Outcome.ALLOW:
                return self._finish(context, proposal, decision, None, now)
            try:
                receipt, output = self.adapter.execute(self._capability, context, proposal, digest)
                contract = self.registry.get(proposal.server_id, proposal.tool_name)
                assert contract is not None
                if sorted(Draft202012Validator(contract.output_schema).iter_errors(output), key=lambda e: list(e.path)):
                    unknown = receipt.model_copy(update={"status": EffectStatus.UNKNOWN})
                    result = self._finish(context, proposal, decision, unknown, now)
                else:
                    result = self._finish(context, proposal, decision, receipt, now, output)
            except UnknownEffect:
                reconciled = self.adapter.reconcile(context.tenant_id, proposal.operation_id)
                if reconciled:
                    receipt, output = reconciled
                    result = self._finish(context, proposal, decision, receipt, now, output)
                else:
                    unknown = EffectReceipt(
                        effect_id=None,
                        tenant_id=context.tenant_id,
                        operation_id=proposal.operation_id,
                        tool_name=proposal.tool_name,
                        request_digest=digest,
                        status=EffectStatus.UNKNOWN,
                    )
                    result = self._finish(context, proposal, decision, unknown, now)
            self._idempotency[key] = (digest, result)
            return result

    def _finish(
        self,
        context: AuthenticatedContext,
        proposal: ToolProposal,
        decision: ToolDecision,
        receipt: EffectReceipt | None,
        now: datetime,
        output: dict[str, Any] | None = None,
    ) -> GatewayResult:
        effect = receipt or EffectReceipt(
            effect_id=None,
            tenant_id=context.tenant_id,
            operation_id=proposal.operation_id,
            tool_name=proposal.tool_name,
            request_digest=decision.request_digest,
            status=EffectStatus.NOT_ATTEMPTED,
        )
        self.evidence.append(
            EvidenceEvent(
                decision_id=decision.decision_id,
                tenant_id=context.tenant_id,
                subject_id=context.subject_id,
                workload_id=context.workload_id,
                task_id=context.task_id,
                operation_id=proposal.operation_id,
                tool_name=proposal.tool_name,
                request_digest=decision.request_digest,
                manifest_digest=decision.manifest_digest,
                outcome=decision.outcome,
                reason_codes=decision.reason_codes,
                policy_version=decision.policy_version,
                facts_version=decision.facts_version,
                effect_status=effect.status,
                occurred_at=now,
            )
        )
        return GatewayResult(decision=decision, effect=effect, output=output)


def validate_outbound_url(
    url: str,
    resolver: Callable[[str], Iterable[str]],
    allowed_hosts: frozenset[str],
) -> tuple[str, ...]:
    """Validate scheme/host and every resolved A/AAAA address before connect."""

    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL must be credential-free HTTPS")
    if parsed.fragment or parsed.port not in (None, 443):
        raise ValueError("URL fragments and non-standard ports are forbidden")
    host = parsed.hostname.rstrip(".").lower()
    if host not in allowed_hosts:
        raise ValueError("destination host is not allowlisted")
    addresses = tuple(resolver(host))
    if not addresses:
        raise ValueError("destination did not resolve")
    for raw in addresses:
        address = ipaddress.ip_address(raw)
        if not address.is_global:
            raise ValueError("destination resolved to a non-global address")
    return addresses


def validate_redirect_chain(
    urls: Iterable[str],
    resolver: Callable[[str], Iterable[str]],
    allowed_hosts: frozenset[str],
    max_hops: int = 3,
) -> tuple[tuple[str, ...], ...]:
    """Apply the complete destination policy to the initial URL and every hop."""

    chain = tuple(urls)
    if not chain or len(chain) > max_hops + 1:
        raise ValueError("redirect chain is empty or exceeds the hop limit")
    return tuple(validate_outbound_url(url, resolver, allowed_hosts) for url in chain)


PO_INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "vendor_id": {"type": "string", "pattern": "^VEN-[0-9]{3}$"},
        "amount_cents": {"type": "integer", "minimum": 1},
        "currency": {"const": "CAD"},
    },
    "required": ["vendor_id", "amount_cents", "currency"],
    "additionalProperties": False,
}
PO_OUTPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "effect_id": {"type": "string", "pattern": "^EF-[0-9a-f]{16}$"},
        "status": {"const": "created"},
        "tenant_id": {"type": "string"},
    },
    "required": ["effect_id", "status", "tenant_id"],
    "additionalProperties": False,
}
CANCEL_INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "original_operation_id": {"type": "string", "pattern": "^OP-[A-Z0-9-]+$"},
        "reason": {"type": "string", "minLength": 3, "maxLength": 200},
    },
    "required": ["original_operation_id", "reason"],
    "additionalProperties": False,
}
CANCEL_OUTPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "effect_id": {"type": "string", "pattern": "^EF-[0-9a-f]{16}$"},
        "status": {"const": "cancelled"},
        "tenant_id": {"type": "string"},
        "compensates_effect_id": {"type": "string", "pattern": "^EF-[0-9a-f]{16}$"},
    },
    "required": ["effect_id", "status", "tenant_id", "compensates_effect_id"],
    "additionalProperties": False,
}


def sample_contract(**changes: object) -> ToolContract:
    base = ToolContract(
        server_id="mcp://procurement-prod",
        name="procurement.create_po",
        title="Create purchase order",
        description="Create one CAD purchase order for an approved vendor.",
        input_schema=PO_INPUT_SCHEMA,
        output_schema=PO_OUTPUT_SCHEMA,
        owner="procurement-platform",
        risk_tier="T2",
        allowed_workloads=frozenset({"procurement-agent"}),
        max_autonomous_cents=500_000,
        hard_limit_cents=2_000_000,
        approval_roles=frozenset({"procurement-manager"}),
        reversible=True,
        compensation_tool="procurement.cancel_po",
        review_expires_at=REFERENCE_TIME + timedelta(days=90),
    )
    return base.model_copy(update=changes)


def sample_context(**changes: object) -> AuthenticatedContext:
    base = AuthenticatedContext(
        subject_id="usr-1042",
        workload_id="procurement-agent",
        tenant_id="tenant-north",
        task_id="task-quarterly-supplies",
        authenticated_at=REFERENCE_TIME - timedelta(minutes=2),
        valid_until=REFERENCE_TIME + timedelta(minutes=8),
    )
    return base.model_copy(update=changes)


def sample_cancel_contract(**changes: object) -> ToolContract:
    base = ToolContract(
        server_id="mcp://procurement-prod",
        name="procurement.cancel_po",
        title="Cancel purchase order",
        description="Compensate one tenant-scoped purchase-order effect.",
        input_schema=CANCEL_INPUT_SCHEMA,
        output_schema=CANCEL_OUTPUT_SCHEMA,
        owner="procurement-platform",
        risk_tier="T2",
        allowed_workloads=frozenset({"procurement-agent"}),
        reversible=False,
        review_expires_at=REFERENCE_TIME + timedelta(days=90),
        required_scope="tools:procurement.cancel_po",
    )
    return base.model_copy(update=changes)


def sample_facts(**changes: object) -> TrustedFacts:
    base = TrustedFacts(
        tenant_id="tenant-north",
        approved_vendor_ids=frozenset({"VEN-101", "VEN-202"}),
        task_amount_limit_cents=2_000_000,
        source_version="vendor-master/8421",
        observed_at=REFERENCE_TIME - timedelta(minutes=1),
        valid_until=REFERENCE_TIME + timedelta(minutes=4),
    )
    return base.model_copy(update=changes)


def sample_proposal(contract: ToolContract, **changes: object) -> ToolProposal:
    base = ToolProposal(
        operation_id="OP-1001",
        server_id=contract.server_id,
        tool_name=contract.name,
        arguments={"vendor_id": "VEN-101", "amount_cents": 125_000, "currency": "CAD"},
        observed_manifest_digest=contract.manifest_digest,
    )
    return base.model_copy(update=changes)


def unsafe_schema_only_dispatch(contract: ToolContract, proposal: ToolProposal) -> Outcome:
    """Baseline: trusts discovery and checks only the JSON schema."""

    errors = list(Draft202012Validator(contract.input_schema).iter_errors(proposal.arguments))
    return Outcome.DENY if errors else Outcome.ALLOW


def labelled_evaluation() -> tuple[EvaluationCase, ...]:
    contract = sample_contract()
    context, facts = sample_context(), sample_facts()
    proposal = sample_proposal(contract)
    return (
        EvaluationCase(name="safe autonomous PO", context=context, proposal=proposal, facts=facts, expected=Outcome.ALLOW),
        EvaluationCase(name="approval threshold", context=context, proposal=proposal.model_copy(update={"operation_id": "OP-1002", "arguments": {"vendor_id": "VEN-101", "amount_cents": 700_000, "currency": "CAD"}}), facts=facts, expected=Outcome.ESCALATE),
        EvaluationCase(name="unapproved vendor", context=context, proposal=proposal.model_copy(update={"operation_id": "OP-1003", "arguments": {"vendor_id": "VEN-999", "amount_cents": 10_000, "currency": "CAD"}}), facts=facts, expected=Outcome.DENY),
        EvaluationCase(name="hard amount limit", context=context, proposal=proposal.model_copy(update={"operation_id": "OP-1004", "arguments": {"vendor_id": "VEN-101", "amount_cents": 2_100_000, "currency": "CAD"}}), facts=facts, expected=Outcome.DENY),
        EvaluationCase(name="wrong workload", context=context.model_copy(update={"workload_id": "email-agent"}), proposal=proposal.model_copy(update={"operation_id": "OP-1005"}), facts=facts, expected=Outcome.DENY),
        EvaluationCase(name="wrong tenant facts", context=context, proposal=proposal.model_copy(update={"operation_id": "OP-1006"}), facts=facts.model_copy(update={"tenant_id": "tenant-south"}), expected=Outcome.DENY),
        EvaluationCase(name="poisoned manifest", context=context, proposal=proposal.model_copy(update={"operation_id": "OP-1007", "observed_manifest_digest": "0" * 64}), facts=facts, expected=Outcome.DENY),
        EvaluationCase(name="stale facts", context=context, proposal=proposal.model_copy(update={"operation_id": "OP-1008"}), facts=facts.model_copy(update={"valid_until": REFERENCE_TIME - timedelta(seconds=1)}), expected=Outcome.DENY),
        EvaluationCase(name="schema injection", context=context, proposal=proposal.model_copy(update={"operation_id": "OP-1009", "arguments": {"vendor_id": "VEN-101", "amount_cents": 10_000, "currency": "CAD", "admin": True}}), facts=facts, expected=Outcome.DENY),
    )


def run_evaluation() -> EvaluationSummary:
    contract = sample_contract()
    gateway = ToolGateway(ToolRegistry([contract]))
    cases = labelled_evaluation()
    baseline = [unsafe_schema_only_dispatch(contract, case.proposal) for case in cases]
    candidate = [gateway.evaluate(case.context, case.proposal, case.facts).outcome for case in cases]
    forbidden = [i for i, case in enumerate(cases) if case.expected is Outcome.DENY]
    escalations = [i for i, case in enumerate(cases) if case.expected is Outcome.ESCALATE]
    return EvaluationSummary(
        case_count=len(cases),
        expected_allow_count=sum(c.expected is Outcome.ALLOW for c in cases),
        expected_deny_count=len(forbidden),
        expected_escalate_count=len(escalations),
        baseline_correct_count=sum(got is case.expected for got, case in zip(baseline, cases)),
        candidate_correct_count=sum(got is case.expected for got, case in zip(candidate, cases)),
        forbidden_case_count=len(forbidden),
        baseline_forbidden_allowed_count=sum(baseline[i] is Outcome.ALLOW for i in forbidden),
        candidate_forbidden_allowed_count=sum(candidate[i] is Outcome.ALLOW for i in forbidden),
        escalation_case_count=len(escalations),
        baseline_missed_escalation_count=sum(baseline[i] is not Outcome.ESCALATE for i in escalations),
        candidate_missed_escalation_count=sum(candidate[i] is not Outcome.ESCALATE for i in escalations),
    )
