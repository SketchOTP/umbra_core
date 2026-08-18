from umbra_core.arbitration import ArbitrationState, Arbitrator, Candidate
from umbra_core.physiology import BOUNDS, DEFAULT_DRIFT, OUTCOME_EFFECTS, Physiology
from umbra_core.util import SeededRNG


def test_action_safe_now_but_unsafe_at_next_decision_is_rejected():
    physiology = Physiology(energy=0.055, fatigue=0.20, integrity=0.90, stimulation=0.55)
    candidate = Candidate("APPROACH", {"toward": "resource"})

    immediate = physiology.energy + OUTCOME_EFFECTS["APPROACH"]["energy"]
    next_decision = immediate + DEFAULT_DRIFT["energy"]

    assert immediate >= BOUNDS["energy"].critical_low
    assert next_decision < BOUNDS["energy"].critical_low
    assert Arbitrator._introduces_critical_boundary(candidate, physiology, ignore="energy")


def test_next_decision_guard_covers_all_homeostatic_variables():
    cases = (
        ("energy", 0.055, "APPROACH"),
        ("fatigue", 0.948, "IDLE"),
        ("integrity", 0.0501, "MOVE"),
        ("stimulation", 0.051, "IDLE"),
    )

    for name, value, capability in cases:
        values = {"energy": 0.70, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55}
        values[name] = value
        physiology = Physiology(**values)
        assert not BOUNDS[name].critical_violation(value)
        assert Arbitrator._introduces_critical_boundary(
            Candidate(capability, {}), physiology
        )


def test_scripted_final_commit_path_uses_safe_fallback():
    physiology = Physiology(energy=0.055, fatigue=0.20, integrity=0.90, stimulation=0.55)
    arbitrator = Arbitrator(ArbitrationState(mode="scripted"))

    chosen = arbitrator.select(physiology, [], 1, SeededRNG(13034))

    assert chosen.capability == "IDLE"
    assert chosen.params["source"] == "no_safe_action"
    assert arbitrator._introduces_critical_boundary(chosen, physiology)
