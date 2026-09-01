"""Durable atomic evidence publication for UMBRA-AS-003P.

This module has no UMBRA imports. It writes caller-supplied JSON or text using
file fsync, atomic rename, directory fsync, and readback SHA-256 verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-modal-planning-frame-r1"
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def publish(name: str, data: bytes) -> str:
    if Path(name).name != name or not name.endswith((".json", ".md", ".txt")):
        raise ValueError("unsupported evidence artifact name")
    ROOT.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, ROOT / name)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    readback = (ROOT / name).read_bytes()
    if readback != data:
        raise RuntimeError("evidence readback mismatch")
    return hashlib.sha256(readback).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("payload")
    parser.add_argument("--text", action="store_true")
    args = parser.parse_args()
    data = args.payload.encode() if args.text else canonical_bytes(json.loads(args.payload))
    print(publish(args.name, data))


if __name__ == "__main__":
    main()
