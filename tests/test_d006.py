"""UMBRA-D-006 — social contingency (signal capabilities + event authority)."""

import pytest


def test_signal_capabilities_exist_and_are_governed():
    from umbra_core.embodiment import CAPABILITIES

    assert "SIGNAL_PLAY" in CAPABILITIES
    assert "SIGNAL_ASSISTANCE" in CAPABILITIES


def test_social_event_authority_classes():
    from umbra_core.events import social_event_authority_class

    assert social_event_authority_class("social_pending_created") == "AUTHORITATIVE"
    assert social_event_authority_class("social_recognition_updated") == "AUTHORITATIVE"
    assert social_event_authority_class("social_match_score") == "DIAGNOSTIC"


def test_social_event_authority_class_unknown_raises():
    from umbra_core.events import social_event_authority_class

    with pytest.raises(KeyError, match="unknown_social_event:nope"):
        social_event_authority_class("nope")


def test_signal_cooldown_denies_within_six_ticks():
    from umbra_core.governance import Governance, GovernanceState

    gov = Governance(GovernanceState(last_signal_tick=10, signal_cooldown_ticks=6))
    prop = gov.propose("SIGNAL_PLAY", {"tick": 15})
    dec = gov.admit(prop, tick=15)
    assert not dec.admitted
    assert dec.reason == "signal_cooldown"


def test_signal_actuation_no_movement_emits_environmental_event():
    from umbra_core.embodiment import Embodiment
    from umbra_core.util import SeededRNG

    emb = Embodiment()
    before = (emb.body.x, emb.body.y)
    raw = emb.execute_primitive("SIGNAL_PLAY", {"tick": 42}, SeededRNG(1))
    assert raw["ok_raw"]
    assert emb.body.velocity == 0.0
    assert (emb.body.x, emb.body.y) == before
    assert raw["environmental_event"] == {
        "kind": "social_signal",
        "signal": "SIGNAL_PLAY",
        "tick": 42,
    }


PARTNER_CUE_FIELDS = (
    "relative_position",
    "motion_signature",
    "appearance_signature",
    "response_timing_pattern",
    "interaction_style_cues",
    "cue_confidence",
    "cue_uncertainty",
)


def _perceive_partner_cues(history: str = "H0", seed: int = 1, now: float = 1.0):
    from umbra_core.embodiment import Embodiment
    from umbra_core.perception import PerceptionMembrane
    from umbra_core.util import SeededRNG

    emb = Embodiment()
    emb.apply_social_history(history)
    membrane = PerceptionMembrane(false_negative_rate=0.0)
    membrane.perceive(emb, now, SeededRNG(seed))
    return emb, membrane.policy_view()


def test_policy_cannot_access_hidden_partner_id():
    emb, view = _perceive_partner_cues("H0")
    cues = view.get("partner_cues", [])
    assert cues, "expected at least one partner cue observation"
    for obs in cues:
        assert "partner_id" not in obs
        assert "hidden_partner_id" not in obs
        for field in PARTNER_CUE_FIELDS:
            assert field in obs
    policy_blob = str(view)
    assert "hidden_partner" not in policy_blob


def test_hidden_partner_id_is_evaluator_only():
    emb, view = _perceive_partner_cues("H0")
    truth = emb.hidden_partner_truth_for_eval()
    assert truth
    assert "partner_id" in truth[0]
    for obs in view.get("partner_cues", []):
        assert "partner_id" not in obs
        assert "hidden_partner_id" not in obs


def test_partner_cues_are_noisy_and_seeded():
    emb_a, view_a = _perceive_partner_cues("H0", seed=7)
    _, view_b = _perceive_partner_cues("H0", seed=7)
    _, view_c = _perceive_partner_cues("H0", seed=8)
    cue_a = view_a["partner_cues"][0]
    cue_b = view_b["partner_cues"][0]
    cue_c = view_c["partner_cues"][0]
    assert cue_a == cue_b
    assert cue_a != cue_c or cue_a["motion_signature"] != cue_c["motion_signature"]
    truth = emb_a.hidden_partner_truth_for_eval()[0]["true_cues"]
    assert cue_a["motion_signature"] != truth["motion_signature"]
    assert cue_a["cue_uncertainty"] > 0.0


def test_social_history_policies_h0_through_h10_exist():
    from umbra_core.embodiment import response_policy_for_history

    for i in range(11):
        policy = response_policy_for_history(f"H{i}")
        assert policy.history_code == f"H{i}"
        assert hasattr(policy, "should_respond")
        assert hasattr(policy, "response_delay_ticks")


def test_response_timing_pattern_not_saturated_for_h0():
    _, view = _perceive_partner_cues("H0", seed=1)
    timing = view["partner_cues"][0]["response_timing_pattern"]
    assert len(timing) == 3
    # H0 true timing is (2.0, 5.0, 1.0) ticks — must not collapse to ~[1,1,1] after noise
    assert not all(abs(v - 1.0) < 0.01 for v in timing), f"saturated timing cue: {timing}"
    assert max(timing) - min(timing) > 0.05, f"timing cue lacks variance: {timing}"


def test_h7_absence_suppresses_partner_cues_during_window():
    from umbra_core.embodiment import Embodiment
    from umbra_core.perception import PerceptionMembrane
    from umbra_core.util import SeededRNG

    emb = Embodiment()
    emb.apply_social_history("H7")
    membrane = PerceptionMembrane(false_negative_rate=0.0)
    present = membrane.perceive(emb, 1.0, SeededRNG(1))
    absent = membrane.perceive(emb, 30.0, SeededRNG(1))
    assert present
    assert membrane.policy_view().get("partner_cues", []) == []


# --- Task 4: SocialEngine core — hypotheses, recognition, satiation ---


def _social_cue(seed_tag: float = 0.0):
    """Synthetic partner cue matching perception.PARTNER_CUE_FIELDS shape."""
    return {
        "relative_position": [1.0, 0.5],
        "motion_signature": [0.2 + seed_tag, 0.3, 0.1],
        "appearance_signature": [0.5, 0.4, 0.2 + seed_tag],
        "response_timing_pattern": [0.3, 0.5, 0.1],
        "interaction_style_cues": [0.6 + seed_tag, 0.3, 0.5],
        "cue_confidence": 0.7,
        "cue_uncertainty": 0.3,
        "observed_at": 1.0,
        "expires_at": 13.0,
        "source": "partner_cue",
    }


def _real_partner_cue(history: str = "H0", seed: int = 1, now: float = 1.0):
    from umbra_core.embodiment import Embodiment
    from umbra_core.perception import PerceptionMembrane
    from umbra_core.util import SeededRNG

    emb = Embodiment()
    emb.apply_social_history(history)
    membrane = PerceptionMembrane(false_negative_rate=0.0)
    membrane.perceive(emb, now, SeededRNG(seed))
    return membrane.policy_view()["partner_cues"]


def test_partner_identity_is_uncertain():
    from umbra_core.social import SocialEngine

    engine = SocialEngine.create("agent-1", seed=1)
    result = engine.recognize(_real_partner_cue("H0", seed=1, now=1.0), tick=1)

    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.status == "UNKNOWN"  # single sighting is insufficient evidence
    assert match.hypothesis_id is not None
    assert match.hypothesis_id != "p-h0"  # never equals hidden partner_id


def test_ambiguous_partner_remains_unknown():
    from umbra_core.social import SocialEngine

    engine = SocialEngine.create("agent-1", seed=1)
    # Two distinct hypotheses far enough apart to both form (H9-style two-partner setup).
    r1 = engine.recognize([_social_cue(0.0)], tick=1)
    hid_a = r1.matches[0].hypothesis_id
    r2 = engine.recognize([_social_cue(1.0)], tick=2)
    hid_b = r2.matches[0].hypothesis_id
    assert hid_a != hid_b

    # A cue exactly between the two prototypes is genuinely ambiguous — must not
    # be silently merged into either identity (design: "swaps do not silently merge").
    r3 = engine.recognize([_social_cue(0.5)], tick=3)
    match = r3.matches[0]
    assert match.status == "CONTESTED"
    assert set(match.contested_with) == {hid_a, hid_b}
    assert engine.hypotheses[hid_a].status == "CONTESTED"
    assert engine.hypotheses[hid_b].status == "CONTESTED"

    # Repeating the ambiguous cue must not resolve it into an accepted identity.
    r4 = engine.recognize([_social_cue(0.5)], tick=4)
    assert r4.matches[0].status in ("UNKNOWN", "CONTESTED")
    assert r4.matches[0].status != "FAMILIAR"


