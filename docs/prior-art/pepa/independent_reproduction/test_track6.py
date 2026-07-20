"""UMBRA-D-000 Track 6 required tests — PEPA persistent autonomy contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_IR = Path(__file__).resolve().parent
sys.path.insert(0, str(_IR))

from agent import MAX_GOALS, MAX_RETRIES, Agent, Goal  # noqa: E402
from experiment import (  # noqa: E402
    N_SEEDS,
    TICKS,
    _reflection_stress_probe,
    run_episode,
)
from world import World  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
GOAL = ROOT / ".agent" / "PROJECT_GOAL.md"
SEAL = ROOT / "docs" / "evidence" / "d000-track6" / "track5-seal.json"
EV6 = ROOT / "docs" / "evidence" / "d000-track6"
PRIOR = ROOT / "docs" / "prior-art" / "pepa"
DIRECTIVE = ROOT / "docs" / "directives" / "UMBRA-D-000-prior-art-reproduction.md"
GOAL_MD5 = "d5f60b95f25145812300a5c18013f502"
PRODUCT_PATHS = [ROOT / "src", ROOT / "umbra", ROOT / "packages", ROOT / "kernel"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_track5_is_sealed():
    seal = json.loads(SEAL.read_text())
    assert seal["track5_commit"] == "6bc8d81862d09558f3a62f4bcc4073aa2b3d64d7"
    assert seal["worktree_clean"] is True
    assert seal["tests_passed"] is True
    tip = subprocess.check_output(
        ["git", "-C", str(ROOT), "cat-file", "-t", seal["track5_commit"]], text=True
    ).strip()
    assert tip == "commit"
    assert seal["mimir_task_id"]
    assert seal["evidence_hashes"]
    assert seal["gate0"] == "PASS"
    assert seal["project_goal_md5"] == GOAL_MD5


def test_project_goal_unchanged():
    assert hashlib.md5(GOAL.read_bytes()).hexdigest() == GOAL_MD5
    seal = json.loads(SEAL.read_text())
    assert _sha(GOAL) == seal["project_goal_hash_sha256"]


def test_d001_remains_blocked():
    """Track6 gate: D-001 blocked until D-000S. After QUALIFIED, foundation D-001 is authorized."""
    syn = ROOT / "docs" / "evidence" / "d000-synthesis" / "final-verdict.md"
    profile = (ROOT / ".agent" / "PROJECT_PROFILE.md").read_text()
    if syn.is_file() and "UMBRA_D000S_FOUNDATION_ARCHITECTURE_QUALIFIED" in syn.read_text():
        assert "UMBRA-D-001" in profile
        assert "authorized" in profile.lower() or "active" in profile.lower()
        assert not any(p.exists() for p in PRODUCT_PATHS)
        return
    text = DIRECTIVE.read_text()
    assert "Do not start UMBRA-D-001" in text
    assert "blocked" in profile.lower() and "D-001" in profile


def test_pepa_sources_are_pinned():
    man = json.loads((EV6 / "source-manifest.json").read_text())
    assert man["paper_id"] == "2603.00117"
    assert man["paper_version"] == "v3"
    assert man["project_page"].startswith("https://sites.google.com/view/pepa-persistent")
    assert isinstance(man["repositories"], list)
    assert len(man["repositories"]) >= 1


def test_missing_source_is_marked_paper_only():
    man = json.loads((EV6 / "source-manifest.json").read_text())
    missing = man.get("missing_components") or []
    assert missing, "expected explicit missing components"
    paper_only = man.get("paper_only_claims") or []
    assert paper_only, "expected paper-only claims"
    assert any("Sys3" in x or "LLM" in x or "personality" in x.lower() for x in paper_only + missing)


def test_agent_acts_without_user_prompt():
    m = run_episode("C6", seed=3, history="H0", ticks=2000)
    assert m.unprompted_action_rate > 0.8
    m0 = run_episode("C0", seed=3, history="H0", ticks=2000)
    assert m.viability_time > m0.viability_time


def test_authored_personality_alone_is_not_individuality():
    """Authored personality ≠ lived-history individuality.

    C2 has no memory: different histories must not create lasting play divergence.
    C6 with memory+history must.
    """
    h1_c2 = [run_episode("C2", s, "H1", 2000).play_rate for s in range(8)]
    h2_c2 = [run_episode("C2", s, "H2", 2000).play_rate for s in range(8)]
    c2_effect = abs(sum(h1_c2) / 8 - sum(h2_c2) / 8)

    h1_c6 = [run_episode("C6", s, "H1", 2000).play_rate for s in range(8)]
    h2_c6 = [run_episode("C6", s, "H2", 2000).play_rate for s in range(8)]
    c6_effect = abs(sum(h1_c6) / 8 - sum(h2_c6) / 8)

    assert c6_effect > 0.02
    assert c6_effect > c2_effect + 0.015


def test_different_histories_change_behavior():
    h1 = [run_episode("C6", s, "H1", 2500).play_rate for s in range(10)]
    h2 = [run_episode("C6", s, "H2", 2500).play_rate for s in range(10)]
    assert sum(h1) / len(h1) > sum(h2) / len(h2) + 0.02
    s3 = [run_episode("C6", s, "H3", 2500).social_rate for s in range(10)]
    s4 = [run_episode("C6", s, "H4", 2500).social_rate for s in range(10)]
    assert sum(s3) / len(s3) > sum(s4) / len(s4) + 0.02


def test_homeostasis_ablation_changes_behavior():
    c6 = [run_episode("C6", s, "H0", 2000).viability_time for s in range(8)]
    c0 = [run_episode("C0", s, "H0", 2000).viability_time for s in range(8)]
    assert sum(c6) / len(c6) > sum(c0) / len(c0) + 0.3


def test_memory_ablation_changes_behavior():
    # C4 homeostasis only vs C6 with memory: history effect requires memory
    h1_c6 = [run_episode("C6", s, "H1", 2000).play_rate for s in range(8)]
    h2_c6 = [run_episode("C6", s, "H2", 2000).play_rate for s in range(8)]
    h1_c4 = [run_episode("C4", s, "H1", 2000).play_rate for s in range(8)]
    h2_c4 = [run_episode("C4", s, "H2", 2000).play_rate for s in range(8)]
    eff6 = abs(sum(h1_c6) / 8 - sum(h2_c6) / 8)
    eff4 = abs(sum(h1_c4) / 8 - sum(h2_c4) / 8)
    assert eff6 > eff4 + 0.01


def test_satiation_stops_compulsive_action():
    m = run_episode("C6", seed=5, history="H0", ticks=4000)
    assert m.satiation > 0.0


def test_failed_goal_is_revised():
    a = Agent("C6", 2)
    w = World()
    w.reset(2)
    a.goals = [Goal(name="play", drive="play", priority=0.9, source="internal")]
    a.body.position = 0  # not play cell
    for _ in range(30):
        a.step(w)
    # retries exhausted or reflection revised
    assert not a.goals[0].active or a.goals[0].retries > 0 or a.goals_generated > 1
    assert a.goals_generated >= 1 or any(g.name != "play" for g in a.goals)


def test_external_request_cannot_bypass_governance():
    a = Agent("C6", 1)
    a.phys.energy = 0.1
    assert a.enqueue_external("explore", priority=0.99) is False
    assert a.external_blocked >= 1
    m = run_episode("C6", 4, "H0", 800, force_critical_external=True)
    assert m.external_request_arbitration >= 0.5


def test_reflection_has_measurable_value():
    c6 = [_reflection_stress_probe("C6", s) for s in range(12)]
    c7 = [_reflection_stress_probe("C7", s) for s in range(12)]
    assert sum(c6) / len(c6) > sum(c7) / len(c7) + 0.1


def test_no_llm_preserves_core_operation():
    a = Agent("C6", 7)  # no LLM flags
    assert a.use_llm_goals is False
    w = World()
    w.reset(7)
    for _ in range(500):
        a.step(w)
    assert a.meaningful_ticks > 400
    assert a.phys.viable()


def test_goal_generation_is_bounded():
    a = Agent("C6", 9)
    w = World()
    w.reset(9)
    for _ in range(5000):
        a._ensure_internal_goals()
        a.step(w)
    assert sum(1 for g in a.goals if g.active) <= MAX_GOALS
    # LLM-style budget also bounded
    b = Agent("C3", 9)
    for _ in range(100):
        b._llm_style_generate()
    assert b.llm_style_budget <= 40


def test_retry_loop_is_bounded():
    a = Agent("C6", 11)
    g = Goal(name="play", drive="play", priority=1.0, source="internal")
    a.goals = [g]
    w = World()
    w.reset(11)
    a.body.position = 0
    for _ in range(50):
        a.step(w)
    assert g.retries <= MAX_RETRIES or g.active is False


def test_no_production_umbra_kernel_created():
    for p in PRODUCT_PATHS:
        if p.exists():
            # allow empty placeholders only
            if p.is_dir() and any(p.iterdir()):
                pytest.fail(f"production path populated: {p}")
    assert (PRIOR / "independent_reproduction").is_dir()
    readme = (PRIOR / "README.md").read_text()
    assert "not production" in readme.lower() or "prior-art" in readme.lower()


def test_experiment_scale_constants():
    assert N_SEEDS >= 30
    assert TICKS >= 10_000
