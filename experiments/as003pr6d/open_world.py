"""Pure open-world route evidence analysis for AS-003P-R6D.

This module does not import UMBRA runtime code or alter the frozen R6 relation.
It models only the epistemic distinction between known MAY route witnesses and
an unclosed residual possibility space.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import Iterable

from experiments.as003pr6.l2_schedulability import (
    BranchScheduleResult,
    CandidateScheduleResult,
    ScheduleClass,
    l2_precedes,
)


class RouteEvidenceClass(str, Enum):
    KNOWN_MAY_ROUTE_WITNESS = "KNOWN_MAY_ROUTE_WITNESS"
    KNOWN_ROUTE_FAILURE_HISTORY = "KNOWN_ROUTE_FAILURE_HISTORY"
    RESIDUAL_ROUTE_UNKNOWN = "RESIDUAL_ROUTE_UNKNOWN"


@dataclass(frozen=True)
class RouteWitness:
    identity: str
    observed_total_service_demand: int


@dataclass(frozen=True)
class RouteFailure:
    identity: str
    reason: str


@dataclass(frozen=True)
class RoutePossibilitySet:
    opportunity_identity: str
    body_schema_id: str
    terminal_capability: str
    known_successes: tuple[RouteWitness, ...] = ()
    known_failures: tuple[RouteFailure, ...] = ()
    residual_unknown: bool = True

    @property
    def classifications(self) -> tuple[str, ...]:
        values = [RouteEvidenceClass.KNOWN_MAY_ROUTE_WITNESS.value] * len(self.known_successes)
        values.extend(RouteEvidenceClass.KNOWN_ROUTE_FAILURE_HISTORY.value for _ in self.known_failures)
        if self.residual_unknown:
            values.append(RouteEvidenceClass.RESIDUAL_ROUTE_UNKNOWN.value)
        return tuple(values)


def classify_route_possibility(
    possibility: RoutePossibilitySet,
    deadline: int,
    *,
    closed_world_diagnostic: bool = False,
) -> ScheduleClass:
    """Classify existence of a route schedule without treating samples as bounds."""
    if any(witness.observed_total_service_demand <= deadline for witness in possibility.known_successes):
        return ScheduleClass.COMPLETE_MAY
    if possibility.residual_unknown and not closed_world_diagnostic:
        return ScheduleClass.UNKNOWN
    return ScheduleClass.NONE


def branch_for_classification(classification: ScheduleClass, reason: str) -> BranchScheduleResult:
    return BranchScheduleResult(classification, (), 0, 1, reason)


def candidate_for_classification(classification: ScheduleClass, reason: str) -> CandidateScheduleResult:
    return CandidateScheduleResult((branch_for_classification(classification, reason),))


def evaluate_route_pair(
    a_route: RoutePossibilitySet,
    b_route: RoutePossibilitySet,
    *,
    a_deadline: int,
    b_deadline: int,
    closed_world_diagnostic: bool = False,
    b_nonroute_impossible: bool = False,
    b_hard_violation: bool = False,
) -> tuple[CandidateScheduleResult, CandidateScheduleResult, bool]:
    a_class = classify_route_possibility(a_route, a_deadline, closed_world_diagnostic=closed_world_diagnostic)
    if b_hard_violation:
        b_class, b_reason = ScheduleClass.NONE, "CURRENT_BRANCH_UNSUPPORTED_OR_HARD_VIOLATION"
    elif b_nonroute_impossible:
        b_class, b_reason = ScheduleClass.NONE, "NON_ROUTE_KNOWN_IMPOSSIBILITY"
    else:
        b_class = classify_route_possibility(b_route, b_deadline, closed_world_diagnostic=closed_world_diagnostic)
        b_reason = {
            ScheduleClass.COMPLETE_MAY: "KNOWN_MAY_ROUTE_WITNESS",
            ScheduleClass.UNKNOWN: "RESIDUAL_ROUTE_UNKNOWN",
            ScheduleClass.NONE: "CLOSED_WORLD_KNOWN_ROUTE_SEARCH",
        }[b_class]
    a = candidate_for_classification(a_class, "KNOWN_MAY_ROUTE_WITNESS" if a_class is ScheduleClass.COMPLETE_MAY else "RESIDUAL_ROUTE_UNKNOWN")
    b = candidate_for_classification(b_class, b_reason)
    return a, b, l2_precedes(a, b)


def symbolic_configurations() -> Iterable[dict[str, object]]:
    """Yield a finite, deterministic matrix covering the locked dimensions."""
    for obligations, services, opportunity, route_case, open_world, hard, nonroute in product(
        range(1, 5),
        range(1, 5),
        ("MUST", "MAY", "UNKNOWN"),
        ("fits_deadline", "misses_deadline", "absent"),
        (True, False),
        (False, True),
        (False, True),
    ):
        yield {
            "active_obligations": obligations,
            "corrective_services": services,
            "opportunity_modality": opportunity,
            "route_case": route_case,
            "open_world": open_world,
            "hard_violation": hard,
            "nonroute_known_impossibility": nonroute,
        }


def evaluate_symbolic_configuration(config: dict[str, object]) -> dict[str, object]:
    witness = RouteWitness("retained-route", 7)
    a_route = RoutePossibilitySet("A", "body", "CHARGE", (witness,), (), True)
    route_case = str(config["route_case"])
    b_successes = (
        (RouteWitness("fast-route", 4),)
        if route_case == "fits_deadline"
        else (() if route_case == "absent" else (RouteWitness("slow-route", 9),))
    )
    b_route = RoutePossibilitySet("B", "body", "CHARGE", b_successes, (), True)
    a, b, relation = evaluate_route_pair(
        a_route,
        b_route,
        a_deadline=8,
        b_deadline=5,
        closed_world_diagnostic=not bool(config["open_world"]),
        b_nonroute_impossible=bool(config["nonroute_known_impossibility"]),
        b_hard_violation=bool(config["hard_violation"]),
    )
    if relation and bool(config["hard_violation"]):
        cause = "PREEMPTED_BY_HARD_AUTHORITY"
    elif relation and bool(config["nonroute_known_impossibility"]):
        cause = "NONROUTE_CAUSAL"
    elif relation:
        cause = "ROUTE_CAUSAL_CLOSED_WORLD_DIAGNOSTIC"
    else:
        cause = "NONE"
    return {
        **config,
        "a_class": a.branches[0].classification.value,
        "b_class": b.branches[0].classification.value,
        "l2_precedes": relation,
        "causal_source": cause,
    }
