"""Budget regression; original counterexample remains in Git/evidence."""
import pytest
from tests.test_as018_recovery_reachability import _envelope, _observation, _phys
from umbra_core.recoverability import view


def route(steps, **updates):
    # Selection distance 1.5, minimum supported progress 1.0.
    return _envelope(active_needs=["energy"], physiology=_phys(energy=.29),
                     observations=[_observation(support_center_dx=steps + 1.4,
                                               distance_support_upper_bound=steps + 1.5)],
                     **updates)


@pytest.mark.parametrize("steps,cap", [(34, 32), (33, 32), (34, 1)])
def test_complete_over_limit_route_is_unknown_without_projection(monkeypatch, steps, cap):
    original = view._project_branch_states
    def forbidden(*args, **kwargs):
        if kwargs["capability"] == "APPROACH":
            pytest.fail("over-limit route reached physiological projection")
        return original(*args, **kwargs)
    monkeypatch.setattr(view, "_project_branch_states", forbidden)
    result = route(steps, max_route_steps=cap)
    assert result["status"] == "UNKNOWN_ROUTE"
    evidence = result["route_evidence"][0]
    assert evidence["reason"] == "route_step_limit_exceeded"
    assert evidence["required_movement_executions"] == steps
    assert evidence["max_route_steps"] == cap
    assert evidence["recovery_margin"] is None
    assert "post_route_physiology" not in evidence


@pytest.mark.parametrize("steps", [0, 1, 31, 32])
def test_within_limit_route_projects_exact_untruncated_count(monkeypatch, steps):
    original = view._project_branch_states
    calls = []
    def counted(*args, **kwargs):
        if kwargs["capability"] == "APPROACH":
            calls.append(kwargs["executions"])
        return original(*args, **kwargs)
    monkeypatch.setattr(view, "_project_branch_states", counted)
    result = route(steps)
    assert result["status"] == "BOUNDED_RECOVERY_OPPORTUNITY"
    assert calls == [steps]
    assert result["route_evidence"][0]["required_movement_executions"] == steps


def test_invalid_budget_rejected():
    with pytest.raises(ValueError, match="max_route_steps_must_be_positive"):
        route(1, max_route_steps=0)