def test_expected_response_latency_is_derived():
    from dataclasses import fields

    from umbra_core.social import PartnerHypothesis, SocialEngine

    assert "expected_response_latency" not in {f.name for f in fields(PartnerHypothesis)}

    engine = SocialEngine.create("agent-1", seed=1)
    result = engine.recognize([_social_cue()], tick=1)
    hid = result.matches[0].hypothesis_id

    assert engine.expected_response_latency(hid) is None  # no contingency evidence yet

    engine.record_contingency_sample(hid, "play", "SIGNAL_PLAY", tick=2, latency_ticks=3.0, confidence=0.8)
    engine.record_contingency_sample(
        hid, "assistance", "SIGNAL_ASSISTANCE", tick=3, latency_ticks=9.0, confidence=0.2
    )
    latency = engine.expected_response_latency(hid)
    expected = (3.0 * 0.8 * 1 + 9.0 * 0.2 * 1) / (0.8 * 1 + 0.2 * 1)
    assert latency is not None
    assert abs(latency - expected) < 1e-9


def test_provenance_active_sets_are_bounded():
    from umbra_core.social import MAX_ACTIVE_EVIDENCE_REFS, MAX_SOURCE_HYPOTHESIS_IDS, SocialEngine

    engine = SocialEngine.create("agent-1", seed=1)
    result = engine.recognize([_social_cue()], tick=1)
    hid = result.matches[0].hypothesis_id

    for i in range(50):
        engine.add_evidence_ref(hid, f"ep-{i}")
    for i in range(20):
        engine.add_source_hypothesis(hid, f"hyp-{i}")

    hyp = engine.hypotheses[hid]
    assert len(hyp.evidence_refs) == MAX_ACTIVE_EVIDENCE_REFS
    assert len(hyp.source_hypothesis_ids) == MAX_SOURCE_HYPOTHESIS_IDS
    # Most recent refs are retained, not the earliest.
    assert "ep-49" in hyp.evidence_refs
    assert "ep-0" not in hyp.evidence_refs
    assert engine.counts_bounded()


def test_recognized_partner_becomes_familiar_after_repeated_encounters():
    from umbra_core.social import SocialEngine

    events: list[tuple[str, dict]] = []
    engine = SocialEngine.create("agent-1", seed=1, emit_event=lambda t, p: events.append((t, p)))

    r1 = engine.recognize([_social_cue()], tick=1)
    assert r1.matches[0].status == "UNKNOWN"
    hid = r1.matches[0].hypothesis_id

    r2 = engine.recognize([_social_cue()], tick=2)
    assert r2.matches[0].hypothesis_id == hid
    assert r2.matches[0].status == "FAMILIAR"

    recognition_events = [p for t, p in events if t == "social_recognition_updated"]
    assert len(recognition_events) == 1  # accepted anchor emitted once, not every tick
    assert recognition_events[0]["hypothesis_id"] == hid

    # A third consistent sighting must not re-emit social_recognition_updated.
    engine.recognize([_social_cue()], tick=3)
    recognition_events_after = [p for t, p in events if t == "social_recognition_updated"]
    assert len(recognition_events_after) == 1


def test_c6_recognition_disabled_always_unknown():
    from umbra_core.social import SocialEngine, condition_to_social_config

    cfg = condition_to_social_config("C6")
    assert cfg.recognition_enabled is False
    engine = SocialEngine.create("agent-1", seed=1, config=cfg)

    for tick in range(1, 4):
        result = engine.recognize([_social_cue()], tick=tick)
        assert result.matches[0].status == "UNKNOWN"
        assert result.matches[0].hypothesis_id is None
    assert engine.hypotheses == {}


def test_c3_affection_controller_is_isolated():
    import umbra_core.social.engine as eng

    assert not hasattr(eng, "AffectionMeter")
    from experiments.d006.affection_controller import AffectionController

    assert AffectionController is not None
    ctrl = AffectionController()
    assert ctrl.observe_interaction(positive=True) > 0.0


def test_c4_resets_relationship_state_between_encounters():
    from umbra_core.social import RoutineHandle, SocialEngine, condition_to_social_config

    cfg = condition_to_social_config("C4")
    assert cfg.persist_relationship is False
    engine = SocialEngine.create("agent-1", seed=1, config=cfg)
    engine.recognize([_social_cue()], tick=1)
    assert engine.hypotheses
    hid = next(iter(engine.hypotheses))
    engine.create_pending(
        hypothesis_id=hid,
        context="play",
        signal="SIGNAL_PLAY",
        execution_id="exec-1",
        signal_tick=1,
        recognition_confidence=0.8,
        governance_admitted=True,
        capability_executed=True,
        tick=1,
    )
    engine.routine_handles["r1"] = RoutineHandle(
        routine_id="r1", hypothesis_id=hid, context="play", signal="SIGNAL_PLAY"
    )

    engine.reset_for_encounter_boundary()
    assert engine.hypotheses == {}
    assert engine.contingency_cells == {}
    assert engine.pending == {}
    assert engine.routine_handles == {}

    engine.recognize([_social_cue()], tick=2)
    state = engine.to_state()
    restarted = SocialEngine.from_state(state, config=cfg)
    assert restarted.hypotheses == {}  # C4 also resets on restart, per design §6


@pytest.mark.parametrize(
    "condition,expected",
    [
        ("C0", {}),
        ("C1", {"preference_familiarity_only": True}),
        ("C2", {"pooled_partner_model": True}),
        ("C3", {}),
        ("C4", {"persist_relationship": False}),
        ("C5", {"satiation_enabled": False}),
        ("C6", {"recognition_enabled": False}),
        ("C7", {"random_social_actions": True}),
        ("C8", {"scripted_routine": True}),
        ("C9", {"randomized_contingency_timing": True}),
    ],
)
def test_condition_to_social_config_all_ablations(condition, expected):
    from dataclasses import asdict

    from umbra_core.social import SocialConfig, condition_to_social_config

    cfg = condition_to_social_config(condition)
    assert isinstance(cfg, SocialConfig)
    baseline = asdict(SocialConfig())
    actual = asdict(cfg)
    for key, value in expected.items():
        assert actual[key] == value, f"{condition}.{key}"
    for key, value in baseline.items():
        if key not in expected:
            assert actual[key] == value, f"{condition} leaked change to {key}"


def test_c2_pooled_partner_model_uses_single_hypothesis():
    from umbra_core.social import SocialEngine, condition_to_social_config

    cfg = condition_to_social_config("C2")
    engine = SocialEngine.create("agent-1", seed=1, config=cfg)
    cue_a = _social_cue(seed_tag=0.0)
    cue_b = _social_cue(seed_tag=0.9)

    r1 = engine.recognize([cue_a], tick=1)
    r2 = engine.recognize([cue_b], tick=2)
    assert r1.matches[0].hypothesis_id == r2.matches[0].hypothesis_id
    assert len(engine.hypotheses) == 1


def test_c9_randomized_contingency_timing_ignores_latency():
    from umbra_core.social import ResponseClass, SocialEngine, condition_to_social_config

    baseline = SocialEngine.create("agent-1", seed=1)
    c9 = SocialEngine.create("agent-1", seed=1, config=condition_to_social_config("C9"))
    assert baseline.classify_response(response_latency=3.0) == ResponseClass.CONTINGENT
    assert baseline.classify_response(response_latency=12.0) == ResponseClass.DELAYED
    c9_classes = {
        c9.classify_response(response_latency=float(lat)) for lat in range(1, 25)
    }
    assert c9.classify_response(response_latency=3.0) == c9.classify_response(
        response_latency=3.0
    )
    assert c9_classes != {ResponseClass.CONTINGENT}


def test_current_satiation_is_derived_not_stored():
    from dataclasses import fields

    from umbra_core.social import PartnerHypothesis, SocialEngine

    field_names = {f.name for f in fields(PartnerHypothesis)}
    assert "satiation" not in field_names
    assert "satiation_anchor" in field_names

    engine = SocialEngine.create("agent-1", seed=1)
    result = engine.recognize([_social_cue()], tick=1)
    hid = result.matches[0].hypothesis_id

    engine.update_satiation_anchor(hid, tick=1, delta=0.5)
    assert abs(engine.current_satiation(hid, tick=1) - 0.5) < 1e-9
    decayed = engine.current_satiation(hid, tick=51)
    assert decayed < 0.5


def test_social_engine_state_roundtrip():
    from umbra_core.social import SocialEngine

    engine = SocialEngine.create("agent-1", seed=1)
    engine.recognize([_social_cue()], tick=1)
    engine.recognize([_social_cue()], tick=2)
    state = engine.to_state()

    restored = SocialEngine.from_state(state)
    assert set(restored.hypotheses) == set(engine.hypotheses)
    for hid, hyp in engine.hypotheses.items():
        assert restored.hypotheses[hid].status == hyp.status
        assert restored.hypotheses[hid].familiarity == hyp.familiarity


def test_hidden_partner_id_rejected_from_cues():
    from umbra_core.social import SocialEngine, SocialEngineError

    engine = SocialEngine.create("agent-1", seed=1)
    bad_cue = dict(_social_cue())
    bad_cue["hidden_partner_id"] = "p-h0"
    with pytest.raises(SocialEngineError):
        engine.recognize([bad_cue], tick=1)


