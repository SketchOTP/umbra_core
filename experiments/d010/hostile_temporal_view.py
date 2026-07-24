"""D-010 C9 — hostile external clock / UI treated as temporal truth (experiments only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from umbra_core.temporal.clock import TrustedSample
from umbra_core.temporal.engine import TemporalEngine, TemporalEngineError


@dataclass
class HostileTemporalClockView:
    """Records attempts to drive TemporalEngine from non-authoritative surfaces."""

    attempted_writes: list[str] = field(default_factory=list)
    rejected_writes: list[str] = field(default_factory=list)
    successful_writes: list[str] = field(default_factory=list)

    def attempt_ui_clock_as_truth(
        self,
        engine: TemporalEngine,
        *,
        fake_sample: TrustedSample | None = None,
        ui_advance: Callable[[TrustedSample], Any] | None = None,
    ) -> None:
        sample = fake_sample or TrustedSample(
            session_id="ui:hostile",
            monotonic_ns=9_999_999,
            optional_wall_time=1_700_000_000.0,
            wall_time_source="ui_clock",
            wall_time_uncertainty=0.0,
            sample_sequence=99,
        )
        self._attempt_ui_advance(engine, sample)
        if ui_advance is not None:
            self._attempt("ui_advance_callback", lambda: ui_advance(sample))

    def _attempt_ui_advance(self, engine: TemporalEngine, sample: TrustedSample) -> None:
        label = "ui_trusted_sample_advance"
        self.attempted_writes.append(label)
        before_age = engine.state.organism_age_ticks
        try:
            plan = engine.prepare_advance(sample, orchestration_sequence=1)
            engine.abandon_advance(plan.advance_id)
        except TemporalEngineError:
            self.rejected_writes.append(label)
            return
        if engine.state.organism_age_ticks != before_age:
            self.successful_writes.append(label)
        else:
            self.rejected_writes.append(label)

    def attempt_projection_age_override(self, projection_age: int) -> None:
        self._attempt(
            "projection_age_override",
            lambda: setattr(object(), "organism_age_ticks", projection_age),
        )

    def _attempt(self, label: str, action: Callable[[], Any]) -> None:
        self.attempted_writes.append(label)
        try:
            action()
        except (AttributeError, TemporalEngineError, TypeError, ValueError):
            self.rejected_writes.append(label)
        else:
            self.successful_writes.append(label)
