"""D-009 habitat experiment condition switches (C0–C13).

C2/C3 are isolated under `experiments/d009/diagnostic_controllers.py` and must
not share this production schema (same pattern as D-007 individuality C2/C3).
"""

from __future__ import annotations

from dataclasses import dataclass

_HABITAT_DIAGNOSTIC_ONLY_CONDITIONS = frozenset({"C2", "C3"})


class HabitatConfigError(Exception):
    """Raised when a diagnostic-only condition requests production `HabitatConfig`."""


@dataclass
class HabitatConfig:
    """Ablation switches for D-009 habitat conditions."""

    manipulation_candidates_enabled: bool = True
    affordance_execution_enabled: bool = True
    environmental_routines_enabled: bool = True
    habitat_dynamics_enabled: bool = True
    static_habitat: bool = False  # C1 — no persistent habitat mutation path
    reset_on_restart: bool = False  # C8
    p0_compatibility_mode: bool = False  # C13 — Gate 13 performance baseline


def condition_to_habitat_config(condition: str) -> HabitatConfig:
    """Map a D-009 ablation label to `HabitatConfig`.

  C2/C3 raise — those are experiments-only diagnostic controllers.
  C9/C10/C12 are harness-level controls (hostile UI, bypass attempts, replay
  shuffle) and keep the C0-like production schema here.
  """
    if condition in _HABITAT_DIAGNOSTIC_ONLY_CONDITIONS:
        raise HabitatConfigError(
            f"{condition}_is_experiments_only_diagnostic_not_production_schema"
        )
    cfg = HabitatConfig()
    if condition == "C0":
        return cfg
    if condition == "C1":
        cfg.static_habitat = True
        return cfg
    if condition == "C6":
        cfg.environmental_routines_enabled = False
        return cfg
    if condition == "C8":
        cfg.reset_on_restart = True
        return cfg
    if condition == "C13":
        cfg.p0_compatibility_mode = True
        cfg.manipulation_candidates_enabled = False
        cfg.affordance_execution_enabled = False
        cfg.environmental_routines_enabled = False
        cfg.habitat_dynamics_enabled = False
        return cfg
    if condition in ("C4", "C5", "C7", "C9", "C10", "C11", "C12"):
        return cfg
    if condition.startswith("C"):
        raise HabitatConfigError(f"unknown_habitat_condition:{condition}")
    return cfg


def p0_compatibility_config() -> HabitatConfig:
    """Frozen P0 compatibility mode (same as C13)."""
    return condition_to_habitat_config("C13")