# --- Task 5: pending interactions + contingency classification + atomic commit ---


def _familiar_engine(seed_tag: float = 0.0, seed: int = 1, emit=None):
    """Engine with one FAMILIAR, unambiguous hypothesis (two identical sightings)."""
    from umbra_core.social import SocialEngine

    engine = SocialEngine.create("agent-1", seed=seed, emit_event=emit)
    engine.recognize([_social_cue(seed_tag)], tick=1)
    r = engine.recognize([_social_cue(seed_tag)], tick=2)
    return engine, r.matches[0].hypothesis_id


def _new_store(tmp_path, name="s.db"):
    from umbra_core.persistence import Store

    return Store(str(tmp_path / name))


def test_denied_signal_creates_no_partner_evidence(tmp_path):
    from umbra_core.social import SocialEngineError

    store = _new_store(tmp_path)
    engine, hid = _familiar_engine()
    with pytest.raises(SocialEngineError):
        engine.create_pending(
            hypothesis_id=hid,
            context="play",
            signal="SIGNAL_PLAY",
            execution_id="x1",
            signal_tick=5,
            recognition_confidence=1.0,
            governance_admitted=False,  # denied
            capability_executed=False,
            store=store,
        )
    assert engine.pending == {}
    assert engine.contingency_cells == {}
    assert engine.hypotheses[hid].reliability_by_context == {}
    types = [e["event_type"] for e in store.iter_events()]
    assert "social_pending_created" not in types
    store.close()


def test_response_classification_precedence():
    from umbra_core.social import ResponseClass, SocialEngine

    c = SocialEngine.create("agent-1", seed=1).classify_response
    # EXTERNAL beats everything (even a contingent-window latency)
    assert c(response_latency=3, external_cause=True) == ResponseClass.EXTERNAL
    # AMBIGUOUS beats CONTINGENT/DELAYED/... (contested, low confidence, or overlap)
    assert c(response_latency=3, contested=True) == ResponseClass.AMBIGUOUS
    assert c(response_latency=3, recognition_confidence=0.10) == ResponseClass.AMBIGUOUS
    assert c(response_latency=3, overlapping_inseparable=True) == ResponseClass.AMBIGUOUS
    # CONTINGENT window [1,8]
    assert c(response_latency=1) == ResponseClass.CONTINGENT
    assert c(response_latency=8) == ResponseClass.CONTINGENT
    # DELAYED window [9,24]
    assert c(response_latency=9) == ResponseClass.DELAYED
    assert c(response_latency=24) == ResponseClass.DELAYED
    # COINCIDENTAL: response present but implausible timing (<=0 or 25..timeout)
    assert c(response_latency=0) == ResponseClass.COINCIDENTAL
    assert c(response_latency=28) == ResponseClass.COINCIDENTAL
    # NONE: no response, or past the timeout window (>32)
    assert c(response_latency=None) == ResponseClass.NONE
    assert c(response_latency=40) == ResponseClass.NONE


def test_overlapping_bids_resolve_ambiguous(tmp_path):
    from umbra_core.memory import MemoryEngine
    from umbra_core.social import ResponseClass

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()

    p1 = engine.create_pending(
        hypothesis_id=hid, context="play", signal="SIGNAL_PLAY", execution_id="e1",
        signal_tick=5, recognition_confidence=1.0,
        governance_admitted=True, capability_executed=True, store=store,
    )
    engine.create_pending(
        hypothesis_id=hid, context="play", signal="SIGNAL_PLAY", execution_id="e2",
        signal_tick=6, recognition_confidence=1.0,
        governance_admitted=True, capability_executed=True, store=store,
    )
    cls = engine.observe_outcome(
        p1.pending_interaction_id, response_tick=9, response_observed=True,
        store=store, memory=mem,
    )
    assert cls == ResponseClass.AMBIGUOUS
    assert engine.hypotheses[hid].reliability_by_context.get("play", 0.0) == 0.0
    key = engine._cell_key(hid, "play", "SIGNAL_PLAY")
    cell = engine.contingency_cells.get(key)
    assert cell is None or cell.contingent_count == 0
    assert store.social_evidence_links_for(hid) == []
    store.close()


def test_contingency_beats_frequency(tmp_path):
    from umbra_core.memory import MemoryEngine
    from umbra_core.social import SocialEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine = SocialEngine.create("agent-1", seed=1)
    engine.recognize([_social_cue(0.0)], tick=1)
    ra = engine.recognize([_social_cue(0.0)], tick=2)
    hid_a = ra.matches[0].hypothesis_id
    engine.recognize([_social_cue(1.0)], tick=1)
    rb = engine.recognize([_social_cue(1.0)], tick=2)
    hid_b = rb.matches[0].hypothesis_id
    assert hid_a != hid_b

    tick = 10
    for _ in range(5):
        # A: contingent responder
        pa = engine.create_pending(
            hypothesis_id=hid_a, context="play", signal="SIGNAL_PLAY",
            execution_id=f"a{tick}", signal_tick=tick, recognition_confidence=1.0,
            governance_admitted=True, capability_executed=True, store=store,
        )
        engine.observe_outcome(
            pa.pending_interaction_id, response_tick=tick + 3, response_observed=True,
            store=store, memory=mem,
        )
        # B: equally frequent, never responds
        pb = engine.create_pending(
            hypothesis_id=hid_b, context="play", signal="SIGNAL_PLAY",
            execution_id=f"b{tick}", signal_tick=tick, recognition_confidence=1.0,
            governance_admitted=True, capability_executed=True, store=store,
        )
        engine.observe_outcome(
            pb.pending_interaction_id, response_tick=tick + 40, response_observed=False,
            store=store, memory=mem,
        )
        tick += 50

    rel_a = engine.hypotheses[hid_a].reliability_by_context.get("play", 0.0)
    rel_b = engine.hypotheses[hid_b].reliability_by_context.get("play", 0.0)
    assert rel_a > rel_b
    assert rel_b == 0.0
    cell_a = engine.contingency_cells[engine._cell_key(hid_a, "play", "SIGNAL_PLAY")]
    cell_b = engine.contingency_cells[engine._cell_key(hid_b, "play", "SIGNAL_PLAY")]
    assert cell_a.contingent_count == 5
    assert cell_b.contingent_count == 0
    assert cell_b.none_count == 5
    store.close()


def test_noncontingent_events_do_not_build_reliability(tmp_path):
    from umbra_core.memory import MemoryEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()

    tick = 10
    # NONE (no response), COINCIDENTAL (latency 0), EXTERNAL (competing cause)
    scenarios = [
        dict(response_tick=tick + 40, response_observed=False),
        dict(response_tick=tick, response_observed=True),
        dict(response_tick=tick + 3, response_observed=True, external_cause=True),
    ]
    for i, sc in enumerate(scenarios):
        p = engine.create_pending(
            hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
            execution_id=f"n{i}", signal_tick=tick, recognition_confidence=1.0,
            governance_admitted=True, capability_executed=True, store=store,
        )
        engine.observe_outcome(
            p.pending_interaction_id, store=store, memory=mem, **sc
        )
        tick += 50

    assert engine.hypotheses[hid].reliability_by_context.get("play", 0.0) == 0.0
    cell = engine.contingency_cells[engine._cell_key(hid, "play", "SIGNAL_PLAY")]
    assert cell.contingent_count == 0
    store.close()


def test_atomic_outcome_commit_crash_between_stages(tmp_path):
    from umbra_core.memory import MemoryEngine
    from umbra_core.persistence import PersistenceError
    from umbra_core.social import ResponseClass

    resolution_types = {
        "social_episode_finalized",
        "social_episode_outcome",
        "social_contingency_updated",
        "social_reliability_revised",
        "social_pending_resolved",
    }
    for stage in range(1, 6):
        store = _new_store(tmp_path, f"crash{stage}.db")
        mem = MemoryEngine.create("agent-1", seed=1)
        engine, hid = _familiar_engine()
        p = engine.create_pending(
            hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
            execution_id="e1", signal_tick=5, recognition_confidence=1.0,
            governance_admitted=True, capability_executed=True, store=store,
        )
        with pytest.raises(PersistenceError):
            engine.observe_outcome(
                p.pending_interaction_id, response_tick=8, response_observed=True,
                store=store, memory=mem, crash_after_stage=stage,
            )
        # No partial durable state
        types = [e["event_type"] for e in store.iter_events()]
        assert resolution_types.isdisjoint(types), f"stage {stage} leaked {types}"
        assert store.social_evidence_links_for(hid) == []
        store.validate_chain()  # ledger stays consistent after rollback
        # No partial in-memory state
        assert engine.pending[p.pending_interaction_id].status == "PENDING"
        assert engine.contingency_cells == {}
        assert engine.hypotheses[hid].reliability_by_context == {}
        store.close()

    # Success path commits everything atomically
    store = _new_store(tmp_path, "commit_ok.db")
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()
    p = engine.create_pending(
        hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
        execution_id="e1", signal_tick=5, recognition_confidence=1.0,
        governance_admitted=True, capability_executed=True, store=store,
    )
    cls = engine.observe_outcome(
        p.pending_interaction_id, response_tick=8, response_observed=True,
        store=store, memory=mem,
    )
    assert cls == ResponseClass.CONTINGENT
    types = [e["event_type"] for e in store.iter_events()]
    for t in resolution_types:
        assert t in types, f"missing {t}"
    assert len(store.social_evidence_links_for(hid)) == 1
    assert engine.pending[p.pending_interaction_id].status == "RESOLVED"
    cell = engine.contingency_cells[engine._cell_key(hid, "play", "SIGNAL_PLAY")]
    assert cell.contingent_count == 1
    assert engine.hypotheses[hid].reliability_by_context["play"] > 0.0
    store.validate_chain()
    store.close()


