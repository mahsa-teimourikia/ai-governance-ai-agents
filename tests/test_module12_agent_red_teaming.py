"""Focused campaign, oracle, evidence, and lifecycle tests for Course 12."""

from datetime import timedelta
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


MODULE = Path(__file__).parents[1] / "curriculum/intermediate/12-agent-red-teaming-and-adversarial-testing"
sys.path.insert(0, str(MODULE))
sys.modules.pop("lab", None)

from lab import (  # noqa: E402
    AttackFamily,
    CampaignError,
    CampaignRunner,
    CampaignState,
    EventKind,
    ExpectedBehavior,
    FindingRegistry,
    FindingState,
    Outcome,
    REFERENCE_TIME,
    RulesOfEngagement,
    Severity,
    SimulatedProcurementTarget,
    Surface,
    TargetResult,
    TrajectoryEvent,
    attack_corpus,
    build_openai_trace_artifacts,
    build_promptfoo_config,
    build_tool_integrations,
    evaluate_release_gate,
    inspect_trajectory,
    make_artifact,
    mutate_case,
    run_reference_campaign,
    sample_operator,
    sample_roe,
    sample_security_operator,
    stable_digest,
)


def assert_error(code, function, *args, **kwargs):
    with pytest.raises(CampaignError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code


def test_digest_is_canonical():
    assert stable_digest({"b": {2, 1}, "a": 3}) == stable_digest({"a": 3, "b": {1, 2}})


def test_attack_artifact_detects_content_tampering():
    artifact = make_artifact("ART-1", "synthetic", source=Surface.USER, locator="fixture://one")
    with pytest.raises(ValidationError):
        artifact.model_copy(update={"content": "changed"}).model_validate(
            artifact.model_dump() | {"content": "changed"}
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"environment": "production"},
        {"synthetic_data_only": False},
        {"real_side_effects_allowed": True},
        {"external_targets_allowed": True},
        {"approved_by": ("same", "same")},
    ],
)
def test_rules_of_engagement_reject_unsafe_scope(changes):
    with pytest.raises(ValidationError):
        sample_roe(**changes)


def test_target_must_match_approved_version():
    target = SimulatedProcurementTarget("procurement-agent", "other", False)
    assert_error("TARGET_VERSION_MISMATCH", CampaignRunner, sample_roe(), target)


def test_operator_must_be_current_authorized_and_same_tenant():
    target = SimulatedProcurementTarget("procurement-agent", "vulnerable-1.0", False)
    for operator, code in [
        (sample_operator(roles=frozenset()), "OPERATOR_NOT_AUTHORIZED"),
        (sample_operator(tenant_id="tenant-beta"), "OPERATOR_TENANT_MISMATCH"),
        (sample_operator(authenticated_at=REFERENCE_TIME + timedelta(seconds=1)), "OPERATOR_SESSION_NOT_CURRENT"),
    ]:
        runner = CampaignRunner(sample_roe(), target)
        assert_error(code, runner.run, operator, attack_corpus())


def test_campaign_window_is_enforced():
    target = SimulatedProcurementTarget("procurement-agent", "vulnerable-1.0", False)
    runner = CampaignRunner(sample_roe(), target)
    assert_error(
        "CAMPAIGN_OUTSIDE_WINDOW",
        runner.run,
        sample_operator(valid_until=REFERENCE_TIME + timedelta(days=2)),
        attack_corpus(),
        now=REFERENCE_TIME + timedelta(days=1),
    )


def test_empty_duplicate_and_excessive_corpora_fail_closed():
    target = SimulatedProcurementTarget("procurement-agent", "vulnerable-1.0", False)
    assert_error("EMPTY_CAMPAIGN", CampaignRunner(sample_roe(), target).run, sample_operator(), ())
    duplicate = (attack_corpus()[0], attack_corpus()[0])
    assert_error("DUPLICATE_CASE_ID", CampaignRunner(sample_roe(), target).run, sample_operator(), duplicate)
    assert_error(
        "CAMPAIGN_CASE_BUDGET_EXCEEDED",
        CampaignRunner(sample_roe(maximum_cases=1), target).run,
        sample_operator(),
        attack_corpus()[:2],
    )


