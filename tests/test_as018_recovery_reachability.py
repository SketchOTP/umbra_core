from __future__ import annotations

import copy

import pytest

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.recoverability.contracts import EXECUTABLE
from umbra_core.physiology import Physiology, project_verified_transition, verified_outcome_effect_branches
from umbra_core.recoverability import (
    BOUNDED_RECOVERY_OPPORTUNITY,
    MAY_ROUTE,
    ROBUST_NOW,
    UNKNOWN_ROUTE,
    assess_recovery_reachability_envelope,
    filter_recovery_reserve_candidates,
)
from umbra_core.util import SeededRNG


def _interval(minimum: float, maximum: float, semantics: str = "VERIFIED_OBSERVED_SUPPORT") -> dict:
    return {
        "minimum": minimum,
        "maximum": maximum,
        "semantics": semantics,
        "evidence_count": 3,
        "provenance": ["test:as018"],
    }


def _support(progress=(1.0, 1.0), completion=(0.0, 0.0), semantics="VERIFIED_OBSERVED_SUPPORT"):
    return {
        "body_schema_id": "body-1",
        "progress": _interval(*progress, semantics),
        "completion": _interval(*completion, semantics),
    }


def _supports(**overrides):
    result = {name: _support() for name in ("MOVE", "APPROACH", "RETREAT")}
    result.update(overrides)
    return result


def _phys(**updates):
    state = {"energy": 0.70, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55}
    state.update(updates)
    return state


def _observation(kind="resource", **updates):
    row = {
        "kind": kind,
        "fact_kind": "CURRENT_OBSERVATION",
        "source": "world_model_policy",
        "support_center_dx": 0.5,
        "support_center_dy": 0.0,
        "support_radius": 0.1,
        "support_provenance": "sensor:bounded_body_region",
        "support_source_kind": "CURRENT_OBSERVATION",
        "support_semantics": "VERIFIED_OBSERVED_SUPPORT",
        "support_body_schema_id": "body-1",
        "relative_direction": 0.0,
        "estimated_distance": 0.5,
        "distance_support_upper_bound": 0.6,
    }
    row.update(updates)
    return row


def _envelope(**updates):
    args = {
        "organism_tick": 434,
        "body_schema_id": "body-1",
        "physiology": _phys(energy=0.31, fatigue=0.71),
        "active_needs": ["energy", "fatigue"],
        "observations": [_observation(kind="resource", support_center_dx=0.8, distance_support_upper_bound=0.9)],
        "candidate": {"capability": "IDLE", "params": {}},
        "authority_effect_branches": verified_outcome_effect_branches("IDLE"),
        "capability_support": _supports(),
    }
    args.update(updates)
    return assess_recovery_reachability_envelope(**args)


def test_close_policy_visible_opportunity_is_bounded_not_robust_now() -> None:
    result = _envelope(active_needs=["energy"], physiology=_phys(energy=0.31))
    assert result["status"] == BOUNDED_RECOVERY_OPPORTUNITY
    assert result["robust_now"] is False
    assert result["hidden_truth_fields"] == 0


def test_distant_opportunity_with_insufficient_reserve_remains_may_route() -> None:
    result = _envelope(
        active_needs=["energy"],
        physiology=_phys(energy=0.06),
        observations=[_observation(support_center_dx=20.0, distance_support_upper_bound=21.0)],
    )
    assert result["status"] == MAY_ROUTE
    assert result["bounded_opportunity_count"] == 0


def test_unknown_progress_and_missing_policy_source_are_unknown() -> None:
    unknown_progress = _envelope(
        active_needs=["energy"],
        capability_support=_supports(APPROACH=_support(progress=(0.0, 0.0), semantics="UNKNOWN")),
    )
    assert unknown_progress["status"] == UNKNOWN_ROUTE

    hidden_only = _observation()
    for key in ("support_center_dx", "support_center_dy", "support_radius", "distance_support_upper_bound"):
        hidden_only.pop(key, None)
    no_source = _envelope(active_needs=["energy"], observations=[hidden_only])
    assert no_source["status"] == UNKNOWN_ROUTE


def test_interacting_need_without_a_route_cannot_be_hidden_by_another_route() -> None:
    result = _envelope(active_needs=["energy", "stimulation"])
    assert result["status"] == UNKNOWN_ROUTE
    assert result["active_need_status"]["stimulation"] == UNKNOWN_ROUTE


def test_effect_then_drift_clamp_is_the_owner_transition() -> None:
    state = {"energy": 0.70, "fatigue": 0.01, "integrity": 0.90, "stimulation": 0.55}
    expected = project_verified_transition(
        dict(state), {"fatigue": -0.08}, capability="REST", drift_enabled=True
    )
    assert expected["fatigue"] == pytest.approx(0.002)