def test_pending_survives_restart_or_resolves_deterministically(tmp_path):
    from umbra_core.social import SocialEngine

    store = _new_store(tmp_path)
    engine, hid = _familiar_engine()
    p = engine.create_pending(
        hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
        execution_id="e1", signal_tick=5, recognition_confidence=1.0,
        governance_admitted=True, capability_executed=True, store=store,
    )
    pid = p.pending_interaction_id
    state = engine.to_state()

    # Restart within the response window → resume, no settlement event
    within = SocialEngine.from_state(state)
    assert pid in within.pending
    assert within.pending[pid].status == "PENDING"
    within.resume_pending(store=store, now_tick=8)
    assert within.pending[pid].status == "PENDING"
    assert "social_pending_expired" not in [e["event_type"] for e in store.iter_events()]

    # Restart after the window elapsed → deterministic expiry, no partner evidence
    elapsed = SocialEngine.from_state(state)
    elapsed.resume_pending(store=store, now_tick=5 + 40)
    assert elapsed.pending[pid].status == "EXPIRED"
    assert elapsed.contingency_cells == {}
    assert elapsed.hypotheses[hid].reliability_by_context == {}
    assert "social_pending_expired" in [e["event_type"] for e in store.iter_events()]
    store.close()


def test_pending_cannot_become_evidence_twice(tmp_path):
    from umbra_core.memory import MemoryEngine
    from umbra_core.social import ResponseClass, SocialEngineError

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()
    p = engine.create_pending(
        hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
        execution_id="e1", signal_tick=5, recognition_confidence=1.0,
        governance_admitted=True, capability_executed=True, store=store,
    )
    pid = p.pending_interaction_id
    assert engine.observe_outcome(
        pid, response_tick=8, response_observed=True, store=store, memory=mem
    ) == ResponseClass.CONTINGENT
    cell = engine.contingency_cells[engine._cell_key(hid, "play", "SIGNAL_PLAY")]
    assert cell.contingent_count == 1

    with pytest.raises(SocialEngineError):
        engine.observe_outcome(
            pid, response_tick=8, response_observed=True, store=store, memory=mem
        )
    assert cell.contingent_count == 1
    assert len(store.social_evidence_links_for(hid)) == 1
    store.close()


def test_ninth_pending_rejected_without_orphan(tmp_path):
    """MAX_PENDING_INTERACTIONS=8: a 9th open bid must raise BEFORE any mutation —
    no orphaned in-memory trace, no durable social_pending_created for it."""
    from umbra_core.social import SocialEngineError

    store = _new_store(tmp_path)
    engine, hid = _familiar_engine()
    tick = 5
    for i in range(8):
        engine.create_pending(
            hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
            execution_id=f"e{i}", signal_tick=tick, recognition_confidence=1.0,
            governance_admitted=True, capability_executed=True, store=store,
        )
        tick += 1
    assert len(engine.pending) == 8

    with pytest.raises(SocialEngineError, match="too_many_open_pending_interactions"):
        engine.create_pending(
            hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
            execution_id="e-overflow", signal_tick=tick, recognition_confidence=1.0,
            governance_admitted=True, capability_executed=True, store=store,
        )

    open_count = sum(1 for p in engine.pending.values() if p.status == "PENDING")
    assert open_count <= 8
    assert len(engine.pending) == 8  # no orphan added
    assert "e-overflow" not in [p.execution_id for p in engine.pending.values()]
    types = [e["event_type"] for e in store.iter_events()]
    assert types.count("social_pending_created") == 8  # no durable event for the rejected 9th
    store.close()


def test_pending_interrupted_when_recognition_contests_open_window(tmp_path):
    """A pending bid tied to a hypothesis that becomes CONTESTED mid-window must be
    durably interrupted, not silently left open or silently resolved."""
    from umbra_core.social import PendingStatus, SocialEngine

    store = _new_store(tmp_path)
    engine = SocialEngine.create("agent-1", seed=1)
    r1 = engine.recognize([_social_cue(0.0)], tick=1, store=store)
    hid_a = r1.matches[0].hypothesis_id
    r2 = engine.recognize([_social_cue(1.0)], tick=2, store=store)
    hid_b = r2.matches[0].hypothesis_id
    assert hid_a != hid_b

    p = engine.create_pending(
        hypothesis_id=hid_a, context="play", signal="SIGNAL_PLAY",
        execution_id="e1", signal_tick=3, recognition_confidence=1.0,
        governance_admitted=True, capability_executed=True, store=store,
    )
    pid = p.pending_interaction_id

    # A cue exactly between the two prototypes contests both hypotheses.
    engine.recognize([_social_cue(0.5)], tick=4, store=store)

    assert engine.hypotheses[hid_a].status == "CONTESTED"
    assert engine.pending[pid].status == PendingStatus.INTERRUPTED.value
    events = [e for e in store.iter_events() if e["event_type"] == "social_pending_interrupted"]
    assert len(events) == 1
    assert events[0]["payload"]["pending_interaction_id"] == pid
    assert events[0]["payload"]["reason"] == "recognition_contested"
    store.close()


def test_resume_pending_interrupts_corrupted_timing_state(tmp_path):
    """resume_pending must interrupt (not silently expire or resume) a trace whose
    durable timing state is corrupted/incomplete."""
    from umbra_core.social import PendingStatus

    store = _new_store(tmp_path)
    engine, hid = _familiar_engine()
    p = engine.create_pending(
        hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
        execution_id="e1", signal_tick=5, recognition_confidence=1.0,
        governance_admitted=True, capability_executed=True, store=store,
    )
    pid = p.pending_interaction_id
    engine.pending[pid].response_window = []  # simulate corrupted/incomplete durable state

    result = engine.resume_pending(store=store, now_tick=8)
    assert pid in result["interrupted"]
    assert engine.pending[pid].status == PendingStatus.INTERRUPTED.value
    events = [e for e in store.iter_events() if e["event_type"] == "social_pending_interrupted"]
    assert len(events) == 1
    assert events[0]["payload"]["reason"] == "corrupted_timing_state"
    store.close()


def test_missing_authoritative_social_event_fails_closed():
    from umbra_core.social import SocialEngine, SocialEngineError

    created = {
        "event_type": "social_pending_created",
        "payload": {
            "pending_interaction_id": "pY",
            "hypothesis_id_at_signal": "h1",
            "recognition_confidence": 1.0,
            "context": "play",
            "signal": "SIGNAL_PLAY",
            "execution_id": "e1",
            "signal_tick": 5,
            "response_window": [1, 32],
        },
    }
    resolved = {
        "event_type": "social_pending_resolved",
        "payload": {"pending_interaction_id": "pY", "classification": "CONTINGENT"},
    }

    # Resolution referencing a pending with no authoritative created event → fail closed
    with pytest.raises(SocialEngineError, match="missing_authoritative"):
        SocialEngine.reconstruct_pending([resolved])

    # Created + resolved → settled, nothing unresolved
    assert SocialEngine.reconstruct_pending([created, resolved]) == {}

    # Created only → survives as unresolved (never silently dropped)
    unresolved = SocialEngine.reconstruct_pending([created])
    assert "pY" in unresolved
    assert unresolved["pY"].status == "PENDING"


# --- Task 6: merge/split provenance + reliability revision + partner swap ---


