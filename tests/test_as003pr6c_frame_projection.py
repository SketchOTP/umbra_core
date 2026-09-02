"""Pure R6C route/affordance projections.

These tests use immutable dictionaries and value objects only. They do not
construct an Organism, call ``tick_once``, access Habitat, or execute a plan.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from umbra_core.embodiment import Body
from umbra_core.hypothetical.frame import (
    PLANNING_FRAME_SCHEMA,
    PlanningModality,
    build_planning_evidence_frame,
)
from umbra_core.hypothetical.modal import (
    candidate_contract,
    modal_continuation_profile,
    modal_services_from_frame,
)
from umbra_core.hypothetical.shadow import capture_runtime_frame
from umbra_core.self_model.engine import SelfModel, SupportSemantics
from umbra_core.physiology import Physiology
from umbra_core.world_model import AffordanceBelief, VerifiedRouteExperience, WorldEntity, WorldModel


SCHEMA = "body-schema-a"


def _entity(identity: str = "op-1", kind: str = "resource", schema: str = SCHEMA) -> dict:
    return {
        "entity_id": identity,
        "entity_kind": kind,
        "last_tick": 7,
        "fact_kind": "CURRENT_OBSERVATION",
        "confidence": 0.8,
        "uncertainty": 0.2,
        "persistence_probability": 0.7,
        "distance_support_upper_bound": 10.0,
        "support_body_schema_id": schema,
        "support_provenance": "sensor:bounded_body_region",
        "verified_recovery_count": 0,
    }


def _support() -> dict:
    return {
        "minimum": 0.5,
        "maximum": 1.0,
        "semantics": SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value,
        "provenance": ["verified:test"],
    }


def _successful_route(schema: str = SCHEMA) -> dict:
    steps = []
    for tick, capability, success, ref in (
        (2, "ORIENT", True, "o1"),
        (3, "CHARGE", False, "c1"),
        (4, "ORIENT", True, "o2"),
        (5, "CHARGE", False, "c2"),
        (6, "APPROACH", True, "a1"),
        (7, "ORIENT", True, "o3"),
        (8, "CHARGE", True, "c3"),
    ):
        steps.append({
            "capability": capability,
            "issue_tick": tick,
            "completion_tick": tick,
            "completion_lag": 0,
            "translational_movement": capability == "APPROACH",
            "success": success,
            "verified_outcome_ref": ref,
        })
    return {
        "schema": "VERIFIED_ROUTE_EXPERIENCE_V2",
        "evidence_id": "route:success-1",
        "opportunity_entity_id": "op-1",
        "opportunity_entity_kind": "resource",
        "body_schema_id": schema,
        "route_capability": "APPROACH",
        "terminal_capability": "CHARGE",
        "start_tick": 2,
        "final_tick": 8,
        "start_distance_support_upper_bound": 10.0,
        "start_fact_kind": "CURRENT_OBSERVATION",
        "start_support_provenance": "sensor:bounded_body_region",
        "verified_movement_execution_count": 1,
        "movement_completion_lags": [0],
        "terminal_completion_lag": 0,
        "terminal_result": True,
        "route_failure_code": None,
        "execution_outcome_refs": ["o1", "c1", "o2", "c2", "a1", "o3", "c3"],
        "evidence_semantics": "VERIFIED_OBSERVED_SUPPORT",
        "route_control_steps": steps,
    }


def _failure_route() -> dict:
    route = _successful_route()
    route["evidence_id"] = "route:failure-1"
    route["terminal_result"] = False
    route["route_failure_code"] = "movement_slip"
    route["final_tick"] = 6
    route["route_control_steps"] = route["route_control_steps"][:5]
    route["execution_outcome_refs"] = route["execution_outcome_refs"][:5]
    route["verified_movement_execution_count"] = 0
    route["movement_completion_lags"] = []
    return route


def _frame(*, route_records=(), affordances=None, schema=SCHEMA, entities=None):
    supports = {
        capability: {
            "body_schema_id": schema,
            "progress": _support(),
            "applied_step": _support(),
            "completion": {**_support(), "minimum": 0.0},
        }
        for capability in ("MOVE", "APPROACH", "RETREAT", "CHARGE", "REST", "INSPECT")
    }
    return build_planning_evidence_frame(
        organism_tick=7,
        organism_age=7,
        monotonic_time=3.5,
        physiology={"energy": 0.7, "fatigue": 0.2, "integrity": 0.9, "stimulation": 0.5},
        body_state={"actuator_delay": 0.0},
        body_profile={
            "profile_id": "TEST_BODY",
            "schema_version": "v1",
            "profile_definition_hash": "profile-hash",
            "supported_capabilities": ("MOVE", "APPROACH", "RETREAT", "CHARGE", "REST", "INSPECT"),
            "body_schema_identity": schema,
            "body_schema_version": 1,
        },
        self_model_body_schema={"body_schema_id": schema, "version": 1},
        capability_support=supports,
        world_entities=list(entities if entities is not None else [_entity(schema=schema)]),
        world_object_persistence=True,
        pending_execution={"pending_action": {}, "delayed_proposal": {}, "pending_actuation": {}, "delay_remaining": 0},
        source_versions={"world": "w1", "self": "s1", "body": "b1"},
        route_evidence_state={"schema": "VERIFIED_ROUTE_EXPERIENCE_V2", "experiences": list(route_records)},
        world_affordances=affordances or {},
        world_model_config={"fixed_authored": False, "affordance_learning": True},
    )


def test_v2_route_is_exact_join_and_may_only_witness():
    frame = _frame(route_records=(_successful_route(),))
    row = frame.route_experience_support.to_plain()["op-1"]
    assert frame.schema == PLANNING_FRAME_SCHEMA
    assert row["modality"] == "MAY"
    witness = row["value"]["witnesses"][0]
    assert witness["route_evidence_id"] == "route:success-1"
    assert [step["capability"] for step in witness["ordered_control_steps"]] == [
        "ORIENT", "CHARGE", "ORIENT", "CHARGE", "APPROACH", "ORIENT", "CHARGE"
    ]
    assert witness["observed_episode_ticks"] == 7
    assert witness["verified_movement_execution_count"] == 1
    assert witness["route_control_execution_count"] == 7
    assert row["value"]["v1_incomplete_count"] == 0


def test_route_projection_preserves_failures_without_probability_or_impossibility():
    frame = _frame(route_records=(_failure_route(),))
    row = frame.route_experience_support.to_plain()["op-1"]
    assert row["modality"] == "UNKNOWN"
    assert row["value"]["failures"][0]["route_failure_code"] == "movement_slip"
    assert row["value"]["witnesses"] == []


def test_mixed_route_history_is_may_plus_separate_failure():
    frame = _frame(route_records=(_failure_route(), _successful_route()))
    row = frame.route_experience_support.to_plain()["op-1"]
    assert row["modality"] == "MAY"
    assert len(row["value"]["witnesses"]) == 1
    assert len(row["value"]["failures"]) == 1


def test_v1_success_is_not_upgraded_to_v2():
    route = _successful_route()
    route["schema"] = "VERIFIED_ROUTE_EXPERIENCE_V1"
    route.pop("route_control_steps")
    frame = _frame(route_records=(route,))
    row = frame.route_experience_support.to_plain()["op-1"]
    assert row["modality"] == "UNKNOWN"
    assert row["value"]["witnesses"] == []
    assert row["value"]["v1_incomplete_count"] == 1


def test_route_join_requires_exact_opportunity_and_body_and_terminal():
    wrong_target = dict(_successful_route(), opportunity_entity_id="other")
    wrong_body = dict(_successful_route(), body_schema_id="other-body")
    wrong_terminal = dict(_successful_route(), terminal_capability="REST")
    frame = _frame(route_records=(wrong_target, wrong_body, wrong_terminal))
    assert frame.route_experience_support.to_plain()["op-1"]["value"]["witnesses"] == []


def test_inspect_requires_instance_and_learned_active_affordance():
    affordance = {
        "aff-inspect": {
            "affordance_id": "aff-inspect",
            "entity_kind": "inspect",
            "action": "inspect",
            "support_count": 3,
            "contradiction_count": 0,
            "confidence": 0.4,
            "status": "ACTIVE",
        }
    }
    frame = _frame(affordances=affordance, entities=[_entity("inspect-1", "inspect")])
    row = frame.affordance_support.to_plain()["aff-inspect"]
    assert row["modality"] == "MAY"
    assert row["value"]["opportunity_entity_ids"] == ["inspect-1"]


def test_affordance_negative_cases_remain_unknown():
    cases = (
        ("CANDIDATE", False),
        ("WEAKENED", False),
        ("SUPERSEDED", False),
    )
    for status, _ in cases:
        frame = _frame(
            affordances={"a": {"entity_kind": "inspect", "action": "inspect", "status": status}},
            entities=[_entity("inspect-1", "inspect")],
        )
        assert frame.affordance_support.to_plain()["a"]["modality"] == "UNKNOWN"
    no_instance = _frame(
        affordances={"a": {"entity_kind": "inspect", "action": "inspect", "status": "ACTIVE"}},
        entities=[],
    )
    assert no_instance.affordance_support.to_plain()["a"]["modality"] == "UNKNOWN"


def test_authored_affordance_is_not_learned_planning_evidence():
    frame = build_planning_evidence_frame(
        organism_tick=7, organism_age=7, monotonic_time=3.5,
        physiology={"energy": 0.7, "fatigue": 0.2, "integrity": 0.9, "stimulation": 0.5},
        body_state={"actuator_delay": 0.0},
        body_profile={"profile_id": "p", "supported_capabilities": ("INSPECT",), "body_schema_identity": SCHEMA},
        self_model_body_schema={"body_schema_id": SCHEMA}, capability_support={},
        world_entities=[_entity("inspect-1", "inspect")], world_object_persistence=True,
        pending_execution={}, source_versions={},
        world_affordances={"a": {"entity_kind": "inspect", "action": "inspect", "status": "ACTIVE"}},
        world_model_config={"fixed_authored": True},
    )
    assert frame.affordance_support.to_plain()["a"]["modality"] == "UNKNOWN"
    assert frame.affordance_support.to_plain()["a"]["value"]["source"] == "authored"


def test_projection_is_deterministic_under_source_insertion_order():
    route = _successful_route()
    left = _frame(route_records=(route,), affordances={"b": {"entity_kind": "resource", "action": "charge", "status": "ACTIVE"}, "a": {"entity_kind": "inspect", "action": "inspect", "status": "ACTIVE"}})
    right = _frame(route_records=(dict(reversed(tuple(route.items()))),), affordances={"a": {"status": "ACTIVE", "action": "inspect", "entity_kind": "inspect"}, "b": {"status": "ACTIVE", "action": "charge", "entity_kind": "resource"}})
    assert left.to_canonical() == right.to_canonical()


def test_route_evidence_does_not_change_existing_modal_profile():
    old = _frame()
    new = _frame(route_records=(_successful_route(),))
    old_profile = modal_continuation_profile(old, candidate_contract("MOVE"), modal_services_from_frame(old))
    new_profile = modal_continuation_profile(new, candidate_contract("MOVE"), modal_services_from_frame(new))
    assert old_profile == new_profile


def test_projection_is_deeply_immutable_and_may_never_be_must():
    frame = _frame(route_records=(_successful_route(),))
    assert frame.route_experience_support.to_plain()["op-1"]["modality"] == PlanningModality.MAY.value
    try:
        frame.route_experience_support["op-1"] = {}
    except TypeError:
        pass
    else:
        raise AssertionError("route projection mutation succeeded")


def test_shadow_capture_copies_route_and_affordance_sources_and_fingerprints_them():
    world = WorldModel.create("agent:fixture", seed=7)
    self_model = SelfModel.create("agent:fixture", seed=7)
    schema = self_model.active.body_schema_id
    world.entities["op-1"] = WorldEntity(
        entity_id="op-1", entity_kind="resource", estimated_state={"estimated_distance": 2.0},
        last_observed_at=0.0, confidence=0.8, uncertainty=0.2, persistence_probability=0.8,
        evidence_count=1, distance_support_upper_bound=2.0,
        support_body_schema_id=schema, fact_kind="CURRENT_OBSERVATION", last_tick=0,
    )
    world.route_evidence.experiences.append(VerifiedRouteExperience.from_dict(_successful_route(schema)))
    world.affordances["aff-inspect"] = AffordanceBelief(
        "aff-inspect", "inspect", "inspect", 3, 0, 0.5, "ACTIVE"
    )
    owner = SimpleNamespace(
        embodiment_adapter=None,
        self_model=self_model,
        world_model=world,
        embodiment=SimpleNamespace(body=Body(), _pending_actuation=None, _delay_remaining=0),
        phys=Physiology(),
        _pending_action=None,
        _delayed_proposal=None,
        tick=0,
        _tick_organism_age=0,
        monotonic_time=0.0,
    )
    frame = capture_runtime_frame(owner)
    assert "world_model_route_evidence" in frame.source_versions
    assert "world_model_affordances" in frame.source_versions
    assert frame.route_experience_support.to_plain()["op-1"]["modality"] == "MAY"
    assert frame.affordance_support.to_plain()["aff-inspect"]["modality"] == "UNKNOWN"
