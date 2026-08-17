"""D-013V bounded observation-support and verified-motion tests."""

from __future__ import annotations

import pytest

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.embodiment import Embodiment
from umbra_core.perception import Observation, PerceptionMembrane
from umbra_core.physiology import Physiology
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.util import SeededRNG
from umbra_core.world_model import FactKind, VerifiedMotionDelta, WorldModel


def _obs(*, distance=5.0, support=None):
    row = {
        "kind": "resource",
        "relative_direction": 0.0,
        "estimated_distance": distance,
        "confidence": 0.8,
        "uncertainty": 0.2,
    }
    if support is not None:
        row["distance_support_upper_bound"] = support
    return [row]


def test_direct_sensor_support_is_distinct_from_generic_uncertainty():
    observation = Observation(
        observation_id="obs-1",
        kind="resource",
        relative_direction=0.0,
        estimated_distance=5.0,
        confidence=0.8,
        uncertainty=0.2,
        observed_at=1.0,
        expires_at=2.0,
        source="sensor",
        distance_support_upper_bound=10.0,
    )
    assert observation.distance_support_upper_bound == 10.0
    assert observation.uncertainty == pytest.approx(1.0 - observation.confidence)
    assert observation.to_dict()["distance_support_upper_bound"] == 10.0


def test_unsupported_observation_does_not_fabricate_support():
    wm = WorldModel.create("agent")
    wm.ingest_observations(_obs(), tick=1, now=1.0)
    entity = next(iter(wm.entities.values()))
    assert entity.distance_support_upper_bound is None
    wm.ingest_observations([], tick=2, now=2.0)
    assert wm.policy_observations(observed_kinds=set()) == []


def test_verified_motion_propagates_nominal_state_and_support_without_world_coords():
    wm = WorldModel.create("agent")
    wm.ingest_observations(_obs(distance=5.0, support=10.0), tick=1, now=1.0)
    delta = VerifiedMotionDelta(
        displacement=1.0,
        body_relative_dx=1.0,
        body_relative_dy=0.0,
        heading_delta=0.0,
        provenance="test:verified_body_transition",
        execution_id="exec-1",
    )
    assert wm.apply_verified_motion(delta, tick=2) == 1
    entity = next(iter(wm.entities.values()))
    assert entity.distance_support_upper_bound == 11.0
    assert entity.estimated_state["estimated_distance"] == 4.0
    remembered = wm.policy_observations(observed_kinds=set())[0]
    assert remembered["fact_kind"] == FactKind.REMEMBERED_ESTIMATE.value
    assert "x" not in remembered and "y" not in remembered


def test_incompatible_reidentification_invalidates_support():
    wm = WorldModel.create("agent")
    wm.ingest_observations(_obs(distance=5.0, support=10.0), tick=1, now=1.0)
    wm.ingest_observations([], tick=2, now=2.0)
    wm.ingest_observations(_obs(distance=9.0, support=10.0), tick=3, now=3.0)
    entity = next(iter(wm.entities.values()))
    assert entity.distance_support_upper_bound is None
    assert wm.metrics["support_contradictions"] == 1


def test_route_budget_uses_support_upper_bound():
    phys = Physiology(energy=0.15)
    feasible, _, _ = Arbitrator._energy_route_budget(
        phys, _obs(distance=2.0, support=2.0)[0]
    )
    infeasible, _, _ = Arbitrator._energy_route_budget(
        phys, _obs(distance=2.0, support=30.0)[0]
    )
    assert feasible
    assert not infeasible


def test_world_model_runtime_propagates_verified_motion(tmp_path):
    org = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "d013v.sqlite"),
            seed=13013,
            world_model_enabled=True,
        )
    )
    org.run_ticks(40)
    assert org.world_model is not None
    assert "x" not in org.world_model.to_state()
    org.close()


def test_final_feasible_route_preempts_projected_route_loss():
    arb = Arbitrator()
    phys = Physiology(energy=0.1565)
    observation = _obs(distance=5.0, support=28.16)[0]
    preserved = arb._preserve_recoverability(
        phys, [observation], Candidate("MOVE", {"step": 1.0}), tick=388
    )
    assert preserved.capability == "APPROACH"
    assert preserved.params["source"] == "preserve_recoverability"
