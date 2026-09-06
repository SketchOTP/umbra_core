"""Single AS-012 full-stack configuration authority."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.as010.full_config import as010_config, semantic_fingerprint

DIRECTIVE = "UMBRA-AS-012"
BASELINE = "b4cc014c3545e19fa0e755407fe2a466e23e72a5"


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
