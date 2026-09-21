from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import importlib.util
from pathlib import Path
import sys

import pytest


@pytest.fixture()
def lab():
    path = (
        Path(__file__).parents[1]
        / "curriculum/intermediate/06-policy-as-code-and-runtime-governance/lab.py"
    )
    spec = importlib.util.spec_from_file_location("module06_lab", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_valid_bundle_and_decision_are_versioned_and_digest_bound(lab):
    bundle = lab.stable_bundle()
    report = lab.validate_bundle(bundle)
    context = lab.demo_context()
    proposal = lab.demo_proposal()
    facts = lab.demo_facts(proposal)
    decision = lab.evaluate_policy(bundle, context, proposal, facts, now=lab.REFERENCE_TIME)

    assert report.valid is True
    assert decision.outcome is lab.Outcome.ALLOW
    assert decision.bundle_version == bundle.version
    assert decision.bundle_revision == bundle.revision
    assert decision.bundle_digest == bundle.digest
    assert decision.input_digest == lab.resolve_input_digest(context, proposal, facts)


@pytest.mark.parametrize(
    ("fact_updates", "reason"),
    [
        ({"authorization_permitted": False}, "authorization_denied"),
        ({"vendor_approved": False}, "vendor_not_approved"),
        ({"vendor_sanctioned": True}, "vendor_sanctioned"),
        ({"tenant_id": "tenant:other"}, "facts_tenant_mismatch"),
        ({"risk_basis_points": 8_000}, "risk_hard_limit_reached"),
    ],
)
def test_hard_denials_dominate_other_domains(lab, fact_updates, reason):
    context = lab.demo_context()
    proposal = lab.demo_proposal(amount_cents=600_000)
    facts = lab.demo_facts(proposal, **fact_updates)
    decision = lab.evaluate_policy(
        lab.stable_bundle(), context, proposal, facts, now=lab.REFERENCE_TIME
    )
    assert decision.outcome is lab.Outcome.DENY
    assert reason in decision.reason_codes


def test_amount_and_risk_thresholds_escalate_instead_of_executing(lab):
    for proposal, risk in (
        (lab.demo_proposal(amount_cents=500_001), 2_000),
        (lab.demo_proposal(operation_id="OP-RISK", amount_cents=100), 5_000),
    ):
        facts = lab.demo_facts(proposal, risk_basis_points=risk)
        decision = lab.evaluate_policy(
            lab.stable_bundle(), lab.demo_context(), proposal, facts, now=lab.REFERENCE_TIME
        )
        assert decision.outcome is lab.Outcome.ESCALATE


@pytest.mark.parametrize(
    ("proposal_updates", "fact_updates", "expected"),
    [
        ({"amount_cents": 500_001}, {}, "escalate"),
        ({}, {"vendor_sanctioned": True}, "deny"),
    ],
)
def test_non_allow_decisions_never_reach_the_effect_adapter(
    lab, proposal_updates, fact_updates, expected
):
    _, gateway, adapter = lab.build_demo_gateway()
    proposal = lab.demo_proposal(**proposal_updates)
    result = gateway.execute(
        lab.demo_context(),
        proposal,
        lab.demo_facts(proposal, **fact_updates),
        now=lab.REFERENCE_TIME,
    )
    assert result.decision.enforced.outcome.value == expected
    assert result.effect.status is lab.EffectStatus.NOT_ATTEMPTED
    assert adapter.applied_count == 0


def test_missing_stale_and_request_mismatched_facts_fail_closed(lab):
    context = lab.demo_context()
    proposal = lab.demo_proposal()
    missing = lab.evaluate_policy(
        lab.stable_bundle(), context, proposal, None, now=lab.REFERENCE_TIME
    )
    stale_facts = lab.demo_facts(proposal, valid_until=lab.REFERENCE_TIME)
    stale = lab.evaluate_policy(
        lab.stable_bundle(), context, proposal, stale_facts, now=lab.REFERENCE_TIME
    )
    other = lab.demo_proposal(operation_id="OP-OTHER")
    mismatched = lab.evaluate_policy(
        lab.stable_bundle(), context, proposal, lab.demo_facts(other), now=lab.REFERENCE_TIME
    )

    assert missing.outcome is lab.Outcome.DENY
    assert "trusted_facts_missing" in missing.reason_codes
    assert "trusted_facts_not_current" in stale.reason_codes
    assert {"facts_operation_mismatch", "facts_proposal_mismatch"}.issubset(
        mismatched.reason_codes
    )


def test_expired_authenticated_context_fails_closed(lab):
    proposal = lab.demo_proposal()
    context = lab.demo_context(valid_until=lab.REFERENCE_TIME)
    decision = lab.evaluate_policy(
        lab.stable_bundle(),
        context,
        proposal,
        lab.demo_facts(proposal),
        now=lab.REFERENCE_TIME,
    )
    assert decision.outcome is lab.Outcome.DENY
    assert "identity_context_not_current" in decision.reason_codes


def test_model_claims_cannot_override_authoritative_facts(lab):
    proposal = lab.demo_proposal(
        model_claimed_approval=True, model_claimed_vendor_safe=True
    )
    facts = lab.demo_facts(proposal, vendor_sanctioned=True)
    decision = lab.evaluate_policy(
        lab.stable_bundle(), lab.demo_context(), proposal, facts, now=lab.REFERENCE_TIME
    )
    assert decision.outcome is lab.Outcome.DENY
    assert "vendor_sanctioned" in decision.reason_codes


def test_restricted_data_to_external_destination_is_denied(lab):
    proposal = lab.demo_proposal(
        data_classification="restricted", destination="external-webhook"
    )
    decision = lab.evaluate_policy(
        lab.stable_bundle(),
        lab.demo_context(),
        proposal,
        lab.demo_facts(proposal),
        now=lab.REFERENCE_TIME,
    )
    assert decision.outcome is lab.Outcome.DENY
    assert decision.reason_codes == ("restricted_data_external_destination",)


def test_static_validation_rejects_schema_domain_and_threshold_defects(lab):
    bundle = lab.stable_bundle().model_copy(
        update={
            "version": "invalid",
            "required_domains": frozenset({"authorization"}),
            "rules": lab.PolicyRules(
                schema_version="wrong/v9",
                approval_threshold_cents=3_000_000,
                hard_amount_limit_cents=2_000_000,
                risk_escalation_basis_points=9_000,
                risk_deny_basis_points=8_000,
            ),
        }
    )
    report = lab.validate_bundle(bundle)
    assert report.valid is False
    assert {item.code for item in report.findings} == {
        "schema_version_mismatch",
        "required_domain_missing",
        "amount_thresholds_unsatisfiable",
        "risk_thresholds_unsatisfiable",
    }


def test_versions_are_immutable_and_invalid_bundles_are_not_registered(lab):
    control = lab.PolicyControlPlane(lab.stable_bundle())
    with pytest.raises(ValueError, match="already exists"):
        control.register(lab.stable_bundle())
    invalid = lab.stable_bundle().model_copy(
        update={
            "version": "bad",
            "rules": lab.PolicyRules(schema_version="unknown/v2"),
        }
    )
    report = control.register(invalid)
    assert report.valid is False
    with pytest.raises(KeyError):
        control.start_shadow("bad")


def test_shadow_candidate_is_evaluated_but_never_enforced(lab):
    control, gateway, adapter = lab.build_demo_gateway()
    active = lab.stable_bundle()
    candidate = active.model_copy(
        update={
            "version": "procurement-policy-1.1.0",
            "revision": "git:bbbbbbb",
            "stage": lab.ReleaseStage.DRAFT,
            "rules": active.rules.model_copy(update={"approval_threshold_cents": 100_000}),
        }
    )
    assert control.register(candidate).valid
    control.start_shadow(candidate.version)
    proposal = lab.demo_proposal()
    result = gateway.execute(
        lab.demo_context(), proposal, lab.demo_facts(proposal), now=lab.REFERENCE_TIME
    )

    assert result.decision.enforced.outcome is lab.Outcome.ALLOW
    assert result.decision.shadow.outcome is lab.Outcome.ESCALATE
    assert result.decision.rollout_stage is lab.ReleaseStage.SHADOW
    assert result.effect.status is lab.EffectStatus.APPLIED
    assert adapter.applied_count == 1


def test_canary_assignment_is_stable_and_records_enforced_version(lab):
    control, gateway, _ = lab.build_demo_gateway()
    active = lab.stable_bundle()
    candidate = active.model_copy(
        update={
            "version": "procurement-policy-1.1.0",
            "revision": "git:ccccccc",
            "stage": lab.ReleaseStage.DRAFT,
            "rules": active.rules.model_copy(update={"approval_threshold_cents": 100_000}),
        }
    )
    control.register(candidate)
    control.start_shadow(candidate.version)
    control.start_canary(candidate.version, 50)
    operation = next(
        f"OP-CANARY-{i}" for i in range(1000) if lab._in_canary(f"OP-CANARY-{i}", 50)
    )
    proposal = lab.demo_proposal(operation_id=operation)
    facts = lab.demo_facts(proposal)
    first = gateway.decide(lab.demo_context(), proposal, facts, now=lab.REFERENCE_TIME)
    second = gateway.decide(lab.demo_context(), proposal, facts, now=lab.REFERENCE_TIME)
    assert first.enforced.bundle_version == candidate.version
    assert first.enforced == second.enforced
    assert first.rollout_stage is lab.ReleaseStage.CANARY


def test_release_gate_blocks_mutation_detected_by_labelled_corpus(lab):
    active = lab.stable_bundle()
    mutant = lab.mutated_bundle()
    metrics = lab.shadow_metrics(active, mutant, lab.labelled_cases())
    assert metrics.false_permit_count == 0
    assert metrics.forbidden_not_denied_count == 1
    assert metrics.incorrect_case_count == 1
    control = lab.PolicyControlPlane(active)
    control.register(mutant)
    control.start_shadow(mutant.version)
    with pytest.raises(ValueError, match="safety regression"):
        control.promote(mutant.version, metrics)


def test_safe_candidate_can_promote_and_rollback_atomically(lab):
    active = lab.stable_bundle()
    candidate = active.model_copy(
        update={
            "version": "procurement-policy-1.0.1",
            "revision": "git:ddddddd",
            "stage": lab.ReleaseStage.DRAFT,
        }
    )
    control = lab.PolicyControlPlane(active)
    control.register(candidate)
    control.start_shadow(candidate.version)
    metrics = lab.shadow_metrics(active, candidate, lab.labelled_cases())
    assert metrics.disagreement_count == 0
    control.start_canary(candidate.version, 10)
    control.promote(candidate.version, metrics)
    promoted, _, _ = control.snapshot()
    assert promoted.version == candidate.version
    control.rollback(active.version)
    rolled_back, candidate_after, percent = control.snapshot()
    assert rolled_back.version == active.version
    assert candidate_after is None
    assert percent == 0


def test_policy_outage_fails_closed_and_never_calls_effect(lab):
    control, gateway, adapter = lab.build_demo_gateway()
    control.set_available(False)
    proposal = lab.demo_proposal()
    result = gateway.execute(
        lab.demo_context(), proposal, lab.demo_facts(proposal), now=lab.REFERENCE_TIME
    )
    assert result.decision.enforced.outcome is lab.Outcome.DENY
    assert result.decision.enforced.reason_codes == (
        "policy_control_plane_unavailable_fail_closed",
    )
    assert result.effect.status is lab.EffectStatus.NOT_ATTEMPTED
    assert adapter.applied_count == 0


def test_direct_effect_bypass_is_rejected(lab):
    _, _, adapter = lab.build_demo_gateway()
    with pytest.raises(PermissionError, match="RuntimeGateway"):
        adapter.apply("tenant:oneplusi", lab.demo_proposal())


def test_runtime_gateway_is_idempotent_and_detects_operation_mutation(lab):
    _, gateway, adapter = lab.build_demo_gateway()
    context = lab.demo_context()
    proposal = lab.demo_proposal()
    facts = lab.demo_facts(proposal)
    first = gateway.execute(context, proposal, facts, now=lab.REFERENCE_TIME)
    replay = gateway.execute(context, proposal, facts, now=lab.REFERENCE_TIME)
    changed = proposal.model_copy(update={"amount_cents": 400_000})
    collision = gateway.execute(
        context, changed, lab.demo_facts(changed), now=lab.REFERENCE_TIME
    )
    assert first.effect == replay.effect
    assert replay.decision.replayed is True
    assert collision.decision.enforced.outcome is lab.Outcome.DENY
    assert collision.decision.enforced.reason_codes == (
        "operation_id_reused_with_different_request",
    )
    assert adapter.applied_count == 1


def test_tenants_with_same_operation_id_receive_distinct_effects(lab):
    _, gateway, adapter = lab.build_demo_gateway()
    proposal = lab.demo_proposal()
    first_context = lab.demo_context()
    second_context = lab.demo_context(tenant_id="tenant:subsidiary")
    first = gateway.execute(
        first_context,
        proposal,
        lab.demo_facts(proposal),
        now=lab.REFERENCE_TIME,
    )
    second = gateway.execute(
        second_context,
        proposal,
        lab.demo_facts(proposal, tenant_id="tenant:subsidiary"),
        now=lab.REFERENCE_TIME,
    )
    assert first.effect.effect_id != second.effect.effect_id
    assert first.effect.tenant_id == "tenant:oneplusi"
    assert second.effect.tenant_id == "tenant:subsidiary"
    assert adapter.applied_count == 2


def test_concurrent_retries_apply_one_effect(lab):
    _, gateway, adapter = lab.build_demo_gateway()
    context = lab.demo_context()
    proposal = lab.demo_proposal()
    facts = lab.demo_facts(proposal)

    def execute_once(_index):
        return gateway.execute(context, proposal, facts, now=lab.REFERENCE_TIME)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(execute_once, range(8)))

    assert adapter.applied_count == 1
    assert len({item.effect.effect_id for item in results}) == 1
    assert sum(item.decision.replayed for item in results) == 7


