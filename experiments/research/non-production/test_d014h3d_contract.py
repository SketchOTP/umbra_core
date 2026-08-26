import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from d014h3d_selector import evaluate
from test_d014h3d_selector import base_state

SOURCES = (
    "base_arbitration", "critical_recovery", "manipulation", "routine_habit",
    "development", "memory", "social", "world_model", "temporal",
    "individuality", "dormant_capability", "final_safety",
)

def test_all_required_source_classes_are_accepted():
    payload = base_state()
    for index, source in enumerate(SOURCES):
        candidate = dict(payload["candidates"][0])
        candidate["source_name"] = source
        candidate["candidate_ref"] = source
        candidate["params"] = {"source_index": index}
        payload["candidates"].append(candidate)
        payload["body_capabilities"]["IDLE"] = {"status": "available", "body_schema_generation": "fixture-body"}
    result = evaluate(payload)
    assert result["status"] == "SELECTED"
    assert {row["source_name"] for row in result["annotated_candidates"]} == set(SOURCES)

def test_known_infeasible_and_no_safe_are_explicit():
    payload = base_state()
    payload["physiology"]["energy"]["value"] = 0.051
    payload["candidates"] = [{
        "source_name": "base_arbitration",
        "capability": "APPROACH",
        "params": {},
        "policy_context": {
            "policy_visible": True, "evidence_refs": ["fixture:bad"],
            "provenance": ["CURRENT_OBSERVATION"],
            "body_schema_generation": "fixture-body",
        },
    }]
    result = evaluate(payload)
    assert result["deduplicated_candidates"][0]["feasibility"] == "KNOWN_INFEASIBLE"
    assert result["resolution"] == "NO_SAFE_ACTION"

def test_body_invalidation_and_overflow_fail_closed():
    payload = base_state()
    payload["body_capabilities"]["CHARGE"]["status"] = "dormant"
    result = evaluate(payload)
    assert all(row["capability"] != "CHARGE" for row in result["annotated_candidates"])
    overflow = base_state()
    overflow["candidates"] = overflow["candidates"] * 50
    assert evaluate(overflow)["status"] == "OVERFLOW"

def test_unknown_route_never_becomes_infeasible():
    payload = base_state()
    payload["candidates"][1]["policy_context"]["route"] = {
        "policy_visible": True, "opportunity_ref": "not-present"
    }
    result = evaluate(payload)
    charge = next(row for row in result["deduplicated_candidates"] if row["capability"] == "CHARGE")
    assert charge["feasibility"] == "UNKNOWN"
    assert result["unknown_neutral"] is True
