from __future__ import annotations

from dataclasses import replace
import json

from umbra_core.hypothetical.core import EvidenceEnvelope
from umbra_core.hypothetical.core import FrozenMap, TransitionStatus
from umbra_core.hypothetical.frame import (
    ModalFact,
    PlanningModality,
    build_planning_evidence_frame,
    modality_from_support_semantics,
    opportunity_fact_from_world_entity,
)
from umbra_core.hypothetical.modal import (
    ContinuationClass,
    ModalService,
    candidate_contract,
    modal_continuation_profile,
    modal_services_from_frame,
    physical_frontier_bound,
    profiles_for_candidate_views,
)
from umbra_core.self_model.engine import SupportSemantics


CAPS = ("MOVE", "APPROACH", "RETREAT", "CHARGE", "REST", "INSPECT")


def support(semantics=SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value, lo=0.5, hi=1.0):
    return {
        "minimum": lo,
        "maximum": hi,
        "semantics": semantics,
        "provenance": ["verified:test"],
    }


def entity(*, fact_kind="CURRENT_OBSERVATION", confidence=0.8, schema="body:1", tick=7, kind="resource", identity="resource:1"):
    return {
        "entity_id": identity,
        "entity_kind": kind,
        "last_tick": tick,
        "fact_kind": fact_kind,
        "confidence": confidence,
        "uncertainty": 0.2,
        "persistence_probability": 0.7,
        "distance_support_upper_bound": 2.0,
        "support_body_schema_id": schema,
        "support_provenance": "sensor:bounded_body_region",
        "verified_recovery_count": 0,
    }


def make_frame(*, entities=None, progress_semantics=SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value, pending=None, schema="body:1"):
    supports = {
        cap: {
            "body_schema_id": schema,
            "progress": support(progress_semantics),
            "applied_step": support(progress_semantics),
            "completion": support(progress_semantics, 0.0, 1.0),
        }
        for cap in CAPS
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
            "supported_capabilities": CAPS,
            "body_schema_identity": schema,
            "body_schema_version": 1,
        },
        self_model_body_schema={"body_schema_id": schema, "version": 1},
        capability_support=supports,
        world_entities=list(entities if entities is not None else [entity(schema=schema)]),
        world_object_persistence=True,
        pending_execution=pending or {"pending_action": {}, "delayed_proposal": {}, "pending_actuation": {}, "delay_remaining": 0},
        source_versions={"world": "w1", "self": "s1", "body": "b1"},
    )


def manual_service(frame, modality, *, allowed=None, identity="service:charge"):
    contract = candidate_contract("CHARGE", 0)
    return ModalService(identity, "CHARGE", ("energy",), "resource:1", (modality,), contract, allowed)


def test_frame_deep_immutability():
    frame = make_frame()
    try:
        frame.physiology_root["energy"] = 0.1
    except TypeError:
        return
    raise AssertionError("frame mutation succeeded")


def test_same_semantic_frame_same_identity():
    assert make_frame().material_fingerprint == make_frame().material_fingerprint


def test_stale_future_tick_rejected():
    try:
        make_frame(entities=[entity(tick=8)])
    except ValueError as exc:
        assert "future world entity" in str(exc)
        return
    raise AssertionError("stale/future join accepted")


def test_root_physiology_exact():
    assert make_frame().physiology_root.to_plain()["energy"] == 0.7


def test_body_profile_capability_exists_as_must():
    row = make_frame().constitutional_capabilities.to_plain()["CHARGE"]
    assert row["modality"] == "MUST"


def test_body_schema_mismatch_makes_opportunity_unknown():
    row = make_frame(entities=[entity(schema="wrong")]).opportunities.to_plain()["resource:1"]
    assert row["current"]["modality"] == "UNKNOWN" and row["future"]["modality"] == "UNKNOWN"


def test_categorical_capability_performance_is_must():
    row = make_frame().capability_support.to_plain()["APPROACH"]["progress"]
    assert row["modality"] == "MUST"


def test_probabilistic_capability_performance_is_may():
    row = make_frame(progress_semantics="PROBABILISTIC_SUPPORT").capability_support.to_plain()["APPROACH"]["progress"]
    assert row["modality"] == "MAY"


def test_current_opportunity_is_must_now_only():
    row = make_frame().opportunities.to_plain()["resource:1"]
    assert row["current"]["modality"] == "MUST" and row["current"]["temporal_scope"] == "root-current"


