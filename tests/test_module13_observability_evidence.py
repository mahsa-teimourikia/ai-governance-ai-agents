"""Focused integrity, privacy, access, retention, and integration tests for Course 13."""

import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

MODULE = (
    Path(__file__).parents[1]
    / "curriculum/advanced/13-observability-as-governance-evidence"
)
sys.path.insert(0, str(MODULE))
sys.modules.pop("lab", None)

from lab import (
    GENESIS_DIGEST,
    REFERENCE_TIME,
    Decision,
    Disposition,
    EventKind,
    EvidenceError,
    EvidenceEvent,
    EvidenceStore,
    RetentionClass,
    RiskTier,
    TraceBuilder,
    TraceEnvelope,
    assess_anomalies,
    build_collector_config,
    build_denied_near_miss_trace,
    build_high_risk_purchase_trace,
    build_openai_trace_artifacts,
    build_otel_artifacts,
    build_routine_read_trace,
    build_tool_manifests,
    choose_retention,
    compute_governance_metrics,
    deterministic_hex,
    make_traceparent,
    parse_traceparent,
    redact_text,
    sample_actor,
    sample_policy,
    sanitize_attributes,
    stable_digest,
    verify_evidence_package,
    verify_trace,
)


def assert_error(code, function, *args, **kwargs):
    with pytest.raises(EvidenceError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code


def root_builder(seed="test", **changes):
    values = {
        "policy": sample_policy(),
        "trace_seed": seed,
        "task_id": "TASK-TEST",
        "principal_ref": "subject:test",
        "agent_id": "procurement-agent:v13",
        "purpose_code": "approved_procurement",
    }
    values.update(changes)
    return TraceBuilder(**values)


def test_stable_digest_is_canonical():
    assert stable_digest({"b": {2, 1}, "a": 3}) == stable_digest({"a": 3, "b": {1, 2}})


def test_deterministic_ids_have_w3c_lengths_and_are_nonzero():
    assert len(deterministic_hex("trace", 32)) == 32
    assert len(deterministic_hex("span", 16)) == 16
    assert deterministic_hex("trace", 32) != "0" * 32


def test_traceparent_round_trip_preserves_sample_flag():
    trace_id = deterministic_hex("trace", 32)
    span_id = deterministic_hex("span", 16)
    header = make_traceparent(trace_id, span_id, sampled=True)
    assert parse_traceparent(header) == {
        "trace_id": trace_id,
        "parent_span_id": span_id,
        "sampled": True,
    }


@pytest.mark.parametrize(
    "value,code",
    [
        ("bad", "TRACEPARENT_INVALID"),
        (f"00-{'0' * 32}-{'1' * 16}-01", "TRACEPARENT_ZERO_ID"),
        (f"00-{'1' * 32}-{'0' * 16}-01", "TRACEPARENT_ZERO_ID"),
    ],
)
def test_traceparent_rejects_invalid_or_zero_ids(value, code):
    assert_error(code, parse_traceparent, value)


def test_policy_rejects_raw_content_capture():
    with pytest.raises(ValidationError):
        sample_policy(capture_raw_content=True)


def test_policy_rejects_forbidden_allowlist_key():
    with pytest.raises(ValidationError):
        sample_policy(allowed_attribute_keys=frozenset({"prompt_content"}))


def test_redaction_covers_api_keys_email_and_account_numbers():
    value = redact_text("sk-abcdefgh alice@example.com 4111 1111 1111 1111")
    assert value == "[REDACTED_API_KEY] [REDACTED_EMAIL] [REDACTED_ACCOUNT]"


def test_sanitizer_redacts_nested_values():
    safe = sanitize_attributes(sample_policy(), {"reason_codes": ["alice@example.com"]})
    assert safe == {"reason_codes": ["[REDACTED_EMAIL]"]}


def test_sanitizer_rejects_raw_and_unknown_fields():
    assert_error(
        "RAW_CONTENT_FIELD_FORBIDDEN",
        sanitize_attributes,
        sample_policy(),
        {"prompt": "secret"},
    )
    assert_error(
        "ATTRIBUTE_NOT_ALLOWLISTED",
        sanitize_attributes,
        sample_policy(),
        {"arbitrary": "value"},
    )


def test_sanitizer_rejects_unsupported_objects():
    assert_error(
        "ATTRIBUTE_TYPE_UNSUPPORTED",
        sanitize_attributes,
        sample_policy(),
        {"reason_codes": [object()]},
    )


def test_builder_requires_root_first():
    builder = root_builder()
    assert_error(
        "ROOT_EVENT_REQUIRED", builder.emit, EventKind.RETRIEVAL, risk_tier=RiskTier.LOW
    )


def test_builder_requires_known_parent_after_root():
    builder = root_builder()
    builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.LOW)
    assert_error(
        "PARENT_SPAN_UNKNOWN",
        builder.emit,
        EventKind.OUTCOME,
        risk_tier=RiskTier.LOW,
        parent_span_id="1" * 16,
        attributes={"outcome_code": "DONE"},
    )


