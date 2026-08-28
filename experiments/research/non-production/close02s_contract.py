"""Pure CLOSE-02S contract shadow; never imported by production runtime."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Iterable


_PROVENANCE_KEYS = frozenset({"source", "intent_id", "goal_id", "trace_id"})


def _behavioral_params(params: dict[str, Any]) -> dict[str, Any]:
    return {str(k): _behavioral_value(v) for k, v in params.items() if str(k) not in _PROVENANCE_KEYS}


def _behavioral_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _behavioral_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_behavioral_value(v) for v in value]
    return value


def _key(candidate: dict[str, Any]) -> str:
    return json.dumps([str(candidate["capability"]), _behavioral_params(dict(candidate.get("params") or {}))], sort_keys=True, separators=(",", ":"))


def _dedupe(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        item = deepcopy(candidate)
        result.setdefault(_key(item), item)
    return [result[key] for key in sorted(result)]


def _executable(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [deepcopy(candidate) for candidate in candidates if bool(candidate.get("authority_valid", True)) and bool(candidate.get("immediately_safe", True))]


def evaluate_contract(*, intent_candidates: list[dict[str, Any]], base_candidates: list[dict[str, Any]], preventive_signal: set[str], hard_recovery: bool, hard_recovery_candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return only the eligibility envelope; it does not select or execute."""
    intents = _dedupe(_executable(intent_candidates))
    base = _dedupe(_executable(base_candidates))
    recovery = _dedupe(_executable(hard_recovery_candidates or []))
    if hard_recovery:
        eligible, state, excluded = recovery, "STATE_5_ACTIVE_OR_CRITICAL_RECOVERY", ["intent", "base", "preventive"]
    elif intents and preventive_signal:
        regulatory = [c for c in base if set(c.get("regulatory_dimensions") or ()).intersection(preventive_signal)]
        eligible, state, excluded = _dedupe([*intents, *regulatory]), "STATE_3_INTENT_ACTIVE_PREVENTIVE_REGULATORY_ATTENTION", ["unrelated_base"]
    elif intents:
        eligible, state, excluded = intents, "STATE_2_INTENT_ACTIVE_NO_REGULATORY_ATTENTION", ["base"]
    elif preventive_signal:
        eligible = [c for c in base if set(c.get("regulatory_dimensions") or ()).intersection(preventive_signal)]
        state, excluded = "STATE_4_NO_INTENT_PREVENTIVE_REGULATORY_ATTENTION", ["unrelated_base"]
    else:
        eligible, state, excluded = base, "STATE_1_NO_INTENT_NO_REGULATORY_ATTENTION", []
    return {"state": state, "eligible": eligible, "excluded_classes": excluded, "no_safe_action": not bool(eligible), "intent_count": len(intents), "intent_conflict": len(intents) > 1, "selection_authority": "existing_action_level_arbitration", "hidden_truth_used": False, "new_threshold": False, "new_weight": False, "source_priority": False}
