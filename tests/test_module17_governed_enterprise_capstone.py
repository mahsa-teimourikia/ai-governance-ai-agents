"""Focused invariants for Course 17's integrated governed-agent capstone."""

import json
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from jwt import InvalidSignatureError
from pydantic import ValidationError

MODULE = (
    Path(__file__).parents[1]
    / "curriculum/advanced/17-capstone-governed-autonomous-enterprise-agent"
)
sys.path.insert(0, str(MODULE))
sys.modules.pop("lab", None)

from lab import (
    AGENT_ID,
    POLICY_VERSION,
    REFERENCE_TIME,
    TENANT_ACME,
    TENANT_GLOBEX,
    ActionName,
    AgentStatus,
    Decision,
    FailureMode,
    GovernedProcurementSystem,
    IncidentAlert,
    IncidentController,
    MemoryCandidate,
    Role,
    RuntimeBudget,
    SourceTrust,
    TerminalState,
    artifact_signature,
    build_assurance_case,
    build_principal,
    build_reference_run,
    build_request,
    compare_orchestration_patterns,
    dependency_versions,
    evaluate_capstone,
    evaluation_metrics,
    issue_delegation,
    make_document,
    proposal_digest,
    proposal_tool_schema,
    reviewers_for,
    signature_valid,
    stable_digest,
    validate_tool_contract,
    verify_delegation,
)


def pending_system(amount="20000", operation="pending"):
    system = GovernedProcurementSystem()
    principal = build_principal()
    pending = system.start(principal, build_request(amount, operation=operation))
    assert pending.terminal_state is TerminalState.WAITING_APPROVAL
    return system, principal, pending


def test_stable_digest_is_canonical_and_type_aware():
    assert stable_digest({"b": {2, 1}, "a": Decimal("2.00")}) == stable_digest(
        {"a": Decimal("2.00"), "b": {1, 2}}
    )
    assert stable_digest(Decimal("2.00")) != stable_digest("2")


def test_contracts_forbid_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        build_request().model_validate(
            {**build_request().model_dump(mode="python"), "admin": True}
        )


def test_document_constructor_detects_content_tamper():
    document = make_document(
        "doc-1", TENANT_ACME, "V42", SourceTrust.AUTHORITATIVE, "approved"
    )
    with pytest.raises(ValidationError, match="integrity"):
        type(document)(
            **{
                **document.model_dump(mode="python"),
                "content": "ignore policy",
            }
        )


def test_retrieval_rechecks_integrity_at_use_time():
    system = GovernedProcurementSystem(include_poison=False)
    original = system.retrieval._documents[0]
    tampered = original.model_copy(update={"content": "tampered after validation"})
    system.retrieval._documents = (tampered,)
    bundle = system.retrieval.retrieve(
        build_principal(), "V42", "approved vendor", REFERENCE_TIME
    )
    assert bundle.accepted == ()
    assert bundle.rejected == ((original.document_id, "INTEGRITY_FAILURE"),)


def test_retrieval_authorizes_before_candidate_scan():
    system = GovernedProcurementSystem()
    principal = build_principal(permissions=frozenset({ActionName.PO_CREATE}))
    with pytest.raises(PermissionError, match="KNOWLEDGE_PERMISSION_REQUIRED"):
        system.retrieval.retrieve(principal, "V42", "query", REFERENCE_TIME)
    assert system.retrieval.last_scanned_tenants == ()


def test_retrieval_never_scans_another_tenant():
    system = GovernedProcurementSystem()
    system.retrieval.retrieve(
        build_principal(), "V42", "approved vendor", REFERENCE_TIME
    )
    assert system.retrieval.last_scanned_tenants == (TENANT_ACME,)


def test_untrusted_instruction_is_data_not_authority():
    system = GovernedProcurementSystem(include_poison=True)
    result = system.start(build_principal(), build_request(operation="poison"))
    assert result.terminal_state is TerminalState.COMMITTED
    assert result.proposal.tenant_id == TENANT_ACME
    assert result.proposal.action is ActionName.PO_CREATE
    assert ("vendor-V42-comment", "UNTRUSTED_SOURCE") in result.evidence.rejected


