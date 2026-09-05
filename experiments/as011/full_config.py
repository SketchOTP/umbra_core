"""The single AS-011 full-stack configuration authority."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.as010.full_config import as010_config, semantic_fingerprint

DIRECTIVE = "UMBRA-AS-011"
BASELINE = "bcd5ff361a22288480dd16cf20e3aad432bda26e"
FULL_FLAGS = {"bounded_continuation_enabled": True, "route_demand_learning_enabled": True}


def as011_config(
    seed: int,
    db: Path,
    regime: str = "R0",
    *,
    bounded: bool = True,
    route_learning: bool = True,
) -> Any:
    """Build AS-010's proven full configuration through one AS-011 seam."""
    return as010_config(seed, db, regime, bounded=bounded, route_learning=route_learning)


def fingerprint(config: Any) -> dict[str, Any]:
    return semantic_fingerprint(config)
