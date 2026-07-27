"""D-012A2 distinct-process, ownership, IPC, crash, and cleanup checks."""
from __future__ import annotations

import ast
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from experiments.d012.campaign_supervisor import CampaignSupervisor, freeze_hash
from experiments.d012.checkpoint_runner import run_checkpoint
from experiments.d012.checkpoint_runner import recover_checkpoint
from experiments.d012.database_ownership import (
    acquire_ownership,
    read_ownership,
    release_ownership,
)
from experiments.d012.failure_codes import SupervisionError
from experiments.d012.organism_worker import Worker, organism_config
from experiments.d012.process_identity import process_identity
from experiments.d012.run_disposable_dry_run import run
from experiments.d012.run_formal_p0 import analyze_samples
from experiments.d012.worker_launcher import WorkerClient, manifest_for
from experiments.d012.worker_protocol import (
    BoundedLog,
    encode_message,
    validate_command,
    validate_manifest,
)
from umbra_core.arbitration import Arbitrator
from umbra_core.physiology import Physiology
from umbra_core.runtime import create_organism
from umbra_core.util import SeededRNG

EXP = Path(__file__).resolve().parents[1] / "experiments/d012"


def test_critical_recovery_approaches_until_charge_is_executable():
    physiology = Physiology(energy=0.04)
    chosen = Arbitrator().select(
        physiology,
        [
            {
                "kind": "resource",
                "relative_direction": 0.0,
                "estimated_distance": 1.526,
                "confidence": 1.0,
                "uncertainty": 0.0,
            }
        ],
        1,
        SeededRNG(12012),
    )
    assert chosen.capability == "APPROACH"


def test_formal_tick_records_complete_recovery_chain(tmp_path):
    manifest = manifest_for(
        tmp_path,
        execution_id="formal-trace-test",
        generation=1,
        ownership_generation=1,
        freeze_manifest_hash=freeze_hash(EXP),
        active_runtime=0.0,
        diagnostic_recovery_reachable=True,
        formal_physiology_trace_path=str(tmp_path / "physiology.jsonl"),
        formal_recovery_trace_path=str(tmp_path / "recovery.jsonl"),
        formal_failure_path=str(tmp_path / "failure.json"),
    )
    worker = Worker(manifest)
    try:
        worker.acquire_and_load(reclaim_dead=False)
        worker.running = True
        worker.organism.phys.energy = 0.25
        before = worker.organism.phys.energy
        for _ in range(5):
            worker.run_formal_tick()
            if worker.organism.phys.energy > before:
                break
        physiology = [
            json.loads(line)
            for line in (tmp_path / "physiology.jsonl").read_text().splitlines()
        ]
        recovery = [
            json.loads(line)
            for line in (tmp_path / "recovery.jsonl").read_text().splitlines()
        ]
        charge = next(
            row for row in recovery if row["selected_candidate"] == "CHARGE"
        )
        assert all(row["candidate_source"] == "recovery_reflex" for row in physiology)
        assert charge["generated_recovery_candidates"] == ["CHARGE"]
        assert charge["governance_decision"]["admitted"]
        assert charge["embodiment_validation"] == "ok"
        assert charge["verified_outcome"]["success"]
        assert charge["energy_after_tick"] > charge["energy_before_tick"]
        assert not (tmp_path / "failure.json").exists()
    finally:
        worker.quiesce()


def test_worker_cleanup_does_not_tick_mutate_physiology_or_append_events(tmp_path):
    client = launch(tmp_path, tick_period_seconds=10.0)
    client.request("START")
    client.request("RUN_DIAGNOSTIC_TICKS", count=3)
    before = client.request("METRICS")["metrics"]
    client.shutdown(0.0)

    connection = sqlite3.connect(tmp_path / "dry-run.sqlite")
    event_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    state = json.loads(
        connection.execute(
            "SELECT state_json FROM snapshots ORDER BY sequence DESC LIMIT 1"
        ).fetchone()[0]
    )
    connection.close()

    assert state["tick"] == before["tick"]
    assert {
        name: state["physiology"][name]
        for name in ("energy", "fatigue", "integrity", "stimulation")
    } == before["physiology"]
    assert event_count == before["event_count"]
    assert read_ownership(tmp_path / "database-ownership.json")["status"] == "RELEASED"
    assert not list(tmp_path.glob("*.sock"))


