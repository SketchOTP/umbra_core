#!/usr/bin/env python3
"""Create-once durable evidence publication for UMBRA-AS-003P-R6."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6-l2-schedulability-attribution-r1"
)


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode() + b"\n"


def publish(name: str, data: bytes) -> str:
    if Path(name).name != name or not name.endswith((".json", ".md", ".txt", ".jsonl")):
        raise ValueError("unsupported evidence artifact name")
    ROOT.mkdir(parents=True, exist_ok=True)
    destination = ROOT / name
    if destination.exists():
        raise FileExistsError(f"AS003P-R6 create-once evidence exists: {destination}")
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    readback = destination.read_bytes()
    if readback != data:
        raise RuntimeError("evidence readback mismatch")
    return hashlib.sha256(readback).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--text", action="store_true")
    args = parser.parse_args()
    raw = sys.stdin.buffer.read()
    data = raw if args.text else canonical_json(json.loads(raw))
    print(publish(args.name, data))


if __name__ == "__main__":
    main()
