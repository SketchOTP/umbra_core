import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from d014h3i_selector import ContractError, canonical_bytes, evaluate, behavioral_candidate_key

def base_state():
    phys = {n: {"value": v, "lower": 0.0, "upper": 1.0, "critical_low": 0.05, "critical_high": 0.95}
            for n, v in (("energy", 0.20), ("fatigue", 0.20), ("integrity", 0.90), ("stimulation", 0.40))}
    def candidate(ref, source, cap, params, route=None, scores=None):
        ctx = {"policy_visible": True, "evidence_refs": ["fixture:" + ref],
               "provenance": ["CURRENT_OBSERVATION"], "body_schema_generation": "fixture-body",
               "native_support": 0.5, "candidate_scores": scores or {}}
        if route is not None: ctx["route"] = route
        return {"candidate_ref": ref, "source_name": source, "capability": cap,
                "params": params, "policy_context": ctx}
    return {
        "schema_version": 2, "physiology": phys,
        "drift": {"energy": -0.002, "fatigue": 0.002, "integrity": -0.0002, "stimulation": -0.002},
        "active_ticks": 11, "observations": [], "remembered_evidence": [],
        "world_entities": [], "affordance_beliefs": [], "transition_models": [],
        "body_capabilities": {"IDLE": {"status": "available", "body_schema_generation": "fixture-body"},
          "APPROACH": {"status": "available", "body_schema_generation": "fixture-body"},
          "CHARGE": {"status": "available", "body_schema_generation": "fixture-body"}},
        "d014e_constraints": {"max_route_steps": 8},
        "effect_branches": {"IDLE": [{"effect": {"energy": 0.0, "fatigue": 0.0, "integrity": 0.0, "stimulation": 0.0}}],
          "APPROACH": [{"effect": {"energy": -0.08, "fatigue": 0.04}}],
          "CHARGE": [{"effect": {"energy": 0.04}}]},
        "effect_branches_exact": {"idle-ref": [{"effect": {"energy": 0.0, "fatigue": 0.0, "integrity": 0.0, "stimulation": 0.0}}],
          "charge-ref": [{"effect": {"energy": 0.04}}],
          "approach-ref": [{"effect": {"energy": -0.08, "fatigue": 0.04}}]},
        "hard_admissibility_exact": {},
        "opportunities": [{"opportunity_ref": "resource:r0", "policy_visible": True, "kind": "resource"}],
        "recovery_focus": "energy",
        "candidates": [
          candidate("idle-ref", "base_arbitration", "IDLE", {}, scores={"expected_regulatory_gain": 0.1}),
          candidate("charge-ref", "world_model", "CHARGE", {"toward": "resource"}, route={
            "policy_visible": True, "opportunity_ref": "resource:r0", "estimated_distance": 1.0,
            "distance_support_upper_bound": 1.0, "progress_per_step": 1.0,
            "terminal_capability": "CHARGE", "terminal_effect_branches": [{"effect": {"energy": 0.04}}]},
            scores={"expected_regulatory_gain": 0.8}),
          candidate("approach-ref", "memory", "APPROACH", {"toward": "resource"},
                    scores={"expected_regulatory_gain": 0.2})]}

def test_replay_route_and_production_scores():
    first, second = evaluate(base_state()), evaluate(base_state())
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first["selected"]["capability"] == "APPROACH"
    charge = next(row for row in first["annotated_candidates"] if row["capability"] == "CHARGE")
    assert charge["route"]["route_kind"] == "DIRECT_APPROACH_THEN_TERMINAL"
    assert charge["route"]["time_to_benefit"] == [2, 2]
    assert first["selected"]["ordinary_evidence"][0] == 0.2

def test_provenance_does_not_change_behavioral_identity():
    left = {"capability": "APPROACH", "params": {"toward": "resource", "candidate_ref": "runtime:1",
             "proposal_id": "proposal-a", "source_name": "memory"}}
    right = {"capability": "APPROACH", "params": {"toward": "resource", "candidate_ref": "runtime:2",
             "proposal_id": "proposal-b", "source_name": "routine"}}
    assert behavioral_candidate_key(left) == behavioral_candidate_key(right)
    different = dict(right, params={"toward": "rest", "step": 2.0})
    assert behavioral_candidate_key(left) != behavioral_candidate_key(different)

def test_unknown_is_neutral_and_hidden_truth_is_rejected():
    payload = base_state()
    payload["candidates"][1]["policy_context"]["route"] = {"policy_visible": True, "opportunity_ref": "missing"}
    result = evaluate(payload)
    assert result["resolution"] in {"UNKNOWN_NEUTRAL_TIE_BREAK", "ORDINARY_ENDOGENOUS_TIE_BREAK"}
    payload["candidates"][0]["policy_context"]["hidden_partner_id"] = "bad"
    try: evaluate(payload)
    except ContractError as exc: assert str(exc) == "hidden_truth_not_allowed"
    else: raise AssertionError("hidden truth accepted")

def test_dedup_and_exact_branch_aliasing_are_separate():
    payload = base_state()
    payload["candidates"].append(dict(payload["candidates"][0], candidate_ref="idle-other", source_name="routine_habit"))
    result = evaluate(payload)
    assert len(result["deduplicated_candidates"]) == 3
    assert result["unknown_neutral"] is True


def test_no_safe_is_structured_and_never_falls_back():
    payload = base_state()
    payload["candidates"] = [payload["candidates"][1]]
    payload["candidates"][0]["policy_context"]["route"] = {
        "policy_visible": True, "opportunity_ref": "missing"
    }
    result = evaluate(payload)
    assert result["selected"] is None
    assert result["resolution"] == "NO_SAFE_ACTION"
    assert result["unknown_neutral"] is True

def test_hard_authority_inadmissibility_is_excluded_before_ranking():
    payload = base_state()
    bad = dict(payload["candidates"][0])
    bad["candidate_ref"] = "hard-bad"
    bad["params"] = {"source": "authoritative-unsafe"}
    payload["candidates"].append(bad)
    payload["effect_branches_exact"]["hard-bad"] = [{
        "energy": -0.20, "fatigue": 0.0, "integrity": 0.0, "stimulation": 0.0
    }]
    result = evaluate(payload)
    assert any(row["candidate_ref"] == "hard-bad" for row in result["hard_rejected_candidates"])
    assert all(row["candidate_ref"] != "hard-bad" for row in result["non_dominated"])
