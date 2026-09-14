"""AS-017 formal population wrapper over the validated full-stack case runner."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from experiments.as014.qualification import HORIZON, REGIMES, SCENARIOS
from experiments.as017.development import DIRECTIVE, run_case as run_development_case


def validate_manifest(manifest: dict[str, Any]) -> None:
    regimes = manifest.get("formal_regimes")
    if (
        manifest.get("schema") != "AS017_FORMAL_SEED_MANIFEST_V1"
        or manifest.get("directive") != DIRECTIVE
        or manifest.get("seed_status") != "frozen_before_formal_execution"
        or tuple(regimes or ()) != REGIMES
        or any(len(regimes[regime]) != 8 for regime in REGIMES)
    ):
        raise RuntimeError("AS017_FORMAL_MANIFEST_CONTRACT_INVALID")
    seeds = [int(seed) for regime in REGIMES for seed in regimes[regime]]
    if len(seeds) != 32 or len(set(seeds)) != 32:
        raise RuntimeError("AS017_FORMAL_MANIFEST_SEED_UNIQUENESS_INVALID")


def execute(
    manifest: dict[str, Any],
    work: Path,
    *,
    on_case: Callable[[dict[str, Any]], None] | None = None,
    horizon: int = HORIZON,
) -> dict[str, Any]:
    validate_manifest(manifest)
    if horizon != HORIZON:
        raise RuntimeError("AS017_FORMAL_HORIZON_INVALID")
    work.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    for regime in REGIMES:
        for seed_index, seed in enumerate(manifest["formal_regimes"][regime]):
            row = run_development_case(regime, int(seed), work, horizon)
            row.update(
                schema="AS017_FORMAL_CASE_V1",
                directive=DIRECTIVE,
                classification="formal_qualification_candidate",
                regime=regime,
                scenario=SCENARIOS[regime],
                seed_index=seed_index,
            )
            rows.append(row)
            if on_case is not None:
                on_case(row)
            if row.get("terminal") != "completed":
                return {
                    "schema": "AS017_FORMAL_POPULATION_V1",
                    "directive": DIRECTIVE,
                    "expected_runs": 32,
                    "completed_runs": len(rows),
                    "all_completed": False,
                    "terminal": f"AS017_FRESH_{regime}_FAIL",
                    "rows": rows,
                }
    return {
        "schema": "AS017_FORMAL_POPULATION_V1",
        "directive": DIRECTIVE,
        "expected_runs": 32,
        "completed_runs": 32,
        "all_completed": True,
        "terminal": "AS017_FORMAL_POPULATION_PASS",
        "rows": rows,
    }
