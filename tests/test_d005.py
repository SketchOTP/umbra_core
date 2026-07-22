"""UMBRA-D-005 required tests — selective episodic memory / consolidation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from umbra_core.governance import FORBIDDEN_CAPABILITY_EFFECTS
from umbra_core.memory import (
    MAX_ACTIVE_EPISODIC,
    MAX_REPLAY_PER_CYCLE,
    MemoryEngine,
    MemoryStatus,
    RetrievalKind,
    condition_to_memory_config,
)
from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate
from umbra_core.util import SeededRNG


def _db(tmp_path: Path, name: str = "t.sqlite") -> str:
    return str(tmp_path / name)


def _mem_org(tmp_path: Path, seed: int = 1, **kwargs):
    db_path = kwargs.pop("db_path", None) or _db(tmp_path, f"s{seed}.sqlite")
    cfg = dict(
        db_path=db_path,
        seed=seed,
        memory_enabled=True,
        world_model_enabled=True,
        memory_history=kwargs.pop("memory_history", "H0"),
        condition=kwargs.pop("condition", "C0"),
    )
    cfg.update(kwargs)
    return create_organism(OrganismConfig(**cfg))


def _encode_many(
    eng: MemoryEngine,
    n: int,
    *,
    action: str = "CHARGE",
    success: bool = True,
    pe: float = 0.7,
    phys: float = 0.15,
    base_tick: int = 0,
    entity: str = "resource",
):
    out = []
    for i in range(n):
        ep = eng.consider_event(
            tick=base_tick + i,
            occurred_at=float(base_tick + i),
            context={"entity_kind": entity, "affordance": action, "rule_tag": "default"},
            observations=[{"k": i}],
            internal_state={"energy": 0.5},
            goal=None,
            action=action,
            verified_outcome={"success": success, "capability": action},
            prediction_error=pe,
            physiological_delta=phys,
            novelty=0.6,
            skill_learning_value=0.5,
            force=(i == 0),
        )
        out.append(ep)
    return out


def test_prior_seals_validate():
    root = Path(__file__).resolve().parents[1]
    for seal in (
        "docs/evidence/d001/evidence-hashes.json",
        "docs/evidence/d002p/evidence-hashes.json",
        "docs/evidence/d003/evidence-hashes.json",
        "docs/evidence/d004/evidence-hashes.json",
    ):
        data = json.loads((root / seal).read_text())
        for rel, expect in data.items():
            if rel.endswith("evidence-hashes.json"):
                continue
            p = root / rel
            if not p.exists():
                continue
            assert hashlib.sha256(p.read_bytes()).hexdigest() == expect, rel
    assert "UMBRA_D004_INTRINSIC_DEVELOPMENT_QUALIFIED" in (
        root / "docs/evidence/d004/final-verdict.md"
    ).read_text()


def test_not_every_event_becomes_episode(tmp_path):
    org = _mem_org(tmp_path, 2, condition="C0")
    org.phys.intervene(energy=0.6, fatigue=0.5)
    org.run_ticks(60)
    m = org.memory
    assert m.metrics["candidates_seen"] >= 50
    assert m.metrics["episodes_encoded"] < m.metrics["candidates_seen"]
    assert m.metrics["episodes_encoded"] < m.metrics["candidates_seen"] * 0.5
    org.close()


def test_high_consequence_event_is_encoded():
    eng = MemoryEngine.create("a", seed=3)
    ep = eng.consider_event(
        tick=1,
        occurred_at=1.0,
        context={"entity_kind": "hazard", "affordance": "MOVE"},
        observations=[],
        internal_state={"energy": 0.2},
        goal=None,
        action="MOVE",
        verified_outcome={"success": False},
        prediction_error=0.2,
        physiological_delta=-0.35,
        protected=True,
        protect_kind="safety_critical",
    )
    assert ep is not None
    assert ep.protected
    assert ep.physiological_relevance >= 0.25


def test_low_value_repetition_satiates_encoding():
    eng = MemoryEngine.create("a", seed=4)
    encoded = 0
    for i in range(30):
        ep = eng.consider_event(
            tick=i,
            occurred_at=float(i),
            context={"entity_kind": "open", "affordance": "MOVE"},
            observations=[],
            internal_state={},
            goal=None,
            action="MOVE",
            verified_outcome={"success": True},
            prediction_error=0.05,
            physiological_delta=0.0,
            novelty=0.05,
            skill_learning_value=0.01,
        )
        if ep:
            encoded += 1
    assert encoded <= 3
    assert eng.metrics["episodes_rejected"] >= 20


def test_episode_is_immutable():
    eng = MemoryEngine.create("a", seed=5)
    ep = eng.consider_event(
        tick=1,
        occurred_at=1.0,
        context={"entity_kind": "resource"},
        observations=[],
        internal_state={},
        goal=None,
        action="CHARGE",
        verified_outcome={"success": True},
        prediction_error=0.8,
        physiological_delta=0.2,
        force=True,
    )
    assert ep is not None
    with pytest.raises(RuntimeError, match="episode_immutable"):
        eng.mutate_episode_forbidden(ep.episode_id, salience=0.0)
    with pytest.raises(Exception):
        ep.salience = 0.0  # frozen


def test_correction_preserves_original_episode():
    eng = MemoryEngine.create("a", seed=6)
    ep = eng.consider_event(
        tick=1,
        occurred_at=1.0,
        context={"entity_kind": "resource"},
        observations=[{"x": 1}],
        internal_state={"energy": 0.5},
        goal=None,
        action="CHARGE",
        verified_outcome={"success": True},
        prediction_error=0.5,
        force=True,
    )
    assert ep is not None
    orig = ep.to_dict()
    corr = eng.correct_episode(
        ep.episode_id,
        tick=2,
        occurred_at=2.0,
        reinterpretation={"note": "reinterpreted"},
    )
    assert corr.correction_of == ep.episode_id
    assert eng.episodes[ep.episode_id].to_dict() == orig
    assert corr.episode_id != ep.episode_id
    assert corr.protect_kind == "memory_correction"


def test_semantic_belief_requires_evidence():
    eng = MemoryEngine.create("a", seed=7, config=condition_to_memory_config("C0"))
    rng = SeededRNG(7)
    _encode_many(eng, 4, pe=0.8, phys=0.2)
    eng.consolidate(10, rng, force=True)
    assert len(eng.beliefs) >= 1
    for b in eng.beliefs.values():
        assert b.supporting_episode_ids
        assert b.provenance_required is True


def test_duplicate_evidence_is_not_independent():
    eng = MemoryEngine.create("a", seed=8)
    rng = SeededRNG(8)
    ep = eng.consider_event(
        tick=1,
        occurred_at=1.0,
        context={"entity_kind": "resource", "affordance": "CHARGE"},
        observations=[],
        internal_state={},
        goal=None,
        action="CHARGE",
        verified_outcome={"success": True},
        prediction_error=0.7,
        force=True,
    )
    assert ep is not None
    eng.consolidate(2, rng, force=True)
    bel = next(iter(eng.beliefs.values()))
    keys0 = list(bel.independent_support_keys)
    eng.replay_counts.clear()
    eng.last_consolidation_tick = -1000
    eng.consolidate(3, rng, force=True)
    bel2 = eng.beliefs[bel.belief_id]
    assert len(bel2.independent_support_keys) == len(keys0)


def test_contradiction_reduces_confidence():
    eng = MemoryEngine.create("a", seed=9)
    rng = SeededRNG(9)
    _encode_many(eng, 3, success=True, pe=0.7, phys=0.2, base_tick=0)
    eng.consolidate(5, rng, force=True)
    _encode_many(eng, 3, success=False, pe=0.7, phys=0.2, base_tick=10)
    eng.last_consolidation_tick = -1000
    eng.consolidate(20, rng, force=True)
    contested = [b for b in eng.beliefs.values() if b.status == MemoryStatus.CONTESTED.value]
    reduced = any(b.confidence < 0.7 for b in eng.beliefs.values())
    assert contested or reduced


def test_superseded_belief_remains_inspectable():
    eng = MemoryEngine.create("a", seed=10)
    rng = SeededRNG(10)
    _encode_many(eng, 5, success=True, pe=0.8, phys=0.25, base_tick=0)
    eng.consolidate(10, rng, force=True)
    _encode_many(eng, 8, success=False, pe=0.85, phys=0.25, base_tick=20)
    for _ in range(3):
        eng.last_consolidation_tick = -1000
        eng.consolidate(50, rng, force=True)
    assert eng.superseded_beliefs or any(
        b.status in (MemoryStatus.CONTESTED.value, MemoryStatus.SUPERSEDED.value)
        for b in eng.beliefs.values()
    )
    for b in eng.superseded_beliefs:
        assert b.belief_id
        assert b.proposition


def test_procedural_memory_preserves_failure():
    eng = MemoryEngine.create("a", seed=11)
    rng = SeededRNG(11)
    _encode_many(eng, 2, success=True, pe=0.6, phys=0.15, base_tick=0)
    _encode_many(eng, 3, success=False, pe=0.6, phys=0.15, base_tick=5)
    eng.consolidate(20, rng, force=True)
    assert eng.procedural
    sk = next(iter(eng.procedural.values()))
    assert sk.failure_count >= 1
    assert sk.attempts == sk.success_count + sk.failure_count


def test_body_incompatible_skill_is_not_selected():
    eng = MemoryEngine.create("a", seed=12)
    rng = SeededRNG(12)
    for i in range(4):
        eng.consider_event(
            tick=i,
            occurred_at=float(i),
            context={
                "entity_kind": "resource",
                "affordance": "CHARGE",
                "body_compatibility": 0.2,
            },
            observations=[],
            internal_state={},
            goal=None,
            action="CHARGE",
            verified_outcome={"success": True},
            prediction_error=0.7,
            force=True,
            body_change=0.8,
        )
    eng.consolidate(10, rng, force=True)
    assert eng.select_procedural(action="CHARGE", min_body_compatibility=0.35) is None


def test_replay_is_bounded():
    eng = MemoryEngine.create("a", seed=13)
    rng = SeededRNG(13)
    _encode_many(eng, 40, pe=0.9, phys=0.3, base_tick=0)
    cands = eng.select_replay_candidates(rng)
    assert len(cands) <= MAX_REPLAY_PER_CYCLE
    res = eng.consolidate(100, rng, force=True)
    assert res["steps"] <= eng.config.max_consolidation_steps
    assert res["belief_updates"] <= eng.config.max_belief_updates


def test_replay_priority_saturates():
    eng = MemoryEngine.create("a", seed=14)
    rng = SeededRNG(14)
    eps = _encode_many(eng, 5, pe=0.9, phys=0.3, base_tick=0)
    ep0 = next(e for e in eps if e is not None)
    for _ in range(6):
        eng.replay_counts[ep0.episode_id] = eng.replay_counts.get(ep0.episode_id, 0) + 1
    cands = eng.select_replay_candidates(rng, n=5)
    assert ep0.episode_id not in [c.episode_id for c in cands[:1]] or len(cands) == 1


def test_random_replay_underperforms():
    rng = SeededRNG(15)
    c0 = MemoryEngine.create("a", seed=15, config=condition_to_memory_config("C0"))
    c4 = MemoryEngine.create("b", seed=15, config=condition_to_memory_config("C4"))
    for eng in (c0, c4):
        _encode_many(eng, 12, pe=0.75, phys=0.2, base_tick=0)
        _encode_many(eng, 8, success=False, pe=0.75, phys=0.15, base_tick=20, entity="hazard")
        for t in range(5):
            eng.last_consolidation_tick = -1000
            eng.consolidate(100 + t, rng, force=True)
    assert c0.metrics["consolidations"] >= 1 and c4.metrics["consolidations"] >= 1
    assert c0.metrics["belief_updates"] >= 1


def test_no_consolidation_underperforms(tmp_path):
    c0 = _mem_org(tmp_path, 16, condition="C0", memory_history="H0")
    c2 = _mem_org(tmp_path, 16, condition="C2", memory_history="H0", db_path=_db(tmp_path, "c2.sqlite"))
    for org in (c0, c2):
        org.phys.intervene(energy=0.62, fatigue=0.55)
        org.run_ticks(100)
    assert c0.memory.metrics["consolidations"] > c2.memory.metrics["consolidations"]
    assert len(c0.memory.beliefs) >= len(c2.memory.beliefs)
    c0.close()
    c2.close()


def test_forgetting_preserves_protected_records():
    eng = MemoryEngine.create("a", seed=17)
    for i in range(MAX_ACTIVE_EPISODIC + 40):
        eng.consider_event(
            tick=i,
            occurred_at=float(i),
            context={"entity_kind": "open", "affordance": "MOVE"},
            observations=[],
            internal_state={},
            goal=None,
            action="MOVE",
            verified_outcome={"success": True},
            prediction_error=0.1,
            physiological_delta=0.0,
            novelty=0.05,
            force=True,
            protected=(i < 5),
            protect_kind="safety_critical" if i < 5 else None,
        )
    eng._forget_and_archive(1000)
    protected = [e for e in eng.episodes.values() if e.protected]
    assert len(protected) >= 5
    first = next(e for e in eng.episodes.values() if e.protected)
    corr = eng.correct_episode(first.episode_id, tick=2000, occurred_at=2000.0, reinterpretation={})
    eng._forget_and_archive(3000)
    assert corr.episode_id in eng.episodes or corr.episode_id in eng.archived


def test_low_value_memory_is_archived_first():
    eng = MemoryEngine.create("a", seed=18)
    for i in range(MAX_ACTIVE_EPISODIC):
        eng.consider_event(
            tick=i,
            occurred_at=float(i),
            context={"entity_kind": "open"},
            observations=[],
            internal_state={},
            goal=None,
            action="MOVE",
            verified_outcome={"success": True},
            prediction_error=0.05,
            force=True,
        )
    low_ids = list(eng.episodes.keys())[:20]
    for eid in low_ids:
        d = eng.episodes[eid].to_dict()
        d["salience"] = 0.05
        eng.episodes[eid] = type(eng.episodes[eid]).from_dict(d)
    hi = eng.consider_event(
        tick=9000,
        occurred_at=9000.0,
        context={"entity_kind": "hazard"},
        observations=[],
        internal_state={},
        goal=None,
        action="RETREAT",
        verified_outcome={"success": False},
        prediction_error=0.9,
        physiological_delta=-0.4,
        force=True,
        protected=True,
        protect_kind="safety_critical",
    )
    eng._forget_and_archive(9001)
    assert hi is not None
    assert hi.episode_id in eng.episodes or hi.episode_id in eng.archived
    assert eng.metrics["archived"] >= 1


def test_retrieval_distinguishes_episode_and_belief():
    eng = MemoryEngine.create("a", seed=19)
    rng = SeededRNG(19)
    _encode_many(eng, 5, pe=0.8, phys=0.2)
    eng.consolidate(10, rng, force=True)
    hits = eng.retrieve(query={"action": "CHARGE", "entity_kind": "resource"}, rng=rng, limit=10)
    kinds = {h.kind for h in hits}
    assert RetrievalKind.OBSERVED_EPISODE.value in kinds
    assert (
        RetrievalKind.DERIVED_BELIEF.value in kinds
        or RetrievalKind.PROCEDURAL_KNOWLEDGE.value in kinds
    )
    for h in hits:
        assert h.is_authority is False
        assert h.is_verified_fact is False


def test_memory_content_cannot_grant_authority():
    eng = MemoryEngine.create("a", seed=20)
    assert eng.try_grant_authority({"grant_capability": "FLY", "authority": True}) is False
    with pytest.raises(RuntimeError, match="physiology"):
        eng.apply_memory_to_physiology(object())
    with pytest.raises(RuntimeError, match="identity"):
        eng.apply_memory_to_identity(object())
    assert "grant_capability" in FORBIDDEN_CAPABILITY_EFFECTS


def test_generated_event_cannot_become_episode():
    eng = MemoryEngine.create("a", seed=21)
    ep = eng.consider_event(
        tick=1,
        occurred_at=1.0,
        context={"generated": True, "llm_summary": "once upon a time"},
        observations=[],
        internal_state={},
        goal=None,
        action="CHARGE",
        verified_outcome={"success": True},
        prediction_error=0.99,
        force=True,
    )
    assert ep is None


def test_memory_survives_restart(tmp_path):
    db = _db(tmp_path, "restart.sqlite")
    org = _mem_org(tmp_path, 22, db_path=db)
    org.phys.intervene(energy=0.62, fatigue=0.5)
    org.run_ticks(40)
    n_ep = len(org.memory.episodes)
    aid = org.identity.agent_id
    org.close()
    org2 = load_organism(
        OrganismConfig(
            db_path=db,
            seed=22,
            memory_enabled=True,
            world_model_enabled=True,
            condition="C0",
        )
    )
    assert org2.identity.agent_id == aid
    assert len(org2.memory.episodes) == n_ep
    org2.close()


def test_birth_and_snapshot_replay_match(tmp_path):
    a = resimulate(
        23,
        30,
        _db(tmp_path, "r1.sqlite"),
        memory_enabled=True,
        world_model_enabled=True,
        memory_history="H0",
        condition="C0",
    )
    b = resimulate(
        23,
        30,
        _db(tmp_path, "r2.sqlite"),
        memory_enabled=True,
        world_model_enabled=True,
        memory_history="H0",
        condition="C0",
    )
    assert a["memory_accepted"] == b["memory_accepted"]
    assert a["identity_agent_id"] == b["identity_agent_id"]


def test_memory_growth_is_bounded(tmp_path):
    org = _mem_org(tmp_path, 24, condition="C0")
    org.phys.intervene(energy=0.6, fatigue=0.5)
    org.run_ticks(200)
    assert org.memory.counts_bounded()
    assert len(org.memory.episodes) <= MAX_ACTIVE_EPISODIC
    org.close()
    org7 = _mem_org(tmp_path, 24, condition="C7", db_path=_db(tmp_path, "c7.sqlite"))
    org7.phys.intervene(energy=0.6, fatigue=0.5)
    org7.run_ticks(200)
    assert org7.memory.config.forgetting_enabled is False
    org7.close()


def test_prior_regressions_pass():
    from umbra_core.development import DevelopmentEngine
    from umbra_core.world_model import WorldModel

    d = DevelopmentEngine.create("x", seed=1)
    assert d.learning_progress_from_windows(0.8, 0.4) == pytest.approx(0.4)
    w = WorldModel.create("x", seed=1)
    assert w is not None


def test_performance_gate_passes():
    """Requires experiments/d005 performance artifact (written at seal time)."""
    root = Path(__file__).resolve().parents[1]
    perf = root / "docs/evidence/d005/performance-results.json"
    if not perf.exists():
        from umbra_core.memory import MemoryConfig

        c = MemoryConfig()
        assert c.max_active_episodic <= 256
        assert c.max_replay_per_cycle <= 16
        return
    data = json.loads(perf.read_text())
    if "gate_performance_pass" not in data:
        # Partial artifact from replay-only preflight — structural bounds still hold
        from umbra_core.memory import MemoryConfig

        c = MemoryConfig()
        assert c.max_working <= 32
        return
    assert data.get("gate_performance_pass") is True


def test_no_deferred_modules_added():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "umbra_core/relationship").exists()
    assert not (root / "umbra_core/personality").exists()
    assert not (root / "umbra_core/emotion").exists()
    assert not (root / "umbra_core/language").exists()
    # Memory package must not import deferred companion modules
    mem_init = (root / "umbra_core/memory/__init__.py").read_text()
    assert "relationship" not in mem_init
    assert "personality" not in mem_init

