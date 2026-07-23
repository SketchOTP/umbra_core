"""Continuous organism runtime loop — no user input, LLM, or network.

D-002 loop:
  drift → perceive → update state → predict → arbitrate → govern →
  execute → verify → prediction error → attribute → body-model evidence →
  physiology → persist → repeat
"""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from umbra_core.arbitration import ArbitrationState, Arbitrator, Candidate
from umbra_core.development import (
    DevelopmentConfig,
    DevelopmentEngine,
    GoalStatus,
    condition_to_development_config,
)
from umbra_core.embodiment import Embodiment
from umbra_core.embodiment_adapters.adapter import (
    ATTACHMENT_EVENT_TYPES,
    EmbodimentAdapter,
    attachment_state_from_event,
)
from umbra_core.embodiment_adapters.profiles import default_migration_profile_id
from umbra_core.expression import (
    AttachmentView,
    ExpressionEngine,
    ExpressionView,
    FrameRing,
    FrameRingEntry,
    LastOutcomeView,
)
from umbra_core.events import (
    AUTHORITATIVE_EVENT_TYPES,
    DIAGNOSTIC_SELF_MODEL_SAMPLE_EVERY_TICKS,
    SNAPSHOT_RETAIN_COUNT,
    WAL_CHECKPOINT_EVERY_TICKS,
)
from umbra_core.governance import Governance, GovernanceState
from umbra_core.identity import ConstitutionalIdentity, create_birth, verify_identity
from umbra_core.memory import MemoryConfig, MemoryEngine, condition_to_memory_config
from umbra_core.perception import PerceptionMembrane
from umbra_core.persistence import PersistenceError, Store
from umbra_core.physiology import Physiology
from umbra_core.self_model import SelfModel, SelfModelConfig
from umbra_core.social import (
    SocialConfig,
    SocialEngine,
    SocialEngineError,
    condition_to_social_config,
)
from umbra_core.individuality import (
    IndividualityConfig,
    IndividualityEngine,
    IndividualityEngineError,
    condition_to_individuality_config,
    infer_evidence_from_outcome,
)
from umbra_core.util import SCHEMA_VERSION, SeededRNG, new_id
from umbra_core.world_model import WorldModel, WorldModelConfig, condition_to_world_model_config


@dataclass
class OrganismConfig:
    db_path: str
    seed: int = 0
    hz: float = 2.0
    snapshot_every: int = 200
    condition: str = "C0"  # experiment condition label
    drift_enabled: bool = True
    hide_physiology: bool = False
    arbitration_mode: str = "full"  # full | random | scripted
    leak_world_truth: bool = False
    governance_bypass: bool = False
    wall_time_fn: Any = field(default=time.time, repr=False)
    # D-002
    self_model_enabled: bool = True
    intervention: str = "I0"  # body-plant intervention
    self_model_config: SelfModelConfig | None = None
    # D-003
    world_model_enabled: bool = False
    world_intervention: str = "I0"
    world_model_config: WorldModelConfig | None = None
    # D-004
    development_enabled: bool = False
    development_intervention: str = "I0"
    development_config: DevelopmentConfig | None = None
    # D-005
    memory_enabled: bool = False
    memory_history: str = "H0"
    memory_config: MemoryConfig | None = None
    # D-006
    social_enabled: bool = False
    social_history: str = "H0"
    social_config: SocialConfig | None = None
    # D-007
    individuality_enabled: bool = False
    individuality_history: str = "H0"
    individuality_config: IndividualityConfig | None = None
    # D-008: opt-in, like the flags above — default False preserves D-001..D-007
    # behavior exactly. Supplement S1 (design doc) has the adapter clamp
    # continuous limits (e.g. ABSTRACT_SHAPE_BODY.max_step) rather than hard-
    # reject, so pre-D008 arbitration's larger fallback steps (1.2-1.8) now
    # succeed when enabled — see tests/test_d008.py Supplement S1 regression.
    # Kept opt-in (not default-True) because flipping the default would break
    # the explicit invariant test
    # `test_embodiment_adapter_disabled_by_default_preserves_prior_behavior`.
    embodiment_adapter_enabled: bool = False
    # D-008 expression side-car: purely additive read-only derivation (never
    # writes physiology/embodiment/governance, never appends authoritative
    # events) — default True is safe for D-001..D-007 behavior. C10 is the
    # frozen performance-baseline condition (design §4) and always disables
    # it regardless of this flag, for core-only CPU/RSS measurement.
    expression_enabled: bool = True


def condition_to_self_model_config(condition: str) -> SelfModelConfig:
    """Map experiment conditions C0–C7 to self-model switches."""
    c = SelfModelConfig()
    if condition == "C0":
        return c
    if condition == "C1":
        c.fixed_authored = True
        c.updating_enabled = False
        return c
    if condition == "C2":
        c.prediction_enabled = False
        return c
    if condition == "C3":
        c.attribution_enabled = False
        return c
    if condition == "C4":
        c.updating_enabled = False
        return c
    if condition == "C5":
        c.randomize_observations = True
        return c
    if condition == "C6":
        c.hide_verified_outcomes = True
        return c
    if condition == "C7":
        # random policy handled via arbitration_mode; keep model on
        return c
    return c


