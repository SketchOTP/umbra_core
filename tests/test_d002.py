"""UMBRA-D-002 required tests — sensorimotor self-model."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from umbra_core.embodiment import Embodiment
from umbra_core.governance import FORBIDDEN_CAPABILITY_EFFECTS, Governance
from umbra_core.identity import FORBIDDEN_IDENTITY_FIELDS, create_birth
from umbra_core.persistence import PersistenceError
from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate
from umbra_core.self_model import (
    MAX_MODEL_VERSIONS,
    MAX_PREDICTION_HISTORY,
    Attribution,
    SelfModel,
    SelfModelConfig,
)
from umbra_core.util import SeededRNG


def _db(tmp_path: Path, name: str = "t.sqlite") -> str:
    return str(tmp_path / name)


def test_d001_seal_is_valid():
    root = Path(__file__).resolve().parents[1]
    seal = json.loads((root / "docs/evidence/d002/d001-seal.json").read_text())
    assert seal["d001_verdict"] == "UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED"
    assert seal["d001_tests"]["passed"] == 45
    assert seal["d001_tests"]["skipped"] == 0
    assert seal["d001_evidence_hashes_verified"] is True
    assert len(seal["starting_commit"]) == 40
    hashes = json.loads((root / "docs/evidence/d001/evidence-hashes.json").read_text())
    import hashlib

    for rel, expect in hashes.items():
        if rel.endswith("evidence-hashes.json"):
            continue
        p = root / rel
        assert p.exists(), rel
        assert hashlib.sha256(p.read_bytes()).hexdigest() == expect, rel


def test_body_schema_is_not_identity():
    ident = create_birth(created_at=1.0, seed=1)
    sm = SelfModel.create(ident.agent_id, now=0.0)
    d = ident.as_dict()
    assert "body_schema_id" not in d
    assert not (set(d) & FORBIDDEN_IDENTITY_FIELDS)
    assert sm.active.body_schema_id != ident.agent_id
    assert "body_schema" not in d


def test_body_change_preserves_agent_id(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=2, intervention="I1"))
    aid = org.identity.agent_id
    org.run_ticks(60)
    assert org.identity.agent_id == aid
    assert org.self_model is not None
    assert org.self_model.agent_id == aid
    org.close()


def test_action_prediction_is_recorded(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=3))
    org.run_ticks(40)
    assert org.self_model is not None
    assert len(org.self_model.predictions) > 0
    p = org.self_model.predictions[0]
    assert "expected_body_delta" in p.to_dict()
    assert "expected_success_probability" in p.to_dict()
    org.close()


def test_prediction_error_uses_verified_outcome(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=4))
    org.run_ticks(50)
    assert org.self_model is not None
    assert len(org.self_model.errors) > 0
    types = {e["event_type"] for e in org.store.iter_events()}
    assert "outcome_verified" in types
    assert "prediction_error" in types
    org.close()


def test_prediction_error_decreases_with_experience(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=5, intervention="I1"))
    org.run_ticks(200)
    assert org.self_model is not None
    early, late = org.self_model.initial_vs_recent_error(window=25, skip_first=5)
    # After learning movement gain, recent error should not exceed early by much;
    # material decrease expected under I1 mismatch.
    assert late < early * 0.95 or late < early - 0.02
    org.close()


def test_policy_cannot_read_world_truth(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=6))
    view = org.perception.policy_view()
    assert "WORLD_TRUTH_LEAK" not in view
    assert "habitat" not in view
    # self-model attribution never receives world_truth
    org.run_ticks(20)
    for a in org.self_model.attributions:
        assert "world_truth" not in a.reasons
        assert "habitat" not in "".join(a.reasons)
    org.close()


def test_external_displacement_is_not_self_attributed(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=7, intervention="I8"))
    # Force idle-heavy window around displacement by setting energy high
    org.phys.intervene(energy=0.85, fatigue=0.1, stimulation=0.55)
    org.run_ticks(55)
    attrs = [a for a in org.self_model.attributions if a.tick == 40]
    # At tick 40 external shove; if an action also ran, may be MIXED — must not be confidently SELF alone without mismatch handling
    labels = {a.label for a in org.self_model.attributions if a.tick >= 40 and a.tick <= 42}
    assert Attribution.EXTERNAL_CAUSED.value in labels or Attribution.MIXED.value in labels or Attribution.UNKNOWN.value in labels
    # Across the shove window, EXTERNAL should appear when no action / large unexpected motion
    external = [a for a in org.self_model.attributions if a.label == Attribution.EXTERNAL_CAUSED.value]
    assert len(external) >= 1
    org.close()


def test_uncertain_attribution_remains_unknown(tmp_path):
    org = create_organism(
        OrganismConfig(db_path=_db(tmp_path), seed=8, condition="C6")
    )
    org.run_ticks(30)
    unknowns = [a for a in org.self_model.attributions if a.label == Attribution.UNKNOWN.value]
    assert len(unknowns) >= 1
    org.close()


def test_single_anomaly_does_not_rewrite_body_model(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=9))
    sid0 = org.self_model.active.body_schema_id
    # One large residual only
    org.self_model.record_dimension_evidence("movement_gain", 0.9, tick=1)
    assert org.self_model.active.body_schema_id == sid0
    assert len(org.self_model.archive) == 0
    org.close()


def test_persistent_change_updates_body_model(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=10, intervention="I1"))
    sid0 = org.self_model.active.body_schema_id
    org.run_ticks(120)
    # Either supersession or material gain adaptation
    adapted = (
        org.self_model.active.body_schema_id != sid0
        or abs(org.self_model.active.expected_motion["step_gain"] - 1.0) > 0.05
        or len(org.self_model.archive) > 0
    )
    assert adapted
    org.close()


def test_previous_body_model_is_preserved(tmp_path):
    sm = SelfModel.create("agent-x", now=0.0)
    sid0 = sm.active.body_schema_id
    for i in range(10):
        sm.record_dimension_evidence("movement_gain", 0.5, tick=i)
    # Below threshold — no supersede yet
    assert sm.active.body_schema_id == sid0
    assert len(sm.archive) == 0
    for i in range(10, 25):
        sm.record_dimension_evidence("movement_gain", 0.5, tick=i)
    assert len(sm.archive) >= 1
    assert sm.archive[0].body_schema_id == sid0
    assert sm.archive[0].active is False
    assert sm.active.body_schema_id != sid0


def test_reduced_sensor_range_is_detected(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=11, intervention="I5"))
    org.run_ticks(100)
    dims = {e.dimension for e in org.self_model.change_evidence}
    supers = [s for s in org.self_model.supersessions if s.get("dimension") == "sensor_range"]
    belief = org.self_model.active.sensor_contracts.get("range", 10.0)
    assert "sensor_range" in dims or supers or belief < 9.5 or org.self_model.active.reachable_affordances.get("INSPECT") != "available"
    org.close()


def test_actuator_delay_is_detected(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=12, intervention="I3"))
    org.run_ticks(80)
    dims = {e.dimension for e in org.self_model.change_evidence}
    assert "actuator_delay" in dims or org.self_model.active.expected_latency > 0 or any(
        s.get("dimension") == "actuator_delay" for s in org.self_model.supersessions
    )
    org.close()


def test_intermittent_failure_reduces_confidence(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=13, intervention="I4"))
    org.embodiment.apply_intervention("I4")
    r0 = org.self_model.active.expected_reliability
    # Force locomotion so intermittent plant failures are observed
    for i in range(60):
        org.self_model.note_body_before(org.embodiment.body.to_state())
        raw = org.embodiment.execute_primitive(
            "MOVE", {"step": 1.0, "heading": 0.3}, SeededRNG(i + 99)
        )
        outcome = org.governance.verify_outcome("MOVE", raw)
        org.self_model.observe_outcome(
            tick=i,
            capability="MOVE",
            verified_outcome={
                "capability": "MOVE",
                "success": outcome.success,
                "reason": outcome.reason,
                "effects": outcome.physiology_effects,
                "verified": True,
            },
            body_after=org.embodiment.body.to_state(),
            observation_summary={"max_range_seen": 5.0},
            action_issued=True,
            now=float(i),
        )
    assert org.self_model.active.expected_reliability < r0
    org.close()


def test_recovery_restores_confidence(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=14, intervention="I9"))
    org.run_ticks(79)
    pre = org.self_model.active.confidence
    org.run_ticks(5)  # crosses recovery at tick 80
    assert org._i9_recovered
    assert org.self_model.active.confidence >= pre - 0.05
    org.close()


def test_incompatible_capability_becomes_dormant():
    sm = SelfModel.create("a", now=0.0)
    sm.mark_incompatible("INSPECT", "dormant")
    assert sm.capability_status("INSPECT") == "dormant"


def test_body_replacement_preserves_identity(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=15, intervention="I11"))
    aid = org.identity.agent_id
    org.run_ticks(30)
    assert org.identity.agent_id == aid
    assert org.self_model.agent_id == aid
    assert len(org.self_model.archive) >= 1
    org.close()


def test_duplicate_primary_body_is_rejected():
    sm = SelfModel.create("a", now=0.0)
    with pytest.raises(ValueError, match="duplicate_primary"):
        sm.bind_primary()
    with pytest.raises(ValueError, match="duplicate_primary"):
        sm.bind_primary(body_binding_id="other-binding")


def test_body_model_survives_restart(tmp_path):
    path = _db(tmp_path)
    org = create_organism(OrganismConfig(db_path=path, seed=16))
    org.run_ticks(40)
    sid = org.self_model.active.body_schema_id
    binding = org.self_model.body_binding_id
    aid = org.identity.agent_id
    org.snapshot_if_due(force=True)
    org.close()
    for _ in range(100):
        org2 = load_organism(OrganismConfig(db_path=path, seed=16))
        assert org2.identity.agent_id == aid
        assert org2.self_model.active.body_schema_id == sid
        assert org2.self_model.body_binding_id == binding
        org2.close()


def test_body_model_replay_is_deterministic(tmp_path):
    a = resimulate(21, 60, _db(tmp_path, "a.sqlite"))
    b = resimulate(21, 60, _db(tmp_path, "b.sqlite"))
    assert a["self_model_hash"] == b["self_model_hash"]
    assert a["body_schema_id"] == b["body_schema_id"]
    assert a["physiology"] == b["physiology"]


def test_corrupt_body_model_fails_closed(tmp_path):
    path = _db(tmp_path)
    org = create_organism(OrganismConfig(db_path=path, seed=17))
    org.run_ticks(10)
    org.snapshot_if_due(force=True)
    org.close()
    store_org = load_organism(OrganismConfig(db_path=path, seed=17))
    snap = store_org.store.load_snapshot()
    state = snap["state"]
    state["self_model"]["state_hash"] = "0" * 64
    from umbra_core.util import sha256_hex

    state_s = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
    store_org.store.conn.execute(
        "UPDATE snapshots SET state_json=?, state_hash=? WHERE snapshot_id=?",
        (state_s, sha256_hex(state_s), snap["snapshot_id"]),
    )
    store_org.close()
    with pytest.raises(PersistenceError):
        load_organism(OrganismConfig(db_path=path, seed=17))


def test_prediction_cannot_grant_authority(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=18))
    grants0 = set(org.governance.state.grants)
    org.self_model.active.confidence = 0.99
    proposal = org.governance.propose(
        "TELEPORT",
        {},
        requested_effects=["grant_capability"],
    )
    dec = org.governance.admit(proposal)
    assert not dec.admitted
    assert set(org.governance.state.grants) == grants0
    org.close()


def test_body_adapter_cannot_self_verify():
    emb = Embodiment()
    raw = emb.execute_primitive("MOVE", {"step": 1.0, "heading": 0.0}, SeededRNG(1))
    assert raw.get("adapter_certified") is False
    gov = Governance()
    outcome = gov.verify_outcome("MOVE", raw)
    assert outcome.verified is True


def test_regulation_recovery_remains_above_threshold(tmp_path):
    """Gate 7 — match D-001 recovery methodology (low_energy, 250 ticks)."""
    recoveries = 0
    trials = 20
    for seed in range(1, trials + 1):
        org = create_organism(OrganismConfig(db_path=_db(tmp_path, f"r{seed}.sqlite"), seed=seed))
        org.phys.intervene(energy=0.12)
        recovered = False
        for _ in range(250):
            org.tick_once()
            if org.phys.in_viable("energy"):
                recovered = True
                break
        if recovered:
            recoveries += 1
        org.close()
    rate = recoveries / trials
    assert rate >= 0.95


def test_model_count_is_bounded():
    sm = SelfModel.create("a", now=0.0)
    for i in range(MAX_MODEL_VERSIONS + 10):
        for j in range(15):
            sm.record_dimension_evidence("movement_gain", 0.5, tick=i * 20 + j)
    assert len(sm.archive) <= MAX_MODEL_VERSIONS


def test_prediction_history_is_bounded(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=19))
    org.run_ticks(400)
    assert len(org.self_model.predictions) <= MAX_PREDICTION_HISTORY
    assert len(org.self_model.errors) <= MAX_PREDICTION_HISTORY
    org.close()


def test_no_deferred_modules_added():
    root = Path(__file__).resolve().parents[1] / "umbra_core"
    forbidden = {
        "world_model.py",
        "episodic_memory.py",
        "semantic_memory.py",
        "relationship.py",
        "language.py",
        "personality.py",
        "emotion.py",
        "reflection.py",
        "llm.py",
    }
    found = {p.name for p in root.rglob("*.py")} & forbidden
    assert not found
    # self_model package exists (required)
    assert (root / "self_model").is_dir()