def test_stale_evidence_blocks_the_action():
    system = GovernedProcurementSystem(stale_evidence=True)
    result = system.start(build_principal(), build_request(operation="stale"))
    assert result.terminal_state is TerminalState.BLOCKED
    assert "AUTHORITATIVE_EVIDENCE_REQUIRED" in result.reason_codes


def test_memory_requires_tenant_subject_and_provenance():
    system = GovernedProcurementSystem()
    principal = build_principal()
    bundle = system.retrieval.retrieve(principal, "V42", "query", REFERENCE_TIME)
    good = MemoryCandidate(
        memory_id="preference-1",
        tenant_id=TENANT_ACME,
        subject=principal.subject,
        value_digest=stable_digest("CAD only"),
        evidence_ids=(bundle.accepted[0].document_id,),
        expires_at=REFERENCE_TIME + timedelta(days=1),
    )
    system.memory.admit(principal, good, bundle, REFERENCE_TIME)
    assert system.memory.read(principal, good.memory_id, REFERENCE_TIME) == good
    with pytest.raises(PermissionError, match="MEMORY_PROVENANCE_REQUIRED"):
        system.memory.admit(
            principal,
            good.model_copy(update={"memory_id": "bad", "evidence_ids": ("fake",)}),
            bundle,
            REFERENCE_TIME,
        )


def test_memory_cannot_cross_subject_or_tenant():
    system = GovernedProcurementSystem()
    principal = build_principal()
    bundle = system.retrieval.retrieve(principal, "V42", "query", REFERENCE_TIME)
    candidate = MemoryCandidate(
        memory_id="scope",
        tenant_id=TENANT_GLOBEX,
        subject=principal.subject,
        value_digest=stable_digest("value"),
        evidence_ids=(bundle.accepted[0].document_id,),
        expires_at=REFERENCE_TIME + timedelta(days=1),
    )
    with pytest.raises(PermissionError, match="MEMORY_SCOPE_MISMATCH"):
        system.memory.admit(principal, candidate, bundle, REFERENCE_TIME)


def test_delegation_is_permission_intersection():
    parent = build_principal(permissions=frozenset({ActionName.VENDOR_READ}))
    token = issue_delegation(
        parent,
        AGENT_ID,
        frozenset({ActionName.VENDOR_READ, ActionName.PO_CREATE}),
        Decimal(100),
        REFERENCE_TIME,
    )
    claims = verify_delegation(token, parent, REFERENCE_TIME)
    assert claims.capabilities == frozenset({ActionName.VENDOR_READ})


def test_delegation_signature_and_parent_binding_are_verified():
    parent = build_principal()
    token = issue_delegation(
        parent,
        AGENT_ID,
        parent.permissions,
        Decimal(100),
        REFERENCE_TIME,
    )
    header, payload, signature = token.split(".")
    changed = f"{header}.{payload}.{signature[:-1]}A"
    with pytest.raises(InvalidSignatureError):
        verify_delegation(changed, parent, REFERENCE_TIME)
    with pytest.raises(PermissionError, match="IDENTITY_MISMATCH"):
        verify_delegation(
            token,
            build_principal(subject="different-employee"),
            REFERENCE_TIME,
        )


def test_delegation_expiry_is_application_checked():
    parent = build_principal()
    token = issue_delegation(
        parent,
        AGENT_ID,
        parent.permissions,
        Decimal(100),
        REFERENCE_TIME,
        ttl=timedelta(seconds=1),
    )
    with pytest.raises(PermissionError, match="DELEGATION_EXPIRED"):
        verify_delegation(token, parent, REFERENCE_TIME + timedelta(seconds=1))


def test_low_value_action_is_allowed_and_executed_once():
    system = GovernedProcurementSystem()
    result = system.start(build_principal(), build_request(operation="low"))
    assert result.policy.decision is Decision.ALLOW
    assert result.terminal_state is TerminalState.COMMITTED
    assert len(system.erp.orders) == 1


