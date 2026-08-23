"""Bounded compositional recovery contracts.

Contracts are policy-side admissibility evidence. They do not choose goals,
score candidates, execute actions, use hidden habitat truth, or replace
governance.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from umbra_core.physiology import BOUNDS, DEFAULT_DRIFT, verified_outcome_effect_branches

ALLOW = "ALLOW"
CONSTRAIN = "CONSTRAIN"
UNKNOWN = "UNKNOWN"
_ROUTE_CAPABILITIES = frozenset({"MOVE", "APPROACH", "RETREAT", "CHARGE", "REST", "INSPECT"})


def _record(contract: str, status: str, capability: str, reason: str, **evidence: Any) -> dict[str, Any]:
    return {"contract": contract, "status": status, "candidate": capability, "reason": reason, "provenance": "policy_visible", "evidence": evidence}


def _target(params: Mapping[str, Any]) -> str | None:
    value = params.get("toward") or params.get("from")
    return str(value) if value is not None else None


def _matching_observation(observations: Sequence[Mapping[str, Any]], target: str | None) -> Mapping[str, Any] | None:
    for observation in observations:
        if target is None or str(observation.get("kind", "")) == target:
            return observation
    return None


def _executability(capability: str, params: Mapping[str, Any], observations: Sequence[Mapping[str, Any]], arbitration_state: Any) -> dict[str, Any]:
    denial = dict(getattr(arbitration_state, "last_verified_denial", None) or {})
    target = _target(params)
    same_capability = denial.get("capability") == capability
    denial_target = denial.get("target_kind") or denial.get("target")
    same_target = not denial_target or denial_target == target
    evidence_changed = bool(params.get("observation_version")) and params.get("observation_version") != denial.get("observation_version")
    if denial and same_capability and same_target and not evidence_changed:
        return _record("E", CONSTRAIN, capability, "matching_verified_denial_still_fresh", target=target, denial_reason=denial.get("reason"), evidence_changed=False)
    observation = _matching_observation(observations, target)
    support = None if observation is None else observation.get("executability_support")
    if support == "SUPPORTED":
        return _record("E", ALLOW, capability, "current_policy_visible_support", target=target)
    if support == "DENIED":
        return _record("E", CONSTRAIN, capability, "current_policy_visible_denial", target=target)
    return _record("E", UNKNOWN, capability, "executability_support_unknown", target=target)


def _critical_margin(name: str, value: float) -> float:
    bounds = BOUNDS[name]
    return min(value - bounds.critical_low, bounds.critical_high - value)


def _worst_margin(physiology: Mapping[str, float], branches: Sequence[Mapping[str, float]], attempts: int) -> float:
    minimum = float("inf")
    for branch in branches or ({},):
        for name in BOUNDS:
            projected = float(physiology[name]) + attempts * (float(branch.get(name, 0.0)) + float(DEFAULT_DRIFT.get(name, 0.0)))
            minimum = min(minimum, _critical_margin(name, projected))
    return minimum


def _reserve(capability: str, physiology: Mapping[str, float], params: Mapping[str, Any], effect_branches: Sequence[Mapping[str, float]] | None) -> dict[str, Any]:
    required = params.get("required_attempts")
    reserve = params.get("retry_reserve")
    if required is None or reserve is None:
        return _record("R", UNKNOWN, capability, "reserve_or_required_attempts_unknown")
    try:
        attempts = max(1, int(required)) + max(0, int(reserve))
    except (TypeError, ValueError):
        return _record("R", UNKNOWN, capability, "reserve_fields_invalid")
    branches = tuple(effect_branches or verified_outcome_effect_branches(capability))
    margin = _worst_margin(physiology, branches, attempts)
    if margin < 0.0:
        return _record("R", CONSTRAIN, capability, "bounded_failure_retry_reserve_inadequate", projected_minimum_margin=margin, attempts=attempts)
    return _record("R", ALLOW, capability, "bounded_failure_retry_reserve_adequate", projected_minimum_margin=margin, attempts=attempts)


def _progress(capability: str, params: Mapping[str, Any], observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if capability not in _ROUTE_CAPABILITIES:
        return _record("P", ALLOW, capability, "route_progress_not_applicable")
    observation = _matching_observation(observations, _target(params))
    status = params.get("progress_status")
    if status is None and observation is not None:
        status = observation.get("progress_status")
    if status == "CONFIRMED":
        return _record("P", ALLOW, capability, "policy_visible_progress_confirmed")
    if status == "STALLED":
        return _record("P", CONSTRAIN, capability, "repeated_route_attempts_without_progress")
    return _record("P", UNKNOWN, capability, "route_progress_unknown")


def _horizon(capability: str, params: Mapping[str, Any]) -> dict[str, Any]:
    remaining = params.get("time_to_critical")
    steps = params.get("required_recovery_steps")
    reserve = params.get("retry_reserve")
    if remaining is None or steps is None or reserve is None:
        return _record("H", UNKNOWN, capability, "time_or_correction_horizon_unknown")
    try:
        remaining_i = int(remaining)
        required_i = max(0, int(steps)) + max(0, int(reserve))
    except (TypeError, ValueError):
        return _record("H", UNKNOWN, capability, "horizon_fields_invalid")
    if remaining_i < required_i:
        return _record("H", CONSTRAIN, capability, "known_horizon_insufficient", time_to_critical=remaining_i, required_steps=required_i)
    if remaining_i <= required_i + 1:
        return _record("H", ALLOW, capability, "horizon_tight_but_sufficient", time_to_critical=remaining_i, required_steps=required_i)
    return _record("H", ALLOW, capability, "horizon_comfortable", time_to_critical=remaining_i, required_steps=required_i)


def evaluate_recovery_contracts(*, capability: str, params: Mapping[str, Any], physiology: Mapping[str, float], observations: Sequence[Mapping[str, Any]], arbitration_state: Any, effect_branches: Sequence[Mapping[str, float]] | None = None) -> dict[str, Any]:
    """Return bounded contract evidence for one policy-visible candidate."""
    contracts = [
        _executability(capability, params, observations, arbitration_state),
        _reserve(capability, physiology, params, effect_branches),
        _progress(capability, params, observations),
        _horizon(capability, params),
    ]
    constrained = [row for row in contracts if row["status"] == CONSTRAIN]
    return {
        "schema": "D014E_COMPOSITIONAL_RECOVERY_CONTRACTS_V1",
        "candidate": capability,
        "contracts": contracts,
        "admissible": not constrained,
        "constrained_by": [row["contract"] for row in constrained],
        "unknown_contracts": [row["contract"] for row in contracts if row["status"] == UNKNOWN],
        "physiology": {name: float(physiology[name]) for name in BOUNDS},
        "hidden_truth_used": False,
    }


def candidate_is_admissible(candidate: Any, *, physiology: Any, observations: Sequence[Mapping[str, Any]], arbitration_state: Any, effect_branches: Sequence[Mapping[str, float]] | None = None) -> bool:
    evidence = evaluate_recovery_contracts(
        capability=str(candidate.capability),
        params=dict(candidate.params),
        physiology=physiology.as_dict(),
        observations=observations,
        arbitration_state=arbitration_state,
        effect_branches=effect_branches,
    )
    return bool(evidence["admissible"])

