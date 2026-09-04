#!/usr/bin/env python3
"""Publish the zero-run AS-007 Phase-0 reconciliation atomically."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


BASELINE = "22c96dd711126d0e87f637032a7871308fede803"
ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-007-recovery-executability-integrated-viability-r1")
MANIFEST = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-006-executable-weak-continuation-integrated-viability-r1/AS006_FINAL_EVIDENCE_MANIFEST.json")


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    status = run("git", "status", "--short")
    head = run("git", "rev-parse", "HEAD")
    master = run("git", "rev-parse", "master")
    remote = run("git", "ls-remote", "github", "refs/heads/master").split()[0]
    payload = {
        "schema": "AS007_STATE_RECONCILIATION_V1",
        "directive": "UMBRA-AS-007",
        "status": "PASS" if head == master == remote == BASELINE else "AS007_START_STATE_MISMATCH",
        "baseline": BASELINE,
        "git": {"head": head, "master": master, "github_master": remote, "initial_status": status},
        "parent": {
            "verdict": "AS006_KNOWN_R1_FAIL",
            "scientific_freeze": "53117fa3cd63ce629f5fee0934e11c027ae8ae9c",
            "final_evidence_seal": "cfb0057f2ad97025563ff99dbb724b21eb0d96f2",
            "manifest_sha256": sha256(MANIFEST),
            "manifest_expected_sha256": "39ffe7ca3865e414994818bdf7afc39cf9227ca493654b2dc35a09999315428b",
        },
        "notion": {
            "page_id": "3b3833cb-27ff-8030-9f1f-e73e7af37fe6",
            "current_authority": "UMBRA-AS-007",
            "refetched_before_start": True,
        },
        "scope": {
            "production_changes_at_start": 0,
            "existing_test_semantic_changes_at_start": 0,
            "organism_creations": 0,
            "organism_loads": 0,
            "organism_ticks": 0,
            "control_runs": 0,
            "shadow_runs": 0,
            "diagnostic_runs": 0,
            "retries": 0,
            "reseeds": 0,
        },
        "evidence_root": str(ROOT),
        "retrieval_confidence": "ADEQUATE",
    }
    atomic_json(ROOT / "AS007_STATE_RECONCILIATION.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