def test_child_evidence_cannot_precede_its_parent():
    builder = root_builder()
    root = builder.emit(
        EventKind.WORKFLOW_STARTED,
        risk_tier=RiskTier.LOW,
        occurred_at=REFERENCE_TIME,
    )
    assert_error(
        "TRACE_TIME_ORDER_INVALID",
        builder.emit,
        EventKind.OUTCOME,
        risk_tier=RiskTier.LOW,
        parent_span_id=root.span_id,
        occurred_at=REFERENCE_TIME - timedelta(seconds=1),
        attributes={"outcome_code": "DONE"},
    )


def test_event_specific_evidence_is_mandatory():
    builder = root_builder()
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.LOW)
    assert_error(
        "EVENT_EVIDENCE_INCOMPLETE",
        builder.emit,
        EventKind.RETRIEVAL,
        risk_tier=RiskTier.LOW,
        parent_span_id=root.span_id,
        attributes={"source_ids": ["one"]},
    )


def test_policy_and_authorization_events_require_decisions():
    builder = root_builder()
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.HIGH)
    assert_error(
        "DECISION_REQUIRED",
        builder.emit,
        EventKind.POLICY_DECISION,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        attributes={"decision_id": "one", "reason_codes": ["HIGH"]},
    )


@pytest.mark.parametrize(
    "kind,attributes,code",
    [
        (
            EventKind.TOOL_PROPOSED,
            {"tool_id": "x", "tool_version": "1", "action_type": "x"},
            "ACTION_DIGEST_REQUIRED",
        ),
        (
            EventKind.APPROVAL,
            {"approval_id": "x", "approver_role": "manager"},
            "ACTION_DIGEST_REQUIRED",
        ),
    ],
)
def test_consequential_events_require_action_binding(kind, attributes, code):
    builder = root_builder()
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.HIGH)
    assert_error(
        code,
        builder.emit,
        kind,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        attributes=attributes,
    )


def test_approval_requires_approval_digest():
    builder = root_builder()
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.HIGH)
    assert_error(
        "APPROVAL_DIGEST_REQUIRED",
        builder.emit,
        EventKind.APPROVAL,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        action_digest=stable_digest("action"),
        attributes={"approval_id": "x", "approver_role": "manager"},
    )


def test_authorization_requires_authority_digest():
    builder = root_builder()
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.HIGH)
    assert_error(
        "AUTHORITY_DIGEST_REQUIRED",
        builder.emit,
        EventKind.AUTHORIZATION,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        decision=Decision.DENY,
        action_digest=stable_digest("action"),
        attributes={"decision_id": "x", "reason_codes": ["DENY"]},
    )


def test_effect_requires_receipt_digest():
    builder = root_builder()
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.HIGH)
    assert_error(
        "EFFECT_RECEIPT_REQUIRED",
        builder.emit,
        EventKind.EFFECT,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        action_digest=stable_digest("action"),
        attributes={
            "effect_status": "DONE",
            "effect_verified": True,
            "external_transaction_ref": "SIM-1",
            "reversible": True,
        },
    )


def test_trace_requires_terminal_evidence():
    builder = root_builder()
    builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.LOW)
    assert_error("TERMINAL_EVIDENCE_REQUIRED", builder.seal)


