from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology


class ZeroNoise:
    def gauss(self, mean, sigma):
        return 0.0


def _score_by_capability(candidate, phys, observations, tick):
    candidate.scores = {}
    candidate.total = {
        "CHARGE": 10.0,
        "INSPECT": 9.0,
        "ORIENT": 1.0,
        "IDLE": 0.0,
        "MOVE": 0.0,
    }.get(candidate.capability, 0.0)
    return candidate


def _safe_arbitrator(generate):
    arb = Arbitrator()
    arb.generate_candidates = generate
    arb._introduces_critical_boundary = lambda *args, **kwargs: False
    arb.score_candidate = _score_by_capability
    return arb


def test_known_tick_one_fixture_selects_existing_development_intent():
    arb = _safe_arbitrator(
        lambda phys, observations, tick: [Candidate("ORIENT", {"heading": 0.0})]
    )
    chosen = arb.select(
        Physiology(),
        [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 1.0}],
        1,
        ZeroNoise(),
        intent_candidates=[
            Candidate("CHARGE", {"toward": "resource", "source": "development_practice"})
        ],
    )
    assert chosen.capability == "CHARGE"


def test_no_intent_preserves_base_affordance_arbitration():
    arb = _safe_arbitrator(
        lambda phys, observations, tick: [
            Candidate("ORIENT", {"heading": 0.0}),
            Candidate("INSPECT", {"toward": "inspect"}),
        ]
    )
    chosen = arb.select(Physiology(), [], 1, ZeroNoise())
    assert chosen.capability == "INSPECT"


def test_urgent_recovery_ignores_optional_intents():
    arb = _safe_arbitrator(
        lambda phys, observations, tick: [Candidate("MOVE", {"step": 1.0})]
    )
    chosen = arb.select(
        Physiology(energy=0.05),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("INSPECT", {"source": "development_practice"})],
    )
    assert chosen.capability != "INSPECT"


def test_intent_source_collection_order_does_not_change_result():
    def make(order):
        arb = _safe_arbitrator(lambda phys, observations, tick: [])
        return arb.select(
            Physiology(),
            [],
            1,
            ZeroNoise(),
            intent_candidates=order,
        )

    first = make([
        Candidate("ORIENT", {"heading": 0.0, "source": "social"}),
        Candidate("IDLE", {"source": "development"}),
    ])
    second = make([
        Candidate("IDLE", {"source": "development"}),
        Candidate("ORIENT", {"heading": 0.0, "source": "social"}),
    ])
    assert first.capability == second.capability
    assert first.params == second.params


def test_duplicate_intents_deduplicate_provenance_only():
    candidates = Arbitrator._canonical_intent_candidates(
        [
            Candidate("INSPECT", {"source": "memory", "memory_item_id": "m1"}),
            Candidate("INSPECT", {"source": "social", "goal_id": "g1"}),
        ]
    )
    assert len(candidates) == 1
    assert candidates[0].capability == "INSPECT"


def test_unsafe_intent_falls_back_to_safe_base_pool():
    arb = Arbitrator()
    arb.generate_candidates = lambda phys, observations, tick: [Candidate("IDLE", {})]
    arb.score_candidate = _score_by_capability
    arb._introduces_critical_boundary = (
        lambda candidate, *args, **kwargs: candidate.capability == "CHARGE"
    )
    chosen = arb.select(
        Physiology(),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("CHARGE", {"source": "development_practice"})],
    )
    assert chosen.capability == "IDLE"


def test_all_actions_unsafe_retains_honest_no_safe_action():
    arb = Arbitrator()
    arb.generate_candidates = lambda phys, observations, tick: [Candidate("CHARGE", {})]
    arb.score_candidate = _score_by_capability
    arb._introduces_critical_boundary = lambda *args, **kwargs: True
    chosen = arb.select(
        Physiology(),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("CHARGE", {"source": "development_practice"})],
    )
    assert chosen.params["source"] == "no_safe_action"