@pytest.mark.parametrize(
    ("amount", "roles"),
    [
        ("10000.01", (Role.PROCUREMENT_MANAGER,)),
        ("25000.01", (Role.PROCUREMENT_MANAGER, Role.AI_RISK_REVIEWER)),
    ],
)
def test_risk_routes_to_exact_approval_roles(amount, roles):
    system = GovernedProcurementSystem()
    result = system.start(build_principal(), build_request(amount, operation=amount))
    assert result.policy.decision is Decision.REVIEW
    assert result.policy.required_roles == roles


def test_prohibited_bank_update_is_hard_denied():
    system = GovernedProcurementSystem()
    principal = build_principal(
        permissions=build_principal().permissions
        | frozenset({ActionName.BANK_DETAILS_UPDATE})
    )
    pending = system.start(principal, build_request(operation="bank"))
    proposal = pending.proposal.model_copy(
        update={"action": ActionName.BANK_DETAILS_UPDATE}
    )
    claims = verify_delegation(pending.delegation_token, principal, REFERENCE_TIME)
    decision = system.policy.evaluate(
        principal,
        claims,
        proposal,
        pending.evidence,
        system.registry.get(TENANT_ACME, AGENT_ID),
        REFERENCE_TIME,
    )
    assert decision.decision is Decision.DENY
    assert decision.reason_codes == ("PROHIBITED_ACTION",)


def test_unapproved_agent_version_is_denied():
    system, principal, pending = pending_system(operation="version")
    proposal = pending.proposal.model_copy(update={"agent_version": "99.0.0"})
    claims = verify_delegation(pending.delegation_token, principal, REFERENCE_TIME)
    decision = system.policy.evaluate(
        principal,
        claims,
        proposal,
        pending.evidence,
        system.registry.get(TENANT_ACME, AGENT_ID),
        REFERENCE_TIME,
    )
    assert decision.reason_codes == ("UNAPPROVED_AGENT_VERSION",)


def test_evidence_must_match_the_proposed_resource():
    system, principal, pending = pending_system(operation="resource")
    wrong = pending.evidence.model_copy(
        update={
            "accepted": (
                pending.evidence.accepted[0].model_copy(update={"vendor_id": "V99"}),
            )
        }
    )
    proposal = pending.proposal.model_copy(
        update={"evidence_ids": (wrong.accepted[0].document_id,)}
    )
    claims = verify_delegation(pending.delegation_token, principal, REFERENCE_TIME)
    decision = system.policy.evaluate(
        principal,
        claims,
        proposal,
        wrong,
        system.registry.get(TENANT_ACME, AGENT_ID),
        REFERENCE_TIME,
    )
    assert decision.reason_codes == ("EVIDENCE_RESOURCE_MISMATCH",)


def test_approval_is_bound_to_proposal_evidence_and_policy():
    system, principal, pending = pending_system(operation="binding")
    receipts = reviewers_for(system, pending, REFERENCE_TIME)
    mutated = receipts[0].model_copy(update={"proposal_digest": stable_digest("other")})
    with pytest.raises(PermissionError, match="NOT_LEDGERED"):
        system.approvals.consume_bundle(
            (mutated,), pending.policy, TENANT_ACME, principal.subject, REFERENCE_TIME
        )


def test_approval_expiry_and_requester_self_approval_fail():
    system, principal, pending = pending_system(operation="approval-expiry")
    requester_reviewer = principal.model_copy(
        update={"roles": frozenset({Role.PROCUREMENT_MANAGER})}
    )
    receipt = system.approvals.issue(
        requester_reviewer,
        pending.policy,
        Role.PROCUREMENT_MANAGER,
        REFERENCE_TIME,
        ttl=timedelta(seconds=1),
    )
    with pytest.raises(PermissionError, match="REQUESTER_CANNOT_APPROVE"):
        system.approvals.consume_bundle(
            (receipt,), pending.policy, TENANT_ACME, principal.subject, REFERENCE_TIME
        )
    receipt = reviewers_for(system, pending, REFERENCE_TIME)[0]
    with pytest.raises(PermissionError, match="APPROVAL_EXPIRED"):
        system.approvals.consume_bundle(
            (receipt,),
            pending.policy,
            TENANT_ACME,
            principal.subject,
            REFERENCE_TIME + timedelta(hours=1),
        )


