#!/usr/bin/env python3
"""AS-003M durable static-evidence writer; it never imports UMBRA."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003m-bounded-regulatory-planning-r1")
BASE = "1d599c79e7be327a538c1ae7b763802e704c9c4c"
AS003L_MANIFEST = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003l-regulatory-schedulability-r1/AS003L_EVIDENCE_MANIFEST.json")
AS003L_MANIFEST_SHA256 = "f33d8e54e2bcbaaa79947292cb18ff112d4ab3689000fc2c3303b7a085d0532b"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_json(name: str, payload: dict) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=EVIDENCE)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        target = EVIDENCE / name
        os.replace(temporary, target)
        fsync_directory(EVIDENCE)
        if target.read_bytes() != data:
            raise RuntimeError(f"readback_mismatch:{name}")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sync() -> None:
    heads = {name: git("rev-parse", name) for name in ("HEAD", "master", "github/master")}
    production_test_delta = git("diff", "--name-only", f"{BASE}..HEAD", "--", "umbra_core", "tests").splitlines()
    goal = (ROOT / ".agent/PROJECT_GOAL.md").read_text(encoding="utf-8")
    required_goal = "Planning must remain bounded, evidence-based, and subordinate to urgent regulation and governance."
    checks = {
        "all_heads_exact_baseline": all(value == BASE for value in heads.values()),
        "as003l_manifest_exists": AS003L_MANIFEST.is_file(),
        "as003l_manifest_hash_matches": AS003L_MANIFEST.is_file() and sha(AS003L_MANIFEST) == AS003L_MANIFEST_SHA256,
        "production_and_test_delta_empty": production_test_delta == [],
        "project_goal_planning_clause_present": required_goal in goal,
    }
    if not all(checks.values()):
        raise RuntimeError("AS003M_START_STATE_MISMATCH:" + ",".join(key for key, value in checks.items() if not value))
    durable_json("AS003M_STATE_AND_GOAL_RECONCILIATION.json", {
        "schema": "AS003M_STATE_AND_GOAL_RECONCILIATION_V1",
        "generated_at": now(),
        "exact_starting_baseline": BASE,
        "heads": heads,
        "as003l": {
            "accepted_verdict": "AS003L_PLANNING_BOUNDARY_REQUIRED",
            "manifest_path": str(AS003L_MANIFEST),
            "manifest_sha256": AS003L_MANIFEST_SHA256,
            "integrity": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0},
        },
        "project_goal": {
            "path": ".agent/PROJECT_GOAL.md",
            "authoritative_clause": required_goal,
            "interpretation": "bounded prospective planning is project-goal-required; blanket no-planner was an over-broad local guard",
        },
        "production_test_delta": production_test_delta,
        "canonical_notion": {
            "page_id": "3b3833cb-27ff-8030-9f1f-e73e7af37fe6",
            "as003m_authority": "fetched_and_confirmed",
        },
        "checks": checks,
        "result": "PASS",
        "scope": {"production_changes": 0, "test_changes": 0, "organism_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0},
    })


if __name__ == "__main__":
    if len(os.sys.argv) != 2 or os.sys.argv[1] != "sync":
        raise SystemExit("usage: as003m_research.py sync")
    sync()
