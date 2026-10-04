"""Focused invariants for Course 16 enterprise governance operating model."""

import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

MODULE = (
    Path(__file__).parents[1]
    / "curriculum/advanced/16-enterprise-agent-governance-operating-model"
)
sys.path.insert(0, str(MODULE))
sys.modules.pop("lab", None)

from lab import (  # noqa: E402
    CONTROL_BASELINES,
    REFERENCE_TIME,
    TENANT_ACME,
    TENANT_GLOBEX,
    AgentCard,
    ApprovalLedger,
    ChangeClass,
    Decision,
    DependencyKind,
    EvidenceStatus,
    GovernanceError,
    GovernanceRegistry,
    Incident,
    IncidentService,
    IncidentSeverity,
    IncidentStatus,
    Lifecycle,
    OperatorRole,
    RegistryAdminService,
    RiskTier,
    accepted_evidence_controls,
    assess_change,
    build_audit_package,
    build_course16_reference_run,
    build_interoperability_artifacts,
    build_operator,
    build_procurement_card,
    build_scenarios,
    classify_risk,
    complete_approvals,
    complete_evidence,
    create_exception,
    evaluate_operating_model,
    export_cyclonedx,
    gate_release,
    make_dependency,
    make_evidence,
    portfolio_metrics,
    recertify,
    release_package_digest,
    sha256_id,
    stable_digest,
    supply_chain_findings,
    verify_audit_package,
)


def clone(model, **changes):
    values = model.model_dump(mode="python")
    values.update(changes)
    return type(model)(**values)


def valid_release(release_id="release-test"):
    card = build_procurement_card()
    evidence = complete_evidence(card)
    ledger = ApprovalLedger()
    approvals = complete_approvals(card, release_id, ledger, evidence=evidence)
    return card, evidence, ledger, approvals


def active_incident_environment():
    card = build_procurement_card()
    registry = GovernanceRegistry()
    registry.register(card)
    for target in (
        Lifecycle.ASSESSING,
        Lifecycle.VALIDATING,
        Lifecycle.PENDING_APPROVAL,
        Lifecycle.APPROVED,
        Lifecycle.ACTIVE,
    ):
        record = registry.get(card.tenant_id, card.agent_id)
        registry.transition(
            card.tenant_id, card.agent_id, target, record.record_version
        )
    return card, registry, IncidentService(registry, frozenset({"siem-primary"}))


def test_digest_is_canonical():
    assert stable_digest({"b": {2, 1}, "a": 3}) == stable_digest({"a": 3, "b": {1, 2}})


def test_card_rejects_unknown_fields_and_external_actions_without_permissions():
    with pytest.raises(ValidationError):
        AgentCard(**build_procurement_card().model_dump(), asserted_safe=True)
    with pytest.raises(ValidationError, match="explicit permissions"):
        clone(build_procurement_card(), permissions=frozenset())


def test_card_rejects_ambiguous_owners_and_duplicate_dependencies():
    card = build_procurement_card()
    with pytest.raises(ValidationError, match="cannot collapse"):
        clone(
            card,
            business_owner_id="same",
            technical_owner_id="same",
            data_owner_id="same",
        )
    with pytest.raises(ValidationError, match="unique"):
        clone(card, dependencies=(card.dependencies[0], card.dependencies[0]))


def test_dependency_needs_version_digest_and_third_party_review():
    dep = build_procurement_card().dependencies[0]
    with pytest.raises(ValidationError):
        clone(dep, version="")
    with pytest.raises(ValidationError):
        clone(dep, digest="latest")
    with pytest.raises(ValidationError, match="review expiry"):
        clone(dep, review_expires_at=None)


