"""Read-only evaluator for the versioned P0 recovery contract.

This module evaluates recorded evidence. It is deliberately not imported by
the organism runtime and never changes organism state or formal databases.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


CONTRACT_V1 = "P0_RECOVERY_CONTRACT_V1"
CONTRACT_VERSION = "P0_RECOVERY_CONTRACT_V2"
CONTRACT_FINGERPRINT = "511c6f56d1cde7c5c28e290e7b1679eea85494b642eb57b5642a5295bbdd2ad2"
VERDICT_NAMESPACE = "D013F"
SAFE_DENIAL = "SAFE_DENIED_RECOVERY_ATTEMPT"
INTEGRITY_FAILURE = "RECOVERY_INTEGRITY_FAILURE"
RECOVERY_SUCCESS = "VERIFIED_RECOVERY_SUCCESS"
RECOVERY_UNRESOLVED = "RECOVERY_UNRESOLVED"
RECOVERY_FAILED = "RECOVERY_FAILED"
CORRECTIVE_CAPABILITIES = frozenset({"APPROACH", "ORIENT", "MOVE"})
RESOURCE_NOT_OBSERVED = "RESOURCE_NOT_OBSERVED"
RESOURCE_OUTSIDE_SELECTION = "RESOURCE_PERCEIVED_OUTSIDE_CHARGE_SELECTION_REGION"
RESOURCE_INSIDE_SELECTION = "RESOURCE_PERCEIVED_INSIDE_CHARGE_SELECTION_REGION"


def validate_contract_selection(version: str, fingerprint: str | None) -> None:
    """Reject ambiguous future campaigns without changing historical V1."""
    if version == CONTRACT_V1:
        return
    if version == CONTRACT_VERSION and fingerprint == CONTRACT_FINGERPRINT:
        return
    if version == CONTRACT_VERSION:
        raise ValueError("V2 contract fingerprint missing_or_incorrect")
    raise ValueError(f"unknown recovery contract:{version}")


def _observation_signature(observations: Iterable[dict[str, Any]]) -> str:
    """Hash policy-visible perception facts, excluding authoritative coordinates."""
    selected: list[dict[str, Any]] = []
    for observation in observations:
        selected.append(
            {
                key: observation.get(key)
                for key in (
                    "observation_id",
                    "observed_at",
                    "kind",
                    "estimated_distance",
                    "confidence",
                    "uncertainty",
                    "perception_state_version",
                )
                if key in observation
            }
        )
    selected.sort(key=lambda value: (str(value.get("kind", "")), str(value.get("observation_id", ""))))
    payload = json.dumps(selected, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _material_resource_state(row: dict[str, Any]) -> str:
    """Return the policy-visible resource state used for evaluator novelty."""
    observations = [dict(item) for item in row.get("observations") or []]
    resource_observations = [
        item for item in observations
        if str(item.get("kind", "")) in {"resource", "novel_crystal"}
    ]
    if not resource_observations:
        return RESOURCE_NOT_OBSERVED

    affordances = [dict(item) for item in row.get("available_recovery_affordances") or []]
    entries: list[dict[str, Any]] = []
    for observation in resource_observations:
        kind = str(observation.get("kind", "resource"))
        matching = [item for item in affordances if item.get("kind") == kind]
        affordance = matching[0] if matching else {}
        boundary = row.get("execution_boundary")
        if affordance.get("radius") is not None:
            boundary = float(affordance["radius"]) + 0.3
        distance = observation.get("estimated_distance")
        if boundary is None or distance is None:
            region = "RESOURCE_PERCEIVED_REGION_UNRESOLVED"
        elif float(distance) <= float(boundary):
            region = RESOURCE_INSIDE_SELECTION
        else:
            region = RESOURCE_OUTSIDE_SELECTION
        entries.append({
            "kind": kind,
            "region": region,
            "chargeable": affordance.get("chargeable"),
        })
    entries.sort(key=lambda item: (item["kind"], item["region"], str(item["chargeable"])))
    return json.dumps({"resources": entries}, sort_keys=True, separators=(",", ":"))


def material_evidence_key(row: dict[str, Any]) -> str:
    """Build capability-relevant materiality while retaining raw provenance."""
    if "observations" in row:
        return _material_resource_state(row)
    # Compatibility for pre-V2 fixture rows. Live V2 rows contain observations.
    legacy = row.get("observation_signature")
    if legacy is not None:
        return "LEGACY_OBSERVATION_SIGNATURE:" + str(legacy)
    return RESOURCE_NOT_OBSERVED


def _capability(value: Any) -> str:
    """Return a normalized non-empty capability label."""
    if value is None:
        return ""
    return str(value).strip()


def _capability_provenance(
    row: dict[str, Any], outcome: dict[str, Any]
) -> tuple[str, list[str]]:
    """Resolve the governed action and fail closed on authority disagreement."""
    selected = _capability(row.get("selected_candidate"))
    executed = _capability(row.get("executed_capability"))
    verified = _capability(outcome.get("capability"))
    governance = dict(row.get("governance") or {})
    governed = _capability(governance.get("capability"))
    reasons: list[str] = []

    if executed and verified and executed != verified:
        reasons.append("capability_provenance_mismatch:executed_vs_verified")
    if governed and executed and governed != executed:
        reasons.append("capability_provenance_mismatch:governance_vs_executed")
    if governed and verified and governed != verified:
        reasons.append("capability_provenance_mismatch:governance_vs_verified")
    if (executed or governed) and not verified:
        reasons.append("capability_provenance_mismatch:verified_capability_missing")

    # selected_candidate is diagnostic proposal provenance. It is only a
    # fallback for legacy fixtures that contain no authoritative action.
    canonical = executed or verified or governed or selected
    return canonical, reasons


def normalize_trace_row(
    row: dict[str, Any], previous: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Derive V2 episode facts from the actual worker trace shape."""
    normalized = dict(row)
    observations = [dict(item) for item in normalized.get("observations") or []]
    signature = normalized.get("observation_signature") or _observation_signature(observations)
    normalized["observation_signature"] = signature
    material_key = material_evidence_key(normalized)
    normalized["material_evidence_key"] = material_key
    material_changed = previous is None or material_key != previous.get("material_evidence_key")
    normalized["material_evidence_changed"] = material_changed
    if "observations" in normalized:
        normalized["new_evidence"] = material_changed
    elif "new_evidence" not in normalized:
        normalized["new_evidence"] = material_changed
    outcome = _outcome(normalized)
    capability, provenance_reasons = _capability_provenance(normalized, outcome)
    normalized["attempt_capability"] = capability
    normalized["capability_provenance_reasons"] = provenance_reasons
    normalized["corrective_action"] = bool(
        capability in CORRECTIVE_CAPABILITIES and outcome.get("success")
    )
    affordances = [dict(item) for item in normalized.get("available_recovery_affordances") or []]
    if "recovery_blocked" not in normalized:
        normalized["recovery_blocked"] = capability == "CHARGE" and not any(
            bool(item.get("chargeable")) and bool(item.get("executable"))
            for item in affordances
        )
    if "actual_distance" not in normalized:
        resources = [
            item for item in affordances
            if item.get("kind") == "resource" and item.get("chargeable")
        ]
        if resources:
            nearest = min(resources, key=lambda item: float(item.get("distance", float("inf"))))
            if nearest.get("distance") is not None:
                normalized["actual_distance"] = float(nearest["distance"])
            if nearest.get("radius") is not None:
                normalized["execution_boundary"] = float(nearest["radius"]) + 0.3
    return normalized


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
    verified = dict(row.get("verified_outcome") or {})
    return dict(verified.get("outcome") or verified)


