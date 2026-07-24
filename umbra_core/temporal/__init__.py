"""D-010 temporal continuity authority types."""

from umbra_core.temporal.clock import TrustedSample, compute_sample_hash
from umbra_core.temporal.migration import TemporalMigrationContext, initialize_temporal_epoch
from umbra_core.temporal.state import (
    AnchorTrustClass,
    TemporalState,
    TimeAnchor,
    WallClockMapping,
    assert_age_never_decreases,
    canonical_serialize,
    compute_definition_hash,
    compute_state_hash,
    sample_temporal_state,
    with_state_hash,
)

__all__ = [
    "AnchorTrustClass",
    "TemporalMigrationContext",
    "TemporalState",
    "TimeAnchor",
    "TrustedSample",
    "WallClockMapping",
    "assert_age_never_decreases",
    "canonical_serialize",
    "compute_definition_hash",
    "compute_sample_hash",
    "compute_state_hash",
    "initialize_temporal_epoch",
    "sample_temporal_state",
    "with_state_hash",
]
