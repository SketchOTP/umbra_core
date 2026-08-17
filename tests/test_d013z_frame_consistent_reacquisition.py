from __future__ import annotations

import math

import pytest

from umbra_core.arbitration import Arbitrator
from umbra_core.physiology import Physiology
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.util import SeededRNG
from umbra_core.world_model import VerifiedMotionDelta, WorldModel


def _wm_with_resource() -> WorldModel:
    wm = WorldModel.create("d013z", seed=13013)
    wm.ingest_observations([{
        "kind": "resource",
        "relative_direction": 0.0,
        "estimated_distance": 5.0,
        "confidence": 0.9,
        "uncertainty": 0.1,
        "source": "sensor",
        "distance_support_upper_bound": 10.0,
    }], tick=1, now=1.0)
    return wm


def _motion(*, dx=0.0, dy=0.0, heading=0.0) -> VerifiedMotionDelta:
    return VerifiedMotionDelta(
        displacement=math.hypot(dx, dy),
        body_relative_dx=dx,
        body_relative_dy=dy,
        heading_delta=heading,
        provenance="test:d013z",
        execution_id=f"exec-{dx}-{dy}-{heading}",
    )


def test_pure_orient_rotates_bearing_without_changing_radius():
    wm = _wm_with_resource()
    wm.apply_verified_motion(_motion(heading=math.pi / 2), tick=2)
    entity = next(iter(wm.entities.values()))
    assert entity.estimated_state["relative_direction"] == pytest.approx(-math.pi / 2)
    assert entity.estimated_state["estimated_distance"] == pytest.approx(5.0)


def test_translation_support_region_does_not_accumulate_path_length():
    wm = _wm_with_resource()
    wm.apply_verified_motion(_motion(dx=1.0), tick=2)
    entity = next(iter(wm.entities.values()))
    assert entity.support_radius == pytest.approx(10.0)
    assert entity.distance_support_upper_bound == pytest.approx(11.0)
    wm.apply_verified_motion(_motion(dx=-1.0), tick=3)
    assert entity.distance_support_upper_bound == pytest.approx(10.0)


def test_combined_transform_is_snapshot_safe():
    wm = _wm_with_resource()
    wm.apply_verified_motion(_motion(dx=1.0, heading=math.pi / 2), tick=2)
    restored = WorldModel.from_state(wm.to_state())
    before = next(iter(wm.entities.values()))
    after = next(iter(restored.entities.values()))
    assert after.support_center_dx == pytest.approx(before.support_center_dx)
    assert after.support_center_dy == pytest.approx(before.support_center_dy)
    assert after.support_radius == pytest.approx(10.0)


def test_verified_charge_preserves_direct_spatial_estimate():
    wm = _wm_with_resource()
    wm.observe_outcome(
        tick=2,
        action="CHARGE",
        params={"toward": "resource"},
        verified_outcome={"success": True, "verified": True},
        observations=[{
            "kind": "resource",
            "relative_direction": 0.3,
            "estimated_distance": 1.0,
            "confidence": 0.9,
            "uncertainty": 0.1,
            "source": "sensor",
            "distance_support_upper_bound": 10.0,
        }],
        action_issued=True,
        now=2.0,
    )
    entity = next(iter(wm.entities.values()))
    assert entity.estimated_state["estimated_distance"] != 0.0
    assert entity.distance_support_upper_bound != 0.0


def test_reacquisition_homes_before_fallback_sweep():
    choice = Arbitrator().select(
        Physiology(energy=0.20),
        [{
            "kind": "resource",
            "relative_direction": 0.2,
            "estimated_distance": 3.0,
            "confidence": 0.8,
            "uncertainty": 0.2,
            "distance_support_upper_bound": 10.0,
            "fact_kind": "REMEMBERED_ESTIMATE",
            "source": "world_model_memory",
        }],
        10,
        SeededRNG(13013),
    )
    assert choice.capability == "APPROACH"
    assert choice.params["strategy"] == "direct_homing"


def test_orient_does_not_change_omnidirectional_sensor_range(tmp_path):
    org = create_organism(OrganismConfig(
        db_path=str(tmp_path / "d013z-orient.sqlite"),
        seed=13013,
        world_model_enabled=True,
    ))
    before = org.embodiment.body.sensor_range
    org.embodiment.execute_primitive("ORIENT", {"heading": 1.0}, org.rng)
    assert org.embodiment.body.sensor_range == before
    org.close()
