"""AS-003 supported-dominance competition for ordinary action selection.

The module deliberately contains no candidate generation, execution, learning,
or mutable prediction state.  It compares coherent proposition channels only
within their own keys and delegates genuine incomparability to the already
qualified candidate-local stochastic term.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from umbra_core.physiology import BOUNDS
from umbra_core.stochastic_competition import (
    candidate_behavioral_identity,
    candidate_stochastic_term,
)


CONTRACT_SCHEMA = "SUPPORTED_DOMINANCE_DISTRIBUTED_COMPETITION_V1"
CONSEQUENCE_VIEW_SCHEMA = "CANDIDATE_CONSEQUENCE_VIEW_V1"
SUPPORTED = "SUPPORTED"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

# This is an invariant ceiling, not a truncation policy.  Exceeding it fails
# closed instead of assigning semantic priority by candidate position.
MAX_ORDINARY_CANDIDATES = 256
MAX_CHANNELS_PER_CANDIDATE = 64
MAX_PROVENANCE_REFS = 4


@dataclass(frozen=True)
class EvidenceValue:
    """One ordinal value inside one coherent proposition channel."""

    status: str
    order: float | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {SUPPORTED, UNKNOWN, NOT_APPLICABLE}:
            raise ValueError(f"invalid_evidence_status:{self.status}")
        if self.status == SUPPORTED and self.order is None:
            raise ValueError("supported_evidence_requires_order")
        if self.status != SUPPORTED and self.order is not None:
            raise ValueError("unsupported_evidence_cannot_have_order")
        if len(self.provenance) > MAX_PROVENANCE_REFS:
            raise ValueError("evidence_provenance_bound_exceeded")

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "order": self.order,
            "provenance": list(self.provenance),
        }


def supported(order: float, *provenance: str) -> EvidenceValue:
    return EvidenceValue(
        SUPPORTED,
        float(order),
        tuple(str(item) for item in provenance if item)[:MAX_PROVENANCE_REFS],
    )


def unknown(*provenance: str) -> EvidenceValue:
    return EvidenceValue(
        UNKNOWN,
        None,
        tuple(str(item) for item in provenance if item)[:MAX_PROVENANCE_REFS],
    )


def not_applicable() -> EvidenceValue:
    return EvidenceValue(NOT_APPLICABLE, None, ())


@dataclass(frozen=True)
class CandidateConsequenceView:
    identity: str
    capability: str
    params: Mapping[str, Any]
    channels: Mapping[str, EvidenceValue]
    stochastic_term: float
    schema: str = CONSEQUENCE_VIEW_SCHEMA

    def __post_init__(self) -> None:
        if len(self.channels) > MAX_CHANNELS_PER_CANDIDATE:
            raise ValueError("candidate_channel_bound_exceeded")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "identity": self.identity,
            "capability": self.capability,
            "params": dict(self.params),
            "channels": {
                key: value.as_dict() for key, value in sorted(self.channels.items())
            },
            "stochastic_term": self.stochastic_term,
        }


@dataclass(frozen=True)
class DominanceAttempt:
    dominator: str
    target: str
    passed: bool
    reason: str
    strict_channels: tuple[str, ...] = ()
    blocking_channels: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "dominator": self.dominator,
            "target": self.target,
            "passed": self.passed,
            "reason": self.reason,
            "strict_channels": list(self.strict_channels),
            "blocking_channels": list(self.blocking_channels),
        }


@dataclass(frozen=True)
class CompetitionResult:
    selected_identity: str
    frontier_identities: tuple[str, ...]
    dominated_identities: tuple[str, ...]
    attempts: tuple[DominanceAttempt, ...]
    stochastic_resolution_required: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": CONTRACT_SCHEMA,
            "selected_identity": self.selected_identity,
            "frontier_identities": list(self.frontier_identities),
            "dominated_identities": list(self.dominated_identities),
            "stochastic_resolution_required": self.stochastic_resolution_required,
            "attempts": [attempt.as_dict() for attempt in self.attempts],
        }


def _coerce_evidence(value: Any) -> EvidenceValue:
    if isinstance(value, EvidenceValue):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("evidence_value_must_be_mapping")
    status = str(value.get("status", UNKNOWN))
    provenance = tuple(str(item) for item in value.get("provenance", ()) if item)
    order = value.get("order")
    return EvidenceValue(
        status,
        float(order) if status == SUPPORTED and order is not None else None,
        provenance[:MAX_PROVENANCE_REFS],
    )


def supported_dominance(
    a: CandidateConsequenceView, b: CandidateConsequenceView
) -> DominanceAttempt:
    """Return a complete, order-independent dominance explanation."""

    strict: list[str] = []
    blocked: list[str] = []
    for key in sorted(set(a.channels) | set(b.channels)):
        av = a.channels.get(key, not_applicable())
        bv = b.channels.get(key, not_applicable())
        # Fully-qualified propositions compare only when applicable to both
        # candidates.  Absence is not UNKNOWN and cannot create merit.
        if av.status == NOT_APPLICABLE or bv.status == NOT_APPLICABLE:
            continue
        if av.status != SUPPORTED or bv.status != SUPPORTED:
            blocked.append(key)
            continue
        assert av.order is not None and bv.order is not None
        if av.order < bv.order:
            return DominanceAttempt(
                a.identity,
                b.identity,
                False,
                "worse_in_supported_channel",
                tuple(strict),
                (key,),
            )
        if av.order > bv.order:
            strict.append(key)
    if blocked:
        return DominanceAttempt(
            a.identity,
            b.identity,
            False,
            "unknown_or_inapplicable_blocks_elimination",
            tuple(strict),
            tuple(blocked),
        )
    if not strict:
        return DominanceAttempt(
            a.identity,
            b.identity,
            False,
            "no_strict_supported_improvement",
        )
    return DominanceAttempt(
        a.identity,
        b.identity,
        True,
        "supported_no_worse_everywhere_and_strictly_better",
        tuple(strict),
    )


def resolve_supported_frontier(
    views: Sequence[CandidateConsequenceView],
) -> CompetitionResult:
    """Compute all pairwise relations from one snapshot, then select once."""

    if not views:
        raise ValueError("no_admissible_existing_candidate")
    if len(views) > MAX_ORDINARY_CANDIDATES:
        raise ValueError("ordinary_candidate_bound_exceeded")
    by_identity = {view.identity: view for view in views}
    if len(by_identity) != len(views):
        raise ValueError("duplicate_behavioral_candidate_not_deduplicated")
    ordered = [by_identity[key] for key in sorted(by_identity)]
    attempts: list[DominanceAttempt] = []
    dominated: set[str] = set()
    for a in ordered:
        for b in ordered:
            if a.identity == b.identity:
                continue
            attempt = supported_dominance(a, b)
            attempts.append(attempt)
            if attempt.passed:
                dominated.add(b.identity)
    frontier = [view for view in ordered if view.identity not in dominated]
    if not frontier:
        raise RuntimeError("supported_dominance_frontier_empty")
    selected = sorted(
        frontier,
        key=lambda view: (-view.stochastic_term, view.identity),
    )[0]
    return CompetitionResult(
        selected_identity=selected.identity,
        frontier_identities=tuple(view.identity for view in frontier),
        dominated_identities=tuple(sorted(dominated)),
        attempts=tuple(attempts),
        stochastic_resolution_required=len(frontier) > 1,
    )


def _physiology_channels(
    *,
    physiology: Any,
    effect_branches: Sequence[Mapping[str, float]],
) -> dict[str, EvidenceValue]:
    """Compare conservative one-step distance to each dimension's own ideal."""

    branches = tuple(effect_branches) or ({},)
    channels: dict[str, EvidenceValue] = {}
    for dimension, bounds in BOUNDS.items():
        current = float(physiology.get(dimension))
        worst_distance = max(
            abs((current + float(branch.get(dimension, 0.0))) - bounds.ideal)
            for branch in branches
        )
        channels[f"physiology.{dimension}"] = supported(
            -worst_distance,
            f"constitutional_effect_branch:{dimension}",
        )
    return channels


