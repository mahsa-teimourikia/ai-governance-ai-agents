"""Focused invariants for Course 15 governance control-plane architecture."""

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

MODULE = (
    Path(__file__).parents[1]
    / "curriculum/advanced/15-governance-control-plane-architecture"
)
sys.path.insert(0, str(MODULE))
sys.modules.pop("lab", None)

from lab import (
    POLICY_CANDIDATE_VERSION,
    POLICY_VERSION,
    REFERENCE_TIME,
    TENANT_ACME,
    TENANT_GLOBEX,
    ApprovalLedger,
    ControlPlane,
    ControlPlaneError,
    DecisionEffect,
    EvidenceLog,
    Lifecycle,
    OperationMode,
    OutcomeState,
    PolicyReplica,
    RegistryAdminService,
    ToolGateway,
    attenuate_delegation,
    authorize_policy_activation,
    build_context,
    build_course15_reference_run,
    build_grant,
    build_operator,
    build_otel_demo,
    build_reference_environment,
    build_registry,
    build_scenarios,
    build_sdk_artifacts,
    enforce_constraints,
    evaluate_control_plane,
    evaluate_prompt_only_baseline,
    evaluate_shadow_rollout,
    interoperability_map,
    issue_approval,
    issue_policy_bundle,
    proposal,
    shadow_compare,
    stable_digest,
)


def clone(model, **changes):
    values = model.model_dump(mode="python")
    values.update(changes)
    return type(model)(**values)


def request_for(item=None, **proposal_changes):
    env = build_reference_environment()
    cp = env["control_plane"]
    p = item or proposal(**proposal_changes)
    request = cp.build_request(
        env["context"],
        "procurement-agent",
        env["grant"],
        p,
        environment="production",
        now=REFERENCE_TIME,
    )
    return env, request


def test_stable_digest_is_canonical_for_maps_and_sets():
    assert stable_digest({"b": {2, 1}, "a": 3}) == stable_digest({"a": 3, "b": {1, 2}})


def test_context_requires_spiffe_workload_identity():
    with pytest.raises(ValidationError):
        clone(build_context(), workload_id="agent-says-itself")


def test_context_requires_positive_validity_window():
    with pytest.raises(ValidationError):
        clone(build_context(), valid_until=build_context().authenticated_at)


def test_reference_registry_is_tenant_scoped_and_versioned():
    registry = build_registry()
    agent = registry.get_agent(TENANT_ACME, "procurement-agent")
    tool = registry.get_tool(TENANT_ACME, "purchase-order.create")
    assert (agent.registry_version, tool.registry_version) == (1, 1)
    with pytest.raises(ControlPlaneError, match="AGENT_NOT_REGISTERED"):
        registry.get_agent(TENANT_GLOBEX, "procurement-agent")


def test_duplicate_agent_and_tool_registration_are_rejected():
    registry = build_registry()
    with pytest.raises(ControlPlaneError, match="AGENT_ALREADY_REGISTERED"):
        registry.register_agent(registry.get_agent(TENANT_ACME, "procurement-agent"))
    with pytest.raises(ControlPlaneError, match="TOOL_ALREADY_REGISTERED"):
        registry.register_tool(registry.get_tool(TENANT_ACME, "vendor.read"))


def test_registry_update_uses_optimistic_concurrency():
    registry = build_registry()
    updated = registry.transition_agent(
        TENANT_ACME, "procurement-agent", Lifecycle.SUSPENDED, 1
    )
    assert (updated.lifecycle, updated.registry_version) == (Lifecycle.SUSPENDED, 2)
    with pytest.raises(ControlPlaneError, match="REGISTRY_VERSION_CONFLICT"):
        registry.transition_agent(TENANT_ACME, "procurement-agent", Lifecycle.ACTIVE, 1)


def test_tool_registry_update_uses_optimistic_concurrency():
    registry = build_registry()
    updated = registry.transition_tool(
        TENANT_ACME, "vendor.read", Lifecycle.SUSPENDED, 1
    )
    assert (updated.lifecycle, updated.registry_version) == (Lifecycle.SUSPENDED, 2)
    with pytest.raises(ControlPlaneError, match="REGISTRY_VERSION_CONFLICT"):
        registry.transition_tool(TENANT_ACME, "vendor.read", Lifecycle.ACTIVE, 1)


