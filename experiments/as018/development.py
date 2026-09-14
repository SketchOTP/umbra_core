"""Serial AS-018 excluded-development challenge over the current authority path."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

from experiments.as014 import qualification as _as014
from experiments.as014.qualification import HORIZON, REGIMES, SCENARIOS
from experiments.as018.full_config import BASELINE, DIRECTIVE, config, fingerprint


def _candidate_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def run_case(regime: str, seed: int, local_work: Path, horizon: int = HORIZON) -> dict[str, Any]:
    original = (_as014.config, _as014.fingerprint, _as014.DIRECTIVE, _as014.BASELINE)
    trace_path = local_work / "case-traces" / f"{regime}-{seed}.trace.jsonl"

    def traced_config(case_seed: int, db: Path, case_regime: str):
        value = config(case_seed, db, case_regime)
        value.decision_trace_path = str(trace_path)
        value.decision_trace_mode = "compact_acceptance"
        return value

    _as014.config, _as014.fingerprint = traced_config, fingerprint
    _as014.DIRECTIVE, _as014.BASELINE = DIRECTIVE, BASELINE
    try:
        row = _as014.run_case(regime, seed, local_work, horizon)
    finally:
        _as014.config, _as014.fingerprint, _as014.DIRECTIVE, _as014.BASELINE = original
    row.update(
        schema="AS018_DEVELOPMENT_CASE_V1",
        directive=DIRECTIVE,
        baseline=BASELINE,
        candidate_commit=_candidate_commit(),
        classification="excluded_development_not_formal_qualification",
        execution_mode="serial_local_sqlite",
        recovery_reachability_enabled=True,
        decision_trace_filename=str(trace_path.relative_to(local_work)),
    )
    return row


def execute(
    manifest: dict[str, Any],
    local_work: Path,
    *,
    on_case: Callable[[dict[str, Any]], None] | None = None,
    on_case_start: Callable[[dict[str, Any]], None] | None = None,
    on_execution_finished: Callable[[dict[str, Any]], None] | None = None,
    horizon: int = HORIZON,
) -> dict[str, Any]:
    regimes = manifest.get("development_regimes")
    if (
        manifest.get("schema") != "AS018_DEVELOPMENT_SEED_MANIFEST_V1"
        or manifest.get("directive") != DIRECTIVE
        or tuple(regimes or ()) != REGIMES
        or any(len(regimes[regime]) != 8 for regime in REGIMES)
        or horizon != HORIZON
    ):
        raise RuntimeError("AS018_DEVELOPMENT_MANIFEST_CONTRACT_INVALID")
    seeds = [int(seed) for regime in REGIMES for seed in regimes[regime]]
    if len(seeds) != 32 or len(set(seeds)) != 32:
        raise RuntimeError("AS018_DEVELOPMENT_SEED_UNIQUENESS_INVALID")
    local_work.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    for regime in REGIMES:
        for seed_index, seed in enumerate(regimes[regime]):
            if on_case_start is not None:
                on_case_start({
                    "stage": "STARTED",
                    "regime": regime,
                    "seed": int(seed),
                    "seed_index": seed_index,
                    "target_ticks": horizon,
                })
            row = run_case(regime, int(seed), local_work, horizon)
            row["seed_index"] = seed_index
            rows.append(row)
            if on_execution_finished is not None:
                on_execution_finished({"stage": "EXECUTION_FINISHED", **row})
            if on_case is not None:
                on_case(row)
            if row.get("terminal") != "completed":
                return {
                    "schema": "AS018_DEVELOPMENT_CHALLENGE_V1",
                    "directive": DIRECTIVE,
                    "expected_runs": 32,
                    "completed_runs": len(rows),
                    "all_completed": False,
                    "terminal": f"AS018_DEVELOPMENT_{regime}_FAIL",
                    "rows": rows,
                }
    return {
        "schema": "AS018_DEVELOPMENT_CHALLENGE_V1",
        "directive": DIRECTIVE,
        "expected_runs": 32,
        "completed_runs": 32,
        "all_completed": True,
        "terminal": "AS018_DEVELOPMENT_PASS",
        "rows": rows,
    }
