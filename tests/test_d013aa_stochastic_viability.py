from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology
from umbra_core.world_model.engine import WorldModel


def test_support_backed_resource_landmark_persists_without_becoming_current():
    wm = WorldModel.create("test-agent", seed=1)
    wm.ingest_observations(
        [{
            "kind": "resource",
            "relative_direction": 0.0,
            "estimated_distance": 4.0,
            "confidence": 0.8,
            "uncertainty": 0.2,
            "observed_at": 0.0,
            "distance_support_upper_bound": 12.0,
        }],
        tick=1,
        now=0.0,
    )
    for tick in range(2, 120):
        wm.ingest_observations([], tick=tick, now=float(tick))
    entity = next(e for e in wm.entities.values() if e.entity_kind == "resource")
    assert entity.fact_kind == "REMEMBERED_ESTIMATE"
    assert entity.confidence >= 0.8
    assert entity.distance_support_upper_bound is not None
    policy = wm.policy_observations(observed_kinds=set())
    assert policy and policy[0]["fact_kind"] == "REMEMBERED_ESTIMATE"


def test_contradictory_resource_observation_can_clear_landmark_support():
    wm = WorldModel.create("test-agent", seed=2)
    wm.ingest_observations(
        [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 2.0,
          "confidence": 0.8, "uncertainty": 0.2, "observed_at": 0.0,
          "distance_support_upper_bound": 12.0}], tick=1, now=0.0
    )
    wm.ingest_observations([], tick=2, now=1.0)
    wm.ingest_observations(
        [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 8.0,
          "confidence": 0.8, "uncertainty": 0.2, "observed_at": 1.0,
          "distance_support_upper_bound": 12.0}], tick=3, now=2.0
    )
    entity = next(e for e in wm.entities.values() if e.entity_kind == "resource")
    assert entity.fact_kind == "CURRENT_OBSERVATION"
    assert entity.distance_support_upper_bound is None


def test_retry_aware_corridor_preserves_energy_landmark_when_reserve_is_insufficient():
    arbitrator = Arbitrator()
    phys = Physiology(energy=0.31, fatigue=0.70, integrity=0.90, stimulation=0.55)
    chosen = Candidate("APPROACH", {"toward": "rest", "step": 1.5})
    observations = [{"kind": "resource", "fact_kind": "CURRENT_OBSERVATION",
                     "estimated_distance": 10.0, "relative_direction": 0.0,
                     "distance_support_upper_bound": 12.0}]
    replacement = arbitrator._preserve_recoverability(phys, observations, chosen, 1)
    assert replacement.capability == "APPROACH"
    assert replacement.params["toward"] == "resource"
    assert replacement.params["source"] == "retry_aware_recovery_corridor"


def test_retry_aware_corridor_does_not_make_energy_universally_dominant():
    arbitrator = Arbitrator()
    phys = Physiology(energy=0.80, fatigue=0.70, integrity=0.90, stimulation=0.55)
    chosen = Candidate("APPROACH", {"toward": "rest", "step": 1.5})
    observations = [{"kind": "resource", "fact_kind": "CURRENT_OBSERVATION",
                     "estimated_distance": 4.0, "relative_direction": 0.0,
                     "distance_support_upper_bound": 12.0}]
    assert arbitrator._preserve_recoverability(phys, observations, chosen, 1) is chosen
