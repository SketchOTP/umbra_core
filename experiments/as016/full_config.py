"""Canonical full-stack configuration for AS-016 requalification."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.as015.full_config import config as _as015_config
from experiments.as015.full_config import fingerprint as _as015_fingerprint


DIRECTIVE = "UMBRA-AS-016"
BASELINE = "17859e03143b2278e612efeb3e96684f830b741f"
def config(
    seed: int,
    db: Path,
    regime: str = "R0",
    *,
    bounded_continuation: bool = True,
    route_learning: bool = True,
    viability_kernel: bool = True,
    ledger_overrides: dict[str, Any] | None = None,
) -> Any:
    """Return the exact AS-015 full stack under AS-016 repair authority."""
    value = _as015_config(
        seed,
        db,
        regime,
        bounded_continuation=bounded_continuation,
        route_learning=route_learning,
        viability_kernel=viability_kernel,
        ledger_overrides=ledger_overrides,
    )
    return value


def fingerprint(value: Any) -> dict[str, Any]:
    result = _as015_fingerprint(value)
    result["as016"] = {
        "directive": DIRECTIVE,
        "orient_preflight": "immediate_or_delayed_dispatch_mirror",
        "regulatory_endpoints": "current_authority_effect_derived",
        "physiology_projection": "effect_clamp_then_drift_clamp",
        "recovery_reserve": "all_active_needs_robustly_covered",
    }
    return result
