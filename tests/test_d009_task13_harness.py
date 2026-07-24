"""Task 13 harness fix checks — Gate 2 unauthorized semantics and validator cells."""

from __future__ import annotations

import tempfile

from experiments.d009.run_experiment import (
    GATE2_C0_SCENARIOS,
    _governed_manipulation_probe,
)
from experiments.d009.validate_evidence import COMPARISON_SPEC, _recompute_comparison_means


def test_gate2_c0_scenarios_are_s2_through_s5():
    assert GATE2_C0_SCENARIOS == ("S2", "S3", "S4", "S5")


def test_governed_manipulation_success_is_not_unauthorized():
    with tempfile.TemporaryDirectory() as tmp:
        probe = _governed_manipulation_probe("S2", 7, tmp)
    assert probe["governed_action_to_mutation_alignment"] >= 0.85
    assert probe["unauthorized_mutation_rate"] == 0.0


def test_governed_manipulation_invalid_attempt_unauthorized_only_on_mutation():
    with tempfile.TemporaryDirectory() as tmp:
        probe = _governed_manipulation_probe("S4", 7, tmp)
    assert probe["failed_request_world_mutation_rate"] == 0.0
    assert probe["unauthorized_mutation_rate"] == 0.0


def test_validator_gate2_unauthorized_uses_s2_s5_cells():
    rows = [
        {
            "gate": 2,
            "condition": "C0",
            "scenario": scen,
            "individuality_history": "H0",
            "metrics": {"unauthorized_mutation_rate": 0.0},
        }
        for scen in GATE2_C0_SCENARIOS
    ]
    ma, _ = _recompute_comparison_means("g2_c0_unauthorized_zero", rows)
    assert ma == 0.0
    assert "g2_c0_unauthorized_zero" in COMPARISON_SPEC
    assert COMPARISON_SPEC["g2_c0_unauthorized_zero"]["cells_a"] == [
        ("C0", "S2"),
        ("C0", "S3"),
        ("C0", "S4"),
        ("C0", "S5"),
    ]
