"""Durable create-once publication used by every AS-014 scientific CLI."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_json(path: Path, value: Any, *, schema: str) -> str:
    """Atomically publish exactly once, then parse and hash its readback."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise FileExistsError(path)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
        readback = path.read_bytes()
        decoded = json.loads(readback.decode("utf-8"))
        if readback != payload or decoded.get("schema") != schema:
            raise RuntimeError(f"AS014_PUBLICATION_READBACK_INVALID:{path}")
        if hashlib.sha256(readback).hexdigest() != digest:
            raise RuntimeError(f"AS014_PUBLICATION_HASH_MISMATCH:{path}")
        return digest
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
