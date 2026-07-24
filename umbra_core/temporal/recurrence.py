"""Robust parametric recurrence estimation and hypothesis lifecycle (D-010 Decision G)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

_OccurrenceMap = dict[str, tuple[int, str]]

from umbra_core.util import canon_json, sha256_hex

# Frozen estimator constants (ponytail: hardened at Stage B freeze).
ESTIMATOR_SCHEMA_VERSION = "d010.recurrence-estimator.v1"
CONTEXT_SCHEMA_VERSION = "d010.recurrence-context.v1"
MIN_O_LANE_OCCURRENCES_FOR_ACTIVE = 3
MIN_INTERVALS_FOR_PERIOD = 1
MIN_OCCURRENCES_FOR_STABLE_PHASE_ANCHOR = 3
JITTER_MARGIN_MULTIPLIER = 2.0
MAX_RECURRENCE_HYPOTHESES = 64
MAX_MISSES_BEFORE_UNCERTAIN = 3


def estimator_definition_hash() -> str:
    payload = {
        "schema_version": ESTIMATOR_SCHEMA_VERSION,
        "min_o_lane_occurrences_for_active": MIN_O_LANE_OCCURRENCES_FOR_ACTIVE,
        "min_intervals_for_period": MIN_INTERVALS_FOR_PERIOD,
        "min_occurrences_for_stable_phase_anchor": MIN_OCCURRENCES_FOR_STABLE_PHASE_ANCHOR,
        "jitter_margin_multiplier": JITTER_MARGIN_MULTIPLIER,
        "robust_center": "median",
        "robust_spread": "mad",
    }
    return sha256_hex(canon_json(payload))


class EvidenceLane(str, Enum):
    ORGANISM_OBSERVABLE = "O"
    AUTHORITATIVE = "A"


class HypothesisStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    UNCERTAIN = "UNCERTAIN"
    WEAKENED = "WEAKENED"
    INACTIVE = "INACTIVE"
    RETIRED = "RETIRED"


def robust_center(values: Sequence[float]) -> float:
    """Robust center via median (Decision G default)."""
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def robust_spread(values: Sequence[float]) -> float:
    """Robust spread via median absolute deviation (Decision G default)."""
    if len(values) < 2:
        return 0.0
    center = robust_center(values)
    deviations = [abs(float(v) - center) for v in values]
    return robust_center(deviations)


def compute_recurrence_key(
    event_kind: str,
    internal_context_key: str,
    context_schema_version: str,
    estimator_hash: str | None = None,
) -> str:
    payload = {
        "event_kind": event_kind,
        "internal_context_key": internal_context_key,
        "context_schema_version": context_schema_version,
        "estimator_definition_hash": estimator_hash or estimator_definition_hash(),
    }
    return sha256_hex(canon_json(payload))


def recurrence_id_from_key(recurrence_key: str) -> str:
    return f"rec:{recurrence_key[:16]}"


def compute_intervals(occurrence_ticks: Sequence[int]) -> list[float]:
    ordered = sorted(int(t) for t in occurrence_ticks)
    if len(ordered) < 2:
        return []
    return [float(ordered[i] - ordered[i - 1]) for i in range(1, len(ordered))]


def compute_next_index(
    phase_anchor_tick: float,
    period_estimate: float,
    current_age: int,
) -> int:
    """First integer n where phase_anchor_tick + n * period_estimate > current_age."""
    if period_estimate <= 0.0:
        return 0
    n = 0
    while phase_anchor_tick + n * period_estimate <= float(current_age):
        n += 1
    return n


def predict_center(
    *,
    phase_anchor_tick: float | None,
    last_observed_tick: int | None,
    period_estimate: float,
    current_age: int,
    phase_anchor_stable: bool,
) -> float:
    if phase_anchor_stable and phase_anchor_tick is not None and period_estimate > 0.0:
        next_index = compute_next_index(phase_anchor_tick, period_estimate, current_age)
        return phase_anchor_tick + next_index * period_estimate
    if last_observed_tick is not None and period_estimate > 0.0:
        return float(last_observed_tick) + period_estimate
    return float(current_age)


@dataclass(frozen=True)
class RecurrencePrediction:
    next_index: int
    predicted_center: float
    window_start: float
    window_end: float
    period_estimate: float
    jitter_estimate: float
    phase_anchor_tick: float | None
    phase_anchor_stable: bool


@dataclass(frozen=True)
class RecurrenceHypothesis:
    recurrence_id: str
    recurrence_key: str
    event_kind: str
    internal_context_key: str
    context_schema_version: str
    status: HypothesisStatus
    hypothesis_version: int
    occurrence_by_id: tuple[tuple[str, int, str], ...]
    evidence_identities: tuple[str, ...]
    o_lane_occurrence_count: int
    a_lane_seed_count: int
    period_estimate: float
    jitter_estimate: float
    phase_anchor_tick: float | None
    phase_anchor_stable: bool
    last_observed_tick: int | None
    observation_count: int
    miss_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "recurrence_id": self.recurrence_id,
            "recurrence_key": self.recurrence_key,
            "event_kind": self.event_kind,
            "internal_context_key": self.internal_context_key,
            "context_schema_version": self.context_schema_version,
            "status": self.status.value,
            "hypothesis_version": self.hypothesis_version,
            "occurrence_by_id": list(self.occurrence_by_id),
            "evidence_identities": list(self.evidence_identities),
            "o_lane_occurrence_count": self.o_lane_occurrence_count,
            "a_lane_seed_count": self.a_lane_seed_count,
            "period_estimate": self.period_estimate,
            "jitter_estimate": self.jitter_estimate,
            "phase_anchor_tick": self.phase_anchor_tick,
            "phase_anchor_stable": self.phase_anchor_stable,
            "last_observed_tick": self.last_observed_tick,
            "observation_count": self.observation_count,
            "miss_count": self.miss_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RecurrenceHypothesis:
        raw_occurrences = data.get("occurrence_by_id") or []
        occurrence_by_id = _serialize_occurrence_map(_parse_occurrence_entries(raw_occurrences))
        return cls(
            recurrence_id=str(data["recurrence_id"]),
            recurrence_key=str(data["recurrence_key"]),
            event_kind=str(data["event_kind"]),
            internal_context_key=str(data["internal_context_key"]),
            context_schema_version=str(
                data.get("context_schema_version", CONTEXT_SCHEMA_VERSION)
            ),
            status=HypothesisStatus(str(data.get("status", HypothesisStatus.CANDIDATE.value))),
            hypothesis_version=int(data.get("hypothesis_version", 1)),
            occurrence_by_id=occurrence_by_id,
            evidence_identities=tuple(str(x) for x in (data.get("evidence_identities") or [])),
            o_lane_occurrence_count=int(data.get("o_lane_occurrence_count", 0)),
            a_lane_seed_count=int(data.get("a_lane_seed_count", 0)),
            period_estimate=float(data.get("period_estimate", 0.0)),
            jitter_estimate=float(data.get("jitter_estimate", 0.0)),
            phase_anchor_tick=(
                float(data["phase_anchor_tick"])
                if data.get("phase_anchor_tick") is not None
                else None
            ),
            phase_anchor_stable=bool(data.get("phase_anchor_stable", False)),
            last_observed_tick=(
                int(data["last_observed_tick"])
                if data.get("last_observed_tick") is not None
                else None
            ),
            observation_count=int(data.get("observation_count", 0)),
            miss_count=int(data.get("miss_count", 0)),
        )

    def occurrence_ticks(self) -> tuple[int, ...]:
        return _o_lane_ticks_from_map(_parse_occurrence_entries(self.occurrence_by_id))


def _parse_occurrence_entries(
    raw_occurrences: Sequence[Sequence[Any]],
) -> _OccurrenceMap:
    occurrence_map: _OccurrenceMap = {}
    for entry in raw_occurrences:
        if len(entry) == 2:
            occ_id, tick = entry
            lane = EvidenceLane.ORGANISM_OBSERVABLE.value
        else:
            occ_id, tick, lane = entry
            lane = str(lane)
        occurrence_map[str(occ_id)] = (int(tick), lane)
    return occurrence_map


def _serialize_occurrence_map(
    occurrence_map: Mapping[str, tuple[int, str]],
) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        sorted((occ_id, tick, lane) for occ_id, (tick, lane) in occurrence_map.items())
    )


def _o_lane_ticks_from_map(occurrence_map: Mapping[str, tuple[int, str]]) -> tuple[int, ...]:
    return tuple(
        sorted(
            tick
            for tick, lane in occurrence_map.values()
            if lane == EvidenceLane.ORGANISM_OBSERVABLE.value
        )
    )


def _estimate_period_and_jitter(occurrence_ticks: Sequence[int]) -> tuple[float, float]:
    intervals = compute_intervals(occurrence_ticks)
    if len(intervals) < MIN_INTERVALS_FOR_PERIOD:
        return 0.0, 0.0
    period = robust_center(intervals)
    jitter = robust_spread(intervals)
    return period, jitter


def _fit_phase_anchor(occurrence_ticks: Sequence[int]) -> float | None:
    ordered = sorted(int(t) for t in occurrence_ticks)
    if not ordered:
        return None
    return float(ordered[0])


def _phase_anchor_stable(occurrence_ticks: Sequence[int], period_estimate: float) -> bool:
    if len(occurrence_ticks) < MIN_OCCURRENCES_FOR_STABLE_PHASE_ANCHOR:
        return False
    if period_estimate <= 0.0:
        return False
    intervals = compute_intervals(occurrence_ticks)
    if len(intervals) < MIN_INTERVALS_FOR_PERIOD:
        return False
    jitter = robust_spread(intervals)
    return jitter <= period_estimate


def _derive_status(
    *,
    prior_status: HypothesisStatus | None,
    o_lane_occurrence_count: int,
    period_estimate: float,
    interval_count: int,
    miss_count: int,
) -> HypothesisStatus:
    if prior_status in {HypothesisStatus.INACTIVE, HypothesisStatus.RETIRED}:
        return prior_status

    can_promote = (
        o_lane_occurrence_count >= MIN_O_LANE_OCCURRENCES_FOR_ACTIVE
        and period_estimate > 0.0
        and interval_count >= MIN_INTERVALS_FOR_PERIOD
    )
    if can_promote:
        if prior_status == HypothesisStatus.ACTIVE and miss_count >= MAX_MISSES_BEFORE_UNCERTAIN:
            return HypothesisStatus.UNCERTAIN
        if prior_status in {HypothesisStatus.ACTIVE, HypothesisStatus.UNCERTAIN}:
            if miss_count >= MAX_MISSES_BEFORE_UNCERTAIN:
                return HypothesisStatus.UNCERTAIN
            return prior_status
        return HypothesisStatus.ACTIVE

    if prior_status == HypothesisStatus.ACTIVE:
        if miss_count <= 1:
            return HypothesisStatus.ACTIVE
        if miss_count >= MAX_MISSES_BEFORE_UNCERTAIN:
            return HypothesisStatus.UNCERTAIN
        return HypothesisStatus.ACTIVE

    return HypothesisStatus.CANDIDATE


class RecurrenceTracker:
    """Pure recurrence estimator + lifecycle for one hypothesis."""

    def observe(
        self,
        hypothesis: RecurrenceHypothesis | None,
        *,
        recurrence_key: str,
        event_kind: str,
        internal_context_key: str,
        occurrence_id: str,
        evidence_identity: str,
        tick: int,
        lane: EvidenceLane,
        context_schema_version: str = CONTEXT_SCHEMA_VERSION,
    ) -> RecurrenceHypothesis:
        recurrence_id = recurrence_id_from_key(recurrence_key)
        occurrence_map = (
            _parse_occurrence_entries(hypothesis.occurrence_by_id) if hypothesis else {}
        )
        evidence = set(hypothesis.evidence_identities) if hypothesis else set()
        o_lane_count = hypothesis.o_lane_occurrence_count if hypothesis else 0
        a_lane_count = hypothesis.a_lane_seed_count if hypothesis else 0
        prior_status = hypothesis.status if hypothesis else None
        miss_count = hypothesis.miss_count if hypothesis else 0
        hypothesis_version = hypothesis.hypothesis_version if hypothesis else 1

        evidence.add(evidence_identity)
        lane_value = lane.value
        if occurrence_id in occurrence_map:
            prev_tick, prev_lane = occurrence_map[occurrence_id]
            if (
                prev_lane == EvidenceLane.AUTHORITATIVE.value
                and lane_value == EvidenceLane.ORGANISM_OBSERVABLE.value
            ):
                occurrence_map[occurrence_id] = (prev_tick, lane_value)
                o_lane_count += 1
                a_lane_count -= 1
        else:
            occurrence_map[occurrence_id] = (int(tick), lane_value)
            if lane == EvidenceLane.ORGANISM_OBSERVABLE:
                o_lane_count += 1
            else:
                a_lane_count += 1

        occurrence_by_id = _serialize_occurrence_map(occurrence_map)
        o_lane_ticks = _o_lane_ticks_from_map(occurrence_map)
        intervals = compute_intervals(o_lane_ticks)
        period_estimate, jitter_estimate = _estimate_period_and_jitter(o_lane_ticks)
        phase_anchor_tick = _fit_phase_anchor(o_lane_ticks)
        phase_anchor_stable = _phase_anchor_stable(o_lane_ticks, period_estimate)
        last_observed_tick = max(o_lane_ticks) if o_lane_ticks else None
        status = _derive_status(
            prior_status=prior_status,
            o_lane_occurrence_count=o_lane_count,
            period_estimate=period_estimate,
            interval_count=len(intervals),
            miss_count=miss_count,
        )
        if hypothesis and (
            status != hypothesis.status
            or period_estimate != hypothesis.period_estimate
            or phase_anchor_stable != hypothesis.phase_anchor_stable
        ):
            hypothesis_version = hypothesis.hypothesis_version + 1

        return RecurrenceHypothesis(
            recurrence_id=recurrence_id,
            recurrence_key=recurrence_key,
            event_kind=event_kind,
            internal_context_key=internal_context_key,
            context_schema_version=context_schema_version,
            status=status,
            hypothesis_version=hypothesis_version,
            occurrence_by_id=occurrence_by_id,
            evidence_identities=tuple(sorted(evidence)),
            o_lane_occurrence_count=o_lane_count,
            a_lane_seed_count=a_lane_count,
            period_estimate=period_estimate,
            jitter_estimate=jitter_estimate,
            phase_anchor_tick=phase_anchor_tick,
            phase_anchor_stable=phase_anchor_stable,
            last_observed_tick=last_observed_tick,
            observation_count=len(occurrence_by_id),
            miss_count=miss_count,
        )

    def record_miss(self, hypothesis: RecurrenceHypothesis) -> RecurrenceHypothesis:
        miss_count = hypothesis.miss_count + 1
        status = _derive_status(
            prior_status=hypothesis.status,
            o_lane_occurrence_count=hypothesis.o_lane_occurrence_count,
            period_estimate=hypothesis.period_estimate,
            interval_count=len(compute_intervals(hypothesis.occurrence_ticks())),
            miss_count=miss_count,
        )
        hypothesis_version = hypothesis.hypothesis_version
        if status != hypothesis.status:
            hypothesis_version += 1
        return RecurrenceHypothesis(
            recurrence_id=hypothesis.recurrence_id,
            recurrence_key=hypothesis.recurrence_key,
            event_kind=hypothesis.event_kind,
            internal_context_key=hypothesis.internal_context_key,
            context_schema_version=hypothesis.context_schema_version,
            status=status,
            hypothesis_version=hypothesis_version,
            occurrence_by_id=hypothesis.occurrence_by_id,
            evidence_identities=hypothesis.evidence_identities,
            o_lane_occurrence_count=hypothesis.o_lane_occurrence_count,
            a_lane_seed_count=hypothesis.a_lane_seed_count,
            period_estimate=hypothesis.period_estimate,
            jitter_estimate=hypothesis.jitter_estimate,
            phase_anchor_tick=hypothesis.phase_anchor_tick,
            phase_anchor_stable=hypothesis.phase_anchor_stable,
            last_observed_tick=hypothesis.last_observed_tick,
            observation_count=hypothesis.observation_count,
            miss_count=miss_count,
        )

    def predict(
        self,
        hypothesis: RecurrenceHypothesis,
        current_age: int,
    ) -> RecurrencePrediction | None:
        if hypothesis.period_estimate <= 0.0:
            return None
        center = predict_center(
            phase_anchor_tick=hypothesis.phase_anchor_tick,
            last_observed_tick=hypothesis.last_observed_tick,
            period_estimate=hypothesis.period_estimate,
            current_age=current_age,
            phase_anchor_stable=hypothesis.phase_anchor_stable,
        )
        next_index = 0
        if (
            hypothesis.phase_anchor_stable
            and hypothesis.phase_anchor_tick is not None
        ):
            next_index = compute_next_index(
                hypothesis.phase_anchor_tick,
                hypothesis.period_estimate,
                current_age,
            )
        jitter_margin = hypothesis.jitter_estimate * JITTER_MARGIN_MULTIPLIER
        return RecurrencePrediction(
            next_index=next_index,
            predicted_center=center,
            window_start=center - jitter_margin,
            window_end=center + jitter_margin,
            period_estimate=hypothesis.period_estimate,
            jitter_estimate=hypothesis.jitter_estimate,
            phase_anchor_tick=hypothesis.phase_anchor_tick,
            phase_anchor_stable=hypothesis.phase_anchor_stable,
        )


def hypothesis_from_index_entry(
    recurrence_id: str,
    payload: Mapping[str, Any],
) -> RecurrenceHypothesis:
    data = dict(payload)
    data.setdefault("recurrence_id", recurrence_id)
    return RecurrenceHypothesis.from_dict(data)


def upsert_recurrence_index(
    recurrence_index: tuple[tuple[str, dict[str, Any]], ...],
    hypothesis: RecurrenceHypothesis,
) -> tuple[tuple[str, dict[str, Any]], ...]:
    updated = {key: dict(value) for key, value in recurrence_index}
    updated[hypothesis.recurrence_id] = hypothesis.to_dict()
    if len(updated) > MAX_RECURRENCE_HYPOTHESES:
        raise ValueError("recurrence_index_overflow")
    return tuple((key, updated[key]) for key in sorted(updated))


def get_hypothesis_from_index(
    recurrence_index: tuple[tuple[str, dict[str, Any]], ...],
    recurrence_id: str,
) -> RecurrenceHypothesis | None:
    for key, payload in recurrence_index:
        if key == recurrence_id:
            return hypothesis_from_index_entry(key, payload)
    return None