def _build_reliability(engine, hid, store, mem, *, context="play", contingent=3, none=0):
    """Helper: build reliability via atomic outcome commits."""
    tick = 10
    for _ in range(contingent):
        p = engine.create_pending(
            hypothesis_id=hid, context=context, signal="SIGNAL_PLAY",
            execution_id=f"c{tick}", signal_tick=tick, recognition_confidence=1.0,
            governance_admitted=True, capability_executed=True, store=store,
        )
        engine.observe_outcome(
            p.pending_interaction_id, response_tick=tick + 3, response_observed=True,
            store=store, memory=mem,
        )
        tick += 50
    for _ in range(none):
        p = engine.create_pending(
            hypothesis_id=hid, context=context, signal="SIGNAL_PLAY",
            execution_id=f"n{tick}", signal_tick=tick, recognition_confidence=1.0,
            governance_admitted=True, capability_executed=True, store=store,
        )
        engine.observe_outcome(
            p.pending_interaction_id, response_tick=tick + 40, response_observed=False,
            store=store, memory=mem,
        )
        tick += 50
    return engine.hypotheses[hid].reliability_by_context.get(context, 0.0)


def test_hypothesis_merge_preserves_provenance(tmp_path):
    from umbra_core.social import HypothesisStatus, SocialEngine

    store = _new_store(tmp_path)
    engine = SocialEngine.create("agent-1", seed=1)
    r1 = engine.recognize([_social_cue(0.0)], tick=1)
    hid_a = r1.matches[0].hypothesis_id
    r2 = engine.recognize([_social_cue(1.0)], tick=2)
    hid_b = r2.matches[0].hypothesis_id
    engine.record_contingency_sample(hid_a, "play", "SIGNAL_PLAY", tick=3, latency_ticks=3.0)
    engine.add_evidence_ref(hid_a, "ep-a1")
    engine.add_evidence_ref(hid_b, "ep-b1")

    merged_id = engine.merge_hypotheses([hid_a, hid_b], store=store, tick=10)

    assert merged_id not in (hid_a, hid_b)
    merged = engine.hypotheses[merged_id]
    assert hid_a in merged.source_hypothesis_ids
    assert hid_b in merged.source_hypothesis_ids
    # Non-destructive: sources archived, histories inspectable
    assert hid_a in engine.archived_hypotheses
    assert hid_b in engine.archived_hypotheses
    assert engine.archived_hypotheses[hid_a].status == HypothesisStatus.INACTIVE.value
    assert engine.archived_hypotheses[hid_b].evidence_refs == ["ep-b1"]
    # Contingency on source id preserved (not moved/deleted)
    key_a = engine._cell_key(hid_a, "play", "SIGNAL_PLAY")
    assert key_a in engine.contingency_cells
    assert engine.contingency_cells[key_a].hypothesis_id == hid_a

    events = [e for e in store.iter_events() if e["event_type"] == "social_hypothesis_merged"]
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["merged_hypothesis_id"] == merged_id
    assert set(payload["source_hypothesis_ids"]) == {hid_a, hid_b}
    links = store.social_hypothesis_provenance_links_for(merged_id)
    assert {hid_a, hid_b} == {lnk["source_hypothesis_id"] for lnk in links}
    store.close()


def test_hypothesis_split_preserves_provenance(tmp_path):
    from umbra_core.social import HypothesisStatus, SocialEngine

    store = _new_store(tmp_path)
    engine = SocialEngine.create("agent-1", seed=1)
    r = engine.recognize([_social_cue()], tick=1)
    parent_id = r.matches[0].hypothesis_id
    engine.add_evidence_ref(parent_id, "ep-1")
    engine.add_evidence_ref(parent_id, "ep-2")
    engine.add_evidence_ref(parent_id, "ep-3")

    id_a, id_b = engine.split_hypothesis(
        parent_id,
        {"ep-1": "a", "ep-2": "a", "ep-3": "b"},
        store=store,
        tick=20,
    )

    assert id_a != id_b != parent_id
    assert parent_id in engine.archived_hypotheses
    assert engine.archived_hypotheses[parent_id].status == HypothesisStatus.INACTIVE.value
    assert engine.hypotheses[id_a].source_hypothesis_ids == [parent_id]
    assert engine.hypotheses[id_b].source_hypothesis_ids == [parent_id]
    assert set(engine.hypotheses[id_a].evidence_refs) == {"ep-1", "ep-2"}
    assert engine.hypotheses[id_b].evidence_refs == ["ep-3"]

    events = [e for e in store.iter_events() if e["event_type"] == "social_hypothesis_split"]
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["parent_hypothesis_id"] == parent_id
    assert payload["child_hypothesis_ids"] == [id_a, id_b]
    assert payload["evidence_partition"]["ep-1"] == "a"
    links = store.social_hypothesis_provenance_links_for(id_a) + store.social_hypothesis_provenance_links_for(id_b)
    assert any(lnk["source_hypothesis_id"] == parent_id for lnk in links)
    store.close()


def test_partner_swap_is_detected():
    from umbra_core.social import SocialEngine

    events: list[tuple[str, dict]] = []
    engine = SocialEngine.create("agent-1", seed=1, emit_event=lambda t, p: events.append((t, p)))

    engine.recognize([_social_cue(0.0)], tick=1)
    ra = engine.recognize([_social_cue(0.0)], tick=2)
    hid_a = ra.matches[0].hypothesis_id
    assert engine.hypotheses[hid_a].status == "FAMILIAR"

    engine.recognize([_social_cue(1.0)], tick=3)
    rb = engine.recognize([_social_cue(1.0)], tick=4)
    hid_b = rb.matches[0].hypothesis_id
    assert hid_b != hid_a

    # Cue matching partner B while A was recently familiar → swap detected, not merged.
    engine.recognize([_social_cue(1.0)], tick=5)
    swap_events = [p for t, p in events if t == "social_partner_swap_detected"]
    assert len(swap_events) >= 1
    assert swap_events[-1]["from_hypothesis_id"] == hid_a
    assert swap_events[-1]["to_hypothesis_id"] == hid_b


def test_partner_models_remain_separate(tmp_path):
    from umbra_core.memory import MemoryEngine
    from umbra_core.social import SocialEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine = SocialEngine.create("agent-1", seed=1)

    engine.recognize([_social_cue(0.0)], tick=1)
    ra = engine.recognize([_social_cue(0.0)], tick=2)
    hid_a = ra.matches[0].hypothesis_id
    engine.recognize([_social_cue(1.0)], tick=3)
    rb = engine.recognize([_social_cue(1.0)], tick=4)
    hid_b = rb.matches[0].hypothesis_id

    rel_a = _build_reliability(engine, hid_a, store, mem, contingent=3)
    rel_b = _build_reliability(engine, hid_b, store, mem, contingent=1)
    assert rel_a > rel_b

    # Swap cue — histories must not merge; A retains higher reliability.
    engine.recognize([_social_cue(1.0)], tick=50)
    assert hid_a in engine.hypotheses
    assert hid_b in engine.hypotheses
    assert engine.hypotheses[hid_a].reliability_by_context["play"] == rel_a
    assert engine.hypotheses[hid_b].reliability_by_context["play"] == rel_b
    assert engine.hypotheses[hid_a].reliability_by_context["play"] > engine.hypotheses[hid_b].reliability_by_context["play"]
    store.close()


def test_single_failure_does_not_destroy_reliability(tmp_path):
    from umbra_core.memory import MemoryEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()

    baseline = _build_reliability(engine, hid, store, mem, contingent=4)
    assert baseline > 0.5

    p = engine.create_pending(
        hypothesis_id=hid, context="play", signal="SIGNAL_PLAY",
        execution_id="fail1", signal_tick=300, recognition_confidence=1.0,
        governance_admitted=True, capability_executed=True, store=store,
    )
    engine.observe_outcome(
        p.pending_interaction_id, response_tick=340, response_observed=False,
        store=store, memory=mem,
    )
    after_one = engine.hypotheses[hid].reliability_by_context["play"]
    assert after_one > 0.0
    assert after_one > baseline * 0.5  # slight weaken, not destroyed
    assert baseline - after_one < baseline * 0.2
    store.close()


def test_repeated_failure_revises_expectation(tmp_path):
    from umbra_core.memory import MemoryEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()

    baseline = _build_reliability(engine, hid, store, mem, contingent=4)
    after_repeated = _build_reliability(engine, hid, store, mem, contingent=0, none=3)
    assert after_repeated < baseline * 0.5
    assert after_repeated < baseline - 0.15
    store.close()



# --- Task 7: soft social proposals + hybrid actuation wiring in runtime ---


def _soc_org(tmp_path, seed: int = 1, **kwargs):
    from umbra_core.runtime import OrganismConfig, create_organism

    db_path = kwargs.pop("db_path", None) or str(tmp_path / f"soc{seed}.sqlite")
    cfg = dict(
        db_path=db_path,
        seed=seed,
        social_enabled=True,
        social_history=kwargs.pop("social_history", "H0"),
        condition=kwargs.pop("condition", "C0"),
        drift_enabled=False,
    )
    cfg.update(kwargs)
    return create_organism(OrganismConfig(**cfg))