def test_sealed_trace_cannot_accept_more_events_or_reseal():
    builder = root_builder()
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.LOW)
    builder.emit(
        EventKind.OUTCOME,
        risk_tier=RiskTier.LOW,
        parent_span_id=root.span_id,
        attributes={"outcome_code": "DONE"},
    )
    builder.seal()
    assert_error("TRACE_ALREADY_SEALED", builder.seal)
    assert_error(
        "TRACE_ALREADY_SEALED", builder.emit, EventKind.ERROR, risk_tier=RiskTier.LOW
    )


@pytest.mark.parametrize(
    "factory,count",
    [
        (build_high_risk_purchase_trace, 8),
        (build_denied_near_miss_trace, 5),
        (build_routine_read_trace, 3),
    ],
)
def test_reference_traces_are_complete_reconstructable_and_deterministic(
    factory, count
):
    first = factory()
    second = factory()
    assert len(first.events) == count
    assert first == second
    assert verify_trace(first).model_dump() == {
        "valid": True,
        "reconstructable": True,
        "completeness_rate": 1.0,
        "reason_codes": (),
    }


def test_high_risk_trace_binds_approval_authorization_effect_and_outcome():
    trace = build_high_risk_purchase_trace()
    approval = next(event for event in trace.events if event.kind == EventKind.APPROVAL)
    authorization = next(
        event for event in trace.events if event.kind == EventKind.AUTHORIZATION
    )
    effect = next(event for event in trace.events if event.kind == EventKind.EFFECT)
    outcome = next(event for event in trace.events if event.kind == EventKind.OUTCOME)
    assert approval.action_digest == authorization.action_digest == effect.action_digest
    assert approval.approval_digest == authorization.approval_digest
    assert effect.effect_receipt_digest == outcome.effect_receipt_digest


def _effect_builder(*, approved=True, verified=True, denied=False):
    builder = root_builder(seed=f"effect-{approved}-{verified}-{denied}")
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.HIGH)
    action = stable_digest("action")
    approval = stable_digest("approval")
    builder.emit(
        EventKind.TOOL_PROPOSED,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        action_digest=action,
        attributes={"tool_id": "po.create", "tool_version": "1", "action_type": "po"},
    )
    if approved:
        builder.emit(
            EventKind.APPROVAL,
            risk_tier=RiskTier.HIGH,
            parent_span_id=root.span_id,
            action_digest=action,
            approval_digest=approval,
            attributes={"approval_id": "APR", "approver_role": "manager"},
        )
    builder.emit(
        EventKind.AUTHORIZATION,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        decision=Decision.DENY if denied else Decision.ALLOW,
        authority_digest=stable_digest("authority"),
        action_digest=action,
        approval_digest=approval if approved else None,
        attributes={"decision_id": "AUTHZ", "reason_codes": ["TEST"]},
    )
    builder.emit(
        EventKind.EFFECT,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        action_digest=action,
        effect_receipt_digest=stable_digest("receipt"),
        attributes={
            "effect_status": "DONE",
            "effect_verified": verified,
            "external_transaction_ref": "SIM",
            "reversible": True,
        },
    )
    builder.emit(
        EventKind.OUTCOME,
        risk_tier=RiskTier.HIGH,
        parent_span_id=root.span_id,
        attributes={"outcome_code": "DONE"},
    )
    return builder


def test_high_risk_effect_requires_bound_approval():
    assert_error(
        "HIGH_RISK_EFFECT_WITHOUT_BOUND_APPROVAL", _effect_builder(approved=False).seal
    )


def test_effect_must_be_verified():
    assert_error("EFFECT_NOT_VERIFIED", _effect_builder(verified=False).seal)


def test_denied_action_cannot_record_effect():
    assert_error("EFFECT_WITHOUT_ALLOW", _effect_builder(denied=True).seal)


def test_event_digest_tampering_is_rejected():
    event = build_routine_read_trace().events[0]
    changed = event.model_dump(mode="python") | {"purpose_code": "different"}
    with pytest.raises(ValidationError):
        EvidenceEvent.model_validate(changed)


def test_trace_chain_tampering_is_rejected():
    trace = build_routine_read_trace()
    events = list(trace.events)
    events[1] = events[1].model_copy(update={"previous_event_digest": "f" * 64})
    changed = trace.model_dump(mode="python") | {"events": events}
    with pytest.raises(ValidationError):
        TraceEnvelope.model_validate(changed)


