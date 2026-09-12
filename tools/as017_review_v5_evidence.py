#!/usr/bin/env python3
"""Read-only AS-017 V5 evidence review.

The validator never opens a V5 exported database for writing.  It hashes each
source export, copies it to a caller-owned local scratch directory, and only
then runs SQLite and Store validation against the copy.  Its result is an
append-only evidence artifact; it is not an organism runner or a qualifier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from umbra_core.persistence import Store
from umbra_core.util import canon_json


DIRECTIVE = "UMBRA-AS-017"
HORIZON = 7200
SCHEMA = "AS017_DEVELOPMENT_V5_EVIDENCE_REVIEW_V1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def publish_json_once(path: Path, payload: dict[str, Any]) -> str:
    data = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    readback = path.read_bytes()
    require(readback == data, "artifact_readback_mismatch")
    return hashlib.sha256(data).hexdigest()


def _candidate_params(candidate: dict[str, Any], parameter_field: str) -> dict[str, Any] | None:
    """Read one schema-declared parameter representation without aliasing it."""
    value = candidate.get(parameter_field)
    if not isinstance(value, dict):
        return None
    return value


def candidate_identity(candidate: dict[str, Any], *, parameter_field: str) -> tuple[str, str] | None:
    """Return the exact behavioral identity using the producer's field shape."""
    params = _candidate_params(candidate, parameter_field)
    capability = candidate.get("capability")
    if params is None or not isinstance(capability, str):
        return None
    return capability, canon_json(params).decode("utf-8")


def producer_identity(candidate: dict[str, Any], *, parameter_field: str) -> str | None:
    """Mirror viability._candidate_identity: capability plus repr(canon_json(...))."""
    identity = candidate_identity(candidate, parameter_field=parameter_field)
    if identity is None:
        return None
    capability, encoded_params = identity
    return f"{capability}:{encoded_params.encode('utf-8')}"


