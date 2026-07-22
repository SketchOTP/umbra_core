"""D-005 selective episodic memory and offline consolidation.

Episodes are immutable lived evidence. Consolidation restructures experience
into semantic beliefs and procedural knowledge during quiescence only.
Replay competes by salience/relevance/uncertainty; memory never grants authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from umbra_core.util import BoundedRing, SeededRNG, clamp, new_id, sha256_hex


MAX_WORKING = 32
MAX_ACTIVE_EPISODIC = 64
MAX_ARCHIVED_EPISODIC = 256
MAX_SEMANTIC = 128
MAX_PROCEDURAL = 64
MAX_ROUTINE_SUPPORTING_EPISODES = 24
MAX_CORRECTIONS = 128
MAX_REPLAY_QUEUE = 48
MAX_REPLAY_PER_CYCLE = 16
MAX_CONSOLIDATION_STEPS = 8
MAX_BELIEF_UPDATES = 8
MAX_PROCEDURAL_UPDATES = 8
ENCODING_SCORE_THRESHOLD = 0.35
LOW_VALUE_SALIENCE = 0.28
REPLAY_SATURATION = 4  # repeats before priority saturates
SEMANTIC_MIN_INDEPENDENT = 2
BELIEF_DECAY = 0.004
PROCEDURAL_DECAY = 0.003
WORKING_TTL = 24

PROTECTED_KINDS = frozenset(
    {
        "constitutional_identity",
        "lifecycle",
        "governance",
        "capability_grant",
        "capability_revoke",
        "memory_correction",
        "body_model_supersession",
        "scientific_evidence",
        "safety_critical",
    }
)


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONTESTED = "CONTESTED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class RetrievalKind(str, Enum):
    OBSERVED_EPISODE = "OBSERVED_EPISODE"
    DERIVED_BELIEF = "DERIVED_BELIEF"
    PROCEDURAL_KNOWLEDGE = "PROCEDURAL_KNOWLEDGE"
    PREDICTION = "PREDICTION"


def _stable_id(kind: str, key: str) -> str:
    h = sha256_hex(f"umbra:mem:{kind}:{key}")
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _freeze(obj: Any) -> Any:
    """Deep-freeze JSON-like structures for immutability checks."""
    if isinstance(obj, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(_freeze(v) for v in obj)
    return obj


@dataclass(frozen=True)
class Episode:
    """Immutable episodic record — corrections create linked new records."""

    episode_id: str
    agent_id: str
    occurred_at: float
    context: tuple[tuple[str, Any], ...]
    observations: tuple[Any, ...]
    internal_state: tuple[tuple[str, Any], ...]
    goal: str | None
    action: str | None
    verified_outcome: tuple[tuple[str, Any], ...] | None
    prediction_error: float
    salience: float
    novelty: float
    goal_relevance: float
    physiological_relevance: float
    confidence: float
    causal_parent_ids: tuple[str, ...]
    body_binding_id: str | None
    source_event_ids: tuple[str, ...]
    tick: int = 0
    protected: bool = False
    protect_kind: str | None = None
    correction_of: str | None = None
    fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "agent_id": self.agent_id,
            "occurred_at": self.occurred_at,
            "context": dict(self.context),
            "observations": list(self.observations),
            "internal_state": dict(self.internal_state),
            "goal": self.goal,
            "action": self.action,
            "verified_outcome": dict(self.verified_outcome) if self.verified_outcome else None,
            "prediction_error": self.prediction_error,
            "salience": self.salience,
            "novelty": self.novelty,
            "goal_relevance": self.goal_relevance,
            "physiological_relevance": self.physiological_relevance,
            "confidence": self.confidence,
            "causal_parent_ids": list(self.causal_parent_ids),
            "body_binding_id": self.body_binding_id,
            "source_event_ids": list(self.source_event_ids),
            "tick": self.tick,
            "protected": self.protected,
            "protect_kind": self.protect_kind,
            "correction_of": self.correction_of,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Episode:
        vo = d.get("verified_outcome")
        return cls(
            episode_id=str(d["episode_id"]),
            agent_id=str(d["agent_id"]),
            occurred_at=float(d["occurred_at"]),
            context=tuple(sorted((str(k), v) for k, v in (d.get("context") or {}).items())),
            observations=tuple(d.get("observations") or ()),
            internal_state=tuple(
                sorted((str(k), v) for k, v in (d.get("internal_state") or {}).items())
            ),
            goal=d.get("goal"),
            action=d.get("action"),
            verified_outcome=tuple(sorted((str(k), v) for k, v in vo.items())) if vo else None,
            prediction_error=float(d.get("prediction_error", 0.0)),
            salience=float(d.get("salience", 0.0)),
            novelty=float(d.get("novelty", 0.0)),
            goal_relevance=float(d.get("goal_relevance", 0.0)),
            physiological_relevance=float(d.get("physiological_relevance", 0.0)),
            confidence=float(d.get("confidence", 0.5)),
            causal_parent_ids=tuple(d.get("causal_parent_ids") or ()),
            body_binding_id=d.get("body_binding_id"),
            source_event_ids=tuple(d.get("source_event_ids") or ()),
            tick=int(d.get("tick", 0)),
            protected=bool(d.get("protected", False)),
            protect_kind=d.get("protect_kind"),
            correction_of=d.get("correction_of"),
            fingerprint=str(d.get("fingerprint", "")),
        )


@dataclass
class WorkingItem:
    item_id: str
    content: dict[str, Any]
    created_tick: int
    ttl: int = WORKING_TTL
    salience: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkingItem:
        return cls(
            item_id=str(d["item_id"]),
            content=dict(d.get("content") or {}),
            created_tick=int(d.get("created_tick", 0)),
            ttl=int(d.get("ttl", WORKING_TTL)),
            salience=float(d.get("salience", 0.0)),
        )


@dataclass
class SemanticBelief:
    belief_id: str
    proposition: str
    confidence: float
    supporting_episode_ids: list[str]
    contradicting_episode_ids: list[str]
    status: str
    supersedes: str | None = None
    independent_support_keys: list[str] = field(default_factory=list)
    last_updated_tick: int = 0
    provenance_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SemanticBelief:
        return cls(
            belief_id=str(d["belief_id"]),
            proposition=str(d["proposition"]),
            confidence=float(d.get("confidence", 0.0)),
            supporting_episode_ids=list(d.get("supporting_episode_ids") or []),
            contradicting_episode_ids=list(d.get("contradicting_episode_ids") or []),
            status=str(d.get("status", MemoryStatus.ACTIVE.value)),
            supersedes=d.get("supersedes"),
            independent_support_keys=list(d.get("independent_support_keys") or []),
            last_updated_tick=int(d.get("last_updated_tick", 0)),
            provenance_required=bool(d.get("provenance_required", True)),
        )


@dataclass
class SocialRoutineSpec:
    """Partner-scoped D-005 procedural routine — persisted by MemoryEngine only."""

    partner_hypothesis: str
    context: str
    signal: str
    soft_proposals: list[str]
    supporting_episode_ids: list[str]
    interrupt_conditions: list[str] = field(
        default_factory=lambda: [
            "partner_ambiguous",
            "satiation_high",
            "physiology_critical",
        ]
    )
    satiation_constraints: dict[str, float] = field(
        default_factory=lambda: {"max_satiation": 0.85}
    )
    body_requirements: dict[str, float] = field(
        default_factory=lambda: {"min_body_compatibility": 0.35}
    )
    success_conditions: dict[str, Any] = field(default_factory=dict)
    authored: bool = False  # C8 scripted FSM — never learned development


@dataclass
class ProceduralMemory:
    skill_id: str
    applicability: dict[str, Any]
    body_compatibility: float
    attempts: int
    success_count: int
    failure_count: int
    confidence: float
    source_episode_ids: list[str]
    status: str = MemoryStatus.ACTIVE.value
    last_updated_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProceduralMemory:
        return cls(
            skill_id=str(d["skill_id"]),
            applicability=dict(d.get("applicability") or {}),
            body_compatibility=float(d.get("body_compatibility", 1.0)),
            attempts=int(d.get("attempts", 0)),
            success_count=int(d.get("success_count", 0)),
            failure_count=int(d.get("failure_count", 0)),
            confidence=float(d.get("confidence", 0.0)),
            source_episode_ids=list(d.get("source_episode_ids") or []),
            status=str(d.get("status", MemoryStatus.ACTIVE.value)),
            last_updated_tick=int(d.get("last_updated_tick", 0)),
        )


@dataclass
class RetrievalResult:
    kind: str
    item_id: str
    score: float
    content: dict[str, Any]
    provenance: list[str]
    is_authority: bool = False  # always False — retrieval is never executable authority
    is_verified_fact: bool = False  # never auto-true

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryConfig:
    """Ablation switches for D-005 conditions C0–C9."""

    enabled: bool = True
    episodic_enabled: bool = True  # C1 off
    consolidation_enabled: bool = True  # C2 off
    store_every_event: bool = False  # C3
    replay_mode: str = "priority"  # priority|random|salience_only
    contradiction_handling: bool = True  # C6 off
    forgetting_enabled: bool = True  # C7 off
    retrieval_mode: str = "ranked"  # ranked|random
    require_belief_provenance: bool = True  # C9 off
    max_working: int = MAX_WORKING
    max_active_episodic: int = MAX_ACTIVE_EPISODIC
    max_archived: int = MAX_ARCHIVED_EPISODIC
    max_semantic: int = MAX_SEMANTIC
    max_procedural: int = MAX_PROCEDURAL
    max_replay_per_cycle: int = MAX_REPLAY_PER_CYCLE
    max_consolidation_steps: int = MAX_CONSOLIDATION_STEPS
    max_belief_updates: int = MAX_BELIEF_UPDATES
    max_procedural_updates: int = MAX_PROCEDURAL_UPDATES


def condition_to_memory_config(condition: str) -> MemoryConfig:
    c = MemoryConfig()
    if condition == "C0":
        return c
    if condition == "C1":
        c.episodic_enabled = False
        return c
    if condition == "C2":
        c.consolidation_enabled = False
        return c
    if condition == "C3":
        c.store_every_event = True
        return c
    if condition == "C4":
        c.replay_mode = "random"
        return c
    if condition == "C5":
        c.replay_mode = "salience_only"
        return c
    if condition == "C6":
        c.contradiction_handling = False
        return c
    if condition == "C7":
        c.forgetting_enabled = False
        return c
    if condition == "C8":
        c.retrieval_mode = "random"
        return c
    if condition == "C9":
        c.require_belief_provenance = False
        return c
    return c


@dataclass
class MemoryEngine:
    """Bounded selective memory + offline consolidation."""

    agent_id: str
    working: list[WorkingItem] = field(default_factory=list)
    episodes: dict[str, Episode] = field(default_factory=dict)
    archived: dict[str, Episode] = field(default_factory=dict)
    corrections: list[str] = field(default_factory=list)  # correction episode ids
    beliefs: dict[str, SemanticBelief] = field(default_factory=dict)
    superseded_beliefs: list[SemanticBelief] = field(default_factory=list)
    procedural: dict[str, ProceduralMemory] = field(default_factory=dict)
    config: MemoryConfig = field(default_factory=MemoryConfig)
    seed: int | None = None
    replay_counts: dict[str, int] = field(default_factory=dict)
    pattern_counts: dict[str, int] = field(default_factory=dict)
    encoding_fingerprint_seen: dict[str, int] = field(default_factory=dict)
    last_consolidation_tick: int = -10_000
    _bounded_initialized: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        agent_id: str,
        *,
        config: MemoryConfig | None = None,
        seed: int | None = None,
    ) -> MemoryEngine:
        eng = cls(agent_id=agent_id, config=config or MemoryConfig(), seed=seed)
        eng.initialize_bounded_collections()
        eng.metrics = {
            "candidates_seen": 0,
            "episodes_encoded": 0,
            "episodes_rejected": 0,
            "consolidations": 0,
            "replay_items": 0,
            "belief_updates": 0,
            "procedural_updates": 0,
            "archived": 0,
            "corrections": 0,
            "retrievals": 0,
            "last_tick": 0,
            "prediction_hits": 0,
            "prediction_total": 0,
            "goal_success_aided": 0,
            "false_beliefs": 0,
            "consolidation_cost": 0,
            "replay_diversity": 0.0,
        }
        return eng

    def initialize_bounded_collections(self) -> None:
        if self._bounded_initialized:
            return
        self._bounded_initialized = True

    # --- encoding ---------------------------------------------------------

    def _event_fingerprint(
        self,
        *,
        action: str | None,
        goal: str | None,
        context: dict[str, Any],
        outcome_success: bool | None,
    ) -> str:
        ctx_key = "|".join(f"{k}={context.get(k)}" for k in sorted(context) if k in (
            "entity_kind", "affordance", "cell", "rule_tag",
        ))
        return sha256_hex(f"{action}|{goal}|{ctx_key}|{outcome_success}")[:24]

    def encoding_score(
        self,
        *,
        prediction_error: float,
        physiological_delta: float,
        goal_outcome: float,  # 1 success, -1 fail, 0 none
        novelty: float,
        skill_learning_value: float,
        pattern_relevance: float,
        body_change: float,
        fingerprint: str,
    ) -> float:
        """Deterministic bounded encoding score. Auditable weights."""
        if self.config.store_every_event:
            return 1.0
        repeats = self.encoding_fingerprint_seen.get(fingerprint, 0)
        # Low-value repetition satiates encoding
        satiation = clamp(1.0 - 0.15 * repeats, 0.05, 1.0)
        raw = (
            0.22 * clamp(prediction_error)
            + 0.18 * clamp(abs(physiological_delta))
            + 0.16 * clamp(abs(goal_outcome))
            + 0.14 * clamp(novelty)
            + 0.12 * clamp(skill_learning_value)
            + 0.10 * clamp(pattern_relevance)
            + 0.08 * clamp(body_change)
        )
        return clamp(raw * satiation)

    def consider_event(
        self,
        *,
        tick: int,
        occurred_at: float,
        context: dict[str, Any],
        observations: list[Any],
        internal_state: dict[str, Any],
        goal: str | None,
        action: str | None,
        verified_outcome: dict[str, Any] | None,
        prediction_error: float,
        physiological_delta: float = 0.0,
        novelty: float | None = None,
        skill_learning_value: float = 0.0,
        body_change: float = 0.0,
        body_binding_id: str | None = None,
        source_event_ids: list[str] | None = None,
        causal_parent_ids: list[str] | None = None,
        protected: bool = False,
        protect_kind: str | None = None,
        force: bool = False,
    ) -> Episode | None:
        """Selectively encode an experience as an immutable episode."""
        self.metrics["candidates_seen"] = int(self.metrics.get("candidates_seen", 0)) + 1
        self.metrics["last_tick"] = tick

        # Working memory always sees a compact summary (bounded, expires)
        success = None
        if verified_outcome is not None:
            success = bool(verified_outcome.get("success"))
        fp = self._event_fingerprint(
            action=action, goal=goal, context=context, outcome_success=success
        )
        salience_est = clamp(
            0.4 * prediction_error
            + 0.3 * abs(physiological_delta)
            + 0.3 * (1.0 if success is False else (0.7 if success else 0.2))
        )
        self._push_working(
            WorkingItem(
                item_id=new_id() if self.seed is None else _stable_id("wm", f"{self.agent_id}|{tick}|{fp}"),
                content={
                    "action": action,
                    "goal": goal,
                    "success": success,
                    "prediction_error": prediction_error,
                    "fingerprint": fp,
                },
                created_tick=tick,
                salience=salience_est,
            )
        )

        if not self.config.enabled or not self.config.episodic_enabled:
            self.metrics["episodes_rejected"] = int(self.metrics.get("episodes_rejected", 0)) + 1
            return None

        # Generated / invented events cannot become episodes
        if context.get("generated") or context.get("invented") or context.get("llm_summary"):
            self.metrics["episodes_rejected"] = int(self.metrics.get("episodes_rejected", 0)) + 1
            return None

        pattern_key = f"{action}|{context.get('entity_kind')}|{context.get('affordance')}"
        pattern_n = self.pattern_counts.get(pattern_key, 0)
        pattern_relevance = clamp(0.15 + 0.08 * min(pattern_n, 6)) if pattern_n >= 1 else 0.05
        nov = novelty if novelty is not None else clamp(1.0 / (1.0 + pattern_n))
        goal_outcome = 0.0
        if success is True:
            goal_outcome = 1.0
        elif success is False:
            goal_outcome = -1.0

        score = self.encoding_score(
            prediction_error=prediction_error,
            physiological_delta=physiological_delta,
            goal_outcome=goal_outcome,
            novelty=nov,
            skill_learning_value=skill_learning_value,
            pattern_relevance=pattern_relevance,
            body_change=body_change,
            fingerprint=fp,
        )
        # Rare high-consequence / protected always encode
        high_consequence = abs(physiological_delta) >= 0.25 or protected or force
        if not high_consequence and score < ENCODING_SCORE_THRESHOLD and not self.config.store_every_event:
            self.metrics["episodes_rejected"] = int(self.metrics.get("episodes_rejected", 0)) + 1
            self.encoding_fingerprint_seen[fp] = self.encoding_fingerprint_seen.get(fp, 0) + 1
            return None

        goal_rel = clamp(abs(goal_outcome) * 0.7 + (0.3 if goal else 0.0))
        phys_rel = clamp(abs(physiological_delta))
        sal = clamp(
            0.35 * score
            + 0.25 * prediction_error
            + 0.2 * phys_rel
            + 0.2 * (1.0 if high_consequence else nov)
        )
        eid = (
            _stable_id("ep", f"{self.agent_id}|{tick}|{fp}|{len(self.episodes)}")
            if self.seed is not None
            else new_id()
        )
        ep = Episode(
            episode_id=eid,
            agent_id=self.agent_id,
            occurred_at=float(occurred_at),
            context=tuple(sorted((str(k), v) for k, v in context.items())),
            observations=tuple(observations[:8]),  # bound observation payload
            internal_state=tuple(sorted((str(k), v) for k, v in internal_state.items())),
            goal=goal,
            action=action,
            verified_outcome=(
                tuple(sorted((str(k), v) for k, v in verified_outcome.items()))
                if verified_outcome
                else None
            ),
            prediction_error=float(prediction_error),
            salience=sal,
            novelty=nov,
            goal_relevance=goal_rel,
            physiological_relevance=phys_rel,
            confidence=clamp(0.4 + 0.4 * (1.0 - prediction_error) + 0.2 * (1.0 if success else 0.0)),
            causal_parent_ids=tuple(causal_parent_ids or ()),
            body_binding_id=body_binding_id,
            source_event_ids=tuple(source_event_ids or ()),
            tick=tick,
            protected=protected or (protect_kind in PROTECTED_KINDS if protect_kind else False),
            protect_kind=protect_kind,
            fingerprint=fp,
        )
        self.episodes[eid] = ep
        self.encoding_fingerprint_seen[fp] = self.encoding_fingerprint_seen.get(fp, 0) + 1
        self.pattern_counts[pattern_key] = pattern_n + 1
        self.metrics["episodes_encoded"] = int(self.metrics.get("episodes_encoded", 0)) + 1
        self._bound_active_episodes()
        return ep

    def correct_episode(
        self,
        original_id: str,
        *,
        tick: int,
        occurred_at: float,
        reinterpretation: dict[str, Any],
        source_event_ids: list[str] | None = None,
    ) -> Episode:
        """Create a linked correction; original remains immutable."""
        orig = self.episodes.get(original_id) or self.archived.get(original_id)
        if orig is None:
            raise KeyError(f"episode_missing:{original_id}")
        ctx = dict(orig.context)
        ctx.update(reinterpretation)
        ctx["correction"] = True
        corr = self.consider_event(
            tick=tick,
            occurred_at=occurred_at,
            context=ctx,
            observations=list(orig.observations),
            internal_state=dict(orig.internal_state),
            goal=orig.goal,
            action=orig.action,
            verified_outcome=dict(orig.verified_outcome) if orig.verified_outcome else None,
            prediction_error=orig.prediction_error,
            physiological_delta=orig.physiological_relevance,
            novelty=0.2,
            body_binding_id=orig.body_binding_id,
            source_event_ids=source_event_ids or list(orig.source_event_ids),
            causal_parent_ids=[orig.episode_id],
            protected=True,
            protect_kind="memory_correction",
            force=True,
        )
        assert corr is not None
        # Rebuild with correction_of (frozen dataclass) — original stays untouched
        corr_d = corr.to_dict()
        corr_d["correction_of"] = original_id
        corr_d["episode_id"] = corr.episode_id
        corr2 = Episode.from_dict(corr_d)
        self.episodes.pop(corr.episode_id, None)
        self.episodes[corr2.episode_id] = corr2
        self.corrections.append(corr2.episode_id)
        if len(self.corrections) > MAX_CORRECTIONS:
            self.corrections = self.corrections[-MAX_CORRECTIONS:]
        self.metrics["corrections"] = int(self.metrics.get("corrections", 0)) + 1
        return corr2

    def mutate_episode_forbidden(self, episode_id: str, **_kwargs: Any) -> None:
        """Episodes are immutable — any mutation attempt fails closed."""
        raise RuntimeError("episode_immutable")

    # --- D-006 social outcome finalization --------------------------------

    def finalize_social_episode(
        self,
        *,
        episode_key: str,
        tick: int,
        occurred_at: float,
        context: dict[str, Any],
        observations: list[Any],
        internal_state: dict[str, Any],
        goal: str | None,
        action: str | None,
        verified_outcome: dict[str, Any] | None,
        prediction_error: float = 0.0,
        salience: float = 0.5,
        source_event_ids: list[str] | None = None,
        causal_parent_ids: list[str] | None = None,
    ) -> Episode:
        """Build an immutable social-outcome episode WITHOUT inserting it.

        The caller records the episode durably (ledger event + evidence links) inside
        the atomic outcome transaction and only calls `attach_episode` after COMMIT, so
        a rolled-back outcome never leaves an orphan episode in working state.
        """
        eid = _stable_id("ep", f"{self.agent_id}|{episode_key}")
        success = bool(verified_outcome.get("success")) if verified_outcome else False
        return Episode(
            episode_id=eid,
            agent_id=self.agent_id,
            occurred_at=float(occurred_at),
            context=tuple(sorted((str(k), v) for k, v in context.items())),
            observations=tuple(observations[:8]),
            internal_state=tuple(sorted((str(k), v) for k, v in internal_state.items())),
            goal=goal,
            action=action,
            verified_outcome=(
                tuple(sorted((str(k), v) for k, v in verified_outcome.items()))
                if verified_outcome
                else None
            ),
            prediction_error=float(prediction_error),
            salience=clamp(salience),
            novelty=0.2,
            goal_relevance=clamp(0.3 + (0.4 if success else 0.0)),
            physiological_relevance=0.0,
            confidence=clamp(0.5 + (0.3 if success else 0.0)),
            causal_parent_ids=tuple(causal_parent_ids or ()),
            body_binding_id=None,
            source_event_ids=tuple(source_event_ids or ()),
            tick=tick,
            fingerprint=eid[:24],
        )

    def attach_episode(self, ep: Episode) -> None:
        """Insert a pre-finalized immutable episode after its durable commit."""
        if ep.episode_id in self.episodes:
            return  # idempotent — never double-record the same finalized episode
        self.episodes[ep.episode_id] = ep
        self.metrics["episodes_encoded"] = int(self.metrics.get("episodes_encoded", 0)) + 1
        self._bound_active_episodes()

    def promote_social_routine(
        self, spec: SocialRoutineSpec | dict[str, Any], *, tick: int = 0
    ) -> str:
        """Promote a partner-scoped shared routine into D-005 procedural memory.

        Authored C8 scripts must never use this path — they are ablation-only and
        do not count as learned development.
        """
        if isinstance(spec, dict):
            spec = SocialRoutineSpec(
                **{k: v for k, v in spec.items() if k in SocialRoutineSpec.__dataclass_fields__}
            )
        if spec.authored:
            raise ValueError("authored_routine_not_learned_development")
        skill_id = _stable_id(
            "routine",
            f"{self.agent_id}|{spec.partner_hypothesis}|{spec.context}|{spec.signal}",
        )
        if skill_id in self.procedural:
            return skill_id
        min_body = float(spec.body_requirements.get("min_body_compatibility", 0.35))
        applicability: dict[str, Any] = {
            "kind": "social_routine",
            "partner_hypothesis": spec.partner_hypothesis,
            "context": spec.context,
            "signal": spec.signal,
            "soft_proposals": list(spec.soft_proposals),
            "interrupt_conditions": list(spec.interrupt_conditions),
            "satiation_constraints": dict(spec.satiation_constraints),
            "body_requirements": dict(spec.body_requirements),
            "success_conditions": dict(spec.success_conditions),
        }
        support = list(spec.supporting_episode_ids)[-MAX_ROUTINE_SUPPORTING_EPISODES:]
        sk = ProceduralMemory(
            skill_id=skill_id,
            applicability=applicability,
            body_compatibility=min_body,
            attempts=0,
            success_count=len(support),
            failure_count=0,
            confidence=clamp(0.35 + 0.1 * len(support)),
            source_episode_ids=support,
            last_updated_tick=tick,
        )
        self.procedural[skill_id] = sk
        self._bound_procedural()
        self.metrics["social_routines_promoted"] = int(
            self.metrics.get("social_routines_promoted", 0)
        ) + 1
        return skill_id

    def select_social_routine(
        self, *, partner_hypothesis: str, context: str | None = None
    ) -> ProceduralMemory | None:
        """Select an active partner-scoped social routine, if any."""
        cands: list[ProceduralMemory] = []
        for sk in self.procedural.values():
            app = sk.applicability
            if app.get("kind") != "social_routine":
                continue
            if sk.status != MemoryStatus.ACTIVE.value:
                continue
            if app.get("partner_hypothesis") != partner_hypothesis:
                continue
            if context is not None and app.get("context") != context:
                continue
            cands.append(sk)
        if not cands:
            return None
        cands.sort(key=lambda s: (-s.confidence, -s.success_count, s.skill_id))
        return cands[0]

    # --- working memory ---------------------------------------------------

    def _push_working(self, item: WorkingItem) -> None:
        self.working.append(item)
        if len(self.working) > self.config.max_working:
            self.working = self.working[-self.config.max_working :]

    def expire_working(self, tick: int) -> int:
        before = len(self.working)
        self.working = [w for w in self.working if tick - w.created_tick < w.ttl]
        return before - len(self.working)

    # --- quiescence / consolidation ---------------------------------------

    def is_quiescent(self, phys: Any) -> bool:
        """Rest/quiescence: high fatigue or mid energy with low urgency."""
        try:
            fatigue = float(getattr(phys, "fatigue", 0.0))
            energy = float(getattr(phys, "energy", 0.5))
            critical = bool(phys.critical_any()) if hasattr(phys, "critical_any") else False
        except Exception:
            return False
        if critical:
            return False
        return fatigue >= 0.45 or (0.35 <= energy <= 0.75 and fatigue >= 0.25)

    def select_replay_candidates(
        self, rng: SeededRNG, *, n: int | None = None
    ) -> list[Episode]:
        n = n if n is not None else self.config.max_replay_per_cycle
        active = [
            e
            for e in self.episodes.values()
            if e.correction_of is None  # prefer originals for pattern mining
        ]
        if not active:
            return []
        mode = self.config.replay_mode
        if mode == "random":
            pool = list(active)
            rng.shuffle(pool)
            return pool[:n]
        scored: list[tuple[float, Episode]] = []
        for ep in active:
            repeats = self.replay_counts.get(ep.episode_id, 0)
            sat = clamp(1.0 - repeats / REPLAY_SATURATION, 0.05, 1.0)
            if mode == "salience_only":
                pri = ep.salience * sat
            else:
                # priority: salience, PE, goal rel, uncertainty(=PE), contradiction,
                # skill regression proxy, inverse recency of replay, diversity via sat
                contrad = 0.0
                prop = self._proposition_for_episode(ep)
                bel = self.beliefs.get(_stable_id("bl", f"{self.agent_id}|{prop}"))
                if bel and bel.status == MemoryStatus.CONTESTED.value:
                    contrad = 0.8
                skill_reg = 0.0
                sk = self.procedural.get(self._skill_key(ep))
                if sk and sk.failure_count > sk.success_count:
                    skill_reg = 0.6
                pri = (
                    0.22 * ep.salience
                    + 0.18 * ep.prediction_error
                    + 0.14 * ep.goal_relevance
                    + 0.14 * ep.prediction_error  # uncertainty proxy
                    + 0.12 * contrad
                    + 0.10 * skill_reg
                    + 0.05 * (1.0 / (1.0 + repeats))
                    + 0.05 * ep.novelty
                ) * sat
            scored.append((pri, ep))
        scored.sort(key=lambda x: (-x[0], x[1].episode_id))
        # Diversity: avoid same fingerprint monopolizing
        picked: list[Episode] = []
        seen_fp: set[str] = set()
        for _, ep in scored:
            if len(picked) >= n:
                break
            if ep.fingerprint in seen_fp and len(picked) < n // 2:
                continue
            picked.append(ep)
            seen_fp.add(ep.fingerprint)
        if len(picked) < n:
            for _, ep in scored:
                if ep not in picked:
                    picked.append(ep)
                if len(picked) >= n:
                    break
        return picked

    def consolidate(self, tick: int, rng: SeededRNG, *, force: bool = False) -> dict[str, Any]:
        """Bounded offline consolidation. Never rewrites episodes or invents events."""
        if not self.config.enabled or not self.config.consolidation_enabled:
            return {"ran": False, "reason": "disabled"}
        if not force and tick - self.last_consolidation_tick < 8:
            return {"ran": False, "reason": "cooldown"}

        steps = 0
        belief_updates = 0
        proc_updates = 0
        candidates = self.select_replay_candidates(rng)
        replayed_ids: list[str] = []
        for ep in candidates:
            if steps >= self.config.max_consolidation_steps:
                break
            if belief_updates >= self.config.max_belief_updates and proc_updates >= self.config.max_procedural_updates:
                break
            steps += 1
            self.replay_counts[ep.episode_id] = self.replay_counts.get(ep.episode_id, 0) + 1
            replayed_ids.append(ep.episode_id)
            self.metrics["replay_items"] = int(self.metrics.get("replay_items", 0)) + 1

            if belief_updates < self.config.max_belief_updates:
                if self._update_belief_from_episode(ep, tick):
                    belief_updates += 1
                    self.metrics["belief_updates"] = int(self.metrics.get("belief_updates", 0)) + 1
            if proc_updates < self.config.max_procedural_updates:
                if self._update_procedural_from_episode(ep, tick):
                    proc_updates += 1
                    self.metrics["procedural_updates"] = int(
                        self.metrics.get("procedural_updates", 0)
                    ) + 1

        archived_n = 0
        if self.config.forgetting_enabled:
            archived_n = self._forget_and_archive(tick)

        self.last_consolidation_tick = tick
        self.metrics["consolidations"] = int(self.metrics.get("consolidations", 0)) + 1
        self.metrics["consolidation_cost"] = int(self.metrics.get("consolidation_cost", 0)) + steps
        diversity = len(set(replayed_ids)) / max(1, len(replayed_ids))
        self.metrics["replay_diversity"] = float(diversity)
        return {
            "ran": True,
            "steps": steps,
            "belief_updates": belief_updates,
            "procedural_updates": proc_updates,
            "archived": archived_n,
            "replayed": replayed_ids,
            "diversity": diversity,
        }

    def _proposition_for_episode(self, ep: Episode) -> str:
        ctx = dict(ep.context)
        success = None
        if ep.verified_outcome:
            success = dict(ep.verified_outcome).get("success")
        return (
            f"action={ep.action}|entity={ctx.get('entity_kind')}|"
            f"affordance={ctx.get('affordance')}|success={success}|"
            f"rule={ctx.get('rule_tag', 'default')}"
        )

    def _independent_key(self, ep: Episode) -> str:
        """Each distinct encoded episode is one independent observation.

        Encoding-fingerprint satiation prevents storing every similar tick;
        duplicate episode_id references still do not double-count.
        """
        return ep.episode_id

    def _update_belief_from_episode(self, ep: Episode, tick: int) -> bool:
        prop = self._proposition_for_episode(ep)
        bid = _stable_id("bl", f"{self.agent_id}|{prop}")
        bel = self.beliefs.get(bid)
        indep = self._independent_key(ep)
        success = None
        if ep.verified_outcome:
            success = dict(ep.verified_outcome).get("success")

        if bel is None:
            if self.config.require_belief_provenance:
                # Need independent evidence; first episode seeds but low confidence
                bel = SemanticBelief(
                    belief_id=bid,
                    proposition=prop,
                    confidence=0.25,
                    supporting_episode_ids=[ep.episode_id],
                    contradicting_episode_ids=[],
                    status=MemoryStatus.ACTIVE.value,
                    independent_support_keys=[indep],
                    last_updated_tick=tick,
                    provenance_required=True,
                )
                self.beliefs[bid] = bel
                self._bound_beliefs()
                return True
            # C9: allow belief without provenance tracking
            bel = SemanticBelief(
                belief_id=bid,
                proposition=prop,
                confidence=0.55,
                supporting_episode_ids=[],
                contradicting_episode_ids=[],
                status=MemoryStatus.ACTIVE.value,
                independent_support_keys=[],
                last_updated_tick=tick,
                provenance_required=False,
            )
            self.beliefs[bid] = bel
            return True

        # Duplicate independent key does not count as new confirmation
        if indep in bel.independent_support_keys:
            if ep.episode_id not in bel.supporting_episode_ids:
                # still record as non-independent support reference (bounded)
                if len(bel.supporting_episode_ids) < 32:
                    bel.supporting_episode_ids.append(ep.episode_id)
            bel.last_updated_tick = tick
            return False

        # Contradiction: opposite success under same action/entity/rule family
        contradicted = False
        if self.config.contradiction_handling and success is not None:
            # Find sibling beliefs with same action/entity but opposite success
            base = prop.rsplit("|success=", 1)[0]
            for other in list(self.beliefs.values()):
                if other.belief_id == bel.belief_id:
                    continue
                if other.proposition.startswith(base + "|success=") and other.proposition != prop:
                    other_success = other.proposition.rsplit("|success=", 1)[-1]
                    if other_success != str(success):
                        contradicted = True
                        if ep.episode_id not in other.contradicting_episode_ids:
                            other.contradicting_episode_ids.append(ep.episode_id)
                        other.confidence = clamp(other.confidence - 0.2)
                        other.status = MemoryStatus.CONTESTED.value
                        other.last_updated_tick = tick
                        if ep.episode_id not in bel.supporting_episode_ids:
                            bel.supporting_episode_ids.append(ep.episode_id)
                        bel.independent_support_keys.append(indep)
                        bel.confidence = clamp(bel.confidence + 0.08)
                        bel.status = MemoryStatus.CONTESTED.value
                        # Possibly supersede weaker
                        if bel.confidence > other.confidence + 0.25:
                            snap = SemanticBelief.from_dict(other.to_dict())
                            snap.status = MemoryStatus.SUPERSEDED.value
                            self.superseded_beliefs.append(snap)
                            if len(self.superseded_beliefs) > self.config.max_semantic:
                                self.superseded_beliefs = self.superseded_beliefs[
                                    -self.config.max_semantic :
                                ]
                            other.status = MemoryStatus.SUPERSEDED.value
                            bel.supersedes = other.belief_id
                            bel.status = MemoryStatus.ACTIVE.value
                        bel.last_updated_tick = tick
                        return True

        if not contradicted:
            bel.supporting_episode_ids.append(ep.episode_id)
            bel.independent_support_keys.append(indep)
            # Independent confirmations strengthen
            n_indep = len(bel.independent_support_keys)
            if n_indep >= SEMANTIC_MIN_INDEPENDENT:
                bel.confidence = clamp(0.35 + 0.12 * n_indep)
            else:
                bel.confidence = clamp(bel.confidence + 0.05)
            bel.last_updated_tick = tick
            if bel.status == MemoryStatus.SUPERSEDED.value:
                pass
            elif bel.status != MemoryStatus.CONTESTED.value:
                bel.status = MemoryStatus.ACTIVE.value
        return True

    def _skill_key(self, ep: Episode) -> str:
        ctx = dict(ep.context)
        return _stable_id(
            "pr",
            f"{self.agent_id}|{ep.action}|{ctx.get('entity_kind')}|{ctx.get('affordance')}",
        )

    def _update_procedural_from_episode(self, ep: Episode, tick: int) -> bool:
        if not ep.action:
            return False
        sid = self._skill_key(ep)
        sk = self.procedural.get(sid)
        success = bool(dict(ep.verified_outcome).get("success")) if ep.verified_outcome else False
        ctx = dict(ep.context)
        body_compat = float(ctx.get("body_compatibility", 1.0))
        if sk is None:
            sk = ProceduralMemory(
                skill_id=sid,
                applicability={
                    "action": ep.action,
                    "entity_kind": ctx.get("entity_kind"),
                    "affordance": ctx.get("affordance"),
                },
                body_compatibility=body_compat,
                attempts=1,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                confidence=0.3 if success else 0.15,
                source_episode_ids=[ep.episode_id],
                last_updated_tick=tick,
            )
            self.procedural[sid] = sk
            self._bound_procedural()
            return True
        sk.attempts += 1
        if success:
            sk.success_count += 1
            sk.confidence = clamp(sk.confidence + 0.06)
        else:
            sk.failure_count += 1  # never erase failure history
            sk.confidence = clamp(sk.confidence - 0.04)
        sk.body_compatibility = min(sk.body_compatibility, body_compat)
        if ep.episode_id not in sk.source_episode_ids and len(sk.source_episode_ids) < 32:
            sk.source_episode_ids.append(ep.episode_id)
        sk.last_updated_tick = tick
        return True

    def select_procedural(
        self, *, action: str | None = None, min_body_compatibility: float = 0.35
    ) -> ProceduralMemory | None:
        """Select applicable procedural knowledge; body-incompatible skills excluded."""
        cands = []
        for sk in self.procedural.values():
            if sk.status == MemoryStatus.SUPERSEDED.value:
                continue
            if sk.body_compatibility < min_body_compatibility:
                continue
            if action and sk.applicability.get("action") != action:
                continue
            cands.append(sk)
        if not cands:
            return None
        cands.sort(key=lambda s: (-s.confidence, -s.success_count, s.skill_id))
        return cands[0]

    # --- forgetting -------------------------------------------------------

    def _forget_and_archive(self, tick: int) -> int:
        self.expire_working(tick)
        # Semantic / procedural confidence decay
        for bel in self.beliefs.values():
            if bel.status == MemoryStatus.ACTIVE.value:
                bel.confidence = clamp(bel.confidence - BELIEF_DECAY)
        for sk in self.procedural.values():
            if sk.status == MemoryStatus.ACTIVE.value:
                sk.confidence = clamp(sk.confidence - PROCEDURAL_DECAY)

        if len(self.episodes) <= self.config.max_active_episodic:
            # Still archive very low-value old episodes when over soft threshold
            soft = int(self.config.max_active_episodic * 0.85)
            if len(self.episodes) <= soft:
                return 0

        ranked = sorted(
            self.episodes.values(),
            key=lambda e: (
                1 if e.protected else 0,
                e.salience,
                e.physiological_relevance,
                e.goal_relevance,
                -e.tick,  # older first among equals
            ),
        )
        n_arch = 0
        target = int(self.config.max_active_episodic * 0.75)
        for ep in ranked:
            if len(self.episodes) <= target:
                break
            if ep.protected or ep.protect_kind in PROTECTED_KINDS:
                continue
            if ep.salience >= 0.55 and ep.physiological_relevance >= 0.2:
                continue  # retain high-value
            # Prefer archiving low-value
            if ep.salience > LOW_VALUE_SALIENCE and len(self.episodes) > self.config.max_active_episodic:
                pass  # may still archive if over hard max
            elif ep.salience > LOW_VALUE_SALIENCE and len(self.episodes) <= self.config.max_active_episodic:
                continue
            self.episodes.pop(ep.episode_id, None)
            # Compress: drop heavy observation payload in archive
            compressed = Episode.from_dict(
                {
                    **ep.to_dict(),
                    "observations": [],
                    "internal_state": {k: v for k, v in dict(ep.internal_state).items() if k in ("energy", "fatigue")},
                }
            )
            # Mark archived via status in context
            d = compressed.to_dict()
            ctx = dict(d["context"])
            ctx["archived"] = True
            d["context"] = ctx
            self.archived[ep.episode_id] = Episode.from_dict(d)
            n_arch += 1
            self.metrics["archived"] = int(self.metrics.get("archived", 0)) + 1
            if len(self.archived) > self.config.max_archived:
                # Drop oldest non-protected archives
                arch_ranked = sorted(
                    self.archived.values(),
                    key=lambda e: (1 if e.protected else 0, e.tick),
                )
                while len(self.archived) > self.config.max_archived and arch_ranked:
                    drop = arch_ranked.pop(0)
                    if drop.protected:
                        continue
                    self.archived.pop(drop.episode_id, None)
        return n_arch

    def _bound_active_episodes(self) -> None:
        if not self.config.forgetting_enabled:
            # C7: still hard-cap to prevent unbounded growth, but keep more
            hard = self.config.max_active_episodic * 4
            if len(self.episodes) <= hard:
                return
            # Drop lowest salience non-protected only when extremely over
            ranked = sorted(
                self.episodes.values(),
                key=lambda e: (1 if e.protected else 0, e.salience, e.tick),
            )
            while len(self.episodes) > hard and ranked:
                ep = ranked.pop(0)
                if ep.protected:
                    continue
                self.episodes.pop(ep.episode_id, None)
            return
        if len(self.episodes) > self.config.max_active_episodic:
            self._forget_and_archive(int(self.metrics.get("last_tick", 0)))

    def _bound_beliefs(self) -> None:
        if len(self.beliefs) <= self.config.max_semantic:
            return
        ranked = sorted(
            self.beliefs.values(),
            key=lambda b: (0 if b.status == MemoryStatus.SUPERSEDED.value else 1, b.confidence),
        )
        while len(self.beliefs) > self.config.max_semantic and ranked:
            b = ranked.pop(0)
            snap = SemanticBelief.from_dict(b.to_dict())
            snap.status = MemoryStatus.ARCHIVED.value
            self.superseded_beliefs.append(snap)
            self.beliefs.pop(b.belief_id, None)

    def _bound_procedural(self) -> None:
        if len(self.procedural) <= self.config.max_procedural:
            return
        ranked = sorted(self.procedural.values(), key=lambda s: (s.confidence, s.attempts))
        while len(self.procedural) > self.config.max_procedural and ranked:
            s = ranked.pop(0)
            s.status = MemoryStatus.ARCHIVED.value
            self.procedural.pop(s.skill_id, None)

    # --- retrieval --------------------------------------------------------

    def retrieve(
        self,
        *,
        query: dict[str, Any],
        rng: SeededRNG,
        limit: int = 8,
    ) -> list[RetrievalResult]:
        """Retrieve typed memories. Results are evidence, never authority."""
        self.metrics["retrievals"] = int(self.metrics.get("retrievals", 0)) + 1
        results: list[RetrievalResult] = []

        def score_ep(ep: Episode) -> float:
            s = 0.0
            if query.get("action") and ep.action == query["action"]:
                s += 0.25
            if query.get("goal") and ep.goal == query["goal"]:
                s += 0.2
            ctx = dict(ep.context)
            if query.get("entity_kind") and ctx.get("entity_kind") == query["entity_kind"]:
                s += 0.2
            if query.get("rule_tag") and ctx.get("rule_tag") == query["rule_tag"]:
                s += 0.15
            s += 0.1 * ep.confidence + 0.05 * ep.salience + 0.05 * ep.goal_relevance
            # temporal: prefer recent
            last = int(self.metrics.get("last_tick", 0))
            s += 0.05 * clamp(1.0 - abs(last - ep.tick) / max(1, last + 1))
            return s

        eps = list(self.episodes.values())
        if self.config.retrieval_mode == "random":
            rng.shuffle(eps)
            for ep in eps[:limit]:
                results.append(
                    RetrievalResult(
                        kind=RetrievalKind.OBSERVED_EPISODE.value,
                        item_id=ep.episode_id,
                        score=0.5,
                        content=ep.to_dict(),
                        provenance=list(ep.source_event_ids),
                    )
                )
        else:
            ranked = sorted(eps, key=lambda e: (-score_ep(e), e.episode_id))
            for ep in ranked[: max(1, limit // 2)]:
                results.append(
                    RetrievalResult(
                        kind=RetrievalKind.OBSERVED_EPISODE.value,
                        item_id=ep.episode_id,
                        score=score_ep(ep),
                        content=ep.to_dict(),
                        provenance=list(ep.source_event_ids),
                    )
                )

        # Beliefs
        for bel in self.beliefs.values():
            if bel.status == MemoryStatus.SUPERSEDED.value:
                continue
            if self.config.require_belief_provenance and not bel.supporting_episode_ids:
                continue
            match = 0.0
            if query.get("action") and f"action={query['action']}" in bel.proposition:
                match += 0.4
            if query.get("entity_kind") and f"entity={query['entity_kind']}" in bel.proposition:
                match += 0.3
            if match <= 0 and query:
                continue
            results.append(
                RetrievalResult(
                    kind=RetrievalKind.DERIVED_BELIEF.value,
                    item_id=bel.belief_id,
                    score=match + 0.3 * bel.confidence,
                    content=bel.to_dict(),
                    provenance=list(bel.supporting_episode_ids),
                    is_verified_fact=False,
                )
            )

        # Procedural
        sk = self.select_procedural(action=query.get("action"))
        if sk is not None:
            results.append(
                RetrievalResult(
                    kind=RetrievalKind.PROCEDURAL_KNOWLEDGE.value,
                    item_id=sk.skill_id,
                    score=sk.confidence,
                    content=sk.to_dict(),
                    provenance=list(sk.source_episode_ids),
                )
            )

        # Prediction from belief confidence (not fact)
        for r in list(results):
            if r.kind == RetrievalKind.DERIVED_BELIEF.value and r.score > 0.4:
                results.append(
                    RetrievalResult(
                        kind=RetrievalKind.PREDICTION.value,
                        item_id=f"pred:{r.item_id}",
                        score=r.score * 0.8,
                        content={"from_belief": r.item_id, "proposition": r.content.get("proposition")},
                        provenance=r.provenance,
                    )
                )
                break

        results.sort(key=lambda r: (-r.score, r.kind, r.item_id))
        return results[:limit]

    def predict_from_memory(self, *, action: str, entity_kind: str | None = None) -> float | None:
        """Return predicted success probability from beliefs/procedural — not verified truth."""
        self.metrics["prediction_total"] = int(self.metrics.get("prediction_total", 0)) + 1
        sk = self.select_procedural(action=action)
        if sk and sk.attempts >= 2:
            p = sk.success_count / max(1, sk.attempts)
            return float(p)
        best = None
        for bel in self.beliefs.values():
            if bel.status not in (MemoryStatus.ACTIVE.value, MemoryStatus.CONTESTED.value):
                continue
            if f"action={action}" not in bel.proposition:
                continue
            if entity_kind and f"entity={entity_kind}" not in bel.proposition:
                continue
            if "success=True" in bel.proposition:
                score = bel.confidence
            elif "success=False" in bel.proposition:
                score = 1.0 - bel.confidence
            else:
                continue
            if best is None or score > best:
                best = score
        return best

    # --- safety -----------------------------------------------------------

    def try_grant_authority(self, content: dict[str, Any]) -> bool:
        """Memory content cannot grant authority — always False."""
        _ = content
        return False

    def apply_memory_to_physiology(self, phys: Any) -> None:
        """Forbidden — memory must not modify physiology directly."""
        raise RuntimeError("memory_cannot_modify_physiology")

    def apply_memory_to_identity(self, identity: Any) -> None:
        raise RuntimeError("memory_cannot_modify_identity")

    # --- persistence ------------------------------------------------------

    def counts_bounded(self) -> bool:
        if self.config.forgetting_enabled:
            return (
                len(self.working) <= self.config.max_working
                and len(self.episodes) <= self.config.max_active_episodic
                and len(self.archived) <= self.config.max_archived
                and len(self.beliefs) <= self.config.max_semantic
                and len(self.procedural) <= self.config.max_procedural
                and len(self.replay_counts) <= self.config.max_active_episodic + self.config.max_archived
            )
        # C7 may exceed active cap but still hard-bounded
        return (
            len(self.working) <= self.config.max_working
            and len(self.episodes) <= self.config.max_active_episodic * 4
            and len(self.beliefs) <= self.config.max_semantic
            and len(self.procedural) <= self.config.max_procedural
        )

    def memory_growth(self) -> int:
        return len(self.episodes) + len(self.archived) + len(self.beliefs) + len(self.procedural)

    def high_value_retained(self) -> int:
        return sum(
            1
            for e in list(self.episodes.values()) + list(self.archived.values())
            if e.salience >= 0.40 or e.protected or e.physiological_relevance >= 0.2
        )

    def low_value_retained(self) -> int:
        return sum(
            1
            for e in list(self.episodes.values()) + list(self.archived.values())
            if e.salience < LOW_VALUE_SALIENCE and not e.protected
        )

    def accepted_state(self) -> dict[str, Any]:
        """Authoritative memory state for birth/snapshot replay equality."""
        return {
            "agent_id": self.agent_id,
            "episodes": {k: self.episodes[k].to_dict() for k in sorted(self.episodes)},
            "archived": {k: self.archived[k].to_dict() for k in sorted(self.archived)},
            "corrections": list(self.corrections),
            "beliefs": {k: self.beliefs[k].to_dict() for k in sorted(self.beliefs)},
            "superseded_beliefs": [b.to_dict() for b in self.superseded_beliefs],
            "procedural": {k: self.procedural[k].to_dict() for k in sorted(self.procedural)},
            "replay_counts": dict(sorted(self.replay_counts.items())),
            "pattern_counts": dict(sorted(self.pattern_counts.items())),
            "encoding_fingerprint_seen": dict(sorted(self.encoding_fingerprint_seen.items())),
            "last_consolidation_tick": self.last_consolidation_tick,
            "metrics": {
                k: self.metrics[k]
                for k in sorted(self.metrics)
                if k
                in (
                    "candidates_seen",
                    "episodes_encoded",
                    "episodes_rejected",
                    "consolidations",
                    "replay_items",
                    "belief_updates",
                    "procedural_updates",
                    "archived",
                    "corrections",
                )
            },
        }

    def to_state(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "seed": self.seed,
            "working": [w.to_dict() for w in self.working],
            "episodes": {k: v.to_dict() for k, v in self.episodes.items()},
            "archived": {k: v.to_dict() for k, v in self.archived.items()},
            "corrections": list(self.corrections),
            "beliefs": {k: v.to_dict() for k, v in self.beliefs.items()},
            "superseded_beliefs": [b.to_dict() for b in self.superseded_beliefs],
            "procedural": {k: v.to_dict() for k, v in self.procedural.items()},
            "replay_counts": dict(self.replay_counts),
            "pattern_counts": dict(self.pattern_counts),
            "encoding_fingerprint_seen": dict(self.encoding_fingerprint_seen),
            "last_consolidation_tick": self.last_consolidation_tick,
            "metrics": dict(self.metrics),
            "config": asdict(self.config),
        }

    @classmethod
    def from_state(
        cls, state: dict[str, Any], *, config: MemoryConfig | None = None
    ) -> MemoryEngine:
        cfg = config or MemoryConfig(**(state.get("config") or {}))
        eng = cls(
            agent_id=str(state["agent_id"]),
            config=cfg,
            seed=state.get("seed"),
        )
        eng.working = [WorkingItem.from_dict(w) for w in state.get("working") or []]
        eng.episodes = {
            k: Episode.from_dict(v) for k, v in (state.get("episodes") or {}).items()
        }
        eng.archived = {
            k: Episode.from_dict(v) for k, v in (state.get("archived") or {}).items()
        }
        eng.corrections = list(state.get("corrections") or [])
        eng.beliefs = {
            k: SemanticBelief.from_dict(v) for k, v in (state.get("beliefs") or {}).items()
        }
        eng.superseded_beliefs = [
            SemanticBelief.from_dict(b) for b in state.get("superseded_beliefs") or []
        ]
        eng.procedural = {
            k: ProceduralMemory.from_dict(v)
            for k, v in (state.get("procedural") or {}).items()
        }
        eng.replay_counts = {str(k): int(v) for k, v in (state.get("replay_counts") or {}).items()}
        eng.pattern_counts = {
            str(k): int(v) for k, v in (state.get("pattern_counts") or {}).items()
        }
        eng.encoding_fingerprint_seen = {
            str(k): int(v)
            for k, v in (state.get("encoding_fingerprint_seen") or {}).items()
        }
        eng.last_consolidation_tick = int(state.get("last_consolidation_tick", -10_000))
        eng.metrics = dict(state.get("metrics") or {})
        eng.initialize_bounded_collections()
        return eng
