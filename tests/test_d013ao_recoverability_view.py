from __future__ import annotations

import copy

import pytest

from umbra_core.physiology import OUTCOME_EFFECTS, Physiology, verified_outcome_effect_branches
from umbra_core.recoverability import (
    RecoverabilityStatus,
    derive_recoverability_view,
    project_support_region,
)
from umbra_core.self_model.engine import SupportSemantics
from umbra_core.world_model.engine import VerifiedMotionDelta, WorldModel


def _interval(minimum: float, maximum: float, semantics: str = "VERIFIED_OBSERVED_SUPPORT") -> dict:
    return {
        "minimum": minimum,
        "maximum": maximum,
        "semantics": semantics,
        "evidence_count": 3,
        "provenance": ["outcome-1"],
    }


def _support(
    *,
    progress: tuple[float, float] = (1.0, 1.0),
    completion: tuple[float, float] = (0.0, 0.0),
    semantics: str = "VERIFIED_OBSERVED_SUPPORT",
) -> dict:
    return {
        "capability": "APPROACH",
        "body_schema_id": "body-1",
        "progress": _interval(*progress, semantics),
        "completion": _interval(*completion, semantics),
    }


def _capability_support(**kwargs) -> dict:
    approach = _support(**kwargs)
    move = {**_support(**kwargs), "capability": "MOVE"}
    retreat = {**_support(**kwargs), "capability": "RETREAT"}
    return {"APPROACH": approach, "MOVE": move, "RETREAT": retreat}


def _phys(**updates) -> dict:
    state = {
        "energy": 0.70,
        "fatigue": 0.20,
        "integrity": 0.90,
        "stimulation": 0.55,
    }
    state.update(updates)
    return state


def _resource(**updates) -> dict:
    row = {
        "kind": "resource",
        "fact_kind": "REMEMBERED_ESTIMATE",
        "source": "world_model_memory",
        "support_center_dx": 2.0,
        "support_center_dy": 0.0,
        "support_radius": 1.0,
        "support_provenance": "sensor:bounded_body_region",
        "support_source_kind": "CURRENT_OBSERVATION",
        "support_semantics": "VERIFIED_OBSERVED_SUPPORT",
        "support_body_schema_id": "body-1",
    }
    row.update(updates)
    return row


def _view(**updates) -> dict:
    args = {
        "organism_tick": 17,
        "body_schema_id": "body-1",
        "physiology": _phys(energy=0.29),
        "active_needs": ["energy"],
        "observations": [_resource()],
        "candidate": {"capability": "IDLE", "params": {}},
        "authority_effect_branches": verified_outcome_effect_branches("IDLE"),
        "capability_support": _capability_support(),
    }
    args.update(updates)
    return derive_recoverability_view(**args)


def test_world_model_exports_existing_policy_safe_support_geometry() -> None:
    wm = WorldModel.create("d013ao", seed=13013)
    wm.ingest_observations(
        [{
            "kind": "resource",
            "relative_direction": 0.0,
            "estimated_distance": 5.0,
            "confidence": 0.9,
            "uncertainty": 0.1,
            "source": "sensor",
            "distance_support_upper_bound": 10.0,
        }],
        tick=1,
        now=1.0,
        body_schema_id="body-1",
    )
    wm.apply_verified_motion(
        VerifiedMotionDelta(
            displacement=1.0,
            body_relative_dx=1.0,
            body_relative_dy=0.0,
            heading_delta=0.0,
            provenance="test:d013ao",
            execution_id="motion-1",
        ),
        tick=2,
    )
    row = wm.policy_observations(observed_kinds=set(), body_schema_id="body-1")[0]
    assert row["support_center_dx"] == pytest.approx(-1.0)
    assert row["support_center_dy"] == pytest.approx(0.0)
    assert row["support_radius"] == pytest.approx(10.0)
    assert row["support_provenance"] == "sensor:bounded_body_region"
    assert row["support_semantics"] == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    assert row["support_body_schema_id"] == "body-1"

    stale = wm.policy_observations(
        observed_kinds=set(), body_schema_id="replacement-body"
    )[0]
    assert stale["support_body_schema_id"] == "body-1"
    stale_view = _view(
        body_schema_id="replacement-body",
        observations=[stale],
    )
    assert (
        stale_view["candidate_projection"]["status"]
        == RecoverabilityStatus.UNKNOWN_ROUTE_GEOMETRY.value
    )


def test_missing_geometry_remains_unknown_even_with_point_estimate_and_confidence() -> None:
    observation = {
        "kind": "resource",
        "estimated_distance": 1.0,
        "relative_direction": 0.0,
        "confidence": 0.999,
        "distance_support_upper_bound": 1.1,
        "fact_kind": "REMEMBERED_ESTIMATE",
        "source": "world_model_memory",
    }
    view = _view(observations=[observation])
    assert view["candidate_projection"]["status"] == RecoverabilityStatus.UNKNOWN_ROUTE_GEOMETRY.value
    assert view["candidate_projection"]["supported_route_count"] == 0


