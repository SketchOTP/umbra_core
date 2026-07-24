"""D-010 temporal experiment switches — production-safe config only.

Harness condition labels (C0–C13) map via `experiments/d010/conditions.py`.
Diagnostic controllers stay under `experiments/d010/` and must not be imported
from `umbra_core.temporal` engine modules.
"""

from __future__ import annotations

from dataclasses import dataclass

# D-010 control labels must not be activated through OrganismConfig.condition when
# temporal is enabled — harness passes `temporal_config` explicitly (C0 pin).
PRODUCTION_UNREACHABLE_CONTROL_IDS = frozenset(f"C{i}" for i in range(1, 14))


class TemporalConfigError(Exception):
    """Raised when a D-010 control is requested via production organism wiring."""


@dataclass
class TemporalConfig:
    """Ablation switches for D-010 temporal continuity conditions."""

    anticipation_enabled: bool = True
    temporal_routine_eligibility_enabled: bool = True
    temporal_score_modifiers_enabled: bool = True
    wait_generation_enabled: bool = True
    reset_on_restart: bool = False  # C8 — disposable paths only at harness layer
    frequency_only_recurrence: bool = False  # C11
    p0_performance_mode: bool = False  # C13 / Gate 13 P0 baseline


def resolve_temporal_config(config: TemporalConfig | None) -> TemporalConfig:
    return config or TemporalConfig()


def p0_performance_config() -> TemporalConfig:
    """Frozen P0 baseline — TemporalEngine on; anticipation + routines off."""
    return TemporalConfig(
        anticipation_enabled=False,
        temporal_routine_eligibility_enabled=False,
        wait_generation_enabled=False,
        temporal_score_modifiers_enabled=False,
        p0_performance_mode=True,
    )


def assert_no_d010_control_via_organism_condition(
    condition: str,
    *,
    temporal_enabled: bool,
) -> None:
    """Reject D-010 C1–C13 labels on OrganismConfig.condition when temporal is on."""
    if not temporal_enabled:
        return
    if condition in PRODUCTION_UNREACHABLE_CONTROL_IDS:
        raise TemporalConfigError(
            f"{condition}_d010_control_requires_explicit_temporal_config_not_organism_condition"
        )
