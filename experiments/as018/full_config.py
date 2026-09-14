"""AS-018 full configuration with the recovery envelope explicitly enabled."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.as016.full_config import config as _as016_config
from experiments.as016.full_config import fingerprint as _as016_fingerprint


DIRECTIVE = "UMBRA-AS-018"
BASELINE = "11795badd4b43126d62dfe6e15193cf2a0a170ac"


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
    """Use AS-016's accepted organism configuration plus AS-018 RRE."""
    value = _as016_config(
        seed,
        db,
        regime,
        bounded_continuation=bounded_continuation,
        route_learning=route_learning,
        viability_kernel=viability_kernel,
        ledger_overrides=ledger_overrides,
    )
    value.recovery_reachability_enabled = True
    return value


def fingerprint(value: Any) -> dict[str, Any]:
    result = _as016_fingerprint(value)
    result["as018"] = {
        "directive": DIRECTIVE,
        "baseline_organism_subject": BASELINE,
        "recovery_reachability_enabled": bool(value.recovery_reachability_enabled),
        "envelope_schema": "AS018_RECOVERY_REACHABILITY_ENVELOPE_V1",
        "filter_schema": "AS018_RECOVERY_REACHABILITY_FILTER_V1",
        "status_categories": [
            "ROBUST_NOW",
            "BOUNDED_RECOVERY_OPPORTUNITY",
            "MAY_ROUTE",
            "UNKNOWN_ROUTE",
        ],
        "activation": "precritical_recovery_reserve_threat_only",
        "authority": "constraint_only_existing_arbitration_preference",
    }
    return result

