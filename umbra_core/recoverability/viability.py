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

from umbra_core.physiology import (
    BOUNDS,
    project_verified_transition,
    verified_outcome_effect_branches,
)
from umbra_core.recoverability.contracts import EXECUTABLE, TERMINAL_CAPABILITIES
from umbra_core.util import canon_json


ROBUST_NOW = "ROBUST_NOW"
MAY_ROUTE = "MAY_ROUTE"
UNKNOWN_ROUTE = "UNKNOWN_ROUTE"
PROVEN_DIRECT_RECOVERY_PATH = "PROVEN_DIRECT_RECOVERY_PATH"
DIRECT_RECOVERY_PATH_NOT_PROVEN = "DIRECT_RECOVERY_PATH_NOT_PROVEN"
ASSESSMENT_ALLOWED = "ALLOWED"
ASSESSMENT_DENIED = "DENIED"
ASSESSMENT_UNKNOWN = "UNKNOWN"
CERTIFICATE_PROVEN = "PROVEN"
CERTIFICATE_UNKNOWN = "UNKNOWN"


def _candidate_identity(candidate: Any) -> str:
    """Stable exact behavioral identity; params are never capability-aliased."""
    return f"{getattr(candidate, 'capability', '')}:{canon_json(dict(getattr(candidate, 'params', {}) or {}))}"


@dataclass(frozen=True)
class RecoveryAssessmentContext:
    """Explicit facts used by a pure recovery assessment at one root."""

    root_id: str
    physiology: Mapping[str, float]
    observation_version: str
    body_binding_version: str
    governance_version: str
    model_version: str
    drift_enabled: bool = True


@dataclass(frozen=True)
class CandidateAssessment:
    """Pure shared authority result for one exact candidate and parameters."""

    root_id: str
    candidate_identity: str
    requested_params: Mapping[str, Any]
    execution_params: Mapping[str, Any]
    status: str
    reasons: tuple[str, ...]
    effect_branches: tuple[Mapping[str, float], ...]
    successor_physiology: Mapping[str, float] | None


@dataclass(frozen=True)
class RecoveryCertificate:
    """Bounded proof for the selected first action, never a global guarantee."""

    root_id: str
    first_candidate_identity: str
    status: str
    witness: tuple[str, ...]
    terminal_condition: str | None
    assumptions: Mapping[str, str]
    search_budget_status: str
    reason: str


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
    physiology: Mapping[str, float],
    branches: Sequence[Mapping[str, float]],
    *,
    drift_enabled: bool = True,
) -> tuple[bool, dict[str, float]]:
    """Return all-branch noncriticality and its conservative componentwise state."""
    projected: dict[str, float] = {}
    safe = True
    branch_states = [
        project_verified_transition(
            dict(physiology), dict(branch), drift_enabled=drift_enabled
        )
        for branch in (branches or ({},))
    ]
    for name, bounds in BOUNDS.items():
        values = [state[name] for state in branch_states]
        # The lower/upper critical boundary depends on the direction; retain
        # the value with least signed safety margin as evidence, not a score.
        projected[name] = min(
            values,
            key=lambda value: min(value - bounds.critical_low, bounds.critical_high - value),
        )
        if any(bounds.critical_violation(value) for value in values):
            safe = False
    return safe, projected


