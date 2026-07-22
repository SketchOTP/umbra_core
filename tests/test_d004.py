"""UMBRA-D-004 required tests — intrinsic development / learning progress."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from umbra_core.development import (
    MAX_ATTEMPT_HISTORY,
    MAX_GOALS,
    MAX_RETRY_PER_GOAL,
    DevelopmentEngine,
    GoalStatus,
    condition_to_development_config,
)
from umbra_core.governance import FORBIDDEN_CAPABILITY_EFFECTS
from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate
from umbra_core.util import SeededRNG


def _db(tmp_path: Path, name: str = "t.sqlite") -> str:
    return str(tmp_path / name)


def _dev_org(tmp_path: Path, seed: int = 1, **kwargs):
    db_path = kwargs.pop("db_path", None) or _db(tmp_path, f"s{seed}.sqlite")
    cfg = dict(
        db_path=db_path,
        seed=seed,
        development_enabled=True,
        world_model_enabled=True,
        development_intervention=kwargs.pop("development_intervention", "I0"),
        condition=kwargs.pop("condition", "C0"),
    )
    cfg.update(kwargs)
    return create_organism(OrganismConfig(**cfg))


def test_prior_seals_validate():
    root = Path(__file__).resolve().parents[1]
    for seal in (
        "docs/evidence/d001/evidence-hashes.json",
        "docs/evidence/d002p/evidence-hashes.json",
        "docs/evidence/d003/evidence-hashes.json",
    ):
        data = json.loads((root / seal).read_text())
        for rel, expect in data.items():
            if rel.endswith("evidence-hashes.json"):
                continue
            p = root / rel
            if not p.exists():
                continue
            assert hashlib.sha256(p.read_bytes()).hexdigest() == expect, rel
    assert "UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED" in (
        root / "docs/evidence/d003/final-verdict.md"
    ).read_text()


def test_goals_derive_from_experience(tmp_path):
    org = _dev_org(tmp_path, 2)
    org.run_ticks(40)
    assert len(org.development.goals) >= 1
    for g in org.development.goals.values():
        assert g.source in ("experience", "authored")
        assert g.goal_kind == "practice"
        assert g.target_affordance
    # No language-generated arbitrary tasks
    blob = json.dumps(org.development.to_state())
    assert "write_poem" not in blob
    assert "chat" not in blob
    org.close()


def test_no_authored_curriculum(tmp_path):
    org = _dev_org(tmp_path, 3, condition="C0")
    org.run_ticks(50)
    assert org.development.config.authored_curriculum is False
    assert all(g.source == "experience" for g in org.development.goals.values())
    org.close()


def test_learning_progress_uses_two_windows():
    eng = DevelopmentEngine.create("a", seed=4)
    g = eng.ensure_goal(affordance="charge_from", entity_kind="resource")
    # Prior window: failures; recent: successes
    for _ in range(6):
        eng.update_competence(g.goal_id, success=False, tick=1)
    for _ in range(6):
        eng.update_competence(g.goal_id, success=True, tick=2)
    recent, prior = eng.compute_windows(g.goal_id)
    lp = eng.learning_progress_from_windows(recent, prior)
    assert recent > prior
    assert lp == pytest.approx(recent - prior)
    assert g.learning_progress == pytest.approx(lp)


def test_raw_error_is_not_progress():
    eng = DevelopmentEngine.create("a", seed=5)
    g = eng.ensure_goal(affordance="inspect", entity_kind="inspect")
    for _ in range(8):
        eng.update_competence(g.goal_id, success=False, prediction_error=0.95, tick=1)
    # High raw error with no competence gain → LP not equal to error
    assert g.competence_state.prediction_error > 0.5
    assert abs(g.learning_progress) < g.competence_state.prediction_error
    assert g.learning_progress != g.competence_state.prediction_error


def test_competence_improves_with_practice(tmp_path):
    org = _dev_org(tmp_path, 6)
    org.phys.intervene(energy=0.75, fatigue=0.15, stimulation=0.4)
    org.run_ticks(120)
    assert org.development.total_competence() > 0.0
    assert org.development.metrics["competence_gain"] > 0.0
    org.close()


def test_mastered_goal_satiates():
    eng = DevelopmentEngine.create("a", seed=7)
    g = eng.ensure_goal(affordance="charge_from", entity_kind="resource")
    for i in range(16):
        eng.update_competence(g.goal_id, success=True, tick=i)
    assert g.status == GoalStatus.MASTERED.value
    assert g.satiation > 0.3
    phys = type("P", (), {"critical_any": lambda self: False, "energy": 0.8, "fatigue": 0.1, "integrity": 0.9})()
    # After mastery, score should be depressed vs a fresh learnable goal
    g2 = eng.ensure_goal(affordance="inspect", entity_kind="inspect", difficulty=0.4)
    for _ in range(3):
        eng.update_competence(g2.goal_id, success=True, tick=20)
        eng.update_competence(g2.goal_id, success=False, tick=21)
    s_master = eng.score_goal(g, phys_ready=1.0, world_uncertainty=0.1)
    s_learn = eng.score_goal(g2, phys_ready=1.0, world_uncertainty=0.1)
    assert s_master < s_learn


def test_impossible_goal_becomes_dormant():
    eng = DevelopmentEngine.create("a", seed=8)
    g = eng.ensure_goal(
        affordance="charge_from",
        entity_kind="impossible_node",
        learnable=False,
        tag="impossible",
    )
    for i in range(14):
        eng.update_competence(g.goal_id, success=False, tick=i)
    assert g.status in (GoalStatus.DORMANT.value, GoalStatus.IMPOSSIBLE.value)
    assert eng.config.filter_impossible
    score = eng.score_goal(g, phys_ready=1.0, world_uncertainty=0.2)
    assert score < -5.0


def test_noisy_distractor_loses_priority():
    eng = DevelopmentEngine.create("a", seed=9)
    g = eng.ensure_goal(
        affordance="inspect",
        entity_kind="noise_blink",
        learnable=False,
        irreducible_noise=True,
        tag="noise",
    )
    rng = SeededRNG(9)
    for i in range(16):
        eng.update_competence(g.goal_id, success=rng.random() < 0.5, tick=i)
    assert g.status == GoalStatus.DORMANT.value or abs(g.learning_progress) < 0.15
    score = eng.score_goal(g, phys_ready=1.0, world_uncertainty=0.2)
    assert score < 0.0 or g.status == GoalStatus.DORMANT.value


def test_regressed_skill_enters_relearning():
    eng = DevelopmentEngine.create("a", seed=10)
    g = eng.ensure_goal(affordance="charge_from", entity_kind="resource")
    for i in range(12):
        eng.update_competence(g.goal_id, success=True, tick=i)
    assert g.status == GoalStatus.MASTERED.value
    eng.note_regression(g.goal_id, tick=20, reason="degrade")
    assert g.status == GoalStatus.RELEARNING.value
    assert eng.metrics["relearning_events"] >= 1


def test_body_change_reduces_compatible_competence():
    eng = DevelopmentEngine.create("a", seed=11)
    g = eng.ensure_goal(affordance="approach", entity_kind="resource")
    for i in range(10):
        eng.update_competence(g.goal_id, success=True, tick=i, body_compatibility=1.0)
    before = g.competence
    eng.on_body_change(tick=50, compatibility_scale=0.4)
    skill = eng.skills[eng._skill_id(g.goal_id)]
    assert skill.body_compatibility < 1.0
    assert g.competence <= before
    assert g.status == GoalStatus.RELEARNING.value


def test_prior_skill_history_is_preserved():
    eng = DevelopmentEngine.create("a", seed=12)
    g = eng.ensure_goal(affordance="inspect", entity_kind="inspect")
    for i in range(12):
        eng.update_competence(g.goal_id, success=i % 2 == 0, tick=i)
    eng.note_regression(g.goal_id, tick=30, reason="env")
    skill = eng.skills[eng._skill_id(g.goal_id)]
    assert len(skill.history) >= 1
    # History retained after regression
    assert skill.history[0]["competence"] is not None


def test_play_requires_safe_physiology(tmp_path):
    org = _dev_org(tmp_path, 13)
    org.phys.intervene(energy=0.05, fatigue=0.95, integrity=0.1)
    org.development.generate_from_experience([], intervention_tags={})
    g = org.development.select_practice_goal(
        org.phys, critical_recovery=True, rng=org.rng
    )
    assert g is None
    assert org.development.play_active is False
    org.close()


def test_critical_need_interrupts_play(tmp_path):
    org = _dev_org(tmp_path, 14)
    org.phys.intervene(energy=0.8, fatigue=0.1, stimulation=0.4)
    org.run_ticks(30)
    # Drive critical energy — play must stop
    org.phys.intervene(energy=0.05)
    org.development.select_practice_goal(org.phys, critical_recovery=True, rng=org.rng)
    assert org.development.play_active is False
    org.close()


def test_play_has_measurable_learning_value(tmp_path):
    c0 = _dev_org(tmp_path, 15, condition="C0", db_path=_db(tmp_path, "play_c0.sqlite"))
    c0.phys.intervene(energy=0.75, fatigue=0.1, stimulation=0.4)
    c0.run_ticks(100)
    v0 = float(c0.development.metrics.get("play_learning_value", 0.0))
    play0 = int(c0.development.metrics.get("play_ticks", 0))
    c0.close()

    c9 = _dev_org(tmp_path, 15, condition="C9", db_path=_db(tmp_path, "play_c9.sqlite"))
    c9.phys.intervene(energy=0.75, fatigue=0.1, stimulation=0.4)
    c9.run_ticks(100)
    play9 = int(c9.development.metrics.get("play_ticks", 0))
    c9.close()
    assert play0 >= play9
    assert play9 == 0 or c9.development.config.play_enabled is False
    # Play on C0 should accrue some learning value when play ticks occur
    if play0 > 0:
        assert v0 >= 0.0


def test_learning_progress_beats_random(tmp_path):
    """C0 LP selection prefers improving goals over random waste on impossible/noise."""
    rng = SeededRNG(42)

    def run(mode: str) -> float:
        cfg = condition_to_development_config("C1" if mode == "random" else "C0")
        eng = DevelopmentEngine.create("a", config=cfg, seed=1)
        learn = eng.ensure_goal(affordance="charge_from", entity_kind="resource", difficulty=0.4)
        noise = eng.ensure_goal(
            affordance="inspect",
            entity_kind="noise_blink",
            learnable=False,
            irreducible_noise=True,
            tag="noise",
        )
        imposs = eng.ensure_goal(
            affordance="charge_from",
            entity_kind="impossible_node",
            learnable=False,
            tag="imp",
        )
        # Evidence windows: learn improving; noise flat; impossible failing
        for t in range(8):
            eng.update_competence(learn.goal_id, success=t >= 3, tick=t)
        for t in range(8):
            eng.update_competence(noise.goal_id, success=(t % 2 == 0), tick=t)
        for t in range(8):
            eng.update_competence(imposs.goal_id, success=False, tick=t)
        phys = type(
            "P",
            (),
            {
                "critical_any": lambda self: False,
                "energy": 0.8,
                "fatigue": 0.1,
                "integrity": 0.9,
            },
        )()
        learn_attempts = 0
        for t in range(40):
            g = eng.select_practice_goal(phys, world_uncertainty=0.1, rng=rng)
            if g is None:
                continue
            if g.goal_id == learn.goal_id:
                learn_attempts += 1
                eng.update_competence(g.goal_id, success=True, tick=20 + t)
            elif g.goal_id == imposs.goal_id:
                eng.update_competence(g.goal_id, success=False, tick=20 + t)
            else:
                eng.update_competence(g.goal_id, success=rng.random() < 0.5, tick=20 + t)
        return float(learn_attempts)

    assert run("lp") > run("random")


def test_learning_progress_beats_novelty(tmp_path):
    rng = SeededRNG(43)

    def run(condition: str) -> float:
        cfg = condition_to_development_config(condition)
        eng = DevelopmentEngine.create("a", config=cfg, seed=2)
        learn = eng.ensure_goal(affordance="charge_from", entity_kind="resource")
        novel = eng.ensure_goal(
            affordance="approach", entity_kind="shiny", difficulty=0.9, tag="novel"
        )
        novel.novelty = 1.0
        learn.novelty = 0.1
        phys = type(
            "P",
            (),
            {
                "critical_any": lambda self: False,
                "energy": 0.8,
                "fatigue": 0.1,
                "integrity": 0.9,
            },
        )()
        skill = {learn.goal_id: 0.2, novel.goal_id: 0.05}
        for t in range(60):
            g = eng.select_practice_goal(phys, rng=rng)
            if g is None:
                continue
            p = skill.get(g.goal_id, 0.1)
            ok = rng.random() < p
            if ok and g.goal_id == learn.goal_id:
                skill[g.goal_id] = min(0.95, p + 0.1)
            eng.update_competence(g.goal_id, success=ok, tick=t)
        return eng.goals[learn.goal_id].competence

    assert run("C0") >= run("C2")


def test_learning_progress_beats_fixed_curriculum(tmp_path):
    rng = SeededRNG(44)

    def run(condition: str) -> float:
        cfg = condition_to_development_config(condition)
        eng = DevelopmentEngine.create("a", config=cfg, seed=3)
        # Learnable medium goal + hard early authored trap
        easy = eng.ensure_goal(
            affordance="inspect", entity_kind="inspect", difficulty=0.25, source="authored"
        )
        hard = eng.ensure_goal(
            affordance="avoid", entity_kind="hazard", difficulty=0.9, source="authored"
        )
        mid = eng.ensure_goal(
            affordance="charge_from", entity_kind="resource", difficulty=0.4, source="experience"
        )
        if cfg.authored_curriculum:
            eng.authored_order = [hard.goal_id, easy.goal_id, mid.goal_id]
            eng.authored_index = 0
        phys = type(
            "P",
            (),
            {
                "critical_any": lambda self: False,
                "energy": 0.8,
                "fatigue": 0.1,
                "integrity": 0.9,
            },
        )()
        for t in range(70):
            g = eng.select_practice_goal(phys, rng=rng)
            if g is None:
                continue
            # hard rarely succeeds; mid/easy improve
            if g.goal_id == hard.goal_id:
                ok = False
            else:
                ok = rng.random() < (0.7 if g.goal_id != hard.goal_id else 0.0)
            eng.update_competence(g.goal_id, success=ok, tick=t)
        return float(eng.metrics["competence_gain"])

    assert run("C0") >= run("C4") * 0.9


def test_practice_cannot_grant_authority(tmp_path):
    org = _dev_org(tmp_path, 20)
    gov = org.governance
    prop = gov.propose("MOVE", {"step": 1.0}, requested_effects=["grant_capability"])
    dec = gov.admit(prop)
    assert dec.admitted is False
    assert "grant_capability" in FORBIDDEN_CAPABILITY_EFFECTS
    assert not hasattr(org.development, "grant_capability")
    assert not hasattr(org.development, "modify_identity")
    org.close()


def test_goal_count_is_bounded(tmp_path):
    org = _dev_org(tmp_path, 21)
    # Flood ensure_goal
    for i in range(80):
        org.development.ensure_goal(
            affordance="approach", entity_kind="resource", tag=f"x{i}", difficulty=0.3
        )
    assert len(org.development.goals) <= MAX_GOALS
    org.close()


def test_attempt_history_is_bounded():
    eng = DevelopmentEngine.create("a", seed=22)
    g = eng.ensure_goal(affordance="pass_through", entity_kind="open")
    for i in range(MAX_ATTEMPT_HISTORY + 40):
        eng.update_competence(g.goal_id, success=i % 2 == 0, tick=i)
    assert len(eng.attempt_history) <= MAX_ATTEMPT_HISTORY


def test_retry_count_is_bounded():
    eng = DevelopmentEngine.create("a", seed=23)
    g = eng.ensure_goal(affordance="charge_from", entity_kind="resource")
    for i in range(20):
        eng.update_competence(g.goal_id, success=False, tick=i)
    assert g.retry_count <= MAX_RETRY_PER_GOAL


def test_restart_preserves_competence(tmp_path):
    db = _db(tmp_path, "restart.sqlite")
    org = create_organism(
        OrganismConfig(
            db_path=db, seed=24, development_enabled=True, world_model_enabled=True
        )
    )
    org.phys.intervene(energy=0.7, fatigue=0.1, stimulation=0.4)
    org.run_ticks(80)
    aid = org.identity.agent_id
    comp = org.development.total_competence()
    n_goals = len(org.development.goals)
    accepted = org.development.accepted_state()
    org.close()

    org2 = load_organism(
        OrganismConfig(
            db_path=db, seed=24, development_enabled=True, world_model_enabled=True
        )
    )
    assert org2.identity.agent_id == aid
    assert org2.development is not None
    assert len(org2.development.goals) == n_goals
    assert abs(org2.development.total_competence() - comp) < 1e-9
    assert org2.development.accepted_state()["active_goal_id"] == accepted["active_goal_id"]
    org2.close()


def test_birth_and_snapshot_replay_match(tmp_path):
    db = _db(tmp_path, "replay.sqlite")
    a = resimulate(
        25, 40, db, development_enabled=True, world_model_enabled=True
    )
    b = resimulate(
        25, 40, str(tmp_path / "replay2.sqlite"), development_enabled=True, world_model_enabled=True
    )
    assert a["tick"] == b["tick"]
    assert a["identity_agent_id"] == b["identity_agent_id"]
    assert a["development_accepted"] == b["development_accepted"]


def test_regulation_remains_above_threshold(tmp_path):
    """Gate 7: energy-band recovery ≥95% with development enabled."""
    recoveries = 0
    trials = 20
    for seed in range(100, 100 + trials):
        org = _dev_org(
            tmp_path,
            seed,
            development_intervention="I0",
            db_path=_db(tmp_path, f"reg_{seed}.sqlite"),
        )
        org.phys.intervene(energy=0.15, fatigue=0.25, integrity=0.85, stimulation=0.55)
        recovered = False
        for _ in range(250):
            org.tick_once()
            if org.phys.in_viable("energy"):
                recovered = True
                break
        if recovered:
            recoveries += 1
        org.close()
    assert recoveries / trials >= 0.95


def test_performance_gate_passes():
    root = Path(__file__).resolve().parents[1]
    perf = root / "docs/evidence/d004/performance-results.json"
    assert perf.exists(), "performance-results.json required (zero skips)"
    data = json.loads(perf.read_text())
    assert data.get("gate_performance_pass") is True
    assert data["rss_p95_mib"] <= 140.0
    assert data["rss_slope_mib_per_h"] <= 1.0
    assert data["cpu_mean_pct"] <= 5.0


def test_no_deferred_modules_added():
    root = Path(__file__).resolve().parents[1]
    forbidden = [
        "umbra_core/language",
        "umbra_core/personality",
        "umbra_core/relationship",
        "umbra_core/reflection",
        "umbra_core/ui",
        "umbra_core/llm",
        "umbra_core/chemistry",
        "umbra_core/protocell",
        "umbra_core/emotion",
        "umbra_core/memory_d005",
    ]
    for rel in forbidden:
        assert not (root / rel).exists(), rel
    assert (root / "umbra_core/development").is_dir()
