"""D-009 HabitatState, HabitatObject, canonical hashing, and object versioning."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from enum import Enum
from typing import Any, Callable

from umbra_core.util import canon_json, sha256_hex

HABITAT_SCHEMA_VERSION = "d009.habitat-state.v1"
INITIAL_OBJECT_VERSION = 1
INITIAL_DEFINITION_VERSION = 1


class ZoneKind(str, Enum):
    GENERAL = "GENERAL"
    REST = "REST"
    RECOVERY = "RECOVERY"
    MAINTENANCE = "MAINTENANCE"
    EXPLORATION = "EXPLORATION"
    SOCIAL = "SOCIAL"


class ObjectKind(str, Enum):
    SCENERY = "SCENERY"
    OBSTACLE = "OBSTACLE"
    HAZARD = "HAZARD"
    RESOURCE = "RESOURCE"
    INSPECTABLE = "INSPECTABLE"
    REST_STATION = "REST_STATION"
    CHARGE_STATION = "CHARGE_STATION"
    PORTABLE_OBJECT = "PORTABLE_OBJECT"
    ACTIVATABLE_OBJECT = "ACTIVATABLE_OBJECT"
    SOCIAL_ENTITY = "SOCIAL_ENTITY"


@dataclass(frozen=True)
class ZoneBounds:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True)
class BodyConstraints:
    required_capabilities: tuple[str, ...]
    maximum_body_radius: float
    maximum_body_mass_class: str
    locomotion_requirements: tuple[str, ...]


@dataclass(frozen=True)
class EnvironmentalProperties:
    schema_version: str
    values: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class Zone:
    zone_id: str
    zone_kind: ZoneKind
    bounds: ZoneBounds
    occupancy_limit: int
    body_constraints: BodyConstraints
    environmental_properties: EnvironmentalProperties
    rest_support: bool
    maintenance_support: bool


@dataclass(frozen=True)
class ZoneConnection:
    from_zone_id: str
    to_zone_id: str


@dataclass(frozen=True)
class EnvironmentalTransition:
    transition_id: str
    start_tick: int
    completion_tick: int
    definition_hash: str
    status: str


@dataclass(frozen=True)
class FreeLocation:
    x: float
    y: float
    zone_id: str


@dataclass(frozen=True)
class HeldByLocation:
    body_instance_id: str
    attachment_generation: int
    hold_slot: int


ObjectLocation = FreeLocation | HeldByLocation


@dataclass(frozen=True)
class IdleState:
    kind: str = "IDLE"


@dataclass(frozen=True)
class ResourceState:
    remaining_yield: float
    kind: str = "RESOURCE"


@dataclass(frozen=True)
class StationState:
    station_kind: str
    available: bool
    kind: str = "STATION"


@dataclass(frozen=True)
class ActivatableState:
    active: bool
    kind: str = "ACTIVATABLE"


@dataclass(frozen=True)
class SocialEntitySpatialState:
    entity_ref: str
    kind: str = "SOCIAL_ENTITY"


ObjectState = IdleState | ResourceState | StationState | ActivatableState | SocialEntitySpatialState


@dataclass(frozen=True)
class HabitatObject:
    object_id: str
    object_kind: ObjectKind
    definition_version: int
    definition_hash: str
    object_version: int
    object_state_hash: str
    location: ObjectLocation
    state: ObjectState
    mass_class: str
    portable: bool
    passable: bool
    occluded: bool
    collision_radius: float
    affordance_ids: tuple[str, ...]
    visibility: str
    condition: float
    cooldowns: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class HabitatState:
    habitat_id: str
    schema_version: str
    habitat_tick: int
    state_version: int
    definition_hash: str
    state_hash: str
    zones: dict[str, Zone]
    objects: dict[str, HabitatObject]
    zone_connections: tuple[ZoneConnection, ...]
    active_environmental_transitions: tuple[EnvironmentalTransition, ...]
    bounded_environmental_history_refs: tuple[str, ...]


class MutationRejected(Exception):
    """Validation failure — mutation must not commit."""


_OBJECT_DEFINITION_FIELDS = (
    "object_id",
    "object_kind",
    "definition_version",
    "mass_class",
    "portable",
    "passable",
    "occluded",
    "collision_radius",
    "affordance_ids",
)


def canonical_serialize(value: Any) -> Any:
    """Stable JSON-compatible structure for hashing."""
    return _canonical_value(value)


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_canonical_value(item) for item in value)
    if hasattr(value, "__dataclass_fields__"):
        return {
            field.name: _canonical_value(getattr(value, field.name))
            for field in fields(value)
        }
    raise TypeError(f"unsupported_canonical_type:{type(value)!r}")


def _hash_canonical(value: Any) -> str:
    return sha256_hex(canon_json(canonical_serialize(value)))


def object_definition_payload(obj: HabitatObject) -> dict[str, Any]:
    serialized = canonical_serialize(obj)
    return {key: serialized[key] for key in _OBJECT_DEFINITION_FIELDS}


def compute_object_definition_hash(obj: HabitatObject) -> str:
    return _hash_canonical(object_definition_payload(obj))


def compute_object_state_hash(obj: HabitatObject) -> str:
    payload = canonical_serialize(obj)
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.pop("object_state_hash", None)
    return _hash_canonical(payload)


def compute_habitat_definition_hash(state: HabitatState) -> str:
    payload = {
        "habitat_id": state.habitat_id,
        "schema_version": state.schema_version,
        "zones": {zone_id: canonical_serialize(state.zones[zone_id]) for zone_id in sorted(state.zones)},
        "zone_connections": canonical_serialize(state.zone_connections),
        "objects": {
            object_id: object_definition_payload(state.objects[object_id])
            for object_id in sorted(state.objects)
        },
    }
    return _hash_canonical(payload)


def compute_state_hash(state: HabitatState) -> str:
    payload = canonical_serialize(state)
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.pop("state_hash", None)
    return _hash_canonical(payload)


def with_object_state_hash(obj: HabitatObject, *, object_version: int | None = None) -> HabitatObject:
    version = obj.object_version if object_version is None else object_version
    base = replace(obj, object_version=version, object_state_hash="")
    return replace(base, object_state_hash=compute_object_state_hash(base))


def apply_committed_object_mutation(
    obj: HabitatObject,
    mutate_fn: Callable[[HabitatObject], HabitatObject],
) -> HabitatObject:
    updated = mutate_fn(obj)
    return with_object_state_hash(updated, object_version=obj.object_version + 1)


def apply_rejected_object_mutation(
    obj: HabitatObject,
    mutate_fn: Callable[[HabitatObject], HabitatObject],
) -> HabitatObject:
    try:
        mutate_fn(obj)
    except MutationRejected:
        return obj
    raise MutationRejected("rejected_mutation_requires_MutationRejected")


def migrate_object_definition(
    obj: HabitatObject,
    *,
    new_definition_version: int,
    new_definition_hash: str,
    migrate_fn: Callable[[HabitatObject], HabitatObject],
) -> HabitatObject:
    migrated = migrate_fn(obj)
    updated = replace(
        migrated,
        definition_version=new_definition_version,
        definition_hash=new_definition_hash,
    )
    return with_object_state_hash(updated, object_version=obj.object_version + 1)


def with_state_hash(state: HabitatState) -> HabitatState:
    base = replace(state, state_hash="")
    return replace(base, state_hash=compute_state_hash(base))


def _default_zone(zone_id: str, *, zone_kind: ZoneKind, rest_support: bool) -> Zone:
    return Zone(
        zone_id=zone_id,
        zone_kind=zone_kind,
        bounds=ZoneBounds(0.0, 0.0, 20.0, 20.0),
        occupancy_limit=16,
        body_constraints=BodyConstraints(
            required_capabilities=("MOVE",),
            maximum_body_radius=2.0,
            maximum_body_mass_class="MEDIUM",
            locomotion_requirements=("GROUND",),
        ),
        environmental_properties=EnvironmentalProperties(
            schema_version="d009.zone-env.v1",
            values=(("light_level", 0.75),),
        ),
        rest_support=rest_support,
        maintenance_support=False,
    )


def _make_object(
    *,
    object_id: str,
    object_kind: ObjectKind,
    location: ObjectLocation,
    state: ObjectState,
    collision_radius: float,
    affordance_ids: tuple[str, ...] = (),
) -> HabitatObject:
    definition_version = INITIAL_DEFINITION_VERSION
    base = HabitatObject(
        object_id=object_id,
        object_kind=object_kind,
        definition_version=definition_version,
        definition_hash="",
        object_version=INITIAL_OBJECT_VERSION,
        object_state_hash="",
        location=location,
        state=state,
        mass_class="LIGHT",
        portable=object_kind == ObjectKind.PORTABLE_OBJECT,
        passable=object_kind not in {ObjectKind.OBSTACLE, ObjectKind.HAZARD},
        occluded=False,
        collision_radius=collision_radius,
        affordance_ids=affordance_ids,
        visibility="VISIBLE",
        condition=1.0,
        cooldowns=(),
    )
    definition_hash = compute_object_definition_hash(base)
    with_definition = replace(base, definition_hash=definition_hash)
    return with_object_state_hash(with_definition)


def sample_habitat_state() -> HabitatState:
    """Frozen fixture for definition/state hash stability tests."""
    zones = {
        "zone:general": _default_zone("zone:general", zone_kind=ZoneKind.GENERAL, rest_support=False),
        "zone:rest": _default_zone("zone:rest", zone_kind=ZoneKind.REST, rest_support=True),
    }
    objects = {
        "resource:0": _make_object(
            object_id="resource:0",
            object_kind=ObjectKind.RESOURCE,
            location=FreeLocation(4.0, 3.0, "zone:general"),
            state=ResourceState(remaining_yield=1.0),
            collision_radius=1.2,
            affordance_ids=("USE",),
        ),
        "rest:0": _make_object(
            object_id="rest:0",
            object_kind=ObjectKind.REST_STATION,
            location=FreeLocation(12.0, 8.0, "zone:rest"),
            state=StationState(station_kind="REST", available=True),
            collision_radius=1.5,
            affordance_ids=("REST",),
        ),
    }
    base = HabitatState(
        habitat_id="habitat:sample",
        schema_version=HABITAT_SCHEMA_VERSION,
        habitat_tick=0,
        state_version=0,
        definition_hash="",
        state_hash="",
        zones=zones,
        objects=objects,
        zone_connections=(
            ZoneConnection(from_zone_id="zone:general", to_zone_id="zone:rest"),
        ),
        active_environmental_transitions=(),
        bounded_environmental_history_refs=(),
    )
    definition_hash = compute_habitat_definition_hash(base)
    with_definition = replace(base, definition_hash=definition_hash)
    return with_state_hash(with_definition)
