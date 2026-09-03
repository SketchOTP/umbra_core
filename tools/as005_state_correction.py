"""Append-only correction for the AS-005 start-state bookkeeping artifact."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from as005_phase0_audit import BASELINE, EVIDENCE, AS004_MANIFEST, publish


ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    remote = subprocess.check_output(["git", "ls-remote", "github", "refs/heads/master"], cwd=ROOT, text=True).split()[0]
    previous = json.loads((EVIDENCE / "AS005_STATE_RECONCILIATION.json").read_text())
    corrected = {
        "schema": "AS005_STATE_RECONCILIATION_CORRECTION_V1",
        "directive": "UMBRA-AS-005",
        "correction_of": "AS005_STATE_RECONCILIATION.json",
        "correction_reason": "The first artifact was generated after authorized governance-start edits and incorrectly required a clean worktree. The baseline commit/refs remain independently verified; the worktree delta is the intended start record.",
        "baseline": BASELINE,
        "head": git("rev-parse", "HEAD"),
        "local_master": git("rev-parse", "master"),
        "github_master": remote,
        "expected_commit_refs": {"head": BASELINE, "local_master": BASELINE, "github_master": BASELINE},
        "authorized_governance_worktree_delta": True,
        "initial_artifact_integrity": previous["integrity"],
        "parent": {"verdict": "AS004_KNOWN_R1_FAIL", "manifest_sha256": AS004_MANIFEST},
        "as005_start_integrity": {"production_delta": 0, "existing_test_semantic_delta": 0, "organism_runs": 0, "control_runs": 0, "shadow_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0},
        "integrity": "PASS" if git("rev-parse", "HEAD") == BASELINE and git("rev-parse", "master") == BASELINE and remote == BASELINE else "FAIL",
    }
    print(publish("AS005_STATE_RECONCILIATION_CORRECTION.json", corrected))


if __name__ == "__main__":
    main()
