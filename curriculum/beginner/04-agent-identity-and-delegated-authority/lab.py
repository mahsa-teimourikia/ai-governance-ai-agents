"""Deterministic identity and delegated-authority lab for Course 4.

The module models an enterprise procurement agent without external services or
credentials.  The signed JWTs are *teaching artifacts*, not an OAuth server or
production token profile.  Trusted application code binds authenticated human,
logical-agent, and attested-workload identities; a policy enforcement point then
validates and atomically consumes narrow task authority before an effect.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from threading import Lock
from typing import Iterable

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel, ConfigDict, Field, model_validator


REFERENCE_TIME = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
ISSUER = "https://training-sts.example.invalid"
POLICY_VERSION = "delegation-policy-2026-09"
TRUST_DOMAIN = "example.com"
MAX_GRANT_LIFETIME = timedelta(minutes=30)
TEST_KEY_ID = "course04-public-test-key-1"

# Public, deterministic test material: never use this key outside this lab.
_TEST_PRIVATE_BYTES = hashlib.sha256(b"course-04-public-test-key").digest()
_TEST_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(_TEST_PRIVATE_BYTES)
TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def stable_digest(value: object) -> str:
    """Return a stable SHA-256 digest for a model or JSON-compatible value."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")

    def canonicalize(item: object) -> object:
        if isinstance(item, BaseModel):
            return canonicalize(item.model_dump(mode="python"))
        if isinstance(item, dict):
            return {str(key): canonicalize(child) for key, child in item.items()}
        if isinstance(item, (set, frozenset)):
            normalized = [canonicalize(child) for child in item]
            return sorted(
                normalized,
                key=lambda child: json.dumps(
                    child, sort_keys=True, separators=(",", ":"), ensure_ascii=True
                ),
            )
        if isinstance(item, (list, tuple)):
            return [canonicalize(child) for child in item]
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, Decimal):
            return str(item)
        if isinstance(item, Enum):
            return item.value
        return item

    payload = json.dumps(
        canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def token_digest(token: str) -> str:
    """Digest a serialized token without retaining the bearer credential."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PrincipalKind(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    WORKLOAD = "workload"


class Principal(FrozenModel):
    principal_id: str = Field(min_length=3)
    kind: PrincipalKind
    tenant_id: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    version: str | None = None
    active: bool = True

    @model_validator(mode="after")
    def agent_version_is_explicit(self) -> "Principal":
        if self.kind is PrincipalKind.AGENT and not self.version:
            raise ValueError("logical agents require an explicit version")
        return self


class AgentWorkloadBinding(FrozenModel):
    actor_id: str
    workload_id: str
    required_selectors: frozenset[str] = Field(min_length=1)


class IdentityDirectory(FrozenModel):
    principals: tuple[Principal, ...]
    bindings: tuple[AgentWorkloadBinding, ...]

    @model_validator(mode="after")
    def directory_is_consistent(self) -> "IdentityDirectory":
        identifiers = [item.principal_id for item in self.principals]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("principal identifiers must be unique")
        known = set(identifiers)
        by_id = {item.principal_id: item for item in self.principals}
        pairs: set[tuple[str, str]] = set()
        for binding in self.bindings:
            if binding.actor_id not in known or binding.workload_id not in known:
                raise ValueError("bindings must reference known principals")
            if by_id[binding.actor_id].kind is not PrincipalKind.AGENT:
                raise ValueError("binding actor must be a logical agent")
            if by_id[binding.workload_id].kind is not PrincipalKind.WORKLOAD:
                raise ValueError("binding workload must be a workload principal")
            if by_id[binding.actor_id].tenant_id != by_id[binding.workload_id].tenant_id:
                raise ValueError("binding principals must share a tenant")
            pair = (binding.actor_id, binding.workload_id)
            if pair in pairs:
                raise ValueError("agent/workload bindings must be unique")
            pairs.add(pair)
        return self

    def principal(self, principal_id: str, kind: PrincipalKind) -> Principal:
        matches = [item for item in self.principals if item.principal_id == principal_id]
        if len(matches) != 1 or matches[0].kind is not kind or not matches[0].active:
            raise ValueError(f"unknown_or_inactive_{kind.value}")
        return matches[0]

    def binding(self, actor_id: str, workload_id: str) -> AgentWorkloadBinding:
        matches = [
            item
            for item in self.bindings
            if item.actor_id == actor_id and item.workload_id == workload_id
        ]
        if len(matches) != 1:
            raise ValueError("agent_workload_binding_not_found")
        return matches[0]


class AuthenticatedHumanSession(FrozenModel):
    subject_id: str
    tenant_id: str
    session_id: str
    authenticated_at: datetime
    expires_at: datetime
    authentication_methods: frozenset[str]

    @model_validator(mode="after")
    def session_has_strong_authentication(self) -> "AuthenticatedHumanSession":
        if not self.authentication_methods:
            raise ValueError("human session requires authentication evidence")
        if self.expires_at <= self.authenticated_at:
            raise ValueError("human session must have a positive lifetime")
        return self


class WorkloadAttestation(FrozenModel):
    workload_id: str = Field(pattern=r"^spiffe://")
    trust_domain: str
    selectors: frozenset[str]
    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def attestation_interval_is_valid(self) -> "WorkloadAttestation":
        if self.expires_at <= self.issued_at:
            raise ValueError("workload attestation must have a positive lifetime")
        return self


class TrustedTaskContext(FrozenModel):
    subject_id: str
    actor_id: str
    actor_version: str
    workload_id: str
    tenant_id: str
    task_id: str
    session_id: str
    bound_at: datetime
    valid_until: datetime


def bind_trusted_context(
    session: AuthenticatedHumanSession,
    actor_id: str,
    workload: WorkloadAttestation,
    task_id: str,
    directory: IdentityDirectory,
    *,
    now: datetime,
) -> TrustedTaskContext:
    """Bind identities from authenticated application state, never prompt text."""

    human = directory.principal(session.subject_id, PrincipalKind.HUMAN)
    actor = directory.principal(actor_id, PrincipalKind.AGENT)
    registered_workload = directory.principal(workload.workload_id, PrincipalKind.WORKLOAD)
    binding = directory.binding(actor.principal_id, registered_workload.principal_id)
    if len({human.tenant_id, actor.tenant_id, registered_workload.tenant_id, session.tenant_id}) != 1:
        raise ValueError("cross_tenant_identity_chain")
    if not (session.authenticated_at <= now < session.expires_at):
        raise ValueError("human_session_not_current")
    if workload.trust_domain != TRUST_DOMAIN:
        raise ValueError("untrusted_workload_domain")
    if not workload.workload_id.startswith(f"spiffe://{workload.trust_domain}/"):
        raise ValueError("spiffe_id_trust_domain_mismatch")
    if not (workload.issued_at <= now < workload.expires_at):
        raise ValueError("workload_attestation_not_current")
    if not binding.required_selectors.issubset(workload.selectors):
        raise ValueError("workload_selectors_do_not_match_registration")
    return TrustedTaskContext(
        subject_id=human.principal_id,
        actor_id=actor.principal_id,
        actor_version=actor.version or "",
        workload_id=registered_workload.principal_id,
        tenant_id=human.tenant_id,
        task_id=task_id,
        session_id=session.session_id,
        bound_at=now,
        valid_until=min(session.expires_at, workload.expires_at),
    )


class DelegationConstraints(FrozenModel):
    max_amount_cents: int = Field(ge=0)
    allowed_vendor_ids: frozenset[str]
    max_calls: int = Field(ge=1, le=100)


class TaskIntent(FrozenModel):
    intent_id: str
    task_id: str
    tenant_id: str
    description: str = Field(min_length=1)
    approved_actions: frozenset[str]
    approved_resources: frozenset[str]
    constraints: DelegationConstraints
    approved_by: str
    approved_at: datetime

    @model_validator(mode="after")
    def intent_is_bounded(self) -> "TaskIntent":
        if not self.approved_actions or not self.approved_resources:
            raise ValueError("intent requires explicit actions and resources")
        return self


class DelegationGrant(FrozenModel):
    grant_id: str = Field(pattern=r"^GRANT-[A-Z0-9-]+$")
    subject_id: str
    actor_id: str
    actor_version: str
    workload_id: str
    tenant_id: str
    task_id: str
    audience: str = Field(pattern=r"^https://")
    actions: frozenset[str]
    resources: frozenset[str]
    constraints: DelegationConstraints
    issued_at: datetime
    expires_at: datetime
    intent_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: str
    parent_grant_id: str | None = None
    depth: int = Field(ge=0)
    max_depth: int = Field(ge=0, le=5)

    @model_validator(mode="after")
    def grant_is_bounded(self) -> "DelegationGrant":
        if not self.actions or not self.resources:
            raise ValueError("grant requires explicit actions and resources")
        if self.expires_at <= self.issued_at:
            raise ValueError("grant expiry must follow issuance")
        if self.expires_at - self.issued_at > MAX_GRANT_LIFETIME:
            raise ValueError("grant lifetime exceeds training policy")
        if self.depth > self.max_depth:
            raise ValueError("delegation depth exceeds maximum")
        if self.depth == 0 and self.parent_grant_id is not None:
            raise ValueError("root grant cannot have a parent")
        if self.depth > 0 and self.parent_grant_id is None:
            raise ValueError("child grant requires a parent")
        return self


def build_root_grant(
    context: TrustedTaskContext,
    intent: TaskIntent,
    *,
    grant_id: str,
    audience: str,
    actions: Iterable[str],
    resources: Iterable[str],
    constraints: DelegationConstraints,
    expires_at: datetime,
    max_depth: int = 1,
) -> DelegationGrant:
    actions = frozenset(actions)
    resources = frozenset(resources)
    if context.task_id != intent.task_id or context.tenant_id != intent.tenant_id:
        raise ValueError("intent_context_binding_mismatch")
    if context.subject_id != intent.approved_by:
        raise ValueError("authenticated_subject_did_not_approve_intent")
    if intent.approved_at > context.bound_at:
        raise ValueError("intent_approval_is_future_dated")
    if not actions.issubset(intent.approved_actions):
        raise ValueError("requested_actions_exceed_intent")
    if not resources.issubset(intent.approved_resources):
        raise ValueError("requested_resources_exceed_intent")
    if constraints.max_amount_cents > intent.constraints.max_amount_cents:
        raise ValueError("requested_amount_exceeds_intent")
    if not constraints.allowed_vendor_ids.issubset(intent.constraints.allowed_vendor_ids):
        raise ValueError("requested_vendors_exceed_intent")
    if constraints.max_calls > intent.constraints.max_calls:
        raise ValueError("requested_calls_exceed_intent")
    return DelegationGrant(
        grant_id=grant_id,
        subject_id=context.subject_id,
        actor_id=context.actor_id,
        actor_version=context.actor_version,
        workload_id=context.workload_id,
        tenant_id=context.tenant_id,
        task_id=context.task_id,
        audience=audience,
        actions=actions,
        resources=resources,
        constraints=constraints,
        issued_at=context.bound_at,
        expires_at=expires_at,
        intent_digest=stable_digest(intent),
        policy_version=POLICY_VERSION,
        depth=0,
        max_depth=max_depth,
    )


def _grant_claims(grant: DelegationGrant) -> dict[str, object]:
    return {
        "iss": ISSUER,
        "sub": grant.subject_id,
        "act": {"sub": grant.actor_id, "version": grant.actor_version},
        "workload": grant.workload_id,
        "tenant": grant.tenant_id,
        "task": grant.task_id,
        "aud": grant.audience,
        "iat": int(grant.issued_at.timestamp()),
        "exp": int(grant.expires_at.timestamp()),
        "jti": grant.grant_id,
        "authorization_details": [{
            "type": "agent_task",
            "actions": sorted(grant.actions),
            "resources": sorted(grant.resources),
            "constraints": grant.constraints.model_dump(mode="json"),
        }],
        "intent_digest": grant.intent_digest,
        "policy_version": grant.policy_version,
        "parent_grant_id": grant.parent_grant_id,
        "depth": grant.depth,
        "max_depth": grant.max_depth,
    }


def issue_training_token(grant: DelegationGrant) -> str:
    """Sign a deterministic teaching JWT with a public fixed test key."""

    return jwt.encode(
        _grant_claims(grant),
        _TEST_PRIVATE_KEY,
        algorithm="EdDSA",
        headers={"alg": "EdDSA", "kid": TEST_KEY_ID, "typ": "agent-delegation+jwt"},
    )


def verify_training_token(token: str, *, audience: str, now: datetime) -> DelegationGrant:
    """Verify algorithm, key, issuer, audience, time, and exact grant structure."""

    header = jwt.get_unverified_header(token)
    if header != {"alg": "EdDSA", "kid": TEST_KEY_ID, "typ": "agent-delegation+jwt"}:
        raise ValueError("unexpected_token_header")
    try:
        claims = jwt.decode(
            token,
            TEST_PUBLIC_KEY,
            algorithms=["EdDSA"],
            audience=audience,
            issuer=ISSUER,
            options={
                "verify_exp": False,
                "verify_iat": False,
                "require": [
                    "iss",
                    "sub",
                    "act",
                    "workload",
                    "tenant",
                    "task",
                    "aud",
                    "iat",
                    "exp",
                    "jti",
                    "authorization_details",
                    "intent_digest",
                    "policy_version",
                    "depth",
                    "max_depth",
                ],
            },
        )
    except jwt.PyJWTError as exc:
        raise ValueError(f"token_validation_failed:{type(exc).__name__}") from exc
    try:
        issued_at = datetime.fromtimestamp(claims["iat"], tz=timezone.utc)
        expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid_token_times") from exc
    if now < issued_at:
        raise ValueError("token_not_yet_valid")
    if now >= expires_at:
        raise ValueError("token_expired")
    details = claims.get("authorization_details")
    if (
        not isinstance(details, list)
        or len(details) != 1
        or not isinstance(details[0], dict)
        or details[0].get("type") != "agent_task"
    ):
        raise ValueError("invalid_authorization_details")
    detail = details[0]
    try:
        return DelegationGrant(
            grant_id=claims["jti"],
            subject_id=claims["sub"],
            actor_id=claims["act"]["sub"],
            actor_version=claims["act"]["version"],
            workload_id=claims["workload"],
            tenant_id=claims["tenant"],
            task_id=claims["task"],
            audience=claims["aud"],
            actions=frozenset(detail["actions"]),
            resources=frozenset(detail["resources"]),
            constraints=DelegationConstraints(**detail["constraints"]),
            issued_at=issued_at,
            expires_at=expires_at,
            intent_digest=claims["intent_digest"],
            policy_version=claims["policy_version"],
            parent_grant_id=claims.get("parent_grant_id"),
            depth=claims["depth"],
            max_depth=claims["max_depth"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid_token_claims") from exc


ALLOWED_AUDIENCE_TRANSITIONS: dict[str, frozenset[str]] = {
    "https://api.example.com/procurement": frozenset({"https://api.example.com/vendors"}),
}


class AuthorizationRequest(FrozenModel):
    operation_id: str = Field(pattern=r"^OP-[A-Z0-9-]+$")
    audience: str = Field(pattern=r"^https://")
    action: str
    resource: str
    amount_cents: int = Field(ge=0)
    vendor_id: str | None = None


class DecisionOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class AuthorizationDecision(FrozenModel):
    decision_id: str
    outcome: DecisionOutcome
    reason_codes: tuple[str, ...]
    operation_id: str
    request_digest: str
    grant_id: str | None
    token_digest: str
    policy_version: str
    ledger_version: int
    remaining_calls: int
    replayed_decision: bool = False


class AuditEvent(FrozenModel):
    decision_id: str
    operation_id: str
    grant_id: str | None
    parent_grant_id: str | None
    subject_id: str
    actor_id: str
    actor_version: str
    workload_id: str
    tenant_id: str
    task_id: str
    audience: str
    action: str
    resource: str
    amount_cents: int
    vendor_id: str | None
    intent_digest: str | None
    constraints_digest: str | None
    grant_expires_at: datetime | None
    request_digest: str
    token_digest: str
    outcome: DecisionOutcome
    reason_codes: tuple[str, ...]
    policy_version: str
    observed_at: datetime


def _decision_id(grant_id: str | None, request: AuthorizationRequest) -> str:
    digest = stable_digest({"grant_id": grant_id, "request": request.model_dump(mode="json"), "policy": POLICY_VERSION})
    return f"DEC-{digest[:16].upper()}"


class GrantLedger:
    """Thread-safe training ledger for registration, revocation, and consumption."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._grants: dict[str, DelegationGrant] = {}
        self._revoked: set[str] = set()
        self._closed_tasks: set[str] = set()
        self._call_counts: dict[str, int] = {}
        self._delegated_calls: dict[str, int] = {}
        self._operations: dict[tuple[str, str], tuple[str, AuthorizationDecision]] = {}
        self._audit: list[AuditEvent] = []
        self._version = 0

    @property
    def audit_events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._audit)

    def register(self, grant: DelegationGrant) -> None:
        with self._lock:
            if grant.grant_id in self._grants:
                raise ValueError("duplicate_grant_id")
            if grant.parent_grant_id:
                parent = self._grants.get(grant.parent_grant_id)
                if parent is None:
                    raise ValueError("unknown_parent_grant")
                committed = self._call_counts[parent.grant_id] + self._delegated_calls[parent.grant_id]
                available = parent.constraints.max_calls - committed
                if grant.constraints.max_calls > available:
                    raise ValueError("child_calls_exceed_parent_remaining_budget")
                self._delegated_calls[parent.grant_id] += grant.constraints.max_calls
            self._grants[grant.grant_id] = grant
            self._call_counts[grant.grant_id] = 0
            self._delegated_calls[grant.grant_id] = 0
            self._version += 1

    def _remaining_calls(self, grant: DelegationGrant) -> int:
        committed = self._call_counts.get(grant.grant_id, 0) + self._delegated_calls.get(
            grant.grant_id, 0
        )
        return max(grant.constraints.max_calls - committed, 0)

    def revoke(self, grant_id: str) -> None:
        with self._lock:
            if grant_id not in self._grants:
                raise ValueError("unknown_grant")
            self._revoked.add(grant_id)
            self._version += 1

    def close_task(self, task_id: str) -> None:
        with self._lock:
            self._closed_tasks.add(task_id)
            self._version += 1

    def _inactive_reason(self, grant: DelegationGrant) -> str | None:
        current: DelegationGrant | None = grant
        seen: set[str] = set()
        while current is not None:
            if current.grant_id in seen:
                return "delegation_cycle_detected"
            seen.add(current.grant_id)
            if current.grant_id in self._revoked:
                return "grant_or_ancestor_revoked"
            current = self._grants.get(current.parent_grant_id) if current.parent_grant_id else None
        if grant.task_id in self._closed_tasks:
            return "task_closed"
        return None

    def assert_active(self, grant: DelegationGrant) -> None:
        with self._lock:
            registered = self._grants.get(grant.grant_id)
            if registered is None or stable_digest(registered) != stable_digest(grant):
                raise ValueError("grant_not_registered_exactly")
            reason = self._inactive_reason(grant)
            if reason:
                raise ValueError(reason)

    def record_prevalidation_denial(
        self,
        request: AuthorizationRequest,
        context: TrustedTaskContext,
        digest: str,
        reason: str,
        *,
        now: datetime,
    ) -> AuthorizationDecision:
        """Record a denial when a token cannot safely yield a grant identity."""

        with self._lock:
            self._version += 1
            decision = AuthorizationDecision(
                decision_id=_decision_id(None, request),
                outcome=DecisionOutcome.DENY,
                reason_codes=(reason,),
                operation_id=request.operation_id,
                request_digest=stable_digest(request),
                grant_id=None,
                token_digest=digest,
                policy_version=POLICY_VERSION,
                ledger_version=self._version,
                remaining_calls=0,
            )
            self._audit.append(
                AuditEvent(
                    decision_id=decision.decision_id,
                    operation_id=request.operation_id,
                    grant_id=None,
                    parent_grant_id=None,
                    subject_id=context.subject_id,
                    actor_id=context.actor_id,
                    actor_version=context.actor_version,
                    workload_id=context.workload_id,
                    tenant_id=context.tenant_id,
                    task_id=context.task_id,
                    audience=request.audience,
                    action=request.action,
                    resource=request.resource,
                    amount_cents=request.amount_cents,
                    vendor_id=request.vendor_id,
                    intent_digest=None,
                    constraints_digest=None,
                    grant_expires_at=None,
                    request_digest=decision.request_digest,
                    token_digest=digest,
                    outcome=DecisionOutcome.DENY,
                    reason_codes=decision.reason_codes,
                    policy_version=POLICY_VERSION,
                    observed_at=now,
                )
            )
            return decision

    def authorize_and_consume(
        self,
        grant: DelegationGrant,
        token: str,
        request: AuthorizationRequest,
        context: TrustedTaskContext,
        *,
        now: datetime,
    ) -> AuthorizationDecision:
        request_digest = stable_digest(request)
        operation_fingerprint = stable_digest(
            {"grant_id": grant.grant_id, "request": request.model_dump(mode="python")}
        )
        digest = token_digest(token)
        with self._lock:
            operation_key = (context.tenant_id, request.operation_id)
            previous = self._operations.get(operation_key)
            if previous:
                previous_fingerprint, decision = previous
                if previous_fingerprint == operation_fingerprint:
                    return decision.model_copy(update={"replayed_decision": True})
                collision = AuthorizationDecision(
                    decision_id=_decision_id(grant.grant_id, request),
                    outcome=DecisionOutcome.DENY,
                    reason_codes=("operation_id_reused_with_different_request",),
                    operation_id=request.operation_id,
                    request_digest=request_digest,
                    grant_id=grant.grant_id,
                    token_digest=digest,
                    policy_version=POLICY_VERSION,
                    ledger_version=self._version,
                    remaining_calls=self._remaining_calls(grant),
                )
                self._audit.append(
                    AuditEvent(
                        decision_id=collision.decision_id,
                        operation_id=request.operation_id,
                        grant_id=grant.grant_id,
                        parent_grant_id=grant.parent_grant_id,
                        subject_id=context.subject_id,
                        actor_id=context.actor_id,
                        actor_version=context.actor_version,
                        workload_id=context.workload_id,
                        tenant_id=context.tenant_id,
                        task_id=context.task_id,
                        audience=request.audience,
                        action=request.action,
                        resource=request.resource,
                        amount_cents=request.amount_cents,
                        vendor_id=request.vendor_id,
                        intent_digest=grant.intent_digest,
                        constraints_digest=stable_digest(grant.constraints),
                        grant_expires_at=grant.expires_at,
                        request_digest=request_digest,
                        token_digest=digest,
                        outcome=collision.outcome,
                        reason_codes=collision.reason_codes,
                        policy_version=POLICY_VERSION,
                        observed_at=now,
                    )
                )
                return collision

            reasons: list[str] = []
            registered = self._grants.get(grant.grant_id)
            if registered is None or stable_digest(registered) != stable_digest(grant):
                reasons.append("grant_not_registered_exactly")
            inactive = self._inactive_reason(grant)
            if inactive:
                reasons.append(inactive)
            if grant.policy_version != POLICY_VERSION:
                reasons.append("wrong_policy_version")
            expected_bindings = (
                (grant.subject_id, context.subject_id, "subject_mismatch"),
                (grant.actor_id, context.actor_id, "actor_mismatch"),
                (grant.actor_version, context.actor_version, "actor_version_mismatch"),
                (grant.workload_id, context.workload_id, "workload_mismatch"),
                (grant.tenant_id, context.tenant_id, "tenant_mismatch"),
                (grant.task_id, context.task_id, "task_mismatch"),
                (grant.audience, request.audience, "audience_mismatch"),
            )
            reasons.extend(code for expected, actual, code in expected_bindings if expected != actual)
            if not (context.bound_at <= now < context.valid_until):
                reasons.append("trusted_context_not_current")
            if not (grant.issued_at <= now < grant.expires_at):
                reasons.append("grant_not_current")
            if request.action not in grant.actions:
                reasons.append("action_not_delegated")
            if request.resource not in grant.resources:
                reasons.append("resource_not_delegated")
            if request.amount_cents > grant.constraints.max_amount_cents:
                reasons.append("amount_exceeds_delegation")
            vendors = grant.constraints.allowed_vendor_ids
            if vendors and request.vendor_id is None:
                reasons.append("vendor_required")
            elif request.vendor_id is not None and request.vendor_id not in vendors:
                reasons.append("vendor_not_delegated")
            calls = self._call_counts.get(grant.grant_id, 0)
            delegated_calls = self._delegated_calls.get(grant.grant_id, 0)
            if calls + delegated_calls >= grant.constraints.max_calls:
                reasons.append("call_limit_exhausted")

            if reasons:
                outcome = DecisionOutcome.DENY
            else:
                outcome = DecisionOutcome.ALLOW
                calls += 1
                self._call_counts[grant.grant_id] = calls
                self._version += 1
            decision = AuthorizationDecision(
                decision_id=_decision_id(grant.grant_id, request),
                outcome=outcome,
                reason_codes=tuple(sorted(set(reasons))) if reasons else ("all_constraints_satisfied",),
                operation_id=request.operation_id,
                request_digest=request_digest,
                grant_id=grant.grant_id,
                token_digest=digest,
                policy_version=POLICY_VERSION,
                ledger_version=self._version,
                remaining_calls=self._remaining_calls(grant),
            )
            self._operations[operation_key] = (operation_fingerprint, decision)
            self._audit.append(
                AuditEvent(
                    decision_id=decision.decision_id,
                    operation_id=request.operation_id,
                    grant_id=grant.grant_id,
                    parent_grant_id=grant.parent_grant_id,
                    subject_id=context.subject_id,
                    actor_id=context.actor_id,
                    actor_version=context.actor_version,
                    workload_id=context.workload_id,
                    tenant_id=context.tenant_id,
                    task_id=context.task_id,
                    audience=request.audience,
                    action=request.action,
                    resource=request.resource,
                    amount_cents=request.amount_cents,
                    vendor_id=request.vendor_id,
                    intent_digest=grant.intent_digest,
                    constraints_digest=stable_digest(grant.constraints),
                    grant_expires_at=grant.expires_at,
                    request_digest=request_digest,
                    token_digest=digest,
                    outcome=outcome,
                    reason_codes=decision.reason_codes,
                    policy_version=POLICY_VERSION,
                    observed_at=now,
                )
            )
            return decision


