from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any

SPEC_FINGERPRINT = "f5e4da7f53dca5c41526262b7b2e82129a90dd43ec02aafdc889df4f6bee9dec"
SCHEMA_VERSION = 1
DIMENSIONS = ("energy", "fatigue", "integrity", "stimulation")
MAX_CANDIDATES = 128
MAX_PARAMETER_DEPTH = 8
MAX_ROUTE_COUNT = 1024
PROVENANCE_KINDS = {
    "CURRENT_OBSERVATION",
    "REMEMBERED_ESTIMATE",
    "VERIFIED_OUTCOME",
    "BODY_SELF_MODEL",
    "AUTHORITATIVE_EFFECT",
}


class ContractError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _json_depth(value: Any, depth: int = 0) -> int:
    if isinstance(value, dict):
        return max([depth] + [_json_depth(v, depth + 1) for v in value.values()])
    if isinstance(value, list):
        return max([depth] + [_json_depth(v, depth + 1) for v in value])
    return depth


def _validate_json(value: Any, depth: int = 0) -> None:
    if depth > MAX_PARAMETER_DEPTH:
        raise ContractError("parameter_depth")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError("non_string_key")
            _validate_json(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _validate_json(item, depth + 1)
    elif value is None or isinstance(value, (str, bool, int)):
        return
    elif isinstance(value, float) and math.isfinite(value):
        return
    else:
        raise ContractError("non_canonical_json_value")


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(name)
    return value


def _valid_evidence(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    return (
        record.get("policy_visible") is True
        and isinstance(record.get("evidence_ref"), str)
        and bool(record["evidence_ref"])
        and record.get("provenance") in PROVENANCE_KINDS
    )


def _status(record: Any) -> str:
    if record is None:
        return "UNKNOWN"
    return "KNOWN" if _valid_evidence(record) else "INVALID"


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _physiology_vector(state: dict[str, Any]) -> dict[str, dict[str, float]]:
    phys = _require_dict(state.get("physiology"), "physiology")
    if set(phys) != set(DIMENSIONS):
        raise ContractError("physiology_dimensions")
    out: dict[str, dict[str, float]] = {}
    for name in DIMENSIONS:
        item = _require_dict(phys[name], f"physiology.{name}")
        required = {"value", "lower", "upper", "critical_low", "critical_high"}
        if set(item) != required:
            raise ContractError(f"physiology_fields.{name}")
        if not all(_finite(item[k]) for k in required):
            raise ContractError(f"physiology_finite.{name}")
        if not (item["lower"] <= item["critical_low"] <= item["critical_high"] <= item["upper"]):
            raise ContractError(f"physiology_bounds.{name}")
        out[name] = {k: float(item[k]) for k in required}
    return out


def _candidate_key(candidate: dict[str, Any]) -> tuple[str, bytes]:
    return str(candidate["capability"]), canonical_bytes(candidate["params"])


def _context_value(policy_context: dict[str, Any], key: str) -> Any:
    value = policy_context.get(key)
    if isinstance(value, dict) and "policy_visible" in value:
        return value if _valid_evidence(value) else None
    return value


def _route_context(candidate: dict[str, Any]) -> dict[str, Any]:
    pc = candidate.get("policy_context", {})
    if not isinstance(pc, dict):
        raise ContractError("candidate.policy_context")
    route = _context_value(pc, "route")
    if route is None:
        return {"status": "UNKNOWN", "interval": None}
    if not isinstance(route, dict):
        raise ContractError("candidate.route")
    distance = route.get("estimated_distance")
    support = route.get("distance_support_upper_bound", distance)
    if not (_finite(distance) and _finite(support) and float(distance) >= 0 and float(support) >= 0):
        return {"status": "UNKNOWN", "interval": None}
    upper = max(float(distance), float(support))
    return {"status": "KNOWN", "interval": [float(distance), upper]}


def _progress_context(candidate: dict[str, Any]) -> dict[str, Any]:
    pc = candidate.get("policy_context", {})
    progress = _context_value(pc, "progress") if isinstance(pc, dict) else None
    if progress is None:
        return {"status": "UNKNOWN"}
    if not isinstance(progress, dict):
        raise ContractError("candidate.progress")
    fields = ("progress_since_denial", "retry_count", "denial_capability", "new_evidence_since_denial")
    if set(progress) != set(fields):
        return {"status": "UNKNOWN"}
    if not _finite(progress["progress_since_denial"]) or not isinstance(progress["retry_count"], int):
        return {"status": "UNKNOWN"}
    if progress["retry_count"] < 0 or not isinstance(progress["denial_capability"], str) or not isinstance(progress["new_evidence_since_denial"], bool):
        return {"status": "UNKNOWN"}
    return {"status": "KNOWN", "value": deepcopy(progress)}


def _time_context(candidate: dict[str, Any]) -> dict[str, Any]:
    pc = candidate.get("policy_context", {})
    count = _context_value(pc, "estimated_corrective_action_count") if isinstance(pc, dict) else None
    if isinstance(count, int) and not isinstance(count, bool) and 0 <= count <= MAX_ROUTE_COUNT:
        return {"status": "KNOWN", "value": count}
    return {"status": "UNKNOWN"}


def _successor_context(
    candidate: dict[str, Any],
    state: dict[str, Any],
    phys: dict[str, dict[str, float]],
) -> dict[str, Any]:
    branches = state["effect_branches"].get(candidate["capability"])
    drift = _require_dict(state["drift"], "drift")
    if branches is None or not isinstance(branches, list) or not branches:
        return {"status": "UNKNOWN", "branches": []}
    if len(branches) > MAX_ROUTE_COUNT:
        raise ContractError("effect_branch_count")
    results = []
    any_critical = False
    for branch in branches:
        if not isinstance(branch, dict) or not isinstance(branch.get("effect"), dict):
            raise ContractError("effect_branch")
        effect = branch["effect"]
        values = {}
        margins = {}
        branch_status = "KNOWN"
        for name in DIMENSIONS:
            if not _finite(effect.get(name, 0.0)) or not _finite(drift.get(name, 0.0)):
                branch_status = "UNKNOWN"
                break
            item = phys[name]
            after = _clamp(
                item["value"] + float(effect.get(name, 0.0)) + float(drift.get(name, 0.0)),
                item["lower"],
                item["upper"],
            )
            values[name] = after
            margins[name] = {
                "to_critical_low": after - item["critical_low"],
                "to_critical_high": item["critical_high"] - after,
            }
        if branch_status == "UNKNOWN":
            results.append({"status": "UNKNOWN", "effect": deepcopy(effect)})
            continue
        critical = any(
            values[name] < phys[name]["critical_low"] or values[name] > phys[name]["critical_high"]
            for name in DIMENSIONS
        )
        any_critical = any_critical or critical
        results.append({
            "status": "KNOWN",
            "effect": deepcopy(effect),
            "failure": bool(branch.get("failure", False)),
            "values": values,
            "margins": margins,
            "critical": critical,
            "evidence_ref": branch.get("evidence_ref"),
        })
    return {
        "status": "KNOWN" if results and all(x["status"] == "KNOWN" for x in results) else "UNKNOWN",
        "branches": results,
        "tradeoff_label": "SOME_CRITICAL" if any_critical else "ALL_NONCRITICAL",
    }


def _body_status(candidate: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    body = state["body_capabilities"].get(candidate["capability"])
    if not isinstance(body, dict):
        return {"status": "UNKNOWN"}
    status = body.get("status")
    generation = body.get("body_schema_generation")
    if status not in {"available", "degraded", "dormant", "unknown"} or not isinstance(generation, str):
        return {"status": "UNKNOWN"}
    pc = candidate.get("policy_context", {})
    expected = pc.get("body_schema_generation") if isinstance(pc, dict) else None
    if expected is not None and expected != generation:
        return {"status": "STALE", "body_schema_generation": generation}
    return {"status": status.upper(), "body_schema_generation": generation}


def _candidate_annotation(candidate: dict[str, Any], index: int, state: dict[str, Any], phys: dict[str, dict[str, float]], input_fp: str) -> dict[str, Any]:
    context = candidate.get("policy_context", {})
    if not isinstance(context, dict):
        raise ContractError("candidate.policy_context")
    evidence_status = "KNOWN" if context.get("policy_visible") is True else "UNKNOWN"
    route = _route_context(candidate)
    progress = _progress_context(candidate)
    time_to_benefit = _time_context(candidate)
    successor = _successor_context(candidate, state, phys)
    body = _body_status(candidate, state)
    modifier = -1 if successor.get("tradeoff_label") == "SOME_CRITICAL" else 0
    evidence_refs = context.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or not all(isinstance(x, str) and x for x in evidence_refs):
        evidence_refs = []
    return {
        "candidate_ref": str(candidate.get("candidate_ref", f"source:{index}")),
        "capability": candidate["capability"],
        "params": deepcopy(candidate["params"]),
        "context": {
            "evidence_status": evidence_status,
            "route": route,
            "progress": progress,
            "time_to_benefit": time_to_benefit,
            "successor": successor,
            "body": body,
            "modifier": modifier,
        },
        "provenance": {
            "source_index": index,
            "source_name": str(candidate.get("source_name", "UNKNOWN")),
            "evidence_refs": evidence_refs,
            "body_schema_generation": body.get("body_schema_generation"),
            "spec_fingerprint": SPEC_FINGERPRINT,
            "input_fingerprint": input_fp,
        },
    }


def evaluate(state: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "physiology", "observations", "remembered_evidence",
        "world_entities", "affordance_beliefs", "transition_models",
        "body_capabilities", "effect_branches", "drift", "active_ticks",
        "recovery_focus", "candidates",
    }
    if not isinstance(state, dict) or set(state) != required:
        raise ContractError("input_schema")
    if state["schema_version"] != SCHEMA_VERSION or not isinstance(state["active_ticks"], int) or state["active_ticks"] < 0:
        raise ContractError("header")
    _validate_json(state)
    phys = _physiology_vector(state)
    for name in ("observations", "remembered_evidence", "world_entities", "affordance_beliefs", "transition_models", "candidates"):
        if not isinstance(state[name], list):
            raise ContractError(name)
    _require_dict(state["body_capabilities"], "body_capabilities")
    _require_dict(state["effect_branches"], "effect_branches")
    _require_dict(state["drift"], "drift")
    input_fp = fingerprint(state)
    if len(state["candidates"]) > MAX_CANDIDATES:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "OVERFLOW",
            "proposals": [],
            "rejected_inputs": [{"reason": "candidate_count", "count": len(state["candidates"])}],
            "input_fingerprint": input_fp,
            "output_fingerprint": None,
            "spec_fingerprint": SPEC_FINGERPRINT,
        }
    proposals = []
    rejected = []
    seen: dict[tuple[str, bytes], int] = {}
    for index, candidate in enumerate(state["candidates"]):
        try:
            if not isinstance(candidate, dict):
                raise ContractError("candidate")
            capability = candidate.get("capability")
            params = candidate.get("params")
            if not isinstance(capability, str) or not capability or not isinstance(params, dict):
                raise ContractError("candidate_shape")
            _validate_json(params)
            key = _candidate_key(candidate)
            if key in seen:
                proposals[seen[key]]["provenance"]["duplicate_source_indices"].append(index)
                continue
            proposal = _candidate_annotation(candidate, index, state, phys, input_fp)
            proposal["provenance"]["duplicate_source_indices"] = []
            seen[key] = len(proposals)
            proposals.append(proposal)
        except ContractError as exc:
            rejected.append({"source_index": index, "reason": str(exc)})
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "COMPLETE" if not rejected else "CONTRACT_ERROR",
        "proposals": proposals,
        "rejected_inputs": rejected,
        "input_fingerprint": input_fp,
        "output_fingerprint": None,
        "spec_fingerprint": SPEC_FINGERPRINT,
    }
    result["output_fingerprint"] = fingerprint({**result, "output_fingerprint": None})
    return result
