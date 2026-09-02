"""Pure R6A source-contract tests; no organism/runtime imports or creation."""

from experiments.as003pr6a.source_contract import (
    RouteDisposition,
    Strength,
    TimingDisposition,
    derive_route_demand,
    inspect_opportunity,
    source_weakening_never_strengthens,
    terminal_timing,
)


def test_hard_geometry_and_hard_motion_can_bound_demand():
    result = derive_route_demand(
        distance_upper_bound=10,
        progress_minimum=2,
        distance_semantics=Strength.HARD_CONTRACT,
        progress_semantics=Strength.HARD_CONTRACT,
        body_schema_matches=True,
        route_geometry_established=True,
    )
    assert result.disposition is RouteDisposition.SUPPORTED_HARD_BOUND
    assert result.minimum_executions == result.maximum_executions == 5


def test_observed_progress_never_becomes_hard_future_bound():
    result = derive_route_demand(
        distance_upper_bound=10,
        progress_minimum=2,
        distance_semantics=Strength.VERIFIED_OBSERVED_SUPPORT,
        progress_semantics=Strength.VERIFIED_OBSERVED_SUPPORT,
        body_schema_matches=True,
        route_geometry_established=True,
    )
    assert result.disposition is RouteDisposition.MAY_ROUTE_ENVELOPE
    assert result.minimum_executions is None


def test_radial_support_without_route_geometry_is_unknown():
    result = derive_route_demand(
        distance_upper_bound=10,
        progress_minimum=2,
        distance_semantics=Strength.VERIFIED_OBSERVED_SUPPORT,
        progress_semantics=Strength.HARD_CONTRACT,
        body_schema_matches=True,
        route_geometry_established=False,
    )
    assert result.disposition is RouteDisposition.UNKNOWN_ROUTE_DEMAND


def test_bad_progress_and_schema_are_conservative():
    for progress in (None, 0, -1):
        result = derive_route_demand(
            distance_upper_bound=10,
            progress_minimum=progress,
            distance_semantics=Strength.HARD_CONTRACT,
            progress_semantics=Strength.HARD_CONTRACT,
            body_schema_matches=True,
            route_geometry_established=True,
        )
        assert result.disposition is RouteDisposition.UNKNOWN_ROUTE_DEMAND
    mismatch = derive_route_demand(
        distance_upper_bound=10, progress_minimum=2,
        distance_semantics=Strength.HARD_CONTRACT,
        progress_semantics=Strength.HARD_CONTRACT,
        body_schema_matches=False, route_geometry_established=True,
    )
    assert mismatch.disposition is RouteDisposition.UNKNOWN_ROUTE_DEMAND


def test_remembered_and_blocked_routes_do_not_gain_guarantees():
    remembered = derive_route_demand(
        distance_upper_bound=10, progress_minimum=2,
        distance_semantics=Strength.VERIFIED_OBSERVED_SUPPORT,
        progress_semantics=Strength.HARD_CONTRACT,
        body_schema_matches=True, route_geometry_established=True,
        remembered_opportunity=True,
    )
    blocked = derive_route_demand(
        distance_upper_bound=10, progress_minimum=2,
        distance_semantics=Strength.HARD_CONTRACT,
        progress_semantics=Strength.HARD_CONTRACT,
        body_schema_matches=True, route_geometry_established=True,
        route_blocked=True,
    )
    assert remembered.disposition is RouteDisposition.UNKNOWN_ROUTE_DEMAND
    assert blocked.disposition is RouteDisposition.UNKNOWN_ROUTE_DEMAND


def test_inspect_requires_instance_and_active_affordance():
    supported = inspect_opportunity(
        instance_id="i1", entity_kind="inspect", affordance_action="inspect",
        affordance_status="ACTIVE", affordance_strength=Strength.VERIFIED_OBSERVED_SUPPORT,
        body_schema_matches=True,
    )
    kind_only = inspect_opportunity(
        instance_id=None, entity_kind="inspect", affordance_action="inspect",
        affordance_status="ACTIVE", affordance_strength=Strength.HARD_CONTRACT,
        body_schema_matches=True,
    )
    weakened = inspect_opportunity(
        instance_id="i1", entity_kind="inspect", affordance_action="inspect",
        affordance_status="WEAKENED", affordance_strength=Strength.VERIFIED_OBSERVED_SUPPORT,
        body_schema_matches=True,
    )
    assert supported.status == "SUPPORTED" and supported.instance_id == "i1"
    assert kind_only.status == "UNKNOWN"
    assert weakened.status == "UNKNOWN"


def test_inspect_schema_and_action_gaps_are_not_supported():
    assert inspect_opportunity(
        instance_id="i1", entity_kind="inspect", affordance_action="inspect",
        affordance_status="ACTIVE", affordance_strength=Strength.HARD_CONTRACT,
        body_schema_matches=False,
    ).status == "UNKNOWN"
    assert inspect_opportunity(
        instance_id="i1", entity_kind="resource", affordance_action=None,
        affordance_status=None, affordance_strength=Strength.UNKNOWN,
        body_schema_matches=True,
    ).status == "NOT_APPLICABLE"


def test_timing_requires_explicit_source():
    assert terminal_timing("REST").disposition is TimingDisposition.UNKNOWN
    assert terminal_timing("REST", explicit_contract_ticks=1).disposition is TimingDisposition.ONE_TICK_HARD_CONTRACT
    assert terminal_timing("REST", learned_interval=(1, 2)).disposition is TimingDisposition.SOURCE_BACKED_INTERVAL


def test_source_weakening_is_monotone():
    assert source_weakening_never_strengthens(
        {"semantics": "VERIFIED_OBSERVED_SUPPORT"}, {"semantics": "UNKNOWN"}
    )
    assert not source_weakening_never_strengthens(
        {"semantics": "UNKNOWN"}, {"semantics": "HARD_CONTRACT"}
    )


def test_source_contract_is_permutation_invariant():
    kwargs = dict(
        distance_upper_bound=4, progress_minimum=1,
        distance_semantics=Strength.VERIFIED_OBSERVED_SUPPORT,
        progress_semantics=Strength.VERIFIED_OBSERVED_SUPPORT,
        body_schema_matches=True, route_geometry_established=False,
    )
    assert derive_route_demand(**kwargs) == derive_route_demand(**dict(reversed(list(kwargs.items()))))
