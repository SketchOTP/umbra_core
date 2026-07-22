"""UMBRA-D-006 — social contingency (signal capabilities + event authority)."""


def test_signal_capabilities_exist_and_are_governed():
    from umbra_core.embodiment import CAPABILITIES

    assert "SIGNAL_PLAY" in CAPABILITIES
    assert "SIGNAL_ASSISTANCE" in CAPABILITIES


def test_social_event_authority_classes():
    from umbra_core.events import social_event_authority_class

    assert social_event_authority_class("social_pending_created") == "AUTHORITATIVE"
    assert social_event_authority_class("social_recognition_updated") == "AUTHORITATIVE"
    assert social_event_authority_class("social_match_score") == "DIAGNOSTIC"
