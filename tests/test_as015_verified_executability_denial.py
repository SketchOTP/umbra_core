"""AS-015 verified executability-denial source-contract tests."""

from __future__ import annotations

from pathlib import Path

from umbra_core.arbitration import Candidate
from umbra_core.recoverability.contracts import NOT_EXECUTABLE
from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.world_model import VerifiedExecutabilityDenial, WorldModel
from umbra_core.world_model.engine import ModelStatus, TransitionModel


def _denial(*, evidence_id: str, root_id: str, tick: int, reason: str = "affordance_denied"):
    return VerifiedExecutabilityDenial(
        evidence_id=evidence_id,
        root_id=root_id,
        tick=tick,
        capability="CHARGE",
        candidate_identity='{"capability":"CHARGE","params":{"toward":"resource"}}',
        entity_kind="resource",
        policy_evidence_ref=f"observation:{tick}",
        reason=reason,
    )


def test_denial_updates_affordance_only_and_preserves_transition_thresholds():
    wm = WorldModel.create("agent")
    wm.models["charge-model"] = TransitionModel(
        model_id="charge-model",
        conditions={"entity_kind": "resource"},
        action="CHARGE",
        predicted_effect={"success": 1.0},
        latency=0.0,
        confidence=0.9,
        support_count=3,
        contradiction_count=0,
        status=ModelStatus.ACTIVE.value,
    )
    for tick in range(1, 5):
        result = wm.observe_verified_executability_denial(
            _denial(evidence_id=f"denial:{tick}", root_id=f"root:{tick}", tick=tick)
        )
        assert result["accepted"] is True
    belief = wm.affordances["aff-resource-charge_from"]
    assert belief.contradiction_count == 4
    assert belief.status == ModelStatus.WEAKENED.value
    # An unexecuted denial never becomes transition/outcome evidence.
    assert wm.models["charge-model"].contradiction_count == 0
    assert wm.models["charge-model"].predicted_effect == {"success": 1.0}
    assert list(wm.route_evidence.experiences) == []


def test_denial_rejects_disallowed_unverified_and_duplicate_evidence():
    wm = WorldModel.create("agent")
    disallowed = wm.observe_verified_executability_denial(
        _denial(evidence_id="position", root_id="position", tick=1, reason="not_at_resource")
    )
    assert disallowed["accepted"] is False
    assert disallowed["reason"] == "executability_denial_reason_not_allowed"
    unverified = VerifiedExecutabilityDenial(
        **{**_denial(evidence_id="unverified", root_id="u", tick=2).__dict__, "verified": False}
    )
    assert wm.observe_verified_executability_denial(unverified)["accepted"] is False
    first = wm.observe_verified_executability_denial(
        _denial(evidence_id="same", root_id="same", tick=3)
    )
    second = wm.observe_verified_executability_denial(
        _denial(evidence_id="same", root_id="same", tick=3)
    )
    assert first["accepted"] is True
    assert second["duplicate"] is True
    assert wm.affordances["aff-resource-charge_from"].contradiction_count == 1


def test_denial_respects_world_model_learning_switches():
    evidence = _denial(evidence_id="off", root_id="off", tick=1)
    wm = WorldModel.create("agent")
    wm.config.learning_enabled = False
    assert wm.observe_verified_executability_denial(evidence)["reason"] == "learning_disabled"
    wm = WorldModel.create("agent")
    wm.config.affordance_learning = False
    assert (
        wm.observe_verified_executability_denial(evidence)["reason"]
        == "affordance_learning_disabled"
    )


def test_denial_state_survives_snapshot_form_without_replaying_execution():
    wm = WorldModel.create("agent")
    wm.observe_verified_executability_denial(
        _denial(evidence_id="persisted", root_id="root:1", tick=1)
    )
    restored = WorldModel.from_state(wm.to_state())
    duplicate = restored.observe_verified_executability_denial(
        _denial(evidence_id="persisted", root_id="root:1", tick=1)
    )
    assert duplicate["duplicate"] is True
    assert restored.affordances["aff-resource-charge_from"].contradiction_count == 1
    assert restored.models == {}


def test_runtime_defers_and_deduplicates_policy_visible_affordance_denial(tmp_path: Path):
    org = create_organism(OrganismConfig(
        db_path=str(tmp_path / "organism.sqlite"),
        seed=1515,
        world_model_enabled=True,
    ))
    try:
        feature = org.embodiment._habitat.feature("resource")
        assert feature is not None
        org.embodiment.body.x = feature.x
        org.embodiment.body.y = feature.y
        feature.chargeable = False  # legitimate external world change in this fixture
        observations = [row.to_dict() for row in org.perception.perceive(
            org.embodiment, org.monotonic_time, org.rng
        )]
        assert any(row.get("kind") == "resource" for row in observations)
        org._tick_organism_age = 1
        org._begin_executability_denial_root(observations, organism_age=1)
        candidate = Candidate("CHARGE", {"toward": "resource"})
        assert org._candidate_executability(candidate) == NOT_EXECUTABLE
        assert org._candidate_executability(candidate) == NOT_EXECUTABLE
        assert org.world_model.affordances == {}
        assert org.metrics["actions"] == {}
        committed = org._commit_deferred_executability_denials(wall=0.0)
        assert len(committed) == 1
        assert committed[0]["reason"] == "affordance_denied"
        assert committed[0]["executed"] is False
        assert org.world_model.affordances["aff-resource-charge_from"].contradiction_count == 1
        assert org.metrics["actions"] == {}
        persisted = org.store.iter_events()
        record = [
            event for event in persisted
            if event["event_type"] == "world_model_executability_denial_verified"
        ]
        assert len(record) == 1
        assert "target_object_id" not in record[0]["payload"]
        assert "coordinates" not in record[0]["payload"]
    finally:
        org.close()


