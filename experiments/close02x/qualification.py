#!/usr/bin/env python3
"""Strictly ordered CLOSE-02X qualification runner.

The runner reuses the current-stack organism lifecycle. SQLite/WAL and raw
decision traces stay on local/direct-attached scratch. Only closed summaries
are eligible for Atlas finalization.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import resource
import sys
import time
import uuid
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import experiments.close02r.qualification as base_runner

DIRECTIVE = "UMBRA-CLOSE-02X"
HERE = Path(__file__).resolve().parent
EVIDENCE = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-close-02x-prospective-recoverability-r1"
)


def durable_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
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


def _json(name: str) -> dict[str, Any]:
    return json.loads((HERE / name).read_text())


def _trace_metrics(path: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "candidate_views": 0,
        "unknown_views": 0,
        "positive_to_exhausted": 0,
        "constrained_by_dimension": Counter(),
        "first_prospective_transition": None,
    }
    if not path.exists():
        return {**metrics, "trace_bytes": 0}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            for event in row.get("prospective_recoverability", []):
                metrics["candidate_views"] += 1
                for transition in event.get("transitions", []):
                    if "UNKNOWN" in str(transition.get("current_status")) or "UNKNOWN" in str(
                        transition.get("projected_status")
                    ):
                        metrics["unknown_views"] += 1
                    if transition.get("constrained"):
                        metrics["positive_to_exhausted"] += 1
                        metrics["constrained_by_dimension"][str(transition["dimension"])] += 1
                        if metrics["first_prospective_transition"] is None:
                            metrics["first_prospective_transition"] = {
                                "tick": row.get("tick"),
                                "candidate": event.get("candidate"),
                                "transition": transition,
                            }
    metrics["constrained_by_dimension"] = dict(metrics["constrained_by_dimension"])
    metrics["trace_bytes"] = path.stat().st_size
    return metrics


def run_case(regime: str, seed: int, work: Path, horizon: int, stage: str) -> dict[str, Any]:
    trace = work / f"{stage}-{regime}-{seed}.trace.jsonl"
    original_config = base_runner.config

    def traced_config(case_seed: int, db: Path, case_regime: str):
        cfg = original_config(case_seed, db, case_regime)
        cfg.decision_trace_path = str(trace)
        return cfg

    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    base_runner.config = traced_config
    try:
        row = base_runner.run_case(regime, seed, work, horizon)
    finally:
        base_runner.config = original_config
    row.update(
        directive=DIRECTIVE,
        stage=stage,
        prospective=_trace_metrics(trace),
        peak_rss_mib=max(
            rss_before, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        ),
    )
    trace.unlink(missing_ok=True)
    return row


def _failure(stage: dict[str, Any], rows: list[dict[str, Any]], output: Path) -> dict[str, Any]:
    result = {
        "directive": DIRECTIVE,
        "status": "TERMINAL",
        "terminal_stage": stage["stage"],
        "formal_started": stage["stage"].startswith("FORMAL_"),
        "rows": rows,
        "verdict": stage["failure_verdict"],
    }
    durable_json(output, result)
    return result


def _agency_gate(rows: list[dict[str, Any]]) -> tuple[bool, dict[str, Any]]:
    thresholds = _json("CLOSE02X_THRESHOLDS.json")
    development = [row for row in rows if row["stage"].endswith("DEVELOPMENT")]
    max_fraction = 0.0
    for row in development:
        total = max(1, sum(row["actions"].values()))
        max_fraction = max(max_fraction, max(row["actions"].values(), default=0) / total)
    activation = sum(row["prospective"]["positive_to_exhausted"] for row in development)
    dimensions = sorted({
        dimension
        for row in development
        for dimension in row["prospective"]["constrained_by_dimension"]
    })
    maximum_trace = max((row["prospective"]["trace_bytes"] for row in development), default=0)
    maximum_rss = max((row["peak_rss_mib"] for row in development), default=0.0)
    passed = bool(
        development
        and activation > 0
        and max_fraction <= thresholds["maximum_single_action_fraction"]
        and maximum_trace <= thresholds["maximum_trace_bytes_per_run"]
        and maximum_rss <= thresholds["maximum_peak_rss_mib"]
    )
    return passed, {
        "stage": "AGENCY_BOUNDEDNESS",
        "terminal": "completed" if passed else "scientific_failure",
        "fresh_population_positive_to_exhausted": activation,
        "realized_dimensions": dimensions,
        "maximum_single_action_fraction": max_fraction,
        "maximum_trace_bytes": maximum_trace,
        "maximum_peak_rss_mib": maximum_rss,
    }


def execute(work: Path, output: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    manifest = _json("CLOSE02X_STAGE_MANIFEST.json")
    development = _json("CLOSE02X_DEVELOPMENT_SEEDS.json")["seeds"]
    formal = _json("CLOSE02X_FORMAL_SEEDS.json")["seeds"]
    rows: list[dict[str, Any]] = []
    for stage in manifest["stages"]:
        name = stage["stage"]
        if name == "AGENCY_BOUNDEDNESS":
            passed, row = _agency_gate(rows)
            rows.append(row)
            if not passed:
                return _failure(stage, rows, output)
            continue
        if name == "REGRESSIONS":
            result = {
                "directive": DIRECTIVE,
                "status": "QUALIFICATION_POPULATION_PASS_REGRESSIONS_PENDING",
                "terminal_stage": name,
                "formal_started": True,
                "rows": rows,
                "verdict": "CLOSE02X_REGRESSIONS_PENDING",
            }
            durable_json(output, result)
            return result
        seeds = stage.get("seeds")
        if seeds is None:
            source, regime = str(stage["seed_source"]).split(".")
            seeds = (development if source == "development" else formal)[regime]
        for seed in seeds:
            row = run_case(stage["regime"], int(seed), work, int(stage["horizon"]), name)
            rows.append(row)
            durable_json(EVIDENCE / f"{name}-{seed}.json", row)
            if row["terminal"] != "completed":
                return _failure(stage, rows, output)
    raise AssertionError("stage graph did not terminate")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.work, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