def test_trace_rejects_duplicate_spans_and_sequence_gaps():
    trace = build_routine_read_trace()
    duplicate = list(trace.events)
    duplicate[1] = duplicate[1].model_copy(update={"span_id": duplicate[0].span_id})
    with pytest.raises(ValidationError):
        TraceEnvelope.model_validate(
            trace.model_dump(mode="python") | {"events": duplicate}
        )
    gap = list(trace.events)
    gap[1] = gap[1].model_copy(update={"sequence": 9})
    with pytest.raises(ValidationError):
        TraceEnvelope.model_validate(trace.model_dump(mode="python") | {"events": gap})


def test_trace_rejects_a_second_root():
    trace = build_routine_read_trace()
    events = list(trace.events)
    events[1] = events[1].model_copy(update={"parent_span_id": None})
    with pytest.raises(ValidationError):
        TraceEnvelope.model_validate(
            trace.model_dump(mode="python") | {"events": events}
        )


def test_event_envelope_binding_tampering_is_rejected():
    trace = build_routine_read_trace()
    events = list(trace.events)
    events[1] = events[1].model_copy(update={"tenant_id": "tenant-beta"})
    changed = trace.model_dump(mode="python") | {"events": events}
    with pytest.raises(ValidationError):
        TraceEnvelope.model_validate(changed)


def test_verify_trace_fails_closed_on_unvalidated_object():
    trace = build_routine_read_trace()
    values = {name: getattr(trace, name) for name in TraceEnvelope.model_fields}
    values["chain_head"] = "f" * 64
    forged = TraceEnvelope.model_construct(**values)
    result = verify_trace(forged)
    assert result.valid is False
    assert result.reason_codes == ("TRACE_INTEGRITY_INVALID",)


def test_retention_keeps_high_risk_and_denied_anomaly_traces():
    high = choose_retention(build_high_risk_purchase_trace(), routine_sample_rate=0)
    denied = choose_retention(build_denied_near_miss_trace(), routine_sample_rate=0)
    assert high.retain and high.retention_class == RetentionClass.GOVERNANCE
    assert denied.retain and denied.retention_class == RetentionClass.SECURITY


def test_routine_sampling_is_deterministic_and_bounded():
    trace = build_routine_read_trace()
    assert choose_retention(trace, routine_sample_rate=0).retain is False
    assert choose_retention(trace, routine_sample_rate=1).retain is True
    assert choose_retention(trace, routine_sample_rate=0.5) == choose_retention(
        trace, routine_sample_rate=0.5
    )
    assert_error(
        "SAMPLE_RATE_INVALID", choose_retention, trace, routine_sample_rate=1.1
    )


def test_store_requires_policy_tenant_match():
    assert_error(
        "STORE_POLICY_TENANT_MISMATCH", EvidenceStore, "tenant-beta", sample_policy()
    )


@pytest.mark.parametrize(
    "actor,code",
    [
        (sample_actor(roles=frozenset()), "ACTOR_NOT_AUTHORIZED"),
        (sample_actor(tenant_id="tenant-beta"), "ACTOR_TENANT_MISMATCH"),
        (sample_actor(valid_until=REFERENCE_TIME), "ACTOR_SESSION_NOT_CURRENT"),
    ],
)
def test_ingest_requires_current_writer_in_same_tenant(actor, code):
    store = EvidenceStore("tenant-acme", sample_policy())
    assert_error(code, store.ingest, actor, build_routine_read_trace())


def test_ingest_rejects_trace_from_other_tenant():
    other_policy = sample_policy(tenant_id="tenant-beta")
    trace = build_routine_read_trace(other_policy)
    store = EvidenceStore("tenant-acme", sample_policy())
    assert_error("TRACE_TENANT_MISMATCH", store.ingest, sample_actor(), trace)


def test_ingest_binds_evidence_schema_and_policy_versions():
    changed_policy = sample_policy(
        schema_version="governance-evidence/2.0",
        policy_version="evidence-policy/other",
    )
    trace = build_routine_read_trace(changed_policy)
    store = EvidenceStore("tenant-acme", sample_policy())
    assert_error(
        "EVIDENCE_POLICY_BINDING_MISMATCH",
        store.ingest,
        sample_actor(),
        trace,
    )