def test_risk_rules_are_transparent_and_tiered():
    assert classify_risk(build_procurement_card()).tier == RiskTier.HIGH
    critical = clone(build_procurement_card(), autonomy=3, irreversibility=4)
    assert classify_risk(critical).tier == RiskTier.CRITICAL
    read_only = clone(
        build_procurement_card(),
        autonomy=0,
        impact=1,
        access=1,
        irreversibility=1,
        data_sensitivity=1,
        external_actions=False,
        permissions=frozenset(),
        dependencies=(make_dependency("internal-data", DependencyKind.DATA, "1.0.0"),),
    )
    assert classify_risk(read_only).tier == RiskTier.LOW
    assert len(CONTROL_BASELINES[RiskTier.LOW]) < len(CONTROL_BASELINES[RiskTier.HIGH])


def test_regulated_scope_has_high_floor():
    card = clone(
        build_procurement_card(),
        external_actions=False,
        permissions=frozenset(),
        regulatory_scopes=frozenset({"employment"}),
    )
    assert classify_risk(card).tier >= RiskTier.HIGH


def test_supply_chain_detects_unapproved_expired_and_empty_mcp():
    base = build_procurement_card()
    unapproved = clone(
        base.dependencies[0], approved=False, review_expires_at=REFERENCE_TIME
    )
    empty_mcp = make_dependency("empty-mcp", DependencyKind.MCP_SERVER, "1.0.0")
    findings = supply_chain_findings(clone(base, dependencies=(unapproved, empty_mcp)))
    assert "DEPENDENCY_NOT_APPROVED:foundation-model-x" in findings
    assert "THIRD_PARTY_REVIEW_EXPIRED:foundation-model-x" in findings
    assert "MCP_CAPABILITIES_NOT_DECLARED:empty-mcp" in findings


def test_evidence_requires_independent_assessor_and_positive_window():
    item = make_evidence(build_procurement_card(), "agent_card")
    with pytest.raises(ValidationError, match="different"):
        clone(item, assessor_id=item.producer_id)
    with pytest.raises(ValidationError, match="expiry"):
        clone(item, expires_at=item.generated_at)


def test_evidence_is_bound_to_scope_version_manifest_policy_and_signature():
    card = build_procurement_card()
    records = (
        make_evidence(card, "good"),
        make_evidence(card, "tenant", tenant_id=TENANT_GLOBEX),
        make_evidence(card, "version", version="9.9.9"),
        make_evidence(card, "manifest", bound_digest=sha256_id("other")),
        make_evidence(card, "policy", policy_version="old"),
    )
    accepted, reasons = accepted_evidence_controls(card, records)
    assert accepted == frozenset({"good"})
    assert len(reasons) == 4
    tampered = clone(records[0], status=EvidenceStatus.FAIL)
    assert accepted_evidence_controls(card, (tampered,))[1][0].startswith(
        "EVIDENCE_SIGNATURE_INVALID"
    )


def test_gate_passes_complete_current_package():
    card, evidence, ledger, approvals = valid_release()
    result = gate_release(card, evidence, approvals, "release-test", ledger)
    assert result.decision == Decision.PASS and not result.reason_codes


def test_gate_fails_closed_on_missing_or_stale_evidence():
    card, evidence, ledger, approvals = valid_release()
    missing = gate_release(card, evidence[:-1], approvals, "release-test", ledger)
    assert missing.decision == Decision.BLOCK
    stale = list(evidence)
    stale[0] = make_evidence(card, stale[0].control_id, expires_at=REFERENCE_TIME)
    rejected = gate_release(card, stale, approvals, "release-test", ledger)
    assert rejected.decision == Decision.BLOCK
    assert any(
        code.startswith("EVIDENCE_NOT_CURRENT") for code in rejected.reason_codes
    )