def build_consequence_view(
    candidate: Any,
    *,
    physiology: Any,
    effect_branches: Sequence[Mapping[str, float]],
    organism_basis: int | str | None,
    active_tick: int,
    self_model_view: Mapping[str, Any] | None = None,
    world_model_view: Mapping[str, Any] | None = None,
    temporal_channels: Mapping[str, Any] | None = None,
    individuality_channels: Mapping[str, Any] | None = None,
    contextual_channels: Mapping[str, Any] | None = None,
    option_channels: Mapping[str, Any] | None = None,
) -> CandidateConsequenceView:
    """Compose one immutable fixed-size view without cross-channel arithmetic."""

    identity = candidate_behavioral_identity(candidate.capability, candidate.params)
    channels = _physiology_channels(
        physiology=physiology,
        effect_branches=effect_branches,
    )
    for owner in (
        self_model_view,
        world_model_view,
        temporal_channels,
        individuality_channels,
        contextual_channels,
        option_channels,
    ):
        for key, value in sorted((owner or {}).items()):
            if key in channels:
                raise ValueError(f"duplicate_evidence_channel:{key}")
            channels[str(key)] = _coerce_evidence(value)
    stochastic = (
        candidate_stochastic_term(
            organism_basis=organism_basis,
            active_tick=active_tick,
            capability=candidate.capability,
            params=candidate.params,
        )
        if organism_basis is not None
        else 0.0
    )
    return CandidateConsequenceView(
        identity=identity,
        capability=str(candidate.capability),
        params=dict(candidate.params),
        channels=channels,
        stochastic_term=stochastic,
    )