def test_ingest_binds_authenticated_workload_to_producer_and_service():
    trace = build_routine_read_trace()
    store = EvidenceStore("tenant-acme", sample_policy())
    assert_error(
        "PRODUCER_BINDING_MISMATCH",
        store.ingest,
        sample_actor(principal_id="workload:other"),
        trace,
    )
    assert_error(
        "PRODUCER_BINDING_MISMATCH",
        store.ingest,
        sample_actor(service_name="other-service"),
        trace,
    )


def test_ingest_rejects_events_signed_by_a_different_integrity_key():
    store = EvidenceStore(
        "tenant-acme", sample_policy(), integrity_key=b"different-integrity-key"
    )
    assert_error(
        "EVENT_SIGNATURE_INVALID",
        store.ingest,
        sample_actor(),
        build_routine_read_trace(),
    )


def test_ingest_is_idempotent_for_exact_trace():
    store = EvidenceStore("tenant-acme", sample_policy())
    trace = build_routine_read_trace()
    first = store.ingest(sample_actor(), trace)
    second = store.ingest(sample_actor(), trace)
    assert first == second
    assert len(store.ingest_receipts) == 1


def test_ingest_rejects_same_trace_id_with_different_valid_content():
    store = EvidenceStore("tenant-acme", sample_policy())
    original = build_routine_read_trace()
    builder = root_builder(seed="routine-read", target_version="13.0.1")
    root = builder.emit(EventKind.WORKFLOW_STARTED, risk_tier=RiskTier.LOW)
    builder.emit(
        EventKind.OUTCOME,
        risk_tier=RiskTier.LOW,
        parent_span_id=root.span_id,
        attributes={"outcome_code": "CHANGED"},
    )
    changed = builder.seal()
    assert original.trace_id == changed.trace_id
    store.ingest(sample_actor(), original)
    assert_error("TRACE_IMMUTABILITY_CONFLICT", store.ingest, sample_actor(), changed)


def test_read_requires_authorized_role_and_existing_trace():
    store = EvidenceStore("tenant-acme", sample_policy())
    trace = build_routine_read_trace()
    store.ingest(sample_actor(), trace)
    assert_error(
        "ACTOR_NOT_AUTHORIZED",
        store.get,
        sample_actor(),
        trace.trace_id,
        purpose_code="control_assurance",
    )


def test_read_requires_allowed_purpose_and_records_chained_access_receipts():
    store = EvidenceStore("tenant-acme", sample_policy())
    trace = build_routine_read_trace()
    store.ingest(sample_actor(), trace)
    auditor = sample_actor(
        roles=frozenset({"auditor"}), purposes=frozenset({"control_assurance"})
    )
    assert_error(
        "ACCESS_PURPOSE_NOT_AUTHORIZED",
        store.get,
        auditor,
        trace.trace_id,
        purpose_code="marketing",
    )
    store.get(auditor, trace.trace_id, purpose_code="control_assurance")
    store.get(
        auditor,
        trace.trace_id,
        purpose_code="control_assurance",
        now=REFERENCE_TIME + timedelta(seconds=1),
    )
    assert len(store.access_receipts) == 2
    assert store.access_receipts[0].prior_access_digest == GENESIS_DIGEST
    assert (
        store.access_receipts[1].prior_access_digest
        == store.access_receipts[0].receipt_digest
    )


def test_break_glass_requires_security_role_and_a_reason():
    store = EvidenceStore("tenant-acme", sample_policy())
    trace = build_routine_read_trace()
    store.ingest(sample_actor(), trace)
    auditor = sample_actor(roles=frozenset({"auditor"}), purposes=frozenset())
    assert_error(
        "BREAK_GLASS_INVALID",
        store.get,
        auditor,
        trace.trace_id,
        purpose_code="incident_response",
        break_glass=True,
        reason="CASE-13",
    )
    investigator = sample_actor(
        roles=frozenset({"security_investigator"}), purposes=frozenset()
    )
    assert_error(
        "BREAK_GLASS_INVALID",
        store.get,
        investigator,
        trace.trace_id,
        purpose_code="incident_response",
        break_glass=True,
        reason="",
    )
    assert (
        store.get(
            investigator,
            trace.trace_id,
            purpose_code="incident_response",
            break_glass=True,
            reason="CASE-13",
        )
        == trace
    )
    reader = sample_actor(roles=frozenset({"auditor"}))
    assert store.get(reader, trace.trace_id, purpose_code="control_assurance") == trace
    assert_error(
        "TRACE_NOT_FOUND",
        store.get,
        reader,
        "0" * 32,
        purpose_code="control_assurance",
    )


