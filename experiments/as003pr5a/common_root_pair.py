#!/usr/bin/env python3
"""One-shot common-root CONTROL/SHADOW protocol for UMBRA-AS-003P-R5A.

The module is import-safe. ``orchestrate`` creates exactly one prepared root,
backs it up into two independent SQLite databases, starts two persistent branch
workers, and stops at a parent-controlled barrier before any measured tick.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any

from experiments.as003pr5a.analysis import analyze as analyze_modal
from experiments.as003pr5.semantic_comparator import (
    collect_declared_ids,
    compare_run_records,
    compare_values,
)
from experiments.as003pr5a.protocol import (
    RETAINED_DATABASE,
    RETAINED_HABITAT,
    open_retained_database_read_only,
    read_snapshot_metadata,
    retained_root_attestation,
    storage_inventory,
)
from tools.as003pr5a_evidence import ROOT as EVIDENCE_ROOT, canonical_json, publish


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SEED = 45878900
HORIZON = 500
REGIME = "R0"
SCENARIO = "S0"
WORK_ROOT = EVIDENCE_ROOT / "r5a-work"
LOCK_NAME = "AS003PR5A_EXECUTION_PROTOCOL_LOCK.json"


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, set):
        return sorted((_safe(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    return str(value)


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest_file(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPOSITORY_ROOT, text=True).strip()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sqlite_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    return value


def _database_inventory(path: Path) -> dict[str, Any]:
    tables: dict[str, Any] = {}
    source = open_retained_database_read_only() if path == RETAINED_DATABASE else sqlite3.connect(path)
    with source as connection:
        connection.row_factory = sqlite3.Row
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            rows = [
                {key: _sqlite_value(row[key]) for key in row.keys()}
                for row in connection.execute(f"SELECT * FROM {quoted}")
            ]
            rows.sort(key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")))
            data = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
            tables[name] = {"row_count": len(rows), "semantic_sha256": _digest_bytes(data)}
    return {"integrity_check": integrity, "tables": tables}


def _backup_database(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    source_connection = (
        open_retained_database_read_only()
        if source == RETAINED_DATABASE
        else sqlite3.connect(source)
    )
    with source_connection, sqlite3.connect(destination) as target_connection:
        source_connection.backup(target_connection)
        target_connection.commit()
    descriptor = os.open(destination, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory_fd = os.open(destination.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _publish_json(name: str, value: Any) -> str:
    return publish(name, canonical_json(_safe(value)))


def _publish_file(name: str, path: Path) -> str:
    return publish(name, path.read_bytes())


def _retained_root_phase() -> dict[str, Any]:
    from umbra_core.habitat.state import canonical_serialize

    WORK_ROOT.mkdir(parents=False, exist_ok=False)
    attestation = retained_root_attestation()
    if attestation["result"] != "PASS":
        raise RuntimeError("retained_root_attestation_failed")
    source_before = storage_inventory()
    root_inventory = _database_inventory(RETAINED_DATABASE)
    control_db = WORK_ROOT / "control.sqlite"
    shadow_db = WORK_ROOT / "shadow.sqlite"
    _backup_database(RETAINED_DATABASE, control_db)
    _backup_database(RETAINED_DATABASE, shadow_db)
    control_inventory = _database_inventory(control_db)
    shadow_inventory = _database_inventory(shadow_db)
    clone_equal = root_inventory == control_inventory == shadow_inventory
    independent_files = len(
        {os.stat(path).st_ino for path in (RETAINED_DATABASE, control_db, shadow_db)}
    ) == 3

    habitat_bytes = RETAINED_HABITAT.read_bytes()
    habitat_state = pickle.loads(habitat_bytes)
    habitat_canonical = canonical_serialize(habitat_state)
    control_habitat = WORK_ROOT / "CONTROL.habitat.pickle"
    shadow_habitat = WORK_ROOT / "SHADOW.habitat.pickle"
    _atomic_write(control_habitat, habitat_bytes)
    _atomic_write(shadow_habitat, habitat_bytes)
    habitat_independent = len(
        {os.stat(path).st_ino for path in (RETAINED_HABITAT, control_habitat, shadow_habitat)}
    ) == 3
    habitat_equal = (
        _digest_file(control_habitat)
        == _digest_file(shadow_habitat)
        == _digest_file(RETAINED_HABITAT)
    )

    with open_retained_database_read_only() as connection:
        metadata = read_snapshot_metadata(connection)
        snapshot = metadata["latest_snapshot"]
        if snapshot is None:
            raise RuntimeError("retained_latest_snapshot_missing")
        root_state = json.loads(snapshot["state_json"])
        root_events = [
            {
                "sequence": row["sequence"],
                "event_id": row["event_id"],
                "agent_id": row["agent_id"],
                "event_type": row["event_type"],
                "schema_version": row["schema_version"],
                "monotonic_time": row["monotonic_time"],
                "wall_time": row["wall_time"],
                "causal_parent_ids": json.loads(row["causal_parent_ids"]),
                "payload": json.loads(row["payload"]),
                "payload_hash": row["payload_hash"],
                "previous_event_hash": row["previous_event_hash"],
                "event_hash": row["event_hash"],
            }
            for row in connection.execute("SELECT * FROM events ORDER BY sequence")
        ]

    source_after = storage_inventory()
    source_unchanged = all(
        source_before[name].get("sha256") == source_after[name].get("sha256")
        for name in source_before
    )
    shared_writable_sidecars = any(
        path.exists()
        for path in (
            Path(f"{control_db}-wal"),
            Path(f"{control_db}-shm"),
            Path(f"{shadow_db}-wal"),
            Path(f"{shadow_db}-shm"),
        )
    )
    clone_proof = {
        "schema": "AS003PR5A_ROOT_CLONE_PROOF_V1",
        "directive": "UMBRA-AS-003P-R5A",
        "result": "PASS"
        if clone_equal
        and independent_files
        and habitat_equal
        and habitat_independent
        and source_unchanged
        and not shared_writable_sidecars
        else "FAIL",
        "method": "SQLite Connection.backup from read-only immutable retained R5 root",
        "root_creation_count": 0,
        "retained_root_database_sha256": _digest_file(RETAINED_DATABASE),
        "control_database_preload_sha256": _digest_file(control_db),
        "shadow_database_preload_sha256": _digest_file(shadow_db),
        "semantic_inventory": root_inventory,
        "control_inventory_equal": control_inventory == root_inventory,
        "shadow_inventory_equal": shadow_inventory == root_inventory,
        "independent_database_inodes": independent_files,
        "retained_habitat_sha256": _digest_file(RETAINED_HABITAT),
        "control_habitat_sha256": _digest_file(control_habitat),
        "shadow_habitat_sha256": _digest_file(shadow_habitat),
        "habitat_byte_equal": habitat_equal,
        "independent_habitat_inodes": habitat_independent,
        "shared_writable_wal_or_shm": shared_writable_sidecars,
        "retained_source_hashes_before": source_before,
        "retained_source_hashes_after": source_after,
        "retained_source_hashes_unchanged": source_unchanged,
    }
    if clone_proof["result"] != "PASS":
        raise RuntimeError("root_clone_proof_failed")
    root_bundle = {
        "authoritative_state": root_state,
        "authoritative_events": root_events,
        "rng_state": root_state.get("rng_state"),
        "habitat_state": habitat_canonical,
    }
    exact_ids = sorted(collect_declared_ids(root_bundle))
    _publish_json("AS003PR5A_ROOT_CLONE_PROOF.json", clone_proof)
    return {
        "clone_proof": clone_proof,
        "control_db": control_db,
        "shadow_db": shadow_db,
        "control_habitat": control_habitat,
        "shadow_habitat": shadow_habitat,
        "exact_ids": exact_ids,
    }


def _branch(role: str, database: Path, habitat_path: Path, work: Path) -> int:
    from experiments.close02r import qualification as fixture
    from umbra_core.habitat.state import canonical_serialize

    shadow = role == "SHADOW"
    decision_trace = work / f"{role}.decision-trace.jsonl"
    planning_trace = work / f"{role}.planning-shadow.jsonl"
    original_config = fixture.config

    def config(seed: int, db: Path, regime: str):
        value = original_config(seed, db, regime)
        value.decision_trace_path = str(decision_trace)
        value.planning_shadow_path = str(planning_trace) if shadow else None
        return value

    fixture.config = config
    organism = None
    try:
        habitat_state = pickle.loads(habitat_path.read_bytes())
        organism, engine = fixture.reload_existing(SEED, database, REGIME, habitat_state)
        organism.store.validate_chain()
        pre = {
            "schema": "AS003PR5A_BRANCH_PREMEASUREMENT_V1",
            "role": role,
            "shadow_enabled": shadow,
            "tick": organism.tick,
            "pre_authoritative_state": _safe(organism.authoritative_state()),
            "authoritative_events": _safe(list(organism.store.iter_events())),
            "rng_state": _safe(organism.rng.export_state()),
            "habitat_state": canonical_serialize(engine.state),
            "database_path": str(database),
            "process_id": os.getpid(),
            "branch_load_count": 1,
            "measured_ticks": 0,
        }
        _atomic_write(work / f"{role}.pre.json", canonical_json(pre))
        print(f"READY {role}", flush=True)
        command = sys.stdin.readline().strip()
        if not command.startswith("GO "):
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
        final_state = _safe(organism.authoritative_state())
        events = _safe(list(organism.store.iter_events()))
        rng = _safe(organism.rng.export_state())
        habitat = canonical_serialize(engine.state)
        organism.close()
        organism = None
        decisions = _read_jsonl(decision_trace)
        record = {
            "schema": "AS003PR5A_BRANCH_RAW_EXECUTION_V1",
            "role": role,
            "seed": SEED,
            "horizon": HORIZON,
            "shadow_enabled": shadow,
            "timeline": timeline,
            "authoritative_events": events,
            "final_authoritative_state": final_state,
            "rng_state": rng,
            "final_habitat_state": habitat,
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
            "planning_trace_rows": len(_read_jsonl(planning_trace)) if shadow else 0,
            "branch_load_count": 1,
            "measured_ticks": HORIZON,
            "retries": 0,
            "reseeds": 0,
        }
        _atomic_write(work / f"{role}.result.json", canonical_json(record))
        print(f"DONE {role}", flush=True)
        return 0
    except BaseException as error:
        failure = {
            "schema": "AS003PR5A_BRANCH_EXCEPTION_V1",
            "role": role,
            "exception_type": type(error).__name__,
            "exception": str(error),
            "measured_tick": None if organism is None else organism.tick,
            "no_retry": True,
        }
        path = work / f"{role}.exception.json"
        if not path.exists():
            _atomic_write(path, canonical_json(failure))
        return 4
    finally:
        fixture.config = original_config
        if organism is not None:
            organism.close()


def _start_worker(role: str, database: Path, habitat_path: Path) -> subprocess.Popen[str]:
    command = [
        sys.executable,
        "-m",
        "experiments.as003pr5a.common_root_pair",
        "branch",
        "--role",
        role,
        "--database",
        str(database),
        "--habitat",
        str(habitat_path),
        "--work",
        str(WORK_ROOT),
    ]
    return subprocess.Popen(
        command,
        cwd=REPOSITORY_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


def _stop_workers(workers: dict[str, subprocess.Popen[str]]) -> None:
    for worker in workers.values():
        if worker.poll() is None and worker.stdin is not None:
            worker.stdin.write("STOP\n")
            worker.stdin.flush()
    for worker in workers.values():
        try:
            worker.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            worker.terminate()


def _orchestrate() -> int:
    if (EVIDENCE_ROOT / "AS003PR5A_PAIRED_EXECUTION_FINISHED.json").exists():
        raise FileExistsError("R5 one-shot protocol already completed")
    implementation_commit = _git("rev-parse", "HEAD")
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
        control_pre = json.loads((WORK_ROOT / "CONTROL.pre.json").read_text(encoding="utf-8"))
        shadow_pre = json.loads((WORK_ROOT / "SHADOW.pre.json").read_text(encoding="utf-8"))
        pre_sections = {
            "pre_authoritative_state": (
                control_pre["pre_authoritative_state"], shadow_pre["pre_authoritative_state"]
            ),
            "authoritative_events": (control_pre["authoritative_events"], shadow_pre["authoritative_events"]),
            "rng_state": (control_pre["rng_state"], shadow_pre["rng_state"]),
            "habitat_state": (control_pre["habitat_state"], shadow_pre["habitat_state"]),
        }
        pre_control = {name: left for name, (left, _) in pre_sections.items()}
        pre_shadow = {name: right for name, (_, right) in pre_sections.items()}
        pre_parity = compare_values(
            pre_control,
            pre_shadow,
            root="",
            pre_fork_exact_ids=set(root["exact_ids"]),
        )
        pre_parity.update(
            {
                "schema": "AS003PR5A_PREMEASUREMENT_PARITY_V1",
                "directive": "UMBRA-AS-003P-R5A",
                "result": "PASS" if pre_parity["semantic_equal"] else "FAIL",
                "control_branch_loads": 1,
                "shadow_branch_loads": 1,
                "control_measured_ticks": 0,
                "shadow_measured_ticks": 0,
            }
        )
        _publish_json("AS003PR5A_CONTROL_PREMEASUREMENT.json", control_pre)
        _publish_json("AS003PR5A_SHADOW_PREMEASUREMENT.json", shadow_pre)
        _publish_json("AS003PR5A_PREMEASUREMENT_PARITY.json", pre_parity)
        if not pre_parity["semantic_equal"]:
            _stop_workers(workers)
            _publish_json(
                "AS003PR5A_SCIENTIFIC_RESULT.json",
                {
                    "schema": "AS003PR5A_SCIENTIFIC_RESULT_V1",
                    "verdict": "AS003PR5A_PREMEASUREMENT_PARITY_FAIL",
                    "first_semantic_divergence": pre_parity["semantic_differences"][0],
                    "control_measured_ticks": 0,
                    "shadow_measured_ticks": 0,
                    "retries": 0,
                    "reseeds": 0,
                },
            )
            return 0
        barrier = {
            "schema": "AS003PR5A_PREMEASUREMENT_BARRIER_V1",
            "result": "READY_FOR_EXECUTION_LOCK",
            "implementation_commit": implementation_commit,
            "retained_root_attestation_sha256": _digest_file(
                EVIDENCE_ROOT / "AS003PR5A_RETAINED_ROOT_ATTESTATION_CORRECTION.json"
            ),
            "clone_proof_sha256": _digest_file(EVIDENCE_ROOT / "AS003PR5A_ROOT_CLONE_PROOF.json"),
            "premeasurement_parity_sha256": _digest_file(EVIDENCE_ROOT / "AS003PR5A_PREMEASUREMENT_PARITY.json"),
            "branch_process_ids": {role: worker.pid for role, worker in workers.items()},
            "measured_ticks": {"CONTROL": 0, "SHADOW": 0},
        }
        _publish_json("AS003PR5A_PREMEASUREMENT_BARRIER.json", barrier)
        print("AS003PR5A_BARRIER_READY", flush=True)
        release = sys.stdin.readline().strip().split()
        if len(release) != 3 or release[0] != "GO":
            raise RuntimeError("invalid_execution_release")
        release_commit, supplied_lock_sha = release[1], release[2]
        lock_path = EVIDENCE_ROOT / LOCK_NAME
        if not lock_path.exists() or _digest_file(lock_path) != supplied_lock_sha:
            raise RuntimeError("execution_lock_digest_mismatch")
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        if lock.get("implementation_commit") != implementation_commit:
            raise RuntimeError("execution_lock_implementation_mismatch")
        if _git("rev-parse", "HEAD") != release_commit:
            raise RuntimeError("release_commit_not_current_head")
        changed = _git("diff", "--name-only", f"{implementation_commit}..{release_commit}").splitlines()
        forbidden = [
            path for path in changed
            if not (
                path.startswith(".agent/")
                or path == "experiments/as003pr5a/AS003PR5A_EXECUTION_PROTOCOL_LOCK.json"
            )
        ]
        if forbidden:
            raise RuntimeError(f"post_barrier_scientific_change:{forbidden}")
        for worker in workers.values():
            assert worker.stdin is not None
            worker.stdin.write(f"GO {supplied_lock_sha}\n")
            worker.stdin.flush()
        outputs = {}
        for role, worker in workers.items():
            stdout, stderr = worker.communicate()
            outputs[role] = {"exit_code": worker.returncode, "stdout": stdout, "stderr": stderr}
        if any(row["exit_code"] != 0 for row in outputs.values()):
            for role in workers:
                exception = WORK_ROOT / f"{role}.exception.json"
                if exception.exists():
                    _publish_file(f"AS003PR5A_{role}_EXCEPTION.json", exception)
            _publish_json(
                "AS003PR5A_FROZEN_EXECUTION_FAILURE.json",
                {"verdict": "AS003PR5A_FROZEN_EXECUTION_FAIL", "worker_results": outputs, "no_retry": True},
            )
            return 0

        control = json.loads((WORK_ROOT / "CONTROL.result.json").read_text(encoding="utf-8"))
        shadow = json.loads((WORK_ROOT / "SHADOW.result.json").read_text(encoding="utf-8"))
        artifact_sha = {
            "AS003PR5A_CONTROL_RUN_RAW.json": _publish_json("AS003PR5A_CONTROL_RUN_RAW.json", control),
            "AS003PR5A_SHADOW_RUN_RAW.json": _publish_json("AS003PR5A_SHADOW_RUN_RAW.json", shadow),
            "AS003PR5A_CONTROL_DECISION_TRACE.jsonl": _publish_file(
                "AS003PR5A_CONTROL_DECISION_TRACE.jsonl", WORK_ROOT / "CONTROL.decision-trace.jsonl"
            ),
            "AS003PR5A_SHADOW_DECISION_TRACE.jsonl": _publish_file(
                "AS003PR5A_SHADOW_DECISION_TRACE.jsonl", WORK_ROOT / "SHADOW.decision-trace.jsonl"
            ),
            "AS003PR5A_PLANNING_SHADOW_TRACE.jsonl": _publish_file(
                "AS003PR5A_PLANNING_SHADOW_TRACE.jsonl", WORK_ROOT / "SHADOW.planning-shadow.jsonl"
            ),
        }
        parity = compare_run_records(control, shadow, pre_fork_exact_ids=set(root["exact_ids"]))
        parity.update(
            {
                "directive": "UMBRA-AS-003P-R5A",
                "control_measured_ticks": control["measured_ticks"],
                "shadow_measured_ticks": shadow["measured_ticks"],
                "retries": 0,
                "reseeds": 0,
            }
        )
        artifact_sha["AS003PR5A_SEMANTIC_OBSERVER_PARITY.json"] = _publish_json(
            "AS003PR5A_SEMANTIC_OBSERVER_PARITY.json", parity
        )
        if not parity["semantic_equal"]:
            verdict = "AS003PR5A_TRUE_OBSERVER_EFFECT_FAIL"
            blocker = None
            relation = None
        else:
            analyses = analyze_modal(
                EVIDENCE_ROOT / "AS003PR5A_PLANNING_SHADOW_TRACE.jsonl",
                EVIDENCE_ROOT / "AS003PR5A_SHADOW_DECISION_TRACE.jsonl",
            )
            for name, value in analyses.items():
                artifact_sha[name] = _publish_json(name, value)
            summary = analyses["AS003PR5A_MODAL_EVIDENCE_SUMMARY.json"]
            blocker = analyses["AS003PR5A_AS003L_BLOCKER_RESULT.json"]["classification"]
            relation = analyses["AS003PR5A_AS002_FUTURE_BOUNDARY.json"]["disposition"]
            if summary["frames_complete"] == 0:
                verdict = "AS003PR5A_SOURCE_FRAME_CAPTURE_FAIL"
            elif blocker == "BLOCKER_EXPRESSED":
                verdict = "AS003PR5A_OBSERVER_SAFE_MODAL_EVIDENCE_QUALIFIED"
            else:
                verdict = "AS003PR5A_OBSERVER_SAFE_MODAL_EVIDENCE_NONDISCRIMINATING"
        result = {
            "schema": "AS003PR5A_SCIENTIFIC_RESULT_V1",
            "directive": "UMBRA-AS-003P-R5A",
            "verdict": verdict,
            "observer_semantic_parity": parity["semantic_equal"],
            "semantic_difference_count": parity["semantic_difference_count"],
            "first_semantic_divergence": parity["first_semantic_divergence"],
            "as003l_disposition": blocker,
            "as002_future_relation": relation,
            "control_executions": 1,
            "shadow_executions": 1,
            "control_measured_ticks": control["measured_ticks"],
            "shadow_measured_ticks": shadow["measured_ticks"],
            "retries": 0,
            "reseeds": 0,
            "artifact_sha256": artifact_sha,
        }
        _publish_json("AS003PR5A_SCIENTIFIC_RESULT.json", result)
        _publish_json(
            "AS003PR5A_PAIRED_EXECUTION_FINISHED.json",
            {
                "schema": "AS003PR5A_PAIRED_EXECUTION_FINISHED_V1",
                "execution_lock_commit": release_commit,
                "verdict": verdict,
                "control_executions": 1,
                "shadow_executions": 1,
                "retries": 0,
                "reseeds": 0,
                "finished_unix": time.time(),
            },
        )
        print(json.dumps({"verdict": verdict, "parity": parity["semantic_equal"]}, sort_keys=True), flush=True)
        return 0
    except BaseException as error:
        _stop_workers(workers)
        if not (EVIDENCE_ROOT / "AS003PR5A_PROTOCOL_EXCEPTION.json").exists():
            _publish_json(
                "AS003PR5A_PROTOCOL_EXCEPTION.json",
                {
                    "schema": "AS003PR5A_PROTOCOL_EXCEPTION_V1",
                    "exception_type": type(error).__name__,
                    "exception": str(error),
                    "no_retry": True,
                },
            )
        return 5


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True)
    subparsers.add_parser("orchestrate")
    branch = subparsers.add_parser("branch")
    branch.add_argument("--role", choices=("CONTROL", "SHADOW"), required=True)
    branch.add_argument("--database", type=Path, required=True)
    branch.add_argument("--habitat", type=Path, required=True)
    branch.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "branch":
        raise SystemExit(_branch(args.role, args.database, args.habitat, args.work))
    raise SystemExit(_orchestrate())


if __name__ == "__main__":
    main()
