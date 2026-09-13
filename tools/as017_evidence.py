"""Bounded-memory evidence primitives for AS-017 experiment runners.

These helpers are deliberately independent of organism policy.  They stream
files and JSONL records, retain at most one bounded record, and make incomplete
publication visible instead of turning it into a result.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from umbra_core.decision_trace import compact_acceptance_row, trace_row_hash, verify_trace_row_hash


CHUNK_SIZE = 1024 * 1024
MAX_TRACE_RECORD_BYTES = 4 * 1024 * 1024


class EvidenceFormatError(ValueError):
    """Raised when an evidence stream is incomplete or exceeds its bound."""


def stream_sha256(path: Path, *, chunk_size: int = CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def stream_bytes_equal(path: Path, expected: bytes, *, chunk_size: int = CHUNK_SIZE) -> bool:
    offset = 0
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            end = offset + len(chunk)
            if expected[offset:end] != chunk:
                return False
            offset = end
    return offset == len(expected)


def publish_json_once(path: Path, payload: dict[str, Any]) -> str:
    data = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if not stream_bytes_equal(path, data):
        raise RuntimeError("AS017_PUBLICATION_READBACK_MISMATCH")
    return hashlib.sha256(data).hexdigest()


def publish_file_once(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open("rb") as src, destination.open("xb") as dst:
        while chunk := src.read(CHUNK_SIZE):
            digest.update(chunk)
            dst.write(chunk)
        dst.flush()
        os.fsync(dst.fileno())
    actual = stream_sha256(destination)
    if actual != digest.hexdigest():
        raise RuntimeError("AS017_FILE_COPY_READBACK_MISMATCH")
    return actual


def iter_jsonl(path: Path, *, max_record_bytes: int = MAX_TRACE_RECORD_BYTES) -> Iterator[dict[str, Any]]:
    with path.open("rb") as handle:
        line_number = 0
        while raw := handle.readline(max_record_bytes + 1):
            line_number += 1
            if len(raw) > max_record_bytes:
                raise EvidenceFormatError(
                    f"record_exceeds_bound:line_{line_number}:bytes_{len(raw)}"
                )
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise EvidenceFormatError(
                    f"invalid_json:line_{line_number}:{exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise EvidenceFormatError(f"record_not_object:line_{line_number}")
            yield value


def validate_sqlite_copy(path: Path) -> dict[str, Any]:
    """Validate a closed SQLite database without changing it."""
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        raise EvidenceFormatError(
            f"sqlite_validation_failed:integrity={integrity}:foreign_keys={len(foreign_keys)}"
        )
    return {"integrity_check": integrity, "foreign_key_check_rows": len(foreign_keys)}


def reduce_acceptance_trace(
    source: Path,
    destination: Path,
    *,
    max_record_bytes: int = MAX_TRACE_RECORD_BYTES,
) -> dict[str, Any]:
    """Stream a full trace into a compact trace, failing on truncation."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    max_compact_bytes = 0
    digest = hashlib.sha256()
    with destination.open("xb") as output:
        for row in iter_jsonl(source, max_record_bytes=max_record_bytes):
            if not verify_trace_row_hash(row):
                raise EvidenceFormatError(f"trace_row_hash_mismatch:row_{rows + 1}")
            if row.get("schema") == "AS017_ACCEPTANCE_TRACE_ROW_V1":
                # The production sink already emitted the acceptance projection.
                # Copy it losslessly so identity and omission provenance survive.
                compact = dict(row)
            else:
                compact = compact_acceptance_row(row)
                compact["source_trace_row_hash"] = row["trace_row_hash"]
                compact.pop("trace_row_hash", None)
                compact["trace_row_hash"] = trace_row_hash(compact)
            encoded = (json.dumps(compact, sort_keys=True, separators=(",", ":")) + "\n").encode()
            if len(encoded) > max_record_bytes:
                raise EvidenceFormatError(f"compact_record_exceeds_bound:row_{rows + 1}")
            output.write(encoded)
            digest.update(encoded)
            rows += 1
            max_compact_bytes = max(max_compact_bytes, len(encoded))
        output.flush()
        os.fsync(output.fileno())
    return {
        "schema": "AS017_ACCEPTANCE_TRACE_V1",
        "source_path": str(source),
        "compact_path": str(destination),
        "rows": rows,
        "max_compact_record_bytes": max_compact_bytes,
        "compact_sha256": digest.hexdigest(),
    }


