"""Pure AS-004 continuation and authority-boundary tests.

These fixtures use explicit source snapshots and immutable hypothetical
services.  They do not construct or tick an organism.
"""

from __future__ import annotations

from umbra_core.hypothetical.adapters import (
    SourceBackedRegulatoryService,
    SourceOpportunity,
    build_regulatory_service,
    root_state_from_sources,
)
from umbra_core.hypothetical.continuation import (
    bounded_continuation_status,
    service_transition,
)
from umbra_core.hypothetical.core import (
    DependencyToken,
    EvidenceEnvelope,
    FrozenMap,
    RegulatoryService,
    TransitionContract,
    TransitionStatus,
    ValidatedRegulatoryService,
    validate_regulatory_service,
)
from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology


BODY = "body-schema:test"


class ZeroNoise:
    seed = None

    def gauss(self, mean: float, sigma: float) -> float:
        return 0.0


def hard(value: float, ref: str) -> EvidenceEnvelope:
    return EvidenceEnvelope(value, value, "HARD_CONTRACT", (ref,))


def unknown(ref: str) -> EvidenceEnvelope:
    return EvidenceEnvelope.unknown(ref)


def opportunity(persistence: EvidenceEnvelope) -> SourceOpportunity:
    return SourceOpportunity(
        identity="opportunity:test",
        availability=TransitionStatus.SUPPORTED,
        persistence_horizon=persistence,
        provenance=("test:opportunity",),
        token=DependencyToken("opportunity", "opportunity:test", "v1"),
    )


def root(values: dict[str, float], *, persistence: EvidenceEnvelope | None = None):
    return root_state_from_sources(
        root_tick=0,
        physiology=values,
        body_schema_identity=BODY,
        body_schema_version=1,
        opportunities={"opportunity:test": opportunity(persistence or hard(32.0, "test:horizon"))},
    )


def zero_action() -> TransitionContract:
    return TransitionContract(
        semantic_identity="test:current-action",
        duration=hard(1.0, "test:action-duration"),
        effect_branches=({name: hard(0.0, f"test:effect:{name}") for name in ("energy", "fatigue", "integrity", "stimulation")},),
        provenance=("test:current-action",),
    )


def service(
    capability: str,
    owners: tuple[str, ...],
    effects: dict[str, float],
    *,
    persistence: EvidenceEnvelope | None = None,
    duration: EvidenceEnvelope | None = None,
) -> SourceBackedRegulatoryService:
    opp = opportunity(persistence or hard(32.0, "test:horizon"))
    duration = duration or hard(1.0, f"test:{capability}:duration")
    branches = (FrozenMap({name: hard(value, f"test:{capability}:{name}") for name, value in effects.items()}),)
    spec = RegulatoryService(
        semantic_identity=f"test:service:{capability}",
        owners=owners,
        terminal_capability=capability,
        opportunity_identity=opp.identity,
        route_identity=None,
        duration=duration,
        effect_branches=branches,
        body_schema_identity=BODY,
        preconditions=(hard(1.0, f"test:{capability}:capability"),),
        provenance=(f"test:{capability}",),
        availability=TransitionStatus.SUPPORTED,
        dependencies=(opp.token,),
    )
    validated = validate_regulatory_service(spec)
    assert isinstance(validated, ValidatedRegulatoryService)
    return SourceBackedRegulatoryService(
        service=spec,
        validated=validated,
        persistence_horizon=opp.persistence_horizon,
        dependencies=(opp.token,),
        construction_status=TransitionStatus.SUPPORTED,
        reason="test-source-backed",
    )


def test_single_obligation_has_one_supported_continuation() -> None:
    result = bounded_continuation_status(
        root({"energy": 0.20, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55}),
        zero_action(),
        [service("CHARGE", ("energy",), {"energy": 0.12})],
        obligations=("energy",),
    )
    assert result.status is TransitionStatus.SUPPORTED
    assert result.witnesses


def test_two_obligations_require_a_complete_ordered_continuation() -> None:
    result = bounded_continuation_status(
        root({"energy": 0.20, "fatigue": 0.70, "integrity": 0.90, "stimulation": 0.55}),
        zero_action(),
        [
            service("CHARGE", ("energy",), {"energy": 0.12}),
            service("REST", ("fatigue",), {"fatigue": -0.60}),
        ],
        obligations=("energy", "fatigue"),
    )
    assert result.status is TransitionStatus.SUPPORTED
    assert any("test:service:CHARGE" in witness[1] for witness in result.witnesses)


def test_later_service_choice_can_differ_by_current_outcome_branch() -> None:
    current = TransitionContract(
        semantic_identity="test:branching-current-action",
        duration=hard(1.0, "test:action-duration"),
        effect_branches=(
            FrozenMap({"energy": hard(0.0, "test:branch:energy")}),
            FrozenMap({"fatigue": hard(0.0, "test:branch:fatigue")}),
        ),
        provenance=("test:branching-current-action",),
    )
    result = bounded_continuation_status(
        root({"energy": 0.20, "fatigue": 0.70, "integrity": 0.90, "stimulation": 0.55}),
        current,
        [
            service("CHARGE", ("energy",), {"energy": 0.12}),
            service("REST", ("fatigue",), {"fatigue": -0.60}),
        ],
        obligations=("energy", "fatigue"),
    )
    assert result.status is TransitionStatus.SUPPORTED