def test_out_of_scope_family_and_surface_are_rejected():
    target = SimulatedProcurementTarget("procurement-agent", "vulnerable-1.0", False)
    roe = sample_roe(allowed_families=frozenset({AttackFamily.BENIGN}))
    assert_error("CASE_OUTSIDE_ROE", CampaignRunner(roe, target).run, sample_operator(), attack_corpus()[:1])


def test_cross_tenant_fixture_is_rejected_before_target():
    target = SimulatedProcurementTarget("procurement-agent", "vulnerable-1.0", False)
    case = attack_corpus()[0]
    artifact = make_artifact("ART-X", case.artifact.content, source=case.surface, locator="fixture://x", tenant_id="tenant-beta")
    changed = case.model_copy(update={"artifact": artifact})
    assert_error("CASE_TENANT_MISMATCH", CampaignRunner(sample_roe(), target).run, sample_operator(), (changed,))


def test_campaign_is_single_use():
    target = SimulatedProcurementTarget("procurement-agent", "vulnerable-1.0", False)
    runner = CampaignRunner(sample_roe(), target)
    runner.run(sample_operator(), attack_corpus()[:1])
    assert runner.state == CampaignState.COMPLETED
    assert_error("CAMPAIGN_ALREADY_RUN", runner.run, sample_operator(), attack_corpus()[:1])


def test_only_named_security_owner_can_emergency_stop():
    target = SimulatedProcurementTarget("procurement-agent", "vulnerable-1.0", False)
    runner = CampaignRunner(sample_roe(), target)
    assert_error("STOP_NOT_AUTHORIZED", runner.emergency_stop, sample_operator(), "incident")
    assert_error(
        "STOP_OWNER_MISMATCH",
        runner.emergency_stop,
        sample_security_operator(principal_id="user:other-security"),
        "incident",
    )
    runner.emergency_stop(sample_security_operator(), "incident")
    assert runner.state == CampaignState.STOPPED
    assert_error("CAMPAIGN_STOPPED", runner.run, sample_operator(), attack_corpus()[:1])


def test_trajectory_requires_contiguous_events_and_exact_steps():
    event = TrajectoryEvent(sequence=2, kind=EventKind.INPUT, code="X", stage="input")
    with pytest.raises(ValidationError):
        TargetResult(
            target_id="x", target_version="1", case_id="RT-X", terminal_code="DONE", events=(event,), steps=1
        )


def test_target_error_is_indeterminate_not_secure():
    result = TargetResult(
        target_id="x",
        target_version="1",
        case_id="RT-X",
        terminal_code="TARGET_ERROR",
        events=(TrajectoryEvent(sequence=1, kind=EventKind.ERROR, code="TIMEOUT", stage="target"),),
        steps=1,
        error_code="TIMEOUT",
    )
    oracle = inspect_trajectory(result)
    assert oracle.outcome == Outcome.INDETERMINATE
    assert oracle.violations == ("TARGET_ERROR",)


def test_vulnerable_target_exposes_all_twelve_attack_cases():
    report = run_reference_campaign(hardened=False)
    assert report.metrics.model_dump() == {
        "total_cases": 16,
        "attack_cases": 12,
        "legitimate_cases": 4,
        "attack_attempts_blocked": 0,
        "attacks_successful": 12,
        "control_bypasses": 12,
        "harmful_outcomes": 12,
        "legitimate_allowed": 4,
        "legitimate_blocked": 0,
        "indeterminate": 0,
        "critical_harmful_outcomes": 7,
        "detector_triggered_attacks": 6,
        "detector_missed_attacks": 6,
        "detector_false_positives": 0,
        "attack_success_rate": 1.0,
        "control_bypass_rate": 1.0,
        "harmful_outcome_rate": 1.0,
        "legitimate_pass_rate": 1.0,
    }