def launch(
    root: Path,
    *,
    generation: int = 1,
    ownership_generation: int = 1,
    reclaim_dead: bool = False,
    **flags,
) -> WorkerClient:
    root.mkdir(parents=True, exist_ok=True)
    manifest = manifest_for(
        root,
        execution_id="process-boundary-test",
        generation=generation,
        ownership_generation=ownership_generation,
        freeze_manifest_hash=freeze_hash(EXP),
        active_runtime=0.0,
        reclaim_dead=reclaim_dead,
        **flags,
    )
    return WorkerClient.launch(root / f"manifest-{generation}.json", manifest)


def test_worker_is_distinct_and_supervisor_has_no_runtime_import(tmp_path):
    client = launch(tmp_path)
    try:
        ready = client.request("START")
        assert client.pid != os.getpid()
        assert client.identity != process_identity(os.getpid())
        assert ready["process_start_identity"] == client.identity
        assert ready["organism_id"]
    finally:
        client.shutdown(0.0)
    for name in (
        "campaign_supervisor.py",
        "run_disposable_dry_run.py",
        "run_formal_p0.py",
        "run_formal_p0_s1.py",
        "worker_launcher.py",
    ):
        tree = ast.parse((EXP / name).read_text())
        imports = [
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ]
        assert not any(module.startswith("umbra_core") for module in imports)
        source = (EXP / name).read_text()
        assert "create_organism" not in source
        assert "load_organism" not in source
        assert "sqlite3.connect" not in source
    assert "mode=ro" in (EXP / "checkpoint_runner.py").read_text()


def test_formal_p0_freeze_and_stability_decision_are_fail_closed():
    config = json.loads((EXP / "p0-formal-config.json").read_text())
    assert config["minimum_active_seconds"] == 1200
    assert config["normal_stop_seconds"] == 1800
    assert config["maximum_active_seconds"] == 3600
    assert not config["d010_enabled"]
    assert not config["p1_authorized"] and not config["p2_authorized"]
    samples = [
        {
            "sample_index": index,
            "active_runtime_seconds": index * 10,
            "rss_mib": 100.0,
            "cpu_fraction": 0.01,
            "sample_seconds": 10,
        }
        for index in range(121)
    ]
    assert analyze_samples(samples, config)["classification"] == "CLEARLY_STABLE"
    for sample in samples:
        sample["rss_mib"] = 100 + sample["active_runtime_seconds"] / 1800
    assert analyze_samples(samples, config)["classification"] == "FAILED"
    for sample in samples:
        sample["rss_mib"] = 170.0
    assert analyze_samples(samples, config)["classification"] == "AMBIGUOUS"


def test_worker_autonomously_ticks_and_reports_bounded_metrics(tmp_path):
    client = launch(tmp_path)
    try:
        started = client.request("START")
        tick = int(started["chain_tip"])
        time.sleep(1.1)
        response = client.request("METRICS")
        metrics = response["metrics"]
        assert int(response["chain_tip"]) > tick
        assert metrics["tick"] >= 2
        assert not metrics["physiology_critical"]
        assert metrics["durable_raw_count"] == 0
        assert metrics["perception_observation_count"] <= 256
        assert metrics["deduplication_id_count"] <= 512
        assert metrics["memory_count"] <= metrics["memory_count_max"]
        assert metrics["social_hypothesis_count"] <= metrics["social_hypothesis_count_max"]
        assert metrics["routine_count"] <= metrics["routine_count_max"]
        assert metrics["world_model_count"] <= metrics["world_model_count_max"]
        assert metrics["individuality_evidence_count"] <= metrics[
            "individuality_evidence_count_max"
        ]
        assert metrics["expression_retained_count"] <= metrics[
            "expression_retained_count_max"
        ]
    finally:
        client.shutdown(0.0)


