"""D-007 IndividualityEngine — lived individuality / history-shaped dispositions."""

from __future__ import annotations

from umbra_core.individuality.engine import (
    AUTHORITATIVE_INDIVIDUALITY_EVENTS,
    DISPOSITION_DIMENSIONS,
    FORBIDDEN_STATE_KEYS,
    MAX_DISPOSITION_RECORDS,
    MODIFIER_ABS_MAX,
    DispositionEstimate,
    IndividualityConfig,
    IndividualityEngine,
    IndividualityEngineError,
    VerifiedEvidence,
    condition_to_individuality_config,
    infer_evidence_from_outcome,
)

__all__ = [
    "AUTHORITATIVE_INDIVIDUALITY_EVENTS",
    "DISPOSITION_DIMENSIONS",
    "FORBIDDEN_STATE_KEYS",
    "MAX_DISPOSITION_RECORDS",
    "MODIFIER_ABS_MAX",
    "DispositionEstimate",
    "IndividualityConfig",
    "IndividualityEngine",
    "IndividualityEngineError",
    "VerifiedEvidence",
    "condition_to_individuality_config",
    "infer_evidence_from_outcome",
]