def assess_candidate(
    *,
    context: RecoveryAssessmentContext,
    candidate: Any,
    execution_params_for: Callable[[RecoveryAssessmentContext, Any], Mapping[str, Any] | None],
    eligible_for: Callable[[RecoveryAssessmentContext, Any], bool | None],
    compositional_admissible_for: Callable[[RecoveryAssessmentContext, Any, Sequence[Mapping[str, float]]], bool | None],
    executability_for: Callable[[RecoveryAssessmentContext, Any], str | None],
    governance_precondition_for: Callable[[RecoveryAssessmentContext, Any], bool | None],
    effect_branches_for: Callable[[RecoveryAssessmentContext, Any], Sequence[Mapping[str, float]] | None],
) -> CandidateAssessment:
    """Pure exact-candidate assessment shared by selection and certification.

    Callbacks must use the supplied context, not a captured live organism.  The
    function has no learning, RNG, persistence, or actuator side effects.
    """
    requested = dict(getattr(candidate, "params", {}) or {})
    identity = _candidate_identity(candidate)
    execution = execution_params_for(context, candidate)
    if execution is None:
        return CandidateAssessment(context.root_id, identity, requested, {}, ASSESSMENT_UNKNOWN,
                                   ("execution_params_unknown",), (), None)
    execution = dict(execution)
    execution_candidate = type(candidate)(str(getattr(candidate, "capability", "")), execution)
    eligibility = eligible_for(context, candidate)
    if eligibility is not True:
        return CandidateAssessment(context.root_id, identity, requested, execution,
                                   ASSESSMENT_UNKNOWN if eligibility is None else ASSESSMENT_DENIED,
                                   ("self_model_eligibility_unknown" if eligibility is None else "self_model_ineligible",), (), None)
    executable = executability_for(context, candidate)
    if executable != EXECUTABLE:
        return CandidateAssessment(context.root_id, identity, requested, execution,
                                   ASSESSMENT_UNKNOWN if executable is None or executable == ASSESSMENT_UNKNOWN else ASSESSMENT_DENIED,
                                   ("executability_unknown" if executable is None or executable == ASSESSMENT_UNKNOWN else "not_executable",), (), None)
    governance = governance_precondition_for(context, candidate)
    if governance is not True:
        return CandidateAssessment(context.root_id, identity, requested, execution,
                                   ASSESSMENT_UNKNOWN if governance is None else ASSESSMENT_DENIED,
                                   ("governance_precondition_unknown" if governance is None else "governance_precondition_denied",), (), None)
    branches = effect_branches_for(context, candidate)
    if not branches:
        return CandidateAssessment(context.root_id, identity, requested, execution,
                                   ASSESSMENT_UNKNOWN, ("effect_branches_unknown",), (), None)
    normalized = tuple(dict(branch) for branch in branches)
    composition = compositional_admissible_for(context, execution_candidate, normalized)
    if composition is not True:
        return CandidateAssessment(context.root_id, identity, requested, execution,
                                   ASSESSMENT_UNKNOWN if composition is None else ASSESSMENT_DENIED,
                                   ("compositional_constraints_unknown" if composition is None else "compositional_constraints_denied",), normalized, None)
    safe, projected = _project(context.physiology, normalized, drift_enabled=context.drift_enabled)
    if not safe:
        return CandidateAssessment(context.root_id, identity, requested, execution,
                                   ASSESSMENT_DENIED, ("verified_branch_safety_denied",), normalized, projected)
    return CandidateAssessment(context.root_id, identity, requested, execution,
                               ASSESSMENT_ALLOWED, (), normalized, projected)


