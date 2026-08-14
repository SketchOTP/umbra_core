from __future__ import annotations

import json
from pathlib import Path

from experiments.d012.formal_contract_v2 import (
    CONTRACT_FINGERPRINT,
    CONTRACT_V1,
    CONTRACT_VERSION,
    INTEGRITY_FAILURE,
    RECOVERY_FAILED,
    RECOVERY_SUCCESS,
    SAFE_DENIAL,
    normalize_trace_row,
    validate_contract_selection,
)
from experiments.d012.organism_worker import Worker
from experiments.d012.run_formal_p0 import (
    artifact_identity,
    formal_failure_from_metrics,
    write_readonly_postrun_validation,
)
from experiments.d012.worker_launcher import manifest_for
from umbra_core.identity import create_birth
from umbra_core.persistence import Store

from test_d013f_formal_contract_v2 import _row, _success


def _worker(tmp_path: Path, version: str = CONTRACT_VERSION) -> Worker:
    manifest = manifest_for(
        tmp_path,
        execution_id="umbra-d013g-non-formal-001",
        generation=1,
        ownership_generation=1,
        freeze_manifest_hash="fixture",
        active_runtime=0.0,
        formal_recovery_contract_version=version,
        contract_fingerprint=(CONTRACT_FINGERPRINT if version == CONTRACT_VERSION else None),
        formal_physiology_trace_path=str(tmp_path / "PHYSIOLOGY_TRACE.jsonl"),
        formal_recovery_trace_path=str(tmp_path / "RECOVERY_TRACE.jsonl"),
        formal_recovery_evaluation_trace_path=str(tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl"),
        formal_failure_path=str(tmp_path / "FIRST_FAILURE.json"),
    )
    return Worker(manifest)


def _live_denial_row() -> dict:
    row = dict(_row())
    for key in ("observation_signature", "new_evidence", "corrective_action", "recovery_blocked"):
        row.pop(key, None)
    row["observations"] = [{
        "observation_id": "live-obs-1",
        "observed_at": 10.0,
        "kind": "resource",
        "estimated_distance": 1.34,
        "confidence": 0.89,
        "uncertainty": 0.11,
    }]
    return row


def test_v2_safe_denial_crosses_worker_boundary_without_terminal_failure(tmp_path: Path):
    worker = _worker(tmp_path)
    worker.run_diagnostic_ticks = lambda count: [{
        **_live_denial_row(),
        "candidate_source": "recovery_reflex",
        "body_or_habitat_validation": "not_at_resource",
        "physiology_effect": {"energy": -0.003},
        "urgencies": {},
        "energy_drift": -0.002,
    }]

    worker.run_formal_tick()

    assert not (tmp_path / "FIRST_FAILURE.json").exists()
    evaluation = json.loads(
        (tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl").read_text().splitlines()[0]
    )
    assert evaluation["state"] == SAFE_DENIAL
    assert evaluation["contract_version"] == CONTRACT_VERSION


def test_v1_safe_denial_reproduces_historical_terminal_semantic(tmp_path: Path):
    worker = _worker(tmp_path, CONTRACT_V1)
    worker.run_diagnostic_ticks = lambda count: [{
        **_live_denial_row(),
        "candidate_source": "recovery_reflex",
        "body_or_habitat_validation": "not_at_resource",
        "physiology_effect": {"energy": -0.003},
        "urgencies": {},
        "energy_drift": -0.002,
    }]

    worker.run_formal_tick()

    failure = json.loads((tmp_path / "FIRST_FAILURE.json").read_text())
    assert failure["failure"] == "charge_selected_but_not_executable"


def test_runner_v2_boundary_cannot_be_preempted_by_legacy_safe_denial():
    metrics = {"formal_failure": {"failure": "charge_selected_but_not_executable", "triggering_state": _row()}}
    assert formal_failure_from_metrics(metrics, CONTRACT_VERSION) is None
    assert formal_failure_from_metrics(metrics, CONTRACT_V1) == "charge_selected_but_not_executable"


def test_actual_trace_normalization_derives_episode_facts():
    first = _row()
    first.pop("observation_signature")
    first.pop("new_evidence")
    first.pop("corrective_action")
    first.pop("recovery_blocked")
    first["observations"] = [{
        "observation_id": "obs-1",
        "observed_at": 10.0,
        "kind": "resource",
        "estimated_distance": 1.34,
        "confidence": 0.89,
        "uncertainty": 0.11,
    }]
    normalized = normalize_trace_row(first)
    repeated = normalize_trace_row(dict(first), normalized)
    assert normalized["observation_signature"]
    assert normalized["new_evidence"] is True
    assert repeated["new_evidence"] is False
    assert normalized["recovery_blocked"] is True


def test_v2_corrective_recovery_path_is_not_failed(tmp_path: Path):
    worker = _worker(tmp_path)
    approach = _row(
        selected_candidate="APPROACH",
        executed_capability="APPROACH",
        corrective_action=True,
        new_evidence=True,
        verified_outcome={
            "action_issued": True,
            "verified": True,
            "outcome": {
                "capability": "APPROACH",
                "success": True,
                "reason": "ok",
                "effects": {"energy": -0.004},
                "verified": True,
            },
        },
    )
    assert worker._record_v2_recovery_evaluation(_row()) is None
    assert worker._record_v2_recovery_evaluation(approach) is None
    assert worker._record_v2_recovery_evaluation(_success()) is None
    assert worker.recovery_episode_rows
    evaluation_rows = [
        json.loads(line)
        for line in (tmp_path / "P0_RECOVERY_EVALUATION_TRACE.jsonl").read_text().splitlines()
    ]
    assert evaluation_rows[-1]["state"] == RECOVERY_SUCCESS


def test_v2_pathological_repeat_fails_at_worker_boundary(tmp_path: Path):
    worker = _worker(tmp_path)
    assert worker._record_v2_recovery_evaluation(_row()) is None
    failure = worker._record_v2_recovery_evaluation(_row())
    assert failure is not None
    assert failure.startswith(RECOVERY_FAILED + ":")


def test_v2_integrity_failures_remain_immediate_at_worker_boundary(tmp_path: Path):
    cases = [
        _success(actual_distance=2.0, execution_boundary=1.5),
        _row(
            verified_outcome={
                "action_issued": True,
                "verified": True,
                "outcome": {
                    "capability": "CHARGE",
                    "success": False,
                    "reason": "not_at_resource",
                    "effects": {"energy": 0.10},
                    "verified": True,
                },
            },
            physiology_after_tick={"energy": 0.35, "fatigue": 0.45, "integrity": 0.98, "stimulation": 0.11},
        ),
        _row(critical_after_tick=True),
        _row(authority_bypass=True),
    ]
    for index, row in enumerate(cases):
        worker = _worker(tmp_path / str(index))
        assert worker._record_v2_recovery_evaluation(row).startswith(INTEGRITY_FAILURE + ":")


def test_v2_contract_fingerprint_is_required_and_exact():
    validate_contract_selection(CONTRACT_V1, None)
    validate_contract_selection(CONTRACT_VERSION, CONTRACT_FINGERPRINT)
    for fingerprint in (None, "wrong"):
        try:
            validate_contract_selection(CONTRACT_VERSION, fingerprint)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid V2 fingerprint accepted")


def test_future_artifact_identity_and_manifest_propagate_contract():
    identity = artifact_identity(
        directive_id="UMBRA-D-013G-FUTURE",
        execution_id="umbra-d013g-future-001",
        starting_commit="abc123",
        config_hash="config-hash",
        verdict_namespace="D013G",
        recovery_contract_version=CONTRACT_VERSION,
        contract_fingerprint=CONTRACT_FINGERPRINT,
    )
    assert identity["formal_recovery_contract_version"] == CONTRACT_VERSION
    assert identity["contract_fingerprint"] == CONTRACT_FINGERPRINT
    assert "D-012B" not in json.dumps(identity)


def test_future_manifest_and_readonly_artifact_carry_identity(tmp_path: Path):
    manifest = manifest_for(
        tmp_path,
        execution_id="umbra-d013g-future-001",
        generation=1,
        ownership_generation=1,
        freeze_manifest_hash="fixture",
        active_runtime=0.0,
        formal_recovery_contract_version=CONTRACT_VERSION,
        contract_fingerprint=CONTRACT_FINGERPRINT,
        directive="UMBRA-D-013G-FUTURE",
        starting_commit="abc123",
        configuration_fingerprint="config-hash",
        verdict_namespace="D013G",
    )
    assert manifest["formal_recovery_contract_version"] == CONTRACT_VERSION
    assert manifest["contract_fingerprint"] == CONTRACT_FINGERPRINT
    assert manifest["directive"] == "UMBRA-D-013G-FUTURE"

    db = tmp_path / "identity.sqlite"
    store = Store(db)
    identity = create_birth(created_at=1_700_000_000.0, seed=123)
    store.save_identity(identity)
    store.append_event(
        agent_id=identity.agent_id,
        event_type="birth",
        monotonic_time=0.0,
        wall_time=1_700_000_000.0,
        payload={"identity": identity.as_dict()},
        event_id=identity.birth_event_id,
    )
    store.close()
    artifact = write_readonly_postrun_validation(
        db,
        tmp_path / "P0_READONLY_POSTRUN_VALIDATION.json",
        {
            "directive": "UMBRA-D-013G-FUTURE",
            "formal_execution_id": "umbra-d013g-future-001",
            "starting_commit": "abc123",
            "configuration_fingerprint": "config-hash",
            "verdict_namespace": "D013G",
            "formal_recovery_contract_version": CONTRACT_VERSION,
            "contract_fingerprint": CONTRACT_FINGERPRINT,
        },
    )
    assert artifact["directive"] == "UMBRA-D-013G-FUTURE"
    assert artifact["mutating_api_used"] is False
