"""D-014H3E regime-faithful runtime adapter and bounded proof harness."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any, Callable

from d014h3d_selector import evaluate
from umbra_core.arbitration import Candidate
from umbra_core.embodiment_adapters.profiles import MINIMAL_CREATURE_BODY
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.physiology import BOUNDS, DEFAULT_DRIFT
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.temporal.config import TemporalConfig

ROOT = Path(__file__).resolve().parents[3]
HORIZON = 7200
R0_SEEDS = [41241905, 79871850, 27526357, 49452783, 5366620, 3609315, 77955964, 18929722]
KNOWN_R1 = 57531938
DIMENSIONS = ("energy", "fatigue", "integrity", "stimulation")


def _physiology_input(values: dict[str, float]) -> dict[str, dict[str, float]]:
    return {
        name: {
            "value": float(values[name]),
            "lower": 0.0,
            "upper": 1.0,
            "critical_low": BOUNDS[name].critical_low,
            "critical_high": BOUNDS[name].critical_high,
        }
        for name in DIMENSIONS
    }


def _opportunities(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(observations[:16]):
        kind = item.get("kind")
        if kind not in {"resource", "novel_crystal", "rest", "partner"}:
            continue
        result.append({
            "opportunity_ref": f"{kind}:{index}",
            "policy_visible": True,
            "kind": kind,
            "source": item.get("source"),
        })
    return result


def _route_for(row: dict[str, Any], observations: list[dict[str, Any]],
               effect_branches: dict[str, list[dict[str, Any]]]) -> dict[str, Any] | None:
    params = row.get("params") or {}
    toward = params.get("toward")
    if toward is None:
        return None
    for index, obs in enumerate(observations[:16]):
        if obs.get("kind") != toward:
            continue
        distance = obs.get("estimated_distance")
        if not isinstance(distance, (int, float)):
            return None
        terminal = "CHARGE" if toward in {"resource", "novel_crystal"} else "REST"
        return {
            "policy_visible": True,
            "opportunity_ref": f"{toward}:{index}",
            "estimated_distance": float(distance),
            "distance_support_upper_bound": float(obs.get("distance_support_upper_bound", distance)),
            "progress_per_step": max(0.25, float(params.get("step", 1.0))),
            "terminal_capability": terminal,
            "terminal_effect_branches": effect_branches.get(terminal, []),
        }
    return None


def _actual_proposal_rows(context: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    transitions = context.get("candidate_transitions", [])
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        source = str(transition.get("source", "UNKNOWN"))
        reason = transition.get("reason")
        changed = bool(transition.get("changed"))
        emitted = transition.get("candidate_emitted")
        if not isinstance(emitted, dict) or not emitted.get("capability"):
            continue
        if source == "base_arbitration":
            proposal_class = "ACTUAL_PROPOSAL"
        elif source in {"development", "memory", "social", "world_model"} and changed:
            proposal_class = "ACTUAL_PROPOSAL"
        elif source in {"manipulation", "routine", "temporal", "individuality", "critical_recovery"}:
            proposal_class = "MODIFIER_CONTEXT"
        elif source in {"dormant_capability", "final_safety"}:
            proposal_class = "CONSTRAINT"
        else:
            proposal_class = "NO_PROPOSAL"
        if proposal_class != "ACTUAL_PROPOSAL":
            continue
        row = dict(emitted)
        row["source_name"] = source
        row["proposal_class"] = proposal_class
        row["proposal_reason"] = reason
        row["candidate_before"] = transition.get("candidate_before")
        row["evidence"] = transition.get("evidence")
        rows.append(row)
    if not rows:
        current = context.get("current_candidate")
        if isinstance(current, dict) and current.get("capability"):
            rows.append({
                **current,
                "source_name": "base_arbitration",
                "proposal_class": "ACTUAL_PROPOSAL",
                "proposal_reason": "current_final_candidate",
            })
    return rows


def _source_evidence(context: dict[str, Any]) -> dict[str, Any]:
    policy_view = context.get("policy_view")
    if not isinstance(policy_view, dict):
        return {}
    # These are policy-visible observations, not hidden environment truth.
    return {
        "policy_observations": list(policy_view.get("observations", [])),
        "partner_cues": list(policy_view.get("partner_cues", [])),
        "manipulation_bindings": list(policy_view.get("manipulation_bindings", [])),
        "adapter_observations": list(policy_view.get("adapter_observations", [])),
        "perception_state_version": policy_view.get("perception_state_version"),
    }


def selector_input(context: dict[str, Any]) -> dict[str, Any]:
    pool = _actual_proposal_rows(context)
    effect_branches = context["effect_branches"]
    observations = [dict(row) for row in context.get("observations", [])]
    body_generation = context.get("body_schema_generation") or "unknown"
    body_state = dict(context.get("body") or {})
    candidates = []
    for index, row in enumerate(pool):
        capability = str(row["capability"])
        params = dict(row.get("params") or {})
        route = _route_for(row, observations, effect_branches)
        policy_context = {
            "policy_visible": True,
            "evidence_refs": [
                f"runtime:{row.get('source_name', 'unknown')}:{index}"
            ],
            "provenance": [str(row.get("source_name", "UNKNOWN"))],
            "body_schema_generation": body_generation,
            "proposal_class": "ACTUAL_PROPOSAL",
        }
        if route is not None:
            policy_context["route"] = route
        candidates.append({
            "candidate_ref": f"runtime:{index}",
            "source_name": row.get("source_name", "UNKNOWN"),
            "capability": capability,
            "params": params,
            "policy_context": policy_context,
        })
    body_capabilities = {}
    for capability in sorted({str(row["capability"]) for row in pool}):
        status = "available"
        if body_state.get("capability_status", {}).get(capability) in {"degraded", "dormant"}:
            status = body_state["capability_status"][capability]
        body_capabilities[capability] = {
            "status": status,
            "body_schema_generation": body_generation,
        }
    return {
        "schema_version": 1,
        "physiology": _physiology_input(context["physiology"]),
        "drift": dict(DEFAULT_DRIFT),
        "active_ticks": int(context["active_ticks"]),
        "observations": observations,
        "remembered_evidence": [],
        "world_entities": [],
        "affordance_beliefs": [],
        "transition_models": [],
        "body_capabilities": body_capabilities,
        "d014e_constraints": {"max_route_steps": 8},
        "effect_branches": effect_branches,
        "opportunities": _opportunities(observations),
        "recovery_focus": (context.get("critical_recovery_context") or {}).get("recovery_focus"),
        "candidates": candidates,
    }


def h3e_selector_callback(context: dict[str, Any]) -> dict[str, Any]:
    state = selector_input(context)
    result = evaluate(state)
    selected = result.get("selected")
    if not isinstance(selected, dict):
        raise RuntimeError("d014h3e_no_selected_candidate")
    return {
        "candidate": Candidate(str(selected["capability"]), dict(selected["params"])),
        "trace": {
            "selector": result,
            "input_fingerprint": result.get("input_fingerprint"),
            "output_fingerprint": result.get("output_fingerprint"),
            "actual_proposal_count": len(state["candidates"]),
            "source_evidence": _source_evidence(context),
        },
    }



def h3d_selector_callback(context: dict[str, Any]) -> dict[str, Any]:
    state = selector_input(context)
    result = evaluate(state)
    selected = result.get("selected")
    if not isinstance(selected, dict):
        raise RuntimeError("d014h3d_no_selected_candidate")
    return {
        "candidate": Candidate(str(selected["capability"]), dict(selected["params"])),
        "trace": {
            "selector": result,
            "input_fingerprint": result.get("input_fingerprint"),
            "output_fingerprint": result.get("output_fingerprint"),
        },
    }


def identity_selector_callback(context: dict[str, Any]) -> dict[str, Any]:
    current = context["current_candidate"]
    return {
        "candidate": Candidate(str(current["capability"]), dict(current["params"])),
        "trace": {"mode": "identity", "selector_call": 1},
    }


def sentinel_selector_callback(context: dict[str, Any]) -> dict[str, Any]:
    current = context["current_candidate"]
    current_key = (current["capability"], json.dumps(current.get("params") or {}, sort_keys=True))
    seen = set()
    for row in context["candidate_pool"]:
        key = (row["capability"], json.dumps(row.get("params") or {}, sort_keys=True))
        if key in seen or key == current_key:
            continue
        seen.add(key)
        return {
            "candidate": Candidate(str(row["capability"]), dict(row.get("params") or {})),
            "trace": {"mode": "sentinel", "candidate_ref": row.get("source_name")},
        }
    return {
        "candidate": Candidate(str(current["capability"]), dict(current.get("params") or {})),
        "trace": {"mode": "sentinel", "candidate_ref": "current"},
    }


def organism_config(db_path: Path, seed: int, selector: Callable | None,
                    trace_path: Path, scenario: str) -> OrganismConfig:
    from experiments.d009.run_experiment import _habitat_state_for_scenario
    from experiments.d009.scenario_plants import apply_scenario_plants
    return OrganismConfig(
        db_path=str(db_path),
        seed=seed,
        condition="C0",
        snapshot_every=200,
        temporal_enabled=True,
        temporal_config=TemporalConfig(),
        temporal_scenario_id=scenario,
        temporal_scenario_hook=apply_scenario_plants,
        habitat_enabled=True,
        habitat_scenario_id=scenario,
        habitat_scenario_hook=apply_scenario_plants,
        self_model_enabled=True,
        world_model_enabled=True,
        development_enabled=True,
        memory_enabled=True,
        social_enabled=True,
        individuality_enabled=True,
        embodiment_adapter_enabled=True,
        expression_enabled=True,
        drift_enabled=True,
        wall_time_fn=lambda: 0.0,
        decision_trace_path=str(trace_path),
        experimental_final_selector=selector,
    )


def prepare_organism(db_path: Path, seed: int, selector: Callable | None,
                     trace_path: Path, scenario: str):
    from experiments.d009.run_experiment import _habitat_state_for_scenario
    config = organism_config(db_path, seed, selector, trace_path, scenario)
    organism = create_organism(config)
    for method in ("_ensure_development_intervention", "_ensure_memory_history",
                   "_ensure_social_history", "_ensure_individuality_history"):
        getattr(organism, method)()
    organism.embodiment.attach_habitat_engine(HabitatEngine(_habitat_state_for_scenario(scenario)))
    organism.embodiment.body.x, organism.embodiment.body.y = 4.0, 3.0
    organism.perception.perceive_habitat_objects(organism.embodiment, 1.0, organism.rng)
    return organism


def run_one_tick(selector: Callable | None, seed: int = 41241905, scenario: str = "S0") -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="u-h3d-", dir="/dev/shm") as tmp:
        root = Path(tmp)
        trace = root / "decision.jsonl"
        org = prepare_organism(root / "organism.sqlite", seed, selector, trace, scenario)
        try:
            result = org.tick_once()
            state = org.authoritative_state()
            return {
                "result": result,
                "state": state,
                "trace": [json.loads(line) for line in trace.read_text().splitlines()],
            }
        finally:
            org.close()


def run_case(seed: int, selector: Callable, regime: str, scenario: str, horizon: int = HORIZON) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="u-h3d-", dir="/dev/shm") as tmp:
        root = Path(tmp)
        trace = root / "decision.jsonl"
        org = prepare_organism(root / "organism.sqlite", seed, selector, trace)
        try:
            for _ in range(horizon):
                result = org.tick_once()
                if org.phys.critical_any():
                    return {"terminal": "scientific_failure", "ticks": org.tick, "result": result}
            rows = [json.loads(line) for line in trace.read_text().splitlines()]
            return {
                "terminal": "completed",
                "regime": regime,
                "requested_regime": regime,
                "resolved_scenario": scenario,
                "ticks": org.tick,
                "selector_call_count": sum(1 for row in rows if "d014h3d_selector" in row),
                "post_selection_replacement_count": sum(
                    row.get("d014h3d_selector", {}).get("post_selection_replacement_count", 0)
                    for row in rows
                ),
            }
        finally:
            org.close()

run_r0_case = lambda seed, selector, horizon=HORIZON: run_case(seed, selector, "R0", "S0", horizon)
