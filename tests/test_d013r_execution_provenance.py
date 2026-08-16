from __future__ import annotations

from experiments.d012.formal_contract_v2 import (
    INTEGRITY_FAILURE,
    RECOVERY_FAILED,
    RECOVERY_UNRESOLVED,
    SAFE_DENIAL,
    classify_attempt,
    evaluate_episode,
    normalize_trace_row,
)

from test_d013f_formal_contract_v2 import _row


def _authority_row(
    *,
    selected: str,
    executed: str,
    governance: str,
    verified: str,
    success: bool,
    reason: str,
):
    row = _row(
        selected_candidate=selected,
        executed_capability=executed,
        governance={"admitted": True, "capability": governance, "stage_failed": None},
        verified_outcome={
            "action_issued": True,
            "verified": True,
            "capability": verified,
            "success": success,
            "reason": reason,
            "effects": {"energy": 0.0 if not success else -0.004},
            "verified": True,
        },
    )
    if success:
        row["embodiment_validation"] = "ok"
        row["physiology_effect"] = {"energy": -0.004}
    return row


def test_selected_charge_does_not_override_authoritative_rest_denial():
    row = _authority_row(
        selected="CHARGE",
        executed="REST",
        governance="REST",
        verified="REST",
        success=False,
        reason="not_at_rest",
    )
    normalized = normalize_trace_row(row)
    result = classify_attempt(normalized)
    assert normalized["attempt_capability"] == "REST"
    assert result["capability"] == "REST"
    assert result["state"] == RECOVERY_UNRESOLVED
    assert "denial_reason_not_authoritative" not in result["reasons"]


def test_selected_manipulate_does_not_override_authoritative_rest_denial():
    result = classify_attempt(
        _authority_row(
            selected="MANIPULATE",
            executed="REST",
            governance="REST",
            verified="REST",
            success=False,
            reason="not_at_rest",
        )
    )
    assert result["capability"] == "REST"
    assert result["state"] == RECOVERY_UNRESOLVED


def test_corrective_semantics_follow_authoritative_approach():
    row = _authority_row(
        selected="MOVE",
        executed="APPROACH",
        governance="APPROACH",
        verified="APPROACH",
        success=True,
        reason="ok",
    )
    normalized = normalize_trace_row(row)
    result = classify_attempt(normalized)
    assert normalized["attempt_capability"] == "APPROACH"
    assert normalized["corrective_action"] is True
    assert result["capability"] == "APPROACH"
    assert result["state"] == RECOVERY_UNRESOLVED


def test_executed_and_verified_capability_disagreement_fails_closed():
    result = classify_attempt(
        _authority_row(
            selected="REST",
            executed="REST",
            governance="REST",
            verified="CHARGE",
            success=False,
            reason="not_at_resource",
        )
    )
    assert result["state"] == INTEGRITY_FAILURE
    assert "capability_provenance_mismatch:executed_vs_verified" in result["reasons"]


def test_governance_and_execution_capability_disagreement_fails_closed():
    result = classify_attempt(
        _authority_row(
            selected="CHARGE",
            executed="REST",
            governance="CHARGE",
            verified="REST",
            success=False,
            reason="not_at_rest",
        )
    )
    assert result["state"] == INTEGRITY_FAILURE
    assert "capability_provenance_mismatch:governance_vs_executed" in result["reasons"]


def test_historical_charge_denial_remains_safe_denial():
    result = classify_attempt(
        _authority_row(
            selected="CHARGE",
            executed="CHARGE",
            governance="CHARGE",
            verified="CHARGE",
            success=False,
            reason="not_at_resource",
        )
    )
    assert result["state"] == SAFE_DENIAL


def test_historical_repeated_charge_denial_still_fails_without_correction():
    row = _authority_row(
        selected="CHARGE",
        executed="CHARGE",
        governance="CHARGE",
        verified="CHARGE",
        success=False,
        reason="not_at_resource",
    )
    result = evaluate_episode([row, dict(row)])
    assert result["terminal_state"] == RECOVERY_FAILED


def test_d013o_critical_boundary_failure_remains_integrity_failure():
    row = _authority_row(
        selected="REST",
        executed="REST",
        governance="REST",
        verified="REST",
        success=False,
        reason="not_at_rest",
    )
    row["critical_after_tick"] = True
    result = classify_attempt(row)
    assert result["state"] == INTEGRITY_FAILURE
    assert "physiology_integrity_or_critical_boundary" in result["reasons"]
