"""Offline translation of production D-014H2 rows into the frozen H1 pool."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from d014h1_pool import DIMENSIONS, SOURCE_NAMES, evaluate
from umbra_core.physiology import verified_outcome_effect_branches

_SOURCE_MAP = {"routine": "routine_habit"}


def _candidate(row: dict[str, Any], source: str) -> dict[str, Any] | None:
    for transition in row.get("final_candidate_lineage") or []:
        if transition.get("source") != source:
            continue
        candidate = transition.get("candidate_emitted") or transition.get("candidate_after")
        if isinstance(candidate, dict) and candidate.get("capability"):
            return candidate
    return None


def row_to_h1_state(row: dict[str, Any]) -> dict[str, Any]:
    physiology = row.get("physiology") or {}
    h1_phys = {
        name: {
            "value": float(physiology.get(name, 0.0)),
            "critical_low": 0.05,
            "critical_high": 0.95,
        }
        for name in DIMENSIONS
    }
    proposals = []
    for raw_source in SOURCE_NAMES:
        source = raw_source
        trace_source = "routine" if raw_source == "routine_habit" else raw_source
        candidate = _candidate(row, trace_source)
        if candidate is None:
            continue
        proposals.append({
            "source_name": source,
            "capability": str(candidate["capability"]),
            "params": deepcopy(candidate.get("params") or {}),
            "policy_context": {
                "policy_visible": True,
                "provenance": [f"D014H2_TRACE:{trace_source}"],
                "evidence_refs": [f"trace:tick:{row.get('tick')}"],
                "native_support": 0.0,
            },
        })
    capabilities = {
        str(proposal["capability"])
        for proposal in proposals
    }
    branches = {
        capability: [
            {"effect": deepcopy(effect)}
            for effect in verified_outcome_effect_branches(capability)
        ]
        for capability in sorted(capabilities)
    }
    return {
        "physiology": h1_phys,
        "drift": {
            "energy": -0.002,
            "fatigue": 0.002,
            "integrity": -0.0002,
            "stimulation": -0.002,
        },
        "effect_branches": branches,
        "proposals": proposals,
    }


def translate_row(row: dict[str, Any]) -> dict[str, Any]:
    state = row_to_h1_state(row)
    result = evaluate(state)
    return {
        "tick": row.get("tick"),
        "production_final_candidate": deepcopy(row.get("final_candidate")),
        "production_governance_decision": deepcopy(row.get("governance_decision")),
        "production_verified_outcome_linkage": deepcopy(row.get("verified_outcome_linkage")),
        "translation_input": state,
        "h1_result": result,
    }


def translate_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [translate_row(row) for row in rows]
