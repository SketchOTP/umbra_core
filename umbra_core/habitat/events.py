"""D-009 habitat event payloads and canonical ledger apply helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from umbra_core.habitat.state import (
    ActivatableState,
    BodyConstraints,
    EnvironmentalProperties,
    EnvironmentalTransition,
    FreeLocation,
    HabitatObject,
    HabitatState,
    HeldByLocation,
    IdleState,
    ObjectKind,
    ObjectLocation,
    ObjectState,
    ResourceState,
    SocialEntitySpatialState,
    StationState,
    Zone,
    ZoneBounds,
    ZoneConnection,
    ZoneKind,
    apply_committed_object_mutation,
    canonical_serialize,
    compute_habitat_definition_hash,
    migrate_object_definition,
    with_state_hash,
)
from umbra_core.util import new_id

HABITAT_INITIALIZED = "habitat_initialized"
HABITAT_ZONE_ADDED = "habitat_zone_added"
HABITAT_OBJECT_CREATED = "habitat_object_created"
HABITAT_OBJECT_STATE_CHANGED = "habitat_object_state_changed"
HABITAT_OBJECT_MOVED = "habitat_object_moved"
HABITAT_OBJECT_PICKED_UP = "habitat_object_picked_up"
HABITAT_OBJECT_PLACED = "habitat_object_placed"
HABITAT_AFFORDANCE_ACTIVATED = "habitat_affordance_activated"
HABITAT_AFFORDANCE_DEACTIVATED = "habitat_affordance_deactivated"
HABITAT_TRANSITION_APPLIED = "habitat_transition_applied"
HABITAT_DEFINITION_MIGRATED = "habitat_definition_migrated"
HABITAT_HELD_BINDING_REBASED = "habitat_held_binding_rebased"
HABITAT_BODY_ZONE_TRANSITIONED = "habitat_body_zone_transitioned"

HABITAT_EVENT_TYPES = frozenset(
    {
        HABITAT_INITIALIZED,
        HABITAT_ZONE_ADDED,
        HABITAT_OBJECT_CREATED,
        HABITAT_OBJECT_STATE_CHANGED,
        HABITAT_OBJECT_MOVED,
        HABITAT_OBJECT_PICKED_UP,
        HABITAT_OBJECT_PLACED,
        HABITAT_AFFORDANCE_ACTIVATED,
        HABITAT_AFFORDANCE_DEACTIVATED,
        HABITAT_TRANSITION_APPLIED,
        HABITAT_DEFINITION_MIGRATED,
        HABITAT_HELD_BINDING_REBASED,
        HABITAT_BODY_ZONE_TRANSITIONED,
    }
)

AUTHORITATIVE_HABITAT_EVENTS = HABITAT_EVENT_TYPES

INIT_PRIOR_STATE_VERSION = -1
INIT_PRIOR_STATE_HASH = ""


class HabitatEventError(Exception):
    """Fail-closed habitat event apply / replay error."""


def _parse_enum(raw: Any, enum_cls):
    if isinstance(raw, enum_cls):
        return raw
    text = str(raw)
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return enum_cls(text)


def location_to_payload(location: ObjectLocation) -> dict[str, Any]:
    return _location_to_payload(location)


def object_state_to_payload(state: ObjectState) -> dict[str, Any]:
    return _object_state_to_payload(state)


def build_object_moved_event(
    state_before: HabitatState,
    state_after: HabitatState,
    object_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_habitat_event(
        state_before,
        state_after,
        HABITAT_OBJECT_MOVED,
        extra_payload={
            "object_id": object_id,
            "new_location": _location_to_payload(state_after.objects[object_id].location),
        },
        **kwargs,
    )


def build_object_picked_up_event(
    state_before: HabitatState,
    state_after: HabitatState,
    object_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_habitat_event(
        state_before,
        state_after,
        HABITAT_OBJECT_PICKED_UP,
        extra_payload={
            "object_id": object_id,
            "new_location": _location_to_payload(state_after.objects[object_id].location),
        },
        **kwargs,
    )


def build_object_placed_event(
    state_before: HabitatState,
    state_after: HabitatState,
    object_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_habitat_event(
        state_before,
        state_after,
        HABITAT_OBJECT_PLACED,
        extra_payload={
            "object_id": object_id,
            "new_location": _location_to_payload(state_after.objects[object_id].location),
        },
        **kwargs,
    )


def _location_to_payload(location: ObjectLocation) -> dict[str, Any]:
    if isinstance(location, FreeLocation):
        return {
            "mode": "FREE",
            "x": location.x,
            "y": location.y,
            "zone_id": location.zone_id,
        }
    return {
        "mode": "HELD_BY",
        "body_instance_id": location.body_instance_id,
        "attachment_generation": location.attachment_generation,
        "hold_slot": location.hold_slot,
    }


def _location_from_payload(payload: dict[str, Any]) -> ObjectLocation:
    if payload.get("mode") == "HELD_BY" or "body_instance_id" in payload:
        return HeldByLocation(
            body_instance_id=str(payload["body_instance_id"]),
            attachment_generation=int(payload["attachment_generation"]),
            hold_slot=int(payload["hold_slot"]),
        )
    return FreeLocation(
        float(payload["x"]),
        float(payload["y"]),
        str(payload["zone_id"]),
    )


def _object_state_to_payload(state: ObjectState) -> dict[str, Any]:
    return canonical_serialize(state)


def _object_state_from_payload(payload: dict[str, Any]) -> ObjectState:
    kind = payload.get("kind")
    if kind == "IDLE":
        return IdleState()
    if kind == "RESOURCE":
        return ResourceState(remaining_yield=float(payload["remaining_yield"]))
    if kind == "STATION":
        return StationState(
            station_kind=str(payload["station_kind"]),
            available=bool(payload["available"]),
        )
    if kind == "ACTIVATABLE":
        return ActivatableState(active=bool(payload["active"]))
    if kind == "SOCIAL_ENTITY":
        return SocialEntitySpatialState(entity_ref=str(payload["entity_ref"]))
    raise HabitatEventError(f"unknown_object_state_kind:{kind}")


def _zone_from_payload(payload: dict[str, Any]) -> Zone:
    bounds = payload["bounds"]
    body = payload["body_constraints"]
    env = payload["environmental_properties"]
    return Zone(
        zone_id=str(payload["zone_id"]),
        zone_kind=_parse_enum(payload["zone_kind"], ZoneKind),
        bounds=ZoneBounds(
            float(bounds["x_min"]),
            float(bounds["y_min"]),
            float(bounds["x_max"]),
            float(bounds["y_max"]),
        ),
        occupancy_limit=int(payload["occupancy_limit"]),
        body_constraints=BodyConstraints(
            required_capabilities=tuple(body["required_capabilities"]),
            maximum_body_radius=float(body["maximum_body_radius"]),
            maximum_body_mass_class=str(body["maximum_body_mass_class"]),
            locomotion_requirements=tuple(body["locomotion_requirements"]),
        ),
        environmental_properties=EnvironmentalProperties(
            schema_version=str(env["schema_version"]),
            values=tuple((str(k), float(v)) for k, v in env["values"]),
        ),
        rest_support=bool(payload["rest_support"]),
        maintenance_support=bool(payload["maintenance_support"]),
    )


def _object_from_payload(payload: dict[str, Any]) -> HabitatObject:
    return HabitatObject(
        object_id=str(payload["object_id"]),
        object_kind=_parse_enum(payload["object_kind"], ObjectKind),
        definition_version=int(payload["definition_version"]),
        definition_hash=str(payload["definition_hash"]),
        object_version=int(payload["object_version"]),
        object_state_hash=str(payload["object_state_hash"]),
        location=_location_from_payload(payload["location"]),
        state=_object_state_from_payload(payload["state"]),
        mass_class=str(payload["mass_class"]),
        portable=bool(payload["portable"]),
        passable=bool(payload["passable"]),
        occluded=bool(payload["occluded"]),
        collision_radius=float(payload["collision_radius"]),
        affordance_ids=tuple(str(x) for x in payload["affordance_ids"]),
        visibility=str(payload["visibility"]),
        condition=float(payload["condition"]),
        cooldowns=tuple((str(k), int(v)) for k, v in payload["cooldowns"]),
    )


def _transition_from_payload(payload: dict[str, Any]) -> EnvironmentalTransition:
    return EnvironmentalTransition(
        transition_id=str(payload["transition_id"]),
        start_tick=int(payload["start_tick"]),
        completion_tick=int(payload["completion_tick"]),
        definition_hash=str(payload["definition_hash"]),
        status=str(payload["status"]),
    )


def habitat_state_to_init_payload(state: HabitatState) -> dict[str, Any]:
    return {
        "habitat_id": state.habitat_id,
        "schema_version": state.schema_version,
        "habitat_tick": state.habitat_tick,
        "definition_hash": state.definition_hash,
        "zones": {
            zone_id: canonical_serialize(zone) for zone_id, zone in sorted(state.zones.items())
        },
        "objects": {
            object_id: canonical_serialize(obj)
            for object_id, obj in sorted(state.objects.items())
        },
        "zone_connections": canonical_serialize(state.zone_connections),
        "active_environmental_transitions": canonical_serialize(
            state.active_environmental_transitions
        ),
        "bounded_environmental_history_refs": list(state.bounded_environmental_history_refs),
    }


def _state_from_init_payload(payload: dict[str, Any]) -> HabitatState:
    zones = {
        zone_id: _zone_from_payload(zone_payload)
        for zone_id, zone_payload in payload["zones"].items()
    }
    objects = {
        object_id: _object_from_payload(object_payload)
        for object_id, object_payload in payload["objects"].items()
    }
    connections = tuple(
        ZoneConnection(
            from_zone_id=str(conn["from_zone_id"]),
            to_zone_id=str(conn["to_zone_id"]),
        )
        for conn in payload["zone_connections"]
    )
    transitions = tuple(
        _transition_from_payload(item) for item in payload["active_environmental_transitions"]
    )
    base = HabitatState(
        habitat_id=str(payload["habitat_id"]),
        schema_version=str(payload["schema_version"]),
        habitat_tick=int(payload.get("habitat_tick", 0)),
        state_version=0,
        definition_hash=str(payload["definition_hash"]),
        state_hash="",
        zones=zones,
        objects=objects,
        zone_connections=connections,
        active_environmental_transitions=transitions,
        bounded_environmental_history_refs=tuple(
            str(ref) for ref in payload.get("bounded_environmental_history_refs") or ()
        ),
    )
    definition_hash = compute_habitat_definition_hash(base)
    with_definition = replace(base, definition_hash=definition_hash)
    return with_state_hash(with_definition)


def _envelope_fields(
    state_before: HabitatState | None,
    state_after: HabitatState,
    *,
    habitat_tick: int | None = None,
    transaction_id: str | None = None,
    request_id: str | None = None,
    execution_id: str | None = None,
    actor_ref: str | None = None,
    target_ref: str | None = None,
) -> dict[str, Any]:
    prior_version = INIT_PRIOR_STATE_VERSION if state_before is None else state_before.state_version
    prior_hash = INIT_PRIOR_STATE_HASH if state_before is None else state_before.state_hash
    fields: dict[str, Any] = {
        "habitat_id": state_after.habitat_id,
        "transaction_id": transaction_id or new_id(),
        "prior_state_version": prior_version,
        "new_state_version": state_after.state_version,
        "habitat_tick": habitat_tick if habitat_tick is not None else state_after.habitat_tick,
        "request_id": request_id or new_id(),
        "prior_state_hash": prior_hash,
        "new_state_hash": state_after.state_hash,
        "definition_hash": state_after.definition_hash,
    }
    if execution_id is not None:
        fields["execution_id"] = execution_id
    if actor_ref is not None:
        fields["actor_ref"] = actor_ref
    if target_ref is not None:
        fields["target_ref"] = target_ref
    return fields


def build_habitat_event(
    state_before: HabitatState | None,
    state_after: HabitatState,
    event_type: str,
    *,
    event_id: str | None = None,
    extra_payload: dict[str, Any] | None = None,
    **envelope_kwargs: Any,
) -> dict[str, Any]:
    if event_type not in HABITAT_EVENT_TYPES:
        raise HabitatEventError(f"unknown_habitat_event:{event_type}")
    payload = _envelope_fields(state_before, state_after, **envelope_kwargs)
    if extra_payload:
        payload.update(extra_payload)
    return {
        "event_id": event_id or new_id(),
        "event_type": event_type,
        "payload": payload,
    }


def build_initialized_event(state: HabitatState, **kwargs: Any) -> dict[str, Any]:
    init_state = replace(state, state_version=0, state_hash="")
    init_state = with_state_hash(init_state)
    payload = _envelope_fields(None, init_state, **kwargs)
    payload["initial_state"] = habitat_state_to_init_payload(init_state)
    return {
        "event_id": kwargs.get("event_id") or new_id(),
        "event_type": HABITAT_INITIALIZED,
        "payload": payload,
    }


def build_body_zone_transition_event(
    state: HabitatState,
    *,
    body_instance_id: str,
    from_zone_id: str,
    to_zone_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    payload = _envelope_fields(state, state, **kwargs)
    payload.update(
        {
            "body_instance_id": body_instance_id,
            "from_zone_id": from_zone_id,
            "to_zone_id": to_zone_id,
        }
    )
    return {
        "event_id": kwargs.get("event_id") or new_id(),
        "event_type": HABITAT_BODY_ZONE_TRANSITIONED,
        "payload": payload,
    }


def build_held_binding_rebased_event(
    state_before: HabitatState,
    state_after: HabitatState,
    *,
    object_id: str,
    body_instance_id: str,
    old_attachment_generation: int,
    new_attachment_generation: int,
    hold_slot: int,
    **kwargs: Any,
) -> dict[str, Any]:
    payload = _envelope_fields(state_before, state_after, **kwargs)
    payload.update(
        {
            "object_id": object_id,
            "body_instance_id": body_instance_id,
            "old_attachment_generation": old_attachment_generation,
            "new_attachment_generation": new_attachment_generation,
            "hold_slot": hold_slot,
        }
    )
    return {
        "event_id": kwargs.get("event_id") or new_id(),
        "event_type": HABITAT_HELD_BINDING_REBASED,
        "payload": payload,
    }


def _bump_state(state: HabitatState, **updates: Any) -> HabitatState:
    bumped = replace(state, state_version=state.state_version + 1, **updates)
    return with_state_hash(bumped)


def _mutate_object(state: HabitatState, object_id: str, mutate_fn) -> HabitatState:
    obj = state.objects.get(object_id)
    if obj is None:
        raise HabitatEventError(f"missing_object:{object_id}")
    updated = apply_committed_object_mutation(obj, mutate_fn)
    objects = dict(state.objects)
    objects[object_id] = updated
    return _bump_state(state, objects=objects)


def _apply_mutation(
    state: HabitatState | None,
    event_type: str,
    payload: dict[str, Any],
) -> HabitatState:
    if event_type == HABITAT_INITIALIZED:
        new_state = _state_from_init_payload(payload["initial_state"])
        return new_state

    if state is None:
        raise HabitatEventError("missing_habitat_init")

    if event_type == HABITAT_ZONE_ADDED:
        zone = _zone_from_payload(payload["zone"])
        zones = dict(state.zones)
        zones[zone.zone_id] = zone
        definition_hash = compute_habitat_definition_hash(replace(state, zones=zones))
        return with_state_hash(
            replace(
                _bump_state(state, zones=zones),
                definition_hash=definition_hash,
            )
        )

    if event_type == HABITAT_OBJECT_CREATED:
        obj = _object_from_payload(payload["object"])
        objects = dict(state.objects)
        objects[obj.object_id] = obj
        definition_hash = compute_habitat_definition_hash(replace(state, objects=objects))
        return with_state_hash(
            replace(
                _bump_state(state, objects=objects),
                definition_hash=definition_hash,
            )
        )

    if event_type == HABITAT_OBJECT_STATE_CHANGED:
        object_id = str(payload["object_id"])
        new_state = _object_state_from_payload(payload["new_state"])

        def change_state(obj: HabitatObject) -> HabitatObject:
            return replace(obj, state=new_state)

        return _mutate_object(state, object_id, change_state)

    if event_type == HABITAT_OBJECT_MOVED:
        object_id = str(payload["object_id"])
        location = _location_from_payload(payload["new_location"])

        def move(obj: HabitatObject) -> HabitatObject:
            if not isinstance(obj.location, FreeLocation):
                raise HabitatEventError("moved_requires_free_location")
            if not isinstance(location, FreeLocation):
                raise HabitatEventError("moved_requires_free_target")
            return replace(obj, location=location)

        return _mutate_object(state, object_id, move)

    if event_type == HABITAT_OBJECT_PICKED_UP:
        object_id = str(payload["object_id"])
        location = _location_from_payload(payload["new_location"])

        def pick_up(obj: HabitatObject) -> HabitatObject:
            if not isinstance(obj.location, FreeLocation):
                raise HabitatEventError("pick_up_requires_free_location")
            if not isinstance(location, HeldByLocation):
                raise HabitatEventError("pick_up_requires_held_target")
            return replace(obj, location=location)

        return _mutate_object(state, object_id, pick_up)

    if event_type == HABITAT_OBJECT_PLACED:
        object_id = str(payload["object_id"])
        location = _location_from_payload(payload["new_location"])

        def place(obj: HabitatObject) -> HabitatObject:
            if not isinstance(obj.location, HeldByLocation):
                raise HabitatEventError("place_requires_held_location")
            if not isinstance(location, FreeLocation):
                raise HabitatEventError("place_requires_free_target")
            return replace(obj, location=location)

        return _mutate_object(state, object_id, place)

    if event_type == HABITAT_AFFORDANCE_ACTIVATED:
        object_id = str(payload["object_id"])
        new_state = _object_state_from_payload(payload["new_state"])

        def activate(obj: HabitatObject) -> HabitatObject:
            return replace(obj, state=new_state)

        return _mutate_object(state, object_id, activate)

    if event_type == HABITAT_AFFORDANCE_DEACTIVATED:
        object_id = str(payload["object_id"])
        new_state = _object_state_from_payload(payload["new_state"])

        def deactivate(obj: HabitatObject) -> HabitatObject:
            return replace(obj, state=new_state)

        return _mutate_object(state, object_id, deactivate)

    if event_type == HABITAT_TRANSITION_APPLIED:
        transition = _transition_from_payload(payload["transition"])
        transitions = state.active_environmental_transitions + (transition,)
        return _bump_state(state, active_environmental_transitions=transitions)

    if event_type == HABITAT_DEFINITION_MIGRATED:
        object_id = str(payload["object_id"])

        def migrate(obj: HabitatObject) -> HabitatObject:
            return migrate_object_definition(
                obj,
                new_definition_version=int(payload["new_definition_version"]),
                new_definition_hash=str(payload["new_definition_hash"]),
                migrate_fn=lambda current: _object_from_payload(payload["migrated_object"]),
            )

        return _mutate_object(state, object_id, migrate)

    if event_type == HABITAT_HELD_BINDING_REBASED:
        object_id = str(payload["object_id"])
        new_generation = int(payload["new_attachment_generation"])
        hold_slot = int(payload["hold_slot"])

        def rebase(obj: HabitatObject) -> HabitatObject:
            if not isinstance(obj.location, HeldByLocation):
                raise HabitatEventError("rebase_requires_held_location")
            return replace(
                obj,
                location=HeldByLocation(
                    body_instance_id=obj.location.body_instance_id,
                    attachment_generation=new_generation,
                    hold_slot=hold_slot,
                ),
            )

        return _mutate_object(state, object_id, rebase)

    raise HabitatEventError(f"unhandled_habitat_event:{event_type}")


def apply_habitat_event(state: HabitatState | None, event: dict[str, Any]) -> HabitatState:
    event_type = event.get("event_type")
    if event_type not in HABITAT_EVENT_TYPES:
        raise HabitatEventError(f"unknown_habitat_event:{event_type}")
    payload = event.get("payload") or {}

    if state is not None:
        if payload.get("habitat_id") and payload["habitat_id"] != state.habitat_id:
            raise HabitatEventError("habitat_id_mismatch")
        if (
            state.state_version == int(payload["new_state_version"])
            and state.state_hash == payload["new_state_hash"]
        ):
            return state
        if state.state_version != int(payload["prior_state_version"]):
            raise HabitatEventError("invalid_habitat_event_order")
        if state.state_hash != payload["prior_state_hash"]:
            raise HabitatEventError("habitat_state_hash_mismatch")
    elif event_type != HABITAT_INITIALIZED:
        raise HabitatEventError("missing_habitat_init")

    if event_type == HABITAT_BODY_ZONE_TRANSITIONED:
        if int(payload["prior_state_version"]) != int(payload["new_state_version"]):
            raise HabitatEventError("zone_transition_must_not_advance_version")
        if payload["prior_state_hash"] != payload["new_state_hash"]:
            raise HabitatEventError("zone_transition_must_not_change_hash")
        if state is None:
            raise HabitatEventError("invalid_habitat_event_order")
        return state

    new_state = _apply_mutation(state, event_type, payload)
    if new_state.state_version != int(payload["new_state_version"]):
        raise HabitatEventError("event_new_state_version_mismatch")
    if new_state.state_hash != payload["new_state_hash"]:
        raise HabitatEventError("event_new_state_hash_mismatch")
    return new_state


def replay_habitat_from_events(
    events: list[dict[str, Any]],
    *,
    fail_closed_missing: bool = True,
) -> HabitatState:
    if not events:
        if fail_closed_missing:
            raise HabitatEventError("missing_habitat_events_fail_closed")
        raise HabitatEventError("missing_habitat_events_fail_closed")
    state: HabitatState | None = None
    for event in events:
        state = apply_habitat_event(state, event)
    if state is None:
        raise HabitatEventError("missing_habitat_events_fail_closed")
    return state
