"""Strictly ordered AS-004 integrated viability runner.

The runner reuses the established CLOSE-02R/D-014 fixture and changes only
the explicitly authorized AS-004 continuation flag plus durable trace paths.
It never supplies a candidate, effect, or outcome to the organism.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import time
import uuid
from typing import Any

import experiments.close02r.qualification as base_runner


DIRECTIVE = "UMBRA-AS-004"
BASELINE = "6da7326af2ff502bbf6bb712a08ae263b1505d54"
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-004-bounded-continuation-integrated-viability-r1")
DIAGNOSTICS = (
    ("DIAGNOSTIC_A", "R0", 45878900, 500),
    ("DIAGNOSTIC_B", "R0", 22023239, 3500),
    ("KNOWN_R1", "R1", 57531938, 7200),
)


def durable_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        offset = 0
        while offset < len(payload):
            count = os.write(fd, payload[offset:])
            if count <= 0:
                raise OSError("short write")
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace_summary(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "decisions": 0,
        "continuation_decisions": 0,
        "o0_empty": 0,
        "o0_sizes": Counter(),
        "unknown_classifications": 0,
        "eliminations": 0,
        "continuation_statuses": Counter(),
        "stochastic_decisions": 0,
        "first_elimination": None,
    }
    if not path.exists():
        summary["o0_sizes"] = {}
        summary["continuation_statuses"] = {}
        return summary
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            summary["decisions"] += 1
            distributed = row.get("distributed_competition") or {}
            continuation = distributed.get("continuation") or {}
            if not continuation:
                continue
            summary["continuation_decisions"] += 1
            size = int(continuation.get("root_size", 0))
            summary["o0_sizes"][str(size)] += 1
            if size == 0:
                summary["o0_empty"] += 1
            summary["eliminations"] += len(continuation.get("eliminated", ()))
            if summary["first_elimination"] is None and continuation.get("eliminated"):
                summary["first_elimination"] = {"tick": row.get("tick"), "eliminated": continuation["eliminated"]}
            for classification in continuation.get("classifications", ()):
                for _, status in classification.get("status_by_witness", ()):
                    summary["continuation_statuses"][status] += 1
                    if status == "UNKNOWN":
                        summary["unknown_classifications"] += 1
            if distributed.get("stochastic_term") is not None:
                summary["stochastic_decisions"] += 1
    summary["o0_sizes"] = dict(summary["o0_sizes"])
    summary["continuation_statuses"] = dict(summary["continuation_statuses"])
    return summary


def run_case(stage: str, regime: str, seed: int, horizon: int, work: Path) -> dict[str, Any]:
    db = work / f"{stage}-{regime}-{seed}.sqlite"
    trace = work / f"{stage}-{regime}-{seed}.trace.jsonl"
    original_config = base_runner.config

    def as004_config(case_seed: int, case_db: Path, case_regime: str):
        config = original_config(case_seed, case_db, case_regime)
        config.bounded_continuation_enabled = True
        config.decision_trace_path = str(trace)
        return config

    base_runner.config = as004_config
    started = time.monotonic()
    try:
        result = base_runner.run_case(regime, seed, work, horizon)
    finally:
        base_runner.config = original_config
    result.update(
        directive=DIRECTIVE,
        stage=stage,
        trace_sha256=sha256(trace) if trace.exists() else None,
        continuation=trace_summary(trace),
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
        elapsed_seconds=round(time.monotonic() - started, 3),
    )
    trace.unlink(missing_ok=True)
    return result


def execute_diagnostics(work: Path, output: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for stage, regime, seed, horizon in DIAGNOSTICS:
        row = run_case(stage, regime, seed, horizon, work)
        rows.append(row)
        if row.get("terminal") != "completed":
            result = {
                "directive": DIRECTIVE,
                "baseline": BASELINE,
                "phase": "historical_blocker",
                "terminal_stage": stage,
                "rows": rows,
                "verdict": f"AS004_{stage}_FAIL" if stage != "KNOWN_R1" else "AS004_KNOWN_R1_FAIL",
                "retries": 0,
                "reseeds": 0,
            }
            durable_json(output, result)
            return result
    result = {
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "phase": "historical_blocker",
        "terminal_stage": "KNOWN_R1",
        "rows": rows,
        "verdict": "AS004_HISTORICAL_BLOCKERS_PASS",
        "retries": 0,
        "reseeds": 0,
    }
    durable_json(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("diagnostics",), required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    execute_diagnostics(args.work, args.output)


if __name__ == "__main__":
    main()
