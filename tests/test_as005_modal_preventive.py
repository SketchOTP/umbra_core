"""Focused pure AS-005 modal-option and preventive-obligation proofs."""

from __future__ import annotations

from pathlib import Path

from experiments.as005.qualification import as005_config
from umbra_core.arbitration import Candidate
from umbra_core.hypothetical.action_selection import _owner_active, eliminate_by_continuation
from umbra_core.hypothetical.frame import build_planning_evidence_frame
from umbra_core.physiology import BOUNDS


BODY = "body-schema:as005"


def frame_with_route() -> object:
    entity = {
        "entity_id": "entity:resource:1",
        "entity_kind": "resource",
        "estimated_distance": 3.0,
        "distance_support_upper_bound": 3.0,
        "support_body_schema_id": BODY,
        "support_provenance": "test:world:resource",
        "fact_kind": "CURRENT_OBSERVATION",
        "last_tick": 0,
        "confidence": 0.9,
        "verified_recovery_count": 1,
    }
    route = {
        "schema": "VERIFIED_ROUTE_EXPERIENCE_V2",
        "evidence_id": "route:1",
        "opportunity_entity_id": "entity:resource:1",
        "body_schema_id": BODY,
        "route_capability": "APPROACH",
        "terminal_capability": "CHARGE",
        "start_tick": 0,
        "final_tick": 3,
        "start_distance_support_upper_bound": 3.0,
        "start_fact_kind": "CURRENT_OBSERVATION",
        "start_support_provenance": "test:world:resource",
        "verified_movement_execution_count": 1,
        "movement_completion_lags": [1],
        "terminal_completion_lag": 0,
        "terminal_result": True,
        "route_failure_code": None,
        "execution_outcome_refs": ["outcome:1"],
        "route_control_steps": [
            {"capability": "APPROACH", "issue_tick": 0, "completion_tick": 1, "completion_lag": 1, "translational_movement": True, "success": True, "verified_outcome_ref": "outcome:approach"},
            {"capability": "CHARGE", "issue_tick": 3, "completion_tick": 3, "completion_lag": 0, "translational_movement": False, "success": True, "verified_outcome_ref": "outcome:charge"},
        ],
    }
    support = {name: {"body_schema_id": BODY, **{field: {"minimum": 0.0, "maximum": 1.0, "semantics": "VERIFIED_OBSERVED_SUPPORT", "provenance": [f"test:{name}:{field}"]} for field in ("progress", "applied_step", "completion")}} for name in ("APPROACH", "CHARGE", "REST", "INSPECT")}
    return build_planning_evidence_frame(
        organism_tick=0,
        organism_age=0,
        monotonic_time=0.0,
        physiology={"energy": 0.7, "fatigue": 0.2, "integrity": 0.9, "stimulation": 0.55},
        body_state={"actuator_delay": 0},
        body_profile={"profile_id": "profile:as005", "supported_capabilities": ["APPROACH", "CHARGE", "REST", "INSPECT"]},
        self_model_body_schema={"body_schema_id": BODY, "version": 1},
        capability_support=support,
        world_entities=[entity],
        world_object_persistence=True,
        pending_execution={},
        source_versions={"world_model_policy_state": "v1"},
        route_evidence_state={"experiences": [route]},
        world_affordances={},
        world_model_config={"fixed_authored": False, "affordance_learning": True},
    )


def test_may_route_is_a_nonempty_candidate_neutral_o0_option() -> None:
    frame = frame_with_route()
    result = eliminate_by_continuation(frame, [Candidate("IDLE", {}), Candidate("MOVE", {})])
    assert result.root_size == 1
    assert len(result.modal_options) == 1
    assert result.modal_options[0][1] == "MAY"
    assert len(result.classifications) == 2
    assert all(row.status_by_witness[0][1] == "PRESERVED" for row in result.classifications)


def test_modal_o0_is_invariant_to_candidate_order_and_metadata() -> None:
    frame = frame_with_route()
    first = eliminate_by_continuation(frame, [Candidate("MOVE", {"source": "a"}), Candidate("IDLE", {})])
    second = eliminate_by_continuation(frame, [Candidate("IDLE", {"source": "b"}), Candidate("MOVE", {})])
    assert first.modal_options == second.modal_options


def test_preventive_obligation_activates_at_finite_viable_boundary_horizon() -> None:
    assert _owner_active(frame_with_route(), "energy", BOUNDS["energy"]) is False


def test_explicit_as005_configuration_enables_route_learning_without_runtime() -> None:
    config = as005_config(1, Path("/tmp/as005-pure.sqlite"), "R0", Path("/tmp/as005-decision.jsonl"), Path("/tmp/as005-planning.jsonl"))
    assert config.bounded_continuation_enabled is True
    assert config.world_model_config is not None
    assert config.world_model_config.route_demand_learning_enabled is True