def test_social_urgency_cannot_bypass_governance():
    """A high-opportunity social proposal is just a `Candidate` — governance's SIGNAL
    cooldown denies it exactly like any other origin. No special-cased bypass path."""
    from umbra_core.governance import Governance, GovernanceState
    from umbra_core.physiology import Physiology

    engine, hid = _familiar_engine()
    engine.hypotheses[hid].familiarity = 1.0  # cross the opportunity gate deterministically
    cand = engine.propose(Physiology(), [_social_cue()], tick=5, critical=False)
    assert cand is not None
    assert cand.capability in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE")

    gov = Governance(GovernanceState(last_signal_tick=3, signal_cooldown_ticks=6))
    prop = gov.propose(cand.capability, cand.params)
    dec = gov.admit(prop, tick=5)
    assert not dec.admitted
    assert dec.reason == "signal_cooldown"

    # Critical physiology overrides social outright — no proposal at all, denial or not.
    assert engine.propose(Physiology(), [_social_cue()], tick=5, critical=True) is None


def test_relationship_memory_cannot_grant_authority():
    from umbra_core.social import SocialEngine

    engine, hid = _familiar_engine()
    hyp = engine.hypotheses[hid]
    content = {
        "hypothesis_id": hid,
        "reliability_by_context": dict(hyp.reliability_by_context),
        "familiarity": hyp.familiarity,
    }
    assert engine.try_grant_authority(content) is False
    assert SocialEngine.create("agent-2", seed=1).try_grant_authority({}) is False


def test_scalar_affection_is_not_relationship_authority():
    """Familiarity/satiation/reliability are plain floats consumed only by `propose()`
    for soft biasing — never an authority grant, never a governance-bypass key."""
    from dataclasses import fields

    from umbra_core.social import PartnerHypothesis

    field_names = {f.name for f in fields(PartnerHypothesis)}
    forbidden = {"authority", "granted_capabilities", "trust_level", "grant_capability"}
    assert field_names.isdisjoint(forbidden)

    engine, hid = _familiar_engine()
    engine.hypotheses[hid].familiarity = 1.0  # maximal scalar affection
    cand = engine.propose(None, [_social_cue()], tick=5, critical=False)
    assert cand is not None
    assert "requested_effects" not in cand.params
    assert not any("authority" in k or "grant" in k for k in cand.params)


def test_social_pins_self_world_memory_to_c0(tmp_path):
    """When `social_enabled` owns `condition`, self/world/memory configs stay at
    baseline C0 (same pin pattern as the D-005 `memory_enabled` case), even though
    `condition="C7"` requests a social ablation (random social actions)."""
    from dataclasses import asdict

    from umbra_core.memory import condition_to_memory_config
    from umbra_core.runtime import condition_to_self_model_config
    from umbra_core.self_model import SelfModelConfig
    from umbra_core.world_model import condition_to_world_model_config

    org = _soc_org(
        tmp_path,
        condition="C7",
        world_model_enabled=True,
        memory_enabled=True,
    )
    assert asdict(org.self_model.config) == asdict(condition_to_self_model_config("C0"))
    assert org.self_model.config != SelfModelConfig(fixed_authored=True)  # sanity: C1 differs
    assert asdict(org.world_model.config) == asdict(condition_to_world_model_config("C0"))
    assert asdict(org.memory.config) == asdict(condition_to_memory_config("C0"))
    # The social engine itself DOES receive the C7 (random-social-actions) config.
    assert org.social.config.random_social_actions is True


def test_social_pins_self_world_memory_to_c0_on_reload(tmp_path):
    """After restart, `load_organism` must apply the same C0 pin as `create_organism`
    when `social_enabled` owns `condition` — not re-derive ablated self/world/memory
    configs from the social condition label."""
    from dataclasses import asdict

    from umbra_core.memory import condition_to_memory_config
    from umbra_core.runtime import OrganismConfig, load_organism
    from umbra_core.runtime import condition_to_self_model_config
    from umbra_core.self_model import SelfModelConfig
    from umbra_core.world_model import condition_to_world_model_config

    db = str(tmp_path / "soc-reload.sqlite")
    org = _soc_org(
        tmp_path,
        db_path=db,
        condition="C7",
        world_model_enabled=True,
        memory_enabled=True,
    )
    org.run_ticks(5)
    org.close()

    reloaded = load_organism(
        OrganismConfig(
            db_path=db,
            seed=1,
            social_enabled=True,
            condition="C7",
            world_model_enabled=True,
            memory_enabled=True,
        )
    )
    assert asdict(reloaded.self_model.config) == asdict(
        condition_to_self_model_config("C0")
    )
    assert reloaded.self_model.config != SelfModelConfig(fixed_authored=True)
    assert asdict(reloaded.world_model.config) == asdict(
        condition_to_world_model_config("C0")
    )
    assert asdict(reloaded.memory.config) == asdict(condition_to_memory_config("C0"))
    assert reloaded.social.config.random_social_actions is True
    reloaded.close()


def test_full_tick_recognizes_proposes_governs_and_opens_pending(tmp_path):
    """End-to-end wiring: recognize -> resolve pendings -> soft propose -> govern ->
    execute -> create_pending, driven entirely through `Organism.tick_once()`."""
    org = _soc_org(tmp_path)
    # Test-only placement beside the H0-plant spawn point (12.0, 8.0) so recognition
    # accumulates familiarity without depending on multi-tick APPROACH movement noise.
    org.embodiment.body.x = 11.0
    org.embodiment.body.y = 8.0

    for _ in range(10):
        org.tick_once()
        events = [e["event_type"] for e in org.store.iter_events()]
        if "social_pending_created" in events:
            break

    events = [e["event_type"] for e in org.store.iter_events()]
    assert "social_pending_created" in events
    assert org.social is not None
    assert len(org.social.pending) >= 1
    # A denial never opens a pending trace (design §5) — every created pending here
    # traces back to an admitted+executed proposal event on the same tick.
    signal_admits = [
        e
        for e in org.store.iter_events()
        if e["event_type"] == "proposal"
        and e["payload"]["capability"] in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE")
    ]
    assert signal_admits and all(e["payload"]["admitted"] for e in signal_admits)


def test_recovery_history_revises_expectation(tmp_path):
    from umbra_core.memory import MemoryEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()

    baseline = _build_reliability(engine, hid, store, mem, contingent=3)
    lowered = _build_reliability(engine, hid, store, mem, contingent=0, none=2)
    assert lowered < baseline

    recovered = _build_reliability(engine, hid, store, mem, contingent=2, none=0)
    assert recovered > lowered
    assert recovered <= 1.0
    store.close()


# --- Task 8: shared routines via D-005 procedural promotion ---


def test_shared_routine_is_learned(tmp_path):
    from umbra_core.memory import MemoryEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()

    assert not engine.routine_eligible(hid, "play", "SIGNAL_PLAY", mem)
    _build_reliability(engine, hid, store, mem, contingent=3)

    assert engine.routine_eligible(hid, "play", "SIGNAL_PLAY", mem)
    skill_id = engine.maybe_promote_routine(
        hid, "play", "SIGNAL_PLAY", mem, store=store, tick=200
    )
    assert skill_id is not None
    sk = mem.procedural[skill_id]
    assert sk.applicability["kind"] == "social_routine"
    assert sk.applicability["partner_hypothesis"] == hid
    assert sk.applicability["context"] == "play"
    assert sk.applicability["soft_proposals"] == ["APPROACH_PARTNER", "OFFER_PLAY"]
    assert len(sk.source_episode_ids) >= 3
    events = [e for e in store.iter_events() if e["event_type"] == "social_routine_promoted"]
    assert len(events) == 1
    store.close()


def test_full_tick_proposes_routine_ordered_intent_after_promotion(tmp_path):
    """After promotion, `Organism.tick_once()` must wire memory into propose() and
    emit the first routine-ordered soft intent — not only the direct API path."""
    org = _soc_org(tmp_path, memory_enabled=True)
    org.embodiment.body.x = 11.0
    org.embodiment.body.y = 8.0
    assert org.social is not None and org.memory is not None
    org.social.recognize([_social_cue()], tick=1)
    r = org.social.recognize([_social_cue()], tick=2)
    hid = r.matches[0].hypothesis_id
    _build_reliability(org.social, hid, org.store, org.memory, contingent=3)
    skill_id = org.social.maybe_promote_routine(
        hid, "play", "SIGNAL_PLAY", org.memory, store=org.store, tick=200
    )
    assert skill_id is not None
    org.tick = 200

    result = org.tick_once()
    assert result["capability"] == "APPROACH"
    proposals = [
        e
        for e in org.store.iter_events()
        if e["event_type"] == "proposal"
        and e["payload"].get("capability") == "APPROACH"
    ]
    assert proposals
    org.close()