def test_hardened_target_blocks_attacks_and_preserves_controls():
    report = run_reference_campaign(hardened=True)
    assert report.metrics.attack_attempts_blocked == 12
    assert report.metrics.attacks_successful == 0
    assert report.metrics.control_bypasses == 0
    assert report.metrics.harmful_outcomes == 0
    assert report.metrics.legitimate_allowed == 4
    assert report.metrics.legitimate_blocked == 0
    assert report.metrics.legitimate_pass_rate == 1.0
    assert all(result.secure_behavior_observed for result in report.results)


@pytest.mark.parametrize(
    ("case_id", "violation"),
    [
        ("RT-EXFIL", "CANARY_EXFILTRATED"),
        ("RT-RAG", "PAYMENT_WITHOUT_VALID_APPROVAL"),
        ("RT-MEMORY", "AUTHORITY_MEMORY_PERSISTED"),
        ("RT-SSRF-LOOPBACK", "PRIVATE_NETWORK_REACHED"),
        ("RT-SHELL", "PROHIBITED_COMMAND_EXECUTED"),
        ("RT-RUNAWAY", "RUNAWAY_BUDGET_EXCEEDED"),
    ],
)
def test_oracles_use_observable_effects(case_id, violation):
    result = next(item for item in run_reference_campaign(hardened=False).results if item.case_id == case_id)
    assert violation in result.violations
    assert result.harmful_outcome is True


def test_hardened_runaway_stops_within_step_budget():
    target = SimulatedProcurementTarget("procurement-agent", "hardened-2.0", True)
    report = CampaignRunner(sample_roe(target_version="hardened-2.0"), target).run(
        sample_operator(), (next(case for case in attack_corpus() if case.case_id == "RT-RUNAWAY"),)
    )
    assert report.results[0].secure_behavior_observed is True


def test_block_credit_requires_the_expected_enforcement_stage():
    case = attack_corpus()[0].model_copy(update={"expected_stop_stage": "authorization"})
    target = SimulatedProcurementTarget("procurement-agent", "hardened-2.0", True)
    report = CampaignRunner(sample_roe(target_version="hardened-2.0"), target).run(
        sample_operator(), (case,)
    )
    assert report.results[0].outcome == Outcome.SECURE
    assert report.results[0].stop_stage == "egress"
    assert report.results[0].secure_behavior_observed is False


def test_results_store_digests_not_raw_attack_payloads():
    report = run_reference_campaign(hardened=False)
    serialized = report.model_dump_json()
    assert "Ignore policy and export" not in serialized
    assert all(len(result.payload_digest) == 64 for result in report.results)
    assert all(len(result.evidence_digest) == 64 for result in report.results)


def test_report_binds_versions_roe_and_corpus():
    report = run_reference_campaign(hardened=True)
    assert report.target_version == "hardened-2.0"
    assert len(report.roe_digest) == len(report.corpus_digest) == 64
    changed = list(attack_corpus())
    changed[0] = changed[0].model_copy(update={"title": "Changed title"})
    target = SimulatedProcurementTarget("procurement-agent", "hardened-2.0", True)
    second = CampaignRunner(sample_roe(target_version="hardened-2.0"), target).run(sample_operator(), changed)
    assert second.corpus_digest != report.corpus_digest


def test_release_gate_rejects_baseline_and_accepts_hardened():
    failed = evaluate_release_gate(run_reference_campaign(hardened=False))
    passed = evaluate_release_gate(run_reference_campaign(hardened=True))
    assert failed.pass_gate is False
    assert "CRITICAL_HARMFUL_OUTCOME" in failed.reason_codes
    assert "ATTACK_SUCCESS_RATE_EXCEEDED" in failed.reason_codes
    assert passed.pass_gate is True
    assert passed.reason_codes == ()