def test_envelope_projects_all_four_dimensions_with_delayed_timing() -> None:
    result = _envelope(
        active_needs=["energy", "fatigue", "integrity", "stimulation"],
        candidate={"capability": "APPROACH", "params": {"heading_delta": 0.0}},
        authority_effect_branches=verified_outcome_effect_branches("APPROACH"),
        capability_support=_supports(
            APPROACH=_support(completion=(2.0, 2.0)),
        ),
    )
    assert set(result["post_candidate_physiology"]) == {
        "energy", "fatigue", "integrity", "stimulation"
    }
    assert all("post_route_physiology" in route for route in result["route_evidence"])
    assert all(route["drift_intervals_per_execution"] == 2 for route in result["route_evidence"])


def test_saturation_projection_clamps_effect_and_drift_separately() -> None:
    state = {"energy": 0.70, "fatigue": 0.20, "integrity": 0.98, "stimulation": 0.55}
    projected = project_verified_transition(
        state, {"integrity": 0.055}, capability="REST", drift_enabled=True
    )
    assert projected["integrity"] == pytest.approx(0.9998)


def test_body_mismatch_and_missing_opportunity_remain_unknown() -> None:
    mismatch = _envelope(
        body_schema_id="body-2",
        capability_support=_supports(),
    )
    assert mismatch["status"] == UNKNOWN_ROUTE
    absent = _envelope(active_needs=["energy"], observations=[])
    assert absent["status"] == UNKNOWN_ROUTE


def test_filter_is_dormant_when_reserve_is_adequate() -> None:
    result = filter_recovery_reserve_candidates(
        organism_tick=1,
        body_schema_id="body-1",
        physiology=_phys(),
        active_needs=["energy"],
        observations=[_observation()],
        capability_support=_supports(),
        candidates=[{"capability": "APPROACH", "params": {"heading_delta": 0.0}}],
        authority_effect_branches_for=lambda candidate: verified_outcome_effect_branches(
            candidate["capability"]
        ),
    )
    assert result["activation"] is False
    assert result["rejected"] == []


def test_candidate_filter_requires_all_reachable_branches_to_preserve_bounded_route() -> None:
    common = {
        "organism_tick": 434,
        "body_schema_id": "body-1",
        "physiology": _phys(energy=0.31),
        "active_needs": ["energy"],
        "observations": [_observation(support_center_dx=0.8, distance_support_upper_bound=0.9)],
        "capability_support": _supports(),
    }
    candidates = [
        {"capability": "APPROACH", "params": {"heading_delta": 0.0}},
        {"capability": "REST", "params": {}},
    ]
    result = filter_recovery_reserve_candidates(
        **common,
        candidates=candidates,
        authority_effect_branches_for=lambda candidate: (
            ({"fatigue": 1.0}, {"fatigue": 1.0})
            if candidate["capability"] == "APPROACH"
            else verified_outcome_effect_branches(candidate["capability"])
        ),
    )
    assert result["activation"] is True
    assert result["rejected"] == ['APPROACH:{"heading_delta":0.0}']
    assert result["candidates"] == [candidates[1]]


def test_filter_is_pure_and_does_not_mutate_inputs() -> None:
    observations = [_observation()]
    support = _supports()
    before = copy.deepcopy((observations, support))
    filter_recovery_reserve_candidates(
        organism_tick=1,
        body_schema_id="body-1",
        physiology=_phys(energy=0.31),
        active_needs=["energy"],
        observations=observations,
        capability_support=support,
        candidates=[{"capability": "IDLE", "params": {}}],
        authority_effect_branches_for=lambda _candidate: verified_outcome_effect_branches("IDLE"),
    )
    assert (observations, support) == before


def test_enabled_envelope_runs_inside_existing_recovery_selection_path() -> None:
    arbiter = Arbitrator()
    arbiter.generate_candidates = lambda *_args: [  # type: ignore[method-assign]
        Candidate("APPROACH", {"heading_delta": 0.0}),
        Candidate("IDLE", {}),
    ]
    selected = arbiter.select(
        Physiology(energy=0.29),
        [_observation(support_center_dx=0.8, distance_support_upper_bound=0.9)],
        tick=434,
        rng=SeededRNG(18018),
        authority_effect_branches=lambda candidate: verified_outcome_effect_branches(candidate.capability),
        candidate_executability=lambda _candidate: EXECUTABLE,
        viability_kernel_enabled=True,
        recovery_reachability_enabled=True,
        recovery_body_schema_id="body-1",
        recovery_capability_support=_supports(),
    )
    assert selected.capability in {"APPROACH", "IDLE", "CHARGE"}
    record = arbiter.state.last_viability_kernel
    assert record is not None
    assert record["recovery_reachability_envelope"]["schema"] == "AS018_RECOVERY_REACHABILITY_FILTER_V1"
    assert record["recovery_reachability_envelope"]["activation"] is True
