"""Create-once durable command/evidence publication for AS-003P-R6B-R1."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6b-r1-route-control-continuity-r1"
)


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_bytes(name: str, data: bytes, *, root: Path = EVIDENCE_ROOT) -> str:
    root.mkdir(parents=True, exist_ok=True)
    target = root / name
    if target.exists():
        existing = target.read_bytes()
        if existing != data:
            raise FileExistsError(f"immutable evidence differs: {target}")
        return hashlib.sha256(existing).hexdigest()
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=root)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
        _fsync_directory(root)
    finally:
        temporary_path.unlink(missing_ok=True)
    readback = target.read_bytes()
    if readback != data:
        raise RuntimeError(f"evidence readback mismatch: {target}")
    return hashlib.sha256(readback).hexdigest()


def publish_json(name: str, value: Any, *, root: Path = EVIDENCE_ROOT) -> str:
    data = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    return publish_bytes(name, data, root=root)


def run_and_publish(
    name: str,
    argv: Sequence[str],
    *,
    cwd: Path,
    root: Path = EVIDENCE_ROOT,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    completed = subprocess.run(
        list(argv),
        cwd=str(cwd),
        capture_output=True,
        text=False,
        check=False,
    )
    ended = datetime.now(timezone.utc)
    stdout = completed.stdout
    stderr = completed.stderr
    stdout_sha = publish_bytes(f"{name}.stdout", stdout, root=root)
    stderr_sha = publish_bytes(f"{name}.stderr", stderr, root=root)
    record = {
        "schema": "AS003PR6BR1_COMMAND_RECORD_V1",
        "name": name,
        "argv": list(argv),
        "cwd": str(cwd),
        "interpreter": list(argv[:1]),
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "exit_code": completed.returncode,
        "stdout_artifact": f"{name}.stdout",
        "stdout_sha256": stdout_sha,
        "stderr_artifact": f"{name}.stderr",
        "stderr_sha256": stderr_sha,
        "environment_policy": "inherited process environment; no scientific overrides",
    }
    if extra:
        record.update(extra)
    record_sha = publish_json(f"{name}.json", record, root=root)
    record["record_sha256"] = record_sha
    return record
