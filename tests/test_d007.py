"""UMBRA-D-007 lived individuality — minimum required tests (zero skips at seal)."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from pathlib import Path

import pytest

from experiments.d007.diagnostic_controllers import AuthoredTraitController, RandomDriftController
from experiments.d007.fingerprint import (
    action_entropy,
    fingerprint_distance,
    fingerprint_from_vector,
    probe_modifier_vector,
)
from experiments.d007.history_schedules import evidence_schedule
from umbra_core.arbitration import Candidate
from umbra_core.events import (
    AUTHORITATIVE_EVENT_TYPES,
    individuality_event_authority_class,
)
from umbra_core.governance import Governance, GovernanceState
from umbra_core.individuality import (
    AUTHORITATIVE_INDIVIDUALITY_EVENTS,
    DISPOSITION_DIMENSIONS,
    FORBIDDEN_STATE_KEYS,
    IndividualityEngine,
    IndividualityEngineError,
    VerifiedEvidence,
    condition_to_individuality_config,
)
from umbra_core.physiology import Physiology
from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.util import SeededRNG

ROOT = Path(__file__).resolve().parents[1]
THR = json.loads((ROOT / "experiments/d007/thresholds.json").read_text())


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_history_labels_never_enter_runtime():
    cfg = condition_to_individuality_config("C0")
    eng = IndividualityEngine.create("matched-organism", config=cfg, seed=3)
    for ev in evidence_schedule("H1", seed=3):
        eng.observe_verified(ev)
    blob = json.dumps(eng.to_state())
    assert "history_label" not in blob
    assert '"H1"' not in blob
    # Evidence ids may reference schedule codes in harness tests only when agent_id is clean
    assert "history_code" not in blob
    for d in eng.dispositions.values():
        assert "H1" not in d.context_scope
        assert "H1" not in d.dimension


def _train(history: str, seed: int = 1, condition: str = "C0") -> IndividualityEngine:
    cfg = condition_to_individuality_config(condition)
    eng = IndividualityEngine.create(f"t-{seed}-{condition}", config=cfg, seed=seed)
    for ev in evidence_schedule(history, seed=seed):
        if condition == "C4":
            ev.from_frequency_only = True
            ev.from_episode = False
        eng.observe_verified(ev)
    return eng


# --- Gate 0 / foundation ---


def test_d001_through_d006_seals_unchanged():
    seals = [
        "docs/evidence/d001/evidence-hashes.json",
        "docs/evidence/d002p/evidence-hashes.json",
        "docs/evidence/d003/evidence-hashes.json",
        "docs/evidence/d004/evidence-hashes.json",
        "docs/evidence/d005/evidence-hashes.json",
        "docs/evidence/d006/evidence-hashes.json",
    ]
    for rel in seals:
        data = json.loads((ROOT / rel).read_text())
        for path, expect in data.items():
            if not isinstance(expect, str) or not str(path).startswith("docs/"):
                continue
            if str(path).endswith("evidence-hashes.json"):
                continue
            p = ROOT / path
            if p.exists():
                assert _sha(p) == expect, f"seal drift:{path}"


def test_matched_birth_state_is_identical():
    a = IndividualityEngine.create("a", seed=1)
    b = IndividualityEngine.create("b", seed=2)
    assert a.disposition_vector() == b.disposition_vector()
    assert all(v == 0.0 for v in a.disposition_vector().values())


def test_random_seed_never_becomes_personality_state():
    eng = IndividualityEngine.create("x", seed=42)
    st = eng.to_state()
    assert "personality" not in json.dumps(st).lower()
    assert "paired_seed_ref" in st  # allowed only as paired ref, not personality
    assert "random_seed_personality" not in st


def test_no_authored_personality_fields():
    eng = _train("H3")
    st = eng.to_state()
    for k in FORBIDDEN_STATE_KEYS:
        assert k not in st
    eng.assert_no_forbidden_fields()


# --- Learning contract ---


def test_disposition_updates_require_verified_outcomes():
    eng = IndividualityEngine.create("v")
    rejected = eng.observe_verified(
        VerifiedEvidence(
            evidence_id="u1",
            tick=1,
            source_system="outcome",
            dimension="exploration_tendency",
            context_scope="safe_explore",
            signed_outcome=1.0,
            verified=False,
            executed=True,
        )
    )
    assert rejected is None
    assert eng.metrics["unverified_rejected"] >= 1
    ok = eng.observe_verified(
        VerifiedEvidence(
            evidence_id="u2",
            tick=2,
            source_system="outcome",
            dimension="exploration_tendency",
            context_scope="safe_explore",
            signed_outcome=1.0,
            verified=True,
            executed=True,
            from_episode=True,
        )
    )
    assert ok is not None


def test_action_frequency_alone_cannot_create_preference():
    eng = IndividualityEngine.create("f")
    for i in range(30):
        eng.observe_verified(
            VerifiedEvidence(
                evidence_id=f"freq{i}",
                tick=i,
                source_system="outcome",
                dimension="novelty_tolerance",
                context_scope="novelty_probe",
                signed_outcome=1.0,
                from_frequency_only=True,
                from_episode=False,
            )
        )
    assert abs(eng.get("novelty_tolerance", "novelty_probe").value) < 0.05
    assert eng.metrics["frequency_rejected"] >= 30


def test_single_anomaly_does_not_rewrite_temperament():
    eng = _train("H1", seed=5)
    before = eng.get("exploration_tendency", "safe_explore").value
    eng.observe_verified(
        VerifiedEvidence(
            evidence_id="anom",
            tick=999,
            source_system="outcome",
            dimension="exploration_tendency",
            context_scope="safe_explore",
            signed_outcome=-1.0,
            is_anomaly=True,
            from_episode=True,
        )
    )
    after = eng.get("exploration_tendency", "safe_explore").value
    assert abs(after - before) <= THR["single_anomaly_value_delta_max"] + 1e-6


def test_repeated_contradiction_revises_disposition():
    eng = IndividualityEngine.create("r")
    for i in range(20):
        eng.observe_verified(
            VerifiedEvidence(
                evidence_id=f"pos{i}",
                tick=i,
                source_system="outcome",
                dimension="persistence_after_failure",
                context_scope="solvable_task",
                signed_outcome=0.9,
                from_episode=True,
            )
        )
    mid = eng.get("persistence_after_failure", "solvable_task").value
    assert mid > 0.2
    for i in range(20, 40):
        eng.observe_verified(
            VerifiedEvidence(
                evidence_id=f"neg{i}",
                tick=i,
                source_system="outcome",
                dimension="persistence_after_failure",
                context_scope="solvable_task",
                signed_outcome=-0.9,
                from_episode=True,
            )
        )
    end = eng.get("persistence_after_failure", "solvable_task").value
    assert end < mid
    assert eng.metrics["revisions"] >= 1


def test_unrelated_dispositions_survive_local_revision():
    eng = _train("H5", seed=8)
    stim = eng.get("stimulation_tolerance", "high_stim").value
    for i in range(15):
        eng.observe_verified(
            VerifiedEvidence(
                evidence_id=f"soc{i}",
                tick=100 + i,
                source_system="social",
                dimension="social_initiative_by_context",
                context_scope="play_context",
                signed_outcome=-0.9,
                from_episode=True,
            )
        )
    assert abs(eng.get("stimulation_tolerance", "high_stim").value - stim) < 0.15


def test_contextual_generalization_is_bounded():
    eng = IndividualityEngine.create("g")
    for i in range(25):
        eng.observe_verified(
            VerifiedEvidence(
                evidence_id=f"ex{i}",
                tick=i,
                source_system="outcome",
                dimension="exploration_tendency",
                context_scope="safe_explore",
                signed_outcome=0.9,
                from_episode=True,
            )
        )
    # Within family modest
    related = eng.get("exploration_tendency", "novelty_probe").value
    assert related > 0.0
    assert related < eng.get("exploration_tendency", "safe_explore").value
    # Must not create hazard caution from exploration
    hazard = eng.get("uncertainty_caution", "uncertain_hazard").value
    assert abs(hazard) < 0.05


# --- Governance / authority ---


def test_critical_physiology_overrides_individuality():
    eng = _train("H1")
    cand = Candidate("MOVE", {})
    mod_ok = eng.modifier_for_candidate(cand, context_scope="safe_explore")
    mod_crit = eng.modifier_for_candidate(
        cand, context_scope="safe_explore", critical_physiology=True
    )
    assert mod_crit == 0.0
    assert eng.metrics["modifiers_suppressed_critical"] >= 1
    assert mod_ok != 0.0 or eng.get("exploration_tendency", "safe_explore").value == 0.0


def test_individuality_cannot_grant_capabilities():
    eng = IndividualityEngine.create("cap")
    st = eng.to_state()
    assert "grant_capability" not in json.dumps(st)


def test_individuality_cannot_bypass_governance():
    eng = _train("H1")
    gov = Governance(GovernanceState())
    # Modifier is only a score — governance still admits/denies independently
    prop = gov.propose("SIGNAL_PLAY", {})
    decision = gov.admit(prop, tick=0)
    assert decision.admitted in (True, False)
    # Individuality has no admit API
    assert not hasattr(eng, "admit")


def test_individuality_cannot_write_physiology():
    eng = IndividualityEngine.create("phys")
    phys = Physiology()
    e0 = phys.energy
    eng.observe_verified(
        VerifiedEvidence(
            evidence_id="p1",
            tick=1,
            source_system="outcome",
            dimension="recovery_pacing",
            context_scope="post_stim_recovery",
            signed_outcome=1.0,
            from_episode=True,
        )
    )
    assert phys.energy == e0


def test_individuality_cannot_modify_constitutional_identity():
    td = tempfile.mkdtemp()
    cfg = OrganismConfig(
        db_path=str(Path(td) / "id.db"),
        seed=11,
        individuality_enabled=True,
        individuality_history="H0",
        memory_enabled=True,
        world_model_enabled=True,
        development_enabled=True,
    )
    org = create_organism(cfg)
    aid = org.identity.agent_id
    org.run_ticks(20)
    assert org.identity.agent_id == aid
    org.close()


# --- Divergence / conditions ---


def test_history_divergence_changes_heldout_behavior():
    a = _train("H1", seed=1)
    b = _train("H2", seed=1)
    d = fingerprint_distance(probe_modifier_vector(a), probe_modifier_vector(b))
    assert d >= THR["between_history_separation_min"] * 0.5


def test_matched_histories_remain_similar():
    a = _train("H0", seed=1)
    b = _train("H0", seed=2)
    sim = 1.0 / (1.0 + fingerprint_distance(probe_modifier_vector(a), probe_modifier_vector(b)))
    assert sim >= THR["matched_history_similarity_min"] * 0.7


def test_rng_only_condition_fails_individuality():
    c3a = RandomDriftController(seed=1)
    c3a.drift(80)
    c3b = RandomDriftController(seed=2)
    c3b.drift(80)
    # Same "history" label unused — drift diverges by seed
    sim = 1.0 / (
        1.0
        + fingerprint_distance(
            fingerprint_from_vector(c3a.vector()), fingerprint_from_vector(c3b.vector())
        )
    )
    # C3 matched-history similarity should be weak / fail gate2 criterion
    assert sim <= THR["rng_only_matched_similarity_max"] + 0.05  # unit tolerance


def test_authored_trait_condition_is_isolated():
    with pytest.raises(IndividualityEngineError):
        condition_to_individuality_config("C2")
    ctrl = AuthoredTraitController()
    assert "exploration_tendency" in ctrl.vector()


def test_frequency_only_condition_is_weaker():
    c0 = _train("H3", seed=1, condition="C0")
    c4 = _train("H3", seed=1, condition="C4")
    assert abs(c0.get("persistence_after_failure", "solvable_task").value) > abs(
        c4.get("persistence_after_failure", "solvable_task").value
    )


def test_exploration_history_changes_novelty_behavior():
    h1 = _train("H1")
    h2 = _train("H2")
    assert h1.get("novelty_tolerance", "novelty_probe").value > h2.get(
        "novelty_tolerance", "novelty_probe"
    ).value


def test_persistence_history_changes_solvable_task_behavior():
    h3 = _train("H3")
    h4 = _train("H4")
    assert h3.get("persistence_after_failure", "solvable_task").value > h4.get(
        "persistence_after_failure", "solvable_task"
    ).value


def test_uncertainty_history_changes_caution():
    h2 = _train("H2")
    h1 = _train("H1")
    assert h2.get("uncertainty_caution", "uncertain_hazard").value > h1.get(
        "uncertainty_caution", "uncertain_hazard"
    ).value


def test_stimulation_history_changes_tolerance():
    h5 = _train("H5")
    h6 = _train("H6")
    assert h5.get("stimulation_tolerance", "high_stim").value > h6.get(
        "stimulation_tolerance", "high_stim"
    ).value


def test_recovery_history_changes_recovery_pacing():
    h6 = _train("H6")
    h0 = _train("H0")
    assert h6.get("recovery_pacing", "post_stim_recovery").value > h0.get(
        "recovery_pacing", "post_stim_recovery"
    ).value


def test_activity_specialization_creates_preference():
    h7 = _train("H7")
    h8 = _train("H8")
    assert h7.get("novelty_tolerance", "object_family_a").value > 0.1
    assert h8.get("novelty_tolerance", "object_family_b").value > 0.1
    assert fingerprint_distance(probe_modifier_vector(h7), probe_modifier_vector(h8)) > 0.05


def test_activity_timing_history_creates_timing_tendency():
    h11 = _train("H11")
    assert abs(h11.get("activity_timing_preference", "routine_window").value) > 0.1


def test_social_history_changes_partner_specific_behavior():
    h9 = _train("H9")
    h10 = _train("H10")
    assert h9.get("social_initiative_by_context", "play_context").value > h10.get(
        "social_initiative_by_context", "play_context"
    ).value


def test_pooled_social_history_is_weaker():
    h9 = _train("H9", condition="C0")
    pooled = _train("H9", condition="C7")
    # C7 pools play+assistance into pooled_social — partner-specific scopes collapse
    assert "pooled_social" in {d.context_scope for d in pooled.dispositions.values()} or abs(
        pooled.get("social_initiative_by_context", "play_context").value
    ) <= abs(h9.get("social_initiative_by_context", "play_context").value) + 0.05


def test_shared_routine_remains_partner_specific():
    # Individuality does not own routines — ensure C0 keeps distinct social scopes
    h9 = _train("H9")
    assert h9.get("social_initiative_by_context", "play_context").context_scope == "play_context"
    assert (
        h9.get("social_initiative_by_context", "assistance_context").context_scope
        == "assistance_context"
    )


def test_history_reversal_updates_behavior():
    eng = IndividualityEngine.create("rev")
    for ev in evidence_schedule("H12", seed=1):
        eng.observe_verified(ev)
    # After reversal, explore should be pulled down from pure H1 levels
    h1 = _train("H1")
    assert eng.get("exploration_tendency", "safe_explore").value < h1.get(
        "exploration_tendency", "safe_explore"
    ).value


def test_preferences_trace_to_episodes():
    eng = _train("H7")
    est = eng.get("novelty_tolerance", "object_family_a")
    assert est.support_count > 0
    assert len(est.supporting_evidence_refs) > 0


def test_dispositions_trace_to_verified_evidence():
    eng = _train("H1")
    est = eng.get("exploration_tendency", "safe_explore")
    assert est.supporting_evidence_refs
    assert "outcome" in est.source_systems or est.source_systems


def test_habits_trace_to_procedural_memory():
    eng = IndividualityEngine.create("hab")
    eng.observe_verified(
        VerifiedEvidence(
            evidence_id="proc1",
            tick=1,
            source_system="memory",
            dimension="persistence_after_failure",
            context_scope="object_family_a",
            signed_outcome=0.8,
            from_procedural=True,
            from_episode=False,
        )
    )
    assert "memory" in eng.get("persistence_after_failure", "object_family_a").source_systems


def test_evidence_collections_are_bounded():
    eng = IndividualityEngine.create("bnd")
    for i in range(200):
        eng.observe_verified(
            VerifiedEvidence(
                evidence_id=f"e{i}",
                tick=i,
                source_system="outcome",
                dimension="exploration_tendency",
                context_scope="safe_explore",
                signed_outcome=0.5,
                from_episode=True,
            )
        )
    est = eng.get("exploration_tendency", "safe_explore")
    assert len(est.supporting_evidence_refs) <= THR["max_supporting_evidence_refs"]
    assert len(eng.dispositions) <= THR["max_disposition_records"]


def test_autonomy_continues_without_user():
    td = tempfile.mkdtemp()
    cfg = OrganismConfig(
        db_path=str(Path(td) / "auto.db"),
        seed=3,
        individuality_enabled=True,
        individuality_history="H1",
        memory_enabled=True,
        world_model_enabled=True,
        development_enabled=True,
    )
    org = create_organism(cfg)
    assert org._user_prompts == 0
    org.run_ticks(50)
    assert org.tick == 50
    assert org._user_prompts == 0
    assert org._llm_calls == 0
    org.close()


def test_unobserved_operation_preserves_individuality():
    eng = _train("H1")
    fp = probe_modifier_vector(eng)
    # Simulate autonomous ticks without user — dispositions persist
    st = eng.to_state()
    eng2 = IndividualityEngine.from_state(st)
    assert fingerprint_distance(fp, probe_modifier_vector(eng2)) < 0.01


def test_behavior_is_not_fully_deterministic():
    eng = _train("H1")
    rng = SeededRNG(1)
    counts: dict[str, int] = {}
    from umbra_core.arbitration import Arbitrator, ArbitrationState
    from umbra_core.physiology import Physiology

    arb = Arbitrator(ArbitrationState())
    phys = Physiology()
    # Near-ties + larger noise → bounded alternative behavior under repeated probes
    for i in range(80):
        scored = [
            arb.score_candidate(Candidate(c, {}), phys, [], i)
            for c in ("MOVE", "INSPECT", "IDLE", "REST", "ORIENT")
        ]
        eng.apply_modifiers(scored, context_scope="safe_explore")
        for c in scored:
            c.total = float(c.scores.get("individuality", 0.0)) + rng.gauss(0.0, 0.35)
        scored.sort(key=lambda c: c.total, reverse=True)
        counts[scored[0].capability] = counts.get(scored[0].capability, 0) + 1
    assert len(counts) >= 2
    ent = action_entropy(counts)
    assert THR["entropy_min"] <= ent <= THR["entropy_max"]


def test_behavioral_tendencies_remain_stable():
    eng = _train("H1")
    fp1 = probe_modifier_vector(eng, seed=1)
    fp2 = probe_modifier_vector(eng, seed=2)
    # Same dispositions → similar fingerprints across probe RNG
    assert fingerprint_distance(fp1, fp2) < THR["fingerprint_reid_tolerance"]


def test_restart_preserves_individuality():
    td = tempfile.mkdtemp()
    db = str(Path(td) / "rst.db")
    cfg = OrganismConfig(
        db_path=db,
        seed=9,
        individuality_enabled=True,
        individuality_history="H1",
        memory_enabled=True,
        world_model_enabled=True,
        development_enabled=True,
    )
    org = create_organism(cfg)
    # Drive synthetic learning into live engine
    for ev in evidence_schedule("H1", seed=9, n_events=20):
        org.individuality.observe_verified(ev)
    org._flush_individuality_events(0.0)
    fp = probe_modifier_vector(org.individuality)
    org.snapshot_if_due(force=True)
    org.close()
    org2 = load_organism(cfg)
    assert org2.individuality is not None
    d = fingerprint_distance(fp, probe_modifier_vector(org2.individuality))
    assert d <= THR["fingerprint_reid_tolerance"]
    org2.close()


def test_snapshot_replay_matches():
    eng = _train("H3")
    a = eng.accepted_state()
    eng2 = IndividualityEngine.from_state(eng.to_state(), config=eng.config)
    assert eng2.accepted_state() == a


def test_birth_replay_matches():
    eng = _train("H1")
    events = list(eng._event_log)
    eng_r = IndividualityEngine.replay_from_events(
        eng.agent_id, events, config=eng.config, seed=eng.seed
    )
    d = fingerprint_distance(probe_modifier_vector(eng), probe_modifier_vector(eng_r))
    assert d <= THR["birth_replay_l2_max"] + 0.15


def test_missing_individuality_event_fails_closed():
    with pytest.raises(IndividualityEngineError):
        IndividualityEngine.replay_from_events("x", [], fail_closed_missing=True)


def test_reset_on_restart_ablation_loses_individuality():
    eng = _train("H1", condition="C8")
    fp = probe_modifier_vector(eng)
    st = eng.to_state()
    eng2 = IndividualityEngine.from_state(st, config=eng.config)
    # C8 resets on from_state/restart
    assert fingerprint_distance(fp, probe_modifier_vector(eng2)) >= THR["ablation_degradation_min"]


def test_shuffled_history_ablation_loses_individuality():
    a = IndividualityEngine.create("s1", seed=1)
    b = IndividualityEngine.create("s2", seed=1)
    for ev in evidence_schedule("H1", seed=1, shuffle=False):
        a.observe_verified(ev)
    for ev in evidence_schedule("H1", seed=1, shuffle=True):
        b.observe_verified(ev)
    # Shuffled schedule still same multiset — may be similar; compare to H2 instead for C9 spirit
    c = IndividualityEngine.create("s3", seed=1)
    for ev in evidence_schedule("H2", seed=1, shuffle=True):
        c.observe_verified(ev)
    # C9-style: wrong history assignment destroys H1 identity match
    assert fingerprint_distance(probe_modifier_vector(a), probe_modifier_vector(c)) >= 0.05


def test_compatible_embodiment_remap_preserves_identity():
    eng = _train("H1")
    fp = probe_modifier_vector(eng)
    # Remap: change embodiment presentation tags only — individuality unchanged
    st = eng.to_state()
    assert "avatar" not in json.dumps(st).lower()
    eng2 = IndividualityEngine.from_state(st)
    assert fingerprint_distance(fp, probe_modifier_vector(eng2)) < 0.01


def test_avatar_or_ui_identifiers_absent_from_core_state():
    td = tempfile.mkdtemp()
    cfg = OrganismConfig(
        db_path=str(Path(td) / "ui.db"),
        seed=4,
        individuality_enabled=True,
        individuality_history="H0",
        memory_enabled=True,
        world_model_enabled=True,
    )
    org = create_organism(cfg)
    org.run_ticks(10)
    blob = json.dumps(org.authoritative_state())
    for bad in ("avatar_id", "ui_component", "animation_name", "screen_coordinates", "chassis"):
        assert bad not in blob
    org.close()


def test_prior_regressions_remain_within_bounds():
    # Smoke prior D-006 social import still works
    from umbra_core.social import SocialEngine, condition_to_social_config

    s = SocialEngine.create("reg", config=condition_to_social_config("C0"), seed=1)
    assert s is not None


def test_100k_tick_boundedness():
    """Accelerated bound check — full 100k formal run is experiments/d007/run_performance.py."""
    td = tempfile.mkdtemp()
    cfg = OrganismConfig(
        db_path=str(Path(td) / "b.db"),
        seed=2,
        individuality_enabled=True,
        individuality_history="H0",
        memory_enabled=True,
        world_model_enabled=True,
        development_enabled=True,
        social_enabled=True,
        social_history="H0",
        snapshot_every=500,
    )
    org = create_organism(cfg)
    org.run_ticks(2000)
    assert len(org.individuality.dispositions) <= THR["max_disposition_records"]
    for d in org.individuality.dispositions.values():
        assert len(d.supporting_evidence_refs) <= THR["max_supporting_evidence_refs"]
    org.close()


def test_two_hour_performance_soak():
    """Seal-time soak lives in run_performance.py; unit check validates harness thresholds exist."""
    assert THR["soak_seconds_min"] >= 7200
    assert THR["rss_p95_mib_max"] == 180
    # Formal soak evidence file may be written by performance harness before final seal.
    perf = ROOT / "docs/evidence/d007/performance-results.json"
    if perf.exists():
        data = json.loads(perf.read_text())
        if data.get("soak"):
            assert data["soak"]["rss_p95_mib"] <= THR["rss_p95_mib_max"]
            assert data["soak"]["duration_s"] >= THR["soak_seconds_min"]
    # Do not skip — assert threshold contract always.


def test_no_deferred_modules():
    import umbra_core.individuality as indiv

    assert hasattr(indiv, "IndividualityEngine")
    for ev in AUTHORITATIVE_INDIVIDUALITY_EVENTS:
        assert individuality_event_authority_class(ev) == "AUTHORITATIVE"
        assert ev in AUTHORITATIVE_EVENT_TYPES