def test_formal_duplicate_event_suppresses_entire_burst(tmp_path):
    client = launch(tmp_path)
    try:
        client.request("START")
        result = client.request("RUN_EVENT", event_index=3)["event"]
        assert result["perception"]["duplicate_attempts"] == 8
        assert result["perception"]["duplicates_suppressed"] == 8
    finally:
        client.shutdown(0.0)


def test_database_ownership_live_duplicate_generation_and_execution_refusals(tmp_path):
    path = tmp_path / "owner.json"
    db = tmp_path / "organism.sqlite"
    record = acquire_ownership(
        path,
        execution_id="e1",
        database_path=db,
        supervisor_execution_id="e1",
        generation=1,
    )
    with pytest.raises(SupervisionError, match="DATABASE_ALREADY_OWNED"):
        acquire_ownership(
            path,
            execution_id="e1",
            database_path=db,
            supervisor_execution_id="e1",
            generation=2,
        )
    release_ownership(path, record)
    with pytest.raises(SupervisionError, match="OWNERSHIP_GENERATION_CONFLICT"):
        acquire_ownership(
            path,
            execution_id="e1",
            database_path=db,
            supervisor_execution_id="e1",
            generation=1,
        )
    with pytest.raises(SupervisionError, match="DATABASE_EXECUTION_CONFLICT"):
        acquire_ownership(
            path,
            execution_id="e2",
            database_path=db,
            supervisor_execution_id="e2",
            generation=2,
        )


def test_duplicate_live_worker_launch_refuses_with_stable_code(tmp_path):
    first = launch(tmp_path)
    try:
        with pytest.raises(SupervisionError, match="DATABASE_ALREADY_OWNED"):
            launch(tmp_path, generation=2, ownership_generation=2)
    finally:
        first.shutdown(0.0)


def test_dead_ownership_requires_explicit_reclaim(tmp_path):
    path = tmp_path / "owner.json"
    db = tmp_path / "organism.sqlite"
    path.write_text(json.dumps({
        "execution_id": "e1",
        "database_path": str(db),
        "worker_pid": 999_999_999,
        "worker_process_start_identity": "dead",
        "supervisor_execution_id": "e1",
        "acquired_at": 0,
        "ownership_generation": 1,
        "status": "ACTIVE",
    }))
    with pytest.raises(SupervisionError, match="OWNERSHIP_TRANSFER_INCOMPLETE"):
        acquire_ownership(
            path,
            execution_id="e1",
            database_path=db,
            supervisor_execution_id="e1",
            generation=2,
        )
    record = acquire_ownership(
        path,
        execution_id="e1",
        database_path=db,
        supervisor_execution_id="e1",
        generation=2,
        reclaim_dead=True,
    )
    release_ownership(path, record)
    assert list(tmp_path.glob("owner.json.stale.*"))


def test_ipc_rejects_wrong_execution_generation_sequence_and_raw_payload(tmp_path):
    client = launch(tmp_path)
    try:
        expected = client.sequence + 1
        base = {
            "command": "START",
            "execution_id": client.execution_id,
            "generation": client.generation,
            "sequence": expected,
            "process_start_identity": client.identity,
            "active_runtime": 0.0,
            "chain_tip": None,
        }
        wrong = client.raw_request({**base, "execution_id": "wrong"})
        assert wrong["failure_code"] == "IPC_EXECUTION_MISMATCH"
        wrong = client.raw_request({**base, "generation": 99})
        assert wrong["failure_code"] == "IPC_GENERATION_MISMATCH"
        wrong = client.raw_request({**base, "sequence": expected + 1})
        assert wrong["failure_code"] == "IPC_SEQUENCE_INVALID"
        wrong = client.raw_request({**base, "process_start_identity": "wrong"})
        assert wrong["failure_code"] == "IPC_IDENTITY_MISMATCH"
        client.request("START")
        with pytest.raises(SupervisionError, match="IPC_MESSAGE_INVALID"):
            encode_message({"nested": {"raw_payload": "forbidden"}})
    finally:
        client.shutdown(0.0)


