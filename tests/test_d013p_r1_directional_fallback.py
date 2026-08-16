"""D-013P-R1 directional-recovery fallback closure tests."""

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import BOUNDS, OUTCOME_EFFECTS, Physiology
from umbra_core.util import SeededRNG


def _obs(kind: str) -> list[dict[str, object]]:
    return [
        {
            "kind": kind,
            "relative_direction": 0.0,
            "estimated_distance": 1.0,
            "confidence": 1.0,
            "uncertainty": 0.0,
        }
    ]


def _select(physiology: Physiology, observations: list[dict[str, object]]):
    arbitrator = Arbitrator()
    chosen = arbitrator.select(physiology, observations, 100, SeededRNG(13013))
    return arbitrator, chosen


def test_high_integrity_only_stays_diagnostic_not_active():
    physiology = Physiology(
        energy=0.70, fatigue=0.20, integrity=0.99, stimulation=0.55, drift_enabled=False
    )
    arbitrator, chosen = _select(physiology, _obs("rest"))

    assert physiology.needs_recovery() == ["integrity"]
    assert physiology.active_recovery_needs() == []
    assert arbitrator.state.recovery_focus == "diagnostic_only"
    assert not (
        arbitrator.state.recovery_focus == "integrity" and chosen.capability == "REST"
    )


def test_high_energy_only_stays_diagnostic_not_active():
    physiology = Physiology(
        energy=0.95, fatigue=0.20, integrity=0.90, stimulation=0.55, drift_enabled=False
    )
    arbitrator, chosen = _select(physiology, _obs("resource"))

    assert physiology.needs_recovery() == ["energy"]
    assert physiology.active_recovery_needs() == []
    assert arbitrator.state.recovery_focus == "diagnostic_only"
    assert not (
        arbitrator.state.recovery_focus == "energy" and chosen.capability == "CHARGE"
    )


def test_low_fatigue_only_stays_diagnostic_not_active():
    physiology = Physiology(
        energy=0.70, fatigue=0.02, integrity=0.90, stimulation=0.55, drift_enabled=False
    )
    arbitrator, chosen = _select(physiology, _obs("rest"))

    assert physiology.needs_recovery() == ["fatigue"]
    assert physiology.active_recovery_needs() == []
    assert arbitrator.state.recovery_focus == "diagnostic_only"
    assert not (
        arbitrator.state.recovery_focus == "fatigue" and chosen.capability == "REST"
    )


def test_low_energy_remains_active_recovery():
    physiology = Physiology(
        energy=0.20, fatigue=0.20, integrity=0.90, stimulation=0.55, drift_enabled=False
    )
    arbitrator, chosen = _select(physiology, _obs("resource"))

    assert physiology.active_recovery_needs() == ["energy"]
    assert arbitrator.state.recovery_focus == "energy"
    assert chosen.capability == "CHARGE"


def test_high_fatigue_remains_active_recovery():
    physiology = Physiology(
        energy=0.70, fatigue=0.80, integrity=0.90, stimulation=0.55, drift_enabled=False
    )
    arbitrator, chosen = _select(physiology, _obs("rest"))

    assert physiology.active_recovery_needs() == ["fatigue"]
    assert arbitrator.state.recovery_focus == "fatigue"
    assert chosen.capability == "REST"


def test_low_integrity_remains_active_recovery():
    physiology = Physiology(
        energy=0.70, fatigue=0.20, integrity=0.20, stimulation=0.55, drift_enabled=False
    )
    arbitrator, chosen = _select(physiology, _obs("rest"))

    assert physiology.active_recovery_needs() == ["integrity"]
    assert arbitrator.state.recovery_focus == "integrity"
    assert chosen.capability == "REST"


def test_low_stimulation_remains_active_recovery():
    physiology = Physiology(
        energy=0.70, fatigue=0.20, integrity=0.90, stimulation=0.20, drift_enabled=False
    )
    arbitrator, chosen = _select(physiology, _obs("inspect"))

    assert physiology.active_recovery_needs() == ["stimulation"]
    assert arbitrator.state.recovery_focus == "stimulation"
    assert chosen.capability == "INSPECT"


def test_high_stimulation_remains_active_calming_recovery():
    physiology = Physiology(
        energy=0.70, fatigue=0.20, integrity=0.90, stimulation=0.90, drift_enabled=False
    )
    arbitrator, chosen = _select(physiology, _obs("rest"))

    assert physiology.active_recovery_needs() == ["stimulation"]
    assert arbitrator.state.recovery_focus == "stimulation"
    assert chosen.capability == "REST"


def test_d013o_mixed_state_keeps_stimulation_and_rejects_unsafe_rest():
    physiology = Physiology(
        energy=0.4005, fatigue=0.318, integrity=1.0, stimulation=0.059, drift_enabled=False
    )
    arbitrator = Arbitrator()
    arbitrator.state.recovery_focus = "integrity"

    chosen = arbitrator.select(physiology, _obs("rest"), 270, SeededRNG(13013))

    assert physiology.needs_recovery() == ["integrity", "stimulation"]
    assert physiology.active_recovery_needs() == ["stimulation"]
    assert arbitrator.state.recovery_focus == "stimulation"
    assert chosen.capability != "REST"
    assert (
        physiology.stimulation + OUTCOME_EFFECTS.get(chosen.capability, {}).get("stimulation", 0.0)
        >= BOUNDS["stimulation"].critical_low
    )


def test_cross_variable_guard_rejects_rest_that_makes_stimulation_critical():
    physiology = Physiology(
        energy=0.4005, fatigue=0.318, integrity=1.0, stimulation=0.059, drift_enabled=False
    )
    arbitrator = Arbitrator()

    assert arbitrator._introduces_critical_boundary(
        Candidate("REST", {"toward": "rest"}), physiology
    )
    assert not arbitrator._introduces_critical_boundary(
        Candidate("MOVE", {"step": 1.0}), physiology
    )


def test_d013m_denial_still_requires_corrective_approach():
    physiology = Physiology(
        energy=0.2395, fatigue=0.456, integrity=0.984, stimulation=0.109, drift_enabled=False
    )
    observations = _obs("resource")
    arbitrator = Arbitrator()

    first = arbitrator.select(physiology, observations, 138, SeededRNG(13013))
    assert first.capability == "CHARGE"
    arbitrator.note_outcome(
        "CHARGE", False, "not_at_resource", target_kind="resource"
    )

    corrective = arbitrator.select(physiology, observations, 139, SeededRNG(13013))
    assert corrective.capability == "APPROACH"
    assert corrective.params["toward"] == "resource"
