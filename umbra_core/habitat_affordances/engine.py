"""Pure HabitatAffordanceEngine — validation and effect planning only."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

from umbra_core.habitat.engine import BodyPoseView, HabitatSnapshot, ReachProfile
from umbra_core.habitat.events import object_state_to_payload
from umbra_core.habitat.state import (
    ActivatableState,
    FreeLocation,
    HabitatObject,
    HeldByLocation,
    ObjectKind,
    ObjectState,
    ResourceState,
    StationState,
)
from umbra_core.habitat_affordances.definitions import (
    AffordanceDefinition,
    AffordanceOperation,
    AffordancePreconditions,
    WorldEffectMutation,
    default_affordance_definitions,
    definition_hash,
)

MAX_COORDINATE = 20.0
MAX_PUSH_DISTANCE = 5.0
MAX_DIRECTION_COMPONENT = 1.0


@dataclass(frozen=True)
class PickUpParameters:
    kind: str = "PICK_UP"
    hold_slot: int = 0


@dataclass(frozen=True)
class PlaceParameters:
    kind: str = "PLACE"
    target_x: float = 0.0
    target_y: float = 0.0
    expected_zone_id: str = ""
    support_object_id: str | None = None


@dataclass(frozen=True)
class PushParameters:
    kind: str = "PUSH"
    direction_x: float = 0.0
    direction_y: float = 0.0
    requested_distance: float = 0.0


@dataclass(frozen=True)
class ActivateParameters:
    kind: str = "ACTIVATE"


@dataclass(frozen=True)
class DeactivateParameters:
    kind: str = "DEACTIVATE"


@dataclass(frozen=True)
class UseParameters:
    kind: str = "USE"


ManipulationParameters = (
    PickUpParameters
    | PlaceParameters
    | PushParameters
    | ActivateParameters
    | DeactivateParameters
    | UseParameters
)

_PARAMETER_BOUNDS: dict[str, tuple[float, float]] = {
    "target_x": (0.0, MAX_COORDINATE),
    "target_y": (0.0, MAX_COORDINATE),
    "direction_x": (-MAX_DIRECTION_COMPONENT, MAX_DIRECTION_COMPONENT),
    "direction_y": (-MAX_DIRECTION_COMPONENT, MAX_DIRECTION_COMPONENT),
    "requested_distance": (0.0, MAX_PUSH_DISTANCE),
}


@dataclass(frozen=True)
class ManipulationRequest:
    request_id: str
    execution_id: str
    capability: str
    target_object_id: str
    affordance_id: str
    expected_habitat_version: int
    expected_habitat_state_hash: str
    target_object_version: int
    target_object_definition_version: int
    target_object_definition_hash: str
    affordance_definition_version: int
    affordance_definition_hash: str
    body_instance_id: str
    body_profile_id: str
    attachment_generation: int
    parameters: ManipulationParameters


@dataclass(frozen=True)
class AdapterValidatedManipulation:
    body_pose_view: BodyPoseView
    reach_profile: ReachProfile
    requested_parameters: ManipulationParameters
    applied_parameters: ManipulationParameters
    validated_profile: Any
    translation_applied: bool = False


@dataclass(frozen=True)
class HabitatEffectPlan:
    habitat_mutations: tuple[dict[str, Any], ...]
    habitat_events: tuple[dict[str, Any], ...]
    requested_organism_effects: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class AffordanceValidationResult:
    allowed: bool
    failure_code: str | None
    expected_object_version: int | None
    expected_habitat_version: int | None
    effect_plan: HabitatEffectPlan | None
    applied_parameters: ManipulationParameters | None


def validate_manipulation_parameters(params: ManipulationParameters) -> str | None:
    """Return failure code when parameters are malformed or out of bounds."""
    if isinstance(params, PickUpParameters):
        if params.hold_slot < 0 or params.hold_slot > 0:
            return "HOLD_SLOT_UNAVAILABLE"
        return None
    if isinstance(params, PlaceParameters):
        for field_name in ("target_x", "target_y"):
            value = getattr(params, field_name)
            lo, hi = _PARAMETER_BOUNDS[field_name]
            if not math.isfinite(value) or value < lo or value > hi:
                return "PLACEMENT_POSITION_INVALID"
        if not params.expected_zone_id:
            return "MALFORMED_MANIPULATION_REQUEST"
        return None
    if isinstance(params, PushParameters):
        for field_name in ("direction_x", "direction_y", "requested_distance"):
            value = getattr(params, field_name)
            lo, hi = _PARAMETER_BOUNDS[field_name]
            if not math.isfinite(value) or value < lo or value > hi:
                return "MALFORMED_MANIPULATION_REQUEST"
        magnitude = math.hypot(params.direction_x, params.direction_y)
        if magnitude <= 0.0 or magnitude > math.sqrt(2.0) + 1e-9:
            return "MALFORMED_MANIPULATION_REQUEST"
        return None
    if isinstance(params, (ActivateParameters, DeactivateParameters, UseParameters)):
        return None
    return "MALFORMED_MANIPULATION_REQUEST"


def _operation_for_parameters(params: ManipulationParameters) -> AffordanceOperation:
    return AffordanceOperation(params.kind)


def _cooldown_active(obj: HabitatObject, affordance_id: str, habitat_tick: int) -> bool:
    for aff_id, until_tick in obj.cooldowns:
        if aff_id == affordance_id and habitat_tick < until_tick:
            return True
    return False


def _check_preconditions(
    obj: HabitatObject,
    pre: AffordancePreconditions,
    *,
    body_instance_id: str,
) -> str | None:
    if pre.requires_portable and not obj.portable:
        return "OBJECT_NOT_PORTABLE"
    if pre.requires_free_location and not isinstance(obj.location, FreeLocation):
        return "AFFORDANCE_PRECONDITION_FAILED"
    if pre.requires_not_held and isinstance(obj.location, HeldByLocation):
        return "OBJECT_ALREADY_HELD"
    if pre.requires_held_by_body:
        if not isinstance(obj.location, HeldByLocation):
            return "NO_OBJECT_HELD"
        if obj.location.body_instance_id != body_instance_id:
            return "OBJECT_NOT_HELD_BY_BODY"
    if pre.requires_remaining_yield_min is not None:
        if not isinstance(obj.state, ResourceState):
            return "AFFORDANCE_PRECONDITION_FAILED"
        if obj.state.remaining_yield < pre.requires_remaining_yield_min:
            return "AFFORDANCE_PRECONDITION_FAILED"
    if pre.requires_station_available is not None:
        if not isinstance(obj.state, StationState):
            return "AFFORDANCE_PRECONDITION_FAILED"
        if obj.state.available is not pre.requires_station_available:
            return "AFFORDANCE_PRECONDITION_FAILED"
    if pre.requires_activatable_active is not None:
        if not isinstance(obj.state, ActivatableState):
            return "AFFORDANCE_PRECONDITION_FAILED"
        if obj.state.active is not pre.requires_activatable_active:
            return "AFFORDANCE_PRECONDITION_FAILED"
    return None


def _apply_world_effect_mutations(state: ObjectState, mutations: tuple[WorldEffectMutation, ...]) -> ObjectState:
    updated = state
    for mutation in mutations:
        if mutation.field == "state.remaining_yield":
            if not isinstance(updated, ResourceState):
                raise ValueError("world_effect_requires_resource_state")
            if not isinstance(mutation.delta, (int, float)):
                raise ValueError("world_effect_yield_delta_must_be_numeric")
            updated = replace(updated, remaining_yield=updated.remaining_yield + float(mutation.delta))
        elif mutation.field == "state.active":
            if not isinstance(updated, ActivatableState):
                raise ValueError("world_effect_requires_activatable_state")
            if not isinstance(mutation.delta, bool):
                raise ValueError("world_effect_active_delta_must_be_bool")
            updated = replace(updated, active=mutation.delta)
        else:
            raise ValueError(f"unsupported_world_effect_field:{mutation.field}")
    return updated


def _build_effect_plan(
    defn: AffordanceDefinition,
    obj: HabitatObject,
    params: ManipulationParameters,
    *,
    habitat_tick: int,
    body_instance_id: str,
    attachment_generation: int,
) -> HabitatEffectPlan:
    mutations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    organism_effects = [
        {"effect_kind": effect.effect_kind, "magnitude": effect.magnitude}
        for effect in defn.organism_effect_contract.effects
    ]
    if defn.operation == AffordanceOperation.PICK_UP and isinstance(params, PickUpParameters):
        mutations.append(
            {
                "mutation_kind": "SET_LOCATION",
                "object_id": obj.object_id,
                "location": {
                    "mode": "HELD_BY",
                    "body_instance_id": body_instance_id,
                    "attachment_generation": attachment_generation,
                    "hold_slot": params.hold_slot,
                },
            }
        )
        events.append({"event_type": "habitat_object_picked_up", "object_id": obj.object_id})
    elif defn.operation == AffordanceOperation.PLACE and isinstance(params, PlaceParameters):
        mutations.append(
            {
                "mutation_kind": "SET_LOCATION",
                "object_id": obj.object_id,
                "location": {
                    "mode": "FREE",
                    "x": params.target_x,
                    "y": params.target_y,
                    "zone_id": params.expected_zone_id,
                },
            }
        )
        events.append({"event_type": "habitat_object_placed", "object_id": obj.object_id})
    elif defn.operation == AffordanceOperation.PUSH and isinstance(params, PushParameters):
        if isinstance(obj.location, FreeLocation):
            norm = math.hypot(params.direction_x, params.direction_y)
            scale = params.requested_distance / norm if norm > 0 else 0.0
            mutations.append(
                {
                    "mutation_kind": "SET_LOCATION",
                    "object_id": obj.object_id,
                    "location": {
                        "mode": "FREE",
                        "x": obj.location.x + params.direction_x * scale,
                        "y": obj.location.y + params.direction_y * scale,
                        "zone_id": obj.location.zone_id,
                    },
                }
            )
            events.append({"event_type": "habitat_object_moved", "object_id": obj.object_id})
    elif defn.operation == AffordanceOperation.ACTIVATE:
        mutations.append({"mutation_kind": "SET_ACTIVATABLE_ACTIVE", "object_id": obj.object_id, "active": True})
        events.append({"event_type": "habitat_affordance_activated", "object_id": obj.object_id})
    elif defn.operation == AffordanceOperation.DEACTIVATE:
        mutations.append({"mutation_kind": "SET_ACTIVATABLE_ACTIVE", "object_id": obj.object_id, "active": False})
        events.append({"event_type": "habitat_affordance_deactivated", "object_id": obj.object_id})
    elif defn.operation == AffordanceOperation.USE:
        for mutation in defn.world_effect_contract.mutations:
            mutations.append(
                {
                    "mutation_kind": "APPLY_WORLD_EFFECT",
                    "object_id": obj.object_id,
                    "field": mutation.field,
                    "delta": mutation.delta,
                }
            )
        new_state = _apply_world_effect_mutations(obj.state, defn.world_effect_contract.mutations)
        events.append(
            {
                "event_type": "habitat_object_state_changed",
                "object_id": obj.object_id,
                "new_state": object_state_to_payload(new_state),
            }
        )
    if defn.cooldown_ticks > 0:
        mutations.append(
            {
                "mutation_kind": "SET_COOLDOWN",
                "object_id": obj.object_id,
                "affordance_id": defn.affordance_id,
                "cooldown_until_tick": habitat_tick + defn.cooldown_ticks,
            }
        )
    return HabitatEffectPlan(
        habitat_mutations=tuple(mutations),
        habitat_events=tuple(events),
        requested_organism_effects=tuple(organism_effects),
    )


class HabitatAffordanceEngine:
    """Pure affordance validation — never mutates habitat or organism state."""

    def __init__(self, definitions: dict[str, AffordanceDefinition] | None = None) -> None:
        self._definitions = definitions if definitions is not None else default_affordance_definitions()

    def get_definition(self, affordance_id: str) -> AffordanceDefinition | None:
        return self._definitions.get(affordance_id)

    def validate(
        self,
        request: ManipulationRequest,
        habitat_snapshot: HabitatSnapshot,
        adapter_validated: AdapterValidatedManipulation,
        *,
        in_range: bool = True,
    ) -> AffordanceValidationResult:
        _ = adapter_validated.translation_applied
        params = adapter_validated.applied_parameters
        param_failure = validate_manipulation_parameters(params)
        if param_failure is not None:
            return AffordanceValidationResult(
                allowed=False,
                failure_code=param_failure,
                expected_object_version=None,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if request.capability != "MANIPULATE":
            return AffordanceValidationResult(
                allowed=False,
                failure_code="UNSUPPORTED_BODY_CAPABILITY",
                expected_object_version=None,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        defn = self._definitions.get(request.affordance_id)
        if defn is None:
            return AffordanceValidationResult(
                allowed=False,
                failure_code="AFFORDANCE_NOT_SUPPORTED",
                expected_object_version=None,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if request.affordance_definition_version != defn.definition_version:
            return AffordanceValidationResult(
                allowed=False,
                failure_code="AFFORDANCE_DEFINITION_MISMATCH",
                expected_object_version=None,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if request.affordance_definition_hash != definition_hash(defn):
            return AffordanceValidationResult(
                allowed=False,
                failure_code="AFFORDANCE_DEFINITION_MISMATCH",
                expected_object_version=None,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if (
            request.expected_habitat_version != habitat_snapshot.state_version
            or request.expected_habitat_state_hash != habitat_snapshot.state_hash
        ):
            return AffordanceValidationResult(
                allowed=False,
                failure_code="HABITAT_STATE_CONFLICT",
                expected_object_version=None,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        obj = habitat_snapshot.objects.get(request.target_object_id)
        if obj is None:
            return AffordanceValidationResult(
                allowed=False,
                failure_code="OBJECT_NOT_FOUND",
                expected_object_version=None,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if request.target_object_version != obj.object_version:
            return AffordanceValidationResult(
                allowed=False,
                failure_code="STALE_OBJECT_VERSION",
                expected_object_version=obj.object_version,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if (
            request.target_object_definition_version != obj.definition_version
            or request.target_object_definition_hash != obj.definition_hash
        ):
            return AffordanceValidationResult(
                allowed=False,
                failure_code="OBJECT_DEFINITION_MISMATCH",
                expected_object_version=obj.object_version,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if request.affordance_id not in obj.affordance_ids:
            return AffordanceValidationResult(
                allowed=False,
                failure_code="AFFORDANCE_NOT_SUPPORTED",
                expected_object_version=obj.object_version,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if defn.target_object_kind != obj.object_kind:
            return AffordanceValidationResult(
                allowed=False,
                failure_code="AFFORDANCE_NOT_SUPPORTED",
                expected_object_version=obj.object_version,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if _operation_for_parameters(params) != defn.operation:
            return AffordanceValidationResult(
                allowed=False,
                failure_code="MALFORMED_MANIPULATION_REQUEST",
                expected_object_version=obj.object_version,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if not in_range:
            return AffordanceValidationResult(
                allowed=False,
                failure_code="OBJECT_OUT_OF_RANGE",
                expected_object_version=obj.object_version,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        if _cooldown_active(obj, request.affordance_id, habitat_snapshot.habitat_tick):
            return AffordanceValidationResult(
                allowed=False,
                failure_code="AFFORDANCE_COOLDOWN",
                expected_object_version=obj.object_version,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        precondition_failure = _check_preconditions(
            obj,
            defn.preconditions,
            body_instance_id=request.body_instance_id,
        )
        if precondition_failure is not None:
            return AffordanceValidationResult(
                allowed=False,
                failure_code=precondition_failure,
                expected_object_version=obj.object_version,
                expected_habitat_version=habitat_snapshot.state_version,
                effect_plan=None,
                applied_parameters=None,
            )
        effect_plan = _build_effect_plan(
            defn,
            obj,
            params,
            habitat_tick=habitat_snapshot.habitat_tick,
            body_instance_id=request.body_instance_id,
            attachment_generation=request.attachment_generation,
        )
        return AffordanceValidationResult(
            allowed=True,
            failure_code=None,
            expected_object_version=obj.object_version,
            expected_habitat_version=habitat_snapshot.state_version,
            effect_plan=effect_plan,
            applied_parameters=params,
        )
