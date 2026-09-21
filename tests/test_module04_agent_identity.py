from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys

import jwt
import pytest


TEST_NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def lab():
    path = Path(__file__).parents[1] / "curriculum/beginner/04-agent-identity-and-delegated-authority/lab.py"
    spec = importlib.util.spec_from_file_location("module04_lab", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_trusted_context_requires_registered_agent_workload_binding(lab):
    directory = lab.demo_directory()
    context = lab.demo_context()
    assert context.actor_id == "agent:procurement"
    with pytest.raises(ValueError, match="agent_workload_binding_not_found"):
        directory.binding("agent:procurement", "spiffe://example.com/prod/vendor-research")
    with pytest.raises(ValueError, match="binding actor must be a logical agent"):
        lab.IdentityDirectory(
            principals=directory.principals,
            bindings=(
                lab.AgentWorkloadBinding(
                    actor_id="human:user-123",
                    workload_id="spiffe://example.com/prod/procurement",
                    required_selectors=frozenset({"k8s:sa:procurement"}),
                ),
            ),
        )


def test_trusted_context_rejects_cross_tenant_and_untrusted_workload(lab):
    directory = lab.demo_directory()
    now = lab.REFERENCE_TIME
    session = lab.AuthenticatedHumanSession(
        subject_id="human:user-123",
        tenant_id="tenant:other",
        session_id="SESSION-X",
        authenticated_at=now,
        expires_at=now + timedelta(minutes=30),
        authentication_methods=frozenset({"webauthn"}),
    )
    evidence = lab.WorkloadAttestation(
        workload_id="spiffe://example.com/prod/procurement",
        trust_domain=lab.TRUST_DOMAIN,
        selectors=frozenset({"k8s:ns:agents", "k8s:sa:procurement"}),
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="cross_tenant_identity_chain"):
        lab.bind_trusted_context(session, "agent:procurement", evidence, "TASK-X", directory, now=now)

    valid_session = session.model_copy(update={"tenant_id": "tenant:oneplusi"})
    untrusted = evidence.model_copy(update={"trust_domain": "attacker.example"})
    with pytest.raises(ValueError, match="untrusted_workload_domain"):
        lab.bind_trusted_context(valid_session, "agent:procurement", untrusted, "TASK-X", directory, now=now)


def test_workload_attestation_requires_current_registered_selectors(lab):
    directory = lab.demo_directory()
    now = lab.REFERENCE_TIME
    session = lab.AuthenticatedHumanSession(
        subject_id="human:user-123",
        tenant_id="tenant:oneplusi",
        session_id="SESSION-X",
        authenticated_at=now,
        expires_at=now + timedelta(minutes=30),
        authentication_methods=frozenset({"webauthn"}),
    )
    missing_selector = lab.WorkloadAttestation(
        workload_id="spiffe://example.com/prod/procurement",
        trust_domain=lab.TRUST_DOMAIN,
        selectors=frozenset({"k8s:ns:agents"}),
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="selectors"):
        lab.bind_trusted_context(session, "agent:procurement", missing_selector, "TASK-X", directory, now=now)

    expired = missing_selector.model_copy(
        update={
            "selectors": frozenset({"k8s:ns:agents", "k8s:sa:procurement"}),
            "expires_at": now,
        }
    )
    with pytest.raises(ValueError, match="not_current"):
        lab.bind_trusted_context(session, "agent:procurement", expired, "TASK-X", directory, now=now)


def test_human_session_and_bound_identity_context_must_remain_current(lab):
    directory = lab.demo_directory()
    now = lab.REFERENCE_TIME
    session = lab.AuthenticatedHumanSession(
        subject_id="human:user-123",
        tenant_id="tenant:oneplusi",
        session_id="SESSION-EXPIRED",
        authenticated_at=now - timedelta(hours=1),
        expires_at=now,
        authentication_methods=frozenset({"webauthn"}),
    )
    workload = lab.WorkloadAttestation(
        workload_id="spiffe://example.com/prod/procurement",
        trust_domain=lab.TRUST_DOMAIN,
        selectors=frozenset({"k8s:ns:agents", "k8s:sa:procurement"}),
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=10),
    )
    with pytest.raises(ValueError, match="human_session_not_current"):
        lab.bind_trusted_context(
            session, "agent:procurement", workload, "TASK-X", directory, now=now
        )

    context, _, token, ledger = lab.build_demo_authority()
    after_context_expiry = context.valid_until
    decision = lab.authorize_token(
        ledger,
        token,
        lab.demo_request(),
        context,
        now=after_context_expiry,
    )
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert "trusted_context_not_current" in decision.reason_codes


