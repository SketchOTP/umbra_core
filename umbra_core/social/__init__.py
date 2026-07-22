"""D-006 SocialEngine — partner recognition hypotheses, derived satiation/latency."""

from __future__ import annotations

from umbra_core.social.engine import (
    MAX_ACTIVE_EVIDENCE_REFS,
    MAX_CONTINGENCY_CELLS,
    MAX_PARTNER_HYPOTHESES,
    MAX_SOURCE_HYPOTHESIS_IDS,
    ContingencyCell,
    HypothesisStatus,
    PartnerHypothesis,
    RecognitionMatch,
    RecognitionResult,
    SocialConfig,
    SocialEngine,
    SocialEngineError,
    condition_to_social_config,
)

__all__ = [
    "MAX_ACTIVE_EVIDENCE_REFS",
    "MAX_CONTINGENCY_CELLS",
    "MAX_PARTNER_HYPOTHESES",
    "MAX_SOURCE_HYPOTHESIS_IDS",
    "ContingencyCell",
    "HypothesisStatus",
    "PartnerHypothesis",
    "RecognitionMatch",
    "RecognitionResult",
    "SocialConfig",
    "SocialEngine",
    "SocialEngineError",
    "condition_to_social_config",
]