def test_management_plane_requires_current_tenant_bound_admin():
    registry = build_registry()
    service = RegistryAdminService(registry)
    with pytest.raises(ControlPlaneError, match="OPERATOR_ROLE_REQUIRED"):
        service.transition_agent(
            build_operator("viewer"),
            "procurement-agent",
            Lifecycle.SUSPENDED,
            expected_version=1,
            now=REFERENCE_TIME,
        )
    with pytest.raises(ControlPlaneError, match="AGENT_NOT_REGISTERED"):
        service.transition_agent(
            build_operator("registry-admin", tenant_id=TENANT_GLOBEX),
            "procurement-agent",
            Lifecycle.SUSPENDED,
            expected_version=1,
            now=REFERENCE_TIME,
        )
    expired = clone(build_operator("registry-admin"), valid_until=REFERENCE_TIME)
    with pytest.raises(ControlPlaneError, match="OPERATOR_SESSION_INVALID"):
        service.transition_agent(
            expired,
            "procurement-agent",
            Lifecycle.SUSPENDED,
            expected_version=1,
            now=REFERENCE_TIME,
        )


def test_retired_agent_cannot_be_reactivated():
    registry = build_registry()
    retired = registry.transition_agent(
        TENANT_ACME, "procurement-agent", Lifecycle.RETIRED, 1
    )
    with pytest.raises(ControlPlaneError, match="INVALID_LIFECYCLE_TRANSITION"):
        registry.transition_agent(TENANT_ACME, retired.agent_id, Lifecycle.ACTIVE, 2)


def test_discovery_hides_tools_when_agent_is_suspended():
    registry = build_registry()
    assert registry.discover_tools(build_context(), "procurement-agent") == (
        "purchase-order.create",
        "vendor.read",
    )
    registry.transition_agent(TENANT_ACME, "procurement-agent", Lifecycle.SUSPENDED, 1)
    assert registry.discover_tools(build_context(), "procurement-agent") == ()


def test_root_delegation_is_bound_and_signed():
    grant = build_grant()
    assert grant.tenant_id == TENANT_ACME
    assert grant.workload_id == build_context().workload_id
    assert len(grant.signature) == 64


def test_child_delegation_may_only_attenuate():
    parent = build_grant()
    child = attenuate_delegation(
        parent,
        child_agent_id="sourcing-specialist",
        operations=frozenset({"read_vendor"}),
        tool_ids=frozenset({"vendor.read"}),
        resource_prefixes=frozenset({"vendor:acme:"}),
        maximum_amount=0,
        expires_at=REFERENCE_TIME + timedelta(minutes=30),
    )
    assert child.parent_grant_id == parent.grant_id
    assert child.depth == 1
    assert child.operations < parent.operations


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (
            {"operations": frozenset({"read_vendor", "execute_payment"})},
            "DELEGATION_SCOPE_WIDENING",
        ),
        (
            {"tool_ids": frozenset({"vendor.read", "payment.execute"})},
            "DELEGATION_SCOPE_WIDENING",
        ),
        (
            {"resource_prefixes": frozenset({"vendor:globex:"})},
            "DELEGATION_RESOURCE_WIDENING",
        ),
        ({"maximum_amount": 50_001}, "DELEGATION_CONSTRAINT_WIDENING"),
    ],
)
def test_child_delegation_rejects_authority_widening(change, code):
    args = {
        "child_agent_id": "child",
        "operations": frozenset({"read_vendor"}),
        "tool_ids": frozenset({"vendor.read"}),
        "resource_prefixes": frozenset({"vendor:acme:"}),
        "maximum_amount": 0,
        "expires_at": REFERENCE_TIME + timedelta(minutes=10),
    }
    args.update(change)
    with pytest.raises(ControlPlaneError, match=code):
        attenuate_delegation(build_grant(), **args)


def test_tampered_parent_delegation_cannot_be_attenuated():
    parent = clone(build_grant(), maximum_amount=999_999)
    with pytest.raises(ControlPlaneError, match="DELEGATION_SIGNATURE_INVALID"):
        attenuate_delegation(
            parent,
            child_agent_id="child",
            operations=frozenset({"read_vendor"}),
            tool_ids=frozenset({"vendor.read"}),
            resource_prefixes=frozenset({"vendor:acme:"}),
            maximum_amount=0,
            expires_at=REFERENCE_TIME + timedelta(minutes=10),
        )


