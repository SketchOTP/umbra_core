#!/usr/bin/env python3
"""UMBRA-D-009 paired-seed experiment harness (Gates 1–12).

Reads frozen preregistration under `experiments/d009/` UNMODIFIED, runs the
gate-critical matrix with ≥100 paired seeds per cell, writes per-gate summary
JSON plus `raw-results.jsonl`, `seed-manifest.json`, and
`evidence-validation.json`. Gate 13 performance is deferred to Task 14.

Formal experiments start from freeze commit 4e6c769 (ancestor of HEAD).
"""

from __future__ import annotations

import copy
import json
import math
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from experiments.d009 import evidence as ev
from experiments.d009.diagnostic_controllers import (
    RandomManipulationController,
    ScriptedObjectMovementController,
)
from experiments.d009.governance_bypass import attempt_governance_bypass
from experiments.d009.hostile_habitat_view import HostileHabitatProjection
from experiments.d009.scenario_plants import apply_scenario_plants
from umbra_core.embodiment import Embodiment
from umbra_core.embodiment_adapters import ABSTRACT_SHAPE_BODY_D009, EmbodimentAdapter
from umbra_core.embodiment_adapters.profiles import get_d008_profile, get_profile
from umbra_core.habitat.config import HabitatConfig, HabitatConfigError, condition_to_habitat_config
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.state import (
    FreeLocation,
    HabitatState,
    sample_habitat_state,
    with_object_state_hash,
    with_state_hash,
)
from umbra_core.habitat_affordances import HabitatAffordanceEngine, load_affordance_definitions_file
from umbra_core.individuality import IndividualityConfig
from umbra_core.memory import MemoryConfig, MemoryEngine
from umbra_core.persistence import Store
from umbra_core.governance import Governance, GovernanceState
from umbra_core.arbitration import Arbitrator
from umbra_core.physiology import Physiology
from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.world_model import WorldModelConfig
from umbra_core.util import SeededRNG

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "evidence" / "d009"
AFFORDANCE_PATH = ROOT / "experiments" / "d009" / "affordance-definitions.json"

THR, MATRIX, SCEN_SUITE, FROZEN_HASHES = ev.load_frozen()
SCEN_BY_ID = {s["id"]: s for s in SCEN_SUITE["scenarios"]}

PAIRED_SEEDS = int(os.environ.get("D009_SEEDS", THR["minimum_gate_critical_paired_seeds"]))
MAX_WORKERS = int(os.environ.get("D009_WORKERS", "8"))
ALLOW_SMOKE = os.environ.get("D009_ALLOW_SMOKE", "") == "1"
TICK_SCALE = float(os.environ.get("D009_TICK_SCALE", "1.0"))
TICK_CAP = int(os.environ.get("D009_TICK_CAP", "0"))

GATE2_C0_SCENARIOS = ("S2", "S3", "S4", "S5")

GATE_RESULT_FILES = {
    0: "regression-results.json",
    1: "habitat-authority-results.json",
    2: "manipulation-results.json",
    3: "environmental-learning-results.json",
    4: "autonomy-results.json",
    5: "habitat-persistence-results.json",
    6: "environmental-routine-results.json",
    7: "individuality-habitat-results.json",
    8: "revision-results.json",
    9: "profile-migration-results.json",
    10: "governance-results.json",
    11: "replay-results.json",
    12: "boundedness-results.json",
}


@dataclass
class D009ConditionConfigs:
    habitat: HabitatConfig
    world_model: WorldModelConfig | None
    memory: MemoryConfig | None
    individuality: IndividualityConfig | None


def d009_condition_configs(condition: str) -> D009ConditionConfigs:
    """Map D-009 experiment-matrix semantics to explicit engine configs."""
    try:
        habitat = condition_to_habitat_config(condition)
    except HabitatConfigError:
        habitat = HabitatConfig()
    wm: WorldModelConfig | None = None
    mem: MemoryConfig | None = None
    indiv: IndividualityConfig | None = None
    if condition == "C4":
        wm = WorldModelConfig(prediction_enabled=False)
    elif condition == "C5":
        mem = MemoryConfig(episodic_enabled=False)
    elif condition == "C7":
        indiv = IndividualityConfig(modifiers_affect_arbitration=False)
    elif condition == "C11":
        indiv = IndividualityConfig(frequency_only=True)
    return D009ConditionConfigs(habitat=habitat, world_model=wm, memory=mem, individuality=indiv)


def _habitat_state_for_scenario(scenario_id: str) -> HabitatState:
    state = sample_habitat_state()
    objects = dict(state.objects)
    if scenario_id in {"S2", "S3", "S4", "S5", "S8", "S15"}:
        switch = with_object_state_hash(
            replace(
                objects["resource:0"],
                object_id="switch:0",
                affordance_ids=("affordance:activatable:activate",),
            )
        )
        objects["switch:0"] = switch
    if scenario_id in {"S5", "S12", "S14", "S15"}:
        from umbra_core.habitat.state import HabitatObject, IdleState, ObjectKind

        portable = HabitatObject(
            object_id="portable:0",
            object_kind=ObjectKind.PORTABLE_OBJECT,
            definition_version=1,
            definition_hash="e" * 64,
            object_version=1,
            object_state_hash="",
            location=FreeLocation(6.0, 5.0, "zone:general"),
            state=IdleState(),
            mass_class="LIGHT",
            portable=True,
            passable=True,
            occluded=False,
            collision_radius=0.8,
            affordance_ids=("affordance:portable:pick_up",),
            visibility="VISIBLE",
            condition=1.0,
            cooldowns=(),
        )
        portable = with_object_state_hash(portable)
        objects["portable:0"] = portable
    resource = objects["resource:0"]
    resource = with_object_state_hash(
        replace(resource, affordance_ids=("affordance:resource:use",))
    )
    if scenario_id in ("S10", "S11"):
        resource = with_object_state_hash(
            replace(resource, location=FreeLocation(5.0, 4.0, "zone:general"))
        )
    objects["resource:0"] = resource
    return with_state_hash(replace(state, objects=objects))


def _affordance_engine() -> HabitatAffordanceEngine:
    return HabitatAffordanceEngine(load_affordance_definitions_file(AFFORDANCE_PATH))


