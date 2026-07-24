"""UMBRA-D-009 persistent habitat agency tests."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from umbra_core.embodiment import (
    BodyOccupancyView,
    Embodiment,
    HabitatFeature,
    PartnerEntity,
    PartnerTrueCues,
    response_policy_for_history,
)
from umbra_core.events import AUTHORITATIVE_EVENT_TYPES, habitat_event_authority_class, is_authoritative
from umbra_core.habitat.engine import (
    BodyCollisionShape,
    BodyPoseView,
    HabitatEngine,
    Position,
    ReachProfile,
)
from umbra_core.habitat.migration import habitat_object_from_legacy_feature, legacy_object_id_for_feature
from umbra_core.habitat.events import (
    HABITAT_BODY_ZONE_TRANSITIONED,
    HABITAT_EVENT_TYPES,
    HABITAT_OBJECT_MOVED,
    HABITAT_OBJECT_PICKED_UP,
    HabitatEventError,
    apply_habitat_event,
    build_body_zone_transition_event,
    build_initialized_event,
    build_object_moved_event,
    build_object_picked_up_event,
    replay_habitat_from_events,
)
from umbra_core.habitat.projection import (
    HabitatWriteRejected,
    ProjectionMismatchError,
    project_features,
    validate_projection,
)
from umbra_core.habitat.state import (
    ActivatableState,
    FreeLocation,
    HabitatObject,
    HabitatState,
    HeldByLocation,
    IdleState,
    MutationRejected,
    ObjectKind,
    ResourceState,
    Zone,
    ZoneConnection,
    ZoneKind,
    apply_committed_object_mutation,
    apply_rejected_object_mutation,
    compute_habitat_definition_hash,
    compute_object_definition_hash,
    compute_object_state_hash,
    compute_state_hash,
    migrate_object_definition,
    sample_habitat_state,
    with_object_state_hash,
    with_state_hash,
)
from umbra_core.habitat_affordances import (
    AdapterValidatedManipulation,
    AffordanceValidationResult,
    HabitatAffordanceEngine,
    HabitatEffectPlan,
    ManipulationRequest,
    PickUpParameters,
    PlaceParameters,
    PushParameters,
    UseParameters,
    definition_hash,
    load_affordance_definitions_file,
)
from umbra_core.habitat_affordances.engine import validate_manipulation_parameters
from umbra_core.util import canon_json, sha256_hex


def test_habitat_definitions_have_stable_hashes():
    state = sample_habitat_state()
    habitat_hash = compute_habitat_definition_hash(state)
    object_hashes = {
        object_id: compute_object_definition_hash(obj)
        for object_id, obj in state.objects.items()
    }

    assert habitat_hash == "495efd05b8bc8bba8a20d8319f273be772d1b7f70ff0913aa4a455c5b97420c6"
    assert object_hashes == {
        "resource:0": "44a8f12ad4c9de3190d264b874ab57a8b794a8d040b6865e9cf30f735ca24fa3",
        "rest:0": "6436aaf44d387fc8f0b17427c6362f77d4c7874169c423650e50eb154271a1cd",
    }
    assert compute_state_hash(state) == state.state_hash
    for obj in state.objects.values():
        assert compute_object_state_hash(obj) == obj.object_state_hash


def test_object_version_increments_once_per_committed_mutation():
    state = sample_habitat_state()
    obj = state.objects["resource:0"]
    start_version = obj.object_version

    def bump_condition(current: HabitatObject) -> HabitatObject:
        return replace(current, condition=current.condition - 0.1)

    once = apply_committed_object_mutation(obj, bump_condition)
    assert once.object_version == start_version + 1
    assert once.object_state_hash != obj.object_state_hash
    assert compute_object_state_hash(once) == once.object_state_hash

    twice = apply_committed_object_mutation(once, bump_condition)
    assert twice.object_version == start_version + 2

    migrated = migrate_object_definition(
        twice,
        new_definition_version=twice.definition_version + 1,
        new_definition_hash="c3d4e5f6789012345678abcdef0123456789abcdef0123456789abcdef012345",
        migrate_fn=lambda current: replace(current, collision_radius=current.collision_radius + 0.1),
    )
    assert migrated.definition_version == twice.definition_version + 1
    assert migrated.object_version == twice.object_version + 1
    assert migrated.object_state_hash != twice.object_state_hash


def test_failed_mutation_does_not_increment_object_version():
    state = sample_habitat_state()
    obj = state.objects["resource:0"]
    start_version = obj.object_version
    start_hash = obj.object_state_hash

    def rejected(_: HabitatObject) -> HabitatObject:
        raise MutationRejected("HABITAT_COLLECTION_CAP_EXCEEDED")

    result = apply_rejected_object_mutation(obj, rejected)
    assert result.object_version == start_version
    assert result.object_state_hash == start_hash
    assert result is obj


def _engine_with_sample() -> HabitatEngine:
    return HabitatEngine(sample_habitat_state())


def test_habitat_engine_is_only_writer():
    engine = _engine_with_sample()
    snapshot_before = engine.snapshot_view()
    assert engine.zone_free_object_count["zone:general"] == 1
    assert engine.zone_free_object_count["zone:rest"] == 1
    assert not hasattr(engine, "zone_body_count")

    engine.commit_free_location("resource:0", 6.0, 4.0)
    snapshot_after = engine.snapshot_view()
    assert snapshot_after.state_version == snapshot_before.state_version + 1
    assert snapshot_after.state_hash != snapshot_before.state_hash
    obj = engine.get_object("resource:0")
    assert obj is not None and isinstance(obj.location, FreeLocation)
    assert obj.location.x == 6.0

    projection = engine.project()
    with pytest.raises(ProjectionMismatchError):
        engine.validate_projection(
            replace(projection, state_version=projection.state_version + 1)
        )


def test_embodiment_habitat_projection_is_read_only():
    engine = _engine_with_sample()
    emb = Embodiment()
    emb.attach_habitat_engine(engine)
    habitat = emb.habitat

    assert isinstance(habitat.features, tuple)
    with pytest.raises(HabitatWriteRejected):
        habitat.relocate("resource", 1.0, 1.0)
    with pytest.raises(AttributeError):
        habitat.features.append(HabitatFeature("resource", 0.0, 0.0))


def test_projection_matches_authoritative_version_and_hash():
    engine = _engine_with_sample()
    snapshot = engine.snapshot_view()
    projection = project_features(snapshot)
    engine.validate_projection(projection)
    assert projection.state_version == snapshot.state_version
    assert projection.state_hash == snapshot.state_hash
    assert projection.habitat_id == snapshot.habitat_id
    assert {f.object_id for f in projection.features} == {"resource:0", "rest:0"}


def test_projection_mismatch_fails_closed():
    engine = _engine_with_sample()
    projection = engine.project()
    stale = replace(projection, state_version=projection.state_version + 99)
    with pytest.raises(ProjectionMismatchError):
        validate_projection(stale, engine.snapshot_view())


def test_body_occupancy_uses_immutable_embodiment_view():
    engine = _engine_with_sample()
    emb = Embodiment()
    emb.attach_habitat_engine(engine)
    occ = emb.body_occupancy_view()
    with pytest.raises(FrozenInstanceError):
        occ.position_x = 99.0  # type: ignore[misc]

    pose = BodyPoseView(
        body_instance_id=occ.body_instance_id,
        body_pose_version=occ.body_pose_version,
        position=Position(occ.position_x, occ.position_y),
        collision_shape=BodyCollisionShape(max(occ.collision_radius, 0.5)),
        attachment_generation=occ.attachment_generation,
    )
    reach = ReachProfile(reach_radius=emb.body.sensor_range)
    assert engine.check_range(pose, reach, "resource:0") is True
    hash_before = engine.snapshot_view().state_hash
    emb.body.x = 19.0
    emb.body.y = 19.0
    assert engine.snapshot_view().state_hash == hash_before


def test_habitat_does_not_persist_second_body_position():
    engine = _engine_with_sample()
    state = engine.state
    assert "body" not in state.__dataclass_fields__
    assert not hasattr(engine, "zone_body_count")

    emb = Embodiment()
    emb.attach_habitat_engine(engine)
    hash_before = engine.snapshot_view().state_hash
    emb.body.x = 12.5
    emb.body.y = 7.5
    assert engine.snapshot_view().state_hash == hash_before
    occ = emb.body_occupancy_view()
    assert occ.position_x == 12.5
    zone = engine.zone_at(occ.position_x, occ.position_y)
    assert zone in {"zone:general", "zone:rest"}


def test_legacy_reads_do_not_create_second_authority():
    engine = _engine_with_sample()
    emb = Embodiment()
    emb.attach_habitat_engine(engine)
    version_before = engine.snapshot_view().state_version
    _ = emb.habitat.to_state()
    _ = emb.habitat.features
    _ = emb.habitat.feature("resource")
    assert engine.snapshot_view().state_version == version_before

    legacy = HabitatFeature("resource", 17.0, 3.0, 1.8)
    obj = habitat_object_from_legacy_feature(
        legacy,
        object_id=legacy_object_id_for_feature("resource"),
    )
    assert obj.object_id == "feature:resource:0"
    assert obj.object_kind == ObjectKind.RESOURCE


def _embodiment_with_engine() -> tuple[Embodiment, HabitatEngine]:
    engine = _engine_with_sample()
    emb = Embodiment()
    emb.attach_habitat_engine(engine)
    return emb, engine


def _legacy_habitat_snapshot(emb: Embodiment) -> dict[str, object]:
    h = emb._habitat
    return {
        "feature_count": len(h.features),
        "partner_count": len(h.partners),
        "blocked_cells": list(h.blocked_cells),
        "delayed_ticks": h.delayed_consequence_ticks,
        "misleading": h.misleading_correlation,
        "resource_x": h.feature("resource").x if h.feature("resource") else None,
    }


def test_attached_embodiment_rejects_habitat_mutations():
    emb, engine = _embodiment_with_engine()
    before = _legacy_habitat_snapshot(emb)
    engine_before = engine.snapshot_view().state_hash

    mutation_calls = [
        lambda: emb.apply_world_intervention("I1"),
        lambda: emb.apply_development_intervention("I1"),
        lambda: emb.apply_memory_history("H1"),
        lambda: emb.apply_social_history("H0"),
        lambda: emb.apply_individuality_history("H1"),
        lambda: emb.plant_partner(
            PartnerEntity(
                "p-test",
                1.0,
                1.0,
                PartnerTrueCues.for_history("H0"),
                response_policy_for_history("H0"),
            )
        ),
        lambda: emb.move_feature_external("resource", 9.0, 9.0),
        lambda: emb.set_occlusion("inspect", True),
    ]
    for call in mutation_calls:
        with pytest.raises(HabitatWriteRejected):
            call()

    assert _legacy_habitat_snapshot(emb) == before
    assert engine.snapshot_view().state_hash == engine_before


def test_attached_embodiment_primitive_reads_projection_not_legacy_habitat():
    emb, engine = _embodiment_with_engine()
    emb._habitat.blocked_cells.append((10.0, 8.0, 1.8))
    emb._habitat.delayed_consequence_ticks = 3
    emb._habitat.misleading_correlation = True

    habitat = emb.habitat
    assert habitat.blocked_cells == ((10.0, 8.0, 1.8),)
    assert habitat.delayed_consequence_ticks == 3
    assert habitat.misleading_correlation is True

    legacy_resource_x = emb._habitat.feature("resource").x
    emb._habitat.relocate("resource", 99.0, 99.0)
    projected = emb.habitat.feature("resource")
    assert projected is not None
    assert projected.x != 99.0
    assert projected.x == 4.0
    assert legacy_resource_x != projected.x


def test_attached_embodiment_no_alternate_habitat_mutation_path():
    emb, engine = _embodiment_with_engine()
    before = _legacy_habitat_snapshot(emb)
    engine_hash = engine.snapshot_view().state_hash

    from umbra_core.util import SeededRNG

    rng = SeededRNG(0)
    emb.execute_primitive("MOVE", {"step": 1.0, "heading": 0.0}, rng)
    emb.execute_primitive("APPROACH", {"toward": "resource", "step": 0.5, "heading": 0.0}, rng)

    assert _legacy_habitat_snapshot(emb) == before
    assert engine.snapshot_view().state_hash == engine_hash


def test_zone_held_object_count_populated_from_held_objects():
    state = sample_habitat_state()
    held_obj = replace(
        state.objects["resource:0"],
        location=HeldByLocation(body_instance_id="body:default", attachment_generation=0, hold_slot=0),
    )
    objects = dict(state.objects)
    objects["resource:0"] = held_obj
    state = with_state_hash(replace(state, objects=objects))
    engine = HabitatEngine(state)

    assert engine.zone_held_object_count["zone:general"] == 0
    pose = BodyPoseView(
        body_instance_id="body:default",
        body_pose_version=1,
        position=Position(4.0, 3.0),
        collision_shape=BodyCollisionShape(0.5),
        attachment_generation=0,
    )
    engine.project(body_pose=pose)
    assert engine.zone_held_object_count["zone:general"] == 1
    assert engine.zone_held_object_count["zone:rest"] == 0


def _initialized_state() -> tuple[dict, HabitatState]:
    sample = sample_habitat_state()
    init_event = build_initialized_event(sample)
    state = apply_habitat_event(None, init_event)
    return init_event, state


def _state_after_move(state: HabitatState, object_id: str, x: float, y: float) -> HabitatState:
    engine = HabitatEngine(state)
    engine.commit_free_location(object_id, x, y)
    return engine.state


def _sample_habitat_event_chain() -> tuple[list[dict], HabitatState]:
    init_event, state = _initialized_state()
    moved_state = _state_after_move(state, "resource:0", 6.0, 4.0)
    move_event = build_object_moved_event(state, moved_state, "resource:0")
    picked_state_engine = HabitatEngine(moved_state)
    held = HeldByLocation(body_instance_id="body:default", attachment_generation=0, hold_slot=0)

    def pick_up(obj: HabitatObject) -> HabitatObject:
        return replace(obj, location=held)

    picked_state_engine.commit_object_mutation("resource:0", pick_up)
    picked_state = picked_state_engine.state
    pick_event = build_object_picked_up_event(moved_state, picked_state, "resource:0")
    return [init_event, move_event, pick_event], picked_state


def test_habitat_events_are_idempotent():
    events, final_state = _sample_habitat_event_chain()
    state = None
    for event in events:
        first = apply_habitat_event(state, event)
        second = apply_habitat_event(first, event)
        assert second is first
        state = first
    assert state is not None
    assert state.state_hash == final_state.state_hash


def test_invalid_habitat_event_order_fails_closed():
    init_event, state = _initialized_state()
    moved_state = _state_after_move(state, "resource:0", 6.0, 4.0)
    move_event = build_object_moved_event(state, moved_state, "resource:0")
    stale_move = dict(move_event)
    stale_move["payload"] = dict(move_event["payload"])
    stale_move["payload"]["prior_state_version"] = moved_state.state_version
    stale_move["payload"]["prior_state_hash"] = moved_state.state_hash
    with pytest.raises(HabitatEventError, match="invalid_habitat_event_order"):
        apply_habitat_event(state, stale_move)


def test_missing_habitat_event_fails_closed():
    events, _ = _sample_habitat_event_chain()
    gap_events = [events[0], events[2]]
    with pytest.raises(HabitatEventError, match="invalid_habitat_event_order"):
        replay_habitat_from_events(gap_events)
    with pytest.raises(HabitatEventError, match="missing_habitat_events_fail_closed"):
        replay_habitat_from_events([], fail_closed_missing=True)


def test_habitat_state_hash_mismatch_fails_closed():
    init_event, state = _initialized_state()
    moved_state = _state_after_move(state, "resource:0", 6.0, 4.0)
    move_event = build_object_moved_event(state, moved_state, "resource:0")
    bad_hash = dict(move_event)
    bad_hash["payload"] = dict(move_event["payload"])
    bad_hash["payload"]["prior_state_hash"] = "0" * 64
    with pytest.raises(HabitatEventError, match="habitat_state_hash_mismatch"):
        apply_habitat_event(state, bad_hash)


def test_zone_transition_event_does_not_duplicate_body_authority():
    init_event, state = _initialized_state()
    zone_event = build_body_zone_transition_event(
        state,
        body_instance_id="body:default",
        from_zone_id="zone:general",
        to_zone_id="zone:rest",
    )
    after = apply_habitat_event(state, zone_event)
    assert after.state_version == state.state_version
    assert after.state_hash == state.state_hash
    assert zone_event["event_type"] == HABITAT_BODY_ZONE_TRANSITIONED
    events, _ = _sample_habitat_event_chain()
    event_types = [event["event_type"] for event in events]
    assert HABITAT_OBJECT_PICKED_UP in event_types
    assert event_types.count(HABITAT_OBJECT_MOVED) == 1
    assert HABITAT_OBJECT_PICKED_UP != HABITAT_OBJECT_MOVED


def test_birth_replay_rebuilds_projection_from_habitat_events():
    events, final_state = _sample_habitat_event_chain()
    replayed = replay_habitat_from_events(events)
    assert replayed.state_hash == final_state.state_hash
    engine = HabitatEngine(replayed)
    projection = engine.project()
    engine.validate_projection(projection)
    assert projection.state_version == replayed.state_version
    assert projection.state_hash == replayed.state_hash
    resource = engine.get_object("resource:0")
    assert resource is not None and isinstance(resource.location, HeldByLocation)


def test_replay_reproduces_object_versions_and_hashes():
    events, final_state = _sample_habitat_event_chain()
    replayed = replay_habitat_from_events(events)
    for object_id, obj in final_state.objects.items():
        replay_obj = replayed.objects[object_id]
        assert replay_obj.object_version == obj.object_version
        assert replay_obj.object_state_hash == obj.object_state_hash
    assert replayed.state_version == final_state.state_version
    assert replayed.state_hash == final_state.state_hash


def test_habitat_events_are_authoritative_in_registry():
    for event_type in HABITAT_EVENT_TYPES:
        assert habitat_event_authority_class(event_type) == "AUTHORITATIVE"
        assert is_authoritative(event_type)
        assert event_type in AUTHORITATIVE_EVENT_TYPES


_AFFORDANCE_DEFINITIONS_PATH = (
    __import__("pathlib").Path(__file__).resolve().parents[1]
    / "experiments"
    / "d009"
    / "affordance-definitions.json"
)
_HABITAT_DEFINITION_PATH = (
    __import__("pathlib").Path(__file__).resolve().parents[1]
    / "experiments"
    / "d009"
    / "habitat-definition.json"
)


def test_affordance_definitions_have_stable_hashes():
    definitions = load_affordance_definitions_file(_AFFORDANCE_DEFINITIONS_PATH)
    assert set(definitions) == {
        "affordance:resource:use",
        "affordance:portable:pick_up",
        "affordance:activatable:activate",
    }
    assert definition_hash(definitions["affordance:resource:use"]) == (
        "3d19203956ac8b3f4d1fccc2bbf9633d4d6e7ec347c041bb3d1b72daa4221522"
    )
    assert definition_hash(definitions["affordance:portable:pick_up"]) == (
        "e532abe76d155989e2bc7ec13683304900d274d31dfdbd8f441e296a1f1715e3"
    )
    assert definition_hash(definitions["affordance:activatable:activate"]) == (
        "1600db1742600f3b0ceb77c6a2a1b500b6ec8236914f89ddab02454833fc7296"
    )
    habitat_def = json.loads(_HABITAT_DEFINITION_PATH.read_text(encoding="utf-8"))
    payload = {
        key: habitat_def[key]
        for key in ("schema_version", "habitat_id", "zones", "objects")
    }
    assert sha256_hex(canon_json(payload)) == habitat_def["definition_hash"]


def test_manipulation_parameters_are_typed_and_bounded():
    assert validate_manipulation_parameters(PickUpParameters(hold_slot=0)) is None
    assert validate_manipulation_parameters(PickUpParameters(hold_slot=1)) == "HOLD_SLOT_UNAVAILABLE"
    assert validate_manipulation_parameters(PlaceParameters(target_x=5.0, target_y=4.0, expected_zone_id="zone:general")) is None
    assert validate_manipulation_parameters(PlaceParameters(target_x=99.0, target_y=4.0, expected_zone_id="zone:general")) == (
        "PLACEMENT_POSITION_INVALID"
    )
    assert validate_manipulation_parameters(PushParameters(direction_x=1.0, direction_y=0.0, requested_distance=1.0)) is None
    assert validate_manipulation_parameters(PushParameters(direction_x=0.0, direction_y=0.0, requested_distance=1.0)) == (
        "MALFORMED_MANIPULATION_REQUEST"
    )
    assert validate_manipulation_parameters(UseParameters()) is None


def _affordance_engine() -> HabitatAffordanceEngine:
    return HabitatAffordanceEngine(load_affordance_definitions_file(_AFFORDANCE_DEFINITIONS_PATH))


def _adapter_for(params, *, profile=None) -> AdapterValidatedManipulation:
    from umbra_core.embodiment_adapters import ABSTRACT_SHAPE_BODY_D009

    validated = profile or ABSTRACT_SHAPE_BODY_D009
    return AdapterValidatedManipulation(
        body_pose_view=BodyPoseView(
            body_instance_id="body:default",
            body_pose_version=1,
            position=Position(4.0, 3.0),
            collision_shape=BodyCollisionShape(0.5),
            attachment_generation=0,
        ),
        reach_profile=ReachProfile(reach_radius=3.0),
        requested_parameters=params,
        applied_parameters=params,
        validated_profile=validated,
    )


def _use_request_for_resource(state, obj) -> ManipulationRequest:
    defn = _affordance_engine().get_definition("affordance:resource:use")
    assert defn is not None
    engine = HabitatEngine(state)
    snapshot = engine.snapshot_view()
    return ManipulationRequest(
        request_id="req:use",
        execution_id="exec:use",
        capability="MANIPULATE",
        target_object_id=obj.object_id,
        affordance_id=defn.affordance_id,
        expected_habitat_version=snapshot.state_version,
        expected_habitat_state_hash=snapshot.state_hash,
        target_object_version=obj.object_version,
        target_object_definition_version=obj.definition_version,
        target_object_definition_hash=obj.definition_hash,
        affordance_definition_version=defn.definition_version,
        affordance_definition_hash=definition_hash(defn),
        body_instance_id="body:default",
        body_profile_id="ABSTRACT_SHAPE_BODY",
        attachment_generation=0,
        parameters=UseParameters(),
    )


def test_validate_rejects_precondition_failure_with_stable_code():
    state = sample_habitat_state()
    obj = replace(
        state.objects["resource:0"],
        affordance_ids=("affordance:resource:use",),
        state=ResourceState(remaining_yield=0.0),
    )
    obj = with_object_state_hash(obj)
    state = with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}))
    request = _use_request_for_resource(state, obj)
    result = _affordance_engine().validate(request, HabitatEngine(state).snapshot_view(), _adapter_for(UseParameters()))
    assert result.allowed is False
    assert result.failure_code == "AFFORDANCE_PRECONDITION_FAILED"
    assert result.effect_plan is None
    assert HabitatEngine(state).snapshot_view().state_hash == state.state_hash


def test_validate_rejects_cooldown_with_stable_code():
    state = sample_habitat_state()
    obj = replace(
        state.objects["resource:0"],
        affordance_ids=("affordance:resource:use",),
        cooldowns=(("affordance:resource:use", 25),),
    )
    obj = with_object_state_hash(obj)
    state = with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}, habitat_tick=10))
    request = _use_request_for_resource(state, obj)
    result = _affordance_engine().validate(request, HabitatEngine(state).snapshot_view(), _adapter_for(UseParameters()))
    assert result.allowed is False
    assert result.failure_code == "AFFORDANCE_COOLDOWN"
    assert result.effect_plan is None


def test_validate_success_returns_effect_plan_without_mutating_habitat():
    state = sample_habitat_state()
    obj = replace(state.objects["resource:0"], affordance_ids=("affordance:resource:use",))
    obj = with_object_state_hash(obj)
    state = with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}))
    engine = HabitatEngine(state)
    snapshot_before = engine.snapshot_view()
    request = _use_request_for_resource(state, obj)
    result = _affordance_engine().validate(request, snapshot_before, _adapter_for(UseParameters()))
    assert result.allowed is True
    assert result.failure_code is None
    assert result.effect_plan is not None
    assert result.effect_plan.requested_organism_effects
    assert engine.snapshot_view().state_hash == snapshot_before.state_hash


def test_use_effect_plan_emits_registered_state_changed_event():
    state = sample_habitat_state()
    obj = replace(state.objects["resource:0"], affordance_ids=("affordance:resource:use",))
    obj = with_object_state_hash(obj)
    state = with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}))
    request = _use_request_for_resource(state, obj)
    result = _affordance_engine().validate(
        request,
        HabitatEngine(state).snapshot_view(),
        _adapter_for(UseParameters()),
    )
    assert result.allowed is True
    assert result.effect_plan is not None
    event_types = [event["event_type"] for event in result.effect_plan.habitat_events]
    assert "habitat_object_used" not in event_types
    assert event_types == ["habitat_object_state_changed"]
    assert event_types[0] in HABITAT_EVENT_TYPES
    state_event = result.effect_plan.habitat_events[0]
    assert state_event["object_id"] == obj.object_id
    assert state_event["new_state"]["remaining_yield"] == pytest.approx(0.9)


# --- Task 5: execution journal + atomic commit --------------------------------


def _journal_store(tmp_path, name: str = "habitat.db"):
    from umbra_core.persistence import Store

    return Store(tmp_path / name)


def _journal_governance() -> Governance:
    from umbra_core.governance import Governance

    return Governance()


def _state_with_use_resource(state=None):
    state = sample_habitat_state() if state is None else state
    obj = replace(state.objects["resource:0"], affordance_ids=("affordance:resource:use",))
    obj = with_object_state_hash(obj)
    return with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}))


def _state_with_portable(state=None):
    state = sample_habitat_state() if state is None else state
    portable = HabitatObject(
        object_id="portable:0",
        object_kind=ObjectKind.PORTABLE_OBJECT,
        definition_version=1,
        definition_hash="a" * 64,
        object_version=1,
        object_state_hash="",
        location=FreeLocation(5.0, 3.0, "zone:general"),
        state=IdleState(),
        mass_class="LIGHT",
        portable=True,
        passable=True,
        occluded=False,
        collision_radius=0.8,
        affordance_ids=("affordance:portable:pick_up",),
        visibility="VISIBLE",
        condition=1.0,
        cooldowns=(),
    )
    portable = with_object_state_hash(portable)
    return with_state_hash(replace(state, objects={**state.objects, portable.object_id: portable}))


def _use_request(state, obj, *, execution_id="exec:use", request_id="req:use") -> ManipulationRequest:
    defn = _affordance_engine().get_definition("affordance:resource:use")
    assert defn is not None
    engine = HabitatEngine(state)
    snapshot = engine.snapshot_view()
    return ManipulationRequest(
        request_id=request_id,
        execution_id=execution_id,
        capability="MANIPULATE",
        target_object_id=obj.object_id,
        affordance_id=defn.affordance_id,
        expected_habitat_version=snapshot.state_version,
        expected_habitat_state_hash=snapshot.state_hash,
        target_object_version=obj.object_version,
        target_object_definition_version=obj.definition_version,
        target_object_definition_hash=obj.definition_hash,
        affordance_definition_version=defn.definition_version,
        affordance_definition_hash=definition_hash(defn),
        body_instance_id="body:default",
        body_profile_id="ABSTRACT_SHAPE_BODY",
        attachment_generation=0,
        parameters=UseParameters(),
    )


def _pick_up_request(state, obj, *, execution_id="exec:pick", request_id="req:pick") -> ManipulationRequest:
    defn = _affordance_engine().get_definition("affordance:portable:pick_up")
    assert defn is not None
    engine = HabitatEngine(state)
    snapshot = engine.snapshot_view()
    return ManipulationRequest(
        request_id=request_id,
        execution_id=execution_id,
        capability="MANIPULATE",
        target_object_id=obj.object_id,
        affordance_id=defn.affordance_id,
        expected_habitat_version=snapshot.state_version,
        expected_habitat_state_hash=snapshot.state_hash,
        target_object_version=obj.object_version,
        target_object_definition_version=obj.definition_version,
        target_object_definition_hash=obj.definition_hash,
        affordance_definition_version=defn.definition_version,
        affordance_definition_hash=definition_hash(defn),
        body_instance_id="body:default",
        body_profile_id="ABSTRACT_SHAPE_BODY",
        attachment_generation=0,
        parameters=PickUpParameters(hold_slot=0),
    )


def _place_request(state, obj, *, execution_id="exec:place", request_id="req:place") -> ManipulationRequest:
    engine = HabitatEngine(state)
    snapshot = engine.snapshot_view()
    return ManipulationRequest(
        request_id=request_id,
        execution_id=execution_id,
        capability="MANIPULATE",
        target_object_id=obj.object_id,
        affordance_id="affordance:portable:pick_up",
        expected_habitat_version=snapshot.state_version,
        expected_habitat_state_hash=snapshot.state_hash,
        target_object_version=obj.object_version,
        target_object_definition_version=obj.definition_version,
        target_object_definition_hash=obj.definition_hash,
        affordance_definition_version=1,
        affordance_definition_hash="e532abe76d155989e2bc7ec13683304900d274d31dfdbd8f441e296a1f1715e3",
        body_instance_id="body:default",
        body_profile_id="ABSTRACT_SHAPE_BODY",
        attachment_generation=0,
        parameters=PlaceParameters(target_x=7.0, target_y=4.0, expected_zone_id="zone:general"),
    )


def _commit_use(
    store,
    engine,
    phys,
    gov,
    *,
    execution_id="exec:use",
    request_id="req:use",
    crash_after_stage=None,
    request=None,
    validation=None,
):
    from umbra_core.habitat.execution_journal import commit_manipulation_transaction

    if request is None:
        state = engine.state
        obj = state.objects["resource:0"]
        request = _use_request(state, obj, execution_id=execution_id, request_id=request_id)
    if validation is None:
        validation = _affordance_engine().validate(
            request,
            engine.snapshot_view(),
            _adapter_for(UseParameters()),
        )
    return commit_manipulation_transaction(
        store,
        gov,
        engine,
        phys,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
        crash_after_stage=crash_after_stage,
    )


def test_execution_id_has_exactly_one_terminal_outcome(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_COMMITTED_SUCCESS
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    result = _commit_use(store, engine, phys, gov, execution_id="exec:one")
    assert result.journal_status == STATUS_COMMITTED_SUCCESS
    outcomes = [
        e for e in store.iter_events() if e["event_type"] == "outcome_verified"
    ]
    assert len([e for e in outcomes if e["payload"].get("execution_id") == "exec:one"]) == 1
    store.close()


def test_successful_execution_cannot_mutate_twice(tmp_path):
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    hash_before = engine.snapshot_view().state_hash
    energy_before = phys.energy
    state = engine.state
    obj = state.objects["resource:0"]
    request = _use_request(state, obj, execution_id="exec:dup")
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(UseParameters())
    )
    first = _commit_use(
        store, engine, phys, gov, execution_id="exec:dup", request=request, validation=validation
    )
    hash_after_first = engine.snapshot_view().state_hash
    second = _commit_use(
        store, engine, phys, gov, execution_id="exec:dup", request=request, validation=validation
    )
    assert second.idempotent_replay is True
    assert engine.snapshot_view().state_hash == hash_after_first != hash_before
    assert phys.energy == pytest.approx(energy_before + 0.1, rel=0, abs=1e-6)
    assert first.outcome is not None and second.outcome is not None
    assert first.outcome.outcome_id == second.outcome.outcome_id
    store.close()


def test_failed_execution_cannot_execute_after_restart(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_COMMITTED_FAILURE, commit_manipulation_transaction
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    state = engine.state
    obj = replace(
        state.objects["resource:0"],
        state=ResourceState(remaining_yield=0.0),
    )
    obj = with_object_state_hash(obj)
    state = with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}))
    engine = HabitatEngine(state)
    request = _use_request(state, obj)
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(UseParameters())
    )
    assert validation.allowed is False
    result = commit_manipulation_transaction(
        store,
        gov,
        engine,
        phys,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert result.journal_status == STATUS_COMMITTED_FAILURE
    hash_before = engine.snapshot_view().state_hash

    engine2 = HabitatEngine(state)
    phys2 = Physiology()
    gov2 = _journal_governance()
    replay = commit_manipulation_transaction(
        store,
        gov2,
        engine2,
        phys2,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=2,
        monotonic_time=2.0,
        wall_time=2.0,
    )
    assert replay.idempotent_replay is True
    assert replay.journal_status == STATUS_COMMITTED_FAILURE
    assert engine2.snapshot_view().state_hash == hash_before
    store.close()


def test_prepared_execution_recovers_deterministically(tmp_path):
    from umbra_core.habitat.execution_journal import (
        STATUS_COMMITTED_SUCCESS,
        STATUS_PREPARED,
        commit_manipulation_transaction,
        prepare_execution,
        recover_execution,
    )
    from umbra_core.persistence import PersistenceError
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    state = engine.state
    obj = state.objects["resource:0"]
    request = _use_request(state, obj, execution_id="exec:recover")
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(UseParameters())
    )
    prepared = prepare_execution(store, request, prepared_tick=1, transaction_id="txn:recover")
    assert prepared.status == STATUS_PREPARED
    with pytest.raises(PersistenceError):
        commit_manipulation_transaction(
            store,
            gov,
            engine,
            phys,
            request,
            validation,
            agent_id="agent:test",
            prepared_tick=1,
            monotonic_time=1.0,
            wall_time=1.0,
            transaction_id="txn:recover",
            crash_after_stage=1,
        )
    row = store.get_habitat_execution_journal("exec:recover")
    assert row is not None and row["status"] == STATUS_PREPARED
    recovered = recover_execution(store, "exec:recover", agent_id="agent:test")
    assert recovered is not None and recovered.journal_status == STATUS_PREPARED
    engine2 = HabitatEngine(state)
    phys2 = Physiology()
    gov2 = _journal_governance()
    final = commit_manipulation_transaction(
        store,
        gov2,
        engine2,
        phys2,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=1,
        monotonic_time=2.0,
        wall_time=2.0,
        transaction_id="txn:recover",
    )
    assert final.journal_status == STATUS_COMMITTED_SUCCESS
    assert phys2.energy == pytest.approx(phys.energy + 0.1, rel=0, abs=1e-6)
    store.close()


def test_same_execution_id_with_different_payload_fails_closed(tmp_path):
    from umbra_core.habitat.execution_journal import ExecutionJournalError, prepare_execution

    store = _journal_store(tmp_path)
    state = _state_with_use_resource()
    obj = state.objects["resource:0"]
    req_a = _use_request(state, obj, execution_id="exec:mismatch", request_id="req:a")
    prepare_execution(store, req_a, prepared_tick=1)
    req_b = replace(req_a, request_id="req:b", target_object_version=obj.object_version + 99)
    with pytest.raises(ExecutionJournalError) as exc:
        prepare_execution(store, req_b, prepared_tick=2)
    assert exc.value.code == "EXECUTION_PAYLOAD_MISMATCH"
    store.close()


def test_same_request_id_with_different_payload_fails_closed(tmp_path):
    from umbra_core.habitat.execution_journal import ExecutionJournalError, prepare_execution

    store = _journal_store(tmp_path)
    state = _state_with_use_resource()
    obj = state.objects["resource:0"]
    req_a = _use_request(state, obj, execution_id="exec:a", request_id="req:same")
    prepare_execution(store, req_a, prepared_tick=1)
    req_b = _use_request(state, obj, execution_id="exec:b", request_id="req:same")
    with pytest.raises(ExecutionJournalError) as exc:
        prepare_execution(store, req_b, prepared_tick=2)
    assert exc.value.code == "EXECUTION_PAYLOAD_MISMATCH"
    store.close()


def test_prepared_without_evidence_stays_prepared_on_recovery(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_PREPARED, prepare_execution, recover_execution

    store = _journal_store(tmp_path)
    state = _state_with_use_resource()
    obj = state.objects["resource:0"]
    request = _use_request(state, obj, execution_id="exec:unknown")
    prepared = prepare_execution(store, request, prepared_tick=1, transaction_id="txn:unknown")
    row = store.get_habitat_execution_journal("exec:unknown")
    assert row is not None
    assert row["status"] == STATUS_PREPARED
    assert row.get("failure_code") is None
    assert prepared.failure_code is None
    recovered = recover_execution(store, "exec:unknown", agent_id="agent:test")
    assert recovered is not None
    assert recovered.journal_status == STATUS_PREPARED
    assert recovered.outcome is None
    assert recovered.failure_code is None
    store.close()


def test_committed_success_idempotent_replay_rehydrates_stale_engine(tmp_path):
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    initial_state = _state_with_use_resource()
    engine = HabitatEngine(initial_state)
    phys = Physiology()
    gov = _journal_governance()
    state = engine.state
    obj = state.objects["resource:0"]
    request = _use_request(state, obj, execution_id="exec:rehydrate")
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(UseParameters())
    )
    first = _commit_use(
        store, engine, phys, gov, execution_id="exec:rehydrate", request=request, validation=validation
    )
    hash_after = engine.snapshot_view().state_hash
    energy_after = phys.energy

    engine2 = HabitatEngine(initial_state)
    phys2 = Physiology()
    replay = _commit_use(
        store, engine2, phys2, gov, execution_id="exec:rehydrate", request=request, validation=validation
    )
    assert replay.idempotent_replay is True
    assert first.outcome is not None and replay.outcome is not None
    assert first.outcome.outcome_id == replay.outcome.outcome_id
    assert engine2.snapshot_view().state_hash == hash_after
    assert phys2.energy == pytest.approx(energy_after, rel=0, abs=1e-6)
    store.close()


def test_collection_cap_exceeded_commits_durable_failure(tmp_path):
    from umbra_core.habitat.execution_journal import (
        HABITAT_COLLECTION_CAP_EXCEEDED,
        STATUS_COMMITTED_FAILURE,
        commit_manipulation_transaction,
    )
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    state = _state_with_portable()
    zone = replace(state.zones["zone:general"], occupancy_limit=1)
    state = with_state_hash(replace(state, zones={**state.zones, "zone:general": zone}))
    held_obj = replace(
        state.objects["portable:0"],
        location=HeldByLocation(body_instance_id="body:default", attachment_generation=0, hold_slot=0),
    )
    held_obj = with_object_state_hash(held_obj)
    state = with_state_hash(replace(state, objects={**state.objects, held_obj.object_id: held_obj}))
    engine = HabitatEngine(state)
    hash_before = engine.snapshot_view().state_hash
    request = _place_request(state, held_obj, execution_id="exec:cap")
    validation = AffordanceValidationResult(
        allowed=True,
        failure_code=None,
        expected_object_version=held_obj.object_version,
        expected_habitat_version=engine.snapshot_view().state_version,
        effect_plan=HabitatEffectPlan(
            habitat_mutations=(
                {
                    "mutation_kind": "SET_LOCATION",
                    "object_id": held_obj.object_id,
                    "location": {
                        "mode": "FREE",
                        "x": 7.0,
                        "y": 4.0,
                        "zone_id": "zone:general",
                    },
                },
            ),
            habitat_events=({"event_type": "habitat_object_placed", "object_id": held_obj.object_id},),
            requested_organism_effects=(),
        ),
        applied_parameters=PlaceParameters(target_x=7.0, target_y=4.0, expected_zone_id="zone:general"),
    )
    phys = Physiology()
    gov = _journal_governance()
    result = commit_manipulation_transaction(
        store,
        gov,
        engine,
        phys,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert result.journal_status == STATUS_COMMITTED_FAILURE
    assert result.failure_code == HABITAT_COLLECTION_CAP_EXCEEDED
    assert engine.snapshot_view().state_hash == hash_before
    outcomes = [e for e in store.iter_events() if e["event_type"] == "outcome_verified"]
    assert any(
        e["payload"].get("execution_id") == "exec:cap"
        and e["payload"].get("reason") == HABITAT_COLLECTION_CAP_EXCEEDED
        for e in outcomes
    )
    store.close()


def test_event_storage_budget_exceeded_commits_durable_failure(tmp_path):
    from umbra_core.habitat.execution_journal import (
        EVENT_STORAGE_BUDGET_EXCEEDED,
        STATUS_COMMITTED_FAILURE,
    )
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    _commit_use(store, engine, phys, gov, execution_id="exec:budget-fill", request_id="req:budget-fill")
    store.event_storage_budget = len(store.iter_events()) + 1
    engine2 = HabitatEngine(_state_with_use_resource())
    phys2 = Physiology()
    hash_before = engine2.snapshot_view().state_hash
    result = _commit_use(
        store, engine2, phys2, gov, execution_id="exec:budget-exceed", request_id="req:budget-exceed"
    )
    assert result.journal_status == STATUS_COMMITTED_FAILURE
    assert result.failure_code == EVENT_STORAGE_BUDGET_EXCEEDED
    assert engine2.snapshot_view().state_hash == hash_before
    outcomes = [e for e in store.iter_events() if e["event_type"] == "outcome_verified"]
    assert any(
        e["payload"].get("execution_id") == "exec:budget-exceed"
        and e["payload"].get("reason") == EVENT_STORAGE_BUDGET_EXCEEDED
        for e in outcomes
    )
    store.close()


def test_prepared_recovery_cannot_double_mutate(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_COMMITTED_SUCCESS, commit_manipulation_transaction
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    state = engine.state
    obj = state.objects["resource:0"]
    request = _use_request(state, obj, execution_id="exec:once")
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(UseParameters())
    )
    first = _commit_use(
        store, engine, phys, gov, execution_id="exec:once", request=request, validation=validation
    )
    assert first.journal_status == STATUS_COMMITTED_SUCCESS
    version_after = engine.snapshot_view().state_version
    second = _commit_use(
        store, engine, phys, gov, execution_id="exec:once", request=request, validation=validation
    )
    assert second.idempotent_replay is True
    assert engine.snapshot_view().state_version == version_after
    store.close()


def test_resource_and_organism_effect_commit_atomically(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_COMMITTED_SUCCESS
    from umbra_core.persistence import PersistenceError
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    energy_before = phys.energy
    yield_before = engine.get_object("resource:0").state.remaining_yield  # type: ignore[union-attr]
    with pytest.raises(PersistenceError):
        _commit_use(store, engine, phys, gov, execution_id="exec:atomic", crash_after_stage=2)
    assert engine.get_object("resource:0").state.remaining_yield == yield_before  # type: ignore[union-attr]
    assert phys.energy == energy_before
    journal = store.get_habitat_execution_journal("exec:atomic")
    assert journal is not None and journal["status"] == "PREPARED"
    result = _commit_use(store, engine, phys, gov, execution_id="exec:atomic")
    assert result.journal_status == STATUS_COMMITTED_SUCCESS
    assert engine.get_object("resource:0").state.remaining_yield == pytest.approx(yield_before - 0.1)  # type: ignore[union-attr]
    assert phys.energy == pytest.approx(energy_before + 0.1, rel=0, abs=1e-6)
    store.close()


def test_object_pickup_is_atomic(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_COMMITTED_SUCCESS, commit_manipulation_transaction
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    state = _state_with_portable()
    engine = HabitatEngine(state)
    obj = engine.get_object("portable:0")
    assert obj is not None
    request = _pick_up_request(state, obj)
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(PickUpParameters(hold_slot=0))
    )
    assert validation.allowed is True
    phys = Physiology()
    gov = _journal_governance()
    result = commit_manipulation_transaction(
        store,
        gov,
        engine,
        phys,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert result.journal_status == STATUS_COMMITTED_SUCCESS
    picked = engine.get_object("portable:0")
    assert picked is not None and isinstance(picked.location, HeldByLocation)
    habitat_events = [e for e in store.iter_events() if e["event_type"] == "habitat_object_picked_up"]
    assert len(habitat_events) == 1
    store.close()


def test_object_place_is_atomic(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_COMMITTED_SUCCESS, commit_manipulation_transaction
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    state = _state_with_portable()
    held_obj = replace(
        state.objects["portable:0"],
        location=HeldByLocation(body_instance_id="body:default", attachment_generation=0, hold_slot=0),
    )
    held_obj = with_object_state_hash(held_obj)
    state = with_state_hash(replace(state, objects={**state.objects, held_obj.object_id: held_obj}))
    engine = HabitatEngine(state)
    request = _place_request(state, held_obj)
    validation = AffordanceValidationResult(
        allowed=True,
        failure_code=None,
        expected_object_version=held_obj.object_version,
        expected_habitat_version=engine.snapshot_view().state_version,
        effect_plan=HabitatEffectPlan(
            habitat_mutations=(
                {
                    "mutation_kind": "SET_LOCATION",
                    "object_id": held_obj.object_id,
                    "location": {
                        "mode": "FREE",
                        "x": 7.0,
                        "y": 4.0,
                        "zone_id": "zone:general",
                    },
                },
            ),
            habitat_events=({"event_type": "habitat_object_placed", "object_id": held_obj.object_id},),
            requested_organism_effects=(),
        ),
        applied_parameters=PlaceParameters(target_x=7.0, target_y=4.0, expected_zone_id="zone:general"),
    )
    phys = Physiology()
    gov = _journal_governance()
    result = commit_manipulation_transaction(
        store,
        gov,
        engine,
        phys,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert result.journal_status == STATUS_COMMITTED_SUCCESS
    placed = engine.get_object("portable:0")
    assert placed is not None and isinstance(placed.location, FreeLocation)
    assert placed.location.x == 7.0
    store.close()


def test_object_cannot_exist_in_two_locations(tmp_path):
    from umbra_core.habitat.execution_journal import commit_manipulation_transaction
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    state = _state_with_portable()
    engine = HabitatEngine(state)
    obj = engine.get_object("portable:0")
    assert obj is not None
    request = _pick_up_request(state, obj)
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(PickUpParameters(hold_slot=0))
    )
    phys = Physiology()
    gov = _journal_governance()
    commit_manipulation_transaction(
        store,
        gov,
        engine,
        phys,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    picked = engine.get_object("portable:0")
    assert picked is not None and isinstance(picked.location, HeldByLocation)
    free_matches = [
        oid
        for oid, o in engine.state.objects.items()
        if oid == "portable:0" and isinstance(o.location, FreeLocation)
    ]
    assert free_matches == []
    store.close()


def test_failed_manipulation_has_durable_outcome(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_COMMITTED_FAILURE, commit_manipulation_transaction
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    state = engine.state
    obj = replace(state.objects["resource:0"], cooldowns=(("affordance:resource:use", 99),))
    obj = with_object_state_hash(obj)
    state = with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}, habitat_tick=10))
    engine = HabitatEngine(state)
    request = _use_request(state, obj, execution_id="exec:fail")
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(UseParameters())
    )
    result = commit_manipulation_transaction(
        store,
        gov,
        engine,
        phys,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=10,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert result.journal_status == STATUS_COMMITTED_FAILURE
    assert result.failure_code == "AFFORDANCE_COOLDOWN"
    outcomes = [e for e in store.iter_events() if e["event_type"] == "outcome_verified"]
    assert any(e["payload"].get("execution_id") == "exec:fail" for e in outcomes)
    store.close()


def test_invalid_manipulation_changes_no_habitat_state(tmp_path):
    from umbra_core.habitat.execution_journal import commit_manipulation_transaction
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    state = _state_with_use_resource()
    obj = replace(state.objects["resource:0"], state=ResourceState(remaining_yield=0.0))
    obj = with_object_state_hash(obj)
    state = with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}))
    engine = HabitatEngine(state)
    phys = Physiology()
    gov = _journal_governance()
    hash_before = engine.snapshot_view().state_hash
    request = _use_request(state, obj)
    validation = _affordance_engine().validate(
        request, engine.snapshot_view(), _adapter_for(UseParameters())
    )
    commit_manipulation_transaction(
        store,
        gov,
        engine,
        phys,
        request,
        validation,
        agent_id="agent:test",
        prepared_tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert engine.snapshot_view().state_hash == hash_before
    store.close()


def test_crash_during_manipulation_cannot_partially_commit(tmp_path):
    from umbra_core.habitat.execution_journal import STATUS_PREPARED
    from umbra_core.persistence import PersistenceError
    from umbra_core.physiology import Physiology

    store = _journal_store(tmp_path)
    engine = HabitatEngine(_state_with_use_resource())
    phys = Physiology()
    gov = _journal_governance()
    hash_before = engine.snapshot_view().state_hash
    for stage in range(1, 5):
        engine_s = HabitatEngine(_state_with_use_resource())
        phys_s = Physiology()
        gov_s = _journal_governance()
        with pytest.raises(PersistenceError):
            _commit_use(
                store,
                engine_s,
                phys_s,
                gov_s,
                execution_id=f"exec:crash{stage}",
                request_id=f"req:crash{stage}",
                crash_after_stage=stage,
            )
        journal = store.get_habitat_execution_journal(f"exec:crash{stage}")
        assert journal is not None and journal["status"] == STATUS_PREPARED
        habitat_types = {
            e["event_type"]
            for e in store.iter_events()
            if e["event_type"].startswith("habitat_")
            and e["payload"].get("execution_id") == f"exec:crash{stage}"
        }
        assert habitat_types == set()
        assert engine_s.snapshot_view().state_hash == hash_before
    store.close()


# --- Task 6: D-009 profiles + validate_manipulation + migration ----------------


def test_d008_profile_definitions_remain_unchanged():
    import json
    from pathlib import Path

    from umbra_core.embodiment_adapters import (
        ABSTRACT_SHAPE_BODY,
        MINIMAL_CREATURE_BODY,
        profile_definition_hash,
    )

    thresholds = json.loads(
        Path("experiments/d008/thresholds.json").read_text(encoding="utf-8")
    )
    for profile in (ABSTRACT_SHAPE_BODY, MINIMAL_CREATURE_BODY):
        digest = profile_definition_hash(profile)
        assert thresholds["production_profile_definition_hashes"][profile.profile_id] == digest
        assert profile.schema_version == "d008.body-profile.v1"
        assert "MANIPULATE" not in profile.supported_capabilities


def test_d009_profiles_add_manipulate_and_hold_fields():
    from umbra_core.embodiment_adapters import (
        ABSTRACT_SHAPE_BODY_D009,
        hold_anchor,
        hold_slot_count,
        maximum_held_mass_class,
        profile_definition_hash,
    )

    profile = ABSTRACT_SHAPE_BODY_D009
    assert profile.schema_version == "d009.body-profile.v1"
    assert "MANIPULATE" in profile.supported_capabilities
    assert hold_slot_count(profile) == 1
    assert maximum_held_mass_class(profile) == "LIGHT"
    assert hold_anchor(profile) == {"x": 0.4, "y": 0.2}
    assert profile_definition_hash(profile) != profile_definition_hash(
        __import__("umbra_core.embodiment_adapters", fromlist=["ABSTRACT_SHAPE_BODY"]).ABSTRACT_SHAPE_BODY
    )


def test_manipulate_requires_supported_body_profile(tmp_path):
    from umbra_core.embodiment_adapters import (
        ABSTRACT_SHAPE_BODY,
        EmbodimentAdapter,
        ManipulationValidationError,
    )
    from umbra_core.persistence import Store

    store = Store(str(tmp_path / "adapter.sqlite"))
    adapter = EmbodimentAdapter(
        store=store,
        agent_id="agent:test",
        profile_resolver=lambda _: ABSTRACT_SHAPE_BODY,
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    adapter.attach(ABSTRACT_SHAPE_BODY.profile_id, profile_resolver=lambda _: ABSTRACT_SHAPE_BODY)
    emb = Embodiment()
    with pytest.raises(ManipulationValidationError) as exc:
        adapter.validate_manipulation(
            capability="MANIPULATE",
            parameters=UseParameters(),
            attachment_generation=adapter.state.attachment_generation,
            body_instance_id=adapter.state.body_instance_id,
            embodiment=emb,
        )
    assert exc.value.failure_code == "UNSUPPORTED_BODY_CAPABILITY"
    store.close()


def test_adapter_cannot_change_operation_or_target(tmp_path):
    from umbra_core.embodiment_adapters import ABSTRACT_SHAPE_BODY_D009, EmbodimentAdapter
    from umbra_core.persistence import Store

    store = Store(str(tmp_path / "validate.sqlite"))
    adapter = EmbodimentAdapter(
        store=store,
        agent_id="agent:test",
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    adapter.attach(ABSTRACT_SHAPE_BODY_D009.profile_id)
    emb = Embodiment()
    emb.body.x = 4.0
    emb.body.y = 3.0
    params = PickUpParameters(hold_slot=0)
    validated = adapter.validate_manipulation(
        capability="MANIPULATE",
        parameters=params,
        attachment_generation=adapter.state.attachment_generation,
        body_instance_id=adapter.state.body_instance_id,
        embodiment=emb,
    )
    assert validated.requested_parameters == params
    assert validated.applied_parameters == params
    assert validated.requested_parameters.kind == "PICK_UP"
    assert validated.translation_applied is False
    store.close()


def _attach_d008_adapter(store, agent_id: str = "agent:test") -> EmbodimentAdapter:
    from umbra_core.embodiment_adapters import ABSTRACT_SHAPE_BODY, EmbodimentAdapter, get_d008_profile

    adapter = EmbodimentAdapter(
        store=store,
        agent_id=agent_id,
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    adapter.attach(ABSTRACT_SHAPE_BODY.profile_id, profile_resolver=get_d008_profile)
    return adapter


def test_d009_profile_migration_swaps_d008_hash_once(tmp_path):
    from umbra_core.embodiment_adapters import (
        ABSTRACT_SHAPE_BODY,
        get_d008_profile,
        is_d009_profile_hash,
        profile_definition_hash,
    )
    from umbra_core.runtime import maybe_migrate_d009_profile
    from umbra_core.persistence import Store

    store = Store(str(tmp_path / "migrate.sqlite"))
    adapter = _attach_d008_adapter(store)
    org = _minimal_organism_for_migration(store, adapter)
    assert maybe_migrate_d009_profile(store, org) is True
    swap_events = [e for e in store.iter_events() if e["event_type"] == "embodiment_body_profile_swapped"]
    assert len(swap_events) == 1
    assert swap_events[0]["payload"]["origin"] == "D009_PROFILE_MIGRATION"
    assert is_d009_profile_hash(
        ABSTRACT_SHAPE_BODY.profile_id,
        swap_events[0]["payload"]["profile_definition_hash"],
    )
    assert swap_events[0]["payload"]["old_profile_definition_hash"] == profile_definition_hash(
        get_d008_profile(ABSTRACT_SHAPE_BODY.profile_id)
    )
    assert maybe_migrate_d009_profile(store, org) is False
    assert len([e for e in store.iter_events() if e["event_type"] == "embodiment_body_profile_swapped"]) == 1
    store.close()


def test_d009_profile_migration_unknown_source_fails_closed(tmp_path):
    from umbra_core.embodiment_adapters import ProfileMigrationError
    from umbra_core.runtime import maybe_migrate_d009_profile
    from umbra_core.persistence import Store

    store = Store(str(tmp_path / "unknown.sqlite"))
    adapter = _attach_d008_adapter(store)
    events = list(store.iter_events())
    attach = events[-1]
    store.corrupt_event_payload(
        attach["sequence"],
        {**attach["payload"], "profile_definition_hash": "deadbeef" * 8},
    )
    org = _minimal_organism_for_migration(store, adapter)
    with pytest.raises(ProfileMigrationError, match="UMBRA_D009_PROFILE_MIGRATION_FAIL"):
        maybe_migrate_d009_profile(store, org)
    store.close()


def test_profile_swap_rebases_held_object_generation_atomically(tmp_path):
    from umbra_core.embodiment_adapters import get_d008_profile, profile_definition_hash
    from umbra_core.runtime import maybe_migrate_d009_profile
    from umbra_core.persistence import Store

    store = Store(str(tmp_path / "held.sqlite"))
    adapter = _attach_d008_adapter(store)
    state = _state_with_portable()
    body_id = adapter.state.body_instance_id
    portable = state.objects["portable:0"]
    held_state = with_state_hash(
        replace(
            state,
            objects={
                **state.objects,
                "portable:0": with_object_state_hash(
                    replace(
                        portable,
                        location=HeldByLocation(
                            body_instance_id=body_id,
                            attachment_generation=adapter.state.attachment_generation,
                            hold_slot=0,
                        ),
                    )
                ),
            },
        )
    )
    org = _minimal_organism_for_migration(store, adapter)
    engine = HabitatEngine(held_state)
    org.embodiment.attach_habitat_engine(engine)
    assert maybe_migrate_d009_profile(store, org) is True
    swap_events = [e for e in store.iter_events() if e["event_type"] == "embodiment_body_profile_swapped"]
    rebase_events = [e for e in store.iter_events() if e["event_type"] == "habitat_held_binding_rebased"]
    assert len(swap_events) == 1
    assert len(rebase_events) == 1
    assert rebase_events[0]["payload"]["new_attachment_generation"] == swap_events[0]["payload"]["new_generation"]
    held = engine.get_object("portable:0")
    assert held is not None and isinstance(held.location, HeldByLocation)
    assert held.location.attachment_generation == adapter.state.attachment_generation
    assert swap_events[0]["payload"]["profile_definition_hash"] != profile_definition_hash(
        get_d008_profile("ABSTRACT_SHAPE_BODY")
    )
    store.close()


def test_incompatible_profile_swap_with_held_object_fails(tmp_path):
    from umbra_core.embodiment_adapters import ProfileMigrationError
    from umbra_core.runtime import maybe_migrate_d009_profile
    from umbra_core.persistence import Store

    store = Store(str(tmp_path / "heavy.sqlite"))
    adapter = _attach_d008_adapter(store)
    state = _state_with_portable()
    body_id = adapter.state.body_instance_id
    portable = replace(state.objects["portable:0"], mass_class="HEAVY")
    held_state = with_state_hash(
        replace(
            state,
            objects={
                **state.objects,
                "portable:0": with_object_state_hash(
                    replace(
                        portable,
                        location=HeldByLocation(
                            body_instance_id=body_id,
                            attachment_generation=adapter.state.attachment_generation,
                            hold_slot=0,
                        ),
                    )
                ),
            },
        )
    )
    org = _minimal_organism_for_migration(store, adapter)
    engine = HabitatEngine(held_state)
    org.embodiment.attach_habitat_engine(engine)
    with pytest.raises(ProfileMigrationError, match="UMBRA_D009_PROFILE_MIGRATION_FAIL"):
        maybe_migrate_d009_profile(store, org)
    assert [e for e in store.iter_events() if e["event_type"] == "embodiment_body_profile_swapped"] == []
    store.close()


def _minimal_organism_for_migration(store, adapter):
    from types import SimpleNamespace

    from umbra_core.runtime import Organism, OrganismConfig

    identity = SimpleNamespace(agent_id="agent:test")
    config = OrganismConfig(db_path="unused", wall_time_fn=lambda: 0.0)
    return Organism(
        identity=identity,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        embodiment=Embodiment(),
        perception=__import__("umbra_core.perception", fromlist=["PerceptionMembrane"]).PerceptionMembrane(),
        arbitrator=__import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator(
            __import__("umbra_core.arbitration", fromlist=["ArbitrationState"]).ArbitrationState()
        ),
        governance=__import__("umbra_core.governance", fromlist=["Governance"]).Governance(
            __import__("umbra_core.governance", fromlist=["GovernanceState"]).GovernanceState()
        ),
        rng=__import__("umbra_core.util", fromlist=["SeededRNG"]).SeededRNG(1),
        config=config,
        embodiment_adapter=adapter,
    )


# --- Task 7: address-only candidates + trusted resolve + governance path -------


def _task7_habitat_setup(*, hidden_resource: bool = False):
    from umbra_core.embodiment_adapters import ABSTRACT_SHAPE_BODY_D009, EmbodimentAdapter
    from umbra_core.perception import PerceptionMembrane
    from umbra_core.util import SeededRNG

    state = _state_with_use_resource()
    if hidden_resource:
        obj = replace(
            state.objects["resource:0"],
            visibility="HIDDEN",
            affordance_ids=("affordance:resource:use",),
        )
        obj = with_object_state_hash(obj)
        state = with_state_hash(replace(state, objects={obj.object_id: obj}))
    engine = HabitatEngine(state)
    emb = Embodiment()
    emb.body.x = 4.0
    emb.body.y = 3.0
    emb.attach_habitat_engine(engine)
    perception = PerceptionMembrane(false_negative_rate=0.0, noise_sigma=0.0)
    rng = SeededRNG(42)
    perception.perceive_habitat_objects(emb, 1.0, rng)
    adapter = EmbodimentAdapter(
        store=__import__("umbra_core.persistence", fromlist=["Store"]).Store(":memory:"),
        agent_id="agent:test",
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    adapter.attach(ABSTRACT_SHAPE_BODY_D009.profile_id)
    return engine, emb, perception, adapter, rng


def _task7_manipulation_candidate(perception, arbitrator):
    bindings = perception.policy_view()["manipulation_bindings"]
    cands = arbitrator.generate_manipulation_candidates(bindings, __import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(), 1)
    use_cands = [c for c in cands if c.perceived_affordance_ref == "affordance:resource:use"]
    assert use_cands, "expected use manipulation candidate"
    return use_cands[0]


def test_policy_candidate_contains_no_authoritative_object_id():
    from umbra_core.arbitration import Arbitrator
    from umbra_core.perception import assert_no_world_truth

    _, _, perception, _, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, Arbitrator())
    payload = mc.as_dict()
    assert "target_object_id" not in payload
    assert "object_id" not in str(payload)
    cand = mc.to_candidate()
    assert "target_object_id" not in cand.params
    assert_no_world_truth(cand.params)


def test_trusted_runtime_resolves_address_to_authoritative_object():
    from umbra_core.perception import resolve_manipulation_address

    engine, _, perception, _, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    resolved = resolve_manipulation_address(
        target_address_ref=mc.target_address_ref,
        perception_evidence_ref=mc.perception_evidence_ref,
        perception_state_version=mc.perception_state_version,
        bindings=perception.object_bindings,
        habitat_engine=engine,
    )
    assert resolved.target_object_id == "resource:0"
    assert resolved.target_object_version == engine.get_object("resource:0").object_version


def test_hidden_object_ids_never_enter_arbitration():
    from umbra_core.arbitration import Arbitrator

    engine, emb, perception, _, rng = _task7_habitat_setup(hidden_resource=True)
    hidden_id = "resource:0"
    arbitrator = Arbitrator()
    bindings = perception.policy_view()["manipulation_bindings"]
    cands = arbitrator.generate_manipulation_candidates(bindings, __import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(), 1)
    arbitration_blob = str(bindings) + str([c.as_dict() for c in cands])
    assert hidden_id not in arbitration_blob
    perception.perceive_habitat_objects(emb, 2.0, rng)
    assert hidden_id not in str(perception.policy_view())


def test_hidden_objects_do_not_generate_manipulation_candidates():
    from umbra_core.arbitration import Arbitrator

    _, _, perception, _, _ = _task7_habitat_setup(hidden_resource=True)
    bindings = perception.policy_view()["manipulation_bindings"]
    cands = Arbitrator().generate_manipulation_candidates(
        bindings,
        __import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        1,
    )
    assert all(b["perceived_object_kind"] != "resource" for b in bindings)
    assert all(c.perceived_object_kind != "resource" for c in cands)


def test_manipulate_requires_current_address_binding(tmp_path):
    from umbra_core.governance import Governance, GovernanceState

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", mc.to_candidate().params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=[],
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is False
    assert outcome.reason == "OBJECT_NOT_PERCEIVED"
    store.close()


def test_stale_object_address_binding_fails_closed(tmp_path):
    from umbra_core.governance import Governance, GovernanceState

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    params = mc.to_candidate().params
    params["perception_state_version"] = mc.perception_state_version - 1
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=perception.object_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is False
    assert outcome.reason == "OBJECT_ADDRESS_BINDING_STALE"
    store.close()


def test_ambiguous_object_address_binding_fails_closed(tmp_path):
    from umbra_core.governance import Governance, GovernanceState
    from umbra_core.perception import ObjectAddressBinding

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    dup = ObjectAddressBinding(
        target_address_ref=mc.target_address_ref,
        perception_evidence_ref=mc.perception_evidence_ref,
        perception_state_version=mc.perception_state_version,
        binding_hash="dup",
        object_id="rest:0",
        object_version=engine.get_object("rest:0").object_version,
        perceived_object_kind="rest",
        perceived_affordance_refs=("affordance:resource:use",),
        relative_direction=0.0,
        estimated_distance=1.0,
    )
    bindings = list(perception.object_bindings) + [dup]
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", mc.to_candidate().params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is False
    assert outcome.reason == "OBJECT_ADDRESS_AMBIGUOUS"
    store.close()


def test_manipulate_requires_governance(tmp_path):
    from umbra_core.governance import Governance, GovernanceDecision, GovernanceState

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", mc.to_candidate().params)
    denied = gov.admit(
        gov.propose("MANIPULATE", {**mc.to_candidate().params, "target_object_id": "resource:0"}),
        tick=1,
    )
    assert denied.admitted is False
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    no_admit = gov.execute_manipulation(
        proposal,
        GovernanceDecision(False, "policy", "denied", proposal.proposal_id, "MANIPULATE"),
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=perception.object_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert no_admit is None
    hash_before = engine.snapshot_view().state_hash
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=perception.object_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is True
    assert engine.snapshot_view().state_hash != hash_before
    store.close()


def test_valid_manipulation_changes_habitat(tmp_path):
    from umbra_core.governance import Governance, GovernanceState

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", mc.to_candidate().params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    hash_before = engine.snapshot_view().state_hash
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=perception.object_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is True
    assert engine.snapshot_view().state_hash != hash_before
    obj = engine.get_object("resource:0")
    assert isinstance(obj.state, ResourceState)
    assert obj.state.remaining_yield == pytest.approx(0.9)
    store.close()


def test_stale_object_version_fails_closed(tmp_path):
    from umbra_core.governance import Governance, GovernanceState
    from umbra_core.perception import ObjectAddressBinding

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    stale_bindings = [
        ObjectAddressBinding(
            target_address_ref=b.target_address_ref,
            perception_evidence_ref=b.perception_evidence_ref,
            perception_state_version=b.perception_state_version,
            binding_hash=b.binding_hash,
            object_id=b.object_id,
            object_version=b.object_version + 99 if b.object_id == "resource:0" else b.object_version,
            perceived_object_kind=b.perceived_object_kind,
            perceived_affordance_refs=b.perceived_affordance_refs,
            relative_direction=b.relative_direction,
            estimated_distance=b.estimated_distance,
        )
        for b in perception.object_bindings
    ]
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", mc.to_candidate().params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=stale_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is False
    assert outcome.reason == "OBJECT_ADDRESS_BINDING_STALE"
    store.close()


def test_object_out_of_range_fails(tmp_path):
    from umbra_core.governance import Governance, GovernanceState

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    emb.body.x = -15.0
    emb.body.y = -15.0
    emb.body.sensor_range = 2.0
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", mc.to_candidate().params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    hash_before = engine.snapshot_view().state_hash
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=perception.object_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is False
    assert outcome.reason == "OBJECT_OUT_OF_RANGE"
    assert engine.snapshot_view().state_hash == hash_before
    store.close()


def test_unsupported_affordance_fails(tmp_path):
    from umbra_core.governance import Governance, GovernanceState

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    params = mc.to_candidate().params
    params["perceived_affordance_ref"] = "affordance:missing:noop"
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=perception.object_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is False
    assert outcome.reason == "AFFORDANCE_NOT_SUPPORTED"
    store.close()


def test_object_definition_mismatch_fails_closed(tmp_path):
    from umbra_core.governance import Governance, GovernanceState
    from umbra_core.habitat_affordances.engine import ManipulationRequest, UseParameters

    state = _state_with_use_resource()
    obj = replace(state.objects["resource:0"], definition_hash="0" * 64)
    obj = with_object_state_hash(obj)
    state = with_state_hash(replace(state, objects={**state.objects, obj.object_id: obj}))
    engine = HabitatEngine(state)
    emb = Embodiment()
    emb.body.x = 4.0
    emb.body.y = 3.0
    emb.attach_habitat_engine(engine)
    perception = __import__("umbra_core.perception", fromlist=["PerceptionMembrane"]).PerceptionMembrane(
        false_negative_rate=0.0, noise_sigma=0.0
    )
    perception.perceive_habitat_objects(emb, 1.0, __import__("umbra_core.util", fromlist=["SeededRNG"]).SeededRNG(1))
    from umbra_core.embodiment_adapters import ABSTRACT_SHAPE_BODY_D009, EmbodimentAdapter

    adapter = EmbodimentAdapter(
        store=_journal_store(tmp_path),
        agent_id="agent:test",
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    adapter.attach(ABSTRACT_SHAPE_BODY_D009.profile_id)
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", mc.to_candidate().params)
    decision = gov.admit(proposal, tick=1)
    from umbra_core.perception import resolve_manipulation_address

    resolved = resolve_manipulation_address(
        target_address_ref=mc.target_address_ref,
        perception_evidence_ref=mc.perception_evidence_ref,
        perception_state_version=mc.perception_state_version,
        bindings=perception.object_bindings,
        habitat_engine=engine,
    )
    obj = engine.get_object(resolved.target_object_id)
    defn = _affordance_engine().get_definition("affordance:resource:use")
    snapshot = engine.snapshot_view()
    request = ManipulationRequest(
        request_id=proposal.proposal_id,
        execution_id="exec:mismatch",
        capability="MANIPULATE",
        target_object_id=resolved.target_object_id,
        affordance_id=defn.affordance_id,
        expected_habitat_version=snapshot.state_version,
        expected_habitat_state_hash=snapshot.state_hash,
        target_object_version=resolved.target_object_version,
        target_object_definition_version=obj.definition_version,
        target_object_definition_hash="f" * 64,
        affordance_definition_version=defn.definition_version,
        affordance_definition_hash=definition_hash(defn),
        body_instance_id=adapter.state.body_instance_id,
        body_profile_id=adapter.state.body_profile_id,
        attachment_generation=adapter.state.attachment_generation,
        parameters=UseParameters(),
    )
    validation = _affordance_engine().validate(
        request, snapshot, _adapter_for(UseParameters()), in_range=True
    )
    assert validation.allowed is False
    assert validation.failure_code == "OBJECT_DEFINITION_MISMATCH"


def test_affordance_definition_mismatch_fails_closed(tmp_path):
    from umbra_core.governance import Governance, GovernanceState

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    params = mc.to_candidate().params
    params["expected_affordance_hash"] = "0" * 64
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    from umbra_core.perception import resolve_manipulation_address
    from umbra_core.habitat_affordances.engine import ManipulationRequest, UseParameters

    resolved = resolve_manipulation_address(
        target_address_ref=mc.target_address_ref,
        perception_evidence_ref=mc.perception_evidence_ref,
        perception_state_version=mc.perception_state_version,
        bindings=perception.object_bindings,
        habitat_engine=engine,
    )
    obj = engine.get_object(resolved.target_object_id)
    defn = _affordance_engine().get_definition("affordance:resource:use")
    snapshot = engine.snapshot_view()
    request = ManipulationRequest(
        request_id=proposal.proposal_id,
        execution_id="exec:aff_mismatch",
        capability="MANIPULATE",
        target_object_id=resolved.target_object_id,
        affordance_id=defn.affordance_id,
        expected_habitat_version=snapshot.state_version,
        expected_habitat_state_hash=snapshot.state_hash,
        target_object_version=resolved.target_object_version,
        target_object_definition_version=obj.definition_version,
        target_object_definition_hash=obj.definition_hash,
        affordance_definition_version=defn.definition_version,
        affordance_definition_hash="f" * 64,
        body_instance_id=adapter.state.body_instance_id,
        body_profile_id=adapter.state.body_profile_id,
        attachment_generation=adapter.state.attachment_generation,
        parameters=UseParameters(),
    )
    validation = _affordance_engine().validate(
        request, snapshot, _adapter_for(UseParameters()), in_range=True
    )
    assert validation.allowed is False
    assert validation.failure_code == "AFFORDANCE_DEFINITION_MISMATCH"


def test_profile_definition_mismatch_fails_closed(tmp_path):
    from umbra_core.governance import Governance, GovernanceState

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mc = _task7_manipulation_candidate(perception, __import__("umbra_core.arbitration", fromlist=["Arbitrator"]).Arbitrator())
    params = mc.to_candidate().params
    params["expected_profile_hash"] = "0" * 64
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", params)
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=perception.object_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None and outcome.success is False
    assert outcome.reason == "PROFILE_HASH_MISMATCH"
    store.close()


# --- Task 8: learning, routines, individuality environmental scoring ----------


def _environmental_anchors(**overrides):
    base = {
        "execution_id": "exec:env:1",
        "request_id": "req:env:1",
        "target_object_id": "resource:0",
        "target_address_ref": "addr:resource:0",
        "perception_evidence_ref": "pev:1",
        "object_definition_hash": "a" * 64,
        "affordance_definition_hash": "b" * 64,
        "committed_habitat_version": 1,
        "perceived_object_kind": "resource",
    }
    base.update(overrides)
    return base


def test_world_model_update_is_idempotent_by_execution():
    from umbra_core.world_model import WorldModel

    wm = WorldModel.create("agent:test")
    anchors = _environmental_anchors()
    verified = {"success": True, "verified": True}
    first = wm.observe_environmental_outcome(
        anchors=anchors,
        verified_outcome=verified,
        tick=1,
    )
    models_after_first = len(wm.models)
    second = wm.observe_environmental_outcome(
        anchors=anchors,
        verified_outcome=verified,
        tick=2,
    )
    assert first.get("adapted") is True
    assert second.get("duplicate") is True
    assert len(wm.models) == models_after_first


def test_environmental_learning_requires_verified_outcome():
    from umbra_core.world_model import WorldModel

    wm = WorldModel.create("agent:test")
    denied = wm.observe_environmental_outcome(
        anchors=_environmental_anchors(),
        verified_outcome=None,
        tick=1,
        denied=True,
    )
    incomplete = wm.observe_environmental_outcome(
        anchors=_environmental_anchors(execution_id="exec:missing"),
        verified_outcome=None,
        tick=1,
    )
    stale = wm.observe_environmental_outcome(
        anchors=_environmental_anchors(execution_id="exec:stale"),
        verified_outcome={"success": True, "verified": True},
        tick=1,
        stale_binding=True,
    )
    assert denied["rejected"] and denied["reason"] == "denied_proposal"
    assert incomplete["rejected"] and incomplete["reason"] == "unverified_outcome"
    assert stale["rejected"] and stale["reason"] == "stale_binding"
    assert len(wm._processed_environmental_executions) == 0


def test_frequency_alone_does_not_create_environmental_preference():
    from umbra_core.individuality import IndividualityEngine, VerifiedEvidence
    from umbra_core.memory import MemoryEngine
    from umbra_core.util import SeededRNG

    indiv = IndividualityEngine.create("agent:test")
    mem = MemoryEngine.create("agent:test")
    rng = SeededRNG(1)
    for i in range(12):
        mem.consider_event(
            tick=i,
            occurred_at=float(i),
            context={
                "entity_kind": "resource",
                "affordance": "affordance:resource:use",
                "frequency_only": True,
            },
            observations=[],
            internal_state={"energy": 0.5},
            goal=None,
            action="MANIPULATE",
            verified_outcome=None,
            prediction_error=0.0,
            force=True,
        )
        indiv.observe_habitat_verified(
            VerifiedEvidence(
                evidence_id=f"freq-{i}",
                tick=i,
                source_system="habitat",
                dimension="object_preference",
                context_scope="habitat:object:resource",
                signed_outcome=1.0,
                verified=True,
                executed=True,
                from_frequency_only=True,
            )
        )
    _ = rng
    assert indiv.metrics.get("frequency_rejected", 0) >= 1
    assert not any(
        sk.applicability.get("kind") == "environmental_routine"
        for sk in mem.procedural.values()
    )


def test_environmental_learning_revises_on_contradiction():
    from umbra_core.world_model import WorldModel
    from umbra_core.world_model.engine import (
        SUPERSEDE_CONTRADICTION_THRESHOLD,
        SUPERSEDE_SUPPORT_MIN,
    )

    wm = WorldModel.create("agent:test")
    kind = "resource"
    for i in range(SUPERSEDE_SUPPORT_MIN + 2):
        wm.observe_environmental_outcome(
            anchors=_environmental_anchors(execution_id=f"exec:ok:{i}"),
            verified_outcome={"success": True, "verified": True},
            tick=i,
            object_kind=kind,
        )
    active = [
        m
        for m in wm.models.values()
        if m.action == "MANIPULATE" and m.conditions.get("entity_kind") == kind
    ]
    assert active
    before_support = active[0].support_count
    for i in range(SUPERSEDE_CONTRADICTION_THRESHOLD):
        wm.observe_environmental_outcome(
            anchors=_environmental_anchors(execution_id=f"exec:fail:{i}"),
            verified_outcome={"success": False, "verified": True},
            tick=100 + i,
            object_kind=kind,
        )
    revised = [
        m
        for m in wm.models.values()
        if m.action == "MANIPULATE"
        and m.conditions.get("entity_kind") == kind
        and m.status in ("WEAKENED", "SUPERSEDED", "ACTIVE")
    ]
    assert revised
    assert before_support >= SUPERSEDE_SUPPORT_MIN
    assert wm.live_supersessions() or any(m.status == "WEAKENED" for m in revised)


def test_environmental_routine_promoted_from_multiple_episodes():
    from umbra_core.memory import MemoryEngine, RoutineLifecycle
    from umbra_core.memory.engine import EnvironmentalRoutineSpec

    mem = MemoryEngine.create("agent:test")
    ep_ids: list[str] = []
    for i in range(3):
        ep = mem.consider_event(
            tick=i,
            occurred_at=float(i),
            context={
                "entity_kind": "resource",
                "affordance": "affordance:resource:use",
                "zone_id": "zone:general",
            },
            observations=[],
            internal_state={"energy": 0.5},
            goal=None,
            action="MANIPULATE",
            verified_outcome={"success": True},
            prediction_error=0.4,
            force=True,
        )
        assert ep is not None
        ep_ids.append(ep.episode_id)
    rid = mem.promote_environmental_routine(
        EnvironmentalRoutineSpec(
            object_kind="resource",
            affordance_ref="affordance:resource:use",
            zone_id="zone:general",
            soft_proposals=[],
            supporting_episode_ids=ep_ids,
        ),
        tick=5,
        lifecycle=RoutineLifecycle.ACTIVE.value,
    )
    sk = mem.procedural[rid]
    assert sk.applicability["lifecycle"] == RoutineLifecycle.ACTIVE.value
    assert len(sk.source_episode_ids) >= 3


def test_environmental_routine_interruptible_and_missing_object_safe():
    from umbra_core.memory import MemoryEngine, RoutineLifecycle
    from umbra_core.memory.engine import EnvironmentalRoutineSpec

    mem = MemoryEngine.create("agent:test")
    rid = mem.promote_environmental_routine(
        EnvironmentalRoutineSpec(
            object_kind="resource",
            affordance_ref="affordance:resource:use",
            zone_id="zone:general",
            soft_proposals=[],
            supporting_episode_ids=["ep:1", "ep:2", "ep:3"],
        ),
        tick=1,
    )
    lifecycle = mem.update_environmental_routine_lifecycle(
        rid, success=False, interrupted=True, tick=2
    )
    assert lifecycle == RoutineLifecycle.WEAKENED.value
    lifecycle = mem.update_environmental_routine_lifecycle(
        rid, success=False, object_missing=True, tick=3
    )
    assert lifecycle in (
        RoutineLifecycle.WEAKENED.value,
        RoutineLifecycle.INACTIVE.value,
    )
    proposals = mem.routine_soft_proposals(mem.procedural[rid], bindings=[])
    assert proposals == []


def test_environmental_routine_lifecycle_not_fifo():
    from umbra_core.memory import MemoryEngine, RoutineLifecycle
    from umbra_core.memory.engine import EnvironmentalRoutineSpec

    mem = MemoryEngine.create("agent:test")
    rid = mem.promote_environmental_routine(
        EnvironmentalRoutineSpec(
            object_kind="resource",
            affordance_ref="affordance:resource:use",
            zone_id=None,
            soft_proposals=[],
            supporting_episode_ids=["ep:a", "ep:b", "ep:c"],
        ),
        tick=1,
    )
    sk = mem.procedural[rid]
    sk.confidence = 0.05
    sk.failure_count = 10
    sk.success_count = 1
    mem.update_environmental_routine_lifecycle(
        rid, success=False, interrupted=True, tick=2
    )
    mem.update_environmental_routine_lifecycle(
        rid, success=False, object_missing=True, tick=3
    )
    mem.update_environmental_routine_lifecycle(
        rid, success=False, object_missing=True, tick=4
    )
    assert sk.applicability["lifecycle"] in (
        RoutineLifecycle.INACTIVE.value,
        RoutineLifecycle.RETIRED.value,
    )
    assert rid in mem.procedural


def test_different_histories_produce_different_environmental_bias():
    from umbra_core.individuality import IndividualityEngine, VerifiedEvidence

    a = IndividualityEngine.create("agent:a")
    b = IndividualityEngine.create("agent:b")
    for eng, sign in ((a, 1.0), (b, -1.0)):
        for i in range(6):
            eng.observe_habitat_verified(
                VerifiedEvidence(
                    evidence_id=f"hist-{i}",
                    tick=i,
                    source_system="habitat",
                    dimension="object_preference",
                    context_scope="habitat:object:resource",
                    signed_outcome=sign,
                    verified=True,
                    executed=True,
                )
            )
    va = a.dispositions[("habitat:object_preference", "habitat:object:resource")].value
    vb = b.dispositions[("habitat:object_preference", "habitat:object:resource")].value
    assert va * vb < 0


def test_individuality_disabled_reduces_separation():
    from umbra_core.arbitration import Arbitrator, Candidate
    from umbra_core.individuality import IndividualityEngine, VerifiedEvidence
    from umbra_core.physiology import Physiology

    def separation(enabled: bool) -> float:
        eng = IndividualityEngine.create(
            "agent:test",
            config=__import__(
                "umbra_core.individuality",
                fromlist=["IndividualityConfig"],
            ).IndividualityConfig(
                enabled=enabled,
                modifiers_affect_arbitration=enabled,
            ),
        )
        for i in range(8):
            eng.observe_habitat_verified(
                VerifiedEvidence(
                    evidence_id=f"sep-{i}",
                    tick=i,
                    source_system="habitat",
                    dimension="environmental_persistence",
                    context_scope="habitat:object:resource",
                    signed_outcome=1.0 if i % 2 == 0 else -1.0,
                    verified=True,
                    executed=True,
                )
            )
        arb = Arbitrator()
        phys = Physiology()
        obs = [{"kind": "resource", "relative_direction": 0.1, "estimated_distance": 1.0}]
        cands = [
            Candidate(
                "MANIPULATE",
                {
                    "perceived_object_kind": "resource",
                    "source": "NEED_RELEVANCE",
                },
            ),
            Candidate("IDLE", {}),
        ]
        scored = [
            arb.score_candidate(c, phys, obs, 1) for c in cands
        ]
        eng.apply_modifiers(scored, context_scope="habitat:default")
        return abs(scored[0].total - scored[1].total)

    assert separation(True) > separation(False)


def test_manipulation_candidates_compete_in_arbitration():
    from umbra_core.arbitration import Arbitrator
    from umbra_core.physiology import Physiology

    _, _, perception, _, _ = _task7_habitat_setup()
    bindings = perception.policy_view()["manipulation_bindings"]
    phys = Physiology()
    phys.energy = 0.31
    arb = Arbitrator()
    obs = [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 1.0}]
    chosen = arb.select(
        phys,
        obs,
        tick=1,
        rng=__import__("umbra_core.util", fromlist=["SeededRNG"]).SeededRNG(7),
        manipulation_bindings=bindings,
    )
    assert chosen.capability == "MANIPULATE"
    assert chosen.params.get("target_address_ref")


def test_routine_proposals_require_governance_each_step(tmp_path):
    from umbra_core.governance import Governance, GovernanceState
    from umbra_core.memory import EnvironmentalRoutineSpec, MemoryEngine

    engine, emb, perception, adapter, _ = _task7_habitat_setup()
    mem = MemoryEngine.create("agent:test")
    rid = mem.promote_environmental_routine(
        EnvironmentalRoutineSpec(
            object_kind="resource",
            affordance_ref="affordance:resource:use",
            zone_id="zone:general",
            soft_proposals=[],
            supporting_episode_ids=["ep:1", "ep:2", "ep:3"],
        ),
        tick=1,
    )
    proposals = mem.routine_soft_proposals(mem.procedural[rid], perception.policy_view()["manipulation_bindings"])
    assert proposals
    assert "target_object_id" not in proposals[0]
    gov = Governance(GovernanceState())
    proposal = gov.propose("MANIPULATE", proposals[0])
    decision = gov.admit(proposal, tick=1)
    store = _journal_store(tmp_path)
    outcome = gov.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=_affordance_engine(),
        adapter=adapter,
        embodiment=emb,
        bindings=perception.object_bindings,
        store=store,
        phys=__import__("umbra_core.physiology", fromlist=["Physiology"]).Physiology(),
        agent_id="agent:test",
        tick=1,
        monotonic_time=1.0,
        wall_time=1.0,
    )
    assert outcome is not None
    assert outcome.verified is True
    store.close()
