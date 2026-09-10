#!/usr/bin/env python3
"""Create and read back the prospective AS-016 scientific-lock contract."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-016-regulatory-execution-recovery-requalification-r1"
)
ACCEPTED_REVIEW_SHA = "a6d7493acfe264c766e9e2af6dec2f0f8f55acc8"
SCIENTIFIC_IMPLEMENTATION_SHA = "c669bb1d9500e750f51b2d70b99d90f8f0d8f12c"
TRACKED_TREE_SHA = "a4d0e35ade97a5331be1b8a17e7c03688882151b"
LOCK_NAME = "AS016_SCIENTIFIC_LOCK_CONTRACT_V1.json"
READINESS_NAME = "AS016_PRELOCK_READINESS_V2.json"
MANIFEST_NAME = "AS016_SEED_MANIFEST.json"
DISJOINTNESS_NAME = "AS016_SEED_DISJOINTNESS_PROOF.json"
REGISTRY_NAME = "AS016_HISTORICAL_SEED_REGISTRY.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def imported_source_hashes() -> dict[str, str]:
    # Import every frozen entrypoint before reading sys.modules so the record
    # covers the actual transitive harness closure, not a partial hand list.
    import experiments.as016.downstream  # noqa: F401
    import experiments.as016.full_config  # noqa: F401
    import experiments.as016.qualification  # noqa: F401
    import experiments.as016.run_downstream  # noqa: F401
    import experiments.as016.run_qualification  # noqa: F401

    result: dict[str, str] = {}
    for module in tuple(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            continue
        if path.suffix == ".py":
            result[relative.as_posix()] = sha(path)
    return dict(sorted(result.items()))


def read_json(name: str) -> tuple[dict[str, Any], str]:
    path = EVIDENCE_ROOT / name
    if not path.is_file():
        raise RuntimeError(f"AS016_LOCK_REQUIRED_EVIDENCE_MISSING:{name}")
    return json.loads(path.read_text()), sha(path)


def verify_state() -> tuple[dict[str, Any], dict[str, str], str]:
    head = git("rev-parse", "HEAD")
    if head == ACCEPTED_REVIEW_SHA:
        publication_sha = head
    else:
        if git("rev-parse", "HEAD^") != ACCEPTED_REVIEW_SHA:
            raise RuntimeError("AS016_LOCK_PUBLICATION_PARENT_MISMATCH")
        changed = set(git("diff", "--name-only", "HEAD^", "HEAD").splitlines())
        allowed = {
            ".agent/CURRENT.md",
            ".agent/RECORD.md",
            "tools/as016_establish_scientific_lock.py",
        }
        if not changed or not changed <= allowed:
            raise RuntimeError("AS016_LOCK_PUBLICATION_SEMANTIC_DELTA")
        publication_sha = head
    if git("rev-parse", f"{ACCEPTED_REVIEW_SHA}^{{tree}}") != TRACKED_TREE_SHA:
        raise RuntimeError("AS016_LOCK_ACCEPTED_TREE_MISMATCH")
    if git("status", "--porcelain"):
        raise RuntimeError("AS016_LOCK_EXECUTION_WORKTREE_NOT_CLEAN")
    if subprocess.call(
        ["git", "diff", "--quiet", SCIENTIFIC_IMPLEMENTATION_SHA, ACCEPTED_REVIEW_SHA,
         "--", "umbra_core", "tests", "experiments/as016"], cwd=ROOT
    ) != 0:
        raise RuntimeError("AS016_LOCK_SEMANTIC_DELTA_AFTER_SCIENTIFIC_IMPLEMENTATION")

    readiness, readiness_sha = read_json(READINESS_NAME)
    manifest, manifest_sha = read_json(MANIFEST_NAME)
    disjointness, disjointness_sha = read_json(DISJOINTNESS_NAME)
    registry, registry_sha = read_json(REGISTRY_NAME)
    if readiness.get("candidate", {}).get("head") != SCIENTIFIC_IMPLEMENTATION_SHA:
        raise RuntimeError("AS016_LOCK_READINESS_IMPLEMENTATION_MISMATCH")
    if readiness.get("result") != "READY_FOR_ARCHITECT_LOCK_REVIEW":
        raise RuntimeError("AS016_LOCK_READINESS_RESULT_INVALID")
    if readiness.get("formal_seed_manifest_sha256") != manifest_sha:
        raise RuntimeError("AS016_LOCK_MANIFEST_READINESS_HASH_MISMATCH")
    if readiness.get("seed_disjointness_sha256") != disjointness_sha:
        raise RuntimeError("AS016_LOCK_DISJOINTNESS_READINESS_HASH_MISMATCH")
    if manifest.get("directive") != "UMBRA-AS-016" or manifest.get("seed_status") != "frozen_before_formal_execution":
        raise RuntimeError("AS016_LOCK_MANIFEST_CONTRACT_INVALID")
    formal = manifest.get("formal_regimes", {})
    if tuple(formal) != ("R0", "R1", "R2", "R3") or any(len(formal[name]) != 8 for name in formal):
        raise RuntimeError("AS016_LOCK_POPULATION_MANIFEST_INVALID")
    seeds = [seed for values in formal.values() for seed in values]
    seeds += list(manifest.get("downstream", {}).values())
    if len(seeds) != 36 or len(set(seeds)) != 36:
        raise RuntimeError("AS016_LOCK_SEED_UNIQUENESS_INVALID")
    if set(seeds) & set(registry.get("historical_seeds", ())):
        raise RuntimeError("AS016_LOCK_HISTORICAL_SEED_COLLISION")
    if disjointness.get("result") != "PASS" or disjointness.get("new_seed_count") != 36:
        raise RuntimeError("AS016_LOCK_DISJOINTNESS_PROOF_INVALID")
    return manifest, {
        READINESS_NAME: readiness_sha,
        MANIFEST_NAME: manifest_sha,
        DISJOINTNESS_NAME: disjointness_sha,
        REGISTRY_NAME: registry_sha,
    }, publication_sha


def contract(manifest: dict[str, Any], evidence_hashes: dict[str, str], publication_sha: str) -> dict[str, Any]:
    from experiments.as016.downstream import ACCELERATED, SOAK, VARIANTS
    from experiments.as016.full_config import config, fingerprint
    from experiments.as016.qualification import HORIZON, REGIMES, SCENARIOS

    with tempfile.TemporaryDirectory(prefix="as016-lock-config-") as directory:
        config_fingerprints = {
            regime: fingerprint(config(0, Path(directory) / f"{regime}.sqlite", regime))
            for regime in REGIMES
        }
    execution_root = EVIDENCE_ROOT / "AS016_FORMAL_POPULATION_WORK_V1"
    return {
        "schema": "AS016_SCIENTIFIC_LOCK_CONTRACT_V1",
        "directive": "UMBRA-AS-016",
        "lock_status": "ESTABLISHED_BEFORE_FORMAL_ORGANISM_CREATION",
        "scientific_implementation_sha": SCIENTIFIC_IMPLEMENTATION_SHA,
        "accepted_review_sha": ACCEPTED_REVIEW_SHA,
        "accepted_tracked_tree_sha": TRACKED_TREE_SHA,
        "lock_publication_sha": publication_sha,
        "execution_checkout": str(ROOT),
        "execution_subject": {
            "clean_detached_checkout_required": True,
            "imported_modules_resolve_under_execution_checkout": True,
            "transitive_imported_harness_source_hashes": imported_source_hashes(),
            "environment": {
                "python_executable": sys.executable,
                "python_version": sys.version,
                "platform": platform.platform(),
                "cwd": os.getcwd(),
                "pythonpath": os.environ.get("PYTHONPATH", ""),
            },
        },
        "evidence_readback_sha256": evidence_hashes,
        "seed_contract": {
            "manifest": manifest,
            "manifest_sha256": evidence_hashes[MANIFEST_NAME],
            "disjointness_sha256": evidence_hashes[DISJOINTNESS_NAME],
            "formal_seed_count": 32,
            "downstream_seed_count": 4,
            "retries": 0,
            "reseeds": 0,
            "substitutions": 0,
        },
        "population_contract": {
            "configuration_name": "AS016_FULL_CONFIGURATION",
            "configuration_fingerprints": config_fingerprints,
            "regimes": list(REGIMES),
            "scenarios": SCENARIOS,
            "organisms_per_regime": 8,
            "ticks_per_organism": HORIZON,
            "execution_mode": "reviewed_serial_runner_only",
            "command": [
                sys.executable, "-m", "experiments.as016.run_qualification",
                "--manifest", str(EVIDENCE_ROOT / MANIFEST_NAME),
                "--work", str(execution_root),
            ],
            "output_schema": "AS016_FORMAL_POPULATION_V1",
            "per_case_schema": "AS016_FORMAL_CASE_V1",
            "acceptance": {
                "all_32_complete_7200_ticks": True,
                "no_critical_physiology": True,
                "no_invalid_terminal_collapse_escape": True,
                "no_authority_bypass_or_hidden_habitat_truth": True,
                "per_case_durable_before_advance": True,
            },
        },
        "downstream_contract": {
            "lifecycle_seed": manifest["downstream"]["lifecycle"],
            "boundedness_seed": manifest["downstream"]["boundedness"],
            "soak_seed": manifest["downstream"]["soak"],
            "matched_ablation_seed": manifest["downstream"]["ablation_matched"],
            "accelerated": ACCELERATED,
            "real_time_soak": SOAK,
            "ablation_variants": list(VARIANTS),
            "orders_after_population_pass": ["lifecycle", "repeated_compaction_100k", "isolated_S3_soak", "matched_five_arm_ablation", "goal_to_evidence_assessment"],
            "output_schemas": ["AS016_LIFECYCLE_RESULT_V1", "AS016_BOUNDEDNESS_RESULT_V1", "AS016_REALTIME_SOAK_RESULT_V1", "AS016_ABLATION_RESULT_V1"],
        },
        "first_failure_stop_rule": {
            "first_frozen_scientific_or_protocol_failure_is_terminal": True,
            "after_lock_forbidden": ["repair", "retry", "reseed", "seed_substitution", "shortened_horizon", "threshold_change", "scenario_change", "execution_mode_change"],
            "downstream_gates_not_run_after_population_failure": True,
        },
        "nonsemantic_lock_publication_delta": {
            "asserted_no_delta_paths": ["umbra_core/**", "tests/**", "experiments/as016/**"],
            "scientific_implementation_to_review_diff_paths": [".agent/CURRENT.md", ".agent/RECORD.md", "tools/as016_publish_prelock_readiness.py"],
        },
    }


def main() -> None:
    manifest, evidence_hashes, publication_sha = verify_state()
    value = contract(manifest, evidence_hashes, publication_sha)
    path = EVIDENCE_ROOT / LOCK_NAME
    if path.exists():
        existing = json.loads(path.read_text())
        if existing != value:
            raise RuntimeError("AS016_LOCK_CREATE_ONCE_CONTENT_MISMATCH")
        digest = sha(path)
    else:
        from tools.as016_evidence import publish
        digest = publish(LOCK_NAME, value)
    if json.loads(path.read_text()) != value or sha(path) != digest:
        raise RuntimeError("AS016_LOCK_READBACK_INVALID")
    print(json.dumps({"lock": LOCK_NAME, "sha256": digest, "status": value["lock_status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