def authorize_token(
    ledger: GrantLedger,
    token: str,
    request: AuthorizationRequest,
    context: TrustedTaskContext,
    *,
    now: datetime,
) -> AuthorizationDecision:
    """PEP entry point: cryptographic validation precedes stateful authorization."""

    digest = token_digest(token)
    try:
        grant = verify_training_token(token, audience=request.audience, now=now)
    except (ValueError, jwt.PyJWTError) as exc:
        reason = str(exc).replace(" ", "_")
        return ledger.record_prevalidation_denial(request, context, digest, reason, now=now)
    return ledger.authorize_and_consume(grant, token, request, context, now=now)


def attenuate_grant(
    parent_token: str,
    child_context: TrustedTaskContext,
    ledger: GrantLedger,
    *,
    parent_audience: str,
    grant_id: str,
    audience: str,
    actions: Iterable[str],
    resources: Iterable[str],
    constraints: DelegationConstraints,
    expires_at: datetime,
    now: datetime,
) -> tuple[DelegationGrant, str]:
    """Create a child grant only when every authority dimension narrows."""

    parent = verify_training_token(parent_token, audience=parent_audience, now=now)
    ledger.assert_active(parent)
    if not (child_context.bound_at <= now < child_context.valid_until):
        raise ValueError("child_context_not_current")
    actions = frozenset(actions)
    resources = frozenset(resources)
    checks = {
        "child_subject_mismatch": child_context.subject_id != parent.subject_id,
        "child_tenant_mismatch": child_context.tenant_id != parent.tenant_id,
        "child_task_mismatch": child_context.task_id != parent.task_id,
        "child_actions_exceed_parent": not actions.issubset(parent.actions),
        "child_resources_exceed_parent": not resources.issubset(parent.resources),
        "child_amount_exceeds_parent": constraints.max_amount_cents > parent.constraints.max_amount_cents,
        "child_vendors_exceed_parent": not constraints.allowed_vendor_ids.issubset(parent.constraints.allowed_vendor_ids),
        "child_calls_exceed_parent": constraints.max_calls > parent.constraints.max_calls,
        "child_expiry_exceeds_parent": expires_at > parent.expires_at,
        "child_audience_not_allowed": audience not in ALLOWED_AUDIENCE_TRANSITIONS.get(parent.audience, frozenset()),
        "delegation_depth_exceeded": parent.depth + 1 > parent.max_depth,
    }
    failed = tuple(code for code, is_failed in checks.items() if is_failed)
    if failed:
        raise ValueError(",".join(failed))
    child = DelegationGrant(
        grant_id=grant_id,
        subject_id=parent.subject_id,
        actor_id=child_context.actor_id,
        actor_version=child_context.actor_version,
        workload_id=child_context.workload_id,
        tenant_id=parent.tenant_id,
        task_id=parent.task_id,
        audience=audience,
        actions=actions,
        resources=resources,
        constraints=constraints,
        issued_at=now,
        expires_at=expires_at,
        intent_digest=parent.intent_digest,
        policy_version=parent.policy_version,
        parent_grant_id=parent.grant_id,
        depth=parent.depth + 1,
        max_depth=parent.max_depth,
    )
    ledger.register(child)
    return child, issue_training_token(child)


