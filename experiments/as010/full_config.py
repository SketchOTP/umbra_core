"""Single canonical AS-010 runtime configuration.

The base regime is the established D-014 configuration.  The two material
AS-007 full-stack switches are explicit here so downstream harnesses cannot
silently fall back to the reduced D-014 configuration.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.d014.run_formal import config as d014_config
from umbra_core.world_model import condition_to_world_model_config

SCENARIOS = {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}


def as010_config(
    seed: int,
    db: Path,
    regime: str,
    *,
    decision_trace: Path | None = None,
    planning_shadow: Path | None = None,
    bounded: bool = True,
    route_learning: bool = True,
) -> Any:
    if regime not in SCENARIOS:
        raise ValueError(f"unknown AS-010 regime: {regime}")
    value = d014_config(seed, db, regime)
    value.bounded_continuation_enabled = bounded
    value.world_model_enabled = True
    world_config = value.world_model_config or condition_to_world_model_config("C0")
    world_config.route_demand_learning_enabled = route_learning
    value.world_model_config = world_config
    value.decision_trace_path = str(decision_trace) if decision_trace else None
    value.planning_shadow_path = str(planning_shadow) if planning_shadow else None
    return value


def semantic_fingerprint(value: Any) -> dict[str, Any]:
    """Stable, source-level-independent fingerprint of behaviorally relevant config."""
    fields = (
        "seed", "condition", "snapshot_every", "drift_enabled", "arbitration_mode",
        "leak_world_truth", "governance_bypass", "self_model_enabled",
        "world_model_enabled", "development_enabled", "memory_enabled", "social_enabled",
        "individuality_enabled", "embodiment_adapter_enabled", "expression_enabled",
        "habitat_enabled", "habitat_scenario_id", "temporal_enabled", "temporal_scenario_id",
        "bounded_continuation_enabled",
    )
    result = {name: getattr(value, name) for name in fields}
    wc = value.world_model_config or condition_to_world_model_config("C0")
    result["world_model_config"] = {
        "learning_enabled": wc.learning_enabled,
        "prediction_enabled": wc.prediction_enabled,
        "affordance_learning": wc.affordance_learning,
        "contradiction_revision": wc.contradiction_revision,
        "object_persistence": wc.object_persistence,
        "planning_enabled": wc.planning_enabled,
        "route_demand_learning_enabled": wc.route_demand_learning_enabled,
        "max_route_experiences": wc.max_route_experiences,
    }
    result["hooks"] = {
        "habitat_scenario_hook": getattr(value.habitat_scenario_hook, "__name__", None),
        "temporal_scenario_hook": getattr(value.temporal_scenario_hook, "__name__", None),
    }
    return result
