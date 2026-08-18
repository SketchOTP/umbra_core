from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.governance import Governance
from umbra_core.physiology import BOUNDS, DEFAULT_DRIFT, Physiology
from umbra_core.util import SeededRNG


def test_verified_failure_branch_is_projected_with_next_decision_drift():
    physiology = Physiology(energy=0.052, fatigue=0.66, integrity=0.93, stimulation=0.62)
    governance = Governance()
    success = governance.verify_outcome("REST", {"ok_raw": True, "reason": "ok"})
    failure = governance.verify_outcome(
        "REST", {"ok_raw": False, "reason": "not_at_rest"}
    )

    assert success.physiology_effects["energy"] == 0.015
    assert failure.physiology_effects["energy"] == -0.003
    assert (
        physiology.energy
        + success.physiology_effects["energy"]
        + DEFAULT_DRIFT["energy"]
        >= BOUNDS["energy"].critical_low
    )
    assert (
        physiology.energy
        + failure.physiology_effects["energy"]
        + DEFAULT_DRIFT["energy"]
        < BOUNDS["energy"].critical_low
    )
    assert Arbitrator._introduces_critical_boundary(
        Candidate("REST", {"toward": "rest"}), physiology
    )


def test_unsafe_idle_is_explicit_no_safe_action():
    physiology = Physiology(energy=0.052, fatigue=0.66, integrity=0.93, stimulation=0.62)
    arbitrator = Arbitrator()

    chosen = arbitrator.select(
        physiology,
        [{"kind": "rest", "relative_direction": 0.0, "estimated_distance": 2.0}],
        1,
        SeededRNG(13013),
    )

    assert chosen.params["source"] == "no_safe_action"
    assert Arbitrator._introduces_critical_boundary(chosen, physiology)


def test_not_at_rest_denial_is_retained_for_existing_recovery_feedback():
    arbitrator = Arbitrator()
    arbitrator.note_outcome("CHARGE", False, "not_at_rest", target_kind="resource")

    assert arbitrator.state.last_verified_denial == {
        "capability": "CHARGE",
        "reason": "not_at_rest",
        "target_kind": "resource",
    }