def test_current_observation_future_is_not_must():
    assert make_frame().opportunities.to_plain()["resource:1"]["future"]["modality"] == "MAY"


def test_stale_current_observation_is_not_root_must():
    row = make_frame(entities=[entity(tick=6)]).opportunities.to_plain()["resource:1"]
    assert row["current"]["modality"] == "UNKNOWN"


def test_lawful_retention_is_may():
    fact = opportunity_fact_from_world_entity(entity(), root_tick=7, body_schema_identity="body:1", object_persistence=True)
    assert fact.modality is PlanningModality.MAY and fact.valid_through_ticks > 0


def test_no_invented_may_threshold_when_persistence_disabled():
    fact = opportunity_fact_from_world_entity(entity(), root_tick=7, body_schema_identity="body:1", object_persistence=False)
    assert fact.modality is PlanningModality.UNKNOWN


def test_no_habitat_world_truth_in_frame():
    encoded = json.dumps(make_frame().to_canonical(), sort_keys=True)
    assert "HabitatEngine" not in encoded and "state.objects" not in encoded


def test_must_not_created_from_may():
    assert modality_from_support_semantics("PROBABILISTIC_SUPPORT") is PlanningModality.MAY


def test_may_can_weaken_to_unknown():
    known = opportunity_fact_from_world_entity(entity(confidence=0.8), root_tick=7, body_schema_identity="body:1", object_persistence=True)
    weak = opportunity_fact_from_world_entity(entity(confidence=0.01), root_tick=7, body_schema_identity="body:1", object_persistence=True)
    assert known.modality is PlanningModality.MAY and weak.modality is PlanningModality.UNKNOWN


def test_exact_unsupported_remains_unsupported():
    assert modality_from_support_semantics("NOT_APPLICABLE") is PlanningModality.UNSUPPORTED


def test_pending_action_constrains_fresh_proof():
    frame = make_frame(pending={"pending_action": {"capability": "MOVE"}, "delayed_proposal": {}, "pending_actuation": {}, "delay_remaining": 0})
    assert modal_continuation_profile(frame, candidate_contract("MOVE"), ()).classification is ContinuationClass.UNKNOWN


def test_old_world_plan_absent_from_authority_fields():
    assert "pending_world_plan" not in make_frame().pending_execution.to_plain()


def test_strong_must_all_branch_proof():
    frame = make_frame()
    result = modal_continuation_profile(frame, candidate_contract("MOVE"), (manual_service(frame, PlanningModality.MUST),))
    assert result.classification is ContinuationClass.STRONG_MUST


def test_strong_may_all_branch_proof():
    frame = make_frame()
    result = modal_continuation_profile(frame, candidate_contract("MOVE"), (manual_service(frame, PlanningModality.MAY),))
    assert result.classification is ContinuationClass.STRONG_MAY


def test_weak_may_partial_branch_proof():
    frame = make_frame()
    result = modal_continuation_profile(frame, candidate_contract("MOVE"), (manual_service(frame, PlanningModality.MAY, allowed=(0,)),))
    assert result.classification is ContinuationClass.WEAK_MAY


def test_no_continuation_proof():
    assert modal_continuation_profile(make_frame(), candidate_contract("MOVE"), ()).classification is ContinuationClass.NO_CONTINUATION


def test_unknown_proof():
    frame = make_frame()
    result = modal_continuation_profile(frame, candidate_contract("MOVE"), (manual_service(frame, PlanningModality.UNKNOWN),))
    assert result.classification is ContinuationClass.UNKNOWN


def test_charge_service_constructed():
    assert any(service.capability == "CHARGE" for service in modal_services_from_frame(make_frame()))


def test_rest_coupled_service_constructed():
    services = modal_services_from_frame(make_frame(entities=[entity(kind="rest", identity="rest:1")]))
    rest = next(service for service in services if service.capability == "REST")
    assert rest.owners == ("fatigue", "integrity")


def test_inspect_service_constructed():
    services = modal_services_from_frame(make_frame(entities=[entity(kind="inspect", identity="inspect:1")]))
    assert any(service.capability == "INSPECT" for service in services)


def test_route_timing_unknown_propagates_unknown():
    frame = make_frame(progress_semantics="UNKNOWN")
    assert next(iter(modal_services_from_frame(frame))).modality is PlanningModality.UNKNOWN