def test_unknown_effect_is_reconciled_before_retry(lab, monkeypatch):
    _, gateway, adapter = lab.build_demo_gateway()
    context = lab.demo_context()
    proposal = lab.demo_proposal()
    facts = lab.demo_facts(proposal)

    def lose_response(*_args, **_kwargs):
        raise TimeoutError("effect outcome unknown")

    monkeypatch.setattr(adapter, "apply", lose_response)
    with pytest.raises(TimeoutError, match="unknown"):
        gateway.execute(context, proposal, facts, now=lab.REFERENCE_TIME)
    retry = gateway.execute(context, proposal, facts, now=lab.REFERENCE_TIME)
    assert retry.decision.replayed is True
    assert retry.effect.status is lab.EffectStatus.UNKNOWN
    assert adapter.applied_count == 0


def test_release_evidence_is_bound_to_exact_candidate(lab):
    active = lab.stable_bundle()
    candidate = active.model_copy(
        update={
            "version": "procurement-policy-1.0.1",
            "revision": "git:eeeeeee",
            "stage": lab.ReleaseStage.DRAFT,
        }
    )
    control = lab.PolicyControlPlane(active)
    control.register(candidate)
    control.start_shadow(candidate.version)
    control.start_canary(candidate.version, 10)
    metrics = lab.shadow_metrics(active, candidate, lab.labelled_cases())
    forged = metrics.model_copy(update={"candidate_bundle_digest": "0" * 64})
    with pytest.raises(ValueError, match="candidate bundle"):
        control.promote(candidate.version, forged)


