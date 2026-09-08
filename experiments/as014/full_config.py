"""Canonical current full-stack configuration for AS-014 requalification."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.as010.full_config import as010_config, semantic_fingerprint


DIRECTIVE = "UMBRA-AS-014"
BASELINE = "a97171a2dab7c1750e2556727bce9e3648bb359a"
LEDGER_CONTRACT = {
    "ledger_compaction_enabled": True,
    "ledger_hot_tail_event_max": 32_768,
    "ledger_max_events_per_tick": 32,
    "ledger_checkpoint_keep": 4,
    "ledger_physical_reclaim": True,
}


def config(
    seed: int,
    db: Path,
    regime: str = "R0",
    *,
    bounded_continuation: bool = True,
    route_learning: bool = True,
    ledger_overrides: dict[str, Any] | None = None,
) -> Any:
    """Build the AS-007 full configuration plus AS-014 persistence only."""
    value = as010_config(
        seed,
        db,
        regime,
        bounded=bounded_continuation,
        route_learning=route_learning,
    )
    for name, setting in {**LEDGER_CONTRACT, **(ledger_overrides or {})}.items():
        setattr(value, name, setting)
    return value


def fingerprint(value: Any) -> dict[str, Any]:
    result = semantic_fingerprint(value)
    result["ledger"] = {
        name: getattr(value, name)
        for name in LEDGER_CONTRACT
    }
    return result