def test_runtime_does_not_learn_from_positional_terminal_denial(tmp_path: Path):
    org = create_organism(OrganismConfig(
        db_path=str(tmp_path / "position.sqlite"),
        seed=1516,
        world_model_enabled=True,
    ))
    try:
        observations = [row.to_dict() for row in org.perception.perceive(
            org.embodiment, org.monotonic_time, org.rng
        )]
        org._tick_organism_age = 1
        org._begin_executability_denial_root(observations, organism_age=1)
        assert org._candidate_executability(Candidate("CHARGE", {"toward": "resource"})) == NOT_EXECUTABLE
        assert org._commit_deferred_executability_denials(wall=0.0) == []
        assert org.world_model.affordances == {}
    finally:
        org.close()


def test_runtime_denial_provenance_survives_snapshot_restart(tmp_path: Path):
    path = tmp_path / "restart.sqlite"
    org = create_organism(OrganismConfig(
        db_path=str(path), seed=1517, world_model_enabled=True,
    ))
    try:
        feature = org.embodiment._habitat.feature("resource")
        assert feature is not None
        org.embodiment.body.x = feature.x
        org.embodiment.body.y = feature.y
        feature.chargeable = False
        observations = [row.to_dict() for row in org.perception.perceive(
            org.embodiment, org.monotonic_time, org.rng
        )]
        org._tick_organism_age = 1
        org._begin_executability_denial_root(observations, organism_age=1)
        org._candidate_executability(Candidate("CHARGE", {"toward": "resource"}))
        committed = org._commit_deferred_executability_denials(wall=0.0)
        assert len(committed) == 1
        org.snapshot_if_due(force=True)
    finally:
        org.close()
    restored = load_organism(OrganismConfig(
        db_path=str(path), seed=1517, world_model_enabled=True,
    ))
    try:
        assert restored.world_model.affordances["aff-resource-charge_from"].contradiction_count == 1
        evidence_id = committed[0]["evidence_id"]
        duplicate = restored.world_model.observe_verified_executability_denial(
            _denial(evidence_id=evidence_id, root_id=committed[0]["root_id"], tick=1)
        )
        assert duplicate["duplicate"] is True
    finally:
        restored.close()


def test_world_change_race_learns_affordance_without_unsafe_retry(tmp_path: Path):
    """A real world change after normal selection feeds only affordance learning."""
    org = create_organism(OrganismConfig(
        db_path=str(tmp_path / "race.sqlite"),
        seed=4415,
        world_model_enabled=True,
    ))
    try:
        feature = org.embodiment._habitat.feature("resource")
        assert feature is not None

        def policy_observations():
            org.embodiment.body.x = feature.x
            org.embodiment.body.y = feature.y
            org.phys.intervene(energy=0.10, fatigue=0.20, stimulation=0.50)
            return [row.to_dict() for row in org.perception.perceive(
                org.embodiment, org.monotonic_time, org.rng
            )]

        def normal_selected_charge(observations):
            candidate = org.arbitrator.select(
                org.phys,
                observations,
                org.tick,
                org.rng,
                candidate_executability=org._candidate_executability,
            )
            assert candidate.capability == "CHARGE"
            return candidate

        def governed_charge(candidate, observations):
            proposal = org.governance.propose(candidate.capability, candidate.params)
            decision = org.governance.admit(proposal, tick=org.tick)
            assert decision.admitted
            org._pending_action = {"capability": "CHARGE", "params": candidate.params}
            outcome = org.governance.execute_and_verify(
                proposal, decision, org.embodiment, org.rng,
                resolve_params=org._resolve_params, tick=org.tick,
            )
            assert outcome is not None
            return org._finish_outcome(outcome, 0.0, observations, action_issued=True)

        # Three ordinary selected/governed successes establish the live model
        # and affordance. Nothing writes WorldModel state directly.
        for _ in range(3):
            observations = policy_observations()
            result = governed_charge(normal_selected_charge(observations), observations)
            assert result["success"] is True
            org.tick += 1
            org._tick_organism_age = org.tick
        belief = org.world_model.affordances["aff-resource-charge_from"]
        assert belief.support_count == 3
        assert belief.status == ModelStatus.ACTIVE.value

        # External world authority changes after the normal candidate has been
        # selected. The proposal is unchanged; normal Governance/execution then
        # produces the genuine verified negative outcome.
        observations = policy_observations()
        selected = normal_selected_charge(observations)
        feature.chargeable = False
        executed_denial = governed_charge(selected, observations)
        assert executed_denial["success"] is False
        assert executed_denial["reason"] == "affordance_denied"
        transition = next(model for model in org.world_model.models.values() if model.action == "CHARGE")
        assert transition.contradiction_count == 1
        assert transition.status == ModelStatus.ACTIVE.value
        assert belief.contradiction_count == 1

        # Later roots still generate ordinary CHARGE candidates, but preflight
        # blocks physical execution. Distinct roots now contribute only the
        # deferred affordance-denial evidence.
        for _ in range(8):
            org.embodiment.body.x = feature.x
            org.embodiment.body.y = feature.y
            org.phys.intervene(energy=0.10, fatigue=0.20, stimulation=0.50)
            org.tick_once()
            if belief.status == ModelStatus.WEAKENED.value:
                break
        assert belief.status == ModelStatus.WEAKENED.value
        assert belief.contradiction_count >= 4
        assert transition.contradiction_count == 1
        denial_events = [
            event for event in org.store.iter_events()
            if event["event_type"] == "world_model_executability_denial_verified"
        ]
        assert len(denial_events) >= 3
        assert all(event["payload"]["executed"] is False for event in denial_events)
        assert org.metrics["actions"].get("CHARGE") == 4
    finally:
        org.close()
