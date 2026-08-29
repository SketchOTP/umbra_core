#!/usr/bin/env python3
"""CLOSE-02U-ATTRIB diagnostic collector.

This file is experiment-only.  It wraps existing production calls without
changing their inputs, outputs, RNG, persistence, or decision semantics.
"""
from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import json
import os
import shutil
import sys
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d014.run_formal import config
from umbra_core.arbitration import Arbitrator
from umbra_core.decision_trace import canonical_fingerprint, candidate_to_trace
from umbra_core.governance import authority_effect_branches as _authority_effect_branches
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism
from umbra_core.runtime import authority_effect_branches as _runtime_authority_effect_branches


SEED = 57531938
REGIME = "R1"
SCENARIO = "S16"
HORIZON = 1600
EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-close-02u-attrib-r1"
)


def safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else str(value)
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    if isinstance(value, set):
        return sorted((safe(v) for v in value), key=repr)
    if hasattr(value, "to_state"):
        try:
            return safe(value.to_state())
        except Exception:
            return "<unserializable>"
    if hasattr(value, "to_dict"):
        try:
            return safe(value.to_dict())
        except Exception:
            return "<unserializable>"
    return str(value)


def fp(value: Any) -> str:
    return canonical_fingerprint(safe(value))


def candidate(value: Any) -> dict[str, Any] | None:
    return candidate_to_trace(value)


def make_organism(db: Path, trace_path: Path | None = None):
    cfg = config(SEED, db, REGIME)
    cfg.decision_trace_path = str(trace_path) if trace_path else None
    organism = create_organism(cfg)
    for method in (
        "_ensure_development_intervention",
        "_ensure_memory_history",
        "_ensure_social_history",
        "_ensure_individuality_history",
    ):
        getattr(organism, method)()
    engine = HabitatEngine(_habitat_state_for_scenario(SCENARIO))
    organism.embodiment.attach_habitat_engine(engine)
    organism.embodiment.body.x, organism.embodiment.body.y = 4.0, 3.0
    organism.perception.perceive_habitat_objects(organism.embodiment, 1.0, organism.rng)
    return organism


class Capture:
    def __init__(self) -> None:
        self.rows: dict[int, dict[str, Any]] = {}
        self.current_tick: int | None = None
        self.calls: Counter[str] = Counter()

    def row(self, tick: int | None = None) -> dict[str, Any]:
        key = self.current_tick if tick is None else tick
        if key is None:
            key = -1
        return self.rows.setdefault(key, {"tick": key})

    def start_tick(self, organism: Any) -> None:
        tick = organism.tick + 1
        self.current_tick = tick
        row = self.row(tick)
        row["pre_action_physiology"] = safe(organism.phys.as_dict())
        row["rng_before_fp"] = fp(organism.rng.export_state())
        row["authoritative_state_before_fp"] = fp(organism.authoritative_state())
        row["arbitration_before"] = safe(organism.arbitrator.state.to_state())
        row["active_age_before"] = getattr(organism, "_tick_organism_age", None)

    def finish_tick(self, organism: Any, result: dict[str, Any]) -> None:
        tick = organism.tick
        row = self.row(tick)
        row["post_action_physiology"] = safe(organism.phys.as_dict())
        row["rng_after_fp"] = fp(organism.rng.export_state())
        row["authoritative_state_after_fp"] = fp(organism.authoritative_state())
        row["arbitration_after"] = safe(organism.arbitrator.state.to_state())
        row["result"] = safe(result)
        row["no_safe_action"] = bool(result.get("no_safe_action"))
        row["selected_action"] = result.get("capability")
        row["world_model_after_fp"] = (
            fp(organism.world_model.to_state()) if organism.world_model is not None else None
        )
        row["rest_landmarks"] = [
            {
                key: safe(observation.get(key))
                for key in (
                    "kind",
                    "fact_kind",
                    "source",
                    "estimated_distance",
                    "relative_direction",
                    "uncertainty",
                    "confidence",
                    "persistence_probability",
                    "verified_recovery_count",
                    "last_verified_recovery_tick",
                    "distance_support_center",
                    "distance_support_radius",
                    "distance_support_upper_bound",
                    "support_provenance",
                    "body_schema_id",
                    "observation_version",
                    "progress_status",
                    "executability_support",
                )
                if key in observation
            }
            for observation in row.get("observations", [])
            if observation.get("kind") == "rest"
        ]

    def drift(self, phys: Any, original: Any, dt: float) -> Any:
        row = self.row()
        row["physiology_before_drift"] = safe(phys.as_dict())
        value = original(phys, dt)
        row["drift"] = safe(value)
        row["physiology_after_drift"] = safe(phys.as_dict())
        return value


