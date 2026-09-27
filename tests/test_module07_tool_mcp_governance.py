"""Focused control and failure tests for Course 7."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import sys

import pytest
from mcp.types import Tool


MODULE = Path(__file__).parents[1] / "curriculum/intermediate/07-tool-and-mcp-governance"
sys.path.insert(0, str(MODULE))

from lab import (  # noqa: E402
    ApprovalReceipt,
    ApprovalStore,
    BudgetLedger,
    EffectStatus,
    Outcome,
    POLICY_VERSION,
    REFERENCE_TIME,
    ToolGateway,
    ToolRegistry,
    authorization_challenge,
    run_evaluation,
    sample_cancel_contract,
    sample_context,
    sample_contract,
    sample_facts,
    sample_proposal,
    to_mcp_tool,
    unsafe_schema_only_dispatch,
    validate_outbound_url,
    validate_redirect_chain,
)


def setup_gateway():
    contract = sample_contract()
    return contract, ToolGateway(ToolRegistry([contract]))


def approval_for(gateway, contract, context, proposal, **changes):
    digest = gateway.request_digest(context, proposal)
    receipt = ApprovalReceipt(
        receipt_id="APR-1001",
        request_digest=digest,
        tenant_id=context.tenant_id,
        subject_id=context.subject_id,
        workload_id=context.workload_id,
        task_id=context.task_id,
        tool_name=proposal.tool_name,
        manifest_digest=contract.manifest_digest,
        policy_version=POLICY_VERSION,
        approver_id="manager-77",
        approver_role="procurement-manager",
        issued_at=REFERENCE_TIME - timedelta(minutes=1),
        expires_at=REFERENCE_TIME + timedelta(minutes=5),
    ).model_copy(update=changes)
    gateway.approvals.add(receipt)
    return receipt


def test_official_mcp_descriptor_contains_governance_attestation():
    contract = sample_contract()
    descriptor = to_mcp_tool(contract)
    assert isinstance(descriptor, Tool)
    assert descriptor.inputSchema["additionalProperties"] is False
    assert descriptor.outputSchema["required"] == ["effect_id", "status", "tenant_id"]
    assert descriptor.meta["governance/manifestDigest"] == contract.manifest_digest
    assert descriptor.meta["governance/riskTier"] == "T2"


def test_baseline_allows_schema_valid_but_unauthorized_vendor():
    contract = sample_contract()
    proposal = sample_proposal(
        contract,
        arguments={"vendor_id": "VEN-999", "amount_cents": 10_000, "currency": "CAD"},
    )
    assert unsafe_schema_only_dispatch(contract, proposal) is Outcome.ALLOW


def test_safe_invocation_creates_one_tenant_scoped_effect_and_evidence():
    contract, gateway = setup_gateway()
    result = gateway.invoke(sample_context(), sample_proposal(contract), sample_facts())
    assert result.decision.outcome is Outcome.ALLOW
    assert result.effect.status is EffectStatus.APPLIED
    assert result.output["tenant_id"] == "tenant-north"
    assert gateway.evidence[-1].effect_status is EffectStatus.APPLIED
    assert "credential" not in gateway.evidence[-1].model_dump_json().lower()


@pytest.mark.parametrize(
    ("arguments", "reason"),
    [
        ({"vendor_id": "VEN-101", "amount_cents": 1, "currency": "USD"}, "INPUT_SCHEMA_INVALID"),
        ({"vendor_id": "VEN-101", "amount_cents": 1, "currency": "CAD", "admin": True}, "INPUT_SCHEMA_INVALID"),
        ({"vendor_id": "VEN-999", "amount_cents": 1, "currency": "CAD"}, "VENDOR_NOT_APPROVED"),
        ({"vendor_id": "VEN-101", "amount_cents": 2_100_000, "currency": "CAD"}, "TASK_AMOUNT_LIMIT_EXCEEDED"),
    ],
)
def test_schema_and_semantic_denials(arguments, reason):
    contract, gateway = setup_gateway()
    proposal = sample_proposal(contract, arguments=arguments)
    decision = gateway.evaluate(sample_context(), proposal, sample_facts())
    assert decision.outcome is Outcome.DENY
    assert reason in decision.reason_codes


def test_manifest_drift_is_denied_even_if_descriptor_was_cached():
    contract, gateway = setup_gateway()
    cached = sample_proposal(contract)
    gateway.registry.replace(contract.model_copy(update={"description": "PO tool changed after discovery"}))
    decision = gateway.evaluate(sample_context(), cached, sample_facts())
    assert decision.reason_codes == ("MANIFEST_ATTESTATION_FAILED",)


def test_unregistered_tool_and_model_claims_do_not_grant_authority():
    contract, gateway = setup_gateway()
    unknown = sample_proposal(
        contract,
        tool_name="payments.send",
        model_claimed_approved=True,
        model_claimed_role="admin",
    )
    assert gateway.evaluate(sample_context(), unknown, sample_facts()).reason_codes == ("TOOL_NOT_REGISTERED",)

    bad_vendor = sample_proposal(
        contract,
        model_claimed_approved=True,
        model_claimed_role="procurement-manager",
        arguments={"vendor_id": "VEN-999", "amount_cents": 10_000, "currency": "CAD"},
    )
    assert gateway.evaluate(sample_context(), bad_vendor, sample_facts()).reason_codes == ("VENDOR_NOT_APPROVED",)


def test_revocation_is_rechecked_at_call_time():
    contract, gateway = setup_gateway()
    cached = sample_proposal(contract)
    gateway.registry.revoke(contract.server_id, contract.name)
    assert gateway.evaluate(sample_context(), cached, sample_facts()).reason_codes == ("TOOL_NOT_ACTIVE",)


def test_workload_tenant_and_freshness_are_trusted_boundaries():
    contract, gateway = setup_gateway()
    proposal = sample_proposal(contract)
    assert gateway.evaluate(sample_context(workload_id="email-agent"), proposal, sample_facts()).reason_codes == ("WORKLOAD_NOT_AUTHORIZED",)
    assert gateway.evaluate(sample_context(), proposal, sample_facts(tenant_id="tenant-south")).reason_codes == ("TENANT_BINDING_MISMATCH",)
    stale = sample_facts(valid_until=REFERENCE_TIME - timedelta(seconds=1))
    assert gateway.evaluate(sample_context(), proposal, stale).reason_codes == ("TRUSTED_FACTS_STALE",)


@pytest.mark.parametrize(
    ("context_change", "reason"),
    [
        ({"token_issuer": "https://attacker.example"}, "TOKEN_ISSUER_UNTRUSTED"),
        ({"token_resource": "mcp://other-server"}, "TOKEN_RESOURCE_MISMATCH"),
        ({"scopes": frozenset()}, "TOKEN_SCOPE_INSUFFICIENT"),
    ],
)
def test_mcp_token_claims_are_bound_to_issuer_resource_and_scope(context_change, reason):
    contract, gateway = setup_gateway()
    decision = gateway.evaluate(
        sample_context(**context_change), sample_proposal(contract), sample_facts()
    )
    assert decision.outcome is Outcome.DENY
    assert decision.reason_codes == (reason,)


def test_mcp_http_challenges_distinguish_invalid_token_and_insufficient_scope():
    metadata = "https://mcp.example.test/.well-known/oauth-protected-resource"
    invalid = authorization_challenge(metadata)
    insufficient = authorization_challenge(metadata, insufficient_scope=True)
    assert invalid.status_code == 401
    assert insufficient.status_code == 403
    assert 'error="invalid_token"' in invalid.www_authenticate
    assert 'error="insufficient_scope"' in insufficient.www_authenticate
    assert metadata in invalid.www_authenticate


def test_threshold_escalates_and_exact_receipt_allows_once():
    contract, gateway = setup_gateway()
    context, facts = sample_context(), sample_facts()
    proposal = sample_proposal(
        contract,
        arguments={"vendor_id": "VEN-101", "amount_cents": 700_000, "currency": "CAD"},
    )
    assert gateway.evaluate(context, proposal, facts).outcome is Outcome.ESCALATE
    receipt = approval_for(gateway, contract, context, proposal)
    result = gateway.invoke(context, proposal, facts, approval_receipt_id=receipt.receipt_id)
    assert result.decision.outcome is Outcome.ALLOW

    replay_proposal = proposal.model_copy(update={"operation_id": "OP-REPLAY"})
    replay = gateway.invoke(context, replay_proposal, facts, approval_receipt_id=receipt.receipt_id)
    assert replay.decision.reason_codes == ("APPROVAL_REPLAYED",)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"expires_at": REFERENCE_TIME - timedelta(seconds=1)}, "APPROVAL_EXPIRED"),
        ({"approver_role": "requester"}, "APPROVER_ROLE_INVALID"),
        ({"tenant_id": "tenant-south"}, "APPROVAL_BINDING_MISMATCH"),
        ({"request_digest": "0" * 64}, "APPROVAL_BINDING_MISMATCH"),
    ],
)
def test_invalid_approval_receipts_are_denied(change, reason):
    contract, gateway = setup_gateway()
    context, facts = sample_context(), sample_facts()
    proposal = sample_proposal(
        contract,
        arguments={"vendor_id": "VEN-101", "amount_cents": 700_000, "currency": "CAD"},
    )
    receipt = approval_for(gateway, contract, context, proposal, **change)
    result = gateway.invoke(context, proposal, facts, approval_receipt_id=receipt.receipt_id)
    assert result.decision.reason_codes == (reason,)
    assert result.effect.status is EffectStatus.NOT_ATTEMPTED


def test_atomic_call_budget_admits_exactly_the_limit_under_concurrency():
    ledger = BudgetLedger(call_limit=4, spend_limit_cents=1_000_000)
    context = sample_context()
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(lambda _: ledger.reserve(context, 1), range(12)))
    assert outcomes.count(None) == 4
    assert outcomes.count("CALL_BUDGET_EXCEEDED") == 8
    assert ledger.usage(context) == (4, 4)


def test_idempotent_replay_is_one_effect_but_mutated_replay_is_denied():
    contract, gateway = setup_gateway()
    context, facts = sample_context(), sample_facts()
    proposal = sample_proposal(contract)
    first = gateway.invoke(context, proposal, facts)
    second = gateway.invoke(context, proposal, facts)
    assert first == second
    assert len(gateway.evidence) == 1
    mutated = proposal.model_copy(update={"arguments": {"vendor_id": "VEN-101", "amount_cents": 125_001, "currency": "CAD"}})
    denied = gateway.invoke(context, mutated, facts)
    assert denied.decision.reason_codes == ("IDEMPOTENCY_MUTATION",)


def test_idempotency_namespace_is_tenant_scoped():
    contract, gateway = setup_gateway()
    north = gateway.invoke(sample_context(), sample_proposal(contract), sample_facts())
    south_context = sample_context(tenant_id="tenant-south")
    south_facts = sample_facts(tenant_id="tenant-south")
    south = gateway.invoke(south_context, sample_proposal(contract), south_facts)
    assert north.effect.effect_id != south.effect.effect_id


def test_unknown_after_commit_is_reconciled_without_duplicate():
    contract, gateway = setup_gateway()
    gateway.adapter.failure_mode = "after_commit"
    result = gateway.invoke(sample_context(), sample_proposal(contract), sample_facts())
    assert result.effect.status is EffectStatus.APPLIED
    assert result.output["status"] == "created"


def test_unknown_before_commit_is_not_blindly_retried():
    contract, gateway = setup_gateway()
    gateway.adapter.failure_mode = "before_commit"
    first = gateway.invoke(sample_context(), sample_proposal(contract), sample_facts())
    second = gateway.invoke(sample_context(), sample_proposal(contract), sample_facts())
    assert first.effect.status is EffectStatus.UNKNOWN
    assert first == second


def test_compensation_is_a_separate_governed_tenant_scoped_action():
    create_contract = sample_contract()
    cancel_contract = sample_cancel_contract()
    gateway = ToolGateway(ToolRegistry([create_contract, cancel_contract]))
    context, facts = sample_context(), sample_facts()
    created = gateway.invoke(context, sample_proposal(create_contract), facts)

    cancel = sample_proposal(
        cancel_contract,
        operation_id="OP-CANCEL-1001",
        arguments={"original_operation_id": "OP-1001", "reason": "Duplicate requisition"},
    )
    compensated = gateway.invoke(context, cancel, facts)
    assert compensated.decision.outcome is Outcome.ALLOW
    assert compensated.effect.status is EffectStatus.COMPENSATED
    assert compensated.output["compensates_effect_id"] == created.effect.effect_id
    assert gateway.evidence[-1].tool_name == "procurement.cancel_po"


def test_compensation_cannot_cross_tenant_boundary():
    create_contract = sample_contract()
    cancel_contract = sample_cancel_contract()
    gateway = ToolGateway(ToolRegistry([create_contract, cancel_contract]))
    gateway.invoke(sample_context(), sample_proposal(create_contract), sample_facts())
    south = sample_context(tenant_id="tenant-south")
    cancel = sample_proposal(
        cancel_contract,
        operation_id="OP-CANCEL-SOUTH",
        arguments={"original_operation_id": "OP-1001", "reason": "Attempted cross-tenant cancel"},
    )
    result = gateway.invoke(south, cancel, sample_facts(tenant_id="tenant-south"))
    assert result.effect.status is EffectStatus.UNKNOWN
    assert gateway.adapter.reconcile("tenant-north", "OP-1001") is not None


def test_compensation_requires_its_own_scope():
    create_contract = sample_contract()
    cancel_contract = sample_cancel_contract()
    gateway = ToolGateway(ToolRegistry([create_contract, cancel_contract]))
    context = sample_context()
    gateway.invoke(context, sample_proposal(create_contract), sample_facts())
    cancel = sample_proposal(
        cancel_contract,
        operation_id="OP-CANCEL-NO-SCOPE",
        arguments={"original_operation_id": "OP-1001", "reason": "Duplicate requisition"},
    )
    create_only = context.model_copy(
        update={"scopes": frozenset({"tools:procurement.create_po"})}
    )
    result = gateway.invoke(create_only, cancel, sample_facts())
    assert result.decision.reason_codes == ("TOKEN_SCOPE_INSUFFICIENT",)
    assert result.effect.status is EffectStatus.NOT_ATTEMPTED


def test_adapter_rejects_direct_bypass():
    contract, gateway = setup_gateway()
    with pytest.raises(PermissionError, match="gateway"):
        gateway.adapter.execute(object(), sample_context(), sample_proposal(contract), "0" * 64)


def test_invalid_backend_output_is_not_released_as_success(monkeypatch):
    contract, gateway = setup_gateway()
    original = gateway.adapter.execute

    def invalid_output(*args, **kwargs):
        receipt, _ = original(*args, **kwargs)
        return receipt, {"status": "created"}

    monkeypatch.setattr(gateway.adapter, "execute", invalid_output)
    result = gateway.invoke(sample_context(), sample_proposal(contract), sample_facts())
    assert result.effect.status is EffectStatus.UNKNOWN
    assert result.output is None


@pytest.mark.parametrize(
    "url",
    [
        "http://updates.example.test/a",
        "https://user:secret@updates.example.test/a",
        "https://updates.example.test:8443/a",
        "https://evil.example.test/a",
    ],
)
def test_ssrf_url_shape_and_allowlist_rejections(url):
    resolver = lambda _: ["203.0.113.10"]
    with pytest.raises(ValueError):
        validate_outbound_url(url, resolver, frozenset({"updates.example.test"}))


@pytest.mark.parametrize("address", ["127.0.0.1", "169.254.169.254", "10.1.2.3", "::1", "fc00::1"])
def test_ssrf_rejects_every_non_global_dns_result(address):
    with pytest.raises(ValueError, match="non-global"):
        validate_outbound_url(
            "https://updates.example.test/a",
            lambda _: ["8.8.8.8", address],
            frozenset({"updates.example.test"}),
        )


def test_ssrf_revalidates_every_redirect_and_bounds_hops():
    def resolver(host):
        return ["127.0.0.1"] if host == "internal.example.test" else ["8.8.8.8"]

    allowed = frozenset({"updates.example.test", "internal.example.test"})
    with pytest.raises(ValueError, match="non-global"):
        validate_redirect_chain(
            ["https://updates.example.test/a", "https://internal.example.test/admin"],
            resolver,
            allowed,
        )
    with pytest.raises(ValueError, match="hop limit"):
        validate_redirect_chain(
            [f"https://updates.example.test/{index}" for index in range(5)],
            resolver,
            allowed,
            max_hops=3,
        )


def test_labelled_evaluation_defines_exact_populations_and_improves_baseline():
    summary = run_evaluation()
    assert summary.case_count == 9
    assert summary.expected_allow_count + summary.expected_deny_count + summary.expected_escalate_count == 9
    assert summary.baseline_correct_count == 2
    assert summary.candidate_correct_count == 9
    assert summary.baseline_forbidden_allowed_count == 6
    assert summary.candidate_forbidden_allowed_count == 0
    assert summary.baseline_missed_escalation_count == 1
    assert summary.candidate_missed_escalation_count == 0
