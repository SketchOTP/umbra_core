#!/usr/bin/env python3
"""Build and read back AS-018 Scientific Lock V2 without organism creation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.as018_establish_scientific_lock import (  # noqa: E402
    configuration_contract,
    environment_contract,
    imported_source_hashes,
    sha256,
)


ROOT = Path(__file__).resolve().parents[1]
V1_PATH = ROOT / "experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V1.json"
V2_PATH = ROOT / "experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V2.json"
MANIFEST_PATH = ROOT / "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V2.json"
DISJOINTNESS_PATH = ROOT / "experiments/as018/AS018_FORMAL_SEED_DISJOINTNESS_V2.json"
V1_CLOSEOUT_PATH = ROOT / "docs/evidence/as018/AS018_FORMAL_P0_CLOSEOUT_V1.json"
V1_SUPERSESSION_PATH = ROOT / "docs/evidence/as018/AS018_SCIENTIFIC_LOCK_V1_TERMINAL_PROTOCOL_FAILURE_SUPERSEDED_BY_V2.json"
ORGANISM_IMPLEMENTATION_SHA = "e8d048b510a477e677637b67bc0f56473cfe6540"
REGIMES = ("R0", "R1", "R2", "R3")
SCENARIOS = {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def source_hashes() -> dict[str, str]:
    result = imported_source_hashes()
    for relative in (
        "tools/as018_establish_scientific_lock_v2.py",
        "tools/as018_register_formal_manifest_v2.py",
        "tests/test_as018_formal_protocol_v2.py",
        "tests/test_as017_evidence_pipeline.py",
    ):
        result[relative] = sha256(ROOT / relative)
    return dict(sorted(result.items()))


def build() -> dict[str, Any]:
    v1 = load(V1_PATH)
    manifest = load(MANIFEST_PATH)
    disjointness = load(DISJOINTNESS_PATH)
    execution_subject = manifest["formal_execution_subject"]
    if v1.get("organism_implementation_sha") != ORGANISM_IMPLEMENTATION_SHA:
        raise RuntimeError("AS018_LOCK_V1_ORGANISM_BINDING_INVALID")
    if manifest.get("schema") != "AS018_FORMAL_SEED_MANIFEST_V2":
        raise RuntimeError("AS018_LOCK_V2_MANIFEST_SCHEMA_INVALID")
    if disjointness.get("result") != "PASS":
        raise RuntimeError("AS018_LOCK_V2_DISJOINTNESS_NOT_PASS")
    seeds = [int(seed) for regime in REGIMES for seed in manifest["formal_regimes"][regime]]
    if len(seeds) != 32 or len(set(seeds)) != 32:
        raise RuntimeError("AS018_LOCK_V2_SEED_CONTRACT_INVALID")
    if len(execution_subject) != 40 or any(char not in "0123456789abcdef" for char in execution_subject.lower()):
        raise RuntimeError("AS018_LOCK_V2_EXECUTION_SUBJECT_INVALID")
    if sha256(MANIFEST_PATH) != disjointness.get("manifest_sha256"):
        raise RuntimeError("AS018_LOCK_V2_MANIFEST_DISJOINTNESS_BINDING_INVALID")
    supersession = load(V1_SUPERSESSION_PATH)
    if sha256(V1_CLOSEOUT_PATH) != supersession.get("v1_closeout_sha256"):
        raise RuntimeError("AS018_LOCK_V2_V1_CLOSEOUT_INVALID")
    if subprocess_git("rev-parse", f"{execution_subject}:umbra_core") != subprocess_git(
        "rev-parse", f"{ORGANISM_IMPLEMENTATION_SHA}:umbra_core"
    ):
        raise RuntimeError("AS018_LOCK_V2_PRODUCTION_SUBTREE_CHANGED")

    contract = copy.deepcopy(v1)
    contract.update(
        schema="AS018_SCIENTIFIC_LOCK_CONTRACT_V2",
        lock_version="V2",
        formal_execution_subject=execution_subject,
        lock_status="ESTABLISHED_BEFORE_FORMAL_ORGANISM_CREATION",
    )
    contract["supersedes"] = {
        "path": str(V1_PATH.relative_to(ROOT)),
        "sha256": sha256(V1_PATH),
        "status": "properly_established_terminal_protocol_failure_before_organism_creation",
        "reason": "duplicate_stage_binding_and_non_durable_started_boundary",
        "record": str(V1_SUPERSESSION_PATH.relative_to(ROOT)),
        "record_sha256": sha256(V1_SUPERSESSION_PATH),
        "v1_closeout": str(V1_CLOSEOUT_PATH.relative_to(ROOT)),
        "v1_closeout_sha256": sha256(V1_CLOSEOUT_PATH),
    }
    contract["publication_model"] = dict(contract["publication_model"])
    contract["publication_model"].update({
        "lock_publication_commit_is_governance_only": True,
        "semantic_production_subject_is_organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
        "execution_subject_production_subtree_matches": True,
    })
    contract["frozen_source"] = dict(contract["frozen_source"])
    contract["frozen_source"].update({
        "harness_and_validator_sha256": source_hashes(),
        "formal_acceptance_entrypoint": "tools/as018_formal_acceptance.py",
        "formal_runner_entrypoint": "tools/as018_run_formal.py",
        "live_callback_protocol_tests": "tests/test_as018_formal_protocol_v2.py",
    })
    contract["configuration"] = configuration_contract()
    contract["seed_contract"] = dict(contract["seed_contract"])
    contract["seed_contract"].update({
        "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "disjointness_path": str(DISJOINTNESS_PATH.relative_to(ROOT)),
        "disjointness_sha256": sha256(DISJOINTNESS_PATH),
        "formal_regimes": manifest["formal_regimes"],
        "formal_seed_count": 32,
        "formal_seeds_consumed_at_lock": 0,
        "retries": 0,
        "reseeds": 0,
        "substitutions": 0,
        "disjointness_scope": disjointness["limitation"],
    })
    contract["p0_population_contract"] = dict(contract["p0_population_contract"])
    contract["p0_population_contract"].update({
        "formal_manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "execution_mode": "serial_local_sqlite_wal_shm_hardened_accounting_v2",
        "preflight_command": [
            sys.executable, "tools/as018_run_formal.py",
            "--manifest", str(MANIFEST_PATH.relative_to(ROOT)),
            "--lock", str(V2_PATH.relative_to(ROOT)),
            "--lock-sha256", "<lock-sha256>",
            "--work", "/tmp/as018-p0-v2-formal-work",
            "--candidate-commit", "<lock-publication-or-later-governance-commit>", "--preflight",
        ],
        "launch_command_template": [
            sys.executable, "tools/as018_run_formal.py",
            "--manifest", str(MANIFEST_PATH.relative_to(ROOT)),
            "--lock", str(V2_PATH.relative_to(ROOT)),
            "--lock-sha256", "<lock-sha256>",
            "--work", "<fresh-local-work>", "--result", "<durable-result>",
            "--candidate-commit", "<lock-publication-or-later-governance-commit>",
        ],
        "acceptance": dict(contract["p0_population_contract"]["acceptance"]),
    })
    contract["p0_population_contract"]["acceptance"].update({
        "v2_live_started_callback_required": True,
        "durable_started_precedes_in_memory_consumption": True,
        "reserved_journal_fields_protected": True,
    })
    contract["formal_harness_correction"] = {
        "scope": "formal_harness_and_accounting_only",
        "organism_semantics_unchanged": True,
        "v1_terminal_protocol_failure": str(V1_CLOSEOUT_PATH.relative_to(ROOT)),
        "stage_sequence": [
            "REGISTERED", "STARTED", "EXECUTION_FINISHED", "VALIDATION_STARTED",
            "LOCALLY_VALIDATED", "EXPORT_VERIFIED", "CASE_FINISHED",
        ],
        "durable_started_precedes_seed_consumption": True,
        "seed_consumption_boundary": "after_durable_started_fsync_before_organism_execution",
        "failed_started_write_blocks_organism_creation": True,
        "reserved_journal_fields_rejected": True,
        "interruption_is_recoverable": True,
        "failed_validation_cannot_emit_population_pass": True,
        "export_retry_does_not_reexecute": True,
        "formal_seed_consumption_is_started_cases": True,
        "contract_only_preflight_creates_zero_organisms": True,
    }
    contract["lock_integrity"] = dict(contract["lock_integrity"])
    contract["lock_integrity"].update({
        "formal_organisms_created_at_lock": 0,
        "formal_seeds_consumed_at_lock": 0,
        "v1_supersession_readback_required": True,
        "formal_acceptance_callback_required": True,
        "stage_journal_readback_required": True,
        "v2_live_callback_tests_required": True,
    })
    contract["scientific_subject"] = {
        "organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
        "scientific_thresholds_unchanged_from_v1": True,
        "scenarios_unchanged_from_v1": True,
        "rre_semantics_unchanged_from_v1": True,
        "formal_population_replaced_for_protocol_integrity": True,
    }
    contract["environment"] = environment_contract()
    contract["regression"] = dict(contract["regression"])
    contract["regression"]["harness_protocol_tests"] = "tests/test_as018_formal_protocol_v2.py"
    contract["limitations"] = dict(contract["limitations"])
    contract["limitations"]["v1_formal_seed_99100001"] = "consumed_by_v1_started_rule; excluded from V2"
    contract["limitations"]["v1_formal_seeds_99100002_99100032"] = "not consumed but retired from future qualification"
    return contract


def subprocess_git(*args: str) -> str:
    import subprocess
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


if __name__ == "__main__":
    value = build()
    encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    if V2_PATH.exists() and V2_PATH.read_bytes() != encoded:
        raise RuntimeError("AS018_LOCK_V2_CREATE_ONCE_CONTENT_MISMATCH")
    if not V2_PATH.exists():
        V2_PATH.write_bytes(encoded)
    if V2_PATH.read_bytes() != encoded:
        raise RuntimeError("AS018_LOCK_V2_READBACK_INVALID")
    print(json.dumps({
        "lock_path": str(V2_PATH),
        "lock_sha256": sha256(V2_PATH),
        "organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
        "formal_execution_subject": value["formal_execution_subject"],
        "formal_organisms_created": 0,
        "formal_seeds_consumed": 0,
        "status": value["lock_status"],
    }, sort_keys=True))
