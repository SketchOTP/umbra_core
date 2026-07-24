"""D-010 temporal continuity authority types."""

from umbra_core.temporal.clock import TrustedSample, compute_sample_hash
from umbra_core.temporal.engine import (
    AnchorDelta,
    TemporalAdvancePlan,
    TemporalEngine,
    TemporalEngineError,
    TickTemporalContext,
    build_tick_temporal_context,
)
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
    "AnchorDelta",
    "AnchorTrustClass",
    "TemporalAdvancePlan",
    "TemporalEngine",
    "TemporalEngineError",
    "TemporalMigrationContext",
    "TemporalState",
    "TickTemporalContext",
    "TimeAnchor",
    "TrustedSample",
    "WallClockMapping",
    "assert_age_never_decreases",
    "build_tick_temporal_context",
    "canonical_serialize",
    "compute_definition_hash",
    "compute_sample_hash",
    "compute_state_hash",
    "initialize_temporal_epoch",
    "sample_temporal_state",
    "with_state_hash",
]
