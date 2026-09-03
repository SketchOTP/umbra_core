from __future__ import annotations

from experiments.as003pr6.l2_schedulability import ScheduleClass
from experiments.as003pr6d.open_world import (
    RouteFailure,
    RoutePossibilitySet,
    RouteWitness,
    classify_route_possibility,
    evaluate_route_pair,
    evaluate_symbolic_configuration,
    symbolic_configurations,
)


def possibility(*demands: int, residual: bool = True, failures: int = 0) -> RoutePossibilitySet:
    return RoutePossibilitySet(
        "opportunity",
        "body",
        "CHARGE",
        tuple(RouteWitness(f"success-{index}", demand) for index, demand in enumerate(demands)),
        tuple(RouteFailure(f"failure-{index}", "movement_slip") for index in range(failures)),
        residual,
    )


def test_fitting_may_witness_establishes_possible_completion() -> None:
    assert classify_route_possibility(possibility(7), 8) is ScheduleClass.COMPLETE_MAY


def test_missed_witness_remains_unknown_in_open_world() -> None:
    assert classify_route_possibility(possibility(7), 5) is ScheduleClass.UNKNOWN


def test_closed_world_missed_witness_is_diagnostic_only_none() -> None:
    assert classify_route_possibility(possibility(7), 5, closed_world_diagnostic=True) is ScheduleClass.NONE


def test_observed_minimum_does_not_close_route_space() -> None:
    assert classify_route_possibility(possibility(7, 9, 6), 5) is ScheduleClass.UNKNOWN


def test_repeated_witness_does_not_close_route_space() -> None:
    assert classify_route_possibility(possibility(7, 7, 7), 5) is ScheduleClass.UNKNOWN


def test_failure_history_does_not_cancel_success_or_prove_universal_failure() -> None:
    route = possibility(7, residual=True, failures=1)
    assert classify_route_possibility(route, 8) is ScheduleClass.COMPLETE_MAY
    assert classify_route_possibility(route, 5) is ScheduleClass.UNKNOWN


def test_open_world_blocks_l2_where_closed_world_only_diagnostic_would_fire() -> None:
    a_route = possibility(7)
    b_route = possibility(7)
    _, _, closed_relation = evaluate_route_pair(
        a_route, b_route, a_deadline=8, b_deadline=5, closed_world_diagnostic=True
    )
    _, _, open_relation = evaluate_route_pair(
        a_route, b_route, a_deadline=8, b_deadline=5, closed_world_diagnostic=False
    )
    assert closed_relation is True
    assert open_relation is False


def test_nonroute_and_hard_cases_are_not_route_causal() -> None:
    a_route = possibility(7)
    b_route = possibility(7)
    _, _, nonroute_relation = evaluate_route_pair(
        a_route, b_route, a_deadline=8, b_deadline=8, b_nonroute_impossible=True
    )
    _, _, hard_relation = evaluate_route_pair(
        a_route, b_route, a_deadline=8, b_deadline=8, b_hard_violation=True
    )
    assert nonroute_relation is True
    assert hard_relation is True


def test_symbolic_matrix_is_finite_and_deterministic() -> None:
    first = [evaluate_symbolic_configuration(config) for config in symbolic_configurations()]
    second = [evaluate_symbolic_configuration(config) for config in symbolic_configurations()]
    assert len(first) == 1152
    assert first == second
    assert any(row["l2_precedes"] for row in first)
    assert any(row["causal_source"] == "ROUTE_CAUSAL_CLOSED_WORLD_DIAGNOSTIC" for row in first)
    assert any(row["causal_source"] == "PREEMPTED_BY_HARD_AUTHORITY" for row in first)