def test_export_requires_purpose_and_returns_minimized_manifest():
    store = EvidenceStore("tenant-acme", sample_policy())
    trace = build_high_risk_purchase_trace()
    store.ingest(sample_actor(), trace)
    auditor = sample_actor(
        roles=frozenset({"auditor"}), purposes=frozenset({"annual_audit"})
    )
    assert_error(
        "EXPORT_PURPOSE_REQUIRED",
        store.export_package,
        auditor,
        trace.trace_id,
        purpose_code="",
    )
    package, receipt = store.export_package(
        auditor, trace.trace_id, purpose_code="annual_audit"
    )
    serialized = package.model_dump_json()
    assert "attributes" not in serialized
    assert "kb:vendor" not in serialized
    assert package.package_digest == receipt.package_digest
    assert verify_evidence_package(package)


def test_package_signature_detects_digest_or_content_tampering():
    store = EvidenceStore("tenant-acme", sample_policy())
    trace = build_high_risk_purchase_trace()
    store.ingest(sample_actor(), trace)
    auditor = sample_actor(
        roles=frozenset({"auditor"}), purposes=frozenset({"annual_audit"})
    )
    package, _ = store.export_package(
        auditor, trace.trace_id, purpose_code="annual_audit"
    )
    assert verify_evidence_package(package)
    assert not verify_evidence_package(
        package.model_copy(update={"package_digest": "f" * 64})
    )
    assert not verify_evidence_package(
        package.model_copy(update={"purpose_code": "different"})
    )


def test_custody_receipts_form_an_append_only_chain():
    store = EvidenceStore("tenant-acme", sample_policy())
    trace = build_high_risk_purchase_trace()
    store.ingest(sample_actor(), trace)
    auditor = sample_actor(
        roles=frozenset({"auditor"}), purposes=frozenset({"audit-one", "audit-two"})
    )
    _, first = store.export_package(auditor, trace.trace_id, purpose_code="audit-one")
    _, second = store.export_package(
        auditor,
        trace.trace_id,
        purpose_code="audit-two",
        now=REFERENCE_TIME + timedelta(minutes=4),
    )
    assert first.prior_custody_digest == GENESIS_DIGEST
    assert second.prior_custody_digest == first.receipt_digest


def test_legal_hold_requires_custodian_and_overrides_disposition():
    store = EvidenceStore("tenant-acme", sample_policy())
    trace = build_routine_read_trace()
    store.ingest(sample_actor(), trace)
    auditor = sample_actor(roles=frozenset({"auditor"}))
    assert_error(
        "ACTOR_NOT_AUTHORIZED", store.place_legal_hold, auditor, trace.trace_id
    )
    custodian = sample_actor(roles=frozenset({"evidence_custodian"}))
    store.place_legal_hold(custodian, trace.trace_id)
    plan = store.plan_disposition(
        custodian, trace.trace_id, now=REFERENCE_TIME + timedelta(days=100)
    )
    assert plan.disposition == Disposition.RETAIN
    assert plan.reason_codes == ("LEGAL_HOLD",)


def test_disposition_only_marks_expired_evidence_for_review():
    store = EvidenceStore("tenant-acme", sample_policy(routine_retention_days=14))
    trace = build_routine_read_trace()
    store.ingest(sample_actor(), trace)
    custodian = sample_actor(roles=frozenset({"evidence_custodian"}))
    before = store.plan_disposition(
        custodian, trace.trace_id, now=trace.sealed_at + timedelta(days=13)
    )
    after = store.plan_disposition(
        custodian, trace.trace_id, now=trace.sealed_at + timedelta(days=15)
    )
    assert before.disposition == Disposition.RETAIN
    assert after.disposition == Disposition.ELIGIBLE_FOR_REVIEW


