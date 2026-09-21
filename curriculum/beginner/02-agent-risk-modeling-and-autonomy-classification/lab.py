"""Evidence-aware agent risk modeling for Course 2.

This teaching module keeps risk dimensions visible. It uses deterministic,
organization-specific decision rules instead of presenting weighted decimals or
control-effectiveness percentages as objective measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum, IntEnum
from typing import Iterable

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AutonomyLevel(IntEnum):
    INFORMATIONAL = 0
    ASSISTED = 1
    BOUNDED = 2
    HIGH = 3


class OrdinalLevel(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    SEVERE = 4


class RiskTier(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class ScenarioKind(str, Enum):
    OPERATIONAL = "operational_failure"
    ADVERSARIAL = "adversarial_misuse"


class EvidenceStatus(IntEnum):
    UNKNOWN = 0
    ASSUMED = 1
    DOCUMENTED = 2
    TESTED = 3
    OBSERVED = 4


class ControlType(str, Enum):
    PREVENT = "prevent"
    DETECT = "detect"
    RECOVER = "recover"


class AutonomySignals(FrozenModel):
    produces_recommendations: bool = True
    prepares_state_change: bool = False
    executes_state_change: bool = False
    every_state_change_preapproved: bool = True
    selects_tools_or_plans_steps: bool = False
    can_delegate: bool = False
    determines_completion: bool = False


class AutonomyClassification(FrozenModel):
    level: AutonomyLevel
    reasons: tuple[str, ...]
    review_triggers: tuple[str, ...]


def classify_autonomy(signals: AutonomySignals) -> AutonomyClassification:
    reasons: list[str] = []
    triggers: list[str] = []
    if not signals.executes_state_change and not signals.prepares_state_change:
        level = AutonomyLevel.INFORMATIONAL
        reasons.append("The system recommends; another principal performs any state change.")
    elif not signals.executes_state_change:
        level = AutonomyLevel.ASSISTED
        reasons.append("The system prepares or plans actions, but a trusted actor executes them.")
    elif signals.every_state_change_preapproved and not signals.can_delegate:
        level = AutonomyLevel.BOUNDED
        reasons.append("The system executes within predefined, preapproved action boundaries.")
    else:
        level = AutonomyLevel.HIGH
        reasons.append("The system can select or execute consequential actions without per-action approval.")

    if signals.selects_tools_or_plans_steps:
        triggers.append("planner_or_tool_selection_changed")
    if signals.can_delegate:
        triggers.append("delegation_enabled")
    if signals.determines_completion:
        triggers.append("application_stop_condition_required")
    return AutonomyClassification(level=level, reasons=tuple(reasons), review_triggers=tuple(triggers))


class Capability(FrozenModel):
    capability_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    mutates_state: bool
    external_communication: bool = False
    privileged_access: bool = False
    financial_limit_usd: int = Field(default=0, ge=0)
    reversible: bool
    autonomy: AutonomyLevel


class RiskDimensions(FrozenModel):
    severity: OrdinalLevel
    likelihood: OrdinalLevel
    detectability_difficulty: OrdinalLevel
    irreversibility: OrdinalLevel
    scope: OrdinalLevel


class RiskScenario(FrozenModel):
    scenario_id: str = Field(pattern=r"^[A-Z]+-[0-9]{3}$")
    title: str = Field(min_length=1)
    kind: ScenarioKind
    capability_id: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    dimensions: RiskDimensions
    evidence_status: EvidenceStatus
    evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    owner: str = Field(min_length=1)

    @model_validator(mode="after")
    def evidence_requires_reference(self) -> "RiskScenario":
        if self.evidence_status >= EvidenceStatus.DOCUMENTED and not self.evidence_refs:
            raise ValueError("documented/tested/observed scenarios require evidence_refs")
        return self


class ControlEvidence(FrozenModel):
    evidence_id: str = Field(min_length=1)
    control_id: str = Field(min_length=1)
    scenario_ids: frozenset[str]
    control_type: ControlType
    status: EvidenceStatus
    evidence_ref: str | None = None
    valid_through: date | None = None

    @model_validator(mode="after")
    def verified_evidence_has_reference(self) -> "ControlEvidence":
        if self.status >= EvidenceStatus.TESTED and not self.evidence_ref:
            raise ValueError("tested/observed controls require an evidence reference")
        if self.status >= EvidenceStatus.TESTED and self.valid_through is None:
            raise ValueError("tested/observed controls require a validity date")
        return self


class MitigationClaim(FrozenModel):
    scenario_id: str
    control_id: str
    dimension: str
    from_level: OrdinalLevel
    to_level: OrdinalLevel

    @model_validator(mode="after")
    def reduction_only(self) -> "MitigationClaim":
        allowed = {"likelihood", "detectability_difficulty", "irreversibility", "scope"}
        if self.dimension not in allowed:
            raise ValueError(f"dimension must be one of {sorted(allowed)}")
        if self.to_level >= self.from_level:
            raise ValueError("a mitigation claim must reduce an ordinal level")
        return self


class Assessment(FrozenModel):
    scenario_id: str
    inherent_dimensions: RiskDimensions
    inherent_tier: RiskTier
    residual_dimensions: RiskDimensions
    residual_tier: RiskTier
    disposition: str
    applied_claims: tuple[str, ...]
    rejected_claims: tuple[str, ...]
    required_controls: tuple[str, ...]


CONTROL_PROFILES: dict[RiskTier, tuple[str, ...]] = {
    RiskTier.LOW: ("owner", "basic_telemetry", "periodic_review"),
    RiskTier.MODERATE: ("tool_allowlist", "schema_validation", "human_review_for_writes", "traceability"),
    RiskTier.HIGH: ("strong_identity", "least_privilege", "runtime_authorization", "containment_mode", "continuous_evaluation"),
    RiskTier.CRITICAL: ("reduce_autonomy", "task_scoped_credentials", "multi_party_approval", "isolated_execution", "continuous_red_team", "kill_switch"),
}


def required_controls(tier: RiskTier) -> tuple[str, ...]:
    """Return cumulative minimum controls through the selected tier."""

    ordered: list[str] = []
    for profile_tier in RiskTier:
        if profile_tier > tier:
            break
        for control in CONTROL_PROFILES[profile_tier]:
            if control not in ordered:
                ordered.append(control)
    return tuple(ordered)


def classify_risk(dimensions: RiskDimensions, autonomy: AutonomyLevel) -> tuple[RiskTier, tuple[str, ...]]:
    """Apply an explicit teaching policy; do not interpret this as universal math."""

    reasons: list[str] = []
    if dimensions.severity is OrdinalLevel.SEVERE and (
        dimensions.irreversibility is OrdinalLevel.SEVERE or dimensions.scope is OrdinalLevel.SEVERE
    ):
        reasons.append("Severe impact combined with severe irreversibility or scope.")
        return RiskTier.CRITICAL, tuple(reasons)
    if dimensions.severity is OrdinalLevel.SEVERE:
        reasons.append("Severe consequence requires specialist review even when likelihood is lower.")
        return RiskTier.HIGH, tuple(reasons)
    if dimensions.severity >= OrdinalLevel.HIGH and dimensions.likelihood >= OrdinalLevel.MODERATE:
        reasons.append("High consequence is at least plausible.")
        return RiskTier.HIGH, tuple(reasons)
    if autonomy is AutonomyLevel.HIGH and dimensions.scope >= OrdinalLevel.HIGH:
        reasons.append("High autonomy combined with broad scope.")
        return RiskTier.HIGH, tuple(reasons)
    if dimensions.severity >= OrdinalLevel.MODERATE or dimensions.likelihood >= OrdinalLevel.MODERATE:
        reasons.append("At least one material consequence or likelihood dimension is present.")
        return RiskTier.MODERATE, tuple(reasons)
    reasons.append("Consequences and likelihood are both low under the stated scope.")
    return RiskTier.LOW, tuple(reasons)


def _disposition(tier: RiskTier, evidence_status: EvidenceStatus) -> str:
    if evidence_status <= EvidenceStatus.ASSUMED:
        return "COLLECT_EVIDENCE_BEFORE_APPROVAL"
    return {
        RiskTier.LOW: "STANDARD_REVIEW",
        RiskTier.MODERATE: "APPROVE_WITH_VERIFIED_CONTROLS",
        RiskTier.HIGH: "SPECIALIST_REVIEW_AND_RELEASE_GATE",
        RiskTier.CRITICAL: "REDUCE_AUTONOMY_OR_FORMAL_EXCEPTION",
    }[tier]


def assess(
    scenario: RiskScenario,
    capability: Capability,
    *,
    claims: Iterable[MitigationClaim] = (),
    evidence: Iterable[ControlEvidence] = (),
    as_of: date = date(2026, 9, 20),
) -> Assessment:
    if scenario.capability_id != capability.capability_id:
        raise ValueError(
            f"scenario {scenario.scenario_id} applies to {scenario.capability_id}, "
            f"not {capability.capability_id}"
        )
    inherent_tier, _ = classify_risk(scenario.dimensions, capability.autonomy)
    values = scenario.dimensions.model_dump()
    evidence_by_control = {item.control_id: item for item in evidence}
    applied: list[str] = []
    rejected: list[str] = []

    for claim in claims:
        key = f"{claim.control_id}:{claim.dimension}"
        record = evidence_by_control.get(claim.control_id)
        if claim.scenario_id != scenario.scenario_id:
            rejected.append(f"{key}:wrong_scenario")
            continue
        if values[claim.dimension] != claim.from_level:
            rejected.append(f"{key}:stale_baseline")
            continue
        if record is None or scenario.scenario_id not in record.scenario_ids:
            rejected.append(f"{key}:no_scenario_evidence")
            continue
        if record.status < EvidenceStatus.TESTED:
            rejected.append(f"{key}:evidence_not_tested")
            continue
        if record.valid_through is not None and record.valid_through < as_of:
            rejected.append(f"{key}:evidence_expired")
            continue
        values[claim.dimension] = claim.to_level
        applied.append(key)

    residual = RiskDimensions(**values)
    residual_tier, _ = classify_risk(residual, capability.autonomy)
    return Assessment(
        scenario_id=scenario.scenario_id,
        inherent_dimensions=scenario.dimensions,
        inherent_tier=inherent_tier,
        residual_dimensions=residual,
        residual_tier=residual_tier,
        disposition=_disposition(residual_tier, scenario.evidence_status),
        applied_claims=tuple(applied),
        rejected_claims=tuple(rejected),
        required_controls=required_controls(residual_tier),
    )


@dataclass(frozen=True)
class BlastRadius:
    reachable_assets: tuple[str, ...]
    writable_assets: tuple[str, ...]
    severe_assets: tuple[str, ...]
    trust_zone_crossings: int
    delegated_hops: int


def procurement_graph(include_finance: bool = True) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node("procurement_agent", zone="agent", criticality="moderate")
    graph.add_node("vendor_db", zone="internal_data", criticality="high")
    graph.add_node("email_gateway", zone="external_boundary", criticality="high")
    graph.add_node("purchase_api", zone="finance", criticality="high")
    graph.add_node("erp", zone="finance", criticality="severe")
    graph.add_node("research_agent", zone="agent", criticality="moderate")
    graph.add_node("public_web", zone="external_boundary", criticality="moderate")
    graph.add_edge("procurement_agent", "vendor_db", mode="read", delegated=False)
    graph.add_edge("procurement_agent", "email_gateway", mode="write", delegated=False)
    graph.add_edge("procurement_agent", "purchase_api", mode="write", delegated=False)
    graph.add_edge("purchase_api", "erp", mode="write", delegated=False)
    graph.add_edge("procurement_agent", "research_agent", mode="delegate", delegated=True)
    graph.add_edge("research_agent", "public_web", mode="read", delegated=False)
    if include_finance:
        graph.add_node("payment_service", zone="finance", criticality="severe")
        graph.add_edge("erp", "payment_service", mode="write", delegated=False)
    return graph


def blast_radius(graph: nx.DiGraph, source: str = "procurement_agent") -> BlastRadius:
    reachable = nx.descendants(graph, source)
    writable: set[str] = set()
    crossings = 0
    delegated = 0
    for parent, child in nx.edge_dfs(graph, source):
        edge = graph.edges[parent, child]
        if edge["mode"] in {"write", "delegate"}:
            writable.add(child)
        if graph.nodes[parent]["zone"] != graph.nodes[child]["zone"]:
            crossings += 1
        delegated += int(edge.get("delegated", False))
    severe = {node for node in reachable if graph.nodes[node]["criticality"] == "severe"}
    return BlastRadius(
        reachable_assets=tuple(sorted(reachable)),
        writable_assets=tuple(sorted(writable)),
        severe_assets=tuple(sorted(severe)),
        trust_zone_crossings=crossings,
        delegated_hops=delegated,
    )


def demo_capabilities() -> dict[str, Capability]:
    return {
        "catalog_search": Capability(
            capability_id="catalog_search", description="Search an approved catalogue", mutates_state=False,
            reversible=True, autonomy=AutonomyLevel.BOUNDED,
        ),
        "purchase_order": Capability(
            capability_id="purchase_order", description="Create a binding purchase order", mutates_state=True,
            financial_limit_usd=25_000, reversible=False, autonomy=AutonomyLevel.BOUNDED,
        ),
        "payment": Capability(
            capability_id="payment", description="Issue a vendor payment", mutates_state=True,
            privileged_access=True, financial_limit_usd=100_000, reversible=False, autonomy=AutonomyLevel.HIGH,
        ),
    }


def demo_scenarios() -> tuple[RiskScenario, ...]:
    return (
        RiskScenario(
            scenario_id="OPS-001", title="Duplicate purchase order on retry", kind=ScenarioKind.OPERATIONAL,
            capability_id="purchase_order", trigger="Response is lost after the provider commits the order",
            consequence="A second retry creates another financial commitment",
            dimensions=RiskDimensions(severity=OrdinalLevel.HIGH, likelihood=OrdinalLevel.MODERATE,
                                      detectability_difficulty=OrdinalLevel.MODERATE, irreversibility=OrdinalLevel.HIGH,
                                      scope=OrdinalLevel.MODERATE),
            evidence_status=EvidenceStatus.TESTED, evidence_refs=("test-idempotency-001",),
            owner="Procurement Platform",
        ),
        RiskScenario(
            scenario_id="ADV-001", title="Supplier content redirects payment", kind=ScenarioKind.ADVERSARIAL,
            capability_id="payment", trigger="Indirect prompt injection in a supplier document",
            consequence="Funds are sent to an attacker-controlled account",
            dimensions=RiskDimensions(severity=OrdinalLevel.SEVERE, likelihood=OrdinalLevel.MODERATE,
                                      detectability_difficulty=OrdinalLevel.HIGH, irreversibility=OrdinalLevel.SEVERE,
                                      scope=OrdinalLevel.HIGH),
            evidence_status=EvidenceStatus.DOCUMENTED, evidence_refs=("OWASP-ASI-2026", "NIST-AI-800-5"),
            owner="Finance Security",
        ),
        RiskScenario(
            scenario_id="OPS-002", title="Catalogue recommendation is stale", kind=ScenarioKind.OPERATIONAL,
            capability_id="catalog_search", trigger="Catalogue freshness job misses one update",
            consequence="A human sees an outdated recommendation before purchasing",
            dimensions=RiskDimensions(severity=OrdinalLevel.MODERATE, likelihood=OrdinalLevel.MODERATE,
                                      detectability_difficulty=OrdinalLevel.LOW, irreversibility=OrdinalLevel.LOW,
                                      scope=OrdinalLevel.LOW),
            evidence_status=EvidenceStatus.ASSUMED, assumptions=("No direct write capability exists",),
            owner="Procurement Data",
        ),
    )


def evaluation_report() -> dict[str, float | int]:
    capabilities = demo_capabilities()
    cases = (("OPS-001", RiskTier.HIGH), ("ADV-001", RiskTier.CRITICAL), ("OPS-002", RiskTier.MODERATE))
    scenarios = {item.scenario_id: item for item in demo_scenarios()}
    correct = 0
    for scenario_id, expected in cases:
        scenario = scenarios[scenario_id]
        actual, _ = classify_risk(scenario.dimensions, capabilities[scenario.capability_id].autonomy)
        correct += int(actual is expected)
    return {"correct": correct, "cases": len(cases), "classification_accuracy": correct / len(cases)}
