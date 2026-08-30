from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology


class ZeroNoise:
    seed = None

    def gauss(self, mean, sigma):
        return 0.0


def _configured(base, scores, seen):
    arb = Arbitrator()
    arb.generate_candidates = lambda phys, observations, tick: list(base)

    # AS-003 supersedes ordinary scalar score authority. ``seen`` is retained
    # by the tests as the distributed candidate-pool observation sink.
    arb._introduces_critical_boundary = lambda *args, **kwargs: False
    return arb


def _pool(trace):
    return {view["capability"] for view in trace["views"]}


def test_no_intent_no_preventive_keeps_ordinary_base_pool():
    seen = []
    arb = _configured(
        [Candidate("ORIENT", {}), Candidate("IDLE", {})],
        {"ORIENT": 2.0, "IDLE": 1.0},
        seen,
    )
    trace = {}
    chosen = arb.select(Physiology(), [], 1, ZeroNoise(), distributed_trace=trace)
    assert chosen.capability in {"ORIENT", "IDLE"}
    assert _pool(trace) == {"ORIENT", "IDLE"}


def test_intent_without_preventive_attention_excludes_unrelated_base():
    seen = []
    arb = _configured([Candidate("ORIENT", {})], {"CHARGE": 2.0}, seen)
    trace = {}
    chosen = arb.select(
        Physiology(),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("CHARGE", {"source": "development_practice"})],
        distributed_trace=trace,
    )
    assert chosen.capability == "CHARGE"
    assert _pool(trace) == {"CHARGE"}


def test_intent_and_preventive_attention_admit_only_matching_base():
    seen = []
    arb = _configured(
        [Candidate("REST", {"toward": "rest"}), Candidate("ORIENT", {})],
        {"REST": 10.0, "INSPECT": 9.0, "ORIENT": 1.0},
        seen,
    )
    trace = {}
    chosen = arb.select(
        Physiology(fatigue=0.30),
        [{"kind": "rest", "relative_direction": 0.0, "estimated_distance": 1.0}],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("INSPECT", {"source": "memory"})],
        distributed_trace=trace,
    )
    assert chosen.capability in {"REST", "INSPECT"}
    assert _pool(trace) == {"REST", "INSPECT"}


def test_preventive_lane_does_not_create_no_safe_action_when_no_match_exists():
    seen = []
    arb = _configured([Candidate("ORIENT", {})], {"INSPECT": 2.0}, seen)
    trace = {}
    chosen = arb.select(
        Physiology(fatigue=0.30),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("INSPECT", {"source": "memory"})],
        distributed_trace=trace,
    )
    assert chosen.capability == "INSPECT"
    assert chosen.params.get("source") != "no_safe_action"
    assert _pool(trace) == {"INSPECT"}


def test_hard_recovery_still_excludes_optional_intent():
    seen = []
    arb = _configured([Candidate("MOVE", {})], {"MOVE": 2.0, "INSPECT": 9.0}, seen)
    trace = {}
    chosen = arb.select(
        Physiology(fatigue=0.71),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("INSPECT", {"source": "development_practice"})],
    )
    assert chosen.capability != "INSPECT"


def test_no_intent_preventive_attention_keeps_matching_base_only():
    seen = []
    arb = _configured(
        [Candidate("REST", {"toward": "rest"}), Candidate("ORIENT", {})],
        {"REST": 10.0, "ORIENT": 20.0},
        seen,
    )
    trace = {}
    chosen = arb.select(
        Physiology(fatigue=0.30),
        [],
        1,
        ZeroNoise(),
        distributed_trace=trace,
    )
    assert chosen.capability == "REST"
    assert _pool(trace) == {"REST"}


def test_multiple_preventive_dimensions_use_existing_effects():
    phys = Physiology(energy=0.60, fatigue=0.30)
    assert Arbitrator._candidate_regulatory_dimensions(
        Candidate("REST", {"toward": "rest"}), phys
    ) == frozenset({"energy", "fatigue"})
    assert Arbitrator._candidate_regulatory_dimensions(
        Candidate("ORIENT", {}), phys
    ) == frozenset()


def test_preventive_attention_clears_without_persistent_authority():
    seen = []
    arb = _configured([Candidate("REST", {"toward": "rest"})], {"INSPECT": 3.0}, seen)
    trace = {}
    chosen = arb.select(
        Physiology(fatigue=0.20),
        [],
        1,
        ZeroNoise(),
        intent_candidates=[Candidate("INSPECT", {"source": "social"})],
        distributed_trace=trace,
    )
    assert chosen.capability == "INSPECT"
    assert _pool(trace) == {"INSPECT"}


def test_intent_source_order_does_not_change_selection():
    def run(candidates):
        seen = []
        arb = _configured([], {"CHARGE": 2.0, "INSPECT": 1.0}, seen)
        return arb.select(Physiology(), [], 1, ZeroNoise(), intent_candidates=candidates)

    first = run([
        Candidate("INSPECT", {"source": "memory"}),
        Candidate("CHARGE", {"source": "development"}),
    ])
    second = run([
        Candidate("CHARGE", {"source": "development"}),
        Candidate("INSPECT", {"source": "memory"}),
    ])
    assert (first.capability, first.params) == (second.capability, second.params)
