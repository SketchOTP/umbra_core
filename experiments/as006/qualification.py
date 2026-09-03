"""AS-006 fresh integrated source-activation and scientific runner.

This namespace does not read AS-005 traces. It uses the established CLOSE-02R
runner with a fresh evidence root and the AS-006 configuration seam.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import experiments.close02r.qualification as base_runner
from experiments.d014.run_formal import config as d014_config
from umbra_core.world_model import condition_to_world_model_config


EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-006-executable-weak-continuation-integrated-viability-r1")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as006_config(seed: int, db: Path, regime: str, decision: Path, shadow: Path):
    config = d014_config(seed, db, regime)
    config.bounded_continuation_enabled = True
    config.world_model_enabled = True
    world_config = config.world_model_config or condition_to_world_model_config("C0")
    world_config.route_demand_learning_enabled = True
    config.world_model_config = world_config
    config.decision_trace_path = str(decision)
    config.planning_shadow_path = str(shadow)
    return config


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def summarize(decision: Path, shadow: Path) -> dict[str, Any]:
    rows, shadow_rows = _rows(decision), _rows(shadow)
    continuations = [((row.get("distributed_competition") or {}).get("continuation") or {}) for row in rows]
    classifications = [item for row in continuations for item in row.get("classifications") or ()]
    statuses = [status for item in classifications for _, status in item.get("status_by_witness") or ()]
    return {
        "decision_rows": len(rows),
        "shadow_rows": len(shadow_rows),
        "nonempty_option_rows": sum(1 for row in continuations if row.get("modal_options") or int(row.get("root_size", 0)) > 0),
        "modal_option_count": sum(len(row.get("modal_options") or ()) for row in continuations),
        "route_experience_frames": sum(1 for row in shadow_rows if (row.get("frame") or {}).get("route_experience_support")),
        "modal_profiles": sum(len(row.get("candidate_profiles") or ()) for row in shadow_rows),
        "continuation_status_counts": {name: statuses.count(name) for name in ("PRESERVED", "DESTROYED", "UNKNOWN")},
        "modal_classification_counts": {
            name: sum(1 for row in shadow_rows for profile in row.get("candidate_profiles") or () if ((profile.get("profile") or {}).get("classification") == name))
            for name in ("STRONG_MUST_CONTINUATION", "STRONG_MAY_CONTINUATION", "WEAK_MAY_CONTINUATION", "NO_CONTINUATION", "UNKNOWN")
        },
        "decision_sha256": sha(decision) if decision.exists() else None,
        "shadow_sha256": sha(shadow) if shadow.exists() else None,
    }


def _durable_json(path: Path, value: Any) -> None:
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


def run_source_activation(*, seed: int = 45878900, regime: str = "R0", horizon: int = 500, work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    decision = EVIDENCE / f"AS006_SOURCE_ACTIVATION_{regime}_{seed}.decision.jsonl"
    shadow = EVIDENCE / f"AS006_SOURCE_ACTIVATION_{regime}_{seed}.planning.jsonl"
    db = work / f"AS006_SOURCE_ACTIVATION_{regime}_{seed}.sqlite"
    original = base_runner.config

    def configured(case_seed: int, case_db: Path, case_regime: str):
        return as006_config(case_seed, case_db, case_regime, decision, shadow)

    base_runner.config = configured
    started = time.monotonic()
    try:
        row = base_runner.run_case(regime, seed, work, horizon)
    finally:
        base_runner.config = original
    row.update({"directive": "UMBRA-AS-006", "stage": "DEVELOPMENT_SOURCE_ACTIVATION", "elapsed_seconds": round(time.monotonic() - started, 3), "trace_summary": summarize(decision, shadow)})
    _durable_json(EVIDENCE / "AS006_DEVELOPMENT_SOURCE_ACTIVATION.json", row)
    return row


def run_scientific(*, work: Path) -> dict[str, Any]:
    """Run the frozen A/B/R1 sequence once, stopping at the first terminal gate."""
    stages = (("DIAGNOSTIC_A", "R0", 45878900, 500), ("DIAGNOSTIC_B", "R0", 22023239, 3500), ("KNOWN_R1", "R1", 57531938, 7200))
    rows: list[dict[str, Any]] = []
    for stage, regime, seed, horizon in stages:
        decision = EVIDENCE / f"AS006_{stage}_{seed}.decision.jsonl"
        shadow = EVIDENCE / f"AS006_{stage}_{seed}.planning.jsonl"
        db = work / f"AS006_{stage}_{seed}.sqlite"
        original = base_runner.config

        def configured(case_seed: int, case_db: Path, case_regime: str):
            return as006_config(case_seed, case_db, case_regime, decision, shadow)

        base_runner.config = configured
        started = time.monotonic()
        try:
            row = base_runner.run_case(regime, seed, work, horizon)
        finally:
            base_runner.config = original
        row.update({"directive": "UMBRA-AS-006", "stage": stage, "decision_trace": str(decision), "planning_trace": str(shadow), "trace_summary": summarize(decision, shadow), "elapsed_seconds": round(time.monotonic() - started, 3)})
        rows.append(row)
        if row.get("terminal") != "completed":
            verdict = {"DIAGNOSTIC_A": "AS006_FRESH_R0_FAIL", "DIAGNOSTIC_B": "AS006_FRESH_R0_FAIL", "KNOWN_R1": "AS006_KNOWN_R1_FAIL"}[stage]
            result = {"schema": "AS006_SCIENTIFIC_SEQUENCE_V1", "directive": "UMBRA-AS-006", "terminal_stage": stage, "rows": rows, "verdict": verdict, "retries": 0, "reseeds": 0, "organism_runs": len(rows), "organism_ticks": sum(int(item.get("ticks", 0)) for item in rows)}
            _durable_json(EVIDENCE / "AS006_SCIENTIFIC_SEQUENCE_RESULT.json", result)
            return result
    result = {"schema": "AS006_SCIENTIFIC_SEQUENCE_V1", "directive": "UMBRA-AS-006", "terminal_stage": "DIAGNOSTICS_AB_R1_PASS", "rows": rows, "verdict": "AS006_DIAGNOSTICS_AB_R1_PASS", "retries": 0, "reseeds": 0, "organism_runs": len(rows), "organism_ticks": sum(int(item.get("ticks", 0)) for item in rows)}
    _durable_json(EVIDENCE / "AS006_SCIENTIFIC_SEQUENCE_RESULT.json", result)
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("source-activation", "scientific"), default="source-activation")
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    result = run_scientific(work=args.work) if args.phase == "scientific" else run_source_activation(work=args.work)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