def test_support_set_projection_uses_applied_direction_without_assuming_center_target() -> None:
    toward = project_support_region(
        center_dx=3.0,
        center_dy=0.0,
        radius=1.0,
        heading_delta=0.0,
        progress_values=[1.0],
    )
    away = project_support_region(
        center_dx=3.0,
        center_dy=0.0,
        radius=1.0,
        heading_delta=3.141592653589793,
        progress_values=[1.0],
    )
    assert toward["distance_support_upper_bound"] == pytest.approx(3.0)
    assert away["distance_support_upper_bound"] == pytest.approx(5.0)


def test_observed_capability_support_never_becomes_hard_authority() -> None:
    view = _view()
    projection = view["candidate_projection"]
    assert projection["status"] == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    assert projection["overall_semantics"] == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    assert view["action_authority"] is False
    assert view["persisted_state"] is False
    assert view["rollout_required"] is False


def test_stale_remembered_opportunity_remains_empirical_not_hidden_truth() -> None:
    view = _view(
        observations=[
            _resource(
                support_source_kind="REMEMBERED_OBSERVATION",
                source="world_model_memory",
                fact_kind="REMEMBERED_ESTIMATE",
            )
        ]
    )
    projection = view["candidate_projection"]
    assert projection["status"] == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    assert projection["overall_semantics"] == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    assert view["hidden_truth_fields"] == 0
    assert view["action_authority"] is False


def test_motion_support_and_stationary_retention_keep_their_distinct_semantics() -> None:
    moving = _view(
        candidate={"capability": "MOVE", "params": {"heading_delta": 0.0}},
        authority_effect_branches=verified_outcome_effect_branches("MOVE"),
    )
    stationary = _view()
    assert moving["candidate_projection"]["candidate_motion_support"]["maximum"] == 1.0
    assert (
        moving["candidate_projection"]["candidate_motion_support"]["semantics"]
        == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    )
    assert stationary["candidate_projection"]["candidate_motion_support"] == {
        "minimum": 0.0,
        "maximum": 0.0,
        "semantics": SupportSemantics.HARD_CONTRACT.value,
        "evidence_count": 0,
        "provenance": ["contract:stationary_capability"],
    }


def test_probabilistic_route_support_is_unsupported_for_authority() -> None:
    view = _view(
        capability_support=_capability_support(
            semantics=SupportSemantics.PROBABILISTIC_SUPPORT.value
        )
    )
    assert view["candidate_projection"]["status"] == RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value
    assert view["candidate_projection"]["overall_semantics"] == SupportSemantics.PROBABILISTIC_SUPPORT.value


def test_body_schema_mismatch_cannot_reuse_empirical_support() -> None:
    view = _view(
        body_schema_id="replacement-body",
        observations=[_resource(support_body_schema_id="replacement-body")],
    )
    assert (
        view["candidate_projection"]["status"]
        == RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value
    )
    assert (
        view["candidate_projection"]["overall_semantics"]
        == SupportSemantics.UNKNOWN.value
    )
    stale_geometry = _view(
        observations=[_resource(support_body_schema_id="retired-body")]
    )
    assert (
        stale_geometry["candidate_projection"]["status"]
        == RecoverabilityStatus.UNKNOWN_ROUTE_GEOMETRY.value
    )


def test_closed_form_immediate_and_delayed_timing_matches_runtime_order() -> None:
    immediate = _view()
    immediate_post = immediate["candidate_projection"]["post_candidate_physiology"]
    immediate_oracle = Physiology.from_state(_phys(energy=0.29))
    immediate_oracle.apply_outcome_effects(OUTCOME_EFFECTS["IDLE"])
    immediate_oracle.tick_drift()
    assert immediate_post["energy"] == pytest.approx(immediate_oracle.energy)
    assert immediate_post["fatigue"] == pytest.approx(immediate_oracle.fatigue)

    delayed = _view(
        capability_support=_capability_support(completion=(2.0, 2.0)),
    )
    route = delayed["candidate_projection"]["post_candidate_routes"][0]
    assert route["required_movement_executions"] == 2
    assert route["drift_intervals_per_execution"] == 2
    delayed_oracle = Physiology.from_state(immediate_oracle.to_state())
    for _ in range(2):
        delayed_oracle.apply_outcome_effects(OUTCOME_EFFECTS["APPROACH"])
        delayed_oracle.tick_drift()
        delayed_oracle.tick_drift()
    assert route["post_route_physiology"]["energy"] == pytest.approx(delayed_oracle.energy)
    assert route["post_route_physiology"]["fatigue"] == pytest.approx(delayed_oracle.fatigue)

    orient = _view(
        candidate={"capability": "ORIENT", "params": {"heading_delta": 0.25}},
        authority_effect_branches=verified_outcome_effect_branches("ORIENT"),
    )
    assert (
        orient["candidate_projection"]["candidate_completion_lag_support"]["semantics"]
        == SupportSemantics.UNKNOWN.value
    )
    assert (
        orient["candidate_projection"]["status"]
        == RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value
    )