def test_approval_requires_authenticated_required_role_and_separation():
    card = build_procurement_card()
    ledger = ApprovalLedger()
    with pytest.raises(GovernanceError, match="NOT_AUTHENTICATED"):
        ledger.issue(
            build_operator(OperatorRole.PRODUCT_OWNER),
            card,
            RiskTier.HIGH,
            "r",
            OperatorRole.AI_RISK,
            frozenset(),
        )
    with pytest.raises(GovernanceError, match="NOT_REQUIRED"):
        ledger.issue(
            build_operator(OperatorRole.PRODUCT_OWNER),
            card,
            RiskTier.HIGH,
            "r",
            OperatorRole.PRODUCT_OWNER,
            frozenset(),
        )
    with pytest.raises(GovernanceError, match="SEPARATION"):
        ledger.issue(
            build_operator(OperatorRole.SECURITY_ASSURANCE, card.technical_owner_id),
            card,
            RiskTier.HIGH,
            "r",
            OperatorRole.SECURITY_ASSURANCE,
            frozenset(),
        )


def test_approval_rejects_tamper_release_version_and_expiry():
    card, _, ledger, approvals = valid_release()
    with pytest.raises(GovernanceError, match="SCOPE_MISMATCH"):
        ledger.validate(approvals[0], card, RiskTier.HIGH, "other")
    with pytest.raises(GovernanceError, match="SCOPE_MISMATCH"):
        ledger.validate(
            approvals[0], clone(card, version="3.3.0"), RiskTier.HIGH, "release-test"
        )
    with pytest.raises(GovernanceError, match="SIGNATURE_INVALID"):
        ledger.validate(
            clone(approvals[0], constraints=frozenset({"unlimited"})),
            card,
            RiskTier.HIGH,
            "release-test",
        )
    with pytest.raises(GovernanceError, match="EXPIRED"):
        ledger.validate(
            approvals[0], card, RiskTier.HIGH, "release-test", approvals[0].expires_at
        )


def test_approval_bundle_requires_roles_is_single_use_and_atomic():
    card, _, ledger, approvals = valid_release()
    with pytest.raises(GovernanceError, match="INCOMPLETE"):
        ledger.consume_bundle(approvals[:-1], card, RiskTier.HIGH, "release-test")
    results = []

    def consume():
        try:
            ledger.consume_bundle(approvals, card, RiskTier.HIGH, "release-test")
            return "pass"
        except GovernanceError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: consume(), range(4)))
    assert results.count("pass") == 1
    assert results.count("APPROVAL_ALREADY_CONSUMED") == 3


def test_nonwaivable_control_and_long_exception_are_rejected():
    card = build_procurement_card()
    operator = build_operator(OperatorRole.AI_RISK)
    with pytest.raises(GovernanceError, match="NOT_WAIVABLE"):
        create_exception(
            operator,
            card,
            "kill_switch",
            "Temporary implementation delay",
            frozenset({"disabled"}),
            "Implement and retest the control",
        )
    with pytest.raises(GovernanceError, match="TTL_OUT_OF_RANGE"):
        create_exception(
            operator,
            card,
            "red_team",
            "Independent test is scheduled",
            frozenset({"reduced-scope"}),
            "Complete the independent test",
            ttl=timedelta(days=91),
        )


def test_exact_signed_exception_can_substitute_one_control():
    card = build_procurement_card()
    evidence = tuple(
        item for item in complete_evidence(card) if item.control_id != "red_team"
    )
    exception = create_exception(
        build_operator(OperatorRole.AI_RISK),
        card,
        "red_team",
        "Independent test completes next week",
        frozenset({"reduced-scope", "enhanced-monitoring"}),
        "Complete the independent test and remove exception",
    )
    ledger = ApprovalLedger()
    approvals = complete_approvals(
        card, "r", ledger, evidence=evidence, exceptions=(exception,)
    )
    assert (
        gate_release(card, evidence, approvals, "r", ledger, (exception,)).decision
        == Decision.PASS
    )
    assert (
        gate_release(
            card,
            evidence,
            approvals,
            "r",
            ledger,
            (),
        ).decision
        == Decision.BLOCK
    )


