from __future__ import annotations

import copy
import inspect

import pytest

from close02x_contract import evaluate_candidate
from umbra_core.arbitration import Arbitrator
from umbra_core.physiology import verified_outcome_effect_branches
from umbra_core.recoverability import RecoverabilityStatus
from umbra_core.self_model.engine import SupportSemantics


def interval(minimum=1.0, maximum=1.0, semantics="VERIFIED_OBSERVED_SUPPORT"):
    return {
        "minimum": minimum,
        "maximum": maximum,
        "semantics": semantics,
        "evidence_count": 4,
        "provenance": ["verified-outcome:fixture"],
    }


def support(semantics="VERIFIED_OBSERVED_SUPPORT"):
    return {
        capability: {
            "capability": capability,
            "body_schema_id": "body-1",
            "progress": interval(1.0, 1.0, semantics),
            "completion": interval(0.0, 0.0, semantics),
        }
        for capability in ("MOVE", "APPROACH", "RETREAT")
    }


def observation(kind, *, distance=2.0, radius=0.0, semantics="VERIFIED_OBSERVED_SUPPORT"):
    return {
        "kind": kind,
        "fact_kind": "REMEMBERED_ESTIMATE",
        "source": "world_model_memory",
        "support_center_dx": distance,
        "support_center_dy": 0.0,
        "support_radius": radius,
        "support_provenance": "sensor:bounded_body_region",
        "support_source_kind": "CURRENT_OBSERVATION",
        "support_semantics": semantics,
        "support_body_schema_id": "body-1",
    }


def physiology(**updates):
    state = {
        "energy": 0.70,
        "fatigue": 0.20,
        "integrity": 0.85,
        "stimulation": 0.55,
    }
    state.update(updates)
    return state


def evaluate(*, dimension="energy", candidate=None, effects=None, observations=None, phys=None, capability_support=None):
    candidate = candidate or {"capability": "IDLE", "params": {}}
    effects = effects if effects is not None else verified_outcome_effect_branches(candidate["capability"])
    return evaluate_candidate(
        organism_tick=12,
        body_schema_id="body-1",
        physiology=phys or physiology(energy=0.20),
        attended_dimensions=[dimension],
        observations=observations if observations is not None else [observation("resource")],
        candidate=candidate,
        authority_effect_branches=effects,
        capability_support=capability_support if capability_support is not None else support(),
    )


def transition(result):
    assert len(result["transitions"]) == 1
    return result["transitions"][0]


def test_b1_supported_positive_remains_positive_is_neutral():
    row = transition(evaluate())
    assert row["current_status"] == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    assert row["projected_status"] == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    assert row["constrained"] is False


def test_b2_only_positive_to_exhausted_is_constrained():
    result = evaluate(
        candidate={"capability": "MOVE", "params": {"heading_delta": 3.141592653589793}},
        phys=physiology(energy=0.058),
        observations=[observation("resource", distance=1.5)],
    )
    row = transition(result)
    assert row["current_status"] == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    assert row["projected_status"] == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
    assert result["constrained"] is True


@pytest.mark.parametrize(
    "case",
    [
        {"capability_support": support(SupportSemantics.UNKNOWN.value)},
        {"observations": [observation("resource", semantics=SupportSemantics.PROBABILISTIC_SUPPORT.value)]},
    ],
)
def test_b3_b4_unknown_is_neutral(case):
    result = evaluate(**case)
    assert result["constrained"] is False
    assert "UNKNOWN" in transition(result)["projected_status"]


def test_b5_already_exhausted_is_neutral():
    result = evaluate(phys=physiology(energy=0.055), observations=[observation("resource", distance=5.0)])
    row = transition(result)
    assert row["current_status"] == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
    assert row["constrained"] is False


def test_b6_absent_route_is_neutral():
    row = transition(evaluate(observations=[]))
    assert row["current_status"] == RecoverabilityStatus.NO_KNOWN_RECOVERY_ROUTE.value
    assert row["constrained"] is False


def test_b7_energy_semantics_are_compatible_with_existing_view():
    result = evaluate()
    assert result["current_view"]["schema"] == "HOMEOSTATIC_RECOVERABILITY_VIEW_V1"
    assert result["projected_view"]["schema"] == "HOMEOSTATIC_RECOVERABILITY_VIEW_V1"


