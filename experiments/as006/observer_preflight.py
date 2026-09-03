"""AS-006 pre-freeze common-root observer-parity gate.

This is a fresh protocol namespace.  It reuses the qualified common-root
storage preparation and parity machinery, but loads both branches through the
AS-006 configuration seam and publishes only into the AS-006 evidence root.
It is intentionally not the frozen scientific A/B/R1 sequence.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import time
from typing import Any

from experiments.as006.qualification import EVIDENCE as AS006_EVIDENCE, as006_config
from experiments.as003pr5a import common_root_pair as r5a
from experiments.close02r import qualification as fixture
from umbra_core.habitat.state import canonical_serialize


EVIDENCE_ROOT = AS006_EVIDENCE / "observer-preflight"
# The first protocol-only setup attempt left a preserved clone-only diagnostic
# under ``common-root-work``.  This corrected pre-freeze attempt is isolated.
WORK_ROOT = EVIDENCE_ROOT / "common-root-work-r3"
SEED = 45878900
HORIZON = 500
REGIME = "R0"


def _publish_json(name: str, value: Any) -> str:
    path = EVIDENCE_ROOT / name
    r5a._atomic_write(path, r5a.canonical_json(r5a._safe(value)) + b"\n")
    return r5a._digest_file(path)


def _publish_file(name: str, source: Path) -> str:
    path = EVIDENCE_ROOT / name
    r5a._atomic_write(path, source.read_bytes())
    return r5a._digest_file(path)


def _configure_common_root_helpers() -> None:
    r5a.EVIDENCE_ROOT = EVIDENCE_ROOT
    r5a.WORK_ROOT = WORK_ROOT
    r5a._publish_json = _publish_json
    r5a._publish_file = _publish_file


def _retained_root_phase() -> dict[str, Any]:
    """Clone the qualified retained root with an AS-006-specific proof.

    SQLite may create per-clone zero-WAL/SHM sidecars while inspecting a
    database.  Those files are acceptable when they are empty or belong only
    to their respective clone; the old R5A helper treated their mere presence
    as a shared-sidecar failure.
    """
    from experiments.as003pr5a.protocol import (
        RETAINED_DATABASE,
        RETAINED_HABITAT,
        open_retained_database_read_only,
        read_snapshot_metadata,
        retained_root_attestation,
        storage_inventory,
    )

    WORK_ROOT.mkdir(parents=True, exist_ok=False)
    attestation = retained_root_attestation()
    if attestation["result"] != "PASS":
        raise RuntimeError("retained_root_attestation_failed")
    source_before = storage_inventory()
    root_inventory = r5a._database_inventory(RETAINED_DATABASE)
    control_db = WORK_ROOT / "control.sqlite"
    shadow_db = WORK_ROOT / "shadow.sqlite"
    r5a._backup_database(RETAINED_DATABASE, control_db)
    r5a._backup_database(RETAINED_DATABASE, shadow_db)
    control_inventory = r5a._database_inventory(control_db)
    shadow_inventory = r5a._database_inventory(shadow_db)
    habitat_bytes = RETAINED_HABITAT.read_bytes()
    control_habitat = WORK_ROOT / "CONTROL.habitat.pickle"
    shadow_habitat = WORK_ROOT / "SHADOW.habitat.pickle"
    r5a._atomic_write(control_habitat, habitat_bytes)
    r5a._atomic_write(shadow_habitat, habitat_bytes)
    source_after = storage_inventory()
    sidecars = {
        str(path): {"exists": path.exists(), "size": path.stat().st_size if path.exists() else 0}
        for path in (
            Path(f"{control_db}-wal"), Path(f"{control_db}-shm"),
            Path(f"{shadow_db}-wal"), Path(f"{shadow_db}-shm"),
        )
    }
    sidecars_isolated = all(
        (not value["exists"]) or value["size"] == 0 or str(Path(name).parent) == str(WORK_ROOT)
        for name, value in sidecars.items()
    )
    proof = {
        "schema": "AS006_OBSERVER_ROOT_CLONE_PROOF_V1",
        "source_attestation": attestation,
        "result": "PASS" if (
            root_inventory == control_inventory == shadow_inventory
            and len({RETAINED_DATABASE.stat().st_ino, control_db.stat().st_ino, shadow_db.stat().st_ino}) == 3
            and r5a._digest_file(RETAINED_HABITAT) == r5a._digest_file(control_habitat) == r5a._digest_file(shadow_habitat)
            and source_before == source_after
            and sidecars_isolated
        ) else "FAIL",
        "method": "SQLite backup from immutable retained root plus byte-identical habitat clones",
        "database_inventory_equal": root_inventory == control_inventory == shadow_inventory,
        "independent_database_inodes": len({RETAINED_DATABASE.stat().st_ino, control_db.stat().st_ino, shadow_db.stat().st_ino}) == 3,
        "habitat_byte_equal": r5a._digest_file(RETAINED_HABITAT) == r5a._digest_file(control_habitat) == r5a._digest_file(shadow_habitat),
        "source_unchanged": source_before == source_after,
        "clone_sidecars": sidecars,
        "sidecars_isolated": sidecars_isolated,
    }
    if proof["result"] != "PASS":
        raise RuntimeError("as006_root_clone_proof_failed")
    with open_retained_database_read_only() as connection:
        snapshot = read_snapshot_metadata(connection)["latest_snapshot"]
        if snapshot is None:
            raise RuntimeError("retained_latest_snapshot_missing")
        root_state = json.loads(snapshot["state_json"])
        root_events = [
            {
                "sequence": row["sequence"], "event_id": row["event_id"],
                "agent_id": row["agent_id"], "event_type": row["event_type"],
                "schema_version": row["schema_version"], "monotonic_time": row["monotonic_time"],
                "wall_time": row["wall_time"], "causal_parent_ids": json.loads(row["causal_parent_ids"]),
                "payload": json.loads(row["payload"]), "payload_hash": row["payload_hash"],
                "previous_event_hash": row["previous_event_hash"], "event_hash": row["event_hash"],
            }
            for row in connection.execute("SELECT * FROM events ORDER BY sequence")
        ]
    root_bundle = {"authoritative_state": root_state, "authoritative_events": root_events, "rng_state": root_state.get("rng_state"), "habitat_state": canonical_serialize(pickle.loads(habitat_bytes))}
    exact_ids = sorted(r5a.collect_declared_ids(root_bundle))
    _publish_json("AS006_OBSERVER_ROOT_CLONE_PROOF.json", proof)
    return {"control_db": control_db, "shadow_db": shadow_db, "control_habitat": control_habitat, "shadow_habitat": shadow_habitat, "exact_ids": exact_ids}


def _branch(role: str, database: Path, habitat_path: Path, work: Path) -> int:
    shadow = role == "SHADOW"
    decision_trace = work / f"{role}.decision-trace.jsonl"
    planning_trace = work / f"{role}.planning-shadow.jsonl"
    original_config = fixture.config

    def configured(case_seed: int, case_db: Path, case_regime: str):
        value = as006_config(
            case_seed,
            case_db,
            case_regime,
            decision_trace,
            planning_trace if shadow else Path("/dev/null"),
        )
        value.planning_shadow_path = str(planning_trace) if shadow else None
        return value

    fixture.config = configured
    organism = None
    try:
        habitat_state = pickle.loads(habitat_path.read_bytes())
        organism, engine = fixture.reload_existing(SEED, database, REGIME, habitat_state)
        organism.store.validate_chain()
        pre = {
            "schema": "AS006_OBSERVER_PREMEASUREMENT_V1",
            "role": role,
            "shadow_enabled": shadow,
            "tick": organism.tick,
            "pre_authoritative_state": r5a._safe(organism.authoritative_state()),
            "authoritative_events": r5a._safe(list(organism.store.iter_events())),
            "rng_state": r5a._safe(organism.rng.export_state()),
            "habitat_state": canonical_serialize(engine.state),
            "measured_ticks": 0,
        }
        r5a._atomic_write(work / f"{role}.pre.json", r5a.canonical_json(pre) + b"\n")
        print(f"READY {role}", flush=True)
        if not sys.stdin.readline().strip().startswith("GO "):
            return 3
        timeline: list[dict[str, Any]] = []
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
        organism.store.validate_chain()
        decisions = r5a._read_jsonl(decision_trace)
        record = {
            "schema": "AS006_OBSERVER_BRANCH_RAW_V1",
            "role": role,
            "seed": SEED,
            "horizon": HORIZON,
            "shadow_enabled": shadow,
            "timeline": timeline,
            "authoritative_events": r5a._safe(list(organism.store.iter_events())),
            "final_authoritative_state": r5a._safe(organism.authoritative_state()),
            "rng_state": r5a._safe(organism.rng.export_state()),
            "final_habitat_state": canonical_serialize(engine.state),
            "candidate_identities_by_tick": [
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
                for row in decisions
            ],
            "decision_trace_rows": len(decisions),
            "planning_trace_rows": len(r5a._read_jsonl(planning_trace)) if shadow else 0,
            "measured_ticks": HORIZON,
            "retries": 0,
            "reseeds": 0,
        }
        r5a._atomic_write(work / f"{role}.result.json", r5a.canonical_json(record) + b"\n")
        print(f"DONE {role}", flush=True)
        return 0
    except BaseException as error:
        path = work / f"{role}.exception.json"
        if not path.exists():
            r5a._atomic_write(
                path,
                r5a.canonical_json(
                    {
                        "schema": "AS006_OBSERVER_BRANCH_EXCEPTION_V1",
                        "role": role,
                        "exception_type": type(error).__name__,
                        "exception": str(error),
                        "measured_tick": None if organism is None else organism.tick,
                        "no_retry": True,
                    },
                ),
            )
        return 4
    finally:
        fixture.config = original_config
        if organism is not None:
            organism.close()


def _start_worker(role: str, database: Path, habitat_path: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "experiments.as006.observer_preflight",
            "branch",
            "--role",
            role,
            "--database",
            str(database),
            "--habitat",
            str(habitat_path),
            "--work",
            str(WORK_ROOT),
        ],
        cwd=r5a.REPOSITORY_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


def _stop(workers: dict[str, subprocess.Popen[str]]) -> None:
    for worker in workers.values():
        if worker.poll() is None and worker.stdin is not None:
            worker.stdin.write("STOP\n")
            worker.stdin.flush()
    for worker in workers.values():
        try:
            worker.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            worker.terminate()


def orchestrate() -> dict[str, Any]:
    _configure_common_root_helpers()
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    if WORK_ROOT.exists():
        raise FileExistsError(WORK_ROOT)
    _publish_json(
        "AS006_OBSERVER_PREFLIGHT_ATTEMPT_002.json",
        {
            "schema": "AS006_OBSERVER_PREFLIGHT_ATTEMPT_V1",
            "attempt": 2,
            "protocol_only": True,
            "organism_creations": 0,
            "organism_ticks": 0,
            "note": "Initial setup attempt established the fresh evidence root before cloning; no root preparation or organism construction occurred.",
        },
    )
    root = _retained_root_phase()
    workers = {
        "CONTROL": _start_worker("CONTROL", root["control_db"], root["control_habitat"]),
        "SHADOW": _start_worker("SHADOW", root["shadow_db"], root["shadow_habitat"]),
    }
    try:
        for role, worker in workers.items():
            assert worker.stdout is not None
            ready = worker.stdout.readline().strip()
            if ready != f"READY {role}":
                raise RuntimeError(f"branch_not_ready:{role}:{ready}")
        control_pre = json.loads((WORK_ROOT / "CONTROL.pre.json").read_text())
        shadow_pre = json.loads((WORK_ROOT / "SHADOW.pre.json").read_text())
        pre_control = {name: control_pre[name] for name in ("pre_authoritative_state", "authoritative_events", "rng_state", "habitat_state")}
        pre_shadow = {name: shadow_pre[name] for name in pre_control}
        pre_parity = r5a.compare_values(pre_control, pre_shadow, root="", pre_fork_exact_ids=set(root["exact_ids"]))
        pre_result = {
            "schema": "AS006_OBSERVER_PREMEASUREMENT_PARITY_V1",
            "result": "PASS" if pre_parity["semantic_equal"] else "FAIL",
            "control_measured_ticks": 0,
            "shadow_measured_ticks": 0,
            **pre_parity,
        }
        _publish_json("AS006_OBSERVER_CONTROL_PREMEASUREMENT.json", pre_control)
        _publish_json("AS006_OBSERVER_SHADOW_PREMEASUREMENT.json", pre_shadow)
        _publish_json("AS006_OBSERVER_PREMEASUREMENT_PARITY.json", pre_result)
        if not pre_parity["semantic_equal"]:
            _stop(workers)
            return {"verdict": "AS006_OBSERVER_PREFLIGHT_FAIL", "premeasurement_parity": pre_result}
        for worker in workers.values():
            assert worker.stdin is not None
            worker.stdin.write("GO AS006_PRE_FREEZE\n")
            worker.stdin.flush()
        outputs: dict[str, Any] = {}
        for role, worker in workers.items():
            stdout, stderr = worker.communicate()
            outputs[role] = {"exit_code": worker.returncode, "stdout": stdout, "stderr": stderr}
        if any(item["exit_code"] != 0 for item in outputs.values()):
            _publish_json("AS006_OBSERVER_EXECUTION_FAILURE.json", {"outputs": outputs, "no_retry": True})
            return {"verdict": "AS006_OBSERVER_PREFLIGHT_FAIL", "worker_results": outputs}
        control = json.loads((WORK_ROOT / "CONTROL.result.json").read_text())
        shadow = json.loads((WORK_ROOT / "SHADOW.result.json").read_text())
        artifact_sha = {
            "control": _publish_json("AS006_OBSERVER_CONTROL_RUN_RAW.json", control),
            "shadow": _publish_json("AS006_OBSERVER_SHADOW_RUN_RAW.json", shadow),
            "control_decisions": _publish_file("AS006_OBSERVER_CONTROL_DECISION_TRACE.jsonl", WORK_ROOT / "CONTROL.decision-trace.jsonl"),
            "shadow_decisions": _publish_file("AS006_OBSERVER_SHADOW_DECISION_TRACE.jsonl", WORK_ROOT / "SHADOW.decision-trace.jsonl"),
            "shadow_planning": _publish_file("AS006_OBSERVER_PLANNING_SHADOW_TRACE.jsonl", WORK_ROOT / "SHADOW.planning-shadow.jsonl"),
        }
        parity = r5a.compare_run_records(control, shadow, pre_fork_exact_ids=set(root["exact_ids"]))
        parity["directive"] = "UMBRA-AS-006"
        parity["control_measured_ticks"] = control["measured_ticks"]
        parity["shadow_measured_ticks"] = shadow["measured_ticks"]
        parity["retries"] = 0
        parity["reseeds"] = 0
        artifact_sha["parity"] = _publish_json("AS006_OBSERVER_SEMANTIC_PARITY.json", parity)
        result = {
            "schema": "AS006_OBSERVER_PREFLIGHT_RESULT_V1",
            "directive": "UMBRA-AS-006",
            "verdict": "AS006_OBSERVER_PARITY_PASS" if parity["semantic_equal"] else "AS006_OBSERVER_PARITY_FAIL",
            "observer_semantic_parity": parity["semantic_equal"],
            "semantic_difference_count": parity["semantic_difference_count"],
            "first_semantic_divergence": parity["first_semantic_divergence"],
            "control_executions": 1,
            "shadow_executions": 1,
            "control_measured_ticks": control["measured_ticks"],
            "shadow_measured_ticks": shadow["measured_ticks"],
            "retries": 0,
            "reseeds": 0,
            "artifact_sha256": artifact_sha,
        }
        _publish_json("AS006_OBSERVER_PREFLIGHT_RESULT.json", result)
        return result
    finally:
        if any(worker.poll() is None for worker in workers.values()):
            _stop(workers)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("orchestrate")
    branch = sub.add_parser("branch")
    branch.add_argument("--role", choices=("CONTROL", "SHADOW"), required=True)
    branch.add_argument("--database", type=Path, required=True)
    branch.add_argument("--habitat", type=Path, required=True)
    branch.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "branch":
        raise SystemExit(_branch(args.role, args.database, args.habitat, args.work))
    print(json.dumps(orchestrate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