def token_exchange_request(*, subject_token: str, actor_token: str, audience: str, scope: str) -> dict[str, str]:
    """Return the RFC 8693 request shape; no live token endpoint is called."""

    return {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": subject_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "actor_token": actor_token,
        "actor_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "audience": audience,
        "scope": scope,
    }


def demo_directory() -> IdentityDirectory:
    tenant = "tenant:oneplusi"
    return IdentityDirectory(
        principals=(
            Principal(principal_id="human:user-123", kind=PrincipalKind.HUMAN, tenant_id=tenant, owner="Data & AI"),
            Principal(principal_id="agent:procurement", kind=PrincipalKind.AGENT, tenant_id=tenant, owner="AI Platform", version="1.0.0"),
            Principal(principal_id="spiffe://example.com/prod/procurement", kind=PrincipalKind.WORKLOAD, tenant_id=tenant, owner="Platform IAM"),
            Principal(principal_id="agent:vendor-research", kind=PrincipalKind.AGENT, tenant_id=tenant, owner="AI Platform", version="1.0.0"),
            Principal(principal_id="spiffe://example.com/prod/vendor-research", kind=PrincipalKind.WORKLOAD, tenant_id=tenant, owner="Platform IAM"),
        ),
        bindings=(
            AgentWorkloadBinding(
                actor_id="agent:procurement",
                workload_id="spiffe://example.com/prod/procurement",
                required_selectors=frozenset({"k8s:ns:agents", "k8s:sa:procurement"}),
            ),
            AgentWorkloadBinding(
                actor_id="agent:vendor-research",
                workload_id="spiffe://example.com/prod/vendor-research",
                required_selectors=frozenset({"k8s:ns:agents", "k8s:sa:vendor-research"}),
            ),
        ),
    )


