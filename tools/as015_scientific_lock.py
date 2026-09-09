#!/usr/bin/env python3
"""Create the one-shot AS-015 scientific-lock record before formal ticks."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from experiments.as014.downstream import ACCELERATED, SOAK
from experiments.as015.downstream import VARIANTS
from experiments.as015.full_config import config, fingerprint
from tools.as015_evidence import ROOT, publish


SCIENTIFIC_IMPLEMENTATION_SHA = "76182fca517b69ee6b9eef6c9ec9d44efa520d49"
SEALED_PREDECESSOR_SHA = "b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7"
FORMAL_WORK = ROOT / "AS015_FORMAL_POPULATION_WORK_V1"
ARTIFACTS = (
    "AS015_PRELOCK_READINESS_V2.json",
    "AS015_D003_VERIFIED_DENIAL_CURRENT_AUTHORITY_PASS.json",
    "AS015_VERIFIED_DENIAL_VALIDATION.json",
    "AS015_PREFLIGHT_DENIAL_REVALIDATION_RESULT.json",
    "AS015_FULL_CLI_SURFACE_PREFLIGHT_V2.json",
    "AS015_SEED_MANIFEST.json",
    "AS015_SEED_DISJOINTNESS_PROOF.json",
    "AS015_COMPLETE_SUITE_INHERITED_EXCLUSIONS.json",
)
PRODUCTION_FILES = (
    "umbra_core/arbitration.py",
    "umbra_core/events.py",
    "umbra_core/persistence.py",
    "umbra_core/recoverability/__init__.py",
    "umbra_core/recoverability/viability.py",
    "umbra_core/runtime.py",
    "umbra_core/world_model/__init__.py",
    "umbra_core/world_model/engine.py",
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPOSITORY, text=True).strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _configuration_fingerprints(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="as015-lock-config-") as directory:
        root = Path(directory)
        for regime, seeds in manifest["formal_regimes"].items():
            value = fingerprint(config(int(seeds[0]), root / f"{regime}.sqlite", regime))
            rows[regime] = {"fingerprint": value, "sha256": _canonical_sha(value)}
    return rows


def main() -> None:
    if _git("status", "--porcelain"):
        raise RuntimeError("AS015_LOCK_REQUIRES_CLEAN_WORKTREE")
    if _git("rev-parse", f"{SCIENTIFIC_IMPLEMENTATION_SHA}^") != SEALED_PREDECESSOR_SHA:
        raise RuntimeError("AS015_ACCEPTED_CANDIDATE_PARENT_MISMATCH")
    if _git("diff", "--name-only", SCIENTIFIC_IMPLEMENTATION_SHA, "HEAD", "--", "umbra_core"):
        raise RuntimeError("AS015_LOCK_PUBLICATION_HAS_PRODUCTION_DELTA")
    if _git("rev-parse", "github/master") != _git("rev-parse", "HEAD"):
        raise RuntimeError("AS015_LOCK_GITHUB_REF_MISMATCH")
    if FORMAL_WORK.exists():
        raise RuntimeError("AS015_FORMAL_WORK_ALREADY_EXISTS")

    artifacts = {name: _sha(ROOT / name) for name in ARTIFACTS}
    readiness = json.loads((ROOT / "AS015_PRELOCK_READINESS_V2.json").read_text())
    if readiness.get("result") != "READY_FOR_ARCHITECT_LOCK_REVIEW":
        raise RuntimeError("AS015_PRELOCK_READINESS_NOT_APPROVED")
    if readiness.get("preflight", {}).get("formal_seed_consumed"):
        raise RuntimeError("AS015_FORMAL_SEED_ALREADY_CONSUMED")
    manifest = json.loads((ROOT / "AS015_SEED_MANIFEST.json").read_text())
    disjointness = json.loads((ROOT / "AS015_SEED_DISJOINTNESS_PROOF.json").read_text())
    if manifest.get("seed_status") != "frozen_before_formal_execution" or disjointness.get("result") != "PASS":
        raise RuntimeError("AS015_FORMAL_SEED_CONTRACT_INVALID")

    head = _git("rev-parse", "HEAD")
    lock = {
        "schema": "AS015_SCIENTIFIC_LOCK_V1",
        "directive": "UMBRA-AS-015",
        "scientific_implementation_sha": SCIENTIFIC_IMPLEMENTATION_SHA,
        "sealed_predecessor_sha": SEALED_PREDECESSOR_SHA,
        "governance_publication_sha": head,
        "github_ref_at_lock": _git("rev-parse", "github/master"),
        "production_semantic_delta_since_scientific_implementation": [],
        "production_fingerprints": {name: _sha(REPOSITORY / name) for name in PRODUCTION_FILES},
        "configuration_fingerprints": _configuration_fingerprints(manifest),
        "viability_kernel_fingerprint": _canonical_sha({
            name: _sha(REPOSITORY / name)
            for name in ("umbra_core/recoverability/viability.py", "umbra_core/arbitration.py")
        }),
        "verified_denial_learning_fingerprint": _canonical_sha({
            name: _sha(REPOSITORY / name)
            for name in ("umbra_core/runtime.py", "umbra_core/world_model/engine.py", "umbra_core/events.py")
        }),
        "persistence_checkpoint_contract": {
            "fingerprint": _canonical_sha({"source": _sha(REPOSITORY / "experiments/as014/full_config.py")}),
            "hot_tail_event_max": 32768,
            "checkpoint_keep": 4,
            "physical_reclaim": True,
        },
        "prelock_artifact_sha256": artifacts,
        "formal_seed_manifest": {
            "filename": "AS015_SEED_MANIFEST.json",
            "sha256": artifacts["AS015_SEED_MANIFEST.json"],
            "formal_regimes": manifest["formal_regimes"],
            "disjointness_proof_sha256": artifacts["AS015_SEED_DISJOINTNESS_PROOF.json"],
            "unused_at_lock": True,
        },
        "formal_population": {
            "configuration": "AS015_FULL_CONFIGURATION",
            "work": str(FORMAL_WORK),
            "command": [
                "/home/sketch/cs14n-runtime/bin/python", "-m", "experiments.as015.run_qualification",
                "--manifest", str(ROOT / "AS015_SEED_MANIFEST.json"), "--work", str(FORMAL_WORK),
            ],
            "regimes": {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"},
            "execution_order": ["R0:0-7", "R1:0-7", "R2:0-7", "R3:0-7"],
            "organisms": 32,
            "ticks_per_organism": 7200,
            "retries": 0,
            "reseeds": 0,
            "substitutions": 0,
            "failure_publication": "AS015_FORMAL_POPULATION_FAILURE_V1.json",
            "success_publication": "AS015_FORMAL_POPULATION_RESULT_V1.json",
        },
        "downstream_if_population_passes": {
            "order": ["lifecycle", "accelerated_100k", "real_time_s3", "five_arm_matched_ablation", "close_03"],
            "lifecycle_seed": manifest["downstream"]["lifecycle"],
            "boundedness_seed": manifest["downstream"]["boundedness"],
            "soak_seed": manifest["downstream"]["soak"],
            "ablation_seed": manifest["downstream"]["ablation_matched"],
            "accelerated_contract": ACCELERATED,
            "s3_contract": SOAK,
            "ablation_variants": VARIANTS,
        },
        "evidence_schema": {
            "case": "AS015_FORMAL_CASE_V1",
            "population": "AS015_FORMAL_POPULATION_V1",
            "durable_case_checkpoint": True,
            "create_once_publication": True,
        },
        "first_failure_stop_rule": {
            "terminal": True,
            "forbidden_after_first_formal_tick": [
                "production_change", "test_threshold_change", "configuration_change", "seed_substitution",
                "retry", "reseed", "scenario_change", "acceptance_rule_change", "publication_repair",
            ],
        },
        "formal_started": False,
    }
    digest = publish("AS015_SCIENTIFIC_LOCK_V1.json", lock)
    print(json.dumps({"governance_publication_sha": head, "lock_sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
