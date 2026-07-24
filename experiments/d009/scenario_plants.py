"""D-009 scenario plants S0–S16 — environmental opportunities only.

May change zones, object availability, positions, and affordance exposure.
Must never set preferences, habits, personality, routines, beliefs, or
presentation state.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from umbra_core.habitat.state import (
    FreeLocation,
    with_object_state_hash,
    with_state_hash,
)

if TYPE_CHECKING:
    from umbra_core.habitat.engine import HabitatEngine

_SCENARIO_IDS = tuple(f"S{i}" for i in range(17))


@dataclass(frozen=True)
class ScenarioPlant:
    tick: int
    plant_type: str
    object_id: str | None = None
    x: float | None = None
    y: float | None = None
    zone_id: str | None = None
    availability: str | None = None


# ponytail: inline scaffold — Task 11 freeze commit may move these to scenario-suite.json
_SCENARIO_PLANTS: dict[str, tuple[ScenarioPlant, ...]] = {
    "S0": (),  # baseline — no plants
    "S1": (ScenarioPlant(tick=100, plant_type="expose_zone_connection", zone_id="zone:explore"),),
    "S2": (ScenarioPlant(tick=50, plant_type="relocate_object", object_id="resource:0", x=12.0, y=6.0),),
    "S3": (ScenarioPlant(tick=80, plant_type="enable_affordance_exposure", object_id="rest:0"),),
    "S4": (ScenarioPlant(tick=60, plant_type="block_affordance", object_id="resource:0"),),
    "S5": (ScenarioPlant(tick=120, plant_type="relocate_object", object_id="resource:0", x=7.0, y=7.0),),
    "S6": (ScenarioPlant(tick=40, plant_type="rest_opportunity", zone_id="zone:rest"),),
    "S7": (ScenarioPlant(tick=200, plant_type="enable_affordance_exposure", object_id="resource:0"),),
    "S8": (ScenarioPlant(tick=90, plant_type="relocate_object", object_id="resource:0", x=1.0, y=18.0),),
    "S9": (ScenarioPlant(tick=70, plant_type="temporary_unavailable", object_id="resource:0"),),
    "S10": (ScenarioPlant(tick=30, plant_type="relocate_object", object_id="resource:0", x=5.0, y=5.0),),
    "S11": (),  # replay scenario — no live plants
    "S12": (),  # migration scenario — no live plants
    "S13": (ScenarioPlant(tick=300, plant_type="spawn_clutter", object_id="resource:0", x=10.0, y=10.0),),
    "S14": (),  # contrasting individuals — identical habitat, no personality plants
    "S15": (ScenarioPlant(tick=150, plant_type="spawn_clutter", object_id="rest:0", x=14.0, y=14.0),),
    "S16": (ScenarioPlant(tick=180, plant_type="reverse_affordance", object_id="rest:0"),),
}


def scenario_ids() -> tuple[str, ...]:
    return _SCENARIO_IDS


def plants_for_scenario(scenario_id: str) -> tuple[ScenarioPlant, ...]:
    if scenario_id not in _SCENARIO_PLANTS:
        raise ValueError(f"unknown_scenario:{scenario_id}")
    return _SCENARIO_PLANTS[scenario_id]


def apply_scenario_plants(engine: HabitatEngine, scenario_id: str, tick: int) -> int:
    """Apply environmental opportunity plants for `tick`. Returns plants applied."""
    applied = 0
    for plant in plants_for_scenario(scenario_id):
        if plant.tick != tick:
            continue
        if _apply_plant(engine, plant):
            applied += 1
    return applied


def _apply_plant(engine: HabitatEngine, plant: ScenarioPlant) -> bool:
    if plant.plant_type == "relocate_object":
        if plant.object_id is None or plant.x is None or plant.y is None:
            return False
        obj = engine.get_object(plant.object_id)
        if obj is None or not isinstance(obj.location, FreeLocation):
            return False
        engine.commit_free_location(plant.object_id, plant.x, plant.y, zone_id=plant.zone_id)
        return True
    if plant.plant_type in ("enable_affordance_exposure", "rest_opportunity", "expose_zone_connection"):
        return True  # ponytail: opportunity-only markers; formal harness expands in Task 11
    if plant.plant_type == "block_affordance":
        if plant.object_id is None:
            return False
        obj = engine.get_object(plant.object_id)
        if obj is None:
            return False

        def block(current):
            return with_object_state_hash(replace(current, occluded=True))

        engine.commit_object_mutation(plant.object_id, block)
        return True
    if plant.plant_type == "temporary_unavailable":
        if plant.object_id is None:
            return False
        obj = engine.get_object(plant.object_id)
        if obj is None:
            return False

        def hide(current):
            return with_object_state_hash(replace(current, visibility="HIDDEN"))

        engine.commit_object_mutation(plant.object_id, hide)
        return True
    if plant.plant_type == "reverse_affordance":
        if plant.object_id is None:
            return False
        obj = engine.get_object(plant.object_id)
        if obj is None:
            return False

        def reverse(current):
            return with_object_state_hash(replace(current, occluded=True, condition=0.0))

        engine.commit_object_mutation(plant.object_id, reverse)
        return True
    if plant.plant_type == "spawn_clutter":
        # ponytail: relocate existing object as clutter proxy until spawn caps land
        if plant.object_id is None or plant.x is None or plant.y is None:
            return False
        obj = engine.get_object(plant.object_id)
        if obj is None or not isinstance(obj.location, FreeLocation):
            return False
        engine.commit_free_location(plant.object_id, plant.x, plant.y)
        return True
    return False


def assert_environment_only_plant(plant: ScenarioPlant) -> None:
    forbidden = {
        "preference",
        "habit",
        "personality",
        "routine",
        "belief",
        "presentation",
        "disposition",
    }
    blob = f"{plant.plant_type}:{plant.object_id}:{plant.zone_id}:{plant.availability}".lower()
    if any(word in blob for word in forbidden):
        raise ValueError(f"scenario_plant_touches_forbidden_state:{plant.plant_type}")
