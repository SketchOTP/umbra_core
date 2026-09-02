"""Verified, opportunity-bound route experience for the WorldModel.

This module records observed route episodes only. It deliberately contains no
ranking, utility, probability, planning, or action-selection semantics.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from umbra_core.util import BoundedRing


ROUTE_EVIDENCE_SCHEMA_V1 = "VERIFIED_ROUTE_EXPERIENCE_V1"
ROUTE_EVIDENCE_SCHEMA = "VERIFIED_ROUTE_EXPERIENCE_V2"
ROUTE_EVIDENCE_SEMANTICS = "VERIFIED_OBSERVED_SUPPORT"
DEFAULT_ROUTE_EVIDENCE_CAPACITY = 128
ROUTE_CAPABILITY = "APPROACH"
ROUTE_CONTROL_CAPABILITIES = frozenset(("APPROACH", "ORIENT"))
TERMINAL_CAPABILITIES = frozenset(("CHARGE", "REST", "INSPECT"))
TERMINAL_BY_KIND = {
    "resource": "CHARGE",
    "novel_crystal": "CHARGE",
    "rest": "REST",
    "inspect": "INSPECT",
}
ELIGIBLE_FACT_KINDS = frozenset(("CURRENT_OBSERVATION", "REMEMBERED_ESTIMATE"))
ROUTE_FAILURE_CODES = frozenset(
    ("route_blocked", "movement_slip", "adapter_rejection", "adapter_rejected")
)


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


@dataclass(frozen=True)
class OpportunityResolution:
    status: str
    opportunity_entity_id: str | None
    candidate_entity_ids: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifiedRouteControlStep:
    """One executed, verified action in an opportunity-bound route episode."""

    capability: str
    issue_tick: int
    completion_tick: int
    completion_lag: int
    translational_movement: bool
    success: bool
    verified_outcome_ref: str | None

    def __post_init__(self) -> None:
        if self.capability not in ROUTE_CONTROL_CAPABILITIES | TERMINAL_CAPABILITIES:
            raise ValueError("route_control_step_capability")
        if self.issue_tick < 0 or self.completion_tick < self.issue_tick:
            raise ValueError("route_control_step_tick_range")
        if self.completion_lag != self.completion_tick - self.issue_tick:
            raise ValueError("route_control_step_lag")
        if self.completion_lag < 0:
            raise ValueError("route_control_step_negative_lag")
        if self.capability == ROUTE_CAPABILITY and not self.translational_movement:
            raise ValueError("route_control_step_approach_translation")
        if self.capability != ROUTE_CAPABILITY and self.translational_movement:
            raise ValueError("route_control_step_nonapproach_translation")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> VerifiedRouteControlStep:
        return cls(
            capability=str(value["capability"]),
            issue_tick=int(value["issue_tick"]),
            completion_tick=int(value["completion_tick"]),
            completion_lag=int(value["completion_lag"]),
            translational_movement=bool(value.get("translational_movement", False)),
            success=bool(value.get("success", False)),
            verified_outcome_ref=(
                str(value["verified_outcome_ref"])
                if value.get("verified_outcome_ref")
                else None
            ),
        )


def resolve_opportunity(
    entities: Mapping[str, Any],
    *,
    target_kind: str | None,
    body_schema_id: str | None,
) -> OpportunityResolution:
    """Resolve exactly one policy-safe entity without preference or ordering."""

    if not target_kind:
        return OpportunityResolution("UNAVAILABLE", None, reason="target_kind_missing")
    if not body_schema_id:
        return OpportunityResolution("UNAVAILABLE", None, reason="body_schema_missing")
    matches: list[str] = []
    for key, entity in entities.items():
        entity_id = str(_value(entity, "entity_id", key) or "")
        if not entity_id or str(_value(entity, "entity_kind", "")) != str(target_kind):
            continue
        if str(_value(entity, "fact_kind", "UNKNOWN")) not in ELIGIBLE_FACT_KINDS:
            continue
        support_schema = _value(entity, "support_body_schema_id")
        if support_schema is not None and str(support_schema) != str(body_schema_id):
            continue
        matches.append(entity_id)
    unique = tuple(dict.fromkeys(matches))
    if len(unique) == 1:
        return OpportunityResolution("EXACT", unique[0], unique)
    if len(unique) > 1:
        return OpportunityResolution("AMBIGUOUS", None, unique, reason="multiple_matching_entities")
    return OpportunityResolution("UNAVAILABLE", None, reason="no_matching_policy_safe_entity")


@dataclass(frozen=True)
class VerifiedRouteExperience:
    evidence_id: str
    opportunity_entity_id: str
    opportunity_entity_kind: str
    body_schema_id: str
    route_capability: str
    terminal_capability: str
    start_tick: int
    final_tick: int
    start_distance_support_upper_bound: float | None
    start_fact_kind: str
    start_support_provenance: str | None
    verified_movement_execution_count: int
    movement_completion_lags: tuple[int, ...]
    terminal_completion_lag: int | None
    terminal_result: bool
    route_failure_code: str | None
    execution_outcome_refs: tuple[str, ...]
    evidence_semantics: str = ROUTE_EVIDENCE_SEMANTICS
    route_control_steps: tuple[VerifiedRouteControlStep, ...] = ()
    schema: str = ROUTE_EVIDENCE_SCHEMA

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.opportunity_entity_id or not self.body_schema_id:
            raise ValueError("route_experience_identity_required")
        if self.route_capability != ROUTE_CAPABILITY:
            raise ValueError("route_experience_route_capability")
        if self.terminal_capability not in TERMINAL_CAPABILITIES:
            raise ValueError("route_experience_terminal_capability")
        if self.start_tick < 0 or self.final_tick < self.start_tick:
            raise ValueError("route_experience_tick_range")
        if self.verified_movement_execution_count != len(self.movement_completion_lags):
            raise ValueError("route_experience_movement_count_mismatch")
        if any(int(lag) < 0 for lag in self.movement_completion_lags):
            raise ValueError("route_experience_movement_lag")
        if self.terminal_completion_lag is not None and self.terminal_completion_lag < 0:
            raise ValueError("route_experience_terminal_lag")
        if self.start_distance_support_upper_bound is not None and (
            not math.isfinite(float(self.start_distance_support_upper_bound))
            or float(self.start_distance_support_upper_bound) < 0.0
        ):
            raise ValueError("route_experience_distance_support")
        if self.evidence_semantics != ROUTE_EVIDENCE_SEMANTICS:
            raise ValueError("route_experience_semantics")
        if self.schema not in {ROUTE_EVIDENCE_SCHEMA_V1, ROUTE_EVIDENCE_SCHEMA}:
            raise ValueError("route_experience_schema")
        if self.schema == ROUTE_EVIDENCE_SCHEMA_V1 and self.route_control_steps:
            raise ValueError("v1_route_control_steps_not_representable")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["movement_completion_lags"] = list(self.movement_completion_lags)
        result["execution_outcome_refs"] = list(self.execution_outcome_refs)
        result["route_control_steps"] = [step.to_dict() for step in self.route_control_steps]
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> VerifiedRouteExperience:
        raw_steps = value.get("route_control_steps")
        steps = tuple(
            VerifiedRouteControlStep.from_dict(item)
            for item in (raw_steps or [])
        )
        schema = str(
            value.get(
                "schema",
                ROUTE_EVIDENCE_SCHEMA if raw_steps is not None else ROUTE_EVIDENCE_SCHEMA_V1,
            )
        )
        return cls(
            evidence_id=str(value["evidence_id"]),
            opportunity_entity_id=str(value["opportunity_entity_id"]),
            opportunity_entity_kind=str(value["opportunity_entity_kind"]),
            body_schema_id=str(value["body_schema_id"]),
            route_capability=str(value.get("route_capability", ROUTE_CAPABILITY)),
            terminal_capability=str(value["terminal_capability"]),
            start_tick=int(value["start_tick"]),
            final_tick=int(value["final_tick"]),
            start_distance_support_upper_bound=(
                float(value["start_distance_support_upper_bound"])
                if value.get("start_distance_support_upper_bound") is not None
                else None
            ),
            start_fact_kind=str(value.get("start_fact_kind", "UNKNOWN")),
            start_support_provenance=(
                str(value["start_support_provenance"])
                if value.get("start_support_provenance")
                else None
            ),
            verified_movement_execution_count=int(
                value.get("verified_movement_execution_count", 0)
            ),
            movement_completion_lags=tuple(
                int(v) for v in value.get("movement_completion_lags", [])
            ),
            terminal_completion_lag=(
                int(value["terminal_completion_lag"])
                if value.get("terminal_completion_lag") is not None
                else None
            ),
            terminal_result=bool(value.get("terminal_result", False)),
            route_failure_code=(
                str(value["route_failure_code"])
                if value.get("route_failure_code")
                else None
            ),
            execution_outcome_refs=tuple(
                str(v) for v in value.get("execution_outcome_refs", [])
            ),
            evidence_semantics=str(
                value.get("evidence_semantics", ROUTE_EVIDENCE_SEMANTICS)
            ),
            route_control_steps=steps,
            schema=schema,
        )


@dataclass
class _RouteEpisode:
    opportunity_entity_id: str
    opportunity_entity_kind: str
    body_schema_id: str
    route_capability: str
    terminal_capability: str
    start_tick: int
    start_distance_support_upper_bound: float | None
    start_fact_kind: str
    start_support_provenance: str | None
    movement_completion_lags: list[int] = field(default_factory=list)
    terminal_completion_lag: int | None = None
    terminal_result: bool = False
    route_failure_code: str | None = None
    final_tick: int | None = None
    execution_outcome_refs: list[str] = field(default_factory=list)
    route_control_steps: list[VerifiedRouteControlStep] = field(default_factory=list)

    @property
    def movement_count(self) -> int:
        return len(self.movement_completion_lags)

    def close(self, *, tick: int, outcome_ref: str | None = None) -> None:
        self.final_tick = int(tick)
        if outcome_ref:
            self.execution_outcome_refs.append(str(outcome_ref))

    def to_experience(self, *, evidence_id: str) -> VerifiedRouteExperience:
        if self.final_tick is None:
            raise ValueError("route_episode_not_closed")
        return VerifiedRouteExperience(
            evidence_id=evidence_id,
            opportunity_entity_id=self.opportunity_entity_id,
            opportunity_entity_kind=self.opportunity_entity_kind,
            body_schema_id=self.body_schema_id,
            route_capability=self.route_capability,
            terminal_capability=self.terminal_capability,
            start_tick=self.start_tick,
            final_tick=self.final_tick,
            start_distance_support_upper_bound=self.start_distance_support_upper_bound,
            start_fact_kind=self.start_fact_kind,
            start_support_provenance=self.start_support_provenance,
            verified_movement_execution_count=self.movement_count,
            movement_completion_lags=tuple(self.movement_completion_lags),
            terminal_completion_lag=self.terminal_completion_lag,
            terminal_result=self.terminal_result,
            route_failure_code=self.route_failure_code,
            execution_outcome_refs=tuple(self.execution_outcome_refs),
            route_control_steps=tuple(self.route_control_steps),
        )


@dataclass
class RouteEvidenceStore:
    """Bounded completed evidence plus one ephemeral in-progress episode."""

    capacity: int = DEFAULT_ROUTE_EVIDENCE_CAPACITY
    experiences: BoundedRing[VerifiedRouteExperience] = field(init=False)
    _episode: _RouteEpisode | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if int(self.capacity) < 1:
            raise ValueError("route_evidence_capacity")
        self.capacity = int(self.capacity)
        self.experiences = BoundedRing(self.capacity)

    def _discard(self, reason: str) -> dict[str, Any]:
        self._episode = None
        return {"adapted": False, "discarded": True, "reason": reason}

    def bind_for_issue(
        self,
        *,
        entities: Mapping[str, Any],
        capability: str,
        target_kind: str | None,
        body_schema_id: str | None,
    ) -> dict[str, Any] | None:
        if capability not in ("ORIENT", ROUTE_CAPABILITY, *TERMINAL_CAPABILITIES):
            return None
        resolution = resolve_opportunity(
            entities, target_kind=target_kind, body_schema_id=body_schema_id
        )
        if resolution.status != "EXACT":
            return None
        entity = entities[resolution.opportunity_entity_id]
        return {
            "status": "EXACT",
            "opportunity_entity_id": resolution.opportunity_entity_id,
            "opportunity_entity_kind": str(_value(entity, "entity_kind")),
            "body_schema_id": str(body_schema_id),
            "start_distance_support_upper_bound": _value(
                entity, "distance_support_upper_bound"
            ),
            "start_fact_kind": str(_value(entity, "fact_kind", "UNKNOWN")),
            "start_support_provenance": _value(entity, "support_provenance"),
        }

    def _start(self, binding: Mapping[str, Any], *, tick: int, terminal: str) -> None:
        self._episode = _RouteEpisode(
            opportunity_entity_id=str(binding["opportunity_entity_id"]),
            opportunity_entity_kind=str(binding["opportunity_entity_kind"]),
            body_schema_id=str(binding["body_schema_id"]),
            route_capability=ROUTE_CAPABILITY,
            terminal_capability=terminal,
            start_tick=int(tick),
            start_distance_support_upper_bound=(
                float(binding["start_distance_support_upper_bound"])
                if binding.get("start_distance_support_upper_bound") is not None
                else None
            ),
            start_fact_kind=str(binding.get("start_fact_kind", "UNKNOWN")),
            start_support_provenance=(
                str(binding["start_support_provenance"])
                if binding.get("start_support_provenance")
                else None
            ),
        )

    def _append_closed(self, *, success: bool, tick: int, outcome_ref: str | None) -> dict[str, Any]:
        if self._episode is None:
            return {"adapted": False, "reason": "no_episode"}
        self._episode.terminal_result = bool(success)
        self._episode.close(tick=tick, outcome_ref=outcome_ref)
        experience = self._episode.to_experience(evidence_id=f"route-experience:{outcome_ref or tick}")
        self.experiences.append(experience)
        self._episode = None
        return {"adapted": True, "experience": experience.to_dict()}

    def _record_control_step(
        self,
        *,
        capability: str,
        success: bool,
        tick: int,
        issue_tick: int | None,
        outcome_ref: str | None,
    ) -> int:
        if self._episode is None:
            raise ValueError("route_episode_required")
        issued = int(issue_tick if issue_tick is not None else tick)
        lag = max(0, int(tick) - issued)
        self._episode.route_control_steps.append(
            VerifiedRouteControlStep(
                capability=str(capability),
                issue_tick=issued,
                completion_tick=int(tick),
                completion_lag=lag,
                translational_movement=capability == ROUTE_CAPABILITY,
                success=bool(success),
                verified_outcome_ref=str(outcome_ref) if outcome_ref else None,
            )
        )
        return lag

    def record_verified_outcome(
        self,
        *,
        binding: Mapping[str, Any] | None,
        capability: str,
        success: bool,
        reason: str,
        verified: bool,
        tick: int,
        issue_tick: int | None,
        body_schema_id: str | None,
        outcome_ref: str | None,
    ) -> dict[str, Any]:
        if not binding or binding.get("status") != "EXACT":
            if self._episode is not None:
                return self._discard("missing_exact_binding")
            return {"adapted": False, "reason": "missing_exact_binding"}
        if not verified or not body_schema_id:
            return self._discard("unverified_or_missing_body_schema")
        if str(binding.get("body_schema_id")) != str(body_schema_id):
            return self._discard("body_schema_changed")

        target_id = str(binding.get("opportunity_entity_id"))
        target_kind = str(binding.get("opportunity_entity_kind"))
        terminal = TERMINAL_BY_KIND.get(target_kind)
        if terminal is None:
            return {"adapted": False, "reason": "unsupported_terminal_kind"}

        same_episode = self._episode is not None and (
            self._episode.opportunity_entity_id == target_id
            and self._episode.body_schema_id == str(body_schema_id)
        )
        if self._episode is not None and not same_episode:
            prior_schema = self._episode.body_schema_id
            self._discard(
                "body_schema_changed"
                if prior_schema != str(body_schema_id)
                else "route_switch"
            )
            if prior_schema != str(body_schema_id):
                return {"adapted": False, "discarded": True, "reason": "body_schema_changed"}

        if capability == ROUTE_CAPABILITY:
            if self._episode is None:
                self._start(binding, tick=tick, terminal=terminal)
            lag = self._record_control_step(
                capability=capability,
                success=success,
                tick=tick,
                issue_tick=issue_tick,
                outcome_ref=outcome_ref,
            )
            if not success:
                failure = reason if reason in ROUTE_FAILURE_CODES else reason
                self._episode.route_failure_code = failure
                return self._append_closed(success=False, tick=tick, outcome_ref=outcome_ref)
            self._episode.movement_completion_lags.append(lag)
            if outcome_ref:
                self._episode.execution_outcome_refs.append(str(outcome_ref))
            return {"adapted": False, "episode_active": True, "movement_lag": lag}

        if capability == "ORIENT":
            if self._episode is None:
                self._start(binding, tick=tick, terminal=terminal)
            lag = self._record_control_step(
                capability=capability,
                success=success,
                tick=tick,
                issue_tick=issue_tick,
                outcome_ref=outcome_ref,
            )
            if not success:
                self._episode.route_failure_code = reason
                return self._append_closed(success=False, tick=tick, outcome_ref=outcome_ref)
            if outcome_ref:
                self._episode.execution_outcome_refs.append(str(outcome_ref))
            return {"adapted": False, "episode_active": True, "route_control_lag": lag}

        if capability not in TERMINAL_CAPABILITIES:
            return self._discard("unrelated_action")
        if capability != terminal:
            return self._discard("terminal_capability_mismatch")
        if self._episode is None:
            if not success:
                return {"adapted": False, "reason": "terminal_failure_without_route"}
            self._start(binding, tick=tick, terminal=terminal)
        lag = self._record_control_step(
            capability=capability,
            success=success,
            tick=tick,
            issue_tick=issue_tick,
            outcome_ref=outcome_ref,
        )
        if not success:
            if reason in {"not_at_rest", "not_at_resource", "not_at_inspect"}:
                if outcome_ref:
                    self._episode.execution_outcome_refs.append(str(outcome_ref))
                return {"adapted": False, "episode_active": True, "reason": "premature_terminal"}
            self._episode.route_failure_code = reason
            return self._append_closed(success=False, tick=tick, outcome_ref=outcome_ref)
        self._episode.terminal_completion_lag = lag
        return self._append_closed(success=True, tick=tick, outcome_ref=outcome_ref)

    def route_demand_support(
        self,
        *,
        opportunity_entity_id: str,
        body_schema_id: str,
        terminal_capability: str,
    ) -> dict[str, Any]:
        matches = [
            item
            for item in self.experiences
            if item.opportunity_entity_id == str(opportunity_entity_id)
            and item.body_schema_id == str(body_schema_id)
            and item.terminal_capability == str(terminal_capability)
        ]
        if not matches:
            return {
                "status": "UNKNOWN",
                "support_semantics": ROUTE_EVIDENCE_SEMANTICS,
                "opportunity_entity_id": str(opportunity_entity_id),
                "body_schema_id": str(body_schema_id),
                "terminal_capability": str(terminal_capability),
                "sample_count": 0,
            }
        movement_counts = [m.verified_movement_execution_count for m in matches]
        movement_lags = [lag for m in matches for lag in m.movement_completion_lags]
        terminal_lags = [
            int(m.terminal_completion_lag)
            for m in matches
            if m.terminal_completion_lag is not None
        ]
        return {
            "status": "VERIFIED_OBSERVED_SUPPORT",
            "support_semantics": ROUTE_EVIDENCE_SEMANTICS,
            "opportunity_entity_id": str(opportunity_entity_id),
            "body_schema_id": str(body_schema_id),
            "terminal_capability": str(terminal_capability),
            "sample_count": len(matches),
            "success_sample_count": sum(1 for m in matches if m.terminal_result),
            "failure_sample_count": sum(1 for m in matches if not m.terminal_result),
            "observed_movement_execution_min": min(movement_counts),
            "observed_movement_execution_max": max(movement_counts),
            "movement_completion_lag_min": min(movement_lags) if movement_lags else None,
            "movement_completion_lag_max": max(movement_lags) if movement_lags else None,
            "terminal_completion_lag_min": min(terminal_lags) if terminal_lags else None,
            "terminal_completion_lag_max": max(terminal_lags) if terminal_lags else None,
            "terminal_observations": [m.terminal_result for m in matches],
            "failure_modes": sorted(
                {m.route_failure_code for m in matches if m.route_failure_code}
            ),
            "latest_tick": max(m.final_tick for m in matches),
            "provenance": [ref for m in matches for ref in m.execution_outcome_refs],
        }

    def to_state(self) -> dict[str, Any]:
        return {
            "schema": ROUTE_EVIDENCE_SCHEMA,
            "capacity": self.capacity,
            "experiences": [item.to_dict() for item in self.experiences],
        }

    def accepted_state(self) -> dict[str, Any]:
        return self.to_state()

    @classmethod
    def from_state(
        cls, value: Mapping[str, Any] | None, *, default_capacity: int = DEFAULT_ROUTE_EVIDENCE_CAPACITY
    ) -> RouteEvidenceStore:
        if not value:
            return cls(capacity=default_capacity)
        store = cls(capacity=int(value.get("capacity", default_capacity)))
        for item in value.get("experiences", []):
            store.experiences.append(VerifiedRouteExperience.from_dict(item))
        return store

    def counts_bounded(self) -> bool:
        return len(self.experiences) <= self.capacity
