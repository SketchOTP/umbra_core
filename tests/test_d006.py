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


def test_c4_resets_relationship_state_between_encounters():
    from umbra_core.social import SocialEngine, condition_to_social_config

    cfg = condition_to_social_config("C4")
    assert cfg.persist_relationship is False
    engine = SocialEngine.create("agent-1", seed=1, config=cfg)
    engine.recognize([_social_cue()], tick=1)
    assert engine.hypotheses

    engine.reset_for_encounter_boundary()
    assert engine.hypotheses == {}

    engine.recognize([_social_cue()], tick=2)
    state = engine.to_state()
    restarted = SocialEngine.from_state(state, config=cfg)
    assert restarted.hypotheses == {}  # C4 also resets on restart, per design §6


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