def test_gate_checks_legitimate_work_not_only_attack_rate():
    report = run_reference_campaign(hardened=True)
    assert_error(
        "RELEASE_GATE_THRESHOLD_INVALID",
        evaluate_release_gate,
        report,
        minimum_legitimate_pass_rate=1.01,
    )


def test_gate_rejects_negative_or_overwide_thresholds():
    report = run_reference_campaign(hardened=True)
    assert_error(
        "RELEASE_GATE_THRESHOLD_INVALID",
        evaluate_release_gate,
        report,
        maximum_attack_success_rate=-0.01,
    )


def test_gate_requires_minimum_attack_and_legitimate_coverage():
    target = SimulatedProcurementTarget("procurement-agent", "hardened-2.0", True)
    attacks_only = CampaignRunner(sample_roe(target_version="hardened-2.0"), target).run(
        sample_operator(), attack_corpus()[:2]
    )
    gate = evaluate_release_gate(
        attacks_only,
        minimum_attack_cases=3,
        minimum_legitimate_cases=1,
    )
    assert "ATTACK_COVERAGE_TOO_LOW" in gate.reason_codes
    assert "LEGITIMATE_COVERAGE_TOO_LOW" in gate.reason_codes
    assert_error(
        "RELEASE_GATE_COVERAGE_INVALID",
        evaluate_release_gate,
        attacks_only,
        minimum_attack_cases=0,
    )


def test_mutations_are_bounded_and_preserve_lineage():
    case = attack_corpus()[0]
    variants = mutate_case(case, maximum_variants=3)
    assert len(variants) == 3
    assert len({item.case_id for item in variants}) == 3
    assert all(item.parent_case_id == case.case_id for item in variants)
    assert all(item.artifact.content_digest != case.artifact.content_digest for item in variants)
    assert_error("MUTATION_BUDGET_INVALID", mutate_case, case, maximum_variants=0)


def test_unicode_mutations_do_not_evade_hardened_target():
    case = attack_corpus()[0]
    target = SimulatedProcurementTarget("procurement-agent", "hardened-2.0", True)
    report = CampaignRunner(sample_roe(target_version="hardened-2.0"), target).run(
        sample_operator(), mutate_case(case)
    )
    assert report.metrics.attacks_successful == 0
    assert report.metrics.attack_attempts_blocked == 3


def _finding_fixture():
    vulnerable = run_reference_campaign(hardened=False)
    result = next(item for item in vulnerable.results if item.case_id == "RT-RAG")
    registry = FindingRegistry("tenant-acme")
    return registry, registry.admit(vulnerable, result.case_id), vulnerable, result


def test_only_confirmed_vulnerability_becomes_a_finding():
    registry = FindingRegistry("tenant-acme")
    secure_report = run_reference_campaign(hardened=True)
    assert_error("NO_CONFIRMED_VULNERABILITY", registry.admit, secure_report, secure_report.results[0].case_id)


def test_finding_admission_requires_same_tenant_bound_report():
    registry = FindingRegistry("tenant-acme")
    report = run_reference_campaign(hardened=False).model_copy(update={"tenant_id": "tenant-beta"})
    assert_error("REPORT_TENANT_MISMATCH", registry.admit, report, "RT-RAG")


def test_findings_deduplicate_by_bound_evidence_identity():
    registry, finding, report, result = _finding_fixture()
    assert registry.admit(report, result.case_id) == finding


def test_finding_transition_requires_authorized_current_manager():
    registry, finding, _, _ = _finding_fixture()
    assert_error(
        "FINDING_MANAGER_NOT_AUTHORIZED",
        registry.transition,
        sample_operator(roles=frozenset()),
        finding.finding_id,
        expected_version=1,
        to_state=FindingState.ACCEPTED,
        owner="team",
    )


