"""Fixed-size, policy-provenanced recoverability shadow view.

The functions in this module are deliberately pure.  They own no world,
body, physiology, or policy state and grant no action authority.  The view
only composes state supplied by the existing owners.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any, Mapping, Sequence

from umbra_core.physiology import (
    BOUNDS,
    DEFAULT_DRIFT,
    project_verified_transition,
    verified_outcome_effect_branches,
)
from umbra_core.self_model.engine import SupportSemantics
from umbra_core.util import canon_json


MOTION_CAPABILITIES = frozenset({"MOVE", "APPROACH", "RETREAT"})
DELAYABLE_CAPABILITIES = frozenset({"MOVE", "APPROACH", "RETREAT", "ORIENT"})
RECOVERY_PATHS: dict[str, tuple[str, tuple[str, ...]]] = {
    "resource": ("CHARGE", ("energy",)),
    "novel_crystal": ("CHARGE", ("energy",)),
    "rest": ("REST", ("fatigue", "integrity")),
    "inspect": ("INSPECT", ("stimulation",)),
}
ROUTE_MOVEMENT_CAPABILITY = "APPROACH"
RECOVERY_SELECTION_DISTANCE = 1.5
EPSILON = 1.0e-12
MAX_PROVENANCE_REFS = 8
MAX_TEXT_LENGTH = 160
PROSPECTIVE_BASELINE_CAPABILITY = "PROSPECTIVE_BASELINE"

# These categories belong to the pure reachability envelope.  They are not
# action authority and deliberately remain distinct from the viability kernel's
# current-endpoint statuses in viability.py.
ROBUST_NOW = "ROBUST_NOW"
BOUNDED_RECOVERY_OPPORTUNITY = "BOUNDED_RECOVERY_OPPORTUNITY"
MAY_ROUTE = "MAY_ROUTE"
UNKNOWN_ROUTE = "UNKNOWN_ROUTE"


class RecoverabilityStatus(str, Enum):
    SUPPORTED_MARGIN_POSITIVE = "SUPPORTED_MARGIN_POSITIVE"
    SUPPORTED_MARGIN_EXHAUSTED = "SUPPORTED_MARGIN_EXHAUSTED"
    UNKNOWN_CAPABILITY_SUPPORT = "UNKNOWN_CAPABILITY_SUPPORT"
    UNKNOWN_OPPORTUNITY_SUPPORT = "UNKNOWN_OPPORTUNITY_SUPPORT"
    UNKNOWN_ROUTE_GEOMETRY = "UNKNOWN_ROUTE_GEOMETRY"
    NO_KNOWN_RECOVERY_ROUTE = "NO_KNOWN_RECOVERY_ROUTE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING_COMMITMENT = "PENDING_COMMITMENT"


_SEMANTIC_RANK = {
    SupportSemantics.HARD_CONTRACT.value: 0,
    SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value: 1,
    SupportSemantics.PROBABILISTIC_SUPPORT.value: 2,
    SupportSemantics.UNKNOWN.value: 3,
}


def _finite(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _bounded_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:MAX_TEXT_LENGTH]


def _normalized_semantics(value: Any) -> str:
    parsed = str(value)
    if parsed in _SEMANTIC_RANK or parsed == SupportSemantics.NOT_APPLICABLE.value:
        return parsed
    return SupportSemantics.UNKNOWN.value


def _weakest_semantics(*values: str) -> str:
    relevant = [value for value in values if value != SupportSemantics.NOT_APPLICABLE.value]
    if not relevant:
        return SupportSemantics.NOT_APPLICABLE.value
    return max(
        relevant,
        key=lambda value: _SEMANTIC_RANK.get(value, _SEMANTIC_RANK[SupportSemantics.UNKNOWN.value]),
    )


def _interval(envelope: Mapping[str, Any] | None, name: str) -> dict[str, Any]:
    if not envelope:
        return {
            "minimum": None,
            "maximum": None,
            "semantics": SupportSemantics.UNKNOWN.value,
            "evidence_count": 0,
            "provenance": [],
        }
    row = dict(envelope.get(name) or {})
    semantics = _normalized_semantics(
        row.get("semantics", SupportSemantics.UNKNOWN.value)
    )
    minimum = _finite(row.get("minimum"))
    maximum = _finite(row.get("maximum"))
    if minimum is None or maximum is None:
        semantics = SupportSemantics.UNKNOWN.value
    return {
        "minimum": minimum,
        "maximum": maximum,
        "semantics": semantics,
        "evidence_count": int(row.get("evidence_count", 0)),
        "provenance": [
            str(item)[:MAX_TEXT_LENGTH]
            for item in tuple(row.get("provenance", ()))[:MAX_PROVENANCE_REFS]
        ],
    }


def _signed_critical_margin(name: str, value: float) -> float:
    bounds = BOUNDS[name]
    return min(float(value) - bounds.critical_low, bounds.critical_high - float(value))


def _slack(physiology: Mapping[str, Any]) -> dict[str, float]:
    return {name: _signed_critical_margin(name, float(physiology[name])) for name in BOUNDS}


def _drift_intervals(completion_max: float | None) -> int:
    # Immediate completion (lag 0) still has one autonomous drift before the
    # next decision.  A delayed completion at lag N is committed after N
    # drift applications, and the runtime may decide again on that same tick.
    if completion_max is None:
        return 1
    return max(1, int(math.ceil(max(0.0, completion_max))))


def _worst_projected_value(
    current: float,
    branches: Sequence[Mapping[str, Any]],
    name: str,
    *,
    capability: str,
    executions: int,
    drift_intervals: int,
    drift_enabled: bool,
) -> float:
    choices = branches or ({},)
    projected: list[float] = []
    for branch in choices:
        state = {variable: float(current) for variable in BOUNDS}
        # Only the selected dimension is known at this helper boundary.  The
        # complete-state caller below supplies the correlated projection; this
        # fallback keeps the helper safe for legacy direct callers.
        state[name] = float(current)
        for _ in range(executions):
            state = project_verified_transition(
                state,
                dict(branch),
                capability=capability,
                drift_enabled=drift_enabled,
                dt=float(drift_intervals),
            )
        projected.append(float(state[name]))
    return min(projected, key=lambda value: _signed_critical_margin(name, value))


def _project_branch_states(
    current: Mapping[str, Any],
    branches: Sequence[Mapping[str, Any]],
    *,
    capability: str,
    executions: int,
    drift_intervals: int,
    drift_enabled: bool,
) -> list[dict[str, float]]:
    """Project correlated branches through the physiology owner's transition."""
    states: list[dict[str, float]] = []
    for branch in branches or ({},):
        state = {name: float(current[name]) for name in BOUNDS}
        for _ in range(max(0, executions)):
            state = project_verified_transition(
                state,
                dict(branch),
                capability=capability,
                drift_enabled=drift_enabled,
                dt=float(drift_intervals),
            )
        states.append(state)
    return states


