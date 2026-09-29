"""Focused invariants for Course 14 agent evaluation and governance."""

import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

MODULE = (
    Path(__file__).parents[1]
    / "curriculum/advanced/14-agent-evaluation-and-continuous-governance"
)
sys.path.insert(0, str(MODULE))
sys.modules.pop("lab", None)

from lab import (
    DATASET_ID,
    DATASET_VERSION,
    EVALUATOR_VERSION,
    REFERENCE_TIME,
    CanaryDecision,
    CanarySnapshot,
    CaseSource,
    ChangeKind,
    DatasetSplit,
    EvaluationError,
    GateDecision,
    GatePolicy,
    JudgeLabel,
    PolicyDecision,
    ProductionIncident,
    RateWindow,
    ReleaseStage,
    ReviewerContext,
    RiskTier,
    TerminalState,
    apply_release_gate,
    approve_regression_candidate,
    assess_rate_drift,
    build_course14_reference_run,
    build_judge_calibration_fixture,
    build_openai_trace_evaluation_artifact,
    build_otel_evaluation_artifact,
    build_reference_dataset,
    build_targets,
    build_tool_manifests,
    calibrate_judge,
    compare_reports,
    decide_canary,
    evaluate_target,
    grade_run,
    incident_to_regression_candidate,
    required_suites,
    run_synthetic_agent,
    stable_digest,
    wilson_interval,
)


def reference_bundle():
    return build_course14_reference_run()


def clone(model, **changes):
    values = model.model_dump(mode="python")
    values.update(changes)
    return type(model)(**values)


def test_stable_digest_is_canonical_for_dicts_and_sets():
    assert stable_digest({"b": {2, 1}, "a": 3}) == stable_digest({"a": 3, "b": {1, 2}})


def test_reference_dataset_is_versioned_and_has_16_unique_cases():
    dataset = build_reference_dataset()
    assert (dataset.dataset_id, dataset.version) == (DATASET_ID, DATASET_VERSION)
    assert len(dataset.cases) == 16
    assert len({case.case_id for case in dataset.cases}) == 16
    assert len(dataset.dataset_digest) == 64


def test_reference_dataset_covers_realistic_sources_and_risk_tiers():
    cases = build_reference_dataset().cases
    assert {case.source_type for case in cases} == set(CaseSource)
    assert {case.risk_tier for case in cases} >= {
        RiskTier.LOW,
        RiskTier.HIGH,
        RiskTier.CRITICAL,
    }
    assert all(case.source_ref and case.source_group for case in cases)


def test_reference_dataset_covers_required_governance_suites():
    tags = {tag for case in build_reference_dataset().cases for tag in case.suite_tags}
    assert tags >= required_suites(frozenset(ChangeKind))


def test_case_requires_effect_to_be_allowed_completed_tool_action():
    with pytest.raises(ValidationError):
        clone(build_reference_dataset().cases[0], expected_decision=PolicyDecision.DENY)


def test_case_requires_high_risk_for_approval():
    with pytest.raises(ValidationError):
        clone(build_reference_dataset().cases[1], risk_tier=RiskTier.LOW)


def test_case_requires_at_least_one_suite():
    with pytest.raises(ValidationError):
        clone(build_reference_dataset().cases[0], suite_tags=frozenset())


def test_forbidden_tool_may_be_expected_proposal_when_effect_must_be_blocked():
    case = next(c for c in build_reference_dataset().cases if c.case_id == "EV-03")
    assert case.expected_tool == "payment.execute"
    assert case.expected_tool in case.forbidden_tools
    assert not case.effect_expected


def test_dataset_rejects_empty_and_duplicate_case_ids():
    dataset = build_reference_dataset()
    with pytest.raises(ValidationError):
        clone(dataset, cases=())
    with pytest.raises(ValidationError):
        clone(dataset, cases=dataset.cases + (dataset.cases[0],))


def test_dataset_rejects_source_group_leakage_across_splits():
    dataset = build_reference_dataset()
    leaked = clone(
        dataset.cases[1],
        case_id="EV-99",
        source_group=dataset.cases[0].source_group,
        split=DatasetSplit.DEVELOPMENT,
    )
    with pytest.raises(ValidationError):
        clone(dataset, cases=dataset.cases + (leaked,))


