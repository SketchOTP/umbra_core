"""Pure bounded robust-continuation proof over source-backed snapshots.

This module proves feasibility only. It neither ranks actions nor stores an
action queue. Current action choice and later regulatory service choice are
existential; every supported outcome branch is universal for a supported
result. Missing or probabilistic evidence remains UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
import itertools
import json
from typing import Iterable, Mapping, Sequence

from .adapters import SourceBackedRegulatoryService
from .core import BRANCH_CEILING, EvidenceEnvelope, HypotheticalState, TransitionContract, TransitionResult, TransitionStatus, transition


# AS-003L fixed the maximum ordinary corrective-service policy depth at one
# service per true regulatory owner.  Four owners therefore yield at most the
# complete 4! service-order space before physical branch expansion.  This is a
# constitutional bound, not a search tuning knob.
MAX_CONTINUATION_DEPTH = 4
MAX_SERVICE_ORDERS = 24


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


@dataclass(frozen=True)
class ContinuationWitness:
    """One source-backed corrective service order, never an executable plan."""

    branch_key: str
    services: tuple[str, ...]

    def to_canonical(self) -> dict[str, object]:
        return {"branch": self.branch_key, "services": list(self.services)}


def _branch_key(index: int, branch: HypotheticalState) -> str:
    # The branch key is only an O0 relation key.  It is derived from the
    # immutable source-backed state and never exposed as action identity.
    return f"branch:{index}:{branch.semantic_identity}"


def _obligations_complete(state: HypotheticalState, obligations: Sequence[str]) -> TransitionStatus:
    """Return categorical completion for every physical branch in ``state``.

    The hypothetical substrate deliberately does not import the live
    physiology owner.  The caller supplies the already-qualified obligation
    names and this function uses the substrate's interval evidence only.  A
    branch with unknown values cannot be called complete.
    """
    from umbra_core.physiology import BOUNDS

    for branch in state.physiology_branches:
        for owner in obligations:
            value = branch.values.get(owner)
            if value is None or not value.categorical_supported():
                return TransitionStatus.UNKNOWN
            if value.minimum is None or value.maximum is None:
                return TransitionStatus.UNKNOWN
            if not BOUNDS[owner].in_viable(value.minimum) or not BOUNDS[owner].in_viable(value.maximum):
                return TransitionStatus.UNSUPPORTED
    return TransitionStatus.SUPPORTED


def _service_covers(service: SourceBackedRegulatoryService, remaining: frozenset[str]) -> bool:
    return bool(set(service.service.owners) & set(remaining))


def _complete_witness() -> str:
    return json.dumps({"kind": "complete"}, sort_keys=True, separators=(",", ":"))


def _service_witness(identity: str, children: Sequence[str]) -> str:
    return json.dumps(
        {"children": list(children), "kind": "service", "service": identity},
        sort_keys=True,
        separators=(",", ":"),
    )


def _enumerate_witnesses(
    state: HypotheticalState,
    remaining: frozenset[str],
    used: frozenset[str],
    depth: int,
    path_factor: int,
    available: Sequence[SourceBackedRegulatoryService],
    max_depth: int,
    frontier: list[int],
    order_witnesses: set[str],
    unknown_reasons: set[str],
) -> tuple[TransitionStatus, set[str], str]:
    complete = _obligations_complete(state, remaining)
    if complete is TransitionStatus.SUPPORTED:
        return complete, {_complete_witness()}, "OBLIGATIONS_COMPLETE"
    if complete is TransitionStatus.UNKNOWN:
        unknown_reasons.add("PHYSIOLOGY_COMPLETION_UNKNOWN")
    if depth >= max_depth:
        unknown_reasons.add("CONTINUATION_DEPTH_EXHAUSTED")
        return TransitionStatus.UNKNOWN, set(), "CONTINUATION_DEPTH_EXHAUSTED"
    supported_witnesses: set[str] = set()
    saw_unknown = complete is TransitionStatus.UNKNOWN
    for service in available:
        identity = service.service.semantic_identity
        if identity in used or not _service_covers(service, remaining):
            continue
        result = service_transition(state, service)
        if result.status is TransitionStatus.UNSUPPORTED:
            continue
        if result.status is TransitionStatus.UNKNOWN:
            unknown_reasons.add(result.reason)
            saw_unknown = True
            continue
        projected_frontier = path_factor * len(result.successors)
        frontier[0] = max(frontier[0], projected_frontier)
        if projected_frontier > BRANCH_CEILING:
            unknown_reasons.add("BRANCH_FRONTIER_EXCEEDED")
            saw_unknown = True
            continue
        child_remaining = frozenset(set(remaining) - set(service.service.owners))
        child_witnesses: list[set[str]] = []
        child_unknown = False
        child_supported = True
        for child in result.successors:
            served = _obligations_complete(child, service.service.owners)
            if served is TransitionStatus.UNSUPPORTED:
                child_supported = False
                break
            if served is TransitionStatus.UNKNOWN:
                child_unknown = True
                child_supported = False
                continue
            status, witnesses, reason = _enumerate_witnesses(
                child,
                child_remaining,
                frozenset((*used, identity)),
                depth + 1,
                projected_frontier,
                available,
                max_depth,
                frontier,
                order_witnesses,
                unknown_reasons,
            )
            if status is TransitionStatus.SUPPORTED:
                child_witnesses.append(witnesses)
            elif status is TransitionStatus.UNKNOWN:
                child_unknown = True
                child_supported = False
            else:
                child_supported = False
        if child_supported and len(child_witnesses) == len(result.successors):
            combinations = itertools.product(*child_witnesses)
            service_witnesses = {
                _service_witness(identity, children)
                for children in combinations
            }
            order_witnesses.update(service_witnesses)
            if len(order_witnesses) > MAX_SERVICE_ORDERS:
                unknown_reasons.add("SERVICE_ORDER_FRONTIER_EXCEEDED")
                saw_unknown = True
                continue
            supported_witnesses.update(service_witnesses)
        elif child_unknown:
            saw_unknown = True
    if supported_witnesses:
        return TransitionStatus.SUPPORTED, supported_witnesses, "SUPPORTED_CONTINUATION"
    if saw_unknown:
        return TransitionStatus.UNKNOWN, set(), "CONTINUATION_UNKNOWN"
    return TransitionStatus.UNSUPPORTED, set(), "NO_SUPPORTED_CONTINUATION"


def bounded_continuation_status(
    root: HypotheticalState,
    current_candidate: TransitionContract,
    services: Iterable[SourceBackedRegulatoryService],
    *,
    obligations: Iterable[str],
    max_depth: int = MAX_CONTINUATION_DEPTH,
) -> ContinuationProof:
    """Evaluate a bounded AND/OR continuation over all supported branches.

    The current candidate and each later service are OR choices.  Every
    supported effect branch is an AND obligation.  A known supported service
    may satisfy an OR node; an UNKNOWN branch remains UNKNOWN when no
    supported alternative exists.  Services are not repeated because the
    AS-003L contract authorizes one corrective instance per owner.
    """
    if max_depth < 1 or max_depth > MAX_CONTINUATION_DEPTH:
        return ContinuationProof(TransitionStatus.UNKNOWN, "CONTINUATION_DEPTH_OUT_OF_CONTRACT")
    required = tuple(sorted({str(owner) for owner in obligations}))
    if not required:
        return ContinuationProof(TransitionStatus.UNSUPPORTED, "NO_ACTIVE_REGULATORY_OBLIGATIONS")
    available = tuple(sorted(tuple(services), key=lambda item: item.service.semantic_identity))
    current = transition(root, current_candidate)
    if current.status is not TransitionStatus.SUPPORTED:
        reason = "BRANCH_FRONTIER_EXCEEDED" if current.reason == "BRANCH_CEILING_EXCEEDED" else f"CURRENT_CANDIDATE_{current.reason}"
        return ContinuationProof(TransitionStatus.UNKNOWN if current.reason == "BRANCH_CEILING_EXCEEDED" else current.status, reason, max_active_paths=len(current.successors))
    max_paths = len(current.successors)
    branch_witnesses: list[tuple[str, str]] = []
    unknown_reasons: set[str] = set()
    order_witnesses: set[str] = set()
    frontier = [max_paths]
    for index, branch in enumerate(current.successors):
        status, witnesses, reason = _enumerate_witnesses(
            branch,
            frozenset(required),
            frozenset(),
            0,
            max(1, len(current.successors)),
            available,
            max_depth,
            frontier,
            order_witnesses,
            unknown_reasons,
        )
        key = _branch_key(index, branch)
        if status is TransitionStatus.SUPPORTED:
            branch_witnesses.append((key, min(witnesses)))
        elif status is TransitionStatus.UNKNOWN:
            unknown_reasons.add(reason)
            return ContinuationProof(TransitionStatus.UNKNOWN, "BRANCH_CONTINUATION_UNKNOWN", tuple(branch_witnesses), frontier[0], tuple(sorted(unknown_reasons)))
        else:
            return ContinuationProof(TransitionStatus.UNSUPPORTED, "BRANCH_HAS_NO_SUPPORTED_CONTINUATION", tuple(branch_witnesses), frontier[0], tuple(sorted(unknown_reasons)))
    return ContinuationProof(TransitionStatus.SUPPORTED, "ROBUST_BOUNDED_CONTINUATION_SUPPORTED", tuple(branch_witnesses), frontier[0], tuple(sorted(unknown_reasons)))


def root_continuation_set(
    root: HypotheticalState,
    services: Iterable[SourceBackedRegulatoryService],
    *,
    obligations: Iterable[str],
    max_depth: int = MAX_CONTINUATION_DEPTH,
) -> ContinuationSet:
    """Construct O0 before candidate evaluation from root evidence only."""
    required = tuple(sorted({str(owner) for owner in obligations}))
    available = tuple(sorted(tuple(services), key=lambda item: item.service.semantic_identity))
    mapping: dict[str, set[str]] = {}
    for index, branch in enumerate(root.physiology_branches):
        branch_state = HypotheticalState(
            root_tick=root.root_tick,
            elapsed_time=root.elapsed_time,
            physiology_branches=(branch,),
            body_schema_identity=root.body_schema_identity,
            opportunities=root.opportunities,
            routes=root.routes,
            pending_commitment=root.pending_commitment,
            provenance=root.provenance,
            dependencies=root.dependencies,
            depth=root.depth,
        )
        witnesses: set[str] = set()
        _status, witnesses, _reason = _enumerate_witnesses(
            branch_state,
            frozenset(required),
            frozenset(),
            0,
            1,
            available,
            max_depth,
            [1],
            set(),
            set(),
        )
        if witnesses:
            mapping[_branch_key(index, branch)] = witnesses
    return ContinuationSet.from_mapping(mapping)


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
