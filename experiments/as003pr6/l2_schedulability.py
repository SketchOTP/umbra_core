"""Bounded, non-scalar L2 regulatory schedulability research relation.

This module is intentionally independent of ``umbra_core``.  It evaluates
immutable literal evidence records only and has no runtime, persistence,
learning, RNG, or action-selection authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import permutations
from typing import Iterable, Mapping, Sequence


OWNERS = ("energy", "fatigue", "integrity", "stimulation")
MAX_DEPTH = 5
MAX_ACTIVE_PATHS = 32


class Modality(str, Enum):
    MUST = "MUST"
    MAY = "MAY"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"


class ScheduleClass(str, Enum):
    COMPLETE_MUST = "COMPLETE_MUST_SCHEDULE"
    COMPLETE_MAY = "COMPLETE_MAY_SCHEDULE"
    UNKNOWN = "SCHEDULE_UNKNOWN"
    NONE = "NO_COMPLETE_SCHEDULE"


@dataclass(frozen=True)
class RegulatoryObligation:
    owner: str
    originating_state: float
    deadline: int | None
    deadline_provenance: tuple[str, ...]
    acceptable_capabilities: tuple[str, ...]
    required_effect_direction: int
    source_dependencies: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.owner not in OWNERS:
            raise ValueError("unknown regulatory owner")
        if self.deadline is not None and self.deadline < 0:
            raise ValueError("negative obligation deadline")
        if self.required_effect_direction not in {-1, 1}:
            raise ValueError("effect direction must be -1 or 1")


@dataclass(frozen=True)
class RegulatoryServiceEnvelope:
    identity: str
    capability: str
    owner_coverage: tuple[str, ...]
    opportunity_identity: str
    capability_modality: Modality
    opportunity_modality: Modality
    opportunity_valid_through: int | None
    route_modality: Modality
    route_demand: int | None
    completion_demand: int | None
    effect_branches: tuple[tuple[tuple[str, float], ...], ...]
    provenance: tuple[str, ...]

    @property
    def requirement_modality(self) -> Modality:
        requirements = (
            self.capability_modality,
            self.opportunity_modality,
            self.route_modality,
        )
        if Modality.UNSUPPORTED in requirements:
            return Modality.UNSUPPORTED
        if (
            Modality.UNKNOWN in requirements
            or self.opportunity_valid_through is None
            or self.route_demand is None
            or self.completion_demand is None
        ):
            return Modality.UNKNOWN
        if Modality.MAY in requirements:
            return Modality.MAY
        return Modality.MUST

    @property
    def total_demand(self) -> int | None:
        if self.route_demand is None or self.completion_demand is None:
            return None
        # One terminal action is part of the AS-003L service-demand contract.
        return self.route_demand + self.completion_demand + 1

    def effect_maps(self) -> tuple[dict[str, float], ...]:
        return tuple(dict(branch) for branch in self.effect_branches)


@dataclass(frozen=True)
class CandidateBranch:
    physiology: tuple[tuple[str, float], ...]
    elapsed: int = 0
    supported: bool = True
    hard_violation: bool = False

    def state(self) -> dict[str, float]:
        return dict(self.physiology)


@dataclass(frozen=True)
class BranchScheduleResult:
    classification: ScheduleClass
    complete_sequences: tuple[tuple[str, ...], ...]
    permutations_evaluated: int
    maximum_active_paths: int
    reason: str


@dataclass(frozen=True)
class CandidateScheduleResult:
    branches: tuple[BranchScheduleResult, ...]

    @property
    def complete_on_every_branch(self) -> bool:
        return bool(self.branches) and all(
            branch.classification in {ScheduleClass.COMPLETE_MUST, ScheduleClass.COMPLETE_MAY}
            for branch in self.branches
        )

    @property
    def has_unknown(self) -> bool:
        return any(branch.classification is ScheduleClass.UNKNOWN for branch in self.branches)

    @property
    def has_proven_no_schedule(self) -> bool:
        return any(branch.classification is ScheduleClass.NONE for branch in self.branches)


def _service_corrects(service: RegulatoryServiceEnvelope, obligation: RegulatoryObligation) -> bool:
    if service.capability not in obligation.acceptable_capabilities:
        return False
    if obligation.owner not in service.owner_coverage:
        return False
    effects = service.effect_maps()
    if not effects:
        return False
    return all(
        obligation.required_effect_direction * float(branch.get(obligation.owner, 0.0)) > 0.0
        for branch in effects
    )


def _sequence_result(
    branch: CandidateBranch,
    obligations: Sequence[RegulatoryObligation],
    sequence: Sequence[RegulatoryServiceEnvelope],
) -> tuple[bool, bool, int]:
    """Return (complete, uses_may, active_path_count) conservatively."""
    states = [(branch.state(), int(branch.elapsed), frozenset())]
    uses_may = False
    for service in sequence:
        modality = service.requirement_modality
        if modality in {Modality.UNKNOWN, Modality.UNSUPPORTED}:
            return False, uses_may, len(states)
        uses_may = uses_may or modality is Modality.MAY
        demand = service.total_demand
        assert demand is not None
        next_states: list[tuple[dict[str, float], int, frozenset[str]]] = []
        for state, elapsed, served in states:
            finish = elapsed + demand
            if finish > int(service.opportunity_valid_through):
                continue
            served_now = {
                obligation.owner
                for obligation in obligations
                if _service_corrects(service, obligation)
                and obligation.deadline is not None
                and finish <= obligation.deadline
            }
            for effects in service.effect_maps():
                successor = dict(state)
                for owner, delta in effects.items():
                    if owner in successor:
                        successor[owner] += float(delta)
                next_states.append((successor, finish, served | frozenset(served_now)))
        if not next_states:
            return False, uses_may, len(states)
        if len(next_states) > MAX_ACTIVE_PATHS:
            return False, uses_may, len(next_states)
        states = next_states
    required = {obligation.owner for obligation in obligations}
    return bool(states) and all(served >= required for _, _, served in states), uses_may, len(states)


def evaluate_branch(
    branch: CandidateBranch,
    obligations: Sequence[RegulatoryObligation],
    services: Sequence[RegulatoryServiceEnvelope],
) -> BranchScheduleResult:
    if not branch.supported or branch.hard_violation:
        return BranchScheduleResult(ScheduleClass.NONE, (), 0, 1, "CURRENT_BRANCH_UNSUPPORTED_OR_HARD_VIOLATION")
    if any(obligation.deadline is None for obligation in obligations):
        return BranchScheduleResult(ScheduleClass.UNKNOWN, (), 0, 1, "OBLIGATION_DEADLINE_UNKNOWN")
    if not obligations:
        return BranchScheduleResult(ScheduleClass.COMPLETE_MUST, ((),), 1, 1, "NO_ACTIVE_OBLIGATION")
    relevant = tuple(
        service
        for service in services
        if any(_service_corrects(service, obligation) for obligation in obligations)
    )
    if any(service.requirement_modality is Modality.UNKNOWN for service in relevant):
        # Unknown source facts may conceal a complete schedule, so absence cannot
        # be proven even if some known schedules are explored.
        unknown_present = True
    else:
        unknown_present = False
    if len(relevant) > MAX_DEPTH:
        return BranchScheduleResult(ScheduleClass.UNKNOWN, (), 0, 1, "DEPTH_BOUND_EXCEEDED")
    completed: list[tuple[str, ...]] = []
    completed_must: list[tuple[str, ...]] = []
    permutations_evaluated = 0
    maximum_paths = 1
    known = tuple(s for s in relevant if s.requirement_modality in {Modality.MUST, Modality.MAY})
    for length in range(1, len(known) + 1):
        for order in permutations(known, length):
            permutations_evaluated += 1
            complete, uses_may, active_paths = _sequence_result(branch, obligations, order)
            maximum_paths = max(maximum_paths, active_paths)
            if active_paths > MAX_ACTIVE_PATHS:
                return BranchScheduleResult(ScheduleClass.UNKNOWN, (), permutations_evaluated, active_paths, "BRANCH_BOUND_EXCEEDED")
            if complete:
                identity = tuple(service.identity for service in order)
                completed.append(identity)
                if not uses_may:
                    completed_must.append(identity)
    if completed_must:
        return BranchScheduleResult(ScheduleClass.COMPLETE_MUST, tuple(sorted(completed)), permutations_evaluated, maximum_paths, "ROBUST_COMPLETE_MUST_SCHEDULE_EXISTS")
    if completed:
        return BranchScheduleResult(ScheduleClass.COMPLETE_MAY, tuple(sorted(completed)), permutations_evaluated, maximum_paths, "ROBUST_COMPLETE_MAY_SCHEDULE_EXISTS")
    if unknown_present:
        return BranchScheduleResult(ScheduleClass.UNKNOWN, (), permutations_evaluated, maximum_paths, "SOURCE_EVIDENCE_UNKNOWN")
    return BranchScheduleResult(ScheduleClass.NONE, (), permutations_evaluated, maximum_paths, "EXHAUSTIVE_KNOWN_SEARCH_HAS_NO_COMPLETE_SCHEDULE")


def evaluate_candidate(
    branches: Iterable[CandidateBranch],
    obligations_by_branch: Sequence[Sequence[RegulatoryObligation]],
    services: Sequence[RegulatoryServiceEnvelope],
) -> CandidateScheduleResult:
    material = tuple(branches)
    if len(material) != len(obligations_by_branch):
        raise ValueError("branch/obligation mismatch")
    return CandidateScheduleResult(
        tuple(
            evaluate_branch(branch, tuple(obligations), tuple(services))
            for branch, obligations in zip(material, obligations_by_branch, strict=True)
        )
    )


def l2_precedes(a: CandidateScheduleResult, b: CandidateScheduleResult) -> bool:
    """Only a one-way loss of full schedulability can establish precedence."""
    return (
        a.complete_on_every_branch
        and not a.has_unknown
        and b.has_proven_no_schedule
        and not b.has_unknown
    )


def effect_branch(values: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted((str(owner), float(delta)) for owner, delta in values.items()))