def certify_candidate_recovery(
    *,
    context: RecoveryAssessmentContext,
    first_candidate: Any,
    assessments: Mapping[str, CandidateAssessment],
    successor_assessment_for: Callable[[RecoveryAssessmentContext, Mapping[str, float], Any], CandidateAssessment] | None = None,
    max_steps: int = 16,
    max_explored_states: int = 256,
) -> RecoveryCertificate:
    """Certify this exact first action, conservatively re-assessing successors.

    Without a successor-context authority callback, only an action that
    directly reaches the existing viable region is proven.  Missing future
    facts are UNKNOWN rather than an invented continuation or impossibility.
    """
    first_id = _candidate_identity(first_candidate)
    assumptions = {
        "observation_version": context.observation_version,
        "body_binding_version": context.body_binding_version,
        "governance_version": context.governance_version,
        "model_version": context.model_version,
    }
    first = assessments.get(first_id) or next(
        (value for value in assessments.values() if value.candidate_identity == first_id),
        None,
    )
    if first is None or first.status != ASSESSMENT_ALLOWED:
        return RecoveryCertificate(context.root_id, first_id, CERTIFICATE_UNKNOWN, (), None,
                                   assumptions, "NOT_STARTED", "first_action_not_allowed")
    successors = [
        project_verified_transition(dict(context.physiology), dict(branch), drift_enabled=context.drift_enabled)
        for branch in first.effect_branches
    ]
    if all(not active_recovery_needs_for(state) for state in successors):
        return RecoveryCertificate(context.root_id, first_id, CERTIFICATE_PROVEN, (first_id,),
                                   "current_viable_region", assumptions, "COMPLETE", "direct_recovery")
    # A current terminal endpoint may need several immediate applications.
    # This remains conditional on the exact root versions above; the runtime
    # drops/reassesses the witness at the next root if any condition changes.
    # No position/body fact is projected or invented here.
    states = successors
    witness = [first_id]
    for _ in range(1, max_steps):
        if len(states) > max_explored_states:
            return RecoveryCertificate(context.root_id, first_id, CERTIFICATE_UNKNOWN, tuple(witness), None,
                                       assumptions, "BUDGET_EXHAUSTED", "bounded_search_incomplete")
        states = [
            project_verified_transition(dict(state), dict(branch), drift_enabled=context.drift_enabled)
            for state in states for branch in first.effect_branches
        ]
        witness.append(first_id)
        if all(not active_recovery_needs_for(state) for state in states):
            return RecoveryCertificate(context.root_id, first_id, CERTIFICATE_PROVEN, tuple(witness),
                                       "current_viable_region", assumptions, "COMPLETE", "bounded_direct_recovery")
    if successor_assessment_for is None:
        return RecoveryCertificate(context.root_id, first_id, CERTIFICATE_UNKNOWN, (first_id,), None,
                                   assumptions, "SUCCESSOR_CONTEXT_REQUIRED", "future_context_not_assumed")
    # Keep the certified domain explicitly finite and require every reachable
    # branch to possess one lawful next step.  The callback supplies a fresh
    # explicit successor context; the live root is never read as that state.
    explored = 0
    for state in successors:
        if explored >= max_explored_states or max_steps < 2:
            return RecoveryCertificate(context.root_id, first_id, CERTIFICATE_UNKNOWN, (first_id,), None,
                                       assumptions, "BUDGET_EXHAUSTED", "bounded_search_incomplete")
        explored += 1
        permitted = [
            assessment for assessment in assessments.values()
            if successor_assessment_for(context, state, first_candidate).status == ASSESSMENT_ALLOWED
        ]
        if not permitted:
            return RecoveryCertificate(context.root_id, first_id, CERTIFICATE_UNKNOWN, (first_id,), None,
                                       assumptions, "EXHAUSTED_SUPPORTED_DOMAIN", "no_supported_successor")
    return RecoveryCertificate(context.root_id, first_id, CERTIFICATE_UNKNOWN, (first_id,), None,
                               assumptions, "SUCCESSOR_REVALIDATION_REQUIRED", "conditional_witness_only")


def _corrects_need(
    need: str,
    physiology: Mapping[str, float],
    branches: Sequence[Mapping[str, float]],
    *,
    drift_enabled: bool = True,
) -> bool:
    direction = _direction(need, float(physiology[need]))
    if not direction:
        return False
    # A recovery endpoint is only directional if every authority-reachable
    # branch moves the requested dimension toward its existing ideal. Use the
    # physiology owner's two-stage clamp, rather than an approximate sum of
    # effect and drift at saturation boundaries.
    return bool(branches) and all(
        direction
        * (
            project_verified_transition(
                dict(physiology), dict(branch), drift_enabled=drift_enabled
            )[need]
            - float(physiology[need])
        )
        > 0.0
        for branch in branches
    )


def _success_branch_corrects_need(
    need: str,
    physiology: Mapping[str, float],
    branches: Sequence[Mapping[str, float]],
    *,
    drift_enabled: bool = True,
) -> bool:
    """Direction for a MAY route after a future terminal success.

    This never produces a robust reserve: a terminal failure or failure to
    arrive remains open-world.  It only permits the ordinary target-bound
    approach candidate to remain visible to active recovery.
    """
    return _corrects_need(
        need, physiology, tuple(branches[:1]), drift_enabled=drift_enabled
    )