def requested_parameters_match(
    candidate: dict[str, Any], outcome: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    """Validate requested parameters and explicit adapter translation separately."""
    requested = _candidate_params(candidate, "params")
    observed_requested = _candidate_params(outcome, "requested_params")
    applied = _candidate_params(outcome, "applied_params")
    if requested is None or observed_requested is None or applied is None:
        return False, {"status": "UNRESOLVED", "reason": "parameter_representation_missing"}
    if observed_requested != requested:
        return False, {"status": "UNRESOLVED", "reason": "requested_parameters_changed"}

    # V5's only recorded translation is the runtime's body-relative heading
    # conversion.  The applied absolute heading cannot be re-derived from this
    # linkage record alone, so require the explicit translation evidence when
    # the adapter changed the parameter name.  All non-translated requested
    # values must remain exactly represented in the applied request.
    translated = {"heading_delta": "heading"}
    translation: dict[str, str] = {}
    for key, value in requested.items():
        applied_key = translated.get(key, key)
        if applied_key not in applied:
            if key == "heading_delta":
                return False, {"status": "UNRESOLVED", "reason": "adapter_translation_missing:heading_delta_to_heading"}
            return False, {"status": "UNRESOLVED", "reason": f"applied_parameter_missing:{key}"}
        if key != "heading_delta" and applied[applied_key] != value:
            return False, {"status": "UNRESOLVED", "reason": f"applied_parameter_changed:{key}"}
        if key in translated:
            translation[key] = applied_key
    allowed_applied_keys = {translated.get(key, key) for key in requested}
    if set(applied) - allowed_applied_keys:
        return False, {
            "status": "UNRESOLVED",
            "reason": "unrecorded_adapter_translation",
            "unexpected_applied_keys": sorted(set(applied) - allowed_applied_keys),
        }
    if "heading_delta" in requested:
        if "heading" not in applied:
            return False, {"status": "UNRESOLVED", "reason": "adapter_translation_missing:heading_delta_to_heading"}
        if not isinstance(applied["heading"], (int, float)):
            return False, {"status": "UNRESOLVED", "reason": "adapter_translation_invalid:heading"}
    if translation:
        return True, {"status": "EXPLAINED_ADAPTER_TRANSLATION", "mapping": translation}
    return True, {"status": "EXACT_REQUEST_APPLIED_MATCH"}


def validate_trace(trace: Path) -> tuple[dict[str, dict[str, Any]], dict[str, int], list[str]]:
    """Validate trace integrity and enumerate declared recovery-capture scope."""
    records: dict[str, dict[str, Any]] = {}
    scope: Counter[str] = Counter()
    failures: list[str] = []
    with trace.open(encoding="utf-8") as handle:
        for expected_tick, line in enumerate(handle, start=1):
            row = json.loads(line)
            stored_hash = row.pop("trace_row_hash", None)
            observed_hash = canonical_sha256(row)
            if stored_hash != observed_hash:
                failures.append(f"trace_hash_mismatch:tick_{expected_tick}")
            if row.get("tick") != expected_tick:
                failures.append(f"trace_tick_mismatch:expected_{expected_tick}_got_{row.get('tick')}")
            row["trace_row_hash"] = stored_hash
            if stored_hash is not None:
                records[str(stored_hash)] = row
            kernel = row.get("viability_kernel")
            if not isinstance(kernel, dict):
                scope["NO_VIABILITY_OBLIGATION"] += 1
            elif kernel.get("selected_recovery_certificate") is not None:
                scope["CERTIFICATE_CAPTURED"] += 1
            else:
                scope[f"RECOVERY_WITHOUT_CERTIFICATE:{kernel.get('disposition', 'UNSPECIFIED')}"] += 1
    if len(records) != HORIZON:
        failures.append(f"trace_row_count_expected_{HORIZON}_got_{len(records)}")
    return records, dict(sorted(scope.items())), failures


def validate_linkage(
    linkage: dict[str, Any], trace_records: dict[str, dict[str, Any]], trace_hash: str, candidate_commit: str
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    if linkage.get("schema") != "AS017_RECOVERY_CERTIFICATE_LINKAGE_V1":
        failures.append("linkage_schema_mismatch")
    if linkage.get("candidate_commit") != candidate_commit:
        failures.append("linkage_candidate_commit_mismatch")
    if linkage.get("trace_sha256") != trace_hash:
        failures.append("linkage_trace_hash_mismatch")
    links = linkage.get("linked_records")
    if not isinstance(links, list):
        return {"linkage_records": 0}, [*failures, "linkage_records_missing"]
    statuses: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    parameter_discrepancies: list[dict[str, Any]] = []
    for index, link in enumerate(links):
        trace_key = str(link.get("trace_row_hash"))
        row = trace_records.get(trace_key)
        if row is None:
            failures.append(f"link_{index}:trace_row_missing")
            continue
        certificate = link.get("certificate") or {}
        selected = link.get("selected_candidate") or {}
        proposal = link.get("governance_proposal") or {}
        decision = link.get("governance_decision") or {}
        outcome = link.get("verified_outcome") or {}
        continuation = link.get("continuation") or {}
        first = certificate.get("first_candidate") or {}
        first_identity = candidate_identity(first, parameter_field="requested_params")
        selected_identity = candidate_identity(selected, parameter_field="params")
        proposal_identity = candidate_identity(proposal, parameter_field="params")
        if first_identity is None or selected_identity is None:
            failures.append(f"link_{index}:candidate_identity_fields_missing")
        elif first_identity != selected_identity:
            failures.append(f"link_{index}:certificate_selected_identity_mismatch")
        if producer_identity(first, parameter_field="requested_params") != certificate.get("first_candidate_identity"):
            failures.append(f"link_{index}:certificate_recorded_identity_mismatch")
        kernel = row.get("viability_kernel") or {}
        if certificate != kernel.get("selected_recovery_certificate"):
            failures.append(f"link_{index}:certificate_trace_mismatch")
        if selected_identity is None or proposal_identity is None:
            failures.append(f"link_{index}:proposal_identity_fields_missing")
        elif selected_identity != proposal_identity:
            failures.append(f"link_{index}:selected_proposal_identity_mismatch")
        if selected != row.get("final_candidate"):
            failures.append(f"link_{index}:selected_trace_mismatch")
        if proposal != row.get("governance_proposal"):
            failures.append(f"link_{index}:proposal_trace_mismatch")
        if decision != row.get("governance_decision"):
            failures.append(f"link_{index}:decision_trace_mismatch")
        if outcome != row.get("verified_outcome_linkage"):
            failures.append(f"link_{index}:outcome_trace_mismatch")
        if not bool(decision.get("admitted")):
            failures.append(f"link_{index}:certificate_not_governance_admitted")
        if proposal.get("proposal_id") != outcome.get("governance_proposal_id"):
            failures.append(f"link_{index}:proposal_outcome_id_mismatch")
        parameters_match, parameter_disposition = requested_parameters_match(selected, outcome)
        if parameter_disposition.get("status") != "EXACT_REQUEST_APPLIED_MATCH":
            parameter_discrepancies.append({
                "link_index": index,
                "tick": link.get("tick"),
                "capability": selected.get("capability"),
                "requested_params": selected.get("params"),
                "outcome_requested_params": outcome.get("requested_params"),
                "applied_params": outcome.get("applied_params"),
                **parameter_disposition,
            })
        if not parameters_match:
            failures.append(
                f"link_{index}:requested_applied_parameter_mismatch:{parameter_disposition.get('reason', 'unknown')}"
            )
        if certificate.get("status") != "PROVEN":
            failures.append(f"link_{index}:non_proven_certificate_recorded")
        status = str(continuation.get("status", "UNSPECIFIED"))
        statuses[status] += 1
        categories["verified_continuation" if status == "TERMINAL_RECOVERY_REVALIDATED" else "conditional_continuation"] += 1
    if linkage.get("linked_count") != len(links):
        failures.append("linkage_count_mismatch")
    if linkage.get("unmatched_count") != 0:
        failures.append("linkage_unmatched_records")
    if linkage.get("linked_count") != sum(1 for row in trace_records.values()
                                         if isinstance(row.get("viability_kernel"), dict)
                                         and row["viability_kernel"].get("selected_recovery_certificate") is not None):
        failures.append("linkage_capture_scope_mismatch")
    return {
        "linkage_records": len(links),
        "unmatched_records": int(linkage.get("unmatched_count", -1)),
        "continuation_status_counts": dict(sorted(statuses.items())),
        "claim_scope_counts": dict(sorted(categories.items())),
        "parameter_discrepancies": parameter_discrepancies,
    }, failures


def validate_database_copy(database: Path, scratch: Path, expected: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Run SQLite and source-defined ledger validation only against a local copy."""
    failures: list[str] = []
    observed_hash = sha256(database)
    if observed_hash != expected.get("database_sha256"):
        failures.append("database_source_hash_mismatch")
    copied = scratch / database.name
    shutil.copy2(database, copied)
    copied_hash = sha256(copied)
    if copied_hash != observed_hash:
        failures.append("database_copy_hash_mismatch")
    connection = sqlite3.connect(f"file:{copied}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        integrity = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
        foreign_keys = [list(row) for row in connection.execute("PRAGMA foreign_key_check")]
        if integrity != ["ok"]:
            failures.append("sqlite_integrity_check_failed")
        if foreign_keys:
            failures.append("sqlite_foreign_key_check_failed")
        identity_rows = connection.execute("SELECT agent_id, record_json, commitment FROM identity").fetchall()
        if len(identity_rows) != 1:
            failures.append("identity_row_count_invalid")
            agent_id = None
        else:
            agent_id = str(identity_rows[0]["agent_id"])
            try:
                identity_json = json.loads(identity_rows[0]["record_json"])
                if identity_json.get("agent_id") != agent_id:
                    failures.append("identity_record_agent_mismatch")
                if identity_json.get("identity_commitment") != identity_rows[0]["commitment"]:
                    failures.append("identity_commitment_mismatch")
            except (json.JSONDecodeError, TypeError):
                failures.append("identity_record_invalid")
        latest = connection.execute("SELECT value FROM meta WHERE key='latest_snapshot'").fetchone()
        if latest is None:
            failures.append("latest_snapshot_missing")
            snapshot = None
        else:
            snapshot = connection.execute("SELECT * FROM snapshots WHERE snapshot_id=?", (latest[0],)).fetchone()
            if snapshot is None:
                failures.append("latest_snapshot_row_missing")
        terminal_event = connection.execute("SELECT * FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        checkpoint = connection.execute("SELECT * FROM ledger_checkpoints ORDER BY checkpoint_epoch DESC LIMIT 1").fetchone()
        checkpoint_epoch = int(checkpoint["checkpoint_epoch"]) if checkpoint is not None else 0
        if checkpoint_epoch != int(expected.get("checkpoint_epoch", 0)):
            failures.append("checkpoint_epoch_result_mismatch")
        temporal = None
        if snapshot is not None:
            try:
                state = json.loads(snapshot["state_json"])
                temporal = state.get("temporal") if isinstance(state, dict) else None
                if snapshot["agent_id"] != agent_id or state.get("identity", {}).get("agent_id") != agent_id:
                    failures.append("snapshot_identity_mismatch")
                if float(snapshot["monotonic_time"]) != float(HORIZON):
                    failures.append("snapshot_monotonic_time_mismatch")
                if not isinstance(temporal, dict) or temporal.get("organism_active_ticks") != HORIZON or temporal.get("organism_age_ticks") != HORIZON:
                    failures.append("snapshot_temporal_tick_mismatch")
            except (json.JSONDecodeError, TypeError):
                failures.append("snapshot_state_invalid")
        if terminal_event is None:
            failures.append("terminal_event_missing")
        else:
            try:
                payload = json.loads(terminal_event["payload"])
                advance = payload.get("temporal_advance_record", {})
                if terminal_event["agent_id"] != agent_id:
                    failures.append("terminal_event_identity_mismatch")
                if float(terminal_event["monotonic_time"]) != float(HORIZON):
                    failures.append("terminal_event_monotonic_time_mismatch")
                if advance.get("new_active_ticks") != HORIZON or advance.get("new_age_ticks") != HORIZON:
                    failures.append("terminal_event_temporal_tick_mismatch")
                if snapshot is not None and int(snapshot["sequence"]) != int(terminal_event["sequence"]):
                    failures.append("terminal_snapshot_sequence_mismatch")
            except (json.JSONDecodeError, TypeError):
                failures.append("terminal_event_payload_invalid")
        if agent_id is not None:
            foreign_agent_count = connection.execute("SELECT COUNT(*) FROM events WHERE agent_id != ?", (agent_id,)).fetchone()[0]
            if foreign_agent_count:
                failures.append("retained_event_identity_mismatch")
        checkpoint_summary: dict[str, Any] = {"epoch": checkpoint_epoch, "present": checkpoint is not None}
        if checkpoint is not None:
            checkpoint_summary.update({
                "compacted_sequence_start": int(checkpoint["compacted_sequence_start"]),
                "compacted_sequence_end": int(checkpoint["compacted_sequence_end"]),
                "retained_tail_start": int(checkpoint["compacted_sequence_end"]) + 1,
            })
            first_retained = connection.execute("SELECT sequence, previous_event_hash FROM events ORDER BY sequence ASC LIMIT 1").fetchone()
            if first_retained is None or int(first_retained["sequence"]) != int(checkpoint["compacted_sequence_end"]) + 1:
                failures.append("checkpoint_tail_sequence_mismatch")
            elif first_retained["previous_event_hash"] != checkpoint["terminal_event_hash"]:
                failures.append("checkpoint_tail_hash_join_mismatch")
        table_counts = {str(row[0]): int(row[1]) for row in connection.execute(
            "SELECT name, (SELECT COUNT(*) FROM sqlite_master AS ignored) FROM sqlite_master WHERE type='table'"
        )}
    finally:
        connection.close()
    # Use the current production validator only on the disposable local copy.
    try:
        store = Store(copied)
        try:
            store.load_identity()
            store.load_snapshot()
            store.validate_chain()
        finally:
            store.close()
        chain_valid = True
    except Exception as exc:  # fail closed while retaining the reason in evidence
        failures.append(f"source_chain_validator_failed:{type(exc).__name__}:{exc}")
        chain_valid = False
    return {
        "source_database_sha256": observed_hash,
        "isolated_copy_sha256": copied_hash,
        "sqlite_integrity_check": integrity,
        "sqlite_foreign_key_check": foreign_keys,
        "identity_agent_id": agent_id,
        "terminal_snapshot_temporal": temporal,
        "terminal_event_sequence": int(terminal_event["sequence"]) if terminal_event is not None else None,
        "checkpoint": checkpoint_summary,
        "source_chain_validator_pass": chain_valid,
        "table_presence": sorted(table_counts),
    }, failures


def validate_case(
    row: dict[str, Any], result: dict[str, Any], manifest: dict[str, Any], evidence_root: Path, scratch: Path
) -> dict[str, Any]:
    failures: list[str] = []
    regime, seed, seed_index = str(row.get("regime")), int(row.get("seed")), int(row.get("seed_index"))
    expected_seeds = (manifest.get("development_regimes") or {}).get(regime, [])
    if seed_index >= len(expected_seeds) or expected_seeds[seed_index] != seed:
        failures.append("manifest_regime_seed_binding_mismatch")
    if row.get("candidate_commit") != result.get("candidate_commit"):
        failures.append("candidate_commit_binding_mismatch")
    if row.get("seed_manifest_sha256") != result.get("seed_manifest_sha256"):
        failures.append("manifest_hash_binding_mismatch")
    if row.get("ticks") != HORIZON or row.get("target_ticks") != HORIZON or row.get("terminal") != "completed":
        failures.append("case_terminal_or_tick_mismatch")
    configuration = row.get("configuration") or {}
    if configuration.get("seed") != seed or configuration.get("habitat_scenario_id") != row.get("scenario"):
        failures.append("configuration_binding_mismatch")
    stem = f"{regime}-{seed_index:02d}-{seed}"
    case_path = evidence_root / "case-results" / f"{stem}.json"
    trace_path = evidence_root / "case-traces" / str(row.get("decision_trace_filename", "")).split("/")[-1]
    database_path = evidence_root / "case-databases" / f"{regime}-{seed}.sqlite"
    linkage_path = evidence_root / "certificate-linkage" / f"{stem}.json"
    for required in (case_path, trace_path, database_path, linkage_path):
        if not required.is_file():
            failures.append(f"missing_artifact:{required.name}")
    case_hash = sha256(case_path) if case_path.is_file() else None
    if case_path.is_file() and read_json(case_path) != row:
        failures.append("case_result_row_mismatch")
    trace_hash = sha256(trace_path) if trace_path.is_file() else None
    if trace_hash != row.get("decision_trace_sha256"):
        failures.append("trace_source_hash_mismatch")
    trace_records, scope, trace_failures = validate_trace(trace_path) if trace_path.is_file() else ({}, {}, ["trace_missing"])
    failures.extend(trace_failures)
    linkage = read_json(linkage_path) if linkage_path.is_file() else {}
    linkage_hash = sha256(linkage_path) if linkage_path.is_file() else None
    if linkage_hash != row.get("certificate_linkage_sha256"):
        failures.append("linkage_source_hash_mismatch")
    linkage_summary, linkage_failures = validate_linkage(
        linkage, trace_records, trace_hash or "", str(result.get("candidate_commit"))
    )
    failures.extend(linkage_failures)
    database_summary, database_failures = validate_database_copy(database_path, scratch, row) if database_path.is_file() else ({}, ["database_missing"])
    failures.extend(database_failures)
    return {
        "case": {"regime": regime, "seed_index": seed_index, "seed": seed},
        "artifacts": {
            "case_result_sha256": case_hash,
            "trace_sha256": trace_hash,
            "linkage_sha256": linkage_hash,
            "database_expected_sha256": row.get("database_sha256"),
        },
        "binding": {
            "candidate_commit": row.get("candidate_commit"),
            "seed_manifest_sha256": row.get("seed_manifest_sha256"),
            "configuration_seed": configuration.get("seed"),
            "configuration_scenario": configuration.get("habitat_scenario_id"),
        },
        "terminal": {"case_terminal": row.get("terminal"), "ticks": row.get("ticks"), "target_ticks": row.get("target_ticks")},
        "database": database_summary,
        "trace_capture_scope": scope,
        "certificate_linkage": linkage_summary,
        "verdict": "PASS" if not failures else "FAIL",
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-work", type=Path, required=True)
    parser.add_argument("--scratch-parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-commit", required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "AS017_EVIDENCE_REVIEW_OUTPUT_ALREADY_EXISTS")
    result, manifest = read_json(args.result), read_json(args.manifest)
    require(result.get("directive") == DIRECTIVE and result.get("terminal") == "AS017_DEVELOPMENT_PASS", "result_contract_invalid")
    require(result.get("candidate_commit") == args.candidate_commit, "candidate_commit_mismatch")
    require(manifest.get("directive") == DIRECTIVE and manifest.get("horizon_ticks") == HORIZON, "manifest_contract_invalid")
    manifest_hash = sha256(args.manifest)
    require(result.get("seed_manifest_sha256") == manifest_hash, "manifest_hash_mismatch")
    rows = result.get("rows")
    require(isinstance(rows, list) and len(rows) == 16 and result.get("completed_runs") == 16, "result_rows_invalid")
    require(result.get("retries") == 0 and result.get("reseeds") == 0 and result.get("formal_seed_consumption") == 0, "execution_boundary_invalid")
    tool_hash = sha256(Path(__file__).resolve())
    with tempfile.TemporaryDirectory(prefix="as017-v5-review-", dir=args.scratch_parent) as temporary:
        scratch = Path(temporary)
        cases = [validate_case(row, result, manifest, args.evidence_work, scratch) for row in rows]
    failures = [case["case"] for case in cases if case["verdict"] != "PASS"]
    aggregate_scope: Counter[str] = Counter()
    aggregate_linkage: Counter[str] = Counter()
    for case in cases:
        aggregate_scope.update(case["trace_capture_scope"])
        aggregate_linkage.update(case["certificate_linkage"].get("continuation_status_counts", {}))
    payload = {
        "schema": SCHEMA,
        "directive": DIRECTIVE,
        "classification": "existing_v5_development_evidence_review_not_formal_qualification",
        "validator": {"path": str(Path(__file__).resolve()), "sha256": tool_hash, "candidate_commit": args.candidate_commit},
        "inputs": {"result": str(args.result), "result_sha256": sha256(args.result), "manifest": str(args.manifest), "manifest_sha256": manifest_hash, "evidence_work": str(args.evidence_work)},
        "execution_boundary": {"retries": result.get("retries"), "reseeds": result.get("reseeds"), "formal_seed_consumption": result.get("formal_seed_consumption")},
        "case_count": len(cases),
        "case_pass_count": len(cases) - len(failures),
        "case_failures": failures,
        "aggregate_trace_capture_scope": dict(sorted(aggregate_scope.items())),
        "aggregate_certificate_continuation_statuses": dict(sorted(aggregate_linkage.items())),
        "requirements": {
            "transition_consistency": "NOT_DEMONSTRATED_BY_LINKAGE_ONLY",
            "supported_successor_assumptions": "NOT_DEMONSTRATED_BY_V5_DIRECT_RECOVERY_CERTIFICATES",
            "compound_or_recurring_recovery": "NOT_DEMONSTRATED_BY_V5_DIRECT_RECOVERY_CERTIFICATES",
            "observer_neutrality": "NOT_DEMONSTRATED_BY_EXISTING_V5_ARTIFACTS",
            "affected_regressions": "NOT_EVALUATED_BY_THIS_READ_ONLY_EVIDENCE_REVIEW",
        },
        "cases": cases,
        "terminal": "AS017_V5_EVIDENCE_REVIEW_PASS" if not failures else "AS017_V5_EVIDENCE_REVIEW_FAIL",
    }
    digest = publish_json_once(args.output, payload)
    print(json.dumps({"terminal": payload["terminal"], "sha256": digest, "cases": len(cases), "failed_cases": len(failures)}, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
