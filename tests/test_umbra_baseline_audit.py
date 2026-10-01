from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from experiments.as018.full_config import config
from tools.as017_evidence import StageJournal, stream_sha256
from tools.as017_validate_v8c import _validate_database
from tools.umbra_baseline_audit import audit_population, validate_accounting, validate_database_copy, validate_trace_scope
from umbra_core.decision_trace import trace_row_hash
from umbra_core.runtime import create_organism


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "fixture.sqlite"
    cfg = config(88009999, path, "R0", ledger_overrides={"ledger_hot_tail_event_max": 32})
    cfg.snapshot_every = 1
    organism = create_organism(cfg)
    identity = organism.identity.as_dict()
    organism.run_ticks(4)
    organism.snapshot_if_due(force=True)
    # Disposable persistence fixture: leave a genuine anchored hot-tail event
    # after compaction, without running another organism tick.
    organism.store.append_event(agent_id=identity["agent_id"], event_type="audit_fixture",
                                monotonic_time=4.0, wall_time=1700000004.0,
                                payload={"fixture": True})
    organism.store.save_snapshot(identity["agent_id"], organism.store.last_sequence(),
                                 4, organism.authoritative_state())
    organism.close()
    return path, identity


def test_valid_copy_passes_and_original_bytes_do_not_change(database):
    path, identity = database
    digest = stream_sha256(path)
    report = validate_database_copy(path, digest, 4, 88009999, expected_identity=identity)
    assert report["verdict"] == "PASS", report
    assert stream_sha256(path) == digest


@pytest.mark.parametrize("mutation,reason", [
    ("UPDATE snapshots SET state_json='{}'", "snapshot_hash_mismatch"),
    ("UPDATE events SET payload='{}' WHERE sequence=(SELECT MIN(sequence) FROM events)", "payload_hash_mismatch"),
    ("UPDATE ledger_checkpoints SET checkpoint_hash='forged'", "checkpoint_hash_mismatch"),
])
def test_frozen_shape_check_accepts_tampering_new_copy_audit_rejects(database, tmp_path, mutation, reason):
    path, identity = database
    connection = sqlite3.connect(path)
    try:
        connection.execute(mutation)
        connection.commit()
    finally:
        connection.close()
    digest = stream_sha256(path)  # file checksum matches altered bytes, not authority
    scratch = tmp_path / "old"
    scratch.mkdir()
    old = _validate_database(path, digest, 4, scratch)
    assert old["verdict"] == "PASS", old
    new = validate_database_copy(path, digest, 4, 88009999, expected_identity=identity)
    assert new["verdict"] == "FAIL"
    assert any(reason in failure for failure in new["failures"]), new
    assert stream_sha256(path) == digest


def test_wrong_seed_identity_tick_and_file_binding_fail(database):
    path, identity = database
    report = validate_database_copy(path, "wrong", 5, 1, expected_identity={**identity, "agent_id": "other"})
    assert report["verdict"] == "FAIL"
    assert {"database_hash_mismatch", "birth_identity_mismatch", "terminal_tick_mismatch", "snapshot_seed_mismatch"} <= set(report["failures"])


def test_unbound_surviving_wal_is_not_silently_ignored(database):
    path, _ = database
    Path(str(path) + "-wal").write_bytes(b"synthetic")
    report = validate_database_copy(path, stream_sha256(path), 4, 88009999)
    assert report["verdict"] == "FAIL"
    assert "sidecar_binding_missing_or_mismatched:-wal" in report["failures"]


def row(tick=1):
    value = {"tick": tick, "active_ticks": tick, "physiology": {
        "energy": 0.8, "fatigue": 0.2, "integrity": 1.0, "stimulation": 0.4},
        "viability_kernel": None}
    value["trace_row_hash"] = trace_row_hash(value)
    return value


def write_rows(path, rows):
    path.write_text("".join(json.dumps(value) + "\n" for value in rows))


def test_exact_scope_accepts_ordinary_roots_without_requiring_recovery(tmp_path):
    path = tmp_path / "trace.jsonl"
    write_rows(path, [row(1), row(2)])
    assert validate_trace_scope(path, 2)["verdict"] == "PASS"


@pytest.mark.parametrize("rows,reason", [
    ([row(1), row(3)], "noncontiguous_tick"),
    ([row(1), row(1)], "noncontiguous_tick"),
    ([{**row(1), "trace_row_hash": "wrong"}], "row_hash"),
    ([row(1)], "trace_horizon_mismatch"),
])
def test_missing_duplicate_and_corrupted_records_fail(tmp_path, rows, reason):
    path = tmp_path / "trace.jsonl"
    write_rows(path, rows)
    report = validate_trace_scope(path, 2)
    assert report["verdict"] == "FAIL"
    assert any(reason in failure for failure in report["failures"])