def test_approval_bundle_consumption_is_atomic_under_concurrency():
    system, principal, pending = pending_system(operation="approval-race")
    receipts = reviewers_for(system, pending, REFERENCE_TIME)

    def consume():
        try:
            system.approvals.consume_bundle(
                receipts,
                pending.policy,
                TENANT_ACME,
                principal.subject,
                REFERENCE_TIME,
            )
            return "ok"
        except PermissionError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: consume(), range(2)))
    assert outcomes.count("ok") == 1
    assert sum("ALREADY_CONSUMED" in item for item in outcomes) == 1


def test_checkpoint_binds_proposal_and_evidence():
    system, principal, pending = pending_system(operation="checkpoint-binding")
    receipts = reviewers_for(system, pending, REFERENCE_TIME)
    changed = pending.model_copy(
        update={
            "proposal": pending.proposal.model_copy(update={"amount": Decimal(24000)})
        }
    )
    with pytest.raises(PermissionError, match="CHECKPOINT_ARTIFACT_MISMATCH"):
        system.resume(principal, changed, receipts)


def test_checkpoint_signature_and_resume_identity_are_verified():
    system, principal, pending = pending_system(operation="checkpoint-auth")
    assert pending.checkpoint is not None
    tampered = pending.checkpoint.model_copy(update={"tenant_id": TENANT_GLOBEX})
    with pytest.raises(PermissionError, match="CHECKPOINT_SIGNATURE_INVALID"):
        system.checkpoints.claim(tampered, principal, 1)
    other = build_principal(subject="other-employee")
    with pytest.raises(PermissionError, match="RESUME_NOT_AUTHORIZED"):
        system.checkpoints.claim(pending.checkpoint, other, 1)


def test_checkpoint_can_only_be_claimed_once():
    system, principal, pending = pending_system(operation="checkpoint-race")
    assert pending.checkpoint is not None

    def claim():
        try:
            system.checkpoints.claim(pending.checkpoint, principal, 1)
            return "ok"
        except RuntimeError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: claim(), range(2)))
    assert outcomes.count("ok") == 1
    assert sum("STALE_CHECKPOINT_VERSION" in item for item in outcomes) == 1


def test_failed_approval_does_not_burn_checkpoint():
    system, principal, pending = pending_system(operation="approval-recovery")
    with pytest.raises(PermissionError, match="APPROVAL_SET_INCOMPLETE"):
        system.resume(principal, pending, ())

    receipts = reviewers_for(system, pending, REFERENCE_TIME)
    completed = system.resume(principal, pending, receipts)
    assert completed.terminal_state is TerminalState.COMMITTED
    assert completed.execution is not None


def test_gateway_rechecks_agent_state_at_time_of_use():
    system, principal, pending = pending_system(operation="time-of-use")
    receipts = reviewers_for(system, pending, REFERENCE_TIME)
    system.registry.suspend(TENANT_ACME, AGENT_ID, 1)
    with pytest.raises(PermissionError, match="POLICY_OR_STATE_CHANGED_AT_RESUME"):
        system.resume(principal, pending, receipts)
    assert system.erp.orders == {}


def test_same_logical_operation_is_deduplicated():
    system = GovernedProcurementSystem()
    first = system.start(build_principal(), build_request(operation="dedup"))
    assert first.execution is not None
    replay = system.gateway.execute(first.proposal, first.policy, "", RuntimeBudget())
    assert replay.duplicate
    assert system.erp.calls == 1
    assert len(system.erp.orders) == 1


def test_logical_operation_mutation_is_rejected():
    system = GovernedProcurementSystem()
    first = system.start(build_principal(), build_request(operation="collision"))
    changed = first.proposal.model_copy(update={"amount": Decimal(9000)})
    changed_policy = first.policy.model_copy(
        update={"proposal_digest": proposal_digest(changed)}
    )
    with pytest.raises(PermissionError, match="LOGICAL_OPERATION_MUTATED"):
        system.gateway.execute(changed, changed_policy, "", RuntimeBudget())


