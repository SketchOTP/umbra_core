"""Durable, create-once publication for the AS-003P-R6C evidence root."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6c-route-affordance-frame-r1")


def publish(name: str, payload: Any) -> str:
    """Atomically create one JSON artifact and verify its readback digest."""
    destination = ROOT / name
    if destination.exists():
        raise FileExistsError(destination)
    ROOT.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
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
    if destination.read_text(encoding="utf-8") != encoded:
        raise OSError(f"readback_mismatch:{destination}")
    return digest
