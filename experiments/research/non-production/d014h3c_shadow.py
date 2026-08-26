"""D-014H3C non-production prospective affordance competition shadow.

This module never calls production authority and never changes organism state.
It evaluates only already-emitted, policy-visible candidates at one decision
boundary. UNKNOWN is neutral and hidden truth is rejected.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

DIMENSIONS = ("energy", "fatigue", "integrity", "stimulation")
FORBIDDEN_KEYS = {"world_truth", "true_distance", "oracle", "hidden_partner_id", "hidden_identity"}
SCHEMA_VERSION = 1


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(float(value)) != float("inf")


def _reject_hidden(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in FORBIDDEN_KEYS or any(token in str(key).lower() for token in ("hidden_", "oracle_", "true_")):
                raise ValueError("hidden_truth_not_allowed")
            _reject_hidden(item)
    elif isinstance(value, list):
        for item in value:
            _reject_hidden(item)


def _vector(state: dict[str, Any]) -> dict[str, float]:
    physiology = state.get("physiology")
    if not isinstance(physiology, dict) or set(physiology) != set(DIMENSIONS):
        raise ValueError("physiology_dimensions")
    values = {}
    for name in DIMENSIONS:
        item = physiology[name]
        if not isinstance(item, dict) or not all(_finite(item.get(key)) for key in ("value", "critical_low", "critical_high")):
            raise ValueError("physiology_vector")
        values[name] = float(item["value"])
    return values


def _candidate_key(candidate: dict[str, Any]) -> str:
    return fingerprint({"capability": candidate["capability"], "params": candidate.get("params", {})})


def _successor(candidate: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    branches = state.get("effect_branches", {}).get(candidate["capability"])
    drift = state.get("drift", {})
    if not isinstance(branches, list) or not branches:
        return {"status": "UNKNOWN", "branches": []}
    results = []
    for branch in branches:
        effect = branch.get("effect") if isinstance(branch, dict) else None
        if not isinstance(effect, dict):
            results.append({"status": "UNKNOWN"})
            continue
        row = {"status": "KNOWN", "values": {}, "margin": {}, "failure": bool(branch.get("failure", False))}
        for name in DIMENSIONS:
            item = state["physiology"][name]
            delta = effect.get(name, 0.0)
            drift_delta = drift.get(name, 0.0)
            if not _finite(delta) or not _finite(drift_delta):
                row["status"] = "UNKNOWN"
                break
            value = float(item["value"]) + float(delta) + float(drift_delta)
            row["values"][name] = value
            row["margin"][name] = min(
                value - float(item["critical_low"]),
                float(item["critical_high"]) - value,
            )
        if row["status"] == "KNOWN":
            row["critical"] = any(
                row["values"][name] < float(state["physiology"][name]["critical_low"])
                or row["values"][name] > float(state["physiology"][name]["critical_high"])
                for name in DIMENSIONS
            )
        results.append(row)
    return {
        "status": "KNOWN" if all(row["status"] == "KNOWN" for row in results) else "UNKNOWN",
        "branches": results,
    }


def _dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Partial order only; UNKNOWN never becomes a negative or positive fact."""
    lm, rm = left.get("successor", {}), right.get("successor", {})
    if lm.get("status") != "KNOWN" or rm.get("status") != "KNOWN":
        return False
    lb = lm.get("branches", [])
    rb = rm.get("branches", [])
    if len(lb) != len(rb) or not lb or any(x.get("critical") for x in lb):
        return False
    if any(x.get("critical") for x in rb):
        return True
    left_margin = [min(x["margin"][name] for x in lb) for name in DIMENSIONS]
    right_margin = [min(x["margin"][name] for x in rb) for name in DIMENSIONS]
    return all(a >= b for a, b in zip(left_margin, right_margin)) and any(a > b for a, b in zip(left_margin, right_margin))


def evaluate(state: dict[str, Any]) -> dict[str, Any]:
    required = {"physiology", "drift", "effect_branches", "candidates"}
    if not isinstance(state, dict) or set(state) != required:
        raise ValueError("input_schema")
    _reject_hidden(state)
    _vector(state)
    candidates = state["candidates"]
    if not isinstance(candidates, list):
        raise ValueError("candidates")
    annotated = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict) or not isinstance(candidate.get("capability"), str):
            raise ValueError("candidate")
        context = candidate.get("policy_context", {})
        if not isinstance(context, dict) or context.get("policy_visible") is not True:
            continue
        row = {
            "candidate_ref": str(candidate.get("candidate_ref", f"source:{index}")),
            "source_index": index,
            "capability": candidate["capability"],
            "params": deepcopy(candidate.get("params", {})),
            "policy_context": deepcopy(context),
            "candidate_key": _candidate_key(candidate),
        }
        row["successor"] = _successor(candidate, state)
        row["endogenous_rank"] = context.get("existing_endogenous_rank")
        annotated.append(row)
    non_dominated = [
        row for row in annotated
        if not any(_dominates(other, row) for other in annotated if other["candidate_key"] != row["candidate_key"])
    ]
    ranked = [row for row in non_dominated if isinstance(row.get("endogenous_rank"), int)]
    selected = None
    resolution = "UNKNOWN"
    if ranked and len(ranked) == len(non_dominated):
        selected = min(ranked, key=lambda row: (row["endogenous_rank"], row["candidate_key"]))
        resolution = "EXISTING_ENDOGENOUS_ORDER"
    elif len(non_dominated) == 1:
        selected = non_dominated[0]
        resolution = "PARTIAL_ORDER_UNIQUE"
    elif not non_dominated:
        resolution = "NO_POLICY_VISIBLE_CANDIDATE"
    else:
        resolution = "UNKNOWN_TIE"
    return {
        "schema_version": SCHEMA_VERSION,
        "input_fingerprint": fingerprint(state),
        "candidate_count": len(annotated),
        "annotated_candidates": annotated,
        "non_dominated": non_dominated,
        "selected": selected,
        "resolution": resolution,
        "production_authority": False,
        "hidden_truth_used": False,
    }
