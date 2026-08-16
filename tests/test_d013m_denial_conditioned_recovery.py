"""D-013M non-formal regression for verified recovery denials."""

from umbra_core.arbitration import ArbitrationState, Arbitrator
from umbra_core.physiology import Physiology
from umbra_core.util import SeededRNG


def _state() -> Physiology:
    return Physiology(
        energy=0.2395,
        fatigue=0.456,
        integrity=0.984,
        stimulation=0.109,
        drift_enabled=False,
    )


def _resource_observation() -> list[dict[str, object]]:
    return [
        {
            "kind": "resource",
            "relative_direction": 0.0,
            "estimated_distance": 1.4,
            "confidence": 1.0,
            "uncertainty": 0.0,
        }
    ]


def test_verified_denial_prevents_immediate_equivalent_charge_repeat():
    arbitrator = Arbitrator()
    observations = _resource_observation()

    first = arbitrator.select(_state(), observations, 138, SeededRNG(13013))
    assert first.capability == "CHARGE"

    arbitrator.note_outcome(
        "CHARGE", False, "not_at_resource", target_kind="resource"
    )
    second = arbitrator.select(_state(), observations, 139, SeededRNG(13013))

    assert second.capability == "APPROACH"
    assert second.params["toward"] == "resource"
    assert arbitrator.state.retry_counts["CHARGE"] == 1


def test_corrective_verified_outcome_reopens_charge_opportunity():
    arbitrator = Arbitrator()
    observations = _resource_observation()

    arbitrator.select(_state(), observations, 138, SeededRNG(13013))
    arbitrator.note_outcome(
        "CHARGE", False, "not_at_resource", target_kind="resource"
    )
    corrective = arbitrator.select(_state(), observations, 139, SeededRNG(13013))
    assert corrective.capability == "APPROACH"

    arbitrator.note_outcome("APPROACH", True, "ok", target_kind="resource")
    next_recovery = arbitrator.select(_state(), observations, 140, SeededRNG(13013))

    assert next_recovery.capability == "CHARGE"
    assert arbitrator.state.last_verified_denial is None


def test_denial_state_survives_arbitration_snapshot_round_trip():
    arbitrator = Arbitrator()
    arbitrator.note_outcome(
        "CHARGE", False, "not_at_affordance", target_kind="resource"
    )

    restored = Arbitrator(ArbitrationState.from_state(arbitrator.state.to_state()))

    assert restored.state.last_verified_denial == {
        "capability": "CHARGE",
        "reason": "not_at_affordance",
        "target_kind": "resource",
    }
