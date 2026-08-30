import math
import statistics

import pytest

from experiments.close02z.candidate_stochastic_contract import (
    COMPETITION_NAMESPACE,
    NOISE_SIGMA,
    behavioral_identity,
    candidate_stochastic_term,
    candidate_terms,
)


BASE = [
    {"capability": "APPROACH", "params": {"toward": "resource", "heading_delta": -3.0, "step": 1.0}},
    {"capability": "APPROACH", "params": {"toward": "rest", "heading_delta": 3.14, "step": 1.0}},
    {"capability": "CHARGE", "params": {"toward": "resource"}},
    {"capability": "REST", "params": {"toward": "rest", "source": "memory", "memory_item_id": "m1"}},
]


def _terms(candidates=BASE, basis=57531938, tick=569):
    return candidate_terms(candidates, organism_basis=basis, active_tick=tick)


def test_deterministic_identity_and_term():
    assert behavioral_identity(BASE[0]) == behavioral_identity(dict(BASE[0]))
    assert _terms() == _terms()


def test_permutation_insertion_and_deletion_stability():
    baseline = _terms()
    assert _terms(list(reversed(BASE))) == baseline
    inserted = _terms([*BASE, {"capability": "MOVE", "params": {"step": 1.0}}])
    deleted = _terms(BASE[:-1])
    assert all(inserted[key] == value for key, value in baseline.items())
    assert all(deleted[key] == baseline[key] for key in deleted)


@pytest.mark.parametrize(
    "source_params",
    [
        {"source": "base"},
        {"source": "memory", "memory_item_id": "m1"},
        {"source": "development", "practice_goal_id": "g1"},
        {"source": "social", "trace_id": "s1"},
        {"source": "world_model", "proposal_id": "w1"},
        {"source": "routine", "routine_skill_id": "r1"},
    ],
)
def test_source_and_provenance_are_neutral(source_params):
    candidate = {"capability": "REST", "params": {"toward": "rest", **source_params}}
    assert behavioral_identity(candidate) == '{"capability":"REST","params":{"toward":"rest"}}'
    assert candidate_stochastic_term(candidate, organism_basis=9, active_tick=8) == candidate_stochastic_term(
        {"capability": "REST", "params": {"toward": "rest"}},
        organism_basis=9,
        active_tick=8,
    )


def test_behavior_tick_organism_and_namespace_distinctions():
    left = {"capability": "MOVE", "params": {"heading_delta": -0.7, "step": 1.0}}
    right = {"capability": "MOVE", "params": {"heading_delta": 0.7, "step": 1.0}}
    base = candidate_stochastic_term(left, organism_basis=4, active_tick=9)
    assert base != candidate_stochastic_term(right, organism_basis=4, active_tick=9)
    assert base != candidate_stochastic_term(left, organism_basis=4, active_tick=10)
    assert base != candidate_stochastic_term(left, organism_basis=5, active_tick=9)
    assert base != candidate_stochastic_term(
        left, organism_basis=4, active_tick=9, namespace="execution_environment:v1"
    )


def test_restart_and_body_migration_do_not_renumber_terms():
    persisted = {"basis": 57531938, "tick": 569}
    before = _terms(basis=persisted["basis"], tick=persisted["tick"])
    restarted = _terms([dict(candidate) for candidate in BASE], **persisted)
    migrated = _terms([dict(candidate) for candidate in BASE], **persisted)
    assert before == restarted == migrated


def test_no_pool_fields_or_mutable_draw_cursor_enter_key():
    before = candidate_stochastic_term(BASE[0], organism_basis=7, active_tick=3)
    for _ in range(100):
        candidate_stochastic_term(BASE[-1], organism_basis=7, active_tick=3)
    assert candidate_stochastic_term(BASE[0], organism_basis=7, active_tick=3) == before
    assert "index" not in COMPETITION_NAMESPACE and "count" not in COMPETITION_NAMESPACE


def test_duplicate_equivalence_has_one_identity_and_one_term():
    duplicate = {"capability": "REST", "params": {"toward": "rest", "source": "development"}}
    assert behavioral_identity(BASE[-1]) == behavioral_identity(duplicate)
    assert len(_terms([BASE[-1], duplicate])) == 1


def test_nonfinite_behavioral_parameters_fail_closed():
    with pytest.raises(ValueError, match="non_finite_behavioral_parameter"):
        behavioral_identity({"capability": "MOVE", "params": {"step": math.nan}})


def test_preregistered_marginal_distribution_translation():
    # Frozen broad sample: 40k independent semantic keys, sigma 0.08.
    values = [
        candidate_stochastic_term(
            {"capability": ("MOVE", "REST", "CHARGE", "INSPECT")[i % 4], "params": {"sample": i}},
            organism_basis=1000 + (i % 257),
            active_tick=i,
        )
        for i in range(40_000)
    ]
    assert abs(statistics.fmean(values)) <= 0.0015
    assert 0.078 <= statistics.pstdev(values) <= 0.082
    assert 0.49 <= sum(value > 0.0 for value in values) / len(values) <= 0.51
    assert NOISE_SIGMA == 0.08
