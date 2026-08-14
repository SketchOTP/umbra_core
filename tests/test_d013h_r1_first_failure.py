from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.d012.failure_codes import SupervisionError
from experiments.d012.organism_worker import Worker
from experiments.d012.run_formal_p0 import (
    REQUIRED_OUTPUTS,
    V2_REQUIRED_OUTPUTS,
    evaluator_initialization_record,
    publish_evidence,
    publish_evidence_preserving_first_failure,
    write_readonly_postrun_validation,
)
from experiments.d012.formal_contract_v2 import CONTRACT_FINGERPRINT, CONTRACT_VERSION

from test_d013h_v2_formal_readiness import _denial, _manifest


def _identity() -> dict[str, str]:
    return {
        "directive": "UMBRA-D-013H-R1",
        "formal_execution_id": "umbra-d013h-r1-non-formal-001",
        "starting_commit": "6bdf157b736e352ee9f170b40d6803b0074bcc58",
        "configuration_fingerprint": "r1-config",
        "verdict_namespace": "D013H_R1",
        "formal_recovery_contract_version": CONTRACT_VERSION,
        "contract_fingerprint": CONTRACT_FINGERPRINT,
    }


def _write_base_outputs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_OUTPUTS:
        (path / name).write_text("NON_FORMAL_TEST\n")


def _write_v2_bundle(path: Path, *, include_trace: bool = True) -> dict[str, str]:
    identity = _identity()
    _write_base_outputs(path)
    (path / "P0_READONLY_POSTRUN_VALIDATION.json").write_text(
        json.dumps(identity) + "\n"
    )
    if include_trace:
        (path / "P0_RECOVERY_EVALUATION_TRACE.jsonl").write_text(
            json.dumps(evaluator_initialization_record(identity)) + "\n"
        )
    return identity


def _init_trace(manifest: dict[str, object], path: Path) -> None:
    identity = {
        "directive": str(manifest["directive"]),
        "formal_execution_id": str(manifest["execution_id"]),
        "starting_commit": str(manifest["starting_commit"]),
        "configuration_fingerprint": str(manifest["configuration_fingerprint"]),
        "verdict_namespace": str(manifest["verdict_namespace"]),
        "formal_recovery_contract_version": str(
            manifest["formal_recovery_contract_version"]
        ),
        "contract_fingerprint": str(manifest["contract_fingerprint"]),
    }
    path.write_text(json.dumps(evaluator_initialization_record(identity)) + "\n")


def test_v2_evaluator_init_is_written_before_recovery_evaluation(tmp_path: Path):
    manifest = _manifest(tmp_path)
    trace = tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    _init_trace(manifest, trace)
    worker = Worker(manifest)
    assert json.loads(trace.read_text().splitlines()[0])["record_type"] == "EVALUATOR_INIT"
    assert worker.recovery_episode_rows == []
    worker._record_v2_recovery_evaluation(_denial("obs-1", 1.0, 4.0))
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    assert [record["record_type"] for record in records] == [
        "EVALUATOR_INIT",
        "RECOVERY_EVALUATION",
    ]


def test_v2_evaluator_init_carries_exact_campaign_identity(tmp_path: Path):
    manifest = _manifest(tmp_path)
    trace = tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    _init_trace(manifest, trace)
    record = json.loads(trace.read_text())
    assert record["directive"] == manifest["directive"]
    assert record["formal_execution_id"] == manifest["execution_id"]
    assert record["starting_commit"] == manifest["starting_commit"]
    assert record["configuration_fingerprint"] == manifest["configuration_fingerprint"]
    assert record["contract_version"] == CONTRACT_VERSION
    assert record["contract_fingerprint"] == CONTRACT_FINGERPRINT


def test_v2_init_is_not_loaded_as_recovery_episode(tmp_path: Path):
    manifest = _manifest(tmp_path)
    trace = tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    _init_trace(manifest, trace)
    worker = Worker(manifest)
    assert worker.recovery_episode_rows == []


def test_replacement_worker_loads_recovery_rows_after_init(tmp_path: Path):
    trace = tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    first_manifest = _manifest(tmp_path, generation=1, trace_path=trace)
    _init_trace(first_manifest, trace)
    first = Worker(first_manifest)
    first._record_v2_recovery_evaluation(_denial("obs-1", 1.0, 4.0))
    replacement = Worker(_manifest(tmp_path, generation=2, trace_path=trace))
    assert len(replacement.recovery_episode_rows) == 1
    assert replacement.recovery_episode_rows[0] == first.recovery_episode_rows[0]


