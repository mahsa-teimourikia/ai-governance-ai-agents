"""Credential-free capstone lab: a small governed agent runtime."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

UTC = timezone.utc

@dataclass(frozen=True)
class Action:
    name: str
    tenant: str
    amount: float = 0
    vendor: str = ""
    idempotency_key: str = ""

@dataclass
class Identity:
    subject: str
    tenant: str
    permissions: set[str]

@dataclass
class Approval:
    action_hash: str
    approver: str
    expires_at: datetime

@dataclass
class Evidence:
    event: str
    decision: str
    reason: str
    action_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

def fingerprint(action: Action) -> str:
    raw = f"{action.name}|{action.tenant}|{action.amount:.2f}|{action.vendor}|{action.idempotency_key}"
    return sha256(raw.encode()).hexdigest()[:16]

class GovernanceRuntime:
    def __init__(self):
        self.kill_switch = False
        self.executed: set[str] = set()
        self.evidence: list[Evidence] = []

    def authorize(self, identity: Identity, action: Action, approval: Approval | None = None) -> Evidence:
        h = fingerprint(action)
        def deny(reason):
            e = Evidence("authorization", "DENY", reason, h, {"subject": identity.subject})
            self.evidence.append(e); return e
        if self.kill_switch: return deny("global kill switch active")
        if identity.tenant != action.tenant: return deny("tenant boundary violation")
        required = {"vendor.read" if action.name == "vendor.read" else "po.create"}
        if not required.issubset(identity.permissions): return deny("missing permission")
        if action.name == "po.create" and action.amount > 10000:
            if approval is None: return deny("human approval required")
            if approval.action_hash != h: return deny("approval does not bind to exact action")
            if approval.expires_at <= datetime.now(UTC): return deny("approval expired")
        if h in self.executed: return deny("duplicate idempotency key")
        e = Evidence("authorization", "ALLOW", "policy and authority checks passed", h)
        self.evidence.append(e); return e

    def execute(self, identity: Identity, action: Action, approval: Approval | None = None) -> Evidence:
        decision = self.authorize(identity, action, approval)
        if decision.decision == "DENY": return decision
        self.executed.add(decision.action_hash)
        result = Evidence("tool_execution", "COMMITTED", "gateway executed bounded action", decision.action_hash,
                          {"tool": action.name, "amount": action.amount})
        self.evidence.append(result); return result

def delegate(parent: Identity, child_subject: str, requested: set[str], tenant: str) -> Identity:
    if parent.tenant != tenant:
        raise PermissionError("delegation cannot cross tenant boundary")
    return Identity(child_subject, tenant, parent.permissions & requested)

def run_demo():
    runtime = GovernanceRuntime()
    manager = Identity("procurement-manager", "acme", {"vendor.read", "po.create"})
    researcher = delegate(manager, "research-agent", {"vendor.read"}, "acme")
    safe_read = runtime.execute(researcher, Action("vendor.read", "acme", vendor="V42", idempotency_key="r1"))
    amplified = runtime.execute(researcher, Action("po.create", "acme", 12000, "V42", "p1"))
    action = Action("po.create", "acme", 12000, "V42", "p2")
    approval = Approval(fingerprint(action), "manager", datetime.now(UTC) + timedelta(minutes=5))
    approved = runtime.execute(manager, action, approval)
    return [safe_read, amplified, approved]

if __name__ == "__main__":
    for item in run_demo(): print(item)