def test_active_kernel_requires_real_rre_surface(tmp_path):
    path = tmp_path / "trace.jsonl"
    value = row()
    value["viability_kernel"] = {}
    value["trace_row_hash"] = trace_row_hash(value)
    write_rows(path, [value])
    assert "active_kernel_rre_unavailable:1" in validate_trace_scope(path, 1)["failures"]


def test_rre_schema_does_not_promote_uncertainty_or_grant_authority(tmp_path):
    path = tmp_path / "trace.jsonl"
    value = row()
    envelope = {"schema": "AS018_RECOVERY_REACHABILITY_FILTER_V1", "activation": False,
                "action_authority": False, "hidden_truth_fields": 0,
                "baseline": {"schema": "AS018_RECOVERY_REACHABILITY_ENVELOPE_V1", "status": "UNKNOWN_ROUTE",
                             "organism_tick": 1, "robust_now": False, "reserve_threatened": False}}
    value["viability_kernel"] = {"recovery_reachability_envelope": envelope}
    value["trace_row_hash"] = trace_row_hash(value)
    write_rows(path, [value])
    assert validate_trace_scope(path, 1)["verdict"] == "PASS"
    envelope["activation"] = True
    envelope["action_authority"] = True
    value["trace_row_hash"] = trace_row_hash(value)
    write_rows(path, [value])
    result = validate_trace_scope(path, 1)
    assert result["verdict"] == "FAIL"
    assert "unsupported_reserve_activation:1" in result["failures"]


def test_missing_population_stays_blocked_with_all_32_unknown(tmp_path):
    report = audit_population(tmp_path / "result.json", tmp_path / "stages.jsonl", tmp_path / "work")
    assert report["verdict"] == "BLOCKED"
    assert len(report["cases"]) == 32
    assert all(case["verdict"] == "BLOCKED" for case in report["cases"])
    assert report["formal_execution_performed"] is False


def test_accounting_requires_one_ordered_start_and_complete_artifact_bindings(tmp_path):
    path = tmp_path / "stages.jsonl"
    case = "R0-00-100001"
    journal = StageJournal(path)
    journal.append("REGISTERED", expected_cases=1)
    journal.append("REGISTERED_CASE", case_id=case)
    journal.append("STARTED", case_id=case, regime="R0", seed_index=0, seed=100001, target_ticks=7200)
    journal.append("EXECUTION_FINISHED", case_id=case)
    journal.append("VALIDATION_STARTED", case_id=case)
    journal.append("VALIDATION_STARTED", case_id=case, source_database="fixture.sqlite", source_trace="fixture.jsonl")
    artifacts = ["database", "compact_trace", "linkage_records", "linkage_summary", "case_result"]
    for name in artifacts[:-1]:
        journal.append("EXPORT_VERIFIED", case_id=case, artifact=name, sha256="a" * 64)
    journal.append("LOCALLY_VALIDATED", case_id=case)
    journal.append("EXPORT_VERIFIED", case_id=case, artifact="case_result", sha256="a" * 64)
    journal.append("CASE_FINISHED", case_id=case, required_artifacts=artifacts, case_result_sha256="a" * 64)
    journal.close()
    assert validate_accounting(path, {case: ("R0", 0, 100001)})["verdict"] == "PASS"
    with path.open("a") as handle:
        handle.write(json.dumps({"stage": "STARTED", "case_id": case}) + "\n")
    assert validate_accounting(path, {case: ("R0", 0, 100001)})["verdict"] == "FAIL"


def test_torn_journal_retains_valid_prefix_but_never_accepts(tmp_path):
    path = tmp_path / "stages.jsonl"
    path.write_text('{"stage":"REGISTERED","case_id":"R0-00-100001"}\n{"stage":')
    result = validate_accounting(path, {"R0-00-100001": ("R0", 0, 100001)})
    assert result["summary"]["records"] == 1
    assert result["verdict"] == "FAIL"


def test_journal_record_bound_stops_before_unbounded_accounting(tmp_path):
    path = tmp_path / "stages.jsonl"
    path.write_text('{"stage":"REGISTERED"}\n' * 5000)
    result = validate_accounting(path, {"R0-00-100001": ("R0", 0, 100001)})
    assert result["verdict"] == "FAIL"
    assert result["summary"]["records"] == 4097
    assert "journal_record_bound_exceeded" in result["summary"]["journal_error"]
