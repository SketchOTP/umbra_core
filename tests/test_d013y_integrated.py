from umbra_core.arbitration import Arbitrator
from umbra_core.physiology import Physiology
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.util import SeededRNG
from umbra_core.world_model import WorldModel


def test_cold_start_discovery_uses_physical_action_and_real_observation(tmp_path):
    org = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "cold-start.sqlite"),
            seed=13013,
            world_model_enabled=True,
        )
    )
    first_resource = None
    for _ in range(80):
        row = org.tick_once()
        if org.world_model and any(
            e.entity_kind == "resource"
            and e.fact_kind == "CURRENT_OBSERVATION"
            for e in org.world_model.entities.values()
        ):
            first_resource = row["tick"]
            break
    assert first_resource is not None
    assert first_resource < 168
    assert org.phys.energy > 0.05
    assert not any(
        "x" in observation or "y" in observation
        for observation in org.world_model.policy_observations(observed_kinds=set())
    )
    org.close()


def test_verified_charge_strengthens_only_after_direct_observation():
    wm = WorldModel.create("agent", seed=13013)
    direct = [{
        "kind": "resource",
        "relative_direction": 0.0,
        "estimated_distance": 1.0,
        "confidence": 0.9,
        "uncertainty": 0.1,
        "source": "sensor",
        "distance_support_upper_bound": 10.0,
    }]
    wm.ingest_observations(direct, tick=1, now=1.0)
    result = wm.observe_outcome(
        tick=2,
        action="CHARGE",
        params={"toward": "resource"},
        verified_outcome={"success": True, "verified": True},
        observations=direct,
        action_issued=True,
        now=2.0,
    )
    assert result["verified_recovery_memory_strengthened"] is True
    entity = next(iter(wm.entities.values()))
    assert entity.verified_recovery_count == 1


def test_remembered_resource_requests_bounded_active_reacquisition():
    chosen = Arbitrator().select(
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
    assert chosen.capability == "APPROACH"
    assert chosen.params["strategy"] == "direct_homing"
    assert chosen.params["source"] == "active_reacquisition"
    assert chosen.params["fact_kind"] == "REMEMBERED_ESTIMATE"
