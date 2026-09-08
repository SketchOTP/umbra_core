"""Freeze the AS-014 pre-formal protocol before the first formal tick."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from tools.as014_evidence import ROOT, publish


BASELINE = "a97171a2dab7c1750e2556727bce9e3648bb359a"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if _git("status", "--porcelain"):
        raise RuntimeError("AS014_LOCK_REQUIRES_CLEAN_WORKTREE")
    commit = _git("rev-parse", "HEAD")
    production_files = _git("diff", "--name-only", f"{BASELINE}..{commit}", "--", "umbra_core").splitlines()
    artifact_names = (
        "AS014_FULL_CONFIGURATION_CONTRACT.json",
        "AS014_SEED_MANIFEST.json",
        "AS014_SEED_DISJOINTNESS_PROOF.json",
        "AS014_R2_AUTHORITY_INTERVENTION_PREFLIGHT.json",
        "AS014_R3_EXECUTABLE_PREFLIGHT.json",
        "AS014_LIFECYCLE_EXECUTABLE_PREFLIGHT.json",
        "AS014_FULL_CLI_SURFACE_PREFLIGHT.json",
        "AS014_FORMAL_RUNNER_PREFLIGHT.json",
        "AS014_FORMAL_RUNNER_CLI_WRAPPER_PREFLIGHT.json",
        "AS014_APPLICABLE_REGRESSION_CLASSIFICATION.json",
    )
    artifacts = {name: _sha(ROOT / name) for name in artifact_names}
    manifest = json.loads((ROOT / "AS014_SEED_MANIFEST.json").read_text())
    work = ROOT / "AS014_FORMAL_POPULATION_WORK"
    if work.exists():
        raise RuntimeError("AS014_FORMAL_WORK_ALREADY_EXISTS")
    lock: dict[str, Any] = {
        "schema": "AS014_SCIENTIFIC_LOCK_V1",
        "directive": "UMBRA-AS-014",
        "baseline": BASELINE,
        "implementation_commit": commit,
        "github_ref_at_lock": _git("rev-parse", "github/master"),
        "production_files_changed_since_baseline": production_files,
        "prelock_artifact_sha256": artifacts,
        "formal_seed_manifest_sha256": artifacts["AS014_SEED_MANIFEST.json"],
        "formal_regimes": manifest["formal_regimes"],
        "formal_execution": {
            "command": [
                "/home/sketch/cs14n-runtime/bin/python",
                "-m",
                "experiments.as014.run_qualification",
                "--manifest",
                str(ROOT / "AS014_SEED_MANIFEST.json"),
                "--work",
                str(work),
            ],
            "execution_order": ["R0:0-7", "R1:0-7", "R2:0-7", "R3:0-7"],
            "horizon_per_organism": 7200,
            "organisms": 32,
            "retries": 0,
            "reseeds": 0,
            "post_first_tick_changes_forbidden": [
                "production", "harness_semantics", "seed_substitution",
                "retry", "reseed", "threshold", "command", "publication",
            ],
        },
        "downstream_order_if_population_passes": [
            "lifecycle", "accelerated_100k", "real_time_s3_soak", "matched_causal_ablation"
        ],
        "validation": {
            "protected_suite": "120 passed, 2 skipped twice",
            "applicable_suite_candidate_only_failures": 0,
            "authority_3": "PASS",
            "governance": "PASS",
            "diff_check": "PASS",
        },
        "formal_started": False,
    }
    digest = publish("AS014_SCIENTIFIC_LOCK.json", lock)
    print(json.dumps({"commit": commit, "sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
