"""Sensorimotor self-model: body schema, prediction, attribution, adaptation.

Narrow body knowledge only — not a general world model, not identity,
not consciousness. Predictions change expectations, never permissions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

from umbra_core.util import BoundedRing, clamp, new_id, sha256_hex, canon_json
from umbra_core.identity import deterministic_id


MAX_MODEL_VERSIONS = 32
MAX_PREDICTION_HISTORY = 256
MAX_ERROR_HISTORY = 256
MAX_CHANGE_EVIDENCE = 64

# Preregistered detection thresholds (Gate 3).
CHANGE_EVIDENCE_THRESHOLD = 15
CHANGE_MEAN_ERROR_THRESHOLD = 0.40
SINGLE_ANOMALY_CEILING = 1  # one outlier must not rewrite
FALSE_CHANGE_RATE_BOUND = 0.08  # preregistered Gate 3 bound


class Attribution(str, Enum):
    SELF_CAUSED = "SELF_CAUSED"
    EXTERNAL_CAUSED = "EXTERNAL_CAUSED"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


@dataclass
class BodySchema:
    """Adaptive body model — not constitutional identity."""

    body_schema_id: str
    body_binding_id: str
    version: int
    sensor_contracts: dict[str, float]
    actuator_contracts: dict[str, float]
    expected_motion: dict[str, float]
    expected_latency: float
    expected_cost: dict[str, float]
    expected_reliability: float
    reachable_affordances: dict[str, str]  # capability -> available|degraded|dormant
    confidence: float
    evidence_count: int
    updated_at: float
    superseded_by: str | None = None
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BodySchema:
        return cls(
            body_schema_id=str(d["body_schema_id"]),
            body_binding_id=str(d["body_binding_id"]),
            version=int(d["version"]),
            sensor_contracts={k: float(v) for k, v in d.get("sensor_contracts", {}).items()},
            actuator_contracts={k: float(v) for k, v in d.get("actuator_contracts", {}).items()},
            expected_motion={k: float(v) for k, v in d.get("expected_motion", {}).items()},
            expected_latency=float(d.get("expected_latency", 0.0)),
            expected_cost={k: float(v) for k, v in d.get("expected_cost", {}).items()},
            expected_reliability=float(d.get("expected_reliability", 0.95)),
            reachable_affordances=dict(d.get("reachable_affordances", {})),
            confidence=float(d.get("confidence", 0.5)),
            evidence_count=int(d.get("evidence_count", 0)),
            updated_at=float(d.get("updated_at", 0.0)),
            superseded_by=d.get("superseded_by"),
            active=bool(d.get("active", True)),
        )

    @classmethod
    def bootstrap(cls, body_binding_id: str, now: float, *, seed: int | None = None, version: int = 1) -> BodySchema:
        caps = (
            "IDLE",
            "ORIENT",
            "MOVE",
            "APPROACH",
            "RETREAT",
            "INSPECT",
            "REST",
            "CHARGE",
            # D-006: SIGNAL_PLAY/SIGNAL_ASSISTANCE are body-level affordances too — without
            # this the dormant-capability fallback in Organism.tick_once silently downgrades
            # every social signal proposal to IDLE before it ever reaches governance.
            "SIGNAL_PLAY",
            "SIGNAL_ASSISTANCE",
        )
        schema_id = (
            deterministic_id(int(seed), f"body_schema_v{version}")
            if seed is not None
            else new_id()
        )
        return cls(
            body_schema_id=schema_id,
            body_binding_id=body_binding_id,
            version=version,
            sensor_contracts={"range": 10.0, "noise": 0.25},
            actuator_contracts={
                "movement_gain": 1.0,
                "turning_gain": 1.0,
                "actuator_delay": 0.0,
                "body_radius": 0.0,
            },
            expected_motion={"step_gain": 1.0, "turn_gain": 1.0},
            expected_latency=0.0,
            expected_cost={"MOVE": 0.008, "APPROACH": 0.01, "RETREAT": 0.01, "REST": -0.01},
            expected_reliability=0.95,
            reachable_affordances={c: "available" for c in caps},
            confidence=0.45,
            evidence_count=0,
            updated_at=now,
        )


@dataclass
class Prediction:
    prediction_id: str
    capability: str
    tick: int
    expected_body_delta: dict[str, float]
    expected_observation_delta: dict[str, float]
    expected_physiology_cost: dict[str, float]
    expected_duration: float
    expected_success_probability: float
    prediction_confidence: float
    intent_issued: bool
    body_schema_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Prediction:
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class PredictionError:
    error_id: str
    prediction_id: str
    tick: int
    body_error: float
    observation_error: float
    success_error: float
    duration_error: float
    verified_success: bool
    capability: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PredictionError:
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class AttributionDecision:
    decision_id: str
    tick: int
    label: str
    confidence: float
    reasons: list[str]
    prediction_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AttributionDecision:
        return cls(
            decision_id=str(d["decision_id"]),
            tick=int(d["tick"]),
            label=str(d["label"]),
            confidence=float(d["confidence"]),
            reasons=list(d.get("reasons", [])),
            prediction_id=d.get("prediction_id"),
        )


@dataclass
class ChangeEvidence:
    evidence_id: str
    dimension: str
    residual: float
    tick: int
    body_schema_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChangeEvidence:
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class SelfModelConfig:
    """Experiment / ablation switches for D-002 conditions."""

    adaptive: bool = True  # C0
    fixed_authored: bool = False  # C1
    prediction_enabled: bool = True  # C2 off
    attribution_enabled: bool = True  # C3 off
    updating_enabled: bool = True  # C4 off
    randomize_observations: bool = False  # C5
    hide_verified_outcomes: bool = False  # C6
    # Bounds
    max_versions: int = MAX_MODEL_VERSIONS
    max_prediction_history: int = MAX_PREDICTION_HISTORY
    max_error_history: int = MAX_ERROR_HISTORY
    change_evidence_threshold: int = CHANGE_EVIDENCE_THRESHOLD
    change_mean_error_threshold: float = CHANGE_MEAN_ERROR_THRESHOLD


@dataclass
class SelfModel:
    """Learned sensorimotor body knowledge for one agent."""

    agent_id: str
    body_binding_id: str
    active: BodySchema
    archive: BoundedRing[BodySchema] = field(default_factory=lambda: BoundedRing(MAX_MODEL_VERSIONS))
    predictions: BoundedRing[Prediction] = field(
        default_factory=lambda: BoundedRing(MAX_PREDICTION_HISTORY)
    )
    errors: BoundedRing[PredictionError] = field(
        default_factory=lambda: BoundedRing(MAX_ERROR_HISTORY)
    )
    attributions: BoundedRing[AttributionDecision] = field(
        default_factory=lambda: BoundedRing(MAX_PREDICTION_HISTORY)
    )
    change_evidence: BoundedRing[ChangeEvidence] = field(
        default_factory=lambda: BoundedRing(MAX_CHANGE_EVIDENCE)
    )
    supersessions: BoundedRing[dict[str, Any]] = field(
        default_factory=lambda: BoundedRing(MAX_MODEL_VERSIONS)
    )
    config: SelfModelConfig = field(default_factory=SelfModelConfig)
    seed: int | None = None
    _body_before: dict[str, float] | None = field(default=None, repr=False)
    _pending_prediction: Prediction | None = field(default=None, repr=False)
    _last_attribution: AttributionDecision | None = field(default=None, repr=False)
    _obs_range_window: BoundedRing[float] = field(
        default_factory=lambda: BoundedRing(40), repr=False
    )
    primary_bound: bool = True
    _bounded_initialized: bool = False

    @classmethod
    def create(
        cls,
        agent_id: str,
        now: float = 0.0,
        config: SelfModelConfig | None = None,
        *,
        seed: int | None = None,
    ) -> SelfModel:
        binding = (
            deterministic_id(int(seed), "body_binding") if seed is not None else new_id()
        )
        schema = BodySchema.bootstrap(binding, now, seed=seed, version=1)
        cfg = config or SelfModelConfig()
        return cls(
            agent_id=agent_id,
            body_binding_id=binding,
            active=schema,
            archive=BoundedRing(cfg.max_versions),
            predictions=BoundedRing(cfg.max_prediction_history),
            errors=BoundedRing(cfg.max_error_history),
            attributions=BoundedRing(cfg.max_prediction_history),
            change_evidence=BoundedRing(MAX_CHANGE_EVIDENCE),
            supersessions=BoundedRing(cfg.max_versions),
            config=cfg,
            seed=seed,
            primary_bound=True,
        )

    def initialize_bounded_collections(self) -> None:
        """Populate ring capacity before RUNTIME_READY (structural init, not RSS wait).

        Rings are filled with pad objects, then every live write mutates a slot
        in place so post-READY ticks do not allocate new history objects.
        """
        if self._bounded_initialized:
            return
        self._pad_rings_to_capacity()
        self._bounded_initialized = True

    def _pad_rings_to_capacity(self) -> None:
        """Fill rings to maxlen with pads (tick=-1); live writes overwrite in place."""
        specs = (
            (
                self.predictions,
                lambda: Prediction(
                    prediction_id="init",
                    capability="IDLE",
                    tick=-1,
                    expected_body_delta={},
                    expected_observation_delta={},
                    expected_physiology_cost={},
                    expected_duration=0.0,
                    expected_success_probability=0.0,
                    prediction_confidence=0.0,
                    intent_issued=False,
                    body_schema_id=self.active.body_schema_id,
                ),
            ),
            (
                self.errors,
                lambda: PredictionError(
                    error_id="init",
                    prediction_id="init",
                    tick=-1,
                    body_error=0.0,
                    observation_error=0.0,
                    success_error=0.0,
                    duration_error=0.0,
                    verified_success=False,
                    capability="IDLE",
                ),
            ),
            (
                self.attributions,
                lambda: AttributionDecision(
                    decision_id="init",
                    tick=-1,
                    label=Attribution.UNKNOWN.value,
                    confidence=0.0,
                    reasons=["init"],
                    prediction_id=None,
                ),
            ),
            (
                self.change_evidence,
                lambda: ChangeEvidence(
                    evidence_id="init",
                    dimension="init",
                    residual=0.0,
                    tick=-1,
                    body_schema_id=self.active.body_schema_id,
                ),
            ),
        )
        for ring, factory in specs:
            live = [x for x in ring if getattr(x, "tick", 0) >= 0]
            ring.clear()
            for _ in range(max(0, ring.maxlen - len(live))):
                ring.append(factory())
            for item in live[-ring.maxlen :]:
                ring.append(item)
        # Prefill nested maps so later ticks mutate keys instead of replacing dicts.
        for p in self.predictions:
            if not p.expected_body_delta:
                p.expected_body_delta = {"dx": 0.0, "dy": 0.0, "dheading": 0.0}
            if not p.expected_observation_delta:
                p.expected_observation_delta = {"range": 10.0}
            if not p.expected_physiology_cost:
                p.expected_physiology_cost = {"energy": 0.0}
        self._bounded_initialized = True

    def _append_change_evidence(self, ev: ChangeEvidence) -> None:
        reused = self.change_evidence.reclaim_oldest()
        if reused is None:
            self.change_evidence.append(ev)
            return
        reused.evidence_id = ev.evidence_id
        reused.dimension = ev.dimension
        reused.residual = ev.residual
        reused.tick = ev.tick
        reused.body_schema_id = ev.body_schema_id
        self.change_evidence.advance_after_reclaim()

    def live_predictions(self) -> list[Prediction]:
        return [p for p in self.predictions if p.tick >= 0]

    def live_errors(self) -> list[PredictionError]:
        return [e for e in self.errors if e.tick >= 0]

    def live_attributions(self) -> list[AttributionDecision]:
        return [a for a in self.attributions if a.tick >= 0]

    def live_change_evidence(self) -> list[ChangeEvidence]:
        return [c for c in self.change_evidence if c.tick >= 0]

    def bind_primary(self, body_binding_id: str | None = None) -> str:
        """Bind primary body. Duplicate primary binding is rejected."""
        if self.primary_bound and body_binding_id and body_binding_id != self.body_binding_id:
            raise ValueError("duplicate_primary_body_binding")
        if self.primary_bound and body_binding_id is None and self.body_binding_id:
            raise ValueError("duplicate_primary_body_binding")
        if body_binding_id:
            self.body_binding_id = body_binding_id
            self.active.body_binding_id = body_binding_id
        self.primary_bound = True
        return self.body_binding_id

    def replace_body(self, *, reduced: bool, now: float) -> BodySchema:
        """Migrate to replacement body — preserves agent_id and archives prior schema."""
        prior = self.active
        prior.active = False
        self.archive.append(prior)
        # ring auto-evicts; no list trim
        ver = prior.version + 1
        if self.seed is not None:
            new_binding = deterministic_id(self.seed, f"body_binding_v{ver}")
            schema = BodySchema.bootstrap(new_binding, now, seed=self.seed, version=ver)
        else:
            new_binding = new_id()
            schema = BodySchema.bootstrap(new_binding, now, version=ver)
            schema.body_schema_id = new_id()
        if reduced:
            schema.sensor_contracts["range"] = 5.0
            schema.actuator_contracts["movement_gain"] = 0.6
            schema.expected_reliability = 0.7
            schema.reachable_affordances["INSPECT"] = "degraded"
            schema.reachable_affordances["APPROACH"] = "degraded"
        self.body_binding_id = new_binding
        self.active = schema
        self.primary_bound = True
        self.supersessions.append(
            {
                "event": "body_replacement",
                "from": prior.body_schema_id,
                "to": schema.body_schema_id,
                "reduced": reduced,
                "at": now,
            }
        )
        return schema

    def capability_status(self, capability: str) -> str:
        return self.active.reachable_affordances.get(capability, "dormant")

    def note_body_before(self, body_state: dict[str, Any]) -> None:
        self._body_before = {
            "x": float(body_state.get("x", 0.0)),
            "y": float(body_state.get("y", 0.0)),
            "heading": float(body_state.get("heading", 0.0)),
            "sensor_range": float(body_state.get("sensor_range", 10.0)),
            "velocity": float(body_state.get("velocity", 0.0)),
        }

    def predict(
        self,
        capability: str,
        params: dict[str, Any],
        tick: int,
        body_state: dict[str, Any],
    ) -> Prediction | None:
        if not self.config.prediction_enabled:
            self._pending_prediction = None
            return None
        schema = self.active
        step = float(params.get("step", 1.0 if capability != "RETREAT" else 1.2))
        heading = float(params.get("heading", body_state.get("heading", 0.0)))
        gain = schema.expected_motion.get("step_gain", 1.0)
        turn_gain = schema.expected_motion.get("turn_gain", 1.0)
        delay = schema.expected_latency
        dx = dy = dheading = 0.0
        if capability in ("MOVE", "APPROACH", "RETREAT"):
            h = heading
            if capability == "RETREAT":
                h = heading + math.pi
            # turning gain scales heading change from current
            cur_h = float(body_state.get("heading", 0.0))
            dheading = (h - cur_h) * turn_gain
            h2 = cur_h + dheading
            dx = math.cos(h2) * step * gain
            dy = math.sin(h2) * step * gain
        elif capability == "ORIENT":
            target = float(params.get("heading", body_state.get("heading", 0.0)))
            dheading = (target - float(body_state.get("heading", 0.0))) * turn_gain

        cost_key = capability if capability in schema.expected_cost else "MOVE"
        cost = float(schema.expected_cost.get(cost_key, 0.008))
        reused = self.predictions.reclaim_oldest()
        if reused is None:
            p = Prediction(
                prediction_id=new_id(),
                capability=capability,
                tick=tick,
                expected_body_delta={"dx": dx, "dy": dy, "dheading": dheading},
                expected_observation_delta={"range": schema.sensor_contracts.get("range", 10.0)},
                expected_physiology_cost={"energy": -abs(cost) if cost > 0 else cost},
                expected_duration=1.0 + delay,
                expected_success_probability=schema.expected_reliability
                if capability in ("MOVE", "APPROACH", "RETREAT")
                else 0.9,
                prediction_confidence=schema.confidence,
                intent_issued=True,
                body_schema_id=schema.body_schema_id,
            )
            self.predictions.append(p)
        else:
            p = reused
            p.prediction_id = new_id()
            p.capability = capability
            p.tick = tick
            # Mutate nested maps in place — avoid per-tick dict allocation.
            ebd = p.expected_body_delta
            ebd["dx"] = dx
            ebd["dy"] = dy
            ebd["dheading"] = dheading
            p.expected_observation_delta["range"] = schema.sensor_contracts.get("range", 10.0)
            p.expected_physiology_cost["energy"] = -abs(cost) if cost > 0 else cost
            p.expected_duration = 1.0 + delay
            p.expected_success_probability = (
                schema.expected_reliability
                if capability in ("MOVE", "APPROACH", "RETREAT")
                else 0.9
            )
            p.prediction_confidence = schema.confidence
            p.intent_issued = True
            p.body_schema_id = schema.body_schema_id
            self.predictions.advance_after_reclaim()
        if self.config.fixed_authored:
            # C1: freeze authored assumptions — still predict, never update later
            pass
        self._pending_prediction = p
        return p

    def observe_outcome(
        self,
        *,
        tick: int,
        capability: str | None,
        verified_outcome: dict[str, Any] | None,
        body_after: dict[str, Any],
        observation_summary: dict[str, float] | None,
        action_issued: bool,
        now: float,
    ) -> dict[str, Any]:
        """Compare prediction to verified outcome; attribute; maybe adapt."""
        before = self._body_before or {
            "x": body_after.get("x", 0.0),
            "y": body_after.get("y", 0.0),
            "heading": body_after.get("heading", 0.0),
        }
        actual_dx = float(body_after.get("x", 0.0)) - float(before.get("x", 0.0))
        actual_dy = float(body_after.get("y", 0.0)) - float(before.get("y", 0.0))
        actual_disp = math.hypot(actual_dx, actual_dy)

        pred = self._pending_prediction
        err: PredictionError | None = None
        if self.config.hide_verified_outcomes:
            verified_outcome = None

        if pred is not None and verified_outcome is not None:
            edx = pred.expected_body_delta.get("dx", 0.0)
            edy = pred.expected_body_delta.get("dy", 0.0)
            expected_disp = math.hypot(edx, edy)
            body_error = abs(actual_disp - expected_disp)
            if expected_disp > 1e-6:
                body_error = body_error / max(expected_disp, 1e-6)
            else:
                body_error = actual_disp  # unexpected motion
            success = bool(verified_outcome.get("success"))
            success_error = abs(float(success) - pred.expected_success_probability)
            obs_err = 0.0
            if observation_summary is not None:
                er = pred.expected_observation_delta.get("range", 10.0)
                ar = float(observation_summary.get("max_range_seen", er))
                obs_err = abs(ar - er) / max(er, 1.0)
            err = PredictionError(
                error_id=new_id(),
                prediction_id=pred.prediction_id,
                tick=tick,
                body_error=float(body_error),
                observation_error=float(obs_err),
                success_error=float(success_error),
                duration_error=0.0,
                verified_success=success,
                capability=pred.capability,
            )
            reused_e = self.errors.reclaim_oldest()
            if reused_e is None:
                self.errors.append(err)
            else:
                reused_e.error_id = err.error_id
                reused_e.prediction_id = err.prediction_id
                reused_e.tick = err.tick
                reused_e.body_error = err.body_error
                reused_e.observation_error = err.observation_error
                reused_e.success_error = err.success_error
                reused_e.duration_error = err.duration_error
                reused_e.verified_success = err.verified_success
                reused_e.capability = err.capability
                err = reused_e
                self.errors.advance_after_reclaim()

        attr = self._attribute(
            tick=tick,
            action_issued=action_issued,
            pred=pred,
            err=err,
            actual_disp=actual_disp,
            verified_outcome=verified_outcome,
        )
        self._last_attribution = attr
        reused_a = self.attributions.reclaim_oldest()
        if reused_a is None:
            self.attributions.append(attr)
        else:
            reused_a.decision_id = attr.decision_id
            reused_a.tick = attr.tick
            reused_a.label = attr.label
            reused_a.confidence = attr.confidence
            reused_a.reasons = attr.reasons
            reused_a.prediction_id = attr.prediction_id
            self.attributions.advance_after_reclaim()
            attr = reused_a
            self._last_attribution = attr

        adapted = False
        if (
            self.config.adaptive
            and self.config.updating_enabled
            and not self.config.fixed_authored
            and err is not None
            and capability
        ):
            adapted = self._update_from_error(err, actual_dx, actual_dy, pred, now)
        elif (
            self.config.adaptive
            and self.config.updating_enabled
            and not self.config.fixed_authored
            and verified_outcome is not None
            and capability in ("MOVE", "APPROACH", "RETREAT")
        ):
            # Outcome without prior prediction (forced probes) still updates reliability.
            success = bool(verified_outcome.get("success"))
            self.active.expected_reliability = clamp(
                0.85 * self.active.expected_reliability + 0.15 * (1.0 if success else 0.0),
                0.2,
                0.99,
            )
            if not success:
                self.active.confidence = clamp(self.active.confidence - 0.03, 0.05, 0.98)
            self.active.evidence_count += 1
            self.active.updated_at = now

        self._pending_prediction = None
        self._body_before = None
        return {
            "prediction": pred.to_dict() if pred else None,
            "prediction_error": err.to_dict() if err else None,
            "attribution": attr.to_dict(),
            "adapted": adapted,
            "active_schema_id": self.active.body_schema_id,
            "confidence": self.active.confidence,
        }

    def _attribute(
        self,
        *,
        tick: int,
        action_issued: bool,
        pred: Prediction | None,
        err: PredictionError | None,
        actual_disp: float,
        verified_outcome: dict[str, Any] | None,
    ) -> AttributionDecision:
        reasons: list[str] = []
        if not self.config.attribution_enabled:
            return AttributionDecision(
                decision_id=new_id(),
                tick=tick,
                label=Attribution.UNKNOWN.value,
                confidence=0.0,
                reasons=["attribution_disabled"],
                prediction_id=pred.prediction_id if pred else None,
            )

        # Never uses world truth — only intent, timing, prediction, verified change.
        if verified_outcome is None and action_issued:
            reasons.append("outcome_hidden_or_missing")
            label = Attribution.UNKNOWN
            conf = 0.2
        elif action_issued and pred is not None and err is not None:
            if actual_disp < 0.05 and pred.capability in ("IDLE", "REST", "CHARGE", "INSPECT"):
                label = Attribution.SELF_CAUSED
                conf = 0.7
                reasons.append("intent_matched_stationary_action")
            elif err.body_error < 0.35 and verified_outcome.get("success") is not None:
                label = Attribution.SELF_CAUSED
                conf = clamp(0.55 + 0.4 * (1.0 - err.body_error), 0.0, 0.95)
                reasons.append("intent_prediction_verified_match")
            elif actual_disp > 0.4 and err.body_error > 0.8:
                # Moved a lot but not as predicted — mixed/uncertain
                if verified_outcome.get("success"):
                    label = Attribution.MIXED
                    conf = 0.45
                    reasons.append("intent_present_but_large_prediction_mismatch")
                else:
                    label = Attribution.UNKNOWN
                    conf = 0.35
                    reasons.append("failed_action_uncertain_displacement")
            else:
                label = Attribution.SELF_CAUSED
                conf = 0.5
                reasons.append("intent_issued_default_self")
        elif not action_issued and actual_disp > 0.35:
            label = Attribution.EXTERNAL_CAUSED
            conf = clamp(0.5 + min(actual_disp, 2.0) * 0.2, 0.0, 0.95)
            reasons.append("displacement_without_issued_intent")
        elif not action_issued and actual_disp <= 0.35:
            label = Attribution.UNKNOWN
            conf = 0.4
            reasons.append("small_or_no_change_without_intent")
        else:
            label = Attribution.UNKNOWN
            conf = 0.3
            reasons.append("insufficient_evidence")

        return AttributionDecision(
            decision_id=new_id(),
            tick=tick,
            label=label.value if isinstance(label, Attribution) else str(label),
            confidence=float(conf),
            reasons=reasons,
            prediction_id=pred.prediction_id if pred else None,
        )

    def _update_from_error(
        self,
        err: PredictionError,
        actual_dx: float,
        actual_dy: float,
        pred: Prediction | None,
        now: float,
    ) -> bool:
        schema = self.active
        schema.evidence_count += 1
        # Soft confidence update from prediction quality
        quality = 1.0 - clamp(err.body_error, 0.0, 1.0)
        schema.confidence = clamp(0.85 * schema.confidence + 0.15 * quality, 0.05, 0.98)

        if pred and pred.capability in ("MOVE", "APPROACH", "RETREAT"):
            expected = math.hypot(
                pred.expected_body_delta.get("dx", 0.0),
                pred.expected_body_delta.get("dy", 0.0),
            )
            actual = math.hypot(actual_dx, actual_dy)
            if expected > 0.05 and actual > 0.35:
                ratio = actual / expected
                residual = abs(ratio - 1.0)
                dim = "movement_gain"
                # Body-gain change evidence only on successful non-truncated moves.
                if (
                    err.verified_success
                    and residual > 0.45
                    and (ratio < 0.7 or ratio > 1.35)
                ):
                    self._append_change_evidence(
                        ChangeEvidence(
                            evidence_id=new_id(),
                            dimension=dim,
                            residual=residual,
                            tick=err.tick,
                            body_schema_id=schema.body_schema_id,
                        )
                    )
                # EMA nudge toward observed gain (always mild)
                old = schema.expected_motion.get("step_gain", 1.0)
                alpha = 0.35 if residual > 0.3 else 0.2
                schema.expected_motion["step_gain"] = clamp(
                    (1.0 - alpha) * old + alpha * (old * ratio), 0.2, 2.5
                )
                schema.actuator_contracts["movement_gain"] = schema.expected_motion["step_gain"]
            elif expected > 0.05:
                ratio = actual / expected if expected else 1.0
                residual = abs(ratio - 1.0)
                old = schema.expected_motion.get("step_gain", 1.0)
                alpha = 0.15
                schema.expected_motion["step_gain"] = clamp(
                    (1.0 - alpha) * old + alpha * (old * ratio), 0.2, 2.5
                )
                schema.actuator_contracts["movement_gain"] = schema.expected_motion["step_gain"]

            # reliability EMA
            schema.expected_reliability = clamp(
                0.9 * schema.expected_reliability + 0.1 * (1.0 if err.verified_success else 0.0),
                0.2,
                0.99,
            )

        if err.observation_error > self.config.change_mean_error_threshold:
            # Do not treat sparse near-field observations as sensor failure.
            # Rolling max range is checked separately via note_observation_range().
            pass

            # Intermittent failure → reliability and confidence drop
            if not err.verified_success and err.capability in ("MOVE", "APPROACH", "RETREAT"):
                schema.confidence = clamp(schema.confidence - 0.03, 0.05, 0.98)
                schema.expected_reliability = clamp(
                    0.75 * schema.expected_reliability + 0.25 * 0.0,
                    0.2,
                    0.99,
                )

        schema.updated_at = now
        return self._maybe_supersede(now)

    def _maybe_supersede(self, now: float) -> bool:
        """Persistent evidence only — single anomaly must not rewrite."""
        live_ev = self.live_change_evidence()
        if len(live_ev) < self.config.change_evidence_threshold:
            return False
        recent = live_ev[-self.config.change_evidence_threshold :]
        # Require same dimension cluster
        by_dim: dict[str, list[ChangeEvidence]] = {}
        for e in recent:
            by_dim.setdefault(e.dimension, []).append(e)
        for dim, items in by_dim.items():
            if len(items) < self.config.change_evidence_threshold:
                continue
            mean_r = sum(i.residual for i in items) / len(items)
            if mean_r < self.config.change_mean_error_threshold:
                continue
            # Enough persistent evidence → supersede
            return self._supersede(dim, mean_r, now)
        return False

    def _supersede(self, dimension: str, mean_residual: float, now: float) -> bool:
        prior = self.active
        prior.active = False
        prior.superseded_by = None  # filled below
        self.archive.append(prior)

        nxt = BodySchema.from_dict(prior.to_dict())
        nxt.version = prior.version + 1
        if self.seed is not None:
            nxt.body_schema_id = deterministic_id(self.seed, f"body_schema_v{nxt.version}")
        else:
            nxt.body_schema_id = new_id()
        nxt.active = True
        nxt.superseded_by = None
        nxt.evidence_count = 0
        nxt.updated_at = now
        nxt.confidence = clamp(prior.confidence * 0.7 + 0.15, 0.1, 0.9)

        # Apply dimension-specific adaptation to new belief
        if dimension == "movement_gain":
            g = prior.expected_motion.get("step_gain", 1.0)
            # mean_residual implies |ratio-1|; shrink/grow toward observed
            # Use current EMA already in prior
            nxt.expected_motion["step_gain"] = g
            nxt.actuator_contracts["movement_gain"] = g
        elif dimension == "sensor_range":
            r = prior.sensor_contracts.get("range", 10.0)
            nxt.sensor_contracts["range"] = clamp(r * (1.0 - 0.3 * mean_residual), 2.0, 20.0)
            if nxt.sensor_contracts["range"] < 6.0:
                nxt.reachable_affordances["INSPECT"] = "degraded"
        elif dimension == "actuator_delay":
            nxt.expected_latency = min(5.0, prior.expected_latency + 1.0)
            nxt.actuator_contracts["actuator_delay"] = nxt.expected_latency
        elif dimension == "reliability":
            nxt.expected_reliability = clamp(prior.expected_reliability * 0.85, 0.2, 0.99)
            if nxt.expected_reliability < 0.6:
                nxt.reachable_affordances["MOVE"] = "degraded"
                nxt.reachable_affordances["APPROACH"] = "degraded"

        prior.superseded_by = nxt.body_schema_id
        self.active = nxt
        self.change_evidence.clear()  # reset after supersession; keep ring capacity
        self.supersessions.append(
            {
                "event": "schema_supersession",
                "from": prior.body_schema_id,
                "to": nxt.body_schema_id,
                "dimension": dimension,
                "mean_residual": mean_residual,
                "at": now,
            }
        )
        return True

    def note_observation_range(self, max_range_seen: float, tick: int) -> bool:
        """Track rolling max observed distance; flag sensor-range change if capped low."""
        if not self.config.updating_enabled or self.config.fixed_authored:
            return False
        self._obs_range_window.append(float(max_range_seen))
        if len(self._obs_range_window) < 30:
            return False
        belief = self.active.sensor_contracts.get("range", 10.0)
        roll_max = max(self._obs_range_window)
        if belief > 0 and roll_max < belief * 0.45:
            return self.record_dimension_evidence(
                "sensor_range", 1.0 - (roll_max / belief), tick
            )
        return False

    def record_dimension_evidence(self, dimension: str, residual: float, tick: int) -> bool:
        """External hook for detectors (delay, radius, cost) without rewriting immediately."""
        if not self.config.updating_enabled or self.config.fixed_authored:
            return False
        if residual < self.config.change_mean_error_threshold:
            return False
        self._append_change_evidence(
            ChangeEvidence(
                evidence_id=new_id(),
                dimension=dimension,
                residual=residual,
                tick=tick,
                body_schema_id=self.active.body_schema_id,
            )
        )
        return self._maybe_supersede(float(tick))

    def restore_confidence(self, amount: float = 0.05) -> None:
        self.active.confidence = clamp(self.active.confidence + amount, 0.05, 0.98)

    def mark_incompatible(self, capability: str, status: str = "dormant") -> None:
        if status not in ("available", "degraded", "dormant"):
            raise ValueError("bad_capability_status")
        self.active.reachable_affordances[capability] = status

    def mean_body_prediction_error(self, last_n: int = 50) -> float:
        xs = self.live_errors()[-last_n:]
        if not xs:
            return 1.0
        return sum(e.body_error for e in xs) / len(xs)

    def initial_vs_recent_error(self, window: int = 20, skip_first: int = 10) -> tuple[float, float]:
        """Compare early post-warmup locomotion errors to recent ones."""
        errs = self.live_errors()
        xs = [
            e
            for e in errs[skip_first:]
            if e.capability in ("MOVE", "APPROACH", "RETREAT")
        ]
        if not xs:
            xs = errs[skip_first:] or errs
        if len(xs) < window * 2:
            early = xs[: max(1, len(xs) // 2)] or xs
            late = xs[-max(1, len(xs) // 2) :] or xs
        else:
            early = xs[:window]
            late = xs[-window:]

        def mean(errs: list[PredictionError]) -> float:
            return sum(e.body_error for e in errs) / len(errs) if errs else 1.0

        return mean(early), mean(late)

    def to_state(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "body_binding_id": self.body_binding_id,
            "active": self.active.to_dict(),
            "archive": [s.to_dict() for s in self.archive],
            "predictions": [p.to_dict() for p in self.live_predictions()],
            "errors": [e.to_dict() for e in self.live_errors()],
            "attributions": [a.to_dict() for a in self.live_attributions()],
            "change_evidence": [c.to_dict() for c in self.live_change_evidence()],
            "supersessions": list(self.supersessions),
            "config": {
                "adaptive": self.config.adaptive,
                "fixed_authored": self.config.fixed_authored,
                "prediction_enabled": self.config.prediction_enabled,
                "attribution_enabled": self.config.attribution_enabled,
                "updating_enabled": self.config.updating_enabled,
                "randomize_observations": self.config.randomize_observations,
                "hide_verified_outcomes": self.config.hide_verified_outcomes,
            },
            "primary_bound": self.primary_bound,
            "seed": self.seed,
            "bounded_initialized": self._bounded_initialized,
            "state_hash": self.state_hash(),
        }

    def state_hash(self) -> str:
        payload = {
            "active": self.active.to_dict(),
            "archive_ids": [s.body_schema_id for s in self.archive],
            "binding": self.body_binding_id,
            "agent_id": self.agent_id,
        }
        return sha256_hex(canon_json(payload))

    @classmethod
    def from_state(cls, d: dict[str, Any], config: SelfModelConfig | None = None) -> SelfModel:
        cfg_d = d.get("config", {})
        cfg = config or SelfModelConfig(
            adaptive=bool(cfg_d.get("adaptive", True)),
            fixed_authored=bool(cfg_d.get("fixed_authored", False)),
            prediction_enabled=bool(cfg_d.get("prediction_enabled", True)),
            attribution_enabled=bool(cfg_d.get("attribution_enabled", True)),
            updating_enabled=bool(cfg_d.get("updating_enabled", True)),
            randomize_observations=bool(cfg_d.get("randomize_observations", False)),
            hide_verified_outcomes=bool(cfg_d.get("hide_verified_outcomes", False)),
        )
        sm = cls(
            agent_id=str(d["agent_id"]),
            body_binding_id=str(d["body_binding_id"]),
            active=BodySchema.from_dict(d["active"]),
            archive=BoundedRing(
                cfg.max_versions, [BodySchema.from_dict(x) for x in d.get("archive", [])]
            ),
            predictions=BoundedRing(
                cfg.max_prediction_history,
                [Prediction.from_dict(x) for x in d.get("predictions", [])],
            ),
            errors=BoundedRing(
                cfg.max_error_history,
                [PredictionError.from_dict(x) for x in d.get("errors", [])],
            ),
            attributions=BoundedRing(
                cfg.max_prediction_history,
                [AttributionDecision.from_dict(x) for x in d.get("attributions", [])],
            ),
            change_evidence=BoundedRing(
                MAX_CHANGE_EVIDENCE,
                [ChangeEvidence.from_dict(x) for x in d.get("change_evidence", [])],
            ),
            supersessions=BoundedRing(cfg.max_versions, list(d.get("supersessions", []))),
            config=cfg,
            seed=d.get("seed"),
            primary_bound=bool(d.get("primary_bound", True)),
            _bounded_initialized=bool(d.get("bounded_initialized", False)),
        )
        # Corruption fail-closed: hash mismatch if present
        if "state_hash" in d and d["state_hash"] != sm.state_hash():
            raise ValueError("corrupt_body_model")
        return sm