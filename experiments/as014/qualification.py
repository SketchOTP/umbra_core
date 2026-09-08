"""AS-014 full-stack R0--R3 qualification with bounded persistence enabled.

This owns the current-stack configuration instead of monkey-patching a
historical runner.  The regimes retain their previously frozen intervention
meaning; AS-014 adds only checkpoint-plus-tail persistence maintenance.
"""

from __future__ import annotations

import copy
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from experiments.as009.qualification import PARTNER_OBJECT_ID, partner_object
from experiments.as014.full_config import BASELINE, DIRECTIVE, config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d014.run_formal import adapter_burst
from umbra_core.embodiment_adapters.profiles import MINIMAL_CREATURE_BODY
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism


HORIZON = 7200
REGIMES = ("R0", "R1", "R2", "R3")
SCENARIOS = {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}


def _ensure_histories(organism: Any) -> None:
    for method in (
        "_ensure_development_intervention",
        "_ensure_memory_history",
        "_ensure_social_history",
        "_ensure_individuality_history",
    ):
        getattr(organism, method)()


def _prepare(seed: int, db: Path, regime: str) -> tuple[Any, HabitatEngine]:
    organism = create_organism(config(seed, db, regime))
    _ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario(SCENARIOS[regime]))
    organism.embodiment.attach_habitat_engine(engine)
    organism.embodiment.body.x, organism.embodiment.body.y = 4.0, 3.0
    organism.perception.perceive_habitat_objects(organism.embodiment, 1.0, organism.rng)
    return organism, engine


def _reload(seed: int, db: Path, regime: str, state: Any) -> tuple[Any, HabitatEngine]:
    organism = load_organism(config(seed, db, regime))
    engine = HabitatEngine(copy.deepcopy(state))
    organism.embodiment.attach_habitat_engine(engine)
    binding = organism.embodiment.habitat_authority_binding
    view = engine.snapshot_view()
    if binding is None or binding["habitat_id"] != view.habitat_id or binding["state_hash"] != view.state_hash:
        raise RuntimeError("AS014_R2_HABITAT_REATTACHMENT_INVALID")
    return organism, engine


def _close(organism: Any) -> None:
    organism.close()


