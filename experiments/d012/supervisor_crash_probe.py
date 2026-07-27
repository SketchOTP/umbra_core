"""Disposable helper that proves a worker survives actual supervisor death."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .campaign_supervisor import CampaignSupervisor, freeze_hash
from .durability import atomic_write_text
from .worker_launcher import WorkerClient, manifest_for


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    execution_id = "supervisor-crash-probe"
    database = args.root / "dry-run.sqlite"
    supervisor = CampaignSupervisor(
        args.root,
        execution_id,
        database,
        args.root / "evidence",
        freeze_hash(Path(__file__).resolve().parent),
    )
    supervisor.acquire()
    manifest = manifest_for(
        args.root,
        execution_id=execution_id,
        generation=1,
        ownership_generation=1,
        freeze_manifest_hash=freeze_hash(Path(__file__).resolve().parent),
        active_runtime=0.0,
    )
    client = WorkerClient.launch(args.root / "manifest-1.json", manifest)
    supervisor.attach_worker(client.pid, client.identity, 1)
    started = client.request("START")
    supervisor.record_worker_status(started)
    record = {
        "execution_id": execution_id,
        "generation": 1,
        "socket_path": str(client.socket_path),
        "pid": client.pid,
        "identity": client.identity,
        "sequence": client.sequence,
        "active_runtime": client.active_runtime,
        "chain_tip": client.chain_tip,
    }
    path = args.root / "reattach.json"
    atomic_write_text(path, json.dumps(record, sort_keys=True))
    os._exit(73)


if __name__ == "__main__":
    main()
