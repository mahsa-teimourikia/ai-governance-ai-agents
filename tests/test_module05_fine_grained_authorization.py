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
        / "curriculum/beginner/05-fine-grained-authorization-for-agents/lab.py"
    )
    spec = importlib.util.spec_from_file_location("module05_lab", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_role_only_baseline_allows_an_over_scoped_request(lab):
    proposal = lab.demo_proposal(
        amount_cents=9_999_999,
        resource_id="department:finance",
        vendor_id="vendor:unknown",
    )
    assert lab.unsafe_role_only_authorize("ProcurementManager", proposal) is True


def test_dual_authorization_allows_valid_user_task_agent_and_context(lab):
    identity, proposal, repository, _, _ = lab.build_demo_environment()
    decision = repository.preview(identity, proposal, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.ALLOW
    assert decision.reason_codes == ("all_authorization_constraints_satisfied",)
    assert decision.evidence_versions == (
        "task:grant-v3",
        "resource:resource-v7",
        "vendor:vendor-v11",
        "risk:risk-v5-1",
    )


@pytest.mark.parametrize(
    ("identity", "resource_tenant", "reason"),
    [
        (None, "tenant:other", "resource_tenant_mismatch"),
        ("wrong_actor", "tenant:oneplusi", "task_actor_mismatch"),
        ("wrong_tenant", "tenant:oneplusi", "task_tenant_mismatch"),
    ],
)
def test_identity_and_tenant_bindings_fail_closed(lab, identity, resource_tenant, reason):
    if identity == "wrong_actor":
        identity = lab.demo_identity(actor_id="agent:other")
    elif identity == "wrong_tenant":
        identity = lab.demo_identity(tenant_id="tenant:other")
    _, proposal, repository, _, _ = lab.build_demo_environment(
        identity=identity, resource_tenant=resource_tenant
    )
    actual_identity = identity or lab.demo_identity()
    decision = repository.preview(actual_identity, proposal, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert reason in decision.reason_codes


@pytest.mark.parametrize(
    ("proposal", "reason"),
    [
        (
            lambda lab: lab.demo_proposal(resource_id="department:finance"),
            "resource_not_granted_to_task",
        ),
        (
            lambda lab: lab.demo_proposal(vendor_id="vendor:other"),
            "vendor_not_granted_to_task",
        ),
        (
            lambda lab: lab.demo_proposal(country="GB"),
            "country_not_allowed_for_vendor",
        ),
        (
            lambda lab: lab.demo_proposal(amount_cents=1_000_001),
            "amount_exceeds_task_limit",
        ),
        (
            lambda lab: lab.demo_proposal().model_copy(
                update={"action": "payment:issue"}
            ),
            "action_not_granted_to_task",
        ),
    ],
)
def test_task_and_resource_dimensions_are_independently_enforced(lab, proposal, reason):
    identity, proposal, repository, _, _ = lab.build_demo_environment(
        proposal=proposal(lab)
    )
    decision = repository.preview(identity, proposal, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert reason in decision.reason_codes


def test_user_resource_relationship_is_required_even_when_task_is_valid(lab):
    identity, proposal, repository, _, _ = lab.build_demo_environment(
        authorized_users=frozenset()
    )
    decision = repository.preview(identity, proposal, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert "user_not_authorized_for_resource" in decision.reason_codes


@pytest.mark.parametrize(
    ("approved", "sanctioned", "reason"),
    [
        (False, False, "vendor_not_approved"),
        (True, True, "vendor_sanctioned"),
    ],
)
def test_authoritative_vendor_hard_denies_cannot_be_overridden(lab, approved, sanctioned, reason):
    identity, proposal, repository, _, _ = lab.build_demo_environment(
        vendor_approved=approved, vendor_sanctioned=sanctioned
    )
    approval = lab.issue_demo_approval(identity, proposal, now=lab.REFERENCE_TIME)
    decision = repository.preview(
        identity, proposal, approval=approval, now=lab.REFERENCE_TIME
    )
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert reason in decision.reason_codes


def test_current_risk_evidence_is_bound_to_the_exact_proposal(lab):
    identity, proposal, repository, _, _ = lab.build_demo_environment()
    altered = proposal.model_copy(update={"amount_cents": 450_001})
    decision = repository.preview(identity, altered, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert "risk_assessment_proposal_mismatch" in decision.reason_codes


def test_stale_identity_task_and_risk_evidence_fail_closed(lab):
    identity, proposal, repository, _, _ = lab.build_demo_environment()
    decision = repository.preview(
        identity, proposal, now=lab.REFERENCE_TIME + timedelta(minutes=21)
    )
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert {
        "identity_context_not_current",
        "task_grant_not_current",
        "risk_assessment_not_current",
    }.issubset(decision.reason_codes)


def test_amount_and_risk_escalation_requires_request_bound_approval(lab):
    proposal = lab.demo_proposal(amount_cents=600_000)
    identity, proposal, repository, pep, adapter = lab.build_demo_environment(
        proposal=proposal
    )
    escalated = repository.preview(identity, proposal, now=lab.REFERENCE_TIME)
    assert escalated.outcome is lab.DecisionOutcome.ESCALATE
    assert escalated.reason_codes == ("amount_requires_approval",)

    approval = lab.issue_demo_approval(identity, proposal, now=lab.REFERENCE_TIME)
    result = pep.execute(
        identity, proposal, approval=approval, now=lab.REFERENCE_TIME
    )
    assert result.decision.outcome is lab.DecisionOutcome.ALLOW
    assert result.effect.status is lab.EffectStatus.APPLIED
    assert adapter.applied_count == 1


def test_approval_cannot_authorize_a_mutated_request(lab):
    original = lab.demo_proposal(amount_cents=600_000)
    identity = lab.demo_identity()
    approval = lab.issue_demo_approval(identity, original, now=lab.REFERENCE_TIME)
    altered = original.model_copy(update={"amount_cents": 700_000})
    identity, altered, repository, _, _ = lab.build_demo_environment(
        identity=identity, proposal=altered
    )
    decision = repository.preview(
        identity, altered, approval=approval, now=lab.REFERENCE_TIME
    )
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert "approval_request_mismatch" in decision.reason_codes


def test_expired_and_wrong_role_approvals_are_denied(lab):
    proposal = lab.demo_proposal(amount_cents=600_000)
    identity, proposal, repository, _, _ = lab.build_demo_environment(proposal=proposal)
    approval = lab.issue_demo_approval(identity, proposal, now=lab.REFERENCE_TIME)

    wrong_role = approval.model_copy(update={"approver_role": "Employee"})
    denied = repository.preview(
        identity, proposal, approval=wrong_role, now=lab.REFERENCE_TIME
    )
    assert "approval_wrong_role" in denied.reason_codes

    expired = approval.model_copy(update={"expires_at": lab.REFERENCE_TIME})
    denied = repository.preview(
        identity, proposal, approval=expired, now=lab.REFERENCE_TIME
    )
    assert "approval_not_current" in denied.reason_codes


def test_approval_retry_is_idempotent_but_cannot_authorize_another_operation(lab):
    first_proposal = lab.demo_proposal(amount_cents=600_000)
    second_proposal = lab.demo_proposal(
        operation_id="OP-PO-002", amount_cents=600_000
    )
    identity, first_proposal, repository, pep, adapter = lab.build_demo_environment(
        proposal=first_proposal, additional_proposals=(second_proposal,)
    )
    approval = lab.issue_demo_approval(
        identity, first_proposal, now=lab.REFERENCE_TIME
    )

    first = pep.execute(
        identity, first_proposal, approval=approval, now=lab.REFERENCE_TIME
    )
    retry = pep.execute(
        identity, first_proposal, approval=approval, now=lab.REFERENCE_TIME
    )
    reuse = pep.execute(
        identity, second_proposal, approval=approval, now=lab.REFERENCE_TIME
    )

    assert first.decision.outcome is lab.DecisionOutcome.ALLOW
    assert retry.decision.replayed_decision is True
    assert reuse.decision.outcome is lab.DecisionOutcome.DENY
    assert "approval_request_mismatch" in reuse.decision.reason_codes
    assert adapter.applied_count == 1


def test_pep_does_not_invoke_effect_for_deny_or_escalate(lab):
    denied_identity, denied_proposal, _, denied_pep, denied_adapter = (
        lab.build_demo_environment(vendor_approved=False)
    )
    denied = denied_pep.execute(
        denied_identity, denied_proposal, now=lab.REFERENCE_TIME
    )
    assert denied.effect.status is lab.EffectStatus.NOT_ATTEMPTED
    assert denied_adapter.applied_count == 0

    proposal = lab.demo_proposal(amount_cents=600_000)
    identity, proposal, _, pep, adapter = lab.build_demo_environment(proposal=proposal)
    escalated = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    assert escalated.decision.outcome is lab.DecisionOutcome.ESCALATE
    assert escalated.effect.status is lab.EffectStatus.NOT_ATTEMPTED
    assert adapter.applied_count == 0


def test_idempotent_retry_returns_persisted_effect_once(lab):
    identity, proposal, _, pep, adapter = lab.build_demo_environment()
    first = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    retry = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    assert first.effect == retry.effect
    assert retry.decision.replayed_decision is True
    assert adapter.applied_count == 1


def test_operation_id_mutation_is_denied_and_audited(lab):
    identity, proposal, repository, pep, adapter = lab.build_demo_environment()
    pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    mutated = proposal.model_copy(update={"amount_cents": 400_000})
    collision = pep.execute(identity, mutated, now=lab.REFERENCE_TIME)
    assert collision.decision.outcome is lab.DecisionOutcome.DENY
    assert collision.decision.reason_codes == (
        "operation_id_reused_with_different_request",
    )
    assert collision.effect.status is lab.EffectStatus.NOT_ATTEMPTED
    assert repository.audit_events[-1].reason_codes == collision.decision.reason_codes
    assert adapter.applied_count == 1


def test_call_limit_consumption_is_atomic_under_concurrency(lab):
    proposals = tuple(
        lab.demo_proposal(operation_id=f"OP-RACE-{index}") for index in range(8)
    )
    identity, first, _, pep, adapter = lab.build_demo_environment(
        proposal=proposals[0],
        additional_proposals=proposals[1:],
        max_calls=1,
    )
    assert first == proposals[0]

    def execute(item):
        return pep.execute(identity, item, now=lab.REFERENCE_TIME)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(execute, proposals))
    assert sum(
        item.decision.outcome is lab.DecisionOutcome.ALLOW for item in results
    ) == 1
    assert sum(
        "task_call_limit_exhausted" in item.decision.reason_codes for item in results
    ) == 7
    assert adapter.applied_count == 1


def test_toctou_reauthorization_observes_authoritative_vendor_change(lab):
    identity, proposal, repository, pep, adapter = lab.build_demo_environment()
    preview = repository.preview(identity, proposal, now=lab.REFERENCE_TIME)
    assert preview.outcome is lab.DecisionOutcome.ALLOW
    repository.replace_vendor(
        lab.VendorRecord(
            vendor_id="vendor:acme",
            tenant_id="tenant:oneplusi",
            approved=False,
            sanctioned=False,
            allowed_countries=frozenset({"CA"}),
            version="vendor-v12-revoked",
        )
    )
    result = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    assert result.decision.outcome is lab.DecisionOutcome.DENY
    assert "vendor_not_approved" in result.decision.reason_codes
    assert result.decision.authorization_epoch == 2
    assert adapter.applied_count == 0


def test_closed_task_is_denied_at_final_enforcement(lab):
    identity, proposal, repository, pep, adapter = lab.build_demo_environment()
    repository.close_task(identity.task_id)
    result = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    assert result.decision.outcome is lab.DecisionOutcome.DENY
    assert "task_not_active" in result.decision.reason_codes
    assert adapter.applied_count == 0


def test_policy_outage_fails_closed_but_can_be_retried(lab):
    identity, proposal, repository, pep, adapter = lab.build_demo_environment()
    repository.set_available(False)
    unavailable = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    assert unavailable.decision.reason_codes == ("pdp_unavailable_fail_closed",)
    assert adapter.applied_count == 0

    repository.set_available(True)
    recovered = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    assert recovered.decision.outcome is lab.DecisionOutcome.ALLOW
    assert adapter.applied_count == 1


def test_uncertain_effect_is_not_retried_or_reported_as_success(lab):
    identity, proposal, _, pep, adapter = lab.build_demo_environment()
    original_apply = adapter.apply

    def lose_response(_proposal):
        raise TimeoutError("effect outcome is unknown")

    adapter.apply = lose_response
    with pytest.raises(TimeoutError, match="unknown"):
        pep.execute(identity, proposal, now=lab.REFERENCE_TIME)

    adapter.apply = original_apply
    retry = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    assert retry.decision.replayed_decision is True
    assert retry.effect.status is lab.EffectStatus.UNKNOWN
    assert adapter.applied_count == 0


def test_audit_evidence_uses_digests_versions_and_reason_codes(lab):
    identity, proposal, repository, pep, _ = lab.build_demo_environment()
    result = pep.execute(identity, proposal, now=lab.REFERENCE_TIME)
    event = repository.audit_events[0]
    assert event.decision_id == result.decision.decision_id
    assert event.request_digest == result.decision.request_digest
    assert event.resolved_input_digest == result.decision.resolved_input_digest
    assert event.policy_version == lab.POLICY_VERSION
    assert event.evidence_versions == result.decision.evidence_versions
    assert "vendor:acme" not in event.model_dump_json()


def test_openfga_sdk_requests_encode_separate_user_and_task_checks(lab):
    identity, proposal, _, _, _ = lab.build_demo_environment()
    user_check, task_check = lab.openfga_dual_check_requests(identity, proposal)
    assert user_check.user == "user:user-123"
    assert user_check.relation == "user_can_create"
    assert task_check.user == "task:TASK-PO-123"
    assert task_check.relation == "task_can_create"
    assert task_check.contextual_tuples[0].user == "agent:procurement-v1"
    assert task_check.contextual_tuples[0].relation == "calling_agent"


def test_policy_examples_are_default_deny_and_preserve_hard_forbids(lab):
    assert "forbid" in lab.CEDAR_POLICY
    assert "vendorSanctioned" in lab.CEDAR_POLICY
    assert 'default decision := {"outcome": "deny"' in lab.REGO_POLICY
    assert "input.user_authorized" in lab.REGO_POLICY
    assert "task_creator and task from calling_agent" in lab.OPENFGA_MODEL


def test_labelled_evaluation_has_explicit_safety_populations(lab):
    summary = lab.run_evaluation()
    assert summary.case_count == summary.correct_count == 10
    assert summary.baseline_correct_count == 2
    assert summary.forbidden_case_count == 7
    assert summary.baseline_forbidden_allowed_count == 7
    assert summary.forbidden_allowed_count == 0
    assert summary.legitimate_case_count == 2
    assert summary.baseline_false_denial_count == 0
    assert summary.false_denial_count == 0
    assert summary.escalation_case_count == 1
    assert summary.baseline_missed_escalation_count == 1
