#!/usr/bin/env python3
"""Publish AS-016 validation accounting without establishing scientific lock."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.as016_evidence import ROOT as EVIDENCE_ROOT
from tools.as016_evidence import publish


BASELINE = "17859e03143b2278e612efeb3e96684f830b741f"
INHERITED_NODES = (
    "tests/test_d012.py::test_disposable_real_runtime_dry_run_and_process_audit",
    "tests/test_d012_process_boundary.py::test_full_distinct_process_campaign",
    "tests/test_d013ab_multineed_corridor.py::test_active_fatigue_recovery_uses_corridor_adjudication_once",
    "tests/test_d013ab_multineed_corridor.py::test_integrity_and_stimulation_candidates_share_the_boundary",
    "tests/test_d013ak_authority_reachability.py::test_default_13035_authority_retains_charge_without_changing_score",
    "tests/test_d013h_v2_formal_readiness.py::test_real_perception_path_detects_material_resource_change",
    "tests/test_d013y_integrated.py::test_cold_start_discovery_uses_physical_action_and_real_observation",
)
ARTIFACTS = (
    "AS016_R0_41616031_FAILURE_ATTRIBUTION_V1.json",
    "AS016_R0_41616031_DIRECT_PATH_DEVELOPMENT_V1.json",
    "AS016_POST_DIRECT_PATH_R1_R3_REVALIDATION_V1.json",
    "AS016_FULL_CLI_SURFACE_PREFLIGHT_V2.json",
    "AS016_FORMAL_POPULATION_CLI_PREFLIGHT_V1.json",
    "AS016_PREFLIGHT_POPULATION_CLI_V1_RESULT.json",
    "AS016_HISTORICAL_SEED_REGISTRY.json",
    "AS016_SEED_MANIFEST.json",
    "AS016_SEED_DISJOINTNESS_PROOF.json",
)
SOURCE_PATHS = (
    "umbra_core/arbitration.py",
    "umbra_core/embodiment.py",
    "umbra_core/physiology.py",
    "umbra_core/recoverability/__init__.py",
    "umbra_core/recoverability/contracts.py",
    "umbra_core/recoverability/viability.py",
    "experiments/as016/full_config.py",
    "experiments/as016/qualification.py",
    "experiments/as016/run_qualification.py",
    "experiments/as016/downstream.py",
    "experiments/as016/run_downstream.py",
    "experiments/as016/preflight_cli.py",
    "tools/as016_evidence.py",
    "tools/as016_seed_manifest.py",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    missing = [name for name in ARTIFACTS if not (EVIDENCE_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"AS016_PRELOCK_REQUIRED_ARTIFACTS_MISSING:{missing}")
    complete = {
        "schema": "AS016_COMPLETE_SUITE_INHERITED_EXCLUSIONS_V1",
        "directive": "UMBRA-AS-016",
        "candidate_command": "python -m pytest -q --ignore=tests/test_close02x_prospective_recoverability.py",
        "candidate": {"passed": 1365, "skipped": 4, "failed": 7},
        "baseline": BASELINE,
        "baseline_exact_node_result": {"passed": 0, "failed": 7},
        "inherited_nodes": list(INHERITED_NODES),
        "candidate_only_failures": 0,
        "orphan_collection_debt": "tests/test_close02x_prospective_recoverability.py imports an absent baseline symbol; raw collection fails at baseline and candidate",
    }
    complete_sha = publish("AS016_COMPLETE_SUITE_INHERITED_EXCLUSIONS_V1.json", complete)
    evidence_hashes = {name: _sha(EVIDENCE_ROOT / name) for name in ARTIFACTS}
    readiness = {
        "schema": "AS016_PRELOCK_READINESS_V1",
        "directive": "UMBRA-AS-016",
        "baseline": BASELINE,
        "candidate": {
            "head": _git("rev-parse", "HEAD"),
            "source_hashes": {path: _sha(ROOT / path) for path in SOURCE_PATHS},
            "production_paths_changed": [
                "umbra_core/arbitration.py", "umbra_core/embodiment.py", "umbra_core/physiology.py",
                "umbra_core/recoverability/__init__.py", "umbra_core/recoverability/contracts.py",
                "umbra_core/recoverability/viability.py",
            ],
        },
        "validation": {
            "focused_recovery_persistence_body": "90 passed twice",
            "execution_contract": "20 passed",
            "applicable_suite": "1365 passed, 4 skipped, 7 exact-baseline inherited failures",
            "candidate_only_failures": 0,
            "authority_3_0": "PASS",
            "governance": "PASS",
            "git_diff_check": "PASS",
        },
        "development_revalidation": {
            "R0": "4000/4000, no NO_SAFE_ACTION, all physiology noncritical",
            "R1_R3": "each 4000/4000; R2 restart/social authority and R3 body transition passed",
            "formal_seeds_used": [],
        },
        "preflight": {
            "downstream_cli": "8/8 PASS with publication/readback",
            "population_cli": "4/4 development cases with durable result records",
            "formal_seed_consumed": False,
            "scientific_lock_established": False,
        },
        "artifacts": evidence_hashes | {"AS016_COMPLETE_SUITE_INHERITED_EXCLUSIONS_V1.json": complete_sha},
        "formal_seed_manifest_sha256": evidence_hashes["AS016_SEED_MANIFEST.json"],
        "seed_disjointness_sha256": evidence_hashes["AS016_SEED_DISJOINTNESS_PROOF.json"],
        "result": "READY_FOR_ARCHITECT_LOCK_REVIEW",
    }
    print(publish("AS016_PRELOCK_READINESS_V1.json", readiness))


if __name__ == "__main__":
    main()