def test_build_request_rejects_expired_identity():
    env = build_reference_environment()
    with pytest.raises(ControlPlaneError, match="IDENTITY_EXPIRED"):
        env["control_plane"].build_request(
            env["context"],
            "procurement-agent",
            env["grant"],
            proposal(),
            environment="production",
            now=REFERENCE_TIME + timedelta(hours=2),
        )


def test_build_request_rejects_forged_delegation():
    env = build_reference_environment()
    forged = clone(env["grant"], maximum_amount=1_000_000)
    with pytest.raises(ControlPlaneError, match="DELEGATION_SIGNATURE_INVALID"):
        env["control_plane"].build_request(
            env["context"],
            "procurement-agent",
            forged,
            proposal(),
            environment="production",
            now=REFERENCE_TIME,
        )


@pytest.mark.parametrize(
    "grant_change",
    [
        {"tenant_id": TENANT_GLOBEX},
        {"principal_id": "user:attacker"},
        {"workload_id": "spiffe://evil.example/workload"},
        {"agent_id": "different-agent"},
        {"environment": "development"},
    ],
)
def test_build_request_rejects_every_delegation_binding_mismatch(grant_change):
    env = build_reference_environment()
    forged = clone(env["grant"], **grant_change)
    # Re-signing is unavailable to agent/model callers; signature fails before binding.
    with pytest.raises(ControlPlaneError):
        env["control_plane"].build_request(
            env["context"],
            "procurement-agent",
            forged,
            proposal(),
            environment="production",
            now=REFERENCE_TIME,
        )


def test_build_request_rejects_stale_delegation_policy():
    env = build_reference_environment()
    stale = clone(env["grant"], policy_version="old", signature="0" * 64)
    with pytest.raises(ControlPlaneError, match="DELEGATION_SIGNATURE_INVALID"):
        env["control_plane"].build_request(
            env["context"],
            "procurement-agent",
            stale,
            proposal(),
            environment="production",
            now=REFERENCE_TIME,
        )


def test_policy_bundle_binds_tenant_environment_and_threshold():
    original = issue_policy_bundle()
    different_threshold = issue_policy_bundle(approval_threshold=5_000)
    different_tenant = issue_policy_bundle(tenant_id=TENANT_GLOBEX)
    assert (
        len({original.digest, different_threshold.digest, different_tenant.digest}) == 3
    )
    env = build_reference_environment()
    wrong_scope = ControlPlane(env["registry"], different_tenant)
    with pytest.raises(ControlPlaneError, match="POLICY_SCOPE_MISMATCH"):
        wrong_scope.build_request(
            env["context"],
            "procurement-agent",
            env["grant"],
            proposal(),
            environment="production",
            now=REFERENCE_TIME,
        )


def test_small_purchase_order_is_allowed():
    env, request = request_for(amount=5_000)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    assert decision.effect == DecisionEffect.ALLOW
    assert decision.action_digest == request.action_digest


def test_large_purchase_order_requires_action_bound_approval():
    env, request = request_for(amount=25_000)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    assert decision.effect == DecisionEffect.ESCALATE
    assert set(decision.obligations) >= {
        "ACTION_BOUND_APPROVAL",
        "SINGLE_USE_EXECUTION",
    }


@pytest.mark.parametrize(
    ("item", "reason"),
    [
        (proposal(operation="execute_payment"), "DIRECT_PAYMENT_PROHIBITED"),
        (
            proposal(resource_id="cost-center:globex:finance"),
            "RESOURCE_OUTSIDE_DELEGATION",
        ),
        (proposal(amount=60_000), "AMOUNT_OUTSIDE_DELEGATION"),
        (proposal(purpose="different-purpose"), "PURPOSE_MISMATCH"),
        (clone(proposal(), schema_version="purchase-order/99"), "TOOL_SCHEMA_MISMATCH"),
        (clone(proposal(), tool_version="99.0.0"), "TOOL_VERSION_MISMATCH"),
    ],
)
def test_decision_plane_rejects_unsafe_proposals(item, reason):
    env, request = request_for(item)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    assert decision.effect == DecisionEffect.DENY
    assert reason in decision.reason_codes