def test_change_routing_invalidates_relevant_controls():
    before = build_procurement_card()
    prompt = clone(before, version="3.2.1", prompt_digest=sha256_id("new"))
    assert assess_change(before, prompt).change_class == ChangeClass.MATERIAL
    expanded = clone(
        before, version="3.3.0", permissions=before.permissions | {"vendor.create"}
    )
    major = assess_change(before, expanded)
    assert (
        major.change_class == ChangeClass.MAJOR
        and "approval" in major.invalidated_controls
    )
    external = clone(
        clone(before, external_actions=False), version="4.0.0", external_actions=True
    )
    assert assess_change(
        clone(before, external_actions=False), external
    ).suspend_before_review


def test_change_requires_new_version_and_same_identity():
    card = build_procurement_card()
    with pytest.raises(GovernanceError, match="NEW_VERSION"):
        assess_change(card, clone(card, prompt_digest=sha256_id("new")))
    with pytest.raises(GovernanceError, match="IDENTITY_MISMATCH"):
        assess_change(card, clone(card, version="3.3.0", agent_id="other-agent"))


def test_registry_is_tenant_scoped_concurrent_and_transitioned():
    registry = GovernanceRegistry()
    registry.register(build_procurement_card())
    with pytest.raises(GovernanceError, match="NOT_REGISTERED"):
        registry.get(TENANT_GLOBEX, "procurement-agent")
    current = registry.transition(
        TENANT_ACME, "procurement-agent", Lifecycle.ASSESSING, 1
    )
    assert current.record_version == 2
    with pytest.raises(GovernanceError, match="VERSION_CONFLICT"):
        registry.transition(TENANT_ACME, "procurement-agent", Lifecycle.VALIDATING, 1)
    with pytest.raises(GovernanceError, match="INVALID_LIFECYCLE"):
        registry.transition(TENANT_ACME, "procurement-agent", Lifecycle.ACTIVE, 2)


def test_registry_routes_major_and_critical_replacements():
    before = build_procurement_card()
    registry = GovernanceRegistry()
    registry.register(before)
    major_card = clone(
        before, version="3.3.0", permissions=before.permissions | {"vendor.create"}
    )
    major, _ = registry.replace_card(major_card, 1)
    assert major.lifecycle == Lifecycle.ASSESSING
    registry2 = GovernanceRegistry()
    base = clone(before, external_actions=False)
    registry2.register(base)
    critical, _ = registry2.replace_card(
        clone(base, version="4.0.0", external_actions=True), 1
    )
    assert critical.lifecycle == Lifecycle.SUSPENDED


def test_incident_rejects_untrusted_or_invalid_alert_and_deduplicates():
    card, _, service = active_incident_environment()
    with pytest.raises(GovernanceError, match="NOT_TRUSTED"):
        service.admit(
            "a",
            "model-text",
            sha256_id("a"),
            card.tenant_id,
            card.agent_id,
            "misuse",
            IncidentSeverity.HIGH,
        )
    with pytest.raises(GovernanceError, match="DIGEST_INVALID"):
        service.admit(
            "a",
            "siem-primary",
            "bad",
            card.tenant_id,
            card.agent_id,
            "misuse",
            IncidentSeverity.HIGH,
        )
    args = (
        "a",
        "siem-primary",
        sha256_id("a"),
        card.tenant_id,
        card.agent_id,
        "misuse",
        IncidentSeverity.HIGH,
    )
    assert service.admit(*args) == service.admit(*args)


def test_incident_containment_changes_registry_and_preserves_evidence():
    card, registry, service = active_incident_environment()
    incident = service.admit(
        "a",
        "siem-primary",
        sha256_id("a"),
        card.tenant_id,
        card.agent_id,
        "misuse",
        IncidentSeverity.HIGH,
    )
    with pytest.raises(GovernanceError, match="COMMANDER"):
        service.contain(
            incident.incident_id, build_operator(OperatorRole.AI_RISK), ("trace",)
        )
    contained = service.contain(
        incident.incident_id,
        build_operator(OperatorRole.INCIDENT_COMMANDER),
        ("trace", "policy"),
    )
    assert registry.get(card.tenant_id, card.agent_id).lifecycle == Lifecycle.SUSPENDED
    assert (
        contained.status == IncidentStatus.CONTAINED
        and "DISABLE_AGENT" in contained.containment_actions
    )


