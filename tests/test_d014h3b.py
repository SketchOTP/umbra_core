from __future__ import annotations

from copy import deepcopy

from umbra_core.embodiment import _make_partner
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.events import (
    apply_habitat_event,
    build_initialized_event,
    replay_habitat_from_events,
)
from umbra_core.habitat.state import (
    FreeLocation,
    SocialEntitySpatialState,
    make_social_entity_object,
    sample_habitat_state,
)
from umbra_core.embodiment import Embodiment
from umbra_core.perception import PerceptionMembrane
from umbra_core.util import SeededRNG


def _social_object() -> object:
    partner = _make_partner("partner:d014", 6.0, 4.0, "H0", index=0)
    policy = partner.response_policy
    return make_social_entity_object(
        object_id="social:partner:d014",
        entity_ref=partner.hidden_partner_id,
        location=FreeLocation(6.0, 4.0, "zone:general"),
        history_code=policy.history_code,
        motion_signature=partner.true_cues.motion_signature,
        appearance_signature=partner.true_cues.appearance_signature,
        response_timing_pattern=partner.true_cues.response_timing_pattern,
        interaction_style_cues=partner.true_cues.interaction_style_cues,
        response_mode=policy.mode,
        contingent_probability=policy.contingent_probability,
        flip_at=policy.flip_at,
        absent_windows=tuple(policy.absent_windows),
    )


def test_social_entity_creation_replay_and_occlusion_are_authoritative():
    initial = sample_habitat_state()
    engine = HabitatEngine(initial)
    init_event = build_initialized_event(initial, event_id="evt:init")
    created = engine.commit_object_creation(
        _social_object(),
        event_id="evt:create",
        transaction_id="txn:create",
        request_id="req:create",
    )
    hidden = engine.commit_object_visibility(
        "social:partner:d014",
        occluded=True,
        event_id="evt:hide",
        transaction_id="txn:hide",
        request_id="req:hide",
    )
    events = [init_event, created, hidden]
    replayed = replay_habitat_from_events(events)
    assert replayed.state_hash == engine.state.state_hash
    assert replayed.objects["social:partner:d014"].occluded is True
    assert isinstance(replayed.objects["social:partner:d014"].state, SocialEntitySpatialState)
    assert replayed.objects["social:partner:d014"].state.entity_ref == "partner:d014"


def test_social_entity_bridge_is_anonymous_and_visibility_aware():
    engine = HabitatEngine(sample_habitat_state())
    engine.commit_object_creation(_social_object(), event_id="evt:create", transaction_id="txn:create", request_id="req:create")
    emb = Embodiment()
    emb.body.x, emb.body.y = 4.0, 3.0
    emb.attach_habitat_engine(engine)
    membrane = PerceptionMembrane(false_negative_rate=0.0, noise_sigma=0.0)
    membrane.perceive(emb, 600.0, SeededRNG(7))
    assert len(membrane.partner_cues) == 1
    assert "partner_id" not in membrane.policy_view()
    assert "hidden_partner_id" not in membrane.policy_view()
    assert "entity_ref" not in membrane.policy_view()

    engine.commit_object_visibility("social:partner:d014", occluded=True)
    membrane.perceive(emb, 2400.0, SeededRNG(7))
    assert membrane.partner_cues == []

    engine.commit_object_visibility("social:partner:d014", occluded=False)
    membrane.perceive(emb, 2600.0, SeededRNG(7))
    assert len(membrane.partner_cues) == 1


def test_identical_authoritative_replay_has_identical_hashes():
    def run_once():
        initial = sample_habitat_state()
        engine = HabitatEngine(initial)
        init_event = build_initialized_event(initial, event_id="evt:init")
        create_event = engine.commit_object_creation(_social_object(), event_id="evt:create", transaction_id="txn:create", request_id="req:create")
        hide_event = engine.commit_object_visibility("social:partner:d014", occluded=True, event_id="evt:hide", transaction_id="txn:hide", request_id="req:hide")
        show_event = engine.commit_object_visibility("social:partner:d014", occluded=False, event_id="evt:show", transaction_id="txn:show", request_id="req:show")
        events = [init_event, create_event, hide_event, show_event]
        return [event["event_type"] for event in events], [event["payload"]["new_state_hash"] for event in events], replay_habitat_from_events(events).state_hash

    assert run_once() == run_once()
