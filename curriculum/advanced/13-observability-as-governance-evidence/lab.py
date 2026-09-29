"""Deterministic governance-evidence lab for Course 13.

The module models an enterprise procurement-agent evidence pipeline without
calling a model, network, collector, cloud service, or business system.  It
keeps operational tracing separate from trusted evidence, rejects raw content,
binds approvals and outcomes to exact actions, validates an append-only event
chain, applies tenant-aware access control, and produces offline OpenTelemetry
and OpenAI Agents SDK artifacts for integration study.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from enum import IntEnum, StrEnum
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from threading import RLock
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

REFERENCE_TIME = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
SCHEMA_VERSION = "governance-evidence/1.0"
POLICY_VERSION = "evidence-policy/13.1"
TARGET_ID = "procurement-agent"
TARGET_VERSION = "13.0.0"
GENESIS_DIGEST = "0" * 64
SYNTHETIC_INTEGRITY_KEY = b"course-13-synthetic-integrity-key"
SYNTHETIC_PSEUDONYM_KEY = b"course-13-synthetic-pseudonym-key"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class RiskTier(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


class EventKind(StrEnum):
    WORKFLOW_STARTED = "workflow_started"
    RETRIEVAL = "retrieval"
    DELEGATION = "delegation"
    POLICY_DECISION = "policy_decision"
    APPROVAL = "approval"
    TOOL_PROPOSED = "tool_proposed"
    AUTHORIZATION = "authorization"
    EFFECT = "effect"
    OUTCOME = "outcome"
    ERROR = "error"


class RetentionClass(StrEnum):
    ROUTINE = "routine"
    GOVERNANCE = "governance"
    SECURITY = "security"
    LEGAL_HOLD = "legal_hold"


class Disposition(StrEnum):
    RETAIN = "retain"
    ELIGIBLE_FOR_REVIEW = "eligible_for_review"


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
        return value.astimezone(UTC).isoformat()
    if isinstance(value, (IntEnum, StrEnum)):
        return value.value
    return value


def stable_digest(value: object) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def keyed_digest(value: str, key: bytes = SYNTHETIC_PSEUDONYM_KEY) -> str:
    """Create a stable lab pseudonym; production keys belong in a managed KMS."""

    return (
        "psn_" + hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
    )


def sign_digest(digest: str, key: bytes = SYNTHETIC_INTEGRITY_KEY) -> str:
    return hmac.new(key, digest.encode("ascii"), hashlib.sha256).hexdigest()


def deterministic_hex(seed: str, length: int) -> str:
    value = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:length]
    return value if set(value) != {"0"} else "1" + value[1:]


def trace_id_for(seed: str) -> str:
    return deterministic_hex(f"trace:{seed}", 32)


def span_id_for(seed: str) -> str:
    return deterministic_hex(f"span:{seed}", 16)


TRACEPARENT_RE = re.compile(
    r"^00-(?P<trace>[0-9a-f]{32})-(?P<parent>[0-9a-f]{16})-(?P<flags>[0-9a-f]{2})$"
)


def make_traceparent(trace_id: str, parent_span_id: str, *, sampled: bool) -> str:
    candidate = f"00-{trace_id}-{parent_span_id}-{'01' if sampled else '00'}"
    parse_traceparent(candidate)
    return candidate


def parse_traceparent(value: str) -> dict[str, object]:
    match = TRACEPARENT_RE.fullmatch(value)
    if not match:
        raise EvidenceError("TRACEPARENT_INVALID")
    if set(match["trace"]) == {"0"} or set(match["parent"]) == {"0"}:
        raise EvidenceError("TRACEPARENT_ZERO_ID")
    return {
        "trace_id": match["trace"],
        "parent_span_id": match["parent"],
        "sampled": bool(int(match["flags"], 16) & 1),
    }


class AuthenticatedActor(FrozenModel):
    principal_id: str
    tenant_id: str
    service_name: str | None = None
    roles: frozenset[str]
    purposes: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {"control_assurance", "incident_response", "retention_administration"}
        )
    )
    authenticated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def valid_lifetime(self) -> AuthenticatedActor:
        if self.valid_until <= self.authenticated_at:
            raise ValueError("actor session lifetime must be positive")
        return self


DEFAULT_ALLOWED_ATTRIBUTE_KEYS = frozenset(
    {
        "source_ids",
        "source_digests",
        "trust_labels",
        "knowledge_base_version",
        "delegation_id",
        "delegate_id",
        "scope_digest",
        "decision_id",
        "reason_codes",
        "risk_score_band",
        "approval_id",
        "approver_role",
        "tool_id",
        "tool_version",
        "action_type",
        "amount_band",
        "currency",
        "effect_status",
        "effect_verified",
        "external_transaction_ref",
        "reversible",
        "outcome_code",
        "error_code",
        "anomaly_codes",
        "model_name",
        "input_tokens",
        "output_tokens",
    }
)

FORBIDDEN_KEY_PARTS = (
    "prompt",
    "content",
    "message",
    "body",
    "password",
    "secret",
    "credential",
    "api_key",
    "authorization_header",
    "raw_input",
    "raw_output",
)

SENSITIVE_PATTERNS = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[REDACTED_ACCOUNT]"),
)


class EvidencePolicy(FrozenModel):
    tenant_id: str
    schema_version: str = SCHEMA_VERSION
    policy_version: str = POLICY_VERSION
    capture_raw_content: bool = False
    allowed_attribute_keys: frozenset[str] = DEFAULT_ALLOWED_ATTRIBUTE_KEYS
    routine_retention_days: int = Field(default=14, ge=1, le=365)
    governance_retention_days: int = Field(default=365, ge=30, le=3650)
    security_retention_days: int = Field(default=730, ge=30, le=3650)

    @model_validator(mode="after")
    def safe_policy(self) -> EvidencePolicy:
        if self.capture_raw_content:
            raise ValueError("canonical evidence policy forbids raw content")
        if any(
            any(part in key.lower() for part in FORBIDDEN_KEY_PARTS)
            for key in self.allowed_attribute_keys
        ):
            raise ValueError("attribute allowlist contains a forbidden content field")
        return self


def redact_text(value: str) -> str:
    redacted = value
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact_value(value: object) -> object:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(key): _redact_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(child) for child in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    raise EvidenceError("ATTRIBUTE_TYPE_UNSUPPORTED")


def sanitize_attributes(
    policy: EvidencePolicy, attributes: dict[str, object]
) -> dict[str, object]:
    for key in attributes:
        normalized = key.lower()
        if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
            raise EvidenceError("RAW_CONTENT_FIELD_FORBIDDEN")
        if key not in policy.allowed_attribute_keys:
            raise EvidenceError("ATTRIBUTE_NOT_ALLOWLISTED")
    return {key: _redact_value(value) for key, value in sorted(attributes.items())}


class EvidenceEvent(FrozenModel):
    schema_version: str
    event_id: str
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    span_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    parent_span_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    sequence: int = Field(gt=0)
    occurred_at: datetime
    tenant_id: str
    producer_id: str
    service_name: str
    target_id: str
    target_version: str
    task_id: str
    kind: EventKind
    principal_ref: str
    agent_id: str
    purpose_code: str
    risk_tier: RiskTier
    policy_version: str
    decision: Decision | None = None
    authority_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    action_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    approval_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    effect_receipt_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    attributes: dict[str, object] = Field(default_factory=dict)
    previous_event_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_signature: str = Field(pattern=r"^[0-9a-f]{64}$")

    def digest_material(self) -> dict[str, object]:
        return self.model_dump(
            mode="python", exclude={"event_digest", "event_signature"}
        )

    @model_validator(mode="after")
    def digest_is_valid(self) -> EvidenceEvent:
        if self.event_digest != stable_digest(self.digest_material()):
            raise ValueError("event digest mismatch")
        if not hmac.compare_digest(
            self.event_signature, sign_digest(self.event_digest)
        ):
            raise ValueError("event signature mismatch")
        return self


class TraceEnvelope(FrozenModel):
    trace_id: str
    tenant_id: str
    target_id: str
    target_version: str
    schema_version: str
    policy_version: str
    events: tuple[EvidenceEvent, ...]
    chain_head: str = Field(pattern=r"^[0-9a-f]{64}$")
    trace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    sealed_at: datetime

    def trace_material(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "tenant_id": self.tenant_id,
            "target_id": self.target_id,
            "target_version": self.target_version,
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "event_digests": [event.event_digest for event in self.events],
            "chain_head": self.chain_head,
        }

    @model_validator(mode="after")
    def valid_envelope(self) -> TraceEnvelope:
        if not self.events:
            raise ValueError("trace must contain evidence")
        expected_sequence = tuple(range(1, len(self.events) + 1))
        if tuple(event.sequence for event in self.events) != expected_sequence:
            raise ValueError("event sequence must be contiguous")
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("event IDs must be unique")
        if len({event.span_id for event in self.events}) != len(self.events):
            raise ValueError("span IDs must be unique")
        seen_spans: set[str] = set()
        producer_bindings = {
            (event.producer_id, event.service_name) for event in self.events
        }
        if len(producer_bindings) != 1:
            raise ValueError("trace must use one authenticated producer binding")
        expected_previous = GENESIS_DIGEST
        for index, event in enumerate(self.events):
            if (
                event.trace_id != self.trace_id
                or event.tenant_id != self.tenant_id
                or event.target_id != self.target_id
                or event.target_version != self.target_version
                or event.schema_version != self.schema_version
                or event.policy_version != self.policy_version
            ):
                raise ValueError("event does not match envelope bindings")
            if index == 0:
                if (
                    event.kind != EventKind.WORKFLOW_STARTED
                    or event.parent_span_id is not None
                ):
                    raise ValueError("trace must begin with a root workflow event")
            elif event.parent_span_id not in seen_spans:
                raise ValueError("parent span must precede its child")
            elif event.occurred_at < next(
                parent.occurred_at
                for parent in self.events[:index]
                if parent.span_id == event.parent_span_id
            ):
                raise ValueError("child evidence cannot precede its parent")
            if event.previous_event_digest != expected_previous:
                raise ValueError("event hash chain is broken")
            expected_previous = event.event_digest
            seen_spans.add(event.span_id)
        if self.events[-1].kind not in {EventKind.OUTCOME, EventKind.ERROR}:
            raise ValueError("sealed trace needs a terminal outcome or error")
        if self.chain_head != self.events[-1].event_digest:
            raise ValueError("chain head mismatch")
        if self.trace_digest != stable_digest(self.trace_material()):
            raise ValueError("trace digest mismatch")
        return self


EVENT_REQUIRED_ATTRIBUTES: dict[EventKind, frozenset[str]] = {
    EventKind.RETRIEVAL: frozenset(
        {"source_ids", "source_digests", "knowledge_base_version"}
    ),
    EventKind.DELEGATION: frozenset({"delegation_id", "delegate_id", "scope_digest"}),
    EventKind.POLICY_DECISION: frozenset({"decision_id", "reason_codes"}),
    EventKind.APPROVAL: frozenset({"approval_id", "approver_role"}),
    EventKind.TOOL_PROPOSED: frozenset({"tool_id", "tool_version", "action_type"}),
    EventKind.AUTHORIZATION: frozenset({"decision_id", "reason_codes"}),
    EventKind.EFFECT: frozenset(
        {"effect_status", "effect_verified", "external_transaction_ref", "reversible"}
    ),
    EventKind.OUTCOME: frozenset({"outcome_code"}),
    EventKind.ERROR: frozenset({"error_code"}),
}


class TraceBuilder:
    def __init__(
        self,
        policy: EvidencePolicy,
        *,
        trace_seed: str,
        task_id: str,
        principal_ref: str,
        agent_id: str,
        purpose_code: str,
        producer_id: str = "workload:procurement-observer",
        service_name: str = "procurement-agent",
        target_id: str = TARGET_ID,
        target_version: str = TARGET_VERSION,
    ):
        self.policy = policy
        self.trace_id = trace_id_for(trace_seed)
        self.task_id = task_id
        self.principal_ref = principal_ref
        self.agent_id = agent_id
        self.purpose_code = purpose_code
        self.producer_id = producer_id
        self.service_name = service_name
        self.target_id = target_id
        self.target_version = target_version
        self._events: list[EvidenceEvent] = []
        self._sealed = False

    @property
    def events(self) -> tuple[EvidenceEvent, ...]:
        return tuple(self._events)

    def emit(
        self,
        kind: EventKind,
        *,
        risk_tier: RiskTier,
        parent_span_id: str | None = None,
        decision: Decision | None = None,
        authority_digest: str | None = None,
        action_digest: str | None = None,
        approval_digest: str | None = None,
        effect_receipt_digest: str | None = None,
        attributes: dict[str, object] | None = None,
        occurred_at: datetime | None = None,
    ) -> EvidenceEvent:
        if self._sealed:
            raise EvidenceError("TRACE_ALREADY_SEALED")
        sequence = len(self._events) + 1
        if sequence == 1:
            if kind != EventKind.WORKFLOW_STARTED or parent_span_id is not None:
                raise EvidenceError("ROOT_EVENT_REQUIRED")
        else:
            known = {event.span_id for event in self._events}
            if parent_span_id not in known:
                raise EvidenceError("PARENT_SPAN_UNKNOWN")
        event_time = occurred_at or REFERENCE_TIME + timedelta(seconds=sequence)
        if parent_span_id is not None:
            parent = next(
                event for event in self._events if event.span_id == parent_span_id
            )
            if event_time < parent.occurred_at:
                raise EvidenceError("TRACE_TIME_ORDER_INVALID")
        safe_attributes = sanitize_attributes(self.policy, attributes or {})
        required = EVENT_REQUIRED_ATTRIBUTES.get(kind, frozenset())
        if not required.issubset(safe_attributes):
            raise EvidenceError("EVENT_EVIDENCE_INCOMPLETE")
        if (
            kind in {EventKind.POLICY_DECISION, EventKind.AUTHORIZATION}
            and decision is None
        ):
            raise EvidenceError("DECISION_REQUIRED")
        if (
            kind
            in {
                EventKind.APPROVAL,
                EventKind.TOOL_PROPOSED,
                EventKind.AUTHORIZATION,
                EventKind.EFFECT,
            }
            and action_digest is None
        ):
            raise EvidenceError("ACTION_DIGEST_REQUIRED")
        if kind == EventKind.APPROVAL and approval_digest is None:
            raise EvidenceError("APPROVAL_DIGEST_REQUIRED")
        if kind == EventKind.AUTHORIZATION and authority_digest is None:
            raise EvidenceError("AUTHORITY_DIGEST_REQUIRED")
        if kind == EventKind.EFFECT and effect_receipt_digest is None:
            raise EvidenceError("EFFECT_RECEIPT_REQUIRED")
        span_id = span_id_for(f"{self.trace_id}:{sequence}:{kind.value}")
        material = {
            "schema_version": self.policy.schema_version,
            "event_id": f"EV-{self.trace_id[:8]}-{sequence:03d}",
            "trace_id": self.trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "sequence": sequence,
            "occurred_at": event_time,
            "tenant_id": self.policy.tenant_id,
            "producer_id": self.producer_id,
            "service_name": self.service_name,
            "target_id": self.target_id,
            "target_version": self.target_version,
            "task_id": self.task_id,
            "kind": kind,
            "principal_ref": self.principal_ref,
            "agent_id": self.agent_id,
            "purpose_code": self.purpose_code,
            "risk_tier": risk_tier,
            "policy_version": self.policy.policy_version,
            "decision": decision,
            "authority_digest": authority_digest,
            "action_digest": action_digest,
            "approval_digest": approval_digest,
            "effect_receipt_digest": effect_receipt_digest,
            "attributes": safe_attributes,
            "previous_event_digest": (
                self._events[-1].event_digest if self._events else GENESIS_DIGEST
            ),
        }
        digest = stable_digest(material)
        event = EvidenceEvent(
            **material,
            event_digest=digest,
            event_signature=sign_digest(digest),
        )
        self._events.append(event)
        return event

    def seal(
        self, *, sealed_at: datetime = REFERENCE_TIME + timedelta(minutes=1)
    ) -> TraceEnvelope:
        if self._sealed:
            raise EvidenceError("TRACE_ALREADY_SEALED")
        if not self._events or self._events[-1].kind not in {
            EventKind.OUTCOME,
            EventKind.ERROR,
        }:
            raise EvidenceError("TERMINAL_EVIDENCE_REQUIRED")
        self._validate_consequence_bindings()
        self._sealed = True
        head = self._events[-1].event_digest
        material = {
            "trace_id": self.trace_id,
            "tenant_id": self.policy.tenant_id,
            "target_id": self.target_id,
            "target_version": self.target_version,
            "schema_version": self.policy.schema_version,
            "policy_version": self.policy.policy_version,
            "event_digests": [event.event_digest for event in self._events],
            "chain_head": head,
        }
        return TraceEnvelope(
            **{key: value for key, value in material.items() if key != "event_digests"},
            events=tuple(self._events),
            trace_digest=stable_digest(material),
            sealed_at=sealed_at,
        )

    def _validate_consequence_bindings(self) -> None:
        proposals = [e for e in self._events if e.kind == EventKind.TOOL_PROPOSED]
        approvals = [e for e in self._events if e.kind == EventKind.APPROVAL]
        authorizations = [e for e in self._events if e.kind == EventKind.AUTHORIZATION]
        effects = [e for e in self._events if e.kind == EventKind.EFFECT]
        if effects and not proposals:
            raise EvidenceError("EFFECT_WITHOUT_PROPOSAL")
        for effect in effects:
            if not any(
                proposal.action_digest == effect.action_digest for proposal in proposals
            ):
                raise EvidenceError("EFFECT_ACTION_UNBOUND")
            matching_auth = [
                event
                for event in authorizations
                if event.action_digest == effect.action_digest
                and event.decision == Decision.ALLOW
            ]
            if not matching_auth:
                raise EvidenceError("EFFECT_WITHOUT_ALLOW")
            if effect.risk_tier >= RiskTier.HIGH:
                matching_approval = [
                    event
                    for event in approvals
                    if event.action_digest == effect.action_digest
                    and event.approval_digest == matching_auth[-1].approval_digest
                ]
                if not matching_approval:
                    raise EvidenceError("HIGH_RISK_EFFECT_WITHOUT_BOUND_APPROVAL")
            if effect.attributes.get("effect_verified") is not True:
                raise EvidenceError("EFFECT_NOT_VERIFIED")
        denied = [e for e in authorizations if e.decision == Decision.DENY]
        if any(
            effect.action_digest == denial.action_digest
            for denial in denied
            for effect in effects
        ):
            raise EvidenceError("DENIED_ACTION_EFFECT_RECORDED")


class VerificationResult(FrozenModel):
    valid: bool
    reconstructable: bool
    completeness_rate: float
    reason_codes: tuple[str, ...]


def verify_trace(envelope: TraceEnvelope) -> VerificationResult:
    reasons: list[str] = []
    try:
        validated = TraceEnvelope.model_validate(envelope.model_dump(mode="python"))
    except ValidationError:
        return VerificationResult(
            valid=False,
            reconstructable=False,
            completeness_rate=0.0,
            reason_codes=("TRACE_INTEGRITY_INVALID",),
        )
    kinds = {event.kind for event in validated.events}
    maximum_risk = max(event.risk_tier for event in validated.events)
    requirements = {
        "ROOT": EventKind.WORKFLOW_STARTED in kinds,
        "TERMINAL": bool(kinds & {EventKind.OUTCOME, EventKind.ERROR}),
        "IDENTITY": all(event.principal_ref for event in validated.events),
        "PURPOSE": all(event.purpose_code for event in validated.events),
        "AUTHORITY": (
            maximum_risk < RiskTier.MEDIUM
            or any(event.authority_digest for event in validated.events)
        ),
        "POLICY": (maximum_risk < RiskTier.HIGH or EventKind.POLICY_DECISION in kinds),
        "APPROVAL": (
            maximum_risk < RiskTier.HIGH
            or not any(event.kind == EventKind.EFFECT for event in validated.events)
            or EventKind.APPROVAL in kinds
        ),
        "OUTCOME_RECEIPT": (
            not any(event.kind == EventKind.EFFECT for event in validated.events)
            or any(event.effect_receipt_digest for event in validated.events)
        ),
    }
    for name, passed in requirements.items():
        if not passed:
            reasons.append(f"MISSING_{name}")
    completeness = sum(requirements.values()) / len(requirements)
    return VerificationResult(
        valid=not reasons,
        reconstructable=not reasons,
        completeness_rate=completeness,
        reason_codes=tuple(reasons),
    )


class SamplingDecision(FrozenModel):
    retain: bool
    retention_class: RetentionClass
    reason_codes: tuple[str, ...]


def choose_retention(
    envelope: TraceEnvelope, *, routine_sample_rate: float = 0.1
) -> SamplingDecision:
    if not 0 <= routine_sample_rate <= 1:
        raise EvidenceError("SAMPLE_RATE_INVALID")
    events = envelope.events
    reasons: list[str] = []
    maximum_risk = max(event.risk_tier for event in events)
    decisions = {event.decision for event in events if event.decision is not None}
    anomalies = any(event.attributes.get("anomaly_codes") for event in events)
    if maximum_risk >= RiskTier.HIGH:
        reasons.append("HIGH_RISK")
    if decisions & {Decision.DENY, Decision.ESCALATE}:
        reasons.append("CONTROL_DECISION")
    if anomalies:
        reasons.append("ANOMALY")
    if EventKind.ERROR in {event.kind for event in events}:
        reasons.append("ERROR")
    if reasons:
        retention_class = (
            RetentionClass.SECURITY
            if anomalies or "ERROR" in reasons
            else RetentionClass.GOVERNANCE
        )
        return SamplingDecision(
            retain=True, retention_class=retention_class, reason_codes=tuple(reasons)
        )
    bucket = int(envelope.trace_id[:8], 16) / 0xFFFFFFFF
    return SamplingDecision(
        retain=bucket < routine_sample_rate,
        retention_class=RetentionClass.ROUTINE,
        reason_codes=("DETERMINISTIC_ROUTINE_SAMPLE",),
    )


class IngestReceipt(FrozenModel):
    trace_id: str
    trace_digest: str
    tenant_id: str
    ingested_by: str
    ingested_at: datetime
    prior_receipt_digest: str
    receipt_digest: str


class CustodyReceipt(FrozenModel):
    package_id: str
    tenant_id: str
    actor_id: str
    purpose_code: str
    package_digest: str
    transferred_at: datetime
    prior_custody_digest: str
    receipt_digest: str


class AccessReceipt(FrozenModel):
    trace_id: str
    tenant_id: str
    principal_ref: str
    purpose_code: str
    break_glass: bool
    reason: str | None
    accessed_at: datetime
    prior_access_digest: str
    receipt_digest: str


class EvidencePackage(FrozenModel):
    package_id: str
    tenant_id: str
    trace_id: str
    purpose_code: str
    target_id: str
    target_version: str
    schema_version: str
    policy_version: str
    trace_digest: str
    chain_head: str
    event_manifest: tuple[dict[str, object], ...]
    verification: VerificationResult
    package_digest: str
    package_signature: str


def verify_evidence_package(
    package: EvidencePackage, key: bytes = SYNTHETIC_INTEGRITY_KEY
) -> bool:
    material = package.model_dump(
        mode="python", exclude={"package_digest", "package_signature"}
    )
    digest = stable_digest(material)
    return hmac.compare_digest(package.package_digest, digest) and hmac.compare_digest(
        package.package_signature, sign_digest(digest, key)
    )


class DispositionPlan(FrozenModel):
    trace_id: str
    disposition: Disposition
    eligible_at: datetime | None
    reason_codes: tuple[str, ...]


class EvidenceStore:
    """In-memory append-only teaching store; no deletion method is exposed."""

    def __init__(
        self,
        tenant_id: str,
        policy: EvidencePolicy,
        integrity_key: bytes = SYNTHETIC_INTEGRITY_KEY,
    ):
        if tenant_id != policy.tenant_id:
            raise EvidenceError("STORE_POLICY_TENANT_MISMATCH")
        if len(integrity_key) < 16:
            raise ValueError("integrity key is too short")
        self.tenant_id = tenant_id
        self.policy = policy
        self._integrity_key = integrity_key
        self._traces: dict[str, TraceEnvelope] = {}
        self._ingest_receipts: list[IngestReceipt] = []
        self._custody_receipts: list[CustodyReceipt] = []
        self._access_receipts: list[AccessReceipt] = []
        self._legal_holds: set[str] = set()
        self._lock = RLock()

    @property
    def ingest_receipts(self) -> tuple[IngestReceipt, ...]:
        return tuple(self._ingest_receipts)

    @property
    def custody_receipts(self) -> tuple[CustodyReceipt, ...]:
        return tuple(self._custody_receipts)

    @property
    def access_receipts(self) -> tuple[AccessReceipt, ...]:
        return tuple(self._access_receipts)

    def _authorize(
        self, actor: AuthenticatedActor, roles: frozenset[str], now: datetime
    ) -> None:
        if now < actor.authenticated_at or now >= actor.valid_until:
            raise EvidenceError("ACTOR_SESSION_NOT_CURRENT")
        if actor.tenant_id != self.tenant_id:
            raise EvidenceError("ACTOR_TENANT_MISMATCH")
        if not actor.roles.intersection(roles):
            raise EvidenceError("ACTOR_NOT_AUTHORIZED")

    def ingest(
        self,
        actor: AuthenticatedActor,
        envelope: TraceEnvelope,
        *,
        now: datetime = REFERENCE_TIME + timedelta(minutes=2),
    ) -> IngestReceipt:
        self._authorize(actor, frozenset({"evidence_writer"}), now)
        if envelope.tenant_id != self.tenant_id:
            raise EvidenceError("TRACE_TENANT_MISMATCH")
        if (
            envelope.schema_version != self.policy.schema_version
            or envelope.policy_version != self.policy.policy_version
        ):
            raise EvidenceError("EVIDENCE_POLICY_BINDING_MISMATCH")
        producer_bindings = {
            (event.producer_id, event.service_name) for event in envelope.events
        }
        if producer_bindings != {(actor.principal_id, actor.service_name)}:
            raise EvidenceError("PRODUCER_BINDING_MISMATCH")
        if not all(
            hmac.compare_digest(
                event.event_signature,
                sign_digest(event.event_digest, self._integrity_key),
            )
            for event in envelope.events
        ):
            raise EvidenceError("EVENT_SIGNATURE_INVALID")
        verification = verify_trace(envelope)
        if not verification.valid:
            raise EvidenceError("TRACE_VERIFICATION_FAILED")
        with self._lock:
            existing = self._traces.get(envelope.trace_id)
            if existing is not None:
                if existing.trace_digest != envelope.trace_digest:
                    raise EvidenceError("TRACE_IMMUTABILITY_CONFLICT")
                return next(
                    receipt
                    for receipt in self._ingest_receipts
                    if receipt.trace_id == envelope.trace_id
                )
            prior = (
                self._ingest_receipts[-1].receipt_digest
                if self._ingest_receipts
                else GENESIS_DIGEST
            )
            material = {
                "trace_id": envelope.trace_id,
                "trace_digest": envelope.trace_digest,
                "tenant_id": self.tenant_id,
                "ingested_by": actor.principal_id,
                "ingested_at": now,
                "prior_receipt_digest": prior,
            }
            receipt = IngestReceipt(**material, receipt_digest=stable_digest(material))
            self._traces[envelope.trace_id] = envelope
            self._ingest_receipts.append(receipt)
            return receipt

    def get(
        self,
        actor: AuthenticatedActor,
        trace_id: str,
        *,
        purpose_code: str,
        break_glass: bool = False,
        reason: str | None = None,
        now: datetime = REFERENCE_TIME,
    ) -> TraceEnvelope:
        self._authorize(
            actor,
            frozenset(
                {
                    "evidence_reader",
                    "auditor",
                    "security_investigator",
                    "evidence_custodian",
                }
            ),
            now,
        )
        if not break_glass and purpose_code not in actor.purposes:
            raise EvidenceError("ACCESS_PURPOSE_NOT_AUTHORIZED")
        if break_glass and (
            "security_investigator" not in actor.roles
            or not reason
            or not reason.strip()
        ):
            raise EvidenceError("BREAK_GLASS_INVALID")
        try:
            envelope = self._traces[trace_id]
        except KeyError as exc:
            raise EvidenceError("TRACE_NOT_FOUND") from exc
        with self._lock:
            prior = (
                self._access_receipts[-1].receipt_digest
                if self._access_receipts
                else GENESIS_DIGEST
            )
            material = {
                "trace_id": trace_id,
                "tenant_id": self.tenant_id,
                "principal_ref": keyed_digest(actor.principal_id),
                "purpose_code": purpose_code,
                "break_glass": break_glass,
                "reason": reason,
                "accessed_at": now,
                "prior_access_digest": prior,
            }
            self._access_receipts.append(
                AccessReceipt(**material, receipt_digest=stable_digest(material))
            )
        return envelope

    def export_package(
        self,
        actor: AuthenticatedActor,
        trace_id: str,
        *,
        purpose_code: str,
        now: datetime = REFERENCE_TIME + timedelta(minutes=3),
    ) -> tuple[EvidencePackage, CustodyReceipt]:
        self._authorize(
            actor,
            frozenset({"auditor", "security_investigator", "evidence_custodian"}),
            now,
        )
        if not purpose_code.strip():
            raise EvidenceError("EXPORT_PURPOSE_REQUIRED")
        envelope = self.get(actor, trace_id, purpose_code=purpose_code, now=now)
        manifest = tuple(
            {
                "event_id": event.event_id,
                "kind": event.kind.value,
                "sequence": event.sequence,
                "event_digest": event.event_digest,
                "decision": event.decision.value if event.decision else None,
                "risk_tier": event.risk_tier.name,
            }
            for event in envelope.events
        )
        package_id = f"PKG-{stable_digest((trace_id, purpose_code))[:12].upper()}"
        package_material = {
            "package_id": package_id,
            "tenant_id": self.tenant_id,
            "trace_id": envelope.trace_id,
            "purpose_code": purpose_code,
            "target_id": envelope.target_id,
            "target_version": envelope.target_version,
            "schema_version": envelope.schema_version,
            "policy_version": envelope.policy_version,
            "trace_digest": envelope.trace_digest,
            "chain_head": envelope.chain_head,
            "event_manifest": manifest,
            "verification": verify_trace(envelope),
        }
        package = EvidencePackage(
            **package_material,
            package_digest=stable_digest(package_material),
            package_signature=sign_digest(
                stable_digest(package_material), self._integrity_key
            ),
        )
        with self._lock:
            prior = (
                self._custody_receipts[-1].receipt_digest
                if self._custody_receipts
                else GENESIS_DIGEST
            )
            receipt_material = {
                "package_id": package.package_id,
                "tenant_id": self.tenant_id,
                "actor_id": actor.principal_id,
                "purpose_code": purpose_code,
                "package_digest": package.package_digest,
                "transferred_at": now,
                "prior_custody_digest": prior,
            }
            receipt = CustodyReceipt(
                **receipt_material,
                receipt_digest=stable_digest(receipt_material),
            )
            self._custody_receipts.append(receipt)
        return package, receipt

    def place_legal_hold(
        self,
        actor: AuthenticatedActor,
        trace_id: str,
        *,
        now: datetime = REFERENCE_TIME,
    ) -> None:
        self._authorize(actor, frozenset({"evidence_custodian"}), now)
        if trace_id not in self._traces:
            raise EvidenceError("TRACE_NOT_FOUND")
        with self._lock:
            self._legal_holds.add(trace_id)

    def plan_disposition(
        self,
        actor: AuthenticatedActor,
        trace_id: str,
        *,
        now: datetime,
    ) -> DispositionPlan:
        self._authorize(actor, frozenset({"evidence_custodian"}), now)
        envelope = self.get(
            actor,
            trace_id,
            purpose_code="retention_administration",
            now=now,
        )
        if trace_id in self._legal_holds:
            return DispositionPlan(
                trace_id=trace_id,
                disposition=Disposition.RETAIN,
                eligible_at=None,
                reason_codes=("LEGAL_HOLD",),
            )
        retention = choose_retention(envelope, routine_sample_rate=1.0)
        days = {
            RetentionClass.ROUTINE: self.policy.routine_retention_days,
            RetentionClass.GOVERNANCE: self.policy.governance_retention_days,
            RetentionClass.SECURITY: self.policy.security_retention_days,
            RetentionClass.LEGAL_HOLD: self.policy.security_retention_days,
        }[retention.retention_class]
        eligible_at = envelope.sealed_at + timedelta(days=days)
        return DispositionPlan(
            trace_id=trace_id,
            disposition=(
                Disposition.ELIGIBLE_FOR_REVIEW
                if now >= eligible_at
                else Disposition.RETAIN
            ),
            eligible_at=eligible_at,
            reason_codes=(retention.retention_class.value.upper(),),
        )


class GovernanceMetrics(FrozenModel):
    trace_population: int
    reconstructable_traces: int
    high_risk_population: int
    verified_high_risk_outcomes: int
    decision_population: int
    allowed: int
    denied: int
    escalated: int
    near_miss_population: int
    reconstructability_rate: float
    verified_high_risk_outcome_rate: float


def compute_governance_metrics(envelopes: Iterable[TraceEnvelope]) -> GovernanceMetrics:
    traces = tuple(envelopes)
    if not traces:
        raise EvidenceError("EMPTY_METRIC_POPULATION")
    verifications = [verify_trace(trace) for trace in traces]
    high_risk = [
        trace
        for trace in traces
        if max(event.risk_tier for event in trace.events) >= RiskTier.HIGH
    ]
    verified_high_risk = [
        trace
        for trace in high_risk
        if any(
            event.kind == EventKind.EFFECT
            and event.attributes.get("effect_verified") is True
            and event.effect_receipt_digest
            for event in trace.events
        )
        or any(
            event.kind == EventKind.AUTHORIZATION and event.decision == Decision.DENY
            for event in trace.events
        )
    ]
    decisions = [
        event.decision
        for trace in traces
        for event in trace.events
        if event.kind == EventKind.AUTHORIZATION and event.decision is not None
    ]
    near_misses = sum(
        decision in {Decision.DENY, Decision.ESCALATE} for decision in decisions
    )
    return GovernanceMetrics(
        trace_population=len(traces),
        reconstructable_traces=sum(result.reconstructable for result in verifications),
        high_risk_population=len(high_risk),
        verified_high_risk_outcomes=len(verified_high_risk),
        decision_population=len(decisions),
        allowed=decisions.count(Decision.ALLOW),
        denied=decisions.count(Decision.DENY),
        escalated=decisions.count(Decision.ESCALATE),
        near_miss_population=near_misses,
        reconstructability_rate=sum(result.reconstructable for result in verifications)
        / len(traces),
        verified_high_risk_outcome_rate=(
            len(verified_high_risk) / len(high_risk) if high_risk else 1.0
        ),
    )


class AnomalyAssessment(FrozenModel):
    signal_only: bool = True
    score: float
    reason_codes: tuple[str, ...]


def assess_anomalies(
    envelope: TraceEnvelope,
    *,
    known_tools: frozenset[str] = frozenset({"vendor.read", "po.create"}),
    maximum_delegation_depth: int = 2,
) -> AnomalyAssessment:
    reasons: set[str] = set()
    tools = {
        str(event.attributes["tool_id"])
        for event in envelope.events
        if "tool_id" in event.attributes
    }
    if tools - known_tools:
        reasons.add("NEW_TOOL")
    delegation_count = sum(
        event.kind == EventKind.DELEGATION for event in envelope.events
    )
    if delegation_count > maximum_delegation_depth:
        reasons.add("DELEGATION_DEPTH")
    denial_count = sum(
        event.kind == EventKind.AUTHORIZATION and event.decision == Decision.DENY
        for event in envelope.events
    )
    if denial_count >= 3:
        reasons.add("REPEATED_DENIAL")
    if any(
        event.attributes.get("amount_band") == "VERY_HIGH" for event in envelope.events
    ):
        reasons.add("VALUE_OUTLIER")
    ordered = tuple(sorted(reasons))
    return AnomalyAssessment(score=min(1.0, len(ordered) * 0.25), reason_codes=ordered)


def sample_actor(
    *, roles: frozenset[str] = frozenset({"evidence_writer"}), **changes: object
) -> AuthenticatedActor:
    values: dict[str, object] = {
        "principal_id": "workload:procurement-observer",
        "tenant_id": "tenant-acme",
        "service_name": "procurement-agent",
        "roles": roles,
        "authenticated_at": REFERENCE_TIME - timedelta(minutes=5),
        "valid_until": REFERENCE_TIME + timedelta(days=800),
    }
    values.update(changes)
    return AuthenticatedActor(**values)


def sample_policy(**changes: object) -> EvidencePolicy:
    values: dict[str, object] = {"tenant_id": "tenant-acme"}
    values.update(changes)
    return EvidencePolicy(**values)


def _common_builder(seed: str, policy: EvidencePolicy | None = None) -> TraceBuilder:
    return TraceBuilder(
        policy or sample_policy(),
        trace_seed=seed,
        task_id=f"TASK-{seed.upper()}",
        principal_ref=keyed_digest("employee:synthetic-alex"),
        agent_id="procurement-agent:v13",
        purpose_code="approved_procurement",
    )


def build_high_risk_purchase_trace(
    policy: EvidencePolicy | None = None,
) -> TraceEnvelope:
    builder = _common_builder("high-risk-purchase", policy)
    authority = stable_digest(
        {"grant": "DG-13", "scope": ["po.create"], "limit": 15000}
    )
    action = stable_digest(
        {"tool": "po.create", "vendor": "V-42", "amount": 12000, "currency": "CAD"}
    )
    approval = stable_digest({"action": action, "approver": "role:procurement-manager"})
    receipt = stable_digest(
        {"action": action, "transaction": "PO-SIM-1042", "status": "committed"}
    )
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.HIGH)
    builder.emit(
        EventKind.RETRIEVAL,
        risk_tier=RiskTier.MEDIUM,
        parent_span_id=root.span_id,
        attributes={
            "source_ids": ["kb:vendor-42:v7", "policy:procurement:v13"],
            "source_digests": [
                stable_digest("vendor-42-v7"),
                stable_digest("policy-v13"),
            ],
            "trust_labels": ["MEDIUM", "HIGH"],
            "knowledge_base_version": "kb-2026-09-27",
        },
    )
    policy_event = builder.emit(
        EventKind.POLICY_DECISION,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        decision=Decision.ESCALATE,
        authority_digest=authority,
        attributes={
            "decision_id": "PD-1042",
            "reason_codes": ["HIGH_VALUE", "NEW_VENDOR"],
            "risk_score_band": "HIGH",
        },
    )
    builder.emit(
        EventKind.APPROVAL,
        risk_tier=RiskTier.HIGH,
        parent_span_id=policy_event.span_id,
        decision=Decision.ALLOW,
        action_digest=action,
        approval_digest=approval,
        attributes={"approval_id": "APR-1042", "approver_role": "procurement-manager"},
    )
    proposal = builder.emit(
        EventKind.TOOL_PROPOSED,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        action_digest=action,
        attributes={
            "tool_id": "po.create",
            "tool_version": "2.1",
            "action_type": "purchase_order",
            "amount_band": "HIGH",
            "currency": "CAD",
        },
    )
    builder.emit(
        EventKind.AUTHORIZATION,
        risk_tier=RiskTier.HIGH,
        parent_span_id=proposal.span_id,
        decision=Decision.ALLOW,
        authority_digest=authority,
        action_digest=action,
        approval_digest=approval,
        attributes={"decision_id": "AUTHZ-1042", "reason_codes": ["APPROVAL_BOUND"]},
    )
    builder.emit(
        EventKind.EFFECT,
        risk_tier=RiskTier.HIGH,
        parent_span_id=proposal.span_id,
        action_digest=action,
        effect_receipt_digest=receipt,
        attributes={
            "effect_status": "COMMITTED",
            "effect_verified": True,
            "external_transaction_ref": "PO-SIM-1042",
            "reversible": True,
        },
    )
    builder.emit(
        EventKind.OUTCOME,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        effect_receipt_digest=receipt,
        attributes={"outcome_code": "PURCHASE_ORDER_VERIFIED"},
    )
    return builder.seal()


def build_denied_near_miss_trace(policy: EvidencePolicy | None = None) -> TraceEnvelope:
    builder = _common_builder("denied-egress", policy)
    authority = stable_digest({"grant": "DG-13", "scope": ["vendor.read"]})
    action = stable_digest({"tool": "http.post", "destination": "external.invalid"})
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.CRITICAL)
    decision = builder.emit(
        EventKind.POLICY_DECISION,
        risk_tier=RiskTier.CRITICAL,
        parent_span_id=root.span_id,
        decision=Decision.DENY,
        authority_digest=authority,
        attributes={
            "decision_id": "PD-EGRESS-1",
            "reason_codes": ["DESTINATION_DENIED", "SCOPE_EXCEEDED"],
            "anomaly_codes": ["NEW_DESTINATION"],
        },
    )
    proposal = builder.emit(
        EventKind.TOOL_PROPOSED,
        risk_tier=RiskTier.CRITICAL,
        parent_span_id=decision.span_id,
        action_digest=action,
        attributes={
            "tool_id": "http.post",
            "tool_version": "1.0",
            "action_type": "external_egress",
        },
    )
    builder.emit(
        EventKind.AUTHORIZATION,
        risk_tier=RiskTier.CRITICAL,
        parent_span_id=proposal.span_id,
        decision=Decision.DENY,
        authority_digest=authority,
        action_digest=action,
        attributes={
            "decision_id": "AUTHZ-EGRESS-1",
            "reason_codes": ["TOOL_NOT_DELEGATED"],
        },
    )
    builder.emit(
        EventKind.OUTCOME,
        risk_tier=RiskTier.CRITICAL,
        parent_span_id=root.span_id,
        attributes={"outcome_code": "EGRESS_PREVENTED"},
    )
    return builder.seal()


def build_routine_read_trace(policy: EvidencePolicy | None = None) -> TraceEnvelope:
    builder = _common_builder("routine-read", policy)
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.LOW)
    builder.emit(
        EventKind.RETRIEVAL,
        risk_tier=RiskTier.LOW,
        parent_span_id=root.span_id,
        attributes={
            "source_ids": ["kb:vendor-42:v7"],
            "source_digests": [stable_digest("vendor-42-v7")],
            "knowledge_base_version": "kb-2026-09-27",
        },
    )
    builder.emit(
        EventKind.OUTCOME,
        risk_tier=RiskTier.LOW,
        parent_span_id=root.span_id,
        attributes={"outcome_code": "VENDOR_READ_COMPLETE"},
    )
    return builder.seal()


class ToolManifest(FrozenModel):
    name: str
    package: str
    installed_version: str | None
    interoperability: str
    governance_boundary: str
    current_status: str


def _installed(package: str) -> str | None:
    try:
        return package_version(package)
    except PackageNotFoundError:
        return None


def build_tool_manifests() -> dict[str, ToolManifest]:
    return {
        "opentelemetry": ToolManifest(
            name="OpenTelemetry",
            package="opentelemetry-api/sdk>=1.30",
            installed_version=_installed("opentelemetry-sdk"),
            interoperability="W3C Trace Context and OTLP traces, metrics, and logs",
            governance_boundary="Transport and correlation do not establish authorization or evidence integrity.",
            current_status="GenAI conventions have moved to their dedicated repository; pin schema versions.",
        ),
        "openinference_phoenix": ToolManifest(
            name="OpenInference + Arize Phoenix",
            package="openinference instrumentation / arize-phoenix",
            installed_version=_installed("arize-phoenix"),
            interoperability="AI-specific semantic conventions on OpenTelemetry/OTLP",
            governance_boundary="Verbose prompts, outputs, tool arguments, and evaluations need explicit masking.",
            current_status="Open-source tracing, evaluation, datasets, and experiments.",
        ),
        "langsmith": ToolManifest(
            name="LangSmith",
            package="langsmith",
            installed_version=_installed("langsmith"),
            interoperability="LangChain/LangGraph tracing with OpenTelemetry integration options",
            governance_boundary="A vendor trace schema is not an organization evidence policy.",
            current_status="Tracing, evaluation, feedback, and operational monitoring.",
        ),
        "langfuse": ToolManifest(
            name="Langfuse",
            package="langfuse v4",
            installed_version=_installed("langfuse"),
            interoperability="OpenTelemetry-native Python and JavaScript/TypeScript SDKs",
            governance_boundary="Background delivery, access, retention, and content capture need review.",
            current_status="Open-source tracing, prompt management, evaluation, and datasets.",
        ),
        "openai_agents": ToolManifest(
            name="OpenAI Agents SDK tracing",
            package="openai-agents",
            installed_version=_installed("openai-agents"),
            interoperability="Native agent, generation, tool, guardrail, handoff, and custom spans",
            governance_boundary="Sensitive capture defaults and exporter composition must be configured deliberately.",
            current_status="Supports custom processors, replacement exporters, and explicit flush.",
        ),
    }


def build_otel_artifacts(envelope: TraceEnvelope) -> dict[str, object]:
    """Create real in-memory OpenTelemetry spans without network export."""

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": "course-13-procurement-agent",
                "service.version": envelope.target_version,
                "deployment.environment.name": "offline-lab",
                "governance.schema.version": envelope.schema_version,
            }
        )
    )
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("course13.governance-evidence", "1.0")
    spans_by_evidence_id: dict[str, Any] = {}
    for event in envelope.events:
        parent_context = (
            trace.set_span_in_context(spans_by_evidence_id[event.parent_span_id])
            if event.parent_span_id is not None
            else None
        )
        span = tracer.start_span(
            f"governance.{event.kind.value}", context=parent_context
        )
        span.set_attribute("governance.trace.digest", envelope.trace_digest)
        span.set_attribute("governance.tenant.ref", stable_digest(envelope.tenant_id))
        span.set_attribute("governance.policy.version", envelope.policy_version)
        span.set_attribute("governance.event.id", event.event_id)
        span.set_attribute("governance.event.digest", event.event_digest)
        span.set_attribute("governance.evidence.span_id", event.span_id)
        span.set_attribute("governance.risk.tier", event.risk_tier.name)
        if event.decision:
            span.set_attribute("governance.decision", event.decision.value)
        spans_by_evidence_id[event.span_id] = span
        span.end()
    provider.force_flush()
    return {
        "provider": provider,
        "exporter": exporter,
        "spans": exporter.get_finished_spans(),
    }


def build_openai_trace_artifacts(envelope: TraceEnvelope) -> dict[str, object]:
    """Construct real Agents SDK trace/config objects without starting or exporting."""

    from agents import RunConfig, custom_span, trace

    safe_metadata = {
        "trace_digest": envelope.trace_digest,
        "target_version": envelope.target_version,
        "schema_version": envelope.schema_version,
    }
    run_config = RunConfig(
        trace_include_sensitive_data=False,
        workflow_name="Course 13 governed procurement",
        trace_id=f"trace_{envelope.trace_id}",
        group_id=stable_digest(envelope.events[0].task_id)[:16],
        trace_metadata=safe_metadata,
    )
    trace_object = trace(
        run_config.workflow_name,
        trace_id=run_config.trace_id,
        group_id=run_config.group_id,
        metadata=safe_metadata,
    )
    evidence_span = custom_span(
        "governance_evidence",
        data={
            "trace_digest": envelope.trace_digest,
            "event_count": len(envelope.events),
        },
        parent=trace_object,
    )
    return {"run_config": run_config, "trace": trace_object, "span": evidence_span}


def build_collector_config() -> dict[str, object]:
    """Return a non-executing, secure-by-default Collector teaching manifest."""

    return {
        "receivers": {
            "otlp": {
                "protocols": {
                    "grpc": {"endpoint": "127.0.0.1:4317"},
                    "http": {"endpoint": "127.0.0.1:4318"},
                }
            }
        },
        "processors": {
            "memory_limiter": {"limit_mib": 256, "spike_limit_mib": 64},
            "attributes/governance": {
                "actions": [
                    {"key": "gen_ai.input.messages", "action": "delete"},
                    {"key": "gen_ai.output.messages", "action": "delete"},
                ]
            },
            "tail_sampling/governance": {
                "decision_wait": "10s",
                "policies": [
                    {
                        "name": "errors",
                        "type": "status_code",
                        "status_code": {"status_codes": ["ERROR"]},
                    },
                    {
                        "name": "deny-or-escalate",
                        "type": "string_attribute",
                        "string_attribute": {
                            "key": "governance.decision",
                            "values": ["deny", "escalate"],
                        },
                    },
                    {
                        "name": "high-risk",
                        "type": "string_attribute",
                        "string_attribute": {
                            "key": "governance.risk.tier",
                            "values": ["HIGH", "CRITICAL"],
                        },
                    },
                    {
                        "name": "routine-sample",
                        "type": "probabilistic",
                        "probabilistic": {"sampling_percentage": 10},
                    },
                ],
            },
            "batch": {"send_batch_size": 512, "timeout": "5s"},
        },
        "exporters": {
            "otlp/evidence": {
                "endpoint": "evidence-collector.internal.example:4317",
                "tls": {"insecure": False, "ca_file": "/run/secrets/evidence-ca.pem"},
                "sending_queue": {"enabled": True, "queue_size": 2048},
                "retry_on_failure": {"enabled": True},
            }
        },
        "service": {
            "pipelines": {
                "traces/governance": {
                    "receivers": ["otlp"],
                    "processors": [
                        "memory_limiter",
                        "attributes/governance",
                        "tail_sampling/governance",
                        "batch",
                    ],
                    "exporters": ["otlp/evidence"],
                }
            }
        },
    }