def test_root_grant_cannot_exceed_approved_intent(lab):
    context = lab.demo_context()
    intent = lab.demo_intent()
    with pytest.raises(ValueError, match="actions_exceed_intent"):
        lab.build_root_grant(
            context,
            intent,
            grant_id="GRANT-BAD-ACTION",
            audience="https://api.example.com/procurement",
            actions={"payment:issue"},
            resources=intent.approved_resources,
            constraints=intent.constraints,
            expires_at=lab.REFERENCE_TIME + timedelta(minutes=10),
        )
    with pytest.raises(ValueError, match="amount_exceeds_intent"):
        lab.build_root_grant(
            context,
            intent,
            grant_id="GRANT-BAD-AMOUNT",
            audience="https://api.example.com/procurement",
            actions=intent.approved_actions,
            resources=intent.approved_resources,
            constraints=intent.constraints.model_copy(update={"max_amount_cents": 500_001}),
            expires_at=lab.REFERENCE_TIME + timedelta(minutes=10),
        )
    future_intent = intent.model_copy(update={"approved_at": context.bound_at + timedelta(seconds=1)})
    with pytest.raises(ValueError, match="future_dated"):
        lab.build_root_grant(
            context,
            future_intent,
            grant_id="GRANT-FUTURE-INTENT",
            audience="https://api.example.com/procurement",
            actions=intent.approved_actions,
            resources=intent.approved_resources,
            constraints=intent.constraints,
            expires_at=lab.REFERENCE_TIME + timedelta(minutes=10),
        )


def test_token_verification_pins_header_signature_issuer_audience_and_time(lab):
    _, grant, token, _ = lab.build_demo_authority()
    verified = lab.verify_training_token(token, audience=grant.audience, now=lab.REFERENCE_TIME)
    assert verified == grant
    with pytest.raises(ValueError, match="AudienceError"):
        lab.verify_training_token(token, audience="https://api.example.com/vendors", now=lab.REFERENCE_TIME)
    with pytest.raises(ValueError, match="token_expired"):
        lab.verify_training_token(token, audience=grant.audience, now=grant.expires_at)
    with pytest.raises(ValueError, match="token_not_yet_valid"):
        lab.verify_training_token(token, audience=grant.audience, now=grant.issued_at - timedelta(seconds=1))


