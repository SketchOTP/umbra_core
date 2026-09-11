"""Serial AS-017 development challenge using isolated local SQLite work."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from experiments.as014 import qualification as _as014
from experiments.as014.qualification import HORIZON, REGIMES
from experiments.as016.full_config import config, fingerprint


DIRECTIVE = "UMBRA-AS-017"
BASELINE = "fd8c50e1134d7d2ef54e20148ac9b7880e63708d"


def run_case(regime: str, seed: int, local_work: Path, horizon: int = HORIZON) -> dict[str, Any]:
    """Reuse frozen regime mechanics with an inert per-case decision trace."""
    original = (_as014.config, _as014.fingerprint, _as014.DIRECTIVE, _as014.BASELINE)
    trace_path = local_work / "case-traces" / f"{regime}-{seed}.trace.jsonl"

    def traced_config(case_seed: int, db: Path, case_regime: str):
        value = config(case_seed, db, case_regime)
        # DecisionTraceSink is default-disabled and never read by policy.  It
        # records the prospective certificate-to-execution linkage only.
        value.decision_trace_path = str(trace_path)
        return value

    _as014.config, _as014.fingerprint = traced_config, fingerprint
    _as014.DIRECTIVE, _as014.BASELINE = DIRECTIVE, BASELINE
    try:
        row = _as014.run_case(regime, seed, local_work, horizon)
    finally:
        _as014.config, _as014.fingerprint, _as014.DIRECTIVE, _as014.BASELINE = original
    row.update(
        schema="AS017_DEVELOPMENT_CASE_V2",
        directive=DIRECTIVE,
        baseline=BASELINE,
        classification="excluded_development_not_formal_qualification",
        execution_mode="serial_local_sqlite",
        decision_trace_filename=str(trace_path.relative_to(local_work)),
    )
    return row


def execute(
    manifest: dict[str, Any], local_work: Path, *, on_case: Callable[[dict[str, Any]], None], horizon: int = HORIZON
) -> dict[str, Any]:
    regimes = manifest.get("development_regimes")
    if (
        manifest.get("directive") != DIRECTIVE
        or tuple(regimes or ()) != REGIMES
        or any(len(regimes[regime]) != 4 for regime in REGIMES)
        or horizon != HORIZON
    ):
        raise RuntimeError("AS017_DEVELOPMENT_MANIFEST_CONTRACT_INVALID")
    local_work.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    for regime in REGIMES:
        for seed_index, seed in enumerate(regimes[regime]):
            row = run_case(regime, int(seed), local_work, horizon)
            row["seed_index"] = seed_index
            rows.append(row)
            on_case(row)
            if row.get("terminal") != "completed":
                return {"schema": "AS017_DEVELOPMENT_CHALLENGE_V2", "directive": DIRECTIVE,
                        "terminal": f"AS017_DEVELOPMENT_{regime}_FAIL", "expected_runs": 16,
                        "completed_runs": len(rows), "all_completed": False, "rows": rows}
    return {"schema": "AS017_DEVELOPMENT_CHALLENGE_V2", "directive": DIRECTIVE,
            "terminal": "AS017_DEVELOPMENT_PASS", "expected_runs": 16,
            "completed_runs": 16, "all_completed": True, "rows": rows}
