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


class HypothesisStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    FAMILIAR = "FAMILIAR"
    CONTESTED = "CONTESTED"
    INACTIVE = "INACTIVE"


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
    """Minimal (hypothesis, context, signal) latency cell — see module docstring."""

    hypothesis_id: str
    context: str
    signal: str
    latency_ema: float = 0.0
    latency_variance: float = 0.0
    contingent_count: int = 0
    confidence: float = 0.0
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
            confidence=float(d.get("confidence", 0.0)),
            last_updated=int(d.get("last_updated", 0)),
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
    config: SocialConfig = field(default_factory=SocialConfig)
    seed: int | None = None
    emit_event: Callable[[str, dict[str, Any]], None] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    _hypothesis_counter: int = 0
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

    def recognize(self, cues: list[dict[str, Any]], tick: int) -> RecognitionResult:
        """Match/update hypotheses from noisy partner cues. No hidden partner_id."""
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
            "hypothesis_counter": self._hypothesis_counter,
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
            eng._hypothesis_counter = int(state.get("hypothesis_counter", 0))
        # else: C4 fails closed to a fresh relationship state on restart (design §6).
        eng.metrics = dict(state.get("metrics") or {})
        eng._bounded_initialized = True
        return eng
