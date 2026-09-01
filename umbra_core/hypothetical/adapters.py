"""Pure, source-backed inputs for the AS-003N hypothetical substrate.

These adapters accept explicit immutable snapshots. They do not import runtime,
arbitration, Governance, Embodiment, persistence, or a world planner, and they
never mutate a source owner. A current observation is deliberately distinct
from a source-proven bounded persistence horizon.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from umbra_core.physiology import BOUNDS, DEFAULT_DRIFT, Physiology, verified_outcome_effect_branches
from umbra_core.self_model.engine import CapabilitySupportEnvelope, SupportInterval, SupportSemantics

from .core import (
    DependencyToken,
    EvidenceEnvelope,
    FrozenMap,
    HypotheticalState,
    OpportunityEvidence,
    PhysiologyBranch,
    RegulatoryService,
    RouteEvidence,
    TransitionContract,
    TransitionStatus,
    ValidatedRegulatoryService,
    validate_regulatory_service,
)


OWNER_NAMES = tuple(BOUNDS)
SERVICE_OWNERS = {"CHARGE": ("energy",), "REST": ("fatigue", "integrity"), "INSPECT": ("stimulation",)}


def _observed(value: float, provenance: str) -> EvidenceEnvelope:
    value = float(value)
    return EvidenceEnvelope(value, value, SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value, (provenance,))


def _hard(value: float, provenance: str) -> EvidenceEnvelope:
    value = float(value)
    return EvidenceEnvelope(value, value, SupportSemantics.HARD_CONTRACT.value, (provenance,))


def envelope_from_interval(interval: SupportInterval, *, expected_body_schema: str, source_body_schema: str, provenance: str) -> EvidenceEnvelope:
    """Preserve source support exactly; a mismatched or incomplete body is unknown."""
    if str(expected_body_schema) != str(source_body_schema):
        return EvidenceEnvelope.unknown(provenance, "body-schema-mismatch")
    return EvidenceEnvelope(interval.minimum, interval.maximum, interval.semantics, tuple((*interval.provenance, provenance)))


@dataclass(frozen=True)
class SourceOpportunity:
    """An explicit policy-safe opportunity snapshot.

    ``persistence_horizon`` is root-relative elapsed time for which an
    authoritative source guarantees availability. A present observation with
    no such source must use ``EvidenceEnvelope.unknown``.
    """

    identity: str
    availability: TransitionStatus
    persistence_horizon: EvidenceEnvelope
    provenance: tuple[str, ...]
    token: DependencyToken

    def evidence(self) -> OpportunityEvidence:
        return OpportunityEvidence(self.identity, self.availability, self.persistence_horizon, self.provenance)


@dataclass(frozen=True)
class SourceRoute:
    identity: str
    availability: TransitionStatus
    timing: EvidenceEnvelope
    capability: EvidenceEnvelope
    provenance: tuple[str, ...]
    token: DependencyToken

    def evidence(self) -> RouteEvidence:
        return RouteEvidence(self.identity, self.availability, self.timing, self.capability, self.provenance)


@dataclass(frozen=True)
class SourceBackedRegulatoryService:
    """A validated non-executable service plus its source persistence fact."""

    service: RegulatoryService
    validated: ValidatedRegulatoryService | None
    persistence_horizon: EvidenceEnvelope
    dependencies: tuple[DependencyToken, ...]
    construction_status: TransitionStatus
    reason: str


def root_state_from_sources(
    *,
    root_tick: int,
    physiology: Physiology | Mapping[str, float],
    body_schema_identity: str,
    body_schema_version: int | str,
    opportunities: Mapping[str, SourceOpportunity] = {},
    routes: Mapping[str, SourceRoute] = {},
    pending_commitment: Mapping[str, object] = {},
    additional_dependencies: tuple[DependencyToken, ...] = (),
) -> HypotheticalState:
    """Build an exact root snapshot without turning it into a future guarantee."""
    raw = physiology.as_dict() if isinstance(physiology, Physiology) else dict(physiology)
    if set(raw) != set(OWNER_NAMES):
        raise ValueError("root physiology requires exactly the four authoritative owners")
    values = {name: _observed(float(raw[name]), f"physiology-root:{root_tick}:{name}") for name in OWNER_NAMES}
    root_token = DependencyToken("physiology_root", "organism", f"{int(root_tick)}:{','.join(f'{name}={raw[name]!r}' for name in OWNER_NAMES)}")
    body_token = DependencyToken("body_schema", str(body_schema_identity), str(body_schema_version))
    source_opportunities = {identity: item.evidence() for identity, item in opportunities.items()}
    source_routes = {identity: item.evidence() for identity, item in routes.items()}
    tokens = (*additional_dependencies, root_token, body_token, *(item.token for item in opportunities.values()), *(item.token for item in routes.values()))
    return HypotheticalState(
        root_tick=int(root_tick),
        elapsed_time=_hard(0.0, "physiology-contract:root-elapsed-time"),
        physiology_branches=(PhysiologyBranch(FrozenMap(values), (f"physiology-root:{root_tick}",)),),
        body_schema_identity=str(body_schema_identity),
        opportunities=source_opportunities,
        routes=source_routes,
        pending_commitment=dict(pending_commitment),
        provenance=(f"source-root:{root_tick}",),
        dependencies=tokens,
    )


def capability_envelopes(envelope: CapabilitySupportEnvelope, *, body_schema_identity: str) -> tuple[EvidenceEnvelope, EvidenceEnvelope, EvidenceEnvelope]:
    """Return progress, applied-step, and completion without support promotion."""
    base = f"self-model-capability:{envelope.capability}"
    return (
        envelope_from_interval(envelope.progress, expected_body_schema=body_schema_identity, source_body_schema=envelope.body_schema_id, provenance=f"{base}:progress"),
        envelope_from_interval(envelope.applied_step, expected_body_schema=body_schema_identity, source_body_schema=envelope.body_schema_id, provenance=f"{base}:applied-step"),
        envelope_from_interval(envelope.completion, expected_body_schema=body_schema_identity, source_body_schema=envelope.body_schema_id, provenance=f"{base}:completion"),
    )


def capability_transition_contract(
    capability: str,
    *,
    duration: EvidenceEnvelope,
    opportunity_identity: str | None = None,
    route_identity: str | None = None,
    required_evidence: tuple[EvidenceEnvelope, ...] = (),
) -> TransitionContract:
    """Use existing complete effect branches and explicit drift, never urgency."""
    if not duration.categorical_supported():
        branches = ({name: EvidenceEnvelope.unknown(f"outcome-branch:{capability}") for name in OWNER_NAMES},)
    else:
        branches = []
        for branch_index, outcome in enumerate(verified_outcome_effect_branches(str(capability))):
            effects: dict[str, EvidenceEnvelope] = {}
            for owner in OWNER_NAMES:
                outcome_effect = float(outcome.get(owner, 0.0))
                drift_effect = _hard(DEFAULT_DRIFT[owner], f"physiology-contract:drift:{owner}").scale(duration.maximum or 0.0)
                effects[owner] = _hard(outcome_effect, f"verified-outcome:{capability}:branch:{branch_index}:{owner}").add(drift_effect)
            branches.append(effects)
    return TransitionContract(
        semantic_identity=f"source-capability:{capability}",
        duration=duration,
        effect_branches=tuple(branches),
        required_evidence=required_evidence,
        opportunity_identity=opportunity_identity,
        route_identity=route_identity,
        availability=TransitionStatus.SUPPORTED,
        provenance=(f"source-capability:{capability}",),
    )


def build_regulatory_service(
    *,
    capability: str,
    body_schema_identity: str,
    opportunity: SourceOpportunity,
    route: SourceRoute | None,
    duration: EvidenceEnvelope,
    capability_support: EvidenceEnvelope,
    body_version_token: DependencyToken,
) -> SourceBackedRegulatoryService:
    """Construct only a source-supported, non-executable regulatory service."""
    capability = str(capability)
    owners = SERVICE_OWNERS.get(capability)
    if owners is None:
        raise ValueError("only CHARGE, REST, and INSPECT are source-backed AS-003O services")
    route_id = None if route is None else route.identity
    dependencies = (body_version_token, opportunity.token, *((route.token,) if route else ()))
    required = (duration, capability_support, opportunity.persistence_horizon, *((route.timing, route.capability) if route else ()))
    if opportunity.availability is TransitionStatus.UNSUPPORTED or (route is not None and route.availability is TransitionStatus.UNSUPPORTED):
        status, reason = TransitionStatus.UNSUPPORTED, "KNOWN_SOURCE_UNAVAILABLE"
    elif not all(item.categorical_supported() for item in required) or opportunity.availability is not TransitionStatus.SUPPORTED or (route is not None and route.availability is not TransitionStatus.SUPPORTED):
        status, reason = TransitionStatus.UNKNOWN, "SOURCE_EVIDENCE_INSUFFICIENT"
    else:
        status, reason = TransitionStatus.SUPPORTED, "SOURCE_BACKED"
    contract = capability_transition_contract(capability, duration=duration, opportunity_identity=opportunity.identity, route_identity=route_id, required_evidence=(capability_support,))
    service = RegulatoryService(
        semantic_identity=f"source-service:{capability}:{body_schema_identity}:{opportunity.identity}:{route_id or 'stationary'}",
        owners=owners,
        terminal_capability=capability,
        opportunity_identity=opportunity.identity,
        route_identity=route_id,
        duration=duration,
        effect_branches=contract.effect_branches,
        body_schema_identity=body_schema_identity,
        preconditions=(capability_support,),
        provenance=(f"source-service:{capability}", *opportunity.provenance, *((*route.provenance,) if route else ())),
        availability=status,
        dependencies=dependencies,
    )
    validated = validate_regulatory_service(service)
    if isinstance(validated, ValidatedRegulatoryService):
        return SourceBackedRegulatoryService(service, validated, opportunity.persistence_horizon, dependencies, status, reason)
    return SourceBackedRegulatoryService(service, None, opportunity.persistence_horizon, dependencies, validated.status, validated.reason)