def test_tampered_and_algorithm_confusion_tokens_fail_closed(lab):
    context, _, token, ledger = lab.build_demo_authority()
    request = lab.demo_request()
    head, payload, signature = token.split(".")
    tampered = f"{head}.{payload[:-1]}{'A' if payload[-1] != 'A' else 'B'}.{signature}"
    decision = lab.authorize_token(ledger, tampered, request, context, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.DENY

    unsigned = jwt.encode({"sub": "human:user-123"}, key="", algorithm="none")
    decision = lab.authorize_token(
        ledger,
        unsigned,
        request.model_copy(update={"operation_id": "OP-NONE-001"}),
        context,
        now=lab.REFERENCE_TIME,
    )
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert "unexpected_token_header" in decision.reason_codes
    assert len(ledger.audit_events) == 2
    assert all(event.grant_id is None for event in ledger.audit_events)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"action": "payment:issue"}, "action_not_delegated"),
        ({"resource": "department:finance"}, "resource_not_delegated"),
        ({"amount_cents": 500_001}, "amount_exceeds_delegation"),
        ({"vendor_id": None}, "vendor_required"),
        ({"vendor_id": "vendor-unknown"}, "vendor_not_delegated"),
    ],
)
def test_pep_checks_every_request_dimension(lab, changes, reason):
    context, _, token, ledger = lab.build_demo_authority()
    changes["operation_id"] = f"OP-{reason.upper().replace('_', '-') }"
    request = lab.demo_request().model_copy(update=changes)
    decision = lab.authorize_token(ledger, token, request, context, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert reason in decision.reason_codes


def test_pep_binds_subject_actor_version_workload_tenant_and_task_from_trusted_context(lab):
    context, _, token, ledger = lab.build_demo_authority()
    altered = context.model_copy(update={"actor_version": "2.0.0", "task_id": "TASK-OTHER"})
    decision = lab.authorize_token(ledger, token, lab.demo_request(), altered, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert {"actor_version_mismatch", "task_mismatch"}.issubset(decision.reason_codes)


def test_identical_operation_retry_is_idempotent_but_mutated_reuse_is_denied(lab):
    context, _, token, ledger = lab.build_demo_authority()
    request = lab.demo_request()
    first = lab.authorize_token(ledger, token, request, context, now=lab.REFERENCE_TIME)
    retry = lab.authorize_token(ledger, token, request, context, now=lab.REFERENCE_TIME)
    altered = request.model_copy(update={"amount_cents": 100_000})
    collision = lab.authorize_token(ledger, token, altered, context, now=lab.REFERENCE_TIME)
    assert first.outcome is lab.DecisionOutcome.ALLOW
    assert retry.outcome is lab.DecisionOutcome.ALLOW
    assert retry.replayed_decision is True
    assert retry.decision_id == first.decision_id
    assert collision.outcome is lab.DecisionOutcome.DENY
    assert collision.reason_codes == ("operation_id_reused_with_different_request",)
    assert ledger.audit_events[-1].reason_codes == collision.reason_codes


def test_operation_retry_is_bound_to_the_original_grant(lab):
    context, grant, token, ledger = lab.build_demo_authority()
    replacement = grant.model_copy(update={"grant_id": "GRANT-ROOT-002"})
    replacement_token = lab.issue_training_token(replacement)
    ledger.register(replacement)
    request = lab.demo_request()

    first = lab.authorize_token(ledger, token, request, context, now=lab.REFERENCE_TIME)
    replay_under_another_grant = lab.authorize_token(
        ledger, replacement_token, request, context, now=lab.REFERENCE_TIME
    )

    assert first.outcome is lab.DecisionOutcome.ALLOW
    assert replay_under_another_grant.outcome is lab.DecisionOutcome.DENY
    assert replay_under_another_grant.reason_codes == (
        "operation_id_reused_with_different_request",
    )


def test_call_limit_consumption_is_atomic_under_concurrency(lab):
    context, _, token, ledger = lab.build_demo_authority()

    def attempt(index):
        request = lab.demo_request(operation_id=f"OP-CONCURRENT-{index}")
        return lab.authorize_token(ledger, token, request, context, now=lab.REFERENCE_TIME)

    with ThreadPoolExecutor(max_workers=8) as pool:
        decisions = list(pool.map(attempt, range(8)))
    assert sum(item.outcome is lab.DecisionOutcome.ALLOW for item in decisions) == 1
    assert sum("call_limit_exhausted" in item.reason_codes for item in decisions) == 7


def test_revocation_and_task_closure_fail_closed(lab):
    context, grant, token, ledger = lab.build_demo_authority()
    ledger.revoke(grant.grant_id)
    revoked = lab.authorize_token(ledger, token, lab.demo_request(), context, now=lab.REFERENCE_TIME)
    assert revoked.outcome is lab.DecisionOutcome.DENY
    assert "grant_or_ancestor_revoked" in revoked.reason_codes

    context, grant, token, ledger = lab.build_demo_authority()
    ledger.close_task(grant.task_id)
    closed = lab.authorize_token(ledger, token, lab.demo_request(), context, now=lab.REFERENCE_TIME)
    assert closed.outcome is lab.DecisionOutcome.DENY
    assert "task_closed" in closed.reason_codes


def test_child_delegation_attenuates_all_authority_dimensions(lab):
    _, parent, token, ledger = lab.build_demo_authority()
    child_context = lab.demo_context(research_agent=True)
    constraints = lab.DelegationConstraints(
        max_amount_cents=0,
        allowed_vendor_ids=frozenset({"vendor-acme"}),
        max_calls=1,
    )
    child, child_token = lab.attenuate_grant(
        token,
        child_context,
        ledger,
        parent_audience=parent.audience,
        grant_id="GRANT-CHILD-001",
        audience="https://api.example.com/vendors",
        actions={"vendor:read"},
        resources={"department:data-ai"},
        constraints=constraints,
        expires_at=lab.REFERENCE_TIME + timedelta(minutes=5),
        now=lab.REFERENCE_TIME,
    )
    assert child.parent_grant_id == parent.grant_id
    assert child.depth == 1
    assert lab.verify_training_token(
        child_token, audience="https://api.example.com/vendors", now=lab.REFERENCE_TIME
    ) == child


def test_child_delegation_requires_a_current_trusted_context(lab):
    _, parent, token, ledger = lab.build_demo_authority()
    context = lab.demo_context(research_agent=True)
    with pytest.raises(ValueError, match="child_context_not_current"):
        lab.attenuate_grant(
            token,
            context,
            ledger,
            parent_audience=parent.audience,
            grant_id="GRANT-CHILD-STALE",
            audience="https://api.example.com/vendors",
            actions={"vendor:read"},
            resources={"department:data-ai"},
            constraints=lab.DelegationConstraints(
                max_amount_cents=0,
                allowed_vendor_ids=frozenset({"vendor-acme"}),
                max_calls=1,
            ),
            expires_at=lab.REFERENCE_TIME + timedelta(minutes=5),
            now=context.valid_until,
        )


def test_multiple_children_cannot_amplify_parent_call_budget(lab):
    _, parent, token, ledger = lab.build_demo_authority()
    context = lab.demo_context(research_agent=True)
    constraints = lab.DelegationConstraints(
        max_amount_cents=0,
        allowed_vendor_ids=frozenset({"vendor-acme"}),
        max_calls=1,
    )
    lab.attenuate_grant(
        token,
        context,
        ledger,
        parent_audience=parent.audience,
        grant_id="GRANT-CHILD-FIRST",
        audience="https://api.example.com/vendors",
        actions={"vendor:read"},
        resources={"department:data-ai"},
        constraints=constraints,
        expires_at=lab.REFERENCE_TIME + timedelta(minutes=5),
        now=lab.REFERENCE_TIME,
    )
    with pytest.raises(ValueError, match="child_calls_exceed_parent_remaining_budget"):
        lab.attenuate_grant(
            token,
            context,
            ledger,
            parent_audience=parent.audience,
            grant_id="GRANT-CHILD-SECOND",
            audience="https://api.example.com/vendors",
            actions={"vendor:read"},
            resources={"department:data-ai"},
            constraints=constraints,
            expires_at=lab.REFERENCE_TIME + timedelta(minutes=5),
            now=lab.REFERENCE_TIME,
        )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"actions": {"payment:issue"}}, "child_actions_exceed_parent"),
        ({"resources": {"department:finance"}}, "child_resources_exceed_parent"),
        ({"max_amount_cents": 500_001}, "child_amount_exceeds_parent"),
        ({"allowed_vendor_ids": frozenset({"vendor-unknown"})}, "child_vendors_exceed_parent"),
        ({"audience": "https://api.example.com/payments"}, "child_audience_not_allowed"),
        ({"expires_at": TEST_NOW + timedelta(minutes=31)}, "child_expiry_exceeds_parent"),
    ],
)
def test_child_delegation_rejects_privilege_amplification(lab, changes, reason):
    _, parent, token, ledger = lab.build_demo_authority()
    context = lab.demo_context(research_agent=True)
    params = {
        "parent_audience": parent.audience,
        "grant_id": "GRANT-CHILD-BAD",
        "audience": "https://api.example.com/vendors",
        "actions": {"vendor:read"},
        "resources": {"department:data-ai"},
        "constraints": lab.DelegationConstraints(
            max_amount_cents=0,
            allowed_vendor_ids=frozenset({"vendor-acme"}),
            max_calls=1,
        ),
        "expires_at": lab.REFERENCE_TIME + timedelta(minutes=5),
        "now": lab.REFERENCE_TIME,
    }
    constraint_fields = {"max_amount_cents", "allowed_vendor_ids", "max_calls"}
    if constraint_fields.intersection(changes):
        params["constraints"] = params["constraints"].model_copy(update=changes)
    else:
        params.update(changes)
    with pytest.raises(ValueError, match=reason):
        lab.attenuate_grant(token, context, ledger, **params)


