"""UMBRA-D-009 persistent habitat agency tests."""

from __future__ import annotations

from dataclasses import replace

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