def test_recovery_requires_security_evidence_then_risk_closure():
    card, _, service = active_incident_environment()
    incident = service.admit(
        "a",
        "siem-primary",
        sha256_id("a"),
        card.tenant_id,
        card.agent_id,
        "misuse",
        IncidentSeverity.HIGH,
    )
    service.contain(
        incident.incident_id,
        build_operator(OperatorRole.INCIDENT_COMMANDER),
        ("trace",),
    )
    with pytest.raises(GovernanceError, match="RECOVERY_EVIDENCE"):
        service.close(incident.incident_id, build_operator(OperatorRole.AI_RISK))
    recovery = service.request_recovery(
        incident.incident_id,
        build_operator(OperatorRole.SECURITY_ASSURANCE),
        "remediation-1",
    )
    assert (
        service.close(recovery.incident_id, build_operator(OperatorRole.AI_RISK)).status
        == IncidentStatus.CLOSED
    )


def test_recertification_blocks_open_incident_and_missing_package():
    card = build_procurement_card()
    record = GovernanceRegistry().register(card)
    incident = Incident(
        incident_id="i",
        alert_id="a",
        tenant_id=card.tenant_id,
        agent_id=card.agent_id,
        severity=IncidentSeverity.HIGH,
        kind="misuse",
        source_id="siem",
        source_digest=sha256_id("a"),
        status=IncidentStatus.OPEN,
        opened_at=REFERENCE_TIME,
    )
    result = recertify(record, (), (), (incident,), ())
    assert result.decision == Decision.REVIEW and "OPEN_INCIDENT" in result.reason_codes


def test_cyclonedx_export_is_current_deterministic_and_typed():
    first = export_cyclonedx(build_procurement_card())
    second = export_cyclonedx(build_procurement_card())
    assert (
        first["specVersion"] == "1.7"
        and first["serialNumber"] == second["serialNumber"]
    )
    assert {c["type"] for c in first["components"]} >= {
        "machine-learning-model",
        "data",
        "application",
    }
    assert all(c["hashes"][0]["alg"] == "SHA-256" for c in first["components"])


def test_evaluation_exposes_numerators_denominators_and_baseline_gap():
    metrics = evaluate_operating_model(build_scenarios())["metrics"]
    assert metrics["governed_decision_correctness"] == {
        "numerator": 15,
        "denominator": 15,
        "value": 1.0,
    }
    assert metrics["unsafe_release_prevention"] == {
        "numerator": 13,
        "denominator": 13,
        "value": 1.0,
    }
    assert metrics["valid_release_pass_rate"] == {
        "numerator": 2,
        "denominator": 2,
        "value": 1.0,
    }
    assert (
        metrics["baseline_decision_correctness"]["value"]
        < metrics["governed_decision_correctness"]["value"]
    )


def test_portfolio_metrics_define_population_and_rates():
    registry = GovernanceRegistry()
    first = registry.register(build_procurement_card())
    second_card = clone(
        build_procurement_card(tenant_id=TENANT_GLOBEX),
        agent_id="research-agent",
        external_actions=False,
        permissions=frozenset(),
    )
    second = registry.register(second_card)
    report = portfolio_metrics((first, second))
    assert report["population"].startswith("registered agent")
    assert report["high_or_critical"]["denominator"] == 2


