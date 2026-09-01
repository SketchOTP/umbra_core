#!/usr/bin/env python3
"""AS-003P-R1 protocol wrapper around the frozen AS-003P observer pair.

The scientific leg implementation, fixture, normalization, coverage logic,
seed, and horizon are imported unchanged from AS-003P. This module changes
only the fresh evidence destination, directive metadata, artifact namespace,
and repository-root module invocation recorded by the protocol.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from experiments.as003p import shadow_diagnostic as frozen


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r1-shadow-protocol-recovery"
)
COMMAND = "/usr/bin/python3 -m experiments.as003pr1.shadow_diagnostic"


def main() -> None:
    frozen.ROOT = ROOT
    required = [
        "AS003PR1_PAIRED_EXECUTION_STARTED.json",
        "AS003PR1_PAIRED_EXECUTION_FINISHED.json",
        "AS003PR1_CONTROL_RUN.json",
        "AS003PR1_SHADOW_RUN.json",
        "AS003PR1_CONTROL_DECISION_TRACE.jsonl",
        "AS003PR1_SHADOW_DECISION_TRACE.jsonl",
        "AS003PR1_PLANNING_SHADOW_TRACE.jsonl",
        "AS003PR1_OBSERVER_PARITY.json",
    ]
    existing = [name for name in required if (ROOT / name).exists()]
    if existing:
        raise FileExistsError(f"AS003P-R1 one-shot pair already executed: {existing}")
    started_at = time.time()
    git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    start_record = {
        "schema": "AS003PR1_PAIRED_EXECUTION_STARTED_V1",
        "directive": "UMBRA-AS-003P-R1",
        "command": COMMAND,
        "working_directory": str(Path.cwd()),
        "git_commit": git_commit,
        "fixture": {
            "regime": "R0",
            "scenario": "S0",
            "seed": frozen.SEED,
            "horizon": frozen.HORIZON,
        },
        "scientific_runner": "experiments.as003p.shadow_diagnostic.run_one",
        "control_authorized": 1,
        "shadow_authorized": 1,
        "retries_authorized": 0,
        "reseeds_authorized": 0,
        "formal": False,
        "started_unix": started_at,
    }
    digests = {
        "AS003PR1_PAIRED_EXECUTION_STARTED.json": frozen._publish(
            "AS003PR1_PAIRED_EXECUTION_STARTED.json", frozen._json_bytes(start_record)
        )
    }
    work = Path(tempfile.mkdtemp(prefix="umbra-as003pr1-pair-"))
    try:
        control, control_trace, _ = frozen.run_one(shadow=False, work=work / "control")
        digests["AS003PR1_CONTROL_RUN.json"] = frozen._publish(
            "AS003PR1_CONTROL_RUN.json", frozen._json_bytes(control)
        )
        digests["AS003PR1_CONTROL_DECISION_TRACE.jsonl"] = frozen._publish(
            "AS003PR1_CONTROL_DECISION_TRACE.jsonl", control_trace
        )

        shadow, shadow_trace, planning_trace = frozen.run_one(shadow=True, work=work / "shadow")
        assert planning_trace is not None
        digests["AS003PR1_SHADOW_RUN.json"] = frozen._publish(
            "AS003PR1_SHADOW_RUN.json", frozen._json_bytes(shadow)
        )
        digests["AS003PR1_SHADOW_DECISION_TRACE.jsonl"] = frozen._publish(
            "AS003PR1_SHADOW_DECISION_TRACE.jsonl", shadow_trace
        )
        digests["AS003PR1_PLANNING_SHADOW_TRACE.jsonl"] = frozen._publish(
            "AS003PR1_PLANNING_SHADOW_TRACE.jsonl", planning_trace
        )

        semantic_fields = [
            "timeline",
            "authoritative_events",
            "final_authoritative_state_hash",
            "rng_state_hash",
            "subsystem_hashes",
            "candidate_identities_by_tick",
        ]
        comparisons = {field: control[field] == shadow[field] for field in semantic_fields}
        parity = {
            "schema": "AS003PR1_OBSERVER_PARITY_V1",
            "directive": "UMBRA-AS-003P-R1",
            "fixture": {
                "regime": "R0",
                "scenario": "S0",
                "seed": frozen.SEED,
                "horizon": frozen.HORIZON,
            },
            "normalization": {
                "administrative_uuid_relations": "first-occurrence canonical tokens",
                "excluded_derivatives": sorted(frozen.DERIVATIVE_HASH_KEYS),
                "owner_state_fields_excluded": [],
            },
            "comparisons": comparisons,
            "exact_authoritative_parity": all(comparisons.values()),
            "control_final_state_hash": control["final_authoritative_state_hash"],
            "shadow_final_state_hash": shadow["final_authoritative_state_hash"],
            "control_rng_hash": control["rng_state_hash"],
            "shadow_rng_hash": shadow["rng_state_hash"],
            "coverage": frozen.shadow_coverage(planning_trace),
            "control_executions": 1,
            "shadow_executions": 1,
            "retries": 0,
            "reseeds": 0,
            "formal": False,
            "verdict_if_false": "AS003PR1_OBSERVER_EFFECT_FAIL",
        }
        digests["AS003PR1_OBSERVER_PARITY.json"] = frozen._publish(
            "AS003PR1_OBSERVER_PARITY.json", frozen._json_bytes(parity)
        )
        finished = {
            "schema": "AS003PR1_PAIRED_EXECUTION_FINISHED_V1",
            "directive": "UMBRA-AS-003P-R1",
            "git_commit": git_commit,
            "started_unix": started_at,
            "finished_unix": time.time(),
            "control_executions": 1,
            "shadow_executions": 1,
            "retries": 0,
            "reseeds": 0,
            "exact_authoritative_parity": parity["exact_authoritative_parity"],
            "artifact_sha256": dict(sorted(digests.items())),
        }
        digests["AS003PR1_PAIRED_EXECUTION_FINISHED.json"] = frozen._publish(
            "AS003PR1_PAIRED_EXECUTION_FINISHED.json", frozen._json_bytes(finished)
        )
        print(json.dumps({"parity": parity, "digests": digests}, sort_keys=True))
        if not parity["exact_authoritative_parity"]:
            raise SystemExit(2)
    except BaseException as exc:
        if not (ROOT / "AS003PR1_EXECUTION_EXCEPTION.json").exists():
            frozen._publish(
                "AS003PR1_EXECUTION_EXCEPTION.json",
                frozen._json_bytes(
                    {
                        "schema": "AS003PR1_EXECUTION_EXCEPTION_V1",
                        "directive": "UMBRA-AS-003P-R1",
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
