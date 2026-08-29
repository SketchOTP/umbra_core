"""CLOSE-02U verified recovery-landmark continuity contract tests."""

from __future__ import annotations

import math

from umbra_core.world_model import VerifiedMotionDelta, WorldModel


def _observation(kind: str, *, source: str = "sensor", fact_kind: str = "CURRENT_OBSERVATION") -> dict:
    return {
        "kind": kind,
        "relative_direction": 0.0,
        "estimated_distance": 2.0,
        "confidence": 0.9,
        "uncertainty": 0.1,
        "source": source,
        "fact_kind": fact_kind,
        "distance_support_upper_bound": 4.0,
    }


def _outcome(*, success: bool = True, verified: bool = True, effects: dict | None = None) -> dict:
    result = {"success": success, "verified": verified}
    if effects is not None:
        result["effects"] = effects
    return result


def _observe_rest(wm: WorldModel, outcome: dict) -> dict:
    direct = [_observation("rest")]
    wm.ingest_observations(direct, tick=1, now=1.0)
    return wm.observe_outcome(
        tick=2,
        action="REST",
        params={"toward": "rest"},
        verified_outcome=outcome,
        observations=direct,
        action_issued=True,
        now=2.0,
    )


def test_direct_successful_rest_qualifies_verified_recovery_landmark():
    wm = WorldModel.create("close02u", seed=1)
    result = _observe_rest(wm, _outcome(effects={"fatigue": -0.08, "integrity": 0.055}))
    entity = next(iter(wm.entities.values()))
    assert result["verified_recovery_memory_strengthened"] is True
    assert entity.verified_recovery_count == 1
    assert entity.last_verified_success_tick == 2


def test_failed_or_denied_rest_does_not_qualify():
    for outcome in (_outcome(success=False), _outcome(verified=False)):
        wm = WorldModel.create("close02u", seed=2)
        result = _observe_rest(wm, outcome)
        entity = next(iter(wm.entities.values()))
        assert result.get("verified_recovery_memory_strengthened", False) is False
        assert entity.verified_recovery_count == 0


def test_unverified_rest_observation_is_not_indefinitely_persistent():
    wm = WorldModel.create("close02u", seed=3)
    wm.ingest_observations([_observation("rest")], tick=1, now=1.0)
    initial = next(iter(wm.entities.values())).confidence
    wm.ingest_observations([], tick=2, now=2.0)
    entity = next(iter(wm.entities.values()))
    assert entity.fact_kind == "REMEMBERED_ESTIMATE"
    assert entity.confidence < initial


def test_verified_rest_remains_policy_visible_after_disappearance():
    wm = WorldModel.create("close02u", seed=4)
    _observe_rest(wm, _outcome(effects={"fatigue": -0.08}))
    wm.ingest_observations([], tick=3, now=3.0)
    policy = wm.policy_observations(observed_kinds=set())
    assert len(policy) == 1
    assert policy[0]["kind"] == "rest"
    assert policy[0]["fact_kind"] == "REMEMBERED_ESTIMATE"
    assert policy[0]["verified_recovery_count"] == 1
    assert policy[0]["support_semantics"] == "VERIFIED_OBSERVED_SUPPORT"


def test_verified_rest_support_updates_with_verified_body_motion():
    wm = WorldModel.create("close02u", seed=5)
    _observe_rest(wm, _outcome(effects={"fatigue": -0.08}))
    delta = VerifiedMotionDelta(
        displacement=1.0,
        body_relative_dx=1.0,
        body_relative_dy=0.0,
        heading_delta=0.0,
        provenance="test:close02u",
        execution_id="close02u-motion-1",
    )
    assert wm.apply_verified_motion(delta, tick=3) == 1
    entity = next(iter(wm.entities.values()))
    assert entity.fact_kind == "REMEMBERED_ESTIMATE"
    assert entity.distance_support_upper_bound == 5.0


def test_verified_rest_landmark_round_trips_without_hidden_truth():
    wm = WorldModel.create("close02u", seed=6)
    _observe_rest(wm, _outcome(effects={"fatigue": -0.08}))
    wm.ingest_observations([], tick=3, now=3.0)
    restored = WorldModel.from_state(wm.to_state())
    assert restored.accepted_state() == wm.accepted_state()
    assert restored.policy_observations(observed_kinds=set()) == wm.policy_observations(observed_kinds=set())
    assert all("x" not in row and "y" not in row for row in restored.policy_observations(observed_kinds=set()))


def test_unrelated_successful_interaction_does_not_become_rest_landmark():
    wm = WorldModel.create("close02u", seed=7)
    resource = [_observation("resource")]
    wm.ingest_observations(resource, tick=1, now=1.0)
    result = wm.observe_outcome(
        tick=2,
        action="REST",
        params={"toward": "rest"},
        verified_outcome=_outcome(effects={"fatigue": -0.08}),
        observations=resource,
        action_issued=True,
        now=2.0,
    )
    assert result.get("verified_recovery_memory_strengthened", False) is False
    assert next(iter(wm.entities.values())).verified_recovery_count == 0


def test_resource_landmark_existing_behavior_remains_compatible():
    wm = WorldModel.create("close02u", seed=8)
    resource = [_observation("resource")]
    wm.ingest_observations(resource, tick=1, now=1.0)
    result = wm.observe_outcome(
        tick=2,
        action="CHARGE",
        params={"toward": "resource"},
        verified_outcome=_outcome(effects={"energy": 0.14}),
        observations=resource,
        action_issued=True,
        now=2.0,
    )
    assert result["verified_recovery_memory_strengthened"] is True
    wm.ingest_observations([], tick=3, now=3.0)
    entity = next(iter(wm.entities.values()))
    assert entity.verified_recovery_count == 1
    assert entity.confidence > 0.9


def test_failed_rest_with_effects_does_not_qualify_even_with_support():
    wm = WorldModel.create("close02u", seed=9)
    result = _observe_rest(wm, _outcome(success=False, effects={"fatigue": 0.08}))
    assert result.get("verified_recovery_memory_strengthened", False) is False

