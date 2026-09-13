from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tracemalloc

import pytest

from tools.as017_evidence import (
    EvidenceFormatError,
    StageJournal,
    iter_jsonl,
    publish_file_once,
    publish_json_once,
    reduce_acceptance_trace,
    reduce_certificate_linkage,
    summarize_stage_journal,
    stream_sha256,
    trace_row_hash,
    validate_sqlite_copy,
)
from umbra_core.decision_trace import DecisionTraceSink


def test_stream_hash_and_copy_match_standard_sha256(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes((b"0123456789abcdef" * 400_000) + b"tail")
    destination = tmp_path / "destination.bin"

    expected = stream_sha256(source)
    assert stream_sha256(source) == expected
    assert publish_file_once(source, destination) == expected
    assert destination.read_bytes() == source.read_bytes()


def test_file_processing_memory_is_bounded_by_chunk_size(tmp_path: Path) -> None:
    source = tmp_path / "large.bin"
    with source.open("wb") as handle:
        for _ in range(8):
            handle.write(b"bounded-chunk\n" * 100_000)
    destination = tmp_path / "large-copy.bin"
    tracemalloc.start()
    try:
        publish_file_once(source, destination)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 4 * 1024 * 1024


def test_compact_trace_does_not_retain_diagnostic_competition_bulk(tmp_path: Path) -> None:
    trace = tmp_path / "trace.jsonl"
    sink = DecisionTraceSink(str(trace), mode="compact_acceptance")
    sink.record(
        {
            "tick": 1,
            "decision_cycle": True,
            "physiology": {"energy": 0.8, "fatigue": 0.2, "integrity": 1.0, "stimulation": 0.7},
            "final_candidate": {"capability": "IDLE", "params": {}},
            "distributed_competition": {
                "schema": "bulk",
                "attempts": [{"payload": "x" * 10_000} for _ in range(100)],
                "selected_identity": "idle",
                "frontier_size": 1,
            },
        }
    )
    sink.close()
    row = json.loads(trace.read_text())
    assert row["schema"] == "AS017_ACCEPTANCE_TRACE_ROW_V1"
    assert "distributed_competition" not in row
    assert row["distributed_competition_summary"]["frontier_size"] == 1
    assert row["omitted_diagnostic_fields"]["distributed_competition"] is True


def test_trace_reduction_rejects_truncated_record(tmp_path: Path) -> None:
    source = tmp_path / "truncated.jsonl"
    first = {"tick": 1}
    first["trace_row_hash"] = trace_row_hash(first)
    source.write_text(json.dumps(first) + '\n{"tick":2', encoding="utf-8")
    with pytest.raises(EvidenceFormatError, match="invalid_json:line_2"):
        reduce_acceptance_trace(source, tmp_path / "compact.jsonl")


def test_compact_export_preserves_authenticated_identity_and_rejects_mutation(tmp_path: Path) -> None:
    source = tmp_path / "compact.jsonl"
    sink = DecisionTraceSink(str(source), mode="compact_acceptance")
    sink.record({"tick": 1, "final_candidate": {"capability": "IDLE", "params": {}}})
    sink.close()
    destination = tmp_path / "exported.jsonl"
    reduce_acceptance_trace(source, destination)
    original = json.loads(source.read_text())
    exported = json.loads(destination.read_text())
    assert exported["trace_row_hash"] == original["trace_row_hash"]
    assert exported["omitted_diagnostic_fields"] == original["omitted_diagnostic_fields"]

    altered = tmp_path / "altered.jsonl"
    altered_row = dict(original)
    altered_row["tick"] = 2
    altered.write_text(json.dumps(altered_row) + "\n")
    with pytest.raises(EvidenceFormatError, match="trace_row_hash_mismatch"):
        reduce_acceptance_trace(altered, tmp_path / "altered-export.jsonl")


def test_missing_trace_identity_is_rejected_by_linkage_reducer(tmp_path: Path) -> None:
    source = tmp_path / "missing-hash.jsonl"
    source.write_text(json.dumps({"tick": 1}) + "\n", encoding="utf-8")
    with pytest.raises(EvidenceFormatError, match="trace_row_hash_mismatch"):
        reduce_certificate_linkage(source, tmp_path / "records.jsonl")


def test_linkage_reduction_streams_records_and_reports_scope(tmp_path: Path) -> None:
    source = tmp_path / "compact.jsonl"
    first = {"tick": 1, "decision_cycle": True}
    second = {
        "tick": 2,
        "viability_kernel": {
            "selected_recovery_certificate": {"status": "PROVEN", "root_id": "r1"}
        },
        "final_candidate": {"capability": "CHARGE", "params": {}},
        "governance_proposal": {"proposal_id": "p1"},
        "governance_decision": {"admitted": True},
        "verified_outcome_linkage": {"verified_outcome_id": "o1"},
        "recovery_certificate_continuation": {"status": "NEXT_ROOT_REVALIDATION_REQUIRED"},
    }
    second["trace_row_hash"] = trace_row_hash(second)
    first["trace_row_hash"] = trace_row_hash(first)
    source.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
    records = tmp_path / "records.jsonl"
    summary = reduce_certificate_linkage(source, records)
    assert summary["trace_rows"] == 2
    assert summary["linked_records"] == 1
    assert summary["status_counts"] == {
        "NEXT_ROOT_REVALIDATION_REQUIRED": 1,
        "NO_VIABILITY_OBLIGATION": 1,
    }
    assert len(records.read_text().splitlines()) == 1


def test_stage_journal_is_append_only_and_fsync_backed(tmp_path: Path) -> None:
    path = tmp_path / "stages.jsonl"
    journal = StageJournal(path)
    journal.append("REGISTERED", case_count=16)
    journal.append("STARTED", case_id="R0-00-1", pid=123)
    journal.close()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["stage"] for row in rows] == ["REGISTERED", "STARTED"]
    assert rows[1]["case_id"] == "R0-00-1"