def _physiology(row: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    before = {k: float(v) for k, v in dict(row.get("physiology_before_tick") or {}).items()}
    after = {k: float(v) for k, v in dict(row.get("physiology_after_tick") or {}).items()}
    return before, after


def _has_authority_chain(row: dict[str, Any], outcome: dict[str, Any]) -> bool:
    event_types = set(row.get("event_types") or [])
    governance = dict(row.get("governance") or {})
    verified = dict(row.get("verified_outcome") or {})
    verified_detail = dict(verified.get("outcome") or verified)
    return (
        "proposal" in event_types
        and "outcome_verified" in event_types
        and bool(
            verified.get(
                "action_issued",
                verified_detail.get("action_issued", row.get("action_issued", False)),
            )
        )
        and bool(
            verified.get(
                "verified",
                verified_detail.get(
                    "verified", row.get("verified_action", outcome.get("verified"))
                ),
            )
        )
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
    capability, provenance_reasons = _capability_provenance(row, outcome)
    before, after = _physiology(row)
    reasons: list[str] = list(provenance_reasons)

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
    if str(previous.get("attempt_capability")) != str(current.get("attempt_capability")):
        return False
    if previous.get("corrective_action") or current.get("corrective_action"):
        return False
    if current.get("new_evidence"):
        return False
    return previous.get("material_evidence_key") == current.get("material_evidence_key")


def evaluate_episode(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate an episode as a state machine over immutable trace rows."""
    states: list[dict[str, Any]] = []
    previous_denial: dict[str, Any] | None = None
    previous_row: dict[str, Any] | None = None
    for raw_row in rows:
        row = normalize_trace_row(raw_row, previous_row)
        previous_row = row
        attempt = classify_attempt(row)
        if attempt["state"] != SAFE_DENIAL and (
            row.get("corrective_action") or row.get("new_evidence")
        ):
            previous_denial = None
        if attempt["state"] == SAFE_DENIAL:
            if (
                previous_denial is not None
                and _materially_same_denial(previous_denial, row)
                and row.get("recovery_blocked", True)
            ):
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
