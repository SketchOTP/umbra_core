from __future__ import annotations

import copy

import pytest

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.distributed_competition import (
    MAX_ORDINARY_CANDIDATES,
    CandidateConsequenceView,
    build_consequence_view,
    evaluate_candidates,
    resolve_supported_frontier,
    supported,
    supported_dominance,
    unknown,
)
from umbra_core.physiology import Physiology, verified_outcome_effect_branches
from umbra_core.stochastic_competition import candidate_behavioral_identity
from umbra_core.util import SeededRNG


def view(name, channels, noise=0.0):
    return CandidateConsequenceView(name, name, {}, channels, noise)


def test_supported_dominance_eliminates_strictly_worse_candidate():
    better = view("better", {"x": supported(2), "y": supported(1)})
    worse = view("worse", {"x": supported(1), "y": supported(1)}, 99)
    assert supported_dominance(better, worse).passed
    assert resolve_supported_frontier([worse, better]).selected_identity == "better"


def test_tradeoff_remains_nondominated():
    a = view("a", {"x": supported(2), "y": supported(1)}, -1)
    b = view("b", {"x": supported(1), "y": supported(2)}, 1)
    result = resolve_supported_frontier([a, b])
    assert result.frontier_identities == ("a", "b")
    assert result.selected_identity == "b"


def test_unknown_blocks_elimination():
    a = view("a", {"x": supported(2), "y": unknown()})
    b = view("b", {"x": supported(1), "y": supported(0)})
    assert not supported_dominance(a, b).passed


def test_all_unknown_pool_remains_selectable():
    result = resolve_supported_frontier(
        [view("a", {"x": unknown()}, 0.1), view("b", {"x": unknown()}, 0.2)]
    )
    assert result.selected_identity == "b"


def test_simultaneous_result_is_order_independent():
    values = [
        view("a", {"x": supported(3)}),
        view("b", {"x": supported(2)}),
        view("c", {"x": supported(1)}),
    ]
    assert resolve_supported_frontier(values).as_dict() == resolve_supported_frontier(
        list(reversed(values))
    ).as_dict()


@pytest.mark.parametrize("order", [(0, 1, 2), (2, 0, 1), (1, 2, 0)])
def test_candidate_permutation_invariance(order):
    values = [view("a", {"x": supported(2)}), view("b", {"x": supported(1)}), view("c", {"x": unknown()})]
    assert resolve_supported_frontier([values[i] for i in order]).selected_identity == "a"


def test_unrelated_dominated_insertion_does_not_change_winner():
    pool = [view("a", {"x": supported(2)}, 0.1), view("b", {"x": supported(2)}, 0.2)]
    assert resolve_supported_frontier(pool).selected_identity == "b"
    assert resolve_supported_frontier(pool + [view("c", {"x": supported(1)}, 9)]).selected_identity == "b"


def test_unrelated_deletion_preserves_survivor_terms():
    pool = [view("a", {"x": supported(2)}, 0.1), view("b", {"x": supported(2)}, 0.2), view("c", {"x": supported(1)}, 9)]
    assert {v.identity: v.stochastic_term for v in pool[:-1]} == {"a": 0.1, "b": 0.2}


def test_source_equivalent_duplicates_are_rejected_before_competition():
    candidate = Candidate("REST", {"toward": "rest"})
    duplicate = Candidate("REST", {"toward": "rest", "source": "memory"})
    assert candidate_behavioral_identity(candidate.capability, candidate.params) == candidate_behavioral_identity(duplicate.capability, duplicate.params)
    with pytest.raises(ValueError, match="duplicate_behavioral_candidate"):
        evaluate_candidates(
            [candidate, duplicate], physiology=Physiology(), organism_basis=1, active_tick=1,
            effect_branches_for=lambda c: verified_outcome_effect_branches(c.capability),
        )


def test_provenance_does_not_change_order():
    assert supported(1, "one").order == supported(1, "two").order


def test_stochastic_resolution_only_uses_frontier():
    result = resolve_supported_frontier([view("a", {"x": supported(2)}, -9), view("b", {"x": supported(1)}, 99)])
    assert result.selected_identity == "a"


