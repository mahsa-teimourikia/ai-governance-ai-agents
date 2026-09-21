from datetime import date
import importlib.util
from pathlib import Path
import sys

from jsonschema import validate
import pytest


@pytest.fixture()
def lab():
    path = Path(__file__).parents[1] / "curriculum/beginner/03-standards-regulation-and-governance-operating-model/lab.py"
    spec = importlib.util.spec_from_file_location("module03_lab", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_inventory_requires_explicit_boundaries_and_unique_capabilities(lab):
    system = lab.demo_system()
    payload = system.model_dump()
    payload["prohibited_use"] = ()
    with pytest.raises(ValueError, match="intended and prohibited"):
        lab.AgentSystemRecord(**payload)

    payload = system.model_dump()
    payload["capabilities"] = system.capabilities + (system.capabilities[0],)
    with pytest.raises(ValueError, match="identifiers must be unique"):
        lab.AgentSystemRecord(**payload)


def test_control_selection_uses_capability_facts_and_crosswalks_only_support(lab):
    system = lab.demo_system()
    controls = lab.select_controls(system, lab.control_library())
    selected_ids = {item.control_id for item in controls}
    assert selected_ids == {"AG-ASR-001", "AG-AUTH-001", "AG-HUM-001", "AG-INV-001", "AG-OBS-001", "AG-RSK-001"}
    assert all(mapping.relationship == "supports" for control in controls for mapping in control.mappings)


def test_regulatory_logic_routes_questions_without_auto_classifying(lab):
    system = lab.demo_system(include_eu=True)
    record = lab.build_applicability_record(
        system,
        completed_by={
            lab.ReviewDomain.SECURITY: "Security reviewer",
            lab.ReviewDomain.IMPACT_ASSESSMENT: "Impact reviewer",
        },
        as_of=lab.METHODOLOGY_SNAPSHOT,
    )
    assert lab.pending_review_domains(record) == (lab.ReviewDomain.EU_AI_ACT,)
    assert "does not constitute legal advice" in record.disclaimer


def test_evidence_is_bound_to_system_version_result_and_freshness(lab):
    as_of = lab.METHODOLOGY_SNAPSHOT
    system = lab.demo_system()
    controls = lab.select_controls(system, lab.control_library())
    evidence = list(lab.demo_evidence(system, controls, as_of=as_of))
    evidence[0] = evidence[0].model_copy(update={"system_version": "0.9.0"})
    evidence[1] = evidence[1].model_copy(update={"result": lab.EvidenceResult.FAIL})
    evidence[2] = evidence[2].model_copy(update={"valid_until": date(2026, 9, 19)})
    evidence[3] = evidence[3].model_copy(update={"produced_on": date(2026, 9, 21)})
    result = lab.assess_evidence(system, controls, evidence, as_of=as_of)
    assert result.satisfied_count == result.required_count - 4
    assert any("wrong_system_or_version" in item for item in result.rejected_evidence)
    assert any("failed_test_or_assessment" in item for item in result.rejected_evidence)
    assert any("expired" in item for item in result.rejected_evidence)
    assert any("future_dated" in item for item in result.rejected_evidence)

    duplicated = lab.demo_evidence(system, controls, as_of=as_of)
    with pytest.raises(ValueError, match="evidence identifiers must be unique"):
        lab.assess_evidence(system, controls, duplicated + (duplicated[0],), as_of=as_of)


def test_gate_approves_only_exact_bound_current_package(lab):
    package = lab.build_demo_package()
    assert package.decision.outcome is lab.GateOutcome.APPROVED_INTERNAL_RELEASE
    assert package.evidence_assessment.required_count == package.evidence_assessment.satisfied_count
    assert package.decision.legal_compliance_established is False
    assert package.decision.system_digest == lab.system_digest(package.system)
    assert package.decision.applicability_digest == lab.stable_digest(package.applicability)
    assert package.decision.evidence_assessment_digest == lab.stable_digest(package.evidence_assessment)
    assert len(package.decision.decision_digest) == 64


def test_gate_does_not_average_away_one_missing_requirement(lab):
    as_of = lab.METHODOLOGY_SNAPSHOT
    system = lab.demo_system()
    controls = lab.select_controls(system, lab.control_library())
    evidence = lab.demo_evidence(system, controls, as_of=as_of)[:-1]
    assessment = lab.assess_evidence(system, controls, evidence, as_of=as_of)
    applicability = lab.build_applicability_record(
        system, completed_by=lab.demo_completed_reviews(system), as_of=as_of
    )
    request = lab.GateRequest(
        request_id="GATE-MISSING-01",
        system_id=system.system_id,
        system_version=system.version,
        system_digest=lab.system_digest(system),
        control_profile_version=lab.CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    decision = lab.evaluate_gate(request, system, controls, applicability, assessment, as_of=as_of)
    assert decision.outcome is lab.GateOutcome.BLOCKED
    assert any(reason.startswith("missing_evidence:") for reason in decision.reason_codes)


def test_changed_system_invalidates_gate_request_and_old_evidence(lab):
    as_of = lab.METHODOLOGY_SNAPSHOT
    old_system = lab.demo_system()
    new_payload = old_system.model_dump()
    new_payload["version"] = "1.1.0"
    new_system = lab.AgentSystemRecord(**new_payload)
    controls = lab.select_controls(new_system, lab.control_library())
    old_evidence = lab.demo_evidence(old_system, lab.select_controls(old_system, lab.control_library()), as_of=as_of)
    assessment = lab.assess_evidence(new_system, controls, old_evidence, as_of=as_of)
    applicability = lab.build_applicability_record(
        new_system, completed_by=lab.demo_completed_reviews(new_system), as_of=as_of
    )
    request = lab.GateRequest(
        request_id="GATE-STALE-01",
        system_id=new_system.system_id,
        system_version=new_system.version,
        system_digest=lab.system_digest(old_system),
        control_profile_version=lab.CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    decision = lab.evaluate_gate(request, new_system, controls, applicability, assessment, as_of=as_of)
    assert decision.outcome is lab.GateOutcome.BLOCKED
    assert "request_digest_mismatch" in decision.reason_codes
    assert assessment.satisfied_count == 0


def test_pending_specialist_review_cannot_be_treated_as_approval(lab):
    as_of = lab.METHODOLOGY_SNAPSHOT
    system = lab.demo_system(include_eu=True)
    controls = lab.select_controls(system, lab.control_library())
    assessment = lab.assess_evidence(system, controls, lab.demo_evidence(system, controls, as_of=as_of), as_of=as_of)
    applicability = lab.build_applicability_record(system, completed_by={}, as_of=as_of)
    request = lab.GateRequest(
        request_id="GATE-REVIEW-01",
        system_id=system.system_id,
        system_version=system.version,
        system_digest=lab.system_digest(system),
        control_profile_version=lab.CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    decision = lab.evaluate_gate(request, system, controls, applicability, assessment, as_of=as_of)
    assert decision.outcome is lab.GateOutcome.SPECIALIST_REVIEW_REQUIRED
    assert lab.ReviewDomain.EU_AI_ACT in decision.pending_reviews


def test_expired_applicability_record_requires_fresh_specialist_review(lab):
    as_of = lab.METHODOLOGY_SNAPSHOT
    system = lab.demo_system()
    controls = lab.select_controls(system, lab.control_library())
    assessment = lab.assess_evidence(
        system, controls, lab.demo_evidence(system, controls, as_of=as_of), as_of=as_of
    )
    applicability = lab.build_applicability_record(
        system, completed_by=lab.demo_completed_reviews(system), as_of=date(2026, 1, 1)
    )
    request = lab.GateRequest(
        request_id="GATE-EXPIRED-REVIEW",
        system_id=system.system_id,
        system_version=system.version,
        system_digest=lab.system_digest(system),
        control_profile_version=lab.CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    decision = lab.evaluate_gate(request, system, controls, applicability, assessment, as_of=as_of)
    assert decision.outcome is lab.GateOutcome.SPECIALIST_REVIEW_REQUIRED
    assert "applicability_review_not_current" in decision.reason_codes


def test_gate_rejects_incomplete_applicability_and_evidence_populations(lab):
    as_of = lab.METHODOLOGY_SNAPSHOT
    system = lab.demo_system(include_eu=True)
    controls = lab.select_controls(system, lab.control_library())
    assessment = lab.assess_evidence(
        system, controls, lab.demo_evidence(system, controls, as_of=as_of), as_of=as_of
    )
    applicability = lab.build_applicability_record(
        system, completed_by=lab.demo_completed_reviews(system), as_of=as_of
    )
    incomplete_applicability = applicability.model_copy(update={"reviews": applicability.reviews[:-1]})
    incomplete_assessment = assessment.model_copy(
        update={
            "required_requirement_keys": assessment.required_requirement_keys[:-1],
            "required_count": assessment.required_count - 1,
            "satisfied_count": assessment.satisfied_count - 1,
        }
    )
    request = lab.GateRequest(
        request_id="GATE-POPULATION-01",
        system_id=system.system_id,
        system_version=system.version,
        system_digest=lab.system_digest(system),
        control_profile_version=lab.CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    decision = lab.evaluate_gate(
        request,
        system,
        controls,
        incomplete_applicability,
        incomplete_assessment,
        as_of=as_of,
    )
    assert decision.outcome is lab.GateOutcome.BLOCKED
    assert "applicability_review_coverage_mismatch" in decision.reason_codes
    assert "evidence_population_mismatch" in decision.reason_codes


def test_gate_rejects_a_caller_narrowed_control_profile(lab):
    as_of = lab.METHODOLOGY_SNAPSHOT
    system = lab.demo_system()
    full_controls = lab.select_controls(system, lab.control_library())
    narrowed_controls = full_controls[:-1]
    evidence = lab.demo_evidence(system, narrowed_controls, as_of=as_of)
    assessment = lab.assess_evidence(system, narrowed_controls, evidence, as_of=as_of)
    applicability = lab.build_applicability_record(
        system, completed_by=lab.demo_completed_reviews(system), as_of=as_of
    )
    request = lab.GateRequest(
        request_id="GATE-NARROWED-01",
        system_id=system.system_id,
        system_version=system.version,
        system_digest=lab.system_digest(system),
        control_profile_version=lab.CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    decision = lab.evaluate_gate(
        request, system, narrowed_controls, applicability, assessment, as_of=as_of
    )
    assert decision.outcome is lab.GateOutcome.BLOCKED
    assert "control_profile_coverage_mismatch" in decision.reason_codes


def test_current_failed_evidence_blocks_even_when_duplicate_pass_exists(lab):
    as_of = lab.METHODOLOGY_SNAPSHOT
    system = lab.demo_system()
    controls = lab.select_controls(system, lab.control_library())
    evidence = list(lab.demo_evidence(system, controls, as_of=as_of))
    evidence.append(
        evidence[0].model_copy(
            update={"evidence_id": "EV-FAILED-DUPLICATE", "result": lab.EvidenceResult.FAIL}
        )
    )
    assessment = lab.assess_evidence(system, controls, evidence, as_of=as_of)
    assert not assessment.missing_requirements
    applicability = lab.build_applicability_record(
        system, completed_by=lab.demo_completed_reviews(system), as_of=as_of
    )
    request = lab.GateRequest(
        request_id="GATE-FAILED-DUPLICATE",
        system_id=system.system_id,
        system_version=system.version,
        system_digest=lab.system_digest(system),
        control_profile_version=lab.CONTROL_PROFILE_VERSION,
        target_environment="production",
    )
    decision = lab.evaluate_gate(request, system, controls, applicability, assessment, as_of=as_of)
    assert decision.outcome is lab.GateOutcome.BLOCKED
    assert "blocking_evidence:EV-FAILED-DUPLICATE:failed_test_or_assessment" in decision.reason_codes


def test_raci_requires_one_accountable_role_and_complete_activity_coverage(lab):
    entries = lab.demo_raci()
    required = [item.activity for item in entries]
    assert lab.validate_raci(entries, required) == tuple(sorted(required))
    with pytest.raises(ValueError, match="exactly one accountable"):
        lab.RACIEntry(activity="Release", accountable=("Business", "Governance"), responsible=("Engineering",))
    with pytest.raises(ValueError, match="missing activities"):
        lab.validate_raci(entries, required + ["Retire system"])


def test_exceptions_expire_and_cannot_bypass_non_exception_controls(lab):
    system = lab.demo_system()
    controls = lab.select_controls(system, lab.control_library())
    exception = lab.ExceptionRecord(
        exception_id="EX-001",
        system_id=system.system_id,
        system_version=system.version,
        control_id="AG-AUTH-001",
        rationale="Authorization migration is incomplete.",
        compensating_controls=("Disable state-changing capabilities",),
        requester="Technical Owner",
        risk_acceptor="Business Owner",
        issued_on=date(2026, 8, 1),
        expires_on=date(2026, 9, 1),
        remediation_plan="Complete the policy enforcement migration.",
        evidence_ids=("EV-COMP-001",),
    )
    accepted, reasons = lab.evaluate_exception(exception, system, controls, as_of=lab.METHODOLOGY_SNAPSHOT)
    assert accepted is False
    assert reasons == (
        "control_not_exception_eligible",
        "exception_expired",
        "unverified_compensating_evidence",
    )


def test_material_change_detects_expansion_and_sets_reassessment_scope(lab):
    before = lab.demo_system()
    after_payload = before.model_dump()
    after_payload.update(
        version="2.0.0",
        jurisdictions=frozenset({"CA", "EU"}),
        autonomy=lab.AutonomyLevel.HIGH,
        affected_groups=("procurement staff", "suppliers", "job applicants"),
    )
    after = lab.AgentSystemRecord(**after_payload)
    result = lab.assess_change(lab.snapshot(before), lab.snapshot(after))
    assert lab.ChangeTrigger.JURISDICTION in result.triggers
    assert lab.ChangeTrigger.AUTONOMY in result.triggers
    assert lab.ChangeTrigger.AFFECTED_GROUP in result.triggers
    assert result.full_reassessment_required is True
    assert "legal and regulatory applicability" in result.reassessment_scopes


def test_governance_package_and_oscal_projection_are_honestly_labelled(lab):
    package = lab.build_demo_package()
    payload = package.model_dump(mode="json")
    validate(instance=payload, schema=lab.GOVERNANCE_PACKAGE_SCHEMA)
    projection = lab.oscal_component_projection(package.system, package.controls)
    assert projection["format"] == "teaching-projection-not-oscal-conformant"
    assert projection["target_oscal_version"] == "1.2.3"
    assert "Validate a real OSCAL artifact" in projection["validation_required"]


def test_labelled_gate_fixture_reports_explicit_denominator(lab):
    assert lab.evaluation_report() == {"correct": 5, "cases": 5, "decision_accuracy": 1.0}