def test_metrics_name_exact_populations_and_denominators():
    metrics = compute_governance_metrics(
        [
            build_high_risk_purchase_trace(),
            build_denied_near_miss_trace(),
            build_routine_read_trace(),
        ]
    )
    assert metrics.trace_population == metrics.reconstructable_traces == 3
    assert metrics.high_risk_population == metrics.verified_high_risk_outcomes == 2
    assert metrics.decision_population == 2
    assert (metrics.allowed, metrics.denied, metrics.escalated) == (1, 1, 0)
    assert metrics.near_miss_population == 1
    assert (
        metrics.reconstructability_rate
        == metrics.verified_high_risk_outcome_rate
        == 1.0
    )
    assert_error("EMPTY_METRIC_POPULATION", compute_governance_metrics, [])


def test_anomaly_assessment_is_a_signal_not_a_violation():
    assessment = assess_anomalies(build_denied_near_miss_trace())
    assert assessment.signal_only is True
    assert assessment.score == 0.25
    assert assessment.reason_codes == ("NEW_TOOL",)


def test_tool_manifests_cover_common_portable_and_managed_options():
    manifests = build_tool_manifests()
    assert set(manifests) == {
        "opentelemetry",
        "openinference_phoenix",
        "langsmith",
        "langfuse",
        "openai_agents",
    }
    assert manifests["opentelemetry"].installed_version is not None
    assert all(item.governance_boundary for item in manifests.values())


def test_real_opentelemetry_spans_are_created_only_in_memory():
    evidence = build_high_risk_purchase_trace()
    artifacts = build_otel_artifacts(evidence)
    spans = artifacts["spans"]
    assert len(spans) == len(evidence.events)
    by_evidence_span_id = {
        span.attributes["governance.evidence.span_id"]: span for span in spans
    }
    assert len({span.context.trace_id for span in spans}) == 1
    for event in evidence.events:
        span = by_evidence_span_id[event.span_id]
        assert span.attributes["governance.trace.digest"] == evidence.trace_digest
        if event.parent_span_id is None:
            assert span.parent is None
        else:
            expected_parent = by_evidence_span_id[event.parent_span_id]
            assert span.parent.span_id == expected_parent.context.span_id
    serialized = json_like(spans)
    assert "approved laptop" not in serialized
    assert "alice@example.com" not in serialized


def json_like(value):
    return repr(value)


def test_openai_agents_objects_disable_sensitive_trace_capture():
    trace = build_high_risk_purchase_trace()
    artifacts = build_openai_trace_artifacts(trace)
    config = artifacts["run_config"]
    assert config.trace_include_sensitive_data is False
    assert config.trace_id == f"trace_{trace.trace_id}"
    assert artifacts["trace"].trace_id == config.trace_id
    assert artifacts["span"].trace_id == config.trace_id


def test_collector_manifest_is_local_ingress_minimized_and_tls_exported():
    config = build_collector_config()
    protocols = config["receivers"]["otlp"]["protocols"]
    assert all(item["endpoint"].startswith("127.0.0.1:") for item in protocols.values())
    actions = config["processors"]["attributes/governance"]["actions"]
    assert {item["key"] for item in actions} == {
        "gen_ai.input.messages",
        "gen_ai.output.messages",
    }
    exporter = config["exporters"]["otlp/evidence"]
    assert exporter["tls"]["insecure"] is False
    assert exporter["sending_queue"]["enabled"] is True
    processors = config["service"]["pipelines"]["traces/governance"]["processors"]
    assert (
        processors.index("attributes/governance")
        < processors.index("tail_sampling/governance")
        < processors.index("batch")
    )


def test_reference_reports_never_store_raw_prompt_or_tool_content():
    serialized = "".join(
        trace.model_dump_json()
        for trace in [
            build_high_risk_purchase_trace(),
            build_denied_near_miss_trace(),
            build_routine_read_trace(),
        ]
    )
    for forbidden in ("prompt", "password", "api_key", "raw_input", "raw_output"):
        assert forbidden not in serialized.lower()
