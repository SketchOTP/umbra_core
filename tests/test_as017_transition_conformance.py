from __future__ import annotations

from umbra_core.arbitration import Candidate
from umbra_core.embodiment import Embodiment
from umbra_core.governance import Governance, VerifiedOutcome, authority_effect_branches
from umbra_core.physiology import Physiology, project_verified_transition


def test_authoritative_prediction_matches_contextual_verified_execution() -> None:
    embodiment = Embodiment()
    candidate = Candidate("MOVE", {"heading": 0.0, "step": 1.0})
    initial = {"energy": 0.15, "fatigue": 0.70, "integrity": 0.90, "stimulation": 0.55}
    predicted = project_verified_transition(
        initial,
        authority_effect_branches(
            candidate,
            embodiment,
            None,
            resolve_params=lambda params: dict(params),
            physiology=initial,
        )[0],
    )
    physiology = Physiology(energy=0.15, fatigue=0.70, integrity=0.90, stimulation=0.55)
    Governance().apply_physiology(
        physiology,
        VerifiedOutcome(
            outcome_id="test-outcome",
            capability="MOVE",
            success=True,
            reason="ok",
            physiology_effects={"energy": -0.005, "fatigue": 0.004, "stimulation": 0.003},
            raw={"ok_raw": True, "reason": "ok"},
            verified=True,
        ),
    )
    physiology.tick_drift()
    assert predicted == physiology.as_dict()
