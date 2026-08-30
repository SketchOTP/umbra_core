import random

import pytest

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology
from umbra_core.stochastic_competition import (
    CANDIDATE_COMPETITION_NAMESPACE,
    CANDIDATE_NOISE_SIGMA,
    candidate_behavioral_identity,
    candidate_stochastic_term,
)
from umbra_core.util import SeededRNG


POOL = [
    Candidate("APPROACH", {"toward": "resource", "heading_delta": -3.0, "step": 1.0}),
    Candidate("APPROACH", {"toward": "rest", "heading_delta": 3.14, "step": 1.0}),
    Candidate("CHARGE", {"toward": "resource"}),
    Candidate("REST", {"toward": "rest", "source": "memory", "memory_item_id": "m1"}),
]


def _mapping(candidates):
    return {
        candidate_behavioral_identity(candidate.capability, candidate.params): candidate_stochastic_term(
            organism_basis=57531938,
            active_tick=569,
            capability=candidate.capability,
            params=candidate.params,
        )
        for candidate in candidates
    }


def test_production_permutation_insertion_and_deletion_mapping():
    baseline = _mapping(POOL)
    assert _mapping(list(reversed(POOL))) == baseline
    inserted = _mapping([*POOL, Candidate("MOVE", {"step": 1.0})])
    deleted = _mapping(POOL[:-1])
    assert all(inserted[key] == value for key, value in baseline.items())
    assert all(deleted[key] == baseline[key] for key in deleted)


def test_production_source_neutrality_and_behavioral_distinction():
    a = Candidate("REST", {"toward": "rest", "source": "memory", "memory_item_id": "m1"})
    b = Candidate("REST", {"toward": "rest", "source": "development", "practice_goal_id": "g1"})
    c = Candidate("REST", {"toward": "resource"})
    assert candidate_behavioral_identity(a.capability, a.params) == candidate_behavioral_identity(b.capability, b.params)
    assert _mapping([a]) == _mapping([b])
    assert candidate_behavioral_identity(a.capability, a.params) != candidate_behavioral_identity(c.capability, c.params)


def test_production_namespace_tick_and_organism_isolation():
    candidate = POOL[0]
    kwargs = {"capability": candidate.capability, "params": candidate.params}
    term = candidate_stochastic_term(organism_basis=1, active_tick=8, **kwargs)
    assert term != candidate_stochastic_term(organism_basis=2, active_tick=8, **kwargs)
    assert term != candidate_stochastic_term(organism_basis=1, active_tick=9, **kwargs)
    assert term != candidate_stochastic_term(
        organism_basis=1,
        active_tick=8,
        namespace="execution_environment:v1",
        **kwargs,
    )
    assert CANDIDATE_COMPETITION_NAMESPACE == "ordinary_candidate_competition:v1"
    assert CANDIDATE_NOISE_SIGMA == 0.08


def test_select_does_not_consume_shared_gaussian_cursor(monkeypatch):
    rng = SeededRNG(17)
    before = rng.export_state()

    def forbidden_gauss(*_args, **_kwargs):
        raise AssertionError("shared candidate-scoring gauss consumed")

    monkeypatch.setattr(rng, "gauss", forbidden_gauss)
    Arbitrator().select(Physiology(), [], 12, rng, effective_active_ticks=12)
    assert rng.export_state() == before


def test_seedless_zero_noise_fixture_remains_supported_without_draws():
    class ZeroNoise:
        def gauss(self, *_args):
            raise AssertionError("seedless fixture draw consumed")

    chosen = Arbitrator().select(Physiology(), [], 12, ZeroNoise())
    assert chosen.capability in {"IDLE", "ORIENT", "MOVE"}


def test_environment_rng_api_and_sequence_remain_unchanged():
    expected = random.Random(31)
    rng = SeededRNG(31)
    assert rng.random() == expected.random()
    assert rng.uniform(-1.0, 1.0) == expected.uniform(-1.0, 1.0)
    assert rng.gauss(0.0, 1.0) == expected.gauss(0.0, 1.0)


def test_restart_and_body_migration_preserve_basis_without_new_state():
    candidate = POOL[0]
    before = candidate_stochastic_term(
        organism_basis=57531938,
        active_tick=569,
        capability=candidate.capability,
        params=candidate.params,
    )
    persisted = SeededRNG(57531938).export_state()
    restored = SeededRNG(0)
    restored.import_state(persisted)
    after = candidate_stochastic_term(
        organism_basis=restored.seed,
        active_tick=569,
        capability=candidate.capability,
        params=candidate.params,
    )
    assert after == before


def test_nonfinite_and_unsupported_params_fail_closed():
    with pytest.raises(ValueError, match="non_finite_behavioral_parameter"):
        candidate_behavioral_identity("MOVE", {"step": float("nan")})
    with pytest.raises(TypeError, match="unsupported_behavioral_parameter"):
        candidate_behavioral_identity("MOVE", {"bad": object()})


def test_exact_total_ties_use_behavioral_identity_not_input_order(monkeypatch):
    def constant_term(**_kwargs):
        return 0.0

    monkeypatch.setattr("umbra_core.arbitration.candidate_stochastic_term", constant_term)
    forward = [Candidate("MOVE", {"heading_delta": 0.7}), Candidate("MOVE", {"heading_delta": -0.7})]
    reverse = list(reversed([Candidate("MOVE", {"heading_delta": 0.7}), Candidate("MOVE", {"heading_delta": -0.7})]))

    def choose(candidates):
        arb = Arbitrator()
        monkeypatch.setattr(arb, "generate_candidates", lambda *_args: candidates)
        chosen = arb.select(Physiology(), [], 4, SeededRNG(1), effective_active_ticks=4)
        return candidate_behavioral_identity(chosen.capability, chosen.params)

    assert choose(forward) == choose(reverse)