def test_sensitive_field_is_constrained_and_removed():
    env, request = request_for(
        proposal(
            tool_id="vendor.read",
            operation="read_vendor",
            resource_id="vendor:acme:42",
            requested_fields=("name", "bank_account"),
        )
    )
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    constrained = enforce_constraints(request, decision)
    assert decision.effect == DecisionEffect.CONSTRAIN
    assert constrained.proposal.requested_fields == ("name",)
    assert constrained.action_digest != request.action_digest


def test_read_only_mode_blocks_mutation_but_not_read():
    env, write = request_for(amount=1_000)
    env["control_plane"].mode = OperationMode.READ_ONLY
    assert (
        env["control_plane"].decide(write, env["grant"], now=REFERENCE_TIME).effect
        == DecisionEffect.DENY
    )
    _, read = request_for(
        proposal(
            tool_id="vendor.read", operation="read_vendor", resource_id="vendor:acme:42"
        )
    )
    assert (
        env["control_plane"].decide(read, env["grant"], now=REFERENCE_TIME).effect
        == DecisionEffect.ALLOW
    )


def test_stopped_mode_denies_everything():
    env, request = request_for(
        proposal(
            tool_id="vendor.read", operation="read_vendor", resource_id="vendor:acme:42"
        )
    )
    env["control_plane"].mode = OperationMode.STOPPED
    assert (
        "CONTROL_PLANE_STOPPED"
        in env["control_plane"]
        .decide(request, env["grant"], now=REFERENCE_TIME)
        .reason_codes
    )


def test_suspended_agent_is_denied_at_decision_time():
    env, request = request_for()
    env["registry"].transition_agent(
        TENANT_ACME, "procurement-agent", Lifecycle.SUSPENDED, 1
    )
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    assert decision.effect == DecisionEffect.DENY
    assert "AGENT_NOT_ACTIVE" in decision.reason_codes


def test_policy_signature_tampering_fails_closed():
    env, request = request_for()
    env["control_plane"].policy = clone(
        env["control_plane"].policy, ruleset="attacker-rule"
    )
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    assert "POLICY_SIGNATURE_INVALID" in decision.reason_codes


def test_expired_policy_bundle_fails_closed():
    env, request = request_for()
    cp = ControlPlane(env["registry"], issue_policy_bundle(expires_at=REFERENCE_TIME))
    assert (
        "POLICY_BUNDLE_EXPIRED"
        in cp.decide(request, env["grant"], now=REFERENCE_TIME).reason_codes
    )


def test_outage_allows_only_fresh_low_risk_last_known_good_read():
    env, read = request_for(
        proposal(
            tool_id="vendor.read", operation="read_vendor", resource_id="vendor:acme:42"
        )
    )
    cp = ControlPlane(env["registry"], issue_policy_bundle(), policy_available=False)
    decision = cp.decide(read, env["grant"], now=REFERENCE_TIME + timedelta(minutes=10))
    assert decision.effect == DecisionEffect.ALLOW
    assert decision.used_last_known_good
    _, write = request_for()
    blocked = cp.decide(write, env["grant"], now=REFERENCE_TIME + timedelta(minutes=10))
    assert blocked.effect == DecisionEffect.DENY
    assert "POLICY_SERVICE_UNAVAILABLE" in blocked.reason_codes


def test_stale_last_known_good_read_fails_closed():
    env, read = request_for(
        proposal(
            tool_id="vendor.read", operation="read_vendor", resource_id="vendor:acme:42"
        )
    )
    cp = ControlPlane(
        env["registry"],
        issue_policy_bundle(expires_at=REFERENCE_TIME + timedelta(hours=1)),
        policy_available=False,
    )
    decision = cp.decide(read, env["grant"], now=REFERENCE_TIME + timedelta(minutes=16))
    assert decision.effect == DecisionEffect.DENY


def test_approval_requires_correct_role():
    env, request = request_for(amount=25_000)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    with pytest.raises(ControlPlaneError, match="APPROVER_ROLE_INVALID"):
        issue_approval(
            decision,
            tenant_id=TENANT_ACME,
            approver_id="user:peer",
            approver_role="requester",
        )


