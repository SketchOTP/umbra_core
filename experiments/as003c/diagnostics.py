#!/usr/bin/env python3
"""AS-003C single-stage diagnostic runner with retained frontier traces.

This module composes the existing CLOSE-02R R0/S0 lifecycle unchanged.  It
only enables the default-disabled, observational decision trace and summarizes
the distributed-competition fields already emitted by runtime.  It must be
called only after the AS-003C freeze.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import experiments.close02r.qualification as base_runner


DIRECTIVE = "UMBRA-AS-003C"
STAGES: dict[str, dict[str, Any]] = {
    "DIAGNOSTIC_A": {
        "regime": "R0",
        "scenario": "S0",
        "seed": 45878900,
        "horizon": 500,
        "failure_verdict": "AS003C_FLAT_AUTHORITY_COMPATIBILITY_FAIL",
    },
    "DIAGNOSTIC_B": {
        "regime": "R0",
        "scenario": "S0",
        "seed": 22023239,
        "horizon": 3500,
        "failure_verdict": "AS003C_HIERARCHICAL_AUTHORITY_COMPATIBILITY_FAIL",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trace_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid_trace_jsonl_line:{number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"invalid_trace_row:{number}")
            rows.append(row)
    return rows


def frontier_metrics(trace_path: Path) -> dict[str, Any]:
    """Summarize only read-only runtime trace fields needed by AS-003C."""

    rows = _trace_rows(trace_path)
    qualifying: list[tuple[dict[str, Any], dict[str, Any]]] = []
    channels_by_elimination: Counter[str] = Counter()
    support_by_channel: Counter[str] = Counter()
    unknown_by_channel: Counter[str] = Counter()
    for row in rows:
        competition = row.get("distributed_competition")
        if not isinstance(competition, dict):
            continue
        candidate_count = int(competition.get("admissible_candidate_count", 0))
        if candidate_count < 2:
            continue
        qualifying.append((row, competition))
        for key, value in (competition.get("supported_count_by_channel") or {}).items():
            support_by_channel[str(key)] += int(value)
        for key, value in (competition.get("unknown_count_by_channel") or {}).items():
            unknown_by_channel[str(key)] += int(value)
        for attempt in competition.get("attempts") or []:
            if isinstance(attempt, dict) and attempt.get("passed"):
                for key in attempt.get("strict_channels") or []:
                    channels_by_elimination[str(key)] += 1

    dominance_count = sum(
        int(competition.get("pairwise_dominance_count", 0))
        for _, competition in qualifying
    )
    eliminated_count = sum(
        int(competition.get("eliminated_candidate_count", 0))
        for _, competition in qualifying
    )
    full_frontier_count = sum(
        bool(competition.get("frontier_equals_full_pool"))
        for _, competition in qualifying
    )
    stochastic_count = sum(
        bool(competition.get("stochastic_resolution_required"))
        for _, competition in qualifying
    )
    distributed_changed_count = sum(
        bool(competition.get("distributed_changed_winner"))
        for _, competition in qualifying
    )
    unknown_functional_count = sum(
        bool(competition.get("unknown_count_by_channel"))
        and row.get("final_candidate") is not None
        for row, competition in qualifying
    )
    return {
        "trace_rows": len(rows),
        "trace_sha256": sha256(trace_path),
        "qualifying_ordinary_multi_candidate_decisions": len(qualifying),
        "pairwise_dominance_count": dominance_count,
        "eliminated_candidate_count": eliminated_count,
        "frontier_full_pool_occurrences": full_frontier_count,
        "stochastic_resolution_occurrences": stochastic_count,
        "distributed_changed_winner_occurrences": distributed_changed_count,
        "unknown_functional_selection_occurrences": unknown_functional_count,
        "support_count_by_channel": dict(sorted(support_by_channel.items())),
        "unknown_count_by_channel": dict(sorted(unknown_by_channel.items())),
        "strict_elimination_channels": dict(sorted(channels_by_elimination.items())),
        "dominance_realized": dominance_count > 0 and eliminated_count > 0,
        "evidence_causality_realized": distributed_changed_count > 0,
        "unknown_functional_realized": unknown_functional_count > 0,
        "complete_frontier_saturation": bool(qualifying) and full_frontier_count == len(qualifying),
    }


def run_stage(stage_name: str, work: Path, evidence: Path) -> dict[str, Any]:
    if stage_name not in STAGES:
        raise ValueError(f"unknown_stage:{stage_name}")
    stage = STAGES[stage_name]
    work.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    trace = evidence / f"{stage_name}.decision-trace.jsonl"
    if trace.exists():
        raise FileExistsError(trace)

    original_config = base_runner.config

    def traced_config(seed: int, db: Path, regime: str):
        cfg = original_config(seed, db, regime)
        cfg.decision_trace_path = str(trace)
        return cfg

    base_runner.config = traced_config
    try:
        row = base_runner.run_case(
            str(stage["regime"]), int(stage["seed"]), work, int(stage["horizon"])
        )
    finally:
        base_runner.config = original_config
    if not trace.exists():
        raise RuntimeError("decision_trace_missing")
    metrics = frontier_metrics(trace)
    passed = bool(
        row.get("terminal") == "completed"
        and int(row.get("ticks", -1)) == int(stage["horizon"])
        and row.get("critical_failure") is None
        and row.get("first_no_safe_action") is None
    )
    return {
        "directive": DIRECTIVE,
        "stage": stage_name,
        "regime": stage["regime"],
        "scenario": stage["scenario"],
        "seed": stage["seed"],
        "horizon": stage["horizon"],
        "trace_path": str(trace),
        "run": row,
        "frontier_metrics": metrics,
        "result": "PASS" if passed else "FAIL",
        "failure_verdict": None if passed else stage["failure_verdict"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_stage(args.stage, args.work, args.evidence), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
