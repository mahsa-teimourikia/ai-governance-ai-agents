from datetime import date
import importlib.util
from pathlib import Path
import sys

import pytest


@pytest.fixture()
def lab():
    path = Path(__file__).parents[1] / "curriculum/beginner/02-agent-risk-modeling-and-autonomy-classification/lab.py"
    spec = importlib.util.spec_from_file_location("module02_lab", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_autonomy_classification_uses_observable_authority(lab):
    informational = lab.classify_autonomy(lab.AutonomySignals(produces_recommendations=True))
    bounded = lab.classify_autonomy(lab.AutonomySignals(
        prepares_state_change=True, executes_state_change=True, every_state_change_preapproved=True,
    ))
    high = lab.classify_autonomy(lab.AutonomySignals(
        prepares_state_change=True, executes_state_change=True, every_state_change_preapproved=False,
        selects_tools_or_plans_steps=True, can_delegate=True,
    ))
    assert informational.level is lab.AutonomyLevel.INFORMATIONAL
    assert bounded.level is lab.AutonomyLevel.BOUNDED
    assert high.level is lab.AutonomyLevel.HIGH


def test_same_autonomy_can_have_different_risk(lab):
    capabilities = lab.demo_capabilities()
    low_dimensions = lab.RiskDimensions(
        severity=lab.OrdinalLevel.LOW, likelihood=lab.OrdinalLevel.LOW,
        detectability_difficulty=lab.OrdinalLevel.LOW, irreversibility=lab.OrdinalLevel.LOW,
        scope=lab.OrdinalLevel.LOW,
    )
    payment = next(item for item in lab.demo_scenarios() if item.scenario_id == "ADV-001")
    low_tier, _ = lab.classify_risk(low_dimensions, lab.AutonomyLevel.HIGH)
    payment_tier, _ = lab.classify_risk(payment.dimensions, capabilities["payment"].autonomy)
    assert low_tier is lab.RiskTier.LOW
    assert payment_tier is lab.RiskTier.CRITICAL


def test_assumed_control_does_not_reduce_residual_risk(lab):
    capabilities = lab.demo_capabilities()
    scenario = next(item for item in lab.demo_scenarios() if item.scenario_id == "OPS-001")
    claim = lab.MitigationClaim(
        scenario_id=scenario.scenario_id, control_id="idempotency", dimension="likelihood",
        from_level=lab.OrdinalLevel.MODERATE, to_level=lab.OrdinalLevel.LOW,
    )
    evidence = lab.ControlEvidence(
        evidence_id="e-planned", control_id="idempotency", scenario_ids=frozenset({scenario.scenario_id}),
        control_type=lab.ControlType.PREVENT, status=lab.EvidenceStatus.DOCUMENTED,
        evidence_ref="design-doc-12",
    )
    result = lab.assess(scenario, capabilities[scenario.capability_id], claims=[claim], evidence=[evidence])
    assert result.residual_dimensions == result.inherent_dimensions
    assert "idempotency:likelihood:evidence_not_tested" in result.rejected_claims


def test_current_scenario_specific_evidence_can_support_reduction(lab):
    capabilities = lab.demo_capabilities()
    scenario = next(item for item in lab.demo_scenarios() if item.scenario_id == "OPS-001")
    claim = lab.MitigationClaim(
        scenario_id=scenario.scenario_id, control_id="idempotency", dimension="likelihood",
        from_level=lab.OrdinalLevel.MODERATE, to_level=lab.OrdinalLevel.LOW,
    )
    evidence = lab.ControlEvidence(
        evidence_id="e-tested", control_id="idempotency", scenario_ids=frozenset({scenario.scenario_id}),
        control_type=lab.ControlType.PREVENT, status=lab.EvidenceStatus.TESTED,
        evidence_ref="tests/test_module01_governance.py::test_idempotent_retry_does_not_duplicate_effect",
        valid_through=date(2026, 12, 31),
    )
    result = lab.assess(scenario, capabilities[scenario.capability_id], claims=[claim], evidence=[evidence])
    assert result.residual_dimensions.likelihood is lab.OrdinalLevel.LOW
    assert result.applied_claims == ("idempotency:likelihood",)


def test_verified_control_evidence_requires_a_validity_date(lab):
    with pytest.raises(ValueError, match="validity date"):
        lab.ControlEvidence(
            evidence_id="e-undated", control_id="idempotency", scenario_ids=frozenset({"OPS-001"}),
            control_type=lab.ControlType.PREVENT, status=lab.EvidenceStatus.TESTED,
            evidence_ref="test-idempotency-001",
        )


def test_assessment_rejects_a_mismatched_capability(lab):
    capabilities = lab.demo_capabilities()
    scenario = next(item for item in lab.demo_scenarios() if item.scenario_id == "OPS-001")
    with pytest.raises(ValueError, match="applies to purchase_order"):
        lab.assess(scenario, capabilities["payment"])


def test_expired_or_wrong_scenario_evidence_is_rejected(lab):
    capabilities = lab.demo_capabilities()
    scenario = next(item for item in lab.demo_scenarios() if item.scenario_id == "OPS-001")
    claim = lab.MitigationClaim(
        scenario_id=scenario.scenario_id, control_id="idempotency", dimension="likelihood",
        from_level=lab.OrdinalLevel.MODERATE, to_level=lab.OrdinalLevel.LOW,
    )
    expired = lab.ControlEvidence(
        evidence_id="e-old", control_id="idempotency", scenario_ids=frozenset({scenario.scenario_id}),
        control_type=lab.ControlType.PREVENT, status=lab.EvidenceStatus.TESTED,
        evidence_ref="old-test", valid_through=date(2026, 1, 1),
    )
    result = lab.assess(scenario, capabilities[scenario.capability_id], claims=[claim], evidence=[expired])
    assert result.rejected_claims == ("idempotency:likelihood:evidence_expired",)

    wrong_scenario = expired.model_copy(
        update={"evidence_id": "e-wrong", "scenario_ids": frozenset({"ADV-001"}), "valid_through": date(2026, 12, 31)}
    )
    result = lab.assess(scenario, capabilities[scenario.capability_id], claims=[claim], evidence=[wrong_scenario])
    assert result.rejected_claims == ("idempotency:likelihood:no_scenario_evidence",)


def test_blast_radius_reports_counts_not_magic_score(lab):
    broad = lab.blast_radius(lab.procurement_graph(include_finance=True))
    constrained = lab.blast_radius(lab.procurement_graph(include_finance=False))
    assert broad.reachable_assets == (
        "email_gateway", "erp", "payment_service", "public_web", "purchase_api", "research_agent", "vendor_db",
    )
    assert broad.writable_assets == (
        "email_gateway", "erp", "payment_service", "purchase_api", "research_agent",
    )
    assert broad.severe_assets == ("erp", "payment_service")
    assert broad.trust_zone_crossings == 4
    assert broad.delegated_hops == 1
    assert constrained.reachable_assets == (
        "email_gateway", "erp", "public_web", "purchase_api", "research_agent", "vendor_db",
    )
    assert constrained.writable_assets == ("email_gateway", "erp", "purchase_api", "research_agent")
    assert constrained.severe_assets == ("erp",)
    assert constrained.trust_zone_crossings == 4
    assert constrained.delegated_hops == 1


def test_operational_and_adversarial_scenarios_remain_distinct(lab):
    kinds = {item.scenario_id: item.kind for item in lab.demo_scenarios()}
    assert kinds["OPS-001"] is lab.ScenarioKind.OPERATIONAL
    assert kinds["ADV-001"] is lab.ScenarioKind.ADVERSARIAL


def test_labelled_fixture_reports_explicit_denominator(lab):
    report = lab.evaluation_report()
    assert report == {"correct": 3, "cases": 3, "classification_accuracy": 1.0}


def test_higher_tier_control_profiles_are_cumulative(lab):
    controls = lab.required_controls(lab.RiskTier.CRITICAL)
    assert "owner" in controls
    assert "schema_validation" in controls
    assert "runtime_authorization" in controls
    assert "reduce_autonomy" in controls