def test_revoked_parent_invalidates_child_and_prevents_new_delegation(lab):
    _, parent, token, ledger = lab.build_demo_authority()
    context = lab.demo_context(research_agent=True)
    constraints = lab.DelegationConstraints(
        max_amount_cents=0,
        allowed_vendor_ids=frozenset({"vendor-acme"}),
        max_calls=1,
    )
    child, child_token = lab.attenuate_grant(
        token,
        context,
        ledger,
        parent_audience=parent.audience,
        grant_id="GRANT-CHILD-001",
        audience="https://api.example.com/vendors",
        actions={"vendor:read"},
        resources={"department:data-ai"},
        constraints=constraints,
        expires_at=lab.REFERENCE_TIME + timedelta(minutes=5),
        now=lab.REFERENCE_TIME,
    )
    ledger.revoke(parent.grant_id)
    request = lab.AuthorizationRequest(
        operation_id="OP-CHILD-READ",
        audience="https://api.example.com/vendors",
        action="vendor:read",
        resource="department:data-ai",
        amount_cents=0,
        vendor_id="vendor-acme",
    )
    decision = lab.authorize_token(ledger, child_token, request, context, now=lab.REFERENCE_TIME)
    assert decision.outcome is lab.DecisionOutcome.DENY
    assert "grant_or_ancestor_revoked" in decision.reason_codes
    with pytest.raises(ValueError, match="grant_or_ancestor_revoked"):
        lab.attenuate_grant(
            token,
            context,
            ledger,
            parent_audience=parent.audience,
            grant_id="GRANT-CHILD-002",
            audience="https://api.example.com/vendors",
            actions={"vendor:read"},
            resources={"department:data-ai"},
            constraints=constraints,
            expires_at=lab.REFERENCE_TIME + timedelta(minutes=5),
            now=lab.REFERENCE_TIME,
        )


