#!/usr/bin/env python3
"""Behavior-neutral CLOSE-02X attribution trace collector.

The production decision trace is default-disabled and observational. This
wrapper first compares a bounded trace-off/trace-on fixture, then may execute
the one authorized frozen-X R1/S16 reproduction while retaining its trace.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import experiments.close02r.qualification as base_runner
from umbra_core.decision_trace import canonical_fingerprint

DIRECTIVE = "UMBRA-CLOSE-02X-ATTRIB"
BASELINE = "af78ddfe97132970bbb3b6d17488bcd2e85db2e9"
FROZEN_X = "0c55fc21e6066facd242da07658fef38fe0ad031"
TARGET_SEED = 57531938
TARGET_HORIZON = 1000
PARITY_SEED = 271828
PARITY_HORIZON = 16


def _stable_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "elapsed_seconds"}


def _run_with_optional_trace(
    *, regime: str, seed: int, work: Path, horizon: int, trace: Path | None
) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    original_config = base_runner.config

    if trace is not None:
        def traced_config(case_seed: int, db: Path, case_regime: str):
            cfg = original_config(case_seed, db, case_regime)
            cfg.decision_trace_path = str(trace)
            return cfg

        base_runner.config = traced_config
    try:
        return base_runner.run_case(regime, seed, work, horizon)
    finally:
        base_runner.config = original_config


def parity(work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    trace = work / "parity-enabled.trace.jsonl"

    def fixture(name: str, trace_path: Path | None) -> dict[str, Any]:
        case_dir = work / name
        case_dir.mkdir(parents=True, exist_ok=True)
        db = case_dir / "fixture.sqlite"
        original_config = base_runner.config

        def fixture_config(case_seed: int, case_db: Path, case_regime: str):
            cfg = original_config(case_seed, case_db, case_regime)
            cfg.decision_trace_path = str(trace_path) if trace_path else None
            return cfg

        base_runner.config = fixture_config
        organism = None
        identifiers = (uuid.UUID(int=value) for value in range(1, 10000))
        try:
            with patch("umbra_core.util.uuid.uuid4", side_effect=lambda: next(identifiers)):
                organism, _ = base_runner.prepare(PARITY_SEED, db, "R0")
                outputs = []
                for _ in range(PARITY_HORIZON):
                    result = organism.tick_once()
                    outputs.append({
                        key: result.get(key)
                        for key in (
                            "tick", "capability", "denied", "H", "outcome",
                            "action_issued", "no_safe_action", "external_displacement",
                        )
                    })
                return {
                    "outputs": outputs,
                    "physiology": organism.phys.as_dict(),
                    "rng_fp": canonical_fingerprint(organism.rng.export_state()),
                    "authority_fp": canonical_fingerprint(organism.authoritative_state()),
                    "arbitration_fp": canonical_fingerprint(organism.arbitrator.state.to_state()),
                }
        finally:
            base_runner.config = original_config
            if organism is not None:
                organism.close()
            for suffix in ("", "-wal", "-shm"):
                Path(str(db) + suffix).unlink(missing_ok=True)

    disabled = fixture("off", None)
    enabled = fixture("on", trace)
    rows = [line for line in trace.read_text().splitlines() if line.strip()]
    equal = disabled == enabled
    passed = equal and len(rows) == PARITY_HORIZON
    return {
        "directive": DIRECTIVE,
        "phase": "TRACE_PARITY",
        "baseline": BASELINE,
        "frozen_x": FROZEN_X,
        "seed": PARITY_SEED,
        "horizon": PARITY_HORIZON,
        "trace_default_disabled": True,
        "observable_output_equal": disabled["outputs"] == enabled["outputs"],
        "physiology_equal": disabled["physiology"] == enabled["physiology"],
        "rng_equal": disabled["rng_fp"] == enabled["rng_fp"],
        "authority_equal": disabled["authority_fp"] == enabled["authority_fp"],
        "arbitration_equal": disabled["arbitration_fp"] == enabled["arbitration_fp"],
        "trace_rows": len(rows),
        "result": "PASS" if passed else "FAIL",
    }


def diagnostic(work: Path, trace: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    row = _run_with_optional_trace(
        regime="R1", seed=TARGET_SEED, work=work,
        horizon=TARGET_HORIZON, trace=trace,
    )
    return {
        "directive": DIRECTIVE,
        "phase": "ONE_AUTHORIZED_DIAGNOSTIC_REPRODUCTION",
        "baseline": BASELINE,
        "frozen_x": FROZEN_X,
        "regime": "R1",
        "scenario": "S16",
        "seed": TARGET_SEED,
        "ceiling": TARGET_HORIZON,
        "qualification_evidence": False,
        "row": row,
        "trace_path": str(trace),
        "trace_rows": sum(1 for line in trace.read_text().splitlines() if line.strip()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("parity", "diagnostic"), required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--trace", type=Path)
    args = parser.parse_args()
    if args.phase == "parity":
        result = parity(args.work)
    else:
        if args.trace is None:
            raise SystemExit("--trace is required for diagnostic")
        result = diagnostic(args.work, args.trace)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