def test_target_digest_binds_entire_version_vector():
    baseline, candidate = build_targets()
    assert baseline.config_digest != candidate.config_digest
    assert (
        clone(candidate, prompt_version="prompt/2.1").config_digest
        != candidate.config_digest
    )


def test_unknown_synthetic_target_fails_closed():
    case = build_reference_dataset().cases[0]
    with pytest.raises(EvaluationError, match="UNKNOWN_SYNTHETIC_TARGET"):
        run_synthetic_agent(case, clone(build_targets()[1], system_version="unknown"))


def test_run_requires_workflow_root():
    case = build_reference_dataset().cases[0]
    run = run_synthetic_agent(case, build_targets()[1])
    with pytest.raises(ValidationError):
        clone(run, events=run.events[1:])


def test_run_requires_continuous_sequence():
    case = build_reference_dataset().cases[0]
    run = run_synthetic_agent(case, build_targets()[1])
    events = (clone(run.events[0], sequence=2),) + run.events[1:]
    with pytest.raises(ValidationError):
        clone(run, events=events)


def test_run_requires_terminal_evidence():
    case = build_reference_dataset().cases[0]
    run = run_synthetic_agent(case, build_targets()[1])
    with pytest.raises(ValidationError):
        clone(run, events=run.events[:-1])


def test_run_digest_detects_trace_tampering():
    case = build_reference_dataset().cases[0]
    run = run_synthetic_agent(case, build_targets()[1])
    with pytest.raises(ValidationError):
        clone(run, latency_ms=run.latency_ms + 1)


def test_grade_rejects_case_run_binding_mismatch():
    dataset = build_reference_dataset()
    run = run_synthetic_agent(dataset.cases[0], build_targets()[1])
    with pytest.raises(EvaluationError, match="CASE_RUN_BINDING_MISMATCH"):
        grade_run(dataset.cases[1], run)


def test_candidate_passes_every_case_deterministically():
    report = reference_bundle()["candidate"]
    assert report.metrics.task_successes == 16
    assert all(result.task_success for result in report.results)
    assert evaluate_target(build_reference_dataset(), build_targets()[1]) == report


def test_candidate_records_blocked_attempts_without_calling_them_outcomes():
    report = reference_bundle()["candidate"]
    adversarial = [r for r in report.results if r.forbidden_tool_attempted]
    assert len(adversarial) == 6
    assert all(not result.forbidden_outcome for result in adversarial)
    assert report.metrics.forbidden_outcomes == 0


def test_baseline_exposes_forbidden_and_critical_outcomes():
    metrics = reference_bundle()["baseline"].metrics
    assert metrics.forbidden_outcomes == 5
    assert metrics.critical_safety_violations == 4
    assert metrics.task_successes == 5


def test_baseline_detects_cross_tenant_execution():
    result = next(
        r for r in reference_bundle()["baseline"].results if r.case_id == "EV-05"
    )
    assert not result.tenant_isolation_correct
    assert result.safety_violation
    assert "TENANT_ISOLATION_INVALID" in result.reason_codes


def test_baseline_detects_approval_digest_mismatch():
    result = next(
        r for r in reference_bundle()["baseline"].results if r.case_id == "EV-07"
    )
    assert not result.approval_binding_correct
    assert "APPROVAL_BINDING_INVALID" in result.reason_codes


def test_baseline_detects_fake_success_after_unknown_tool_outcome():
    result = next(
        r for r in reference_bundle()["baseline"].results if r.case_id == "EV-08"
    )
    assert not result.effect_correct
    assert not result.task_success


def test_baseline_detects_valid_work_blocking_separately_from_safety():
    result = next(
        r for r in reference_bundle()["baseline"].results if r.case_id == "EV-10"
    )
    assert result.valid_work_blocked
    assert not result.safety_violation
    assert "VALID_WORK_BLOCKED" in result.reason_codes


def test_metrics_keep_exact_numerators_and_denominators():
    metrics = reference_bundle()["candidate"].metrics
    assert (metrics.task_successes, metrics.case_population) == (16, 16)
    assert (metrics.high_risk_policy_correct, metrics.high_risk_population) == (13, 13)
    assert (metrics.blocked_attacks, metrics.attack_population) == (6, 6)
    assert (metrics.verified_effects, metrics.verified_effect_population) == (3, 3)


