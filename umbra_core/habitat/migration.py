"""Legacy HabitatFeature → HabitatObject migration helpers."""

from __future__ import annotations

from umbra_core.embodiment import HabitatFeature
from umbra_core.habitat.state import (
    FreeLocation,
    HabitatObject,
    IdleState,
    ObjectKind,
    ResourceState,
    StationState,
    _make_object,
    compute_object_definition_hash,
    with_object_state_hash,
)
from dataclasses import replace

_OBJECT_KIND_BY_FEATURE_KIND: dict[str, ObjectKind] = {
    "rest": ObjectKind.REST_STATION,
    "resource": ObjectKind.RESOURCE,
    "inspect": ObjectKind.INSPECTABLE,
    "hazard": ObjectKind.HAZARD,
    "open": ObjectKind.OBSTACLE,
    "novel_crystal": ObjectKind.PORTABLE_OBJECT,
    "impossible_node": ObjectKind.OBSTACLE,
    "noise_blink": ObjectKind.INSPECTABLE,
    "spurious_blink": ObjectKind.INSPECTABLE,
}

_FEATURE_KIND_BY_OBJECT_KIND: dict[ObjectKind, str] = {
    ObjectKind.REST_STATION: "rest",
    ObjectKind.RESOURCE: "resource",
    ObjectKind.INSPECTABLE: "inspect",
    ObjectKind.HAZARD: "hazard",
    ObjectKind.OBSTACLE: "hazard",
    ObjectKind.PORTABLE_OBJECT: "resource",
    ObjectKind.ACTIVATABLE_OBJECT: "inspect",
    ObjectKind.SCENERY: "open",
    ObjectKind.CHARGE_STATION: "resource",
    ObjectKind.SOCIAL_ENTITY: "partner",
}


def legacy_object_id_for_feature(kind: str, *, index: int = 0) -> str:
    """Deterministic legacy feature ID → authoritative object_id."""
    return f"feature:{kind}:{index}"


def object_kind_for_feature_kind(kind: str) -> ObjectKind:
    return _OBJECT_KIND_BY_FEATURE_KIND.get(kind, ObjectKind.INSPECTABLE)


def feature_kind_from_object(obj: HabitatObject) -> str:
    return _FEATURE_KIND_BY_OBJECT_KIND.get(obj.object_kind, "inspect")


def habitat_object_from_legacy_feature(
    feature: HabitatFeature,
    *,
    object_id: str | None = None,
    zone_id: str = "zone:general",
    index: int = 0,
) -> HabitatObject:
    """Build a HabitatObject from a legacy HabitatFeature plant."""
    kind = feature.kind
    oid = object_id or legacy_object_id_for_feature(kind, index=index)
    object_kind = object_kind_for_feature_kind(kind)
    if object_kind == ObjectKind.RESOURCE:
        state = ResourceState(remaining_yield=1.0)
    elif object_kind == ObjectKind.REST_STATION:
        state = StationState(station_kind="REST", available=feature.restable)
    else:
        state = IdleState()
    base = _make_object(
        object_id=oid,
        object_kind=object_kind,
        location=FreeLocation(feature.x, feature.y, zone_id),
        state=state,
        collision_radius=feature.radius,
    )
    updated = replace(
        base,
        passable=feature.passable,
        occluded=feature.occluded,
        portable=object_kind == ObjectKind.PORTABLE_OBJECT,
    )
    definition_hash = compute_object_definition_hash(updated)
    with_definition = replace(updated, definition_hash=definition_hash)
    return with_object_state_hash(with_definition)
