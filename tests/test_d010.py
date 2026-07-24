"""UMBRA-D-010 temporal continuity tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from umbra_core.temporal.clock import TrustedSample, compute_sample_hash
from umbra_core.temporal.engine import (
    TemporalEngine,
    TemporalEngineError,
    build_tick_temporal_context,
)
from umbra_core.temporal.migration import TemporalMigrationContext, initialize_temporal_epoch
from umbra_core.temporal.state import (
    AnchorTrustClass,
    TemporalState,
    TimeAnchor,
    assert_age_never_decreases,
    compute_state_hash,
    sample_temporal_state,
    with_state_hash,
)


def _migration_context() -> TemporalMigrationContext:
    return TemporalMigrationContext(
        migration_id="d010.genesis.v1",
        source_commit="af35371",
        source_seal="UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED",
        pre_temporal_history_ref="event-log:pre-d010",
        genesis_session_id="session:genesis",
        genesis_monotonic_ns=1_000_000,
        genesis_sample_sequence=0,
    )


def test_temporal_state_hash_is_canonical():
    state = sample_temporal_state()
    assert compute_state_hash(state) == state.state_hash

    cleared = replace(state, state_hash="")
    assert compute_state_hash(cleared) == state.state_hash

    shuffled = replace(
        state,
        recurrence_index=(("rec:late", {"status": "CANDIDATE"}), ("rec:early", {"status": "ACTIVE"})),
    )
    shuffled = with_state_hash(shuffled)
    assert compute_state_hash(shuffled) == shuffled.state_hash
    assert shuffled.state_hash != state.state_hash

    reordered = replace(state, organism_age_ticks=state.organism_age_ticks)
    assert compute_state_hash(reordered) == state.state_hash


def test_organism_age_never_decreases():
    state = sample_temporal_state()
    assert_age_never_decreases(state.organism_age_ticks, state.organism_age_ticks)

    with pytest.raises(ValueError, match="organism_age_ticks_decreased"):
        assert_age_never_decreases(5, 4)


def test_time_anchor_has_trust_provenance_fields():
    anchor = sample_temporal_state().last_time_anchor
    assert isinstance(anchor, TimeAnchor)
    assert anchor.anchor_trust_class == AnchorTrustClass.MISSING_WALL
    assert anchor.trust_reason_codes == ("genesis_no_wall_sample",)
    assert anchor.eligible_as_downtime_baseline is False
    assert anchor.source_sample_hash
    assert anchor.session_id_at_commit == "session:genesis"
    assert anchor.advance_id == "advance:genesis"


def test_trusted_sample_hash_is_stable():
    sample = TrustedSample(
        session_id="session:a",
        monotonic_ns=42,
        optional_wall_time=None,
        wall_time_source=None,
        wall_time_uncertainty=0.0,
        sample_sequence=1,
    )
    assert compute_sample_hash(sample) == compute_sample_hash(sample)
    assert len(compute_sample_hash(sample)) == 64


def test_temporal_init_is_idempotent():
    ctx = _migration_context()
    first = initialize_temporal_epoch(None, ctx=ctx)
    second = initialize_temporal_epoch(first, ctx=ctx)
    assert second is first
    assert second.organism_age_ticks == 0
    assert second.organism_active_ticks == 0
    assert second.temporal_epoch_id == first.temporal_epoch_id


def test_second_load_does_not_reset_age():
    ctx = _migration_context()
    genesis = initialize_temporal_epoch(None, ctx=ctx)
    aged = with_state_hash(
        replace(
            genesis,
            organism_age_ticks=7,
            organism_active_ticks=5,
            state_version=genesis.state_version + 1,
        )
    )
    reloaded = initialize_temporal_epoch(aged, ctx=ctx)
    assert reloaded is aged
    assert reloaded.organism_age_ticks == 7
    assert reloaded.organism_active_ticks == 5


def _trusted_sample(*, sequence: int = 1) -> TrustedSample:
    return TrustedSample(
        session_id="session:test",
        monotonic_ns=2_000_000,
        optional_wall_time=None,
        wall_time_source=None,
        wall_time_uncertainty=0.0,
        sample_sequence=sequence,
    )


def _engine_with_age(*, age: int = 0, active: int = 0, version: int = 0) -> TemporalEngine:
    state = sample_temporal_state()
    if age or active or version:
        state = with_state_hash(
            replace(
                state,
                organism_age_ticks=age,
                organism_active_ticks=active,
                state_version=version,
            )
        )
    return TemporalEngine(state)


def test_abandoned_tick_does_not_advance_age():
    engine = _engine_with_age(age=3, active=2, version=4)
    before = engine.state
    plan = engine.prepare_advance(_trusted_sample(), orchestration_sequence=1)
    engine.abandon_advance(plan.advance_id)
    after = engine.state
    assert after.organism_age_ticks == before.organism_age_ticks == 3
    assert after.organism_active_ticks == before.organism_active_ticks == 2
    assert after.state_version == before.state_version == 4
    assert engine.in_flight_plan is None


def test_advance_id_unique_across_prepare_abandon_cycles():
    engine = _engine_with_age()
    first = engine.prepare_advance(_trusted_sample(sequence=1), orchestration_sequence=1)
    engine.abandon_advance(first.advance_id)
    second = engine.prepare_advance(_trusted_sample(sequence=2), orchestration_sequence=2)
    engine.abandon_advance(second.advance_id)
    assert first.advance_id != second.advance_id
    assert first.advance_id.startswith("advance:")
    assert second.advance_id.startswith("advance:")


def test_tick_context_uses_proposed_age():
    engine = _engine_with_age(age=5, active=4, version=2)
    plan = engine.prepare_advance(_trusted_sample(), orchestration_sequence=7)
    context = build_tick_temporal_context(plan)
    assert context.effective_age_ticks == 6
    assert context.effective_active_ticks == 5
    assert context.advance_id == plan.advance_id
    assert context.orchestration_sequence == 7
    assert context.prior_state_version == 2
    assert context.prior_state_hash == engine.state.state_hash


def test_prepare_advance_does_not_mutate_state():
    engine = _engine_with_age(age=9, active=8, version=3)
    before = engine.state
    engine.prepare_advance(_trusted_sample(), orchestration_sequence=1)
    after = engine.state
    assert after is before
    assert after.organism_age_ticks == 9
    assert after.organism_active_ticks == 8
    assert after.state_version == 3


def test_prepare_while_in_flight_raises():
    engine = _engine_with_age()
    engine.prepare_advance(_trusted_sample(sequence=1), orchestration_sequence=1)
    with pytest.raises(TemporalEngineError, match="advance_already_prepared"):
        engine.prepare_advance(_trusted_sample(sequence=2), orchestration_sequence=2)


def test_runtime_attaches_temporal_engine_when_enabled(tmp_path):
    from umbra_core.runtime import OrganismConfig, create_organism

    config = OrganismConfig(
        db_path=str(tmp_path / "temporal.db"),
        temporal_enabled=True,
    )
    org = create_organism(config)
    assert org.temporal is not None
    assert org.temporal.state.organism_age_ticks == 0
    assert org.temporal.in_flight_plan is None
