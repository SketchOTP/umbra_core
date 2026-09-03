"""AS-005 bounded development/source-activation runner.

This harness is deliberately separate from AS-004. It uses the established
CLOSE-02R fixture and enables only the two AS-005 configuration seams: bounded
continuation and WorldModel verified route learning. It retains planner rows
and decision traces rather than deleting them. This is development evidence;
the formal AS-005 freeze command is not defined by this module.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import experiments.close02r.qualification as base_runner
from experiments.d014.run_formal import config as d014_config
from umbra_core.world_model import condition_to_world_model_config


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-005-preventive-modal-continuation-integrated-viability-r1")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as005_config(seed: int, db: Path, regime: str, decision: Path, shadow: Path):
    config = d014_config(seed, db, regime)
    config.bounded_continuation_enabled = True
    config.world_model_enabled = True
    world_config = config.world_model_config or condition_to_world_model_config("C0")
    world_config.route_demand_learning_enabled = True
    config.world_model_config = world_config
    config.decision_trace_path = str(decision)
    config.planning_shadow_path = str(shadow)
    return config


def summarize(decision: Path, shadow: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in decision.read_text(encoding="utf-8").splitlines() if line.strip()] if decision.exists() else []
    shadow_rows = [json.loads(line) for line in shadow.read_text(encoding="utf-8").splitlines() if line.strip()] if shadow.exists() else []
    continuations = [((row.get("distributed_competition") or {}).get("continuation") or {}) for row in rows]
    nonempty = [row for row in continuations if int(row.get("root_size", 0)) > 0 or row.get("modal_options")]
    modal_count = sum(len(row.get("modal_options") or ()) for row in continuations)
    return {
        "decision_rows": len(rows),
        "shadow_rows": len(shadow_rows),
        "continuation_rows": len(continuations),
        "nonempty_option_rows": len(nonempty),
        "modal_option_count": modal_count,
        "strict_o0_nonempty_rows": sum(1 for row in continuations if int(row.get("root_size", 0)) > 0),
        "route_experience_frames": sum(1 for row in shadow_rows if (row.get("frame") or {}).get("route_experience_support")),
        "modal_profiles": sum(len(row.get("candidate_profiles") or ()) for row in shadow_rows),
        "modal_classifications": {
            classification: sum(1 for row in shadow_rows for profile in row.get("candidate_profiles") or () if ((profile.get("profile") or {}).get("classification") == classification))
            for classification in ("STRONG_MUST_CONTINUATION", "STRONG_MAY_CONTINUATION", "WEAK_MAY_CONTINUATION", "NO_CONTINUATION", "UNKNOWN")
        },
        "decision_sha256": sha(decision) if decision.exists() else None,
        "shadow_sha256": sha(shadow) if shadow.exists() else None,
    }


def run_source_activation(*, seed: int = 45878900, regime: str = "R0", horizon: int = 500, work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    db = work / f"AS005_SOURCE_ACTIVATION_{regime}_{seed}.sqlite"
    decision = work / f"AS005_SOURCE_ACTIVATION_{regime}_{seed}.decision.jsonl"
    shadow = work / f"AS005_SOURCE_ACTIVATION_{regime}_{seed}.planning.jsonl"
    original = base_runner.config

    def configured(case_seed: int, case_db: Path, case_regime: str):
        return as005_config(case_seed, case_db, case_regime, decision, shadow)

    base_runner.config = configured
    started = time.monotonic()
    try:
        row = base_runner.run_case(regime, seed, work, horizon)
    finally:
        base_runner.config = original
    row.update({"directive": "UMBRA-AS-005", "stage": "DEVELOPMENT_SOURCE_ACTIVATION", "elapsed_seconds": round(time.monotonic() - started, 3), "trace_summary": summarize(decision, shadow)})
    return row


def _durable_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temp.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def run_scientific(*, work: Path) -> dict[str, Any]:
    """Run the exact post-freeze A/B/R1 sequence once, stopping terminally."""
    stages = (
        ("DIAGNOSTIC_A", "R0", 45878900, 500),
        ("DIAGNOSTIC_B", "R0", 22023239, 3500),
        ("KNOWN_R1", "R1", 57531938, 7200),
    )
    rows: list[dict[str, Any]] = []
    for stage, regime, seed, horizon in stages:
        decision = EVIDENCE / f"AS005_{stage}_{seed}.decision.jsonl"
        shadow = EVIDENCE / f"AS005_{stage}_{seed}.planning.jsonl"
        db = work / f"AS005_{stage}_{seed}.sqlite"
        original = base_runner.config

        def configured(case_seed: int, case_db: Path, case_regime: str):
            return as005_config(case_seed, case_db, case_regime, decision, shadow)

        base_runner.config = configured
        started = time.monotonic()
        try:
            row = base_runner.run_case(regime, seed, work, horizon)
        finally:
            base_runner.config = original
        row.update({"directive": "UMBRA-AS-005", "stage": stage, "decision_trace": str(decision), "planning_trace": str(shadow), "decision_sha256": sha(decision) if decision.exists() else None, "planning_sha256": sha(shadow) if shadow.exists() else None, "elapsed_seconds": round(time.monotonic() - started, 3)})
        summary = summarize(decision, shadow)
        row["as005_trace_summary"] = summary
        rows.append(row)
        if row.get("terminal") != "completed":
            result = {"schema": "AS005_SCIENTIFIC_SEQUENCE_V1", "directive": "UMBRA-AS-005", "terminal_stage": stage, "rows": rows, "verdict": "AS005_KNOWN_R1_FAIL" if stage == "KNOWN_R1" else f"AS005_{stage}_FAIL", "retries": 0, "reseeds": 0, "organism_runs": len(rows), "control_runs": 0, "shadow_runs": 0}
            _durable_json(EVIDENCE / "AS005_SCIENTIFIC_SEQUENCE_RESULT.json", result)
            return result
    result = {"schema": "AS005_SCIENTIFIC_SEQUENCE_V1", "directive": "UMBRA-AS-005", "terminal_stage": "SCIENTIFIC_SEQUENCE_PASS", "rows": rows, "verdict": "AS005_DIAGNOSTICS_AB_R1_PASS", "retries": 0, "reseeds": 0, "organism_runs": len(rows), "control_runs": 0, "shadow_runs": 0}
    _durable_json(EVIDENCE / "AS005_SCIENTIFIC_SEQUENCE_RESULT.json", result)
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=45878900)
    parser.add_argument("--regime", default="R0")
    parser.add_argument("--horizon", type=int, default=500)
    parser.add_argument("--phase", choices=("source-activation", "scientific"), default="source-activation")
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "scientific":
        print(json.dumps(run_scientific(work=args.work), indent=2, sort_keys=True))
    else:
        print(json.dumps(run_source_activation(seed=args.seed, regime=args.regime, horizon=args.horizon, work=args.work), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