def test_metrics_report_cost_latency_and_risk_slices():
    metrics = reference_bundle()["candidate"].metrics
    assert metrics.cost_per_successful_task_usd == pytest.approx(0.02375)
    assert metrics.p95_latency_ms == 755
    assert {item.name: item.population for item in metrics.risk_slices} == {
        "LOW": 3,
        "HIGH": 8,
        "CRITICAL": 5,
    }


@pytest.mark.parametrize("successes,population", [(-1, 10), (11, 10), (0, 0)])
def test_wilson_interval_rejects_invalid_populations(successes, population):
    with pytest.raises(EvaluationError, match="INTERVAL_POPULATION_INVALID"):
        wilson_interval(successes, population)


def test_wilson_interval_is_bounded_at_extremes():
    low = wilson_interval(0, 10)
    high = wilson_interval(10, 10)
    assert low.lower == 0 and 0 < low.upper < 1
    assert 0 < high.lower < 1 and high.upper == 1


def test_small_perfect_sample_still_expresses_uncertainty():
    interval = reference_bundle()["candidate"].metrics.task_success_interval
    assert interval.point == 1
    assert 0.80 < interval.lower < 0.81


def test_evaluation_rejects_empty_split():
    with pytest.raises(EvaluationError, match="EVALUATION_SPLIT_EMPTY"):
        evaluate_target(
            build_reference_dataset(),
            build_targets()[1],
            split=DatasetSplit.CALIBRATION,
        )


def test_report_digest_detects_metric_tampering():
    report = reference_bundle()["candidate"]
    with pytest.raises(ValidationError):
        clone(report, metrics=clone(report.metrics, task_successes=15))


def test_paired_comparison_is_same_case_and_statistically_exact():
    comparison = reference_bundle()["comparison"]
    assert comparison.population == 16
    assert len(comparison.improvements) == 11
    assert not comparison.regressions
    assert comparison.exact_mcnemar_p_value == pytest.approx(0.0009765625)


def test_paired_comparison_rejects_dataset_mismatch():
    bundle = reference_bundle()
    changed = bundle["candidate"].model_copy(update={"dataset_digest": "0" * 64})
    with pytest.raises(EvaluationError, match="REPORT_DATASET_MISMATCH"):
        compare_reports(bundle["baseline"], changed)


def test_paired_comparison_rejects_evaluator_mismatch():
    bundle = reference_bundle()
    changed = bundle["candidate"].model_copy(update={"evaluator_version": "other"})
    with pytest.raises(EvaluationError, match="REPORT_EVALUATOR_MISMATCH"):
        compare_reports(bundle["baseline"], changed)


def test_paired_comparison_rejects_case_population_mismatch():
    bundle = reference_bundle()
    changed = bundle["candidate"].model_copy(
        update={"results": bundle["candidate"].results[:-1]}
    )
    with pytest.raises(EvaluationError, match="REPORT_CASE_POPULATION_MISMATCH"):
        compare_reports(bundle["baseline"], changed)


def test_judge_calibration_measures_agreement_bias_and_disagreements():
    calibration = reference_bundle()["calibration"]
    assert calibration.population == 12
    assert calibration.exact_agreement == pytest.approx(10 / 12)
    assert calibration.cohen_kappa == pytest.approx(0.75)
    assert calibration.position_consistency == pytest.approx(11 / 12)
    assert calibration.disagreement_item_ids == ("J-05", "J-06", "J-12")


def test_judge_calibration_requires_six_blind_items():
    items = build_judge_calibration_fixture()
    with pytest.raises(EvaluationError, match="JUDGE_CALIBRATION_POPULATION_TOO_SMALL"):
        calibrate_judge(items[:5])
    with pytest.raises(EvaluationError, match="JUDGE_CALIBRATION_NOT_BLIND"):
        calibrate_judge((clone(items[0], split=DatasetSplit.CALIBRATION),) + items[1:])


def test_judge_calibration_rejects_mixed_versions():
    items = build_judge_calibration_fixture()
    with pytest.raises(EvaluationError, match="JUDGE_CALIBRATION_VERSION_MIXED"):
        calibrate_judge((clone(items[0], judge_version="other"),) + items[1:])