def run_case(regime: str, seed: int, work: Path, horizon: int = HORIZON) -> dict[str, Any]:
    if regime not in REGIMES:
        raise ValueError(regime)
    db = work / f"{regime}-{seed}.sqlite"
    organism, engine = _prepare(seed, db, regime)
    identity = organism.identity.agent_id
    state: dict[str, Any] = {
        "organism": organism,
        "engine": engine,
        "restart_count": 0,
        "restart_identity_preserved": False,
        "partner_created": False,
        "partner_present_after_restart": False,
        "partner_occluded": False,
        "partner_reappeared": False,
        "adapter_accepts": 0,
        "body_change_count": 0,
        "body_identity_preserved": False,
        "visible_cue_ticks": 0,
        "occluded_cue_ticks": 0,
        "reappeared_cue_ticks": 0,
    }
    actions: Counter[str] = Counter()
    extrema = {"min_energy": 1.0, "max_fatigue": 0.0, "min_integrity": 1.0, "min_stimulation": 1.0}
    first_no_safe: int | None = None
    failure: dict[str, Any] | None = None
    started = time.monotonic()
    try:
        for _ in range(horizon):
            organism = state["organism"]
            tick = organism.tick + 1
            if regime == "R2" and tick == 600:
                event = state["engine"].commit_object_creation(
                    partner_object(),
                    event_id=f"as014:create:{seed}",
                    transaction_id=f"as014:create-txn:{seed}",
                    request_id=f"as014:create-req:{seed}",
                )
                state["partner_created"] = event.get("event_type") == "habitat_object_created"
            if regime == "R2" and tick == 1200:
                state["adapter_accepts"] += int(adapter_burst(organism, seed, tick))
            if regime == "R2" and tick == 1800:
                saved_habitat = copy.deepcopy(state["engine"].state)
                organism.snapshot_if_due(force=True)
                _close(organism)
                organism, engine = _reload(seed, db, regime, saved_habitat)
                state.update(
                    organism=organism,
                    engine=engine,
                    restart_count=state["restart_count"] + 1,
                    restart_identity_preserved=organism.identity.agent_id == identity,
                    partner_present_after_restart=len(engine.authoritative_social_entities()) == 1,
                )
            if regime == "R2" and tick == 2400:
                state["engine"].commit_object_visibility(
                    PARTNER_OBJECT_ID,
                    occluded=True,
                    event_id=f"as014:hide:{seed}",
                    transaction_id=f"as014:hide-txn:{seed}",
                    request_id=f"as014:hide-req:{seed}",
                )
                state["partner_occluded"] = True
            if regime == "R2" and tick == 2600:
                state["engine"].commit_object_visibility(
                    PARTNER_OBJECT_ID,
                    occluded=False,
                    event_id=f"as014:show:{seed}",
                    transaction_id=f"as014:show-txn:{seed}",
                    request_id=f"as014:show-req:{seed}",
                )
                state["partner_reappeared"] = True
            if regime == "R3" and tick == 3600:
                organism.embodiment_adapter.swap_profile(
                    MINIMAL_CREATURE_BODY.profile_id,
                    origin="D014_R3_PREREGISTERED",
                )
                state.update(
                    body_change_count=1,
                    body_profile_after=organism.embodiment_adapter.profile.profile_id,
                    body_identity_preserved=organism.identity.agent_id == identity,
                )
            result = organism.tick_once()
            state["engine"] = organism.embodiment._habitat_engine
            actions[str(result.get("capability"))] += 1
            extrema["min_energy"] = min(extrema["min_energy"], float(organism.phys.energy))
            extrema["max_fatigue"] = max(extrema["max_fatigue"], float(organism.phys.fatigue))
            extrema["min_integrity"] = min(extrema["min_integrity"], float(organism.phys.integrity))
            extrema["min_stimulation"] = min(extrema["min_stimulation"], float(organism.phys.stimulation))
            if result.get("no_safe_action") and first_no_safe is None:
                first_no_safe = organism.tick
            if regime == "R2" and state["partner_created"]:
                cue_count = len(getattr(organism.perception, "partner_cues", ()))
                if 600 <= organism.tick < 2400:
                    state["visible_cue_ticks"] += int(cue_count > 0)
                elif 2400 <= organism.tick < 2600:
                    state["occluded_cue_ticks"] += int(cue_count > 0)
                elif 2600 <= organism.tick < 2800:
                    state["reappeared_cue_ticks"] += int(cue_count > 0)
            if organism.phys.critical_any():
                failure = {"tick": organism.tick, "physiology": organism.phys.as_dict(), "result": result}
                break
        completed = failure is None and state["organism"].tick >= horizon
        checkpoint = state["organism"].store.latest_checkpoint()
        state["organism"].store.validate_chain()
        return {
            "schema": "AS014_FORMAL_CASE_V1",
            "directive": DIRECTIVE,
            "baseline": BASELINE,
            "regime": regime,
            "scenario": SCENARIOS[regime],
            "seed": seed,
            "ticks": state["organism"].tick,
            "target_ticks": horizon,
            "terminal": "completed" if completed else "scientific_failure",
            "critical_failure": failure,
            "first_no_safe_action": first_no_safe,
            "actions": dict(actions),
            "configuration": fingerprint(state["organism"].config),
            "checkpoint_epoch": checkpoint["checkpoint_epoch"] if checkpoint else 0,
            "hot_tail_event_count": len(state["organism"].store.iter_events()),
            **extrema,
            **{key: value for key, value in state.items() if key not in {"organism", "engine"}},
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    finally:
        _close(state["organism"])


def execute(
    manifest: dict[str, Any],
    work: Path,
    *,
    on_case: Callable[[dict[str, Any]], None] | None = None,
    horizon: int = HORIZON,
) -> dict[str, Any]:
    regimes = manifest.get("regimes")
    if (
        manifest.get("directive") != DIRECTIVE
        or tuple(regimes or ()) != REGIMES
        or any(len(regimes[regime]) != 8 for regime in REGIMES)
        or horizon < 1
    ):
        raise RuntimeError("AS014_FORMAL_MANIFEST_INVALID")
    work.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    for regime in REGIMES:
        for index, seed in enumerate(regimes[regime]):
            row = run_case(regime, int(seed), work, horizon)
            row["seed_index"] = index
            rows.append(row)
            if on_case is not None:
                on_case(row)
            if row["terminal"] != "completed":
                return {
                    "schema": "AS014_FORMAL_POPULATION_V1",
                    "directive": DIRECTIVE,
                    "baseline": BASELINE,
                    "expected_runs": 32,
                    "completed_runs": len(rows),
                    "terminal": f"AS014_FRESH_{regime}_FAIL",
                    "rows": rows,
                }
    return {
        "schema": "AS014_FORMAL_POPULATION_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "expected_runs": 32,
        "completed_runs": 32,
        "all_completed": True,
        "rows": rows,
    }


__all__ = ["HORIZON", "REGIMES", "SCENARIOS", "execute", "run_case"]