def test_transient_before_commit_can_retry_within_budget():
    system, principal, pending = pending_system(operation="retry")
    receipts = reviewers_for(system, pending, REFERENCE_TIME)
    first = system.resume(
        principal,
        pending,
        receipts,
        failure_mode=FailureMode.TRANSIENT_BEFORE_COMMIT,
    )
    assert first.terminal_state is TerminalState.RETRYABLE
    budget = RuntimeBudget(max_retries=1)
    second = system.gateway.execute(
        first.proposal, first.policy, "durable-authorization", budget
    )
    assert second.terminal_state is TerminalState.COMMITTED
    assert budget.retries == 1
    assert system.erp.calls == 2


def test_unknown_outcome_requires_reconciliation_not_retry():
    system, principal, pending = pending_system(operation="unknown")
    receipts = reviewers_for(system, pending, REFERENCE_TIME)
    uncertain = system.resume(
        principal,
        pending,
        receipts,
        failure_mode=FailureMode.UNKNOWN_AFTER_COMMIT,
    )
    duplicate = system.gateway.execute(
        uncertain.proposal,
        uncertain.policy,
        "durable-authorization",
        RuntimeBudget(),
    )
    assert uncertain.terminal_state is TerminalState.WAITING_RECONCILIATION
    assert duplicate.duplicate
    assert system.erp.calls == 1
    assert (
        system.gateway.reconcile(uncertain.execution).terminal_state
        is TerminalState.COMMITTED
    )


def test_cancellation_and_delegation_depth_stop_before_work():
    system = GovernedProcurementSystem()
    cancelled = RuntimeBudget()
    cancelled.cancel()
    with pytest.raises(RuntimeError, match="RUN_CANCELLED"):
        system.start(
            build_principal(), build_request(operation="cancel"), budget=cancelled
        )
    with pytest.raises(RuntimeError, match="DELEGATION_DEPTH_EXHAUSTED"):
        system.start(
            build_principal(),
            build_request(operation="depth"),
            budget=RuntimeBudget(max_delegation_depth=0),
        )
    assert system.erp.orders == {}


def test_incident_containment_requires_trusted_source_and_security_role():
    system = GovernedProcurementSystem()
    controller = IncidentController(system.registry, frozenset({"siem-primary"}))
    alert = IncidentAlert(
        alert_id="alert-1",
        tenant_id=TENANT_ACME,
        agent_id=AGENT_ID,
        source="siem-primary",
        severity="CRITICAL",
        observed_at=REFERENCE_TIME,
    )
    with pytest.raises(PermissionError, match="SECURITY_OPERATOR_REQUIRED"):
        controller.contain(build_principal(), alert)
    operator = build_principal(
        subject="incident-commander", roles=frozenset({Role.SECURITY_OPERATOR})
    )
    suspended = controller.contain(operator, alert)
    assert suspended.status is AgentStatus.SUSPENDED


def test_telemetry_records_decisions_without_payload_content():
    system = GovernedProcurementSystem()
    result = system.start(
        build_principal(),
        build_request(operation="telemetry", user_text="SECRET-NOT-FOR-TELEMETRY"),
    )
    serialized = json.dumps(system.telemetry.spans())
    assert result.terminal_state is TerminalState.COMMITTED
    assert "governance.policy.evaluate" in serialized
    assert "governance.tool.execute" in serialized
    assert "SECRET-NOT-FOR-TELEMETRY" not in serialized


def test_pydantic_schema_is_validated_by_jsonschema():
    system = GovernedProcurementSystem()
    result = system.start(build_principal(), build_request(operation="schema"))
    validate_tool_contract(result.proposal)
    schema = proposal_tool_schema()
    assert schema["name"] == "create_purchase_order"
    assert schema["inputSchema"]["additionalProperties"] is False


def test_architecture_comparison_names_structural_tradeoffs():
    manager, handoff = compare_orchestration_patterns()
    assert manager.pattern == "manager-as-tools"
    assert (
        manager.privileged_capability_exposure < handoff.privileged_capability_exposure
    )
    assert manager.coordination_events > handoff.coordination_events
    assert manager.final_action_owner == "manager"