def _scale_negative_energy(
    branches: Sequence[Mapping[str, Any]], scale: float
) -> tuple[dict[str, float], ...]:
    result: list[dict[str, float]] = []
    for branch in branches:
        effects = {str(name): float(value) for name, value in branch.items()}
        if scale != 1.0 and effects.get("energy", 0.0) < 0.0:
            effects["energy"] *= scale
        result.append(effects)
    return tuple(result)


def _project_physiology(
    physiology: Mapping[str, Any],
    branches: Sequence[Mapping[str, Any]],
    completion_max: float | None,
    *,
    capability: str = PROSPECTIVE_BASELINE_CAPABILITY,
    drift_enabled: bool = True,
) -> dict[str, float]:
    intervals = _drift_intervals(completion_max)
    states = _project_branch_states(
        physiology,
        branches,
        capability=capability,
        executions=1,
        drift_intervals=intervals,
        drift_enabled=drift_enabled,
    )
    return {
        name: min(
            (float(state[name]) for state in states),
            key=lambda value: _signed_critical_margin(name, value),
        )
        for name in BOUNDS
    }


def project_support_region(
    *,
    center_dx: float,
    center_dy: float,
    radius: float,
    heading_delta: float,
    progress_values: Sequence[float],
) -> dict[str, Any]:
    """Project a bounded body-relative region through supported motion.

    The target is never assumed to be at the center.  The returned upper
    distance is the maximum over the supplied progress-support endpoints.
    Rotation into the post-action body frame is unnecessary for distance
    because Euclidean norm is rotation invariant.
    """
    if radius < 0.0:
        raise ValueError("support radius must be non-negative")
    c = math.cos(float(heading_delta))
    s = math.sin(float(heading_delta))
    projected = [
        {
            "progress": float(progress),
            "center_dx": float(center_dx) - float(progress) * c,
            "center_dy": float(center_dy) - float(progress) * s,
        }
        for progress in progress_values
    ]
    upper = max(
        math.hypot(row["center_dx"], row["center_dy"]) + float(radius)
        for row in projected
    )
    return {
        "support_radius": float(radius),
        "projected_centers": projected,
        "distance_support_upper_bound": upper,
    }


def _opportunity_semantics(observation: Mapping[str, Any]) -> str:
    explicit = observation.get("support_semantics")
    if explicit is not None:
        return _normalized_semantics(explicit)
    if observation.get("fact_kind") == "REMEMBERED_ESTIMATE":
        return SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    return SupportSemantics.UNKNOWN.value


