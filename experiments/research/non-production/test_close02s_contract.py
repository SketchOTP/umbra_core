from close02s_contract import evaluate_contract


def candidate(capability, source, **params):
    return {"capability": capability, "params": params, "source": source}


def eligible(candidate_value, *, dimensions=()):
    return {**candidate_value, "authority_valid": True, "immediately_safe": True, "regulatory_dimensions": list(dimensions)}


def keys(result):
    return [(item["capability"], item["params"]) for item in result["eligible"]]


def test_native_intent_is_not_erased_by_base_motor_candidate():
    result = evaluate_contract(intent_candidates=[eligible(candidate("CHARGE", "development"), dimensions=("energy",))], base_candidates=[eligible(candidate("ORIENT", "base"))], preventive_signal=set(), hard_recovery=False)
    assert result["state"] == "STATE_2_INTENT_ACTIVE_NO_REGULATORY_ATTENTION"
    assert keys(result) == [("CHARGE", {})]


def test_preventive_lane_readds_only_regulatory_base_action():
    result = evaluate_contract(intent_candidates=[eligible(candidate("APPROACH", "development"), dimensions=("stimulation",))], base_candidates=[eligible(candidate("REST", "base"), dimensions=("fatigue",)), eligible(candidate("ORIENT", "base"))], preventive_signal={"fatigue"}, hard_recovery=False)
    assert result["state"] == "STATE_3_INTENT_ACTIVE_PREVENTIVE_REGULATORY_ATTENTION"
    assert keys(result) == [("APPROACH", {}), ("REST", {})]


def test_no_useful_preventive_action_is_no_safe_action():
    result = evaluate_contract(intent_candidates=[eligible(candidate("INSPECT", "memory"))], base_candidates=[eligible(candidate("ORIENT", "base"))], preventive_signal={"fatigue"}, hard_recovery=False)
    assert result["no_safe_action"] is False
    assert keys(result) == [("INSPECT", {})]


def test_hard_recovery_excludes_optional_intent():
    result = evaluate_contract(intent_candidates=[eligible(candidate("INSPECT", "development"))], base_candidates=[eligible(candidate("ORIENT", "base"))], preventive_signal={"fatigue"}, hard_recovery=True, hard_recovery_candidates=[eligible(candidate("REST", "recovery"), dimensions=("fatigue",))])
    assert keys(result) == [("REST", {})]


def test_equivalent_intents_dedupe_without_source_vote():
    result = evaluate_contract(intent_candidates=[eligible(candidate("CHARGE", "development"), dimensions=("energy",)), eligible(candidate("CHARGE", "memory"), dimensions=("energy",))], base_candidates=[], preventive_signal=set(), hard_recovery=False)
    assert result["intent_count"] == 1
    assert result["source_priority"] is False


def test_conflicting_intents_are_preserved_and_source_order_invariant():
    a = [eligible(candidate("CHARGE", "development")), eligible(candidate("INSPECT", "memory"))]
    b = list(reversed(a))
    first = evaluate_contract(intent_candidates=a, base_candidates=[], preventive_signal=set(), hard_recovery=False)
    second = evaluate_contract(intent_candidates=b, base_candidates=[], preventive_signal=set(), hard_recovery=False)
    assert keys(first) == keys(second)
    assert first["intent_conflict"] is True
    assert first["selection_authority"] == "existing_action_level_arbitration"


def test_unsafe_intent_does_not_enter_eligible_set():
    result = evaluate_contract(intent_candidates=[{**candidate("CHARGE", "development"), "authority_valid": False}], base_candidates=[eligible(candidate("REST", "base"), dimensions=("fatigue",))], preventive_signal={"fatigue"}, hard_recovery=False)
    assert keys(result) == [("REST", {})]


def test_no_intent_preventive_signal_keeps_only_matching_base_action():
    result = evaluate_contract(intent_candidates=[], base_candidates=[eligible(candidate("REST", "base"), dimensions=("fatigue",)), eligible(candidate("MOVE", "base"))], preventive_signal={"fatigue"}, hard_recovery=False)
    assert keys(result) == [("REST", {})]


def test_all_unsafe_candidates_produce_no_safe_action():
    result = evaluate_contract(intent_candidates=[{**candidate("INSPECT", "memory"), "authority_valid": False}], base_candidates=[{**candidate("ORIENT", "base"), "immediately_safe": False}], preventive_signal=set(), hard_recovery=False)
    assert result["no_safe_action"] is True
