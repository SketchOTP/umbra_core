"""AS-016-owned R0--R3 population execution.

Regime mechanics remain imported from AS-014, while configuration authority,
result schemas, and baseline are AS-016 owned.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from experiments.as014 import qualification as _as014
from experiments.as014.qualification import HORIZON, REGIMES, SCENARIOS
from experiments.as016.full_config import BASELINE, DIRECTIVE


def run_case(
    regime: str,
    seed: int,
    work: Path,
    horizon: int = HORIZON,
) -> dict[str, Any]:
    original = (_as014.config, _as014.fingerprint, _as014.DIRECTIVE, _as014.BASELINE)
    from experiments.as016.full_config import config, fingerprint

    _as014.config, _as014.fingerprint = config, fingerprint
    _as014.DIRECTIVE, _as014.BASELINE = DIRECTIVE, BASELINE
    try:
        row = _as014.run_case(regime, seed, work, horizon)
    finally:
        _as014.config, _as014.fingerprint, _as014.DIRECTIVE, _as014.BASELINE = original
    row.update(
        schema="AS016_FORMAL_CASE_V1",
        directive=DIRECTIVE,
        baseline=BASELINE,
        inherited_regime_harness="AS014_R0_R3_SEMANTICS_UNCHANGED",
    )
    return row


def execute(
    manifest: dict[str, Any],
    work: Path,
    *,
    on_case: Callable[[dict[str, Any]], None] | None = None,
    horizon: int = HORIZON,
    preflight: bool = False,
) -> dict[str, Any]:
    regimes = manifest.get("formal_regimes")
    per_regime = 1 if preflight else 8
    if (
        manifest.get("directive") != DIRECTIVE
        or tuple(regimes or ()) != REGIMES
        or any(len(regimes[regime]) != per_regime for regime in REGIMES)
        or horizon < 1
    ):
        raise RuntimeError("AS016_FORMAL_MANIFEST_INVALID")
    work.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    for regime in REGIMES:
        for index, seed in enumerate(regimes[regime]):
            row = run_case(regime, int(seed), work, horizon)
            row["seed_index"] = index
            rows.append(row)
            if on_case is not None:
                on_case(row)
            if row["terminal"] != "completed":
                return {
                    "schema": "AS016_FORMAL_POPULATION_V1",
                    "directive": DIRECTIVE,
                    "baseline": BASELINE,
                    "expected_runs": len(REGIMES) * per_regime,
                    "completed_runs": len(rows),
                    "terminal": f"AS016_FRESH_{regime}_FAIL",
                    "rows": rows,
                }
    return {
        "schema": "AS016_FORMAL_POPULATION_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "expected_runs": len(REGIMES) * per_regime,
        "completed_runs": len(REGIMES) * per_regime,
        "all_completed": True,
        "rows": rows,
    }


__all__ = ["HORIZON", "REGIMES", "SCENARIOS", "execute", "run_case"]
