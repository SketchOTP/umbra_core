"""Source-backed categorical recovery viability for ordinary policy candidates.

This module owns neither policy state nor a need-to-action table.  It derives
regulatory endpoints from the authoritative branch effects of terminal
candidates already emitted by ordinary candidate generation.  It deliberately
distinguishes a currently executable robust endpoint from a target-bound MAY
route: observed movement evidence cannot become a future-arrival guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping, Sequence

from umbra_core.physiology import BOUNDS, DEFAULT_DRIFT, verified_outcome_effect_branches
from umbra_core.recoverability.contracts import EXECUTABLE, TERMINAL_CAPABILITIES
from umbra_core.util import clamp


ROBUST_NOW = "ROBUST_NOW"
MAY_ROUTE = "MAY_ROUTE"
UNKNOWN_ROUTE = "UNKNOWN_ROUTE"


@dataclass(frozen=True)
class RegulatoryRecoveryRoute:
    """One derived route, retaining the ordinary candidate that realizes it."""

    need: str
    status: str
    candidate: Any
    endpoint_capability: str
    target_kind: str | None
    source: str
    projected_physiology: Mapping[str, float] | None
    blocked_by: str | None = None


def _target(candidate: Any) -> str | None:
    params = dict(getattr(candidate, "params", {}) or {})
    value = params.get("toward") or params.get("from")
    return None if value is None else str(value)


def _direction(name: str, value: float) -> float:
    """Direction toward existing ideal: +1 rises, -1 falls, 0 is neutral."""
    ideal = BOUNDS[name].ideal
    return 1.0 if value < ideal else -1.0 if value > ideal else 0.0


def _project(
    physiology: Mapping[str, float], branches: Sequence[Mapping[str, float]]
) -> tuple[bool, dict[str, float]]:
    """Return all-branch noncriticality and its conservative componentwise state."""
    projected: dict[str, float] = {}
    safe = True
    for name, bounds in BOUNDS.items():
        values = [
            clamp(
                float(physiology[name])
                + float(branch.get(name, 0.0))
                + float(DEFAULT_DRIFT.get(name, 0.0))
            )
            for branch in (branches or ({},))
        ]
        # The lower/upper critical boundary depends on the direction; retain
        # the value with least signed safety margin as evidence, not a score.
        projected[name] = min(
            values,
            key=lambda value: min(value - bounds.critical_low, bounds.critical_high - value),
        )
        if any(bounds.critical_violation(value) for value in values):
            safe = False
    return safe, projected


def _corrects_need(
    need: str,
    physiology: Mapping[str, float],
    branches: Sequence[Mapping[str, float]],
) -> bool:
    direction = _direction(need, float(physiology[need]))
    if not direction:
        return False
    # A recovery endpoint is only directional if every authority-reachable
    # branch moves the requested dimension toward its existing ideal.
    return bool(branches) and all(
        direction * (
            float(branch.get(need, 0.0)) + float(DEFAULT_DRIFT.get(need, 0.0))
        ) > 0.0
        for branch in branches
    )


def _success_branch_corrects_need(
    need: str, physiology: Mapping[str, float], branches: Sequence[Mapping[str, float]]
) -> bool:
    """Direction for a MAY route after a future terminal success.

    This never produces a robust reserve: a terminal failure or failure to
    arrive remains open-world.  It only permits the ordinary target-bound
    approach candidate to remain visible to active recovery.
    """
    return _corrects_need(need, physiology, tuple(branches[:1]))


def _policy_bounded_approach(
    candidate: Any, observation: Mapping[str, Any] | None
) -> Any | None:
    """Keep a MAY recovery approach inside its current policy-visible range.

    This is not a route-length proof and cannot create a robust reserve.  It
    only avoids issuing a known full step after the policy observation already
    reports that the target is nearer than that step.  The existing terminal
    preflight remains the authority for arrival and use.
    """
    if observation is None:
        return None
    try:
        distance = float(observation.get("estimated_distance"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(distance) or distance <= 0.0:
        return None
    params = dict(getattr(candidate, "params", {}) or {})
    try:
        nominal_step = float(params.get("step", 1.0))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(nominal_step) or nominal_step <= 0.0:
        return None
    params["step"] = min(nominal_step, distance)
    params["source"] = "policy_visible_recovery_approach"
    return type(candidate)(str(candidate.capability), params)


def enumerate_regulatory_recovery_routes(
    *,
    physiology: Mapping[str, float],
    active_needs: Sequence[str],
    candidates: Sequence[Any],
    observations: Sequence[Mapping[str, Any]],
    authority_effect_branches_for: Callable[[Any], Sequence[Mapping[str, float]]],
    current_executability_for: Callable[[Any], str],
) -> tuple[RegulatoryRecoveryRoute, ...]:
    """Derive direct endpoints and explicitly non-authoritative MAY routes.

    The only endpoint/need relationship comes from each candidate's current
    authority effect branches.  Target identity comes from ordinary candidate
    parameters and policy-visible observations; no Habitat identifier or
    coordinate enters the result.
    """
    needs = tuple(name for name in BOUNDS if name in {str(value) for value in active_needs})
    terminal = [candidate for candidate in candidates if str(candidate.capability) in TERMINAL_CAPABILITIES]
    observation_by_kind = {
        str(observation.get("kind", "")): observation
        for observation in observations
        if observation.get("kind")
    }
    routes: list[RegulatoryRecoveryRoute] = []

    for endpoint in terminal:
        endpoint_target = _target(endpoint)
        branches = tuple(dict(branch) for branch in authority_effect_branches_for(endpoint))
        executable = current_executability_for(endpoint) == EXECUTABLE
        safe, projected = _project(physiology, branches)
        for need in needs:
            if executable and safe and _corrects_need(need, physiology, branches):
                routes.append(
                    RegulatoryRecoveryRoute(
                        need=need,
                        status=ROBUST_NOW,
                        candidate=endpoint,
                        endpoint_capability=str(endpoint.capability),
                        target_kind=endpoint_target,
                        source="current_authority_preflight",
                        projected_physiology=projected,
                    )
                )

    # A non-executable endpoint can still describe a target-bound option for
    # active recovery.  It is not a robust recovery reserve: route progress
    # and future terminal execution remain open-world / stochastic.
    for endpoint in terminal:
        if current_executability_for(endpoint) == EXECUTABLE:
            continue
        endpoint_target = _target(endpoint)
        if endpoint_target is None or endpoint_target not in observation_by_kind:
            continue
        endpoint_branches = tuple(
            dict(branch) for branch in verified_outcome_effect_branches(str(endpoint.capability))
        )
        for approach in candidates:
            if str(approach.capability) != "APPROACH" or _target(approach) != endpoint_target:
                continue
            bounded_approach = _policy_bounded_approach(
                approach, observation_by_kind[endpoint_target]
            )
            if bounded_approach is None:
                continue
            for need in needs:
                if _success_branch_corrects_need(need, physiology, endpoint_branches):
                    routes.append(
                        RegulatoryRecoveryRoute(
                            need=need,
                            status=MAY_ROUTE,
                            candidate=bounded_approach,
                            endpoint_capability=str(endpoint.capability),
                            target_kind=endpoint_target,
                            source="policy_visible_target_bound_candidate_pair",
                            projected_physiology=None,
                            blocked_by="future_arrival_not_hard_proven",
                        )
                    )

    # Stable ordering makes the evaluator deterministic and does not consume
    # RNG.  Duplicates may arise from an ordinary candidate pool; preserve one.
    unique: dict[tuple[str, str, str | None, str], RegulatoryRecoveryRoute] = {}
    for route in routes:
        key = (route.need, route.endpoint_capability, route.target_kind, route.status)
        unique.setdefault(key, route)
    return tuple(
        unique[key]
        for key in sorted(unique, key=lambda value: (value[0], value[1], value[2] or "", value[3]))
    )


def robust_candidates(routes: Sequence[RegulatoryRecoveryRoute]) -> tuple[Any, ...]:
    """Return deduplicated current endpoints only; MAY routes never imply authority."""
    selected: list[Any] = []
    seen: set[tuple[str, str | None]] = set()
    for route in routes:
        if route.status != ROBUST_NOW:
            continue
        key = (str(route.candidate.capability), route.target_kind)
        if key not in seen:
            seen.add(key)
            selected.append(route.candidate)
    return tuple(selected)


def may_route_candidates(routes: Sequence[RegulatoryRecoveryRoute]) -> tuple[Any, ...]:
    """Return source-visible approach candidates only when no direct endpoint exists."""
    selected: list[Any] = []
    seen: set[tuple[str, str | None]] = set()
    for route in routes:
        if route.status != MAY_ROUTE:
            continue
        key = (str(route.candidate.capability), route.target_kind)
        if key not in seen:
            seen.add(key)
            selected.append(route.candidate)
    return tuple(selected)