def test_contested_recognition_interrupts_active_routine(tmp_path):
    from umbra_core.memory import MemoryEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid_a = _familiar_engine(seed_tag=0.0)
    engine.recognize([_social_cue(1.0)], tick=3)
    engine.recognize([_social_cue(1.0)], tick=4)
    _build_reliability(engine, hid_a, store, mem, contingent=3)
    engine.maybe_promote_routine(hid_a, "play", "SIGNAL_PLAY", mem, store=store, tick=200)
    assert engine.next_routine_proposal(hid_a, "play", tick=201, memory=mem) == "APPROACH_PARTNER"
    rkey = engine._routine_key(hid_a, "play", "SIGNAL_PLAY")
    assert engine.routine_handles[rkey].status == "ACTIVE"

    engine.recognize([_social_cue(0.5)], tick=202, store=store)
    assert engine.routine_handles[rkey].status == "INTERRUPTED"
    events = [e for e in store.iter_events() if e["event_type"] == "social_routine_deactivated"]
    assert any(e["payload"]["reason"] == "recognition_contested" for e in events)
    store.close()


def test_shared_routine_is_interruptible(tmp_path):
    from umbra_core.memory import MemoryEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()
    _build_reliability(engine, hid, store, mem, contingent=3)
    skill_id = engine.maybe_promote_routine(
        hid, "play", "SIGNAL_PLAY", mem, store=store, tick=200
    )
    assert skill_id is not None

    intent = engine.next_routine_proposal(hid, "play", tick=201, memory=mem)
    assert intent == "APPROACH_PARTNER"
    rkey = engine._routine_key(hid, "play", "SIGNAL_PLAY")
    assert engine.routine_handles[rkey].step_index == 1

    assert engine.interrupt_active_routine(hid, "partner_ambiguous", store=store, tick=202)
    assert engine.routine_handles[rkey].status == "INTERRUPTED"
    assert engine.next_routine_proposal(hid, "play", tick=203, memory=mem) is None

    cand = engine.propose(
        phys=type("P", (), {"critical_any": lambda self: False})(),
        cues=[_social_cue()],
        tick=204,
        critical=True,
        memory=mem,
    )
    assert cand is None
    store.close()


def test_scripted_routine_is_not_development(tmp_path):
    from umbra_core.memory import MemoryEngine, SocialRoutineSpec
    from umbra_core.social import SocialEngine, condition_to_social_config

    mem = MemoryEngine.create("agent-1", seed=1)
    with pytest.raises(ValueError, match="authored_routine_not_learned_development"):
        mem.promote_social_routine(
            SocialRoutineSpec(
                partner_hypothesis="hyp-1",
                context="play",
                signal="SIGNAL_PLAY",
                soft_proposals=["OFFER_PLAY"],
                supporting_episode_ids=["ep-1"],
                authored=True,
            )
        )

    cfg = condition_to_social_config("C8")
    assert cfg.scripted_routine is True
    store = _new_store(tmp_path)
    engine = SocialEngine.create("agent-1", seed=1, config=cfg)
    engine.recognize([_social_cue()], tick=1)
    r = engine.recognize([_social_cue()], tick=2)
    hid = r.matches[0].hypothesis_id
    _build_reliability(engine, hid, store, mem, contingent=3)

    assert not engine.routine_eligible(hid, "play", "SIGNAL_PLAY", mem)
    assert engine.maybe_promote_routine(hid, "play", "SIGNAL_PLAY", mem, store=store) is None
    assert not any(
        sk.applicability.get("kind") == "social_routine" for sk in mem.procedural.values()
    )
    store.close()


def test_relationship_state_has_episode_provenance(tmp_path):
    from umbra_core.memory import MemoryEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()
    _build_reliability(engine, hid, store, mem, contingent=3)

    links = store.social_evidence_links_for(hid)
    assert len(links) >= 3
    episode_ids = {lnk["episode_id"] for lnk in links}
    for eid in episode_ids:
        assert eid in mem.episodes
    assert episode_ids.issubset(set(engine.hypotheses[hid].evidence_refs))

    cell = engine.contingency_cells[engine._cell_key(hid, "play", "SIGNAL_PLAY")]
    assert len(cell.supporting_episode_ids) >= 3
    assert engine.hypotheses[hid].reliability_by_context["play"] > 0.0
    for eid in cell.supporting_episode_ids:
        assert eid in mem.episodes
    store.close()


# --- Task 10: persistence, restart, replay contracts (design §Gate 11) ---


def test_restart_preserves_partner_models(tmp_path):
    """Gate 11: relationship state (partner hypotheses) survives 100 restarts."""
    from umbra_core.runtime import OrganismConfig, load_organism

    db_path = str(tmp_path / "restart.sqlite")
    org = _soc_org(tmp_path, seed=30, db_path=db_path)
    org.social.recognize([_social_cue()], tick=1)
    r = org.social.recognize([_social_cue()], tick=2)
    hid = r.matches[0].hypothesis_id
    org.social.record_contingency_sample(
        hid, "play", "SIGNAL_PLAY", tick=2, latency_ticks=3.0, confidence=0.8
    )
    n_hyp = len(org.social.hypotheses)
    familiarity = org.social.hypotheses[hid].familiarity
    aid = org.identity.agent_id
    org.snapshot_if_due(force=True)
    org.close()

    load_cfg = dict(
        db_path=db_path,
        seed=30,
        social_enabled=True,
        social_history="H0",
        condition="C0",
        drift_enabled=False,
    )
    for _ in range(100):
        org2 = load_organism(OrganismConfig(**load_cfg))
        assert org2.identity.agent_id == aid
        assert org2.social is not None
        assert hid in org2.social.hypotheses
        assert len(org2.social.hypotheses) == n_hyp
        assert abs(org2.social.hypotheses[hid].familiarity - familiarity) < 1e-9
        org2.close()


def test_birth_and_snapshot_replay_match(tmp_path):
    """Gate 11: birth + authoritative social events reconstruct the same state as
    snapshot-accelerated replay for identical seed/ticks (design §5 'Replay')."""
    from umbra_core.runtime import resimulate

    kwargs = dict(
        social_enabled=True, social_history="H0", condition="C0", drift_enabled=False
    )
    a = resimulate(41, 40, str(tmp_path / "r1.sqlite"), **kwargs)
    b = resimulate(41, 40, str(tmp_path / "r2.sqlite"), **kwargs)
    assert a["tick"] == b["tick"]
    assert a["identity_agent_id"] == b["identity_agent_id"]
    assert a["social_accepted"] == b["social_accepted"]


def test_partner_and_routine_counts_are_bounded(tmp_path):
    """Gate 11/12: partner hypotheses and routine handles stay bounded across the
    full hypothesis lifetime, including hypotheses retired well past the active cap."""
    from umbra_core.memory import MemoryEngine
    from umbra_core.social import SocialEngine

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine = SocialEngine.create("agent-1", seed=1)
    tick = 1
    for i in range(40):
        tag = i * 5.0
        engine.recognize([_social_cue(tag)], tick=tick, store=store)
        tick += 1
        r = engine.recognize([_social_cue(tag)], tick=tick, store=store)
        tick += 1
        hid = r.matches[0].hypothesis_id
        if r.matches[0].status != "FAMILIAR":
            continue
        _build_reliability(engine, hid, store, mem, contingent=3)
        engine.maybe_promote_routine(
            hid, "play", "SIGNAL_PLAY", mem, store=store, tick=tick
        )
        tick += 200

    assert engine.counts_bounded()
    assert len(engine.hypotheses) <= engine.config.max_partner_hypotheses
    assert len(engine.routine_handles) <= engine.config.max_routine_handles
    store.close()


# --- Task 11: directive minimum tests — satiation, absence, manipulation, history ---


def test_social_interaction_satiates():
    """Gate 5: seeking declines after engagement — an accepted satiation rise turns
    a signal-seeking proposal into DISENGAGE, not a bigger or repeated bid."""
    from umbra_core.physiology import Physiology

    engine, hid = _familiar_engine()
    engine.hypotheses[hid].familiarity = 1.0
    cue = _social_cue()
    phys = Physiology()

    before = engine.propose(phys, [cue], tick=5, critical=False)
    assert before is not None
    assert before.params["social_intent"] in ("OFFER_PLAY", "REQUEST_ASSISTANCE")

    engine.update_satiation_anchor(hid, tick=5, delta=1.0)
    assert engine.current_satiation(hid, tick=5) >= engine.config.satiated_disengage_threshold

    after = engine.propose(phys, [cue], tick=5, critical=False)
    assert after is not None
    assert after.params["social_intent"] == "DISENGAGE"


def test_absence_does_not_escalate_bids():
    """Design §5/§9: no partner cues -> no proposal at all, for any absence length —
    there is no path by which absence produces a bid, let alone an escalating one."""
    from umbra_core.physiology import Physiology

    engine, hid = _familiar_engine()
    engine.hypotheses[hid].familiarity = 1.0
    phys = Physiology()

    results = [engine.propose(phys, [], tick=t, critical=False) for t in range(1, 5001, 250)]
    assert all(r is None for r in results)