def test_cross_need_bottleneck_can_exhaust_route_even_when_energy_route_exists() -> None:
    view = _view(
        physiology=_phys(energy=0.30, fatigue=0.94),
        observations=[_resource(support_center_dx=3.0, support_radius=1.0)],
    )
    route = view["candidate_projection"]["post_candidate_routes"][0]
    assert route["status"] == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
    assert route["bottleneck_variable"] == "fatigue"


def test_multi_need_aggregate_does_not_hide_an_unknown_route() -> None:
    unknown_inspect = _resource(kind="inspect")
    unknown_inspect.pop("support_center_dx")
    view = _view(
        active_needs=["energy", "stimulation"],
        observations=[_resource(), unknown_inspect],
    )
    assert view["candidate_projection"]["supported_route_count"] == 1
    assert view["candidate_projection"]["unknown_route_count"] == 1
    assert (
        view["candidate_projection"]["status"]
        == RecoverabilityStatus.UNKNOWN_ROUTE_GEOMETRY.value
    )


def test_energy_cost_scale_is_included_in_route_burden() -> None:
    nominal = _view(body_energy_cost_scale=1.0)
    scaled = _view(body_energy_cost_scale=2.0)
    nominal_energy = nominal["candidate_projection"]["post_candidate_routes"][0][
        "post_route_physiology"
    ]["energy"]
    scaled_energy = scaled["candidate_projection"]["post_candidate_routes"][0][
        "post_route_physiology"
    ]["energy"]
    assert scaled_energy < nominal_energy


def test_terminal_recovery_effect_and_next_decision_drift_are_projected() -> None:
    route = _view()["candidate_projection"]["post_candidate_routes"][0]
    assert route["terminal_capability"] == "CHARGE"
    assert route["terminal_effect_branches"]
    assert route["terminal_drift_intervals"] == 1
    assert route["post_terminal_physiology"] != route["post_route_physiology"]


def test_no_known_opportunity_and_pending_commitment_remain_distinct() -> None:
    no_route = _view(observations=[])
    assert no_route["known_recovery_opportunity_count"] == 0
    assert no_route["candidate_projection"]["status"] == RecoverabilityStatus.NO_KNOWN_RECOVERY_ROUTE.value
    pending = _view(pending_commitment=True)
    assert pending["known_recovery_opportunity_count"] == 1
    assert pending["candidate_projection"]["status"] == RecoverabilityStatus.PENDING_COMMITMENT.value
    assert pending["candidate_projection"]["fresh_action_recoverability"] == SupportSemantics.NOT_APPLICABLE.value


def test_derivation_is_pure_fixed_size_and_restart_recomputable() -> None:
    physiology = _phys(energy=0.29)
    observations = [_resource()]
    support = _capability_support()
    before = copy.deepcopy((physiology, observations, support))
    first = _view(
        physiology=physiology,
        observations=observations,
        capability_support=support,
    )
    second = _view(
        physiology=copy.deepcopy(physiology),
        observations=copy.deepcopy(observations),
        capability_support=copy.deepcopy(support),
    )
    assert first == second
    assert (physiology, observations, support) == before
    assert first["fixed_size"] is True
    assert first["hidden_truth_fields"] == 0

    duplicated = _view(
        active_needs=["energy"] * 100,
        observations=[_resource(support_center_dx=2.0 + index / 100.0) for index in range(100)],
        candidate={"capability": "IDLE", "params": {"ignored": "x" * 10000}},
    )
    assert duplicated["active_needs"] == ["energy"]
    assert len(duplicated["candidate_projection"]["post_candidate_routes"]) == 1
    assert duplicated["candidate_projection"]["params"] == {}

    oversized = _view(
        body_schema_id="b" * 1000,
        observations=[
            _resource(
                support_body_schema_id="b" * 1000,
                support_provenance="p" * 1000,
                support_source_kind="s" * 1000,
                fact_kind="f" * 1000,
            )
        ],
    )
    route = oversized["candidate_projection"]["post_candidate_routes"][0]
    assert len(oversized["body_schema_id"]) == 160
    assert len(route["opportunity_provenance"]) == 160
    assert len(route["opportunity_fact_kind"]) == 160

    untrusted_text = _view(
        candidate={"capability": "C" * 1000, "params": {}},
        capability_support={
            "IDLE": {
                "body_schema_id": "body-1",
                "progress": _interval(0.0, 0.0, "X" * 1000),
            }
        },
        observations=[_resource(support_semantics="X" * 1000)],
    )
    assert len(untrusted_text["candidate_projection"]["capability"]) == 160
    assert (
        untrusted_text["candidate_projection"]["overall_semantics"]
        == SupportSemantics.UNKNOWN.value
    )
