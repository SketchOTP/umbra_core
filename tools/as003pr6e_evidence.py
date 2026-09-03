"""Durable create-once publication for AS-003P-R6E evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6e-known-option-preservation-r1"
)


def _publish_bytes(name: str, encoded: bytes) -> str:
    destination = ROOT / name
    if destination.exists():
        raise FileExistsError(destination)
    ROOT.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary_path.unlink(missing_ok=True)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    if destination.read_bytes() != encoded:
        raise OSError(f"readback_mismatch:{destination}")
    return digest


def publish(name: str, payload: Any) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
    return _publish_bytes(name, encoded)


def publish_text(name: str, content: str) -> str:
    encoded = (content if content.endswith("\n") else content + "\n").encode()
    return _publish_bytes(name, encoded)


def capture_command(name: str, argv: list[str], *, cwd: str) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    finished = datetime.now(timezone.utc).isoformat()
    stdout_name = f"{name}.stdout"
    stderr_name = f"{name}.stderr"
    stdout_sha = publish_text(stdout_name, completed.stdout)
    stderr_sha = publish_text(stderr_name, completed.stderr)
    record = {
        "name": name,
        "argv": argv,
        "cwd": cwd,
        "started_at": started,
        "finished_at": finished,
        "exit_code": completed.returncode,
        "stdout_artifact": stdout_name,
        "stdout_sha256": stdout_sha,
        "stderr_artifact": stderr_name,
        "stderr_sha256": stderr_sha,
        "organism_creation": 0,
        "organism_load": 0,
        "organism_ticks": 0,
        "control_runs": 0,
        "shadow_runs": 0,
        "diagnostic_runs": 0,
    }
    record["record_sha256"] = publish(f"{name}.json", record)
    return record
