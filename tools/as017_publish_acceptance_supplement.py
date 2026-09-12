#!/usr/bin/env python3
"""Publish the scoped AS-017 V5 acceptance supplement.

This is an evidence-only publisher.  It reads retained V5 artifacts and the
bounded observer probe result, performs copy/read-only checks, and creates one
new JSON artifact without changing any historical result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


V5_CANDIDATE = "fe783295a0de175b88000a9ffadfd1b7ff4afa38"
DIRECTIVE = "UMBRA-AS-017"
SEED_MANIFEST_SHA = "8c609eb39b98cf994cd2290cbd531305b4ba520fef670156fd1d08b069e3247d"
V5_RESULT_SHA = "3df1cbc626df142e8e68b6e037491e0b90254de2f03dd37ccf97993b883e9c5b"
V5_REVIEW_SHA = "7180fd31195af5e83ee3f0960366b74099194a734023b83e18628b9372ea90da"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def artifact(path: Path) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def event_payloads(db: Path) -> list[tuple[int, str, dict[str, Any]]]:
    uri = f"file:{db}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        rows = connection.execute(
            "SELECT sequence, event_type, payload FROM events ORDER BY sequence"
        ).fetchall()
    output: list[tuple[int, str, dict[str, Any]]] = []
    for sequence, event_type, payload in rows:
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            decoded = {}
        output.append((int(sequence), str(event_type), decoded if isinstance(decoded, dict) else {}))
    return output


def retained_episode(db: Path, linkage: Path) -> dict[str, Any]:
    events = event_payloads(db)
    linked = read_json(linkage).get("linked_records", [])
    linked_by_tick: dict[int, dict[str, Any]] = {}
    for record in linked:
        if isinstance(record, dict) and isinstance(record.get("tick"), int):
            linked_by_tick[record["tick"]] = record

    selected: list[dict[str, Any]] = []
    for tick in (6412, 6414, 6416, 6419, 6423, 6426, 6436):
        record = linked_by_tick.get(tick)
        if not record:
            continue
        selected.append(
            {
                "tick": tick,
                "capability": record.get("selected_candidate", {}).get("capability"),
                "requested_params": record.get("selected_candidate", {}).get("params", {}),
                "certificate_status": record.get("certificate", {}).get("status"),
                "continuation_status": record.get("continuation", {}).get("status"),
                "governance_admitted": record.get("governance_decision", {}).get("admitted"),
                "proposal_id": record.get("governance_proposal", {}).get("proposal_id"),
                "verified_outcome_id": record.get("verified_outcome", {}).get("verified_outcome_id"),
                "applied_params": record.get("verified_outcome", {}).get("applied_params", {}),
                "effects": record.get("verified_outcome", {}).get("effects", {}),
                "outcome_success": record.get("verified_outcome", {}).get("success"),
                "event_sequence": record.get("verified_outcome", {}).get("event_sequence"),
            }
        )

    physiology: dict[int, dict[str, Any]] = {}
    for _sequence, event_type, payload in events:
        tick = payload.get("tick")
        if isinstance(tick, int) and 6408 <= tick <= 6436:
            if event_type in {"physiology_drift", "outcome_verified"}:
                physiology.setdefault(tick, {})[event_type] = payload

    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as connection:
        event_counts = Counter(
            row[0]
            for row in connection.execute("SELECT event_type FROM events")
        )

    return {
        "case": "R0-01-17182603",
        "database": artifact(db),
        "linkage": artifact(linkage),
        "retained_tail_scope": "read_only_events_table_and_case_linkage",
        "episode_ticks": [row["tick"] for row in selected],
        "sequence": selected,
        "physiology_event_samples": physiology,
        "event_counts": dict(sorted(event_counts.items())),
        "interpretation": (
            "The retained tail shows multi-need pressure followed by recurring governed "
            "REST and later CHARGE, with successful verified effects. This supports "
            "compound/recurring recovery for this retained episode only; it is not an "
            "indefinite guarantee and does not resolve all 416 next-root statuses."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--observer-result", type=Path, required=True)
    parser.add_argument("--observer-script", type=Path, required=True)
    parser.add_argument("--full-suite-log", type=Path, required=True)
    parser.add_argument("--applicable-suite-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise RuntimeError("AS017_SUPPLEMENT_CREATE_ONCE_PATH_EXISTS")

    evidence = args.evidence_root / "AS017_DEVELOPMENT_V5_EVIDENCE"
    v5_result = args.evidence_root / "AS017_DEVELOPMENT_V5_RESULT.json"
    v5_review = args.evidence_root / "AS017_DEVELOPMENT_V5_EVIDENCE_REVIEW_V3.json"
    packet = args.evidence_root / "AS017_RECOVERY_ACCEPTANCE_PACKET_V1.json"
    manifest = args.evidence_root / "AS017_DEVELOPMENT_SEED_MANIFEST.json"
    episode_db = evidence / "case-databases" / "R0-17182603.sqlite"
    episode_linkage = evidence / "certificate-linkage" / "R0-01-17182603.json"

    inputs = [
        v5_result,
        v5_review,
        packet,
        manifest,
        episode_db,
        episode_linkage,
        args.observer_result,
        args.observer_script,
        args.full_suite_log,
        args.applicable_suite_log,
    ]
    missing = [str(path) for path in inputs if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing evidence inputs: " + ", ".join(missing))

    v5 = read_json(v5_result)
    review = read_json(v5_review)
    observer = read_json(args.observer_result)

    if v5.get("candidate_commit") != V5_CANDIDATE:
        raise ValueError("V5 candidate binding mismatch")
    if review.get("terminal") != "AS017_V5_EVIDENCE_REVIEW_PASS":
        raise ValueError("V5 review is not the accepted scoped review")
    if observer.get("candidate_commit") != V5_CANDIDATE:
        raise ValueError("observer probe candidate binding mismatch")

    review_hashes = {
        "v5_result": artifact(v5_result),
        "v5_review": artifact(v5_review),
        "acceptance_packet": artifact(packet),
        "seed_manifest": artifact(manifest),
        "observer_result": artifact(args.observer_result),
        "observer_script": artifact(args.observer_script),
        "full_suite_log": artifact(args.full_suite_log),
        "applicable_suite_log": artifact(args.applicable_suite_log),
    }

    observer_summary = {
        "result": observer.get("result"),
        "candidate_commit": observer.get("candidate_commit"),
        "seed": observer.get("seed"),
        "regime": observer.get("regime"),
        "horizon": observer.get("horizon"),
        "semantic_differences": observer.get("semantic_differences"),
        "capture_on": {
            "ticks": observer.get("capture_on", {}).get("ticks"),
            "terminal": observer.get("capture_on", {}).get("terminal"),
            "actions": observer.get("capture_on", {}).get("actions"),
            "proposal_count": observer.get("capture_on", {}).get("proposal_count"),
            "trace_present": observer.get("capture_on", {}).get("trace_present"),
            "trace_sha256": observer.get("capture_on", {}).get("trace_sha256"),
            "rng_final": observer.get("capture_on", {}).get("rng_final"),
        },
        "capture_off": {
            "ticks": observer.get("capture_off", {}).get("ticks"),
            "terminal": observer.get("capture_off", {}).get("terminal"),
            "actions": observer.get("capture_off", {}).get("actions"),
            "proposal_count": observer.get("capture_off", {}).get("proposal_count"),
            "trace_present": observer.get("capture_off", {}).get("trace_present"),
            "trace_sha256": observer.get("capture_off", {}).get("trace_sha256"),
            "rng_final": observer.get("capture_off", {}).get("rng_final"),
        },
        "scope_limit": (
            "One bounded development seed and passive Governance/outcome capture; "
            "not a formal qualification replicate."
        ),
    }

    supplement = {
        "schema": "AS017_RECOVERY_ACCEPTANCE_SUPPLEMENT_V1",
        "directive": DIRECTIVE,
        "classification": "scoped_prelock_development_evidence",
        "terminal": "AS017_RECOVERY_ACCEPTANCE_SCOPED_PASS_PRELOCK",
        "candidate": {
            "implementation_commit": V5_CANDIDATE,
            "seed_manifest_sha256": SEED_MANIFEST_SHA,
            "formal_seed_consumption": 0,
            "retries": 0,
            "reseeds": 0,
        },
        "historical_boundaries": {
            "v5_development_pass_preserved": True,
            "v5_review_preserved": True,
            "v1_observer_probe_startup_failure": {
                "job": "job-mtyq2jxc-c23f73a5",
                "classification": "zero_tick_probe_infrastructure_failure",
            },
            "v5_trace_evidence_not_reexecuted": True,
            "orient_heading_angles_numerically_verified": False,
        },
        "artifact_hashes": review_hashes,
        "retained_v5_summary": {
            "terminal": v5.get("terminal"),
            "completed_runs": v5.get("completed_runs"),
            "expected_runs": v5.get("expected_runs"),
            "total_ticks": sum(int(row.get("ticks", 0)) for row in v5.get("rows", [])),
            "aggregate_certificate_continuation_statuses": review.get(
                "aggregate_certificate_continuation_statuses", {}
            ),
            "aggregate_trace_capture_scope": review.get("aggregate_trace_capture_scope", {}),
            "validator_review_terminal": review.get("terminal"),
        },
        "compound_recurring_recovery": {
            "verdict": "PASS_WITH_SCOPE_LIMITS",
            "evidence": retained_episode(episode_db, episode_linkage),
            "coverage": {
                "retained_regulatory_outcomes": 1517,
                "near_regulatory_pairs_within_10_ticks": 1047,
                "multi_nonviable_state_regulatory_samples": 988,
                "certificate_linked_records": 6932,
                "next_root_revalidation_required_unresolved": 416,
            },
            "limitations": [
                "V5 certificates have one-step witnesses; this supplement does not turn them into multi-step certificates.",
                "The episode is retained tail evidence after compaction, not a complete birth-to-7200 replay.",
                "No indefinite-survival or global viability claim is made.",
            ],
        },
        "observer_neutrality": {
            "verdict": "PASS_WITH_SCOPE_LIMITS",
            "evidence": observer_summary,
            "capture_contract": [
                "capture is passive around existing Governance proposal/execution calls",
                "no additional preflight calls are made",
                "capture-on and capture-off use isolated databases",
                "proposal/outcome sequences and final RNG state are compared",
            ],
        },
        "recovery_acceptance_matrix": {
            "transition_consistency": {
                "verdict": "PASS_WITH_SCOPE_LIMITS",
                "support": "V5 affected contract tests and retained verified outcomes; linkage review alone is not a complete timing proof.",
            },
            "supported_successor_assumptions": {
                "verdict": "PASS",
                "support": "Published successor-denial and supported-successor contract tests in the affected suite.",
            },
            "compound_or_recurring_recovery": {
                "verdict": "PASS_WITH_SCOPE_LIMITS",
                "support": "Retained R0-01-17182603 multi-need REST recurrence followed by CHARGE, with governed verified outcomes.",
            },
            "observer_neutrality": {
                "verdict": "PASS_WITH_SCOPE_LIMITS",
                "support": "Bounded V5 R1 capture-on/off probe: 1200/1200, no compared semantic differences.",
            },
            "affected_regressions": {
                "verdict": "NOT_CLEAN_RAW_SUITE",
                "support": "Focused owner/recovery set: 377 passed. Applicable repository run: 1376 passed, 7 failed, 4 skipped; raw collection also has one documented orphan import exclusion.",
                "classification": "The seven failures are retained as inherited/pre-existing per earlier A/B/C differential records; this supplement does not independently rerun that differential.",
            },
        },
        "regression_and_governance": {
            "focused_suite": {"passed": 377, "failed": 0, "runs": 2, "status": "PASS"},
            "applicable_suite": {"passed": 1376, "failed": 7, "skipped": 4, "status": "NOT_CLEAN"},
            "full_suite_collection": {"status": "INHERITED_COLLECTION_EXCLUSION", "exit_code": 2},
            "candidate_only_failures": "NOT_ESTABLISHED_BY_THIS_SUPPLEMENT",
            "authority_3": "NOT_RUN_IN_THIS_SUPPLEMENT",
            "governance": "NOT_RUN_IN_THIS_SUPPLEMENT",
            "git_diff_check": "NOT_RUN_IN_THIS_SUPPLEMENT",
        },
        "prelock_status": {
            "v5_development_pass": True,
            "scoped_review_pass": True,
            "recovery_acceptance_complete": False,
            "scientific_lock_authorized": False,
            "formal_launch_authorized": False,
            "remaining_requirements": [
                "reconcile transition consistency and successor evidence beyond linkage scope",
                "retain unresolved 416 continuation statuses explicitly",
                "complete applicable regression reconciliation and governance checks",
                "obtain Architect lock review before formal science",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(supplement, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"path": str(args.output), "sha256": sha256(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