def test_reference_run_connects_record_gate_bom_and_evaluation():
    run = build_course16_reference_run()
    assert run["assessment"].tier == RiskTier.HIGH
    assert run["gate"].decision == Decision.PASS
    assert run["bom"]["specVersion"] == "1.7"
    assert run["evaluation"]["metrics"]["governed_decision_correctness"]["value"] == 1.0


def test_example_agent_card_tracks_reference_contract():
    import yaml

    document = yaml.safe_load(
        (MODULE / "agent-card.example.yaml").read_text(encoding="utf-8")
    )
    assert document["apiVersion"] == "governance.oneplusi.io/v1"
    assert document["metadata"]["id"] == "procurement-agent"
    assert (
        document["spec"]["controls"]["policyBundle"]
        == "enterprise-agent-governance/16.1"
    )
    assert all(
        item["digest"].startswith("sha256:")
        for item in document["spec"]["dependencies"]
    )


def test_approval_package_digest_rejects_added_or_replaced_evidence():
    card, evidence, ledger, approvals = valid_release()
    changed = evidence + (make_evidence(card, "optional-new-evidence"),)
    result = gate_release(card, changed, approvals, "release-test", ledger)
    assert result.decision == Decision.BLOCK
    assert "APPROVAL_SCOPE_MISMATCH" in result.reason_codes
    assert approvals[0].package_digest != release_package_digest(
        card, RiskTier.HIGH, "release-test", changed
    )


def test_exception_signature_tamper_is_rejected():
    card = build_procurement_card()
    evidence = tuple(
        item for item in complete_evidence(card) if item.control_id != "red_team"
    )
    exception = create_exception(
        build_operator(OperatorRole.AI_RISK),
        card,
        "red_team",
        "Independent test completes next week",
        frozenset({"reduced-scope", "enhanced-monitoring"}),
        "Complete the independent test and remove exception",
    )
    forged = clone(exception, signature="0" * 64)
    ledger = ApprovalLedger()
    approvals = complete_approvals(
        card, "r", ledger, evidence=evidence, exceptions=(forged,)
    )
    result = gate_release(card, evidence, approvals, "r", ledger, (forged,))
    assert result.decision == Decision.BLOCK
    assert any(code.startswith("EXCEPTION_INVALID") for code in result.reason_codes)


def test_registry_admin_is_authenticated_and_gate_bound():
    card = build_procurement_card()
    registry = GovernanceRegistry()
    admin = RegistryAdminService(registry)
    with pytest.raises(GovernanceError, match="ROLE_REQUIRED"):
        admin.register(build_operator(OperatorRole.PRODUCT_OWNER), card)
    with pytest.raises(GovernanceError, match="TENANT_MISMATCH"):
        admin.register(
            build_operator(OperatorRole.PORTFOLIO_REGISTRAR, tenant_id=TENANT_GLOBEX),
            card,
        )
    record = admin.register(build_operator(OperatorRole.PORTFOLIO_REGISTRAR), card)
    operator = build_operator(OperatorRole.GOVERNANCE_OPERATOR)
    for target in (
        Lifecycle.ASSESSING,
        Lifecycle.VALIDATING,
        Lifecycle.PENDING_APPROVAL,
    ):
        record = admin.transition(
            operator, card.tenant_id, card.agent_id, target, record.record_version
        )
    with pytest.raises(GovernanceError, match="PASSING_BOUND_GATE"):
        admin.transition(
            operator,
            card.tenant_id,
            card.agent_id,
            Lifecycle.APPROVED,
            record.record_version,
        )
    card2, evidence, ledger, approvals = valid_release("admin-release")
    gate = gate_release(card2, evidence, approvals, "admin-release", ledger)
    approved = admin.transition(
        operator,
        card.tenant_id,
        card.agent_id,
        Lifecycle.APPROVED,
        record.record_version,
        gate=gate,
    )
    assert approved.lifecycle == Lifecycle.APPROVED


