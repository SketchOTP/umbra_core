"""Compressed D-012 schedule supervised through a distinct OS worker."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d012.campaign_supervisor import CampaignSupervisor, freeze_hash
from experiments.d012.checkpoint_runner import run_checkpoint
from experiments.d012.database_ownership import assert_quiescent, read_ownership
from experiments.d012.process_identity import identity_matches, process_identity
from experiments.d012.worker_launcher import WorkerClient, manifest_for


def run(output: Path) -> dict[str, object]:
    experiment_root = Path(__file__).resolve().parent
    schedule = json.loads(
        (experiment_root / "opportunity-schedule.json").read_text()
    )["events"]
    output.mkdir(parents=True, exist_ok=True)
    database = output / "dry-run.sqlite"
    ownership_path = output / "database-ownership.json"
    evidence = output / "evidence"
    execution_id = "d012-distinct-worker-dry-run"
    frozen_hash = freeze_hash(experiment_root)
    supervisor = CampaignSupervisor(
        output, execution_id, database, evidence, frozen_hash
    )
    client: WorkerClient | None = None
    worker_pids: list[int] = []
    worker_identities: list[str] = []
    trace: list[dict[str, object]] = []
    checkpoints = {4: "C1", 9: "C2", 14: "C3", 18: "C4"}
    restarts = {4, 9, 14, 17}
    generation = 1
    ownership_generation = 1
    organism_id: str | None = None

    def launch(*, reclaim_dead: bool = False) -> WorkerClient:
        nonlocal ownership_generation, organism_id
        manifest = manifest_for(
            output,
            execution_id=execution_id,
            generation=generation,
            ownership_generation=ownership_generation,
            freeze_manifest_hash=frozen_hash,
            active_runtime=supervisor.runtime.committed_seconds,
            reclaim_dead=reclaim_dead,
        )
        worker = WorkerClient.launch(
            output / f"worker-manifest-{generation}.json", manifest
        )
        supervisor.attach_worker(worker.pid, worker.identity, generation)
        worker_pids.append(worker.pid)
        worker_identities.append(worker.identity)
        started = worker.request(
            "START", active_runtime=supervisor.runtime.committed_seconds
        )
        supervisor.record_worker_status(started)
        current_id = str(started["organism_id"])
        if organism_id is None:
            organism_id = current_id
        elif current_id != organism_id:
            raise RuntimeError("organism_identity_changed")
        ownership_generation = int(started["ownership_generation"])
        supervisor.set_status("RUNNING")
        return worker

    def checkpoint(worker: WorkerClient, checkpoint_id: str) -> None:
        nonlocal ownership_generation
        supervisor.set_status("CHECKPOINTING")
        ready = worker.request(
            "CHECKPOINT_PREPARE",
            active_runtime=supervisor.runtime.committed_seconds,
        )
        if ready["status"] != "CHECKPOINT_READY":
            raise RuntimeError("checkpoint_not_ready")
        supervisor.record_worker_status(ready)
        assert_quiescent(ownership_path)
        run_checkpoint(
            database,
            evidence,
            checkpoint_id,
            ownership_path=ownership_path,
        )
        supervisor.complete_checkpoint(checkpoint_id)
        resumed = worker.request(
            "RESUME", active_runtime=supervisor.runtime.committed_seconds
        )
        supervisor.record_worker_status(resumed)
        ownership_generation = int(resumed["ownership_generation"])
        supervisor.set_status("RUNNING")

    supervisor.acquire()
    supervisor.set_status("PREFLIGHT")
    try:
        client = launch()
        checkpoint(client, "C0")
        for index, event in enumerate(schedule):
            started = time.monotonic()
            supervisor.start_interval(started)
            response = client.request(
                "RUN_EVENT",
                event_index=index,
                active_runtime=supervisor.runtime.committed_seconds,
            )
            supervisor.record_worker_status(response)
            supervisor.stop_interval(time.monotonic())
            event_result = dict(response["event"])
            if event_result["event"] != event["id"]:
                raise RuntimeError("schedule_event_mismatch")
            if event_result["organism_id"] != organism_id:
                raise RuntimeError("organism_identity_changed")
            trace.append(event_result)
            supervisor.complete_event(str(event["id"]))
            if index in restarts:
                supervisor.set_status("RESTARTING")
                stopped = client.shutdown(supervisor.runtime.committed_seconds)
                supervisor.record_worker_status(stopped)
                ownership_generation = int(stopped["ownership_generation"]) + 1
                generation += 1
                client = launch()
            if index in checkpoints:
                checkpoint(client, checkpoints[index])
        stopped = client.shutdown(supervisor.runtime.committed_seconds)
        supervisor.record_worker_status(stopped)
        ownership_generation = int(stopped["ownership_generation"])
        client = None
        supervisor.set_status("COMPLETED")
        supervisor.release()
    except BaseException:
        if client is not None and identity_matches(client.pid, client.identity):
            client.force_kill()
        supervisor.set_status("FAILED_INFRASTRUCTURE")
        supervisor.release()
        raise

    owner = read_ownership(ownership_path)
    remaining = [
        pid
        for pid, identity in zip(worker_pids, worker_identities)
        if identity_matches(pid, identity)
    ]
    sockets = sorted(path.name for path in output.glob("*.sock"))
    result = {
        "dry_run": True,
        "formal": False,
        "events": len(trace),
        "restarts": len(restarts),
        "checkpoints": 5,
        "d010_enabled": False,
        "raw_payload_count": 0,
        "supervisor_pid": process_identity_pid(),
        "supervisor_process_start_identity": process_identity(process_identity_pid()),
        "worker_pids": worker_pids,
        "worker_process_start_identities": worker_identities,
        "distinct_worker_pids": all(pid != process_identity_pid() for pid in worker_pids),
        "distinct_worker_identities": all(
            identity != process_identity(process_identity_pid())
            for identity in worker_identities
        ),
        "organism_id": organism_id,
        "final_ownership_status": None if owner is None else owner["status"],
        "ownership_generation": ownership_generation,
        "remaining_worker_pids": remaining,
        "remaining_sockets": sockets,
        "active_runtime_seconds": supervisor.runtime.committed_seconds,
        "log_bounds": {
            name: (output / name).stat().st_size
            for name in ("supervisor.log", "organism-worker.log")
        },
        "trace": trace,
    }
    (output / "dry-run-result.json").write_text(json.dumps(result, sort_keys=True))
    return result


def process_identity_pid() -> int:
    # Kept local so supervisor code never imports worker-owned runtime modules.
    import os

    return os.getpid()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = args.output or Path(tempfile.mkdtemp(prefix="umbra-d012-worker-dry-"))
    print(json.dumps(run(target), sort_keys=True))
