"""Canonical full-stack configuration for AS-015 requalification."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.as014.full_config import LEDGER_CONTRACT
from experiments.as014.full_config import config as _as014_config
from experiments.as014.full_config import fingerprint as _as014_fingerprint


DIRECTIVE = "UMBRA-AS-015"
BASELINE = "b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7"


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
    """Return AS-014's persistence contract plus the AS-015 production kernel.

    The viability kernel is production behavior, not an AS-015 config flag;
    this factory owns the remaining full-stack configuration values.
    """
    value = _as014_config(
        seed,
        db,
        regime,
        bounded_continuation=bounded_continuation,
        route_learning=route_learning,
        ledger_overrides=ledger_overrides,
    )
    value.viability_kernel_enabled = bool(viability_kernel)
    return value


def fingerprint(value: Any) -> dict[str, Any]:
    result = _as014_fingerprint(value)
    result["as015"] = {
        "directive": DIRECTIVE,
        "multi_need_viability_kernel": "enabled_by_current_production",
        "persistence_contract": dict(LEDGER_CONTRACT),
        "viability_kernel_enabled": bool(value.viability_kernel_enabled),
    }
    return result
