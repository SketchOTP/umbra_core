from types import MethodType

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology
from umbra_core.util import SeededRNG


def _resource(distance=10.0, support=12.0):
    return {
        "kind": "resource",
        "fact_kind": "CURRENT_OBSERVATION",
        "estimated_distance": distance,
        "relative_direction": 0.0,
        "distance_support_upper_bound": support,
    }


def _rest(distance=10.0):
    return {
        "kind": "rest",
        "estimated_distance": distance,
        "relative_direction": 0.0,
    }


def _commit_spy(arbitrator):
    calls = []
    original = arbitrator._commit

    def wrapped(self, candidate, tick):
        calls.append((candidate, tick))
        return original(candidate, tick)

    arbitrator._commit = MethodType(wrapped, arbitrator)
    return calls


def test_active_fatigue_recovery_uses_corridor_adjudication_once():
    arbitrator = Arbitrator()
    calls = _commit_spy(arbitrator)
    physiology = Physiology(energy=0.31, fatigue=0.70, integrity=0.90, stimulation=0.55)

    chosen = arbitrator.select(
        physiology,
        [_rest(), _resource()],
        1,
        SeededRNG(13015),
    )

    assert chosen.params["toward"] == "resource"
    assert chosen.params["source"] == "retry_aware_recovery_corridor"
    assert len(calls) == 1


def test_fatigue_recovery_remains_allowed_when_energy_corridor_is_ample():
    arbitrator = Arbitrator()
    calls = _commit_spy(arbitrator)
    physiology = Physiology(energy=0.80, fatigue=0.70, integrity=0.90, stimulation=0.55)

    chosen = arbitrator.select(
        physiology,
        [_rest(), _resource()],
        1,
        SeededRNG(13015),
    )

    assert chosen.params["toward"] == "rest"
    assert len(calls) == 1


def test_preserve_recoverability_only_proposes_and_does_not_commit():
    arbitrator = Arbitrator()
    calls = _commit_spy(arbitrator)
    physiology = Physiology(energy=0.31, fatigue=0.70, integrity=0.90, stimulation=0.55)

    replacement = arbitrator._preserve_recoverability(
        physiology,
        [_resource()],
        Candidate("APPROACH", {"toward": "rest", "step": 1.4}),
        1,
    )

    assert replacement.params["toward"] == "resource"
    assert calls == []


def test_integrity_and_stimulation_candidates_share_the_boundary():
    arbitrator = Arbitrator()
    calls = _commit_spy(arbitrator)

    physiology = Physiology(energy=0.80, fatigue=0.40, integrity=0.70, stimulation=0.80)
    integrity = arbitrator.select(
        physiology,
        [_rest(), _resource()],
        1,
        SeededRNG(4),
    )
    assert integrity.capability in {"REST", "APPROACH", "IDLE", "RETREAT"}

    physiology = Physiology(energy=0.80, fatigue=0.40, integrity=0.90, stimulation=0.80)
    stimulation = arbitrator.select(
        physiology,
        [_rest(), _resource()],
        2,
        SeededRNG(5),
    )
    assert stimulation.capability in {"REST", "APPROACH", "IDLE", "INSPECT", "MOVE"}
    assert len(calls) == 2


def test_energy_recovery_still_commits_once_without_global_energy_override():
    arbitrator = Arbitrator()
    calls = _commit_spy(arbitrator)
    physiology = Physiology(energy=0.20, fatigue=0.40, integrity=0.90, stimulation=0.55)

    chosen = arbitrator.select(
        physiology,
        [_resource(distance=1.0, support=2.0)],
        1,
        SeededRNG(8),
    )

    assert chosen.capability == "CHARGE"
    assert len(calls) == 1
