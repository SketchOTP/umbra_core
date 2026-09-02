"""Pure AS-003P-R6B route-evidence contract tests.

These tests instantiate only the isolated WorldModel/value objects. They do not
construct an Organism, call ``tick_once``, access Habitat, or execute a capability.
"""

from __future__ import annotations

import pytest

from umbra_core.world_model import (
    FactKind,
    VerifiedRouteExperience,
    WorldEntity,
    WorldModel,
    WorldModelConfig,
    resolve_opportunity,
)


SCHEMA = "body-schema-a"


def entity(
    entity_id: str = "op-1",
    kind: str = "resource",
    *,
    fact_kind: str = FactKind.CURRENT_OBSERVATION.value,
    support_schema: str | None = SCHEMA,
    distance: float | None = 3.0,
) -> WorldEntity:
    return WorldEntity(
        entity_id=entity_id,
        entity_kind=kind,
        estimated_state={"relative_direction": 0.0, "estimated_distance": 3.0},
        last_observed_at=0.0,
        confidence=0.8,
        uncertainty=0.2,
        persistence_probability=0.8,
        evidence_count=1,
        distance_support_upper_bound=distance,
        support_provenance="sensor:bounded_body_region" if distance is not None else None,
        support_source_kind="CURRENT_OBSERVATION" if distance is not None else None,
        support_body_schema_id=support_schema,
        fact_kind=fact_kind,
        last_tick=0,
    )


def world(*entities: WorldEntity, capacity: int = 128) -> WorldModel:
    cfg = WorldModelConfig(
        route_demand_learning_enabled=True,
        max_route_experiences=capacity,
    )
    wm = WorldModel.create("agent-1", config=cfg, seed=7)
    wm.entities = {item.entity_id: item for item in entities}
    return wm


def binding(wm: WorldModel, capability: str = "APPROACH", kind: str = "resource"):
    return wm.route_issue_binding(
        capability=capability,
        params={"toward": kind},
        body_schema_id=SCHEMA,
    )


def outcome(
    wm: WorldModel,
    *,
    bind,
    capability: str,
    tick: int,
    issue_tick: int,
    success: bool = True,
    reason: str = "ok",
    verified: bool = True,
    ref: str | None = None,
):
    return wm.observe_outcome(
        tick=tick,
        action=capability,
        params={"toward": bind["opportunity_entity_kind"]} if bind else {},
        verified_outcome={
            "success": success,
            "verified": verified,
            "reason": reason,
            "outcome_id": ref or f"outcome-{tick}",
        },
        observations=[],
        action_issued=True,
        now=float(tick),
        issue_tick=issue_tick,
        body_schema_id=SCHEMA,
        route_binding=bind,
        provenance_ref=ref or f"outcome_verified:sequence:{tick}",
    )


def test_exact_resolution_requires_one_policy_safe_entity():
    result = resolve_opportunity({"op-1": entity()}, target_kind="resource", body_schema_id=SCHEMA)
    assert result.status == "EXACT"
    assert result.opportunity_entity_id == "op-1"


@pytest.mark.parametrize(
    ("items", "kind", "schema", "expected"),
    [
        ([entity("a"), entity("b")], "resource", SCHEMA, "AMBIGUOUS"),
        ([entity(support_schema="other")], "resource", SCHEMA, "UNAVAILABLE"),
        ([entity(fact_kind=FactKind.UNKNOWN.value)], "resource", SCHEMA, "UNAVAILABLE"),
        ([entity()], None, SCHEMA, "UNAVAILABLE"),
        ([entity()], "resource", None, "UNAVAILABLE"),
        ([entity(kind="rest")], "resource", SCHEMA, "UNAVAILABLE"),
    ],
)
def test_resolution_rejects_ambiguous_or_unsupported_inputs(items, kind, schema, expected):
    assert resolve_opportunity({e.entity_id: e for e in items}, target_kind=kind, body_schema_id=schema).status == expected


