from experiments.close02y.candidate_stable_contract import (
    candidate_identity,
    canonical_deduplicate,
    stable_rank,
    stable_terms,
    stochastic_term,
)


BASE = [
    {"capability": "APPROACH", "params": {"toward": "resource", "heading_delta": -3.0, "step": 1.0}},
    {"capability": "APPROACH", "params": {"toward": "rest", "heading_delta": 3.14, "step": 1.0}},
    {"capability": "CHARGE", "params": {"toward": "resource"}},
    {"capability": "REST", "params": {"toward": "rest", "source": "memory", "memory_item_id": "m1"}},
]


def test_permutation_invariance():
    assert stable_terms(BASE, organism_basis=7, active_tick=569) == stable_terms(
        list(reversed(BASE)), organism_basis=7, active_tick=569
    )


def test_unrelated_insertion_and_deletion_leave_survivors_unchanged():
    before = stable_terms(BASE, organism_basis=7, active_tick=569)
    inserted = [*BASE, {"capability": "MOVE", "params": {"step": 1.0}}]
    after_insert = stable_terms(inserted, organism_basis=7, active_tick=569)
    after_delete = stable_terms(BASE[:-1], organism_basis=7, active_tick=569)
    assert all(after_insert[key] == value for key, value in before.items())
    assert all(after_delete[key] == before[key] for key in after_delete)


def test_source_equivalent_duplicates_share_identity_and_term():
    memory = {"capability": "REST", "params": {"toward": "rest", "source": "memory", "memory_item_id": "m1"}}
    development = {"capability": "REST", "params": {"toward": "rest", "source": "development_practice", "practice_goal_id": "g9"}}
    assert candidate_identity(memory) == candidate_identity(development)
    assert stochastic_term(memory, organism_basis=11, active_tick=8) == stochastic_term(
        development, organism_basis=11, active_tick=8
    )
    assert len(canonical_deduplicate([memory, development])) == 1


def test_genuine_behavioral_difference_can_receive_distinct_term():
    left = {"capability": "MOVE", "params": {"heading_delta": -0.7, "step": 1.0}}
    right = {"capability": "MOVE", "params": {"heading_delta": 0.7, "step": 1.0}}
    assert candidate_identity(left) != candidate_identity(right)
    assert stochastic_term(left, organism_basis=4, active_tick=9) != stochastic_term(
        right, organism_basis=4, active_tick=9
    )


def test_tick_and_organism_basis_are_legitimate_variability_dimensions():
    cand = BASE[0]
    term = stochastic_term(cand, organism_basis=4, active_tick=9)
    assert term != stochastic_term(cand, organism_basis=4, active_tick=10)
    assert term != stochastic_term(cand, organism_basis=5, active_tick=9)


def test_replay_restart_and_body_migration_do_not_renumber_terms():
    persisted = {"organism_basis": 57531938, "active_tick": 569}
    before = stable_terms(BASE, **persisted)
    restarted = stable_terms([dict(c) for c in BASE], **persisted)
    body_migrated = stable_terms([dict(c) for c in BASE], **persisted)
    assert before == restarted == body_migrated


def test_namespace_separates_candidate_competition_from_other_domains():
    cand = BASE[0]
    competition = stochastic_term(cand, organism_basis=7, active_tick=569)
    environment = stochastic_term(
        cand,
        organism_basis=7,
        active_tick=569,
        namespace="execution_environment:v1",
    )
    assert competition != environment


def test_canonical_identity_is_exact_tie_fallback_not_input_order():
    totals = {candidate_identity(candidate): 1.0 for candidate in BASE}
    forward = stable_rank(BASE, totals, organism_basis=7, active_tick=569)
    reverse = stable_rank(reversed(BASE), totals, organism_basis=7, active_tick=569)
    assert forward == reverse


def test_retained_tick_569_x_deletion_only_removes_rest_term():
    u = stable_terms(BASE, organism_basis=57531938, active_tick=569)
    x = stable_terms(BASE[:-1], organism_basis=57531938, active_tick=569)
    assert set(u) - set(x) == {candidate_identity(BASE[-1])}
    assert all(x[key] == u[key] for key in x)


def test_candidate_identity_rejects_nonfinite_parameters():
    try:
        candidate_identity({"capability": "MOVE", "params": {"step": float("nan")}})
    except ValueError as exc:
        assert str(exc) == "non_finite_behavioral_parameter"
    else:
        raise AssertionError("nonfinite parameter accepted")
