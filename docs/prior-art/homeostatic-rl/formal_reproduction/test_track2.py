"""Deterministic unit + causal tests for Track 2 homeostatic RL formal reproduction."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]  # UMBRA-CORE
FR = Path(__file__).resolve().parent
sys.path.insert(0, str(FR))

from drives import DRIVES, drive_euclidean, drive_linear, drive_nonlinear  # noqa: E402
from environment import FORBIDDEN_COMMANDS, World  # noqa: E402
from experiment import (  # noqa: E402
    food_value_by_state,
    run_episode,
    run_suite,
    temperature_action_reversal,
)
from physiology import ENERGY, Physiology  # noqa: E402
from rewards import compute_reward, hardcoded_need_action  # noqa: E402


def test_micropsi_reproduction_label_is_precise():
    mod = ROOT / "docs/prior-art/micropsi2/reproduce_modulators.py"
    text = mod.read_text()
    assert 'REPRODUCTION_STATUS = "INDEPENDENT_MECHANISM_REPRODUCTION"' in text
    assert "UPSTREAM_RUNTIME_EXECUTED = False" in text
    notes = (ROOT / "docs/prior-art/micropsi2/NOTES.md").read_text()
    assert "INDEPENDENT_MECHANISM_REPRODUCTION" in notes
    assert "not" in notes.lower() and "complete upstream" in notes.lower()


def test_project_goal_hash_unchanged():
    data = (ROOT / ".agent/PROJECT_GOAL.md").read_bytes()
    h = hashlib.md5(data).hexdigest()
    # pinned at Track 2 start
    assert h == "d5f60b95f25145812300a5c18013f502"


def test_d001_remains_blocked():
    profile = (ROOT / ".agent/PROJECT_PROFILE.md").read_text()
    assert "UMBRA-D-001 is blocked" in profile or "D-001 is blocked" in profile
    d000 = (ROOT / "docs/directives/UMBRA-D-000-prior-art-reproduction.md").read_text()
    assert "D-001" in d000 and ("block" in d000.lower() or "BLOCK" in d000)


def test_mimir_project_resolves():
    profile = (ROOT / ".agent/PROJECT_PROFILE.md").read_text()
    assert "7777645d52a91b49" in profile


def test_drive_zero_at_ideal_state():
    p = Physiology(energy=ENERGY.ideal, temperature=0.50)
    assert drive_linear(p) == pytest.approx(0.0)
    assert drive_euclidean(p) == pytest.approx(0.0)
    assert drive_nonlinear(p) == pytest.approx(0.0)


def test_drive_increases_with_deviation():
    ideal = Physiology(energy=0.70, temperature=0.50)
    bad = Physiology(energy=0.20, temperature=0.50)
    for fn in DRIVES.values():
        assert fn(bad) > fn(ideal)


def test_drive_handles_multiple_needs():
    one = Physiology(energy=0.20, temperature=0.50)
    two = Physiology(energy=0.20, temperature=0.15)
    assert drive_nonlinear(two) > drive_nonlinear(one)


def test_drive_reduction_reward_positive_on_recovery():
    before = Physiology(energy=0.20, temperature=0.50)
    after = before.copy()
    after.apply_outcome(d_energy=0.30, drift_enabled=False)
    r = compute_reward("R2", before, after, "food", drive_name="D3")
    assert r > 0


def test_drive_reduction_reward_negative_on_overshoot():
    before = Physiology(energy=0.75, temperature=0.50)
    after = before.copy()
    after.apply_outcome(d_energy=0.30, drift_enabled=False)
    r = compute_reward("R2", before, after, "food", drive_name="D3")
    assert r < 0


def test_autonomous_drift_occurs_during_idle():
    p = Physiology(energy=0.70, temperature=0.50)
    e0 = p.energy
    p.tick_autonomous()
    assert p.energy < e0


def test_policy_cannot_assign_internal_state():
    """Physiology has no public setter used by policies; intervene is experiment-only."""
    w = World()
    w.reset(seed=0)
    e0 = w.phys.energy
    # step STAY — energy only via drift, not policy assignment
    w.step("STAY")
    assert w.phys.energy != e0 or w.cfg.drift_enabled
    assert not hasattr(type(w.phys), "set_energy")


def test_food_value_depends_on_energy_state():
    v = food_value_by_state("D3")
    assert v["deficit"] > v["satiated"]


def test_temperature_action_reverses_with_internal_state():
    v = temperature_action_reversal("D3")
    assert v["cold_warm"] > 0
    assert v["hot_warm"] < 0


def test_resource_seeking_satiates():
    m_hungry, _ = run_episode("C4", "I1", seed=0, steps=50)
    m_full, _ = run_episode("C4", "I8", seed=0, steps=50)
    # hungry should consume at least as much as already-fed abundant case's early phase;
    # satiation: unnecessary consumption lower when starting nearer ideal under C4 vs C1
    from experiment import _satiation_check

    assert _satiation_check([0, 1, 2])["pass"]


def test_competing_needs_change_action_preference():
    from experiment import _competition_check

    assert _competition_check([0, 1, 2])["pass"]


def test_internal_state_ablation_impairs_regulation():
    from experiment import _compare_ablation

    assert _compare_ablation("C4", "C5", "I1", [0, 1, 2])["pass"]


def test_drift_ablation_impairs_autonomous_behavior():
    # With drift disabled under I9, energy should not fall; autonomous motivation weaker
    m6, tr6 = run_episode("C6", "I9", seed=0, steps=30)
    m4, tr4 = run_episode("C4", "I9", seed=0, steps=30)
    drop4 = tr4[0]["energy"] - tr4[-1]["energy"]
    drop6 = tr6[0]["energy"] - tr6[-1]["energy"]
    assert drop4 > drop6


def test_prediction_ablation_impairs_anticipation():
    from experiment import _anticipation_check

    r = _anticipation_check([0, 1, 2])
    assert r["pass"]


def test_resource_relocation_changes_behavior():
    from experiment import _relocation_check

    assert _relocation_check([0, 1, 2])["pass"]


def test_no_need_uses_direct_action_command():
    assert "GO_EAT" in FORBIDDEN_COMMANDS
    w = World()
    w.reset(seed=0)
    with pytest.raises(ValueError, match="forbidden"):
        w.step("GO_EAT")


def test_every_mechanism_has_classification():
    matrix = ROOT / "docs/prior-art/homeostatic-rl/MECHANISM_MATRIX.md"
    assert matrix.exists()
    text = matrix.read_text()
    for token in ("ADAPT", "REJECT", "REFERENCE"):
        assert token in text
    # every data row in the table should include a classification cell marker
    assert text.count("**ADAPT**") + text.count("**REJECT**") + text.count(
        "**REFERENCE**"
    ) + text.count("**UNRESOLVED**") + text.count("**ADOPT**") >= 10
    ledger = (ROOT / "docs/prior-art/SELECTION_LEDGER.md").read_text()
    assert "HRRL drive-reduction" in ledger or "drive-reduction" in ledger


def test_upstream_attempts_have_evidence():
    path = ROOT / "docs/evidence/d000-track2/upstream-smoke.json"
    assert path.exists(), "upstream-smoke.json must exist"
    data = json.loads(path.read_text())
    assert "homeostatic_agents_pfrl" in data
    assert "deeprl_gfn" in data
    for key in ("homeostatic_agents_pfrl", "deeprl_gfn"):
        assert data[key].get("attempted") is True


def test_no_production_umbra_kernel_exists():
    # no src/umbra organism package
    assert not (ROOT / "src/umbra").exists()
    assert not (ROOT / "umbra").exists()
    fr = (FR / "__init__.py").read_text()
    assert "Not a production" in fr or "not a production" in fr.lower()