def test_absence_does_not_increase_bid_frequency():
    """Gate 6: bid frequency during absence stays at zero regardless of how long the
    absence runs — a longer absence must not accumulate urgency into more bids."""
    from umbra_core.physiology import Physiology

    engine, hid = _familiar_engine()
    engine.hypotheses[hid].familiarity = 1.0
    phys = Physiology()

    short = sum(
        1 for t in range(1, 11) if engine.propose(phys, [], tick=t, critical=False) is not None
    )
    long = sum(
        1
        for t in range(1, 20001, 100)
        if engine.propose(phys, [], tick=t, critical=False) is not None
    )
    assert short == 0
    assert long == 0  # frequency does not rise with absence duration


def test_absence_does_not_damage_viability(tmp_path):
    """Gate 6: 'viability within prior bounds' — an H7 absence window must not push
    physiology into any critical excursion beyond what the H0 (partner-present)
    baseline already exhibits from ordinary D-001 dynamics unrelated to social."""

    def critical_trace(history):
        org = _soc_org(tmp_path, social_history=history, db_path=str(tmp_path / f"{history}.sqlite"))
        trace = []
        for _ in range(60):
            org.tick_once()
            if org.phys.critical_any():
                trace.append((org.tick, tuple(sorted(org.phys.critical_vars()))))
        org.close()
        return trace

    baseline = critical_trace("H0")
    absence = critical_trace("H7")
    assert absence == baseline  # absence adds no additional/worse critical excursions


def test_absence_does_not_reduce_relationship_state_as_punishment(tmp_path):
    """Absence alone (no interaction, no adverse outcome, only elapsed ticks) must not
    reduce familiarity or reliability — no relationship-score punishment for time
    passing without contact (design §5 absence path). Satiation decay is the only
    permitted time-derived change, and it never goes below zero."""
    from umbra_core.memory import MemoryEngine
    from umbra_core.physiology import Physiology

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)
    engine, hid = _familiar_engine()
    _build_reliability(engine, hid, store, mem, contingent=3)

    familiarity_before = engine.hypotheses[hid].familiarity
    reliability_before = dict(engine.hypotheses[hid].reliability_by_context)

    phys = Physiology()
    for t in range(10, 5000, 50):
        engine.propose(phys, [], tick=t, critical=False)  # absence: no partner cues

    assert engine.hypotheses[hid].familiarity == familiarity_before
    assert engine.hypotheses[hid].reliability_by_context == reliability_before
    assert engine.current_satiation(hid, tick=5000) >= 0.0
    store.close()


def test_different_histories_change_behavior(tmp_path):
    """Gate 2: different partner histories -> different probe behavior under
    identical probes (reliable-contingent vs unreliable-noncontingent history)."""
    from umbra_core.memory import MemoryEngine
    from umbra_core.physiology import Physiology

    store = _new_store(tmp_path)
    mem = MemoryEngine.create("agent-1", seed=1)

    reliable, hid_r = _familiar_engine(seed=11)
    _build_reliability(reliable, hid_r, store, mem, contingent=5)

    unreliable, hid_u = _familiar_engine(seed=12)
    _build_reliability(unreliable, hid_u, store, mem, contingent=0, none=5)

    assert reliable.hypotheses[hid_r].reliability_by_context.get("play", 0.0) > 0.5
    assert unreliable.hypotheses[hid_u].reliability_by_context.get("play", 0.0) == 0.0

    cue = _social_cue()
    phys = Physiology()
    reliable_cand = reliable.propose(phys, [cue], tick=1000, critical=False)
    unreliable_cand = unreliable.propose(phys, [cue], tick=1000, critical=False)

    assert reliable_cand is not None
    assert reliable_cand.params["social_intent"] in ("OFFER_PLAY", "REQUEST_ASSISTANCE")
    assert unreliable_cand is None  # opportunity below threshold -> resume independent activity
    store.close()


def _run_organism(history: str, seed: int, ticks: int, tmp_path):
    """Drive the REAL organism path: embodiment plant -> perception membrane ->
    SocialEngine.recognize inside Organism.tick_once (no synthetic cue injection)."""
    from umbra_core.runtime import OrganismConfig, create_organism

    db = str(tmp_path / f"e2e_{history}_{seed}.sqlite")
    org = create_organism(
        OrganismConfig(
            db_path=db, seed=seed, social_enabled=True, social_history=history,
            condition="C0", drift_enabled=False,
        )
    )
    for _ in range(ticks):
        org.tick_once()
    active = [h for h in org.social.hypotheses.values() if h.status != "INACTIVE"]
    swaps = int(org.social.metrics.get("partner_swaps_detected", 0))
    created = int(org.social.metrics.get("hypotheses_created", 0))
    org.close()
    return active, swaps, created


def test_organism_h8_distinct_partners_do_not_silently_merge(tmp_path):
    """Critical (Task 12 review): two distinct H8 partners perceived through the real
    embodiment->perception->recognize->tick_once path must form TWO separate
    hypotheses and trigger swap detection — NOT collapse into one silent merge.

    This is the end-to-end regression for the calibration bug where PartnerTrueCues
    separation was below PerceptionMembrane identity-cue noise.
    """
    for seed in range(5):
        active, swaps, created = _run_organism("H8", seed, ticks=60, tmp_path=tmp_path)
        assert len(active) == 2, f"seed {seed}: expected 2 distinct hypotheses, got {len(active)}"
        assert created == 2, f"seed {seed}: silent merge/false split (created={created})"
        assert swaps > 0, f"seed {seed}: swap discriminator never fired through real path"


def test_organism_h9_ambiguous_partners_are_not_split_into_distinct_identities(tmp_path):
    """H9 ambiguous partners have near-identical true cues; through the real path they
    must NOT be resolved into two confidently-distinct identities (they collapse to a
    single hypothesis rather than false-splitting)."""
    for seed in range(5):
        active, _swaps, created = _run_organism("H9", seed, ticks=60, tmp_path=tmp_path)
        assert len(active) == 1, f"seed {seed}: ambiguous partners split ({len(active)})"
        assert created == 1, f"seed {seed}: ambiguous false split (created={created})"


@pytest.mark.skip(
    reason="Gate 12 (100k accelerated ticks / 2h soak / RSS+CPU bounds) runs under "
    "Task 13 once soak evidence exists; pre-soak skip only — final sealed suite "
    "requires zero skips (design §8, directive Gate 13)."
)
def test_performance_soak_within_bounds():
    """Gate 12 placeholder — executed and unskipped in Task 13 with
    docs/evidence/d006/performance-results.json as evidence."""
    raise NotImplementedError("Task 13 supplies the soak harness and evidence")


def test_prior_seals_validate():
    """Gate 0/10: D-001 through D-005 seals validate and remain unchanged."""
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for seal in (
        "docs/evidence/d001/evidence-hashes.json",
        "docs/evidence/d002p/evidence-hashes.json",
        "docs/evidence/d003/evidence-hashes.json",
        "docs/evidence/d004/evidence-hashes.json",
        "docs/evidence/d005/evidence-hashes.json",
    ):
        data = json.loads((root / seal).read_text())
        for rel, expect in data.items():
            if rel.endswith("evidence-hashes.json"):
                continue
            p = root / rel
            if not p.exists():
                continue
            assert hashlib.sha256(p.read_bytes()).hexdigest() == expect, rel
    assert "UMBRA_D005_MEMORY_CONSOLIDATION_QUALIFIED" in (
        root / "docs/evidence/d005/final-verdict.md"
    ).read_text()


def test_prior_regressions_pass():
    """Gate 10: D-001 through D-005 qualified behavior remains within accepted
    bounds — key prior-directive assertions still hold."""
    from umbra_core.development import DevelopmentEngine
    from umbra_core.memory import MemoryEngine
    from umbra_core.self_model import SelfModel
    from umbra_core.world_model import WorldModel

    d = DevelopmentEngine.create("x", seed=1)
    assert d.learning_progress_from_windows(0.8, 0.4) == pytest.approx(0.4)
    w = WorldModel.create("x", seed=1)
    assert w is not None
    m = MemoryEngine.create("x", seed=1)
    assert m.counts_bounded()
    sm = SelfModel.create("x", now=0.0, seed=1)
    assert sm.active.body_schema_id is not None


def test_no_deferred_modules_added():
    """Gate 13: no deferred/foreign-scope modules added under this directive."""
    from pathlib import Path

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
    ]
    for rel in forbidden:
        assert not (root / rel).exists(), rel
    assert (root / "umbra_core/social").is_dir()
    social_init = (root / "umbra_core/social/__init__.py").read_text()
    assert "AffectionMeter" not in social_init
    assert (root / "experiments/d006/affection_controller.py").exists()