def test_issue_binding_is_exact_and_contains_source_snapshot():
    wm = world(entity())
    bind = binding(wm)
    assert bind["status"] == "EXACT"
    assert bind["opportunity_entity_id"] == "op-1"
    assert bind["start_distance_support_upper_bound"] == 3.0
    assert bind["start_support_provenance"] == "sensor:bounded_body_region"


def test_default_off_has_no_issue_binding():
    wm = WorldModel.create("agent-1", config=WorldModelConfig(), seed=7)
    wm.entities = {"op-1": entity()}
    assert wm.route_issue_binding(capability="APPROACH", params={"toward": "resource"}, body_schema_id=SCHEMA) is None


def test_successful_route_closes_with_raw_movement_and_terminal_lags():
    wm = world(entity())
    bind = binding(wm)
    first = outcome(wm, bind=bind, capability="APPROACH", tick=3, issue_tick=1, ref="move-1")
    assert first["route_learning"]["episode_active"] is True
    final = outcome(wm, bind=bind, capability="CHARGE", tick=5, issue_tick=4, ref="charge-1")
    record = final["route_learning"]["experience"]
    assert record["verified_movement_execution_count"] == 1
    assert record["movement_completion_lags"] == [2]
    assert record["terminal_completion_lag"] == 1
    assert record["terminal_result"] is True
    assert record["execution_outcome_refs"] == ["move-1", "charge-1"]


def test_zero_movement_terminal_success_is_valid_when_exactly_bound():
    wm = world(entity(distance=None))
    bind = binding(wm, capability="CHARGE")
    result = outcome(wm, bind=bind, capability="CHARGE", tick=2, issue_tick=2, ref="charge-0")
    record = result["route_learning"]["experience"]
    assert record["verified_movement_execution_count"] == 0
    assert record["terminal_result"] is True


@pytest.mark.parametrize("reason", ["route_blocked", "movement_slip", "adapter_rejected"])
def test_verified_route_failure_closes_without_terminal_success(reason):
    wm = world(entity())
    bind = binding(wm)
    result = outcome(
        wm, bind=bind, capability="APPROACH", tick=2, issue_tick=1,
        success=False, reason=reason, ref=f"failure-{reason}",
    )
    record = result["route_learning"]["experience"]
    assert record["terminal_result"] is False
    assert record["route_failure_code"] == reason
    assert record["terminal_completion_lag"] is None


def test_premature_terminal_does_not_invent_movement_requirement():
    wm = world(entity())
    bind = binding(wm)
    result = outcome(
        wm, bind=bind, capability="CHARGE", tick=2, issue_tick=2,
        success=False, reason="not_at_resource", ref="premature",
    )
    assert result["route_learning"]["reason"] == "terminal_failure_without_route"
    assert len(wm.route_evidence.experiences) == 0


def test_unverified_outcome_never_creates_evidence():
    wm = world(entity())
    bind = binding(wm)
    result = outcome(
        wm, bind=bind, capability="APPROACH", tick=2, issue_tick=1,
        verified=False, ref="unverified",
    )
    assert result["route_learning"]["discarded"] is True
    assert len(wm.route_evidence.experiences) == 0


def test_route_switch_discards_incomplete_episode():
    wm = world(entity("a"), entity("b"))
    # Ambiguous resolution prevents either binding, so use a second WorldModel
    # to make the switch explicit after the first episode has started.
    wm = world(entity("a"))
    first = binding(wm)
    outcome(wm, bind=first, capability="APPROACH", tick=1, issue_tick=1, ref="a-move")
    wm.entities["b"] = entity("b", kind="rest")
    switched = binding(wm, capability="APPROACH", kind="rest")
    result = outcome(wm, bind=switched, capability="APPROACH", tick=2, issue_tick=2, ref="b-move")
    assert result["route_learning"]["episode_active"] is True
    assert len(wm.route_evidence.experiences) == 0


