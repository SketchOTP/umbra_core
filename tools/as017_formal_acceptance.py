"""Fail-closed P0 case acceptance for the AS-017 formal runner."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Callable

from tools.as017_evidence import (
    EvidenceFormatError,
    publish_file_once,
    publish_json_once,
    reduce_acceptance_trace,
    reduce_certificate_linkage,
    stream_sha256,
)
from tools.as017_validate_linkage_v2 import validate_linkage_v2
from tools.as017_validate_v8c import _validate_database


def _case_id(row: dict[str, Any]) -> str:
    return f"{row['regime']}-{row['seed_index']:02d}-{row['seed']}"


def accept_case(
    row: dict[str, Any],
    work: Path,
    candidate_commit: str,
    manifest_sha256: str,
    journal: Any,
) -> dict[str, Any]:
    """Export and validate every artifact before allowing CASE_FINISHED."""
    case_id = _case_id(row)
    failures: list[str] = []
    if row.get("terminal") != "completed":
        failures.append("execution_not_completed")
    if row.get("ticks") != 7200 or row.get("target_ticks") != 7200:
        failures.append("tick_horizon_mismatch")
    if row.get("critical_failure") is not None:
        failures.append("critical_physiology")
    if row.get("first_no_safe_action") is not None:
        failures.append("unresolved_no_safe_action")
    if row.get("candidate_commit") != candidate_commit:
        failures.append("candidate_binding_mismatch")
    if row.get("seed_manifest_sha256") != manifest_sha256:
        failures.append("manifest_binding_mismatch")
    if row.get("configuration", {}).get("seed") != row.get("seed"):
        failures.append("configuration_seed_mismatch")
    if failures:
        journal.append("CASE_REJECTED", case_id=case_id, failures=failures)
        return {"verdict": "FAIL", "case_id": case_id, "failures": failures}

    database = work / f"{row['regime']}-{row['seed']}.sqlite"
    trace_name = row.get("decision_trace_filename")
    if not trace_name:
        failures.extend(("required_local_artifact_missing", "required_trace_binding_missing"))
        journal.append("CASE_REJECTED", case_id=case_id, failures=failures)
        return {"verdict": "FAIL", "case_id": case_id, "failures": failures}
    trace = work / str(trace_name)
    if not database.is_file() or not trace.is_file():
        failures.append("required_local_artifact_missing")
        journal.append("CASE_REJECTED", case_id=case_id, failures=failures)
        return {"verdict": "FAIL", "case_id": case_id, "failures": failures}

    exports = work / "exports"
    exported_database = exports / "case-databases" / database.name
    compact_trace = work / "case-traces-compact" / trace.name
    exported_trace = exports / "case-traces" / compact_trace.name
    linkage_records = work / "certificate-linkage" / f"{case_id}.jsonl"
    exported_records = exports / "certificate-linkage" / linkage_records.name
    summary_path = exports / "certificate-linkage" / f"{case_id}.summary.json"

    journal.append("VALIDATION_STARTED", case_id=case_id, source_database=str(database), source_trace=str(trace))
    journal.append("EXPORT_STARTED", case_id=case_id, artifact="database", destination=str(exported_database))
    database_sha256 = publish_file_once(database, exported_database)
    journal.append("EXPORT_VERIFIED", case_id=case_id, artifact="database", sha256=database_sha256)

    trace_summary = reduce_acceptance_trace(trace, compact_trace)
    if trace_summary["rows"] != row["ticks"]:
        failures.append("trace_row_count_mismatch")
    journal.append("EXPORT_STARTED", case_id=case_id, artifact="compact_trace", destination=str(exported_trace))
    trace_sha256 = publish_file_once(compact_trace, exported_trace)
    journal.append("EXPORT_VERIFIED", case_id=case_id, artifact="compact_trace", sha256=trace_sha256)

    linkage = reduce_certificate_linkage(exported_trace, linkage_records)
    linkage["candidate_commit"] = candidate_commit
    journal.append("EXPORT_STARTED", case_id=case_id, artifact="linkage_records", destination=str(exported_records))
    records_sha256 = publish_file_once(linkage_records, exported_records)
    linkage["records_sha256"] = records_sha256
    journal.append("EXPORT_VERIFIED", case_id=case_id, artifact="linkage_records", sha256=records_sha256)
    linkage["trace_path"] = str(exported_trace)
    linkage["records_path"] = str(exported_records)
    linkage_summary_sha256 = publish_json_once(summary_path, linkage)
    journal.append("EXPORT_VERIFIED", case_id=case_id, artifact="linkage_summary", sha256=linkage_summary_sha256)

    with tempfile.TemporaryDirectory(prefix="as017-formal-case-db-") as scratch_name:
        database_report = _validate_database(
            exported_database, database_sha256, row["target_ticks"], Path(scratch_name)
        )
    if database_report["verdict"] != "PASS":
        failures.extend(database_report["failures"])
    linkage_report = validate_linkage_v2(
        summary_path,
        exported_records,
        exported_trace,
        candidate_commit,
        expected_summary_sha256=linkage_summary_sha256,
        expected_trace_sha256=trace_sha256,
    )
    if linkage_report["verdict"] != "PASS":
        failures.extend(linkage_report["failures"])
    if trace_summary["rows"] != 7200:
        failures.append("authenticated_trace_scope_incomplete")
    if not database_report.get("identity_present"):
        failures.append("identity_missing")

    if not failures:
        journal.append(
            "LOCALLY_VALIDATED",
            case_id=case_id,
            database_validation=database_report,
            trace_processing=trace_summary,
            linkage_validation=linkage_report,
        )

    acceptance = {
        "schema": "AS017_FORMAL_CASE_ACCEPTANCE_V1",
        "verdict": "PASS" if not failures else "FAIL",
        "case_id": case_id,
        "candidate_commit": candidate_commit,
        "manifest_sha256": manifest_sha256,
        "database": database_report,
        "trace": trace_summary | {"exported_sha256": trace_sha256},
        "linkage": linkage_report,
        "failures": failures,
    }
    if failures:
        journal.append("CASE_REJECTED", case_id=case_id, failures=failures, acceptance=acceptance)
        return acceptance

    row["database_sha256"] = database_sha256
    row["decision_trace_sha256"] = trace_sha256
    row["certificate_linkage_sha256"] = linkage_summary_sha256
    row["formal_acceptance"] = acceptance
    case_result = work / "exports" / "case-results" / f"{case_id}.json"
    case_result_sha256 = publish_json_once(case_result, row)
    journal.append("EXPORT_VERIFIED", case_id=case_id, artifact="case_result", sha256=case_result_sha256)
    journal.append(
        "CASE_FINISHED",
        case_id=case_id,
        required_artifacts=["database", "compact_trace", "linkage_records", "linkage_summary", "case_result"],
        case_result_sha256=case_result_sha256,
    )
    acceptance["case_result_sha256"] = case_result_sha256
    return acceptance


__all__ = ["accept_case"]
