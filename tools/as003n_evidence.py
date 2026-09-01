"""Durable evidence writer for UMBRA-AS-003N.

This helper deliberately imports no UMBRA modules.  It atomically writes the
JSON records that describe the governed substrate implementation; it cannot
construct an organism or invoke live runtime behavior.
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
    "umbra-as-003n-hypothetical-transition-substrate-r1"
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def write_json(name: str, payload: object) -> str:
    if Path(name).name != name or not name.endswith(".json"):
        raise ValueError("evidence artifact name must be a local .json filename")
    ROOT.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(payload)
    fd, temp_name = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, ROOT / name)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    written = (ROOT / name).read_bytes()
    if written != data:
        raise RuntimeError("readback mismatch")
    return hashlib.sha256(written).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("payload")
    args = parser.parse_args()
    print(write_json(args.name, json.loads(args.payload)))


if __name__ == "__main__":
    main()
