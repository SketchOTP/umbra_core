"""Pure, non-authoritative hypothetical transition substrate.

This package has no live callsites.  It represents conservative hypothetical
evidence only; it neither plans nor executes organism behavior.
"""

from umbra_core.hypothetical.core import (
    BRANCH_CEILING,
    DependencyToken,
    EvidenceEnvelope,
    HypotheticalState,
    OpportunityEvidence,
    PhysiologyBranch,
    RegulatoryService,
    RouteEvidence,
    TransitionContract,
    TransitionResult,
    TransitionStatus,
    ValidatedRegulatoryService,
    dependency_fingerprint,
    dependency_fingerprint_matches,
    transition,
    validate_regulatory_service,
)

__all__ = [
    "BRANCH_CEILING",
    "DependencyToken",
    "EvidenceEnvelope",
    "HypotheticalState",
    "OpportunityEvidence",
    "PhysiologyBranch",
    "RegulatoryService",
    "RouteEvidence",
    "TransitionContract",
    "TransitionResult",
    "TransitionStatus",
    "ValidatedRegulatoryService",
    "dependency_fingerprint",
    "dependency_fingerprint_matches",
    "transition",
    "validate_regulatory_service",
]