def test_supervisor_reattaches_to_live_worker(tmp_path):
    original = launch(tmp_path)
    original.request("START")
    attached = WorkerClient.reattach(
        execution_id=original.execution_id,
        generation=original.generation,
        socket_path=original.socket_path,
        pid=original.pid,
        identity=original.identity,
        sequence=original.sequence,
        active_runtime=original.active_runtime,
        chain_tip=original.chain_tip,
    )
    assert attached.pid == original.pid
    attached.shutdown(0.0)


def test_worker_survives_actual_supervisor_death_and_reattaches(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "experiments.d012.supervisor_crash_probe",
            "--root",
            str(tmp_path),
        ],
        check=False,
    )
    assert completed.returncode == 73
    record = json.loads((tmp_path / "reattach.json").read_text())
    supervisor = CampaignSupervisor(
        tmp_path,
        record["execution_id"],
        tmp_path / "dry-run.sqlite",
        tmp_path / "evidence",
        freeze_hash(EXP),
    )
    recovered = supervisor.recover_after_crash(prior_classified=True)
    assert recovered["organism_pid"] == record["pid"]
    attached = WorkerClient.reattach(
        execution_id=record["execution_id"],
        generation=record["generation"],
        socket_path=Path(record["socket_path"]),
        pid=record["pid"],
        identity=record["identity"],
        sequence=record["sequence"],
        active_runtime=record["active_runtime"],
        chain_tip=record["chain_tip"],
    )
    attached.shutdown(0.0)
    supervisor.set_status("COMPLETED")
    supervisor.release()
    assert not (tmp_path / "campaign.lock").exists()
    assert list(tmp_path.glob("campaign.lock.stale.*"))
    assert b"worker_ready" in (tmp_path / "organism-worker.log").read_bytes()


@pytest.mark.parametrize("force", [False, True])
def test_dead_worker_is_reclaimed_without_duplicate(force, tmp_path):
    first = launch(tmp_path)
    first.request("START")
    if force:
        first.force_kill()
    else:
        first.terminate()
    owner = read_ownership(tmp_path / "database-ownership.json")
    assert owner and owner["status"] == "ACTIVE"
    second = launch(
        tmp_path,
        generation=2,
        ownership_generation=int(owner["ownership_generation"]) + 1,
        reclaim_dead=True,
    )
    try:
        started = second.request("START")
        assert started["organism_id"]
        assert second.pid != first.pid
    finally:
        second.shutdown(0.0)


@pytest.mark.parametrize("force", [False, True])
def test_signal_during_ordinary_ticking_recovers_identity(force, tmp_path):
    first = launch(tmp_path)
    started = first.request("START")
    organism_id = started["organism_id"]
    error: list[BaseException] = []

    def run_ticks() -> None:
        try:
            first.request("RUN_DIAGNOSTIC_TICKS", count=100_000)
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=run_ticks)
    thread.start()
    deadline = time.monotonic() + 5
    while b"diagnostic_ticks_started" not in (tmp_path / "organism-worker.log").read_bytes():
        assert time.monotonic() < deadline
        time.sleep(0.01)
    if force:
        first.force_kill()
    else:
        first.terminate()
    thread.join(timeout=5)
    assert not thread.is_alive() and error
    owner = read_ownership(tmp_path / "database-ownership.json")
    assert owner
    replacement = launch(
        tmp_path,
        generation=2,
        ownership_generation=int(owner["ownership_generation"]) + 1,
        reclaim_dead=True,
    )
    try:
        assert replacement.request("START")["organism_id"] == organism_id
    finally:
        replacement.shutdown(0.0)


