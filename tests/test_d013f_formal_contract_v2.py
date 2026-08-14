from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from experiments.d012.formal_contract_v2 import (
    INTEGRITY_FAILURE,
    RECOVERY_FAILED,
    RECOVERY_SUCCESS,
    SAFE_DENIAL,
    classify_attempt,
    evaluate_episode,
    future_formal_metadata,
)
from experiments.d012.run_formal_p0 import artifact_identity
from experiments.d012.readonly_validation import validate_read_only
from umbra_core.identity import create_birth
from umbra_core.persistence import Store


def _row(**overrides):
    row = {
        "event_types": ["physiology_drift", "proposal", "outcome_verified"],
        "selected_candidate": "CHARGE",
        "governance": {"admitted": True, "stage_failed": None},
        "verified_outcome": {
            "action_issued": True,
            "verified": True,
            "outcome": {
                "capability": "CHARGE",
                "success": False,
                "reason": "not_at_resource",
                "effects": {"energy": -0.003},
                "verified": True,
            },
        },
        "available_recovery_affordances": [{"kind": "resource", "executable": False}],
        "physiology_before_tick": {"energy": 0.25, "fatigue": 0.45, "integrity": 0.98, "stimulation": 0.11},
        "physiology_after_tick": {"energy": 0.244, "fatigue": 0.452, "integrity": 0.979, "stimulation": 0.108},
        "critical_before_tick": False,
        "critical_after_tick": False,
        "observation_signature": "resource:1.34",
        "new_evidence": False,
        "corrective_action": False,
        "recovery_blocked": True,
    }
    row.update(overrides)
    return row


def _success(**overrides):
    row = _row(
        selected_candidate="CHARGE",
        embodiment_validation="ok",
        available_recovery_affordances=[{"kind": "resource", "executable": True}],
        physiology_effect={"energy": 0.20},
        physiology_after_tick={"energy": 0.444, "fatigue": 0.40, "integrity": 0.98, "stimulation": 0.11},
        verified_outcome={
            "action_issued": True,
            "verified": True,
            "outcome": {
                "capability": "CHARGE", "success": True, "reason": "ok",
                "effects": {"energy": 0.20}, "verified": True,
            },
        },
    )
    row.update(overrides)
    return row


def test_d013d_replay_is_safe_denial_not_viability_failure():
    result = classify_attempt(_row())
    assert result["state"] == SAFE_DENIAL


def test_unsafe_execution_and_false_positive_credit_remain_failures():
    assert classify_attempt(_success(actual_distance=2.0, execution_boundary=1.5))["state"] == INTEGRITY_FAILURE
    assert classify_attempt(_row(
        verified_outcome={
            "action_issued": True, "verified": True,
            "outcome": {"capability": "CHARGE", "success": False, "reason": "not_at_resource", "effects": {"energy": 0.10}, "verified": True},
        },
        physiology_after_tick={"energy": 0.35, "fatigue": 0.45, "integrity": 0.98, "stimulation": 0.11},
    ))["state"] == INTEGRITY_FAILURE


def test_pathological_repetition_fails_without_new_evidence():
    result = evaluate_episode([_row(), _row()])
    assert result["terminal_state"] == RECOVERY_FAILED
    assert result["states"][-1]["reasons"] == ["repeated_denial_without_new_evidence_or_correction"]


def test_critical_floor_and_authority_corruption_remain_failures():
    assert classify_attempt(_row(critical_after_tick=True))["state"] == INTEGRITY_FAILURE
    assert classify_attempt(_row(authority_bypass=True))["state"] == INTEGRITY_FAILURE


def test_successful_charge_is_verified_recovery_success():
    assert classify_attempt(_success())["state"] == RECOVERY_SUCCESS


def test_denial_then_corrective_action_then_new_evidence_can_recover():
    approach = _row(
        selected_candidate="APPROACH",
        observation_signature="resource:1.34->0.9",
        new_evidence=True,
        corrective_action=True,
        verified_outcome={
            "action_issued": True, "verified": True,
            "outcome": {"capability": "APPROACH", "success": True, "reason": "ok", "effects": {"energy": -0.004}, "verified": True},
        },
        available_recovery_affordances=[{"kind": "resource", "executable": False}],
    )
    result = evaluate_episode([_row(), approach, _success()])
    assert result["states"][0]["state"] == SAFE_DENIAL
    assert result["terminal_state"] == RECOVERY_SUCCESS


def test_future_metadata_does_not_leak_d012b_labels():
    metadata = future_formal_metadata(
        directive_id="UMBRA-D-013F-FUTURE",
        formal_execution_id="umbra-d013f-future-001",
        baseline_commit="abc123",
        configuration_fingerprint="config-hash",
        verdict_namespace="D013F",
        allowed_terminal_verdicts=["D013F_P0_VIABILITY_PASS", "D013F_P0_VIABILITY_FAIL"],
    )
    raw = json.dumps(metadata)
    assert metadata["directive"] == "UMBRA-D-013F-FUTURE"
    assert metadata["verdict_namespace"] == "D013F"
    assert "D-012B" not in raw
    assert "UMBRA_D012B" not in raw


def test_formal_runner_artifact_identity_uses_future_campaign_namespace():
    identity = artifact_identity(
        directive_id="UMBRA-D-013F-FUTURE",
        execution_id="umbra-d013f-future-001",
        starting_commit="abc123",
        config_hash="config-hash",
        verdict_namespace="D013F",
    )
    assert identity["directive"] == "UMBRA-D-013F-FUTURE"
    assert identity["formal_execution_id"] == "umbra-d013f-future-001"
    assert identity["verdict_namespace"] == "D013F"
    assert "D-012B" not in json.dumps(identity)


def test_read_only_validator_does_not_mutate_database(tmp_path: Path):
    db = tmp_path / "organism.sqlite"
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
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    before_state = sqlite3.connect(db)
    before_count = before_state.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    before_tip = before_state.execute("SELECT value FROM meta WHERE key='ledger_tip'").fetchone()[0]
    before_snapshots = before_state.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    before_state.close()

    result = validate_read_only(db)

    after_state = sqlite3.connect(db)
    assert after_state.execute("SELECT COUNT(*) FROM events").fetchone()[0] == before_count
    assert after_state.execute("SELECT value FROM meta WHERE key='ledger_tip'").fetchone()[0] == before_tip
    assert after_state.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == before_snapshots
    assert after_state.execute("SELECT COUNT(*) FROM events WHERE event_type='runtime_ready'").fetchone()[0] == 0
    after_state.close()
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    assert result["mutating_api_used"] is False