def test_unknown_opportunity_horizon_blocks_guaranteed_continuation() -> None:
    result = bounded_continuation_status(
        root({"energy": 0.20, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55}),
        zero_action(),
        [service("CHARGE", ("energy",), {"energy": 0.12}, persistence=unknown("test:unknown-horizon"))],
        obligations=("energy",),
    )
    assert result.status is TransitionStatus.UNKNOWN


def test_failure_branch_is_universal_not_cherry_picked() -> None:
    failing = service(
        "CHARGE",
        ("energy",),
        {"energy": 0.12},
    )
    # Rebuild the service with a second supported branch that cannot restore
    # the obligation.  The proof must not accept the favorable branch alone.
    spec = failing.service
    two_branch_spec = RegulatoryService(
        semantic_identity=spec.semantic_identity + ":two-branch",
        owners=spec.owners,
        terminal_capability=spec.terminal_capability,
        opportunity_identity=spec.opportunity_identity,
        route_identity=spec.route_identity,
        duration=spec.duration,
        effect_branches=(
            FrozenMap({"energy": hard(0.12, "test:success")}),
            FrozenMap({"energy": hard(-0.25, "test:failure")}),
        ),
        body_schema_identity=spec.body_schema_identity,
        preconditions=spec.preconditions,
        provenance=spec.provenance,
        availability=spec.availability,
        dependencies=spec.dependencies,
    )
    validated = validate_regulatory_service(two_branch_spec)
    assert isinstance(validated, ValidatedRegulatoryService)
    two_branch = SourceBackedRegulatoryService(
        two_branch_spec,
        validated,
        failing.persistence_horizon,
        failing.dependencies,
        TransitionStatus.SUPPORTED,
        "test-source-backed",
    )
    result = bounded_continuation_status(
        root({"energy": 0.20, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55}),
        zero_action(),
        [two_branch],
        obligations=("energy",),
    )
    assert result.status is TransitionStatus.UNSUPPORTED


def test_non_categorical_service_transition_is_unknown() -> None:
    valid = service("CHARGE", ("energy",), {"energy": 0.12})
    invalid_spec = RegulatoryService(
        semantic_identity="test:service:unknown-duration",
        owners=valid.service.owners,
        terminal_capability=valid.service.terminal_capability,
        opportunity_identity=valid.service.opportunity_identity,
        route_identity=valid.service.route_identity,
        duration=unknown("test:duration"),
        effect_branches=valid.service.effect_branches,
        body_schema_identity=valid.service.body_schema_identity,
        preconditions=valid.service.preconditions,
        provenance=valid.service.provenance,
        availability=valid.service.availability,
        dependencies=valid.service.dependencies,
    )
    result = service_transition(
        root({"energy": 0.20, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55}),
        SourceBackedRegulatoryService(
            invalid_spec,
            None,
            valid.persistence_horizon,
            valid.dependencies,
            TransitionStatus.UNKNOWN,
            "SOURCE_EVIDENCE_INSUFFICIENT",
        ),
    )
    assert result.status is TransitionStatus.UNKNOWN


def test_more_than_four_service_steps_are_bounded_unknown() -> None:
    result = bounded_continuation_status(
        root({"energy": 0.20, "fatigue": 0.70, "integrity": 0.34, "stimulation": 0.24}),
        zero_action(),
        [
            service("CHARGE", ("energy",), {"energy": 0.12}),
            service("REST", ("fatigue",), {"fatigue": -0.66}),
        ],
        obligations=("energy", "fatigue", "integrity", "stimulation"),
        max_depth=4,
    )
    assert result.status is not TransitionStatus.SUPPORTED


def test_as004_filter_receives_base_pool_and_optional_intent_together() -> None:
    arb = Arbitrator()
    arb.generate_candidates = lambda phys, observations, tick: [
        Candidate("IDLE", {}),
        Candidate("ORIENT", {"heading": 0.0}),
    ]
    arb._introduces_critical_boundary = lambda *args, **kwargs: False
    seen: list[tuple[str, ...]] = []

    def continuation_filter(candidates):
        seen.append(tuple(candidate.capability for candidate in candidates))
        return tuple(candidates), {"root_size": 1, "survivor_count": len(candidates)}

    trace: dict[str, object] = {}
    arb.select(
        Physiology(),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("CHARGE", {"source": "optional"})],
        continuation_filter_for=continuation_filter,
        distributed_trace=trace,
    )
    assert seen and set(seen[0]) == {"IDLE", "ORIENT", "CHARGE"}
    assert trace["continuation"]["root_size"] == 1
