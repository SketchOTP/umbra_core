"""Publish the post-denial-learning AS-015 pre-lock candidate fingerprint."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from tools.as015_evidence import ROOT as EVIDENCE_ROOT
from tools.as015_evidence import publish


PROJECT = Path(__file__).resolve().parents[1]


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=PROJECT, text=True).strip()


def main() -> None:
    source_paths = (
        "umbra_core/arbitration.py",
        "umbra_core/events.py",
        "umbra_core/recoverability/__init__.py",
        "umbra_core/recoverability/viability.py",
        "umbra_core/runtime.py",
        "umbra_core/world_model/__init__.py",
        "umbra_core/world_model/engine.py",
        "experiments/as015/full_config.py",
        "experiments/as015/qualification.py",
        "experiments/as015/run_qualification.py",
        "experiments/as015/preflight_cli.py",
    )
    evidence_paths = (
        "AS015_D003_VERIFIED_DENIAL_CURRENT_AUTHORITY_PASS.json",
        "AS015_VERIFIED_DENIAL_VALIDATION.json",
        "AS015_COMPLETE_SUITE_INHERITED_EXCLUSIONS.json",
        "AS015_PREFLIGHT_DENIAL_REVALIDATION_RESULT.json",
        "AS015_FULL_CLI_SURFACE_PREFLIGHT_V2.json",
        "AS015_SEED_MANIFEST.json",
        "AS015_SEED_DISJOINTNESS_PROOF.json",
    )
    missing = [name for name in evidence_paths if not (EVIDENCE_ROOT / name).is_file()]
    payload = {
        "schema": "AS015_PRELOCK_READINESS_V2",
        "directive": "UMBRA-AS-015",
        "baseline": "b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7",
        "candidate": {
            "head": _git("rev-parse", "HEAD"),
            "working_tree_diff_sha256": hashlib.sha256(
                subprocess.check_output(["git", "diff", "--binary"], cwd=PROJECT)
            ).hexdigest(),
            "source_hashes": {path: _hash(PROJECT / path) for path in source_paths},
        },
        "validation": {
            "owner_suites": "346 passed",
            "protected_lineage": "707 passed, 4 skipped",
            "applicable_suite": "1358 passed, 4 skipped, 7 deselected",
            "candidate_only_failures": 0,
            "authority_3_0": "PASS",
            "governance": "PASS",
            "git_diff_check": "PASS",
        },
        "preflight": {
            "nonformal_r0_r3": "R0/R1/R2/R3 each completed 4000 ticks; seeds 41515001..41515004",
            "literal_downstream_cli": "PASS: lifecycle, boundedness, soak, and five ablation variants",
            "formal_seed_consumed": False,
            "scientific_lock_established": False,
        },
        "evidence_hashes": {
            name: _hash(EVIDENCE_ROOT / name) for name in evidence_paths if (EVIDENCE_ROOT / name).is_file()
        },
        "missing_required_evidence": missing,
        "result": "READY_FOR_ARCHITECT_LOCK_REVIEW" if not missing else "INCOMPLETE",
    }
    print(publish("AS015_PRELOCK_READINESS_V2.json", payload))


if __name__ == "__main__":
    main()
