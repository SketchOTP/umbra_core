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
