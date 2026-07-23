"""D-007 IndividualityEngine — slow history-shaped disposition estimates.

Bounded integration layer over D-001..D-006. Owns disposition anchors,
provenance refs, and bounded arbitration modifiers. Does not own identity,
physiology, world truth, embodiment, capability grants, episodic/procedural
authority, social-partner truth, or final execution.

Temperament here means slow measurable experience-shaped behavioral
dispositions only — never authored personality, scalar affection, or
character classes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from umbra_core.arbitration import Candidate
from umbra_core.util import clamp, new_id


# Mirrored from experiments/d007/thresholds.json (frozen).
MODIFIER_ABS_MAX = 0.35
LEARNING_RATE_BASE = 0.05
ANOMALY_CONFIDENCE_DELTA = 0.08
REVISION_MIN_CONTRADICTIONS = 3
SINGLE_ANOMALY_VALUE_DELTA_MAX = 0.08
MAX_DISPOSITION_RECORDS = 64
MAX_CONTEXT_SCOPES = 24
MAX_SUPPORTING_EVIDENCE_REFS = 24
MAX_CONTRADICTING_EVIDENCE_REFS = 24
MAX_ACTIVE_EVIDENCE_REFS = 32
MAX_EVENT_LOG = 256  # in-memory ring; SQLite ledger remains authoritative
GENERALIZATION_WITHIN_FAMILY_MAX = 0.35
GENERALIZATION_CROSS_FAMILY = 0.0

DISPOSITION_DIMENSIONS = (
    "exploration_tendency",
    "novelty_tolerance",
    "persistence_after_failure",
    "uncertainty_caution",
    "stimulation_tolerance",
    "recovery_pacing",
    "activity_timing_preference",
    "social_initiative_by_context",
)

# Preregistered context families — cross-family generalization = 0.
CONTEXT_FAMILIES: dict[str, frozenset[str]] = {
    "explore": frozenset({"safe_explore", "novelty_probe", "default"}),
    "persist": frozenset({"solvable_task", "practice", "object_family_a", "object_family_b", "default"}),
    "hazard": frozenset({"uncertain_hazard", "integrity_risk", "default"}),
    "stim": frozenset({"high_stim", "inspect_activity", "default"}),
    "recover": frozenset({"post_stim_recovery", "rest_pacing", "interruption", "default"}),
    "timing": frozenset({"diurnal_phase", "routine_window", "default"}),
    "social": frozenset({"play_context", "assistance_context", "pooled_social", "default"}),
}

CONTEXT_TO_FAMILY: dict[str, str] = {
    scope: family for family, scopes in CONTEXT_FAMILIES.items() for scope in scopes if scope != "default"
}

# Capability relevance for modifiers (dimension → capability weights).
DIM_CAP_WEIGHTS: dict[str, dict[str, float]] = {
    "exploration_tendency": {"MOVE": 1.0, "INSPECT": 0.7, "APPROACH": 0.5, "ORIENT": 0.3},
    "novelty_tolerance": {"INSPECT": 1.0, "APPROACH": 0.8, "MOVE": 0.4},
    "persistence_after_failure": {"INSPECT": 0.9, "CHARGE": 0.7, "APPROACH": 0.6, "MOVE": 0.4},
    "uncertainty_caution": {"RETREAT": 1.0, "IDLE": 0.5, "APPROACH": -0.6, "MOVE": -0.3},
    "stimulation_tolerance": {"INSPECT": 1.0, "REST": -0.4, "IDLE": -0.2},
    "recovery_pacing": {"REST": 1.0, "IDLE": 0.7, "INSPECT": -0.5},
    "activity_timing_preference": {"MOVE": 0.6, "REST": 0.6, "CHARGE": 0.4},
    "social_initiative_by_context": {
        "SIGNAL_PLAY": 1.0,
        "SIGNAL_ASSISTANCE": 1.0,
        "APPROACH": 0.5,
        "ORIENT": 0.3,
    },
}

FORBIDDEN_STATE_KEYS = frozenset(
    {
        "personality_score",
        "personality_type",
        "goodness",
        "happiness",
        "affection",
        "bond_level",
        "obedience",
        "character_class",
        "avatar_id",
        "ui_component_id",
        "animation_name",
        "screen_coordinates",
        "robotic_chassis_id",
        "device_personality",
        "history_label",
        "random_seed_personality",
        "preferred_activity_authored",
        "preferred_partner_authored",
    }
)

AUTHORITATIVE_INDIVIDUALITY_EVENTS = frozenset(
    {
        "individuality_disposition_created",
        "individuality_disposition_updated",
        "individuality_disposition_revised",
        "individuality_disposition_deactivated",
        "individuality_profile_migrated",
    }
)


class IndividualityEngineError(Exception):
    """Fail-closed individuality / provenance failure."""


def _family_of(context_scope: str) -> str | None:
    if context_scope in CONTEXT_TO_FAMILY:
        return CONTEXT_TO_FAMILY[context_scope]
    for family, scopes in CONTEXT_FAMILIES.items():
        if context_scope in scopes:
            return family
    return None


def _generalization_strength(src_scope: str, dst_scope: str) -> float:
    if src_scope == dst_scope:
        return 1.0
    sf = _family_of(src_scope)
    df = _family_of(dst_scope)
    if sf is None or df is None or sf != df:
        return GENERALIZATION_CROSS_FAMILY
    return GENERALIZATION_WITHIN_FAMILY_MAX


def _ring_append(lst: list[str], item: str, cap: int) -> None:
    if item in lst:
        lst.remove(item)
    lst.append(item)
    while len(lst) > cap:
        lst.pop(0)


@dataclass
class DispositionEstimate:
    dimension: str
    context_scope: str
    value: float = 0.0
    confidence: float = 0.0
    uncertainty: float = 1.0
    plasticity: float = 1.0
    support_count: int = 0
    contradiction_count: int = 0
    supporting_evidence_refs: list[str] = field(default_factory=list)
    contradicting_evidence_refs: list[str] = field(default_factory=list)
    last_update_tick: int = 0
    source_systems: list[str] = field(default_factory=list)
    active: bool = True

    def to_state(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "context_scope": self.context_scope,
            "value": self.value,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "plasticity": self.plasticity,
            "support_count": self.support_count,
            "contradiction_count": self.contradiction_count,
            "supporting_evidence_refs": list(self.supporting_evidence_refs),
            "contradicting_evidence_refs": list(self.contradicting_evidence_refs),
            "last_update_tick": self.last_update_tick,
            "source_systems": list(self.source_systems),
            "active": self.active,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> DispositionEstimate:
        return cls(
            dimension=str(d["dimension"]),
            context_scope=str(d["context_scope"]),
            value=float(d.get("value", 0.0)),
            confidence=float(d.get("confidence", 0.0)),
            uncertainty=float(d.get("uncertainty", 1.0)),
            plasticity=float(d.get("plasticity", 1.0)),
            support_count=int(d.get("support_count", 0)),
            contradiction_count=int(d.get("contradiction_count", 0)),
            supporting_evidence_refs=list(d.get("supporting_evidence_refs") or []),
            contradicting_evidence_refs=list(d.get("contradicting_evidence_refs") or []),
            last_update_tick=int(d.get("last_update_tick", 0)),
            source_systems=list(d.get("source_systems") or []),
            active=bool(d.get("active", True)),
        )


@dataclass
class IndividualityConfig:
    enabled: bool = True
    learning_enabled: bool = True
    modifiers_affect_arbitration: bool = True
    episodic_evidence_enabled: bool = True
    procedural_refs_enabled: bool = True
    pool_social_contexts: bool = False
    reset_on_restart: bool = False
    frequency_only: bool = False
    modifier_abs_max: float = MODIFIER_ABS_MAX
    learning_rate_base: float = LEARNING_RATE_BASE

    def to_state(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "learning_enabled": self.learning_enabled,
            "modifiers_affect_arbitration": self.modifiers_affect_arbitration,
            "episodic_evidence_enabled": self.episodic_evidence_enabled,
            "procedural_refs_enabled": self.procedural_refs_enabled,
            "pool_social_contexts": self.pool_social_contexts,
            "reset_on_restart": self.reset_on_restart,
            "frequency_only": self.frequency_only,
            "modifier_abs_max": self.modifier_abs_max,
            "learning_rate_base": self.learning_rate_base,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> IndividualityConfig:
        return cls(
            enabled=bool(d.get("enabled", True)),
            learning_enabled=bool(d.get("learning_enabled", True)),
            modifiers_affect_arbitration=bool(d.get("modifiers_affect_arbitration", True)),
            episodic_evidence_enabled=bool(d.get("episodic_evidence_enabled", True)),
            procedural_refs_enabled=bool(d.get("procedural_refs_enabled", True)),
            pool_social_contexts=bool(d.get("pool_social_contexts", False)),
            reset_on_restart=bool(d.get("reset_on_restart", False)),
            frequency_only=bool(d.get("frequency_only", False)),
            modifier_abs_max=float(d.get("modifier_abs_max", MODIFIER_ABS_MAX)),
            learning_rate_base=float(d.get("learning_rate_base", LEARNING_RATE_BASE)),
        )


def condition_to_individuality_config(condition: str) -> IndividualityConfig:
    """Map ablation condition → production IndividualityConfig.

    C2/C3 are experiments-only diagnostic controllers — they must not share
    production schemas. Calling this with C2/C3 raises.
    """
    if condition in ("C2", "C3"):
        raise IndividualityEngineError(
            f"{condition}_is_experiments_only_diagnostic_not_production_schema"
        )
    cfg = IndividualityConfig()
    if condition == "C1":
        cfg.enabled = False
        cfg.learning_enabled = False
        cfg.modifiers_affect_arbitration = False
    elif condition == "C4":
        cfg.frequency_only = True
    elif condition == "C5":
        cfg.episodic_evidence_enabled = False
    elif condition == "C6":
        cfg.procedural_refs_enabled = False
    elif condition == "C7":
        cfg.pool_social_contexts = True
    elif condition == "C8":
        cfg.reset_on_restart = True
    elif condition == "C10":
        cfg.modifiers_affect_arbitration = False
    elif condition not in ("C0", "C9"):
        # C9 is harness-level shuffle; production config remains C0-like.
        if condition.startswith("C"):
            raise IndividualityEngineError(f"unknown_individuality_condition:{condition}")
    return cfg


@dataclass
class VerifiedEvidence:
    """Finalized verified experience eligible for disposition update."""

    evidence_id: str
    tick: int
    source_system: str  # physiology|world|development|memory|social|governance|outcome
    dimension: str
    context_scope: str
    signed_outcome: float  # [-1, 1] positive = support for higher disposition value
    verified: bool = True
    executed: bool = True
    severe_safety: bool = False
    is_anomaly: bool = False
    from_episode: bool = False
    from_procedural: bool = False
    from_frequency_only: bool = False
    action: str | None = None
    partner_context: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class IndividualityEngine:
    SCHEMA_VERSION = "d007-v1"

    def __init__(
        self,
        agent_id: str,
        config: IndividualityConfig | None = None,
        *,
        seed: int = 0,
    ):
        self.agent_id = agent_id
        self.config = config or IndividualityConfig()
        self.seed = int(seed)  # paired RNG seed — never a personality variable
        self.dispositions: dict[tuple[str, str], DispositionEstimate] = {}
        self.metrics: dict[str, Any] = {
            "updates": 0,
            "revisions": 0,
            "anomalies_seen": 0,
            "modifiers_applied": 0,
            "modifiers_suppressed_critical": 0,
            "frequency_rejected": 0,
            "unverified_rejected": 0,
            "events_emitted": 0,
        }
        self._pending_events: list[dict[str, Any]] = []
        self._event_log: list[dict[str, Any]] = []  # authoritative in-memory for replay tests
        self._last_modifiers: dict[str, float] = {}
        self._bounded_initialized = False
        self.initialize_neutral_anchors()

    @classmethod
    def create(
        cls, agent_id: str, config: IndividualityConfig | None = None, *, seed: int = 0
    ) -> IndividualityEngine:
        eng = cls(agent_id, config=config, seed=seed)
        for dim in DISPOSITION_DIMENSIONS:
            eng._ensure(dim, "default", tick=0, emit_created=True)
        return eng

    def initialize_neutral_anchors(self) -> None:
        """Birth: identical neutral disposition anchors for all matched organisms."""
        for dim in DISPOSITION_DIMENSIONS:
            key = (dim, "default")
            if key not in self.dispositions:
                self.dispositions[key] = DispositionEstimate(
                    dimension=dim, context_scope="default", value=0.0
                )

    def initialize_bounded_collections(self) -> None:
        self._bounded_initialized = True
        # Caps enforced on every update; nothing unbounded to pad.

    def _ensure(
        self, dimension: str, context_scope: str, *, tick: int, emit_created: bool
    ) -> DispositionEstimate:
        if dimension not in DISPOSITION_DIMENSIONS:
            raise IndividualityEngineError(f"unknown_dimension:{dimension}")
        if self.config.pool_social_contexts and _family_of(context_scope) == "social":
            context_scope = "pooled_social"
        key = (dimension, context_scope)
        if key not in self.dispositions:
            if len(self.dispositions) >= MAX_DISPOSITION_RECORDS:
                # Evict lowest-confidence non-default inactive first, else lowest confidence.
                victims = sorted(
                    self.dispositions.values(),
                    key=lambda d: (d.context_scope == "default", d.confidence, -d.uncertainty),
                )
                for v in victims:
                    if v.context_scope != "default" or len(self.dispositions) >= MAX_DISPOSITION_RECORDS:
                        self.dispositions.pop((v.dimension, v.context_scope), None)
                        break
            est = DispositionEstimate(dimension=dimension, context_scope=context_scope)
            self.dispositions[key] = est
            if emit_created:
                self._emit(
                    "individuality_disposition_created",
                    {
                        "dimension": dimension,
                        "context_scope": context_scope,
                        "prior_anchor": 0.0,
                        "new_anchor": 0.0,
                        "confidence": 0.0,
                        "uncertainty": 1.0,
                        "causal_evidence_refs": [],
                        "source_system": "individuality",
                        "update_reason": "birth_or_first_scope",
                        "tick": tick,
                        "schema_version": self.SCHEMA_VERSION,
                    },
                )
        return self.dispositions[key]

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if event_type not in AUTHORITATIVE_INDIVIDUALITY_EVENTS:
            raise IndividualityEngineError(f"non_authoritative_event:{event_type}")
        rec = {"event_type": event_type, "payload": dict(payload), "event_id": new_id()}
        self._pending_events.append(rec)
        self._event_log.append(rec)
        while len(self._event_log) > MAX_EVENT_LOG:
            self._event_log.pop(0)
        self.metrics["events_emitted"] = int(self.metrics["events_emitted"]) + 1

    def drain_events(self) -> list[dict[str, Any]]:
        out = list(self._pending_events)
        self._pending_events.clear()
        return out

    def get(self, dimension: str, context_scope: str = "default") -> DispositionEstimate:
        if self.config.pool_social_contexts and _family_of(context_scope) == "social":
            context_scope = "pooled_social"
        key = (dimension, context_scope)
        if key in self.dispositions:
            return self.dispositions[key]
        return self.dispositions.get((dimension, "default")) or DispositionEstimate(
            dimension=dimension, context_scope=context_scope
        )

    def observe_verified(self, evidence: VerifiedEvidence) -> dict[str, Any] | None:
        """Update dispositions from finalized verified experience only."""
        if not self.config.enabled or not self.config.learning_enabled:
            return None
        if not evidence.verified or not evidence.executed:
            self.metrics["unverified_rejected"] = int(self.metrics["unverified_rejected"]) + 1
            return None
        if evidence.from_episode and not self.config.episodic_evidence_enabled:
            return None
        if evidence.from_procedural and not self.config.procedural_refs_enabled:
            return None
        if evidence.from_frequency_only and not self.config.frequency_only:
            # Frequency alone cannot create preference/persistence/etc. in C0.
            self.metrics["frequency_rejected"] = int(self.metrics["frequency_rejected"]) + 1
            return None
        if self.config.frequency_only and not evidence.from_frequency_only:
            # C4: only frequency proxies update (diagnostic weaker path).
            return None

        scope = evidence.context_scope
        if self.config.pool_social_contexts and _family_of(scope) == "social":
            scope = "pooled_social"

        est = self._ensure(evidence.dimension, scope, tick=evidence.tick, emit_created=True)
        prior = est.value
        signed = clamp(float(evidence.signed_outcome), -1.0, 1.0)

        # Single anomaly: confidence weaken only unless severe safety.
        if evidence.is_anomaly and not evidence.severe_safety:
            self.metrics["anomalies_seen"] = int(self.metrics["anomalies_seen"]) + 1
            est.confidence = clamp(est.confidence - ANOMALY_CONFIDENCE_DELTA)
            est.uncertainty = clamp(est.uncertainty + ANOMALY_CONFIDENCE_DELTA)
            _ring_append(
                est.contradicting_evidence_refs,
                evidence.evidence_id,
                MAX_CONTRADICTING_EVIDENCE_REFS,
            )
            est.contradiction_count += 1
            est.last_update_tick = evidence.tick
            if evidence.source_system not in est.source_systems:
                est.source_systems.append(evidence.source_system)
            self._emit(
                "individuality_disposition_updated",
                {
                    "dimension": est.dimension,
                    "context_scope": est.context_scope,
                    "prior_anchor": prior,
                    "new_anchor": est.value,
                    "confidence": est.confidence,
                    "uncertainty": est.uncertainty,
                    "causal_evidence_refs": [evidence.evidence_id],
                    "source_system": evidence.source_system,
                    "update_reason": "anomaly_confidence_weaken",
                    "tick": evidence.tick,
                    "schema_version": self.SCHEMA_VERSION,
                },
            )
            self.metrics["updates"] = int(self.metrics["updates"]) + 1
            return {"reason": "anomaly_confidence_weaken", "value": est.value, "prior": prior}

        # Direction relative to current value: support vs contradiction.
        expected_dir = 1.0 if signed >= 0 else -1.0
        current_dir = 1.0 if est.value >= 0 else -1.0
        agrees = (est.support_count == 0 and est.contradiction_count == 0) or (
            abs(est.value) < 0.05
        ) or (expected_dir == current_dir) or (signed * est.value >= 0)

        lr = self.config.learning_rate_base * est.plasticity * (1.0 - 0.5 * est.confidence)
        if self.config.frequency_only:
            lr *= 0.25  # materially weaker

        delta = lr * (signed - est.value)
        # Bound single-step change (also covers non-severe single events).
        delta = clamp(delta, -SINGLE_ANOMALY_VALUE_DELTA_MAX, SINGLE_ANOMALY_VALUE_DELTA_MAX)
        new_val = clamp(est.value + delta, -1.0, 1.0)

        if agrees or abs(est.value) < 0.05:
            est.value = new_val
            est.support_count += 1
            _ring_append(
                est.supporting_evidence_refs, evidence.evidence_id, MAX_SUPPORTING_EVIDENCE_REFS
            )
            est.confidence = clamp(est.confidence + 0.04 * abs(signed))
            est.uncertainty = clamp(1.0 - est.confidence)
            est.plasticity = clamp(est.plasticity * 0.995, 0.15, 1.0)
            reason = "evidence_support"
            event_type = "individuality_disposition_updated"
        else:
            est.contradiction_count += 1
            _ring_append(
                est.contradicting_evidence_refs,
                evidence.evidence_id,
                MAX_CONTRADICTING_EVIDENCE_REFS,
            )
            if est.contradiction_count >= REVISION_MIN_CONTRADICTIONS:
                # Sustained contradiction revises toward contradictory evidence.
                est.value = clamp(est.value + clamp(delta * 2.5, -0.2, 0.2), -1.0, 1.0)
                est.confidence = clamp(est.confidence * 0.7)
                est.uncertainty = clamp(1.0 - est.confidence)
                est.contradiction_count = 0
                reason = "sustained_contradiction_revision"
                event_type = "individuality_disposition_revised"
                self.metrics["revisions"] = int(self.metrics["revisions"]) + 1
            else:
                # Mild pull without full rewrite.
                est.value = new_val
                est.confidence = clamp(est.confidence - 0.03)
                est.uncertainty = clamp(1.0 - est.confidence)
                reason = "contradiction_soft_update"
                event_type = "individuality_disposition_updated"

        if evidence.source_system not in est.source_systems:
            est.source_systems.append(evidence.source_system)
        est.last_update_tick = evidence.tick
        self._emit(
            event_type,
            {
                "dimension": est.dimension,
                "context_scope": est.context_scope,
                "prior_anchor": prior,
                "new_anchor": est.value,
                "confidence": est.confidence,
                "uncertainty": est.uncertainty,
                "causal_evidence_refs": [evidence.evidence_id],
                "source_system": evidence.source_system,
                "update_reason": reason,
                "tick": evidence.tick,
                "schema_version": self.SCHEMA_VERSION,
            },
        )
        self.metrics["updates"] = int(self.metrics["updates"]) + 1

        # Bounded within-family generalization (never into unrelated/unsafe families).
        self._generalize(est, evidence, signed)

        return {"reason": reason, "value": est.value, "prior": prior}

    def _generalize(
        self, src: DispositionEstimate, evidence: VerifiedEvidence, signed: float
    ) -> None:
        family = _family_of(src.context_scope)
        if family is None:
            return
        # Never auto-generalize explore→hazard or persist→hazard.
        if family in ("explore", "persist"):
            unsafe = CONTEXT_FAMILIES["hazard"]
        else:
            unsafe = frozenset()
        for scope in CONTEXT_FAMILIES[family]:
            if scope == src.context_scope or scope == "default":
                continue
            if scope in unsafe:
                continue
            g = _generalization_strength(src.context_scope, scope)
            if g <= 0:
                continue
            other = self._ensure(src.dimension, scope, tick=evidence.tick, emit_created=True)
            # Modest pull only.
            pull = g * self.config.learning_rate_base * 0.35 * (signed - other.value)
            pull = clamp(pull, -0.03, 0.03)
            other.value = clamp(other.value + pull, -1.0, 1.0)
            other.last_update_tick = evidence.tick

    def modifier_for_candidate(
        self,
        cand: Candidate,
        *,
        context_scope: str = "default",
        critical_physiology: bool = False,
        tick: int = 0,
        phase_hint: float | None = None,
    ) -> float:
        """Bounded individuality score contribution. Never selects/executes."""
        if not self.config.enabled:
            return 0.0
        if critical_physiology:
            self.metrics["modifiers_suppressed_critical"] = (
                int(self.metrics["modifiers_suppressed_critical"]) + 1
            )
            self._last_modifiers[cand.capability] = 0.0
            return 0.0

        total = 0.0
        for dim, weights in DIM_CAP_WEIGHTS.items():
            w = weights.get(cand.capability)
            if not w:
                continue
            est = self.get(dim, context_scope)
            # Also blend default if contextual confidence low.
            base = self.get(dim, "default")
            val = est.value
            if est.confidence < 0.2 and base.context_scope == "default":
                val = 0.6 * val + 0.4 * base.value
            contrib = val * w * (0.3 + 0.7 * max(est.confidence, base.confidence))
            if dim == "activity_timing_preference" and phase_hint is not None:
                # Positive disposition prefers active half of the phase cycle.
                active = 1.0 if phase_hint >= 0.5 else -1.0
                if cand.capability in ("MOVE", "CHARGE", "INSPECT"):
                    contrib = val * w * active
                elif cand.capability in ("REST", "IDLE"):
                    contrib = val * w * (-active)
            total += contrib

        total = clamp(total, -self.config.modifier_abs_max, self.config.modifier_abs_max)
        self._last_modifiers[cand.capability] = total
        self.metrics["modifiers_applied"] = int(self.metrics["modifiers_applied"]) + 1
        if not self.config.modifiers_affect_arbitration:
            return 0.0  # C10: recorded but unused
        return total

    def apply_modifiers(
        self,
        scored: list[Candidate],
        *,
        context_scope: str = "default",
        critical_physiology: bool = False,
        tick: int = 0,
        phase_hint: float | None = None,
    ) -> list[Candidate]:
        for c in scored:
            mod = self.modifier_for_candidate(
                c,
                context_scope=context_scope,
                critical_physiology=critical_physiology,
                tick=tick,
                phase_hint=phase_hint,
            )
            c.scores["individuality"] = mod
            if self.config.modifiers_affect_arbitration and not critical_physiology:
                c.total += mod
        return scored

    def disposition_vector(self, context_scope: str = "default") -> dict[str, float]:
        return {dim: self.get(dim, context_scope).value for dim in DISPOSITION_DIMENSIONS}

    def internal_fingerprint_summary(self) -> dict[str, float]:
        """Internal continuity check summary — not the evaluator fingerprint."""
        out: dict[str, float] = {}
        for dim in DISPOSITION_DIMENSIONS:
            vals = [d.value for d in self.dispositions.values() if d.dimension == dim and d.active]
            out[dim] = sum(vals) / len(vals) if vals else 0.0
        return out

    def assert_no_forbidden_fields(self, state: dict[str, Any] | None = None) -> None:
        state = state if state is not None else self.to_state()
        blob = str(state)
        for k in FORBIDDEN_STATE_KEYS:
            if k in state or f'"{k}"' in blob:
                # Allow key name only inside metrics comments? Strict: key presence.
                if k in state:
                    raise IndividualityEngineError(f"forbidden_field:{k}")
        # Nested sweep
        def walk(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, val in obj.items():
                    if key in FORBIDDEN_STATE_KEYS:
                        raise IndividualityEngineError(f"forbidden_field:{key}")
                    walk(val)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(state)

    def on_restart(self) -> None:
        if self.config.reset_on_restart:
            self.dispositions.clear()
            self.initialize_neutral_anchors()
            self._event_log.clear()

    def to_state(self) -> dict[str, Any]:
        state = {
            "agent_id": self.agent_id,
            "schema_version": self.SCHEMA_VERSION,
            "config": self.config.to_state(),
            "dispositions": [d.to_state() for d in self.dispositions.values()],
            "metrics": dict(self.metrics),
            # Ledger is authoritative; do not embed event history in snapshots (RSS).
            "event_log": [],
            "last_modifiers": dict(self._last_modifiers),
            # seed stored only for paired replay of stochastic arbitration elsewhere —
            # never exposed as personality.
            "paired_seed_ref": self.seed,
        }
        self.assert_no_forbidden_fields(state)
        return state

    def accepted_state(self) -> dict[str, Any]:
        """Birth/snapshot replay equality — exclude non-deterministic diagnostics."""
        return {
            "agent_id": self.agent_id,
            "schema_version": self.SCHEMA_VERSION,
            "dispositions": sorted(
                (
                    {
                        "dimension": d.dimension,
                        "context_scope": d.context_scope,
                        "value": round(d.value, 6),
                        "confidence": round(d.confidence, 6),
                        "support_count": d.support_count,
                        "contradiction_count": d.contradiction_count,
                        "active": d.active,
                    }
                    for d in self.dispositions.values()
                ),
                key=lambda x: (x["dimension"], x["context_scope"]),
            ),
        }

    @classmethod
    def from_state(
        cls, state: dict[str, Any], config: IndividualityConfig | None = None
    ) -> IndividualityEngine:
        cfg = config or IndividualityConfig.from_state(state.get("config") or {})
        eng = cls(
            agent_id=str(state["agent_id"]),
            config=cfg,
            seed=int(state.get("paired_seed_ref", 0)),
        )
        eng.dispositions.clear()
        for d in state.get("dispositions") or []:
            est = DispositionEstimate.from_state(d)
            eng.dispositions[(est.dimension, est.context_scope)] = est
        eng.metrics = dict(state.get("metrics") or eng.metrics)
        eng._event_log = list(state.get("event_log") or [])
        eng._last_modifiers = dict(state.get("last_modifiers") or {})
        if cfg.reset_on_restart:
            eng.on_restart()
        eng.assert_no_forbidden_fields()
        return eng

    @classmethod
    def replay_from_events(
        cls,
        agent_id: str,
        events: list[dict[str, Any]],
        config: IndividualityConfig | None = None,
        *,
        seed: int = 0,
        fail_closed_missing: bool = True,
    ) -> IndividualityEngine:
        """Reconstruct individuality from authoritative events (birth replay)."""
        eng = cls.create(agent_id, config=config, seed=seed)
        # Clear birth created events for clean rebuild from ledger.
        eng.dispositions.clear()
        eng._event_log.clear()
        eng._pending_events.clear()
        eng.metrics["events_emitted"] = 0
        if not events and fail_closed_missing:
            raise IndividualityEngineError("missing_individuality_events_fail_closed")
        for ev in events:
            et = ev.get("event_type")
            if et not in AUTHORITATIVE_INDIVIDUALITY_EVENTS:
                continue
            p = ev.get("payload") or {}
            dim = p.get("dimension")
            scope = p.get("context_scope", "default")
            if not dim:
                if fail_closed_missing:
                    raise IndividualityEngineError("malformed_individuality_event")
                continue
            est = eng._ensure(str(dim), str(scope), tick=int(p.get("tick", 0)), emit_created=False)
            if et == "individuality_disposition_deactivated":
                est.active = False
                continue
            prior = float(p.get("prior_anchor", est.value))
            new = float(p.get("new_anchor", est.value))
            # Fail closed if event claims an update but anchors are inconsistent with schema.
            if "new_anchor" not in p and fail_closed_missing:
                raise IndividualityEngineError("missing_anchor_in_individuality_event")
            est.value = clamp(new, -1.0, 1.0)
            est.confidence = float(p.get("confidence", est.confidence))
            est.uncertainty = float(p.get("uncertainty", est.uncertainty))
            est.last_update_tick = int(p.get("tick", 0))
            refs = list(p.get("causal_evidence_refs") or [])
            for r in refs:
                _ring_append(est.supporting_evidence_refs, r, MAX_SUPPORTING_EVIDENCE_REFS)
            if et == "individuality_disposition_revised":
                eng.metrics["revisions"] = int(eng.metrics["revisions"]) + 1
            # Keep event log authoritative.
            eng._event_log.append(
                {"event_type": et, "payload": dict(p), "event_id": ev.get("event_id") or new_id()}
            )
            _ = prior  # provenance inspectability
        if not eng.dispositions and fail_closed_missing:
            raise IndividualityEngineError("replay_produced_empty_individuality")
        # Ensure all required dimensions exist (neutral if never updated).
        for dim in DISPOSITION_DIMENSIONS:
            eng._ensure(dim, "default", tick=0, emit_created=False)
        return eng


def infer_evidence_from_outcome(
    *,
    evidence_id: str,
    tick: int,
    capability: str,
    success: bool,
    context_scope: str,
    verified: bool = True,
    source_system: str = "outcome",
    history_hint: str | None = None,
    is_anomaly: bool = False,
    severe_safety: bool = False,
    from_episode: bool = True,
    from_procedural: bool = False,
    from_frequency_only: bool = False,
) -> list[VerifiedEvidence]:
    """Map a verified action outcome into one or more disposition evidence items.

    History labels are NOT stored — only context_scope + signed outcomes.
    `history_hint` is harness-only and must not be persisted on the engine.
    """
    if not verified:
        return []
    sign = 1.0 if success else -1.0
    items: list[VerifiedEvidence] = []

    def add(dim: str, scope: str, signed: float) -> None:
        items.append(
            VerifiedEvidence(
                evidence_id=f"{evidence_id}:{dim}:{scope}",
                tick=tick,
                source_system=source_system,
                dimension=dim,
                context_scope=scope,
                signed_outcome=signed,
                verified=True,
                executed=True,
                severe_safety=severe_safety,
                is_anomaly=is_anomaly,
                from_episode=from_episode,
                from_procedural=from_procedural,
                from_frequency_only=from_frequency_only,
                action=capability,
            )
        )

    # Default capability→dimension mapping (context from caller).
    if capability in ("MOVE", "ORIENT") and context_scope in (
        "safe_explore",
        "novelty_probe",
        "default",
    ):
        add("exploration_tendency", context_scope if context_scope != "default" else "safe_explore", sign)
    if capability in ("INSPECT", "APPROACH") and context_scope in (
        "novelty_probe",
        "safe_explore",
        "object_family_a",
        "object_family_b",
        "default",
    ):
        scope = context_scope if context_scope != "default" else "novelty_probe"
        add("novelty_tolerance", scope, sign)
    if capability in ("INSPECT", "CHARGE", "APPROACH") and context_scope in (
        "solvable_task",
        "practice",
        "default",
    ):
        scope = context_scope if context_scope != "default" else "solvable_task"
        add("persistence_after_failure", scope, sign if success else -abs(sign))
    if capability in ("RETREAT", "IDLE", "APPROACH") and context_scope in (
        "uncertain_hazard",
        "integrity_risk",
        "default",
    ):
        scope = "uncertain_hazard" if context_scope == "default" else context_scope
        # Success on RETREAT under hazard supports caution; success on APPROACH under hazard opposes it.
        if capability == "RETREAT":
            add("uncertainty_caution", scope, abs(sign) if success else -0.5)
        elif capability == "APPROACH":
            add("uncertainty_caution", scope, -sign)
    if capability == "INSPECT" and context_scope in ("high_stim", "inspect_activity", "default"):
        scope = "high_stim" if context_scope == "default" else context_scope
        add("stimulation_tolerance", scope, sign)
    if capability in ("REST", "IDLE") and context_scope in (
        "post_stim_recovery",
        "rest_pacing",
        "default",
    ):
        scope = "post_stim_recovery" if context_scope == "default" else context_scope
        add("recovery_pacing", scope, sign)
    if context_scope in ("diurnal_phase", "routine_window"):
        add("activity_timing_preference", context_scope, sign)
    if capability in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE", "APPROACH") and context_scope in (
        "play_context",
        "assistance_context",
        "pooled_social",
        "default",
    ):
        scope = "play_context" if context_scope == "default" else context_scope
        add("social_initiative_by_context", scope, sign)

    _ = history_hint  # harness-only; deliberately unused for state
    return items
