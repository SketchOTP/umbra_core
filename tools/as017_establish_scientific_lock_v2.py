#!/usr/bin/env python3
"""Build Lock V2 around the unchanged organism and corrected formal harness."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.as017_establish_scientific_lock import (  # noqa: E402
    DISJOINTNESS_PATH,
    MANIFEST_PATH,
    ORGANISM_IMPLEMENTATION_SHA,
    configuration_contract,
    environment_contract,
    load_json,
    production_subtree_sha,
    sha256,
)

ROOT = Path(__file__).resolve().parents[1]
V1_PATH = ROOT / "experiments/as017/AS017_SCIENTIFIC_LOCK_CONTRACT_V1.json"
V2_PATH = ROOT / "experiments/as017/AS017_SCIENTIFIC_LOCK_CONTRACT_V2.json"
V1_SUPERSESSION_PATH = ROOT / "docs/evidence/as017-integrated-core/AS017_SCIENTIFIC_LOCK_V1_SUPERSESSION.json"
EXECUTION_SUBJECT = "31da940336721edbf8d4f265cf69d109661404ce"
REGIMES = ("R0", "R1", "R2", "R3")


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
        "tools/as017_formal_acceptance.py",
        "tools/as017_run_formal.py",
        "tools/as017_establish_scientific_lock_v2.py",
    ]
    return {path: sha256(ROOT / path) for path in paths}


def build() -> dict[str, Any]:
    v1 = load_json(V1_PATH)
    manifest = load_json(MANIFEST_PATH)
    disjointness = load_json(DISJOINTNESS_PATH)
    if v1.get("organism_implementation_sha") != ORGANISM_IMPLEMENTATION_SHA:
        raise RuntimeError("AS017_LOCK_V1_ORGANISM_BINDING_INVALID")
    if manifest.get("seed_status") != "frozen_before_formal_execution":
        raise RuntimeError("AS017_LOCK_MANIFEST_NOT_FROZEN")
    if disjointness.get("result") != "PASS":
        raise RuntimeError("AS017_LOCK_DISJOINTNESS_NOT_PASS")

    contract = dict(v1)
    contract.update(
        schema="AS017_SCIENTIFIC_LOCK_CONTRACT_V2",
        lock_version="V2",
        execution_subject_commit=EXECUTION_SUBJECT,
    )
    contract["supersedes"] = {
        "path": "experiments/as017/AS017_SCIENTIFIC_LOCK_CONTRACT_V1.json",
        "sha256": sha256(V1_PATH),
        "status": "properly_established_never_executed",
        "reason": "formal_harness_accounting_and_acceptance_defect",
        "supersession_record": str(V1_SUPERSESSION_PATH.relative_to(ROOT)),
        "supersession_record_sha256": sha256(V1_SUPERSESSION_PATH),
    }
    contract["publication_model"] = dict(contract["publication_model"])
    contract["publication_model"]["semantic_production_subject_is_organism_implementation_sha"] = ORGANISM_IMPLEMENTATION_SHA
    contract["frozen_source"] = dict(contract["frozen_source"])
    contract["frozen_source"]["harness_and_validator_sha256"] = source_hashes()
    contract["frozen_source"]["formal_acceptance_entrypoint"] = "tools/as017_formal_acceptance.py"
    contract["seed_contract"] = dict(contract["seed_contract"])
    contract["seed_contract"]["formal_seeds_consumed_at_lock"] = 0
    contract["p0_population_contract"] = dict(contract["p0_population_contract"])
    contract["p0_population_contract"]["preflight_command"] = [
        sys.executable, "tools/as017_run_formal.py",
        "--manifest", "experiments/as017/AS017_FORMAL_SEED_MANIFEST_V1.json",
        "--work", "/tmp/as017-formal-work-v2",
        "--candidate-commit", EXECUTION_SUBJECT, "--preflight",
    ]
    contract["p0_population_contract"]["launch_command_template"] = [
        sys.executable, "tools/as017_run_formal.py",
        "--manifest", "experiments/as017/AS017_FORMAL_SEED_MANIFEST_V1.json",
        "--work", "<fresh-local-work>", "--result", "<durable-result>",
        "--candidate-commit", EXECUTION_SUBJECT,
    ]
    contract["p0_population_contract"]["acceptance"] = dict(contract["p0_population_contract"]["acceptance"])
    contract["p0_population_contract"]["acceptance"].update({
        "formal_case_acceptance_required": True,
        "case_stage_journal_required": True,
        "case_completion_requires_all_validated_artifacts": True,
        "population_pass_requires_exactly_32_accepted_cases": True,
        "seed_consumed_on_started": True,
        "actual_seed_consumption_must_be_reported": True,
    })
    contract["formal_harness_correction"] = {
        "scope": "accounting_and_acceptance_only",
        "organism_semantics_unchanged": True,
        "stage_sequence": [
            "REGISTERED", "STARTED", "EXECUTION_FINISHED", "VALIDATION_STARTED",
            "LOCALLY_VALIDATED", "EXPORT_VERIFIED", "CASE_FINISHED",
        ],
        "interruption_is_recoverable": True,
        "failed_validation_cannot_emit_population_pass": True,
        "export_retry_does_not_reexecute": True,
        "formal_seed_consumption_is_len_started_cases": True,
        "contract_only_preflight_creates_zero_organisms": True,
    }
    contract["lock_integrity"] = dict(contract["lock_integrity"])
    contract["lock_integrity"].update({
        "formal_organisms_created_at_lock": 0,
        "formal_seeds_consumed_at_lock": 0,
        "v1_supersession_readback_required": True,
        "formal_acceptance_callback_required": True,
        "stage_journal_readback_required": True,
    })
    # Keep the unchanged scientific sequence and conditions, while making the
    # changed harness identity explicit to every downstream consumer.
    contract["scientific_subject"] = {
        "organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
        "scientific_thresholds_unchanged_from_v1": True,
        "scenarios_unchanged_from_v1": True,
        "formal_seed_manifest_unchanged_from_v1": True,
    }
    return contract


def main() -> None:
    value = build()
    encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    if V2_PATH.exists() and V2_PATH.read_bytes() != encoded:
        raise RuntimeError("AS017_LOCK_V2_CREATE_ONCE_CONTENT_MISMATCH")
    if not V2_PATH.exists():
        V2_PATH.parent.mkdir(parents=True, exist_ok=True)
        with V2_PATH.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
    if V2_PATH.read_bytes() != encoded:
        raise RuntimeError("AS017_LOCK_V2_READBACK_INVALID")
    print(json.dumps({
        "lock_path": str(V2_PATH),
        "lock_sha256": sha256(V2_PATH),
        "organism_implementation_sha": ORGANISM_IMPLEMENTATION_SHA,
        "execution_subject_commit": EXECUTION_SUBJECT,
        "formal_organisms_created": 0,
        "formal_seeds_consumed": 0,
        "status": value["lock_status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
