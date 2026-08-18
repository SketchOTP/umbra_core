
"""D-013T reserve-aware energy recovery semantics."""

from experiments.d012.formal_contract_v2 import normalize_trace_row
from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import BOUNDS, OUTCOME_EFFECTS, Physiology
from umbra_core.util import SeededRNG


def _resource(distance: float) -> list[dict[str, object]]:
    return [
        {
            "kind": "resource",
            "relative_direction": 0.0,
            "estimated_distance": distance,
            "confidence": 1.0,
            "uncertainty": 0.0,
        }
    ]


def _low_energy(energy: float) -> Physiology:
    return Physiology(
        energy=energy,
        fatigue=0.20,
        integrity=0.90,
        stimulation=0.55,
        drift_enabled=False,
    )


def test_exact_d013s_boundary_rejects_same_focus_critical_crossing():
    physiology = _low_energy(0.0525)
    arbitrator = Arbitrator()

    chosen = arbitrator.select(physiology, _resource(3.8), 414, SeededRNG(13013))

    assert chosen.capability == "IDLE"
    assert chosen.params["source"] == "no_safe_action"
    assert (
        physiology.energy + OUTCOME_EFFECTS["APPROACH"]["energy"]
        < BOUNDS["energy"].critical_low
    )


def test_safe_near_floor_approach_remains_eligible():
    physiology = _low_energy(0.0600)
    chosen = Arbitrator().select(physiology, _resource(1.6), 10, SeededRNG(13013))

    assert chosen.capability == "APPROACH"
    projected = physiology.energy + OUTCOME_EFFECTS["APPROACH"]["energy"]
    assert projected >= BOUNDS["energy"].critical_low


def test_energy_focus_signal_assistance_crossing_is_rejected():
    physiology = _low_energy(0.0505)
    chosen = Arbitrator().select(physiology, _resource(8.0), 414, SeededRNG(13013))

    assert chosen.capability != "SIGNAL_ASSISTANCE"
    projected = physiology.energy + OUTCOME_EFFECTS[chosen.capability].get("energy", 0.0)
    assert projected >= BOUNDS["energy"].critical_low


def test_energy_focus_generic_negative_energy_capability_is_guarded():
    physiology = _low_energy(0.0505)
    chosen = Arbitrator().select(physiology, [], 414, SeededRNG(13013))

    assert chosen.capability != "MOVE"
    projected = physiology.energy + OUTCOME_EFFECTS[chosen.capability].get("energy", 0.0)
    assert projected >= BOUNDS["energy"].critical_low


def test_safe_negative_energy_signal_remains_eligible():
    physiology = _low_energy(0.0600)
    chosen = Arbitrator().select(physiology, _resource(8.0), 414, SeededRNG(13013))

    assert chosen.capability == "SIGNAL_ASSISTANCE"
    projected = physiology.energy + OUTCOME_EFFECTS[chosen.capability]["energy"]
    assert projected >= BOUNDS["energy"].critical_low


def test_charge_remains_eligible_and_restorative():
    physiology = _low_energy(0.0505)
    chosen = Arbitrator().select(physiology, _resource(1.0), 414, SeededRNG(13013))

    assert chosen.capability == "IDLE"
    assert chosen.params["source"] == "no_safe_action"


def test_reachable_energy_recovery_preserves_progress_and_charge():
    physiology = _low_energy(0.0600)
    arbitrator = Arbitrator()

    approach = arbitrator.select(physiology, _resource(2.4), 10, SeededRNG(13013))
    assert approach.capability == "APPROACH"
    arbitrator.note_outcome("APPROACH", True, "ok", target_kind="resource")

    physiology.energy += OUTCOME_EFFECTS["APPROACH"]["energy"]
    charge = arbitrator.select(physiology, _resource(1.4), 11, SeededRNG(13013))
    assert charge.capability == "CHARGE"


def test_infeasible_distant_recovery_exposes_bounded_denial_without_idle_loop():
    physiology = _low_energy(0.0700)
    arbitrator = Arbitrator()
    choices = [
        arbitrator.select(physiology, _resource(8.0), tick, SeededRNG(13013))
        for tick in range(1, 13)
    ]

    assert all(choice.capability == "SIGNAL_ASSISTANCE" for choice in choices)
    assert all(choice.capability != "IDLE" for choice in choices)
    assert all(
        choice.params["reason"] == "energy_recovery_route_infeasible"
        for choice in choices
    )


def test_d013m_verified_denial_still_requires_corrective_approach():
    physiology = Physiology(
        energy=0.2395, fatigue=0.456, integrity=0.984, stimulation=0.109,
        drift_enabled=False,
    )
    arbitrator = Arbitrator()
    first = arbitrator.select(physiology, _resource(1.4), 138, SeededRNG(13013))
    assert first.capability == "CHARGE"
    arbitrator.note_outcome("CHARGE", False, "not_at_resource", target_kind="resource")

    corrective = arbitrator.select(physiology, _resource(1.4), 139, SeededRNG(13013))
    assert corrective.capability == "APPROACH"


def test_d013p_cross_variable_boundary_guard_remains_intact():
    physiology = Physiology(
        energy=0.4005, fatigue=0.318, integrity=1.0, stimulation=0.059,
        drift_enabled=False,
    )
    arbitrator = Arbitrator()
    arbitrator.state.recovery_focus = "integrity"

    chosen = arbitrator.select(
        physiology,
        [{"kind": "rest", "relative_direction": 0.0, "estimated_distance": 1.0}],
        270,
        SeededRNG(13013),
    )

    assert chosen.capability != "REST"
    assert (
        physiology.stimulation + OUTCOME_EFFECTS[chosen.capability].get("stimulation", 0.0)
        >= BOUNDS["stimulation"].critical_low
    )


def test_d013p_r1_diagnostic_only_state_is_not_recovery_target():
    physiology = Physiology(
        energy=0.95, fatigue=0.20, integrity=0.99, stimulation=0.55,
        drift_enabled=False,
    )
    arbitrator = Arbitrator()
    chosen = arbitrator.select(
        physiology,
        [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 1.0}],
        100,
        SeededRNG(13013),
    )

    assert arbitrator.state.recovery_focus == "diagnostic_only"
    assert chosen.capability != "CHARGE"


def test_d013r_authoritative_capability_provenance_remains_executable_source():
    row = {
        "event_types": ["physiology_drift", "proposal", "outcome_verified"],
        "selected_candidate": "CHARGE",
        "executed_capability": "REST",
        "governance": {"admitted": True, "capability": "REST", "stage_failed": None},
        "verified_outcome": {
            "action_issued": True,
            "verified": True,
            "capability": "REST",
            "success": False,
            "reason": "not_at_rest",
            "effects": {"energy": -0.003},
        },
    }

    normalized = normalize_trace_row(row)
    assert normalized["attempt_capability"] == "REST"
