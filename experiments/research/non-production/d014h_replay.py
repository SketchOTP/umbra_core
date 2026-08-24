from __future__ import annotations

from copy import deepcopy
from d014h_regulation import canonical_bytes, evaluate, fingerprint


def synthetic_fixture():
    phys = {}
    for name, value, low, high in (
        ("energy", 0.70, 0.0, 1.0),
        ("fatigue", 0.20, 0.0, 1.0),
        ("integrity", 0.90, 0.0, 1.0),
        ("stimulation", 0.40, 0.0, 1.0),
    ):
        phys[name] = {
            "value": value,
            "lower": low,
            "upper": high,
            "critical_low": 0.05,
            "critical_high": 0.95,
        }
    return {
        "schema_version": 1,
        "physiology": phys,
        "observations": [{
            "policy_visible": True,
            "evidence_ref": "synthetic:obs:0",
            "provenance": "CURRENT_OBSERVATION",
        }],
        "remembered_evidence": [],
        "world_entities": [],
        "affordance_beliefs": [],
        "transition_models": [],
        "body_capabilities": {
            "IDLE": {"status": "available", "body_schema_generation": "synthetic-1"},
            "CHARGE": {"status": "available", "body_schema_generation": "synthetic-1"},
            "MOVE": {"status": "degraded", "body_schema_generation": "synthetic-1"},
        },
        "effect_branches": {
            "IDLE": [{
                "effect": {"energy": 0.0, "fatigue": 0.0, "integrity": 0.0, "stimulation": 0.0},
                "failure": False,
                "evidence_ref": "synthetic:effect:idle",
            }],
            "CHARGE": [{
                "effect": {"energy": 0.1, "fatigue": 0.0, "integrity": 0.0, "stimulation": 0.0},
                "failure": False,
                "evidence_ref": "synthetic:effect:charge",
            }],
            "MOVE": [{
                "effect": {"energy": -0.04, "fatigue": 0.02, "integrity": 0.0, "stimulation": 0.0},
                "failure": False,
                "evidence_ref": "synthetic:effect:move",
            }],
        },
        "drift": {"energy": -0.002, "fatigue": 0.002, "integrity": -0.0002, "stimulation": -0.002},
        "active_ticks": 12,
        "recovery_focus": "energy",
        "candidates": [
            {
                "candidate_ref": "synthetic:c0",
                "capability": "IDLE",
                "params": {},
                "source_name": "synthetic",
                "policy_context": {
                    "policy_visible": True,
                    "evidence_refs": ["synthetic:obs:0"],
                    "body_schema_generation": "synthetic-1",
                    "route": {"estimated_distance": 0.0, "distance_support_upper_bound": 0.0},
                    "estimated_corrective_action_count": 0,
                },
            },
            {
                "candidate_ref": "synthetic:c1",
                "capability": "CHARGE",
                "params": {"toward": "resource"},
                "source_name": "synthetic",
                "policy_context": {
                    "policy_visible": True,
                    "evidence_refs": ["synthetic:obs:0"],
                    "body_schema_generation": "synthetic-1",
                    "route": {"estimated_distance": 1.0, "distance_support_upper_bound": 1.5},
                    "estimated_corrective_action_count": 1,
                },
            },
            {
                "candidate_ref": "synthetic:c2",
                "capability": "CHARGE",
                "params": {"toward": "resource"},
                "source_name": "duplicate",
                "policy_context": {"policy_visible": True},
            },
        ],
    }


def replay_twice(payload):
    first = evaluate(deepcopy(payload))
    second = evaluate(deepcopy(payload))
    return {
        "replay_equal": canonical_bytes(first) == canonical_bytes(second),
        "first": first,
        "second": second,
        "input_fingerprint": fingerprint(payload),
    }
