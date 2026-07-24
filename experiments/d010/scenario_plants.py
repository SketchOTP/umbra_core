"""D-010 scenario plants S0–S17 — event timing and opportunity only.

May shift periodic resource availability, partner cue timing, overlapping
recurrence opportunities, restart windows, downtime gaps, absence stretches,
and schedule-revision opportunities. Must never plant expectations, routines,
preferences, or forced actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from umbra_core.habitat.engine import HabitatEngine

_SCENARIO_IDS = tuple(f"S{i}" for i in range(18))


@dataclass(frozen=True)
class ScenarioPlant:
    tick: int
    plant_type: str
    object_id: str | None = None
    x: float | None = None
    y: float | None = None
    zone_id: str | None = None
    recurrence_key: str | None = None
    availability: str | None = None
    delay_ticks: int | None = None


# ponytail: inline scaffold — Task 11 freeze may move these to scenario-suite.json
_SCENARIO_PLANTS: dict[str, tuple[ScenarioPlant, ...]] = {
    "S0": (),  # baseline
    "S1": (ScenarioPlant(tick=60, plant_type="periodic_resource_window", object_id="resource:0"),),
    "S2": (ScenarioPlant(tick=80, plant_type="delayed_partner_cue", delay_ticks=20),),
    "S3": (ScenarioPlant(tick=100, plant_type="overlap_recurrence_opportunity", recurrence_key="rec:s9:a"),),
    "S4": (ScenarioPlant(tick=120, plant_type="overlap_recurrence_opportunity", recurrence_key="rec:s9:b"),),
    "S5": (ScenarioPlant(tick=150, plant_type="restart_mid_window", object_id="resource:0"),),
    "S6": (ScenarioPlant(tick=200, plant_type="downtime_gap_opportunity"),),
    "S7": (ScenarioPlant(tick=250, plant_type="absence_stretch", zone_id="zone:rest"),),
    "S8": (ScenarioPlant(tick=90, plant_type="relocate_object", object_id="resource:0", x=14.0, y=8.0),),
    "S9": (ScenarioPlant(tick=70, plant_type="temporary_unavailable", object_id="resource:0"),),
    "S10": (ScenarioPlant(tick=40, plant_type="schedule_revision_opportunity", recurrence_key="rec:rev:0"),),
    "S11": (),  # replay — harness-level
    "S12": (),  # migration — harness-level
    "S13": (ScenarioPlant(tick=180, plant_type="expose_zone_connection", zone_id="zone:explore"),),
    "S14": (ScenarioPlant(tick=220, plant_type="rest_opportunity", zone_id="zone:rest"),),
    "S15": (ScenarioPlant(tick=300, plant_type="enable_affordance_exposure", object_id="rest:0"),),
    "S16": (ScenarioPlant(tick=160, plant_type="block_affordance", object_id="resource:0"),),
    "S17": (ScenarioPlant(tick=280, plant_type="spawn_clutter", object_id="resource:0", x=6.0, y=16.0),),
}


def scenario_ids() -> tuple[str, ...]:
    return _SCENARIO_IDS


def plants_for_scenario(scenario_id: str) -> tuple[ScenarioPlant, ...]:
    if scenario_id not in _SCENARIO_PLANTS:
        raise ValueError(f"unknown_scenario:{scenario_id}")
    return _SCENARIO_PLANTS[scenario_id]


def apply_scenario_plants(
    engine: HabitatEngine | None,
    scenario_id: str,
    tick: int,
    *,
    opportunity_hook: Callable[[ScenarioPlant], bool] | None = None,
) -> int:
    """Apply timing/opportunity plants for `tick`. Returns plants applied."""
    applied = 0
    for plant in plants_for_scenario(scenario_id):
        if plant.tick != tick:
            continue
        if _apply_plant(engine, plant, opportunity_hook=opportunity_hook):
            applied += 1
    return applied


def _apply_plant(
    engine: HabitatEngine | None,
    plant: ScenarioPlant,
    *,
    opportunity_hook: Callable[[ScenarioPlant], bool] | None = None,
) -> bool:
    if opportunity_hook is not None:
        return opportunity_hook(plant)
    if engine is None:
        return plant.plant_type.endswith("_opportunity") or plant.plant_type in {
            "periodic_resource_window",
            "delayed_partner_cue",
            "downtime_gap_opportunity",
            "absence_stretch",
            "schedule_revision_opportunity",
            "restart_mid_window",
            "overlap_recurrence_opportunity",
        }
    if plant.plant_type == "relocate_object":
        if plant.object_id is None or plant.x is None or plant.y is None:
            return False
        obj = engine.get_object(plant.object_id)
        if obj is None:
            return False
        engine.commit_free_location(plant.object_id, plant.x, plant.y, zone_id=plant.zone_id)
        return True
    if plant.plant_type in (
        "periodic_resource_window",
        "delayed_partner_cue",
        "overlap_recurrence_opportunity",
        "restart_mid_window",
        "downtime_gap_opportunity",
        "absence_stretch",
        "schedule_revision_opportunity",
        "expose_zone_connection",
        "rest_opportunity",
        "enable_affordance_exposure",
    ):
        return True  # ponytail: opportunity markers; formal harness expands in Task 11
    if plant.plant_type == "block_affordance":
        if plant.object_id is None:
            return False
        obj = engine.get_object(plant.object_id)
        return obj is not None
    if plant.plant_type == "temporary_unavailable":
        if plant.object_id is None:
            return False
        return engine.get_object(plant.object_id) is not None
    if plant.plant_type == "spawn_clutter":
        if plant.object_id is None or plant.x is None or plant.y is None:
            return False
        obj = engine.get_object(plant.object_id)
        if obj is None:
            return False
        engine.commit_free_location(plant.object_id, plant.x, plant.y)
        return True
    return False


def assert_timing_opportunity_only_plant(plant: ScenarioPlant) -> None:
    forbidden = {
        "expectation",
        "routine",
        "preference",
        "forced_action",
        "habit",
        "personality",
        "belief",
        "presentation",
        "disposition",
    }
    blob = (
        f"{plant.plant_type}:{plant.object_id}:{plant.zone_id}:"
        f"{plant.recurrence_key}:{plant.availability}"
    ).lower()
    if any(word in blob for word in forbidden):
        raise ValueError(f"scenario_plant_touches_forbidden_state:{plant.plant_type}")