def test_stage_summary_keeps_interrupted_case_unresolved(tmp_path: Path) -> None:
    path = tmp_path / "stages.jsonl"
    journal = StageJournal(path)
    journal.append("REGISTERED", case_count=1)
    journal.append("STARTED", case_id="R0-00-1", pid=123)
    journal.close()
    summary = summarize_stage_journal(path)
    assert summary["case_states"] == {"R0-00-1": "STARTED"}
    assert summary["incomplete_cases"] == ["R0-00-1"]


@pytest.mark.parametrize(
    ("stages", "complete"),
    [
        (["STARTED"], False),
        (["STARTED", "EXECUTION_FINISHED"], False),
        (["STARTED", "EXECUTION_FINISHED", "LOCALLY_VALIDATED", "EXPORT_PENDING"], False),
        (["STARTED", "EXECUTION_FINISHED", "LOCALLY_VALIDATED", "EXPORT_STARTED", "EXPORT_VERIFIED", "CASE_FINISHED"], True),
    ],
)
def test_stage_summary_distinguishes_execution_from_export(
    tmp_path: Path, stages: list[str], complete: bool
) -> None:
    path = tmp_path / "stages.jsonl"
    journal = StageJournal(path)
    journal.append("REGISTERED", case_count=1)
    for stage in stages:
        journal.append(stage, case_id="R0-00-1")
    journal.close()
    summary = summarize_stage_journal(path)
    assert (summary["incomplete_cases"] == []) is complete


def test_disappeared_worker_at_export_boundary_remains_incomplete(tmp_path: Path) -> None:
    journal_path = tmp_path / "worker.stages.jsonl"
    worker_code = """
from pathlib import Path
import os
from tools.as017_evidence import StageJournal
j = StageJournal(Path(__import__('sys').argv[1]))
j.append('REGISTERED', case_count=1)
j.append('STARTED', case_id='R0-00-1')
j.append('EXECUTION_FINISHED', case_id='R0-00-1')
j.append('LOCALLY_VALIDATED', case_id='R0-00-1')
j.append('EXPORT_STARTED', case_id='R0-00-1', artifact='database')
os._exit(23)
"""
    completed = subprocess.run([sys.executable, "-c", worker_code, str(journal_path)])
    assert completed.returncode == 23
    summary = summarize_stage_journal(journal_path)
    assert summary["journal_status"] == "VALID"
    assert summary["case_states"] == {"R0-00-1": "EXPORT_STARTED"}
    assert summary["incomplete_cases"] == ["R0-00-1"]
    assert summary["acceptance_ready"] is False


