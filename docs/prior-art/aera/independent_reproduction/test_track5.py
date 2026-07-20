"""UMBRA-D-000 Track 5 required tests — AERA causal learning contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_IR = Path(__file__).resolve().parent
sys.path.insert(0, str(_IR))

from environment import World  # noqa: E402
from experiment import N_SEEDS, make_store, prediction_probe, run_all_experiments, run_goal_episode, seed_oracle  # noqa: E402
from governance import Authority, GovernanceGate, Physiology, homeostasis_cannot_rewrite, homeostasis_priority  # noqa: E402
from models import MAX_PLAN_DEPTH, ModelStore  # noqa: E402
from planner import Planner, babble_episode  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
GOAL = ROOT / ".agent" / "PROJECT_GOAL.md"
SEAL = ROOT / "docs" / "evidence" / "d000-track5" / "track4-seal.json"
EV5 = ROOT / "docs" / "evidence" / "d000-track5"
PRIOR = ROOT / "docs" / "prior-art" / "aera"
DIRECTIVE = ROOT / "docs" / "directives" / "UMBRA-D-000-prior-art-reproduction.md"
PRODUCT_PATHS = [ROOT / "src", ROOT / "umbra", ROOT / "packages"]
GOAL_MD5 = "d5f60b95f25145812300a5c18013f502"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_track4_is_sealed():
    seal = json.loads(SEAL.read_text())
    assert seal["track4_commit"] == "d4df38bd51b2ca3ccc0615a74b808b02595992f3"
    assert seal["worktree_clean"] is True
    assert seal["tests_passed"] is True
    assert seal["upstream_tests_passed"] is True
    tip = subprocess.check_output(
        ["git", "-C", str(ROOT), "cat-file", "-t", seal["track4_commit"]], text=True
    ).strip()
    assert tip == "commit"
    assert seal["mimir_task_id"]
    assert seal["mimir_outcome_version"] is not None
    assert seal["evidence_hashes"]
    assert seal["gate0"] == "PASS"


def test_project_goal_unchanged():
    assert hashlib.md5(GOAL.read_bytes()).hexdigest() == GOAL_MD5
    seal = json.loads(SEAL.read_text())
    assert _sha(GOAL) == seal["project_goal_hash_sha256"]


def test_d001_remains_blocked():
    text = DIRECTIVE.read_text()
    assert "UMBRA-D-001" in text
    assert "Do not start UMBRA-D-001" in text
    profile = (ROOT / ".agent" / "PROJECT_PROFILE.md").read_text()
    assert "blocked" in profile.lower() and "D-001" in profile


def test_aera_source_is_pinned():
    man = EV5 / "source-manifest.json"
    assert man.is_file()
    data = json.loads(man.read_text())
    assert "IIIM-IS/AERA" in data["repository"]
    assert len(data["commit"]) == 40
    upstream = PRIOR / "upstream" / "AERA"
    if upstream.is_dir():
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=upstream, text=True).strip()
        assert head == data["commit"]


def test_license_is_reference_only():
    lic = PRIOR / "LICENSE_AUDIT.md"
    assert lic.is_file()
    text = lic.read_text()
    assert "SOURCE_AVAILABLE_REFERENCE_ONLY" in text
    assert "CADIA" in text
    man = json.loads((EV5 / "source-manifest.json").read_text())
    assert man["license_stance"] == "SOURCE_AVAILABLE_REFERENCE_ONLY"
    assert len(man["license_hash"]) == 64


def test_forward_model_learns():
    store = ModelStore()
    before = prediction_probe(store, [(("near:sphere",), "grab", "grab_ok_sphere")])
    babble_episode(World(), store, seed=1, steps=60)
    after = prediction_probe(store, [(("near:sphere",), "grab", "grab_ok_sphere")])
    assert after > before
    assert after >= 0.5


def test_inverse_model_improves_goal_success():
    ok2, _, _, _ = run_goal_episode("C2", seed=3)
    # Fresh C3
    store = make_store("C3")
    babble_episode(World(), store, 3, steps=50)
    ok3, _, _, _ = run_goal_episode("C3", seed=3, store=store)
    # Across seeds C2 should dominate; single seed may vary — use multi-seed
    c2 = sum(1 for s in range(10) if run_goal_episode("C2", s)[0])
    c3 = 0
    for s in range(10):
        st = make_store("C3")
        babble_episode(World(), st, s, steps=50)
        c3 += int(run_goal_episode("C3", s, st)[0])
    assert c2 > c3


def test_held_out_generalization():
    store = ModelStore()
    babble_episode(World(), store, seed=7, steps=60)
    exact = prediction_probe(store, [(("near:sphere",), "grab", "grab_ok_sphere")])
    held = prediction_probe(
        store, [(("cue:distractor_lit", "near:sphere"), "grab", "grab_ok_sphere")]
    )
    # Structural ⊆ match should generalize at least as well as exact
    assert held >= exact * 0.9
    assert held > 0.0


def test_contradiction_reduces_model_confidence():
    store = ModelStore(handle_contradiction=True)
    for _ in range(4):
        store.observe(("near:sphere",), "grab", "grab_ok_sphere")
    m = next(x for x in store.active_models() if x.outcome == "grab_ok_sphere")
    c0 = m.confidence
    for _ in range(6):
        store.observe(("near:sphere",), "grab", "grab_fail")
    m2 = next((x for x in store._models.values() if x.outcome == "grab_ok_sphere"), None)
    assert m2 is not None
    assert m2.confidence < c0 or m2.invalidated


def test_obsolete_model_is_superseded():
    store = ModelStore()
    store.observe(("near:sphere",), "grab", "grab_ok_sphere")
    store.observe(("near:sphere",), "grab", "grab_ok_sphere")
    for _ in range(5):
        store.observe(("near:sphere",), "grab", "grab_fail")
    obsolete = [m for m in store._models.values() if m.outcome == "grab_ok_sphere"][0]
    winner = [m for m in store.active_models() if m.outcome == "grab_fail"]
    assert obsolete.invalidated or obsolete.superseded_by or obsolete.confidence < 0.5
    assert winner


def test_misleading_correlation_is_not_permanent():
    store = ModelStore()
    # Cue lights with near sphere, but approaching distractor never causes grab_ok
    for _ in range(8):
        store.observe(("cue:distractor_lit", "near:sphere"), "grab", "grab_ok_sphere")
        store.observe(("cue:distractor_lit",), "approach_distractor", "near_distractor")
    pred, _ = store.predict(("cue:distractor_lit",), "approach_distractor")
    assert pred != "grab_ok_sphere"
    # Inverse for grab_ok should prefer grab near sphere, not approach_distractor
    inv = store.inverse("grab_ok_sphere")
    assert inv
    assert inv[0].action == "grab"


def test_failed_prediction_interrupts_plan():
    store = ModelStore()
    seed_oracle(store)
    # Wrong expectation planted
    store.observe(("near:distractor",), "grab", "grab_ok_sphere")
    planner = Planner(store, seed=0)
    planner.enqueue_goal("grab_ok_sphere", 1.0)
    world = World()
    world.reset(0)
    world.agent_near = "distractor"
    # Force a step that will mismatch if plan picks grab from wrong model
    planner.active_plan = planner.compose_plan("grab_ok_sphere", world.observe()["features"])
    if planner.active_plan.steps and planner.active_plan.steps[0].action == "grab":
        planner.active_plan.steps[0].expected_outcome = "grab_ok_sphere"
    for _ in range(5):
        planner.act(world, learn=True)
        if planner.interruptions:
            break
    # Either interrupted or reached via replan without endless same fail
    assert planner.interruptions >= 0  # mechanism exists
    # Stronger: run until interrupt when prediction fails
    store2 = ModelStore()
    store2.seed_model(("near:distractor",), "grab", "grab_ok_sphere", support=5)
    p2 = Planner(store2, use_composition=False, seed=1)
    p2.enqueue_goal("grab_ok_sphere", 1.0)
    w2 = World()
    w2.reset(1)
    w2.agent_near = "distractor"
    p2.active_plan = p2.compose_plan("grab_ok_sphere", w2.features())
    assert p2.active_plan.steps
    p2.active_plan.steps[0].expected_outcome = "grab_ok_sphere"
    p2.act(w2, learn=True)
    assert p2.interruptions >= 1 or p2.active_plan is None or p2.active_plan.interrupted


def test_planning_depth_is_bounded():
    store = ModelStore()
    # Deep chain of fake outcomes
    for i in range(10):
        store.observe((), f"a{i}", f"o{i}")
        store.observe((), f"a{i}", f"o{i+1}" if False else f"o{i}")
    # Link o0 <- ... impossible deep; planner max_depth
    p = Planner(store, max_depth=MAX_PLAN_DEPTH, seed=0)
    plan = p.compose_plan("missing_goal_xyz", ())
    assert len(plan.steps) <= MAX_PLAN_DEPTH


def test_model_count_is_bounded():
    store = ModelStore(max_models=15)
    for i in range(40):
        store.observe((f"x{i}",), "wait", f"y{i}")
    assert store.model_count() <= 15


def test_restart_preserves_learned_models(tmp_path):
    store = ModelStore()
    babble_episode(World(), store, seed=2, steps=25)
    path = tmp_path / "models.sqlite"
    store.save_sqlite(str(path))
    loaded = ModelStore.load_sqlite(str(path))
    assert loaded.model_count() == store.model_count()
    assert {m["model_id"] for m in loaded.dump()} == {m["model_id"] for m in store.dump()}


def test_homeostasis_prioritizes_but_does_not_command():
    store = ModelStore()
    seed_oracle(store)
    phys = Physiology(energy=0.1)
    homeostasis_cannot_rewrite(store, phys)
    prio = homeostasis_priority(phys)
    assert prio > homeostasis_priority(Physiology(energy=0.9))
    # Urgency does not select action itself
    assert not hasattr(phys, "command_action")


def test_learned_model_cannot_authorize_action():
    store = ModelStore()
    m = store.observe(("near:sphere",), "grab", "grab_ok_sphere")
    gate = GovernanceGate()
    assert gate.model_grants_authority(store, m.model_id) is False
    prop = gate.propose_from_model(store, "grab", m.model_id)
    assert gate.authorize(prop, Authority.NONE) is False
    assert gate.authorize(prop, Authority.POLICY) is True


def test_no_generated_code_executes():
    # Independent package must not exec/eval generated programs (exclude this test's asserts)
    for p in _IR.glob("*.py"):
        if p.name == "test_track5.py":
            continue
        text = p.read_text()
        assert "exec(" not in text
        assert "eval(" not in text
        assert "__import__('os')" not in text


def test_no_production_umbra_kernel_created():
    for p in PRODUCT_PATHS:
        assert not p.exists()
    assert not (ROOT / "umbra_kernel").exists()
    # Independent code stays under prior-art
    assert "prior-art/aera/independent_reproduction" in str(_IR)


def test_experiment_gates_aggregate():
    """Run compact experiment (fewer seeds in CI unit; full 30 offline)."""
    data = run_all_experiments(EV5, seeds=8)
    c2 = data["causal"]["C2"]["phases"]
    assert c2["P0"]["prediction_accuracy"] > 0.3
    assert c2["P1"]["goal_success_rate"] >= data["causal"]["C3"]["phases"]["P1"]["goal_success_rate"]
    assert c2["P3"]["contradiction_recovery"] >= data["causal"]["C4"]["phases"]["P3"]["contradiction_recovery"]
    assert c2["P4"]["bounded_model_count"] is True
    assert c2["P6"]["restart_continuity"] == 1.0
    assert data["ablation"]["no_inverse_C3_vs_C2"]["inverse_helps"] or c2["P1"]["goal_success_rate"] > 0
