from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology


class ZeroNoise:
    def gauss(self, mean, sigma):
        return 0.0


def _score(candidate, phys, observations, tick):
    candidate.total = 10.0 if candidate.capability == "INSPECT" else 0.0
    candidate.scores = {}
    return candidate


def test_existing_candidate_enters_one_ordinary_final_choice():
    arb = Arbitrator()
    arb.generate_candidates = lambda phys, observations, tick: [Candidate("IDLE", {})]
    arb._preserve_recoverability = lambda phys, observations, candidate, tick: candidate
    arb.score_candidate = _score

    chosen = arb.select(
        Physiology(),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("INSPECT", {"source": "existing"})],
    )

    assert chosen.capability == "INSPECT"
    assert chosen.params["source"] == "existing"


def test_existing_candidate_does_not_enter_critical_recovery_competition():
    arb = Arbitrator()
    arb._introduces_critical_boundary = lambda *args, **kwargs: False
    arb._preserve_recoverability = lambda phys, observations, candidate, tick: candidate
    arb.score_candidate = _score

    chosen = arb.select(
        Physiology(energy=0.05),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("INSPECT", {"source": "existing"})],
    )

    assert chosen.capability != "INSPECT"
    assert chosen.params.get("source") != "existing"
