#!/usr/bin/env python3
"""Create and read back the AS-018 scientific lock without organism creation."""

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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ORGANISM_IMPLEMENTATION_SHA = "e8d048b510a477e677637b67bc0f56473cfe6540"
EXECUTION_SUBJECT = "d7968a2de557513f2316d684b394ed851d1aae51"
MASTER_SHA = "fd8c50e1134d7d2ef54e20148ac9b7880e63708d"
MANIFEST_PATH = ROOT / "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V1.json"
DISJOINTNESS_PATH = ROOT / "experiments/as018/AS018_FORMAL_SEED_DISJOINTNESS_V1.json"
LOCK_PATH = ROOT / "experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V1.json"
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
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def imported_source_hashes() -> dict[str, str]:
    # Import the actual formal entrypoint and its validator closure so the lock
    # covers transitive repository-owned harness code, not a hand-picked list.
    import experiments.as018.full_config  # noqa: F401
    import experiments.as018.qualification  # noqa: F401
    import experiments.as018.formal_accounting  # noqa: F401
    import tools.as018_formal_acceptance  # noqa: F401
    import tools.as018_run_formal  # noqa: F401

    result: dict[str, str] = {}
    for module in tuple(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError:
            continue
        if path.suffix == ".py" and path.is_file():
            result[path.relative_to(ROOT).as_posix()] = sha256(path)
    result["tools/as018_establish_scientific_lock.py"] = sha256(ROOT / "tools/as018_establish_scientific_lock.py")
    return dict(sorted(result.items()))


def configuration_contract() -> dict[str, Any]:
    from experiments.as018.full_config import config, fingerprint

    with tempfile.TemporaryDirectory(prefix="as018-lock-config-") as directory:
        values = {
            regime: fingerprint(config(0, Path(directory) / f"{regime}.sqlite", regime))
            for regime in REGIMES
        }
    return {
        "name": "AS018_FULL_CONFIGURATION_RRE_ENABLED",
        "seed_binding": "manifest_seed_per_case",
        "database_binding": "isolated_local_runtime_path_per_case",
        "regimes": list(REGIMES),
        "scenarios": SCENARIOS,
        "ticks_per_organism": 7200,
        "fingerprints": values,
        "fingerprint_sha256": {regime: canonical_sha(value) for regime, value in values.items()},
    }


def environment_contract() -> dict[str, Any]:
    freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], cwd=ROOT)
    return {
        "python_executable": sys.executable,
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "cwd_at_lock_creation": os.getcwd(),
        "pythonpath": os.environ.get("PYTHONPATH", ""),
        "pip_freeze_sha256": hashlib.sha256(freeze).hexdigest(),
    }


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict[str, Any]:
    manifest = load(MANIFEST_PATH)
    disjointness = load(DISJOINTNESS_PATH)
    if manifest.get("organism_implementation_sha") != ORGANISM_IMPLEMENTATION_SHA:
        raise RuntimeError("AS018_LOCK_MANIFEST_ORGANISM_MISMATCH")
    if manifest.get("formal_execution_subject") != EXECUTION_SUBJECT:
        raise RuntimeError("AS018_LOCK_EXECUTION_SUBJECT_MANIFEST_MISMATCH")
    if manifest.get("seed_status") != "frozen_before_formal_execution":
        raise RuntimeError("AS018_LOCK_MANIFEST_NOT_FROZEN")
    if disjointness.get("result") != "PASS":
        raise RuntimeError("AS018_LOCK_DISJOINTNESS_NOT_PASS")
    seeds = [seed for regime in REGIMES for seed in manifest["formal_regimes"][regime]]
    if len(seeds) != 32 or len(set(seeds)) != 32:
        raise RuntimeError("AS018_LOCK_FORMAL_SEED_CONTRACT_INVALID")
    if git("rev-parse", "HEAD") != EXECUTION_SUBJECT:
        raise RuntimeError("AS018_LOCK_EXECUTION_SUBJECT_NOT_CURRENT")
    if git("rev-parse", f"{EXECUTION_SUBJECT}:umbra_core") != git("rev-parse", f"{ORGANISM_IMPLEMENTATION_SHA}:umbra_core"):
        raise RuntimeError("AS018_LOCK_PRODUCTION_SUBTREE_CHANGED")

    evidence = {
        "development_closeout": {
            "path": "docs/evidence/as018/AS018_DEVELOPMENT_V3_CLOSEOUT.json",
            "sha256": sha256(ROOT / "docs/evidence/as018/AS018_DEVELOPMENT_V3_CLOSEOUT.json"),
        },
        "development_manifest": {
            "path": "experiments/as018/AS018_DEVELOPMENT_SEED_MANIFEST_V2.json",
            "sha256": sha256(ROOT / "experiments/as018/AS018_DEVELOPMENT_SEED_MANIFEST_V2.json"),
        },
        "development_disjointness": {
            "path": "docs/evidence/as018/AS018_DEVELOPMENT_SEED_DISJOINTNESS_V2.json",
            "sha256": sha256(ROOT / "docs/evidence/as018/AS018_DEVELOPMENT_SEED_DISJOINTNESS_V2.json"),
        },
        "formal_failure_forensic_map": {
            "path": "docs/evidence/as018/AS018_FORMAL_FAILURE_FORENSIC_MAP.json",
            "sha256": sha256(ROOT / "docs/evidence/as018/AS018_FORMAL_FAILURE_FORENSIC_MAP.json"),
        },
        "regression_accounting": {
            "path": "docs/evidence/as018/AS018_REGRESSION_ACCOUNTING_V1.json",
            "sha256": sha256(ROOT / "docs/evidence/as018/AS018_REGRESSION_ACCOUNTING_V1.json"),
        },
    }
    return {
        "schema": "AS018_SCIENTIFIC_LOCK_CONTRACT_V1",
        "directive": "UMBRA-AS-018",
        "lock_status": "ESTABLISHED_BEFORE_FORMAL_ORGANISM_CREATION",
        "organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
        "formal_execution_subject": EXECUTION_SUBJECT,
        "lock_publication_commit_recorded_in_append_only_closeout": True,
        "sealed_master_sha": MASTER_SHA,
        "publication_model": {
            "lock_publication_commit_is_governance_only": True,
            "semantic_production_subject_is_organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
            "production_subtree": "umbra_core",
            "production_subtree_sha_at_organism_subject": git("rev-parse", f"{ORGANISM_IMPLEMENTATION_SHA}:umbra_core"),
            "execution_subject_production_subtree_matches": True,
        },
        "predecessor_evidence": {
            "as017_terminal": "AS017_FRESH_R1_FAIL",
            "as017_formal_failure_seed": 26489381,
            "as018_v1": "docs/evidence/as018/AS018_DEVELOPMENT_V1_VALIDATION_INTERRUPTION.json",
            "as018_v2_replay": "docs/evidence/as018/AS018_DEVELOPMENT_V2_REPLAY_CLOSEOUT.json",
            "as018_v3_development_only": True,
            "historical_evidence_immutable": True,
        },
        "evidence_readback_sha256": evidence,
        "frozen_source": {
            "production_subtree": "umbra_core",
            "production_subtree_sha": git("rev-parse", f"{ORGANISM_IMPLEMENTATION_SHA}:umbra_core"),
            "transitive_imported_harness_source_hashes": imported_source_hashes(),
            "contract_test_sha256": {
                "tests/test_as018_scientific_lock.py": sha256(ROOT / "tests/test_as018_scientific_lock.py"),
            },
            "clean_detached_checkout_required": True,
            "import_provenance_required": True,
        },
        "configuration": configuration_contract(),
        "rre_authority_invariants": [
            "ROBUST_NOW, BOUNDED_RECOVERY_OPPORTUNITY, MAY_ROUTE, and UNKNOWN_ROUTE remain distinct",
            "RRE is a viability constraint, not a preference owner or action selector",
            "only supported recovery-reserve-eliminating candidates may be rejected under a genuine threat",
            "normal distributed arbitration remains authoritative among surviving candidates",
            "no Habitat coordinates, hidden IDs, renderer state, or future-world truth enter RRE",
            "body and movement support originate through lawful SelfModel/body evidence",
            "physiology projection follows owner effect-clamp then drift-clamp semantics",
            "unsupported or probabilistic route evidence remains UNKNOWN or MAY_ROUTE",
            "RRE is dormant outside the recovery-reserve threat boundary",
        ],
        "environment": environment_contract(),
        "seed_contract": {
            "manifest_path": "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V1.json",
            "manifest_sha256": sha256(MANIFEST_PATH),
            "disjointness_path": "experiments/as018/AS018_FORMAL_SEED_DISJOINTNESS_V1.json",
            "disjointness_sha256": sha256(DISJOINTNESS_PATH),
            "formal_regimes": manifest["formal_regimes"],
            "formal_seed_count": 32,
            "organisms_per_regime": 8,
            "ticks_per_organism": 7200,
            "total_ticks": 230400,
            "retries": 0,
            "reseeds": 0,
            "substitutions": 0,
            "formal_seeds_consumed_at_lock": 0,
            "disjointness_scope": disjointness["limitation"],
        },
        "p0_population_contract": {
            "configuration": "AS018_FULL_CONFIGURATION_RRE_ENABLED",
            "regimes": list(REGIMES),
            "scenarios": SCENARIOS,
            "organisms_per_regime": 8,
            "ticks_per_organism": 7200,
            "total_organisms": 32,
            "total_ticks": 230400,
            "execution_mode": "serial_local_sqlite_wal_shm_hardened_accounting",
            "case_schema": "AS018_FORMAL_CASE_V1",
            "output_schema": "AS018_FORMAL_POPULATION_V1",
            "stage_sequence": ["REGISTERED", "STARTED", "EXECUTION_FINISHED", "VALIDATION_STARTED", "LOCALLY_VALIDATED", "EXPORT_VERIFIED", "CASE_FINISHED"],
            "acceptance": {
                "exact_registered_seed_regime_scenario_candidate_configuration": True,
                "all_32_complete_7200": True,
                "no_critical_physiology": True,
                "no_unresolved_no_safe_action": True,
                "identity_preserved": True,
                "terminal_snapshot_and_checkpoint_tail_valid": True,
                "sqlite_integrity_and_foreign_key_valid": True,
                "authenticated_trace_and_semantic_linkage_valid": True,
                "required_rre_evidence_valid": True,
                "case_finished_only_after_all_artifact_validation": True,
                "population_pass_requires_exactly_32_accepted_cases": True,
                "no_hidden_retry_reseed_or_substitution": True,
            },
            "preflight_command": [
                sys.executable, "tools/as018_run_formal.py",
                "--manifest", "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V1.json",
                "--lock", "experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V1.json",
                "--lock-sha256", "<lock-sha256>",
                "--work", "/tmp/as018-formal-work-v1",
                "--candidate-commit", EXECUTION_SUBJECT, "--preflight",
            ],
            "launch_command_template": [
                sys.executable, "tools/as018_run_formal.py",
                "--manifest", "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V1.json",
                "--lock", "experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V1.json",
                "--lock-sha256", "<lock-sha256>",
                "--work", "<fresh-local-work>", "--result", "<durable-result>",
                "--candidate-commit", EXECUTION_SUBJECT,
            ],
        },
        "qualification_sequence": [
            {"stage": "P0", "name": "fresh_integrated_population", "acceptance": "all 32 cases satisfy frozen P0 contract"},
            {"stage": "P1", "name": "lifecycle_continuity", "acceptance": "restart, snapshot/load, downtime, Habitat reattachment, body continuity/transfer"},
            {"stage": "P2", "name": "repeated_compaction_100k", "acceptance": "existing bounded persistence, RSS, storage, restart, and chain thresholds"},
            {"stage": "P3", "name": "isolated_real_time_s3", "acceptance": "preregistered 300-second warmup plus 3600-second measurement protocol"},
            {"stage": "P4", "name": "essential_organization_causal_qualification", "acceptance": "OPEN_REQUIRES_PROSPECTIVE_PROTOCOL for memory, relationships, self-model, WorldModel, individuality, temporal continuity, authoritative history"},
            {"stage": "P5", "name": "believable_creature_close_03", "acceptance": "OPEN_REQUIRES_PROSPECTIVE_PROTOCOL pending whole-organism protocol"},
        ],
        "downstream_contract": {
            "accelerated_100k": {"ticks": 100000, "rss_hard_max_mib": 180.0, "rss_slope_mib_per_hour_max": 1.0, "event_growth_records_per_tick_max": 32},
            "s3": {"warmup_seconds": 300.0, "measure_seconds": 3600.0, "tick_hz": 2.0, "sample_interval_seconds": 5.0, "minimum_samples": 360, "cpu_mean_fraction_max": 0.05, "rss_hard_max_mib": 180.0, "rss_slope_mib_per_hour_max": 1.0},
            "ablation_variants": ["FULL", "TERMINAL_READINESS_DISABLED", "CONTINUATION_DISABLED", "ROUTE_LEARNING_DISABLED", "VIABILITY_KERNEL_DISABLED"],
            "ablation_design": "one matched base seed, five arms, identical persistence behavior",
        },
        "stop_rules": {
            "first_preregistered_scientific_or_protocol_failure_terminal_for_active_stage": True,
            "downstream_not_run_after_failed_upstream_stage": True,
            "after_lock_forbidden": ["repair", "retry", "reseed", "substitution", "threshold_change", "scenario_change", "horizon_change", "execution_mode_change", "RRE_semantic_change"],
            "infrastructure_failure_classified_separately": True,
            "consumed_seed_remains_consumed_after_interruption": True,
        },
        "lock_integrity": {
            "formal_organisms_created_at_lock": 0,
            "formal_seeds_consumed_at_lock": 0,
            "literal_preflight_creates_zero_organisms": True,
            "lock_fails_closed_on_bound_identity_change": True,
            "lock_artifact_self_hash_reported_out_of_band": True,
        },
        "regression": {
            "raw_result": "1422 passed / 4 skipped / 9 inherited failures",
            "candidate_only_failures": 0,
            "inherited_failures_unwaived": True,
            "evidence_path": "docs/evidence/as018/AS018_REGRESSION_ACCOUNTING_V1.json",
        },
        "limitations": {
            "external_seed_records": "not independently available to this checkout; universal disjointness outside local scan scope is not claimed",
            "p4_status": "OPEN_REQUIRES_PROSPECTIVE_PROTOCOL",
            "p5_status": "OPEN_REQUIRES_PROSPECTIVE_PROTOCOL",
            "development_not_formal": True,
        },
    }


def main() -> None:
    value = build()
    encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    if LOCK_PATH.exists():
        if LOCK_PATH.read_bytes() != encoded:
            raise RuntimeError("AS018_LOCK_CREATE_ONCE_CONTENT_MISMATCH")
    else:
        with LOCK_PATH.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    if LOCK_PATH.read_bytes() != encoded:
        raise RuntimeError("AS018_LOCK_READBACK_INVALID")
    print(json.dumps({
        "lock_path": str(LOCK_PATH),
        "lock_sha256": sha256(LOCK_PATH),
        "organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
        "formal_execution_subject": EXECUTION_SUBJECT,
        "formal_organisms_created": 0,
        "formal_seeds_consumed": 0,
        "status": value["lock_status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