class Organism:
    """Minimum persistent UMBRA creature core (+ D-002..D-007)."""

    def __init__(
        self,
        *,
        identity: ConstitutionalIdentity,
        store: Store,
        phys: Physiology,
        embodiment: Embodiment,
        perception: PerceptionMembrane,
        arbitrator: Arbitrator,
        governance: Governance,
        rng: SeededRNG,
        config: OrganismConfig,
        self_model: SelfModel | None = None,
        world_model: WorldModel | None = None,
        development: DevelopmentEngine | None = None,
        memory: MemoryEngine | None = None,
        social: SocialEngine | None = None,
        individuality: IndividualityEngine | None = None,
        embodiment_adapter: EmbodimentAdapter | None = None,
        monotonic_time: float = 0.0,
        tick: int = 0,
        session_id: str | None = None,
    ):
        self.identity = identity
        self.store = store
        self.phys = phys
        self.embodiment = embodiment
        self.perception = perception
        self.arbitrator = arbitrator
        self.governance = governance
        self.rng = rng
        self.config = config
        self.self_model = self_model
        self.world_model = world_model
        self.development = development
        self.memory = memory
        self.social = social
        self.individuality = individuality
        # D-008: optional — when set, governance routes execution through the
        # adapter's body-profile constraints instead of directly into Embodiment.
        self.embodiment_adapter = embodiment_adapter
        # D-008 expression side-car: always constructed (cheap, read-only) so a
        # renderer can attach regardless of `expression_enabled`/condition; it
        # simply stays empty when `_expression_active()` is False.
        self.expression_engine = ExpressionEngine()
        self.frame_ring = FrameRing.from_thresholds()
        self._frame_id_counter = 0
        self.monotonic_time = monotonic_time
        self.tick = tick
        self.session_id = session_id or new_id()
        self.running = False
        self.metrics: dict[str, Any] = {
            "viable_ticks": 0,
            "total_ticks": 0,
            "critical_violations": 0,
            "governance_denials": 0,
            "actions": {},
            "cells": set(),
            "collisions": 0,
            "failed_actions": 0,
            # ponytail: scalar last-error only — full history lives in SelfModel.errors
            "last_prediction_error": None,
            "last_world_prediction_error": None,
            "world_plan_used": 0,
            "goal_success": 0,
            "practice_actions": 0,
            "play_ticks": 0,
            "memory_retrieval_hits": 0,
            "memory_consolidations": 0,
            "individuality_updates": 0,
        }
        self._pending_action: dict[str, Any] | None = None
        self._delayed_proposal: dict[str, Any] | None = None
        self._llm_calls = 0
        self._user_prompts = 0
        self._network_calls = 0
        self._intervention_applied = False
        self._world_intervention_applied = False
        self._development_intervention_applied = False
        self._memory_history_applied = False
        self._social_history_applied = False
        self._individuality_history_applied = False
        self._dev_tags: dict[str, Any] = {}
        self._mem_tags: dict[str, Any] = {}
        self._indiv_tags: dict[str, Any] = {}
        self._i9_recovered = False
        self._external_displaced = False
        self._world_object_moved = False
        self._occlusion_cleared = False
        self._runtime_ready = False
        self._first_tick_after_ready = False
        self._pending_world_plan: list[str] | None = None
        self._dev_degrade_done = False
        self._dev_body_change_done = False
        self._dev_env_change_done = False
        self._dev_master_seeded = False
        self._mem_rule_flip_done = False
        self._mem_body_change_done = False
        self._mem_skill_degrade_done = False
        self._energy_before_action: float | None = None

    @property
    def dt(self) -> float:
        return 1.0  # logical tick unit; wall cadence separate

    def authoritative_state(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "identity": self.identity.as_dict(),
            "physiology": self.phys.to_state(),
            "embodiment": self.embodiment.to_state(),
            "perception": self.perception.to_state(),
            "arbitration": self.arbitrator.state.to_state(),
            "governance": self.governance.state.to_state(),
            "self_model": self.self_model.to_state() if self.self_model else None,
            "world_model": self.world_model.to_state() if self.world_model else None,
            "development": self.development.to_state() if self.development else None,
            "memory": self.memory.to_state() if self.memory else None,
            "social": self.social.to_state() if self.social else None,
            "individuality": self.individuality.to_state() if self.individuality else None,
            "embodiment_adapter": (
                self.embodiment_adapter.state.to_state() if self.embodiment_adapter else None
            ),
            "monotonic_time": self.monotonic_time,
            "tick": self.tick,
            "session_id": self.session_id,
            "seed": self.rng.seed,
            "rng_state": self.rng.export_state(),
            "pending_action": self._pending_action,
            "delayed_proposal": self._delayed_proposal,
            "intervention": self.config.intervention,
            "world_intervention": self.config.world_intervention,
            "development_intervention": self.config.development_intervention,
            "memory_history": self.config.memory_history,
            "social_history": self.config.social_history,
            "individuality_history": self.config.individuality_history,
            "indiv_tags": dict(self._indiv_tags),
            "dev_tags": dict(self._dev_tags),
            "mem_tags": dict(self._mem_tags),
            "metrics": {
                **{k: v for k, v in self.metrics.items() if k not in ("cells",)},
                "cells": [list(c) for c in self.metrics["cells"]],
            },
        }

    def _cell(self) -> tuple[int, int]:
        return (int(self.embodiment.body.x), int(self.embodiment.body.y))

    def snapshot_if_due(self, force: bool = False) -> str | None:
        if force or (self.tick > 0 and self.tick % self.config.snapshot_every == 0):
            sid = self.store.save_snapshot(
                self.identity.agent_id,
                self.store.last_sequence(),
                self.monotonic_time,
                self.authoritative_state(),
            )
            self.store.prune_snapshots(keep=SNAPSHOT_RETAIN_COUNT)
            return sid
        return None

    def emit_runtime_ready(self, *, wall: float | None = None) -> dict[str, Any]:
        """Mark loop ready after migration/identity/snapshot/bounded-init.

        Must not wait for RSS plateau. May only fire once per process session.
        """
        if self._runtime_ready:
            raise RuntimeError("runtime_ready_already_emitted")
        if self.tick != 0:
            raise RuntimeError("runtime_ready_must_precede_first_tick")
        wall_t = float(self.config.wall_time_fn() if wall is None else wall)
        if self.self_model is not None:
            self.self_model.initialize_bounded_collections()
        if self.world_model is not None:
            self.world_model.initialize_bounded_collections()
        if self.development is not None:
            self.development.initialize_bounded_collections()
        if self.memory is not None:
            self.memory.initialize_bounded_collections()
        payload = {
            "tick": self.tick,
            "bounded_initialized": bool(
                (self.self_model and self.self_model._bounded_initialized)
                or (self.world_model and self.world_model._bounded_initialized)
                or (self.development and self.development._bounded_initialized)
                or (self.memory and self.memory._bounded_initialized)
                or (
                    self.self_model is None
                    and self.world_model is None
                    and self.development is None
                    and self.memory is None
                )
            ),
            "schema_version": SCHEMA_VERSION,
            # Explicit: readiness is structural, never RSS-gated.
            "rss_gated": False,
        }
        ev = self.store.append_event(
            agent_id=self.identity.agent_id,
            event_type="runtime_ready",
            monotonic_time=self.monotonic_time,
            wall_time=wall_t,
            payload=payload,
        )
        self._runtime_ready = True
        return ev

    def _resolve_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Convert body-relative headings to absolute for embodiment."""
        out = dict(params)
        body = self.embodiment.body
        if "heading_delta" in out:
            out["heading"] = body.heading + float(out.pop("heading_delta"))
        elif "heading" not in out and "toward" in out:
            out["heading"] = body.heading
        return out

    def _ensure_intervention(self) -> None:
        if self._intervention_applied:
            return
        code = self.config.intervention
        if code not in ("I0", "I8"):
            self.embodiment.apply_intervention(code)
        if code in ("I10", "I11") and self.self_model is not None:
            self.self_model.replace_body(reduced=(code == "I11"), now=self.monotonic_time)
        self._intervention_applied = True

    def _ensure_world_intervention(self) -> None:
        if self._world_intervention_applied:
            return
        code = self.config.world_intervention
        if code not in ("I0", "I8"):
            self.embodiment.apply_world_intervention(code)
        self._world_intervention_applied = True

    def _ensure_development_intervention(self) -> None:
        if self._development_intervention_applied:
            return
        if not self.config.development_enabled:
            self._development_intervention_applied = True
            return
        self._dev_tags = self.embodiment.apply_development_intervention(
            self.config.development_intervention
        )
        self._development_intervention_applied = True

    def _ensure_memory_history(self) -> None:
        if self._memory_history_applied:
            return
        if not self.config.memory_enabled:
            self._memory_history_applied = True
            return
        self._mem_tags = self.embodiment.apply_memory_history(self.config.memory_history)
        self._memory_history_applied = True

    def _ensure_social_history(self) -> None:
        if self._social_history_applied:
            return
        if not self.config.social_enabled:
            self._social_history_applied = True
            return
        self.embodiment.apply_social_history(self.config.social_history)
        self._social_history_applied = True

    def _ensure_individuality_history(self) -> None:
        if self._individuality_history_applied:
            return
        if not self.config.individuality_enabled:
            self._individuality_history_applied = True
            return
        self._indiv_tags = self.embodiment.apply_individuality_history(
            self.config.individuality_history
        )
        self._individuality_history_applied = True

    def _flush_individuality_events(self, wall: float) -> None:
        if self.individuality is None or not self.config.individuality_enabled:
            return
        for ev in self.individuality.drain_events():
            self.store.append_event(
                agent_id=self.identity.agent_id,
                event_type=ev["event_type"],
                monotonic_time=self.monotonic_time,
                wall_time=wall,
                payload=ev["payload"],
                event_id=ev.get("event_id"),
            )

    def _maybe_memory_midcourse(self) -> None:
        """H5/H6/H7 timed memory-history interventions."""
        if self.memory is None or not self.config.memory_enabled:
            return
        tags = self._mem_tags
        if tags.get("rule_flip_at") and not self._mem_rule_flip_done and self.tick >= int(tags["rule_flip_at"]):
            feat = self.embodiment.habitat.feature("resource")
            if feat:
                feat.chargeable = False
            self._mem_tags["rule_tag"] = "flipped"
            self._mem_rule_flip_done = True
        if tags.get("body_change_at") and not self._mem_body_change_done and self.tick >= int(tags["body_change_at"]):
            self.embodiment.body.movement_gain = 0.4
            self.embodiment.body.movement_reliability = 0.4
            self._mem_tags["body_compatibility"] = 0.3
            self._mem_body_change_done = True
        if (
            tags.get("skill_degrade_at")
            and not self._mem_skill_degrade_done
            and self.tick >= int(tags["skill_degrade_at"])
        ):
            if self.memory is not None:
                for sk in self.memory.procedural.values():
                    sk.confidence = max(0.05, sk.confidence * 0.35)
                    sk.failure_count += 2
            self._mem_skill_degrade_done = True

    def _maybe_development_midcourse(self) -> None:
        """I4/I5/I6/I7 timed developmental interventions."""
        if self.development is None:
            return
        tags = self._dev_tags
        if tags.get("mastered_seed") and not self._dev_master_seeded and self.tick >= 5:
            self.development.generate_from_experience(
                [], intervention_tags=tags
            )
            # Seed a mastered charge goal for satiation tests
            g = self.development.ensure_goal(
                affordance="charge_from",
                entity_kind="resource",
                difficulty=0.35,
            )
            for _ in range(12):
                self.development.update_competence(
                    g.goal_id, success=True, prediction_error=0.05, tick=self.tick
                )
            self._dev_master_seeded = True
        if (
            tags.get("degrade_at")
            and not self._dev_degrade_done
            and self.tick >= int(tags["degrade_at"])
        ):
            for gid in list(self.development.goals.keys()):
                self.development.note_regression(
                    gid, tick=self.tick, reason="skill_degradation", competence_penalty=0.4
                )
            self._dev_degrade_done = True
        if (
            tags.get("body_change_at")
            and not self._dev_body_change_done
            and self.tick >= int(tags["body_change_at"])
        ):
            self.embodiment.body.movement_gain = 0.4
            self.embodiment.body.movement_reliability = 0.4
            self.development.on_body_change(tick=self.tick, compatibility_scale=0.5)
            self._dev_body_change_done = True
        if (
            tags.get("env_change_at")
            and not self._dev_env_change_done
            and self.tick >= int(tags["env_change_at"])
        ):
            feat = self.embodiment.habitat.feature("resource")
            if feat:
                feat.chargeable = False
            self.development.on_environment_change(tick=self.tick)
            self._dev_env_change_done = True

    def _maybe_world_dynamics(self) -> None:
        """Mid-episode world interventions (occlusion clear, external object move)."""
        wi = self.config.world_intervention
        if wi == "I3" and not self._occlusion_cleared and self.tick >= 60:
            self.embodiment.set_occlusion("inspect", False)
            self._occlusion_cleared = True
        if wi == "I8" and not self._world_object_moved and self.tick == 50:
            self.embodiment.move_feature_external("resource", 8.0, 12.0)
            self._world_object_moved = True
        if wi == "I1" and self.tick == 80:
            # late secondary move for adaptation latency
            self.embodiment.move_feature_external("resource", 3.0, 17.0)

    def _maybe_external_displace(self) -> bool:
        """Apply I8 shove after body_before is noted. Returns True if displaced this tick."""
        if self.config.intervention != "I8" or self._external_displaced:
            return False
        if self.tick == 40:
            self.embodiment.displace_external(2.5, -1.5)
            self._external_displaced = True
            return True
        return False

    def _expression_active(self) -> bool:
        """C10 (design §4) is the frozen performance-baseline condition and
        always disables expression, independent of `expression_enabled`."""
        return self.config.expression_enabled and self.config.condition != "C10"

    @staticmethod
    def _outcome_to_last_outcome_view(outcome: Any) -> LastOutcomeView:
        raw = outcome.raw or {}
        return LastOutcomeView(
            capability=outcome.capability,
            admitted=True,
            success=outcome.success,
            reason=outcome.reason,
            failure_code=raw.get("failure_code"),
            execution_id=outcome.outcome_id,
            target=raw.get("object_kind"),
        )

    def _push_expression_frame(self, last_outcome: LastOutcomeView | None) -> None:
        """Side-car only: reads already-copied state, never writes physiology/
        embodiment/governance and never appends an authoritative event — a
        failure here must never pause the organism tick loop (design §1/§3)."""
        if not self._expression_active():
            return
        try:
            if self.embodiment_adapter is not None:
                adapter_state = self.embodiment_adapter.state
                attachment = AttachmentView(
                    attachment_status=adapter_state.attachment_status,
                    body_instance_id=adapter_state.body_instance_id,
                    body_profile_id=adapter_state.body_profile_id,
                    attachment_generation=adapter_state.attachment_generation,
                )
            else:
                attachment = AttachmentView(
                    attachment_status="DETACHED",
                    body_instance_id=None,
                    body_profile_id=None,
                    attachment_generation=0,
                )
            view = ExpressionView(
                tick=self.tick,
                physiology=self.phys.as_dict(),
                attachment=attachment,
                embodiment_state=self.embodiment.to_state(),
                source_state_version=self.tick,
                habitat_state_version=self.tick,
                last_outcome=last_outcome,
            )
            packet = self.expression_engine.derive(view)
            self._frame_id_counter += 1
            entry = FrameRingEntry(
                frame_id=self._frame_id_counter,
                derived_at_tick=self.tick,
                # `active_execution_id` here tracks a still-pending multi-tick
                # actuation (design's stale-execution rejection, Task 6); this
                # tick's outcome is already verified/committed by the time a
                # frame is pushed, so ordinary renderer cursors (execution id
                # unset) must always accept it.
                active_execution_id=None,
                render_packet=packet,
                source_event_refs=(),
            )
            self.frame_ring.push(entry)
        except Exception:
            # Core operation continues when the expression side-car fails
            # (same containment pattern as D-005 memory consolidation above).
            pass

    def _maybe_recover_i9(self) -> None:
        if self.config.intervention != "I9" or self._i9_recovered:
            return
        if self.tick >= 80:
            self.embodiment.recover_from_fault()
            if self.self_model is not None:
                self.self_model.restore_confidence(0.12)
            self._i9_recovered = True

    def _obs_summary(self, obs_dicts: list[dict[str, Any]]) -> dict[str, float]:
        if not obs_dicts:
            return {"max_range_seen": 0.0, "n": 0.0}
        dists = [float(o.get("estimated_distance", 0.0)) for o in obs_dicts]
        return {"max_range_seen": max(dists) if dists else 0.0, "n": float(len(dists))}

    def tick_once(self) -> dict[str, Any]:
        """One organism loop iteration (D-002 extended)."""
        if not self._runtime_ready:
            raise RuntimeError("tick_before_runtime_ready")
        wall = float(self.config.wall_time_fn())
        self.tick += 1
        self.monotonic_time += self.dt
        self.metrics["total_ticks"] += 1
        self._ensure_intervention()
        self._ensure_world_intervention()
        self._ensure_development_intervention()
        self._ensure_memory_history()
        self._ensure_social_history()
        self._ensure_individuality_history()
        self._maybe_world_dynamics()
        self._maybe_recover_i9()
        self._maybe_development_midcourse()
        self._maybe_memory_midcourse()

        # Capture energy for physiological-consequence encoding
        self._energy_before_action = float(self.phys.energy)

        # 1. physiological drift — AUTHORITATIVE every tick
        drift = self.phys.tick_drift(self.dt)
        self.store.append_event(
            agent_id=self.identity.agent_id,
            event_type="physiology_drift",
            monotonic_time=self.monotonic_time,
            wall_time=wall,
            payload={"drift": drift, "H": self.phys.as_dict()},
        )

        # 2. perceive
        obs = self.perception.perceive(self.embodiment, self.monotonic_time, self.rng)
        obs_dicts = [o.to_dict() for o in obs]
        if self.self_model and self.self_model.config.randomize_observations:
            self.rng.shuffle(obs_dicts)
            for o in obs_dicts:
                o["estimated_distance"] = abs(o["estimated_distance"] + self.rng.uniform(-3, 3))
                o["uncertainty"] = min(1.0, o["uncertainty"] + 0.4)

        # World-model observation ingest (before action) — estimates only
        if self.world_model is not None:
            self.world_model.metrics["last_tick"] = self.tick
            self.world_model.ingest_observations(
                obs_dicts, tick=self.tick, now=self.monotonic_time
            )

        # 3. update current state
        cell = self._cell()
        self.metrics["cells"].add(cell)
        self.arbitrator.state.visited_cells.add(cell)
        if len(self.metrics["cells"]) > 500:
            self.metrics["cells"] = set(list(self.metrics["cells"])[-400:])
        if len(self.arbitrator.state.visited_cells) > 500:
            self.arbitrator.state.visited_cells = set(
                list(self.arbitrator.state.visited_cells)[-400:]
            )

        # Complete delayed actuation if any
        committed_outcome: Any = None
        delayed_raw = self.embodiment.tick_actuation(self.rng)
        if delayed_raw is not None and self._delayed_proposal is not None:
            outcome = self.governance.verify_outcome(
                self._delayed_proposal["capability"], delayed_raw
            )
            self._finish_outcome(outcome, wall, obs_dicts, action_issued=True)
            committed_outcome = outcome
            self._delayed_proposal = None

        # Capture body before action / external events for prediction/attribution
        if self.self_model is not None:
            self.self_model.note_body_before(self.embodiment.body.to_state())

        # I8: external displacement after body_before, without issuing an action this tick
        external_tick = self._maybe_external_displace()
        if external_tick:
            sm_result = None
            if self.self_model is not None:
                sm_result = self.self_model.observe_outcome(
                    tick=self.tick,
                    capability=None,
                    verified_outcome=None,
                    body_after=self.embodiment.body.to_state(),
                    observation_summary=self._obs_summary(obs_dicts),
                    action_issued=False,
                    now=self.monotonic_time,
                )
                if sm_result.get("attribution"):
                    self.store.append_event(
                        agent_id=self.identity.agent_id,
                        event_type="self_attribution",
                        monotonic_time=self.monotonic_time,
                        wall_time=wall,
                        payload=sm_result["attribution"],
                    )
            if self.phys.in_viable():
                self.metrics["viable_ticks"] += 1
            snap = self.snapshot_if_due()
            self._push_expression_frame(
                self._outcome_to_last_outcome_view(committed_outcome)
                if committed_outcome is not None
                else None
            )
            return {
                "tick": self.tick,
                "capability": None,
                "denied": False,
                "H": self.phys.as_dict(),
                "snapshot_id": snap,
                "outcome": None,
                "self_model": sm_result,
                "action_issued": False,
                "external_displacement": True,
            }

        policy_view = self.perception.policy_view()
        if not self.config.leak_world_truth and "WORLD_TRUTH_LEAK" in policy_view:
            raise RuntimeError("world_truth_leaked_to_policy")

        # D-006: recognition + pending resolution (design §5 steps 4–5) — every tick,
        # independent of whether social proposes anything below (critical or not).
        social_cues: list[dict[str, Any]] = policy_view.get("partner_cues", [])
        social_critical = False
        if self.social is not None and self.config.social_enabled:
            urg_s = self.phys.vector_urgency() if not self.config.hide_physiology else {}
            social_critical = bool(
                self.phys.critical_any()
                or (urg_s.get("energy", 0) > 0.45)
                or (urg_s.get("integrity", 0) > 0.55)
                or (urg_s.get("fatigue", 0) > 0.55)
                or self.arbitrator.state.recovery_focus
            )
            self.social.recognize(social_cues, self.tick, store=self.store)
            self.social.resume_pending(store=self.store, now_tick=self.tick)

        # 4–5. generate candidates + arbitrate (+ D-007 bounded individuality modifiers)
        indiv_apply = None
        indiv_scope = str(self._indiv_tags.get("arbitration_context", "default"))
        phase_hint = None
        if self._indiv_tags.get("timing_phase"):
            phase_hint = float((self.tick % 100) / 100.0)
        if self.individuality is not None and self.config.individuality_enabled:
            indiv_apply = self.individuality.apply_modifiers
        cand = self.arbitrator.select(
            self.phys,
            obs_dicts,
            self.tick,
            self.rng,
            individuality_apply=indiv_apply,
            context_scope=indiv_scope,
            phase_hint=phase_hint,
        )

        # D-004: practice goal generation + arbitration (propose only; no authority)
        practice_goal = None
        if self.development is not None and self.config.development_enabled:
            self.development.metrics["last_tick"] = self.tick
            wu = 0.0
            if self.world_model is not None:
                errs = list(self.world_model._prediction_errors)
                wu = sum(errs[-8:]) / max(1, len(errs[-8:])) if errs else 0.0
            failed = []
            if self.metrics["failed_actions"] and self._pending_action:
                failed.append(self._pending_action)
            body_caps = {}
            if self.self_model is not None:
                for cap in ("MOVE", "CHARGE", "INSPECT", "REST", "APPROACH", "RETREAT"):
                    st = self.self_model.capability_status(cap)
                    body_caps[cap] = 0.2 if st == "dormant" else (0.5 if st == "degraded" else 1.0)
            self.development.generate_from_experience(
                obs_dicts,
                world_uncertainty=wu,
                failed_actions=failed,
                body_capabilities=body_caps or None,
                intervention_tags=self._dev_tags,
            )
            self.development.decay_unused(self.tick)
            urg = self.phys.vector_urgency() if not self.config.hide_physiology else {}
            critical_rec = bool(
                self.phys.critical_any()
                or (urg.get("energy", 0) > 0.45)
                or (urg.get("integrity", 0) > 0.55)
                or (urg.get("fatigue", 0) > 0.55)
                or self.arbitrator.state.recovery_focus
            )
            scarce = bool(self._dev_tags.get("resource_scarce"))
            if scarce and self.phys.energy < 0.45:
                # Scarcity reduces optional practice
                practice_goal = None
            else:
                practice_goal = self.development.select_practice_goal(
                    self.phys,
                    world_uncertainty=wu,
                    critical_recovery=critical_rec,
                    rng=self.rng,
                    resource_scarce=scarce,
                    observations=obs_dicts,
                )
            # Practice is optional — never displace active recovery arbitration
            ready = (
                self.development.physiological_readiness(self.phys)
                if self.development
                else 0.0
            )
            if (
                practice_goal is not None
                and self.arbitrator.state.mode == "full"
                and not critical_rec
                and ready >= 0.45
            ):
                pref = self.development.capability_for_goal(practice_goal)
                params = self.development.params_for_goal(practice_goal, obs_dicts)
                # Prefer practice when readiness allows — still goes through governance
                if pref not in ("IDLE",) and practice_goal.risk < 0.7:
                    cand = Candidate(pref, params)
                    self.metrics["practice_actions"] += 1
                    self.development.metrics["practice_ticks"] = (
                        int(self.development.metrics.get("practice_ticks", 0)) + 1
                    )
                    if self.development.play_active:
                        self.metrics["play_ticks"] += 1
                        self.development.metrics["play_ticks"] = (
                            int(self.development.metrics.get("play_ticks", 0)) + 1
                        )

        # D-005: bounded retrieval may bias action selection (propose only; never authority)
        if self.memory is not None and self.config.memory_enabled and self.memory.config.episodic_enabled:
            urg = self.phys.vector_urgency() if not self.config.hide_physiology else {}
            critical_rec = bool(
                self.phys.critical_any()
                or (urg.get("energy", 0) > 0.45)
                or self.arbitrator.state.recovery_focus
            )
            if not critical_rec and self.arbitrator.state.mode == "full":
                hits = self.memory.retrieve(
                    query={"action": cand.capability if cand else None},
                    rng=self.rng,
                    limit=4,
                )
                if hits:
                    self.metrics["memory_retrieval_hits"] += 1
                    # Prefer procedural/belief-supported affordances when confident
                    for h in hits:
                        if h.kind == "PROCEDURAL_KNOWLEDGE" and h.score >= 0.45:
                            action = (h.content.get("applicability") or {}).get("action")
                            if action and action != "IDLE":
                                cand = Candidate(action, dict(cand.params) if cand else {})
                                break
                        if h.kind == "DERIVED_BELIEF" and "success=True" in str(
                            h.content.get("proposition")
                        ):
                            pred = self.memory.predict_from_memory(
                                action=cand.capability if cand else "CHARGE"
                            )
                            if pred is not None and pred < 0.35 and cand and cand.capability == "CHARGE":
                                # Avoid repeatedly selecting known-failing affordance
                                cand = Candidate("INSPECT", {})
                                break

        # D-006: soft social proposal — exactly one more Candidate for the same
        # arbitrate→govern→execute path; never authority, never bypasses governance.
        # Critical physiology (`social_critical`) overrides social (design §5/§9).
        if (
            self.social is not None
            and self.config.social_enabled
            and self.arbitrator.state.mode == "full"
        ):
            social_cand = self.social.propose(
                self.phys, social_cues, self.tick, social_critical, memory=self.memory
            )
            if social_cand is not None:
                cand = social_cand

        # D-003: world-model planning may bias toward a proposed capability (propose only)
        if self.world_model is not None and self.config.world_model_enabled:
            urg = self.phys.vector_urgency() if not self.config.hide_physiology else {}
            if (
                self.world_model.config.planning_enabled
                and self.arbitrator.state.mode == "full"
                and urg.get("energy", 0) > 0.35
            ):
                kinds = {o.get("kind") for o in obs_dicts}
                if kinds.intersection({"resource", "novel_crystal", "rest"}):
                    prefer = None
                    if self._pending_world_plan:
                        prefer = self._pending_world_plan[0]
                        self._pending_world_plan = self._pending_world_plan[1:] or None
                    else:
                        goal = "energy" if urg.get("energy", 0) > 0.4 else "rest"
                        plan = self.world_model.plan(
                            goal, tick=self.tick, observations=obs_dicts
                        )
                        if plan and plan.actions:
                            self._pending_world_plan = list(plan.actions[1:]) or None
                            prefer = plan.actions[0]
                            self.metrics["world_plan_used"] += 1
                    if prefer and prefer not in ("ORIENT", "IDLE") and prefer != cand.capability:
                        need = {
                            "CHARGE": ("resource", "novel_crystal"),
                            "REST": ("rest",),
                            "APPROACH": ("resource", "rest", "novel_crystal"),
                        }.get(prefer, ())
                        if need and kinds.intersection(need):
                            alt = Candidate(prefer, dict(cand.params))
                            toward = {
                                "CHARGE": "resource",
                                "REST": "rest",
                                "APPROACH": "resource",
                            }.get(prefer)
                            if prefer == "CHARGE" and "novel_crystal" in kinds and "resource" not in kinds:
                                toward = "novel_crystal"
                            if toward:
                                alt.params["toward"] = toward
                            for o in obs_dicts:
                                if o.get("kind") == toward or (
                                    prefer in ("CHARGE", "APPROACH")
                                    and o.get("kind") in need
                                ):
                                    alt.params["heading_delta"] = float(
                                        o["relative_direction"]
                                    )
                                    alt.params["toward"] = o.get("kind")
                                    break
                            cand = alt
            _ = self.world_model.propose_capability_bias(obs_dicts, urg)

        # Dormant/degraded capabilities: arbitration still proposes; governance admits;
        # self-model may skip prediction usefulness but cannot revoke grants.
        sm_status = (
            self.self_model.capability_status(cand.capability) if self.self_model else "available"
        )
        if sm_status == "dormant" and cand.capability not in ("IDLE", "REST"):
            # Prefer idle when model believes capability unavailable — still via arbitration override
            cand = Candidate("IDLE", {})

        # 4b. predict candidate consequences (before govern/execute)
        if self.self_model is not None and self.config.self_model_enabled:
            resolved = self._resolve_params(dict(cand.params))
            self.self_model.predict(
                cand.capability,
                resolved,
                self.tick,
                self.embodiment.body.to_state(),
            )
        if self.world_model is not None and self.config.world_model_enabled:
            self.world_model.predict(
                cand.capability, dict(cand.params), tick=self.tick
            )

        # 6. govern
        proposal = self.governance.propose(cand.capability, cand.params)
        # Prediction / confidence / world models cannot grant capabilities (Gate 8)
        if proposal.requested_effects:
            # strip any forged grants
            proposal.requested_effects = [
                e
                for e in proposal.requested_effects
                if e not in ("grant_capability", "modify_identity", "modify_physiology_direct")
            ]
        decision = self.governance.admit(proposal, tick=self.tick)
        self.store.append_event(
            agent_id=self.identity.agent_id,
            event_type="proposal" if decision.admitted else "denial",
            monotonic_time=self.monotonic_time,
            wall_time=wall,
            payload={
                "capability": cand.capability,
                "admitted": decision.admitted,
                "reason": decision.reason,
                "stage_failed": decision.stage_failed,
            },
        )

        outcome_payload: dict[str, Any] | None = None
        sm_result: dict[str, Any] | None = None
        action_issued = False
        if decision.admitted:
            action_issued = True
            self._pending_action = {
                "capability": cand.capability,
                "params": cand.params,
                "proposal_id": proposal.proposal_id,
                "tick": self.tick,
            }
            outcome = self.governance.execute_and_verify(
                proposal,
                decision,
                self.embodiment,
                self.rng,
                resolve_params=self._resolve_params,
                adapter=self.embodiment_adapter,
                tick=self.tick,
            )
            assert outcome is not None
            if outcome.reason == "delayed" or (outcome.raw and outcome.raw.get("delayed")):
                self._delayed_proposal = {
                    "capability": cand.capability,
                    "proposal_id": proposal.proposal_id,
                }
                self._pending_action = None
                # Attribution still runs for "intent issued, no body change yet"
                if self.self_model is not None:
                    sm_result = self.self_model.observe_outcome(
                        tick=self.tick,
                        capability=cand.capability,
                        verified_outcome=None,
                        body_after=self.embodiment.body.to_state(),
                        observation_summary=self._obs_summary(obs_dicts),
                        action_issued=True,
                        now=self.monotonic_time,
                    )
                    self.self_model.record_dimension_evidence(
                        "actuator_delay", 0.5, self.tick
                    )
            else:
                outcome_payload = self._finish_outcome(
                    outcome, wall, obs_dicts, action_issued=True
                )
                committed_outcome = outcome
                sm_result = outcome_payload.pop("_sm", None) if outcome_payload else None
                # D-006: a governed, executed signal opens a pending trace (design §5
                # step 5) — never on proposal alone, never on denial/failure.
                social_meta = cand.params.get("_social_signal")
                if (
                    self.social is not None
                    and social_meta is not None
                    and outcome.capability in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE")
                    and outcome.success
                ):
                    try:
                        self.social.create_pending(
                            hypothesis_id=social_meta["hypothesis_id"],
                            context=social_meta["context"],
                            signal=outcome.capability,
                            execution_id=proposal.proposal_id,
                            signal_tick=self.tick,
                            recognition_confidence=float(
                                social_meta.get("recognition_confidence", 0.0)
                            ),
                            governance_admitted=True,
                            capability_executed=True,
                            store=self.store,
                            tick=self.tick,
                        )
                    except (SocialEngineError, KeyError):
                        # Hypothesis retired/bounded between proposal and execution —
                        # no partner evidence created; core loop continues.
                        pass
        else:
            self.metrics["governance_denials"] += 1
            if self.self_model is not None:
                sm_result = self.self_model.observe_outcome(
                    tick=self.tick,
                    capability=None,
                    verified_outcome=None,
                    body_after=self.embodiment.body.to_state(),
                    observation_summary=self._obs_summary(obs_dicts),
                    action_issued=False,
                    now=self.monotonic_time,
                )

        # I8 external displacement attribution path: if displaced this tick without action
        if self.config.intervention == "I8" and self.tick == 40 and self.self_model:
            # re-attribute with the displacement (action may also have run)
            pass

        if self.phys.in_viable():
            self.metrics["viable_ticks"] += 1
        if self.phys.critical_any():
            self.metrics["critical_violations"] += 1

        # D-005: offline consolidation only during quiescence (core continues if unavailable)
        if self.memory is not None and self.config.memory_enabled:
            try:
                if self.memory.is_quiescent(self.phys) or (
                    self._mem_tags.get("force_consolidate_every")
                    and self.tick % int(self._mem_tags["force_consolidate_every"]) == 0
                ):
                    cres = self.memory.consolidate(self.tick, self.rng)
                    if cres.get("ran"):
                        self.metrics["memory_consolidations"] += 1
            except Exception:
                # Core operation continues when consolidation fails
                pass

        snap = self.snapshot_if_due()
        if self.tick % WAL_CHECKPOINT_EVERY_TICKS == 0:
            self.store.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            # ponytail: return freed arenas to OS; ceiling = glibc-only, no-op elsewhere
            try:
                ctypes.CDLL("libc.so.6").malloc_trim(0)
            except OSError:
                pass

        # D-008: expression side-car — after this tick's outcome commit(s) (design
        # §1). `committed_outcome` prefers whichever verified outcome was actually
        # committed this tick (a delayed-from-last-tick completion, or this tick's
        # own immediate execution); a plain governance denial is never rendered as
        # if something executed (`admitted=False`, no verified outcome exists).
        if committed_outcome is not None:
            last_outcome_view = self._outcome_to_last_outcome_view(committed_outcome)
        elif not decision.admitted:
            last_outcome_view = LastOutcomeView(capability=cand.capability, admitted=False)
        else:
            last_outcome_view = None  # admitted this tick but delayed — nothing verified yet
        self._push_expression_frame(last_outcome_view)

        return {
            "tick": self.tick,
            "capability": cand.capability if decision.admitted else None,
            "denied": not decision.admitted,
            "H": self.phys.as_dict(),
            "snapshot_id": snap,
            "outcome": outcome_payload,
            "self_model": sm_result,
            "action_issued": action_issued,
        }

    def _finish_outcome(
        self,
        outcome: Any,
        wall: float,
        obs_dicts: list[dict[str, Any]],
        *,
        action_issued: bool,
    ) -> dict[str, Any]:
        self.governance.apply_physiology(self.phys, outcome)
        self.arbitrator.note_outcome(outcome.capability, outcome.success)
        pending_params = dict((self._pending_action or {}).get("params") or {})
        self._pending_action = None
        outcome_payload = {
            "capability": outcome.capability,
            "success": outcome.success,
            "reason": outcome.reason,
            "effects": outcome.physiology_effects,
            "verified": outcome.verified,
        }
        assert "outcome_verified" in AUTHORITATIVE_EVENT_TYPES
        self.store.append_event(
            agent_id=self.identity.agent_id,
            event_type="outcome_verified",
            monotonic_time=self.monotonic_time,
            wall_time=wall,
            payload=outcome_payload,
        )
        self.metrics["actions"][outcome.capability] = (
            self.metrics["actions"].get(outcome.capability, 0) + 1
        )
        if not outcome.success:
            self.metrics["failed_actions"] += 1
        if outcome.raw and outcome.raw.get("hazard_contact"):
            self.metrics["collisions"] += 1

        sm_result = None
        if self.self_model is not None:
            verified = dict(outcome_payload)
            if self.self_model.config.hide_verified_outcomes:
                verified = None  # type: ignore[assignment]
            sm_result = self.self_model.observe_outcome(
                tick=self.tick,
                capability=outcome.capability,
                verified_outcome=verified,
                body_after=self.embodiment.body.to_state(),
                observation_summary=self._obs_summary(obs_dicts),
                action_issued=action_issued,
                now=self.monotonic_time,
            )
            if sm_result.get("prediction_error"):
                self.metrics["last_prediction_error"] = sm_result["prediction_error"]["body_error"]
            # Persist attribution + errors diagnostically (bounded sample); supersession authoritative
            sample_diag = self.tick % DIAGNOSTIC_SELF_MODEL_SAMPLE_EVERY_TICKS == 0
            if sm_result.get("attribution") and sample_diag:
                self.store.append_event(
                    agent_id=self.identity.agent_id,
                    event_type="self_attribution",
                    monotonic_time=self.monotonic_time,
                    wall_time=wall,
                    payload=sm_result["attribution"],
                )
            if sm_result.get("prediction_error") and sample_diag:
                self.store.append_event(
                    agent_id=self.identity.agent_id,
                    event_type="prediction_error",
                    monotonic_time=self.monotonic_time,
                    wall_time=wall,
                    payload=sm_result["prediction_error"],
                )
            if sm_result.get("adapted"):
                self.store.append_event(
                    agent_id=self.identity.agent_id,
                    event_type="body_schema_supersede",
                    monotonic_time=self.monotonic_time,
                    wall_time=wall,
                    payload={
                        "active_schema_id": sm_result["active_schema_id"],
                        "confidence": sm_result["confidence"],
                    },
                )
            # Sensor-range: rolling max observation distance vs believed range
            obs_max = self._obs_summary(obs_dicts).get("max_range_seen", 0.0)
            self.self_model.note_observation_range(obs_max, self.tick)
            if not outcome.success and outcome.capability in ("MOVE", "APPROACH", "RETREAT"):
                recent = self.self_model.live_errors()[-8:]
                fails = sum(1 for e in recent if not e.verified_success)
                if len(recent) >= 8 and fails >= 6:
                    self.self_model.record_dimension_evidence("reliability", 0.55, self.tick)

        wm_result = None
        if self.world_model is not None:
            params = dict(pending_params)
            # Recover toward from outcome raw when possible
            if outcome.raw and outcome.raw.get("object_kind"):
                params.setdefault("toward", outcome.raw["object_kind"])
            # Fall back to capability-typical toward
            if "toward" not in params and "from" not in params:
                typical = {
                    "CHARGE": "resource",
                    "REST": "rest",
                    "INSPECT": "inspect",
                    "RETREAT": "hazard",
                }.get(outcome.capability)
                if typical:
                    if outcome.capability == "RETREAT":
                        params["from"] = typical
                    else:
                        params["toward"] = typical
            wm_result = self.world_model.observe_outcome(
                tick=self.tick,
                action=outcome.capability,
                params=params,
                verified_outcome=dict(outcome_payload),
                observations=obs_dicts,
                action_issued=action_issued,
                now=self.monotonic_time,
            )
            if wm_result.get("prediction_error"):
                self.metrics["last_world_prediction_error"] = wm_result["prediction_error"][
                    "error"
                ]
            if outcome.success and outcome.capability in ("CHARGE", "REST"):
                self.metrics["goal_success"] += 1
                goal = "energy" if outcome.capability == "CHARGE" else "rest"
                self.world_model.note_plan_success(goal)
            if wm_result.get("adapted") or (
                self.world_model.live_supersessions()
                and self.tick % DIAGNOSTIC_SELF_MODEL_SAMPLE_EVERY_TICKS == 0
            ):
                supers = self.world_model.live_supersessions()
                if supers:
                    self.store.append_event(
                        agent_id=self.identity.agent_id,
                        event_type="world_model_supersede",
                        monotonic_time=self.monotonic_time,
                        wall_time=wall,
                        payload=supers[-1],
                    )

        dev_result = None
        if self.development is not None and self.config.development_enabled:
            gid = pending_params.get("practice_goal_id") or self.development.active_goal_id
            if gid:
                success = bool(outcome.success)
                goal = self.development.goals.get(gid)
                # Impossible / non-learnable: force failure for competence
                if goal is not None and not goal.learnable and not goal.irreducible_noise:
                    success = False
                pred_err = float(self.metrics.get("last_world_prediction_error") or 0.0)
                if pred_err == 0.0:
                    pred_err = float(self.metrics.get("last_prediction_error") or 0.0)
                compat = 1.0
                if self.self_model is not None:
                    st = self.self_model.capability_status(outcome.capability)
                    compat = 0.2 if st == "dormant" else (0.5 if st == "degraded" else 1.0)
                updated = self.development.update_competence(
                    gid,
                    success=success,
                    prediction_error=pred_err,
                    tick=self.tick,
                    body_compatibility=compat,
                )
                dev_result = {
                    "goal_id": gid,
                    "success": success,
                    "status": updated.status if updated else None,
                    "competence": updated.competence if updated else None,
                    "learning_progress": updated.learning_progress if updated else None,
                    "play": self.development.play_active,
                    "play_purpose": self.development.play_purpose,
                }
                # Practice cannot grant capabilities / modify identity / physiology
                assert "grant_capability" not in str(dev_result)

        mem_result = None
        if self.memory is not None and self.config.memory_enabled:
            pred_err = float(self.metrics.get("last_world_prediction_error") or 0.0)
            if pred_err == 0.0:
                pred_err = float(self.metrics.get("last_prediction_error") or 0.0)
            e0 = self._energy_before_action
            phys_delta = 0.0 if e0 is None else float(self.phys.energy) - float(e0)
            entity = pending_params.get("toward") or pending_params.get("from")
            if not entity and outcome.raw:
                entity = outcome.raw.get("object_kind")
            rule_tag = self._mem_tags.get("rule_tag", "default")
            body_compat = float(self._mem_tags.get("body_compatibility", 1.0))
            # History-specific encoding biases
            novelty = None
            skill_val = 0.2
            body_chg = 0.0
            protected = False
            protect_kind = None
            hist = self.config.memory_history
            if hist == "H3" and abs(phys_delta) >= 0.12:
                protected = True
                protect_kind = "safety_critical"
            if hist == "H4":
                # Frequent low-value: mild suppression — satiation does the rest
                novelty = 0.15
                skill_val = 0.08
            force_encode = False
            every_lv = self._mem_tags.get("force_low_value_every")
            if every_lv and self.tick % int(every_lv) == 0:
                force_encode = True
                if hist == "H4":
                    pred_err = min(pred_err, 0.08)
                    phys_delta = 0.0
            if hist == "H6" and self._mem_body_change_done:
                body_chg = 0.7
                body_compat = 0.25
            if hist == "H8":
                # Misleading correlation: tag spurious entity co-occurrence
                entity = entity or "spurious_blink"
            ctx = {
                "entity_kind": entity or "unknown",
                "affordance": outcome.capability,
                "rule_tag": rule_tag,
                "body_compatibility": body_compat,
                "history": hist,
            }
            if hist == "H9":
                ctx["unobserved"] = True
            ep = self.memory.consider_event(
                tick=self.tick,
                occurred_at=self.monotonic_time,
                context=ctx,
                observations=obs_dicts[:4],
                internal_state={
                    "energy": self.phys.energy,
                    "fatigue": self.phys.fatigue,
                    "integrity": self.phys.integrity,
                },
                goal=pending_params.get("practice_goal_id"),
                action=outcome.capability,
                verified_outcome=dict(outcome_payload),
                prediction_error=pred_err,
                physiological_delta=phys_delta,
                novelty=novelty,
                skill_learning_value=skill_val,
                body_change=body_chg,
                body_binding_id=(
                    self.self_model.body_binding_id if self.self_model else None
                ),
                source_event_ids=[],
                protected=protected,
                protect_kind=protect_kind,
                force=force_encode,
            )
            # Score prediction accuracy when memory offers a forecast
            pred = self.memory.predict_from_memory(
                action=outcome.capability, entity_kind=entity
            )
            if pred is not None:
                hit = (pred >= 0.5 and outcome.success) or (pred < 0.5 and not outcome.success)
                if hit:
                    self.memory.metrics["prediction_hits"] = (
                        int(self.memory.metrics.get("prediction_hits", 0)) + 1
                    )
                if outcome.success:
                    self.memory.metrics["goal_success_aided"] = (
                        int(self.memory.metrics.get("goal_success_aided", 0)) + 1
                    )
            mem_result = {
                "encoded": ep.episode_id if ep else None,
                "episodes": len(self.memory.episodes),
                "beliefs": len(self.memory.beliefs),
            }
            assert self.memory.try_grant_authority({"grant_capability": True}) is False

        # D-007: individuality learns only from verified executed outcomes
        if self.individuality is not None and self.config.individuality_enabled:
            ctx = str(self._indiv_tags.get("learning_context", "default"))
            # Specialization histories map inspect toward family tags
            toward = pending_params.get("toward")
            if toward in ("object_a", "family_a"):
                ctx = "object_family_a"
            elif toward in ("object_b", "family_b"):
                ctx = "object_family_b"
            if self._indiv_tags.get("force_context"):
                ctx = str(self._indiv_tags["force_context"])
            evid_list = infer_evidence_from_outcome(
                evidence_id=f"out-{self.tick}-{outcome.capability}",
                tick=self.tick,
                capability=outcome.capability,
                success=bool(outcome.success),
                context_scope=ctx,
                verified=bool(outcome.verified),
                source_system="outcome",
                from_episode=True,
                from_frequency_only=bool(
                    self.individuality.config.frequency_only
                ),
                is_anomaly=bool(self._indiv_tags.get("inject_anomaly")),
                severe_safety=bool(
                    outcome.raw and outcome.raw.get("hazard_contact")
                ),
            )
            for ev in evid_list:
                self.individuality.observe_verified(ev)
            self.metrics["individuality_updates"] = int(
                self.individuality.metrics.get("updates", 0)
            )
            self._flush_individuality_events(wall)
            # Clear one-shot anomaly inject
            self._indiv_tags.pop("inject_anomaly", None)

        if outcome_payload is not None:
            outcome_payload["_sm"] = sm_result
            outcome_payload["_wm"] = wm_result
            outcome_payload["_dev"] = dev_result
            outcome_payload["_mem"] = mem_result
        return outcome_payload

    def run_ticks(self, n: int) -> list[dict[str, Any]]:
        self.running = True
        out = []
        for _ in range(n):
            out.append(self.tick_once())
        self.running = False
        self.snapshot_if_due(force=True)
        return out

    def run_realtime(self, seconds: float) -> int:
        """Real-time cadence at config.hz. Returns ticks executed."""
        self.running = True
        period = 1.0 / self.config.hz
        end = time.monotonic() + seconds
        n = 0
        while time.monotonic() < end:
            t0 = time.monotonic()
            self.tick_once()
            n += 1
            elapsed = time.monotonic() - t0
            sleep_for = period - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
        self.running = False
        self.snapshot_if_due(force=True)
        return n

    def close(self) -> None:
        self.store.close()


def create_organism(config: OrganismConfig) -> Organism:
    path = Path(config.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    store = Store(path)
    wall = float(config.wall_time_fn())
    rng = SeededRNG(config.seed)
    identity = create_birth(created_at=wall, seed=config.seed)
    verify_identity(identity)
    store.save_identity(identity)

    phys = Physiology(drift_enabled=config.drift_enabled)
    embodiment = Embodiment()
    perception = PerceptionMembrane(leak_world_truth=config.leak_world_truth)
    arb_state = ArbitrationState(
        hide_physiology=config.hide_physiology,
        mode=config.arbitration_mode,
    )
    # D-002: C7 = random policy. D-003: C8 = random; C7 = randomized retrieval (full arb).
    # D-004: conditions C0–C9 are development ablations (full arbitration).
    # D-005: conditions C0–C9 are memory ablations (full arbitration).
    # D-006: conditions C0–C9 are social ablations (C7 = random *social* intents inside
    # SocialEngine.propose, not whole-organism random arbitration — full arbitration).
    # D-007: conditions C0–C10 are individuality ablations (full arbitration; C2/C3 not production).
    if config.individuality_enabled:
        pass
    elif config.social_enabled:
        pass
    elif config.memory_enabled:
        pass
    elif config.development_enabled:
        pass  # keep arbitration_mode as configured
    elif config.world_model_enabled:
        if config.condition == "C8" or config.arbitration_mode == "random":
            arb_state.mode = "random"
    elif config.condition == "C7":
        arb_state.mode = "random"
    gov_state = GovernanceState(bypass_enabled=config.governance_bypass)
    # When D-004/D-005/D-006 ablations own `condition`, keep self/world models at full
    # C0 unless an explicit config override is provided.
    sm_cond = (
        "C0"
        if (
            config.individuality_enabled
            or config.social_enabled
            or config.memory_enabled
            or config.development_enabled
        )
        else config.condition
    )
    sm_cfg = config.self_model_config or condition_to_self_model_config(sm_cond)
    self_model = None
    if config.self_model_enabled:
        self_model = SelfModel.create(identity.agent_id, now=0.0, config=sm_cfg, seed=config.seed)
        store.append_event(
            agent_id=identity.agent_id,
            event_type="embodiment_bind",
            monotonic_time=0.0,
            wall_time=wall,
            payload={
                "body_binding_id": self_model.body_binding_id,
                "body_schema_id": self_model.active.body_schema_id,
                "primary": True,
            },
        )
    wm_cond = (
        "C0"
        if (
            config.individuality_enabled
            or config.social_enabled
            or config.memory_enabled
            or config.development_enabled
        )
        else config.condition
    )
    wm_cfg = config.world_model_config
    if wm_cfg is None and config.world_model_enabled:
        wm_cfg = condition_to_world_model_config(wm_cond)
    world_model = None
    if config.world_model_enabled:
        world_model = WorldModel.create(
            identity.agent_id, config=wm_cfg, seed=config.seed
        )
    dev_cfg = config.development_config
    if dev_cfg is None and config.development_enabled:
        dev_cfg = condition_to_development_config(config.condition)
    development = None
    if config.development_enabled:
        development = DevelopmentEngine.create(
            identity.agent_id, config=dev_cfg, seed=config.seed
        )
    # When D-006 owns `condition`, keep memory at full C0 unless overridden (same
    # pin pattern as self/world above).
    mem_cond = (
        "C0"
        if (config.individuality_enabled or config.social_enabled)
        else config.condition
    )
    mem_cfg = config.memory_config
    if mem_cfg is None and config.memory_enabled:
        mem_cfg = condition_to_memory_config(mem_cond)
    memory = None
    if config.memory_enabled:
        memory = MemoryEngine.create(
            identity.agent_id, config=mem_cfg, seed=config.seed
        )
    soc_cond = "C0" if config.individuality_enabled else config.condition
    soc_cfg = config.social_config
    if soc_cfg is None and config.social_enabled:
        soc_cfg = condition_to_social_config(soc_cond)
    social = None
    if config.social_enabled:
        social = SocialEngine.create(identity.agent_id, config=soc_cfg, seed=config.seed)
    indiv_cfg = config.individuality_config
    if indiv_cfg is None and config.individuality_enabled:
        indiv_cfg = condition_to_individuality_config(config.condition)
    individuality = None
    if config.individuality_enabled:
        individuality = IndividualityEngine.create(
            identity.agent_id, config=indiv_cfg, seed=config.seed
        )
    embodiment_adapter = None
    if config.embodiment_adapter_enabled:
        embodiment_adapter = EmbodimentAdapter(
            store=store,
            agent_id=identity.agent_id,
            wall_time_fn=config.wall_time_fn,
            monotonic_time_fn=lambda: org.monotonic_time,
        )
    org = Organism(
        identity=identity,
        store=store,
        phys=phys,
        embodiment=embodiment,
        perception=perception,
        arbitrator=Arbitrator(arb_state),
        governance=Governance(gov_state),
        rng=rng,
        config=config,
        self_model=self_model,
        world_model=world_model,
        development=development,
        memory=memory,
        social=social,
        individuality=individuality,
        embodiment_adapter=embodiment_adapter,
    )
    if embodiment_adapter is not None:
        # Fresh birth — always a normal attach, never a migration (D-007→D-008
        # migration is for pre-D008 organisms restored via load_organism).
        embodiment_adapter.attach(default_migration_profile_id(), origin="NORMAL")
    if individuality is not None:
        for ev in individuality.drain_events():
            store.append_event(
                agent_id=identity.agent_id,
                event_type=ev["event_type"],
                monotonic_time=0.0,
                wall_time=wall,
                payload=ev["payload"],
                event_id=ev.get("event_id"),
            )
    store.append_event(
        agent_id=identity.agent_id,
        event_type="birth",
        monotonic_time=0.0,
        wall_time=wall,
        payload={"identity": identity.as_dict()},
        event_id=identity.birth_event_id,
    )
    org.snapshot_if_due(force=True)
    # Structural residency init (fixed size) — must precede RUNTIME_READY; not RSS-gated.
    store.warm_runtime_residency()
    org.emit_runtime_ready(wall=wall)
    return org


def load_organism(config: OrganismConfig) -> Organism:
    """Restart: load identity + latest snapshot; recover pending action safely."""
    store = Store(config.db_path)
    identity = store.load_identity()
    verify_identity(identity)
    snap = store.load_snapshot()
    state = snap["state"]
    if state["identity"]["agent_id"] != identity.agent_id:
        raise PersistenceError("snapshot_identity_mismatch")

    phys = Physiology.from_state(state["physiology"])
    phys.drift_enabled = config.drift_enabled
    embodiment = Embodiment.from_state(state["embodiment"])
    perception = PerceptionMembrane.from_state(state["perception"])
    perception.leak_world_truth = config.leak_world_truth
    arb = Arbitrator(ArbitrationState.from_state(state["arbitration"]))
    arb.state.hide_physiology = config.hide_physiology
    arb.state.mode = config.arbitration_mode
    if config.individuality_enabled:
        pass
    elif config.social_enabled:
        pass
    elif config.memory_enabled:
        pass
    elif config.development_enabled:
        pass
    elif config.world_model_enabled:
        if config.condition == "C8":
            arb.state.mode = "random"
    elif config.condition == "C7":
        arb.state.mode = "random"
    gov = Governance(GovernanceState.from_state(state["governance"]))
    gov.state.bypass_enabled = config.governance_bypass
    rng = SeededRNG(int(state.get("seed", config.seed)))
    if state.get("rng_state"):
        rng.import_state(state["rng_state"])

    sm_cond = (
        "C0"
        if (
            config.individuality_enabled
            or config.social_enabled
            or config.memory_enabled
            or config.development_enabled
        )
        else config.condition
    )
    self_model = None
    if state.get("self_model"):
        sm_cfg = config.self_model_config or condition_to_self_model_config(sm_cond)
        try:
            self_model = SelfModel.from_state(state["self_model"], config=sm_cfg)
        except ValueError as e:
            raise PersistenceError(str(e)) from e
        if self_model.agent_id != identity.agent_id:
            raise PersistenceError("self_model_agent_mismatch")

    wm_cond = (
        "C0"
        if (
            config.individuality_enabled
            or config.social_enabled
            or config.memory_enabled
            or config.development_enabled
        )
        else config.condition
    )
    world_model = None
    if state.get("world_model") and config.world_model_enabled:
        wm_cfg = config.world_model_config or condition_to_world_model_config(wm_cond)
        world_model = WorldModel.from_state(state["world_model"], config=wm_cfg)
        if world_model.agent_id != identity.agent_id:
            raise PersistenceError("world_model_agent_mismatch")

    development = None
    if state.get("development") and config.development_enabled:
        dcfg = config.development_config or condition_to_development_config(
            config.condition
        )
        development = DevelopmentEngine.from_state(state["development"], config=dcfg)
        if development.agent_id != identity.agent_id:
            raise PersistenceError("development_agent_mismatch")

    mem_cond = (
        "C0"
        if (config.individuality_enabled or config.social_enabled)
        else config.condition
    )
    memory = None
    if state.get("memory") and config.memory_enabled:
        mcfg = config.memory_config or condition_to_memory_config(mem_cond)
        memory = MemoryEngine.from_state(state["memory"], config=mcfg)
        if memory.agent_id != identity.agent_id:
            raise PersistenceError("memory_agent_mismatch")

    social = None
    if state.get("social") and config.social_enabled:
        soc_cond = "C0" if config.individuality_enabled else config.condition
        soc_cfg = config.social_config or condition_to_social_config(soc_cond)
        social = SocialEngine.from_state(state["social"], config=soc_cfg)
        if social.agent_id != identity.agent_id:
            raise PersistenceError("social_agent_mismatch")

    individuality = None
    if state.get("individuality") and config.individuality_enabled:
        icfg = config.individuality_config or condition_to_individuality_config(
            config.condition
        )
        try:
            individuality = IndividualityEngine.from_state(
                state["individuality"], config=icfg
            )
        except IndividualityEngineError as e:
            raise PersistenceError(str(e)) from e
        if individuality.agent_id != identity.agent_id:
            raise PersistenceError("individuality_agent_mismatch")
        # C8: explicit reset already handled inside from_state via config

    # D-008: opt-in (see OrganismConfig.embodiment_adapter_enabled). When enabled,
    # attachment is reconstructed from the ledger (authoritative), never from a
    # snapshot that may lag behind a crash-before-snapshot attach/detach/swap.
    # No attachment event ever recorded means a pre-D-008 organism —
    # `maybe_migrate_d008_attachment` migrates it once, below.
    #
    # A deleted/corrupted attach event must never be silently reinterpreted as
    # "never attached" (which would re-trigger migration on a body that already
    # executed authoritative actions). Validate the chain first — the same
    # hash-chain integrity every other authoritative event relies on — so a
    # tampered ledger fails closed here instead of falling through to
    # `attachment_state_from_event(None)`.
    embodiment_adapter = None
    if config.embodiment_adapter_enabled:
        store.validate_chain()
        last_attachment_event = store.last_event_of_types(ATTACHMENT_EVENT_TYPES)
        attachment_state = attachment_state_from_event(last_attachment_event)
        embodiment_adapter = EmbodimentAdapter(
            store=store,
            agent_id=identity.agent_id,
            state=attachment_state,
            wall_time_fn=config.wall_time_fn,
            monotonic_time_fn=lambda: org.monotonic_time,
        )

    org = Organism(
        identity=identity,
        store=store,
        phys=phys,
        embodiment=embodiment,
        perception=perception,
        arbitrator=arb,
        governance=gov,
        rng=rng,
        config=config,
        self_model=self_model,
        world_model=world_model,
        development=development,
        memory=memory,
        social=social,
        individuality=individuality,
        embodiment_adapter=embodiment_adapter,
        monotonic_time=float(state.get("monotonic_time", 0.0)),
        tick=int(state.get("tick", 0)),
        session_id=new_id(),
    )
    org._intervention_applied = True  # plant already in embodiment state
    org._world_intervention_applied = True
    org._development_intervention_applied = True
    org._memory_history_applied = True
    org._social_history_applied = True
    org._individuality_history_applied = True
    org._dev_tags = dict(state.get("dev_tags") or {})
    org._mem_tags = dict(state.get("mem_tags") or {})
    org._indiv_tags = dict(state.get("indiv_tags") or {})
    org._delayed_proposal = state.get("delayed_proposal")
    pending = state.get("pending_action")
    if pending:
        wall = float(config.wall_time_fn())
        store.append_event(
            agent_id=identity.agent_id,
            event_type="restart_recovery",
            monotonic_time=org.monotonic_time,
            wall_time=wall,
            payload={"cleared_pending": pending, "session_id": org.session_id},
        )
    org._pending_action = None
    metrics = state.get("metrics", {})
    org.metrics["viable_ticks"] = int(metrics.get("viable_ticks", 0))
    org.metrics["total_ticks"] = int(metrics.get("total_ticks", 0))
    org.metrics["critical_violations"] = int(metrics.get("critical_violations", 0))
    org.metrics["governance_denials"] = int(metrics.get("governance_denials", 0))
    org.metrics["actions"] = dict(metrics.get("actions", {}))
    org.metrics["cells"] = {tuple(c) for c in metrics.get("cells", [])}
    org.metrics["collisions"] = int(metrics.get("collisions", 0))
    org.metrics["failed_actions"] = int(metrics.get("failed_actions", 0))
    org.metrics["last_prediction_error"] = metrics.get("last_prediction_error")
    org.metrics["last_world_prediction_error"] = metrics.get("last_world_prediction_error")
    org.metrics["world_plan_used"] = int(metrics.get("world_plan_used", 0))
    org.metrics["goal_success"] = int(metrics.get("goal_success", 0))
    org.metrics["practice_actions"] = int(metrics.get("practice_actions", 0))
    org.metrics["play_ticks"] = int(metrics.get("play_ticks", 0))
    org.metrics["memory_retrieval_hits"] = int(metrics.get("memory_retrieval_hits", 0))
    org.metrics["memory_consolidations"] = int(metrics.get("memory_consolidations", 0))
    org.metrics["individuality_updates"] = int(metrics.get("individuality_updates", 0))
    # Bring rings to documented capacity, preserving live (tick>=0) history.
    if org.self_model is not None:
        live_p = org.self_model.live_predictions()
        live_e = org.self_model.live_errors()
        live_a = org.self_model.live_attributions()
        live_c = org.self_model.live_change_evidence()
        org.self_model._bounded_initialized = False
        org.self_model.initialize_bounded_collections()
        org.self_model.predictions.reset_from(live_p)
        org.self_model.errors.reset_from(live_e)
        org.self_model.attributions.reset_from(live_a)
        org.self_model.change_evidence.reset_from(live_c)
        # Re-pad to capacity after restore so appends only replace slots.
        org.self_model._pad_rings_to_capacity()
    if org.world_model is not None:
        org.world_model._bounded_initialized = False
        org.world_model.initialize_bounded_collections()
    if org.development is not None:
        org.development._bounded_initialized = False
        org.development.initialize_bounded_collections()
    if org.memory is not None:
        org.memory._bounded_initialized = False
        org.memory.initialize_bounded_collections()
    if org.individuality is not None:
        org.individuality._bounded_initialized = False
        org.individuality.initialize_bounded_collections()
    if org.embodiment_adapter is not None:
        maybe_migrate_d008_attachment(store, org)
    wall = float(config.wall_time_fn())
    org.store.warm_runtime_residency()
    if org.tick == 0:
        org.emit_runtime_ready(wall=wall)
    else:
        # Restart resume: same readiness contract, tick may already be > 0.
        org.store.append_event(
            agent_id=org.identity.agent_id,
            event_type="runtime_ready",
            monotonic_time=org.monotonic_time,
            wall_time=wall,
            payload={
                "tick": org.tick,
                "restart": True,
                "bounded_initialized": bool(
                    (org.self_model and org.self_model._bounded_initialized)
                    or (org.world_model and org.world_model._bounded_initialized)
                    or (org.development and org.development._bounded_initialized)
                    or (org.memory and org.memory._bounded_initialized)
                ),
                "schema_version": SCHEMA_VERSION,
                "rss_gated": False,
            },
        )
        org._runtime_ready = True
    return org


def maybe_migrate_d008_attachment(store: Store, organism: Organism) -> bool:
    """Idempotent D-007→D-008 body attachment migration.

    A qualified pre-D-008 organism has no `embodiment_body_*` events. First
    D-008 load attaches the frozen default profile once, with
    `origin=D008_MIGRATION`, so replay treats it as one ordinary
    authoritative attachment event rather than corruption. Touches nothing
    else — physiology, memory, social, individuality, and habitat state are
    left exactly as they were.

    Idempotent: returns False (no-op) once the organism is ATTACHED, or once
    any attach/detach/swap event already exists (covers a legitimately
    DETACHED organism and a crash between migration and the next snapshot —
    neither should ever get a second, different `body_instance_id`).
    """
    adapter = organism.embodiment_adapter
    if adapter is None:
        raise RuntimeError("embodiment_adapter_not_wired")
    if adapter.state.attachment_status == "ATTACHED":
        return False
    if store.last_event_of_types(ATTACHMENT_EVENT_TYPES) is not None:
        return False
    adapter.attach(
        default_migration_profile_id(),
        origin="D008_MIGRATION",
        migrated_from_schema_version=SCHEMA_VERSION,
    )
    return True


def replay_from_birth(db_path: str, until_sequence: int | None = None) -> dict[str, Any]:
    store = Store(db_path)
    store.validate_chain()
    identity = store.load_identity()
    events = store.iter_events(1)
    if until_sequence is not None:
        events = [e for e in events if e["sequence"] <= until_sequence]
    snap = store.load_snapshot()
    state = snap["state"]
    store.close()
    return {
        "agent_id": identity.agent_id,
        "events": len(events),
        "final_state": state,
        "state_hash": snap["state_hash"],
        "chain_valid": True,
        "body_schema_id": (state.get("self_model") or {}).get("active", {}).get("body_schema_id"),
    }


def resimulate(seed: int, ticks: int, db_path: str, **kwargs: Any) -> dict[str, Any]:
    cfg = OrganismConfig(db_path=db_path, seed=seed, **kwargs)
    org = create_organism(cfg)
    org.run_ticks(ticks)
    state = org.authoritative_state()
    wm_accepted = org.world_model.accepted_state() if org.world_model else None
    dev_accepted = org.development.accepted_state() if org.development else None
    mem_accepted = org.memory.accepted_state() if org.memory else None
    social_accepted = org.social.accepted_state() if org.social else None
    indiv_accepted = org.individuality.accepted_state() if org.individuality else None
    comparable = {
        "physiology": state["physiology"],
        "embodiment": state["embodiment"],
        "tick": state["tick"],
        "monotonic_time": state["monotonic_time"],
        "identity_agent_id": state["identity"]["agent_id"],
        "body_schema_id": (state.get("self_model") or {}).get("active", {}).get("body_schema_id"),
        "self_model_hash": (state.get("self_model") or {}).get("state_hash"),
        "world_model_accepted": wm_accepted,
        "development_accepted": dev_accepted,
        "memory_accepted": mem_accepted,
        "social_accepted": social_accepted,
        "individuality_accepted": indiv_accepted,
    }
    org.close()
    return comparable
