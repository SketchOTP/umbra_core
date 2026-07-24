"""UMBRA-D-009 persistent habitat agency tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from umbra_core.embodiment import BodyOccupancyView, Embodiment, HabitatFeature
from umbra_core.habitat.engine import (
    BodyCollisionShape,
    BodyPoseView,
    HabitatEngine,
    Position,
    ReachProfile,
)
from umbra_core.habitat.migration import habitat_object_from_legacy_feature, legacy_object_id_for_feature
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
    with_state_hash,
)


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
    emb.body.x = 19.0
    emb.body.y = 19.0
    # habitat state unchanged — body position is not persisted in habitat
    assert engine.snapshot_view().state_hash == engine.snapshot_view().state_hash


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
