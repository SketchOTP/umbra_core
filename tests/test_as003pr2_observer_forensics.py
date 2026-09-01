"""Pure zero-organism proofs for the AS-003P-R2 forensic tooling."""

from copy import deepcopy
from types import SimpleNamespace

from tools.as003pr2_forensics import (
    comparator_proof,
    world_relationship_audit,
    world_semantic_diff,
)
from umbra_core.embodiment import Body
from umbra_core.hypothetical.shadow import capture_runtime_frame, shadow_row
from umbra_core.physiology import Physiology
from umbra_core.self_model.engine import SelfModel
from umbra_core.world_model.engine import FactKind, WorldEntity, WorldModel


def test_frozen_comparator_has_preregistered_id_renaming_false_positive():
    proof = comparator_proof()
    assert proof["result"] == "FROZEN_COMPARATOR_NOT_ID_RENAMING_INVARIANT"
    assert proof["synthetic_false_positive_count"] > 0
    assert proof["synthetic_false_negative_count"] == 0


def test_retained_world_model_is_exactly_semantically_equal():
    result = world_semantic_diff()
    assert result["accepted_state_equal"] is True
    assert result["full_id_invariant_world_model_equal"] is True
    assert result["semantic_difference_count"] == 0


def test_retained_world_model_relationships_follow_semantic_models():
    result = world_relationship_audit()
    assert result["all_relationship_fields_equal"] is True


def test_physiology_as_dict_is_pure():
    owner = Physiology(energy=0.61, fatigue=0.31, integrity=0.88, stimulation=0.47)
    before = deepcopy(owner.to_state())
    owner.as_dict()
    assert owner.to_state() == before


def test_world_entity_to_dict_is_pure():
    owner = WorldEntity(
        entity_id="entity:fixture",
        entity_kind="resource",
        estimated_state={"estimated_distance": 2.0, "relative_direction": 0.25},
        last_observed_at=4.0,
        confidence=0.8,
        uncertainty=0.2,
        persistence_probability=0.7,
        evidence_count=3,
        fact_kind=FactKind.CURRENT_OBSERVATION.value,
        last_tick=7,
    )
    before = deepcopy(owner)
    owner.to_dict()
    assert owner == before


def test_world_model_comparison_accessors_are_pure():
    owner = WorldModel.create("agent:fixture", seed=91)
    owner.entities["entity:fixture"] = WorldEntity(
        entity_id="entity:fixture",
        entity_kind="resource",
        estimated_state={"estimated_distance": 2.0, "relative_direction": 0.25},
        last_observed_at=4.0,
        confidence=0.8,
        uncertainty=0.2,
        persistence_probability=0.7,
        evidence_count=3,
        fact_kind=FactKind.CURRENT_OBSERVATION.value,
        last_tick=7,
    )
    before = deepcopy(owner.to_state())
    owner.to_state()
    owner.state_hash()
    owner.accepted_state()
    assert owner.to_state() == before


def test_self_model_shadow_accessors_are_pure():
    owner = SelfModel.create("agent:fixture", seed=91)
    before = deepcopy(owner.to_state())
    owner.capability_support("APPROACH")
    owner.to_state()
    assert owner.to_state() == before


def test_exact_capture_runtime_frame_owner_reads_are_pure():
    physiology = Physiology(energy=0.61, fatigue=0.31, integrity=0.88, stimulation=0.47)
    self_model = SelfModel.create("agent:fixture", seed=91)
    world_model = WorldModel.create("agent:fixture", seed=91)
    world_model.entities["entity:fixture"] = WorldEntity(
        entity_id="entity:fixture",
        entity_kind="resource",
        estimated_state={"estimated_distance": 2.0, "relative_direction": 0.25},
        last_observed_at=4.0,
        confidence=0.8,
        uncertainty=0.2,
        persistence_probability=0.7,
        evidence_count=3,
        distance_support_upper_bound=2.4,
        support_body_schema_id=self_model.active.body_schema_id,
        fact_kind=FactKind.CURRENT_OBSERVATION.value,
        last_tick=7,
    )
    embodiment = SimpleNamespace(body=Body(), _pending_actuation=None, _delay_remaining=0)
    owner = SimpleNamespace(
        embodiment_adapter=None,
        self_model=self_model,
        world_model=world_model,
        embodiment=embodiment,
        phys=physiology,
        _pending_action=None,
        _delayed_proposal=None,
        tick=7,
        _tick_organism_age=7,
        monotonic_time=3.5,
    )
    before = {
        "physiology": deepcopy(physiology.to_state()),
        "self_model": deepcopy(self_model.to_state()),
        "world_model": deepcopy(world_model.to_state()),
        "body": deepcopy(embodiment.body.to_state()),
    }
    frame = capture_runtime_frame(owner)
    assert physiology.to_state() == before["physiology"]
    assert self_model.to_state() == before["self_model"]
    assert world_model.to_state() == before["world_model"]
    assert embodiment.body.to_state() == before["body"]
    assert frame.organism_tick == 7


def test_shadow_row_is_pure_over_immutable_frame():
    physiology = Physiology()
    self_model = SelfModel.create("agent:fixture", seed=92)
    world_model = WorldModel.create("agent:fixture", seed=92)
    embodiment = SimpleNamespace(body=Body(), _pending_actuation=None, _delay_remaining=0)
    owner = SimpleNamespace(
        embodiment_adapter=None,
        self_model=self_model,
        world_model=world_model,
        embodiment=embodiment,
        phys=physiology,
        _pending_action=None,
        _delayed_proposal=None,
        tick=7,
        _tick_organism_age=7,
        monotonic_time=3.5,
    )
    frame = capture_runtime_frame(owner)
    before = frame.to_canonical()
    row = shadow_row(frame, ({"identity": "candidate:idle", "capability": "IDLE"},))
    assert frame.to_canonical() == before
    assert row["behavioral_authority"] is False
    assert row["rng_consumed"] is False
    assert row["owner_mutation"] is False
