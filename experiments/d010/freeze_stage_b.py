#!/usr/bin/env python3
"""Stage B preregistration freeze for UMBRA-D-010 (Task 12).

Writes frozen thresholds/matrix/scenario-suite/seed manifests/test-manifest,
stage-a-hashes, performance-protocol, and formal-execution-contract.json.
Does not embed freeze_commit (recorded at formal execution start in Task 13).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d010 import stage_a as sa

DIRECTIVE = "UMBRA-D-010"
AGENT_MEMORY = "D-20260724-1605-d010-freeze-invalidate-v4"
FORMAL_EXECUTION_ID = "d010-fe-stage-b-v4"

ALLOWED_VERDICTS = [
    "UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED",
    "UMBRA_D010_PARTIAL_FOUNDATION",
    "UMBRA_D010_TEMPORAL_AUTHORITY_FAIL",
    "UMBRA_D010_RECURRENCE_LEARNING_FAIL",
    "UMBRA_D010_FUTURE_LEAKAGE_FAIL",
    "UMBRA_D010_ANTICIPATION_FAIL",
    "UMBRA_D010_REVISION_FAIL",
    "UMBRA_D010_TEMPORAL_ROUTINE_FAIL",
    "UMBRA_D010_AUTONOMY_FAIL",
    "UMBRA_D010_ABSENCE_SAFETY_FAIL",
    "UMBRA_D010_DOWNTIME_CONTINUITY_FAIL",
    "UMBRA_D010_REPLAY_FAIL",
    "UMBRA_D010_BOUNDEDNESS_FAIL",
    "UMBRA_D010_REGRESSION_FAIL",
    "UMBRA_D010_PERFORMANCE_FAIL",
]

FREEZE_JSON_ARTIFACTS = (
    "thresholds.json",
    "experiment-matrix.json",
    "scenario-suite.json",
    "performance-protocol.json",
    "runtime-tick-classification.json",
    "development-seed-manifest.json",
    "formal-seed-manifest.json",
    "test-manifest.json",
    "stage-a-hashes.json",
)

IMPLEMENTATION_SOURCE_PATHS = (
    "umbra_core/temporal/clock.py",
    "umbra_core/temporal/config.py",
    "umbra_core/temporal/downtime.py",
    "umbra_core/temporal/engine.py",
    "umbra_core/temporal/events.py",
    "umbra_core/temporal/migration.py",
    "umbra_core/temporal/recurrence.py",
    "umbra_core/temporal/state.py",
    "umbra_core/runtime.py",
    "experiments/d010/conditions.py",
    "experiments/d010/control_rows.py",
    "experiments/d010/diagnostic_controllers.py",
    "experiments/d010/evidence.py",
    "experiments/d010/governance_bypass.py",
    "experiments/d010/hostile_temporal_view.py",
    "experiments/d010/replay_shuffle.py",
    "experiments/d010/run_experiment.py",
    "experiments/d010/run_performance.py",
    "experiments/d010/run_seal.py",
    "experiments/d010/scenario_plants.py",
    "experiments/d010/scan_runtime_tick_uses.py",
    "experiments/d010/stage_a.py",
    "experiments/d010/validate_evidence.py",
    "tests/test_d010.py",
)

RUNNER_PATHS = (
    "experiments/d010/run_experiment.py",
    "experiments/d010/run_performance.py",
    "experiments/d010/run_seal.py",
    "experiments/d010/validate_evidence.py",
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_paths(relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for rel in sorted(relative_paths):
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"freeze_fail:missing_source:{rel}")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


def _write_json(name: str, payload: dict[str, Any]) -> None:
    (EXP / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _freeze_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _artifact_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in FREEZE_JSON_ARTIFACTS:
        path = EXP / name
        if path.is_file():
            out[f"experiments/d010/{name}"] = file_sha256(path)
    out["experiments/d010/temporal-event-schemas.json"] = file_sha256(
        EXP / "temporal-event-schemas.json"
    )
    out["experiments/d010/failure-code-registry.json"] = file_sha256(
        EXP / "failure-code-registry.json"
    )
    return out


def _hash_manifest_payload(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "manifest_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def _freeze_manifest(name: str) -> str:
    payload = _load_json(name)
    payload["frozen_before_execution"] = True
    payload.pop("manifest_hash", None)
    payload["manifest_hash"] = _hash_manifest_payload(payload)
    _write_json(name, payload)
    return str(payload["manifest_hash"])


def freeze_stage_b() -> dict[str, Any]:
    errors = sa.validate_test_manifest_complete()
    if errors:
        raise SystemExit(f"freeze_fail:test_manifest:{errors[0]}")
    sa.validate_seed_nonoverlap()

    freeze_ts = _freeze_timestamp()

    thr = _load_json("thresholds.json")
    thr.pop("draft", None)
    thr["frozen_before_execution"] = True
    thr["threshold_freeze_timestamp"] = freeze_ts
    thr["allowed_verdicts"] = ALLOWED_VERDICTS
    thr["formal_seed_nonoverlap_rule"] = thr.get("formal_seed_nonoverlap_rule") or {
        "development_ranges": [[1, 10000]],
        "formal_ranges": [[50001, 60000]],
        "forbidden_intersection": True,
        "development_rows_excluded_from_formal_summaries": True,
    }
    _write_json("thresholds.json", thr)

    matrix = _load_json("experiment-matrix.json")
    matrix["frozen_before_execution"] = True
    matrix["threshold_freeze_timestamp"] = freeze_ts
    _write_json("experiment-matrix.json", matrix)

    scen = _load_json("scenario-suite.json")
    scen["frozen_before_execution"] = True
    _write_json("scenario-suite.json", scen)

    proto = _load_json("performance-protocol.json")
    proto["frozen_before_execution"] = True
    proto["threshold_freeze_timestamp"] = freeze_ts
    _write_json("performance-protocol.json", proto)

    runtime_cls = _load_json("runtime-tick-classification.json")
    runtime_cls["frozen_before_execution"] = True
    _write_json("runtime-tick-classification.json", runtime_cls)

    dev_hash = _freeze_manifest("development-seed-manifest.json")
    seed_manifest_hash = _freeze_manifest("formal-seed-manifest.json")
    test_manifest_hash = _freeze_manifest("test-manifest.json")

    stage_payload = sa.write_stage_a_hashes()
    stage_payload["frozen_before_execution"] = True
    _write_json("stage-a-hashes.json", stage_payload)

    implementation_source_hash = hash_paths(IMPLEMENTATION_SOURCE_PATHS)
    runner_hash = hash_paths(RUNNER_PATHS)
    event_registry_hash = file_sha256(EXP / "temporal-event-schemas.json")
    failure_registry_hash = file_sha256(EXP / "failure-code-registry.json")

    artifact_hashes = _artifact_hashes()
    freeze_bundle_hash = hashlib.sha256(
        json.dumps(artifact_hashes, sort_keys=True).encode("utf-8")
    ).hexdigest()

    contract = {
        "schema_version": "d010.formal-execution-contract.v1",
        "directive": DIRECTIVE,
        "agent_memory_directive": AGENT_MEMORY,
        "formal_execution_id": FORMAL_EXECUTION_ID,
        "frozen_before_execution": True,
        "threshold_freeze_timestamp": freeze_ts,
        "freeze_bundle_hash": freeze_bundle_hash,
        "implementation_source_hash": implementation_source_hash,
        "runner_hash": runner_hash,
        "test_manifest_hash": test_manifest_hash,
        "seed_manifest_hash": seed_manifest_hash,
        "development_seed_manifest_hash": dev_hash,
        "event_registry_hash": event_registry_hash,
        "failure_code_registry_hash": failure_registry_hash,
        "stage_a_bundle_hash": stage_payload["bundle_hash"],
        "allowed_verdicts": ALLOWED_VERDICTS,
        "formal_seed_nonoverlap_rule": thr["formal_seed_nonoverlap_rule"],
        "artifact_hashes": artifact_hashes,
        "notes": "freeze_commit is recorded in docs/evidence/d010/formal-execution-manifest.json at Task 13 run start",
    }
    _write_json("formal-execution-contract.json", contract)

    sa.assert_no_placeholder_hashes(sa.compute_stage_a_hashes())
    return contract


def main() -> None:
    contract = freeze_stage_b()
    print(json.dumps({"frozen": True, "formal_execution_id": contract["formal_execution_id"]}, indent=2))


if __name__ == "__main__":
    main()