def test_required_suites_rejects_no_changes():
    with pytest.raises(EvaluationError, match="CHANGE_SET_EMPTY"):
        required_suites(())


def test_tool_and_policy_changes_select_security_suites():
    suites = required_suites({ChangeKind.TOOL, ChangeKind.POLICY})
    assert suites >= {
        "tool-contract",
        "authorization",
        "recovery",
        "policy",
        "approval",
        "safety",
    }


def test_reference_release_gate_approves_exact_fresh_evidence():
    gate = reference_bundle()["gate"]
    assert gate.decision == GateDecision.APPROVE
    assert gate.authorized_stage == ReleaseStage.SHADOW
    assert not gate.reason_codes and not gate.constraints
    assert len(gate.evidence_digest) == 64


def test_release_gate_rejects_target_mismatch():
    bundle = reference_bundle()
    gate = apply_release_gate(
        clone(bundle["request"], target=build_targets()[0]),
        bundle["candidate"],
        bundle["comparison"],
        judge_calibration=bundle["calibration"],
    )
    assert gate.decision == GateDecision.BLOCK
    assert gate.authorized_stage is None
    assert "TARGET_EVIDENCE_MISMATCH" in gate.reason_codes


def test_release_gate_rejects_evidence_that_predates_change():
    bundle = reference_bundle()
    request = clone(
        bundle["request"],
        created_at=bundle["candidate"].generated_at + timedelta(minutes=1),
    )
    gate = apply_release_gate(
        request,
        bundle["candidate"],
        bundle["comparison"],
        judge_calibration=bundle["calibration"],
    )
    assert gate.decision == GateDecision.BLOCK
    assert "EVALUATION_PREDATES_CHANGE" in gate.reason_codes


def test_release_gate_rejects_stale_evidence():
    bundle = reference_bundle()
    gate = apply_release_gate(
        bundle["request"],
        bundle["candidate"],
        bundle["comparison"],
        judge_calibration=bundle["calibration"],
        now=REFERENCE_TIME + timedelta(days=40),
    )
    assert gate.decision == GateDecision.BLOCK
    assert "EVALUATION_STALE" in gate.reason_codes


def test_release_gate_rejects_missing_change_triggered_suites():
    bundle = reference_bundle()
    candidate = bundle["candidate"].model_copy(
        update={"covered_suites": frozenset({"golden"})}
    )
    gate = apply_release_gate(
        bundle["request"],
        candidate,
        bundle["comparison"],
        judge_calibration=bundle["calibration"],
    )
    assert "REQUIRED_SUITES_MISSING" in gate.reason_codes


def test_release_gate_requires_calibration_when_model_judge_is_used():
    bundle = reference_bundle()
    gate = apply_release_gate(
        bundle["request"], bundle["candidate"], bundle["comparison"]
    )
    assert gate.decision == GateDecision.BLOCK
    assert "JUDGE_CALIBRATION_MISSING" in gate.reason_codes


def test_release_gate_rejects_comparison_not_bound_to_candidate_report():
    bundle = reference_bundle()
    comparison = bundle["comparison"].model_copy(
        update={"candidate_report_digest": "0" * 64}
    )
    gate = apply_release_gate(
        bundle["request"],
        bundle["candidate"],
        comparison,
        judge_calibration=bundle["calibration"],
    )
    assert gate.decision == GateDecision.BLOCK
    assert "COMPARISON_EVIDENCE_MISMATCH" in gate.reason_codes


def test_release_gate_rejects_judge_false_accepts():
    bundle = reference_bundle()
    items = list(build_judge_calibration_fixture())
    items[1] = clone(
        items[1], judge_label=JudgeLabel.PASS, swapped_order_label=JudgeLabel.PASS
    )
    gate = apply_release_gate(
        bundle["request"],
        bundle["candidate"],
        bundle["comparison"],
        judge_calibration=calibrate_judge(items),
    )
    assert gate.decision == GateDecision.BLOCK
    assert "JUDGE_FALSE_ACCEPT" in gate.reason_codes