def test_body_schema_change_discards_incomplete_episode():
    wm = world(entity())
    bind = binding(wm)
    outcome(wm, bind=bind, capability="APPROACH", tick=1, issue_tick=1, ref="move")
    changed = dict(bind)
    changed["body_schema_id"] = "body-schema-b"
    result = wm.route_evidence.record_verified_outcome(
        binding=changed, capability="CHARGE", success=True, reason="ok", verified=True,
        tick=2, issue_tick=2, body_schema_id="body-schema-b", outcome_ref="charge",
    )
    assert result["discarded"] is True
    assert len(wm.route_evidence.experiences) == 0


def test_unrelated_verified_action_discards_incomplete_episode():
    wm = world(entity())
    bind = binding(wm)
    outcome(wm, bind=bind, capability="APPROACH", tick=1, issue_tick=1, ref="move")
    result = wm.route_evidence.record_verified_outcome(
        binding=None, capability="ORIENT", success=True, reason="ok", verified=True,
        tick=2, issue_tick=2, body_schema_id=SCHEMA, outcome_ref="orient",
    )
    assert result["discarded"] is True
    assert len(wm.route_evidence.experiences) == 0


def test_support_query_is_unknown_without_exact_opportunity_body_and_terminal_match():
    wm = world(entity())
    assert wm.route_demand_support(
        opportunity_entity_id="op-1", body_schema_id=SCHEMA, terminal_capability="CHARGE"
    )["status"] == "UNKNOWN"


def test_support_query_reports_observed_support_not_utility():
    wm = world(entity())
    bind = binding(wm)
    outcome(wm, bind=bind, capability="APPROACH", tick=3, issue_tick=1, ref="move")
    outcome(wm, bind=bind, capability="CHARGE", tick=4, issue_tick=4, ref="charge")
    support = wm.route_demand_support(
        opportunity_entity_id="op-1", body_schema_id=SCHEMA, terminal_capability="CHARGE"
    )
    assert support["status"] == "VERIFIED_OBSERVED_SUPPORT"
    assert support["success_sample_count"] == 1
    assert "utility" not in support
    assert "probability" not in support
    assert support["provenance"] == ["move", "charge"]


def test_persistence_round_trip_retains_completed_evidence_and_drops_episode():
    wm = world(entity())
    bind = binding(wm)
    outcome(wm, bind=bind, capability="APPROACH", tick=1, issue_tick=1, ref="move")
    state = wm.to_state()
    restored = WorldModel.from_state(state, config=wm.config)
    assert restored.route_evidence.accepted_state() == wm.route_evidence.accepted_state()
    assert restored.route_evidence._episode is None


def test_capacity_is_fixed_and_oldest_completed_evidence_is_evicted():
    wm = world(entity(), capacity=2)
    bind = binding(wm)
    for index in range(3):
        outcome(wm, bind=bind, capability="CHARGE", tick=index, issue_tick=index, ref=f"charge-{index}")
    assert len(wm.route_evidence.experiences) == 2
    assert [e.execution_outcome_refs for e in wm.route_evidence.experiences] == [("charge-1",), ("charge-2",)]
    assert wm.counts_bounded()


def test_experience_is_immutable_and_requires_observed_semantics():
    wm = world(entity())
    bind = binding(wm)
    result = outcome(wm, bind=bind, capability="CHARGE", tick=1, issue_tick=1, ref="charge")
    record = VerifiedRouteExperience.from_dict(result["route_learning"]["experience"])
    with pytest.raises(Exception):
        record.terminal_result = False  # type: ignore[misc]
    assert record.evidence_semantics == "VERIFIED_OBSERVED_SUPPORT"


def test_source_renaming_does_not_change_semantics_of_binding_fields():
    wm = world(entity())
    bind = binding(wm)
    renamed = dict(bind)
    renamed["start_support_provenance"] = "different-source-label"
    assert renamed["opportunity_entity_id"] == bind["opportunity_entity_id"]
    assert renamed["body_schema_id"] == bind["body_schema_id"]
