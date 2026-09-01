"""Durable atomic evidence publication for UMBRA-AS-003O.

This helper imports no UMBRA modules. It only atomically publishes immutable
evidence records and verifies their readback hashes; it cannot enter runtime
or execute an organism.
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
    "umbra-as-003o-source-backed-continuation-r1"
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def write_bytes(name: str, data: bytes) -> str:
    if Path(name).name != name or not name.endswith((".json", ".md", ".txt")):
        raise ValueError("evidence artifact name must be a local supported filename")
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
    written = (ROOT / name).read_bytes()
    if written != data:
        raise RuntimeError("evidence readback mismatch")
    return hashlib.sha256(written).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("payload")
    parser.add_argument("--text", action="store_true")
    args = parser.parse_args()
    data = args.payload.encode("utf-8") if args.text else canonical_bytes(json.loads(args.payload))
    print(write_bytes(args.name, data))


if __name__ == "__main__":
    main()
