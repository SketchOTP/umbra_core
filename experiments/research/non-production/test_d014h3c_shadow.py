import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from d014h3c_shadow import evaluate, canonical_bytes


def state():
    phys = {
        name: {"value": value, "critical_low": 0.05, "critical_high": 0.95}
        for name, value in (("energy", 0.2), ("fatigue", 0.2), ("integrity", 0.9), ("stimulation", 0.4))
    }
    return {
        "physiology": phys,
        "drift": {"energy": -0.002, "fatigue": 0.002, "integrity": -0.0002, "stimulation": -0.002},
        "effect_branches": {
            "IDLE": [{"effect": {}}],
            "CHARGE": [{"effect": {"energy": 0.1}}],
            "MOVE": [{"effect": {"energy": -0.04, "fatigue": 0.02}}],
        },
        "candidates": [
            {"candidate_ref": "idle", "capability": "IDLE", "params": {}, "policy_context": {"policy_visible": True, "existing_endogenous_rank": 2}},
            {"candidate_ref": "charge", "capability": "CHARGE", "params": {"toward": "resource"}, "policy_context": {"policy_visible": True, "existing_endogenous_rank": 1}},
            {"candidate_ref": "unknown", "capability": "MOVE", "params": {"step": 1.0}, "policy_context": {"policy_visible": True, "existing_endogenous_rank": 3}},
        ],
    }


def test_replay_is_byte_equal():
    first = evaluate(state())
    second = evaluate(state())
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first["production_authority"] is False


def test_full_vector_and_existing_order():
    result = evaluate(state())
    assert set(result["annotated_candidates"][0]["successor"]["branches"][0]["values"]) == {"energy", "fatigue", "integrity", "stimulation"}
    assert result["selected"]["candidate_ref"] == "charge"


def test_unknown_is_neutral_and_hidden_truth_rejected():
    payload = state()
    payload["candidates"][2]["policy_context"].pop("existing_endogenous_rank")
    result = evaluate(payload)
    assert result["resolution"] in {"UNKNOWN_TIE", "EXISTING_ENDOGENOUS_ORDER", "PARTIAL_ORDER_UNIQUE"}
    payload["candidates"][0]["policy_context"]["world_truth"] = "forbidden"
    try:
        evaluate(payload)
    except ValueError as exc:
        assert str(exc) == "hidden_truth_not_allowed"
    else:
        raise AssertionError("hidden truth accepted")