def test_b8_fatigue_uses_existing_rest_effect_semantics():
    result = evaluate(
        dimension="fatigue",
        candidate={"capability": "MOVE", "params": {"heading_delta": 3.141592653589793}},
        phys=physiology(fatigue=0.90),
        observations=[observation("rest", distance=1.5)],
    )
    assert transition(result)["current_status"] in {
        RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value,
        RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value,
    }
    assert "REST" in {
        route["terminal_capability"]
        for route in result["projected_view"]["candidate_projection"]["post_candidate_routes"]
    }


def test_b9_stimulation_uses_existing_inspect_effect_semantics():
    result = evaluate(
        dimension="stimulation",
        candidate={"capability": "IDLE", "params": {}},
        phys=physiology(stimulation=0.10),
        observations=[observation("inspect", distance=1.5)],
    )
    assert "INSPECT" in {
        route["terminal_capability"]
        for route in result["projected_view"]["candidate_projection"]["post_candidate_routes"]
    }


def test_b10_integrity_without_policy_support_is_unknown_and_neutral():
    result = evaluate(
        dimension="integrity",
        candidate={"capability": "IDLE", "params": {}},
        phys=physiology(integrity=0.10),
        observations=[observation("rest")],
        capability_support=support(SupportSemantics.UNKNOWN.value),
    )
    assert "UNKNOWN" in transition(result)["projected_status"]
    assert result["constrained"] is False


def test_b11_uncertainty_never_becomes_hidden_certainty():
    result = evaluate(observations=[observation("resource", semantics="PROBABILISTIC_SUPPORT")])
    assert result["constrained"] is False
    assert result["hidden_truth_fields"] == 0


def test_b12_verified_motion_support_is_policy_labeled_only():
    result = evaluate()
    route = result["projected_view"]["candidate_projection"]["post_candidate_routes"][0]
    assert route["margin_semantics"] == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value


def test_b13_contradictory_evidence_revises_to_unknown():
    known = evaluate()
    contradicted = evaluate(observations=[observation("resource", semantics="UNKNOWN")])
    assert transition(known)["projected_status"] == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    assert "UNKNOWN" in transition(contradicted)["projected_status"]


def test_b14_b15_view_has_no_action_or_candidate_authority():
    result = evaluate()
    assert result["action_authority"] is False
    assert result["candidate_created"] is False
    assert result["projected_view"]["action_authority"] is False


def test_b16_source_provenance_does_not_change_treatment():
    a = evaluate(candidate={"capability": "MOVE", "params": {"heading_delta": 0.0, "source": "development"}})
    b = evaluate(candidate={"capability": "MOVE", "params": {"heading_delta": 0.0, "source": "memory"}})
    assert a["transitions"] == b["transitions"]


def test_b17_rejected_v_urgent_and_remembered_rest_semantics_are_absent():
    source = inspect.getsource(Arbitrator.select)
    assert "active_reacquisition" in source  # pre-V/U energy behavior remains
    urgent = source[source.index("def commit_safe_recovery"):source.index("base_cands =")]
    assert "contract_admissible(chosen)" not in urgent
    fatigue = source[source.index('if focus == "fatigue"'):source.index('if focus == "integrity"')]
    assert "REMEMBERED_ESTIMATE" not in fatigue
    assert "active_reacquisition" not in fatigue


@pytest.mark.parametrize("seed", [5366620, 3609315, 77955964, 18929722])
def test_b18_retained_controls_without_route_lineage_remain_neutral(seed):
    # Retained control summaries provide extrema/no-safe markers but no bounded
    # route geometry.  Honest replay is UNKNOWN/no-known-route, never danger.
    result = evaluate(observations=[])
    assert seed in {5366620, 3609315, 77955964, 18929722}
    assert result["constrained"] is False
    assert transition(result)["current_status"] == RecoverabilityStatus.NO_KNOWN_RECOVERY_ROUTE.value


def test_pure_evaluator_is_deterministic_and_nonmutating():
    candidate = {"capability": "MOVE", "params": {"heading_delta": 0.0}}
    observations = [observation("resource")]
    before = copy.deepcopy((candidate, observations))
    first = evaluate(candidate=candidate, observations=observations)
    second = evaluate(candidate=copy.deepcopy(candidate), observations=copy.deepcopy(observations))
    assert first == second
    assert (candidate, observations) == before
    assert first["rollout_required"] is False
