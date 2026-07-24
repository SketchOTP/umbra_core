"""Policy-facing temporal expectation views (D-010 §1.9 / §2.8)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umbra_core.temporal.recurrence import (
    HypothesisStatus,
    RecurrenceHypothesis,
    RecurrencePrediction,
)
from umbra_core.util import clamp

POLICY_VISIBLE_STATUSES = frozenset(
    {HypothesisStatus.ACTIVE.value, HypothesisStatus.UNCERTAIN.value}
)


@dataclass(frozen=True)
class PolicyExpectationView:
    recurrence_id: str
    window_start: float
    window_end: float
    confidence: float
    uncertainty: float
    expected_context: str
    expectation_version: int
    status: str  # ACTIVE | UNCERTAIN only


def build_policy_context_view(event_kind: str) -> str:
    """Coarse policy context — event kind only; no hidden internal ids."""
    return str(event_kind)


def hypothesis_confidence(hypothesis: RecurrenceHypothesis) -> float:
    if hypothesis.status == HypothesisStatus.ACTIVE:
        base = 0.7 + min(0.25, hypothesis.o_lane_occurrence_count * 0.05)
        base -= min(0.2, hypothesis.miss_count * 0.05)
        return clamp(base, 0.5, 0.95)
    base = 0.35 + min(0.15, hypothesis.o_lane_occurrence_count * 0.03)
    base -= min(0.1, hypothesis.miss_count * 0.03)
    return clamp(base, 0.2, 0.5)


def hypothesis_uncertainty(hypothesis: RecurrenceHypothesis) -> float:
    if hypothesis.period_estimate <= 0.0:
        return 1.0
    spread = hypothesis.jitter_estimate / hypothesis.period_estimate
    return clamp(spread, 0.0, 1.0)


def build_policy_expectation_view(
    hypothesis: RecurrenceHypothesis,
    prediction: RecurrencePrediction,
) -> PolicyExpectationView | None:
    if hypothesis.status.value not in POLICY_VISIBLE_STATUSES:
        return None
    return PolicyExpectationView(
        recurrence_id=hypothesis.recurrence_id,
        window_start=prediction.window_start,
        window_end=prediction.window_end,
        confidence=hypothesis_confidence(hypothesis),
        uncertainty=hypothesis_uncertainty(hypothesis),
        expected_context=build_policy_context_view(hypothesis.event_kind),
        expectation_version=hypothesis.hypothesis_version,
        status=hypothesis.status.value,
    )


def policy_expectation_views_from_index(
    recurrence_index: tuple[tuple[str, dict[str, Any]], ...],
    *,
    current_age: int,
    predict_fn,
) -> tuple[PolicyExpectationView, ...]:
    """Build policy-visible views; hides CANDIDATE/WEAKENED/INACTIVE/RETIRED."""
    views: list[PolicyExpectationView] = []
    for recurrence_id, _payload in recurrence_index:
        prediction = predict_fn(recurrence_id, current_age=current_age)
        if prediction is None:
            continue
        from umbra_core.temporal.recurrence import get_hypothesis_from_index

        hypothesis = get_hypothesis_from_index(recurrence_index, recurrence_id)
        if hypothesis is None:
            continue
        view = build_policy_expectation_view(hypothesis, prediction)
        if view is not None:
            views.append(view)
    return tuple(sorted(views, key=lambda v: v.recurrence_id))
