#!/usr/bin/env python3
"""Bounded V5 capture-on/off comparison for AS-017 pre-lock evidence.

This is development evidence only.  It runs one fresh R1/S16 seed twice, with
isolated databases, and observes existing Governance calls without invoking
preflight a second time or changing their return values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.as014 import qualification as as014
from experiments.as016.full_config import config, fingerprint
from umbra_core.governance import Governance
from umbra_core.runtime import Organism


DIRECTIVE = "UMBRA-AS-017"
CANDIDATE = "fe783295a0de175b88000a9ffadfd1b7ff4afa38"
REGIME = "R1"
HORIZON = 1200
SEED = 61001742


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _semantic_outcome(outcome: Any) -> dict[str, Any] | None:
    if outcome is None:
        return None
    raw = getattr(outcome, "raw", {}) or {}
    applied = raw.get("applied_parameters", raw.get("params"))
    return {
        "capability": str(getattr(outcome, "capability", "")),
        "success": bool(getattr(outcome, "success", False)),
        "reason": str(getattr(outcome, "reason", "")),
        "verified": bool(getattr(outcome, "verified", False)),
        "requested_params": dict(raw.get("requested_parameters", {}) or {}),
        "applied_params": dict(applied or {}) if isinstance(applied, dict) else None,
        "effects": dict(getattr(outcome, "physiology_effects", {}) or {}),
    }


def _run(mode: str, root: Path) -> dict[str, Any]:
    work = root / mode
    work.mkdir(parents=True, exist_ok=False)
    db = work / "organism.sqlite"
    trace = work / "decision-trace.jsonl"
    calls: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    rng_final: dict[str, Any] = {}

    original_config = as014.config
    original_fingerprint = as014.fingerprint
    original_propose = Governance.propose
    original_execute = Governance.execute_and_verify
    original_close = Organism.close

    def probe_config(case_seed: int, case_db: Path, regime: str):
        value = config(case_seed, case_db, regime)
        if mode == "capture_on":
            value.decision_trace_path = str(trace)
        return value

    def propose(self: Governance, capability: str, params: dict[str, Any], requested_effects=None):
        calls.append({"capability": capability, "params": dict(params), "requested_effects": list(requested_effects or [])})
        return original_propose(self, capability, params, requested_effects)

    def execute(self: Governance, proposal, decision, embodiment, rng, **kwargs):
        result = original_execute(self, proposal, decision, embodiment, rng, **kwargs)
        outcomes.append({
            "capability": str(proposal.capability),
            "params": dict(proposal.params),
            "admitted": bool(decision.admitted),
            "outcome": _semantic_outcome(result),
        })
        return result

    def close(self: Organism):
        rng_final.update(self.rng.export_state())
        return original_close(self)

    as014.config = probe_config
    as014.fingerprint = fingerprint
    Governance.propose = propose
    Governance.execute_and_verify = execute
    Organism.close = close
    try:
        row = as014.run_case(REGIME, SEED, work, horizon=HORIZON)
    finally:
        as014.config = original_config
        as014.fingerprint = original_fingerprint
        Governance.propose = original_propose
        Governance.execute_and_verify = original_execute
        Organism.close = original_close

    row.update({
        "mode": mode,
        "proposal_count": len(calls),
        "proposal_sequence": calls,
        "outcome_sequence": outcomes,
        "rng_final": rng_final,
        "trace_present": trace.is_file(),
        "trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest() if trace.is_file() else None,
        "config_fingerprint": fingerprint(probe_config(SEED, db, REGIME)),
    })
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.root.exists() or args.result.exists():
        raise RuntimeError("AS017_OBSERVER_PROBE_CREATE_ONCE_PATH_EXISTS")
    args.root.mkdir(parents=True)
    on = _run("capture_on", args.root)
    off = _run("capture_off", args.root)

    comparable = ["ticks", "terminal", "actions", "first_no_safe_action", "min_energy", "max_fatigue", "min_integrity", "min_stimulation", "proposal_sequence", "outcome_sequence", "rng_final"]
    diffs = {
        key: {"capture_on": on.get(key), "capture_off": off.get(key)}
        for key in comparable
        if on.get(key) != off.get(key)
    }
    result = {
        "schema": "AS017_OBSERVER_NEUTRALITY_PROBE_V1",
        "directive": DIRECTIVE,
        "candidate_commit": CANDIDATE,
        "classification": "bounded_nonformal_development_evidence",
        "seed": SEED,
        "regime": REGIME,
        "horizon": HORIZON,
        "capture_on": on,
        "capture_off": off,
        "comparison_fields": comparable,
        "semantic_differences": sorted(diffs),
        "semantic_difference_details": diffs,
        "result": "PASS" if not diffs and on["trace_present"] and not off["trace_present"] else "FAIL",
        "formal_seed_consumption": 0,
        "retries": 0,
        "reseeds": 0,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    with args.result.open("xb") as handle:
        handle.write(payload)
        handle.flush()
    print(json.dumps({"result": result["result"], "sha256": _digest(result), "path": str(args.result)}, sort_keys=True))


if __name__ == "__main__":
    main()