def demo_context(*, research_agent: bool = False, now: datetime = REFERENCE_TIME) -> TrustedTaskContext:
    directory = demo_directory()
    suffix = "vendor-research" if research_agent else "procurement"
    session = AuthenticatedHumanSession(
        subject_id="human:user-123",
        tenant_id="tenant:oneplusi",
        session_id="SESSION-001",
        authenticated_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(minutes=55),
        authentication_methods=frozenset({"pwd", "webauthn"}),
    )
    workload = WorkloadAttestation(
        workload_id=f"spiffe://example.com/prod/{suffix}",
        trust_domain=TRUST_DOMAIN,
        selectors=frozenset({"k8s:ns:agents", f"k8s:sa:{suffix}"}),
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=9),
    )
    return bind_trusted_context(
        session,
        f"agent:{suffix}",
        workload,
        "TASK-BUY-LAPTOPS-001",
        directory,
        now=now,
    )


def demo_intent(now: datetime = REFERENCE_TIME) -> TaskIntent:
    return TaskIntent(
        intent_id="INTENT-001",
        task_id="TASK-BUY-LAPTOPS-001",
        tenant_id="tenant:oneplusi",
        description="Buy approved laptops for the Data & AI department within CAD 5,000.",
        approved_actions=frozenset({"vendor:read", "purchase_order:create"}),
        approved_resources=frozenset({"department:data-ai"}),
        constraints=DelegationConstraints(
            max_amount_cents=500_000,
            allowed_vendor_ids=frozenset({"vendor-acme", "vendor-northstar"}),
            max_calls=1,
        ),
        approved_by="human:user-123",
        approved_at=now,
    )


