"""AS-007 frozen A/B/R1 qualification sequence.

This is a fresh harness namespace.  It preserves the AS-006 fixture, seeds,
horizons, and stop rule while enabling only the already-locked terminal
executability contract in production.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import experiments.close02r.qualification as base_runner
from experiments.d014.run_formal import config as d014_config
from umbra_core.world_model import condition_to_world_model_config


EVIDENCE = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-007-recovery-executability-integrated-viability-r1"
)
TERMINAL_CAPABILITIES = {"REST", "CHARGE", "INSPECT"}
STAGES = (
    ("DIAGNOSTIC_A", "R0", 45878900, 500),
    ("DIAGNOSTIC_B", "R0", 22023239, 3500),
    ("KNOWN_R1", "R1", 57531938, 7200),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return sha256(path)


def as007_config(seed: int, db: Path, regime: str, decision: Path, shadow: Path):
    value = d014_config(seed, db, regime)
    value.bounded_continuation_enabled = True
    value.world_model_enabled = True
    world_config = value.world_model_config or condition_to_world_model_config("C0")
    world_config.route_demand_learning_enabled = True
    value.world_model_config = world_config
    value.decision_trace_path = str(decision)
    value.planning_shadow_path = str(shadow)
    return value


def run_stage(stage: str, regime: str, seed: int, horizon: int, work: Path) -> dict[str, Any]:
    decision = EVIDENCE / f"AS007_{stage}_{seed}.decision.jsonl"
    shadow = EVIDENCE / f"AS007_{stage}_{seed}.planning.jsonl"
    database = work / f"AS007_{stage}_{seed}.sqlite"
    readiness: list[dict[str, Any]] = []
    original_config = base_runner.config
    original_prepare = base_runner.prepare

    def configured(case_seed: int, case_db: Path, case_regime: str):
        return as007_config(case_seed, case_db, case_regime, decision, shadow)

    def prepared(case_seed: int, case_db: Path, case_regime: str):
        organism, engine = original_prepare(case_seed, case_db, case_regime)
        original_readiness = organism._candidate_executability

        def observed(candidate: Any) -> str:
            status = original_readiness(candidate)
            if candidate.capability in TERMINAL_CAPABILITIES:
                readiness.append({
                    "decision_tick": organism.tick + 1,
                    "capability": candidate.capability,
                    "status": status,
                })
            return status

        organism._candidate_executability = observed
        return organism, engine

    base_runner.config = configured
    base_runner.prepare = prepared
    started = time.monotonic()
    try:
        row = base_runner.run_case(regime, seed, work, horizon)
    finally:
        base_runner.config = original_config
        base_runner.prepare = original_prepare
    row.update({
        "directive": "UMBRA-AS-007",
        "stage": stage,
        "decision_trace": str(decision),
        "planning_trace": str(shadow),
        "decision_trace_sha256": sha256(decision) if decision.exists() else None,
        "planning_trace_sha256": sha256(shadow) if shadow.exists() else None,
        "readiness_status_counts": {
            status: sum(item["status"] == status for item in readiness)
            for status in ("EXECUTABLE", "NOT_EXECUTABLE", "UNKNOWN")
        },
        "terminal_readiness_calls": len(readiness),
        "readiness_observations": readiness,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    })
    return row


def run_scientific(work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    for stage, regime, seed, horizon in STAGES:
        row = run_stage(stage, regime, seed, horizon, work)
        rows.append(row)
        if row.get("terminal") != "completed":
            verdict = "AS007_FRESH_R0_FAIL" if stage != "KNOWN_R1" else "AS007_KNOWN_R1_FAIL"
            result = {
                "schema": "AS007_SCIENTIFIC_SEQUENCE_V1",
                "directive": "UMBRA-AS-007",
                "terminal_stage": stage,
                "rows": rows,
                "verdict": verdict,
                "retries": 0,
                "reseeds": 0,
                "organism_runs": len(rows),
                "organism_ticks": sum(int(item.get("ticks", 0)) for item in rows),
                "downstream_populations_started": False,
            }
            result["artifact_sha256"] = durable_json(EVIDENCE / "AS007_SCIENTIFIC_SEQUENCE_RESULT.json", result)
            return result
    result = {
        "schema": "AS007_SCIENTIFIC_SEQUENCE_V1",
        "directive": "UMBRA-AS-007",
        "terminal_stage": "DIAGNOSTICS_AB_R1_PASS",
        "rows": rows,
        "verdict": "AS007_DIAGNOSTICS_AB_R1_PASS",
        "retries": 0,
        "reseeds": 0,
        "organism_runs": len(rows),
        "organism_ticks": sum(int(item.get("ticks", 0)) for item in rows),
        "downstream_populations_started": False,
    }
    result["artifact_sha256"] = durable_json(EVIDENCE / "AS007_SCIENTIFIC_SEQUENCE_RESULT.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("scientific",), default="scientific")
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_scientific(args.work), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
