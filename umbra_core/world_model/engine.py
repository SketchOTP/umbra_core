"""D-003 predictive world model — entities, transitions, affordances, planning.

Narrow embodied environment model learned from uncertain observations and
verified outcomes. Not general intelligence. Predictions are never verified
facts. Learned models propose actions only — never grant authority.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from umbra_core.identity import deterministic_id
from umbra_core.util import BoundedRing, clamp, new_id, sha256_hex, canon_json


MAX_ENTITIES = 32
MAX_TRANSITION_MODELS = 64
MAX_AFFORDANCES = 128
MAX_OBSERVATION_HISTORY = 256
MAX_PREDICTION_HISTORY = 256
MAX_CONTRADICTION_HISTORY = 64
MAX_PLAN_TRACES = 32
MAX_PLAN_DEPTH = 4
MAX_CANDIDATE_PLANS = 32
MAX_PLAN_RETRIES = 4

# Preregistered revision thresholds
SINGLE_ANOMALY_CEILING = 1
SUPERSEDE_CONTRADICTION_THRESHOLD = 8
SUPERSEDE_SUPPORT_MIN = 5
PERSISTENCE_DECAY_PER_TICK = 0.015
REIDENTIFY_DISTANCE_THRESHOLD = 3.5
REIDENTIFY_CONFIDENCE_THRESHOLD = 0.35

AFFORDANCE_ACTIONS = (
    "approach",
    "inspect",
    "avoid",
    "rest_near",
    "charge_from",
    "pass_through",
    "collide_with",
)

# Map organism capabilities → affordance labels for learning
CAPABILITY_TO_AFFORDANCE = {
    "APPROACH": "approach",
    "INSPECT": "inspect",
    "RETREAT": "avoid",
    "REST": "rest_near",
    "CHARGE": "charge_from",
    "MOVE": "pass_through",
    "MANIPULATE": "use",
}

REQUIRED_ENVIRONMENTAL_ANCHOR_KEYS = (
    "execution_id",
    "request_id",
    "target_object_id",
    "target_address_ref",
    "perception_evidence_ref",
    "object_definition_hash",
    "affordance_definition_hash",
    "committed_habitat_version",
)
MAX_PROCESSED_ENVIRONMENTAL_EXECUTIONS = 256


class ModelStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    WEAKENED = "WEAKENED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class FactKind(str, Enum):
    """Distinguish observation / memory / prediction / verified / unknown."""

    CURRENT_OBSERVATION = "CURRENT_OBSERVATION"
    REMEMBERED_ESTIMATE = "REMEMBERED_ESTIMATE"
    PREDICTION = "PREDICTION"
    VERIFIED_OUTCOME = "VERIFIED_OUTCOME"
    UNKNOWN = "UNKNOWN"


@dataclass
class WorldEntity:
    entity_id: str
    entity_kind: str
    estimated_state: dict[str, float]  # relative_direction, estimated_distance
    last_observed_at: float
    confidence: float
    uncertainty: float
    persistence_probability: float
    evidence_count: int
    fact_kind: str = FactKind.UNKNOWN.value
    last_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorldEntity:
        return cls(
            entity_id=str(d["entity_id"]),
            entity_kind=str(d["entity_kind"]),
            estimated_state={k: float(v) for k, v in d.get("estimated_state", {}).items()},
            last_observed_at=float(d.get("last_observed_at", 0.0)),
            confidence=float(d.get("confidence", 0.0)),
            uncertainty=float(d.get("uncertainty", 1.0)),
            persistence_probability=float(d.get("persistence_probability", 0.5)),
            evidence_count=int(d.get("evidence_count", 0)),
            fact_kind=str(d.get("fact_kind", FactKind.UNKNOWN.value)),
            last_tick=int(d.get("last_tick", 0)),
        )


@dataclass
class TransitionModel:
    model_id: str
    conditions: dict[str, Any]  # entity_kind, context keys
    action: str
    predicted_effect: dict[str, float]
    latency: float
    confidence: float
    support_count: int
    contradiction_count: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TransitionModel:
        return cls(
            model_id=str(d["model_id"]),
            conditions=dict(d.get("conditions", {})),
            action=str(d["action"]),
            predicted_effect={k: float(v) for k, v in d.get("predicted_effect", {}).items()},
            latency=float(d.get("latency", 0.0)),
            confidence=float(d.get("confidence", 0.0)),
            support_count=int(d.get("support_count", 0)),
            contradiction_count=int(d.get("contradiction_count", 0)),
            status=str(d.get("status", ModelStatus.CANDIDATE.value)),
        )


@dataclass
class AffordanceBelief:
    affordance_id: str
    entity_kind: str
    action: str
    support_count: int
    contradiction_count: int
    confidence: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AffordanceBelief:
        return cls(
            affordance_id=str(d["affordance_id"]),
            entity_kind=str(d["entity_kind"]),
            action=str(d["action"]),
            support_count=int(d.get("support_count", 0)),
            contradiction_count=int(d.get("contradiction_count", 0)),
            confidence=float(d.get("confidence", 0.0)),
            status=str(d.get("status", ModelStatus.CANDIDATE.value)),
        )


@dataclass
class WorldPrediction:
    prediction_id: str
    tick: int
    action: str
    entity_kind: str | None
    predicted_world_change: dict[str, float]
    expected_observations: list[str]
    prediction_confidence: float
    uncertainty: float
    model_ids: list[str]
    fact_kind: str = FactKind.PREDICTION.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorldPrediction:
        return cls(
            prediction_id=str(d["prediction_id"]),
            tick=int(d["tick"]),
            action=str(d["action"]),
            entity_kind=d.get("entity_kind"),
            predicted_world_change={
                k: float(v) for k, v in d.get("predicted_world_change", {}).items()
            },
            expected_observations=list(d.get("expected_observations", [])),
            prediction_confidence=float(d.get("prediction_confidence", 0.0)),
            uncertainty=float(d.get("uncertainty", 1.0)),
            model_ids=list(d.get("model_ids", [])),
            fact_kind=str(d.get("fact_kind", FactKind.PREDICTION.value)),
        )


@dataclass
class PlanTrace:
    plan_id: str
    tick: int
    goal: str
    actions: list[str]
    depth: int
    retries: int
    predicted_success: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlanTrace:
        return cls(
            plan_id=str(d["plan_id"]),
            tick=int(d["tick"]),
            goal=str(d["goal"]),
            actions=list(d.get("actions", [])),
            depth=int(d.get("depth", 0)),
            retries=int(d.get("retries", 0)),
            predicted_success=float(d.get("predicted_success", 0.0)),
        )


@dataclass
class WorldModelConfig:
    """Experiment / ablation switches for D-003 conditions C0–C8."""

    learning_enabled: bool = True  # C0
    fixed_authored: bool = False  # C1
    prediction_enabled: bool = True  # C2 off
    affordance_learning: bool = True  # C3 off
    contradiction_revision: bool = True  # C4 off
    object_persistence: bool = True  # C5 off
    planning_enabled: bool = True  # C6 off
    randomize_retrieval: bool = False  # C7
    # Bounds
    max_entities: int = MAX_ENTITIES
    max_models: int = MAX_TRANSITION_MODELS
    max_affordances: int = MAX_AFFORDANCES
    max_plan_depth: int = MAX_PLAN_DEPTH
    max_candidate_plans: int = MAX_CANDIDATE_PLANS
    max_plan_retries: int = MAX_PLAN_RETRIES


def condition_to_world_model_config(condition: str) -> WorldModelConfig:
    c = WorldModelConfig()
    if condition == "C0":
        return c
    if condition == "C1":
        c.fixed_authored = True
        c.learning_enabled = False
        return c
    if condition == "C2":
        c.prediction_enabled = False
        return c
    if condition == "C3":
        c.affordance_learning = False
        return c
    if condition == "C4":
        c.contradiction_revision = False
        return c
    if condition == "C5":
        c.object_persistence = False
        return c
    if condition == "C6":
        c.planning_enabled = False
        return c
    if condition == "C7":
        c.randomize_retrieval = True
        return c
    if condition == "C8":
        # random policy handled via arbitration; keep model on
        return c
    return c


@dataclass
class WorldModel:
    """Learned environment knowledge — separate from body schema."""

    agent_id: str
    entities: dict[str, WorldEntity] = field(default_factory=dict)
    models: dict[str, TransitionModel] = field(default_factory=dict)
    affordances: dict[str, AffordanceBelief] = field(default_factory=dict)
    predictions: BoundedRing[WorldPrediction] = field(
        default_factory=lambda: BoundedRing(MAX_PREDICTION_HISTORY)
    )
    contradictions: BoundedRing[dict[str, Any]] = field(
        default_factory=lambda: BoundedRing(MAX_CONTRADICTION_HISTORY)
    )
    supersessions: BoundedRing[dict[str, Any]] = field(
        default_factory=lambda: BoundedRing(MAX_TRANSITION_MODELS)
    )
    plan_traces: BoundedRing[PlanTrace] = field(
        default_factory=lambda: BoundedRing(MAX_PLAN_TRACES)
    )
    observation_log: BoundedRing[dict[str, Any]] = field(
        default_factory=lambda: BoundedRing(MAX_OBSERVATION_HISTORY)
    )
    config: WorldModelConfig = field(default_factory=WorldModelConfig)
    seed: int | None = None
    _pending_prediction: WorldPrediction | None = field(default=None, repr=False)
    _plan_retries: dict[str, int] = field(default_factory=dict)
    _bounded_initialized: bool = False
    _prediction_errors: BoundedRing[float] = field(
        default_factory=lambda: BoundedRing(MAX_PREDICTION_HISTORY), repr=False
    )
    _external_move_ticks: list[int] = field(default_factory=list)
    _processed_environmental_executions: dict[str, dict[str, Any]] = field(
        default_factory=dict, repr=False
    )
    metrics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        agent_id: str,
        *,
        config: WorldModelConfig | None = None,
        seed: int | None = None,
    ) -> WorldModel:
        cfg = config or WorldModelConfig()
        wm = cls(
            agent_id=agent_id,
            config=cfg,
            seed=seed,
            predictions=BoundedRing(MAX_PREDICTION_HISTORY),
            contradictions=BoundedRing(MAX_CONTRADICTION_HISTORY),
            supersessions=BoundedRing(cfg.max_models),
            plan_traces=BoundedRing(MAX_PLAN_TRACES),
            observation_log=BoundedRing(MAX_OBSERVATION_HISTORY),
            _prediction_errors=BoundedRing(MAX_PREDICTION_HISTORY),
        )
        if cfg.fixed_authored:
            wm._seed_authored_priors(seed)
        return wm

    def _seed_authored_priors(self, seed: int | None) -> None:
        """C1: fixed authored assumptions (not learned from experience)."""
        priors = {
            ("resource", "CHARGE"): {"success": 1.0, "energy_delta": 0.15},
            ("rest", "REST"): {"success": 1.0, "fatigue_delta": -0.1},
            ("hazard", "APPROACH"): {"success": 0.0, "integrity_delta": -0.2},
            ("inspect", "INSPECT"): {"success": 1.0},
        }
        for i, ((kind, action), effect) in enumerate(priors.items()):
            mid = (
                deterministic_id(int(seed or 0), f"authored:{kind}:{action}")
                if seed is not None
                else new_id()
            )
            self.models[mid] = TransitionModel(
                model_id=mid,
                conditions={"entity_kind": kind},
                action=action,
                predicted_effect=dict(effect),
                latency=0.0,
                confidence=0.9,
                support_count=0,
                contradiction_count=0,
                status=ModelStatus.ACTIVE.value,
            )
            aid = f"aff-{kind}-{CAPABILITY_TO_AFFORDANCE.get(action, action.lower())}"
            self.affordances[aid] = AffordanceBelief(
                affordance_id=aid,
                entity_kind=kind,
                action=CAPABILITY_TO_AFFORDANCE.get(action, action.lower()),
                support_count=10,
                contradiction_count=0,
                confidence=0.9,
                status=ModelStatus.ACTIVE.value,
            )

    def initialize_bounded_collections(self) -> None:
        if self._bounded_initialized:
            return
        self._pad_rings()
        self._bounded_initialized = True

    def _pad_rings(self) -> None:
        while len(self.predictions) < self.predictions.maxlen:
            self.predictions.append(
                WorldPrediction(
                    prediction_id="init",
                    tick=-1,
                    action="IDLE",
                    entity_kind=None,
                    predicted_world_change={},
                    expected_observations=[],
                    prediction_confidence=0.0,
                    uncertainty=1.0,
                    model_ids=[],
                )
            )
        while len(self.contradictions) < self.contradictions.maxlen:
            self.contradictions.append({"tick": -1, "init": True})
        while len(self.plan_traces) < self.plan_traces.maxlen:
            self.plan_traces.append(
                PlanTrace(
                    plan_id="init",
                    tick=-1,
                    goal="",
                    actions=[],
                    depth=0,
                    retries=0,
                    predicted_success=0.0,
                )
            )
        while len(self.observation_log) < self.observation_log.maxlen:
            self.observation_log.append({"tick": -1, "init": True})
        while len(self._prediction_errors) < self._prediction_errors.maxlen:
            self._prediction_errors.append(-1.0)

    def _ring_write(self, ring: BoundedRing[Any], item: Any) -> None:
        """In-place overwrite when full (steady RSS)."""
        old = ring.reclaim_oldest()
        if old is None:
            ring.append(item)
            return
        if hasattr(old, "__dict__") and hasattr(item, "__dict__"):
            old.__dict__.clear()
            old.__dict__.update(item.__dict__)
            ring.advance_after_reclaim()
        elif isinstance(old, dict) and isinstance(item, dict):
            old.clear()
            old.update(item)
            ring.advance_after_reclaim()
        else:
            ring.append(item)

    # --- Entity / observation -------------------------------------------------

    def ingest_observations(
        self,
        observations: list[dict[str, Any]],
        *,
        tick: int,
        now: float,
    ) -> list[str]:
        """Update entities from sensor observations. Never reads world truth."""
        seen_kinds: set[str] = set()
        reidentified: list[str] = []
        for o in observations:
            kind = str(o.get("kind", "unknown"))
            seen_kinds.add(kind)
            est = {
                "relative_direction": float(o.get("relative_direction", 0.0)),
                "estimated_distance": float(o.get("estimated_distance", 0.0)),
            }
            conf = float(o.get("confidence", 0.5))
            unc = float(o.get("uncertainty", 0.5))
            existing = self._find_entity(kind, est)
            if existing is not None:
                # re-identification of remembered entity
                was_remembered = existing.fact_kind == FactKind.REMEMBERED_ESTIMATE.value
                existing.estimated_state = est
                existing.last_observed_at = now
                existing.last_tick = tick
                existing.confidence = clamp(0.5 * existing.confidence + 0.5 * conf)
                existing.uncertainty = unc
                existing.persistence_probability = clamp(
                    existing.persistence_probability + 0.1
                )
                existing.evidence_count += 1
                existing.fact_kind = FactKind.CURRENT_OBSERVATION.value
                if was_remembered:
                    reidentified.append(existing.entity_id)
            else:
                eid = (
                    deterministic_id(int(self.seed or 0), f"ent:{kind}:{tick}")
                    if self.seed is not None
                    else new_id()
                )
                if len(self.entities) >= self.config.max_entities:
                    self._evict_weakest_entity()
                self.entities[eid] = WorldEntity(
                    entity_id=eid,
                    entity_kind=kind,
                    estimated_state=est,
                    last_observed_at=now,
                    confidence=conf,
                    uncertainty=unc,
                    persistence_probability=0.7,
                    evidence_count=1,
                    fact_kind=FactKind.CURRENT_OBSERVATION.value,
                    last_tick=tick,
                )
            self._ring_write(
                self.observation_log,
                {
                    "tick": tick,
                    "kind": kind,
                    "est": est,
                    "confidence": conf,
                    "fact_kind": FactKind.CURRENT_OBSERVATION.value,
                },
            )

        # Persistence decay for unobserved
        if self.config.object_persistence:
            for ent in list(self.entities.values()):
                if ent.entity_kind not in seen_kinds:
                    ent.fact_kind = FactKind.REMEMBERED_ESTIMATE.value
                    ent.confidence = clamp(ent.confidence - PERSISTENCE_DECAY_PER_TICK)
                    ent.uncertainty = clamp(ent.uncertainty + PERSISTENCE_DECAY_PER_TICK)
                    ent.persistence_probability = clamp(
                        ent.persistence_probability - PERSISTENCE_DECAY_PER_TICK
                    )
                    # predicted location is NOT observation
                    if ent.confidence < 0.05:
                        del self.entities[ent.entity_id]
        else:
            # C5: drop unobserved immediately
            for eid, ent in list(self.entities.items()):
                if ent.entity_kind not in seen_kinds:
                    del self.entities[eid]
        return reidentified

    def _find_entity(self, kind: str, est: dict[str, float]) -> WorldEntity | None:
        best = None
        best_d = float("inf")
        for ent in self.entities.values():
            if ent.entity_kind != kind:
                continue
            d = abs(
                ent.estimated_state.get("estimated_distance", 0.0)
                - est.get("estimated_distance", 0.0)
            )
            if d < best_d:
                best, best_d = ent, d
        if best is None:
            return None
        if best.fact_kind == FactKind.CURRENT_OBSERVATION.value:
            return best  # same-kind refresh
        if (
            best.confidence >= REIDENTIFY_CONFIDENCE_THRESHOLD
            and best_d <= REIDENTIFY_DISTANCE_THRESHOLD
        ):
            return best
        # same kind always merges (bounded habitat: one feature per kind typically)
        return best

    def _evict_weakest_entity(self) -> None:
        if not self.entities:
            return
        weakest = min(self.entities.values(), key=lambda e: e.confidence)
        del self.entities[weakest.entity_id]

    # --- Prediction -----------------------------------------------------------

    def predict(
        self,
        action: str,
        params: dict[str, Any],
        *,
        tick: int,
    ) -> WorldPrediction | None:
        if not self.config.prediction_enabled:
            return None
        toward = params.get("toward") or params.get("from")
        entity_kind = str(toward) if toward else None
        models = self._retrieve_models(action, entity_kind)
        effect: dict[str, float] = {}
        confs: list[float] = []
        mids: list[str] = []
        weight = 0.0
        for m in models:
            w = max(0.05, m.confidence)
            for k, v in m.predicted_effect.items():
                effect[k] = effect.get(k, 0.0) + v * w
            weight += w
            confs.append(m.confidence)
            mids.append(m.model_id)
        if weight > 0:
            effect = {k: v / weight for k, v in effect.items()}
        if "success" in effect:
            effect["success"] = clamp(effect["success"])
        if not models and self.config.fixed_authored:
            effect = {"success": 0.5}
            confs = [0.3]
        pred_conf = sum(confs) / len(confs) if confs else 0.2
        expected = []
        if entity_kind:
            expected.append(entity_kind)
        pred = WorldPrediction(
            prediction_id=new_id(),
            tick=tick,
            action=action,
            entity_kind=entity_kind,
            predicted_world_change=effect,
            expected_observations=expected,
            prediction_confidence=pred_conf,
            uncertainty=clamp(1.0 - pred_conf),
            model_ids=mids,
            fact_kind=FactKind.PREDICTION.value,
        )
        self._pending_prediction = pred
        self._ring_write(self.predictions, pred)
        return pred

    def _retrieve_models(
        self, action: str, entity_kind: str | None
    ) -> list[TransitionModel]:
        pool = [
            m
            for m in self.models.values()
            if m.status in (ModelStatus.ACTIVE.value, ModelStatus.CANDIDATE.value, ModelStatus.WEAKENED.value)
            and m.action == action
            and (
                entity_kind is None
                or m.conditions.get("entity_kind") == entity_kind
                or m.conditions.get("entity_kind") is None
            )
        ]
        if self.config.randomize_retrieval and pool:
            # C7: shuffle order / pick poorly
            pool = list(reversed(pool))
            if len(pool) > 1:
                pool = pool[1:] + pool[:1]
        # Prefer ACTIVE, then by confidence
        pool.sort(
            key=lambda m: (
                0 if m.status == ModelStatus.ACTIVE.value else 1,
                -m.confidence,
            )
        )
        return pool[:4]

    # --- Outcome update -------------------------------------------------------

    def observe_outcome(
        self,
        *,
        tick: int,
        action: str | None,
        params: dict[str, Any] | None,
        verified_outcome: dict[str, Any] | None,
        observations: list[dict[str, Any]],
        action_issued: bool,
        now: float,
    ) -> dict[str, Any]:
        """Compare prediction to verified outcome; revise models. Never treat prediction as fact."""
        result: dict[str, Any] = {
            "prediction_error": None,
            "adapted": False,
            "reidentified": [],
            "external_not_self": False,
        }
        # Observations already ingested at tick start; only detect external shift here.
        if not action_issued and verified_outcome is None:
            moved = self._detect_unexpected_entity_shift(observations, tick)
            if moved:
                self._external_move_ticks.append(tick)
                result["external_not_self"] = True
            self._pending_prediction = None
            return result

        if verified_outcome is None or action is None:
            self._pending_prediction = None
            return result

        # Verified outcomes are facts; predictions are not.
        verified = dict(verified_outcome)
        verified["fact_kind"] = FactKind.VERIFIED_OUTCOME.value
        success = bool(verified.get("success"))
        toward = (params or {}).get("toward") or (params or {}).get("from")
        entity_kind = str(toward) if toward else self._infer_kind_from_obs(observations)

        pred = self._pending_prediction
        error = 0.0
        if pred is not None and self.config.prediction_enabled:
            expected_success = pred.predicted_world_change.get("success", 0.5)
            error = abs(expected_success - (1.0 if success else 0.0))
            # Gate1: only score action-conditioned predictions with entity context
            # or interaction capabilities (not bare IDLE wander).
            scoreable = (
                pred.entity_kind is not None
                or action in ("CHARGE", "REST", "INSPECT", "APPROACH", "RETREAT", "MOVE")
            ) and (pred.model_ids or pred.entity_kind is not None or action in ("CHARGE", "REST", "INSPECT"))
            if scoreable:
                self._ring_write(self._prediction_errors, error)
                result["prediction_error"] = {
                    "tick": tick,
                    "error": error,
                    "prediction_id": pred.prediction_id,
                    "fact_kind_prediction": FactKind.PREDICTION.value,
                    "fact_kind_verified": FactKind.VERIFIED_OUTCOME.value,
                }

        if self.config.learning_enabled and not self.config.fixed_authored:
            self._update_transition(
                action=action,
                entity_kind=entity_kind,
                success=success,
                verified=verified,
                error=error,
                tick=tick,
            )
            if self.config.affordance_learning:
                self._update_affordance(action, entity_kind, success, tick)

        self._pending_prediction = None
        return result

    def observe_environmental_outcome(
        self,
        *,
        anchors: dict[str, Any],
        verified_outcome: dict[str, Any] | None,
        tick: int,
        terminal: bool = True,
        denied: bool = False,
        stale_binding: bool = False,
        object_kind: str | None = None,
        current_habitat_version: int | None = None,
        current_object_definition_hash: str | None = None,
        current_affordance_definition_hash: str | None = None,
    ) -> dict[str, Any]:
        """Learn from governed MANIPULATE outcomes with full evidence anchors.

        Idempotent by execution_id. Rejects incomplete, denied, stale, or
        non-terminal bindings. Does not treat action frequency as preference.
        """
        result: dict[str, Any] = {
            "adapted": False,
            "rejected": False,
            "reason": None,
            "duplicate": False,
        }
        if denied:
            result["rejected"] = True
            result["reason"] = "denied_proposal"
            return result
        if not terminal:
            result["rejected"] = True
            result["reason"] = "nonterminal_execution"
            return result
        if stale_binding:
            result["rejected"] = True
            result["reason"] = "stale_binding"
            return result

        missing = [k for k in REQUIRED_ENVIRONMENTAL_ANCHOR_KEYS if not anchors.get(k)]
        if missing:
            result["rejected"] = True
            result["reason"] = f"incomplete_anchors:{','.join(missing)}"
            return result

        execution_id = str(anchors["execution_id"])
        if execution_id in self._processed_environmental_executions:
            result["duplicate"] = True
            result["prior"] = dict(self._processed_environmental_executions[execution_id])
            return result

        if verified_outcome is None or not verified_outcome.get("verified", True):
            result["rejected"] = True
            result["reason"] = "unverified_outcome"
            return result

        committed_version = int(anchors["committed_habitat_version"])
        if (
            current_habitat_version is not None
            and committed_version != current_habitat_version
        ):
            result["rejected"] = True
            result["reason"] = "stale_habitat_version"
            return result
        if (
            current_object_definition_hash is not None
            and str(anchors["object_definition_hash"])
            != str(current_object_definition_hash)
        ):
            result["rejected"] = True
            result["reason"] = "obsolete_object_definition"
            return result
        if (
            current_affordance_definition_hash is not None
            and str(anchors["affordance_definition_hash"])
            != str(current_affordance_definition_hash)
        ):
            result["rejected"] = True
            result["reason"] = "obsolete_affordance_definition"
            return result

        success = bool(verified_outcome.get("success"))
        kind = object_kind or str(anchors.get("perceived_object_kind") or "habitat_object")
        verified = dict(verified_outcome)
        verified["fact_kind"] = FactKind.VERIFIED_OUTCOME.value
        verified["execution_id"] = execution_id

        models_before = len(self.models)
        if self.config.learning_enabled and not self.config.fixed_authored:
            self._update_transition(
                action="MANIPULATE",
                entity_kind=kind,
                success=success,
                verified=verified,
                error=0.0 if success else 1.0,
                tick=tick,
            )
            if self.config.affordance_learning:
                self._update_affordance("MANIPULATE", kind, success, tick)

        record = {
            "tick": tick,
            "success": success,
            "entity_kind": kind,
            "models_delta": len(self.models) - models_before,
        }
        self._processed_environmental_executions[execution_id] = record
        if len(self._processed_environmental_executions) > MAX_PROCESSED_ENVIRONMENTAL_EXECUTIONS:
            oldest = next(iter(self._processed_environmental_executions))
            self._processed_environmental_executions.pop(oldest, None)

        result["adapted"] = record["models_delta"] != 0 or success
        result["record"] = record
        return result

    def _infer_kind_from_obs(self, observations: list[dict[str, Any]]) -> str | None:
        if not observations:
            return None
        return str(observations[0].get("kind"))

    def _detect_unexpected_entity_shift(
        self, observations: list[dict[str, Any]], tick: int
    ) -> bool:
        for o in observations:
            kind = str(o.get("kind"))
            for ent in self.entities.values():
                if ent.entity_kind != kind:
                    continue
                if ent.fact_kind != FactKind.REMEMBERED_ESTIMATE.value:
                    continue
                d0 = ent.estimated_state.get("estimated_distance", 0.0)
                d1 = float(o.get("estimated_distance", d0))
                if abs(d1 - d0) > 2.0:
                    return True
        return False

    def _update_transition(
        self,
        *,
        action: str,
        entity_kind: str | None,
        success: bool,
        verified: dict[str, Any],
        error: float,
        tick: int,
    ) -> None:
        key_kind = entity_kind or "any"
        matching = [
            m
            for m in self.models.values()
            if m.action == action
            and m.conditions.get("entity_kind") == key_kind
            and m.status != ModelStatus.REJECTED.value
            and m.status != ModelStatus.SUPERSEDED.value
        ]
        effect = {
            "success": 1.0 if success else 0.0,
        }
        if "effects" in verified and isinstance(verified["effects"], dict):
            for k, v in verified["effects"].items():
                effect[f"phys_{k}"] = float(v)

        if not matching:
            if len(self.models) >= self.config.max_models:
                self._evict_weakest_model()
            mid = new_id()
            self.models[mid] = TransitionModel(
                model_id=mid,
                conditions={"entity_kind": key_kind},
                action=action,
                predicted_effect=effect,
                latency=0.0,
                confidence=0.35,
                support_count=1 if success else 0,
                contradiction_count=0 if success else 1,
                status=ModelStatus.CANDIDATE.value,
            )
            return

        for m in matching:
            predicted_ok = m.predicted_effect.get("success", 0.5) >= 0.5
            agrees = predicted_ok == success
            if agrees:
                m.support_count += 1
                m.confidence = clamp(m.confidence + 0.04)
                # blend effect
                for k, v in effect.items():
                    old = m.predicted_effect.get(k, v)
                    m.predicted_effect[k] = 0.8 * old + 0.2 * v
                if m.support_count >= 3 and m.status == ModelStatus.CANDIDATE.value:
                    m.status = ModelStatus.ACTIVE.value
                if m.status == ModelStatus.WEAKENED.value and m.support_count > m.contradiction_count + 2:
                    m.status = ModelStatus.ACTIVE.value
            else:
                # Single anomaly must not rewrite established model
                m.contradiction_count += 1
                self._ring_write(
                    self.contradictions,
                    {
                        "tick": tick,
                        "model_id": m.model_id,
                        "action": action,
                        "entity_kind": key_kind,
                        "predicted_success": predicted_ok,
                        "verified_success": success,
                    },
                )
                if not self.config.contradiction_revision:
                    continue
                if m.support_count >= SUPERSEDE_SUPPORT_MIN and m.contradiction_count <= SINGLE_ANOMALY_CEILING:
                    # retain; do not rewrite
                    continue
                if m.contradiction_count >= 3:
                    m.status = ModelStatus.WEAKENED.value
                    m.confidence = clamp(m.confidence - 0.08)
                if (
                    m.contradiction_count >= SUPERSEDE_CONTRADICTION_THRESHOLD
                    and m.support_count >= SUPERSEDE_SUPPORT_MIN
                ):
                    self._supersede_model(m, effect, tick)

    def _supersede_model(
        self, old: TransitionModel, new_effect: dict[str, float], tick: int
    ) -> None:
        old.status = ModelStatus.SUPERSEDED.value
        mid = new_id()
        record = {
            "tick": tick,
            "old_model_id": old.model_id,
            "new_model_id": mid,
            "old_effect": dict(old.predicted_effect),
            "old_support": old.support_count,
            "old_contradictions": old.contradiction_count,
            "action": old.action,
            "conditions": dict(old.conditions),
        }
        self._ring_write(self.supersessions, record)
        # Remove superseded from active map (inspectable via supersessions ring)
        if old.model_id in self.models:
            del self.models[old.model_id]
        if len(self.models) >= self.config.max_models:
            self._evict_weakest_model()
        self.models[mid] = TransitionModel(
            model_id=mid,
            conditions=dict(old.conditions),
            action=old.action,
            predicted_effect=dict(new_effect),
            latency=old.latency,
            confidence=0.4,
            support_count=1,
            contradiction_count=0,
            status=ModelStatus.ACTIVE.value,
        )
        self.metrics["supersessions"] = int(self.metrics.get("supersessions", 0)) + 1

    def _evict_weakest_model(self) -> None:
        for status in (
            ModelStatus.SUPERSEDED.value,
            ModelStatus.REJECTED.value,
            ModelStatus.WEAKENED.value,
            ModelStatus.CANDIDATE.value,
        ):
            cands = [m for m in self.models.values() if m.status == status]
            if cands:
                weakest = min(cands, key=lambda m: (m.confidence, m.support_count))
                del self.models[weakest.model_id]
                return
        cands = list(self.models.values())
        if not cands:
            return
        weakest = min(cands, key=lambda m: m.confidence)
        del self.models[weakest.model_id]

    def _update_affordance(
        self, action: str, entity_kind: str | None, success: bool, tick: int
    ) -> None:
        if entity_kind is None:
            return
        aff_action = CAPABILITY_TO_AFFORDANCE.get(action)
        if aff_action is None:
            return
        # Hazard contact on approach → collide / avoid learning
        key = f"aff-{entity_kind}-{aff_action}"
        bel = self.affordances.get(key)
        if bel is None:
            if len(self.affordances) >= self.config.max_affordances:
                weakest = min(self.affordances.values(), key=lambda a: a.confidence)
                del self.affordances[weakest.affordance_id]
            bel = AffordanceBelief(
                affordance_id=key,
                entity_kind=entity_kind,
                action=aff_action,
                support_count=0,
                contradiction_count=0,
                confidence=0.3,
                status=ModelStatus.CANDIDATE.value,
            )
            self.affordances[key] = bel
        if success:
            bel.support_count += 1
            bel.confidence = clamp(bel.confidence + 0.05)
            if bel.support_count >= 3:
                bel.status = ModelStatus.ACTIVE.value
        else:
            bel.contradiction_count += 1
            bel.confidence = clamp(bel.confidence - 0.06)
            if bel.contradiction_count >= 4 and bel.contradiction_count > bel.support_count:
                bel.status = ModelStatus.WEAKENED.value
                # revise false affordance
                if self.config.contradiction_revision and bel.contradiction_count >= 6:
                    bel.status = ModelStatus.SUPERSEDED.value
                    # learn opposite when approach fails near hazard-like
                    if aff_action == "approach":
                        avoid_key = f"aff-{entity_kind}-avoid"
                        if avoid_key not in self.affordances:
                            self.affordances[avoid_key] = AffordanceBelief(
                                affordance_id=avoid_key,
                                entity_kind=entity_kind,
                                action="avoid",
                                support_count=1,
                                contradiction_count=0,
                                confidence=0.4,
                                status=ModelStatus.ACTIVE.value,
                            )

    # --- Planning -------------------------------------------------------------

    def plan(
        self,
        goal: str,
        *,
        tick: int,
        observations: list[dict[str, Any]],
    ) -> PlanTrace | None:
        """Bounded composition of learned transitions. Proposes actions only."""
        if not self.config.planning_enabled:
            return None
        retries = self._plan_retries.get(goal, 0)
        if retries >= self.config.max_plan_retries:
            return None

        # Simple goal → action sequence from affordances + models
        depth_limit = min(self.config.max_plan_depth, MAX_PLAN_DEPTH)
        candidates: list[list[str]] = []
        obs_kinds = {str(o.get("kind")) for o in observations}

        if goal == "energy":
            seeds = [["APPROACH", "CHARGE"], ["MOVE", "APPROACH", "CHARGE"]]
            if "resource" in obs_kinds or any(
                e.entity_kind == "resource" for e in self.entities.values()
            ):
                seeds.append(["APPROACH", "CHARGE"])
            # generalization: charge_from affordance on novel kinds
            for aff in self.affordances.values():
                if aff.action == "charge_from" and aff.confidence > 0.4:
                    seeds.append(["APPROACH", "CHARGE"])
                    break
        elif goal == "rest":
            seeds = [["APPROACH", "REST"], ["MOVE", "APPROACH", "REST"]]
        elif goal == "avoid_hazard":
            seeds = [["RETREAT"], ["MOVE", "MOVE"]]
        elif goal == "inspect":
            seeds = [["APPROACH", "INSPECT"], ["MOVE", "APPROACH", "INSPECT"]]
        else:
            seeds = [["MOVE"], ["MOVE", "MOVE"]]

        for seq in seeds:
            trimmed = seq[:depth_limit]
            if trimmed and len(candidates) < self.config.max_candidate_plans:
                candidates.append(trimmed)
            # expand with MOVE prefixes (bounded)
            for prefix_len in range(1, min(2, depth_limit)):
                alt = (["MOVE"] * prefix_len) + trimmed
                alt = alt[:depth_limit]
                if len(candidates) < self.config.max_candidate_plans:
                    candidates.append(alt)

        if not candidates:
            return None

        def score(seq: list[str]) -> float:
            s = 0.0
            for a in seq:
                models = self._retrieve_models(a, None)
                if models:
                    s += max(m.confidence for m in models)
                else:
                    s += 0.15
                # affordance bonus
                for aff in self.affordances.values():
                    mapped = CAPABILITY_TO_AFFORDANCE.get(a)
                    if mapped and aff.action == mapped and aff.confidence > 0.3:
                        s += 0.2 * aff.confidence
            return s / max(1, len(seq))

        candidates.sort(key=score, reverse=True)
        best = candidates[0]
        trace = PlanTrace(
            plan_id=new_id(),
            tick=tick,
            goal=goal,
            actions=best,
            depth=len(best),
            retries=retries,
            predicted_success=score(best),
        )
        self._plan_retries[goal] = retries + 1
        # bound retry map
        if len(self._plan_retries) > 16:
            oldest = next(iter(self._plan_retries))
            del self._plan_retries[oldest]
        self._ring_write(self.plan_traces, trace)
        return trace

    def note_plan_success(self, goal: str) -> None:
        self._plan_retries[goal] = 0

    def propose_capability_bias(
        self, observations: list[dict[str, Any]], phys_urgency: dict[str, float]
    ) -> list[tuple[str, float]]:
        """Return (capability, score_bonus) for arbitration — proposals only."""
        bonuses: list[tuple[str, float]] = []
        if not self.config.planning_enabled and not self.config.prediction_enabled:
            return bonuses
        # Goal from urgency
        goal = "explore"
        if phys_urgency.get("energy", 0) > 0.45:
            goal = "energy"
        elif phys_urgency.get("fatigue", 0) > 0.45:
            goal = "rest"
        elif any(o.get("kind") == "hazard" for o in observations):
            goal = "avoid_hazard"
        plan = self.plan(goal, tick=int(self.metrics.get("last_tick", 0)), observations=observations)
        if plan and plan.actions:
            bonuses.append((plan.actions[0], 0.35 * plan.predicted_success))
        # Affordance-guided
        for o in observations:
            kind = str(o.get("kind"))
            for aff in self.affordances.values():
                if aff.entity_kind != kind or aff.confidence < 0.35:
                    continue
                if aff.action == "charge_from":
                    bonuses.append(("CHARGE", 0.25 * aff.confidence))
                    bonuses.append(("APPROACH", 0.2 * aff.confidence))
                elif aff.action == "rest_near":
                    bonuses.append(("REST", 0.25 * aff.confidence))
                elif aff.action == "avoid":
                    bonuses.append(("RETREAT", 0.3 * aff.confidence))
                elif aff.action == "inspect":
                    bonuses.append(("INSPECT", 0.2 * aff.confidence))
                elif aff.status == ModelStatus.WEAKENED.value and aff.action == "approach":
                    bonuses.append(("APPROACH", -0.3))
        return bonuses

    # --- Metrics / introspection ----------------------------------------------

    def live_predictions(self) -> list[WorldPrediction]:
        return [p for p in self.predictions if p.tick >= 0]

    def live_contradictions(self) -> list[dict[str, Any]]:
        return [c for c in self.contradictions if c.get("tick", -1) >= 0]

    def live_supersessions(self) -> list[dict[str, Any]]:
        return [s for s in self.supersessions if s.get("tick", -1) >= 0]

    def mean_prediction_error(self, window: int = 25) -> float:
        errs = [e for e in self._prediction_errors if e >= 0.0]
        if not errs:
            return 1.0
        xs = errs[-window:]
        return sum(xs) / len(xs)

    def initial_vs_recent_error(
        self, window: int = 25, skip_first: int = 5
    ) -> tuple[float, float]:
        errs = [e for e in self._prediction_errors if e >= 0.0]
        if len(errs) < skip_first + window:
            if len(errs) < 2:
                return 1.0, 1.0
            mid = len(errs) // 2
            early = sum(errs[:mid]) / max(1, mid)
            late = sum(errs[mid:]) / max(1, len(errs) - mid)
            return early, late
        early = sum(errs[skip_first : skip_first + window]) / window
        late = sum(errs[-window:]) / window
        return early, late

    def affordance_confidence(self, entity_kind: str, action: str) -> float:
        key = f"aff-{entity_kind}-{action}"
        bel = self.affordances.get(key)
        return bel.confidence if bel else 0.0

    def counts_bounded(self) -> bool:
        return (
            len(self.entities) <= self.config.max_entities
            and len(self.models) <= self.config.max_models
            and len(self.affordances) <= self.config.max_affordances
            and len(self.predictions) <= MAX_PREDICTION_HISTORY
            and len(self.plan_traces) <= MAX_PLAN_TRACES
        )

    def state_hash(self) -> str:
        return sha256_hex(canon_json(self.to_state()))

    def to_state(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "models": {k: v.to_dict() for k, v in self.models.items()},
            "affordances": {k: v.to_dict() for k, v in self.affordances.items()},
            "predictions": [p.to_dict() for p in self.live_predictions()],
            "contradictions": self.live_contradictions(),
            "supersessions": self.live_supersessions(),
            "plan_traces": [p.to_dict() for p in self.plan_traces if p.tick >= 0],
            "observation_log": [o for o in self.observation_log if o.get("tick", -1) >= 0],
            "prediction_errors": [e for e in self._prediction_errors if e >= 0.0],
            "plan_retries": dict(self._plan_retries),
            "processed_environmental_executions": dict(
                self._processed_environmental_executions
            ),
            "metrics": dict(self.metrics),
            "seed": self.seed,
            "state_hash": None,  # filled by caller via state_hash()
        }

    def accepted_state(self) -> dict[str, Any]:
        """Comparable accepted world-model state for replay equality."""
        st = self.to_state()
        # Drop volatile ids that differ across birth vs snapshot paths if regenerated;
        # compare structural content.
        models = sorted(
            (
                {
                    "conditions": m["conditions"],
                    "action": m["action"],
                    "predicted_effect": m["predicted_effect"],
                    "support_count": m["support_count"],
                    "contradiction_count": m["contradiction_count"],
                    "status": m["status"],
                    "confidence": round(m["confidence"], 4),
                }
                for m in st["models"].values()
            ),
            key=lambda x: (x["action"], str(x["conditions"]), x["status"]),
        )
        entities = sorted(
            (
                {
                    "entity_kind": e["entity_kind"],
                    "estimated_state": {
                        k: round(v, 4) for k, v in e["estimated_state"].items()
                    },
                    "confidence": round(e["confidence"], 4),
                    "fact_kind": e["fact_kind"],
                    "evidence_count": e["evidence_count"],
                }
                for e in st["entities"].values()
            ),
            key=lambda x: x["entity_kind"],
        )
        affordances = sorted(
            (
                {
                    "entity_kind": a["entity_kind"],
                    "action": a["action"],
                    "support_count": a["support_count"],
                    "contradiction_count": a["contradiction_count"],
                    "confidence": round(a["confidence"], 4),
                    "status": a["status"],
                }
                for a in st["affordances"].values()
            ),
            key=lambda x: (x["entity_kind"], x["action"]),
        )
        return {
            "entities": entities,
            "models": models,
            "affordances": affordances,
            "supersession_count": len(st["supersessions"]),
            "contradiction_count": len(st["contradictions"]),
        }

    @classmethod
    def from_state(
        cls, d: dict[str, Any], config: WorldModelConfig | None = None
    ) -> WorldModel:
        cfg = config or WorldModelConfig()
        wm = cls(
            agent_id=str(d["agent_id"]),
            config=cfg,
            seed=d.get("seed"),
        )
        wm.entities = {
            k: WorldEntity.from_dict(v) for k, v in d.get("entities", {}).items()
        }
        wm.models = {
            k: TransitionModel.from_dict(v) for k, v in d.get("models", {}).items()
        }
        wm.affordances = {
            k: AffordanceBelief.from_dict(v) for k, v in d.get("affordances", {}).items()
        }
        for p in d.get("predictions", []):
            wm.predictions.append(WorldPrediction.from_dict(p))
        for c in d.get("contradictions", []):
            wm.contradictions.append(dict(c))
        for s in d.get("supersessions", []):
            wm.supersessions.append(dict(s))
        for p in d.get("plan_traces", []):
            wm.plan_traces.append(PlanTrace.from_dict(p))
        for o in d.get("observation_log", []):
            wm.observation_log.append(dict(o))
        for e in d.get("prediction_errors", []):
            wm._prediction_errors.append(float(e))
        wm._plan_retries = dict(d.get("plan_retries", {}))
        wm._processed_environmental_executions = dict(
            d.get("processed_environmental_executions") or {}
        )
        wm.metrics = dict(d.get("metrics", {}))
        return wm
