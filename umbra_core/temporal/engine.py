"""TemporalEngine — sole durable temporal authority (D-010)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umbra_core.temporal.clock import TrustedSample, compute_sample_hash
from umbra_core.temporal.state import TemporalState
from umbra_core.util import new_id


class TemporalEngineError(Exception):
    """TemporalEngine invariant violation."""


@dataclass(frozen=True)
class AnchorDelta:
    """Proposed anchor mutation payload; applied on txn commit (Task 3)."""

    trusted_sample_hash: str
    orchestration_sequence: int


@dataclass(frozen=True)
class TemporalAdvancePlan:
    advance_id: str
    expected_state_version: int
    expected_state_hash: str
    orchestration_sequence: int
    trusted_sample_hash: str
    prior_age_ticks: int
    next_age_ticks: int
    prior_active_ticks: int
    next_active_ticks: int
    anchor_delta: AnchorDelta


@dataclass(frozen=True)
class TickTemporalContext:
    advance_id: str
    effective_age_ticks: int
    effective_active_ticks: int
    orchestration_sequence: int
    prior_state_version: int
    prior_state_hash: str


def build_tick_temporal_context(plan: TemporalAdvancePlan) -> TickTemporalContext:
    """Build speculative tick context from a prepared advance plan."""
    return TickTemporalContext(
        advance_id=plan.advance_id,
        effective_age_ticks=plan.next_age_ticks,
        effective_active_ticks=plan.next_active_ticks,
        orchestration_sequence=plan.orchestration_sequence,
        prior_state_version=plan.expected_state_version,
        prior_state_hash=plan.expected_state_hash,
    )


class TemporalEngine:
    """Sole temporal writer. ponytail: commit/apply deferred to Task 3."""

    def __init__(self, state: TemporalState) -> None:
        self._state = state
        self._in_flight: TemporalAdvancePlan | None = None

    @property
    def state(self) -> TemporalState:
        return self._state

    @property
    def in_flight_plan(self) -> TemporalAdvancePlan | None:
        return self._in_flight

    def prepare_advance(
        self,
        sample: TrustedSample,
        orchestration_sequence: int,
    ) -> TemporalAdvancePlan:
        if self._in_flight is not None:
            raise TemporalEngineError("advance_already_prepared")

        prior_age = self._state.organism_age_ticks
        prior_active = self._state.organism_active_ticks
        sample_hash = compute_sample_hash(sample)
        plan = TemporalAdvancePlan(
            advance_id=f"advance:{new_id()}",
            expected_state_version=self._state.state_version,
            expected_state_hash=self._state.state_hash,
            orchestration_sequence=orchestration_sequence,
            trusted_sample_hash=sample_hash,
            prior_age_ticks=prior_age,
            next_age_ticks=prior_age + 1,
            prior_active_ticks=prior_active,
            next_active_ticks=prior_active + 1,
            anchor_delta=AnchorDelta(
                trusted_sample_hash=sample_hash,
                orchestration_sequence=orchestration_sequence,
            ),
        )
        self._in_flight = plan
        return plan

    def abandon_advance(self, advance_id: str) -> None:
        if self._in_flight is None:
            raise TemporalEngineError("no_advance_prepared")
        if self._in_flight.advance_id != advance_id:
            raise TemporalEngineError("advance_id_mismatch")
        self._in_flight = None

    def build_tick_context(self, plan: TemporalAdvancePlan) -> TickTemporalContext:
        return build_tick_temporal_context(plan)