def test_release_gate_can_constrain_cost_without_masking_safety():
    bundle = reference_bundle()
    gate = apply_release_gate(
        bundle["request"],
        bundle["candidate"],
        bundle["comparison"],
        gate_policy=GatePolicy(maximum_cost_per_success_usd=0.01),
        judge_calibration=bundle["calibration"],
    )
    assert gate.decision == GateDecision.CONSTRAIN
    assert gate.authorized_stage == ReleaseStage.SHADOW
    assert gate.constraints == ("COST_BUDGET_REVIEW",)


def test_small_offline_suite_cannot_directly_authorize_production():
    bundle = reference_bundle()
    request = clone(bundle["request"], requested_stage=ReleaseStage.PRODUCTION)
    gate = apply_release_gate(
        request,
        bundle["candidate"],
        bundle["comparison"],
        judge_calibration=bundle["calibration"],
    )
    assert gate.decision == GateDecision.CONSTRAIN
    assert gate.authorized_stage == ReleaseStage.CANARY
    assert "CANARY_ONLY_INSUFFICIENT_PRODUCTION_EVIDENCE" in gate.constraints


def test_canary_rolls_back_on_critical_or_forbidden_outcome():
    common = {"population": 1, "successful_tasks": 0, "errors": 0}
    assert (
        decide_canary(
            CanarySnapshot(**common, critical_policy_violations=1, forbidden_outcomes=0)
        )
        == CanaryDecision.ROLLBACK
    )
    assert (
        decide_canary(
            CanarySnapshot(**common, critical_policy_violations=0, forbidden_outcomes=1)
        )
        == CanaryDecision.ROLLBACK
    )


def test_canary_holds_small_or_uncertain_population():
    small = CanarySnapshot(
        population=50,
        successful_tasks=50,
        errors=0,
        critical_policy_violations=0,
        forbidden_outcomes=0,
    )
    uncertain = CanarySnapshot(
        population=200,
        successful_tasks=195,
        errors=1,
        critical_policy_violations=0,
        forbidden_outcomes=0,
    )
    assert decide_canary(small) == CanaryDecision.HOLD
    assert decide_canary(uncertain) == CanaryDecision.HOLD


def test_canary_expands_only_with_sufficient_clean_evidence():
    clean = CanarySnapshot(
        population=500,
        successful_tasks=495,
        errors=1,
        critical_policy_violations=0,
        forbidden_outcomes=0,
    )
    assert decide_canary(clean) == CanaryDecision.EXPAND


def test_canary_rolls_back_on_error_rate():
    bad = CanarySnapshot(
        population=200,
        successful_tasks=190,
        errors=10,
        critical_policy_violations=0,
        forbidden_outcomes=0,
    )
    assert decide_canary(bad) == CanaryDecision.ROLLBACK


def test_drift_is_signal_only_and_refuses_small_population_alerts():
    result = assess_rate_drift(
        RateWindow(events=1, population=10), RateWindow(events=5, population=10)
    )
    assert result.signal_only and not result.sufficient_data and not result.alert


def test_drift_alerts_on_sufficient_material_rate_shift():
    result = assess_rate_drift(
        RateWindow(events=5, population=200), RateWindow(events=25, population=200)
    )
    assert result.sufficient_data and result.alert
    assert result.absolute_change == pytest.approx(0.1)


def test_incident_rejects_email_and_api_key_content():
    base = {
        "incident_id": "INC-14",
        "tenant_id": "tenant-acme",
        "risk_tier": RiskTier.HIGH,
        "trace_ref": "trace://INC-14",
        "observed_outcome_code": "WRONG_EFFECT",
    }
    with pytest.raises(ValidationError):
        ProductionIncident(**base, sanitized_summary="contact user@example.com")
    with pytest.raises(ValidationError):
        ProductionIncident(**base, sanitized_summary="token sk-abcdefgh1234")


