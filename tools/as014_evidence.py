"""Create-once durable evidence publication for UMBRA-AS-014."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-014-persistent-ledger-boundedness-completion-r1"
)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish(name: str, value: Any) -> str:
    """Publish one JSON/Markdown artifact with durable create-once semantics."""
    target = ROOT / name
    if target.name != name or not name.endswith((".json", ".md", ".txt", ".jsonl")):
        raise ValueError(f"unsupported_evidence_name:{name}")
    if target.exists():
        raise FileExistsError(f"create_once_evidence_exists:{target}")
    ROOT.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    temp = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            raise FileExistsError(f"create_once_race:{target}")
        os.replace(temp, target)
        _fsync_directory(ROOT)
        readback = target.read_bytes()
        if readback != payload:
            raise RuntimeError(f"readback_mismatch:{target}")
        return hashlib.sha256(readback).hexdigest()
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