def evaluate_candidates(
    candidates: Sequence[Any],
    *,
    physiology: Any,
    organism_basis: int | str | None,
    active_tick: int,
    effect_branches_for: Callable[[Any], Sequence[Mapping[str, float]]],
    self_model_view_for: Callable[[Any], Mapping[str, Any]] | None = None,
    world_model_view_for: Callable[[Any], Mapping[str, Any]] | None = None,
    temporal_channels_for: Callable[[Any], Mapping[str, Any]] | None = None,
    individuality_channels_for: Callable[[Any], Mapping[str, Any]] | None = None,
    contextual_channels_for: Callable[[Any], Mapping[str, Any]] | None = None,
    option_channels_for: Callable[[Any], Mapping[str, Any]] | None = None,
) -> tuple[Any, tuple[CandidateConsequenceView, ...], CompetitionResult]:
    """Evaluate a bounded canonical pool and return one existing candidate."""

    if len(candidates) > MAX_ORDINARY_CANDIDATES:
        raise ValueError("ordinary_candidate_bound_exceeded")
    views = tuple(
        build_consequence_view(
            candidate,
            physiology=physiology,
            effect_branches=effect_branches_for(candidate),
            organism_basis=organism_basis,
            active_tick=active_tick,
            self_model_view=(
                self_model_view_for(candidate) if self_model_view_for else None
            ),
            world_model_view=(
                world_model_view_for(candidate) if world_model_view_for else None
            ),
            temporal_channels=(
                temporal_channels_for(candidate) if temporal_channels_for else None
            ),
            individuality_channels=(
                individuality_channels_for(candidate)
                if individuality_channels_for
                else None
            ),
            contextual_channels=(
                contextual_channels_for(candidate) if contextual_channels_for else None
            ),
            option_channels=(
                option_channels_for(candidate) if option_channels_for else None
            ),
        )
        for candidate in candidates
    )
    result = resolve_supported_frontier(views)
    selected = next(
        candidate
        for candidate, view in zip(candidates, views)
        if view.identity == result.selected_identity
    )
    return selected, views, result


def trace_summary(
    views: Sequence[CandidateConsequenceView], result: CompetitionResult
) -> dict[str, Any]:
    channel_keys = sorted({key for view in views for key in view.channels})
    supported_counts = {
        key: sum(view.channels.get(key, not_applicable()).status == SUPPORTED for view in views)
        for key in channel_keys
    }
    unknown_counts = {
        key: sum(view.channels.get(key, not_applicable()).status == UNKNOWN for view in views)
        for key in channel_keys
    }
    stochastic_full_pool = sorted(
        views, key=lambda view: (-view.stochastic_term, view.identity)
    )[0]
    return {
        **result.as_dict(),
        "admissible_candidate_count": len(views),
        "applicable_channel_count": len(channel_keys),
        "supported_count_by_channel": supported_counts,
        "unknown_count_by_channel": unknown_counts,
        "pairwise_dominance_count": sum(attempt.passed for attempt in result.attempts),
        "eliminated_candidate_count": len(result.dominated_identities),
        "frontier_size": len(result.frontier_identities),
        "frontier_full_pool_ratio": len(result.frontier_identities) / len(views),
        "frontier_equals_full_pool": len(result.frontier_identities) == len(views),
        "stochastic_only_full_pool_shadow_winner": stochastic_full_pool.identity,
        "distributed_changed_winner": stochastic_full_pool.identity != result.selected_identity,
        "views": [view.as_dict() for view in views],
    }
