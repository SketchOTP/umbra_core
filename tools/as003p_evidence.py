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
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


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
    parser.add_argument("payload", nargs="?")
    parser.add_argument("--text", action="store_true")
    parser.add_argument("--capture-pure", action="store_true")
    args = parser.parse_args()
    if args.capture_pure:
        command = (sys.executable, "tools/as003p_pure_tests.py")
        started = datetime.now(timezone.utc).isoformat()
        completed = subprocess.run(
            command,
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        ended = datetime.now(timezone.utc).isoformat()
        passes = [line.removeprefix("PASS ") for line in completed.stdout.splitlines() if line.startswith("PASS ")]
        record = {
            "schema": "AS003P_PURE_EXECUTION_RECORD_V1",
            "command": list(command),
            "working_directory": str(Path(__file__).resolve().parents[1]),
            "start_utc": started,
            "end_utc": ended,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "passing_tests": passes,
            "passing_test_count": len(passes),
            "organism_runs": 0,
            "rng_consumed": 0,
            "owner_mutations": 0,
        }
        digest = publish(args.name, canonical_bytes(record))
        print(json.dumps({"sha256": digest, "exit_code": completed.returncode, "tests": len(passes)}, sort_keys=True))
        raise SystemExit(completed.returncode)
    if args.payload is None:
        parser.error("payload is required unless --capture-pure is used")
    data = args.payload.encode() if args.text else canonical_bytes(json.loads(args.payload))
    print(publish(args.name, data))


if __name__ == "__main__":
    main()