def test_rollback_rejects_never_active_draft(lab):
    active = lab.stable_bundle()
    draft = active.model_copy(
        update={
            "version": "procurement-policy-draft",
            "revision": "git:fffffff",
            "stage": lab.ReleaseStage.DRAFT,
        }
    )
    control = lab.PolicyControlPlane(active)
    control.register(draft)
    with pytest.raises(ValueError, match="previously active"):
        control.rollback(draft.version)


def test_evidence_minimizes_sensitive_values_and_names_authoritative_versions(lab):
    _, gateway, _ = lab.build_demo_gateway()
    proposal = lab.demo_proposal()
    result = gateway.execute(
        lab.demo_context(), proposal, lab.demo_facts(proposal), now=lab.REFERENCE_TIME
    )
    assert result.decision.evidence_versions == (
        "authorization:authz-v12",
        "vendor:vendor-v31",
        "risk:risk-v9",
    )
    serialized = result.decision.model_dump_json()
    assert "vendor:acme" not in serialized
    assert "human:buyer-123" not in serialized
    event = gateway.audit_events[0]
    assert event.decision_id == result.decision.decision_id
    assert event.request_digest == result.decision.enforced.input_digest
    assert event.bundle_digest == lab.stable_bundle().digest
    assert "vendor:acme" not in event.model_dump_json()