def test_incident_becomes_reviewable_not_automatically_promoted_regression():
    incident = ProductionIncident(
        incident_id="INC-14",
        tenant_id="tenant-acme",
        risk_tier=RiskTier.HIGH,
        sanitized_summary="purchase outcome differed from approved action",
        trace_ref="trace://INC-14",
        observed_outcome_code="WRONG_EFFECT",
    )
    candidate = incident_to_regression_candidate(
        incident,
        expected_decision=PolicyDecision.ESCALATE,
        expected_terminal_state=TerminalState.REVIEW_REQUIRED,
        expected_outcome_code="ACTION_REVIEW_REQUIRED",
        expected_tool="po.create",
    )
    assert candidate.proposed_case.source_type == CaseSource.INCIDENT
    assert not candidate.reviewed
    reviewer = ReviewerContext(
        principal_id="reviewer:1",
        tenant_id="tenant-acme",
        roles=frozenset({"viewer"}),
        authenticated_at=REFERENCE_TIME,
        valid_until=REFERENCE_TIME + timedelta(hours=1),
    )
    with pytest.raises(EvaluationError, match="REGRESSION_REVIEW_NOT_AUTHORIZED"):
        approve_regression_candidate(candidate, reviewer=reviewer)
    assert approve_regression_candidate(
        candidate,
        reviewer=reviewer.model_copy(update={"roles": frozenset({"evaluation_owner"})}),
    ).reviewed


def test_regression_review_requires_current_same_tenant_context():
    incident = ProductionIncident(
        incident_id="INC-15",
        tenant_id="tenant-acme",
        risk_tier=RiskTier.HIGH,
        sanitized_summary="verified outcome did not match",
        trace_ref="trace://INC-15",
        observed_outcome_code="WRONG_EFFECT",
    )
    candidate = incident_to_regression_candidate(
        incident,
        expected_decision=PolicyDecision.ESCALATE,
        expected_terminal_state=TerminalState.REVIEW_REQUIRED,
        expected_outcome_code="ACTION_REVIEW_REQUIRED",
        expected_tool="po.create",
    )
    reviewer = ReviewerContext(
        principal_id="reviewer:1",
        tenant_id="tenant-acme",
        roles=frozenset({"evaluation_owner"}),
        authenticated_at=REFERENCE_TIME,
        valid_until=REFERENCE_TIME + timedelta(hours=1),
    )
    with pytest.raises(EvaluationError, match="REGRESSION_REVIEW_SESSION_INVALID"):
        approve_regression_candidate(
            candidate, reviewer=reviewer, now=reviewer.valid_until
        )
    with pytest.raises(EvaluationError, match="REGRESSION_REVIEW_TENANT_MISMATCH"):
        approve_regression_candidate(
            candidate,
            reviewer=reviewer.model_copy(update={"tenant_id": "tenant-other"}),
        )


def test_tool_manifests_cover_common_frameworks_and_boundaries():
    manifests = build_tool_manifests()
    assert set(manifests) == {
        "inspect_ai",
        "promptfoo",
        "langsmith",
        "phoenix",
        "langfuse",
        "deepeval",
        "ragas",
        "openai",
    }
    assert all(
        item.best_fit and item.governance_boundary and item.current_status
        for item in manifests.values()
    )
    assert "deprecation" in manifests["openai"].governance_boundary.lower()


def test_real_opentelemetry_span_is_offline_minimized_and_versioned():
    artifact = build_otel_evaluation_artifact(reference_bundle()["candidate"])
    assert len(artifact["spans"]) == 1
    attrs = artifact["spans"][0].attributes
    assert attrs["gen_ai.evaluation.name"] == "task_success"
    assert attrs["governance.evaluator.version"] == EVALUATOR_VERSION
    assert not any("prompt" in key or "content" in key for key in attrs)


def test_openai_agents_trace_artifact_is_constructed_without_export():
    artifact = build_openai_trace_evaluation_artifact(reference_bundle()["candidate"])
    assert set(artifact) == {"trace", "span"}
    assert artifact["trace"].trace_id.startswith("trace_")
    assert artifact["span"].span_data.name == "evaluation_result"


def test_reference_bundle_keeps_evidence_chain_bound_together():
    bundle = reference_bundle()
    assert bundle["baseline"].dataset_digest == bundle["candidate"].dataset_digest
    assert bundle["comparison"].candidate_report_id == bundle["candidate"].report_id
    assert bundle["request"].target == bundle["candidate"].target


def test_lab_contains_no_credentials_network_or_raw_prompt_fields():
    source = (MODULE / "lab.py").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in source
    assert "requests." not in source
    assert "prompt_content" not in source
    assert "subprocess" not in source