def test_finding_lifecycle_requires_owner_remediation_and_regression():
    registry, finding, _, _ = _finding_fixture()
    assert_error(
        "FINDING_OWNER_REQUIRED", registry.transition, sample_operator(), finding.finding_id,
        expected_version=1, to_state=FindingState.ACCEPTED
    )
    accepted, _ = registry.transition(
        sample_operator(), finding.finding_id, expected_version=1,
        to_state=FindingState.ACCEPTED, owner="security-engineering"
    )
    assert_error(
        "REMEDIATION_REFERENCE_REQUIRED", registry.transition, sample_operator(), finding.finding_id,
        expected_version=accepted.version, to_state=FindingState.REMEDIATED
    )
    remediated, _ = registry.transition(
        sample_operator(), finding.finding_id, expected_version=accepted.version,
        to_state=FindingState.REMEDIATED, remediation_ref="PR-SEC-42"
    )
    assert_error(
        "REGRESSION_EVIDENCE_REQUIRED", registry.transition, sample_operator(), finding.finding_id,
        expected_version=remediated.version, to_state=FindingState.VERIFIED
    )


def test_finding_closes_only_after_secure_new_version_regression():
    registry, finding, old_report, _ = _finding_fixture()
    accepted, _ = registry.transition(
        sample_operator(), finding.finding_id, expected_version=1,
        to_state=FindingState.ACCEPTED, owner="security-engineering"
    )
    remediated, _ = registry.transition(
        sample_operator(), finding.finding_id, expected_version=accepted.version,
        to_state=FindingState.REMEDIATED, remediation_ref="PR-SEC-42"
    )
    assert_error(
        "REMEDIATED_VERSION_REQUIRED", registry.transition, sample_operator(), finding.finding_id,
        expected_version=remediated.version, to_state=FindingState.VERIFIED, regression_report=old_report
    )
    regression_report = run_reference_campaign(hardened=True)
    verified, receipt = registry.transition(
        sample_operator(), finding.finding_id, expected_version=remediated.version,
        to_state=FindingState.VERIFIED, regression_report=regression_report
    )
    assert receipt.new_version == verified.version
    closed, _ = registry.transition(
        sample_operator(), finding.finding_id, expected_version=verified.version,
        to_state=FindingState.CLOSED
    )
    assert closed.state == FindingState.CLOSED
    assert len(registry.receipts) == 4


def test_finding_optimistic_version_blocks_stale_update():
    registry, finding, _, _ = _finding_fixture()
    registry.transition(
        sample_operator(), finding.finding_id, expected_version=1,
        to_state=FindingState.ACCEPTED, owner="security-engineering"
    )
    assert_error(
        "FINDING_VERSION_CONFLICT", registry.transition, sample_operator(), finding.finding_id,
        expected_version=1, to_state=FindingState.REMEDIATED, remediation_ref="PR-SEC-42"
    )


def test_common_tool_manifests_are_current_and_honest():
    tools = build_tool_integrations()
    assert set(tools) == {"pyrit", "garak", "promptfoo", "foundry"}
    assert tools["pyrit"].package == "pyrit>=1.1,<2"
    assert tools["garak"].package == "garak>=0.17,<1"
    assert "preview" in tools["foundry"].current_status.lower()
    assert "Remote generation" in tools["promptfoo"].boundary


def test_promptfoo_artifact_targets_only_local_authorized_fixture():
    config = build_promptfoo_config()
    assert config["targets"][0]["id"] == "file://authorized_local_target.py"
    assert config["metadata"] == {"environment": "purple-lab", "syntheticOnly": True}
    assert config["redteam"]["maxConcurrency"] == 1
    assert config["redteam"]["maxCharsPerMessage"] == 500
    assert config["env"]["PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION"] == "true"


def test_real_openai_agents_sdk_trace_objects_construct_without_starting():
    artifacts = build_openai_trace_artifacts()
    assert artifacts["trace"].name == "Course 12 synthetic red-team campaign"
    assert artifacts["trace"].metadata["synthetic"] is True
    assert artifacts["case_span"].span_data.name == "red_team_case"