class StageJournal:
    """Append-only, fsync-backed campaign accounting independent of CPJ."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = path.open("x", encoding="utf-8")

    def append(self, stage: str, **fields: Any) -> None:
        record = {
            "schema": "AS017_STAGE_RECORD_V1",
            "stage": stage,
            **fields,
        }
        encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        self._handle.write(encoded)
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        self._handle.close()


def summarize_stage_journal(path: Path) -> dict[str, Any]:
    """Read accounting with bounded memory and expose incomplete cases."""
    latest: dict[str, dict[str, Any]] = {}
    stage_counts: Counter[str] = Counter()
    records = 0
    expected_cases: int | None = None
    journal_status = "VALID"
    journal_error = None
    try:
        for row in iter_jsonl(path):
            records += 1
            stage = str(row.get("stage", "UNKNOWN"))
            stage_counts[stage] += 1
            if stage == "REGISTERED":
                registered_count = row.get("expected_cases", row.get("case_count"))
                if isinstance(registered_count, int) and registered_count >= 0:
                    expected_cases = registered_count
            case_id = row.get("case_id")
            if isinstance(case_id, str):
                latest[case_id] = row
    except EvidenceFormatError as exc:
        journal_status = "CORRUPTED"
        journal_error = str(exc)
    return {
        "schema": "AS017_STAGE_SUMMARY_V1",
        "journal_status": journal_status,
        "journal_error": journal_error,
        "records": records,
        "expected_cases": expected_cases,
        "stage_counts": dict(sorted(stage_counts.items())),
        "case_states": {case_id: row.get("stage", "UNKNOWN") for case_id, row in sorted(latest.items())},
        "incomplete_cases": sorted(
            case_id for case_id, row in latest.items()
            if row.get("stage") != "CASE_FINISHED"
            or set(row.get("required_artifacts", [])) < {
                "database", "compact_trace", "linkage_records", "linkage_summary", "case_result"
            }
            or not isinstance(row.get("case_result_sha256"), str)
        ),
        "completed_case_count": sum(row.get("stage") == "CASE_FINISHED" for row in latest.values()),
        "acceptance_ready": journal_status == "VALID" and expected_cases is not None
        and len(latest) == expected_cases and all(
            row.get("stage") == "CASE_FINISHED"
            and set(row.get("required_artifacts", [])) >= {
                "database", "compact_trace", "linkage_records", "linkage_summary", "case_result"
            }
            and isinstance(row.get("case_result_sha256"), str)
            for row in latest.values()
        ),
    }


def reduce_certificate_linkage(
    trace: Path,
    records_destination: Path,
    *,
    max_record_bytes: int = MAX_TRACE_RECORD_BYTES,
) -> dict[str, Any]:
    """Reduce compact trace rows without retaining linked records in memory."""
    records_destination.parent.mkdir(parents=True, exist_ok=True)
    statuses: Counter[str] = Counter()
    linked = 0
    trace_rows = 0
    digest = hashlib.sha256()
    with records_destination.open("x", encoding="utf-8") as output:
        for row in iter_jsonl(trace, max_record_bytes=max_record_bytes):
            trace_rows += 1
            if not verify_trace_row_hash(row):
                raise EvidenceFormatError(f"trace_row_hash_mismatch:row_{trace_rows}")
            kernel = row.get("viability_kernel")
            if not isinstance(kernel, dict):
                statuses["NO_VIABILITY_OBLIGATION"] += 1
                continue
            certificate = kernel.get("selected_recovery_certificate")
            if certificate is None:
                statuses["ABSENT_CERTIFICATE"] += 1
                continue
            continuation = row.get("recovery_certificate_continuation") or {}
            status = str(continuation.get("status", "UNMATCHED"))
            statuses[status] += 1
            record = {
                "tick": row.get("tick"),
                "certificate": certificate,
                "selected_candidate": row.get("final_candidate"),
                "governance_proposal": row.get("governance_proposal"),
                "governance_decision": row.get("governance_decision"),
                "verified_outcome": row.get("verified_outcome_linkage"),
                "continuation": continuation,
                "trace_row_hash": row.get("trace_row_hash"),
            }
            encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
            if len(encoded) > max_record_bytes:
                raise EvidenceFormatError(f"linkage_record_exceeds_bound:row_{trace_rows}")
            output.write(encoded.decode("utf-8"))
            digest.update(encoded)
            linked += 1
        output.flush()
        os.fsync(output.fileno())
    return {
        "schema": "AS017_RECOVERY_CERTIFICATE_LINKAGE_V2",
        "trace_path": str(trace),
        "records_path": str(records_destination),
        "trace_rows": trace_rows,
        "linked_records": linked,
        "status_counts": dict(sorted(statuses.items())),
        "records_sha256": digest.hexdigest(),
        "unmatched_count": statuses["UNMATCHED"],
    }


__all__ = [
    "CHUNK_SIZE",
    "MAX_TRACE_RECORD_BYTES",
    "EvidenceFormatError",
    "StageJournal",
    "compact_acceptance_row",
    "iter_jsonl",
    "publish_file_once",
    "publish_json_once",
    "reduce_acceptance_trace",
    "reduce_certificate_linkage",
    "summarize_stage_journal",
    "stream_sha256",
    "stream_bytes_equal",
    "trace_row_hash",
    "validate_sqlite_copy",
    "verify_trace_row_hash",
]
