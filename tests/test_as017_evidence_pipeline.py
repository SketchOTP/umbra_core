from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tracemalloc

import pytest

from tools.as017_evidence import (
    EvidenceFormatError,
    StageJournal,
    publish_file_once,
    publish_json_once,
    reduce_acceptance_trace,
    reduce_certificate_linkage,
    summarize_stage_journal,
    stream_sha256,
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
    source.write_text('{"tick":1}\n{"tick":2', encoding="utf-8")
    with pytest.raises(EvidenceFormatError, match="invalid_json:line_2"):
        reduce_acceptance_trace(source, tmp_path / "compact.jsonl")


def test_linkage_reduction_streams_records_and_reports_scope(tmp_path: Path) -> None:
    source = tmp_path / "compact.jsonl"
    source.write_text(
        json.dumps({"tick": 1, "decision_cycle": True})
        + "\n"
        + json.dumps(
            {
                "tick": 2,
                "viability_kernel": {
                    "selected_recovery_certificate": {"status": "PROVEN", "root_id": "r1"}
                },
                "final_candidate": {"capability": "CHARGE", "params": {}},
                "governance_proposal": {"proposal_id": "p1"},
                "governance_decision": {"admitted": True},
                "verified_outcome_linkage": {"verified_outcome_id": "o1"},
                "recovery_certificate_continuation": {"status": "NEXT_ROOT_REVALIDATION_REQUIRED"},
                "trace_row_hash": "row-2",
            }
        )
        + "\n",
        encoding="utf-8",
    )
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
        (["STARTED", "EXECUTION_FINISHED", "LOCALLY_VALIDATED", "EXPORT_STARTED", "EXPORT_VERIFIED"], True),
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


def test_json_publication_readback_does_not_use_path_read_bytes(tmp_path: Path) -> None:
    destination = tmp_path / "result.json"
    digest = publish_json_once(destination, {"terminal": "ok", "rows": 1})
    assert digest == hashlib.sha256(destination.read_bytes()).hexdigest()
