import copy

import umbra_core.runtime as runtime_module
from umbra_core.arbitration import Candidate
from umbra_core.embodiment import Embodiment
from umbra_core.governance import (
    Governance,
    GovernanceState,
    authority_effect_branches,
    project_verified_outcome,
)
from umbra_core.physiology import (
    OUTCOME_EFFECTS,
    Physiology,
    verified_outcome_effect_branches,
)
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.util import SeededRNG


def _organism(tmp_path, *, seed=13035):
    return create_organism(
        OrganismConfig(
            db_path=str(tmp_path / f"ak-{seed}.sqlite"),
            seed=seed,
            condition="C0",
            intervention="I0",
            world_model_enabled=True,
        )
    )


def _authority(org, candidate):
    return authority_effect_branches(
        candidate,
        org.embodiment,
        org.embodiment_adapter,
        resolve_params=org._resolve_params,
    )


def test_default_13035_authority_retains_charge_without_changing_score(tmp_path):
    org = _organism(tmp_path)
    try:
        authority_resolver = runtime_module.authority_effect_branches
        runtime_module.authority_effect_branches = lambda candidate, *args, **kwargs: (
            verified_outcome_effect_branches(candidate.capability)
        )
        for _ in range(265):
            assert not org.tick_once().get("no_safe_action")
        runtime_module.authority_effect_branches = authority_resolver
        before_counts = dict(org.arbitrator.state.action_counts)
        row = org.tick_once()
        assert row["tick"] == 266
        assert row["capability"] == "CHARGE"
        assert row["outcome"]["success"] is True
        assert row.get("no_safe_action") is not True
        assert org.arbitrator.state.action_counts["CHARGE"] == before_counts["CHARGE"] + 1
    finally:
        runtime_module.authority_effect_branches = authority_resolver
        org.close()


def test_charge_and_rest_preflight_share_execution_semantics():
    embodiment = Embodiment()
    governance = Governance(GovernanceState())
    for capability, toward, kind in (
        ("CHARGE", "resource", "resource"),
        ("REST", "rest", "rest"),
    ):
        feature = embodiment.habitat.feature(kind)
        assert feature is not None
        embodiment.body.x = feature.x
        embodiment.body.y = feature.y
        params = {"toward": toward}
        preflight = embodiment.preflight_primitive(capability, params)
        assert preflight is not None and preflight["ok_raw"] is True
        actual = copy.deepcopy(embodiment).execute_primitive(
            capability, params, SeededRNG(1)
        )
        verified = governance.verify_outcome(capability, actual)
        assert project_verified_outcome(capability, preflight) == (
            verified.success,
            verified.physiology_effects,
        )


def test_state_dependent_boundaries_and_missing_target_remain_conservative(tmp_path):
    org = _organism(tmp_path, seed=1)
    try:
        resource = org.embodiment.habitat.feature("resource")
        assert resource is not None
        org.embodiment.body.x = resource.x + resource.radius + 0.301
        org.embodiment.body.y = resource.y
        failure = _authority(
            org,
            Candidate("CHARGE", {"toward": "resource"})
        )
        assert failure == ({"energy": -0.003, "fatigue": 0.002},)
        org.embodiment.habitat.features = [
            feature
            for feature in org.embodiment.habitat.features
            if feature.kind != "resource"
        ]
        ambiguous = _authority(
            org,
            Candidate("CHARGE", {"toward": "resource"})
        )
        assert ambiguous == failure
    finally:
        org.close()


def test_stochastic_delay_scaling_and_hazard_branches_remain_represented(tmp_path):
    org = _organism(tmp_path, seed=2)
    try:
        org.embodiment.body.energy_cost_scale = 2.0
        movement = _authority(org, Candidate("MOVE", {"step": 1.0}))
        assert {branch["energy"] for branch in movement} >= {-0.010, -0.006}
        assert any(
            branch.get("integrity") == OUTCOME_EFFECTS["HAZARD_HIT"]["integrity"]
            for branch in movement
        )
        org.embodiment.body.actuator_delay = 1.0
        delayed = _authority(
            org,
            Candidate("ORIENT", {"heading": 0.0})
        )
        assert {} in delayed
    finally:
        org.close()


def test_truly_empty_authority_safe_set_still_fails_closed(tmp_path):
    org = _organism(tmp_path, seed=3)
    try:
        org.phys = Physiology(
            energy=0.051,
            fatigue=0.949,
            integrity=0.21,
            stimulation=0.949,
        )
        org.embodiment.body.x = 20.0
        org.embodiment.body.y = 20.0
        assert _authority(
            org,
            Candidate("CHARGE", {"toward": "resource"})
        ) == ({"energy": -0.003, "fatigue": 0.002},)
    finally:
        org.close()