def test_death_before_ready_and_after_ownership_are_classified(tmp_path):
    with pytest.raises(SupervisionError, match="ORGANISM_START_FAILED"):
        launch(tmp_path / "before", crash_before_ready=True)
    after = tmp_path / "after"
    with pytest.raises(SupervisionError, match="ORGANISM_START_FAILED"):
        launch(after, crash_after_ownership=True)
    owner = read_ownership(after / "database-ownership.json")
    assert owner and owner["status"] == "ACTIVE"


def test_checkpoint_requires_worker_quiescence_and_recovers_after_checkpoint_crash(tmp_path):
    client = launch(tmp_path)
    client.request("START")
    with pytest.raises(SupervisionError, match="CHECKPOINT_NOT_QUIESCENT"):
        run_checkpoint(
            tmp_path / "dry-run.sqlite",
            tmp_path / "evidence",
            "C0",
            ownership_path=tmp_path / "database-ownership.json",
        )
    with pytest.raises(SupervisionError, match="IPC_MESSAGE_INVALID"):
        client.request("CHECKPOINT_PREPARE", inject_crash=True)
    client.force_kill()
    owner = read_ownership(tmp_path / "database-ownership.json")
    assert owner
    replacement = launch(
        tmp_path,
        generation=2,
        ownership_generation=int(owner["ownership_generation"]) + 1,
        reclaim_dead=True,
    )
    try:
        replacement.request("START")
        replacement.request("CHECKPOINT_PREPARE")
        result = run_checkpoint(
            tmp_path / "dry-run.sqlite",
            tmp_path / "evidence",
            "C0",
            ownership_path=tmp_path / "database-ownership.json",
        )
        assert result["raw_payload_count"] == 0
    finally:
        replacement.shutdown(0.0)


@pytest.mark.parametrize(
    "stage",
    [
        "before_copy",
        "during_copy",
        "after_copy_before_hash",
        "after_hash_before_result",
        "after_result",
    ],
)
def test_every_checkpoint_transaction_crash_stage_is_incomplete(stage, tmp_path):
    database = tmp_path / "organism.sqlite"
    organism = create_organism(organism_config(database))
    organism.run_ticks(2)
    organism.close()
    evidence = tmp_path / "evidence"
    with pytest.raises(SupervisionError, match="CHECKPOINT_INCOMPLETE"):
        run_checkpoint(database, evidence, "C0", fail_at=stage)
    assert not recover_checkpoint(evidence, "C0")
    assert not (evidence / "C0.complete").exists()
    assert not (evidence / "C0.json").exists()


def test_manifest_and_log_bounds_fail_closed(tmp_path):
    with pytest.raises(SupervisionError, match="WORKER_MANIFEST_INVALID"):
        validate_manifest({"execution_id": "missing"})
    log = BoundedLog(
        tmp_path / "worker.log",
        "e1",
        generation=1,
        max_bytes=256,
        max_files=2,
    )
    for index in range(30):
        log.write("bounded", index=index, text="x" * 40)
    files = list(tmp_path.glob("worker.log*"))
    assert len(files) <= 3
    assert all(path.stat().st_size <= 256 for path in files)
    assert all(b"raw_payload" not in path.read_bytes() for path in files)


def test_full_distinct_process_campaign(tmp_path):
    result = run(tmp_path / "campaign")
    assert result["events"] == 19
    assert result["restarts"] == 4
    assert result["checkpoints"] == 5
    assert result["distinct_worker_pids"]
    assert result["distinct_worker_identities"]
    assert len(set(result["worker_pids"])) == 5
    assert result["final_ownership_status"] == "RELEASED"
    assert result["remaining_worker_pids"] == []
    assert result["remaining_sockets"] == []
    assert result["raw_payload_count"] == 0
    assert all(size <= 65_536 for size in result["log_bounds"].values())
    assert len({event["index"] for event in result["trace"]}) == 19
