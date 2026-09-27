"""Focused invariant and failure tests for Course 8."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import sys

import pytest


MODULE = Path(__file__).parents[1] / "curriculum/intermediate/08-human-oversight-and-bounded-autonomy"
sys.path.insert(0, str(MODULE))
sys.modules.pop("lab", None)

from lab import (  # noqa: E402
    ControlError,
    Route,
)

# Import separately to keep the invariant list readable.
from lab import (  # noqa: E402
    OperatorContext,
    OversightSystem,
    REFERENCE_TIME,
    ReviewChoice,
    ReviewEvent,
    WorkflowStatus,
    labelled_evaluation,
    microsoft_create_po,
    openai_create_po,
    reviewer_metrics,
    risk_basis_points,
    route_action,
    run_evaluation,
    sample_action,
    sample_context,
    sample_envelope,
    sample_facts,
    sample_reviewer,
    stable_digest,
)


def assert_error(code, function, *args, **kwargs):
    with pytest.raises(ControlError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code


def manager_approval(system, record):
    return system.review(
        record.workflow_id,
        record.version,
        sample_reviewer("manager"),
        ReviewChoice.APPROVE,
    )


def test_real_framework_descriptors_expose_approval_mechanisms():
    assert openai_create_po.name == "openai_create_po"
    assert openai_create_po.needs_approval is True
    assert microsoft_create_po.name == "microsoft_create_po"
    assert microsoft_create_po.approval_mode == "always_require"


def test_model_claims_do_not_change_routing():
    action = sample_action(model_claimed_risk="safe", model_claimed_approved=True, amount_cents=600_000)
    decision = route_action(sample_context(), action, sample_facts(), sample_envelope())
    assert decision.route is Route.APPROVE


@pytest.mark.parametrize(
    ("changes", "facts_changes", "expected", "reason"),
    [
        ({"tool_name": "payments.send"}, {}, Route.DENY, "TOOL_OUTSIDE_ENVELOPE"),
        ({"currency": "USD"}, {}, Route.DENY, "CURRENCY_NOT_ALLOWED"),
        ({"vendor_id": "VEN-303"}, {}, Route.DENY, "VENDOR_NOT_APPROVED"),
        ({"vendor_id": "VEN-999"}, {}, Route.DENY, "VENDOR_SANCTIONED"),
        ({"amount_cents": 5_500_000}, {"task_remaining_cents": 6_000_000}, Route.DENY, "HARD_AMOUNT_LIMIT"),
        ({}, {"incident_mode": "critical"}, Route.DENY, "CRITICAL_INCIDENT_STOP"),
        ({}, {"incident_mode": "elevated"}, Route.APPROVE, "ELEVATED_INCIDENT"),
        ({"reversible": False}, {}, Route.MULTI_APPROVE, "IRREVERSIBLE_ACTION"),
    ],
)
def test_hard_policy_and_dynamic_degradation(changes, facts_changes, expected, reason):
    decision = route_action(
        sample_context(), sample_action(**changes), sample_facts(**facts_changes), sample_envelope()
    )
    assert decision.route is expected
    assert decision.reason_codes == (reason,)


def test_risk_score_is_deterministic_and_monotonic_for_teaching_fixture():
    low = risk_basis_points(sample_action(amount_cents=50_000))
    high = risk_basis_points(
        sample_action(amount_cents=1_000_000, reversible=False, data_sensitivity=4, anomaly_basis_points=8_000)
    )
    assert low == risk_basis_points(sample_action(amount_cents=50_000))
    assert high > low


def test_auto_allow_executes_and_verifies_one_effect():
    system = OversightSystem(sample_envelope())
    context, facts, action = sample_context(), sample_facts(), sample_action()
    record = system.propose(context, action, facts)
    assert record.route is Route.AUTO_ALLOW
    assert record.status is WorkflowStatus.READY
    result = system.execute(record.workflow_id, record.version, context, facts)
    assert result.verified is True
    assert result.reason_code == "OUTCOME_VERIFIED"
    assert result.workflow.status is WorkflowStatus.COMPLETED


def test_outcome_verification_binds_the_vendor_as_well_as_value():
    from lab import EffectReceipt, verify_effect

    action = sample_action()
    wrong_vendor = EffectReceipt(
        effect_id="effect-foreign-vendor",
        tenant_id="tenant-north",
        operation_id=action.operation_id,
        vendor_id="VEN-202",
        amount_cents=action.amount_cents,
        currency=action.currency,
        status="created",
    )
    assert verify_effect(action, wrong_vendor) is False


def test_verification_route_requires_trusted_verification_receipt():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    action = sample_action(amount_cents=200_000)
    pending = system.propose(context, action, facts)
    assert pending.route is Route.VERIFY
    assert pending.status is WorkflowStatus.PENDING
    assert_error("WORKFLOW_NOT_READY", system.execute, pending.workflow_id, pending.version, context, facts)
    ready = system.verify(pending.workflow_id, pending.version, facts)
    assert ready.verification.action_digest == stable_digest(action)
    assert system.execute(ready.workflow_id, ready.version, context, facts).verified is True


def test_single_approval_is_exact_authorized_and_single_use():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    pending = system.propose(context, sample_action(amount_cents=600_000), facts)
    ready = manager_approval(system, pending)
    assert ready.status is WorkflowStatus.READY
    result = system.execute(ready.workflow_id, ready.version, context, facts)
    assert result.verified
    assert_error(
        "WORKFLOW_NOT_REVIEWABLE",
        system.review,
        ready.workflow_id,
        result.workflow.version,
        sample_reviewer("manager", reviewer_id="usr-manager-NEW"),
        ReviewChoice.APPROVE,
    )


def test_separation_of_duties_and_reviewer_authority_are_enforced():
    system = OversightSystem(sample_envelope())
    pending = system.propose(sample_context(), sample_action(amount_cents=600_000), sample_facts())
    requester = sample_reviewer("manager", reviewer_id="usr-requester-1042")
    assert_error("SEPARATION_OF_DUTIES", system.review, pending.workflow_id, pending.version, requester, ReviewChoice.APPROVE)
    stranger = sample_reviewer("auditor")
    assert_error("REVIEWER_NOT_AUTHORIZED", system.review, pending.workflow_id, pending.version, stranger, ReviewChoice.APPROVE)


def test_reviewer_identity_and_tenant_come_from_authenticated_context():
    system = OversightSystem(sample_envelope())
    pending = system.propose(sample_context(), sample_action(amount_cents=600_000), sample_facts())
    wrong_tenant = sample_reviewer("manager", tenant_id="tenant-south")
    assert_error("REVIEWER_TENANT_MISMATCH", system.review, pending.workflow_id, pending.version, wrong_tenant, ReviewChoice.APPROVE)
    expired = sample_reviewer("manager", valid_until=REFERENCE_TIME - timedelta(seconds=1))
    assert_error("REVIEWER_AUTHENTICATION_STALE", system.review, pending.workflow_id, pending.version, expired, ReviewChoice.APPROVE)


def test_rejection_is_terminal_and_cannot_be_overridden():
    system = OversightSystem(sample_envelope())
    pending = system.propose(sample_context(), sample_action(amount_cents=600_000), sample_facts())
    rejected = system.review(pending.workflow_id, pending.version, sample_reviewer(), ReviewChoice.REJECT)
    assert rejected.status is WorkflowStatus.REJECTED
    assert_error("WORKFLOW_NOT_READY", system.execute, rejected.workflow_id, rejected.version, sample_context(), sample_facts())


def test_multi_party_approval_requires_distinct_roles_and_people():
    system = OversightSystem(sample_envelope())
    pending = system.propose(sample_context(), sample_action(amount_cents=2_000_000), sample_facts())
    one = system.review(pending.workflow_id, pending.version, sample_reviewer("manager"), ReviewChoice.APPROVE)
    assert one.status is WorkflowStatus.PENDING
    assert_error(
        "REVIEW_ROLE_ALREADY_FILLED",
        system.review,
        one.workflow_id,
        one.version,
        sample_reviewer("manager", reviewer_id="usr-manager-2002"),
        ReviewChoice.APPROVE,
    )
    ready = system.review(one.workflow_id, one.version, sample_reviewer("finance"), ReviewChoice.APPROVE)
    assert ready.status is WorkflowStatus.READY
    assert {d.reviewer_role for d in ready.decisions} == {"manager", "finance"}


def test_expired_request_fails_closed():
    system = OversightSystem(sample_envelope())
    pending = system.propose(sample_context(), sample_action(amount_cents=600_000), sample_facts())
    expired = system.review(
        pending.workflow_id,
        pending.version,
        sample_reviewer(valid_until=REFERENCE_TIME + timedelta(hours=6)),
        ReviewChoice.APPROVE,
        now=REFERENCE_TIME + timedelta(hours=5),
    )
    assert expired.status is WorkflowStatus.EXPIRED
    assert expired.terminal_reason == "APPROVAL_EXPIRED"


def test_optimistic_version_prevents_concurrent_duplicate_reviews():
    system = OversightSystem(sample_envelope())
    pending = system.propose(sample_context(), sample_action(amount_cents=600_000), sample_facts())

    def submit(index):
        try:
            system.review(
                pending.workflow_id,
                pending.version,
                sample_reviewer("manager", reviewer_id=f"usr-manager-{index}"),
                ReviewChoice.APPROVE,
            )
            return "accepted"
        except ControlError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(submit, range(8)))
    assert results.count("accepted") == 1
    assert results.count("VERSION_CONFLICT") == 7


def test_same_operation_is_idempotent_but_changed_request_is_rejected():
    system = OversightSystem(sample_envelope())
    context, facts, action = sample_context(), sample_facts(), sample_action()
    first = system.propose(context, action, facts)
    assert system.propose(context, action, facts) == first
    assert_error(
        "OPERATION_MUTATION",
        system.propose,
        context,
        action.model_copy(update={"amount_cents": 60_000}),
        facts,
    )


def test_redirect_invalidates_prior_approval_and_rebinds_digest():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    pending = system.propose(context, sample_action(amount_cents=600_000), facts)
    ready = manager_approval(system, pending)
    old_digest = ready.approval.action_digest
    operator = OperatorContext(operator_id="ops-1", tenant_id=context.tenant_id, roles=frozenset({"oversight_operator"}))
    redirected = system.redirect(
        ready.workflow_id,
        ready.version,
        operator,
        sample_action(operation_id="OP-1001", amount_cents=700_000),
        context,
        facts,
    )
    assert redirected.status is WorkflowStatus.PENDING
    assert redirected.decisions == ()
    assert redirected.approval.action_digest != old_digest


def test_redirect_to_verification_band_cannot_skip_verification():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    original = system.propose(context, sample_action(amount_cents=600_000), facts)
    ready = manager_approval(system, original)
    operator = OperatorContext(
        operator_id="ops-1",
        tenant_id=context.tenant_id,
        roles=frozenset({"oversight_operator"}),
    )
    redirected = system.redirect(
        ready.workflow_id,
        ready.version,
        operator,
        sample_action(operation_id="OP-1001", amount_cents=200_000),
        context,
        facts,
    )
    assert redirected.route is Route.VERIFY
    assert redirected.status is WorkflowStatus.PENDING
    assert redirected.verification is None
    assert_error(
        "WORKFLOW_NOT_READY",
        system.execute,
        redirected.workflow_id,
        redirected.version,
        context,
        facts,
    )


def test_terminate_revokes_pending_authority():
    system = OversightSystem(sample_envelope())
    pending = system.propose(sample_context(), sample_action(amount_cents=600_000), sample_facts())
    operator = OperatorContext(operator_id="ops-1", tenant_id="tenant-north", roles=frozenset({"oversight_operator"}))
    terminated = system.terminate(pending.workflow_id, pending.version, operator)
    assert terminated.status is WorkflowStatus.TERMINATED
    assert_error("WORKFLOW_NOT_READY", system.execute, terminated.workflow_id, terminated.version, sample_context(), sample_facts())


def test_pause_stops_next_effect_and_resume_revalidates_route_and_facts_version():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    ready = system.propose(context, sample_action(), facts)
    operator = OperatorContext(operator_id="ops-1", tenant_id="tenant-north", roles=frozenset({"oversight_operator"}))
    paused = system.pause(ready.workflow_id, ready.version, operator)
    assert paused.status is WorkflowStatus.PAUSED
    assert_error("WORKFLOW_NOT_READY", system.execute, paused.workflow_id, paused.version, context, facts)
    changed = facts.model_copy(update={"source_version": "procurement-facts/next"})
    assert_error(
        "OVERSIGHT_REEVALUATION_REQUIRED",
        system.resume,
        paused.workflow_id,
        paused.version,
        operator,
        context,
        changed,
    )
    resumed = system.resume(paused.workflow_id, paused.version, operator, context, facts)
    assert resumed.status is WorkflowStatus.READY


def test_policy_and_facts_are_revalidated_after_approval():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    pending = system.propose(context, sample_action(amount_cents=600_000), facts)
    ready = manager_approval(system, pending)
    changed_facts = facts.model_copy(update={"sanctioned_vendors": frozenset({"VEN-101"})})
    assert_error("VENDOR_SANCTIONED", system.execute, ready.workflow_id, ready.version, context, changed_facts)

    other = OversightSystem(sample_envelope())
    ready2 = manager_approval(other, other.propose(context, sample_action(operation_id="OP-POLICY", amount_cents=600_000), facts))
    other.envelope = sample_envelope(policy_version="oversight-policy/next")
    assert_error("POLICY_CHANGED", other.execute, ready2.workflow_id, ready2.version, context, facts)

    third = OversightSystem(sample_envelope())
    ready3 = manager_approval(third, third.propose(context, sample_action(operation_id="OP-FACTS", amount_cents=600_000), facts))
    new_version = facts.model_copy(update={"source_version": "procurement-facts/next"})
    assert_error("TRUSTED_FACTS_CHANGED", third.execute, ready3.workflow_id, ready3.version, context, new_version)


def test_storage_tampering_is_detected_before_execution():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    ready = manager_approval(system, system.propose(context, sample_action(amount_cents=600_000), facts))
    tampered = ready.model_copy(update={"action": ready.action.model_copy(update={"amount_cents": 700_000})})
    system._records[ready.workflow_id] = tampered
    assert_error("ACTION_CHANGED_AFTER_APPROVAL", system.execute, ready.workflow_id, ready.version, context, facts)


def test_atomic_task_budget_admits_only_remaining_capacity():
    system = OversightSystem(sample_envelope(task_action_limit=2, task_spend_limit_cents=200_000))
    context, facts = sample_context(), sample_facts()
    records = [
        system.propose(context, sample_action(operation_id=f"OP-BUDGET-{index}", amount_cents=100_000), facts)
        for index in range(5)
    ]

    def execute(record):
        try:
            return system.execute(record.workflow_id, record.version, context, facts).reason_code
        except ControlError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(execute, records))
    assert results.count("OUTCOME_VERIFIED") == 2
    assert results.count("ACTION_BUDGET_EXCEEDED") == 3
    assert system.budget_usage(context) == (2, 200_000)


def test_outcome_mismatch_closes_loop_as_failure():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    record = system.propose(context, sample_action(), facts)
    system.adapter.mismatch_next = True
    result = system.execute(record.workflow_id, record.version, context, facts)
    assert result.verified is False
    assert result.workflow.status is WorkflowStatus.FAILED
    assert result.reason_code == "OUTCOME_MISMATCH"


def test_timeout_after_commit_is_reconciled_and_timeout_before_commit_is_not_retried():
    context, facts = sample_context(), sample_facts()
    after = OversightSystem(sample_envelope())
    after_record = after.propose(context, sample_action(operation_id="OP-AFTER"), facts)
    after.adapter.failure_mode_next = "after_commit"
    reconciled = after.execute(after_record.workflow_id, after_record.version, context, facts)
    assert reconciled.verified is True
    assert reconciled.workflow.status is WorkflowStatus.COMPLETED

    before = OversightSystem(sample_envelope())
    before_record = before.propose(context, sample_action(operation_id="OP-BEFORE"), facts)
    before.adapter.failure_mode_next = "before_commit"
    unknown = before.execute(before_record.workflow_id, before_record.version, context, facts)
    assert unknown.verified is False
    assert unknown.workflow.status is WorkflowStatus.FAILED
    assert before.adapter.reconcile(context.tenant_id, "OP-BEFORE") is None
    assert_error(
        "WORKFLOW_NOT_READY",
        before.execute,
        unknown.workflow.workflow_id,
        unknown.workflow.version,
        context,
        facts,
    )


def test_checkpoint_round_trip_preserves_pending_request_and_version():
    system = OversightSystem(sample_envelope())
    pending = system.propose(sample_context(), sample_action(amount_cents=600_000), sample_facts())
    checkpoint = system.checkpoint()
    restored = OversightSystem.restore(sample_envelope(), checkpoint)
    loaded = restored.get(pending.workflow_id)
    assert loaded == pending
    assert loaded.approval.action_digest == stable_digest(loaded.action)
    ready = manager_approval(restored, loaded)
    assert ready.status is WorkflowStatus.READY


def test_direct_effect_bypass_is_rejected():
    system = OversightSystem(sample_envelope())
    with pytest.raises(PermissionError, match="gateway"):
        system.adapter.execute(object(), "tenant-north", sample_action())


def test_reviewer_metrics_name_exact_population_and_fatigue_signals():
    events = (
        ReviewEvent(reviewer_id="r1", expected_choice=ReviewChoice.REJECT, actual_choice=ReviewChoice.APPROVE, latency_seconds=0.5),
        ReviewEvent(reviewer_id="r1", expected_choice=ReviewChoice.APPROVE, actual_choice=ReviewChoice.APPROVE, latency_seconds=0.8),
        ReviewEvent(reviewer_id="r1", expected_choice=ReviewChoice.REJECT, actual_choice=ReviewChoice.APPROVE, latency_seconds=1.0),
        ReviewEvent(reviewer_id="r2", expected_choice=ReviewChoice.REJECT, actual_choice=ReviewChoice.REJECT, latency_seconds=12.0),
    )
    metrics = reviewer_metrics(events)
    assert metrics.event_count == 4
    assert metrics.approval_count == 3
    assert metrics.approval_rate == 0.75
    assert metrics.median_latency_seconds == 0.9
    assert metrics.fast_approval_count == 3
    assert metrics.disagreement_count == 2
    assert metrics.busiest_reviewer_count == 3


def test_labelled_routing_evaluation_declares_all_populations():
    summary = run_evaluation()
    assert summary.case_count == 10
    assert (
        summary.expected_auto_count
        + summary.expected_verify_count
        + summary.expected_single_count
        + summary.expected_multi_count
        + summary.expected_deny_count
    ) == 10
    assert summary.baseline_correct_count == 2
    assert summary.candidate_correct_count == 10
    assert summary.baseline_human_review_count == 10
    assert summary.candidate_human_review_count == 4
    assert summary.baseline_hard_denial_overridden_count == 4
    assert summary.candidate_hard_denial_overridden_count == 0


def test_labelled_corpus_has_unique_operation_ids():
    cases = labelled_evaluation()
    assert len({case.action.operation_id for case in cases}) == len(cases)


def test_checkpoint_restore_preserves_pending_review_and_budget_state():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    auto = system.propose(context, sample_action(), facts)
    system.execute(auto.workflow_id, auto.version, context, facts)
    pending = system.propose(
        context,
        sample_action(operation_id="OP-RESTORE", amount_cents=600_000),
        facts,
    )
    restored = OversightSystem.restore(system.envelope, system.checkpoint())
    assert restored.get(pending.workflow_id).status is WorkflowStatus.PENDING
    assert restored.get(pending.workflow_id).approval == pending.approval
    assert restored.budget_usage(context) == (1, 50_000)


def test_pause_blocks_effect_and_resume_rechecks_current_state():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    ready = system.propose(context, sample_action(), facts)
    operator = OperatorContext(
        operator_id="ops-1",
        tenant_id=context.tenant_id,
        roles=frozenset({"oversight_operator"}),
    )
    paused = system.pause(ready.workflow_id, ready.version, operator)
    assert paused.status is WorkflowStatus.PAUSED
    assert_error(
        "WORKFLOW_NOT_READY",
        system.execute,
        paused.workflow_id,
        paused.version,
        context,
        facts,
    )
    resumed = system.resume(paused.workflow_id, paused.version, operator, context, facts)
    assert resumed.status is WorkflowStatus.READY
    assert system.execute(resumed.workflow_id, resumed.version, context, facts).verified


def test_resume_requires_reevaluation_when_facts_version_changes():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    ready = system.propose(context, sample_action(), facts)
    operator = OperatorContext(
        operator_id="ops-1",
        tenant_id=context.tenant_id,
        roles=frozenset({"oversight_operator"}),
    )
    paused = system.pause(ready.workflow_id, ready.version, operator)
    newer = facts.model_copy(update={"source_version": "procurement-facts/8472"})
    assert_error(
        "OVERSIGHT_REEVALUATION_REQUIRED",
        system.resume,
        paused.workflow_id,
        paused.version,
        operator,
        context,
        newer,
    )


def test_route_change_after_approval_requires_new_review():
    system = OversightSystem(sample_envelope())
    context, facts = sample_context(), sample_facts()
    ready = manager_approval(
        system,
        system.propose(context, sample_action(amount_cents=600_000), facts),
    )
    elevated = facts.model_copy(update={"incident_mode": "normal", "source_version": facts.source_version})
    system.envelope = system.envelope.model_copy(update={"single_approval_limit_cents": 500_000})
    assert_error(
        "OVERSIGHT_ROUTE_CHANGED",
        system.execute,
        ready.workflow_id,
        ready.version,
        context,
        elevated,
    )


def test_ambiguous_after_commit_is_reconciled_by_idempotency_key():
    system = OversightSystem(sample_envelope())
    context, facts, action = sample_context(), sample_facts(), sample_action()
    ready = system.propose(context, action, facts)
    system.adapter.failure_mode_next = "after_commit"
    result = system.execute(ready.workflow_id, ready.version, context, facts)
    assert result.verified is True
    assert result.effect.status == "created"
    reconciled = system.adapter.reconcile(context.tenant_id, action.operation_id)
    assert reconciled is not None
    assert reconciled.status == "created"
    assert reconciled.effect_id == result.effect.effect_id


def test_before_commit_failure_reconciles_as_absent():
    system = OversightSystem(sample_envelope())
    context, facts, action = sample_context(), sample_facts(), sample_action()
    ready = system.propose(context, action, facts)
    system.adapter.failure_mode_next = "before_commit"
    result = system.execute(ready.workflow_id, ready.version, context, facts)
    assert result.verified is False
    assert result.effect.status == "not_found"
    assert system.adapter.reconcile(context.tenant_id, action.operation_id) is None
