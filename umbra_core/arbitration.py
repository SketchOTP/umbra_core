"""Action arbitration — vector scoring, hysteresis, anti-thrash. No LLM."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Mapping

from umbra_core.embodiment import CAPABILITIES
from umbra_core.physiology import (
    BOUNDS,
    DEFAULT_DRIFT,
    OUTCOME_EFFECTS,
    Physiology,
    verified_outcome_effects,
    verified_outcome_effect_branches,
)
from umbra_core.temporal.policy import PolicyExpectationView
from umbra_core.util import SeededRNG, canon_json, clamp
from umbra_core.wait_execution import (
    FallbackBias,
    MAXIMUM_WAIT_TICKS,
    WaitJournal,
    wait_deadline_age_tick,
)
from umbra_core.recoverability.contracts import candidate_is_admissible
from umbra_core.recoverability import prospective_recoverability_transition

# ponytail: frozen modifier caps at D-010 Task 6; hardened at Stage B freeze.
ACTIVE_POSITIVE_CAP = 0.35
ACTIVE_NEGATIVE_CAP = -0.15
UNCERTAIN_POSITIVE_CAP = 0.12
UNCERTAIN_NEGATIVE_CAP = -0.06
COMBINED_TEMPORAL_CAP = 0.40
PER_TICK_NEGATIVE_FLOOR = -0.50
MAX_EXPECTATIONS_PER_CANDIDATE = 2
PREPARATION_HORIZON_TICKS = 5
TEMPORAL_MODIFIER_TARGETS = frozenset({"MOVE", "APPROACH", "INSPECT", "REST"})
WAIT_CAPABILITY = "WAIT"
CHARGE_SELECTION_DISTANCE = 1.5
APPROACH_RECOVERY_STEP = 1.5


@dataclass
class ManipulationCandidate:
    """Address-only MANIPULATE candidate — never carries authoritative object_id."""

    target_address_ref: str
    perception_evidence_ref: str
    perception_state_version: int
    perceived_object_kind: str
    perceived_affordance_ref: str
    parameters: dict[str, Any]
    capability: str = "MANIPULATE"
    source: str = "NEED_RELEVANCE"
    expected_outcome: str = ""
    latency: float = 0.0
    effort: float = 0.0
    success_confidence: float = 0.5
    uncertainty: float = 0.5
    supporting_evidence_refs: tuple[str, ...] = ()

    def to_candidate(self) -> Candidate:
        return Candidate(
            self.capability,
            {
                "target_address_ref": self.target_address_ref,
                "perception_evidence_ref": self.perception_evidence_ref,
                "perception_state_version": self.perception_state_version,
                "perceived_object_kind": self.perceived_object_kind,
                "perceived_affordance_ref": self.perceived_affordance_ref,
                "parameters": dict(self.parameters),
                "source": self.source,
            },
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "target_address_ref": self.target_address_ref,
            "perception_evidence_ref": self.perception_evidence_ref,
            "perception_state_version": self.perception_state_version,
            "perceived_object_kind": self.perceived_object_kind,
            "perceived_affordance_ref": self.perceived_affordance_ref,
            "parameters": dict(self.parameters),
            "source": self.source,
        }


_AFFORDANCE_DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "affordance:resource:use": {"kind": "USE"},
    "affordance:portable:pick_up": {"kind": "PICK_UP", "hold_slot": 0},
    "affordance:activatable:activate": {"kind": "ACTIVATE"},
}


@dataclass
class Candidate:
    capability: str
    params: dict[str, Any]
    scores: dict[str, float] = field(default_factory=dict)
    total: float = 0.0


@dataclass
class ArbitrationState:
    last_capability: str | None = None
    last_switch_tick: int = 0
    consecutive_same: int = 0
    retry_counts: dict[str, int] = field(default_factory=dict)
    visited_cells: set[tuple[int, int]] = field(default_factory=set)
    action_counts: dict[str, int] = field(default_factory=dict)
    thrash_events: int = 0
    hysteresis: float = 0.12
    max_retries: int = 4
    search_heading: float = 0.0
    discovery_actions_remaining: int = 0
    discovery_cooldown_until: int = 0
    reacquisition_streak: int = 0
    recovery_focus: str | None = None
    last_verified_denial: dict[str, str] | None = None
    # ablation flags
    hide_physiology: bool = False
    mode: str = "full"  # full | random | scripted

    def to_state(self) -> dict[str, Any]:
        return {
            "last_capability": self.last_capability,
            "last_switch_tick": self.last_switch_tick,
            "consecutive_same": self.consecutive_same,
            "retry_counts": dict(self.retry_counts),
            "visited_cells": [list(c) for c in self.visited_cells],
            "action_counts": dict(self.action_counts),
            "thrash_events": self.thrash_events,
            "hysteresis": self.hysteresis,
            "max_retries": self.max_retries,
            "search_heading": self.search_heading,
            "discovery_actions_remaining": self.discovery_actions_remaining,
            "discovery_cooldown_until": self.discovery_cooldown_until,
            "reacquisition_streak": self.reacquisition_streak,
            "recovery_focus": self.recovery_focus,
            "last_verified_denial": dict(self.last_verified_denial)
            if self.last_verified_denial
            else None,
            "hide_physiology": self.hide_physiology,
            "mode": self.mode,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> ArbitrationState:
        s = cls(
            last_capability=d.get("last_capability"),
            last_switch_tick=int(d.get("last_switch_tick", 0)),
            consecutive_same=int(d.get("consecutive_same", 0)),
            retry_counts=dict(d.get("retry_counts", {})),
            action_counts=dict(d.get("action_counts", {})),
            thrash_events=int(d.get("thrash_events", 0)),
            hysteresis=float(d.get("hysteresis", 0.12)),
            max_retries=int(d.get("max_retries", 4)),
            search_heading=float(d.get("search_heading", 0.0)),
            discovery_actions_remaining=int(d.get("discovery_actions_remaining", 0)),
            discovery_cooldown_until=int(d.get("discovery_cooldown_until", 0)),
            reacquisition_streak=int(d.get("reacquisition_streak", 0)),
            recovery_focus=d.get("recovery_focus"),
            last_verified_denial=(
                dict(d["last_verified_denial"])
                if d.get("last_verified_denial")
                else None
            ),
            hide_physiology=bool(d.get("hide_physiology", False)),
            mode=str(d.get("mode", "full")),
        )
        s.visited_cells = {tuple(c) for c in d.get("visited_cells", [])}
        return s


SCRIPT_CYCLE = ["ORIENT", "MOVE", "MOVE", "INSPECT", "MOVE", "CHARGE", "REST", "IDLE"]
RECOVERY_DENIAL_REASONS = frozenset(
    {"not_at_resource", "not_at_affordance", "not_executable", "not_at_rest"}
)


def _modifier_cap_for_status(status: str) -> tuple[float, float]:
    if status == "ACTIVE":
        return ACTIVE_POSITIVE_CAP, ACTIVE_NEGATIVE_CAP
    return UNCERTAIN_POSITIVE_CAP, UNCERTAIN_NEGATIVE_CAP


def _view_modifier_delta(view: PolicyExpectationView, capability: str) -> float:
    if capability not in TEMPORAL_MODIFIER_TARGETS:
        return 0.0
    positive_cap, negative_cap = _modifier_cap_for_status(view.status)
    proximity = clamp(
        1.0 - abs(view.uncertainty),
        0.0,
        1.0,
    )
    if view.status == "UNCERTAIN":
        exploratory = min(positive_cap, view.confidence * positive_cap * proximity)
        return max(0.0, exploratory)
    signed = (view.confidence - 0.5) * 2.0 * proximity
    if signed >= 0.0:
        return min(signed * positive_cap, positive_cap)
    return max(signed * abs(negative_cap), negative_cap)


def apply_temporal_modifiers(
    candidates: list[Candidate],
    policy_views: tuple[PolicyExpectationView, ...],
    *,
    effective_age_ticks: int,
    fallback_biases: tuple[FallbackBias, ...] = (),
) -> None:
    """Apply capped soft temporal modifiers before signed cancellation."""
    if policy_views:
        eligible_views = [
            view
            for view in policy_views
            if (view.window_start - PREPARATION_HORIZON_TICKS)
            <= effective_age_ticks
            <= view.window_end
        ]
        eligible_views = sorted(eligible_views, key=lambda v: v.recurrence_id)[
            :MAX_EXPECTATIONS_PER_CANDIDATE
        ]
        for cand in candidates:
            if cand.capability not in TEMPORAL_MODIFIER_TARGETS:
                continue
            total_delta = 0.0
            for view in eligible_views:
                total_delta += _view_modifier_delta(view, cand.capability)
            total_delta = clamp(total_delta, PER_TICK_NEGATIVE_FLOOR, COMBINED_TEMPORAL_CAP)
            cand.total += total_delta
            cand.scores["temporal_modifier"] = (
                cand.scores.get("temporal_modifier", 0.0) + total_delta
            )
    for bias in fallback_biases:
        for cand in candidates:
            if cand.capability != bias.candidate_class:
                continue
            cand.total += bias.bounded_delta
            cand.scores["fallback_bias"] = (
                cand.scores.get("fallback_bias", 0.0) + bias.bounded_delta
            )


def wait_window_open(view: PolicyExpectationView, effective_age_ticks: int) -> bool:
    return view.window_start <= effective_age_ticks <= view.window_end


def propose_wait_candidates(
    policy_views: tuple[PolicyExpectationView, ...],
    *,
    effective_age_ticks: int,
    wait_journal: WaitJournal | None = None,
) -> list[Candidate]:
    """Generate WAIT only for ACTIVE expectations inside the open window."""
    cands: list[Candidate] = []
    for view in policy_views:
        if view.status != "ACTIVE":
            continue
        if not wait_window_open(view, effective_age_ticks):
            continue
        if wait_journal is not None and wait_journal.is_suppressed(
            view.recurrence_id,
            view.expectation_version,
            effective_age_ticks,
        ):
            continue
        deadline = wait_deadline_age_tick(
            started_age_tick=effective_age_ticks,
            window_end=view.window_end,
            maximum_wait_ticks=MAXIMUM_WAIT_TICKS,
        )
        cands.append(
            Candidate(
                WAIT_CAPABILITY,
                {
                    "recurrence_id": view.recurrence_id,
                    "window_start": view.window_start,
                    "window_end": view.window_end,
                    "maximum_wait_ticks": MAXIMUM_WAIT_TICKS,
                    "expectation_version": view.expectation_version,
                    "wait_deadline": deadline,
                    "interrupt_conditions": (),
                    "source": "TEMPORAL_EXPECTATION",
                },
            )
        )
    return cands


def active_fallback_biases(
    wait_journal: WaitJournal,
    *,
    effective_age_ticks: int,
) -> tuple[FallbackBias, ...]:
    biases: list[FallbackBias] = []
    for execution in wait_journal.executions.values():
        if not execution.is_terminal():
            continue
        if execution.fallback_bias is None:
            continue
        bias = execution.fallback_bias
        expires_at = execution.started_age_tick + bias.expires_after_ticks
        if effective_age_ticks <= expires_at:
            biases.append(bias)
    return tuple(biases)


class Arbitrator:
    def __init__(self, state: ArbitrationState | None = None):
        self.state = state or ArbitrationState()

    @staticmethod
    def _introduces_critical_boundary(
        cand: Candidate,
        phys: Physiology,
        *,
        ignore: str | None = None,
        effect_branches: tuple[dict[str, float], ...] | None = None,
    ) -> bool:
        """Reject actions that make the next decision state critical.

        The runtime applies DEFAULT_DRIFT at the beginning of the next tick,
        before perception and arbitration. Safety therefore projects the
        verified action effect and that unavoidable drift together. The legacy
        ignore parameter remains for API compatibility, but the next-decision
        invariant covers every homeostatic variable.
        """
        _ = ignore
        drift = DEFAULT_DRIFT if phys.drift_enabled else {}
        branches = effect_branches or verified_outcome_effect_branches(cand.capability)
        for effects in branches:
            for name in BOUNDS:
                before = phys.get(name)
                after = clamp(
                    before
                    + float(effects.get(name, 0.0))
                    + float(drift.get(name, 0.0))
                )
                if not BOUNDS[name].critical_violation(before) and BOUNDS[name].critical_violation(after):
                    return True
        return False

    @staticmethod
    def _intent_behavioral_params(value: Any) -> Any:
        provenance_keys = {
            "source", "memory_item_id", "practice_goal_id", "routine_skill_id",
            "goal_id", "trace_id", "provenance",
        }
        if isinstance(value, dict):
            return {
                str(key): Arbitrator._intent_behavioral_params(item)
                for key, item in value.items()
                if str(key) not in provenance_keys
            }
        if isinstance(value, list):
            return [Arbitrator._intent_behavioral_params(item) for item in value]
        if isinstance(value, tuple):
            return tuple(Arbitrator._intent_behavioral_params(item) for item in value)
        return value

    @classmethod
    def _canonical_intent_candidates(
        cls, candidates: list[Candidate]
    ) -> list[Candidate]:
        # Canonicalize and deduplicate active intents without source weight.
        ordered = sorted(
            candidates,
            key=lambda candidate: (
                str(candidate.capability),
                canon_json(cls._intent_behavioral_params(candidate.params)),
                canon_json(candidate.params),
            ),
        )
        unique: list[Candidate] = []
        seen: set[tuple[str, bytes]] = set()
        for candidate in ordered:
            key = (
                str(candidate.capability),
                canon_json(cls._intent_behavioral_params(candidate.params)),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    @staticmethod
    def _preventive_attention_dimensions(phys: Physiology) -> frozenset[str]:
        """Return noncritical dimensions already marked urgent by physiology."""
        if phys.critical_any():
            return frozenset()
        active = set(phys.active_recovery_needs())
        urgency = phys.vector_urgency()
        return frozenset(
            name
            for name in BOUNDS
            if name not in active and float(urgency.get(name, 0.0)) > 0.0
        )

    @classmethod
    def _candidate_regulatory_dimensions(
        cls, candidate: Candidate, phys: Physiology
    ) -> frozenset[str]:
        """Derive support from existing verified effects and visible route meaning."""
        attention = cls._preventive_attention_dimensions(phys)
        if not attention:
            return frozenset()
        effects = verified_outcome_effects(candidate.capability, True)
        dimensions: set[str] = set()
        for name in attention:
            value = phys.get(name)
            ideal = BOUNDS[name].ideal
            direction = 1.0 if value < ideal else -1.0 if value > ideal else 0.0
            delta = float(effects.get(name, 0.0))
            if direction and delta * direction > 0.0:
                dimensions.add(name)

        toward = candidate.params.get("toward")
        if toward in {"resource", "novel_crystal"} and "energy" in attention:
            dimensions.add("energy")
        if toward == "rest" and "fatigue" in attention:
            dimensions.add("fatigue")
        if toward == "inspect" and "stimulation" in attention:
            dimensions.add("stimulation")
        if candidate.params.get("from") == "hazard" and "integrity" in attention:
            dimensions.add("integrity")
        return frozenset(dimensions)

    @staticmethod
    def _prospective_recoverability_filter(
        *,
        candidates: list[Candidate],
        phys: Physiology,
        observations: list[dict[str, Any]],
        tick: int,
        attended_dimensions: frozenset[str],
        context: Mapping[str, Any] | None,
        effect_branches: Callable[[Candidate], tuple[dict[str, float], ...]] | None,
    ) -> tuple[list[Candidate], list[dict[str, Any]]]:
        """Constrain only supported positive-to-exhausted option loss."""
        if not attended_dimensions or context is None:
            return list(candidates), []
        kept: list[Candidate] = []
        events: list[dict[str, Any]] = []
        for candidate in candidates:
            branches = (
                effect_branches(candidate)
                if effect_branches is not None
                else verified_outcome_effect_branches(candidate.capability)
            )
            event = prospective_recoverability_transition(
                organism_tick=int(tick),
                body_schema_id=str(context.get("body_schema_id", "unknown")),
                physiology=phys.to_state(),
                attended_dimensions=tuple(attended_dimensions),
                observations=observations,
                candidate=candidate,
                authority_effect_branches=branches,
                capability_support=dict(context.get("capability_support") or {}),
                body_energy_cost_scale=float(
                    context.get("body_energy_cost_scale", 1.0)
                ),
                pending_commitment=bool(context.get("pending_commitment", False)),
            )
            events.append(event)
            if not event["constrained"]:
                kept.append(candidate)
        return kept, events

    @staticmethod
    def _no_safe_action() -> Candidate:
        return Candidate(
            "IDLE",
            {"source": "no_safe_action", "reason": "no_verified_branch_safe"},
        )

    @staticmethod
    def _energy_route_budget(
        phys: Physiology, observation: dict[str, Any]
    ) -> tuple[bool, int, float]:
        """Estimate a bounded resource route from policy-visible observations.

        The estimate uses the same visible charge-selection boundary and
        recovery approach step already used by arbitration. It intentionally
        excludes hidden habitat coordinates and evaluator-only affordance
        truth. The first approach is charged at its known verified effect;
        later approaches include one autonomous drift interval between actions.
        """
        distance = float(observation.get("estimated_distance", float("inf")))
        support = observation.get("distance_support_upper_bound")
        if support is not None and math.isfinite(float(support)):
            distance = max(distance, float(support))
        if not math.isfinite(distance):
            return True, 0, 0.0
        # Preserve the existing emergency progress path once criticality
        # already exists; reserve feasibility governs the non-critical descent
        # into the floor exposed by D-013S.
        if BOUNDS["energy"].critical_violation(phys.energy):
            return True, 0, 0.0
        approaches = max(
            0,
            int(
                math.ceil(
                    max(0.0, distance - CHARGE_SELECTION_DISTANCE)
                    / APPROACH_RECOVERY_STEP
                )
            ),
        )
        approach_cost = max(
            0.0, -float(OUTCOME_EFFECTS["APPROACH"].get("energy", 0.0))
        )
        drift_cost = max(0.0, -float(DEFAULT_DRIFT.get("energy", 0.0)))
        route_cost = approaches * approach_cost + max(0, approaches - 1) * drift_cost
        safe_reserve = phys.energy - BOUNDS["energy"].critical_low
        return safe_reserve >= route_cost, approaches, route_cost

    @classmethod
    def _ordinary_action_destroys_recovery_route(
        cls, phys: Physiology, observation: dict[str, Any], cand: Candidate
    ) -> bool:
        """Detect only a feasible-to-infeasible projected transition."""
        support = observation.get("distance_support_upper_bound")
        if support is None or not math.isfinite(float(support)):
            return False
        currently_feasible, _, _ = cls._energy_route_budget(phys, observation)
        if not currently_feasible:
            return False
        energy_delta = float(OUTCOME_EFFECTS.get(cand.capability, {}).get("energy", 0.0))
        projected_energy = phys.energy + float(DEFAULT_DRIFT.get("energy", 0.0)) + energy_delta
        projected = dict(observation)
        if cand.capability in ("MOVE", "APPROACH", "RETREAT"):
            projected["distance_support_upper_bound"] = (
                float(support) + max(0.0, float(cand.params.get("step", 1.0)))
            )
        projected_feasible, _, _ = cls._energy_route_budget_at_energy(
            projected_energy, projected
        )
        return not projected_feasible

    @staticmethod
    def _energy_route_budget_at_energy(
        energy: float, observation: dict[str, Any]
    ) -> tuple[bool, int, float]:
        distance = float(observation.get("estimated_distance", float("inf")))
        support = observation.get("distance_support_upper_bound")
        if support is not None and math.isfinite(float(support)):
            distance = max(distance, float(support))
        if not math.isfinite(distance):
            return True, 0, 0.0
        approaches = max(
            0, int(math.ceil(max(0.0, distance - CHARGE_SELECTION_DISTANCE) / APPROACH_RECOVERY_STEP))
        )
        approach_cost = max(0.0, -float(OUTCOME_EFFECTS["APPROACH"].get("energy", 0.0)))
        drift_cost = max(0.0, -float(DEFAULT_DRIFT.get("energy", 0.0)))
        route_cost = approaches * approach_cost + max(0, approaches - 1) * drift_cost
        return energy - BOUNDS["energy"].critical_low >= route_cost, approaches, route_cost

    def _preserve_recoverability(
        self, phys: Physiology, observations: list[dict[str, Any]], chosen: Candidate, tick: int
    ) -> Candidate:
        if chosen.capability in ("CHARGE", "APPROACH") and chosen.params.get("toward") == "resource":
            return chosen
        # When another need is approaching its recovery target, preserve an
        # existing energy landmark only if the nominal route plus the already
        # governed retry/drift allowance no longer fits in the existing
        # energy reserve. This keeps stochasticity inside a viable candidate
        # set without making energy universally dominant.
        if chosen.params.get("toward") == "rest":
            for observation in observations:
                if observation.get("kind") not in {"resource", "novel_crystal"}:
                    continue
                support = observation.get("distance_support_upper_bound")
                if support is None or not math.isfinite(float(support)):
                    continue
                _, _, route_cost = self._energy_route_budget(phys, observation)
                approach_cost = max(
                    0.0, -float(OUTCOME_EFFECTS["APPROACH"].get("energy", 0.0))
                )
                drift_cost = max(0.0, -float(DEFAULT_DRIFT.get("energy", 0.0)))
                retry_cost = self.state.max_retries * (approach_cost + drift_cost)
                reserve = phys.energy - BOUNDS["energy"].viable_low
                if reserve >= route_cost + retry_cost:
                    continue
                nominal_distance = float(observation.get("estimated_distance", float("inf")))
                if nominal_distance <= CHARGE_SELECTION_DISTANCE:
                    preserved = Candidate(
                        "CHARGE",
                        {
                            "toward": observation.get("kind", "resource"),
                            "source": "retry_aware_recovery_corridor",
                        },
                    )
                else:
                    preserved = Candidate(
                        "APPROACH",
                        {
                            "heading_delta": float(observation.get("relative_direction", 0.0)),
                            "step": APPROACH_RECOVERY_STEP,
                            "toward": observation.get("kind", "resource"),
                            "source": "retry_aware_recovery_corridor",
                        },
                    )
                return preserved
        for observation in observations:
            if observation.get("kind") != "resource":
                continue
            if not self._ordinary_action_destroys_recovery_route(phys, observation, chosen):
                continue
            preserved = Candidate(
                "APPROACH",
                {
                    "heading_delta": float(observation.get("relative_direction", 0.0)),
                    "step": 1.5,
                    "toward": "resource",
                    "source": "preserve_recoverability",
                    "distance_support_upper_bound": observation.get(
                        "distance_support_upper_bound"
                    ),
                },
            )
            return preserved
        return chosen

    def generate_candidates(
        self,
        phys: Physiology,
        observations: list[dict[str, Any]],
        tick: int,
    ) -> list[Candidate]:
        obs_by_kind = {o["kind"]: o for o in observations}
        cands: list[Candidate] = [
            Candidate("IDLE", {}),
            Candidate("ORIENT", {"heading": 0.0}),
        ]

        # Orient toward each observed feature
        for kind, o in obs_by_kind.items():
            heading = float(o["relative_direction"])  # relative — body-frame; runtime converts
            cands.append(Candidate("ORIENT", {"heading_delta": heading, "toward": kind}))
            if kind == "resource":
                cands.append(
                    Candidate(
                        "APPROACH",
                        {"heading_delta": heading, "step": 1.0, "toward": "resource"},
                    )
                )
                cands.append(Candidate("CHARGE", {"toward": "resource"}))
            elif kind == "rest":
                cands.append(
                    Candidate(
                        "APPROACH",
                        {"heading_delta": heading, "step": 1.0, "toward": "rest"},
                    )
                )
                cands.append(Candidate("REST", {"toward": "rest"}))
            elif kind == "inspect":
                cands.append(
                    Candidate(
                        "APPROACH",
                        {"heading_delta": heading, "step": 1.0, "toward": "inspect"},
                    )
                )
                cands.append(Candidate("INSPECT", {"toward": "inspect"}))
            elif kind == "hazard":
                cands.append(
                    Candidate(
                        "RETREAT",
                        {"heading_delta": heading, "step": 1.2, "from": "hazard"},
                    )
                )
            elif kind == "novel_crystal":
                cands.append(
                    Candidate(
                        "APPROACH",
                        {"heading_delta": heading, "step": 1.0, "toward": "novel_crystal"},
                    )
                )
                cands.append(Candidate("CHARGE", {"toward": "novel_crystal"}))

        cands.append(Candidate("MOVE", {"heading_delta": 0.0, "step": 1.0}))
        cands.append(Candidate("MOVE", {"heading_delta": 0.7, "step": 1.0}))
        cands.append(Candidate("MOVE", {"heading_delta": -0.7, "step": 1.0}))
        return cands

    def generate_manipulation_candidates(
        self,
        manipulation_bindings: list[dict[str, Any]],
        phys: Physiology,
        tick: int,
    ) -> list[ManipulationCandidate]:
        """Address-only MANIPULATE candidates from perception bindings."""
        _ = phys, tick
        cands: list[ManipulationCandidate] = []
        for binding in manipulation_bindings:
            affordances = binding.get("perceived_affordance_refs") or []
            for affordance_ref in affordances:
                params = dict(_AFFORDANCE_DEFAULT_PARAMS.get(affordance_ref, {"kind": "USE"}))
                cands.append(
                    ManipulationCandidate(
                        target_address_ref=str(binding["target_address_ref"]),
                        perception_evidence_ref=str(binding["perception_evidence_ref"]),
                        perception_state_version=int(binding["perception_state_version"]),
                        perceived_object_kind=str(binding["perceived_object_kind"]),
                        perceived_affordance_ref=str(affordance_ref),
                        parameters=params,
                        source="NEED_RELEVANCE",
                        supporting_evidence_refs=(str(binding["perception_evidence_ref"]),),
                    )
                )
        return cands

    def score_candidate(
        self,
        cand: Candidate,
        phys: Physiology,
        observations: list[dict[str, Any]],
        tick: int,
    ) -> Candidate:
        obs_by_kind = {o["kind"]: o for o in observations}
        urg = {n: 0.0 for n in BOUNDS} if self.state.hide_physiology else phys.vector_urgency()

        # expected_regulatory_gain
        gain = 0.0
        cap = cand.capability
        toward = cand.params.get("toward") or cand.params.get("from")
        if cap == "CHARGE":
            gain += urg["energy"] * 1.4 - phys.satiation_penalty("energy") * 1.2
        elif cap == "REST":
            gain += urg["fatigue"] * 1.4 - phys.satiation_penalty("fatigue") * 1.2
        elif cap == "INSPECT":
            gain += urg["stimulation"] * 1.2 - phys.satiation_penalty("stimulation") * 0.8
        elif cap == "MANIPULATE":
            kind = str(cand.params.get("perceived_object_kind", ""))
            if kind == "resource" or "resource" in str(
                cand.params.get("perceived_affordance_ref", "")
            ):
                gain += urg["energy"] * 1.6
            gain += urg["stimulation"] * 0.35
            if cand.params.get("source") == "PROCEDURAL_ROUTINE":
                gain += 0.15
        elif cap == "RETREAT":
            gain += urg["integrity"] * 1.5
        elif cap in ("APPROACH", "MOVE", "ORIENT"):
            if toward == "resource":
                gain += urg["energy"] * 0.7
            elif toward == "rest":
                gain += urg["fatigue"] * 0.7
            elif toward == "inspect":
                gain += urg["stimulation"] * 0.6
            elif toward == "hazard" or cand.params.get("from") == "hazard":
                gain += urg["integrity"] * 0.9
            else:
                # blind exploration scales with unmet needs
                gain += urg["stimulation"] * 0.15
                gain += urg["energy"] * 0.35
                gain += urg["fatigue"] * 0.25
                gain += urg["integrity"] * 0.15

        # Information-seeking is an endogenous affordance when no policy-safe
        # essential recovery route is known. It is bounded by the state budget
        # and remains subordinate to ordinary critical recovery above.
        if cand.params.get("source") == "essential_resource_discovery":
            gain += 0.55
        elif cand.params.get("source") == "active_reacquisition":
            gain += urg["energy"] * 0.8

        # option preservation — keep some energy / avoid hazard approaches
        option = 0.2
        if cap in ("MOVE", "APPROACH") and toward == "hazard":
            option -= 0.8
        if phys.energy < 0.25 and cap in ("MOVE", "APPROACH", "INSPECT"):
            option -= 0.3
        if phys.critical_any() and cap not in ("CHARGE", "REST", "RETREAT", "IDLE"):
            option -= 0.5

        # novelty / coverage
        novelty = 0.05
        if cap == "MOVE":
            novelty += 0.15
        if cap == "INSPECT":
            novelty += 0.25

        # uncertainty reduction
        unc_red = 0.0
        for o in observations:
            unc_red += float(o.get("uncertainty", 0)) * 0.05
        if cap == "INSPECT":
            unc_red += 0.2
        if cap == "ORIENT":
            unc_red += 0.05

        # effort / risk
        effort = {
            "IDLE": 0.0,
            "ORIENT": 0.05,
            "MOVE": 0.25,
            "APPROACH": 0.22,
            "RETREAT": 0.25,
            "INSPECT": 0.1,
            "REST": 0.05,
            "CHARGE": 0.08,
            "MANIPULATE": 0.3,
        }.get(cap, 0.2)
        risk = 0.0
        if toward == "hazard" and cap != "RETREAT":
            risk += 0.9
        if "hazard" in obs_by_kind and cap == "APPROACH" and toward != "hazard":
            # mild risk if navigating near hazard without retreat
            if float(obs_by_kind["hazard"].get("estimated_distance", 99)) < 3.0:
                risk += 0.25

        # commitment continuity
        continuity = 0.0
        if self.state.last_capability == cap:
            continuity = self.state.hysteresis + 0.05 * min(5, self.state.consecutive_same)
        elif self.state.last_capability is not None:
            # switching cost
            continuity = -0.08
            if tick - self.state.last_switch_tick < 3:
                continuity -= 0.15

        # retry penalty
        retries = self.state.retry_counts.get(cap, 0)
        if retries >= self.state.max_retries:
            gain -= 2.0

        scores = {
            "expected_regulatory_gain": gain,
            "expected_option_preservation": option,
            "novelty": novelty,
            "uncertainty_reduction": unc_red,
            "effort_cost": -effort,
            "risk_cost": -risk,
            "commitment_continuity": continuity,
        }
        cand.scores = scores
        cand.total = sum(scores.values())
        return cand

    def select(
        self,
        phys: Physiology,
        observations: list[dict[str, Any]],
        tick: int,
        rng: SeededRNG,
        individuality_apply: Any | None = None,
        *,
        context_scope: str = "default",
        phase_hint: float | None = None,
        manipulation_bindings: list[dict[str, Any]] | None = None,
        routine_proposals: list[dict[str, Any]] | None = None,
        policy_expectations: tuple[PolicyExpectationView, ...] | None = None,
        effective_age_ticks: int | None = None,
        effective_active_ticks: int | None = None,
        discovery_needed: bool = False,
        wait_journal: WaitJournal | None = None,
        wait_generation_enabled: bool = True,
        temporal_modifiers_enabled: bool = True,
        authority_effect_branches: Callable[
            [Candidate], tuple[dict[str, float], ...]
        ] | None = None,
        intent_candidates: list[Candidate] | None = None,
        candidate_allowed: Callable[[Candidate], bool] | None = None,
        prospective_recoverability_context: Mapping[str, Any] | None = None,
        prospective_recoverability_observer: Callable[[dict[str, Any]], None]
        | None = None,
    ) -> Candidate:
        # ``tick`` remains the orchestration clock for compatibility and for
        # explicitly orchestration-scoped modes.  Organism policy cadence must
        # use the authoritative active clock whenever temporal continuity is
        # enabled; direct callers without that context retain legacy behavior.
        orchestration_tick = tick
        active_tick = (
            effective_active_ticks
            if effective_active_ticks is not None
            else orchestration_tick
        )

        def introduces(candidate: Candidate, *, ignore: str | None = None) -> bool:
            if authority_effect_branches is None:
                return self._introduces_critical_boundary(
                    candidate, phys, ignore=ignore
                )
            branches = authority_effect_branches(candidate)
            return self._introduces_critical_boundary(
                candidate, phys, ignore=ignore, effect_branches=branches
            )

        def contract_admissible(candidate: Candidate) -> bool:
            branches = (
                authority_effect_branches(candidate)
                if authority_effect_branches is not None
                else None
            )
            return candidate_is_admissible(
                candidate,
                physiology=phys,
                observations=observations,
                arbitration_state=self.state,
                effect_branches=branches,
            )

        def candidate_allowed_here(candidate: Candidate) -> bool:
            return candidate_allowed is None or candidate_allowed(candidate)

        mode = self.state.mode
        if mode == "random":
            cap = rng.choice(list(CAPABILITIES))
            cand = Candidate(cap, {"step": 1.0, "heading_delta": rng.uniform(-1.0, 1.0)})
            if introduces(cand):
                cand = self._no_safe_action()
            self._commit(cand, active_tick)
            return cand
        if mode == "scripted":
            cap = SCRIPT_CYCLE[orchestration_tick % len(SCRIPT_CYCLE)]
            cand = Candidate(cap, {"step": 1.0, "heading_delta": 0.3})
            if introduces(cand):
                cand = self._no_safe_action()
            self._commit(cand, active_tick)
            return cand

        # recovery reflexes — disabled under physiology-hidden ablation (C3)
        needs = (
            []
            if self.state.hide_physiology
            else phys.active_recovery_needs()
        )
        diagnostic_only = (
            []
            if self.state.hide_physiology
            else [name for name in phys.needs_recovery() if name not in needs]
        )
        # Diagnostic attention is a cross-component urgency marker, never a recovery target.
        if diagnostic_only and not needs:
            self.state.recovery_focus = "diagnostic_only"
        critical = bool(needs or phys.critical_any()) and not self.state.hide_physiology
        if critical:
            crit = phys.critical_vars()
            # sticky recovery yields to energy need or a verified denial correction
            ORDER = ("energy", "fatigue", "integrity", "stimulation")
            pool = set(crit) if crit else set(needs)
            if self.state.recovery_focus and self.state.recovery_focus not in pool:
                self.state.recovery_focus = None
            if (
                self.state.recovery_focus
                and self.state.recovery_focus in pool
                and not (
                    self.state.recovery_focus != "energy"
                    and "energy" in pool
                )
            ):
                focus = self.state.recovery_focus
            else:
                focus = next((n for n in ORDER if n in pool), max(pool, key=phys.urgency))
                self.state.recovery_focus = focus
            kinds = {o["kind"] for o in observations}

            def pick_recovery(cands: list[Candidate]) -> Candidate:
                # ignore hysteresis for recovery — break orient thrash
                # individuality modifiers suppressed under critical physiology
                scored = []
                for c in cands:
                    sc = self.score_candidate(c, phys, observations, active_tick)
                    sc.total -= sc.scores.get("commitment_continuity", 0.0)
                    if c.capability == "MOVE":
                        sc.total += 0.5
                    if c.capability == "ORIENT":
                        sc.total -= 1.0
                    scored.append(sc)
                if individuality_apply is not None:
                    individuality_apply(
                        scored,
                        context_scope=context_scope,
                        critical_physiology=True,
                        tick=active_tick,
                        phase_hint=phase_hint,
                    )
                scored.sort(key=lambda c: c.total, reverse=True)
                return scored[0]

            def commit_safe_recovery(chosen: Candidate) -> Candidate:
                """Adjudicate and commit one recovery action exactly once."""
                def focus_exemption(candidate: Candidate) -> str | None:
                    energy_effect = float(
                        OUTCOME_EFFECTS.get(candidate.capability, {}).get("energy", 0.0)
                    )
                    return (
                        None
                        if focus == "energy" and energy_effect < 0.0
                        else focus
                    )

                def immediately_safe(candidate: Candidate) -> bool:
                    return not introduces(candidate, ignore=focus_exemption(candidate))

                # Optional higher-level intents never gate urgent recovery.
                # Recovery remains on its established authority path.
                if not immediately_safe(chosen):
                    alternatives = [
                        candidate
                        for candidate in self.generate_candidates(
                            phys, observations, orchestration_tick
                        )
                        if candidate_allowed_here(candidate)
                        and immediately_safe(candidate)
                        and contract_admissible(candidate)
                    ]
                    chosen = (
                        pick_recovery(alternatives)
                        if alternatives
                        else self._no_safe_action()
                    )

                preserved = self._preserve_recoverability(
                    phys, observations, chosen, active_tick
                )
                if preserved is not chosen and immediately_safe(preserved):
                    if contract_admissible(preserved):
                        chosen = preserved
                    else:
                        alternatives = [
                            candidate
                            for candidate in self.generate_candidates(
                                phys, observations, orchestration_tick
                            )
                            if candidate_allowed_here(candidate)
                            and immediately_safe(candidate)
                            and contract_admissible(candidate)
                        ]
                        chosen = (
                            pick_recovery(alternatives)
                            if alternatives
                            else self._no_safe_action()
                        )

                if not immediately_safe(chosen):
                    alternatives = [
                        candidate
                        for candidate in self.generate_candidates(
                            phys, observations, orchestration_tick
                        )
                        if candidate_allowed_here(candidate)
                        and immediately_safe(candidate)
                        and contract_admissible(candidate)
                    ]
                    chosen = (
                        pick_recovery(alternatives)
                        if alternatives
                        else self._no_safe_action()
                    )

                self._commit(chosen, active_tick)
                return chosen


            if focus == "energy":
                current = [
                    o
                    for o in observations
                    if o.get("kind") in {"resource", "novel_crystal"}
                    and o.get("fact_kind") != "REMEMBERED_ESTIMATE"
                    and o.get("source") != "world_model_memory"
                ]
                remembered = [
                    o
                    for o in observations
                    if o.get("kind") in {"resource", "novel_crystal"}
                    and (
                        o.get("fact_kind") == "REMEMBERED_ESTIMATE"
                        or o.get("source") == "world_model_memory"
                    )
                ]
                if current:
                    self.state.reacquisition_streak = 0
                    kind = str(current[0]["kind"])
                    o = current[0]
                    hd = float(o["relative_direction"])
                    nominal_dist = float(o["estimated_distance"])
                    support = o.get("distance_support_upper_bound")
                    dist = max(
                        nominal_dist,
                        float(support)
                        if support is not None and math.isfinite(float(support))
                        else nominal_dist,
                    )
                    denial = self.state.last_verified_denial or {}
                    denial_target = denial.get("target_kind")
                    repeated_denial = (
                        denial.get("capability") == "CHARGE"
                        and denial.get("reason") in RECOVERY_DENIAL_REASONS
                        and (not denial_target or denial_target == kind)
                    )
                    if nominal_dist <= CHARGE_SELECTION_DISTANCE and not repeated_denial:
                        chosen = Candidate("CHARGE", {"toward": kind})
                        return commit_safe_recovery(chosen)
                    route_feasible, required_approaches, route_cost = (
                        self._energy_route_budget(phys, o)
                    )
                    if not route_feasible:
                        chosen = Candidate(
                            "SIGNAL_ASSISTANCE",
                            {
                                "toward": kind,
                                "reason": "energy_recovery_route_infeasible",
                                "estimated_distance": nominal_dist,
                                "distance_support_upper_bound": support,
                                "required_approach_count": required_approaches,
                                "estimated_route_energy_cost": route_cost,
                            },
                        )
                        return commit_safe_recovery(chosen)
                    chosen = Candidate(
                        "APPROACH",
                        {
                            "heading_delta": hd,
                            "step": 1.5,
                            "toward": kind,
                            "source": "preserve_recoverability"
                            if support is not None
                            else "energy_recovery",
                            "distance_support_upper_bound": support,
                        },
                    )
                    return commit_safe_recovery(chosen)
                if remembered:
                    cue = remembered[0]
                    if self.state.reacquisition_streak < 8:
                        # Exploit corrected body-relative belief before widening search.
                        self.state.reacquisition_streak += 1
                        nominal_dist = float(cue.get("estimated_distance", 1.5))
                        step = min(1.5, max(0.5, nominal_dist))
                        chosen = Candidate(
                            "APPROACH",
                            {
                                "heading_delta": float(cue.get("relative_direction", 0.0)),
                                "step": step,
                                "toward": "resource",
                                "source": "active_reacquisition",
                                "strategy": "direct_homing",
                                "fact_kind": "REMEMBERED_ESTIMATE",
                            },
                        )
                        return commit_safe_recovery(chosen)
                    self.state.reacquisition_streak = 0
                # Widen only after bounded belief exploitation fails.
                if active_tick % 9 == 0:
                    self.state.search_heading += 0.9
                chosen = Candidate(
                    "MOVE",
                    {
                        "heading": self.state.search_heading,
                        "step": 1.5,
                        "source": "bounded_fallback_search",
                    },
                )
                return commit_safe_recovery(chosen)
            if focus == "fatigue":
                if "rest" in kinds:
                    o = next(o for o in observations if o["kind"] == "rest")
                    hd = float(o["relative_direction"])
                    dist = float(o["estimated_distance"])
                    if dist <= 2.2:
                        chosen = Candidate("REST", {"toward": "rest"})
                        return commit_safe_recovery(chosen)
                    chosen = Candidate(
                        "APPROACH",
                        {"heading_delta": hd, "step": 1.4, "toward": "rest"},
                    )
                    return commit_safe_recovery(chosen)
                if active_tick % 9 == 0:
                    self.state.search_heading += 0.9
                chosen = Candidate(
                    "MOVE",
                    {"heading": self.state.search_heading, "step": 1.3},
                )
                return commit_safe_recovery(chosen)
            if focus == "integrity":
                # rest repairs integrity; retreat from hazard first
                if "hazard" in kinds:
                    o = next(o for o in observations if o["kind"] == "hazard")
                    if float(o["estimated_distance"]) < 4.0:
                        chosen = Candidate(
                            "RETREAT",
                            {
                                "heading_delta": float(o["relative_direction"]),
                                "step": 1.8,
                                "from": "hazard",
                            },
                        )
                        return commit_safe_recovery(chosen)
                if "rest" in kinds:
                    o = next(o for o in observations if o["kind"] == "rest")
                    hd = float(o["relative_direction"])
                    if float(o["estimated_distance"]) <= 2.2:
                        chosen = Candidate("REST", {"toward": "rest"})
                        return commit_safe_recovery(chosen)
                    chosen = Candidate(
                        "APPROACH",
                        {"heading_delta": hd, "step": 1.4, "toward": "rest"},
                    )
                    return commit_safe_recovery(chosen)
                if active_tick % 4 == 0:
                    chosen = Candidate("IDLE", {})
                    return commit_safe_recovery(chosen)
                if active_tick % 9 == 0:
                    self.state.search_heading += 0.9
                chosen = Candidate(
                    "MOVE",
                    {"heading": self.state.search_heading, "step": 1.4},
                )
                return commit_safe_recovery(chosen)
            if focus == "stimulation":
                # overshoot: calm down via REST/IDLE rather than more inspect/move
                if phys.stimulation > BOUNDS["stimulation"].viable_high:
                    if "rest" in kinds:
                        o = next(o for o in observations if o["kind"] == "rest")
                        if float(o["estimated_distance"]) <= 2.2:
                            chosen = Candidate("REST", {"toward": "rest"})
                            return commit_safe_recovery(chosen)
                        chosen = Candidate(
                            "APPROACH",
                            {
                                "heading_delta": float(o["relative_direction"]),
                                "step": 1.2,
                                "toward": "rest",
                            },
                        )
                        return commit_safe_recovery(chosen)
                    chosen = Candidate("IDLE", {})
                    return commit_safe_recovery(chosen)
                if "inspect" in kinds:
                    o = next(o for o in observations if o["kind"] == "inspect")
                    hd = float(o["relative_direction"])
                    if float(o["estimated_distance"]) <= 2.2:
                        chosen = Candidate("INSPECT", {"toward": "inspect"})
                        return commit_safe_recovery(chosen)
                    chosen = Candidate(
                        "APPROACH",
                        {"heading_delta": hd, "step": 1.3, "toward": "inspect"},
                    )
                    return commit_safe_recovery(chosen)
                if active_tick % 9 == 0:
                    self.state.search_heading += 0.9
                chosen = Candidate(
                    "MOVE",
                    {"heading": self.state.search_heading, "step": 1.3},
                )
                return commit_safe_recovery(chosen)

        base_cands = [
            candidate
            for candidate in self.generate_candidates(phys, observations, orchestration_tick)
            if candidate_allowed_here(candidate)
        ]
        if discovery_needed and not any(
            o.get("kind") in {"resource", "novel_crystal"} for o in observations
        ):
            if (
                self.state.discovery_actions_remaining <= 0
                and active_tick >= self.state.discovery_cooldown_until
            ):
                self.state.discovery_actions_remaining = 12
            if self.state.discovery_actions_remaining > 0:
                base_cands.append(
                    Candidate(
                        "MOVE",
                        {
                            "heading_delta": 0.25,
                            "step": 1.2,
                            "source": "essential_resource_discovery",
                        },
                    )
                )
        if manipulation_bindings:
            for mc in self.generate_manipulation_candidates(
                manipulation_bindings, phys, orchestration_tick
            ):
                base_cands.append(mc.to_candidate())
        if routine_proposals:
            for proposal in routine_proposals:
                base_cands.append(
                    Candidate(
                        "MANIPULATE",
                        {
                            **dict(proposal),
                            "source": proposal.get("source", "PROCEDURAL_ROUTINE"),
                        },
                    )
                )
        if diagnostic_only and not needs:
            safe = [
                candidate
                for candidate in base_cands
                if not self._worsens_diagnostic_overshoot(
                    candidate, phys, diagnostic_only
                )
            ]
            if safe:
                non_idle = [
                    candidate for candidate in safe
                    if candidate.capability not in {"IDLE", "ORIENT"}
                ]
                base_cands = non_idle or safe
        age_ticks = (
            effective_age_ticks
            if effective_age_ticks is not None
            else orchestration_tick
        )
        if policy_expectations and wait_generation_enabled:
            base_cands.extend(
                propose_wait_candidates(
                    policy_expectations,
                    effective_age_ticks=age_ticks,
                    wait_journal=wait_journal,
                )
            )
        preventive_dimensions = self._preventive_attention_dimensions(phys)
        intent_mode = False
        preventive_only_mode = False
        if intent_candidates:
            admissible_intents = []
            for candidate in self._canonical_intent_candidates(intent_candidates):
                if (
                    candidate_allowed_here(candidate)
                    and not introduces(candidate)
                    and contract_admissible(candidate)
                ):
                    admissible_intents.append(candidate)
            if admissible_intents:
                if preventive_dimensions:
                    regulatory_base = [
                        candidate
                        for candidate in base_cands
                        if (
                            candidate_allowed_here(candidate)
                            and not introduces(candidate)
                            and contract_admissible(candidate)
                            and self._candidate_regulatory_dimensions(
                                candidate, phys
                            ).intersection(preventive_dimensions)
                        )
                    ]
                    cands = self._canonical_intent_candidates(
                        [*admissible_intents, *regulatory_base]
                    )
                else:
                    cands = admissible_intents
                intent_mode = True
            else:
                # Optional intent failure must not manufacture NO_SAFE_ACTION.
                cands = base_cands
        else:
            if preventive_dimensions:
                regulatory_base = [
                    candidate
                    for candidate in base_cands
                    if (
                        candidate_allowed_here(candidate)
                        and not introduces(candidate)
                        and contract_admissible(candidate)
                        and self._candidate_regulatory_dimensions(
                            candidate, phys
                        ).intersection(preventive_dimensions)
                    )
                ]
                if regulatory_base:
                    cands = regulatory_base
                    preventive_only_mode = True
                else:
                    # Preventive attention must not manufacture NO_SAFE_ACTION.
                    cands = base_cands
            else:
                cands = base_cands

        # CLOSE-02X is a pre-crisis candidate constraint only.  It consumes
        # the already-composed CLOSE-02T pool and cannot create, rank, or
        # execute an action.  UNKNOWN and already-exhausted states remain.
        cands, prospective_events = self._prospective_recoverability_filter(
            candidates=cands,
            phys=phys,
            observations=observations,
            tick=active_tick,
            attended_dimensions=preventive_dimensions,
            context=prospective_recoverability_context,
            effect_branches=authority_effect_branches,
        )
        if prospective_recoverability_observer is not None:
            for event in prospective_events:
                prospective_recoverability_observer(event)
        if not cands:
            chosen = self._no_safe_action()
            self._commit(chosen, active_tick)
            return chosen

        scored = [self.score_candidate(c, phys, observations, active_tick) for c in cands]
        if policy_expectations and temporal_modifiers_enabled:
            apply_temporal_modifiers(
                scored,
                policy_expectations,
                effective_age_ticks=age_ticks,
                fallback_biases=(
                    active_fallback_biases(wait_journal, effective_age_ticks=age_ticks)
                    if wait_journal is not None
                    else ()
                ),
            )
        if individuality_apply is not None:
            individuality_apply(
                scored,
                context_scope=context_scope,
                critical_physiology=False,
                tick=active_tick,
                phase_hint=phase_hint,
            )
        # bounded stochasticity: softmax-ish via noisy argmax
        for c in scored:
            c.total += rng.gauss(0.0, 0.08)
        scored.sort(key=lambda c: c.total, reverse=True)
        chosen = scored[0]

        # anti-thrash: if switching every tick among top, stick
        if (
            self.state.last_capability
            and chosen.capability != self.state.last_capability
            and active_tick - self.state.last_switch_tick <= 1
            and self.state.consecutive_same < 2
        ):
            # prefer continuing previous if within hysteresis band
            prev = next((c for c in scored if c.capability == self.state.last_capability), None)
            if prev and (chosen.total - prev.total) < self.state.hysteresis:
                self.state.thrash_events += 1
                chosen = prev

        if intent_mode:
            # Valid intent selection is the final low-level choice. Existing
            # safety and contract checks only narrow the admissible set; they
            # do not replace the selected candidate after arbitration.
            if (
                not candidate_allowed_here(chosen)
                or introduces(chosen)
                or not contract_admissible(chosen)
            ):
                safe_scored = [
                    candidate
                    for candidate in scored
                    if candidate_allowed_here(candidate)
                    and not introduces(candidate)
                    and contract_admissible(candidate)
                ]
                chosen = safe_scored[0] if safe_scored else self._no_safe_action()
        elif preventive_only_mode:
            # Keep State 4 restricted to existing regulatory base actions.
            if (
                not candidate_allowed_here(chosen)
                or introduces(chosen)
                or not contract_admissible(chosen)
            ):
                safe_scored = [
                    candidate
                    for candidate in scored
                    if candidate_allowed_here(candidate)
                    and not introduces(candidate)
                    and contract_admissible(candidate)
                ]
                chosen = safe_scored[0] if safe_scored else self._no_safe_action()
        else:
            # No active valid intent retains the established base semantics.
            preserved = self._preserve_recoverability(
                phys, observations, chosen, active_tick
            )
            if introduces(preserved) or not contract_admissible(preserved):
                safe_scored = [
                    candidate
                    for candidate in scored
                    if candidate_allowed_here(candidate)
                    and not introduces(candidate)
                    and contract_admissible(candidate)
                ]
                preserved = safe_scored[0] if safe_scored else self._no_safe_action()
            chosen = preserved
        self._commit(chosen, active_tick)
        return chosen

    def _commit(self, cand: Candidate, tick: int) -> None:
        if cand.params.get("source") == "no_safe_action":
            return
        source = cand.params.get("source")
        if source == "essential_resource_discovery" and self.state.discovery_actions_remaining > 0:
            self.state.discovery_actions_remaining -= 1
            if self.state.discovery_actions_remaining == 0:
                self.state.discovery_cooldown_until = tick + 48
        if source == "active_reacquisition":
            self.state.discovery_actions_remaining = 0
        if cand.capability != self.state.last_capability:
            if self.state.last_capability is not None and tick - self.state.last_switch_tick <= 2:
                self.state.thrash_events += 1
            self.state.last_capability = cand.capability
            self.state.last_switch_tick = tick
            self.state.consecutive_same = 1
        else:
            self.state.consecutive_same += 1
        self.state.action_counts[cand.capability] = self.state.action_counts.get(cand.capability, 0) + 1

    @staticmethod
    def _worsens_diagnostic_overshoot(
        cand: Candidate, phys: Physiology, diagnostic_only: list[str]
    ) -> bool:
        effects = OUTCOME_EFFECTS.get(cand.capability, {})
        for name in diagnostic_only:
            value = phys.get(name)
            bounds = BOUNDS[name]
            delta = float(effects.get(name, 0.0))
            if value > bounds.viable_high and delta > 0.0:
                return True
            if value < bounds.viable_low and delta < 0.0:
                return True
        return False

    def note_outcome(
        self,
        capability: str,
        success: bool,
        reason: str | None = None,
        *,
        target_kind: str | None = None,
    ) -> None:
        if success:
            self.state.retry_counts[capability] = 0
            self.state.last_verified_denial = None
        else:
            self.state.retry_counts[capability] = self.state.retry_counts.get(capability, 0) + 1
            if reason in RECOVERY_DENIAL_REASONS:
                self.state.last_verified_denial = {
                    "capability": capability,
                    "reason": str(reason),
                    **({"target_kind": target_kind} if target_kind else {}),
                }