def test_service_timing_unknown_propagates_unknown():
    frame = make_frame()
    timings = frame.service_timing.to_plain()
    timings["CHARGE"] = ModalFact(PlanningModality.UNKNOWN, "root-current", reason="test-unknown").to_canonical()
    frame = replace(frame, service_timing=FrozenMap(timings), material_fingerprint="")
    assert next(service for service in modal_services_from_frame(frame) if service.capability == "CHARGE").modality is PlanningModality.UNKNOWN


def test_service_timing_is_source_contract():
    assert make_frame().service_timing.to_plain()["CHARGE"]["modality"] == "MUST"


def test_body_capability_unsupported():
    frame = make_frame()
    missing = frame.constitutional_capabilities.to_plain().get("FLY")
    assert missing is None


def test_fingerprint_invalidation():
    left = make_frame()
    right = build_planning_evidence_frame(
        organism_tick=7, organism_age=7, monotonic_time=3.5,
        physiology={"energy": 0.6, "fatigue": 0.2, "integrity": 0.9, "stimulation": 0.5},
        body_state={"actuator_delay": 0.0}, body_profile=left.body.to_plain(),
        self_model_body_schema={"body_schema_id": "body:1", "version": 1},
        capability_support={}, world_entities=[], world_object_persistence=True,
        pending_execution={}, source_versions={"world": "w1"},
    )
    assert left.material_fingerprint != right.material_fingerprint


def test_candidate_order_invariance():
    frame = make_frame()
    views = ({"identity": "b", "capability": "REST"}, {"identity": "a", "capability": "CHARGE"})
    assert frame.bind_candidates(views).candidate_frame_identity == frame.bind_candidates(tuple(reversed(views))).candidate_frame_identity


def test_source_names_do_not_become_merit():
    frame = make_frame()
    views = ({"identity": "a", "capability": "CHARGE", "params": {"source": "x"}},)
    assert profiles_for_candidate_views(frame, views)[0]["profile"]["classification"] in {item.value for item in ContinuationClass}


def test_branch_frontier_within_32():
    result = physical_frontier_bound((2, 2, 2, 2, 2))
    assert result.status is TransitionStatus.SUPPORTED and result.active_paths == 32


def test_branch_frontier_overflow_is_unknown():
    result = physical_frontier_bound((2, 2, 2, 2, 2, 2))
    assert result.status is TransitionStatus.UNKNOWN and result.reason == "BRANCH_FRONTIER_EXCEEDED"


def test_modal_labels_do_not_multiply_physical_branches():
    frame = make_frame()
    must = modal_continuation_profile(frame, candidate_contract("MOVE"), (manual_service(frame, PlanningModality.MUST),))
    may = modal_continuation_profile(frame, candidate_contract("MOVE"), (manual_service(frame, PlanningModality.MAY),))
    assert must.max_active_paths == may.max_active_paths


def test_no_rng_argument_or_consumption():
    frame = make_frame()
    before = frame.material_fingerprint
    modal_continuation_profile(frame, candidate_contract("MOVE"), modal_services_from_frame(frame))
    assert frame.material_fingerprint == before


def test_no_learning_or_persistence_mutation():
    frame = make_frame()
    before = frame.to_canonical()
    profiles_for_candidate_views(frame, ({"identity": "a", "capability": "MOVE"},))
    assert frame.to_canonical() == before


def test_branch_specific_different_continuations():
    frame = make_frame()
    services = (
        manual_service(frame, PlanningModality.MUST, allowed=(0,), identity="service:a"),
        manual_service(frame, PlanningModality.MUST, allowed=(1,), identity="service:b"),
    )
    result = modal_continuation_profile(frame, candidate_contract("MOVE"), services)
    assert result.classification is ContinuationClass.STRONG_MUST and {row[1] for row in result.branch_witnesses} == {"service:a", "service:b"}


def test_one_branch_unknown_is_unknown():
    frame = make_frame()
    services = (
        manual_service(frame, PlanningModality.MUST, allowed=(0,), identity="service:a"),
        manual_service(frame, PlanningModality.UNKNOWN, allowed=(1,), identity="service:b"),
    )
    assert modal_continuation_profile(frame, candidate_contract("MOVE"), services).classification is ContinuationClass.UNKNOWN
