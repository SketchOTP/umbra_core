"""Engineering characterization only; does not replay a consumed organism.

These tests preserve a discovered limitation, not acceptance of that limitation.
"""
from tests.test_as018_recovery_reachability import _envelope, _observation, _phys


def test_advertised_route_budget_is_not_an_enforced_route_horizon():
    inputs = dict(active_needs=["energy"], physiology=_phys(energy=.29),
                  observations=[_observation(support_center_dx=35.,
                                             distance_support_upper_bound=35.1)])
    one = _envelope(**inputs, max_route_steps=1)
    default = _envelope(**inputs)
    assert one["search_budget"]["max_route_steps"] == 1
    assert one["status"] == "BOUNDED_RECOVERY_OPPORTUNITY"
    assert default["status"] == one["status"]
    assert one["route_evidence"][0]["required_movement_executions"] == 34
    assert default["route_evidence"] == one["route_evidence"]
