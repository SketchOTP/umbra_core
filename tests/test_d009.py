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
    HabitatAffordanceEngine,
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


def _adapter_for(params) -> AdapterValidatedManipulation:
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
