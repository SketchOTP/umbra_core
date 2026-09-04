#!/usr/bin/env python3
"""Publish the immutable AS-007 scientific execution protocol lock."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-007-recovery-executability-integrated-viability-r1"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def publish(path: Path, value: dict) -> str:
    if path.exists():
        raise FileExistsError(path)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return sha(path)


def main() -> None:
    harness = ROOT / "experiments/as007/qualification.py"
    contract = ROOT / "experiments/as007/AS007_EXECUTABILITY_CONTRACT.json"
    result = {
        "schema": "AS007_EXECUTION_PROTOCOL_LOCK_V1",
        "directive": "UMBRA-AS-007",
        "commit": git("rev-parse", "HEAD"),
        "working_directory": str(ROOT),
        "interpreter": "/home/sketch/cs14n-runtime/bin/python",
        "command": "/home/sketch/cs14n-runtime/bin/python -m experiments.as007.qualification --phase scientific --work /tmp/as007-scientific-work",
        "evidence_root": str(EVIDENCE),
        "fixture": {
            "diagnostic_a": {"regime": "R0", "seed": 45878900, "horizon": 500},
            "diagnostic_b": {"regime": "R0", "seed": 22023239, "horizon": 3500},
            "known_r1": {"regime": "R1", "scenario": "S16", "seed": 57531938, "horizon": 7200},
        },
        "harness_sha256": sha(harness),
        "contract_sha256": sha(contract),
        "scientific_source_sha256": {
            "umbra_core/arbitration.py": sha(ROOT / "umbra_core/arbitration.py"),
            "umbra_core/embodiment.py": sha(ROOT / "umbra_core/embodiment.py"),
            "umbra_core/recoverability/contracts.py": sha(ROOT / "umbra_core/recoverability/contracts.py"),
            "umbra_core/runtime.py": sha(ROOT / "umbra_core/runtime.py"),
        },
        "execution_policy": {
            "one_sequence": True,
            "stop_on_first_nonpass": True,
            "retries": 0,
            "reseeds": 0,
            "no_post_lock_code_changes": True,
            "no_downstream_population_before_r1_pass": True,
        },
    }
    result["artifact_sha256"] = publish(EVIDENCE / "AS007_EXECUTION_PROTOCOL_LOCK.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