def install_capture(capture: Capture):
    import umbra_core.arbitration as arbitration_module
    import umbra_core.physiology as physiology_module

    originals: list[tuple[Any, str, Any]] = []

    def wrap(owner: Any, name: str, factory: Any) -> None:
        original = getattr(owner, name)
        originals.append((owner, name, original))
        setattr(owner, name, factory(original))

    def tick_factory(original):
        @functools.wraps(original)
        def wrapped(self, *args, **kwargs):
            capture.start_tick(self)
            try:
                result = original(self, *args, **kwargs)
                capture.finish_tick(self, result)
                return result
            except BaseException:
                capture.row()["exception"] = True
                raise
        return wrapped

    def drift_factory(original):
        @functools.wraps(original)
        def wrapped(self, dt):
            return capture.drift(self, original, dt)
        return wrapped

    def select_factory(original):
        @functools.wraps(original)
        def wrapped(self, phys, observations, tick, rng, *args, **kwargs):
            capture.current_tick = tick
            row = capture.row(tick)
            row["active_recovery_needs"] = safe(phys.active_recovery_needs())
            row["critical_variables"] = safe(phys.critical_vars())
            row["vector_urgency"] = safe(phys.vector_urgency())
            row["needs_recovery"] = safe(phys.needs_recovery())
            row["recovery_focus_before"] = getattr(self.state, "recovery_focus", None)
            row["observations"] = safe(observations)
            row["policy_observation_fp"] = fp(observations)
            row["intent_candidates"] = safe(
                [candidate(c) for c in (kwargs.get("intent_candidates") or [])]
            )
            row["select_parameters"] = {
                "effective_age_ticks": kwargs.get("effective_age_ticks"),
                "effective_active_ticks": kwargs.get("effective_active_ticks"),
                "wait_generation_enabled": kwargs.get("wait_generation_enabled"),
                "temporal_modifiers_enabled": kwargs.get("temporal_modifiers_enabled"),
                "discovery_needed": kwargs.get("discovery_needed"),
            }
            result = original(self, phys, observations, tick, rng, *args, **kwargs)
            row["selected_candidate"] = candidate(result)
            row["recovery_focus_after"] = getattr(self.state, "recovery_focus", None)
            row["last_verified_denial_after"] = safe(self.state.last_verified_denial)
            capture.calls["select"] += 1
            return result
        return wrapped

    def generate_factory(original):
        @functools.wraps(original)
        def wrapped(self, phys, observations, tick, *args, **kwargs):
            result = original(self, phys, observations, tick, *args, **kwargs)
            capture.row(tick)["generated_candidates"] = [
                candidate(c) for c in result
            ]
            return result
        return wrapped

    def score_factory(original):
        @functools.wraps(original)
        def wrapped(self, cand, phys, observations, tick, *args, **kwargs):
            result = original(self, cand, phys, observations, tick, *args, **kwargs)
            capture.row(tick).setdefault("scored_candidates", []).append(candidate(result))
            return result
        return wrapped

    def safety_factory(original):
        @functools.wraps(original)
        def wrapped(self, cand, phys, *args, **kwargs):
            result = original(self, cand, phys, *args, **kwargs)
            capture.row().setdefault("immediate_safety_checks", []).append({
                "candidate": candidate(cand),
                "safe": not bool(result),
                "ignore": kwargs.get("ignore"),
                "effect_branches": safe(kwargs.get("effect_branches")),
            })
            return result
        return wrapped

    def admissibility_factory(original):
        @functools.wraps(original)
        def wrapped(candidate_value, *, physiology, observations, arbitration_state, effect_branches=None):
            result = original(
                candidate_value,
                physiology=physiology,
                observations=observations,
                arbitration_state=arbitration_state,
                effect_branches=effect_branches,
            )
            capture.row().setdefault("contract_checks", []).append({
                "candidate": candidate(candidate_value),
                "admissible": bool(result),
                "effect_branches": safe(effect_branches),
            })
            return result
        return wrapped

    def effect_factory(original):
        @functools.wraps(original)
        def wrapped(candidate_value, *args, **kwargs):
            result = original(candidate_value, *args, **kwargs)
            capture.row().setdefault("authority_effect_branches", []).append({
                "candidate": candidate(candidate_value),
                "branches": safe(result),
            })
            return result
        return wrapped

    wrap(OrganismProxy, "tick_once", tick_factory)  # replaced below by bind helper
    return originals


