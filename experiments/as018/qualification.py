"""AS-018 formal population wrapper with fail-closed case acceptance."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from experiments.as014.qualification import HORIZON, REGIMES, SCENARIOS
from experiments.as018.development import run_case
from experiments.as018.formal_accounting import FormalAccounting


DIRECTIVE = "UMBRA-AS-018"
ORGANISM_IMPLEMENTATION_SHA = "e8d048b510a477e677637b67bc0f56473cfe6540"
EXECUTION_SUBJECT = "d7968a2de557513f2316d684b394ed851d1aae51"


def validate_manifest(manifest: dict[str, Any]) -> None:
    regimes = manifest.get("formal_regimes")
    if (
        manifest.get("schema") != "AS018_FORMAL_SEED_MANIFEST_V1"
        or manifest.get("directive") != DIRECTIVE
        or manifest.get("seed_status") != "frozen_before_formal_execution"
        or manifest.get("organism_implementation_sha") != ORGANISM_IMPLEMENTATION_SHA
        or manifest.get("formal_execution_subject") != EXECUTION_SUBJECT
        or tuple(regimes or ()) != REGIMES
        or any(len(regimes[regime]) != 8 for regime in REGIMES)
        or manifest.get("ticks_per_organism") != HORIZON
        or manifest.get("total_organisms") != 32
        or manifest.get("total_ticks") != 230400
        or any(manifest.get(name) != 0 for name in ("retries", "reseeds", "substitutions", "formal_seeds_consumed"))
    ):
        raise RuntimeError("AS018_FORMAL_MANIFEST_CONTRACT_INVALID")
    seeds = [int(seed) for regime in REGIMES for seed in regimes[regime]]
    if len(seeds) != 32 or len(set(seeds)) != 32:
        raise RuntimeError("AS018_FORMAL_SEED_UNIQUENESS_INVALID")


def _case_id(regime: str, index: int, seed: int) -> str:
    return f"{regime}-{index:02d}-{seed}"


def execute(
    manifest: dict[str, Any],
    work: Path,
    *,
    candidate_commit: str,
    manifest_sha256: str,
    on_case_start: Callable[[dict[str, Any]], None] | None = None,
    on_execution_finished: Callable[[dict[str, Any]], None] | None = None,
    accept_case: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    on_stage: Callable[[str, str, dict[str, Any]], None] | None = None,
    horizon: int = HORIZON,
) -> dict[str, Any]:
    validate_manifest(manifest)
    if horizon != HORIZON:
        raise RuntimeError("AS018_FORMAL_HORIZON_INVALID")
    if accept_case is None:
        raise RuntimeError("AS018_FORMAL_ACCEPTANCE_CALLBACK_REQUIRED")
    case_ids = tuple(
        _case_id(regime, index, int(seed))
        for regime in REGIMES
        for index, seed in enumerate(manifest["formal_regimes"][regime])
    )
    accounting = FormalAccounting(case_ids)
    if work.exists():
        raise RuntimeError("AS018_FORMAL_WORK_PATH_ALREADY_EXISTS")
    work.mkdir(parents=True)
    rows: list[dict[str, Any]] = []
    started: list[dict[str, Any]] = []
    for case_id in case_ids:
        if on_stage is not None:
            on_stage("REGISTERED", case_id, {})
    for regime in REGIMES:
        for seed_index, seed in enumerate(manifest["formal_regimes"][regime]):
            seed = int(seed)
            case_id = _case_id(regime, seed_index, seed)
            accounting.start(case_id)
            start = {
                "stage": "STARTED",
                "case_id": case_id,
                "regime": regime,
                "seed": seed,
                "seed_index": seed_index,
                "target_ticks": horizon,
            }
            started.append(start)
            if on_case_start is not None:
                on_case_start(start)
            row = run_case(regime, seed, work, horizon)
            row.update(
                schema="AS018_FORMAL_CASE_V1",
                directive=DIRECTIVE,
                classification="formal_qualification_candidate",
                candidate_commit=candidate_commit,
                seed_manifest_sha256=manifest_sha256,
                organism_implementation_sha=ORGANISM_IMPLEMENTATION_SHA,
                formal_execution_subject=EXECUTION_SUBJECT,
                regime=regime,
                scenario=SCENARIOS[regime],
                seed_index=seed_index,
            )
            accounting.execution_finished(case_id)
            if on_execution_finished is not None:
                on_execution_finished(row)
            accounting.validation_started(case_id)
            acceptance = accept_case(row)
            if acceptance.get("verdict") != "PASS":
                accounting.reject(case_id)
                return {
                    "schema": "AS018_FORMAL_POPULATION_V1",
                    "directive": DIRECTIVE,
                    "candidate_commit": candidate_commit,
                    "seed_manifest_sha256": manifest_sha256,
                    "expected_runs": 32,
                    "completed_runs": len(rows),
                    "started_cases": started,
                    "formal_seed_consumption": len(accounting.consumed),
                    "all_completed": False,
                    "terminal": "AS018_FORMAL_CASE_ACCEPTANCE_FAIL",
                    "failure": acceptance,
                    "accounting": accounting.summary(),
                    "rows": rows,
                }
            accounting.locally_validated(case_id)
            accounting.export_verified(case_id)
            accounting.finish(case_id)
            row["formal_acceptance"] = acceptance
            rows.append(row)
    summary = accounting.summary()
    if not summary["population_acceptance_ready"]:
        raise RuntimeError("AS018_FORMAL_ACCOUNTING_NOT_COMPLETE")
    return {
        "schema": "AS018_FORMAL_POPULATION_V1",
        "directive": DIRECTIVE,
        "candidate_commit": candidate_commit,
        "seed_manifest_sha256": manifest_sha256,
        "expected_runs": 32,
        "completed_runs": 32,
        "accepted_cases": 32,
        "started_cases": started,
        "formal_seed_consumption": len(accounting.consumed),
        "retries": 0,
        "reseeds": 0,
        "substitutions": 0,
        "all_completed": True,
        "terminal": "AS018_FORMAL_POPULATION_PASS",
        "accounting": summary,
        "rows": rows,
    }


__all__ = ["DIRECTIVE", "EXECUTION_SUBJECT", "HORIZON", "REGIMES", "SCENARIOS", "execute", "validate_manifest"]
