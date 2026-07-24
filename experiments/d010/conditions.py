"""D-010 condition label → TemporalConfig mapping (harness only)."""

from __future__ import annotations

from umbra_core.temporal.config import TemporalConfig, p0_performance_config

_DIAGNOSTIC_ONLY_CONDITIONS = frozenset({"C2", "C3", "C7", "C9", "C10", "C12"})
CONTROL_CONDITION_IDS: tuple[str, ...] = tuple(f"C{i}" for i in range(1, 14))
QUALIFICATION_BASELINE_CONDITION = "C0"


class TemporalConditionError(Exception):
    """Raised when a diagnostic-only D-010 condition requests production config."""


def is_control_condition(condition: str) -> bool:
    return condition in CONTROL_CONDITION_IDS


def condition_to_temporal_config(condition: str) -> TemporalConfig:
    """Map a D-010 ablation label to `TemporalConfig`.

    C2/C3/C7/C9/C10/C12 raise — those are experiments-only diagnostics.
    C1 uses `OrganismConfig.temporal_enabled=False` instead of this mapper.
    """
    if condition in _DIAGNOSTIC_ONLY_CONDITIONS:
        raise TemporalConditionError(
            f"{condition}_is_experiments_only_diagnostic_not_production_schema"
        )
    if condition == "C0":
        return TemporalConfig()
    if condition == "C1":
        raise TemporalConditionError("C1_use_organism_config.temporal_enabled_false")
    if condition == "C4":
        return TemporalConfig(temporal_score_modifiers_enabled=False)
    if condition == "C5":
        return TemporalConfig(wait_generation_enabled=False)
    if condition == "C6":
        return TemporalConfig(temporal_routine_eligibility_enabled=False)
    if condition == "C8":
        return TemporalConfig(reset_on_restart=True)
    if condition == "C11":
        return TemporalConfig(frequency_only_recurrence=True)
    if condition == "C13":
        return p0_performance_config()
    if condition.startswith("C"):
        raise TemporalConditionError(f"unknown_temporal_condition:{condition}")
    return TemporalConfig()
