"""Durable, exclusive, read-back verified publication for AS-013."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_json(path: Path, value: Any, *, schema: str) -> str:
    """Publish once, atomically, and verify the exact bytes after rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = canonical_json(value)
    payload = rendered.encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if path.exists():
        raise FileExistsError(path)
    try:
        with tmp.open("x", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise FileExistsError(path)
        os.replace(tmp, path)
        _fsync_directory(path.parent)
        readback = path.read_bytes()
        if readback != payload:
            raise IOError(f"AS013_PUBLICATION_READBACK_MISMATCH:{path}")
        decoded = json.loads(readback.decode("utf-8"))
        if decoded.get("schema") != schema:
            raise ValueError(f"AS013_PUBLICATION_SCHEMA_MISMATCH:{path}")
        if hashlib.sha256(readback).hexdigest() != digest:
            raise IOError(f"AS013_PUBLICATION_HASH_MISMATCH:{path}")
        return digest
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
