#!/usr/bin/env python3
"""Bounded CLOSE-02Z stochastic-composition compatibility diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.close02r.qualification import durable_json, run_case


DIRECTIVE = "UMBRA-CLOSE-02Z"
STAGES = (
    {
        "stage": "DIAGNOSTIC_A",
        "regime": "R0",
        "seed": 45878900,
        "horizon": 500,
        "failure_verdict": "CLOSE02Z_FLAT_AUTHORITY_COMPATIBILITY_FAIL",
    },
    {
        "stage": "DIAGNOSTIC_B",
        "regime": "R0",
        "seed": 22023239,
        "horizon": 3500,
        "failure_verdict": "CLOSE02Z_HIERARCHICAL_AUTHORITY_COMPATIBILITY_FAIL",
    },
)


def execute(work: Path, evidence: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for stage in STAGES:
        row = run_case(
            str(stage["regime"]),
            int(stage["seed"]),
            work,
            int(stage["horizon"]),
        )
        row.update(directive=DIRECTIVE, stage=stage["stage"])
        durable_json(evidence / f"CLOSE02Z_{stage['stage']}.json", row)
        rows.append(row)
        if row["terminal"] != "completed":
            result = {
                "directive": DIRECTIVE,
                "status": "TERMINAL",
                "verdict": stage["failure_verdict"],
                "rows": rows,
                "known_r1_run": False,
                "viability_qualification": False,
            }
            durable_json(evidence / "CLOSE02Z_COMPATIBILITY_RESULT.json", result)
            return result
    result = {
        "directive": DIRECTIVE,
        "status": "COMPATIBILITY_PASS",
        "verdict": "CLOSE02Z_COMPATIBILITY_DIAGNOSTICS_PASS",
        "rows": rows,
        "known_r1_run": False,
        "viability_qualification": False,
    }
    durable_json(evidence / "CLOSE02Z_COMPATIBILITY_RESULT.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.work, args.evidence), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
