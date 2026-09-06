"""Single AS-013 full-stack configuration authority."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.as010.full_config import as010_config, semantic_fingerprint

DIRECTIVE = "UMBRA-AS-013"
BASELINE = "2723c50d1f06abcae60573307adfe83229def4a6"


def config(
    seed: int,
    db: Path,
    regime: str = "R0",
    *,
    bounded_continuation: bool = True,
    route_learning: bool = True,
) -> Any:
    """Build the exact AS-007-equivalent full configuration through one seam."""
    return as010_config(
        seed,
        db,
        regime,
        bounded=bounded_continuation,
        route_learning=route_learning,
    )


def fingerprint(value: Any) -> dict[str, Any]:
    return semantic_fingerprint(value)
