"""D-003 predictive world model — bounded environment learning."""

from __future__ import annotations

from umbra_core.world_model.engine import (
    AFFORDANCE_ACTIONS,
    MAX_CANDIDATE_PLANS,
    MAX_ENTITIES,
    MAX_PLAN_DEPTH,
    MAX_PLAN_RETRIES,
    MAX_TRANSITION_MODELS,
    AffordanceBelief,
    FactKind,
    ModelStatus,
    PlanTrace,
    TransitionModel,
    VerifiedMotionDelta,
    WorldEntity,
    WorldModel,
    WorldModelConfig,
    WorldPrediction,
    condition_to_world_model_config,
)
from umbra_core.world_model.route_evidence import (
    DEFAULT_ROUTE_EVIDENCE_CAPACITY,
    OpportunityResolution,
    RouteEvidenceStore,
    VerifiedRouteExperience,
    resolve_opportunity,
)

__all__ = [
    "AFFORDANCE_ACTIONS",
    "MAX_CANDIDATE_PLANS",
    "MAX_ENTITIES",
    "MAX_PLAN_DEPTH",
    "MAX_PLAN_RETRIES",
    "MAX_TRANSITION_MODELS",
    "AffordanceBelief",
    "FactKind",
    "ModelStatus",
    "PlanTrace",
    "TransitionModel",
    "VerifiedMotionDelta",
    "WorldEntity",
    "WorldModel",
    "WorldModelConfig",
    "WorldPrediction",
    "condition_to_world_model_config",
    "DEFAULT_ROUTE_EVIDENCE_CAPACITY",
    "OpportunityResolution",
    "RouteEvidenceStore",
    "VerifiedRouteExperience",
    "resolve_opportunity",
]