class OrganismProxy:
    """Marker used only to keep install_capture definitions readable."""


def run_trace(work: Path, output: Path, built_in_trace: Path | None) -> dict[str, Any]:
    import umbra_core.arbitration as arbitration_module
    import umbra_core.physiology as physiology_module
    import umbra_core.runtime as runtime_module
    from umbra_core.runtime import Organism
    from umbra_core.recoverability import contracts as contracts_module

    capture = Capture()
    originals: list[tuple[Any, str, Any]] = []

    def wrap(owner: Any, name: str, factory: Any) -> None:
        original = getattr(owner, name)
        originals.append((owner, name, original))
        setattr(owner, name, factory(original))

    def tick_factory(original):
        @functools.wraps(original)
        def wrapped(self, *args, **kwargs):
            capture.start_tick(self)
            try:
                result = original(self, *args, **kwargs)
                capture.finish_tick(self, result)
                return result
            except BaseException:
                capture.row()["exception"] = True
                raise
        return wrapped

    def drift_factory(original):
        @functools.wraps(original)
        def wrapped(self, dt):
            return capture.drift(self, original, dt)
        return wrapped

    def select_factory(original):
        @functools.wraps(original)
        def wrapped(self, phys, observations, tick, rng, *args, **kwargs):
            capture.current_tick = tick
            row = capture.row(tick)
            row.update({
                "active_recovery_needs": safe(phys.active_recovery_needs()),
                "critical_variables": safe(phys.critical_vars()),
                "vector_urgency": safe(phys.vector_urgency()),
                "needs_recovery": safe(phys.needs_recovery()),
                "recovery_focus_before": getattr(self.state, "recovery_focus", None),
                "observations": safe(observations),
                "policy_observation_fp": fp(observations),
                "intent_candidates": [candidate(c) for c in (kwargs.get("intent_candidates") or [])],
                "select_parameters": {
                    "effective_age_ticks": kwargs.get("effective_age_ticks"),
                    "effective_active_ticks": kwargs.get("effective_active_ticks"),
                    "wait_generation_enabled": kwargs.get("wait_generation_enabled"),
                    "temporal_modifiers_enabled": kwargs.get("temporal_modifiers_enabled"),
                    "discovery_needed": kwargs.get("discovery_needed"),
                },
            })
            result = original(self, phys, observations, tick, rng, *args, **kwargs)
            row["selected_candidate"] = candidate(result)
            row["recovery_focus_after"] = getattr(self.state, "recovery_focus", None)
            row["last_verified_denial_after"] = safe(self.state.last_verified_denial)
            capture.calls["select"] += 1
            return result
        return wrapped

    def generate_factory(original):
        @functools.wraps(original)
        def wrapped(self, phys, observations, tick, *args, **kwargs):
            result = original(self, phys, observations, tick, *args, **kwargs)
            capture.row(tick)["generated_candidates"] = [candidate(c) for c in result]
            return result
        return wrapped

    def score_factory(original):
        @functools.wraps(original)
        def wrapped(self, cand, phys, observations, tick, *args, **kwargs):
            result = original(self, cand, phys, observations, tick, *args, **kwargs)
            capture.row(tick).setdefault("scored_candidates", []).append(candidate(result))
            return result
        return wrapped

    def safety_factory(original):
        @functools.wraps(original)
        def wrapped(self, cand, phys, *args, **kwargs):
            result = original(self, cand, phys, *args, **kwargs)
            capture.row().setdefault("immediate_safety_checks", []).append({
                "candidate": candidate(cand),
                "safe": not bool(result),
                "ignore": kwargs.get("ignore"),
                "effect_branches": safe(kwargs.get("effect_branches")),
            })
            return result
        return wrapped

    def admissibility_factory(original):
        @functools.wraps(original)
        def wrapped(candidate_value, *, physiology, observations, arbitration_state, effect_branches=None):
            result = original(
                candidate_value,
                physiology=physiology,
                observations=observations,
                arbitration_state=arbitration_state,
                effect_branches=effect_branches,
            )
            capture.row().setdefault("contract_checks", []).append({
                "candidate": candidate(candidate_value),
                "admissible": bool(result),
                "effect_branches": safe(effect_branches),
            })
            return result
        return wrapped

    def effect_factory(original):
        @functools.wraps(original)
        def wrapped(candidate_value, *args, **kwargs):
            result = original(candidate_value, *args, **kwargs)
            capture.row().setdefault("authority_effect_branches", []).append({
                "candidate": candidate(candidate_value),
                "branches": safe(result),
            })
            return result
        return wrapped

    def run_once() -> dict[str, Any]:
        db = work / "R1-57531938.sqlite"
        organism = make_organism(db, built_in_trace)
        started = time.monotonic()
        terminal = "completed"
        failure = None
        try:
            for _ in range(HORIZON):
                result = organism.tick_once()
                if result.get("no_safe_action") or organism.phys.critical_any():
                    terminal = "scientific_failure"
                    failure = {
                        "tick": organism.tick,
                        "no_safe_action": bool(result.get("no_safe_action")),
                        "physiology": organism.phys.as_dict(),
                        "result": result,
                    }
                    break
            return {
                "directive": "UMBRA-CLOSE-02U-ATTRIB",
                "baseline": "68746231742a904112eed89d759a22f7f384e23b",
                "regime": REGIME,
                "scenario": SCENARIO,
                "seed": SEED,
                "target_ticks": HORIZON,
                "ticks": organism.tick,
                "terminal": terminal,
                "failure": safe(failure),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "trace_rows": len(capture.rows),
                "select_calls": capture.calls["select"],
            }
        finally:
            organism.close()
            for suffix in ("", "-wal", "-shm"):
                (db.parent / (db.name + suffix)).unlink(missing_ok=True)

    wrap(Organism, "tick_once", tick_factory)
    wrap(physiology_module.Physiology, "tick_drift", drift_factory)
    wrap(Arbitrator, "select", select_factory)
    wrap(Arbitrator, "generate_candidates", generate_factory)
    wrap(Arbitrator, "score_candidate", score_factory)
    wrap(Arbitrator, "_introduces_critical_boundary", safety_factory)
    wrap(contracts_module, "candidate_is_admissible", admissibility_factory)
    wrap(runtime_module, "authority_effect_branches", effect_factory)

    try:
        summary = run_once()
    finally:
        for owner, name, original in reversed(originals):
            setattr(owner, name, original)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for tick in sorted(capture.rows):
            if tick < 1:
                continue
            handle.write(json.dumps(safe(capture.rows[tick]), sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--built-in-trace", type=Path, required=True)
    args = parser.parse_args()
    summary = run_trace(args.work, args.trace, args.built_in_trace)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
