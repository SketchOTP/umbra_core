"""Pure AS-003B qualification-harness contract proofs.

These tests do not construct an organism or call any organism runtime method.
"""
from __future__ import annotations

import json

from experiments.as003b.diagnostics import STAGES, frontier_metrics
from umbra_core.arbitration import Candidate
from umbra_core.stochastic_competition import (
    candidate_behavioral_identity,
    candidate_stochastic_term,
)


def test_diagnostic_stages_are_exact_and_exclude_known_r1():
    assert STAGES == {
        "DIAGNOSTIC_A": {
            "regime": "R0",
            "scenario": "S0",
            "seed": 45878900,
            "horizon": 500,
            "failure_verdict": "AS003B_FLAT_AUTHORITY_COMPATIBILITY_FAIL",
        },
        "DIAGNOSTIC_B": {
            "regime": "R0",
            "scenario": "S0",
            "seed": 22023239,
            "horizon": 3500,
            "failure_verdict": "AS003B_HIERARCHICAL_AUTHORITY_COMPATIBILITY_FAIL",
        },
    }
    assert 57531938 not in {stage["seed"] for stage in STAGES.values()}


def test_close02z_terms_are_source_neutral_and_pool_independent():
    memory = Candidate("REST", {"toward": "rest", "source": "memory", "memory_item_id": "m1"})
    development = Candidate("REST", {"toward": "rest", "source": "development", "practice_goal_id": "g1"})
    other = Candidate("MOVE", {"heading_delta": 0.5, "step": 1.0})
    assert candidate_behavioral_identity(memory.capability, memory.params) == candidate_behavioral_identity(
        development.capability, development.params
    )
    memory_term = candidate_stochastic_term(
        organism_basis=9, active_tick=8, capability=memory.capability, params=memory.params
    )
    assert memory_term == candidate_stochastic_term(
        organism_basis=9, active_tick=8, capability=development.capability, params=development.params
    )
    assert memory_term == candidate_stochastic_term(
        organism_basis=9, active_tick=8, capability=memory.capability, params=memory.params
    )
    assert candidate_stochastic_term(
        organism_basis=9, active_tick=8, capability=other.capability, params=other.params
    ) != memory_term


def test_frontier_metrics_preserve_mechanism_gate_fields(tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps(
            {
                "final_candidate": {"capability": "REST"},
                "distributed_competition": {
                    "admissible_candidate_count": 2,
                    "pairwise_dominance_count": 1,
                    "eliminated_candidate_count": 1,
                    "frontier_equals_full_pool": False,
                    "stochastic_resolution_required": False,
                    "distributed_changed_winner": True,
                    "supported_count_by_channel": {"self.success": 2},
                    "unknown_count_by_channel": {"world.effect": 1},
                    "attempts": [{"passed": True, "strict_channels": ["self.success"]}],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    metrics = frontier_metrics(trace)
    assert metrics["dominance_realized"]
    assert metrics["evidence_causality_realized"]
    assert metrics["unknown_functional_realized"]
    assert not metrics["complete_frontier_saturation"]
    assert metrics["strict_elimination_channels"] == {"self.success": 1}
