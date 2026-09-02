"""Durable evidence publication helpers for UMBRA-AS-003P-R6B.

This module intentionally imports no UMBRA runtime code. It provides create-once
JSON/text publication with file fsync, atomic replacement, directory fsync, and
readback SHA-256 verification for the R6B evidence ledger.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6b-verified-route-learning-r1"
)


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_bytes(name: str, data: bytes, *, root: Path = EVIDENCE_ROOT) -> str:
    """Publish one immutable artifact and return its verified SHA-256."""

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
