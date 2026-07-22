"""D-006 SocialEngine — partner recognition hypotheses and derived satiation.

Partner identity is never certain. SocialEngine only ever sees noisy,
partner_id-free cue vectors (Perception membrane) and maintains internal
`PartnerHypothesis` estimates. Hidden `partner_id` never enters this module;
`hypothesis_id` is generated independently and never equals it.

Recognition confidence decay and current satiation are DERIVED from anchors
(`*_anchor`, `last_*_tick`, `decay_parameters`) — never persisted per tick.
`social_recognition_updated` is authoritative and is emitted only for
accepted anchors / lifecycle-changing status transitions, not every tick.

Contingency tables (pending traces, atomic outcome commit) are Task 5 scope.
`ContingencyCell` / `record_contingency_sample` here are a minimal in-memory
recorder so `expected_response_latency` has something to derive from; they
are provisional and must be superseded by Task 5's atomic
pending→episode→contingency commit before evidence counts as accepted
partner history.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

from umbra_core.identity import deterministic_id
from umbra_core.util import clamp, new_id


# Defaults mirror experiments/d006/thresholds.json (frozen preregistration).
# ponytail: hardcoded to match governance.py's SIGNAL_COOLDOWN_TICKS_DEFAULT
# convention rather than reading the JSON file at import time.
MAX_ACTIVE_EVIDENCE_REFS = 32
MAX_ACTIVE_SUPPORTING_EPISODES = 24
MAX_ACTIVE_CONTRADICTING_EPISODES = 24
MAX_SOURCE_HYPOTHESIS_IDS = 8
MAX_ROUTINE_SUPPORTING_EPISODES = 24
MAX_PARTNER_HYPOTHESES = 16
MAX_CONTINGENCY_CELLS = 256
RECOGNITION_MATCH_THRESHOLD = 0.55
RECOGNITION_CONTEST_GAP_MAX = 0.08
SATIATION_RISE = 0.12
SATIATION_DECAY_PER_TICK = 0.002
MIN_ENCOUNTERS_FOR_FAMILIAR = 2  # ponytail: simplest correct familiarity gate

# Cue fields used for identity matching. `relative_position` is deliberately
# excluded — spatial tracking belongs to WorldModel, not longitudinal
# partner identity (design §1 "additional boundaries").
CUE_VECTOR_FIELDS = (
    "motion_signature",
    "appearance_signature",
    "response_timing_pattern",
    "interaction_style_cues",
)

PROTOTYPE_BLEND_ALPHA = 0.3
CONTINGENCY_EMA_ALPHA = 0.3

# Classification timing windows — frozen in experiments/d006/thresholds.json.
# ponytail: mirrored as module defaults (same convention as the recognition
# thresholds above) rather than reading the JSON at import time.
RESPONSE_WINDOW_CONTINGENT = (1, 8)
RESPONSE_WINDOW_DELAYED = (9, 24)
RESPONSE_NONE_TIMEOUT = 32
MAX_PENDING_INTERACTIONS = 8
RELIABILITY_GAIN = 0.25
RELIABILITY_LOSS = 0.30
RELIABILITY_ANOMALY_WEAKEN = 0.08
SWAP_DETECT_SCORE_MARGIN = 0.15
SWAP_RECENCY_TICKS = 64


class HypothesisStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    FAMILIAR = "FAMILIAR"
    CONTESTED = "CONTESTED"
    INACTIVE = "INACTIVE"


class ResponseClass(str, Enum):
    """Contingency classification — precedence order top to bottom."""

    EXTERNAL = "EXTERNAL"
    AMBIGUOUS = "AMBIGUOUS"
    CONTINGENT = "CONTINGENT"
    DELAYED = "DELAYED"
    COINCIDENTAL = "COINCIDENTAL"
    NONE = "NONE"


class PendingStatus(str, Enum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"
    INTERRUPTED = "INTERRUPTED"


def _match_score(cue: dict[str, Any], prototype: dict[str, Any]) -> float:
    """Normalized similarity in [0,1] over shared cue-vector fields only."""
    sq = 0.0
    dims = 0
    for f in CUE_VECTOR_FIELDS:
        cv = cue.get(f)
        pv = prototype.get(f)
        if cv is None or pv is None or len(cv) != len(pv):
            continue
        for a, b in zip(cv, pv):
            sq += (float(a) - float(b)) ** 2
            dims += 1
    if dims == 0:
        return 0.0
    dist = math.sqrt(sq / dims)  # cue fields are clamped to [0,1]
    return clamp(1.0 - dist)


def _blend_prototype(
    prototype: dict[str, Any], cue: dict[str, Any], alpha: float = PROTOTYPE_BLEND_ALPHA
) -> dict[str, list[float]]:
    blended = dict(prototype)
    for f in CUE_VECTOR_FIELDS:
        cv = cue.get(f)
        if cv is None:
            continue
        pv = blended.get(f)
        if pv is None or len(pv) != len(cv):
            blended[f] = [float(v) for v in cv]
        else:
            blended[f] = [(1 - alpha) * float(p) + alpha * float(c) for p, c in zip(pv, cv)]
    return blended


@dataclass
class PartnerHypothesis:
    """Internal recognition estimate — `hypothesis_id` never equals hidden partner_id."""

    hypothesis_id: str
    status: str = HypothesisStatus.UNKNOWN.value
    recognition_confidence: float = 0.0
    cue_prototype: dict[str, list[float]] = field(default_factory=dict)
    encounter_count: int = 0
    familiarity: float = 0.0
    responsiveness: float = 0.0
    reliability_by_context: dict[str, float] = field(default_factory=dict)
    interaction_preference_by_context: dict[str, float] = field(default_factory=dict)
    satiation_anchor: float = 0.0
    uncertainty: float = 1.0
    last_interaction_tick: int = 0
    last_satiation_update_tick: int = 0
    decay_parameters: dict[str, float] = field(
        default_factory=lambda: {"rate": SATIATION_DECAY_PER_TICK}
    )
    evidence_refs: list[str] = field(default_factory=list)
    source_hypothesis_ids: list[str] = field(default_factory=list)
    created_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PartnerHypothesis:
        return cls(
            hypothesis_id=str(d["hypothesis_id"]),
            status=str(d.get("status", HypothesisStatus.UNKNOWN.value)),
            recognition_confidence=float(d.get("recognition_confidence", 0.0)),
            cue_prototype={
                k: [float(x) for x in v] for k, v in (d.get("cue_prototype") or {}).items()
            },
            encounter_count=int(d.get("encounter_count", 0)),
            familiarity=float(d.get("familiarity", 0.0)),
            responsiveness=float(d.get("responsiveness", 0.0)),
            reliability_by_context={
                k: float(v) for k, v in (d.get("reliability_by_context") or {}).items()
            },
            interaction_preference_by_context={
                k: float(v) for k, v in (d.get("interaction_preference_by_context") or {}).items()
            },
            satiation_anchor=float(d.get("satiation_anchor", 0.0)),
            uncertainty=float(d.get("uncertainty", 1.0)),
            last_interaction_tick=int(d.get("last_interaction_tick", 0)),
            last_satiation_update_tick=int(d.get("last_satiation_update_tick", 0)),
            decay_parameters={
                k: float(v)
                for k, v in (d.get("decay_parameters") or {"rate": SATIATION_DECAY_PER_TICK}).items()
            },
            evidence_refs=list(d.get("evidence_refs") or []),
            source_hypothesis_ids=list(d.get("source_hypothesis_ids") or []),
            created_tick=int(d.get("created_tick", 0)),
        )


@dataclass
class ContingencyCell:
    """(hypothesis, context, signal) contingency evidence — design §2.

    Aggregate counts stay in the cell; complete provenance stays recoverable via the
    `social_evidence_links` table + event ledger. Active episode-id sets are bounded.
    """

    hypothesis_id: str
    context: str
    signal: str
    latency_ema: float = 0.0
    latency_variance: float = 0.0
    contingent_count: int = 0
    delayed_count: int = 0
    none_count: int = 0
    coincidental_count: int = 0
    ambiguous_count: int = 0
    external_count: int = 0
    confidence: float = 0.0
    supporting_episode_ids: list[str] = field(default_factory=list)
    contradicting_episode_ids: list[str] = field(default_factory=list)
    last_updated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContingencyCell:
        return cls(
            hypothesis_id=str(d["hypothesis_id"]),
            context=str(d["context"]),
            signal=str(d["signal"]),
            latency_ema=float(d.get("latency_ema", 0.0)),
            latency_variance=float(d.get("latency_variance", 0.0)),
            contingent_count=int(d.get("contingent_count", 0)),
            delayed_count=int(d.get("delayed_count", 0)),
            none_count=int(d.get("none_count", 0)),
            coincidental_count=int(d.get("coincidental_count", 0)),
            ambiguous_count=int(d.get("ambiguous_count", 0)),
            external_count=int(d.get("external_count", 0)),
            confidence=float(d.get("confidence", 0.0)),
            supporting_episode_ids=list(d.get("supporting_episode_ids") or []),
            contradicting_episode_ids=list(d.get("contradicting_episode_ids") or []),
            last_updated=int(d.get("last_updated", 0)),
        )


@dataclass
class PendingInteraction:
    """Event-sourced pre-episode trace — created only after a governed executed signal."""

    pending_interaction_id: str
    hypothesis_id_at_signal: str
    recognition_confidence: float
    context: str
    signal: str
    execution_id: str
    signal_tick: int
    response_window: list[int]  # [contingent_lo, none_timeout] durable timing bound
    status: str = PendingStatus.PENDING.value
    created_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PendingInteraction:
        return cls(
            pending_interaction_id=str(d["pending_interaction_id"]),
            hypothesis_id_at_signal=str(d["hypothesis_id_at_signal"]),
            recognition_confidence=float(d.get("recognition_confidence", 0.0)),
            context=str(d["context"]),
            signal=str(d["signal"]),
            execution_id=str(d["execution_id"]),
            signal_tick=int(d["signal_tick"]),
            response_window=[int(x) for x in (d.get("response_window") or [1, RESPONSE_NONE_TIMEOUT])],
            status=str(d.get("status", PendingStatus.PENDING.value)),
            created_tick=int(d.get("created_tick", 0)),
        )


@dataclass
class RecognitionMatch:
    hypothesis_id: str | None
    status: str
    recognition_confidence: float
    is_new_hypothesis: bool
    contested_with: list[str] = field(default_factory=list)


@dataclass
class RecognitionResult:
    matches: list[RecognitionMatch]
    emitted_events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SocialConfig:
    """Ablation switches for D-006 conditions (C4/C6 implemented; see condition_to_social_config)."""

    enabled: bool = True
    persist_relationship: bool = True  # C4 off — reset at encounter boundaries + restart
    recognition_enabled: bool = True  # C6 off — always UNKNOWN
    satiation_enabled: bool = True  # C5 off — no social satiation
    max_active_evidence_refs: int = MAX_ACTIVE_EVIDENCE_REFS
    max_active_supporting_episodes: int = MAX_ACTIVE_SUPPORTING_EPISODES
    max_active_contradicting_episodes: int = MAX_ACTIVE_CONTRADICTING_EPISODES
    max_source_hypothesis_ids: int = MAX_SOURCE_HYPOTHESIS_IDS
    max_routine_supporting_episodes: int = MAX_ROUTINE_SUPPORTING_EPISODES
    max_partner_hypotheses: int = MAX_PARTNER_HYPOTHESES
    max_contingency_cells: int = MAX_CONTINGENCY_CELLS
    recognition_match_threshold: float = RECOGNITION_MATCH_THRESHOLD
    recognition_contest_gap_max: float = RECOGNITION_CONTEST_GAP_MAX
    satiation_rise: float = SATIATION_RISE
    satiation_decay_per_tick: float = SATIATION_DECAY_PER_TICK
    min_encounters_for_familiar: int = MIN_ENCOUNTERS_FOR_FAMILIAR
    max_pending_interactions: int = MAX_PENDING_INTERACTIONS
    response_window_contingent: tuple[int, int] = RESPONSE_WINDOW_CONTINGENT
    response_window_delayed: tuple[int, int] = RESPONSE_WINDOW_DELAYED
    response_none_timeout: int = RESPONSE_NONE_TIMEOUT
    contingency_min_recognition_confidence: float = RECOGNITION_MATCH_THRESHOLD
    reliability_gain: float = RELIABILITY_GAIN
    reliability_loss: float = RELIABILITY_LOSS
    reliability_anomaly_weaken: float = RELIABILITY_ANOMALY_WEAKEN
    swap_detect_score_margin: float = SWAP_DETECT_SCORE_MARGIN
    swap_recency_ticks: int = SWAP_RECENCY_TICKS


def condition_to_social_config(condition: str) -> SocialConfig:
    c = SocialConfig()
    if condition == "C0":
        return c
    if condition == "C4":
        c.persist_relationship = False
        return c
    if condition == "C5":
        c.satiation_enabled = False
        return c
    if condition == "C6":
        c.recognition_enabled = False
        return c
    # C1/C2/C3/C7/C8/C9 depend on contingency/runtime/routine wiring landing in
    # later tasks; they fall through to the C0 baseline here (no speculative
    # behavior implemented ahead of that wiring).
    return c


class SocialEngineError(ValueError):
    """Fail-closed SocialEngine boundary violation (e.g. hidden identity leak)."""


@dataclass
class SocialEngine:
    """Bounded partner recognition + derived satiation/latency."""

    agent_id: str
    hypotheses: dict[str, PartnerHypothesis] = field(default_factory=dict)
    archived_hypotheses: dict[str, PartnerHypothesis] = field(default_factory=dict)
    contingency_cells: dict[str, ContingencyCell] = field(default_factory=dict)
    pending: dict[str, PendingInteraction] = field(default_factory=dict)
    config: SocialConfig = field(default_factory=SocialConfig)
    seed: int | None = None
    emit_event: Callable[[str, dict[str, Any]], None] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    _hypothesis_counter: int = 0
    _pending_counter: int = 0
    _bounded_initialized: bool = False

    @classmethod
    def create(
        cls,
        agent_id: str,
        *,
        config: SocialConfig | None = None,
        seed: int | None = None,
        emit_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> SocialEngine:
        eng = cls(agent_id=agent_id, config=config or SocialConfig(), seed=seed, emit_event=emit_event)
        eng._bounded_initialized = True
        eng.metrics = {
            "hypotheses_created": 0,
            "recognition_updates": 0,
            "contested_updates": 0,
            "events_emitted": 0,
            "pending_created": 0,
            "pending_resolved": 0,
            "pending_expired": 0,
            "pending_interrupted": 0,
            "contingency_updates": 0,
            "reliability_revisions": 0,
            "hypothesis_merges": 0,
            "hypothesis_splits": 0,
            "partner_swaps_detected": 0,
        }
        return eng

    # --- boundary safety ---------------------------------------------------

    def _assert_no_hidden_identity(self, cue: dict[str, Any]) -> None:
        if "partner_id" in cue or "hidden_partner_id" in cue:
            raise SocialEngineError("hidden_partner_id_leaked_into_social_engine")

    def _emit(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.emit_event is not None:
            self.emit_event(event_type, payload)
        self.metrics["events_emitted"] = int(self.metrics.get("events_emitted", 0)) + 1
        return {"event_type": event_type, "payload": payload}

    def _new_hypothesis_id(self) -> str:
        self._hypothesis_counter += 1
        if self.seed is not None:
            return deterministic_id(self.seed, f"hyp:{self.agent_id}:{self._hypothesis_counter}")
        return new_id()

    def _get_hypothesis(self, hypothesis_id: str) -> PartnerHypothesis:
        hyp = self.hypotheses.get(hypothesis_id) or self.archived_hypotheses.get(hypothesis_id)
        if hyp is None:
            raise KeyError(f"hypothesis_missing:{hypothesis_id}")
        return hyp

    # --- recognition ---------------------------------------------------

    def _create_hypothesis(self, cue: dict[str, Any], tick: int) -> PartnerHypothesis:
        hid = self._new_hypothesis_id()
        proto = {f: [float(x) for x in cue[f]] for f in CUE_VECTOR_FIELDS if f in cue}
        hyp = PartnerHypothesis(
            hypothesis_id=hid,
            status=HypothesisStatus.UNKNOWN.value,
            cue_prototype=proto,
            encounter_count=1,
            familiarity=0.05,
            last_interaction_tick=tick,
            last_satiation_update_tick=tick,
            created_tick=tick,
        )
        self.hypotheses[hid] = hyp
        self.metrics["hypotheses_created"] = int(self.metrics.get("hypotheses_created", 0)) + 1
        self._prune_hypotheses()
        return hyp

    def recognize(
        self, cues: list[dict[str, Any]], tick: int, *, store: Any = None
    ) -> RecognitionResult:
        """Match/update hypotheses from noisy partner cues. No hidden partner_id.

        `store` is optional and only used to durably interrupt any open pending
        trace tied to a hypothesis that newly becomes CONTESTED mid-window
        (design: contested recognition must not silently settle a bid).
        """
        matches: list[RecognitionMatch] = []
        emitted: list[dict[str, Any]] = []

        for cue in cues:
            self._assert_no_hidden_identity(cue)

            if not self.config.recognition_enabled:
                matches.append(
                    RecognitionMatch(
                        hypothesis_id=None,
                        status=HypothesisStatus.UNKNOWN.value,
                        recognition_confidence=0.0,
                        is_new_hypothesis=False,
                    )
                )
                continue

            candidates = [
                h for h in self.hypotheses.values() if h.status != HypothesisStatus.INACTIVE.value
            ]
            scored = sorted(
                ((h, _match_score(cue, h.cue_prototype)) for h in candidates),
                key=lambda hs: -hs[1],
            )
            best = scored[0] if scored else None

            if best is None or best[1] < self.config.recognition_match_threshold:
                hyp = self._create_hypothesis(cue, tick)
                emitted.append(
                    self._emit(
                        "social_hypothesis_created",
                        {"hypothesis_id": hyp.hypothesis_id, "tick": tick},
                    )
                )
                matches.append(
                    RecognitionMatch(
                        hypothesis_id=hyp.hypothesis_id,
                        status=hyp.status,
                        recognition_confidence=best[1] if best else 0.0,
                        is_new_hypothesis=True,
                    )
                )
                continue

            second = scored[1] if len(scored) > 1 else None
            gap = (best[1] - second[1]) if second is not None else 1.0
            swap_from = self._maybe_detect_partner_swap(best[0].hypothesis_id, best[1], scored, tick)
            if swap_from is not None:
                emitted.append(
                    self._emit(
                        "social_partner_swap_detected",
                        {
                            "from_hypothesis_id": swap_from,
                            "to_hypothesis_id": best[0].hypothesis_id,
                            "tick": tick,
                        },
                    )
                )
                self.metrics["partner_swaps_detected"] = (
                    int(self.metrics.get("partner_swaps_detected", 0)) + 1
                )
            if second is not None and gap < self.config.recognition_contest_gap_max:
                contested_ids = [best[0].hypothesis_id, second[0].hypothesis_id]
                for h in (best[0], second[0]):
                    if h.status != HypothesisStatus.CONTESTED.value:
                        h.status = HypothesisStatus.CONTESTED.value
                        emitted.append(
                            self._emit(
                                "social_hypothesis_contested",
                                {"hypothesis_id": h.hypothesis_id, "tick": tick},
                            )
                        )
                        for pid, p in list(self.pending.items()):
                            if (
                                p.hypothesis_id_at_signal == h.hypothesis_id
                                and p.status == PendingStatus.PENDING.value
                            ):
                                self.interrupt_pending(
                                    pid, "recognition_contested", store=store, tick=tick
                                )
                self.metrics["contested_updates"] = int(self.metrics.get("contested_updates", 0)) + 1
                matches.append(
                    RecognitionMatch(
                        hypothesis_id=best[0].hypothesis_id,
                        status=HypothesisStatus.CONTESTED.value,
                        recognition_confidence=best[1],
                        is_new_hypothesis=False,
                        contested_with=contested_ids,
                    )
                )
                continue

            hyp = best[0]
            prev_status = hyp.status
            hyp.cue_prototype = _blend_prototype(hyp.cue_prototype, cue)
            hyp.encounter_count += 1
            hyp.familiarity = clamp(hyp.familiarity + 0.1)
            hyp.recognition_confidence = best[1]
            hyp.uncertainty = clamp(1.0 - best[1])
            hyp.last_interaction_tick = tick
            if (
                hyp.encounter_count >= self.config.min_encounters_for_familiar
                and prev_status in (HypothesisStatus.UNKNOWN.value, HypothesisStatus.CONTESTED.value)
            ):
                hyp.status = HypothesisStatus.FAMILIAR.value
            if hyp.status != prev_status and hyp.status == HypothesisStatus.FAMILIAR.value:
                self.metrics["recognition_updates"] = (
                    int(self.metrics.get("recognition_updates", 0)) + 1
                )
                emitted.append(
                    self._emit(
                        "social_recognition_updated",
                        {
                            "hypothesis_id": hyp.hypothesis_id,
                            "status": hyp.status,
                            "recognition_confidence": hyp.recognition_confidence,
                            "tick": tick,
                        },
                    )
                )
            matches.append(
                RecognitionMatch(
                    hypothesis_id=hyp.hypothesis_id,
                    status=hyp.status,
                    recognition_confidence=hyp.recognition_confidence,
                    is_new_hypothesis=False,
                )
            )

        self._prune_hypotheses()
        return RecognitionResult(matches=matches, emitted_events=emitted)

    def _prune_hypotheses(self) -> None:
        if len(self.hypotheses) <= self.config.max_partner_hypotheses:
            return
        ranked = sorted(
            self.hypotheses.values(),
            key=lambda h: (
                0 if h.status == HypothesisStatus.INACTIVE.value else 1,
                h.familiarity,
                h.last_interaction_tick,
            ),
        )
        while len(self.hypotheses) > self.config.max_partner_hypotheses and ranked:
            victim = ranked.pop(0)
            self.hypotheses.pop(victim.hypothesis_id, None)
            victim.status = HypothesisStatus.INACTIVE.value
            # Provenance preserved (never silently destroyed) in archive, bounded 2x cap.
            self.archived_hypotheses[victim.hypothesis_id] = victim
            if len(self.archived_hypotheses) > self.config.max_partner_hypotheses * 2:
                oldest = min(self.archived_hypotheses.values(), key=lambda h: h.created_tick)
                self.archived_hypotheses.pop(oldest.hypothesis_id, None)

    def reset_for_encounter_boundary(self) -> None:
        """C4 (persist_relationship=False): reset at encounter boundaries and restarts."""
        if self.config.persist_relationship:
            return
        self.hypotheses.clear()
        self.archived_hypotheses.clear()
        self.contingency_cells.clear()
        self._hypothesis_counter = 0

    # --- provenance caps -----------------------------------------------

    def add_evidence_ref(self, hypothesis_id: str, episode_id: str) -> None:
        hyp = self._get_hypothesis(hypothesis_id)
        if episode_id not in hyp.evidence_refs:
            hyp.evidence_refs.append(episode_id)
        cap = self.config.max_active_evidence_refs
        if len(hyp.evidence_refs) > cap:
            hyp.evidence_refs = hyp.evidence_refs[-cap:]

    def add_source_hypothesis(self, hypothesis_id: str, source_hypothesis_id: str) -> None:
        hyp = self._get_hypothesis(hypothesis_id)
        if source_hypothesis_id not in hyp.source_hypothesis_ids:
            hyp.source_hypothesis_ids.append(source_hypothesis_id)
        cap = self.config.max_source_hypothesis_ids
        if len(hyp.source_hypothesis_ids) > cap:
            hyp.source_hypothesis_ids = hyp.source_hypothesis_ids[-cap:]

    def _maybe_detect_partner_swap(
        self,
        best_id: str,
        best_score: float,
        scored: list[tuple[PartnerHypothesis, float]],
        tick: int,
    ) -> str | None:
        """Detect partner swap without merging histories (design §4)."""
        margin = self.config.swap_detect_score_margin
        recency = self.config.swap_recency_ticks
        for hyp, score in scored:
            if hyp.hypothesis_id == best_id:
                continue
            if hyp.status != HypothesisStatus.FAMILIAR.value:
                continue
            if tick - hyp.last_interaction_tick > recency:
                continue
            if best_score - score >= margin:
                return hyp.hypothesis_id
        return None

    def merge_hypotheses(
        self, ids: list[str], *, store: Any = None, tick: int = 0
    ) -> str:
        """Non-destructive merge: archive sources, create superseding hypothesis with links.

        Source contingency cells and evidence remain keyed to archived hypotheses;
        full lineage is recoverable via `source_hypothesis_ids` (bounded) and ledger links.
        """
        if len(ids) < 2:
            raise SocialEngineError("merge_requires_at_least_two_hypotheses")
        unique_ids = list(dict.fromkeys(ids))
        if len(unique_ids) != len(ids):
            raise SocialEngineError("merge_duplicate_source_ids")
        sources: list[PartnerHypothesis] = []
        for hid in unique_ids:
            if hid not in self.hypotheses:
                raise SocialEngineError(f"merge_source_not_active:{hid}")
            sources.append(self.hypotheses[hid])

        merged_id = self._new_hypothesis_id()
        merged_proto: dict[str, list[float]] = {}
        for f in CUE_VECTOR_FIELDS:
            vecs = [s.cue_prototype.get(f) for s in sources if s.cue_prototype.get(f)]
            if not vecs:
                continue
            dim = len(vecs[0])
            merged_proto[f] = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]

        merged = PartnerHypothesis(
            hypothesis_id=merged_id,
            status=HypothesisStatus.UNKNOWN.value,
            recognition_confidence=max(s.recognition_confidence for s in sources),
            cue_prototype=merged_proto,
            encounter_count=sum(s.encounter_count for s in sources),
            familiarity=clamp(max(s.familiarity for s in sources)),
            responsiveness=max(s.responsiveness for s in sources),
            uncertainty=min(s.uncertainty for s in sources),
            last_interaction_tick=max(s.last_interaction_tick for s in sources),
            last_satiation_update_tick=max(s.last_satiation_update_tick for s in sources),
            created_tick=int(tick),
        )
        merged.source_hypothesis_ids = list(unique_ids)
        for src in sources:
            for prior in src.source_hypothesis_ids:
                if prior not in merged.source_hypothesis_ids:
                    merged.source_hypothesis_ids.append(prior)
        cap = self.config.max_source_hypothesis_ids
        if len(merged.source_hypothesis_ids) > cap:
            merged.source_hypothesis_ids = merged.source_hypothesis_ids[-cap:]

        for src in sources:
            src.status = HypothesisStatus.INACTIVE.value
            self.archived_hypotheses[src.hypothesis_id] = src
            self.hypotheses.pop(src.hypothesis_id, None)

        self.hypotheses[merged_id] = merged
        self.metrics["hypothesis_merges"] = int(self.metrics.get("hypothesis_merges", 0)) + 1

        payload = {
            "merged_hypothesis_id": merged_id,
            "source_hypothesis_ids": unique_ids,
            "tick": int(tick),
        }
        if store is not None:
            store.append_event(
                agent_id=self.agent_id,
                event_type="social_hypothesis_merged",
                monotonic_time=float(tick),
                wall_time=float(tick),
                payload=payload,
            )
            for sid in unique_ids:
                store.insert_social_hypothesis_provenance_link(
                    agent_id=self.agent_id,
                    operation="merge",
                    result_hypothesis_id=merged_id,
                    source_hypothesis_id=sid,
                    tick=int(tick),
                )
        else:
            self._emit("social_hypothesis_merged", payload)
        self._prune_hypotheses()
        return merged_id

    def split_hypothesis(
        self,
        hypothesis_id: str,
        evidence_partition: dict[str, str],
        *,
        store: Any = None,
        tick: int = 0,
    ) -> tuple[str, str]:
        """Non-destructive split: archive parent, create children with partitioned evidence."""
        if hypothesis_id not in self.hypotheses:
            raise SocialEngineError(f"split_source_not_active:{hypothesis_id}")
        parent = self.hypotheses[hypothesis_id]
        refs_a = [eid for eid in parent.evidence_refs if evidence_partition.get(eid) == "a"]
        refs_b = [eid for eid in parent.evidence_refs if evidence_partition.get(eid) == "b"]
        unassigned = [eid for eid in parent.evidence_refs if eid not in refs_a + refs_b]
        if unassigned:
            raise SocialEngineError(f"split_incomplete_partition:{unassigned}")

        id_a = self._new_hypothesis_id()
        id_b = self._new_hypothesis_id()
        base = {
            "status": HypothesisStatus.UNKNOWN.value,
            "recognition_confidence": parent.recognition_confidence,
            "cue_prototype": dict(parent.cue_prototype),
            "familiarity": parent.familiarity,
            "responsiveness": parent.responsiveness,
            "reliability_by_context": dict(parent.reliability_by_context),
            "interaction_preference_by_context": dict(parent.interaction_preference_by_context),
            "satiation_anchor": parent.satiation_anchor,
            "uncertainty": parent.uncertainty,
            "last_interaction_tick": parent.last_interaction_tick,
            "last_satiation_update_tick": parent.last_satiation_update_tick,
            "decay_parameters": dict(parent.decay_parameters),
            "created_tick": int(tick),
        }
        child_a = PartnerHypothesis(
            hypothesis_id=id_a, evidence_refs=refs_a, source_hypothesis_ids=[hypothesis_id], **base
        )
        child_b = PartnerHypothesis(
            hypothesis_id=id_b, evidence_refs=refs_b, source_hypothesis_ids=[hypothesis_id], **base
        )

        parent.status = HypothesisStatus.INACTIVE.value
        self.archived_hypotheses[hypothesis_id] = parent
        self.hypotheses.pop(hypothesis_id, None)
        self.hypotheses[id_a] = child_a
        self.hypotheses[id_b] = child_b
        self.metrics["hypothesis_splits"] = int(self.metrics.get("hypothesis_splits", 0)) + 1

        payload = {
            "parent_hypothesis_id": hypothesis_id,
            "child_hypothesis_ids": [id_a, id_b],
            "evidence_partition": dict(evidence_partition),
            "tick": int(tick),
        }
        if store is not None:
            store.append_event(
                agent_id=self.agent_id,
                event_type="social_hypothesis_split",
                monotonic_time=float(tick),
                wall_time=float(tick),
                payload=payload,
            )
            for child_id in (id_a, id_b):
                store.insert_social_hypothesis_provenance_link(
                    agent_id=self.agent_id,
                    operation="split",
                    result_hypothesis_id=child_id,
                    source_hypothesis_id=hypothesis_id,
                    tick=int(tick),
                )
        else:
            self._emit("social_hypothesis_split", payload)
        self._prune_hypotheses()
        return id_a, id_b

    # --- satiation (derived) --------------------------------------------

    def current_satiation(self, hypothesis_id: str, tick: int) -> float:
        hyp = self._get_hypothesis(hypothesis_id)
        if not self.config.satiation_enabled:
            return 0.0
        elapsed = max(0, tick - hyp.last_satiation_update_tick)
        rate = float(hyp.decay_parameters.get("rate", self.config.satiation_decay_per_tick))
        return clamp(hyp.satiation_anchor - rate * elapsed, 0.0, 1.0)

    def update_satiation_anchor(
        self, hypothesis_id: str, tick: int, delta: float | None = None
    ) -> float:
        """Accepted satiation change — anchors the derived curve; emits authoritative event."""
        hyp = self._get_hypothesis(hypothesis_id)
        d = self.config.satiation_rise if delta is None else delta
        new_anchor = clamp(self.current_satiation(hypothesis_id, tick) + d, 0.0, 1.0)
        hyp.satiation_anchor = new_anchor
        hyp.last_satiation_update_tick = tick
        self._emit(
            "social_satiation_anchor_updated",
            {"hypothesis_id": hypothesis_id, "satiation_anchor": new_anchor, "tick": tick},
        )
        return new_anchor

    # --- contingency / derived latency ----------------------------------

    def _cell_key(self, hypothesis_id: str, context: str, signal: str) -> str:
        return f"{hypothesis_id}|{context}|{signal}"

    def record_contingency_sample(
        self,
        hypothesis_id: str,
        context: str,
        signal: str,
        *,
        tick: int,
        latency_ticks: float,
        confidence: float = 0.5,
    ) -> ContingencyCell:
        """Provisional in-memory recorder — see module docstring; Task 5 supplies
        the authoritative atomic pending→episode→contingency commit."""
        key = self._cell_key(hypothesis_id, context, signal)
        cell = self.contingency_cells.get(key)
        if cell is None:
            cell = ContingencyCell(
                hypothesis_id=hypothesis_id,
                context=context,
                signal=signal,
                latency_ema=float(latency_ticks),
                contingent_count=1,
                confidence=clamp(confidence),
                last_updated=tick,
            )
        else:
            prev = cell.latency_ema
            cell.latency_ema = (1 - CONTINGENCY_EMA_ALPHA) * prev + CONTINGENCY_EMA_ALPHA * latency_ticks
            cell.latency_variance = (
                1 - CONTINGENCY_EMA_ALPHA
            ) * cell.latency_variance + CONTINGENCY_EMA_ALPHA * (latency_ticks - prev) ** 2
            cell.contingent_count += 1
            cell.confidence = clamp(0.5 * cell.confidence + 0.5 * confidence)
            cell.last_updated = tick
        self.contingency_cells[key] = cell
        self._bound_contingency_cells()
        return cell

    def _bound_contingency_cells(self) -> None:
        cap = self.config.max_contingency_cells
        if len(self.contingency_cells) <= cap:
            return
        ranked = sorted(
            self.contingency_cells.values(),
            key=lambda c: c.confidence * c.contingent_count,
        )
        while len(self.contingency_cells) > cap and ranked:
            victim = ranked.pop(0)
            self.contingency_cells.pop(self._cell_key(victim.hypothesis_id, victim.context, victim.signal), None)

    def expected_response_latency(self, hypothesis_id: str) -> float | None:
        """DERIVED partner-level latency — weighted mean of contingency-cell EMAs.

        Never a stored field on `PartnerHypothesis`.
        """
        cells = [
            c
            for c in self.contingency_cells.values()
            if c.hypothesis_id == hypothesis_id and c.contingent_count > 0
        ]
        if not cells:
            return None
        weight_sum = sum(c.confidence * c.contingent_count for c in cells)
        if weight_sum <= 0.0:
            return sum(c.latency_ema for c in cells) / len(cells)
        return sum(c.latency_ema * c.confidence * c.contingent_count for c in cells) / weight_sum

    # --- pending interaction lifecycle ----------------------------------

    def _new_pending_id(self) -> str:
        self._pending_counter += 1
        if self.seed is not None:
            return deterministic_id(self.seed, f"pend:{self.agent_id}:{self._pending_counter}")
        return new_id()

    def create_pending(
        self,
        *,
        hypothesis_id: str,
        context: str,
        signal: str,
        execution_id: str,
        signal_tick: int,
        recognition_confidence: float,
        governance_admitted: bool,
        capability_executed: bool,
        store: Any = None,
        tick: int | None = None,
    ) -> PendingInteraction:
        """Open a pending trace — ONLY after a governance-allowed, executed signal.

        A denied or unexecuted signal creates no trace and therefore no partner
        evidence (design §5/§7). Fails closed on unknown hypothesis.

        Ordering is deliberate: the open-pending bound is checked, and the durable
        `social_pending_created` event is written, BEFORE `self.pending` is ever
        mutated. An overflow raises with no side effect; a durable-write failure
        raises with no side effect. Never an orphaned in-memory trace with no
        ledger event.
        """
        if not (governance_admitted and capability_executed):
            raise SocialEngineError("pending_requires_governed_executed_signal")
        self._get_hypothesis(hypothesis_id)  # fail closed if the hypothesis is unknown
        self._ensure_pending_capacity()
        created_tick = int(tick if tick is not None else signal_tick)
        pending = PendingInteraction(
            pending_interaction_id=self._new_pending_id(),
            hypothesis_id_at_signal=hypothesis_id,
            recognition_confidence=float(recognition_confidence),
            context=str(context),
            signal=str(signal),
            execution_id=str(execution_id),
            signal_tick=int(signal_tick),
            response_window=[
                int(self.config.response_window_contingent[0]),
                int(self.config.response_none_timeout),
            ],
            status=PendingStatus.PENDING.value,
            created_tick=created_tick,
        )
        payload = {**pending.to_dict(), "tick": created_tick}
        if store is not None:
            store.append_event(
                agent_id=self.agent_id,
                event_type="social_pending_created",
                monotonic_time=float(created_tick),
                wall_time=float(created_tick),
                payload=payload,
            )
        else:
            self._emit("social_pending_created", payload)
        self.pending[pending.pending_interaction_id] = pending
        self.metrics["pending_created"] = int(self.metrics.get("pending_created", 0)) + 1
        return pending

    def _ensure_pending_capacity(self) -> None:
        """Free room by evicting settled traces (oldest first); raise BEFORE any
        mutation if open (PENDING) traces already fill the bound. Never evicts an
        open trace — those only leave via resolve/expire/interrupt, never silently."""
        cap = self.config.max_pending_interactions
        if len(self.pending) >= cap:
            settled = [
                pid for pid, p in self.pending.items() if p.status != PendingStatus.PENDING.value
            ]
            settled.sort(key=lambda pid: self.pending[pid].created_tick)
            while len(self.pending) >= cap and settled:
                self.pending.pop(settled.pop(0), None)
        open_count = sum(1 for p in self.pending.values() if p.status == PendingStatus.PENDING.value)
        if open_count >= cap:
            raise SocialEngineError("too_many_open_pending_interactions")

    # --- contingency classification -------------------------------------

    def classify_response(
        self,
        *,
        response_latency: float | None,
        recognition_confidence: float = 1.0,
        external_cause: bool = False,
        overlapping_inseparable: bool = False,
        contested: bool = False,
    ) -> ResponseClass:
        """Classify a response with precedence EXTERNAL→AMBIGUOUS→CONTINGENT→
        DELAYED→COINCIDENTAL→NONE using the frozen timing windows.

        Overlapping inseparable bids and ambiguous/contested recognition produce no
        reliability evidence (→ AMBIGUOUS). Timing windows are preregistered in
        experiments/d006/thresholds.json.
        """
        if external_cause:
            return ResponseClass.EXTERNAL
        if (
            contested
            or overlapping_inseparable
            or recognition_confidence < self.config.contingency_min_recognition_confidence
        ):
            return ResponseClass.AMBIGUOUS
        if response_latency is None:
            return ResponseClass.NONE
        lat = float(response_latency)
        if lat > self.config.response_none_timeout:
            return ResponseClass.NONE
        lo_c, hi_c = self.config.response_window_contingent
        lo_d, hi_d = self.config.response_window_delayed
        if lo_c <= lat <= hi_c:
            return ResponseClass.CONTINGENT
        if lo_d <= lat <= hi_d:
            return ResponseClass.DELAYED
        # Response present but temporally implausible (<=0, or past DELAYED yet within
        # timeout): a coincidence, not causal evidence.
        return ResponseClass.COINCIDENTAL

    def _has_inseparable_overlap(self, pending: PendingInteraction, response_tick: int) -> bool:
        """Another open bid for the same context+signal whose window also covers the
        response — the response cannot be causally attributed to a single bid."""
        for other in self.pending.values():
            if other.pending_interaction_id == pending.pending_interaction_id:
                continue
            if other.status != PendingStatus.PENDING.value:
                continue
            if other.context != pending.context or other.signal != pending.signal:
                continue
            o_lo, o_timeout = other.response_window
            if other.signal_tick + o_lo <= response_tick <= other.signal_tick + o_timeout:
                return True
        return False

    # --- outcome observation + atomic commit ----------------------------

    def observe_outcome(
        self,
        pending_id: str,
        *,
        response_tick: int,
        response_observed: bool,
        store: Any,
        memory: Any,
        external_cause: bool = False,
        occurred_at: float | None = None,
        crash_after_stage: int | None = None,
    ) -> ResponseClass:
        """Classify then atomically commit a pending interaction's outcome."""
        pending = self.pending.get(pending_id)
        if pending is None:
            raise SocialEngineError(f"pending_missing:{pending_id}")
        if pending.status != PendingStatus.PENDING.value:
            raise SocialEngineError(f"pending_not_open:{pending_id}:{pending.status}")
        hyp = self._get_hypothesis(pending.hypothesis_id_at_signal)
        contested = hyp.status == HypothesisStatus.CONTESTED.value
        overlapping = self._has_inseparable_overlap(pending, response_tick)
        latency = (int(response_tick) - pending.signal_tick) if response_observed else None
        classification = self.classify_response(
            response_latency=latency,
            recognition_confidence=pending.recognition_confidence,
            external_cause=external_cause,
            overlapping_inseparable=overlapping,
            contested=contested,
        )
        self.resolve_pending(
            pending_id,
            classification=classification,
            response_latency=latency,
            response_tick=response_tick,
            store=store,
            memory=memory,
            occurred_at=occurred_at,
            crash_after_stage=crash_after_stage,
        )
        return classification

    def resolve_pending(
        self,
        pending_id: str,
        *,
        classification: ResponseClass | str,
        response_latency: float | None,
        response_tick: int,
        store: Any,
        memory: Any,
        occurred_at: float | None = None,
        crash_after_stage: int | None = None,
        lifecycle_event: str = "social_pending_resolved",
    ) -> None:
        """Finalize an outcome in ONE SQLite transaction (design §1 atomic commit).

        Stages: finalize immutable episode → append episode event → update contingency
        evidence (+ links) → revise reliability → append social authority events. On
        crash injection everything rolls back; in-memory model changes apply only after
        COMMIT. A pending can settle exactly once (no double-evidence).
        """
        pending = self.pending.get(pending_id)
        if pending is None:
            raise SocialEngineError(f"pending_missing:{pending_id}")
        if pending.status != PendingStatus.PENDING.value:
            raise SocialEngineError(f"pending_not_open:{pending_id}:{pending.status}")
        hyp = self._get_hypothesis(pending.hypothesis_id_at_signal)
        cls_val = (
            classification.value if isinstance(classification, ResponseClass) else str(classification)
        )
        context, signal = pending.context, pending.signal
        tick = int(response_tick)
        occ = float(occurred_at if occurred_at is not None else tick)

        verified = {
            "success": cls_val == ResponseClass.CONTINGENT.value,
            "classification": cls_val,
        }
        ep = memory.finalize_social_episode(
            episode_key=f"social|{pending_id}",
            tick=tick,
            occurred_at=occ,
            context={
                "entity_kind": "partner",
                "hypothesis_id": hyp.hypothesis_id,
                "social_context": context,
                "signal": signal,
                "classification": cls_val,
                "rule_tag": "social",
            },
            observations=[],
            internal_state={},
            goal=None,
            action=signal,
            verified_outcome=verified,
            source_event_ids=[pending.execution_id],
        )
        episode_id = ep.episode_id

        cell_after, relation = self._preview_contingency(
            hyp, context, signal, cls_val, response_latency, episode_id, tick
        )
        new_reliability, reliability_changed = self._preview_reliability(
            hyp, context, cls_val, cell_after
        )

        def stage_finalize_episode() -> None:
            store.append_event(
                agent_id=self.agent_id,
                event_type="social_episode_finalized",
                monotonic_time=float(tick),
                wall_time=float(tick),
                payload={"episode": ep.to_dict(), "pending_interaction_id": pending_id},
            )

        def stage_episode_event() -> None:
            store.append_event(
                agent_id=self.agent_id,
                event_type="social_episode_outcome",
                monotonic_time=float(tick),
                wall_time=float(tick),
                payload={
                    "episode_id": episode_id,
                    "pending_interaction_id": pending_id,
                    "hypothesis_id": hyp.hypothesis_id,
                    "context": context,
                    "signal": signal,
                    "classification": cls_val,
                },
            )

        def stage_evidence_links() -> None:
            if relation is not None:
                store.insert_social_evidence_link(
                    agent_id=self.agent_id,
                    hypothesis_id=hyp.hypothesis_id,
                    context=context,
                    signal=signal,
                    episode_id=episode_id,
                    pending_interaction_id=pending_id,
                    classification=cls_val,
                    relation=relation,
                    tick=tick,
                )

        def stage_revise_reliability() -> None:
            if reliability_changed:
                store.append_event(
                    agent_id=self.agent_id,
                    event_type="social_reliability_revised",
                    monotonic_time=float(tick),
                    wall_time=float(tick),
                    payload={
                        "hypothesis_id": hyp.hypothesis_id,
                        "context": context,
                        "reliability": new_reliability,
                        "tick": tick,
                    },
                )

        def stage_authority_events() -> None:
            store.append_event(
                agent_id=self.agent_id,
                event_type=lifecycle_event,
                monotonic_time=float(tick),
                wall_time=float(tick),
                payload={
                    "pending_interaction_id": pending_id,
                    "classification": cls_val,
                    "episode_id": episode_id,
                    "tick": tick,
                },
            )
            store.append_event(
                agent_id=self.agent_id,
                event_type="social_contingency_updated",
                monotonic_time=float(tick),
                wall_time=float(tick),
                payload={
                    "hypothesis_id": hyp.hypothesis_id,
                    "context": context,
                    "signal": signal,
                    "classification": cls_val,
                    "episode_id": episode_id,
                    "tick": tick,
                },
            )

        def on_commit() -> None:
            memory.attach_episode(ep)
            key = self._cell_key(hyp.hypothesis_id, context, signal)
            self.contingency_cells[key] = cell_after
            self._bound_contingency_cells()
            if reliability_changed:
                hyp.reliability_by_context[context] = new_reliability
                self.metrics["reliability_revisions"] = (
                    int(self.metrics.get("reliability_revisions", 0)) + 1
                )
            if relation == "support":
                self.add_evidence_ref(hyp.hypothesis_id, episode_id)
            pending.status = self._status_for_event(lifecycle_event)
            hyp.last_interaction_tick = tick
            self.metrics["pending_resolved"] = int(self.metrics.get("pending_resolved", 0)) + 1
            self.metrics["contingency_updates"] = (
                int(self.metrics.get("contingency_updates", 0)) + 1
            )

        store.atomic_social_outcome(
            [
                stage_finalize_episode,
                stage_episode_event,
                stage_evidence_links,
                stage_revise_reliability,
                stage_authority_events,
            ],
            on_commit=on_commit,
            crash_after_stage=crash_after_stage,
        )

    @staticmethod
    def _status_for_event(lifecycle_event: str) -> str:
        return {
            "social_pending_resolved": PendingStatus.RESOLVED.value,
            "social_pending_expired": PendingStatus.EXPIRED.value,
            "social_pending_interrupted": PendingStatus.INTERRUPTED.value,
        }.get(lifecycle_event, PendingStatus.RESOLVED.value)

    def _preview_contingency(
        self,
        hyp: PartnerHypothesis,
        context: str,
        signal: str,
        cls_val: str,
        latency: float | None,
        episode_id: str,
        tick: int,
    ) -> tuple[ContingencyCell, str | None]:
        """Compute the post-outcome cell on a COPY (applied only after commit)."""
        key = self._cell_key(hyp.hypothesis_id, context, signal)
        existing = self.contingency_cells.get(key)
        cell = (
            ContingencyCell.from_dict(existing.to_dict())
            if existing is not None
            else ContingencyCell(hypothesis_id=hyp.hypothesis_id, context=context, signal=signal)
        )
        relation: str | None = None
        if cls_val == ResponseClass.CONTINGENT.value:
            cell.contingent_count += 1
            self._update_cell_latency(cell, latency)
            cell.confidence = clamp(cell.confidence + 0.15)
            self._bounded_append(
                cell.supporting_episode_ids, episode_id, self.config.max_active_supporting_episodes
            )
            relation = "support"
        elif cls_val == ResponseClass.DELAYED.value:
            cell.delayed_count += 1
            self._update_cell_latency(cell, latency)
            cell.confidence = clamp(cell.confidence + 0.05)
            self._bounded_append(
                cell.supporting_episode_ids, episode_id, self.config.max_active_supporting_episodes
            )
            relation = "support"
        elif cls_val == ResponseClass.NONE.value:
            cell.none_count += 1
            cell.confidence = clamp(cell.confidence - 0.05)
            self._bounded_append(
                cell.contradicting_episode_ids,
                episode_id,
                self.config.max_active_contradicting_episodes,
            )
            relation = "contradict"
        elif cls_val == ResponseClass.COINCIDENTAL.value:
            cell.coincidental_count += 1
        elif cls_val == ResponseClass.AMBIGUOUS.value:
            cell.ambiguous_count += 1
        elif cls_val == ResponseClass.EXTERNAL.value:
            cell.external_count += 1
        cell.last_updated = tick
        return cell, relation

    def _update_cell_latency(self, cell: ContingencyCell, latency: float | None) -> None:
        if latency is None:
            return
        lat = float(latency)
        if cell.contingent_count + cell.delayed_count <= 1:
            cell.latency_ema = lat
            cell.latency_variance = 0.0
            return
        prev = cell.latency_ema
        cell.latency_ema = (1 - CONTINGENCY_EMA_ALPHA) * prev + CONTINGENCY_EMA_ALPHA * lat
        cell.latency_variance = (
            1 - CONTINGENCY_EMA_ALPHA
        ) * cell.latency_variance + CONTINGENCY_EMA_ALPHA * (lat - prev) ** 2

    @staticmethod
    def _bounded_append(seq: list[str], value: str, cap: int) -> None:
        if value not in seq:
            seq.append(value)
        if len(seq) > cap:
            del seq[: len(seq) - cap]

    def _preview_reliability(
        self,
        hyp: PartnerHypothesis,
        context: str,
        cls_val: str,
        cell: ContingencyCell | None = None,
    ) -> tuple[float, bool]:
        """Reliability rises from contingent responses; one anomaly weakens slightly;
        repeated contradiction revises down; recovery after failures revises up."""
        prev = hyp.reliability_by_context.get(context, 0.0)
        if cls_val == ResponseClass.CONTINGENT.value:
            gain = self.config.reliability_gain
            if prev < 0.5 and cell is not None and cell.none_count > 0:
                gain *= 1.25  # ponytail: modest recovery boost after prior failures
            new = clamp(prev + gain * (1.0 - prev))
        elif cls_val == ResponseClass.DELAYED.value:
            new = clamp(prev + self.config.reliability_gain * 0.3 * (1.0 - prev))
        elif cls_val == ResponseClass.NONE.value:
            if prev <= 0.0:
                return prev, False
            none_count = cell.none_count if cell is not None else 1
            if none_count <= 1:
                new = clamp(prev - self.config.reliability_anomaly_weaken)
            else:
                new = clamp(prev - self.config.reliability_loss * prev)
        else:
            return prev, False
        if abs(new - prev) < 1e-12:
            return prev, False
        return new, True

    # --- pending recovery / replay --------------------------------------

    def resume_pending(self, *, store: Any, now_tick: int) -> dict[str, list[str]]:
        """After restart, resume open traces still inside their window; deterministically
        expire elapsed ones; interrupt ones whose durable timing state is corrupted or
        incomplete (design §2). Never silently drops; never double-settles.

        Same ordering discipline as `create_pending`: the durable event is written
        BEFORE the in-memory status mutation, so a durable-write failure leaves the
        trace PENDING (retryable) rather than orphaned in a settled state with no
        ledger event.
        """
        resumed: list[str] = []
        expired: list[str] = []
        interrupted: list[str] = []
        for pid, pending in list(self.pending.items()):
            if pending.status != PendingStatus.PENDING.value:
                continue
            window = pending.response_window
            if not isinstance(window, (list, tuple)) or len(window) != 2 or window[1] is None:
                self.interrupt_pending(pid, "corrupted_timing_state", store=store, tick=now_tick)
                interrupted.append(pid)
                continue
            _lo, timeout = window
            if now_tick - pending.signal_tick > timeout:
                if store is not None:
                    store.append_event(
                        agent_id=self.agent_id,
                        event_type="social_pending_expired",
                        monotonic_time=float(now_tick),
                        wall_time=float(now_tick),
                        payload={
                            "pending_interaction_id": pid,
                            "signal_tick": pending.signal_tick,
                            "now_tick": int(now_tick),
                        },
                    )
                pending.status = PendingStatus.EXPIRED.value
                self.metrics["pending_expired"] = int(self.metrics.get("pending_expired", 0)) + 1
                expired.append(pid)
            else:
                resumed.append(pid)
        return {"resumed": resumed, "expired": expired, "interrupted": interrupted}

    def interrupt_pending(
        self, pending_id: str, reason: str, *, store: Any = None, tick: int | None = None
    ) -> PendingInteraction:
        """Explicitly interrupt an open pending trace — e.g. recognition becomes
        CONTESTED mid-window, or resume finds corrupted/incomplete durable timing.
        Fails closed if the trace is missing or already settled. Durable event is
        written before the in-memory mutation (same discipline as `create_pending`)."""
        pending = self.pending.get(pending_id)
        if pending is None:
            raise SocialEngineError(f"pending_missing:{pending_id}")
        if pending.status != PendingStatus.PENDING.value:
            raise SocialEngineError(f"pending_not_open:{pending_id}:{pending.status}")
        interrupt_tick = int(tick if tick is not None else pending.signal_tick)
        payload = {
            "pending_interaction_id": pending_id,
            "reason": str(reason),
            "signal_tick": pending.signal_tick,
            "tick": interrupt_tick,
        }
        if store is not None:
            store.append_event(
                agent_id=self.agent_id,
                event_type="social_pending_interrupted",
                monotonic_time=float(interrupt_tick),
                wall_time=float(interrupt_tick),
                payload=payload,
            )
        else:
            self._emit("social_pending_interrupted", payload)
        pending.status = PendingStatus.INTERRUPTED.value
        self.metrics["pending_interrupted"] = int(self.metrics.get("pending_interrupted", 0)) + 1
        return pending

    @staticmethod
    def reconstruct_pending(events: list[dict[str, Any]]) -> dict[str, PendingInteraction]:
        """Rebuild unresolved pending traces from the event ledger, failing closed if a
        settlement event references a pending with no authoritative created event."""
        pending: dict[str, PendingInteraction] = {}
        settled = {
            "social_pending_resolved",
            "social_pending_expired",
            "social_pending_interrupted",
        }
        for ev in events:
            et = ev.get("event_type")
            payload = ev.get("payload") or {}
            pid = payload.get("pending_interaction_id")
            if et == "social_pending_created":
                pending[str(pid)] = PendingInteraction.from_dict(payload)
            elif et in settled:
                if pid not in pending:
                    raise SocialEngineError(
                        f"missing_authoritative_social_pending_created:{pid}"
                    )
                pending.pop(pid, None)
        return pending

    # --- persistence -----------------------------------------------------

    def counts_bounded(self) -> bool:
        return (
            len(self.hypotheses) <= self.config.max_partner_hypotheses
            and len(self.contingency_cells) <= self.config.max_contingency_cells
            and all(
                len(h.evidence_refs) <= self.config.max_active_evidence_refs
                for h in self.hypotheses.values()
            )
            and all(
                len(h.source_hypothesis_ids) <= self.config.max_source_hypothesis_ids
                for h in self.hypotheses.values()
            )
        )

    def to_state(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "seed": self.seed,
            "hypotheses": {k: v.to_dict() for k, v in self.hypotheses.items()},
            "archived_hypotheses": {k: v.to_dict() for k, v in self.archived_hypotheses.items()},
            "contingency_cells": {k: v.to_dict() for k, v in self.contingency_cells.items()},
            "pending": {k: v.to_dict() for k, v in self.pending.items()},
            "hypothesis_counter": self._hypothesis_counter,
            "pending_counter": self._pending_counter,
            "metrics": dict(self.metrics),
            "config": asdict(self.config),
        }

    @classmethod
    def from_state(
        cls,
        state: dict[str, Any],
        *,
        config: SocialConfig | None = None,
        emit_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> SocialEngine:
        cfg = config or SocialConfig(**(state.get("config") or {}))
        eng = cls(
            agent_id=str(state["agent_id"]),
            config=cfg,
            seed=state.get("seed"),
            emit_event=emit_event,
        )
        if cfg.persist_relationship:
            eng.hypotheses = {
                k: PartnerHypothesis.from_dict(v) for k, v in (state.get("hypotheses") or {}).items()
            }
            eng.archived_hypotheses = {
                k: PartnerHypothesis.from_dict(v)
                for k, v in (state.get("archived_hypotheses") or {}).items()
            }
            eng.contingency_cells = {
                k: ContingencyCell.from_dict(v)
                for k, v in (state.get("contingency_cells") or {}).items()
            }
            eng.pending = {
                k: PendingInteraction.from_dict(v) for k, v in (state.get("pending") or {}).items()
            }
            eng._hypothesis_counter = int(state.get("hypothesis_counter", 0))
            eng._pending_counter = int(state.get("pending_counter", 0))
        # else: C4 fails closed to a fresh relationship state on restart (design §6).
        eng.metrics = dict(state.get("metrics") or {})
        eng._bounded_initialized = True
        return eng
