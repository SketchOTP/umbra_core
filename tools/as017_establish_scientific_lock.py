#!/usr/bin/env python3
"""Build and read back the AS-017 scientific lock without creating an organism."""
from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORGANISM_IMPLEMENTATION_SHA = "11795badd4b43126d62dfe6e15193cf2a0a170ac"
DEVELOPMENT_PUBLICATION_SHA = "2d619b8f4ccf1e7d97b724034227d324bcc8a255"
MASTER_SHA = "fd8c50e1134d7d2ef54e20148ac9b7880e63708d"
MANIFEST_PATH = ROOT / "experiments/as017/AS017_FORMAL_SEED_MANIFEST_V1.json"
DISJOINTNESS_PATH = ROOT / "experiments/as017/AS017_FORMAL_SEED_DISJOINTNESS_V1.json"
LOCK_PATH = ROOT / "experiments/as017/AS017_SCIENTIFIC_LOCK_CONTRACT_V1.json"
REGIMES = ("R0", "R1", "R2", "R3")
SCENARIOS = {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def canonical_sha(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def source_hashes() -> dict[str, str]:
    paths = [
        "experiments/as017/qualification.py",
        "experiments/as017/development.py",
        "experiments/as016/full_config.py",
        "experiments/as016/downstream.py",
        "experiments/as014/qualification.py",
        "experiments/as015/full_config.py",
        "experiments/as015/downstream.py",
        "tools/as017_evidence.py",
        "tools/as017_validate_linkage_v2.py",
        "tools/as017_validate_v8c.py",
        "tools/as017_run_formal.py",
        "tools/as017_establish_scientific_lock.py",
    ]
    return {path: sha256(ROOT / path) for path in paths}


def production_subtree_sha() -> str:
    return git("rev-parse", f"{ORGANISM_IMPLEMENTATION_SHA}:umbra_core")


def configuration_contract() -> dict[str, Any]:
    from experiments.as016.full_config import config, fingerprint
    from experiments.as014.qualification import HORIZON

    with tempfile.TemporaryDirectory(prefix="as017-lock-config-") as directory:
        values = {
            regime: fingerprint(config(0, Path(directory) / f"{regime}.sqlite", regime))
            for regime in REGIMES
        }
    return {
        "name": "AS016_FULL_CONFIGURATION_AS017_LOCKED",
        "seed_binding": "manifest_seed_per_case",
        "database_binding": "isolated_local_runtime_path_per_case",
        "regimes": list(REGIMES),
        "scenarios": SCENARIOS,
        "ticks_per_organism": HORIZON,
        "fingerprints": values,
        "fingerprint_sha256": {regime: canonical_sha(value) for regime, value in values.items()},
    }


def environment_contract() -> dict[str, Any]:
    freeze = subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze"], cwd=ROOT, text=True
    ).encode()
    return {
        "python_executable": sys.executable,
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "cwd_at_lock_creation": os.getcwd(),
        "pythonpath": os.environ.get("PYTHONPATH", ""),
        "pip_freeze_sha256": hashlib.sha256(freeze).hexdigest(),
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build(execution_commit: str) -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)
    disjointness = load_json(DISJOINTNESS_PATH)
    if manifest.get("organism_implementation_sha") != ORGANISM_IMPLEMENTATION_SHA:
        raise RuntimeError("AS017_LOCK_MANIFEST_ORGANISM_MISMATCH")
    if manifest.get("seed_status") != "frozen_before_formal_execution":
        raise RuntimeError("AS017_LOCK_MANIFEST_NOT_FROZEN")
    if disjointness.get("result") != "PASS":
        raise RuntimeError("AS017_LOCK_DISJOINTNESS_NOT_PASS")
    formal = manifest.get("formal_regimes", {})
    seeds = [seed for regime in REGIMES for seed in formal.get(regime, [])]
    if len(seeds) != 32 or len(set(seeds)) != 32:
        raise RuntimeError("AS017_LOCK_FORMAL_SEED_CONTRACT_INVALID")
    return {
        "schema": "AS017_SCIENTIFIC_LOCK_CONTRACT_V1",
        "directive": "UMBRA-AS-017",
        "lock_status": "ESTABLISHED_BEFORE_FORMAL_ORGANISM_CREATION",
        "organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
        "execution_subject_commit": execution_commit,
        "development_publication_sha": DEVELOPMENT_PUBLICATION_SHA,
        "sealed_master_sha": MASTER_SHA,
        "publication_model": {
            "lock_publication_commit_is_governance_only": True,
            "publication_commit_recorded_by_git_after_artifact_commit": True,
            "semantic_production_subject_is_organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
            "production_subtree_sha_at_organism_subject": production_subtree_sha(),
        },
        "predecessor_evidence": {
            "v8c_development_candidate": ORGANISM_IMPLEMENTATION_SHA,
            "v8c_summary": "docs/evidence/as017-integrated-core/AS017_V8C_COPY_ONLY_VALIDATION_SUMMARY.json",
            "v8c_summary_sha256": sha256(ROOT / "docs/evidence/as017-integrated-core/AS017_V8C_COPY_ONLY_VALIDATION_SUMMARY.json"),
            "v8c_regression_closure": "docs/evidence/as017-integrated-core/AS017_V8C_REGRESSION_CLOSURE.json",
            "v8c_regression_closure_sha256": sha256(ROOT / "docs/evidence/as017-integrated-core/AS017_V8C_REGRESSION_CLOSURE.json"),
            "v8_launch_failure": "docs/evidence/as017-integrated-core/AS017_V8_LAUNCH_FAILURE.json",
            "v8_launch_failure_sha256": sha256(ROOT / "docs/evidence/as017-integrated-core/AS017_V8_LAUNCH_FAILURE.json"),
            "development_only": True,
        },
        "frozen_source": {
            "production_subtree": "umbra_core",
            "production_subtree_sha": production_subtree_sha(),
            "harness_and_validator_sha256": source_hashes(),
            "import_provenance_required": True,
            "clean_detached_checkout_required": True,
        },
        "configuration": configuration_contract(),
        "environment": environment_contract(),
        "seed_contract": {
            "manifest_path": "experiments/as017/AS017_FORMAL_SEED_MANIFEST_V1.json",
            "manifest_sha256": sha256(MANIFEST_PATH),
            "disjointness_path": "experiments/as017/AS017_FORMAL_SEED_DISJOINTNESS_V1.json",
            "disjointness_sha256": sha256(DISJOINTNESS_PATH),
            "formal_regimes": manifest["formal_regimes"],
            "formal_seed_count": 32,
            "organisms_per_regime": 8,
            "retries": 0,
            "reseeds": 0,
            "substitutions": 0,
            "formal_seeds_consumed_at_lock": 0,
            "disjointness_scope": disjointness["limitation"],
        },
        "p0_population_contract": {
            "configuration": "AS016_FULL_CONFIGURATION_AS017_LOCKED",
            "regimes": list(REGIMES),
            "scenarios": SCENARIOS,
            "organisms_per_regime": 8,
            "ticks_per_organism": 7200,
            "total_organisms": 32,
            "total_ticks": 230400,
            "execution_mode": "reviewed_serial_runner_only",
            "preflight_command": [
                sys.executable, "tools/as017_run_formal.py",
                "--manifest", "experiments/as017/AS017_FORMAL_SEED_MANIFEST_V1.json",
                "--work", "/tmp/as017-formal-work-v1",
                "--candidate-commit", execution_commit, "--preflight",
            ],
            "launch_command_template": [
                sys.executable, "tools/as017_run_formal.py",
                "--manifest", "experiments/as017/AS017_FORMAL_SEED_MANIFEST_V1.json",
                "--work", "<fresh-local-work>",
                "--result", "<durable-result>",
                "--candidate-commit", execution_commit,
            ],
            "output_schema": "AS017_FORMAL_POPULATION_V1",
            "case_schema": "AS017_FORMAL_CASE_V1",
            "acceptance": {
                "all_32_complete_7200": True,
                "no_critical_physiology": True,
                "no_unresolved_no_safe_action": True,
                "exact_candidate_configuration_seed_binding": True,
                "identity_preserved": True,
                "terminal_snapshot_and_checkpoint_tail_valid": True,
                "sqlite_integrity_and_foreign_key_valid": True,
                "authenticated_trace_and_semantic_linkage_valid": True,
                "no_hidden_retry_reseed_or_substitution": True,
            },
        },
        "qualification_sequence": [
            {
                "stage": "P0",
                "name": "fresh_integrated_population",
                "acceptance": "all 32 cases satisfy p0_population_contract",
            },
            {
                "stage": "P1",
                "name": "lifecycle_continuity",
                "command_surface": "experiments/as016/run_downstream.py --mode lifecycle",
                "acceptance": "restart, downtime, Habitat reattachment, and body continuity/transfer contract passes",
            },
            {
                "stage": "P2",
                "name": "repeated_compaction_100k",
                "command_surface": "experiments/as016/run_downstream.py --mode boundedness --ticks 100000",
                "acceptance": "locked boundedness, storage, RSS, restart, chain, and authority thresholds pass",
            },
            {
                "stage": "P3",
                "name": "isolated_real_time_s3",
                "command_surface": "experiments/as016/run_downstream.py --mode soak --warmup-seconds 300 --measure-seconds 3600",
                "acceptance": "preregistered S3 cadence, CPU, RSS, slope, storage, and restart thresholds pass",
            },
            {
                "stage": "P4",
                "name": "essential_organization_causal_qualification",
                "acceptance": "OPEN_REQUIRES_PROSPECTIVE_PROTOCOL for memory, relationships, self-model, WorldModel, individuality, temporal continuity, authoritative history",
            },
            {
                "stage": "P5",
                "name": "believable_creature_close_03",
                "acceptance": "OPEN_REQUIRES_PROSPECTIVE_PROTOCOL pending P4 and integrated whole-organism assessment",
            },
        ],
        "downstream_contract": {
            "accelerated_100k": {
                "ticks": 100000,
                "rss_hard_max_mib": 180.0,
                "rss_slope_mib_per_hour_max": 1.0,
                "event_growth_records_per_tick_max": 32,
            },
            "s3": {
                "warmup_seconds": 300.0,
                "measure_seconds": 3600.0,
                "tick_hz": 2.0,
                "sample_interval_seconds": 5.0,
                "minimum_samples": 360,
                "cpu_mean_fraction_max": 0.05,
                "rss_hard_max_mib": 180.0,
                "rss_slope_mib_per_hour_max": 1.0,
            },
            "ablation_variants": [
                "FULL", "TERMINAL_READINESS_DISABLED", "CONTINUATION_DISABLED",
                "ROUTE_LEARNING_DISABLED", "VIABILITY_KERNEL_DISABLED",
            ],
            "ablation_design": "one matched base seed, five arms, identical persistence behavior",
        },
        "stop_rules": {
            "first_preregistered_scientific_or_protocol_failure_terminal": True,
            "after_lock_forbidden": [
                "repair", "retry", "reseed", "substitution", "threshold_change",
                "scenario_change", "horizon_shortening", "execution_mode_change",
            ],
            "downstream_not_run_after_failed_upstream_stage": True,
            "infrastructure_failure_classified_separately": True,
        },
        "lock_integrity": {
            "formal_organisms_created_at_lock": 0,
            "formal_seeds_consumed_at_lock": 0,
            "lock_fails_closed_on_bound_identity_change": True,
            "literal_cli_preflight_must_create_zero_organisms": True,
            "historical_negative_evidence_immutable": True,
        },
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-commit", required=True)
    args = parser.parse_args()
    value = build(args.execution_commit)
    encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    if LOCK_PATH.exists():
        if LOCK_PATH.read_bytes() != encoded:
            raise RuntimeError("AS017_LOCK_CREATE_ONCE_CONTENT_MISMATCH")
    else:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOCK_PATH.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    if LOCK_PATH.read_bytes() != encoded:
        raise RuntimeError("AS017_LOCK_READBACK_INVALID")
    print(json.dumps({
        "lock_path": str(LOCK_PATH),
        "lock_sha256": sha256(LOCK_PATH),
        "execution_subject_commit": args.execution_commit,
        "formal_organisms_created": 0,
        "formal_seeds_consumed": 0,
        "status": value["lock_status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