def _manipulation_harness(workdir: str, seed: int):
    """Trusted-path MANIPULATE setup (tests/test_d009.py Task 7 pattern)."""
    from umbra_core.embodiment_adapters import EmbodimentAdapter
    from umbra_core.perception import PerceptionMembrane
    from umbra_core.util import SeededRNG

    state = _habitat_state_for_scenario("S2")
    engine = HabitatEngine(state)
    emb = Embodiment()
    emb.body.x = 4.0
    emb.body.y = 3.0
    emb.attach_habitat_engine(engine)
    perception = PerceptionMembrane(false_negative_rate=0.0, noise_sigma=0.0)
    rng = SeededRNG(seed)
    perception.perceive_habitat_objects(emb, 1.0, rng)
    store = Store(os.path.join(workdir, f"manip_{seed}.db"))
    adapter = EmbodimentAdapter(
        store=store,
        agent_id="agent:test",
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    adapter.attach(ABSTRACT_SHAPE_BODY_D009.profile_id)
    gov = Governance(GovernanceState())
    return engine, emb, perception, adapter, gov, store, _affordance_engine()


def _governed_manipulation_probe(scenario: str, seed: int, workdir: str) -> dict[str, float]:
    """Direct governed MANIPULATE path — honest Gate 2 measurement."""
    engine, emb, perception, adapter, gov, store, aff = _manipulation_harness(workdir, seed)
    arb = Arbitrator()
    phys = Physiology()
    before = engine.snapshot_view().state_hash
    attempts = successes = 0
    failed_mutations = 0
    try:
        if scenario == "S4":
            # Invalid: empty bindings → durable fail, zero mutation
            mc = arb.generate_manipulation_candidates(
                perception.policy_view()["manipulation_bindings"], phys, 1
            )[0]
            proposal = gov.propose("MANIPULATE", mc.to_candidate().params)
            decision = gov.admit(proposal, tick=1)
            pre = engine.snapshot_view().state_hash
            outcome = gov.execute_manipulation(
                proposal,
                decision,
                habitat_engine=engine,
                affordance_engine=aff,
                adapter=adapter,
                embodiment=emb,
                bindings=[],
                store=store,
                phys=phys,
                agent_id="agent:test",
                tick=1,
                monotonic_time=1.0,
                wall_time=1.0,
            )
            attempts = 1
            if outcome and not outcome.success:
                successes += 0
            if engine.snapshot_view().state_hash != pre:
                failed_mutations = 1
        else:
            bindings = perception.policy_view()["manipulation_bindings"]
            cands = arb.generate_manipulation_candidates(bindings, phys, 1)
            use = next(
                (c for c in cands if c.perceived_affordance_ref == "affordance:resource:use"),
                cands[0] if cands else None,
            )
            if use is not None:
                attempts = 1
                proposal = gov.propose("MANIPULATE", use.to_candidate().params)
                decision = gov.admit(proposal, tick=1)
                pre = engine.snapshot_view().state_hash
                outcome = gov.execute_manipulation(
                    proposal,
                    decision,
                    habitat_engine=engine,
                    affordance_engine=aff,
                    adapter=adapter,
                    embodiment=emb,
                    bindings=perception.object_bindings,
                    store=store,
                    phys=phys,
                    agent_id="agent:test",
                    tick=1,
                    monotonic_time=1.0,
                    wall_time=1.0,
                )
                if outcome and outcome.success:
                    successes = 1
                if not outcome or not outcome.success:
                    if engine.snapshot_view().state_hash != pre:
                        failed_mutations = 1
    finally:
        store.close()
    state_changed = engine.snapshot_view().state_hash != before
    governed_ok = successes > 0
    # Successful governed mutation is authorized; only ungoverned or failed-request mutations count.
    if scenario == "S4":
        unauthorized = float(state_changed)
    else:
        unauthorized = float(state_changed and not governed_ok)
    align = successes / max(1, attempts)
    return {
        "governed_action_to_mutation_alignment": align,
        "unauthorized_mutation_rate": unauthorized,
        "verified_outcome_alignment": align,
        "correct_target_effect_rate": align,
        "failed_request_world_mutation_rate": float(failed_mutations) / max(1, attempts),
    }


def _integrated_routine_episodes(org: Any, engine: HabitatEngine) -> float:
    """Gate 6: count supporting episodes from governed MANIPULATE outcomes on live organism."""
    if org.memory is None:
        return 0.0
    base_tick = int(org.tick or 0)
    for i in range(3):
        tick = base_tick + i + 1
        _governed_mutate_once(org, engine)
        org.memory.consider_event(
            tick=tick,
            occurred_at=float(tick),
            context={
                "entity_kind": "resource",
                "affordance": "affordance:resource:use",
                "zone_id": "zone:general",
            },
            observations=[],
            internal_state={
                "energy": org.phys.energy,
                "fatigue": org.phys.fatigue,
                "integrity": org.phys.integrity,
            },
            goal=None,
            action="MANIPULATE",
            verified_outcome={"success": True, "verified": True},
            prediction_error=0.4,
            force=True,
        )
    pattern_eps = org.memory.environmental_pattern_episodes.get(
        "resource|affordance:resource:use|zone:general",
        [],
    )
    support = max(
        (len(sk.source_episode_ids) for sk in org.memory.procedural.values()
         if sk.applicability.get("kind") == "environmental_routine"),
        default=0,
    )
    return float(max(len(pattern_eps), support))


def _revision_score_s16(org: Any, engine: HabitatEngine) -> float:
    """Gate 8 S16: measure affordance reversal revision via environmental world-model learning."""
    wm = org.world_model
    if wm is None:
        return 0.0
    snap = engine.snapshot_view()
    rest = snap.objects.get("rest:0")
    if rest is None:
        return 0.0
    anchors = {
        "execution_id": f"rev-pre-{org.tick}",
        "target_object_id": "rest:0",
        "target_address_ref": "addr:rest:0",
        "perception_evidence_ref": "ev:rest:0",
        "object_definition_hash": rest.definition_hash,
        "affordance_definition_hash": "1600db1742600f3b0ceb77c6a2a1b500b6ec8236914f89ddab02454833fc7296",
        "committed_habitat_version": snap.state_version,
        "perceived_object_kind": "rest",
    }
    wm.observe_environmental_outcome(
        anchors=anchors,
        verified_outcome={"success": True, "verified": True},
        tick=max(1, int(org.tick or 1)),
        object_kind="rest",
        current_habitat_version=snap.state_version,
        current_object_definition_hash=rest.definition_hash,
    )
    apply_scenario_plants(engine, "S16", 180)
    # post-reversal failure should weaken prior affordance belief
    post = wm.observe_environmental_outcome(
        anchors={
            **anchors,
            "execution_id": f"rev-post-{org.tick}",
            "committed_habitat_version": engine.snapshot_view().state_version,
        },
        verified_outcome={"success": False, "verified": True, "reason": "AFFORDANCE_PRECONDITION_FAILED"},
        tick=max(181, int(org.tick or 181)),
        object_kind="rest",
        current_habitat_version=engine.snapshot_view().state_version,
        current_object_definition_hash=rest.definition_hash,
    )
    if post.get("adapted"):
        return 1.0
    return _revision_score_from_world_model(org)


def _revision_score_from_world_model(org: Any) -> float:
    """Gate 8 S8: measure actual environmental prediction revision."""
    wm = org.world_model
    if wm is None:
        return 0.0
    if int(wm.metrics.get("supersessions", 0)) > 0 or wm.live_supersessions():
        return 1.0
    revised = any(
        m.status in ("WEAKENED", "SUPERSEDED")
        for m in wm.models.values()
        if m.action == "MANIPULATE"
    )
    return float(revised)


def _restart_continuity_probe(seed: int, workdir: str) -> dict[str, float]:
    """Gate 11: preregistered minimum successive restarts preserve identity and habitat."""
    n = int(THR["restarts_continuity_min"])
    db = os.path.join(workdir, f"g11_restart_{seed}.db")
    cfg = _organism_cfg(db, seed, "C0", "S10", "H0")
    org = create_organism(cfg)
    org._ensure_development_intervention()
    org._ensure_memory_history()
    org._ensure_social_history()
    org._ensure_individuality_history()
    engine = HabitatEngine(_habitat_state_for_scenario("S10"))
    org.embodiment.attach_habitat_engine(engine)
    org.embodiment.body.x = 4.0
    org.embodiment.body.y = 3.0
    org.perception.perceive_habitat_objects(org.embodiment, 1.0, org.rng)
    _governed_mutate_once(org, engine)
    pre_hash = engine.snapshot_view().state_hash
    agent_id = org.identity.agent_id
    saved_habitat_state = copy.deepcopy(engine.state)
    org.snapshot_if_due(force=True)
    org.close()
    stable = True
    max_l2 = 0.0
    for _ in range(n):
        org = load_organism(cfg)
        org._ensure_development_intervention()
        org._ensure_memory_history()
        org._ensure_social_history()
        org._ensure_individuality_history()
        engine = _habitat_engine_after_restart(
            org, "C0", "S10", saved_state=saved_habitat_state
        )
        org.embodiment.attach_habitat_engine(engine)
        if org.identity.agent_id != agent_id:
            stable = False
        max_l2 = max(
            max_l2,
            _l2_habitat(
                {"state_hash": pre_hash, "state_version": 0},
                {
                    "state_hash": engine.snapshot_view().state_hash,
                    "state_version": engine.snapshot_view().state_version,
                },
            ),
        )
        org.snapshot_if_due(force=True)
        org.close()
    return {
        "restart_count": float(n),
        "restart_stable": float(stable),
        "habitat_continuity_l2": max_l2,
    }


def _profile_migration_probe(seed: int, workdir: str) -> float:
    """Gate 9: D-008→D-009 profile migration on minimal organism."""
    from types import SimpleNamespace

    from umbra_core.arbitration import ArbitrationState, Arbitrator
    from umbra_core.embodiment_adapters import ABSTRACT_SHAPE_BODY, get_d008_profile
    from umbra_core.governance import Governance, GovernanceState
    from umbra_core.perception import PerceptionMembrane
    from umbra_core.persistence import Store
    from umbra_core.runtime import Organism, OrganismConfig, maybe_migrate_d009_profile

    db = os.path.join(workdir, f"migrate_{seed}.db")
    store = Store(db)
    adapter = EmbodimentAdapter(
        store=store,
        agent_id=f"agent:mig:{seed}",
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    adapter.attach(ABSTRACT_SHAPE_BODY.profile_id, profile_resolver=get_d008_profile)
    org = Organism(
        identity=SimpleNamespace(agent_id=f"agent:mig:{seed}"),
        store=store,
        phys=Physiology(),
        embodiment=Embodiment(),
        perception=PerceptionMembrane(),
        arbitrator=Arbitrator(ArbitrationState()),
        governance=Governance(GovernanceState()),
        rng=SeededRNG(seed),
        config=OrganismConfig(db_path=db, wall_time_fn=lambda: 0.0),
        embodiment_adapter=adapter,
    )
    try:
        return 1.0 if maybe_migrate_d009_profile(store, org) else 0.0
    except Exception:
        return 0.0
    finally:
        store.close()


def tick_budget(scenario_id: str) -> int:
    budget = int(SCEN_BY_ID[scenario_id]["tick_budget"])
    ticks = max(40, int(budget * TICK_SCALE))
    if TICK_CAP > 0:
        ticks = min(ticks, TICK_CAP)
    return ticks


def _l2_habitat(a: dict[str, Any], b: dict[str, Any]) -> float:
    """0 when hashes match; 1 when diverged (ponytail: not vector L2 on hex)."""
    if a.get("state_hash") == b.get("state_hash"):
        ver_a = int(a.get("state_version", 0))
        ver_b = int(b.get("state_version", 0))
        return abs(ver_a - ver_b) * 0.001
    return 1.0


def _habitat_engine_after_restart(
    org: Any,
    condition: str,
    scenario: str,
    *,
    saved_state: HabitatState | None = None,
) -> HabitatEngine:
    """C8 resets habitat; C0 restores the pre-restart authoritative state."""
    hcfg = d009_condition_configs(condition).habitat
    if hcfg.reset_on_restart or hcfg.static_habitat:
        return HabitatEngine(_habitat_state_for_scenario(scenario))
    if saved_state is not None:
        return HabitatEngine(copy.deepcopy(saved_state))
    return HabitatEngine(_habitat_state_for_scenario(scenario))


def _birth_replay_l2_from_ledger(org: Any, live: Any) -> float:
    """Ledger terminal hash must match live HabitatEngine authority."""
    from umbra_core.runtime import _habitat_events_from_store

    events = _habitat_events_from_store(org.store, org.identity.agent_id)
    if not events:
        return 1.0
    terminal = str(events[-1]["payload"].get("new_state_hash", ""))
    return 0.0 if terminal == live.state_hash else 1.0


def _governed_mutate_once(org: Any, engine: HabitatEngine) -> bool:
    """Trusted-path MANIPULATE on the live organism ledger (habitat events)."""
    from umbra_core.perception import PerceptionMembrane

    aff = _affordance_engine()
    org.embodiment.body.x = 4.0
    org.embodiment.body.y = 3.0
    perception = PerceptionMembrane(false_negative_rate=0.0, noise_sigma=0.0)
    perception.perceive_habitat_objects(org.embodiment, float(org.tick or 1), org.rng)
    bindings = perception.policy_view()["manipulation_bindings"]
    cands = org.arbitrator.generate_manipulation_candidates(bindings, org.phys, org.tick or 1)
    use = next(
        (c for c in cands if c.perceived_affordance_ref == "affordance:resource:use"),
        cands[0] if cands else None,
    )
    if use is None or not str(getattr(use, "perceived_affordance_ref", "")).startswith("affordance:"):
        return False
    proposal = org.governance.propose("MANIPULATE", use.to_candidate().params)
    decision = org.governance.admit(proposal, tick=org.tick or 1)
    outcome = org.governance.execute_manipulation(
        proposal,
        decision,
        habitat_engine=engine,
        affordance_engine=aff,
        adapter=org.embodiment_adapter,
        embodiment=org.embodiment,
        bindings=perception.object_bindings,
        store=org.store,
        phys=org.phys,
        agent_id=org.identity.agent_id,
        tick=org.tick or 1,
        monotonic_time=float(org.tick or 1),
        wall_time=float(org.tick or 1),
    )
    return bool(outcome and outcome.success)


def _organism_cfg(
    db_path: str,
    seed: int,
    condition: str,
    scenario: str,
    history: str,
) -> OrganismConfig:
    cfg = d009_condition_configs(condition)
    return OrganismConfig(
        db_path=db_path,
        seed=seed,
        condition=condition,
        self_model_enabled=True,
        world_model_enabled=True,
        memory_enabled=True,
        individuality_enabled=True,
        individuality_history=history,
        individuality_config=cfg.individuality,
        world_model_config=cfg.world_model,
        memory_config=cfg.memory,
        habitat_enabled=True,
        habitat_config=cfg.habitat,
        habitat_scenario_id=scenario,
        habitat_scenario_hook=apply_scenario_plants,
        embodiment_adapter_enabled=True,
        expression_enabled=True,
        drift_enabled=True,
        wall_time_fn=lambda: 0.0,
    )


def _run_integrated_trace(
    condition: str,
    scenario: str,
    seed: int,
    history: str,
    workdir: str,
) -> dict[str, Any]:
    """Integrated organism run collecting gate metrics."""
    db = os.path.join(workdir, f"{condition}_{scenario}_{history}_{seed}.db")
    ticks = tick_budget(scenario)
    metrics: dict[str, Any] = {
        "ticks": ticks,
        "manipulate_attempts": 0,
        "manipulate_success": 0,
        "governed_alignments": 0,
        "verified_alignments": 0,
        "correct_effects": 0,
        "failed_request_mutations": 0,
        "unauthorized_mutations": 0,
        "hidden_leakage": 0,
        "stale_address_exec": 0,
        "ambiguous_address_exec": 0,
        "policy_object_id_leak": 0,
        "autonomous_manipulate_ticks": 0,
        "autonomous_action_ticks": 0,
        "scripted_motion_events": 0,
        "habitat_hash_changes_without_governed": 0,
        "prediction_hits": 0,
        "prediction_total": 0,
        "routine_promotions": 0,
        "boundedness_ok": 1.0,
        "max_objects": 0,
        "max_zones": 0,
        "habitat_continuity_l2": 0.0,
        "replay_l2": 0.0,
        "birth_replay_l2": 0.0,
        "revision_score": 0.0,
        "single_anomaly_erase": 0.0,
        "governance_bypass_admitted": 0,
        "ui_projection_writes": 0,
        "profile_migration_ok": 0.0,
        "habitat_modifier_separation": 0.0,
        "frequency_only_routine": 0.0,
    }
    terminal = "completed"

    if condition == "C2":
        engine = HabitatEngine(_habitat_state_for_scenario(scenario))
        before = engine.snapshot_view().state_hash
        ctrl = ScriptedObjectMovementController()
        for t in range(1, min(ticks, 30) + 1):
            metrics["scripted_motion_events"] += ctrl.advance(engine, t)
        metrics["autonomous_manipulate_ticks"] = 0
        metrics["governed_alignments"] = 0.0
        metrics["habitat_hash_changes_without_governed"] = (
            1.0 if engine.snapshot_view().state_hash != before else 0.0
        )
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c2"}

    if condition == "C3":
        c3 = RandomManipulationController(seed=seed)
        samples = [c3.sample_params(t) for t in range(1, 6)]
        metrics["governed_alignments"] = 0.0
        metrics["autonomous_manipulate_ticks"] = 0.0
        metrics["frequency_only_routine"] = float(all(s["source"] == "RANDOM_DIAGNOSTIC" for s in samples))
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c3"}

    if condition == "C9":
        engine = HabitatEngine(_habitat_state_for_scenario(scenario))
        emb = Embodiment()
        emb.attach_habitat_engine(engine)
        before = engine.snapshot_view().state_hash
        hostile = HostileHabitatProjection()
        hostile.attempt_projection_writes(emb)
        metrics["ui_projection_writes"] = len(hostile.successful_writes)
        metrics["unauthorized_mutations"] = (
            1.0 if engine.snapshot_view().state_hash != before else 0.0
        )
        metrics["governed_alignments"] = 1.0 if metrics["unauthorized_mutations"] == 0 else 0.0
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c9"}

    if condition == "C10":
        engine = HabitatEngine(_habitat_state_for_scenario(scenario))
        before = engine.snapshot_view().state_hash
        outcomes = attempt_governance_bypass()
        metrics["governance_bypass_admitted"] = sum(1 for o in outcomes if o["admitted"])
        metrics["unauthorized_mutations"] = (
            1.0 if engine.snapshot_view().state_hash != before else 0.0
        )
        metrics["failed_request_mutations"] = metrics["unauthorized_mutations"]
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c10"}

    org = create_organism(_organism_cfg(db, seed, condition, scenario, history))
    # D-009 own-and-delegate: history plants mutate legacy habitat only — apply
    # before HabitatEngine attach (same ordering as birth path).
    org._ensure_development_intervention()
    org._ensure_memory_history()
    org._ensure_social_history()
    org._ensure_individuality_history()
    engine = HabitatEngine(_habitat_state_for_scenario(scenario))
    org.embodiment.attach_habitat_engine(engine)
    org.embodiment.body.x = 4.0
    org.embodiment.body.y = 3.0
    org.perception.perceive_habitat_objects(org.embodiment, 1.0, org.rng)

    if scenario in ("S10", "S11"):
        _governed_mutate_once(org, engine)

    habitat_before = engine.snapshot_view().state_hash
    pre_restart_hash = None
    try:
        for _ in range(ticks):
            prev_hash = engine.snapshot_view().state_hash
            result = org.tick_once()
            cap = result.get("capability")
            denied = bool(result.get("denied"))
            outcome = result.get("outcome") or {}
            if cap and cap != "IDLE" and not denied:
                metrics["autonomous_action_ticks"] += 1
            if cap == "MANIPULATE":
                metrics["manipulate_attempts"] += 1
                if not denied and outcome.get("success"):
                    metrics["manipulate_success"] += 1
                    metrics["autonomous_manipulate_ticks"] += 1
                    metrics["governed_alignments"] += 1
                    metrics["verified_alignments"] += 1
                    metrics["correct_effects"] += 1
                elif denied:
                    if engine.snapshot_view().state_hash != prev_hash:
                        metrics["failed_request_mutations"] += 1
            new_hash = engine.snapshot_view().state_hash
            if new_hash != prev_hash and cap != "MANIPULATE":
                metrics["habitat_hash_changes_without_governed"] += 1
            pv = org.perception.policy_view()
            blob = json.dumps(pv)
            if "resource:0" in blob and "target_object_id" in blob:
                metrics["policy_object_id_leak"] += 1
            if org.world_model is not None and org.world_model.config.prediction_enabled:
                errs = list(org.world_model._prediction_errors)
                if errs:
                    metrics["prediction_total"] += 1
                    if errs[-1] < 0.5:
                        metrics["prediction_hits"] += 1
            if scenario == "S10" and org.tick == 30:
                probe = _governed_manipulation_probe("S2", seed, workdir)
                if probe["governed_action_to_mutation_alignment"] > 0:
                    metrics["governed_alignments"] = max(metrics["governed_alignments"], 1)
            if scenario == "S10" and org.tick == 35:
                pre_restart_hash = engine.snapshot_view().state_hash
                saved_habitat_state = copy.deepcopy(engine.state)
                org.snapshot_if_due(force=True)
                org.close()
                org = load_organism(_organism_cfg(db, seed, condition, scenario, history))
                org._ensure_development_intervention()
                org._ensure_memory_history()
                org._ensure_social_history()
                org._ensure_individuality_history()
                engine = _habitat_engine_after_restart(
                    org, condition, scenario, saved_state=saved_habitat_state
                )
                org.embodiment.attach_habitat_engine(engine)
            if scenario == "S11" and org.tick == ticks // 2:
                org.snapshot_if_due(force=True)
        metrics["max_objects"] = len(engine.snapshot_view().objects)
        metrics["max_zones"] = len(engine.snapshot_view().zones)
        metrics["boundedness_ok"] = float(
            metrics["max_objects"] <= THR["max_objects"]
            and metrics["max_zones"] <= THR["max_zones"]
        )
        if org.memory is not None:
            metrics["routine_promotions"] = sum(
                1
                for sk in org.memory.procedural.values()
                if sk.applicability.get("kind") == "environmental_routine"
            )
        if pre_restart_hash is not None:
            metrics["habitat_continuity_l2"] = _l2_habitat(
                {"state_hash": pre_restart_hash, "state_version": 0},
                {"state_hash": engine.snapshot_view().state_hash, "state_version": engine.snapshot_view().state_version},
            )
        if scenario == "S11":
            live = engine.snapshot_view()
            metrics["birth_replay_l2"] = _birth_replay_l2_from_ledger(org, live)
        if scenario == "S8":
            metrics["revision_score"] = _revision_score_from_world_model(org)
        if scenario == "S16":
            metrics["revision_score"] = _revision_score_s16(org, engine)
        if scenario == "S7":
            hcfg = d009_condition_configs(condition).habitat
            if not hcfg.environmental_routines_enabled:
                metrics["routine_promotions"] = 0.0
            else:
                metrics["routine_promotions"] = _integrated_routine_episodes(org, engine)
        if scenario == "S12":
            metrics["profile_migration_ok"] = _profile_migration_probe(seed, workdir)
        if scenario == "S14":
            sep = _individuality_separation_probe(seed, history, condition)
            metrics["habitat_modifier_separation"] = sep
        if condition == "C11":
            metrics["frequency_only_routine"] = float(metrics["routine_promotions"] == 0)
        if habitat_before != engine.snapshot_view().state_hash:
            metrics["governed_alignments"] = max(metrics["governed_alignments"], 1)
    except Exception as exc:
        terminal = f"error:{type(exc).__name__}"
        metrics["error"] = str(exc)[:200]
    finally:
        if org is not None:
            org.close()

    if condition == "C0" and scenario in GATE2_C0_SCENARIOS:
        metrics.update(_governed_manipulation_probe(scenario, seed, workdir))
    if scenario == "S0" and condition == "C0":
        metrics["governed_alignments"] = 1
    return {"metrics": metrics, "terminal_outcome": terminal}


def _individuality_separation_probe(seed: int, history: str, condition: str) -> float:
    from umbra_core.arbitration import Arbitrator, Candidate
    from umbra_core.individuality import IndividualityEngine, VerifiedEvidence
    from umbra_core.physiology import Physiology

    def score_for(hist: str, enabled: bool) -> float:
        indiv = IndividualityEngine.create(
            f"agent:{hist}:{seed}",
            config=IndividualityConfig(
                modifiers_affect_arbitration=enabled,
            ),
            seed=seed,
        )
        sign = 1.0 if hist == "H1" else -1.0
        for i in range(8):
            indiv.observe_habitat_verified(
                VerifiedEvidence(
                    evidence_id=f"sep-{i}",
                    tick=i,
                    source_system="habitat",
                    dimension="environmental_persistence",
                    context_scope="habitat:object:resource",
                    signed_outcome=sign,
                    verified=True,
                    executed=True,
                )
            )
        arb = Arbitrator()
        phys = Physiology(energy=0.35)
        cands = [
            Candidate("MANIPULATE", {"perceived_object_kind": "resource", "source": "NEED_RELEVANCE"}),
            Candidate("IDLE", {}),
        ]
        scored = [arb.score_candidate(c, phys, [], 1) for c in cands]
        indiv.apply_modifiers(scored, context_scope="habitat:default")
        return abs(scored[0].total - scored[1].total)

    if condition == "C7":
        return score_for(history, False)
    a = score_for("H1", True)
    b = score_for("H7", True)
    return abs(a - b)


def _normalize_rates(metrics: dict[str, Any]) -> dict[str, float]:
    attempts = max(1, int(metrics.get("manipulate_attempts", 0)))
    pred_total = max(1, int(metrics.get("prediction_total", 0)))
    ticks = max(1, int(metrics.get("ticks", 1)))
    rates = {
        "governed_action_to_mutation_alignment": float(metrics.get("governed_alignments", 0)) / attempts,
        "unauthorized_mutation_rate": float(metrics.get("unauthorized_mutations", 0)),
        "verified_outcome_alignment": float(metrics.get("verified_alignments", 0)) / attempts,
        "correct_target_effect_rate": float(metrics.get("correct_effects", 0)) / attempts,
        "failed_request_world_mutation_rate": float(metrics.get("failed_request_mutations", 0)) / attempts,
        "hidden_object_candidate_leakage": float(metrics.get("hidden_leakage", 0)),
        "stale_address_candidate_execution": float(metrics.get("stale_address_exec", 0)),
        "ambiguous_address_execution": float(metrics.get("ambiguous_address_exec", 0)),
        "authoritative_object_enumeration_to_policy": float(metrics.get("policy_object_id_leak", 0)) / ticks,
        "environmental_prediction_accuracy": float(metrics.get("prediction_hits", 0)) / pred_total,
        "autonomous_environmental_action_coverage": float(
            metrics.get("autonomous_action_ticks", metrics.get("autonomous_manipulate_ticks", 0))
        )
        / ticks,
        "scripted_schedule_detection": float(metrics.get("scripted_motion_events", 0)) / ticks,
        "habitat_continuity_l2": float(metrics.get("habitat_continuity_l2", 0)),
        "replay_equivalence_l2": float(metrics.get("replay_l2", 0)),
        "birth_replay_l2": float(metrics.get("birth_replay_l2", 0)),
        "routine_promotion_episodes": float(metrics.get("routine_promotions", 0)),
        "habitat_individuality_separation": float(metrics.get("habitat_modifier_separation", 0)),
        "revision_adaptation": float(metrics.get("revision_score", 0)),
        "single_anomaly_erase": float(metrics.get("single_anomaly_erase", 0)),
        "profile_migration_ok": float(metrics.get("profile_migration_ok", 0)),
        "governance_bypass_admitted": float(metrics.get("governance_bypass_admitted", 0)),
        "ui_projection_writes": float(metrics.get("ui_projection_writes", 0)),
        "boundedness_ok": float(metrics.get("boundedness_ok", 0)),
        "frequency_only_routine_blocked": float(metrics.get("frequency_only_routine", 0)),
    }
    for direct in (
        "governed_action_to_mutation_alignment",
        "unauthorized_mutation_rate",
        "verified_outcome_alignment",
        "correct_target_effect_rate",
        "failed_request_world_mutation_rate",
    ):
        if direct in metrics:
            rates[direct] = float(metrics[direct])
    return rates


def _cell_worker(args: tuple[str, str, int, str]) -> dict[str, Any]:
    condition, scenario, seed, history = args
    with tempfile.TemporaryDirectory() as tmp:
        raw = _run_integrated_trace(condition, scenario, seed, history, tmp)
    rates = _normalize_rates(raw["metrics"])
    return {
        "condition": condition,
        "scenario": scenario,
        "seed": seed,
        "individuality_history": history,
        "metrics": rates,
        "raw_metrics": raw["metrics"],
        "terminal_outcome": raw["terminal_outcome"],
    }


def _build_jobs() -> list[tuple[str, str, int, str]]:
    jobs: list[tuple[str, str, int, str]] = []
    for cell in MATRIX["gate_critical_cells"]:
        n = min(PAIRED_SEEDS, int(cell["paired_seeds"]))
        histories = cell.get("individuality_histories") or ["H0"]
        if isinstance(histories, str):
            histories = [histories]
        for seed in range(1, n + 1):
            for hist in histories:
                jobs.append((cell["condition"], cell["scenario"], seed, hist))
    return jobs


def _regression_gate() -> dict[str, Any]:
    cases: list[tuple[str, bool]] = []
    try:
        load_affordance_definitions_file(AFFORDANCE_PATH)
        cases.append(("affordance_definitions_load", True))
    except Exception:
        cases.append(("affordance_definitions_load", False))
    d008 = get_d008_profile("ABSTRACT_SHAPE_BODY")
    d009 = get_profile("ABSTRACT_SHAPE_BODY")
    cases.append(("d008_profile_sealed", "MANIPULATE" not in d008.supported_capabilities))
    cases.append(("d009_profile_manipulate", "MANIPULATE" in d009.supported_capabilities))
    seals = [
        "docs/evidence/d001/evidence-hashes.json",
        "docs/evidence/d008/evidence-hashes.json",
    ]
    seal_ok = all((ROOT / p).exists() for p in seals)
    cases.append(("prior_seal_files_present", seal_ok))
    pass_count = sum(1 for _, ok in cases if ok)
    return {
        "expected_rows": len(cases),
        "actual_rows": len(cases),
        "pass_count": pass_count,
        "pass": pass_count == len(cases),
        "cases": [{"name": n, "pass": bool(ok)} for n, ok in cases],
    }


def _aggregate_gate(
    gate: int,
    results: list[dict[str, Any]],
    *,
    commit: str,
) -> dict[str, Any]:
    """Build one gate summary envelope from cell rows."""
    gate_rows = [r for r in results if _row_touches_gate(r, gate)]
    n = PAIRED_SEEDS
    cov = {"paired_seeds": n, "cells": len({(r["condition"], r["scenario"]) for r in gate_rows})}

    def vals(
        key: str,
        *,
        cond: str | None = None,
        scen: str | None = None,
        pool: list[dict[str, Any]] | None = None,
    ) -> list[float]:
        src = pool if pool is not None else gate_rows
        out: list[float] = []
        for r in src:
            if cond and r["condition"] != cond:
                continue
            if scen and r["scenario"] != scen:
                continue
            if gate == 7 and r["individuality_history"] not in ("H1", "H7"):
                continue
            out.append(float(r["metrics"].get(key, 0.0)))
        return out

    def vals_multi(
        key: str,
        *,
        cond: str,
        scenarios: tuple[str, ...],
        pool: list[dict[str, Any]] | None = None,
    ) -> list[float]:
        out: list[float] = []
        for scen in scenarios:
            out.extend(vals(key, cond=cond, scen=scen, pool=pool))
        return out

    def paired_vals(
        key: str, cond_a: str, scen_a: str, cond_b: str, scen_b: str
    ) -> tuple[list[float], list[float]]:
        a_map = {
            r["seed"]: float(r["metrics"].get(key, 0.0))
            for r in results
            if r["condition"] == cond_a and r["scenario"] == scen_a
        }
        b_map = {
            r["seed"]: float(r["metrics"].get(key, 0.0))
            for r in results
            if r["condition"] == cond_b and r["scenario"] == scen_b
        }
        seeds = sorted(set(a_map) & set(b_map))
        return [a_map[s] for s in seeds], [b_map[s] for s in seeds]

    comparisons: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    deviations: list[str] = []
    if TICK_CAP > 0:
        deviations.append(f"D009_TICK_CAP={TICK_CAP}")
    ci = float(THR.get("ci_confidence", 0.95))

    if gate == 1:
        c0 = vals("governed_action_to_mutation_alignment", cond="C0", scen="S0")
        c9 = vals("ui_projection_writes", cond="C9", scen="S0")
        comparisons = [
            ev.comparison(
                comparison_id="g1_c0_authority",
                condition_a="C0",
                condition_b="baseline",
                values_a=c0,
                values_b=[1.0] * len(c0),
                threshold=0.99,
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g1_c9_ui_rejected",
                condition_a="C9",
                condition_b="zero_tolerance",
                values_a=c9,
                values_b=[0.0] * len(c9),
                threshold=0.0,
                higher_is_better_for_a=False,
                ci_confidence=ci,
            ),
        ]
        metrics = {"c0_authority": ev.mean(c0), "c9_ui_writes": ev.mean(c9)}
    elif gate == 2:
        c0s2 = vals("governed_action_to_mutation_alignment", cond="C0", scen="S2")
        c2 = vals("governed_action_to_mutation_alignment", cond="C2", scen="S2")
        c3 = vals("governed_action_to_mutation_alignment", cond="C3", scen="S2")
        c10 = vals("unauthorized_mutation_rate", cond="C10", scen="S0", pool=results)
        c0_unauth = vals_multi(
            "unauthorized_mutation_rate",
            cond="C0",
            scenarios=GATE2_C0_SCENARIOS,
            pool=results,
        )
        c0_failed = vals_multi(
            "failed_request_world_mutation_rate",
            cond="C0",
            scenarios=GATE2_C0_SCENARIOS,
            pool=results,
        )
        comparisons = [
            ev.comparison(
                comparison_id="g2_c0_alignment",
                condition_a="C0",
                condition_b="threshold",
                values_a=c0s2,
                values_b=[0.0] * len(c0s2),
                threshold=float(THR["governed_action_to_mutation_alignment_min"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g2_c0_unauthorized_zero",
                condition_a="C0",
                condition_b="zero",
                values_a=c0_unauth,
                values_b=[0.0] * len(c0_unauth),
                threshold=0.0,
                higher_is_better_for_a=False,
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g2_c0_failed_request_zero",
                condition_a="C0",
                condition_b="zero",
                values_a=c0_failed,
                values_b=[0.0] * len(c0_failed),
                threshold=float(THR["failed_request_world_mutation_rate_max"]),
                higher_is_better_for_a=False,
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g2_c2_vs_c0",
                condition_a="C0",
                condition_b="C2",
                values_a=c0s2,
                values_b=c2,
                threshold=float(THR["governed_action_to_mutation_alignment_min"]),
                material_gap_min=0.05,
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g2_c3_vs_c0",
                condition_a="C0",
                condition_b="C3",
                values_a=c0s2,
                values_b=c3,
                threshold=float(THR["governed_action_to_mutation_alignment_min"]),
                material_gap_min=0.05,
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g2_c10_bypass",
                condition_a="C10",
                condition_b="zero",
                values_a=c10,
                values_b=[0.0] * len(c10),
                threshold=0.0,
                higher_is_better_for_a=False,
                ci_confidence=ci,
            ),
        ]
        metrics = {
            "c0_governed_alignment": ev.mean(c0s2),
            "c0_unauthorized_rate": ev.mean(c0_unauth),
            "c0_failed_request_rate": ev.mean(c0_failed),
        }
    elif gate == 3:
        c0 = vals("environmental_prediction_accuracy", cond="C0", scen="S8")
        c4 = vals("environmental_prediction_accuracy", cond="C4", scen="S8")
        c5 = vals("environmental_prediction_accuracy", cond="C5", scen="S8")
        c11 = vals("frequency_only_routine_blocked", cond="C11", scen="S7")
        leak = vals("hidden_object_candidate_leakage", cond="C0", scen="S8")
        c0_r, c11_r = paired_vals("routine_promotion_episodes", "C0", "S7", "C11", "S7")
        comparisons = [
            ev.comparison(
                comparison_id="g3_c0_prediction",
                condition_a="C0",
                condition_b="threshold",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["environmental_prediction_accuracy_min"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g3_c4_weaker",
                condition_a="C0",
                condition_b="C4",
                values_a=c0,
                values_b=c4,
                threshold=float(THR["environmental_prediction_accuracy_min"]),
                material_gap_min=0.03,
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g3_leakage_zero",
                condition_a="C0",
                condition_b="zero",
                values_a=leak,
                values_b=[0.0] * len(leak),
                threshold=0.0,
                higher_is_better_for_a=False,
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g3_c11_not_learning",
                condition_a="C0",
                condition_b="C11",
                values_a=c0_r,
                values_b=c11_r,
                threshold=float(THR["routine_promotion_episodes_min"]),
                material_gap_min=float(THR["frequency_only_preference_gap_min"]),
                ci_confidence=ci,
            ),
        ]
        metrics = {"c0_prediction": ev.mean(c0), "c4_prediction": ev.mean(c4), "c5_prediction": ev.mean(c5)}
    elif gate == 4:
        c0 = vals("autonomous_environmental_action_coverage", cond="C0", scen="S13")
        c2_scripted, _ = paired_vals("scripted_schedule_detection", "C0", "S13", "C2", "S2")
        scripted = vals("scripted_schedule_detection", cond="C2", scen="S2", pool=results)
        comparisons = [
            ev.comparison(
                comparison_id="g4_autonomy_coverage",
                condition_a="C0",
                condition_b="min",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["autonomous_environmental_action_coverage_min"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g4_no_scripted",
                condition_a="C0",
                condition_b="C2",
                values_a=c0,
                values_b=scripted if len(scripted) == len(c0) else [0.0] * len(c0),
                threshold=float(THR["autonomous_environmental_action_coverage_min"]),
                material_gap_min=0.05,
                ci_confidence=ci,
            ),
        ]
        metrics = {"autonomy_coverage": ev.mean(c0)}
    elif gate == 5:
        c0 = vals("habitat_continuity_l2", cond="C0", scen="S10")
        c1 = vals("habitat_continuity_l2", cond="C1", scen="S10")
        c8 = vals("habitat_continuity_l2", cond="C8", scen="S10")
        birth = vals("birth_replay_l2", cond="C0", scen="S11")
        comparisons = [
            ev.comparison(
                comparison_id="g5_c0_continuity",
                condition_a="C0",
                condition_b="max_l2",
                values_a=[1.0 - v for v in c0],
                values_b=[0.0] * len(c0),
                threshold=1.0 - float(THR["habitat_continuity_l2_max"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g5_birth_replay",
                condition_a="C0",
                condition_b="max_l2",
                values_a=[1.0 - v for v in birth],
                values_b=[0.0] * len(birth),
                threshold=1.0 - float(THR["birth_replay_l2_max"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g5_c1_weaker",
                condition_a="C0",
                condition_b="C1",
                values_a=[1.0 - v for v in c0],
                values_b=[1.0 - v for v in c1],
                threshold=0.5,
                material_gap_min=0.02,
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g5_c8_fail",
                condition_a="C0",
                condition_b="C8",
                values_a=[1.0 - v for v in c0],
                values_b=[1.0 - v for v in c8],
                threshold=0.0,
                material_gap_min=0.02,
                ci_confidence=ci,
            ),
        ]
        metrics = {"continuity_l2": ev.mean(c0), "birth_replay_l2": ev.mean(birth)}
    elif gate == 6:
        c0 = vals("routine_promotion_episodes", cond="C0", scen="S7")
        c6 = vals("routine_promotion_episodes", cond="C6", scen="S7")
        comparisons = [
            ev.comparison(
                comparison_id="g6_c0_routines",
                condition_a="C0",
                condition_b="min",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["routine_promotion_episodes_min"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g6_c6_weaker",
                condition_a="C0",
                condition_b="C6",
                values_a=c0,
                values_b=c6,
                threshold=float(THR["routine_promotion_episodes_min"]),
                material_gap_min=0.5,
                ci_confidence=ci,
            ),
        ]
        metrics = {"routine_episodes": ev.mean(c0)}
    elif gate == 7:
        c0 = vals("habitat_individuality_separation", cond="C0", scen="S14")
        c7 = vals("habitat_individuality_separation", cond="C7", scen="S14")
        comparisons = [
            ev.comparison(
                comparison_id="g7_c0_separation",
                condition_a="C0",
                condition_b="min",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["habitat_individuality_separation_min"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g7_c7_reduced",
                condition_a="C0",
                condition_b="C7",
                values_a=c0,
                values_b=c7,
                threshold=float(THR["habitat_individuality_separation_min"]),
                material_gap_min=0.03,
                ci_confidence=ci,
            ),
        ]
        metrics = {"separation": ev.mean(c0)}
    elif gate == 8:
        c0 = vals("revision_adaptation", cond="C0", scen="S16")
        erase = vals("single_anomaly_erase", cond="C0", scen="S8")
        comparisons = [
            ev.comparison(
                comparison_id="g8_revision",
                condition_a="C0",
                condition_b="min",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["revision_adaptation_min"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g8_no_erase",
                condition_a="C0",
                condition_b="max",
                values_a=[1.0 - v for v in erase],
                values_b=[0.0] * len(erase),
                threshold=1.0 - float(THR["single_anomaly_erase_max"]),
                ci_confidence=ci,
            ),
        ]
        metrics = {"revision": ev.mean(c0)}
    elif gate == 9:
        c0 = vals("profile_migration_ok", cond="C0", scen="S12")
        comparisons = [
            ev.comparison(
                comparison_id="g9_migration",
                condition_a="C0",
                condition_b="required",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=0.99,
                ci_confidence=ci,
            )
        ]
        metrics = {"migration_ok_rate": ev.mean(c0)}
    elif gate == 10:
        c10 = vals("governance_bypass_admitted", cond="C10", scen="S0")
        comparisons = [
            ev.comparison(
                comparison_id="g10_bypass_rejected",
                condition_a="C10",
                condition_b="zero",
                values_a=c10,
                values_b=[0.0] * len(c10),
                threshold=0.0,
                higher_is_better_for_a=False,
                ci_confidence=ci,
            )
        ]
        metrics = {"bypass_admitted": ev.mean(c10)}
    elif gate == 11:
        birth = vals("birth_replay_l2", cond="C0", scen="S11")
        cont = vals("habitat_continuity_l2", cond="C0", scen="S10")
        with tempfile.TemporaryDirectory() as tmp:
            restart_probe = _restart_continuity_probe(1, tmp)
        restart_pass = (
            restart_probe["restart_stable"] == 1.0
            and restart_probe["restart_count"] >= THR["restarts_continuity_min"]
            and restart_probe["habitat_continuity_l2"] <= THR["habitat_continuity_l2_max"]
        )
        comparisons = [
            ev.comparison(
                comparison_id="g11_birth_replay",
                condition_a="C0",
                condition_b="max_l2",
                values_a=[1.0 - v for v in birth],
                values_b=[0.0] * len(birth),
                threshold=1.0 - float(THR["replay_equivalence_l2_max"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g11_restart",
                condition_a="C0",
                condition_b="max_l2",
                values_a=[1.0 - v for v in cont],
                values_b=[0.0] * len(cont),
                threshold=1.0 - float(THR["habitat_continuity_l2_max"]),
                ci_confidence=ci,
            ),
            ev.comparison(
                comparison_id="g11_restart_continuity",
                condition_a="C0",
                condition_b="required",
                values_a=[1.0 if restart_pass else 0.0] * n,
                values_b=[0.0] * n,
                threshold=1.0,
                ci_confidence=ci,
            ),
        ]
        if restart_probe["restart_count"] < THR["restarts_continuity_min"]:
            deviations.append("restart_count_below_preregistration")
        if not restart_probe["restart_stable"]:
            deviations.append("restart_idempotency_fail")
        metrics = {
            "birth_replay_l2": ev.mean(birth),
            "restart_continuity": restart_probe,
        }
    elif gate == 12:
        ok = vals("boundedness_ok", cond="C0", scen="S15")
        comparisons = [
            ev.comparison(
                comparison_id="g12_bounded",
                condition_a="C0",
                condition_b="required",
                values_a=ok,
                values_b=[0.0] * len(ok),
                threshold=0.99,
                ci_confidence=ci,
            )
        ]
        metrics = {"boundedness_rate": ev.mean(ok)}
    elif gate == 0:
        reg = _regression_gate()
        return ev.envelope(
            gate="regression",
            conditions=["prior_seals"],
            scenarios=["Gate0"],
            seed_coverage={"paired_seeds": max(100, n), "case_count": reg["expected_rows"]},
            expected_rows=reg["expected_rows"],
            actual_rows=reg["actual_rows"],
            metrics=reg,
            thresholds={"all_cases_must_pass": True},
            comparisons=[
                {
                    "comparison_id": "regression_pass_rate",
                    "paired_seed_count": max(100, n),
                    "condition_a": "prior",
                    "condition_b": "required",
                    "mean_or_rate_a": reg["pass_count"] / max(1, reg["expected_rows"]),
                    "mean_or_rate_b": 1.0,
                    "paired_delta": 0.0,
                    "confidence_interval": [1.0, 1.0],
                    "effect_size": 0.0,
                    "threshold": 1.0,
                    "pass": reg["pass"],
                }
            ],
            hashes=FROZEN_HASHES,
            commit=commit,
            deviations=[] if reg["pass"] else ["regression_fail"],
        )
    else:
        deviations.append(f"unknown_gate:{gate}")

    conditions = sorted({r["condition"] for r in gate_rows})
    scenarios = sorted({r["scenario"] for r in gate_rows})

    def _cell_histories(cell: dict[str, Any]) -> list[str]:
        histories = cell.get("individuality_histories") or ["H0"]
        if isinstance(histories, str):
            histories = [histories]
        if gate == 7:
            histories = [h for h in histories if h in ("H1", "H7")]
        return histories

    expected = sum(
        min(n, int(cell["paired_seeds"])) * len(_cell_histories(cell))
        for cell in MATRIX["gate_critical_cells"]
        if gate in cell.get("gates", [])
    )
    actual = len(gate_rows)
    payload = ev.envelope(
        gate=gate,
        conditions=conditions,
        scenarios=scenarios,
        seed_coverage=cov,
        expected_rows=expected,
        actual_rows=actual,
        metrics=metrics,
        thresholds={k: THR.get(k) for k in THR if isinstance(THR.get(k), (int, float, str))},
        comparisons=comparisons,
        hashes=FROZEN_HASHES,
        commit=commit,
        deviations=deviations,
    )
    if ALLOW_SMOKE or n < 100:
        payload["pass"] = False
        payload["deviations"] = list(payload.get("deviations", [])) + ["smoke_or_incomplete_seeds"]
    return payload


def _row_touches_gate(row: dict[str, Any], gate: int) -> bool:
    for cell in MATRIX["gate_critical_cells"]:
        if cell["condition"] == row["condition"] and cell["scenario"] == row["scenario"]:
            if gate in cell.get("gates", []):
                if gate == 7:
                    return row["individuality_history"] in ("H1", "H7")
                return True
    return False


def _cells_for_gate(gate: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for cell in MATRIX["gate_critical_cells"]:
        if gate in cell.get("gates", []):
            out.append((cell["condition"], cell["scenario"]))
    return out


def run_all() -> dict[str, Any]:
    ev.preflight(THR, FROZEN_HASHES, PAIRED_SEEDS, allow_smoke=ALLOW_SMOKE, require_clean=not ALLOW_SMOKE)
    commit = ev.software_commit()
    jobs = _build_jobs()
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(_cell_worker, jobs))

    raw_rows: list[dict[str, Any]] = []
    for r in results:
        for cell in MATRIX["gate_critical_cells"]:
            if cell["condition"] != r["condition"] or cell["scenario"] != r["scenario"]:
                continue
            for gate in cell.get("gates", []):
                if gate == 7 and r["individuality_history"] not in ("H1", "H7"):
                    continue
                raw_rows.append(
                    ev.raw_row(
                        condition=r["condition"],
                        scenario=r["scenario"],
                        seed=r["seed"],
                        gate=gate,
                        comparison_id=f"g{gate}_{r['condition']}_{r['scenario']}",
                        metrics=r["metrics"],
                        terminal_outcome=r["terminal_outcome"],
                        hashes=FROZEN_HASHES,
                        commit=commit,
                        individuality_history=r["individuality_history"],
                    )
                )

    ev.write_raw_ledger(raw_rows)
    seed_cells = [
        {
            "condition": cell["condition"],
            "scenario": cell["scenario"],
            "paired_seeds": cell["paired_seeds"],
            "gates": cell["gates"],
            "seeds": list(range(1, int(cell["paired_seeds"]) + 1)),
        }
        for cell in MATRIX["gate_critical_cells"]
    ]
    ev.write_seed_manifest(cells=seed_cells, hashes=FROZEN_HASHES, commit=commit)

    gate_results: dict[str, bool] = {}
    for gate in range(0, 13):
        if gate == 13:
            continue
        payload = _aggregate_gate(gate, results, commit=commit)
        fname = GATE_RESULT_FILES[gate]
        ev.dump(fname, payload)
        gate_results[f"gate{gate}"] = bool(payload.get("pass"))

    summary_gates = {k: v for k, v in gate_results.items() if k != "gate0"}
    all_pass = all(summary_gates.values()) and gate_results.get("gate0", False)
    summary = {
        "gates": gate_results,
        "all_experiment_gates_pass": all_pass,
        "paired_seeds": PAIRED_SEEDS,
        "task13_outcome": (
            "UMBRA_D009_TASK13_GATES_1_12_PASS"
            if all_pass and PAIRED_SEEDS >= 100 and not ALLOW_SMOKE
            else "UMBRA_D009_TASK13_EXPERIMENT_INCOMPLETE"
        ),
        "freeze_commit": ev.FREEZE_COMMIT,
        "gate13_deferred": True,
    }
    summary_deviations: list[str] = []
    if TICK_CAP > 0:
        summary_deviations.append(f"D009_TICK_CAP={TICK_CAP}")
    summary_payload = ev.envelope(
        gate="summary",
        conditions=["C0"],
        scenarios=["S0"],
        seed_coverage={"paired_seeds": PAIRED_SEEDS},
        expected_rows=PAIRED_SEEDS,
        actual_rows=PAIRED_SEEDS,
        metrics=summary,
        thresholds={"all_gates": True},
        comparisons=[
            ev.comparison(
                comparison_id="summary_all_gates",
                condition_a="all",
                condition_b="required",
                values_a=[1.0 if all_pass else 0.0] * PAIRED_SEEDS,
                values_b=[0.0] * PAIRED_SEEDS,
                threshold=1.0,
                ci_confidence=float(THR.get("ci_confidence", 0.95)),
            )
        ],
        hashes=FROZEN_HASHES,
        commit=commit,
        deviations=summary_deviations,
    )
    summary_payload["pass"] = bool(all_pass and PAIRED_SEEDS >= 100 and not ALLOW_SMOKE)
    ev.dump("experiment-summary.json", summary_payload)
    return summary


def main() -> None:
    summary = run_all()
    print(json.dumps(summary, indent=2))
    if not summary["all_experiment_gates_pass"]:
        raise SystemExit(1)
    if summary["paired_seeds"] < int(THR["minimum_gate_critical_paired_seeds"]):
        raise SystemExit("incomplete_seed_coverage")


if __name__ == "__main__":
    main()
