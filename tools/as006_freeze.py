"""Publish the AS-006 pre-freeze scientific lock and final evidence manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any


ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-006-executable-weak-continuation-integrated-viability-r1")
REPO = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: Any) -> str:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return sha(path)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def lock() -> None:
    commit = git("rev-parse", "HEAD")
    files = {
        str(path.relative_to(REPO)): sha(path)
        for path in (
            REPO / "umbra_core/hypothetical/action_selection.py",
            REPO / "umbra_core/hypothetical/continuation.py",
            REPO / "experiments/as006/qualification.py",
            REPO / "experiments/as006/observer_preflight.py",
            REPO / "tests/test_as006_weak_continuation.py",
            REPO / "experiments/as006/AS006_WEAK_CONTINUATION_CONTRACT.json",
        )
    }
    observer = ROOT / "observer-preflight/AS006_OBSERVER_PREFLIGHT_RESULT.json"
    source = ROOT / "AS006_DEVELOPMENT_SOURCE_ACTIVATION.json"
    value = {
        "schema": "AS006_SCIENTIFIC_PROTOCOL_LOCK_V1",
        "directive": "UMBRA-AS-006",
        "status": "FROZEN_BEFORE_SCIENTIFIC_SEQUENCE",
        "implementation_commit": commit,
        "working_directory": str(REPO),
        "python": "/home/sketch/cs14n-runtime/bin/python",
        "scientific_command": "/home/sketch/cs14n-runtime/bin/python -m experiments.as006.qualification --phase scientific --work <fresh-local-workdir>",
        "source_activation_command": "/home/sketch/cs14n-runtime/bin/python -m experiments.as006.qualification --phase source-activation --work <fresh-local-workdir>",
        "focused_command": "/home/sketch/cs14n-runtime/bin/python -m pytest -q tests/test_as005_modal_preventive.py tests/test_as004_continuation.py tests/test_as006_weak_continuation.py",
        "applicable_command": "/home/sketch/cs14n-runtime/bin/python -m pytest -q --ignore=tests/test_close02x_prospective_recoverability.py",
        "fixture_sequence": [
            {"stage": "DIAGNOSTIC_A", "regime": "R0", "scenario": "S0", "seed": 45878900, "horizon": 500},
            {"stage": "DIAGNOSTIC_B", "regime": "R0", "scenario": "S0", "seed": 22023239, "horizon": 3500},
            {"stage": "KNOWN_R1", "regime": "R1", "scenario": "S16", "seed": 57531938, "horizon": 7200},
        ],
        "retries": 0,
        "reseeds": 0,
        "pre_freeze_focused_runs": {"first": "17/17 PASS", "second": "17/17 PASS"},
        "pre_freeze_applicable_regression": {"passed": 1298, "skipped": 2, "inherited_failures": 13, "candidate_only_failures": 0},
        "pre_freeze_source_activation": {"artifact": str(source), "sha256": sha(source), "ticks": 500, "route_frames": 500, "nonempty_option_rows": 262},
        "pre_freeze_observer_gate": {"artifact": str(observer), "sha256": sha(observer), "control": 1, "shadow": 1, "ticks": "500/500", "semantic_differences": 0, "rng_parity": True},
        "scientific_files": files,
        "production_delta_before_scientific_lock": 2,
        "organism_executions_before_scientific_sequence": 3,
        "organism_ticks_before_scientific_sequence": 1500,
        "scientific_sequence_executions_after_lock": 0,
    }
    print(json.dumps({"path": str(ROOT / "AS006_SCIENTIFIC_PROTOCOL_LOCK.json"), "sha256": atomic_json(ROOT / "AS006_SCIENTIFIC_PROTOCOL_LOCK.json", value)}, indent=2))


def manifest() -> None:
    commit = git("rev-parse", "HEAD")
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "AS006_FINAL_EVIDENCE_MANIFEST.json":
            rows.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size})
    value = {
        "schema": "AS006_FINAL_EVIDENCE_MANIFEST_V1",
        "directive": "UMBRA-AS-006",
        "final_commit": commit,
        "verdict": "AS006_PENDING_CLOSEOUT",
        "retries": 0,
        "reseeds": 0,
        "artifacts": rows,
    }
    print(json.dumps({"path": str(ROOT / "AS006_FINAL_EVIDENCE_MANIFEST.json"), "sha256": atomic_json(ROOT / "AS006_FINAL_EVIDENCE_MANIFEST.json", value)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lock", "manifest"))
    args = parser.parse_args()
    lock() if args.mode == "lock" else manifest()