def active_recovery_needs_for(physiology: Mapping[str, float]) -> tuple[str, ...]:
    """Mirror ``Physiology.active_recovery_needs`` for a projected state."""
    active: list[str] = []
    for name, bounds in BOUNDS.items():
        value = float(physiology[name])
        if name == "fatigue":
            actionable = value > bounds.viable_high
        elif name in {"energy", "integrity"}:
            actionable = value < bounds.viable_low
        else:
            actionable = not bounds.in_viable(value)
        if actionable:
            active.append(name)
    return tuple(active)


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
    assessment_for: Callable[[Any], CandidateAssessment] | None = None,
    drift_enabled: bool = True,
) -> tuple[RegulatoryRecoveryRoute, ...]:
    """Derive direct endpoints and explicitly non-authoritative MAY routes.

    The only endpoint/need relationship comes from each candidate's current
    authority effect branches.  Target identity comes from ordinary candidate
    parameters and policy-visible observations; no Habitat identifier or
    coordinate enters the result.
    """
    needs = tuple(name for name in BOUNDS if name in {str(value) for value in active_needs})
    # Current direct regulation is an effect/executability question, not a
    # terminal-affordance category.  For example, immediate ORIENT and IDLE
    # can lawfully regulate physiology without requiring a target-affordance
    # readiness check.  Terminal membership remains relevant only to a
    # distant MAY route, where a future endpoint must be target-bound.
    direct = tuple(candidates)
    terminal = [candidate for candidate in direct if str(candidate.capability) in TERMINAL_CAPABILITIES]
    observation_by_kind = {
        str(observation.get("kind", "")): observation
        for observation in observations
        if observation.get("kind")
    }
    routes: list[RegulatoryRecoveryRoute] = []

    for endpoint in direct:
        endpoint_target = _target(endpoint)
        assessment = assessment_for(endpoint) if assessment_for is not None else None
        branches = tuple(dict(branch) for branch in authority_effect_branches_for(endpoint))
        executable = (
            assessment.status == ASSESSMENT_ALLOWED
            if assessment is not None
            else current_executability_for(endpoint) == EXECUTABLE
        )
        safe, projected = _project(physiology, branches, drift_enabled=drift_enabled)
        for need in needs:
            if executable and safe and _corrects_need(
                need, physiology, branches, drift_enabled=drift_enabled
            ):
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
                if _success_branch_corrects_need(
                    need,
                    physiology,
                    endpoint_branches,
                    drift_enabled=drift_enabled,
                ):
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


def preserves_robust_recovery_reserve(
    *,
    candidate: Any,
    physiology: Mapping[str, float],
    candidates: Sequence[Any],
    observations: Sequence[Mapping[str, Any]],
    authority_effect_branches_for: Callable[[Any], Sequence[Mapping[str, float]]],
    current_executability_for: Callable[[Any], str],
    drift_enabled: bool = True,
    continuation_depth: int = 2,
) -> bool:
    """Whether every next branch retains a bounded robust recovery continuation.

    This is categorical controlled-invariance evidence: it evaluates only
    current ordinary candidates and their trusted branches, and never assumes
    a future terminal arrival or assigns a score.  A one-step route inventory
    is insufficient: its listed endpoints can themselves leave no safe action
    for another active physiological dimension.  ``continuation_depth`` asks
    whether a currently robust endpoint has a bounded next endpoint that also
    preserves the same categorical reserve.
    """
    if continuation_depth < 1:
        raise ValueError("continuation_depth_must_be_positive")

    def state_has_continuation(
        state: Mapping[str, float],
        remaining_depth: int,
    ) -> bool:
        needs = active_recovery_needs_for(state)
        if not needs:
            return True
        successor_routes = enumerate_regulatory_recovery_routes(
            physiology=state,
            active_needs=needs,
            candidates=candidates,
            observations=observations,
            authority_effect_branches_for=authority_effect_branches_for,
            current_executability_for=current_executability_for,
            drift_enabled=drift_enabled,
        )
        direct = robust_candidates(successor_routes)
        covered_needs = {
            route.need for route in successor_routes if route.status == ROBUST_NOW
        }
        if not set(needs).issubset(covered_needs):
            return False
        if remaining_depth == 1:
            return True
        # A set of individually corrective actions is not a controlled
        # invariant unless at least one of those actions keeps a next bounded
        # continuation.  This remains effect- and preflight-derived: no need
        # receives authored priority and no future terminal arrival is assumed.
        return any(
            preserves_robust_recovery_reserve(
                candidate=next_candidate,
                physiology=state,
                candidates=candidates,
                observations=observations,
                authority_effect_branches_for=authority_effect_branches_for,
                current_executability_for=current_executability_for,
                drift_enabled=drift_enabled,
                continuation_depth=remaining_depth - 1,
            )
            for next_candidate in direct
        )

    branches = tuple(dict(branch) for branch in authority_effect_branches_for(candidate))
    if not branches:
        return False
    for branch in branches:
        successor = project_verified_transition(
            dict(physiology), branch, drift_enabled=drift_enabled
        )
        if not state_has_continuation(successor, continuation_depth):
            return False
    return True