def build_demo_authority(now: datetime = REFERENCE_TIME) -> tuple[TrustedTaskContext, DelegationGrant, str, GrantLedger]:
    context = demo_context(now=now)
    intent = demo_intent(now)
    grant = build_root_grant(
        context,
        intent,
        grant_id="GRANT-ROOT-001",
        audience="https://api.example.com/procurement",
        actions=intent.approved_actions,
        resources=intent.approved_resources,
        constraints=intent.constraints,
        expires_at=now + timedelta(minutes=30),
    )
    token = issue_training_token(grant)
    ledger = GrantLedger()
    ledger.register(grant)
    return context, grant, token, ledger


def demo_request(*, operation_id: str = "OP-PO-001") -> AuthorizationRequest:
    return AuthorizationRequest(
        operation_id=operation_id,
        audience="https://api.example.com/procurement",
        action="purchase_order:create",
        resource="department:data-ai",
        amount_cents=450_000,
        vendor_id="vendor-acme",
    )


class EvaluationSummary(FrozenModel):
    case_count: int
    correct_count: int
    accuracy: Decimal
    forbidden_case_count: int
    forbidden_allowed_count: int
    false_denial_count: int
    rows: tuple[dict[str, object], ...]


def run_evaluation(now: datetime = REFERENCE_TIME) -> EvaluationSummary:
    """Evaluate labelled positive, negative, boundary, and lifecycle cases."""

    cases = (
        ("allowed_purchase", demo_request(operation_id="OP-EVAL-1"), True, None),
        ("amount_over_limit", demo_request(operation_id="OP-EVAL-2").model_copy(update={"amount_cents": 500_001}), False, None),
        ("wrong_vendor", demo_request(operation_id="OP-EVAL-3").model_copy(update={"vendor_id": "vendor-unknown"}), False, None),
        ("wrong_resource", demo_request(operation_id="OP-EVAL-4").model_copy(update={"resource": "department:finance"}), False, None),
        ("boundary_amount", demo_request(operation_id="OP-EVAL-5").model_copy(update={"amount_cents": 500_000}), True, None),
        ("revoked_grant", demo_request(operation_id="OP-EVAL-6"), False, "revoke"),
        ("closed_task", demo_request(operation_id="OP-EVAL-7"), False, "close"),
    )
    rows: list[dict[str, object]] = []
    for name, request, expected, setup in cases:
        context, grant, token, ledger = build_demo_authority(now)
        if setup == "revoke":
            ledger.revoke(grant.grant_id)
        elif setup == "close":
            ledger.close_task(grant.task_id)
        decision = authorize_token(ledger, token, request, context, now=now)
        actual = decision.outcome is DecisionOutcome.ALLOW
        rows.append({
            "case": name,
            "expected_allowed": expected,
            "actual_allowed": actual,
            "correct": actual == expected,
            "reason_codes": decision.reason_codes,
        })
    correct = sum(bool(row["correct"]) for row in rows)
    forbidden = [row for row in rows if not row["expected_allowed"]]
    return EvaluationSummary(
        case_count=len(rows),
        correct_count=correct,
        accuracy=Decimal(correct) / Decimal(len(rows)),
        forbidden_case_count=len(forbidden),
        forbidden_allowed_count=sum(bool(row["actual_allowed"]) for row in forbidden),
        false_denial_count=sum(not bool(row["actual_allowed"]) for row in rows if row["expected_allowed"]),
        rows=tuple(rows),
    )