def test_labelled_evaluation_defines_exact_metric_populations(lab):
    summary = lab.summarize_evaluation(lab.stable_bundle(), lab.labelled_cases())
    assert summary.case_count == 10
    assert summary.expected_allow_count == 2
    assert summary.expected_deny_count == 6
    assert summary.expected_escalate_count == 2
    assert summary.baseline_correct_count == 2
    assert summary.candidate_correct_count == 10
    assert summary.forbidden_case_count == 6
    assert summary.baseline_forbidden_allowed_count == 6
    assert summary.candidate_forbidden_allowed_count == 0
    assert summary.legitimate_case_count == 2
    assert summary.candidate_false_denial_count == 0
    assert summary.escalation_case_count == 2
    assert summary.baseline_missed_escalation_count == 2
    assert summary.candidate_missed_escalation_count == 0


def test_opa_mapping_uses_real_json_boundary_and_examples_are_default_deny(lab):
    context = lab.demo_context()
    proposal = lab.demo_proposal()
    facts = lab.demo_facts(proposal)
    payload = lab.opa_input(context, proposal, facts)
    assert payload["context"]["subject_id"] == context.subject_id
    assert payload["facts"]["proposal_digest"] == lab.stable_digest(proposal)
    assert "default decision" in lab.REGO_ARTIFACT
    assert "vendor_sanctioned" in lab.REGO_ARTIFACT
    assert "forbid" in lab.CEDAR_ARTIFACT
