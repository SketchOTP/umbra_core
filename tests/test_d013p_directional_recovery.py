"""D-013P non-formal cross-variable homeostatic recovery diagnostics."""

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import BOUNDS, OUTCOME_EFFECTS, Physiology
from umbra_core.util import SeededRNG


def _frozen_tick_270_state() -> Physiology:
    return Physiology(
        energy=0.4005,
        fatigue=0.318,
        integrity=1.0,
        stimulation=0.059,
        drift_enabled=False,
    )


def _frozen_tick_270_observations() -> list[dict[str, object]]:
    return [
        {
            "kind": "resource",
            "relative_direction": 2.9124692179511054,
            "estimated_distance": 7.92977127815662,
            "confidence": 0.45127743008413623,
            "uncertainty": 0.5487225699158638,
        },
        {
            "kind": "rest",
            "relative_direction": 0.007336005027014317,
            "estimated_distance": 0.7145560879738421,
            "confidence": 0.8692445145359504,
            "uncertainty": 0.13075548546404958,
        },
    ]


def test_pre_fix_boundary_is_reproduced_by_known_rest_effect():
    physiology = _frozen_tick_270_state()

    assert physiology.needs_recovery() == ["integrity", "stimulation"]
    assert physiology.active_recovery_needs() == ["stimulation"]
    rest_after = physiology.stimulation + OUTCOME_EFFECTS["REST"]["stimulation"]
    assert rest_after < BOUNDS["stimulation"].critical_low


def test_direction_aware_recovery_rejects_overshoot_focus_and_unsafe_rest():
    physiology = _frozen_tick_270_state()
    arbitrator = Arbitrator()
    arbitrator.state.recovery_focus = "integrity"

    chosen = arbitrator.select(
        physiology,
        _frozen_tick_270_observations(),
        270,
        SeededRNG(13013),
    )

    assert chosen.capability != "REST"
    assert arbitrator.state.recovery_focus == "stimulation"
    effects = OUTCOME_EFFECTS.get(chosen.capability, {})
    projected_stimulation = physiology.stimulation + effects.get("stimulation", 0.0)
    assert projected_stimulation >= BOUNDS["stimulation"].critical_low


def test_cross_variable_safety_guard_rejects_known_critical_crossing():
    physiology = _frozen_tick_270_state()
    arbitrator = Arbitrator()

    assert arbitrator._introduces_critical_boundary(
        Candidate("REST", {"toward": "rest"}), physiology
    )
    assert not arbitrator._introduces_critical_boundary(
        Candidate("MOVE", {"step": 1.0}), physiology
    )