def test_torn_journal_is_explicitly_corrupt_and_not_acceptance_ready(tmp_path: Path) -> None:
    path = tmp_path / "torn.stages.jsonl"
    journal = StageJournal(path)
    journal.append("REGISTERED", case_count=1)
    journal.append("STARTED", case_id="R0-00-1")
    journal.close()
    with path.open("ab") as handle:
        handle.write(b'{"stage":"CASE_FINISHED"')
    summary = summarize_stage_journal(path)
    assert summary["journal_status"] == "CORRUPTED"
    assert summary["acceptance_ready"] is False


def test_compact_reduce_export_linkage_and_case_close_are_one_chain(tmp_path: Path) -> None:
    full_trace = tmp_path / "trace.jsonl"
    sink = DecisionTraceSink(str(full_trace), mode="compact_acceptance")
    sink.record(
        {
            "tick": 1,
            "viability_kernel": {"selected_recovery_certificate": {"status": "PROVEN"}},
            "final_candidate": {"capability": "CHARGE", "params": {}},
            "governance_proposal": {"proposal_id": "p1"},
            "governance_decision": {"admitted": True},
            "verified_outcome_linkage": {"verified_outcome_id": "o1"},
            "recovery_certificate_continuation": {"status": "PROVEN"},
        }
    )
    sink.close()
    compact = tmp_path / "compact.jsonl"
    reduced = reduce_acceptance_trace(full_trace, compact)
    exported = tmp_path / "exported.jsonl"
    publish_file_once(compact, exported)
    linkage = reduce_certificate_linkage(exported, tmp_path / "linkage.jsonl")
    assert reduced["rows"] == 1
    assert linkage["linked_records"] == 1

    journal_path = tmp_path / "chain.stages.jsonl"
    journal = StageJournal(journal_path)
    journal.append("REGISTERED", case_count=1)
    journal.append("STARTED", case_id="R0-00-1")
    journal.append("EXECUTION_FINISHED", case_id="R0-00-1")
    journal.append("LOCALLY_VALIDATED", case_id="R0-00-1")
    journal.append("EXPORT_VERIFIED", case_id="R0-00-1", artifact="database")
    journal.append("EXPORT_VERIFIED", case_id="R0-00-1", artifact="compact_trace")
    journal.append("EXPORT_VERIFIED", case_id="R0-00-1", artifact="linkage_records")
    journal.append("CASE_FINISHED", case_id="R0-00-1", linkage_records=linkage["linked_records"])
    journal.close()
    assert summarize_stage_journal(journal_path)["acceptance_ready"] is True


def test_json_publication_readback_does_not_use_path_read_bytes(tmp_path: Path) -> None:
    destination = tmp_path / "result.json"
    digest = publish_json_once(destination, {"terminal": "ok", "rows": 1})
    assert digest == hashlib.sha256(destination.read_bytes()).hexdigest()


def test_oversized_jsonl_record_is_rejected_before_full_line_allocation(tmp_path: Path) -> None:
    source = tmp_path / "oversized.jsonl"
    source.write_bytes(b'{"payload":"' + (b"x" * (16 * 1024 * 1024)) + b'"}\n')
    tracemalloc.start()
    try:
        with pytest.raises(EvidenceFormatError, match="record_exceeds_bound"):
            list(iter_jsonl(source))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 10 * 1024 * 1024


def test_sqlite_local_validation_checks_integrity_and_foreign_keys(tmp_path: Path) -> None:
    database = tmp_path / "valid.sqlite"
    import sqlite3
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES ('ok')")
    assert validate_sqlite_copy(database) == {"integrity_check": "ok", "foreign_key_check_rows": 0}
