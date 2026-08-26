import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from d014h3d_selector import ContractError, canonical_bytes, evaluate

def base_state():
    phys = {n: {"value": v, "lower": 0.0, "upper": 1.0, "critical_low": 0.05, "critical_high": 0.95}
            for n, v in (("energy", 0.20), ("fatigue", 0.20), ("integrity", 0.90), ("stimulation", 0.40))}
    def candidate(source, cap, params, route=None, ordinary=None):
        ctx = {
            "policy_visible": True, "evidence_refs": ["fixture:" + source],
            "provenance": ["CURRENT_OBSERVATION"], "body_schema_generation": "fixture-body",
            "native_support": 0.5, "ordinary_evidence": ordinary or {},
        }
        if route is not None:
            ctx["route"] = route
        return {"candidate_ref": source + ":" + cap, "source_name": source, "capability": cap,
                "params": params, "policy_context": ctx}
    return {
        "schema_version": 1, "physiology": phys,
        "drift": {"energy": -0.002, "fatigue": 0.002, "integrity": -0.0002, "stimulation": -0.002},
        "active_ticks": 11, "observations": [], "remembered_evidence": [],
        "world_entities": [], "affordance_beliefs": [], "transition_models": [],
        "body_capabilities": {
            "IDLE": {"status": "available", "body_schema_generation": "fixture-body"},
            "APPROACH": {"status": "available", "body_schema_generation": "fixture-body"},
            "CHARGE": {"status": "available", "body_schema_generation": "fixture-body"},
        },
        "d014e_constraints": {"max_route_steps": 8},
        "effect_branches": {
            "IDLE": [{"effect": {}}],
            "APPROACH": [{"effect": {"energy": -0.08, "fatigue": 0.04}}],
            "CHARGE": [{"effect": {"energy": 0.04}}],
        },
        "opportunities": [{"opportunity_ref": "resource:r0", "policy_visible": True, "kind": "resource"}],
        "recovery_focus": "energy",
        "candidates": [
            candidate("base_arbitration", "IDLE", {}, ordinary={"regulatory_gain": 0.1}),
            candidate("world_model", "CHARGE", {"toward": "resource"}, route={
                "policy_visible": True, "opportunity_ref": "resource:r0", "estimated_distance": 1.0,
                "distance_support_upper_bound": 1.0, "progress_per_step": 1.0,
                "terminal_capability": "CHARGE", "terminal_effect_branches": [{"effect": {"energy": 0.04}}],
            }, ordinary={"regulatory_gain": 0.8}),
            candidate("memory", "APPROACH", {"toward": "resource"}, ordinary={"regulatory_gain": 0.2}),
        ],
    }

def test_replay_and_route():
    first = evaluate(base_state())
    second = evaluate(base_state())
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first["selected"]["capability"] == "CHARGE"
    assert first["selected"]["route"]["route_kind"] == "DIRECT_APPROACH_THEN_TERMINAL"
    assert first["selected"]["route"]["time_to_benefit"] == [2, 2]

def test_unknown_is_neutral_and_hidden_truth_is_rejected():
    payload = base_state()
    payload["candidates"][1]["policy_context"]["route"] = {"policy_visible": True, "opportunity_ref": "missing"}
    result = evaluate(payload)
    assert result["resolution"] in {"UNKNOWN_NEUTRAL_TIE_BREAK", "ORDINARY_ENDOGENOUS_TIE_BREAK"}
    payload["candidates"][0]["policy_context"]["hidden_partner_id"] = "bad"
    try:
        evaluate(payload)
    except ContractError as exc:
        assert str(exc) == "hidden_truth_not_allowed"
    else:
        raise AssertionError("hidden truth accepted")

def test_dedup_and_incomparability():
    payload = base_state()
    payload["candidates"].append(dict(payload["candidates"][0], source_name="routine_habit"))
    result = evaluate(payload)
    assert len(result["deduplicated_candidates"]) == 3
    assert result["unknown_neutral"] is True