def test_conflicting_second_init_fails_closed(tmp_path: Path):
    manifest = _manifest(tmp_path)
    trace = tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"
    _init_trace(manifest, trace)
    conflicting = dict(json.loads(trace.read_text()))
    conflicting["formal_execution_id"] = "other-campaign"
    with trace.open("a") as handle:
        handle.write(json.dumps(conflicting) + "\n")
    with pytest.raises(SupervisionError, match="evaluator_trace_identity:formal_execution_id"):
        Worker(manifest)


def test_zero_recovery_v2_campaign_publishes_init_only_trace(tmp_path: Path):
    work = tmp_path / "work"
    final = tmp_path / "final"
    identity = _write_v2_bundle(work)
    publish_evidence(work, final, CONTRACT_VERSION, identity=identity)
    records = (final / "P0_RECOVERY_EVALUATION_TRACE.jsonl").read_text().splitlines()
    assert len(records) == 1
    assert json.loads(records[0])["record_type"] == "EVALUATOR_INIT"


def test_non_recovery_first_failure_survives_successful_closeout(tmp_path: Path):
    work = tmp_path / "work"
    final = tmp_path / "final"
    identity = _write_v2_bundle(work)
    verdict, first, secondary = publish_evidence_preserving_first_failure(
        work,
        final,
        CONTRACT_VERSION,
        identity=identity,
        verdict="D013H_R1_P0_ABORTED",
        first_failure="organism_identity_changed",
        integrity_verdict="D013H_R1_INTEGRITY_FAIL",
    )
    assert (final / "P0_RECOVERY_EVALUATION_TRACE.jsonl").exists()
    assert (verdict, first, secondary) == (
        "D013H_R1_P0_ABORTED",
        "organism_identity_changed",
        [],
    )


def test_first_failure_survives_later_publication_failure(tmp_path: Path):
    work = tmp_path / "work"
    identity = _write_v2_bundle(work, include_trace=False)
    verdict, first, secondary = publish_evidence_preserving_first_failure(
        work,
        tmp_path / "final",
        CONTRACT_VERSION,
        identity=identity,
        verdict="D013H_R1_P0_ABORTED",
        first_failure="organism_identity_changed",
        integrity_verdict="D013H_R1_INTEGRITY_FAIL",
    )
    assert verdict == "D013H_R1_P0_ABORTED"
    assert first == "organism_identity_changed"
    assert secondary and secondary[0]["stage"] == "evidence_publication"


def test_publication_failure_without_prior_failure_is_terminal(tmp_path: Path):
    work = tmp_path / "work"
    identity = _write_v2_bundle(work, include_trace=False)
    verdict, first, secondary = publish_evidence_preserving_first_failure(
        work,
        tmp_path / "final",
        CONTRACT_VERSION,
        identity=identity,
        verdict="D013H_R1_P0_RUNNING",
        first_failure=None,
        integrity_verdict="D013H_R1_INTEGRITY_FAIL",
    )
    assert verdict == "D013H_R1_INTEGRITY_FAIL"
    assert first == "evidence_publication:SupervisionError"
    assert secondary == []


def test_predatabase_termination_writes_not_applicable_identity_bound_artifact(tmp_path: Path):
    output = tmp_path / "P0_READONLY_POSTRUN_VALIDATION.json"
    result = write_readonly_postrun_validation(tmp_path / "missing.sqlite", output, _identity())
    assert result["validation_status"] == "NOT_APPLICABLE_DATABASE_NOT_CREATED"
    assert result["database_exists"] is False
    assert result["mutating_api_used"] is False
    assert json.loads(output.read_text())["formal_execution_id"] == _identity()["formal_execution_id"]


def test_readonly_failure_artifact_retains_campaign_identity(tmp_path: Path):
    database = tmp_path / "broken.sqlite"
    database.write_text("not sqlite")
    result = write_readonly_postrun_validation(
        database, tmp_path / "P0_READONLY_POSTRUN_VALIDATION.json", _identity()
    )
    assert result["validation_status"] == "FAIL"
    assert result["mutating_api_used"] is False
    assert result["formal_execution_id"] == _identity()["formal_execution_id"]
    assert result["contract_fingerprint"] == CONTRACT_FINGERPRINT


def test_v1_publication_behavior_remains_unchanged(tmp_path: Path):
    work = tmp_path / "work"
    final = tmp_path / "final"
    _write_base_outputs(work)
    publish_evidence(work, final, "P0_RECOVERY_CONTRACT_V1")
    assert not any((final / name).exists() for name in V2_REQUIRED_OUTPUTS)