def _geometry(
    observation: Mapping[str, Any], body_schema_id: str
) -> dict[str, Any] | None:
    center_dx = _finite(observation.get("support_center_dx"))
    center_dy = _finite(observation.get("support_center_dy"))
    radius = _finite(observation.get("support_radius"))
    provenance = observation.get("support_provenance")
    if str(observation.get("support_body_schema_id", "")) != str(body_schema_id):
        return None
    if center_dx is None or center_dy is None or radius is None or radius < 0.0:
        # A policy-visible upper distance is sufficient for a conservative
        # route-length bound, but not for directional geometry.  Do not infer
        # coordinates or progress from it.
        upper = _finite(observation.get("distance_support_upper_bound"))
        if upper is None or upper < 0.0 or not provenance:
            return None
        semantics = _opportunity_semantics(observation)
        if semantics in {
            SupportSemantics.UNKNOWN.value,
            SupportSemantics.PROBABILISTIC_SUPPORT.value,
        }:
            return None
        return {
            "support_center_dx": None,
            "support_center_dy": None,
            "support_radius": None,
            "support_provenance": _bounded_text(provenance),
            "support_source_kind": _bounded_text(observation.get("support_source_kind")),
            "semantics": semantics,
            "distance_support_upper_bound": upper,
            "projected_centers": [],
            "directional_geometry": False,
        }
    if not provenance:
        return None
    return {
        "support_center_dx": center_dx,
        "support_center_dy": center_dy,
        "support_radius": radius,
        "support_provenance": _bounded_text(provenance),
        "support_source_kind": _bounded_text(observation.get("support_source_kind")),
        "semantics": _opportunity_semantics(observation),
        "directional_geometry": True,
    }


