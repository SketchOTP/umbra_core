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
