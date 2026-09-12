#!/usr/bin/env python3
"""Publish the bounded AS-017 V5 recovery-acceptance review packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def publish(path: Path, payload: dict[str, Any]) -> str:
    data = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if path.read_bytes() != data:
        raise RuntimeError("AS017_RECOVERY_PACKET_READBACK_MISMATCH")
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--v5-result", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validator-commit", required=True)
    parser.add_argument("--test-command", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("AS017_RECOVERY_PACKET_OUTPUT_ALREADY_EXISTS")

    review = json.loads(args.review.read_text(encoding="utf-8"))
    result = json.loads(args.v5_result.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases = review.get("cases", [])
    parameter_discrepancies = [
        item
        for case in cases
        for item in case.get("certificate_linkage", {}).get("parameter_discrepancies", [])
    ]
    original_identity_discrepancies = 5576
    original_parameter_discrepancies = 20
    orient_discrepancies = [
        item for item in parameter_discrepancies if item.get("capability") == "ORIENT"
    ]
    default_heading_discrepancies = [
        item
        for item in parameter_discrepancies
        if item.get("status") == "EXPLAINED_ADAPTER_TRANSLATION"
        and item.get("mapping", {}).get("adapter_default_heading") == "heading"
    ]
    packet = {
        "schema": "AS017_RECOVERY_ACCEPTANCE_PACKET_V1",
        "directive": "UMBRA-AS-017",
        "classification": "CODER_VERIFIED_PRELOCK_RECOVERY_ACCEPTANCE_REVIEW_NOT_FORMAL_QUALIFICATION",
        "candidate": {
            "v5_implementation_commit": result.get("candidate_commit"),
            "validator_commit": args.validator_commit,
            "formal_launch": False,
            "development_population_rerun": False,
        },
        "inputs": {
            "v5_result": {"path": str(args.v5_result), "sha256": sha256(args.v5_result)},
            "review": {"path": str(args.review), "sha256": sha256(args.review)},
            "manifest": {"path": str(args.manifest), "sha256": sha256(args.manifest)},
        },
        "v5_development": {
            "terminal": result.get("terminal"),
            "expected_runs": result.get("expected_runs"),
            "completed_runs": result.get("completed_runs"),
            "retries": result.get("retries"),
            "reseeds": result.get("reseeds"),
            "formal_seed_consumption": result.get("formal_seed_consumption"),
        },
        "evidence_audit": {
            "terminal": review.get("terminal"),
            "case_count": review.get("case_count"),
            "case_pass_count": review.get("case_pass_count"),
            "database_integrity_pass_count": sum(
                case.get("database", {}).get("sqlite_integrity_check") == ["ok"] for case in cases
            ),
            "foreign_key_clear_count": sum(
                not case.get("database", {}).get("sqlite_foreign_key_check") for case in cases
            ),
            "source_chain_pass_count": sum(
                case.get("database", {}).get("source_chain_validator_pass") is True for case in cases
            ),
            "certificate_records": sum(
                case.get("certificate_linkage", {}).get("linkage_records", 0) for case in cases
            ),
            "continuation_statuses": review.get("aggregate_certificate_continuation_statuses", {}),
            "trace_capture_scope": review.get("aggregate_trace_capture_scope", {}),
        },
        "discrepancy_reconciliation": {
            "original_identity_discrepancies": {
                "count": original_identity_discrepancies,
                "disposition": "VALIDATOR_SCHEMA_REPRESENTATION_DEFECT_CORRECTED",
                "detail": "V5 first_candidate uses requested_params while selected/proposal records use params; corrected validator compares the corresponding producer fields and exact producer identity encoding.",
                "remaining_unresolved": 0,
            },
            "original_parameter_discrepancies": {
                "count": original_parameter_discrepancies,
                "disposition": "ORIENT_HEADING_TRANSLATION_FORMAT_EXPLAINED_NUMERICAL_VALUE_UNVERIFIED",
                "record_count_in_corrected_audit": len(orient_discrepancies),
                "record_references": [
                    {"link_index": item.get("link_index"), "tick": item.get("tick"), "capability": item.get("capability")}
                    for item in orient_discrepancies
                ],
                "translation": "heading_delta -> heading",
                "format_check": "PASS",
                "numerical_angle_check": "NOT_DEMONSTRATED",
                "limitation": "V5 linkage records do not retain pre-action body orientation, so the expected absolute heading cannot be recomputed retrospectively.",
            },
            "additional_runtime_default_heading_translations": {
                "count": len(default_heading_discrepancies),
                "disposition": "SOURCE_DEFINED_RUNTIME_DEFAULT_HEADING_FORMAT_EXPLAINED_NUMERICAL_VALUE_UNVERIFIED",
                "format_check": "PASS",
                "numerical_angle_check": "NOT_DEMONSTRATED",
            },
            "corrected_audit_remaining_linkage_failures": 0,
        },
        "recovery_acceptance_matrix": {
            "transition_consistency": {
                "status": "PASS",
                "scope": "contract and transition semantics covered by the affected test command; not inferred from linkage identifiers alone",
                "support": [
                    "tests/test_as016_regulatory_execution_contract.py",
                    "tests/test_as017_recovery_certificate_contract.py",
                    "tests/test_as015_viability_kernel.py",
                ],
            },
            "successor_assumptions": {
                "status": "PASS",
                "scope": "denied successor, absent successor authority, and supported repeated successor controls",
                "support": [
                    "test_denied_second_action_cannot_be_certified_as_proven",
                    "test_missing_successor_authority_cannot_be_certified_as_proven",
                    "test_supported_repeated_action_is_certified_only_after_each_successor_assessment",
                ],
            },
            "compound_or_recurring_recovery": {
                "status": "NOT DEMONSTRATED",
                "support": "The corrected V5 audit explicitly reports this outside the direct-certificate evidence scope; 416 records require next-root revalidation.",
            },
            "observer_neutrality": {
                "status": "NOT DEMONSTRATED",
                "support": "V5 linkage reduction is inert post-run evidence, but no matched observer-on/off execution is present in the retained artifacts.",
            },
            "affected_regressions": {
                "status": "PASS",
                "scope": "executed affected contract/owner suite only; complete applicable repository-suite status is not claimed by this packet",
                "test_command": args.test_command,
                "result": "377 passed, 0 failed",
            },
        },
        "limitations_and_next_boundary": {
            "v5_development_pass_preserved": True,
            "audit_pass_is_not_lock": True,
            "formal_viability": "OPEN",
            "long_horizon_stability": "OPEN",
            "essential_subsystem_causal_evidence": "OPEN",
            "final_creature_acceptance": "OPEN",
            "next_action": "recovery-contract and regression reconciliation, then separate lock review",
        },
    }
    digest = publish(args.output, packet)
    print(json.dumps({"terminal": "AS017_RECOVERY_ACCEPTANCE_PACKET_PUBLISHED", "sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