def _candidate_parts(candidate: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(candidate, Mapping):
        capability = _bounded_text(candidate["capability"]) or ""
        raw = dict(candidate.get("params") or {})
    else:
        capability = _bounded_text(candidate.capability) or ""
        raw = dict(candidate.params)
    heading = _finite(raw.get("heading_delta"))
    return capability, ({"heading_delta": heading} if heading is not None else {})


def _candidate_identity(candidate: Any) -> str:
    capability, params = _candidate_parts(candidate)
    encoded = canon_json(params)
    if isinstance(encoded, bytes):
        encoded = encoded.decode("utf-8")
    return f"{capability}:{encoded}"


def _movement_projection(
    observation: Mapping[str, Any],
    body_schema_id: str,
    candidate_capability: str,
    candidate_params: Mapping[str, Any],
    candidate_support: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, str, str | None]:
    geometry = _geometry(observation, body_schema_id)
    if geometry is None:
        return None, SupportSemantics.UNKNOWN.value, RecoverabilityStatus.UNKNOWN_ROUTE_GEOMETRY.value
    if candidate_capability not in MOTION_CAPABILITIES:
        return (
            {
                **geometry,
                "distance_support_upper_bound": geometry.get(
                    "distance_support_upper_bound",
                    math.hypot(
                        geometry["support_center_dx"], geometry["support_center_dy"]
                    )
                    + geometry["support_radius"],
                ),
                "projected_centers": geometry.get("projected_centers") or [{
                    "progress": 0.0,
                    "center_dx": geometry["support_center_dx"],
                    "center_dy": geometry["support_center_dy"],
                }],
            },
            geometry["semantics"],
            None,
        )

    progress = _interval(candidate_support, "progress")
    if progress["semantics"] in {
        SupportSemantics.UNKNOWN.value,
        SupportSemantics.NOT_APPLICABLE.value,
    }:
        return None, progress["semantics"], RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value
    if progress["semantics"] == SupportSemantics.PROBABILISTIC_SUPPORT.value:
        return None, progress["semantics"], RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value
    heading = _finite(candidate_params.get("heading_delta"))
    if heading is None:
        return None, SupportSemantics.UNKNOWN.value, RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value
    # Zero remains reachable for declared movement failure modes.  Observed
    # success extrema are evidence, not a guarantee that a future attempt will
    # realize either endpoint.
    if not geometry.get("directional_geometry", True):
        return geometry, _weakest_semantics(geometry["semantics"], progress["semantics"]), None
    values = [0.0, float(progress["minimum"]), float(progress["maximum"])]
    projected = project_support_region(
        center_dx=geometry["support_center_dx"],
        center_dy=geometry["support_center_dy"],
        radius=geometry["support_radius"],
        heading_delta=heading,
        progress_values=values,
    )
    return (
        {**geometry, **projected},
        _weakest_semantics(geometry["semantics"], progress["semantics"]),
        None,
    )


def _route_projection(
    *,
    active_need: str,
    observation: Mapping[str, Any],
    body_schema_id: str,
    post_candidate_physiology: Mapping[str, Any],
    candidate_capability: str,
    candidate_params: Mapping[str, Any],
    capability_support: Mapping[str, Mapping[str, Any]],
    body_energy_cost_scale: float,
    candidate_timing_semantics: str,
    drift_enabled: bool,
) -> dict[str, Any]:
    terminal_capability, served_needs = RECOVERY_PATHS[str(observation["kind"])]
    candidate_geometry, candidate_semantics, error = _movement_projection(
        observation,
        body_schema_id,
        candidate_capability,
        candidate_params,
        capability_support.get(candidate_capability),
    )
    base = {
        "need": active_need,
        "recovery_opportunity": str(observation["kind"]),
        "opportunity_fact_kind": _bounded_text(observation.get("fact_kind")),
        "opportunity_provenance": _bounded_text(observation.get("support_provenance")),
        "terminal_capability": terminal_capability,
        "route_capability": ROUTE_MOVEMENT_CAPABILITY,
        "served_needs": list(served_needs),
        "candidate_geometry": candidate_geometry,
    }
    if error is not None:
        return {
            **base,
            "status": error,
            "margin_semantics": candidate_semantics,
            "recovery_margin": None,
            "bottleneck_variable": None,
        }

    route_support = capability_support.get(ROUTE_MOVEMENT_CAPABILITY)
    progress = _interval(route_support, "progress")
    completion = _interval(route_support, "completion")
    route_semantics = _weakest_semantics(
        candidate_semantics,
        candidate_timing_semantics,
        progress["semantics"],
        completion["semantics"],
    )
    if progress["semantics"] in {
        SupportSemantics.UNKNOWN.value,
        SupportSemantics.NOT_APPLICABLE.value,
    } or completion["semantics"] in {
        SupportSemantics.UNKNOWN.value,
        SupportSemantics.NOT_APPLICABLE.value,
    }:
        return {
            **base,
            "status": RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value,
            "margin_semantics": route_semantics,
            "directional_progress_support": progress,
            "completion_lag_support": completion,
            "recovery_margin": None,
            "bottleneck_variable": None,
        }
    if route_semantics in {
        SupportSemantics.UNKNOWN.value,
        SupportSemantics.PROBABILISTIC_SUPPORT.value,
    }:
        return {
            **base,
            "status": RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value,
            "margin_semantics": route_semantics,
            "directional_progress_support": progress,
            "completion_lag_support": completion,
            "recovery_margin": None,
            "bottleneck_variable": None,
        }
    minimum_progress = float(progress["minimum"])
    if minimum_progress <= EPSILON:
        return {
            **base,
            "status": RecoverabilityStatus.UNKNOWN_CAPABILITY_SUPPORT.value,
            "margin_semantics": route_semantics,
            "directional_progress_support": progress,
            "completion_lag_support": completion,
            "recovery_margin": None,
            "bottleneck_variable": None,
        }

    upper_distance = float(candidate_geometry["distance_support_upper_bound"])
    executions = int(
        math.ceil(max(0.0, upper_distance - RECOVERY_SELECTION_DISTANCE) / minimum_progress)
    )
    route_branches = _scale_negative_energy(
        verified_outcome_effect_branches(ROUTE_MOVEMENT_CAPABILITY),
        float(body_energy_cost_scale),
    )
    intervals = _drift_intervals(float(completion["maximum"]))
    route_states = _project_branch_states(
        post_candidate_physiology,
        route_branches,
        capability=ROUTE_MOVEMENT_CAPABILITY,
        executions=executions,
        drift_intervals=intervals,
        drift_enabled=drift_enabled,
    )
    route_post = {
        name: min(
            (float(state[name]) for state in route_states),
            key=lambda value: _signed_critical_margin(name, value),
        )
        for name in BOUNDS
    }
    terminal_branches = _scale_negative_energy(
        verified_outcome_effect_branches(terminal_capability),
        float(body_energy_cost_scale),
    )
    terminal_post = _project_physiology(
        route_post,
        terminal_branches,
        0.0,
        capability=terminal_capability,
    )
    margins = _slack(terminal_post)
    bottleneck = min(margins, key=margins.get)
    minimum_margin = margins[bottleneck]
    return {
        **base,
        "status": (
            RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
            if minimum_margin > 0.0
            else RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
        ),
        "margin_semantics": route_semantics,
        "directional_progress_support": progress,
        "completion_lag_support": completion,
        "required_movement_executions": executions,
        "drift_intervals_per_execution": intervals,
        "terminal_effect_branches": list(terminal_branches),
        "terminal_drift_intervals": 1,
        "physiology_burden": {
            name: float(post_candidate_physiology[name]) - route_post[name]
            for name in BOUNDS
        },
        "post_route_physiology": route_post,
        "post_terminal_physiology": terminal_post,
        "homeostatic_slack": margins,
        "recovery_margin": minimum_margin,
        "bottleneck_variable": bottleneck,
    }


def _best_route(routes: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Choose the strongest policy-supported existential route for one slot."""
    positive = [
        route
        for route in routes
        if route["status"] == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    ]
    if positive:
        return max(positive, key=lambda route: float(route["recovery_margin"]))
    unknown = [
        route
        for route in routes
        if route["status"] != RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
    ]
    if unknown:
        return unknown[0]
    return max(
        routes,
        key=lambda route: float(route.get("recovery_margin") or float("-inf")),
    )


def _aggregate_need_status(
    active_needs: Sequence[str], routes: Sequence[Mapping[str, Any]]
) -> str:
    need_statuses: list[str] = []
    for need in active_needs:
        rows = [row for row in routes if row.get("need") == need]
        if not rows:
            need_statuses.append(RecoverabilityStatus.NO_KNOWN_RECOVERY_ROUTE.value)
        else:
            need_statuses.append(str(rows[0]["status"]))
    if not need_statuses:
        return RecoverabilityStatus.NOT_APPLICABLE.value
    if RecoverabilityStatus.NO_KNOWN_RECOVERY_ROUTE.value in need_statuses:
        return RecoverabilityStatus.NO_KNOWN_RECOVERY_ROUTE.value
    if RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value in need_statuses:
        return RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
    unknown = [
        status
        for status in need_statuses
        if status != RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    ]
    return unknown[0] if unknown else RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value


def derive_recoverability_view(
    *,
    organism_tick: int,
    body_schema_id: str,
    physiology: Mapping[str, Any],
    active_needs: Sequence[str],
    observations: Sequence[Mapping[str, Any]],
    candidate: Any,
    authority_effect_branches: Sequence[Mapping[str, Any]],
    capability_support: Mapping[str, Mapping[str, Any]],
    body_energy_cost_scale: float = 1.0,
    pending_commitment: bool = False,
    drift_enabled: bool = True,
) -> dict[str, Any]:
    """Compose a bounded read-only recoverability view for one candidate."""
    capability, params = _candidate_parts(candidate)
    normalized_needs = tuple(
        need for need in BOUNDS if need in {str(item) for item in active_needs}
    )
    current_slack = _slack(physiology)
    schema_support = {
        name: envelope
        for name, envelope in capability_support.items()
        if str(envelope.get("body_schema_id", "")) == str(body_schema_id)
    }
    candidate_motion_support = (
        _interval(schema_support.get(capability), "progress")
        if capability in MOTION_CAPABILITIES
        else {
            "minimum": 0.0,
            "maximum": 0.0,
            "semantics": SupportSemantics.HARD_CONTRACT.value,
            "evidence_count": 0,
            "provenance": ["contract:stationary_capability"],
        }
    )
    known_recovery_opportunity_count = len({
        str(observation.get("kind"))
        for observation in observations
        if str(observation.get("kind")) in RECOVERY_PATHS
    })
    if pending_commitment:
        return {
            "schema": "HOMEOSTATIC_RECOVERABILITY_VIEW_V1",
            "architecture": "CROSS_COMPONENT_DERIVED_VIEW",
            "organism_tick": int(organism_tick),
            "body_schema_id": _bounded_text(body_schema_id),
            "active_needs": list(normalized_needs),
            "known_recovery_opportunity_count": known_recovery_opportunity_count,
            "homeostatic_slack": current_slack,
            "candidate_projection": {
                "capability": capability,
                "params": params,
                "status": RecoverabilityStatus.PENDING_COMMITMENT.value,
                "fresh_action_recoverability": SupportSemantics.NOT_APPLICABLE.value,
                "candidate_motion_support": candidate_motion_support,
                "post_candidate_routes": [],
            },
            "fixed_size": True,
            "persisted_state": False,
            "rollout_required": False,
            "action_authority": False,
            "hidden_truth_fields": 0,
        }

    completion = (
        _interval(schema_support.get(capability), "completion")
        if capability in DELAYABLE_CAPABILITIES
        else {
            "minimum": 0.0,
            "maximum": 0.0,
            "semantics": SupportSemantics.HARD_CONTRACT.value,
            "evidence_count": 0,
            "provenance": ["contract:synchronous_capability"],
        }
    )
    candidate_completion = (
        float(completion["maximum"])
        if completion["maximum"] is not None
        else None
    )
    post_candidate = _project_physiology(
        physiology,
        authority_effect_branches,
        candidate_completion,
        capability=capability,
        drift_enabled=drift_enabled,
    )
    routes: list[dict[str, Any]] = []
    for need in normalized_needs:
        for opportunity_kind in RECOVERY_PATHS:
            matching = [
            observation
            for observation in observations
            if str(observation.get("kind")) == opportunity_kind
            and need in RECOVERY_PATHS[opportunity_kind][1]
            ]
            if matching:
                projected = [
                    _route_projection(
                    active_need=str(need),
                    observation=observation,
                    body_schema_id=str(body_schema_id),
                    post_candidate_physiology=post_candidate,
                    candidate_capability=capability,
                    candidate_params=params,
                    capability_support=schema_support,
                    body_energy_cost_scale=float(body_energy_cost_scale),
                    candidate_timing_semantics=str(completion["semantics"]),
                    drift_enabled=bool(drift_enabled),
                )
                    for observation in matching
                ]
                routes.append(_best_route(projected))

    overall = _aggregate_need_status(normalized_needs, routes)

    supported = [route for route in routes if route["status"].startswith("SUPPORTED_MARGIN_")]
    unknown = [route for route in routes if route not in supported]
    semantics = _weakest_semantics(
        *(str(route.get("margin_semantics", SupportSemantics.UNKNOWN.value)) for route in routes)
    ) if routes else (
        SupportSemantics.NOT_APPLICABLE.value
        if not normalized_needs
        else SupportSemantics.UNKNOWN.value
    )
    return {
        "schema": "HOMEOSTATIC_RECOVERABILITY_VIEW_V1",
        "architecture": "CROSS_COMPONENT_DERIVED_VIEW",
        "organism_tick": int(organism_tick),
        "body_schema_id": _bounded_text(body_schema_id),
        "active_needs": list(normalized_needs),
        "known_recovery_opportunity_count": known_recovery_opportunity_count,
        "homeostatic_slack": current_slack,
        "candidate_projection": {
            "capability": capability,
            "params": params,
            "candidate_motion_support": candidate_motion_support,
            "candidate_completion_lag_support": completion,
            "post_candidate_physiology": post_candidate,
            "post_candidate_routes": routes,
            "supported_route_count": len(supported),
            "unknown_route_count": len(unknown),
            "minimum_supported_margin": (
                min(float(route["recovery_margin"]) for route in supported)
                if supported
                else None
            ),
            "overall_semantics": semantics,
            "status": overall,
        },
        "fixed_size": True,
        "persisted_state": False,
        "rollout_required": False,
        "action_authority": False,
        "hidden_truth_fields": 0,
    }


def _dimension_status(view: Mapping[str, Any], dimension: str) -> str:
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


def _route_evidence(view: Mapping[str, Any], dimension: str) -> list[dict[str, Any]]:
    """Bound trace evidence to the fixed recovery-opportunity vocabulary."""
    return [
        {
            "opportunity": route.get("recovery_opportunity"),
            "fact_kind": route.get("opportunity_fact_kind"),
            "provenance": route.get("opportunity_provenance"),
            "status": route.get("status"),
            "margin_semantics": route.get("margin_semantics"),
            "recovery_margin": route.get("recovery_margin"),
            "bottleneck_variable": route.get("bottleneck_variable"),
        }
        for route in view["candidate_projection"]["post_candidate_routes"]
        if route.get("need") == dimension
    ][: len(RECOVERY_PATHS)]


def prospective_recoverability_transition(
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
    """Compare current and one-candidate margins without action authority."""
    normalized_dimensions = tuple(
        dimension
        for dimension in BOUNDS
        if dimension in {str(item) for item in attended_dimensions}
    )
    common = {
        "organism_tick": int(organism_tick),
        "body_schema_id": str(body_schema_id),
        "physiology": physiology,
        "active_needs": normalized_dimensions,
        "observations": observations,
        "capability_support": capability_support,
        "body_energy_cost_scale": float(body_energy_cost_scale),
        "pending_commitment": bool(pending_commitment),
    }
    current = derive_recoverability_view(
        **common,
        candidate={"capability": PROSPECTIVE_BASELINE_CAPABILITY, "params": {}},
        authority_effect_branches=({},),
    )
    projected = derive_recoverability_view(
        **common,
        candidate=candidate,
        authority_effect_branches=authority_effect_branches,
    )
    transitions: list[dict[str, Any]] = []
    constrained_dimensions: list[str] = []
    for dimension in normalized_dimensions:
        current_status = _dimension_status(current, dimension)
        projected_status = _dimension_status(projected, dimension)
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
                "current_routes": _route_evidence(current, dimension),
                "projected_routes": _route_evidence(projected, dimension),
            }
        )
        if constrained:
            constrained_dimensions.append(dimension)
    capability, params = _candidate_parts(candidate)
    return {
        "schema": "PROSPECTIVE_RECOVERABILITY_TRANSITION_V1",
        "organism_tick": int(organism_tick),
        "candidate": {"capability": capability, "params": params},
        "transitions": transitions,
        "constrained": bool(constrained_dimensions),
        "constrained_dimensions": constrained_dimensions,
        "fixed_size": True,
        "persisted_state": False,
        "rollout_required": False,
        "action_authority": False,
        "candidate_created": False,
        "hidden_truth_fields": 0,
    }


def _envelope_status(view: Mapping[str, Any]) -> str:
    """Map the existing route evidence into the AS-018 categorical vocabulary."""
    raw = str(view["candidate_projection"].get("status"))
    if raw == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value:
        return BOUNDED_RECOVERY_OPPORTUNITY
    if raw == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value:
        # The opportunity is visible and model-supported, but the projected
        # reserve is exhausted.  This is not robust recovery and is retained as
        # a MAY route for ordinary exploration/diagnostics.
        return MAY_ROUTE
    if raw == RecoverabilityStatus.NO_KNOWN_RECOVERY_ROUTE.value:
        return UNKNOWN_ROUTE
    return UNKNOWN_ROUTE


def _reserve_threatened(
    physiology: Mapping[str, Any],
    active_needs: Sequence[str],
    baseline_view: Mapping[str, Any],
) -> bool:
    """Detect a narrow pre-critical reserve threat without choosing an action."""
    if not active_needs:
        return False
    routes = baseline_view["candidate_projection"].get("post_candidate_routes", [])
    horizons = [int(route.get("required_movement_executions", 0)) for route in routes]
    horizon = max(horizons or [0])
    # The viable-band margin activates the filter before the critical boundary;
    # the critical margin scales with a bounded route horizon.  These are
    # activation guards, not physiology thresholds and do not alter BOUNDS.
    for name in active_needs:
        bounds = BOUNDS[name]
        value = float(physiology[name])
        viable_margin = (
            value - bounds.viable_low
            if name != "fatigue"
            else bounds.viable_high - value
        )
        critical_margin = _signed_critical_margin(name, value)
        if viable_margin <= 0.025 or critical_margin <= max(0.01, 0.004 * (horizon + 1)):
            return True
    return False


def assess_recovery_reachability_envelope(
    *,
    organism_tick: int,
    body_schema_id: str,
    physiology: Mapping[str, Any],
    active_needs: Sequence[str],
    observations: Sequence[Mapping[str, Any]],
    candidate: Any,
    authority_effect_branches: Sequence[Mapping[str, Any]],
    capability_support: Mapping[str, Mapping[str, Any]],
    body_energy_cost_scale: float = 1.0,
    drift_enabled: bool = True,
    max_route_steps: int = 32,
) -> dict[str, Any]:
    """Assess a bounded recovery opportunity using policy-visible state only.

    This is a pure shadow assessment.  It does not grant authority, execute a
    candidate, consume randomness, mutate learning, or inspect Habitat state.
    It deliberately certifies only a finite route envelope; terminal recovery
    remains conditional on later ordinary authority and verification.
    """
    if int(max_route_steps) < 1:
        raise ValueError("max_route_steps_must_be_positive")
    capability, params = _candidate_parts(candidate)
    common = {
        "organism_tick": int(organism_tick),
        "body_schema_id": str(body_schema_id),
        "physiology": {name: float(physiology[name]) for name in BOUNDS},
        "active_needs": tuple(str(item) for item in active_needs),
        "observations": tuple(dict(item) for item in observations),
        "candidate": candidate,
        "capability_support": capability_support,
        "body_energy_cost_scale": float(body_energy_cost_scale),
    }
    view = derive_recoverability_view(
        **common,
        authority_effect_branches=tuple(dict(branch) for branch in authority_effect_branches),
        drift_enabled=bool(drift_enabled),
    )
    route_status = str(view["candidate_projection"].get("status"))
    classification = _envelope_status(view)
    bounded_routes = [
        route
        for route in view["candidate_projection"].get("post_candidate_routes", [])
        if route.get("status") == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    ]
    unknown_routes = [
        route
        for route in view["candidate_projection"].get("post_candidate_routes", [])
        if route.get("status") not in {
            RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value,
            RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value,
        }
    ]
    return {
        "schema": "AS018_RECOVERY_REACHABILITY_ENVELOPE_V1",
        "organism_tick": int(organism_tick),
        "body_schema_id": str(body_schema_id)[:MAX_TEXT_LENGTH],
        "candidate": {"capability": capability, "params": params},
        "active_needs": [str(item) for item in view["active_needs"]],
        "active_need_status": {
            str(need): (
                BOUNDED_RECOVERY_OPPORTUNITY
                if _dimension_status(view, str(need))
                == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
                else MAY_ROUTE
                if _dimension_status(view, str(need))
                == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
                else UNKNOWN_ROUTE
            )
            for need in view["active_needs"]
        },
        "status": classification,
        "robust_now": False,
        "route_status": route_status,
        "bounded_opportunity_count": len(bounded_routes),
        "unknown_route_count": len(unknown_routes),
        "reserve_threatened": _reserve_threatened(
            physiology,
            view["active_needs"],
            view,
        ),
        "post_candidate_physiology": dict(view["candidate_projection"].get("post_candidate_physiology") or {}),
        "route_evidence": [dict(route) for route in view["candidate_projection"].get("post_candidate_routes", [])],
        "search_budget": {
            "max_route_steps": int(max_route_steps),
            "status": "BOUNDED_FINITE_ROUTE_ONLY",
        },
        "assumptions": {
            "policy_visible_sources_only": True,
            "terminal_success_not_guaranteed": True,
            "uncertainty_is_not_proof": True,
            "hidden_habitat_fields": 0,
            "drift_semantics": "physiology_owner_effect_clamp_then_drift_clamp",
            "drift_enabled": bool(drift_enabled),
        },
        "fixed_size": True,
        "persisted_state": False,
        "action_authority": False,
        "hidden_truth_fields": 0,
    }


def filter_recovery_reserve_candidates(
    *,
    organism_tick: int,
    body_schema_id: str,
    physiology: Mapping[str, Any],
    active_needs: Sequence[str],
    observations: Sequence[Mapping[str, Any]],
    candidates: Sequence[Any],
    capability_support: Mapping[str, Mapping[str, Any]],
    authority_effect_branches_for: Any,
    body_energy_cost_scale: float = 1.0,
    drift_enabled: bool = True,
    max_route_steps: int = 32,
) -> dict[str, Any]:
    """Constrain only candidates that eliminate every supported envelope branch."""
    baseline = assess_recovery_reachability_envelope(
        organism_tick=organism_tick,
        body_schema_id=body_schema_id,
        physiology=physiology,
        active_needs=active_needs,
        observations=observations,
        candidate={"capability": PROSPECTIVE_BASELINE_CAPABILITY, "params": {}},
        authority_effect_branches=({},),
        capability_support=capability_support,
        body_energy_cost_scale=body_energy_cost_scale,
        drift_enabled=drift_enabled,
        max_route_steps=max_route_steps,
    )
    activation = bool(
        baseline["status"] == BOUNDED_RECOVERY_OPPORTUNITY
        and baseline["reserve_threatened"]
    )
    kept: list[Any] = list(candidates)
    rejected: list[str] = []
    decisions: list[dict[str, Any]] = []
    if not activation:
        return {
            "schema": "AS018_RECOVERY_REACHABILITY_FILTER_V1",
            "activation": False,
            "reason": "reserve_threat_not_established",
            "baseline": baseline,
            "candidates": kept,
            "rejected": rejected,
            "decisions": decisions,
            "action_authority": False,
            "hidden_truth_fields": 0,
        }

    for candidate in candidates:
        branches = tuple(
            dict(branch)
            for branch in (authority_effect_branches_for(candidate) or ({},))
        )
        projected: list[dict[str, Any]] = []
        for branch in branches:
            projected.append(
                assess_recovery_reachability_envelope(
                    organism_tick=organism_tick,
                    body_schema_id=body_schema_id,
                    physiology=physiology,
                    active_needs=active_needs,
                    observations=observations,
                    candidate=candidate,
                    authority_effect_branches=(branch,),
                    capability_support=capability_support,
                    body_energy_cost_scale=body_energy_cost_scale,
                    drift_enabled=drift_enabled,
                    max_route_steps=max_route_steps,
                )
            )
        statuses = [str(item["status"]) for item in projected]
        known_preservation = any(
            status in {BOUNDED_RECOVERY_OPPORTUNITY, ROBUST_NOW}
            for status in statuses
        )
        unknown_branch = UNKNOWN_ROUTE in statuses
        eliminates_all = bool(statuses) and not known_preservation and not unknown_branch
        identity = _candidate_identity(candidate)
        decision = {
            "candidate": identity,
            "branch_statuses": statuses,
            "rejected": eliminates_all,
            "reason": "all_supported_branches_eliminate_bounded_opportunity"
            if eliminates_all
            else "preserved_or_uncertain",
        }
        decisions.append(decision)
        if eliminates_all:
            rejected.append(identity)
        else:
            kept_candidate = candidate
            if kept_candidate not in kept:
                kept.append(kept_candidate)
    rejected_set = set(rejected)
    kept = [
        candidate
        for candidate in kept
        if _candidate_identity(candidate)
        not in rejected_set
    ]
    return {
        "schema": "AS018_RECOVERY_REACHABILITY_FILTER_V1",
        "activation": True,
        "reason": "precritical_recovery_reserve_threat",
        "baseline": baseline,
        "candidates": kept,
        "rejected": rejected,
        "decisions": decisions,
        "action_authority": False,
        "hidden_truth_fields": 0,
    }
