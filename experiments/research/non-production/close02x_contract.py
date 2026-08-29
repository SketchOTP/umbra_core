"""Pure CLOSE-02X contract proof; never imported by production runtime."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from umbra_core.recoverability import RecoverabilityStatus, derive_recoverability_view


_BASELINE_CAPABILITY = "PROSPECTIVE_BASELINE"


def dimension_status(view: Mapping[str, Any], dimension: str) -> str:
    """Return the strongest existential route status for one dimension."""
    routes = [
        route
        for route in view["candidate_projection"]["post_candidate_routes"]
        if route.get("need") == dimension
    ]
    if not routes:
        return RecoverabilityStatus.NO_KNOWN_RECOVERY_ROUTE.value
    if any(
        route.get("status") == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
        for route in routes
    ):
        return RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    if all(
        route.get("status") == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
        for route in routes
    ):
        return RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
    return str(
        next(
            route["status"]
            for route in routes
            if route.get("status")
            != RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
        )
    )


def evaluate_candidate(
    *,
    organism_tick: int,
    body_schema_id: str,
    physiology: Mapping[str, Any],
    attended_dimensions: Sequence[str],
    observations: Sequence[Mapping[str, Any]],
    candidate: Any,
    authority_effect_branches: Sequence[Mapping[str, Any]],
    capability_support: Mapping[str, Mapping[str, Any]],
    body_energy_cost_scale: float = 1.0,
    pending_commitment: bool = False,
) -> dict[str, Any]:
    """Evaluate one candidate without selecting, creating, or executing it."""
    current = derive_recoverability_view(
        organism_tick=organism_tick,
        body_schema_id=body_schema_id,
        physiology=physiology,
        active_needs=attended_dimensions,
        observations=observations,
        candidate={"capability": _BASELINE_CAPABILITY, "params": {}},
        authority_effect_branches=({},),
        capability_support=capability_support,
        body_energy_cost_scale=body_energy_cost_scale,
        pending_commitment=pending_commitment,
    )
    projected = derive_recoverability_view(
        organism_tick=organism_tick,
        body_schema_id=body_schema_id,
        physiology=physiology,
        active_needs=attended_dimensions,
        observations=observations,
        candidate=candidate,
        authority_effect_branches=authority_effect_branches,
        capability_support=capability_support,
        body_energy_cost_scale=body_energy_cost_scale,
        pending_commitment=pending_commitment,
    )
    transitions = []
    constrained_dimensions = []
    for dimension in attended_dimensions:
        current_status = dimension_status(current, dimension)
        projected_status = dimension_status(projected, dimension)
        constrained = bool(
            current_status == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
            and projected_status
            == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
        )
        transitions.append(
            {
                "dimension": dimension,
                "current_status": current_status,
                "projected_status": projected_status,
                "constrained": constrained,
            }
        )
        if constrained:
            constrained_dimensions.append(dimension)
    return {
        "schema": "CLOSE02X_PROSPECTIVE_TRANSITION_PROOF_V1",
        "candidate": projected["candidate_projection"]["capability"],
        "transitions": transitions,
        "constrained": bool(constrained_dimensions),
        "constrained_dimensions": constrained_dimensions,
        "action_authority": False,
        "candidate_created": False,
        "rollout_required": False,
        "hidden_truth_fields": 0,
        "current_view": current,
        "projected_view": projected,
    }