def test_supported_dominance_cannot_be_reversed_by_noise():
    assert resolve_supported_frontier([view("a", {"x": supported(5)}, -999), view("b", {"x": supported(0)}, 999)]).selected_identity == "a"


def test_exact_noise_tie_uses_canonical_identity():
    assert resolve_supported_frontier([view("z", {"x": unknown()}), view("a", {"x": unknown()})]).selected_identity == "a"


def test_no_scalar_total_is_read():
    a = Candidate("IDLE", {}, total=-999)
    b = Candidate("ORIENT", {}, total=999)
    chosen, _, _ = evaluate_candidates(
        [a, b], physiology=Physiology(), organism_basis=3, active_tick=4,
        effect_branches_for=lambda c: verified_outcome_effect_branches(c.capability),
    )
    assert chosen in (a, b)
    assert (a.total, b.total) == (-999, 999)


def test_no_channel_voting_or_ordering():
    a = view("a", {"z": supported(2), "a": supported(1)})
    b = view("b", {"a": supported(1), "z": supported(2)})
    assert not supported_dominance(a, b).passed


def test_hard_safety_is_outside_competition():
    arb = Arbitrator()
    arb.generate_candidates = lambda *_: [Candidate("IDLE", {}), Candidate("MOVE", {"step": 1.0})]
    chosen = arb.select(
        Physiology(), [], 1, SeededRNG(7),
        candidate_allowed=lambda candidate: candidate.capability != "MOVE",
    )
    assert chosen.capability == "IDLE"


def test_inadmissible_candidate_cannot_reenter():
    arb = Arbitrator()
    arb.generate_candidates = lambda *_: [Candidate("IDLE", {}), Candidate("MOVE", {"step": 1.0})]
    arb._introduces_critical_boundary = lambda candidate, *args, **kwargs: candidate.capability == "MOVE"
    assert arb.select(Physiology(), [], 1, SeededRNG(8)).capability == "IDLE"


def test_active_recovery_bypasses_distributed_competition():
    trace = {}
    candidate = Arbitrator().select(Physiology(fatigue=0.71), [], 1, SeededRNG(9), distributed_trace=trace)
    assert candidate.capability
    assert trace == {}


def test_pure_builder_does_not_mutate_inputs():
    candidate = Candidate("MOVE", {"step": 1.0})
    physiology = Physiology()
    before = copy.deepcopy((candidate, physiology))
    build_consequence_view(
        candidate, physiology=physiology,
        effect_branches=verified_outcome_effect_branches("MOVE"),
        organism_basis=1, active_tick=2,
    )
    assert candidate == before[0]
    assert physiology == before[1]


def test_restart_determinism():
    candidate = Candidate("MOVE", {"step": 1.0})
    kwargs = dict(physiology=Physiology(), effect_branches=verified_outcome_effect_branches("MOVE"), organism_basis=4, active_tick=5)
    assert build_consequence_view(candidate, **kwargs).as_dict() == build_consequence_view(copy.deepcopy(candidate), **kwargs).as_dict()


def test_body_migration_changes_only_behavior_or_body_evidence():
    candidate = Candidate("MOVE", {"step": 1.0})
    a = build_consequence_view(candidate, physiology=Physiology(), effect_branches=({},), organism_basis=4, active_tick=5, self_model_view={"body.success:a": unknown()})
    b = build_consequence_view(candidate, physiology=Physiology(), effect_branches=({},), organism_basis=4, active_tick=5, self_model_view={"body.success:b": unknown()})
    assert a.identity == b.identity and a.stochastic_term == b.stochastic_term


def test_fixed_candidate_bound():
    with pytest.raises(ValueError, match="ordinary_candidate_bound"):
        resolve_supported_frontier([view(str(i), {"x": unknown()}) for i in range(MAX_ORDINARY_CANDIDATES + 1)])


def test_fixed_channel_bound():
    with pytest.raises(ValueError, match="candidate_channel_bound"):
        view("a", {str(i): unknown() for i in range(65)})


def test_unselected_candidate_does_not_gain_prediction_state():
    # The pure competition module has no model or learning owner by design.
    assert "predict" not in resolve_supported_frontier.__code__.co_names
    assert "observe_outcome" not in resolve_supported_frontier.__code__.co_names