def test_audit_evidence_contains_digests_not_raw_token(lab):
    context, grant, token, ledger = lab.build_demo_authority()
    lab.authorize_token(ledger, token, lab.demo_request(), context, now=lab.REFERENCE_TIME)
    events = ledger.audit_events
    assert len(events) == 1
    payload = events[0].model_dump_json()
    assert token not in payload
    assert len(events[0].token_digest) == 64
    assert events[0].policy_version == lab.POLICY_VERSION
    assert events[0].actor_version == context.actor_version
    assert events[0].audience == grant.audience
    assert events[0].action == "purchase_order:create"
    assert events[0].resource == "department:data-ai"
    assert events[0].intent_digest == grant.intent_digest
    assert events[0].constraints_digest == lab.stable_digest(grant.constraints)
    assert events[0].grant_expires_at == grant.expires_at


def test_rfc8693_example_is_request_shape_not_claimed_live_implementation(lab):
    request = lab.token_exchange_request(
        subject_token="<user-token>",
        actor_token="<workload-token>",
        audience="procurement-api",
        scope="purchase_order:create",
    )
    assert request["grant_type"] == "urn:ietf:params:oauth:grant-type:token-exchange"
    assert "access_token" not in request


def test_labelled_evaluation_exposes_population_and_safety_errors(lab):
    summary = lab.run_evaluation()
    assert summary.case_count == 7
    assert summary.correct_count == 7
    assert summary.accuracy == 1
    assert summary.forbidden_case_count == 5
    assert summary.forbidden_allowed_count == 0
    assert summary.false_denial_count == 0
