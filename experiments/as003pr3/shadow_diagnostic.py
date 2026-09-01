#!/usr/bin/env python3
"""One-shot AS-003P-R3 raw-preserving control/shadow observer pair.

Scientific fixture, seed, horizon, tick loop, shadow enablement, decision-trace
capture, and planning-frame capture match the frozen AS-003P harness. The R3
protocol additionally preserves raw comparison inputs and applies the
prospectively locked semantic comparator.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

from experiments.as003p import shadow_diagnostic as frozen
from experiments.as003pr3.semantic_comparator import compare_run_records


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r3-semantic-shadow-pair-r1"
)
COMMAND = "/usr/bin/python3 -m experiments.as003pr3.shadow_diagnostic"
WORKING_DIRECTORY = "/home/sketch/Projects/UMBRA-CORE"
SEED = frozen.SEED
HORIZON = frozen.HORIZON


def _raw_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(frozen._safe(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def run_one_raw(*, shadow: bool, work: Path) -> tuple[dict[str, Any], bytes, bytes | None]:
    """Frozen leg logic with raw post-run state/event preservation."""
    work.mkdir(parents=True, exist_ok=False)
    label = "SHADOW" if shadow else "CONTROL"
    decision_trace = work / f"{label}.decision-trace.jsonl"
    planning_trace = work / f"{label}.planning-shadow.jsonl"
    original_config = frozen.fixture.config

    def config(seed: int, db: Path, regime: str):
        cfg = original_config(seed, db, regime)
        cfg.decision_trace_path = str(decision_trace)
        cfg.planning_shadow_path = str(planning_trace) if shadow else None
        return cfg

    frozen.fixture.config = config
    db = work / f"{label}.sqlite"
    organism = None
    timeline: list[dict[str, Any]] = []
    try:
        organism, _ = frozen.fixture.prepare(SEED, db, "R0")
        for _ in range(HORIZON):
            result = organism.tick_once()
            timeline.append(
                {
                    "tick": organism.tick,
                    "capability": result.get("capability"),
                    "denied": result.get("denied"),
                    "action_issued": result.get("action_issued"),
                    "no_safe_action": result.get("no_safe_action", False),
                    "physiology": organism.phys.as_dict(),
                    "outcome": result.get("outcome"),
                }
            )
        raw_events = frozen._safe(list(organism.store.iter_events()))
        raw_final_state = frozen._safe(organism.authoritative_state())
        rng_state = frozen._safe(organism.rng.export_state())
        record = {
            "schema": "AS003PR3_NONFORMAL_RAW_EXECUTION_RECORD_V1",
            "identity": label,
            "regime": "R0",
            "scenario": "S0",
            "seed": SEED,
            "horizon": HORIZON,
            "shadow_enabled": shadow,
            "timeline": frozen._safe(timeline),
            "authoritative_events": raw_events,
            "final_authoritative_state": raw_final_state,
            "raw_final_authoritative_state_sha256": _raw_digest(raw_final_state),
            "raw_authoritative_events_sha256": _raw_digest(raw_events),
            "rng_state": rng_state,
            "rng_state_sha256": _raw_digest(rng_state),
            "subsystem_exact_sha256": {
                key: _raw_digest(raw_final_state.get(key))
                for key in sorted(raw_final_state)
            },
            "retries": 0,
            "reseeds": 0,
            "formal": False,
        }
    finally:
        frozen.fixture.config = original_config
        if organism is not None:
            organism.close()
    decision_bytes = decision_trace.read_bytes()
    planning_bytes = planning_trace.read_bytes() if shadow else None
    rows = frozen._trace_rows(decision_trace)
    record["decision_trace_rows"] = len(rows)
    record["decision_trace_sha256"] = hashlib.sha256(decision_bytes).hexdigest()
    record["candidate_identities_by_tick"] = frozen._safe(
        [
            {
                "tick": row.get("tick"),
                "pool": sorted(
                    view.get("identity")
                    for view in (row.get("distributed_competition") or {}).get("views", [])
                    if view.get("identity")
                ),
                "selected": (row.get("distributed_competition") or {}).get("selected_identity"),
                "governance": row.get("governance_decision"),
                "verified_outcome": row.get("verified_outcome_linkage"),
            }
            for row in rows
        ]
    )
    return record, decision_bytes, planning_bytes


def main() -> None:
    frozen.ROOT = ROOT
    required = [
        "AS003PR3_PAIRED_EXECUTION_STARTED.json",
        "AS003PR3_PAIRED_EXECUTION_FINISHED.json",
        "AS003PR3_CONTROL_RUN_RAW.json",
        "AS003PR3_SHADOW_RUN_RAW.json",
        "AS003PR3_CONTROL_DECISION_TRACE.jsonl",
        "AS003PR3_SHADOW_DECISION_TRACE.jsonl",
        "AS003PR3_PLANNING_SHADOW_TRACE.jsonl",
        "AS003PR3_SEMANTIC_OBSERVER_PARITY.json",
    ]
    existing = [name for name in required if (ROOT / name).exists()]
    if existing:
        raise FileExistsError(f"AS003P-R3 one-shot pair already executed: {existing}")
    started_at = time.time()
    git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    start_record = {
        "schema": "AS003PR3_PAIRED_EXECUTION_STARTED_V1",
        "directive": "UMBRA-AS-003P-R3",
        "command": COMMAND,
        "working_directory": str(Path.cwd()),
        "git_commit": git_commit,
        "fixture": {"regime": "R0", "scenario": "S0", "seed": SEED, "horizon": HORIZON},
        "scientific_fixture": "experiments.close02r.qualification",
        "control_authorized": 1,
        "shadow_authorized": 1,
        "retries_authorized": 0,
        "reseeds_authorized": 0,
        "formal": False,
        "started_unix": started_at,
    }
    digests = {
        "AS003PR3_PAIRED_EXECUTION_STARTED.json": frozen._publish(
            "AS003PR3_PAIRED_EXECUTION_STARTED.json", frozen._json_bytes(start_record)
        )
    }
    work = Path(tempfile.mkdtemp(prefix="umbra-as003pr3-pair-"))
    try:
        control, control_trace, _ = run_one_raw(shadow=False, work=work / "control")
        digests["AS003PR3_CONTROL_RUN_RAW.json"] = frozen._publish(
            "AS003PR3_CONTROL_RUN_RAW.json", frozen._json_bytes(control)
        )
        digests["AS003PR3_CONTROL_DECISION_TRACE.jsonl"] = frozen._publish(
            "AS003PR3_CONTROL_DECISION_TRACE.jsonl", control_trace
        )

        shadow, shadow_trace, planning_trace = run_one_raw(shadow=True, work=work / "shadow")
        assert planning_trace is not None
        digests["AS003PR3_SHADOW_RUN_RAW.json"] = frozen._publish(
            "AS003PR3_SHADOW_RUN_RAW.json", frozen._json_bytes(shadow)
        )
        digests["AS003PR3_SHADOW_DECISION_TRACE.jsonl"] = frozen._publish(
            "AS003PR3_SHADOW_DECISION_TRACE.jsonl", shadow_trace
        )
        digests["AS003PR3_PLANNING_SHADOW_TRACE.jsonl"] = frozen._publish(
            "AS003PR3_PLANNING_SHADOW_TRACE.jsonl", planning_trace
        )

        parity = compare_run_records(control, shadow)
        parity.update(
            {
                "directive": "UMBRA-AS-003P-R3",
                "fixture": {"regime": "R0", "scenario": "S0", "seed": SEED, "horizon": HORIZON},
                "comparator_lock": "experiments/as003pr3/COMPARATOR_LOCK.json",
                "comparator_source_sha256": "596ab86f41523ea16dde44693b5aa7a702f0514fc38c18717aa0070c1590da66",
                "coverage": frozen.shadow_coverage(planning_trace),
                "control_executions": 1,
                "shadow_executions": 1,
                "retries": 0,
                "reseeds": 0,
                "formal": False,
                "verdict_if_false": "AS003PR3_TRUE_OBSERVER_EFFECT_FAIL",
            }
        )
        digests["AS003PR3_SEMANTIC_OBSERVER_PARITY.json"] = frozen._publish(
            "AS003PR3_SEMANTIC_OBSERVER_PARITY.json", frozen._json_bytes(parity)
        )
        finished = {
            "schema": "AS003PR3_PAIRED_EXECUTION_FINISHED_V1",
            "directive": "UMBRA-AS-003P-R3",
            "git_commit": git_commit,
            "started_unix": started_at,
            "finished_unix": time.time(),
            "control_executions": 1,
            "shadow_executions": 1,
            "retries": 0,
            "reseeds": 0,
            "semantic_observer_parity": parity["semantic_equal"],
            "semantic_difference_count": parity["semantic_difference_count"],
            "artifact_sha256": dict(sorted(digests.items())),
        }
        digests["AS003PR3_PAIRED_EXECUTION_FINISHED.json"] = frozen._publish(
            "AS003PR3_PAIRED_EXECUTION_FINISHED.json", frozen._json_bytes(finished)
        )
        print(json.dumps({"parity": parity, "digests": digests}, sort_keys=True))
        if not parity["semantic_equal"]:
            raise SystemExit(2)
    except BaseException as exc:
        if not (ROOT / "AS003PR3_EXECUTION_EXCEPTION.json").exists():
            frozen._publish(
                "AS003PR3_EXECUTION_EXCEPTION.json",
                frozen._json_bytes(
                    {
                        "schema": "AS003PR3_EXECUTION_EXCEPTION_V1",
                        "directive": "UMBRA-AS-003P-R3",
                        "git_commit": git_commit,
                        "started_unix": started_at,
                        "failed_unix": time.time(),
                        "exception_type": type(exc).__name__,
                        "exception": str(exc),
                        "no_retry_authorized": True,
                    }
                ),
            )
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
