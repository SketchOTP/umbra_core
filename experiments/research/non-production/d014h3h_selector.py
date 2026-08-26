"""D-014H3H fresh deterministic authority-safe prospective selector.

This module is research-only. It consumes a frozen, policy-visible proposal
pool and returns a traceable selection. It never calls production authority,
never changes organism state, and never uses hidden world truth.
"""
from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any

SCHEMA_VERSION = 2
BEHAVIORAL_KEY_SCHEMA_VERSION = 1
DIMENSIONS = ("energy", "fatigue", "integrity", "stimulation")
MAX_DIRECT_ROUTE_STEPS = 8
MAX_OPPORTUNITIES = 16
MAX_EFFECT_BRANCHES = 8
MAX_CANDIDATES = 128
FORBIDDEN_TOKENS = ("hidden_", "oracle", "true_distance", "true_identity", "future_outcome")
# These are the existing production Candidate score fields. H3H carries
# them through unchanged; it never synthesizes a source bonus or replacement
# score.
ORDINARY_FIELDS = (
    "expected_regulatory_gain",
    "expected_option_preservation",
    "novelty",
    "uncertainty_reduction",
    "effort_cost",
    "risk_cost",
    "commitment_continuity",
)

# Explicit source-audited execution/target semantics. Provenance-only fields
# are excluded from behavioral identity below, while full params remain in the
# returned row for Governance and execution.
BEHAVIORAL_PARAM_KEYS = frozenset({
    "heading", "heading_delta", "step", "toward", "from", "source", "strategy",
    "tick", "maximum_wait_ticks", "window_start", "window_end",
    "expectation_version", "wait_deadline", "interrupt_conditions",
    "internal_context_key", "expected_occurrence_id", "recurrence_id",
    "target_address_ref", "perception_evidence_ref", "perception_state_version",
    "perceived_object_kind", "perceived_affordance_ref", "parameters",
    "expected_profile_hash", "object_definition_hash",
    "affordance_definition_hash", "zone_id", "binding_stale",
    "practice_goal_id", "_social_signal",
})
PROVENANCE_ONLY_PARAM_KEYS = frozenset({
    "candidate_ref", "proposal_id", "execution_id", "request_id",
    "source_name", "trace_id", "evidence_id", "episode_id", "goal_id",
    "skill_id", "routine_id", "memory_id", "hypothesis_id",
})


