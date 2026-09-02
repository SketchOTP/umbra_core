"""Pure R6B-R1 route-control continuity tests.

These tests use only isolated WorldModel/value objects. They do not construct an
Organism, call ``tick_once``, access Habitat, or execute a capability.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from umbra_core.world_model import (
    FactKind,
    VerifiedRouteExperience,
    WorldEntity,
    WorldModel,
    WorldModelConfig,
)


SCHEMA = "body-schema-a"


def entity(entity_id: str = "op-1", kind: str = "resource", *, schema: str | None = SCHEMA) -> WorldEntity:
    return WorldEntity(
        entity_id=entity_id,
        entity_kind=kind,
        estimated_state={"relative_direction": 0.0, "estimated_distance": 3.0},
        last_observed_at=0.0,
        confidence=0.8,
        uncertainty=0.2,
        persistence_probability=0.8,
        evidence_count=1,
        distance_support_upper_bound=3.0,
        support_provenance="sensor:bounded_body_region",
        support_source_kind="CURRENT_OBSERVATION",
        support_body_schema_id=schema,
        fact_kind=FactKind.CURRENT_OBSERVATION.value,
        last_tick=0,
    )


def world(*items: WorldEntity, capacity: int = 128) -> WorldModel:
    wm = WorldModel.create(
        "agent-1",
        config=WorldModelConfig(
            route_demand_learning_enabled=True,
            max_route_experiences=capacity,
        ),
        seed=7,
    )
    wm.entities = {item.entity_id: item for item in items}
    return wm


def bind(wm: WorldModel, capability: str = "APPROACH", kind: str = "resource"):
    return wm.route_issue_binding(
        capability=capability,
        params={"toward": kind},
        body_schema_id=SCHEMA,
    )


def outcome(
    wm: WorldModel,
    *,
    binding,
    capability: str,
    tick: int,
    issue_tick: int,
    success: bool = True,
    reason: str = "ok",
    ref: str | None = None,
    schema: str = SCHEMA,
):
    return wm.observe_outcome(
        tick=tick,
        action=capability,
        params={"toward": binding["opportunity_entity_kind"]} if binding else {},
        verified_outcome={
            "success": success,
            "verified": True,
            "reason": reason,
            "outcome_id": ref or f"outcome-{tick}",
        },
        observations=[],
        action_issued=True,
        now=float(tick),
        issue_tick=issue_tick,
        body_schema_id=schema,
        route_binding=binding,
        provenance_ref=ref or f"outcome_verified:sequence:{tick}",
    )


def test_same_target_orient_preserves_route_and_records_control_step():
    wm = world(entity())
    approach = bind(wm)
    outcome(wm, binding=approach, capability="APPROACH", tick=2, issue_tick=1, ref="approach")
    orient = bind(wm, capability="ORIENT")
    outcome(wm, binding=orient, capability="ORIENT", tick=4, issue_tick=2, ref="orient")
    terminal = bind(wm, capability="CHARGE")
    result = outcome(wm, binding=terminal, capability="CHARGE", tick=5, issue_tick=4, ref="charge")
    record = result["route_learning"]["experience"]
    assert [step["capability"] for step in record["route_control_steps"]] == [
        "APPROACH", "ORIENT", "CHARGE"
    ]
    assert record["verified_movement_execution_count"] == 1
    assert record["route_control_steps"][1]["translational_movement"] is False
    assert record["route_control_steps"][1]["completion_lag"] == 2
    assert record["execution_outcome_refs"] == ["approach", "orient", "charge"]


def test_multiple_approaches_and_orient_round_trip_in_order():
    wm = world(entity())
    for capability, tick, ref in (
        ("APPROACH", 1, "a1"),
        ("ORIENT", 3, "o1"),
        ("APPROACH", 5, "a2"),
    ):
        outcome(wm, binding=bind(wm, capability), capability=capability, tick=tick, issue_tick=tick, ref=ref)
    result = outcome(wm, binding=bind(wm, "CHARGE"), capability="CHARGE", tick=6, issue_tick=5, ref="c")
    record = VerifiedRouteExperience.from_dict(result["route_learning"]["experience"])
    assert [step.capability for step in record.route_control_steps] == ["APPROACH", "ORIENT", "APPROACH", "CHARGE"]
    assert record.verified_movement_execution_count == 2
    assert record.movement_completion_lags == (0, 0)


def test_orient_can_begin_an_exact_bound_route_without_counting_movement():
    wm = world(entity())
    orient = bind(wm, "ORIENT")
    outcome(wm, binding=orient, capability="ORIENT", tick=2, issue_tick=1, ref="orient")
    result = outcome(wm, binding=bind(wm, "CHARGE"), capability="CHARGE", tick=3, issue_tick=2, ref="charge")
    record = result["route_learning"]["experience"]
    assert record["verified_movement_execution_count"] == 0
    assert record["route_control_steps"][0]["capability"] == "ORIENT"


def test_orient_failure_is_verified_route_failure():
    wm = world(entity())
    result = outcome(
        wm,
        binding=bind(wm, "ORIENT"),
        capability="ORIENT",
        tick=2,
        issue_tick=1,
        success=False,
        reason="orientation_slip",
        ref="orient-failure",
    )
    record = result["route_learning"]["experience"]
    assert record["terminal_result"] is False
    assert record["route_failure_code"] == "orientation_slip"
    assert record["route_control_steps"][0]["success"] is False


def test_same_kind_different_entity_switch_discards_episode():
    wm = world(entity("a"), entity("b"))
    # Make the first binding unique, then add the second target.
    wm.entities = {"a": entity("a")}
    outcome(wm, binding=bind(wm), capability="APPROACH", tick=1, issue_tick=1, ref="a")
    wm.entities["b"] = entity("b")
    switched = bind(wm, "ORIENT")
    assert switched is None
    result = outcome(wm, binding=switched, capability="ORIENT", tick=2, issue_tick=2, ref="b")
    assert result["route_learning"]["discarded"] is True
    assert len(wm.route_evidence.experiences) == 0


def test_exact_different_opportunity_switch_does_not_join_route_episodes():
    wm = world(entity("resource-1", "resource"), entity("rest-1", "rest"))
    outcome(
        wm,
        binding=bind(wm, kind="resource"),
        capability="APPROACH",
        tick=1,
        issue_tick=1,
        ref="resource-approach",
    )
    switched = bind(wm, "ORIENT", kind="rest")
    assert switched is not None
    outcome(wm, binding=switched, capability="ORIENT", tick=2, issue_tick=2, ref="rest-orient")
    assert len(wm.route_evidence.experiences) == 0
    result = outcome(
        wm,
        binding=bind(wm, "REST", kind="rest"),
        capability="REST",
        tick=3,
        issue_tick=3,
        ref="rest-terminal",
    )
    steps = result["route_learning"]["experience"]["route_control_steps"]
    assert [step["capability"] for step in steps] == ["ORIENT", "REST"]


@pytest.mark.parametrize(
    ("capability", "params"),
    [
        ("ORIENT", {"heading": 0.0}),
        ("IDLE", {}),
        ("RETREAT", {"from": "hazard"}),
        ("MOVE", {"step": 1.0}),
    ],
)
def test_unbound_route_interruption_discards_active_episode(capability, params):
    wm = world(entity())
    outcome(wm, binding=bind(wm), capability="APPROACH", tick=1, issue_tick=1, ref="move")
    result = wm.observe_outcome(
        tick=2,
        action=capability,
        params=params,
        verified_outcome={"success": True, "verified": True, "reason": "ok"},
        observations=[],
        action_issued=True,
        now=2.0,
        issue_tick=2,
        body_schema_id=SCHEMA,
        route_binding=None,
        provenance_ref=f"interrupt-{capability}",
    )
    assert result["route_learning"]["discarded"] is True
    assert len(wm.route_evidence.experiences) == 0


def test_ambiguous_same_kind_orient_fails_closed():
    wm = world(entity("a"), entity("b"))
    assert bind(wm, "ORIENT") is None


def test_body_schema_change_invalidates_active_route():
    wm = world(entity())
    first = bind(wm)
    outcome(wm, binding=first, capability="APPROACH", tick=1, issue_tick=1, ref="move")
    changed = dict(first)
    changed["body_schema_id"] = "body-schema-b"
    result = wm.route_evidence.record_verified_outcome(
        binding=changed,
        capability="ORIENT",
        success=True,
        reason="ok",
        verified=True,
        tick=2,
        issue_tick=2,
        body_schema_id="body-schema-b",
        outcome_ref="orient",
    )
    assert result["discarded"] is True
    assert len(wm.route_evidence.experiences) == 0


def test_v2_persistence_retains_control_order_and_v1_remains_uninterpreted():
    wm = world(entity())
    outcome(wm, binding=bind(wm, "ORIENT"), capability="ORIENT", tick=1, issue_tick=1, ref="orient")
    result = outcome(wm, binding=bind(wm, "CHARGE"), capability="CHARGE", tick=2, issue_tick=2, ref="charge")
    record = VerifiedRouteExperience.from_dict(result["route_learning"]["experience"])
    restored = WorldModel.from_state(wm.to_state(), config=wm.config)
    restored_record = next(iter(restored.route_evidence.experiences))
    assert record.schema == "VERIFIED_ROUTE_EXPERIENCE_V2"
    assert [step.capability for step in restored_record.route_control_steps] == ["ORIENT", "CHARGE"]

    legacy = record.to_dict()
    legacy.pop("schema")
    legacy.pop("route_control_steps")
    migrated = VerifiedRouteExperience.from_dict(legacy)
    assert migrated.schema == "VERIFIED_ROUTE_EXPERIENCE_V1"
    assert migrated.route_control_steps == ()


def test_route_control_step_provenance_and_timing_are_exact():
    wm = world(entity())
    outcome(wm, binding=bind(wm, "ORIENT"), capability="ORIENT", tick=5, issue_tick=2, ref="orient-proof")
    result = outcome(wm, binding=bind(wm, "CHARGE"), capability="CHARGE", tick=7, issue_tick=5, ref="charge-proof")
    steps = result["route_learning"]["experience"]["route_control_steps"]
    assert steps[0]["issue_tick"] == 2
    assert steps[0]["completion_tick"] == 5
    assert steps[0]["completion_lag"] == 3
    assert steps[0]["verified_outcome_ref"] == "orient-proof"
    assert steps[1]["completion_lag"] == 2


def test_route_learning_remains_default_off():
    wm = WorldModel.create("agent-1", config=WorldModelConfig(), seed=7)
    wm.entities = {"op-1": entity()}
    assert wm.route_issue_binding(capability="ORIENT", params={"toward": "resource"}, body_schema_id=SCHEMA) is None


def test_route_evidence_capacity_is_unchanged():
    wm = world(entity(), capacity=2)
    for index in range(3):
        outcome(wm, binding=bind(wm, "CHARGE"), capability="CHARGE", tick=index, issue_tick=index, ref=f"charge-{index}")
    assert len(wm.route_evidence.experiences) == 2
    assert wm.counts_bounded()


def test_route_control_record_is_immutable():
    wm = world(entity())
    result = outcome(wm, binding=bind(wm, "ORIENT"), capability="ORIENT", tick=1, issue_tick=1, ref="orient")
    result = outcome(wm, binding=bind(wm, "CHARGE"), capability="CHARGE", tick=2, issue_tick=2, ref="charge")
    step = VerifiedRouteExperience.from_dict(result["route_learning"]["experience"])
    with pytest.raises(Exception):
        replace(step.route_control_steps[0], completion_lag=99)