def direct_regulatory_recovery_path_status(
    *,
    physiology: Mapping[str, float],
    candidates: Sequence[Any],
    observations: Sequence[Mapping[str, Any]],
    authority_effect_branches_for: Callable[[Any], Sequence[Mapping[str, float]]],
    current_executability_for: Callable[[Any], str],
    drift_enabled: bool = True,
    max_explored_states: int = 256,
) -> str:
    """Return whether current direct regulators prove return to viability.

    The search is deliberately limited to current, already-executable effect
    branches.  It neither assumes a future arrival at a terminal opportunity
    nor inserts a route model.  A bounded search that cannot establish a
    direct path is *not* a proof of impossibility; callers may only use that
    distinction to avoid letting a direct-regulator loop suppress a currently
    safe, policy-visible MAY approach.
    """
    if max_explored_states < 1:
        raise ValueError("max_explored_states_must_be_positive")

    def state_key(state: Mapping[str, float]) -> tuple[float, ...]:
        return tuple(round(float(state[name]), 12) for name in BOUNDS)

    explored: set[tuple[float, ...]] = set()
    visiting: set[tuple[float, ...]] = set()
    memo: dict[tuple[float, ...], bool] = {}
    exhausted_budget = False

    def reaches_viability(state: Mapping[str, float]) -> bool:
        nonlocal exhausted_budget
        needs = active_recovery_needs_for(state)
        if not needs:
            return True
        key = state_key(state)
        if key in memo:
            return memo[key]
        if key in visiting:
            # Re-entering a state cannot establish a new finite direct path.
            return False
        if key not in explored:
            if len(explored) >= max_explored_states:
                exhausted_budget = True
                return False
            explored.add(key)
        visiting.add(key)
        try:
            routes = enumerate_regulatory_recovery_routes(
                physiology=state,
                active_needs=needs,
                candidates=candidates,
                observations=observations,
                authority_effect_branches_for=authority_effect_branches_for,
                current_executability_for=current_executability_for,
                drift_enabled=drift_enabled,
            )
            for candidate in robust_candidates(routes):
                branches = tuple(
                    dict(branch) for branch in authority_effect_branches_for(candidate)
                )
                if not branches:
                    continue
                successors = [
                    project_verified_transition(
                        dict(state), branch, drift_enabled=drift_enabled
                    )
                    for branch in branches
                ]
                if all(reaches_viability(successor) for successor in successors):
                    memo[key] = True
                    return True
            memo[key] = False
            return False
        finally:
            visiting.remove(key)

    if reaches_viability(dict(physiology)):
        return PROVEN_DIRECT_RECOVERY_PATH
    # Both an exhausted bounded search and an explored dead end are deliberately
    # non-authoritative here: a current direct path was not proven, but no
    # claim about unobserved future routes is made.
    _ = exhausted_budget
    return DIRECT_RECOVERY_PATH_NOT_PROVEN


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