def test_evaluation_population_and_metric_semantics_are_exact():
    cases = evaluate_capstone()
    metrics = evaluation_metrics(cases)
    assert len(cases) == 15
    assert len({case.case_id for case in cases}) == 15
    assert metrics["baseline_terminal_correctness"] == {
        "numerator": 3,
        "denominator": 15,
        "value": 0.2,
    }
    assert metrics["governed_terminal_correctness"]["value"] == 1.0
    assert metrics["unsafe_commit_prevention"] == {
        "numerator": 12,
        "denominator": 12,
        "value": 1.0,
    }
    assert metrics["valid_completion_or_deduplication"] == {
        "numerator": 3,
        "denominator": 3,
        "value": 1.0,
    }


def test_assurance_case_is_signed_and_bounded():
    assurance = build_assurance_case(evaluate_capstone())
    assert assurance["decision"] == "CONDITIONAL_RELEASE"
    assert signature_valid(assurance["evidence"], assurance["signature"])
    assert assurance["evidence"]["test_population"] == 15
    assert "no live model-quality claim" in assurance["evidence"]["limitations"]
    assert not signature_valid(
        {**assurance["evidence"], "agent_version": "changed"},
        assurance["signature"],
    )


def test_reference_run_uses_real_offline_libraries():
    run = build_reference_run()
    assert set(run["versions"]) == {
        "pydantic",
        "PyJWT",
        "jsonschema",
        "opentelemetry-sdk",
    }
    assert run["committed"].terminal_state is TerminalState.COMMITTED
    assert run["assurance"]["decision"] == "CONDITIONAL_RELEASE"
    assert run["tool_schema"]["inputSchema"]["title"] == "ActionProposal"


def test_dependency_versions_are_not_placeholders():
    assert all(value and value != "unknown" for value in dependency_versions().values())


def test_notebook_is_clean_and_imports_the_canonical_lab():
    notebook = json.loads(
        (MODULE / "17_capstone_governed_autonomous_enterprise_agent.ipynb").read_text()
    )
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "%pip" not in source
    assert "from lab import" in source or "import lab" in source
    assert all(
        cell.get("outputs", []) == [] and cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )


def test_policy_and_artifact_versions_are_visible():
    run = build_reference_run()
    assert run["pending"].policy.policy_version == POLICY_VERSION
    assert run["pending"].proposal.agent_version
    assert (
        artifact_signature(run["assurance"]["evidence"])
        == run["assurance"]["signature"]
    )


def test_diagram_manifest_resolves_to_accessible_svg_sources():
    manifest = yaml.safe_load((MODULE / "diagram-spec.yaml").read_text())
    assert manifest["version"] == 2
    assert len(manifest["diagrams"]) == 4
    for diagram in manifest["diagrams"]:
        path = MODULE / diagram["file"]
        spec = yaml.safe_load((MODULE / diagram["spec"]).read_text())
        root = ET.parse(path).getroot()
        namespace = "{http://www.w3.org/2000/svg}"
        assert spec["version"] == 1
        assert spec["output"]["alt_text"]
        assert (
            (MODULE / diagram["spec"]).parent / spec["output"]["svg"]
        ).resolve() == path.resolve()
        assert root.attrib["role"] == "img"
        assert root.attrib["aria-labelledby"]
        assert root.find(f"{namespace}title") is not None
        assert root.find(f"{namespace}desc") is not None
        assert root.attrib["width"] == str(diagram["canvas"]["width"])
        assert root.attrib["height"] == str(diagram["canvas"]["height"])

        node_by_id = {node["id"]: node for node in spec["nodes"]}
        assert len(node_by_id) == len(spec["nodes"])
        assert len({edge["id"] for edge in spec["edges"]}) == len(spec["edges"])
        for node in spec["nodes"]:
            bounds = node["bounds"]
            assert (
                0
                <= bounds["x"]
                < bounds["x"] + bounds["width"]
                <= spec["canvas"]["width"]
            )
            assert (
                0
                <= bounds["y"]
                < bounds["y"] + bounds["height"]
                <= spec["canvas"]["height"]
            )
        for edge in spec["edges"]:
            for endpoint in (edge["from"], edge["to"]):
                assert endpoint["node"] in node_by_id
                assert endpoint["port"] in node_by_id[endpoint["node"]]["ports"]
            assert all(
                0 <= point[0] <= spec["canvas"]["width"]
                and 0 <= point[1] <= spec["canvas"]["height"]
                for point in edge["route"]
            )
