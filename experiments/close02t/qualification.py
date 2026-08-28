#!/usr/bin/env python3
"""CLOSE-02T gated qualification runner.

The organism lifecycle is delegated to the existing production-native
qualification runner. This wrapper supplies the CLOSE-02T seed manifests,
directive identity, staged first-failure stop, and durable result output.
SQLite/WAL scratch remains local/direct-attached; only finalized summaries are
written to the canonical Atlas evidence root.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.close02r.qualification import run_case as _run_case

DIRECTIVE = "UMBRA-CLOSE-02T"
EVIDENCE = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-close-02t-interruptible-intent-r1"
)


def durable_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        os.write(fd, payload)
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


def run_case(regime: str, seed: int, work: Path, horizon: int, stage: str) -> dict[str, Any]:
    row = _run_case(regime, seed, work, horizon)
    row["directive"] = DIRECTIVE
    row["stage"] = stage
    return row


def load_seeds() -> tuple[dict[str, Any], dict[str, Any]]:
    development = json.loads((EVIDENCE / "CLOSE02T_DEVELOPMENT_SEEDS.json").read_text())
    formal = json.loads((EVIDENCE / "CLOSE02T_FORMAL_SEEDS.json").read_text())
    return development["seeds"], formal["seeds"]


def run_once(regime: str, seed: int, horizon: int, stage: str, work: Path, output: Path) -> dict[str, Any]:
    started = time.monotonic()
    row = run_case(regime, seed, work, horizon, stage)
    result = {
        "directive": DIRECTIVE,
        "stage": stage,
        "run_count": 1,
        "started_at_monotonic": started,
        "row": row,
        "verdict": "PASS" if row["terminal"] == "completed" else "SCIENTIFIC_FAILURE",
    }
    durable_json(output, result)
    return result


def execute(work: Path, output: Path) -> dict[str, Any]:
    development, formal = load_seeds()
    rows: list[dict[str, Any]] = []

    diagnostics = [
        ("KNOWN_DIAGNOSTIC", "R0", 45878900, 500),
        ("LATE_FATIGUE_DIAGNOSTIC", "R0", 22023239, 3500),
    ]
    for stage, regime, seed, horizon in diagnostics:
        result = run_once(regime, seed, horizon, stage, work, output.with_name(f"{stage}.json"))
        rows.append(result["row"])
        if result["verdict"] != "PASS":
            closeout = {
                "directive": DIRECTIVE,
                "phase": "diagnostic",
                "terminal_stage": stage,
                "rows": rows,
                "formal_started": False,
                "verdict": "CLOSE02T_KNOWN_DIAGNOSTIC_FAIL",
            }
            durable_json(output, closeout)
            return closeout

    stages = [
        ("R0_DEVELOPMENT", "R0", development["R0"]),
        ("KNOWN_R1", "R1", development["known_R1"]),
        ("R1_DEVELOPMENT", "R1", development["R1"]),
        ("R2_DEVELOPMENT", "R2", development["R2"]),
        ("R3_DEVELOPMENT", "R3", development["R3"]),
    ]
    for stage, regime, population in stages:
        for seed in population:
            result = run_once(regime, seed, 7200, stage, work, output.with_name(f"{stage}-{seed}.json"))
            rows.append(result["row"])
            if result["verdict"] != "PASS":
                closeout = {
                    "directive": DIRECTIVE,
                    "phase": "development",
                    "terminal_stage": stage,
                    "rows": rows,
                    "formal_started": False,
                    "verdict": f"CLOSE02T_{stage}_FAIL",
                }
                durable_json(output, closeout)
                return closeout

    for regime in ("R0", "R1", "R2", "R3"):
        for seed in formal[regime]:
            result = run_once(regime, seed, 7200, f"FORMAL_{regime}", work, output.with_name(f"FORMAL-{regime}-{seed}.json"))
            rows.append(result["row"])
            if result["verdict"] != "PASS":
                closeout = {
                    "directive": DIRECTIVE,
                    "phase": "formal",
                    "terminal_stage": f"FORMAL_{regime}",
                    "rows": rows,
                    "formal_started": True,
                    "verdict": "CLOSE02T_FORMAL_INTEGRATED_VIABILITY_FAIL",
                }
                durable_json(output, closeout)
                return closeout

    closeout = {
        "directive": DIRECTIVE,
        "phase": "formal",
        "terminal_stage": "complete",
        "rows": rows,
        "formal_started": True,
        "verdict": "CLOSE02T_FINAL_AUTHORITY_INTEGRATED_VIABILITY_QUALIFIED",
    }
    durable_json(output, closeout)
    return closeout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.work, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
