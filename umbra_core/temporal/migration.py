"""D-009 → D-010 temporal epoch initialization."""

from __future__ import annotations

from dataclasses import dataclass, replace

from umbra_core.temporal.clock import TrustedSample, compute_sample_hash
from umbra_core.temporal.state import (
    GENESIS_ADVANCE_ID,
    TEMPORAL_SCHEMA_VERSION,
    AnchorTrustClass,
    TemporalState,
    TimeAnchor,
    compute_definition_hash,
    with_anchor_state_hash,
    with_state_hash,
)
from umbra_core.temporal.observations import empty_dedup_summary
from umbra_core.util import sha256_hex


@dataclass(frozen=True)
class TemporalMigrationContext:
    migration_id: str
    source_commit: str
    source_seal: str
    pre_temporal_history_ref: str
    genesis_session_id: str
    genesis_monotonic_ns: int
    genesis_sample_sequence: int


def _temporal_epoch_id(ctx: TemporalMigrationContext) -> str:
    material = (
        f"{ctx.migration_id}|{ctx.source_commit}|{ctx.source_seal}|"
        f"{ctx.pre_temporal_history_ref}"
    )
    return f"epoch:{sha256_hex(material)[:16]}"


def initialize_temporal_epoch(
    existing: TemporalState | None,
    *,
    ctx: TemporalMigrationContext,
) -> TemporalState:
    """Idempotent D-009→D-010 genesis. Preserves existing age on reload."""
    if existing is not None:
        return existing

    genesis_sample = TrustedSample(
        session_id=ctx.genesis_session_id,
        monotonic_ns=ctx.genesis_monotonic_ns,
        optional_wall_time=None,
        wall_time_source=None,
        wall_time_uncertainty=0.0,
        sample_sequence=ctx.genesis_sample_sequence,
    )
    sample_hash = compute_sample_hash(genesis_sample)
    anchor = with_anchor_state_hash(
        TimeAnchor(
            organism_age_ticks=0,
            organism_active_ticks=0,
            state_version=0,
            state_hash="",
            wall_time=None,
            wall_time_source=None,
            wall_time_uncertainty=0.0,
            session_id_at_commit=ctx.genesis_session_id,
            advance_id=GENESIS_ADVANCE_ID,
            anchor_trust_class=AnchorTrustClass.MISSING_WALL,
            trust_reason_codes=("genesis_no_wall_sample",),
            eligible_as_downtime_baseline=False,
            source_sample_hash=sample_hash,
        )
    )
    base = TemporalState(
        schema_version=TEMPORAL_SCHEMA_VERSION,
        temporal_epoch_id=_temporal_epoch_id(ctx),
        initialized_from_commit=ctx.source_commit,
        pre_temporal_history_ref=ctx.pre_temporal_history_ref,
        organism_age_ticks=0,
        organism_active_ticks=0,
        last_committed_orchestration_sequence=0,
        last_advance_id=GENESIS_ADVANCE_ID,
        last_time_anchor=anchor,
        wall_clock_mapping=None,
        clock_uncertainty=0.0,
        recurrence_index=(),
        dedup_summary=empty_dedup_summary(),
        observation_miss_keys=(),
        state_version=0,
        definition_hash="",
        state_hash="",
    )
    with_definition = replace(base, definition_hash=compute_definition_hash(base))
    return with_state_hash(with_definition)
