"""D-006 SocialEngine — partner recognition hypotheses, derived satiation/latency."""

from __future__ import annotations

from umbra_core.social.engine import (
    MAX_ACTIVE_EVIDENCE_REFS,
    MAX_CONTINGENCY_CELLS,
    MAX_PARTNER_HYPOTHESES,
    MAX_PENDING_INTERACTIONS,
    MAX_SOURCE_HYPOTHESIS_IDS,
    RESPONSE_NONE_TIMEOUT,
    RESPONSE_WINDOW_CONTINGENT,
    RESPONSE_WINDOW_DELAYED,
    ContingencyCell,
    HypothesisStatus,
    PartnerHypothesis,
    PendingInteraction,
    PendingStatus,
    RecognitionMatch,
    RecognitionResult,
    ResponseClass,
    SocialConfig,
    SocialEngine,
    SocialEngineError,
    condition_to_social_config,
)

__all__ = [
    "MAX_ACTIVE_EVIDENCE_REFS",
    "MAX_CONTINGENCY_CELLS",
    "MAX_PARTNER_HYPOTHESES",
    "MAX_PENDING_INTERACTIONS",
    "MAX_SOURCE_HYPOTHESIS_IDS",
    "RESPONSE_NONE_TIMEOUT",
    "RESPONSE_WINDOW_CONTINGENT",
    "RESPONSE_WINDOW_DELAYED",
    "ContingencyCell",
    "HypothesisStatus",
    "PartnerHypothesis",
    "PendingInteraction",
    "PendingStatus",
    "RecognitionMatch",
    "RecognitionResult",
    "ResponseClass",
    "SocialConfig",
    "SocialEngine",
    "SocialEngineError",
    "condition_to_social_config",
]