class ContractError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _json_safe(value: Any, depth: int = 0) -> None:
    if depth > 10:
        raise ContractError("parameter_depth")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError("non_string_key")
            lowered = key.lower()
            if any(token in lowered for token in FORBIDDEN_TOKENS):
                raise ContractError("hidden_truth_not_allowed")
            _json_safe(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _json_safe(item, depth + 1)
    elif value is None or isinstance(value, (str, bool, int)):
        return
    elif isinstance(value, float) and math.isfinite(value):
        return
    else:
        raise ContractError("non_canonical_value")


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(name)
    return value


def _physiology(state: dict[str, Any]) -> dict[str, dict[str, float]]:
    raw = _require_dict(state.get("physiology"), "physiology")
    if set(raw) != set(DIMENSIONS):
        raise ContractError("physiology_dimensions")
    result: dict[str, dict[str, float]] = {}
    required = {"value", "lower", "upper", "critical_low", "critical_high"}
    for name in DIMENSIONS:
        item = _require_dict(raw[name], f"physiology.{name}")
        if set(item) != required or not all(_finite(item[k]) for k in required):
            raise ContractError(f"physiology_fields.{name}")
        if not item["lower"] <= item["critical_low"] <= item["critical_high"] <= item["upper"]:
            raise ContractError(f"physiology_bounds.{name}")
        result[name] = {key: float(item[key]) for key in required}
    return result


def _effect_branches(state: dict[str, Any], capability: str) -> list[dict[str, Any]]:
    raw = _require_dict(state["effect_branches"], "effect_branches").get(capability)
    if not isinstance(raw, list) or not raw or len(raw) > MAX_EFFECT_BRANCHES:
        return []
    result = []
    for branch in raw:
        if not isinstance(branch, dict) or not isinstance(branch.get("effect"), dict):
            return []
        effect = {}
        for name in DIMENSIONS:
            value = branch["effect"].get(name, 0.0)
            if not _finite(value):
                return []
            effect[name] = float(value)
        result.append({"effect": effect, "failure": bool(branch.get("failure", False))})
    return result


def _behavioral_params(params: dict[str, Any]) -> dict[str, Any]:
    """Project only source-audited execution/target semantics for identity."""
    result: dict[str, Any] = {}
    for key, value in params.items():
        if key in PROVENANCE_ONLY_PARAM_KEYS:
            continue
        if key in BEHAVIORAL_PARAM_KEYS:
            result[key] = deepcopy(value)
            continue
        # Unknown fields are retained in the key until the audit proves they
        # are provenance-only. This is fail-closed against identity collapse.
        result[key] = deepcopy(value)
    return result


def behavioral_candidate_key(candidate: dict[str, Any]) -> str:
    return fingerprint({
        "schema_version": BEHAVIORAL_KEY_SCHEMA_VERSION,
        "capability": candidate["capability"],
        "params": _behavioral_params(candidate["params"]),
    })


def _candidate_key(candidate: dict[str, Any]) -> str:
    return behavioral_candidate_key(candidate)


def _valid_evidence(context: dict[str, Any]) -> bool:
    return (
        context.get("policy_visible") is True
        and isinstance(context.get("evidence_refs"), list)
        and all(isinstance(item, str) and item for item in context["evidence_refs"])
    )


def _opportunity_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    opportunities = state.get("opportunities")
    if not isinstance(opportunities, list) or len(opportunities) > MAX_OPPORTUNITIES:
        raise ContractError("opportunity_count")
    result = {}
    for item in opportunities:
        if not isinstance(item, dict) or not isinstance(item.get("opportunity_ref"), str):
            raise ContractError("opportunity")
        if not item.get("policy_visible", False):
            continue
        result[item["opportunity_ref"]] = deepcopy(item)
    return result


def _add_vector(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    return {name: left.get(name, 0.0) + right.get(name, 0.0) for name in DIMENSIONS}


def _margin(vector: dict[str, float], phys: dict[str, dict[str, float]]) -> dict[str, float]:
    return {
        name: min(vector[name] - phys[name]["critical_low"],
                 phys[name]["critical_high"] - vector[name])
        for name in DIMENSIONS
    }


def _critical(vector: dict[str, float], phys: dict[str, dict[str, float]]) -> bool:
    return any(
        vector[name] < phys[name]["critical_low"] or vector[name] > phys[name]["critical_high"]
        for name in DIMENSIONS
    )


def _branch_effects(candidate: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    route = candidate["policy_context"].get("route")
    if isinstance(route, dict) and isinstance(route.get("action_effect_branches"), list):
        raw = route["action_effect_branches"]
        if raw and len(raw) <= MAX_EFFECT_BRANCHES:
            return [{"effect": dict(item.get("effect", {})), "failure": bool(item.get("failure", False))}
                    for item in raw if isinstance(item, dict)]
    ref = candidate.get("candidate_ref")
    exact = state.get("effect_branches_exact", {})
    if isinstance(exact, dict) and isinstance(ref, str):
        raw = exact.get(ref)
        if isinstance(raw, list):
            return [{"effect": dict(item), "failure": False} for item in raw if isinstance(item, dict)]
    return _effect_branches(state, candidate["capability"])


def _route_envelope(candidate: dict[str, Any], state: dict[str, Any],
                    phys: dict[str, dict[str, float]],
                    opportunities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    context = candidate["policy_context"]
    route = context.get("route")
    if route is None:
        branches = _branch_effects(candidate, state)
        if not branches:
            return {"status": "UNKNOWN", "reason": "effect_support_unknown"}
        vectors = []
        for branch in branches:
            vector = _add_vector(
                {name: phys[name]["value"] for name in DIMENSIONS},
                _add_vector(branch["effect"], state["drift"]),
            )
            vectors.append(vector)
        return {
            "status": "KNOWN_INFEASIBLE" if any(_critical(v, phys) for v in vectors) else "KNOWN_FEASIBLE",
            "route_kind": "IMMEDIATE",
            "time_to_benefit": [1, 1],
            "minimum_slack": {name: min(_margin(v, phys)[name] for v in vectors) for name in DIMENSIONS},
            "arrival_physiology": vectors,
            "terminal_benefit_physiology": vectors,
            "branch_count": len(vectors),
        }
    if not isinstance(route, dict):
        return {"status": "UNKNOWN", "reason": "route_shape"}
    if route.get("policy_visible") is not True:
        return {"status": "UNKNOWN", "reason": "route_not_policy_visible"}
    opportunity_ref = route.get("opportunity_ref")
    if not isinstance(opportunity_ref, str) or opportunity_ref not in opportunities:
        return {"status": "UNKNOWN", "reason": "opportunity_unavailable"}
    distance = route.get("estimated_distance")
    support_upper = route.get("distance_support_upper_bound", distance)
    progress = route.get("progress_per_step")
    if not (_finite(distance) and _finite(support_upper) and _finite(progress)
            and float(distance) >= 0 and float(support_upper) >= 0 and float(progress) > 0):
        return {"status": "UNKNOWN", "reason": "route_support_unknown"}
    upper = max(float(distance), float(support_upper))
    progress = float(progress)
    approach_steps = int(math.ceil(upper / progress))
    terminal_capability = route.get("terminal_capability")
    terminal_branches = route.get("terminal_effect_branches")
    if not isinstance(terminal_capability, str) or not isinstance(terminal_branches, list):
        return {"status": "UNKNOWN", "reason": "terminal_affordance_unknown"}
    total_steps = approach_steps + 1
    if total_steps > MAX_DIRECT_ROUTE_STEPS or not terminal_branches:
        return {"status": "UNKNOWN", "reason": "route_bound"}
    action_branches = _branch_effects(candidate, state)
    if not action_branches:
        return {"status": "UNKNOWN", "reason": "approach_effect_unknown"}
    if len(terminal_branches) > MAX_EFFECT_BRANCHES:
        return {"status": "UNKNOWN", "reason": "terminal_branch_bound"}
    states = [{name: phys[name]["value"] for name in DIMENSIONS}]
    for _ in range(approach_steps):
        next_states = []
        for current in states:
            for branch in action_branches:
                effect = branch.get("effect", {})
                if not all(_finite(effect.get(name, 0.0)) for name in DIMENSIONS):
                    return {"status": "UNKNOWN", "reason": "approach_effect_unknown"}
                next_states.append(_add_vector(current, _add_vector(effect, state["drift"])))
        if len(next_states) > MAX_EFFECT_BRANCHES:
            return {"status": "UNKNOWN", "reason": "branch_bound"}
        states = next_states
    arrival = deepcopy(states)
    terminal_states = []
    for current in states:
        for branch in terminal_branches:
            effect = branch.get("effect", {})
            if not all(_finite(effect.get(name, 0.0)) for name in DIMENSIONS):
                return {"status": "UNKNOWN", "reason": "terminal_effect_unknown"}
            terminal_states.append(_add_vector(current, effect))
    if not terminal_states:
        return {"status": "UNKNOWN", "reason": "terminal_effect_unknown"}
    all_vectors = arrival + terminal_states
    critical = any(_critical(vector, phys) for vector in all_vectors)
    return {
        "status": "KNOWN_INFEASIBLE" if critical else "KNOWN_FEASIBLE",
        "route_kind": "DIRECT_APPROACH_THEN_TERMINAL",
        "opportunity_ref": opportunity_ref,
        "route_steps": total_steps,
        "time_to_benefit": [total_steps, total_steps],
        "arrival_physiology": arrival,
        "terminal_benefit_physiology": terminal_states,
        "minimum_slack": {
            name: min(_margin(vector, phys)[name] for vector in all_vectors)
            for name in DIMENSIONS
        },
        "branch_count": len(terminal_states),
        "progress_support": {
            "estimated_distance": float(distance),
            "distance_support_upper_bound": upper,
            "progress_per_step": progress,
        },
    }


def _ordinary_vector(context: dict[str, Any]) -> list[float]:
    raw = context.get("candidate_scores")
    if not isinstance(raw, dict):
        raw = context.get("ordinary_evidence", {})
    if not isinstance(raw, dict):
        return [0.0] * len(ORDINARY_FIELDS)
    result = []
    for field in ORDINARY_FIELDS:
        value = raw.get(field, 0.0)
        result.append(float(value) if _finite(value) else 0.0)
    return result


def _annotate(candidate: dict[str, Any], index: int, state: dict[str, Any],
              phys: dict[str, dict[str, float]], opportunities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    context = candidate.get("policy_context")
    if not isinstance(context, dict) or not _valid_evidence(context):
        raise ContractError("candidate_policy_visibility")
    if not isinstance(candidate.get("capability"), str) or not candidate["capability"]:
        raise ContractError("candidate_capability")
    if not isinstance(candidate.get("params"), dict):
        raise ContractError("candidate_params")
    body = state["body_capabilities"].get(candidate["capability"])
    if not isinstance(body, dict) or body.get("status") not in {"available", "degraded"}:
        raise ContractError("body_eligibility")
    expected_generation = context.get("body_schema_generation")
    if expected_generation is not None and expected_generation != body.get("body_schema_generation"):
        raise ContractError("body_schema_stale")
    envelope = _route_envelope(candidate, state, phys, opportunities)
    route_status = envelope["status"]
    provenance = {
        "source_name": str(candidate.get("source_name", "UNKNOWN")),
        "provenance": sorted(set(str(x) for x in context.get("provenance", []))),
        "evidence_refs": sorted(set(context["evidence_refs"])),
        "body_schema_generation": body.get("body_schema_generation"),
        "opportunity_ref": context.get("route", {}).get("opportunity_ref") if isinstance(context.get("route"), dict) else None,
        "verified_transition_refs": sorted(set(str(x) for x in context.get("verified_transition_refs", []))),
    }
    return {
        "candidate_ref": str(candidate.get("candidate_ref", f"source:{index}")),
        "candidate_key": _candidate_key(candidate),
        "capability": candidate["capability"],
        "params": deepcopy(candidate["params"]),
        "source_name": provenance["source_name"],
        "provenance": provenance,
        "route": envelope,
        "feasibility": route_status,
        "ordinary_evidence": _ordinary_vector(context),
        "native_support": float(context.get("native_support", 0.0)) if _finite(context.get("native_support", 0.0)) else 0.0,
    }


def _merge(group: list[dict[str, Any]]) -> dict[str, Any]:
    first = min(group, key=lambda item: (item["source_index"], item["source_name"]))
    merged = deepcopy(first)
    merged["source_names"] = sorted(set(item["source_name"] for item in group))
    merged["provenance"]["evidence_refs"] = sorted(set(
        ref for item in group for ref in item["provenance"]["evidence_refs"]
    ))
    merged["provenance"]["provenance"] = sorted(set(
        ref for item in group for ref in item["provenance"]["provenance"]
    ))
    merged["duplicate_count"] = len(group)
    merged["source_index"] = first["source_index"]
    return merged


def _dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left["feasibility"] != "KNOWN_FEASIBLE" or right["feasibility"] != "KNOWN_FEASIBLE":
        return False
    lm = left["route"]["minimum_slack"]
    rm = right["route"]["minimum_slack"]
    left_time = left["route"]["time_to_benefit"][1]
    right_time = right["route"]["time_to_benefit"][1]
    no_worse = all(lm[name] >= rm[name] for name in DIMENSIONS) and left_time <= right_time
    strictly = any(lm[name] > rm[name] for name in DIMENSIONS) or left_time < right_time
    return no_worse and strictly


def evaluate(state: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "physiology", "drift", "active_ticks", "observations",
        "remembered_evidence", "world_entities", "affordance_beliefs",
        "transition_models", "body_capabilities", "d014e_constraints",
        "effect_branches", "effect_branches_exact", "opportunities", "recovery_focus", "candidates",
    }
    if not isinstance(state, dict) or set(state) != required:
        raise ContractError("input_schema")
    _json_safe(state)
    if state["schema_version"] != SCHEMA_VERSION or not isinstance(state["active_ticks"], int):
        raise ContractError("header")
    phys = _physiology(state)
    opportunities = _opportunity_map(state)
    if len(state["candidates"]) > MAX_CANDIDATES:
        return {"status": "OVERFLOW", "overflow": "candidate_count",
                "selected": None, "spec_fingerprint": SPEC_FINGERPRINT}
    annotated = []
    rejected = []
    for index, candidate in enumerate(state["candidates"]):
        try:
            if not isinstance(candidate, dict):
                raise ContractError("candidate")
            row = _annotate(candidate, index, state, phys, opportunities)
            row["source_index"] = index
            annotated.append(row)
        except ContractError as exc:
            rejected.append({"source_index": index, "reason": str(exc)})
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in annotated:
        groups.setdefault(row["candidate_key"], []).append(row)
    dedup = [_merge(groups[key]) for key in sorted(groups)]
    dominance = []
    for left in dedup:
        for right in dedup:
            if left["candidate_key"] != right["candidate_key"] and _dominates(left, right):
                dominance.append({"dominates": left["candidate_key"], "dominated": right["candidate_key"]})
    dominated = {row["dominated"] for row in dominance}
    non_dominated = [row for row in dedup if row["candidate_key"] not in dominated]
    feasible = [row for row in non_dominated if row["feasibility"] == "KNOWN_FEASIBLE"]
    if feasible:
        selected = min(feasible, key=lambda row: (
            tuple(-value for value in row["ordinary_evidence"]),
            row["route"]["time_to_benefit"][1],
            row["candidate_key"],
        ))
        resolution = "ORDINARY_ENDOGENOUS_TIE_BREAK"
    elif len(non_dominated) == 1 and non_dominated[0]["feasibility"] == "KNOWN_INFEASIBLE":
        selected = None
        resolution = "NO_SAFE_ACTION"
    elif not non_dominated:
        selected = None
        resolution = "NO_SAFE_ACTION"
    else:
        selected = min(non_dominated, key=lambda row: row["candidate_key"]) if non_dominated else None
        resolution = "UNKNOWN_NEUTRAL_TIE"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "SELECTED" if selected is not None else resolution,
        "input_fingerprint": fingerprint(state),
        "spec_fingerprint": SPEC_FINGERPRINT,
        "annotated_candidates": annotated,
        "deduplicated_candidates": dedup,
        "dominance_relations": dominance,
        "non_dominated": non_dominated,
        "selected": deepcopy(selected),
        "resolution": resolution,
        "unknown_neutral": True,
        "hidden_truth_used": False,
        "scalar_survival_score": False,
        "fixed_need_priority": False,
        "fixed_source_priority": False,
        "final_selector_count": 1,
        "output_fingerprint": fingerprint({
            "status": "SELECTED" if selected is not None else resolution,
            "annotated_candidates": annotated,
            "dominance_relations": dominance,
            "selected": selected,
        }),
    }


SPEC_FINGERPRINT = fingerprint({
    "directive": "UMBRA-D-014H3H",
    "behavioral_key_schema_version": BEHAVIORAL_KEY_SCHEMA_VERSION,
    "route_steps": MAX_DIRECT_ROUTE_STEPS,
    "opportunities": MAX_OPPORTUNITIES,
    "effect_branches": MAX_EFFECT_BRANCHES,
    "dimensions": DIMENSIONS,
    "unknown": "neutral",
})
