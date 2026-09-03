"""Static R6F feasibility audit over existing UMBRA source semantics.

This module is research-only.  It does not create an organism, execute a
runtime tick, write owner state, or alter the R6E relation.  It records two
separate questions: whether an existing policy-visible recoverability seam can
produce a categorical candidate-relative loss, and whether a previously
verified route record remains applicable to an exact later opportunity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology, verified_outcome_effect_branches
from umbra_core.recoverability.contracts import candidate_is_admissible
from umbra_core.world_model.engine import FactKind, WorldEntity
from umbra_core.world_model.route_evidence import (
    ROUTE_EVIDENCE_SEMANTICS,
    ROUTE_CAPABILITY,
    TERMINAL_BY_KIND,
    VerifiedRouteExperience,
    resolve_opportunity,
)


BODY_SCHEMA = "r6f-body-schema"
OPPORTUNITY_ID = "r6f-opportunity-resource"


@dataclass(frozen=True)
class NaturalLossCase:
    source_owner: str
    source_fields: tuple[str, ...]
    physiology: dict[str, float]
    observation: dict[str, Any]
    preserving_candidate: dict[str, Any]
    destroying_candidate: dict[str, Any]
    current_route: tuple[bool, int, float]
    preserving_loss: bool
    destroying_loss: bool
    preserving_hard_admissible: bool
    destroying_hard_admissible: bool
    destruction_status: str


def policy_observation(*, entity_id: str = OPPORTUNITY_ID) -> dict[str, Any]:
    """A policy-visible bounded support record, with no Habitat coordinates."""
    return {
        "entity_id": entity_id,
        "kind": "resource",
        "relative_direction": 0.0,
        "estimated_distance": 5.0,
        "distance_support_upper_bound": 23.01,
        "support_center_dx": 5.0,
        "support_center_dy": 0.0,
        "support_radius": 18.01,
        "support_provenance": "source:policy-visible-bounded-support",
        "support_source_kind": "CURRENT_OBSERVATION",
        "support_semantics": "VERIFIED_OBSERVED_SUPPORT",
        "support_body_schema_id": BODY_SCHEMA,
        "fact_kind": FactKind.CURRENT_OBSERVATION.value,
        "source": "world_model_policy_view",
    }


def natural_loss_probe() -> NaturalLossCase:
    """Find the existing policy seam's fixed, ordinary loss configuration.

    The values are a static boundary probe over existing source semantics, not
    a live fixture, learned-state injection, or proposed threshold.
    """
    physiology = Physiology(energy=0.15).to_state()
    observation = policy_observation()
    preserve = Candidate("IDLE", {})
    destroy = Candidate("MOVE", {"heading_delta": 0.0, "step": 1.0})
    arb = Arbitrator()

    def admissible(candidate: Candidate) -> bool:
        return candidate_is_admissible(
            candidate,
            physiology=Physiology.from_state(physiology),
            observations=[observation],
            arbitration_state=arb.state,
            effect_branches=verified_outcome_effect_branches(candidate.capability),
        )

    current = Arbitrator._energy_route_budget(Physiology.from_state(physiology), observation)
    preserve_loss = Arbitrator._ordinary_action_destroys_recovery_route(
        Physiology.from_state(physiology), observation, preserve
    )
    destroy_loss = Arbitrator._ordinary_action_destroys_recovery_route(
        Physiology.from_state(physiology), observation, destroy
    )
    return NaturalLossCase(
        source_owner="policy-visible recoverability / Physiology / verified effects",
        source_fields=(
            "BOUNDS.energy.critical_low",
            "DEFAULT_DRIFT.energy",
            "OUTCOME_EFFECTS.MOVE.energy",
            "observation.distance_support_upper_bound",
            "observation.support_body_schema_id",
        ),
        physiology={name: float(value) for name, value in physiology.items()},
        observation=observation,
        preserving_candidate={"capability": preserve.capability, "params": dict(preserve.params)},
        destroying_candidate={"capability": destroy.capability, "params": dict(destroy.params)},
        current_route=current,
        preserving_loss=preserve_loss,
        destroying_loss=destroy_loss,
        preserving_hard_admissible=admissible(preserve),
        destroying_hard_admissible=admissible(destroy),
        destruction_status=(
            "CATEGORICAL_SUPPORTED_MARGIN_EXHAUSTED"
            if current[0] and destroy_loss
            else "UNSUPPORTED_STATIC_CASE"
        ),
    )


def route_experience(*, evidence_id: str = "route-experience:r6f") -> VerifiedRouteExperience:
    return VerifiedRouteExperience(
        evidence_id=evidence_id,
        opportunity_entity_id=OPPORTUNITY_ID,
        opportunity_entity_kind="resource",
        body_schema_id=BODY_SCHEMA,
        route_capability=ROUTE_CAPABILITY,
        terminal_capability="CHARGE",
        start_tick=4,
        final_tick=11,
        start_distance_support_upper_bound=23.01,
        start_fact_kind=FactKind.CURRENT_OBSERVATION.value,
        start_support_provenance="source:policy-visible-bounded-support",
        verified_movement_execution_count=1,
        movement_completion_lags=(1,),
        terminal_completion_lag=1,
        terminal_result=True,
        route_failure_code=None,
        execution_outcome_refs=("verified-outcome:r6f-approach", "verified-outcome:r6f-charge"),
    )


def applicable_route(
    experience: VerifiedRouteExperience,
    *,
    entities: Mapping[str, WorldEntity],
    body_schema_id: str,
) -> dict[str, Any]:
    """Check exact later-root identity/applicability without selecting a target."""
    entity = entities.get(experience.opportunity_entity_id)
    resolution = resolve_opportunity(
        entities,
        target_kind=experience.opportunity_entity_kind,
        body_schema_id=body_schema_id,
    )
    checks = {
        "terminal_matches_kind": TERMINAL_BY_KIND.get(experience.opportunity_entity_kind)
        == experience.terminal_capability,
        "route_semantics": experience.evidence_semantics == ROUTE_EVIDENCE_SEMANTICS,
        "experience_body_schema_matches": experience.body_schema_id == body_schema_id,
        "exact_entity_present": entity is not None,
        "exact_resolution": resolution.status == "EXACT"
        and resolution.opportunity_entity_id == experience.opportunity_entity_id,
        "entity_support_schema_matches": entity is not None
        and str(entity.support_body_schema_id) == body_schema_id,
        "entity_kind_matches": entity is not None
        and entity.entity_kind == experience.opportunity_entity_kind,
    }
    return {
        "status": "SUPPORTED" if all(checks.values()) else "UNKNOWN",
        "checks": checks,
        "opportunity_entity_id": experience.opportunity_entity_id,
        "body_schema_id": body_schema_id,
        "hidden_habitat_truth_used": False,
    }


def source_graph() -> dict[str, Any]:
    return {
        "schema": "AS003PR6F_SOURCE_GRAPH_V1",
        "route_learning": {
            "owner": "WorldModel.route_evidence",
            "input": "executed VerifiedOutcome with exact opportunity/body binding",
            "output": "VERIFIED_ROUTE_EXPERIENCE_V2",
            "temporal_position": "before later qualification root",
            "authority": "learning-only; no planner/arbitration reader",
        },
        "natural_loss": {
            "owner": "policy-visible recoverability view",
            "inputs": [
                "Physiology current state",
                "BOUNDS critical boundary",
                "DEFAULT_DRIFT",
                "verified outcome effect branches",
                "WorldModel bounded opportunity support",
            ],
            "candidate_consequence": "existing MOVE effect and support-distance projection",
            "categorical_result": "feasible-to-infeasible supported margin transition",
            "unknown_conditions": [
                "missing support geometry",
                "body-schema mismatch",
                "unknown/probabilistic movement support",
                "non-policy-visible opportunity",
            ],
        },
        "route_applicability": {
            "required": [
                "exact opportunity entity identity",
                "same body schema",
                "eligible current/remembered policy-visible entity",
                "matching terminal capability",
                "verified route evidence semantics",
            ],
            "not_used": ["Habitat coordinates", "confidence winner", "nearest target", "utility"],
        },
    }


def static_feasibility_report() -> dict[str, Any]:
    case = natural_loss_probe()
    experience = route_experience()
    entity = WorldEntity(
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
    applicability = applicable_route(
        experience, entities={OPPORTUNITY_ID: entity}, body_schema_id=BODY_SCHEMA
    )
    return {
        "schema": "AS003PR6F_STATIC_FEASIBILITY_AUDIT_V1",
        "natural_loss": {
            "source_owner": case.source_owner,
            "source_fields": list(case.source_fields),
            "current_route": {
                "feasible": case.current_route[0],
                "required_approaches": case.current_route[1],
                "route_cost": case.current_route[2],
            },
            "preserving_candidate": case.preserving_candidate,
            "destroying_candidate": case.destroying_candidate,
            "preserving_loss": case.preserving_loss,
            "destroying_loss": case.destroying_loss,
            "preserving_hard_admissible": case.preserving_hard_admissible,
            "destroying_hard_admissible": case.destroying_hard_admissible,
            "destruction_status": case.destruction_status,
            "candidate_specific_fields": ["verified MOVE effect", "MOVE step parameter"],
            "root_option_fields": [
                "exact opportunity identity",
                "body schema",
                "verified route evidence identity",
                "pre-root provenance",
            ],
        },
        "route_applicability": applicability,
        "scenario_selection": {
            "status": "DEFERRED_UNTIL_STATIC_GATES_AND_EXISTING_SCENARIO_AUDIT",
            "candidate_pair": "NOT_FROZEN",
            "organism_runs": 0,
        },
        "production_change": 0,
        "hidden_truth_used": False,
    }
