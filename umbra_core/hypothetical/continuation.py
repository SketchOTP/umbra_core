"""Pure bounded robust-continuation proof over source-backed snapshots.

This module proves feasibility only. It neither ranks actions nor stores an
action queue. Current action choice and later regulatory service choice are
existential; every supported outcome branch is universal for a supported
result. Missing or probabilistic evidence remains UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .adapters import SourceBackedRegulatoryService
from .core import BRANCH_CEILING, EvidenceEnvelope, HypotheticalState, TransitionContract, TransitionResult, TransitionStatus, transition


@dataclass(frozen=True)
class ContinuationProof:
    status: TransitionStatus
    reason: str
    witnesses: tuple[tuple[str, str], ...] = ()
    max_active_paths: int = 0
    unknown_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContinuationSet:
    """Exact branch-keyed witness relation; not a value, count, or score."""

    witnesses_by_branch: tuple[tuple[str, tuple[str, ...]], ...]

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Iterable[str]]) -> "ContinuationSet":
        return cls(tuple(sorted((str(key), tuple(sorted({str(value) for value in values}))) for key, values in mapping.items())))


def _horizon_supports(state: HypotheticalState, service: SourceBackedRegulatoryService) -> TransitionStatus:
    horizon = service.persistence_horizon
    duration = service.service.duration
    if not state.elapsed_time.categorical_supported() or not horizon.categorical_supported() or not duration.categorical_supported():
        return TransitionStatus.UNKNOWN
    # Horizon is a guaranteed root-relative interval: every possible elapsed
    # completion must fit within its lower bound, otherwise no guarantee exists.
    if (state.elapsed_time.maximum or 0.0) + (duration.maximum or 0.0) <= (horizon.minimum or 0.0):
        return TransitionStatus.SUPPORTED
    return TransitionStatus.UNKNOWN


def service_transition(state: HypotheticalState, service: SourceBackedRegulatoryService) -> TransitionResult:
    """Try one source-backed service without choosing it for the organism."""
    if service.validated is None:
        return TransitionResult(service.construction_status, (), service.reason, service.service.provenance, service.dependencies)
    horizon_status = _horizon_supports(state, service)
    if horizon_status is not TransitionStatus.SUPPORTED:
        return TransitionResult(horizon_status, (), "OPPORTUNITY_HORIZON_INSUFFICIENT", service.service.provenance, service.dependencies)
    return transition(
        state,
        TransitionContract(
            semantic_identity=service.service.semantic_identity,
            duration=service.service.duration,
            effect_branches=service.service.effect_branches,
            required_evidence=service.service.preconditions,
            opportunity_identity=service.service.opportunity_identity,
            route_identity=service.service.route_identity,
            availability=service.service.availability,
            service=service.validated,
            provenance=service.service.provenance,
        ),
    )


def robust_continuation_status(
    root: HypotheticalState,
    current_candidate: TransitionContract,
    services: Iterable[SourceBackedRegulatoryService],
) -> ContinuationProof:
    """Require one lawful witness after every supported current outcome branch."""
    current = transition(root, current_candidate)
    if current.status is not TransitionStatus.SUPPORTED:
        if current.reason == "BRANCH_CEILING_EXCEEDED":
            return ContinuationProof(TransitionStatus.UNKNOWN, "BRANCH_FRONTIER_EXCEEDED", max_active_paths=BRANCH_CEILING + 1)
        return ContinuationProof(current.status, f"CURRENT_CANDIDATE_{current.reason}", max_active_paths=len(current.successors))
    if len(current.successors) > BRANCH_CEILING:
        return ContinuationProof(TransitionStatus.UNKNOWN, "BRANCH_FRONTIER_EXCEEDED", max_active_paths=len(current.successors))
    available = tuple(services)
    witnesses: list[tuple[str, str]] = []
    unknown_reasons: list[str] = []
    max_paths = len(current.successors)
    for branch in current.successors:
        supported: list[str] = []
        unknown = False
        for service in available:
            outcome = service_transition(branch, service)
            max_paths = max(max_paths, len(outcome.successors))
            if len(outcome.successors) > BRANCH_CEILING:
                return ContinuationProof(TransitionStatus.UNKNOWN, "BRANCH_FRONTIER_EXCEEDED", max_active_paths=len(outcome.successors))
            if outcome.status is TransitionStatus.SUPPORTED:
                supported.append(service.service.semantic_identity)
            elif outcome.status is TransitionStatus.UNKNOWN:
                unknown = True
                unknown_reasons.append(outcome.reason)
        if supported:
            witnesses.append((branch.semantic_identity, sorted(supported)[0]))
        elif unknown:
            return ContinuationProof(TransitionStatus.UNKNOWN, "BRANCH_CONTINUATION_UNKNOWN", tuple(witnesses), max_paths, tuple(sorted(set(unknown_reasons))))
        else:
            return ContinuationProof(TransitionStatus.UNSUPPORTED, "BRANCH_HAS_NO_SUPPORTED_CONTINUATION", tuple(witnesses), max_paths)
    return ContinuationProof(TransitionStatus.SUPPORTED, "ROBUST_CONTINUATION_SUPPORTED", tuple(witnesses), max_paths)


def strict_continuation_superset(left: ContinuationSet, right: ContinuationSet) -> TransitionStatus:
    """Return SUPPORTED only for exact branch-aligned strict witness inclusion."""
    left_map = dict(left.witnesses_by_branch)
    right_map = dict(right.witnesses_by_branch)
    if set(left_map) != set(right_map):
        return TransitionStatus.UNKNOWN
    strictly_larger = False
    for branch in left_map:
        left_values, right_values = set(left_map[branch]), set(right_map[branch])
        if not right_values.issubset(left_values):
            return TransitionStatus.UNSUPPORTED
        strictly_larger = strictly_larger or left_values != right_values
    return TransitionStatus.SUPPORTED if strictly_larger else TransitionStatus.UNSUPPORTED
