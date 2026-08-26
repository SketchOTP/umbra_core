from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from umbra_core.embodiment import (
    Embodiment,
    HabitatAuthorityError,
    _make_partner,
)
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.state import (
    FreeLocation,
    make_social_entity_object,
    sample_habitat_state,
    with_state_hash,
)


def _social_object():
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


def _engine_with_social():
    engine = HabitatEngine(sample_habitat_state())
    engine.commit_object_creation(
        _social_object(),
        event_id="h3f:create",
        transaction_id="h3f:create-tx",
        request_id="h3f:create-req",
    )
    return engine


def test_legacy_no_engine_snapshot_roundtrip_is_unchanged():
    embodiment = Embodiment()
    state = embodiment.to_state()
    restored = Embodiment.from_state(state)
    assert restored.to_state() == state
    assert "habitat_authority" in state
    assert state["habitat_authority"] is None


def test_engine_snapshot_keeps_projection_sanitized_and_social_rows_out_of_legacy_state():
    engine = _engine_with_social()
    embodiment = Embodiment()
    embodiment.attach_habitat_engine(engine)

    projected = embodiment.habitat
    assert len(projected.partners) == 1
    assert not hasattr(projected.partners[0], "hidden_partner_id")
    state = embodiment.to_state()

    assert state["habitat"]["partners"] == []
    assert state["habitat_authority"]["habitat_id"] == engine.state.habitat_id
    assert state["habitat_authority"]["state_hash"] == engine.state.state_hash
    assert "response_policy" not in state["habitat"]
    assert "true_cues" not in state["habitat"]


def test_projection_shaped_snapshot_migrates_without_hidden_social_state():
    engine = _engine_with_social()
    embodiment = Embodiment()
    embodiment.attach_habitat_engine(engine)
    projection_state = embodiment.habitat.to_state()

    migrated = Embodiment.from_state({"habitat": projection_state, "body": embodiment.body.to_state()})

    assert migrated.habitat_authority_binding["habitat_id"] == projection_state["habitat_id"]
    with pytest.raises(HabitatAuthorityError, match="reattachment_required"):
        _ = migrated.habitat
    assert migrated._habitat.partners == []


def test_engine_reattachment_requires_exact_id_version_and_hash():
    engine = _engine_with_social()
    source = Embodiment()
    source.attach_habitat_engine(engine)
    snapshot = source.to_state()

    for field, value in (
        ("habitat_id", "wrong"),
        ("state_version", engine.state.state_version + 1),
        ("state_hash", "0" * 64),
    ):
        migrated = Embodiment.from_state(snapshot)
        wrong_state = replace(engine.state, **{field: value})
        if field != "state_hash":
            wrong_state = with_state_hash(wrong_state)
        wrong = HabitatEngine(wrong_state)
        with pytest.raises(HabitatAuthorityError, match=f"reattachment_{field}_mismatch"):
            migrated.attach_habitat_engine(wrong)


def test_correct_engine_reattaches_and_preserves_authority():
    engine = _engine_with_social()
    source = Embodiment()
    source.attach_habitat_engine(engine)
    snapshot = source.to_state()

    restored = Embodiment.from_state(snapshot)
    restored.attach_habitat_engine(HabitatEngine(deepcopy(engine.state)))

    assert restored.habitat_authority_binding["habitat_id"] == engine.state.habitat_id
    assert restored.habitat_authority_binding["state_hash"] == engine.state.state_hash
    assert len(restored.habitat.partners) == 1

def test_loaded_engine_bound_organism_cannot_tick_before_reattachment(tmp_path):
    from umbra_core.runtime import OrganismConfig, create_organism, load_organism

    db_path = tmp_path / "engine-bound.sqlite"
    config = OrganismConfig(
        db_path=str(db_path),
        seed=17,
        wall_time_fn=lambda: 0.0,
        drift_enabled=False,
        habitat_enabled=True,
    )
    org = create_organism(config)
    engine = _engine_with_social()
    org.embodiment.attach_habitat_engine(engine)
    saved_state = deepcopy(engine.state)
    org.snapshot_if_due(force=True)
    org.close()

    restored = load_organism(config)
    try:
        with pytest.raises(HabitatAuthorityError, match="reattachment_required"):
            restored.tick_once()
        restored.embodiment.attach_habitat_engine(HabitatEngine(saved_state))
        restored.tick_once()
    finally:
        restored.close()
