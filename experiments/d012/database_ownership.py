"""Exclusive durable ownership of a disposable organism database."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .durability import atomic_write_text, fsync_directory
from .failure_codes import SupervisionError
from .process_identity import identity_matches, process_identity


def read_ownership(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SupervisionError("OWNERSHIP_TRANSFER_INCOMPLETE", str(exc)) from exc
    if not isinstance(value, dict) or value.get("status") not in {"ACTIVE", "RELEASED"}:
        raise SupervisionError("OWNERSHIP_TRANSFER_INCOMPLETE")
    return value


def acquire_ownership(
    path: Path,
    *,
    execution_id: str,
    database_path: Path,
    supervisor_execution_id: str,
    generation: int,
    reclaim_dead: bool = False,
) -> dict[str, Any]:
    old = read_ownership(path)
    if old:
        if old["execution_id"] != execution_id or old["database_path"] != str(database_path):
            raise SupervisionError("DATABASE_EXECUTION_CONFLICT")
        if generation <= int(old["ownership_generation"]):
            raise SupervisionError("OWNERSHIP_GENERATION_CONFLICT")
        if old["status"] == "ACTIVE":
            alive = identity_matches(int(old["worker_pid"]), str(old["worker_process_start_identity"]))
            if alive:
                raise SupervisionError("DATABASE_ALREADY_OWNED")
            if not reclaim_dead:
                raise SupervisionError("OWNERSHIP_TRANSFER_INCOMPLETE")
            stale = path.with_suffix(path.suffix + f".stale.{int(time.time_ns())}")
            os.replace(path, stale)
        else:
            released = path.with_suffix(
                path.suffix + f".released.{old['ownership_generation']}"
            )
            os.replace(path, released)
    pid = os.getpid()
    record = {
        "execution_id": execution_id,
        "database_path": str(database_path),
        "worker_pid": pid,
        "worker_process_start_identity": process_identity(pid),
        "supervisor_execution_id": supervisor_execution_id,
        "acquired_at": time.time(),
        "ownership_generation": generation,
        "status": "ACTIVE",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(record, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(path.parent)
    return record


def release_ownership(path: Path, record: dict[str, Any]) -> None:
    current = read_ownership(path)
    if not current or current != record:
        raise SupervisionError("OWNERSHIP_TRANSFER_INCOMPLETE")
    released = {**record, "status": "RELEASED", "released_at": time.time()}
    atomic_write_text(path, json.dumps(released, sort_keys=True))


def assert_quiescent(path: Path) -> None:
    record = read_ownership(path)
    if record and record["status"] == "ACTIVE":
        raise SupervisionError("CHECKPOINT_NOT_QUIESCENT")
