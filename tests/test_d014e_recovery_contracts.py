from types import SimpleNamespace

from umbra_core.arbitration import Candidate
from umbra_core.physiology import Physiology
from umbra_core.recoverability.contracts import (
    ALLOW,
    CONSTRAIN,
    UNKNOWN,
    candidate_is_admissible,
    evaluate_recovery_contracts,
)


def _state(denial=None):
    return SimpleNamespace(last_verified_denial=denial)


def _candidate(capability="APPROACH", **params):
    return Candidate(capability, params)


def _eval(candidate, *, physiology=None, denial=None, observations=()):
    return evaluate_recovery_contracts(
        capability=candidate.capability,
        params=candidate.params,
        physiology=(physiology or Physiology()).as_dict(),
        observations=observations,
        arbitration_state=_state(denial),
    )


def test_fresh_verified_denial_constrains_only_that_attempt():
    row = _eval(
        _candidate("REST", toward="rest"),
        denial={"capability": "REST", "target_kind": "rest", "reason": "not_at_rest"},
    )
    statuses = {item["contract"]: item["status"] for item in row["contracts"]}
    assert statuses["E"] == CONSTRAIN
    assert row["hidden_truth_used"] is False


def test_new_observation_version_does_not_reveal_hidden_truth():
    row = _eval(
        _candidate("REST", toward="rest", observation_version="obs-2"),
        denial={
            "capability": "REST",
            "target_kind": "rest",
            "reason": "not_at_rest",
            "observation_version": "obs-1",
        },
    )
    assert next(item for item in row["contracts"] if item["contract"] == "E")["status"] == UNKNOWN


def test_failure_reserve_and_horizon_constrain_known_insufficient_paths():
    candidate = _candidate(
        "APPROACH",
        toward="resource",
        retry_reserve=1,
        required_attempts=2,
        time_to_critical=2,
        required_recovery_steps=3,
    )
    row = _eval(candidate, physiology=Physiology(energy=0.053))
    statuses = {item["contract"]: item["status"] for item in row["contracts"]}
    assert statuses["R"] == CONSTRAIN
    assert statuses["H"] == CONSTRAIN


def test_stalled_route_is_distinguished_from_unknown_progress():
    stalled = _eval(_candidate("APPROACH", toward="resource", progress_status="STALLED"))
    unknown = _eval(_candidate("APPROACH", toward="resource"))
    assert next(item for item in stalled["contracts"] if item["contract"] == "P")["status"] == CONSTRAIN
    assert next(item for item in unknown["contracts"] if item["contract"] == "P")["status"] == UNKNOWN


def test_unknown_contracts_never_veto_candidate():
    candidate = _candidate("IDLE")
    row = _eval(candidate)
    assert row["admissible"] is True
    assert row["unknown_contracts"]
    assert candidate_is_admissible(
        candidate,
        physiology=Physiology(),
        observations=(),
        arbitration_state=_state(),
    )


def test_contracts_preserve_full_vector_without_scalar_survival_score():
    row = _eval(_candidate("IDLE"))
    assert set(row["physiology"]) == {"energy", "fatigue", "integrity", "stimulation"}
    assert "health_score" not in row
    assert "survival_score" not in row