def test_approval_is_only_issued_for_escalation():
    env, request = request_for(amount=5_000)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    with pytest.raises(ControlPlaneError, match="APPROVAL_NOT_REQUIRED"):
        issue_approval(
            decision,
            tenant_id=TENANT_ACME,
            approver_id="user:director",
            approver_role="procurement-director",
        )


def test_approval_mutation_invalidates_action_binding():
    env, request = request_for(amount=25_000)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    approval = issue_approval(
        decision,
        tenant_id=TENANT_ACME,
        approver_id="user:director",
        approver_role="procurement-director",
    )
    mutated = request.model_copy(
        update={"proposal": request.proposal.model_copy(update={"amount": 25_001})}
    )
    with pytest.raises(ControlPlaneError, match="APPROVAL_ACTION_MISMATCH"):
        ApprovalLedger().consume(approval, mutated, decision, REFERENCE_TIME)


def test_approval_tampering_and_expiry_are_rejected():
    env, request = request_for(amount=25_000)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    approval = issue_approval(
        decision,
        tenant_id=TENANT_ACME,
        approver_id="user:director",
        approver_role="procurement-director",
    )
    with pytest.raises(ControlPlaneError, match="APPROVAL_SIGNATURE_INVALID"):
        ApprovalLedger().consume(
            clone(approval, approver_id="attacker"), request, decision, REFERENCE_TIME
        )
    with pytest.raises(ControlPlaneError, match="APPROVAL_EXPIRED"):
        ApprovalLedger().consume(
            approval, request, decision, REFERENCE_TIME + timedelta(minutes=6)
        )


def test_approval_binds_decision_policy_and_registry_versions():
    env, request = request_for(amount=25_000)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    approval = issue_approval(
        decision,
        tenant_id=TENANT_ACME,
        approver_id="user:director",
        approver_role="procurement-director",
    )
    changed = decision.model_copy(update={"tool_registry_version": 2})
    with pytest.raises(ControlPlaneError, match="APPROVAL_REGISTRY_MISMATCH"):
        ApprovalLedger().consume(approval, request, changed, REFERENCE_TIME)


def test_approval_consumption_is_atomic_under_concurrency():
    env, request = request_for(amount=25_000)
    decision = env["control_plane"].decide(request, env["grant"], now=REFERENCE_TIME)
    approval = issue_approval(
        decision,
        tenant_id=TENANT_ACME,
        approver_id="user:director",
        approver_role="procurement-director",
    )
    ledger = ApprovalLedger()

    def consume():
        try:
            ledger.consume(approval, request, decision, REFERENCE_TIME)
            return "ok"
        except ControlPlaneError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: consume(), range(2)))
    assert sorted(outcomes) == ["APPROVAL_ALREADY_CONSUMED", "ok"]


def test_gateway_never_executes_denied_action():
    env, request = request_for(proposal(operation="execute_payment"))
    gateway = ToolGateway(
        env["control_plane"], env["adapter"], env["approvals"], env["evidence"]
    )
    with pytest.raises(ControlPlaneError):
        gateway.execute(request, env["grant"], now=REFERENCE_TIME)
    assert env["adapter"].calls == 0


def test_gateway_requires_approval_for_escalated_action():
    env, request = request_for(amount=25_000)
    gateway = ToolGateway(
        env["control_plane"], env["adapter"], env["approvals"], env["evidence"]
    )
    with pytest.raises(ControlPlaneError, match="APPROVAL_REQUIRED"):
        gateway.execute(request, env["grant"], now=REFERENCE_TIME)
    assert env["adapter"].calls == 0


def test_gateway_executes_and_verifies_approved_action():
    run = build_course15_reference_run()
    assert run["decision"].effect == DecisionEffect.ESCALATE
    assert run["receipt"].outcome_state == OutcomeState.VERIFIED
    assert run["receipt"].action_digest == run["request"].action_digest
    assert run["evidence"].verify()


def test_gateway_execution_grant_is_single_use():
    env, request = request_for()
    gateway = ToolGateway(
        env["control_plane"], env["adapter"], env["approvals"], env["evidence"]
    )
    gateway.execute(request, env["grant"], now=REFERENCE_TIME)
    with pytest.raises(ControlPlaneError, match="EXECUTION_GRANT_ALREADY_CONSUMED"):
        gateway.execute(request, env["grant"], now=REFERENCE_TIME)
    assert env["adapter"].calls == 1


