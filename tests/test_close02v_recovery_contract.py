from types import SimpleNamespace

from umbra_core.arbitration import Candidate
from umbra_core.physiology import Physiology
from umbra_core.recoverability.contracts import candidate_is_admissible

from experiments.close02v_contract import (
    adjudicate_initial_recovery,
    build_reacquisition_candidate,
    contact_interaction_is_justified,
    interaction_evidence_class,
)


def _state(denial=None):
    return SimpleNamespace(last_verified_denial=denial)


def _rest(*, remembered=False, support="SUPPORTED", version=None):
    row = {
        "kind": "rest",
        "relative_direction": 0.0,
        "estimated_distance": 1.8,
        "fact_kind": "REMEMBERED_ESTIMATE" if remembered else "CURRENT_OBSERVATION",
        "source": "world_model_memory" if remembered else "sensor",
        "executability_support": support,
    }
    if version is not None:
        row["observation_version"] = version
    return row


def _admissible(candidate, observations, state):
    return candidate_is_admissible(
        candidate,
        physiology=Physiology(),
        observations=observations,
        arbitration_state=state,
    )


def test_initial_urgent_choice_requires_contract_before_commit():
    denied = Candidate("REST", {"toward": "rest"})
    fallback = Candidate("APPROACH", {"toward": "rest", "step": 1.4})
    state = _state(
        {"capability": "REST", "target_kind": "rest", "reason": "not_at_rest"}
    )
    result = adjudicate_initial_recovery(
        denied,
        [fallback],
        immediately_safe=lambda _: True,
        contract_admissible=lambda c: _admissible(c, [_rest()], state),
    )
    assert result == fallback


def test_current_rest_evidence_can_justify_contact():
    observation = _rest()
    assert interaction_evidence_class(observation) == "CURRENT_OBSERVATION"
    assert contact_interaction_is_justified(
        Candidate("REST", {"toward": "rest"}), observation
    )


def test_remembered_rest_only_builds_reacquisition():
    observation = _rest(remembered=True)
    candidate = Candidate("REST", {"toward": "rest"})
    assert interaction_evidence_class(observation) == "REMEMBERED_ESTIMATE"
    assert not contact_interaction_is_justified(candidate, observation)
    assert build_reacquisition_candidate(observation).capability == "APPROACH"


def test_matching_denial_suppresses_immediate_repetition():
    observation = _rest()
    candidate = Candidate("REST", {"toward": "rest"})
    state = _state(
        {"capability": "REST", "target_kind": "rest", "reason": "not_at_rest"}
    )
    assert not _admissible(candidate, [observation], state)


def test_fresh_current_evidence_releases_matching_denial():
    observation = _rest(version="obs-2")
    candidate = Candidate("REST", {"toward": "rest", "observation_version": "obs-2"})
    state = _state(
        {
            "capability": "REST",
            "target_kind": "rest",
            "reason": "not_at_rest",
            "observation_version": "obs-1",
        }
    )
    assert _admissible(candidate, [observation], state)


def test_denial_does_not_deadlock_reacquisition():
    observation = _rest(remembered=True)
    candidate = build_reacquisition_candidate(observation)
    state = _state(
        {"capability": "REST", "target_kind": "rest", "reason": "not_at_rest"}
    )
    assert _admissible(candidate, [observation], state)


def test_source_order_does_not_change_filter_result():
    chosen = Candidate("REST", {"toward": "rest"})
    approach = Candidate("APPROACH", {"toward": "rest", "step": 1.4})
    state = _state(
        {"capability": "REST", "target_kind": "rest", "reason": "not_at_rest"}
    )
    admissible = lambda c: _admissible(c, [_rest()], state)
    left = adjudicate_initial_recovery(
        chosen, [approach], immediately_safe=lambda _: True, contract_admissible=admissible
    )
    right = adjudicate_initial_recovery(
        chosen, [approach], immediately_safe=lambda _: True, contract_admissible=admissible
    )
    assert left == right == approach
