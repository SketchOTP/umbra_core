"""Read-only evaluator for the versioned P0 recovery contract.

This module evaluates recorded evidence. It is deliberately not imported by
the organism runtime and never changes organism state or formal databases.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


CONTRACT_VERSION = "P0_RECOVERY_CONTRACT_V2"
VERDICT_NAMESPACE = "D013F"
SAFE_DENIAL = "SAFE_DENIED_RECOVERY_ATTEMPT"
INTEGRITY_FAILURE = "RECOVERY_INTEGRITY_FAILURE"
RECOVERY_SUCCESS = "VERIFIED_RECOVERY_SUCCESS"
RECOVERY_UNRESOLVED = "RECOVERY_UNRESOLVED"
RECOVERY_FAILED = "RECOVERY_FAILED"


def future_formal_metadata(
    *,
    directive_id: str,
    formal_execution_id: str,
    baseline_commit: str,
    configuration_fingerprint: str,
    verdict_namespace: str,
    allowed_terminal_verdicts: Iterable[str],
) -> dict[str, Any]:
    """Build identity fields for a future campaign without D-012 labels."""
    if not directive_id or not formal_execution_id or not baseline_commit:
        raise ValueError("formal identity fields must be non-empty")
    if directive_id == "UMBRA-D-012B" and verdict_namespace != "UMBRA_D012B":
        raise ValueError("D-012B compatibility requires its legacy namespace")
    return {
        "directive": directive_id,
        "formal_execution_id": formal_execution_id,
        "baseline_commit": baseline_commit,
        "configuration_fingerprint": configuration_fingerprint,
        "verdict_namespace": verdict_namespace,
        "allowed_terminal_verdicts": list(allowed_terminal_verdicts),
        "contract_version": CONTRACT_VERSION,
    }


def terminal_verdict(namespace: str, suffix: str) -> str:
    if not namespace or not suffix:
        raise ValueError("verdict namespace and suffix are required")
    return f"{namespace}_{suffix}"


def contract_fingerprint(contract: dict[str, Any]) -> str:
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _outcome(row: dict[str, Any]) -> dict[str, Any]:
    return dict(dict(row.get("verified_outcome") or {}).get("outcome") or {})


def _physiology(row: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    before = {k: float(v) for k, v in dict(row.get("physiology_before_tick") or {}).items()}
    after = {k: float(v) for k, v in dict(row.get("physiology_after_tick") or {}).items()}
    return before, after


def _has_authority_chain(row: dict[str, Any], outcome: dict[str, Any]) -> bool:
    event_types = set(row.get("event_types") or [])
    governance = dict(row.get("governance") or {})
    verified = dict(row.get("verified_outcome") or {})
    return (
        "proposal" in event_types
        and "outcome_verified" in event_types
        and bool(verified.get("action_issued"))
        and bool(verified.get("verified", outcome.get("verified")))
        and bool(governance.get("admitted"))
        and not governance.get("stage_failed")
        and not row.get("authority_bypass", False)
        and not row.get("identity_corruption", False)
        and not row.get("persistence_corruption", False)
        and not row.get("governance_corruption", False)
        and bool(outcome)
    )


def _physiology_safe(row: dict[str, Any]) -> bool:
    before, after = _physiology(row)
    if bool(row.get("critical_before_tick")) or bool(row.get("critical_after_tick")):
        return False
    if row.get("physiology_integrity") is False:
        return False
    values = list(before.values()) + list(after.values())
    return bool(values) and all(0.0 <= value <= 1.0 for value in values)


def classify_attempt(row: dict[str, Any]) -> dict[str, Any]:
    """Classify one recorded recovery attempt without changing its evidence."""
    outcome = _outcome(row)
    capability = str(row.get("selected_candidate") or outcome.get("capability") or "")
    before, after = _physiology(row)
    reasons: list[str] = []

    if not _has_authority_chain(row, outcome):
        reasons.append("authority_chain_invalid")
    if not _physiology_safe(row):
        reasons.append("physiology_integrity_or_critical_boundary")
    if outcome.get("success") and str(outcome.get("reason")) != "ok":
        reasons.append("outcome_semantic_inconsistency")
    if outcome.get("success") and capability == "CHARGE":
        effect = dict(row.get("physiology_effect") or {})
        energy_effect = float(effect.get("energy", outcome.get("effects", {}).get("energy", 0.0)))
        if row.get("actual_distance") is not None and row.get("execution_boundary") is not None:
            if float(row["actual_distance"]) > float(row["execution_boundary"]):
                reasons.append("out_of_range_charge_accepted")
        if energy_effect <= 0.0 or float(after.get("energy", 0.0)) <= float(before.get("energy", 0.0)):
            reasons.append("successful_charge_without_positive_energy_effect")
        if row.get("embodiment_validation") not in {"ok", "validated", True}:
            reasons.append("successful_charge_without_authoritative_validation")
        return {
            "state": INTEGRITY_FAILURE if reasons else RECOVERY_SUCCESS,
            "capability": capability,
            "reasons": reasons,
        }

    if capability == "CHARGE" and not bool(outcome.get("success")):
        effect = dict(row.get("physiology_effect") or {})
        credited_energy = float(effect.get("energy", outcome.get("effects", {}).get("energy", 0.0)))
        denied = str(outcome.get("reason")) in {"not_at_resource", "not_at_affordance", "not_executable"}
        affordances = row.get("available_recovery_affordances") or []
        if not any(not bool(a.get("executable", True)) for a in affordances):
            reasons.append("embodiment_denial_not_recorded")
        if not denied:
            reasons.append("denial_reason_not_authoritative")
        if credited_energy > 0.0 or float(after.get("energy", 0.0)) > float(before.get("energy", 0.0)):
            reasons.append("denied_charge_received_positive_energy_credit")
        if reasons or not _has_authority_chain(row, outcome) or not _physiology_safe(row):
            return {"state": INTEGRITY_FAILURE, "capability": capability, "reasons": reasons or ["unsafe_denial"]}
        return {"state": SAFE_DENIAL, "capability": capability, "reasons": ["verified_authority_preserving_denial"]}

    if reasons:
        return {"state": INTEGRITY_FAILURE, "capability": capability, "reasons": reasons}
    return {"state": RECOVERY_UNRESOLVED, "capability": capability, "reasons": ["no_recovery_classification"]}


def _materially_same_denial(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    if str(previous.get("selected_candidate")) != str(current.get("selected_candidate")):
        return False
    if previous.get("corrective_action") or current.get("corrective_action"):
        return False
    if previous.get("new_evidence") or current.get("new_evidence"):
        return False
    return previous.get("observation_signature") == current.get("observation_signature")


def evaluate_episode(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate an episode as a state machine over immutable trace rows."""
    states: list[dict[str, Any]] = []
    previous_denial: dict[str, Any] | None = None
    for row in rows:
        attempt = classify_attempt(row)
        if attempt["state"] == SAFE_DENIAL:
            if previous_denial is not None and _materially_same_denial(previous_denial, row) and row.get("recovery_blocked", True):
                attempt = {
                    "state": RECOVERY_FAILED,
                    "capability": attempt["capability"],
                    "reasons": ["repeated_denial_without_new_evidence_or_correction"],
                }
            else:
                previous_denial = row
        elif attempt["state"] == RECOVERY_SUCCESS:
            previous_denial = None
        states.append(attempt)
        if attempt["state"] in {INTEGRITY_FAILURE, RECOVERY_FAILED}:
            break
    terminal = states[-1]["state"] if states else RECOVERY_UNRESOLVED
    if terminal == RECOVERY_SUCCESS:
        episode_state = RECOVERY_SUCCESS
    elif terminal in {INTEGRITY_FAILURE, RECOVERY_FAILED}:
        episode_state = terminal
    elif any(item["state"] == SAFE_DENIAL for item in states):
        episode_state = RECOVERY_UNRESOLVED
    else:
        episode_state = RECOVERY_UNRESOLVED
    return {"states": states, "terminal_state": episode_state}