def test_adapter_idempotency_avoids_duplicate_external_effect():
    env, request = request_for()
    first = env["adapter"].execute(request)
    second = env["adapter"].execute(request)
    assert first == second
    assert env["adapter"].calls == 1


def test_unknown_outcome_is_reconciled_before_retry():
    env, request = request_for()
    first = env["adapter"].execute(request, simulate_timeout=True)
    assert first.outcome_state == OutcomeState.UNKNOWN
    reconciled = env["adapter"].reconcile(request.proposal.idempotency_key, request)
    assert reconciled.outcome_state == OutcomeState.VERIFIED
    assert env["adapter"].calls == 1


def test_gateway_reconciles_unknown_without_second_mutation():
    env, request = request_for()
    gateway = ToolGateway(
        env["control_plane"], env["adapter"], env["approvals"], env["evidence"]
    )
    _, unknown = gateway.execute(
        request, env["grant"], now=REFERENCE_TIME, simulate_timeout=True
    )
    assert unknown.outcome_state == OutcomeState.UNKNOWN
    reconciled = gateway.reconcile_unknown(
        request, now=REFERENCE_TIME + timedelta(seconds=1)
    )
    assert reconciled.outcome_state == OutcomeState.VERIFIED
    assert env["adapter"].calls == 1
    assert env["evidence"].entries[-1].event_type == "reconciliation"


def test_reconciliation_is_bound_to_exact_action():
    env, request = request_for()
    env["adapter"].execute(request, simulate_timeout=True)
    changed = request.model_copy(
        update={"proposal": request.proposal.model_copy(update={"amount": 5001})}
    )
    with pytest.raises(ControlPlaneError, match="RECONCILIATION_BINDING_INVALID"):
        env["adapter"].reconcile(request.proposal.idempotency_key, changed)


def test_evidence_chain_detects_tampering():
    log = EvidenceLog()
    entry = log.append(
        "decision", {"x": 1}, TENANT_ACME, POLICY_VERSION, "allow", REFERENCE_TIME
    )
    assert log.verify()
    log._entries[0] = clone(entry, outcome="deny")
    assert not log.verify()


def test_evidence_stores_digests_not_raw_prompt_or_secret():
    log = EvidenceLog()
    secret = "super-secret-vendor-bank-account"
    entry = log.append(
        "decision",
        {"prompt": secret},
        TENANT_ACME,
        POLICY_VERSION,
        "deny",
        REFERENCE_TIME,
    )
    assert secret not in entry.model_dump_json()
    assert len(entry.subject_digest) == 64


def test_evidence_sequence_and_previous_hash_are_continuous():
    log = EvidenceLog()
    first = log.append(
        "decision", 1, TENANT_ACME, POLICY_VERSION, "allow", REFERENCE_TIME
    )
    second = log.append(
        "outcome", 2, TENANT_ACME, POLICY_VERSION, "verified", REFERENCE_TIME
    )
    assert second.sequence == 2
    assert second.previous_hash == first.entry_hash


def test_scenarios_cover_allow_deny_escalate_and_constrain():
    scenarios = build_scenarios()
    assert len(scenarios) == 12
    assert {item.expected_effect for item in scenarios} == set(DecisionEffect)
    assert {item.mode for item in scenarios} == set(OperationMode)
    assert {item.policy_available for item in scenarios} == {True, False}


def test_governed_control_plane_matches_all_expected_decisions():
    report = evaluate_control_plane()
    assert (report.correct_decisions, report.scenario_population) == (12, 12)
    assert report.forbidden_outcomes == 0
    assert report.valid_work_blocked == 0


def test_prompt_only_baseline_exposes_forbidden_outcomes():
    report = evaluate_prompt_only_baseline()
    assert report.forbidden_outcomes == 8
    assert report.correct_decisions == 2


def test_shadow_policy_does_not_replace_enforced_policy():
    env, request = request_for()
    candidate = ControlPlane(
        env["registry"], issue_policy_bundle(POLICY_CANDIDATE_VERSION)
    )
    # The candidate needs a matching delegation only for request construction, not shadow evaluation.
    comparison = shadow_compare(
        request, env["grant"], env["control_plane"], candidate, now=REFERENCE_TIME
    )
    assert comparison["enforced_policy"] == POLICY_VERSION
    assert comparison["shadow_policy"] == POLICY_CANDIDATE_VERSION
    assert comparison["enforced_effect"] == DecisionEffect.ALLOW


