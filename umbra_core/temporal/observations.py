"""D-010 observation plans, window evidence, and durable dedup summaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from umbra_core.util import canon_json, new_id, sha256_hex

# ponytail: frozen at Stage B; upgrade path is experiments/d010 thresholds freeze.
MIN_OBSERVATION_COVERAGE_FRACTION = 0.75
MIN_OBSERVABILITY_QUALITY = 0.5
MAX_RECENT_EVIDENCE_IDENTITIES = 32
MAX_RETAINED_OCCURRENCE_IDENTITIES = 32
MAX_COMPACTED_IDENTITIES = 128


class CommitMode(str, Enum):
    IN_TICK = "IN_TICK"
    POST_HOC = "POST_HOC"


@dataclass(frozen=True)
class HypothesisDelta:
    event_kind: str
    internal_context_key: str
    occurrence_id: str
    evidence_identity: str
    tick: int
    lane: str
    context_schema_version: str


@dataclass(frozen=True)
class TemporalObservationPlan:
    observation_plan_id: str
    commit_mode: CommitMode
    expected_temporal_state_version: int
    expected_temporal_state_hash: str
    source_transaction_id: str | None
    source_event_id: str | None
    source_event_hash: str | None
    committed_advance_id: str | None
    committed_age_ticks: int | None
    committed_temporal_state_version: int | None
    occurrence_id: str
    evidence_identities: tuple[str, ...]
    hypothesis_deltas: tuple[HypothesisDelta, ...]
    temporal_events: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ObservationWindowEvidence:
    recurrence_id: str
    expectation_version: int
    window_start: float
    window_end: float
    coverage_start: float
    coverage_end: float
    observability_quality: float
    supporting_observation_refs: tuple[str, ...]
    matched_occurrence_id: str | None
    downtime_or_conservative_recovery: bool = False


@dataclass(frozen=True)
class DedupSummary:
    recent_evidence_identities: tuple[str, ...]
    retained_occurrence_identities: tuple[str, ...]
    compacted_identities: tuple[str, ...]
    compacted_identity_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "recent_evidence_identities": list(self.recent_evidence_identities),
            "retained_occurrence_identities": list(self.retained_occurrence_identities),
            "compacted_identities": list(self.compacted_identities),
            "compacted_identity_digest": self.compacted_identity_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> DedupSummary:
        if not data:
            return empty_dedup_summary()
        return cls(
            recent_evidence_identities=tuple(
                str(x) for x in (data.get("recent_evidence_identities") or [])
            ),
            retained_occurrence_identities=tuple(
                str(x) for x in (data.get("retained_occurrence_identities") or [])
            ),
            compacted_identities=tuple(
                str(x) for x in (data.get("compacted_identities") or [])
            ),
            compacted_identity_digest=str(data.get("compacted_identity_digest", "")),
        )


def empty_dedup_summary() -> DedupSummary:
    return DedupSummary((), (), (), "")


def compute_compacted_digest(identities: Sequence[str]) -> str:
    if not identities:
        return ""
    return sha256_hex(canon_json(sorted(str(x) for x in identities)))


def identity_seen(
    summary: DedupSummary,
    *,
    evidence_identity: str | None = None,
    occurrence_id: str | None = None,
) -> bool:
    if evidence_identity is not None:
        if (
            evidence_identity in summary.recent_evidence_identities
            or evidence_identity in summary.compacted_identities
        ):
            return True
    if occurrence_id is not None:
        if (
            occurrence_id in summary.retained_occurrence_identities
            or occurrence_id in summary.compacted_identities
        ):
            return True
    return False


def register_identities(
    summary: DedupSummary,
    *,
    evidence_identities: Sequence[str] = (),
    occurrence_ids: Sequence[str] = (),
) -> DedupSummary:
    recent = list(summary.recent_evidence_identities)
    retained = list(summary.retained_occurrence_identities)
    compacted = list(summary.compacted_identities)

    for identity in evidence_identities:
        if identity in recent or identity in compacted:
            continue
        if len(recent) >= MAX_RECENT_EVIDENCE_IDENTITIES:
            evicted = recent.pop(0)
            if evicted not in compacted:
                if len(compacted) >= MAX_COMPACTED_IDENTITIES:
                    raise ValueError("dedup_compaction_overflow")
                compacted.append(evicted)
        recent.append(identity)

    for occ_id in occurrence_ids:
        if occ_id in retained or occ_id in compacted:
            continue
        if len(retained) >= MAX_RETAINED_OCCURRENCE_IDENTITIES:
            evicted = retained.pop(0)
            if evicted not in compacted:
                if len(compacted) >= MAX_COMPACTED_IDENTITIES:
                    raise ValueError("dedup_compaction_overflow")
                compacted.append(evicted)
        retained.append(occ_id)

    return DedupSummary(
        recent_evidence_identities=tuple(recent),
        retained_occurrence_identities=tuple(retained),
        compacted_identities=tuple(compacted),
        compacted_identity_digest=compute_compacted_digest(compacted),
    )


def observation_miss_key(
    recurrence_id: str,
    expectation_version: int,
    window_start: float,
    window_end: float,
) -> str:
    payload = {
        "recurrence_id": recurrence_id,
        "expectation_version": expectation_version,
        "window_start": window_start,
        "window_end": window_end,
    }
    return sha256_hex(canon_json(payload))


def window_coverage_fraction(evidence: ObservationWindowEvidence) -> float:
    window_span = evidence.window_end - evidence.window_start
    if window_span <= 0.0:
        return 0.0
    covered = max(
        0.0,
        min(evidence.coverage_end, evidence.window_end)
        - max(evidence.coverage_start, evidence.window_start),
    )
    return covered / window_span


def miss_eligible(
    evidence: ObservationWindowEvidence,
    *,
    current_expectation_version: int,
) -> bool:
    if evidence.downtime_or_conservative_recovery:
        return False
    if evidence.matched_occurrence_id is not None:
        return False
    if evidence.expectation_version != current_expectation_version:
        return False
    if evidence.observability_quality < MIN_OBSERVABILITY_QUALITY:
        return False
    if window_coverage_fraction(evidence) < MIN_OBSERVATION_COVERAGE_FRACTION:
        return False
    return True


def new_observation_plan_id() -> str:
    return f"obs-plan:{new_id()}"
