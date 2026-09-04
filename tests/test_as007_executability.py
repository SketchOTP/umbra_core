from __future__ import annotations

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.embodiment import Embodiment, Habitat, HabitatFeature
from umbra_core.physiology import Physiology
from umbra_core.recoverability.contracts import (
    EXECUTABLE,
    NOT_EXECUTABLE,
    UNKNOWN_EXECUTABILITY,
)
from umbra_core.util import SeededRNG


def _fatigue() -> Physiology:
    return Physiology(energy=0.8, fatigue=0.8, integrity=0.9, stimulation=0.55)


def _rest_observation() -> list[dict[str, object]]:
    return [{"kind": "rest", "estimated_distance": 1.0, "relative_direction": 0.0}]


def test_initial_critical_terminal_choice_is_gated_by_readiness():
    def readiness(candidate: Candidate) -> str:
        return NOT_EXECUTABLE if candidate.capability == "REST" else EXECUTABLE

    arbitrator = Arbitrator()
    chosen = arbitrator.select(
        _fatigue(),
        _rest_observation(),
        1,
        SeededRNG(7001),
        candidate_executability=readiness,
    )

    assert chosen.capability != "REST"
    assert chosen.params.get("source") != "no_safe_action"


def test_unknown_terminal_readiness_fails_closed_without_other_action():
    arbitrator = Arbitrator()
    arbitrator.generate_candidates = lambda phys, observations, tick: [
        Candidate("REST", {"toward": "rest"})
    ]
    chosen = arbitrator.select(
        _fatigue(),
        _rest_observation(),
        1,
        SeededRNG(7002),
        candidate_executability=lambda candidate: UNKNOWN_EXECUTABILITY,
    )

    assert chosen.capability == "IDLE"
    assert chosen.params["source"] == "no_safe_action"


def test_ordinary_terminal_pool_excludes_not_ready_candidate():
    arbitrator = Arbitrator()
    arbitrator.generate_candidates = lambda phys, observations, tick: [
        Candidate("CHARGE", {"toward": "resource"}),
        Candidate("IDLE", {}),
    ]
    chosen = arbitrator.select(
        Physiology(energy=0.7, fatigue=0.2, integrity=0.9, stimulation=0.55),
        [],
        1,
        SeededRNG(7003),
        candidate_executability=lambda candidate: (
            NOT_EXECUTABLE if candidate.capability == "CHARGE" else EXECUTABLE
        ),
    )

    assert chosen.capability == "IDLE"


def test_embodiment_terminal_preflight_matches_terminal_predicates():
    embodiment = Embodiment(
        _habitat=Habitat(
            features=[
                HabitatFeature("rest", 0.0, 0.0, radius=1.2),
                HabitatFeature("resource", 0.0, 0.0, radius=1.2),
                HabitatFeature("inspect", 0.0, 0.0, radius=1.2),
            ]
        )
    )
    embodiment.body.x = embodiment.body.y = 0.0

    for capability, params in (
        ("REST", {"toward": "rest"}),
        ("CHARGE", {"toward": "resource"}),
        ("INSPECT", {"toward": "inspect"}),
    ):
        preflight = embodiment.preflight_primitive(capability, params)
        assert preflight is not None
        assert preflight["ok_raw"] is True

    embodiment.body.x = 10.0
    for capability, params in (
        ("REST", {"toward": "rest"}),
        ("CHARGE", {"toward": "resource"}),
        ("INSPECT", {"toward": "inspect"}),
    ):
        preflight = embodiment.preflight_primitive(capability, params)
        assert preflight is not None
        assert preflight["ok_raw"] is False