def test_shadow_release_report_binds_candidate_and_exact_population():
    active = issue_policy_bundle()
    candidate = issue_policy_bundle(POLICY_CANDIDATE_VERSION)
    report = evaluate_shadow_rollout(active, candidate)
    assert report.scenario_population == 12
    assert report.candidate_policy_digest == candidate.digest
    assert report.candidate_incorrect_count == 0
    assert report.forbidden_permit_count == 0


def test_policy_activation_requires_current_clean_shadow_evidence():
    active = issue_policy_bundle()
    candidate = issue_policy_bundle(POLICY_CANDIDATE_VERSION)
    report = evaluate_shadow_rollout(active, candidate)
    receipt = authorize_policy_activation(
        candidate,
        report,
        build_operator("policy-admin"),
        now=REFERENCE_TIME + timedelta(minutes=1),
    )
    replica = PolicyReplica("pdp-1", TENANT_ACME, "production")
    replica.activate(candidate, receipt)
    assert replica.active == candidate


def test_policy_activation_blocks_regression_and_cross_scope_replica():
    active = issue_policy_bundle()
    regressing = issue_policy_bundle(POLICY_CANDIDATE_VERSION, approval_threshold=4_000)
    report = evaluate_shadow_rollout(active, regressing)
    assert report.candidate_incorrect_count > 0
    with pytest.raises(ControlPlaneError, match="SHADOW_RELEASE_GATE_FAILED"):
        authorize_policy_activation(
            regressing,
            report,
            build_operator("policy-admin"),
            now=REFERENCE_TIME + timedelta(minutes=1),
        )

    clean = issue_policy_bundle(POLICY_CANDIDATE_VERSION)
    clean_report = evaluate_shadow_rollout(active, clean)
    receipt = authorize_policy_activation(
        clean,
        clean_report,
        build_operator("policy-admin"),
        now=REFERENCE_TIME + timedelta(minutes=1),
    )
    with pytest.raises(ControlPlaneError, match="REPLICA_POLICY_SCOPE_MISMATCH"):
        PolicyReplica("pdp-globex", TENANT_GLOBEX, "production").activate(
            clean, receipt
        )


def test_interoperability_map_covers_common_control_plane_technologies():
    mappings = interoperability_map()
    text = " ".join(item.common_technology for item in mappings)
    for name in (
        "OPA",
        "Cedar",
        "OpenFGA",
        "SPIFFE",
        "Envoy",
        "RFC 8693",
        "MCP",
        "OpenTelemetry",
    ):
        assert name in text
    assert all(item.control_plane_responsibility for item in mappings)


def test_real_sdk_artifacts_are_offline_and_versioned():
    artifacts = build_sdk_artifacts()
    assert type(artifacts["opa_client"]).__name__ == "OpaClient"
    assert type(artifacts["openfga_configuration"]).__name__ == "ClientConfiguration"
    assert set(artifacts["versions"]) == {
        "opa-python-client",
        "openfga_sdk",
        "opentelemetry-sdk",
        "mcp",
    }
    assert "default decision" in artifacts["rego_policy"]
    assert "permit" in artifacts["cedar_policy"]
    assert "schema 1.1" in artifacts["openfga_model"]
    artifacts["opa_client"]._session.close()


def test_otel_demo_uses_in_memory_export_and_minimized_attributes():
    spans = build_otel_demo()
    assert len(spans) == 1
    assert spans[0]["name"] == "governance.authorize"
    attrs = spans[0]["attributes"]
    assert attrs["governance.policy.version"] == POLICY_VERSION
    assert not any("prompt" in key or "token" in key for key in attrs)


def test_reference_run_links_proposal_decision_effect_and_outcome():
    run = build_course15_reference_run()
    assert run["request"].action_digest == run["decision"].action_digest
    assert run["request"].action_digest == run["receipt"].action_digest
    assert len(run["evidence"].entries) == 2
    assert {entry.event_type for entry in run["evidence"].entries} == {
        "decision",
        "outcome",
    }
