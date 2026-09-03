from __future__ import annotations

from dataclasses import replace

from umbra_core.world_model.engine import FactKind, WorldEntity

from experiments.as003pr6f.feasibility import (
    BODY_SCHEMA,
    OPPORTUNITY_ID,
    applicable_route,
    natural_loss_probe,
    policy_observation,
    route_experience,
    static_feasibility_report,
)


def _entity(**updates) -> WorldEntity:
    values = dict(
        entity_id=OPPORTUNITY_ID,
        entity_kind="resource",
        estimated_state={"relative_direction": 0.0, "estimated_distance": 5.0},
        last_observed_at=12.0,
        confidence=0.8,
        uncertainty=0.2,
        persistence_probability=0.8,
        evidence_count=2,
        distance_support_upper_bound=23.01,
        support_center_dx=5.0,
        support_center_dy=0.0,
        support_radius=18.01,
        support_provenance="source:policy-visible-bounded-support",
        support_source_kind="CURRENT_OBSERVATION",
        support_body_schema_id=BODY_SCHEMA,
        fact_kind=FactKind.CURRENT_OBSERVATION.value,
        last_tick=12,
    )
    values.update(updates)
    return WorldEntity(**values)


def test_existing_policy_seam_has_ordinary_natural_loss_case() -> None:
    case = natural_loss_probe()
    assert case.current_route[0] is True
    assert case.preserving_loss is False
    assert case.destroying_loss is True
    assert case.preserving_hard_admissible is True
    assert case.destroying_hard_admissible is True
    assert case.destruction_status == "CATEGORICAL_SUPPORTED_MARGIN_EXHAUSTED"


def test_route_applicability_requires_exact_later_entity_and_body() -> None:
    experience = route_experience()
    supported = applicable_route(
        experience, entities={OPPORTUNITY_ID: _entity()}, body_schema_id=BODY_SCHEMA
    )
    assert supported["status"] == "SUPPORTED"

    stale = applicable_route(
        experience,
        entities={OPPORTUNITY_ID: _entity(support_body_schema_id="old-body")},
        body_schema_id=BODY_SCHEMA,
    )
    assert stale["status"] == "UNKNOWN"

    missing = applicable_route(
        experience, entities={}, body_schema_id=BODY_SCHEMA
    )
    assert missing["status"] == "UNKNOWN"


def test_route_applicability_rejects_ambiguous_same_kind_entities() -> None:
    experience = route_experience()
    other = _entity(entity_id="other-resource")
    result = applicable_route(
        experience,
        entities={OPPORTUNITY_ID: _entity(), "other-resource": other},
        body_schema_id=BODY_SCHEMA,
    )
    assert result["status"] == "UNKNOWN"
    assert result["checks"]["exact_resolution"] is False


def test_source_graph_report_is_non_authoritative_and_deterministic() -> None:
    first = static_feasibility_report()
    second = static_feasibility_report()
    assert first == second
    assert first["production_change"] == 0
    assert first["hidden_truth_used"] is False
    assert first["scenario_selection"]["organism_runs"] == 0