def test_audit_package_binds_record_gate_and_detects_tamper():
    run = build_course16_reference_run()
    package = run["audit"]
    assert verify_audit_package(package)
    tampered = dict(package)
    tampered["package"] = {**package["package"], "generated_at": "changed"}
    assert not verify_audit_package(tampered)
    wrong_record = clone(run["registered"], card=clone(run["card"], version="3.3.0"))
    with pytest.raises(GovernanceError, match="AUDIT_GATE_MANIFEST_MISMATCH"):
        build_audit_package(
            wrong_record,
            run["assessment"],
            run["gate"],
            (),
            (),
        )


def test_real_interoperability_artifacts_are_offline_and_current():
    artifacts = build_interoperability_artifacts(build_procurement_card())
    assert set(artifacts["versions"]) == {
        "cyclonedx-python-lib",
        "sigstore",
        "opentelemetry-sdk",
        "pydantic",
    }
    assert type(artifacts["sigstore_identity_policy"]).__name__ == "Identity"
    assert (
        artifacts["slsa_statement"]["predicateType"] == "https://slsa.dev/provenance/v1"
    )
    assert artifacts["otel_spans"][0]["name"] == "governance.release_gate"


def test_scenario_corpus_has_two_valid_and_thirteen_unsafe_cases():
    scenarios = build_scenarios()
    assert len(scenarios) == 15
    assert len({item.scenario_id for item in scenarios}) == 15
    assert sum(item.label == "valid" for item in scenarios) == 2
    assert sum(item.label == "unsafe" for item in scenarios) == 13


def test_notebook_is_clean_and_imports_canonical_lab():
    import json

    notebook = json.loads(
        (MODULE / "16_enterprise_agent_governance_operating_model.ipynb").read_text()
    )
    sources = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "%pip" not in sources
    assert "import lab" in sources
    assert all(
        cell.get("outputs", []) == [] and cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )


def test_diagram_specs_are_accessible_and_geometry_safe():
    specs = sorted((MODULE / "assets/specs").glob("*.yaml"))
    assert len(specs) == 5

    for spec_path in specs:
        spec = yaml.safe_load(spec_path.read_text())
        canvas = spec["canvas"]
        assert spec["version"] == 1
        assert spec["output"]["alt_text"]

        nodes = spec["nodes"]
        node_by_id = {node["id"]: node for node in nodes}
        assert len(node_by_id) == len(nodes)
        for node in nodes:
            bounds = node["bounds"]
            assert 0 <= bounds["x"] < bounds["x"] + bounds["width"] <= canvas["width"]
            assert 0 <= bounds["y"] < bounds["y"] + bounds["height"] <= canvas["height"]

        for index, left in enumerate(nodes):
            a = left["bounds"]
            for right in nodes[index + 1 :]:
                b = right["bounds"]
                assert (
                    a["x"] + a["width"] <= b["x"]
                    or b["x"] + b["width"] <= a["x"]
                    or a["y"] + a["height"] <= b["y"]
                    or b["y"] + b["height"] <= a["y"]
                )

        edge_ids = {edge["id"] for edge in spec["edges"]}
        assert len(edge_ids) == len(spec["edges"])
        for edge in spec["edges"]:
            for endpoint_name in ("from", "to"):
                endpoint = edge[endpoint_name]
                assert endpoint["node"] in node_by_id
                assert endpoint["port"] in node_by_id[endpoint["node"]]["ports"]
            assert all(
                0 <= point[0] <= canvas["width"] and 0 <= point[1] <= canvas["height"]
                for point in edge["route"]
            )

        svg_path = (spec_path.parent / spec["output"]["svg"]).resolve()
        svg_root = ET.parse(svg_path).getroot()
        assert svg_root.attrib["width"] == str(canvas["width"])
        assert svg_root.attrib["height"] == str(canvas["height"])
        assert svg_root.find("{http://www.w3.org/2000/svg}title") is not None
        assert svg_root.find("{http://www.w3.org/2000/svg}desc") is not None
