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
from umbra_core.temporal.observations import (
    CommitMode,
    ObservationWindowEvidence,
    MAX_RECENT_EVIDENCE_IDENTITIES,
    empty_dedup_summary,
    identity_seen,
    register_identities,
)
from umbra_core.temporal.allowlists import AllowlistError, assert_observable_evidence_allowed
from umbra_core.temporal.migration import TemporalMigrationContext, initialize_temporal_epoch
from umbra_core.temporal.recurrence import (
    EvidenceLane,
    HypothesisStatus,
    RecurrenceHypothesis,
    compute_next_index,
    compute_recurrence_key,
    recurrence_id_from_key,
)
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


def _temporal_org(tmp_path, **kwargs):
    from umbra_core.runtime import OrganismConfig, create_organism

    config = OrganismConfig(
        db_path=str(tmp_path / "temporal.db"),
        temporal_enabled=True,
        snapshot_every=1000,
        **kwargs,
    )
    return create_organism(config)


def test_committed_tick_contains_temporal_advance_record(tmp_path):
    org = _temporal_org(tmp_path)
    org.tick_once()
    events = [e for e in org.store.iter_events() if e["event_type"] == "orchestration_tick_committed"]
    assert len(events) == 1
    record = events[0]["payload"]["temporal_advance_record"]
    assert record["advance_id"].startswith("advance:")
    assert record["new_age_ticks"] == 1
    assert record["prior_age_ticks"] == 0
    assert "temporal_transaction" in events[0]["payload"]


def test_failed_tick_has_no_temporal_advance_record(tmp_path, monkeypatch):
    org = _temporal_org(tmp_path)

    def boom(*_args, **_kwargs):
        raise RuntimeError("tick_failed")

    monkeypatch.setattr(org, "_push_expression_frame", boom)
    with pytest.raises(RuntimeError, match="tick_failed"):
        org.tick_once()
    assert org.temporal.state.organism_age_ticks == 0
    events = [e for e in org.store.iter_events() if e["event_type"] == "orchestration_tick_committed"]
    assert events == []


def test_temporal_advance_commits_atomically_with_tick(tmp_path):
    org = _temporal_org(tmp_path)
    before_version = org.temporal.state.state_version
    org.tick_once()
    assert org.temporal.state.organism_age_ticks == 1
    assert org.temporal.state.organism_active_ticks == 1
    assert org.temporal.state.state_version == before_version + 1
    assert org.temporal.in_flight_plan is None


def test_temporal_advance_id_cannot_commit_twice():
    from umbra_core.temporal.events import apply_advance_plan

    engine = _engine_with_age(age=1, active=1, version=1)
    sample = _trusted_sample(sequence=2)
    plan = engine.prepare_advance(sample, orchestration_sequence=2)
    dup = replace(plan, advance_id=engine.state.last_advance_id)
    engine.abandon_advance(plan.advance_id)
    with pytest.raises(TemporalEngineError, match="advance_id_already_committed"):
        apply_advance_plan(engine.state, dup, sample, "session:test")


def test_tick_replay_reconstructs_anchor_and_clock_mapping(tmp_path):
    from umbra_core.temporal.events import (
        ORCHESTRATION_TICK_COMMITTED,
        replay_temporal_state_from_events,
    )

    org = _temporal_org(tmp_path, wall_time_fn=lambda: 1_700_000_000.5)
    genesis = org.temporal.state
    org.tick_once()
    org.tick_once()
    events = org.store.iter_events()
    replayed = replay_temporal_state_from_events(genesis, events)
    assert replayed.organism_age_ticks == 2
    assert replayed.organism_age_ticks == org.temporal.state.organism_age_ticks
    assert replayed.last_time_anchor.wall_time == 1_700_000_000.5
    assert replayed.wall_clock_mapping is not None
    assert replayed.wall_clock_mapping.wall_time_seconds == 1_700_000_000.5
    tick_events = [e for e in events if e["event_type"] == ORCHESTRATION_TICK_COMMITTED]
    assert len(tick_events) == 2


def test_ordinary_tick_does_not_emit_duplicate_anchor_event(tmp_path):
    from umbra_core.temporal.events import TEMPORAL_ANCHOR_COMMITTED

    org = _temporal_org(tmp_path)
    org.tick_once()
    org.tick_once()
    anchors = [e for e in org.store.iter_events() if e["event_type"] == TEMPORAL_ANCHOR_COMMITTED]
    assert anchors == []


def test_snapshot_on_due_tick_matches_committed_temporal_state(tmp_path):
    from umbra_core.runtime import OrganismConfig, create_organism

    config = OrganismConfig(
        db_path=str(tmp_path / "temporal.db"),
        temporal_enabled=True,
        snapshot_every=1,
    )
    org = create_organism(config)
    org.tick_once()
    snap = org.store.load_snapshot()
    live = org.temporal.state
    snap_temporal = snap["state"]["temporal"]
    assert snap_temporal["organism_age_ticks"] == live.organism_age_ticks == 1
    assert snap_temporal["state_version"] == live.state_version


def test_missing_advance_record_fails_replay(tmp_path):
    from umbra_core.temporal.events import (
        ORCHESTRATION_TICK_COMMITTED,
        TemporalReplayError,
        replay_temporal_state_from_events,
    )

    org = _temporal_org(tmp_path)
    genesis = org.temporal.state
    org.tick_once()
    events = org.store.iter_events()
    bad = []
    for event in events:
        if event["event_type"] != ORCHESTRATION_TICK_COMMITTED:
            bad.append(event)
            continue
        payload = dict(event["payload"])
        payload.pop("temporal_advance_record", None)
        bad.append({**event, "payload": payload})
    with pytest.raises(TemporalReplayError, match="missing_temporal_advance_record"):
        replay_temporal_state_from_events(genesis, bad)


def _observe_periodic(
    engine: TemporalEngine,
    *,
    period: int,
    count: int,
    start: int = 0,
    event_kind: str = "habitat.feeder_cycle",
    context_key: str = "feeder:a",
) -> RecurrenceHypothesis:
    hypothesis: RecurrenceHypothesis | None = None
    for i in range(count):
        hypothesis = engine.observe_recurrence_occurrence(
            event_kind=event_kind,
            internal_context_key=context_key,
            occurrence_id=f"occ:{i}",
            evidence_identity=f"evidence:{i}",
            tick=start + i * period,
            lane=EvidenceLane.ORGANISM_OBSERVABLE,
        )
    assert hypothesis is not None
    return hypothesis


def test_stable_periodic_occurrences_learn_true_period():
    engine = _engine_with_age()
    hypothesis = _observe_periodic(engine, period=10, count=4)
    assert hypothesis.status == HypothesisStatus.ACTIVE
    assert hypothesis.period_estimate == pytest.approx(10.0)
    assert hypothesis.observation_count == 4


def test_jittered_series_learns_usable_period_and_jitter():
    engine = _engine_with_age()
    ticks = [0, 11, 19, 31, 39]
    hypothesis: RecurrenceHypothesis | None = None
    for i, tick in enumerate(ticks):
        hypothesis = engine.observe_recurrence_occurrence(
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:b",
            occurrence_id=f"occ:{i}",
            evidence_identity=f"evidence:{i}",
            tick=tick,
            lane=EvidenceLane.ORGANISM_OBSERVABLE,
        )
    assert hypothesis is not None
    assert hypothesis.status == HypothesisStatus.ACTIVE
    assert hypothesis.period_estimate == pytest.approx(10.0, abs=2.0)
    assert hypothesis.jitter_estimate > 0.0


def test_frequency_only_authoritative_lane_does_not_promote_to_active():
    engine = _engine_with_age()
    hypothesis: RecurrenceHypothesis | None = None
    for i in range(6):
        hypothesis = engine.observe_recurrence_occurrence(
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:auth",
            occurrence_id=f"occ:{i}",
            evidence_identity=f"evidence:{i}",
            tick=i * 10,
            lane=EvidenceLane.AUTHORITATIVE,
        )
    assert hypothesis is not None
    assert hypothesis.status == HypothesisStatus.CANDIDATE
    assert hypothesis.o_lane_occurrence_count == 0
    assert hypothesis.a_lane_seed_count == 6


def test_single_miss_does_not_erase_active_hypothesis():
    engine = _engine_with_age()
    hypothesis = _observe_periodic(engine, period=10, count=4)
    assert hypothesis.status == HypothesisStatus.ACTIVE
    after_miss = engine.record_recurrence_miss(hypothesis.recurrence_id)
    assert after_miss.status == HypothesisStatus.ACTIVE
    assert after_miss.miss_count == 1
    assert after_miss.period_estimate == hypothesis.period_estimate


def test_fitted_phase_anchor_next_index_prediction_matches_formula():
    engine = _engine_with_age()
    hypothesis = _observe_periodic(engine, period=10, count=4, start=5)
    assert hypothesis.phase_anchor_stable is True
    assert hypothesis.phase_anchor_tick == pytest.approx(5.0)

    current_age = 27
    prediction = engine.predict_recurrence(
        hypothesis.recurrence_id,
        current_age=current_age,
    )
    assert prediction is not None
    expected_index = compute_next_index(
        hypothesis.phase_anchor_tick,
        hypothesis.period_estimate,
        current_age,
    )
    expected_center = hypothesis.phase_anchor_tick + expected_index * hypothesis.period_estimate
    assert prediction.next_index == expected_index
    assert prediction.predicted_center == pytest.approx(expected_center)
    assert prediction.phase_anchor_stable is True


def test_multiple_evidence_envelopes_for_one_occurrence_count_once():
    engine = _engine_with_age()
    recurrence_key = compute_recurrence_key(
        "habitat.feeder_cycle",
        "feeder:dedup",
        "d010.recurrence-context.v1",
    )
    recurrence_id = recurrence_id_from_key(recurrence_key)

    engine.observe_recurrence_occurrence(
        event_kind="habitat.feeder_cycle",
        internal_context_key="feeder:dedup",
        occurrence_id="occ:shared",
        evidence_identity="evidence:perception",
        tick=10,
        lane=EvidenceLane.ORGANISM_OBSERVABLE,
    )
    engine.observe_recurrence_occurrence(
        event_kind="habitat.feeder_cycle",
        internal_context_key="feeder:dedup",
        occurrence_id="occ:shared",
        evidence_identity="evidence:social",
        tick=10,
        lane=EvidenceLane.ORGANISM_OBSERVABLE,
    )
    hypothesis = engine.observe_recurrence_occurrence(
        event_kind="habitat.feeder_cycle",
        internal_context_key="feeder:dedup",
        occurrence_id="occ:second",
        evidence_identity="evidence:second",
        tick=20,
        lane=EvidenceLane.ORGANISM_OBSERVABLE,
    )
    assert hypothesis.observation_count == 2
    assert hypothesis.o_lane_occurrence_count == 2
    assert len(hypothesis.evidence_identities) == 3
    assert hypothesis.period_estimate == pytest.approx(10.0)

    reloaded = engine.predict_recurrence(recurrence_id, current_age=25)
    assert reloaded is not None
    assert reloaded.period_estimate == pytest.approx(10.0)


def test_mixed_lane_intervals_use_o_lane_only():
    engine = _engine_with_age()
    hypothesis: RecurrenceHypothesis | None = None
    for i in range(4):
        hypothesis = engine.observe_recurrence_occurrence(
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:mixed",
            occurrence_id=f"occ:a:{i}",
            evidence_identity=f"evidence:a:{i}",
            tick=i * 10,
            lane=EvidenceLane.AUTHORITATIVE,
        )
    for i in range(4):
        hypothesis = engine.observe_recurrence_occurrence(
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:mixed",
            occurrence_id=f"occ:o:{i}",
            evidence_identity=f"evidence:o:{i}",
            tick=5 + i * 10,
            lane=EvidenceLane.ORGANISM_OBSERVABLE,
        )
    assert hypothesis is not None
    assert hypothesis.o_lane_occurrence_count == 4
    assert hypothesis.a_lane_seed_count == 4
    assert hypothesis.period_estimate == pytest.approx(10.0)
    assert hypothesis.observation_count == 8


def test_authoritative_first_then_o_lane_upgrades_occurrence_credit():
    engine = _engine_with_age()
    hypothesis: RecurrenceHypothesis | None = None
    for i in range(3):
        hypothesis = engine.observe_recurrence_occurrence(
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:upgrade",
            occurrence_id=f"occ:{i}",
            evidence_identity=f"evidence:auth:{i}",
            tick=i * 10,
            lane=EvidenceLane.AUTHORITATIVE,
        )
        assert hypothesis is not None
        assert hypothesis.o_lane_occurrence_count == i
        assert hypothesis.a_lane_seed_count == 1
        hypothesis = engine.observe_recurrence_occurrence(
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:upgrade",
            occurrence_id=f"occ:{i}",
            evidence_identity=f"evidence:o:{i}",
            tick=i * 10,
            lane=EvidenceLane.ORGANISM_OBSERVABLE,
        )
        assert hypothesis is not None
        assert hypothesis.o_lane_occurrence_count == i + 1
        assert hypothesis.a_lane_seed_count == 0
    assert hypothesis is not None
    assert hypothesis.observation_count == 3
    assert hypothesis.status == HypothesisStatus.ACTIVE
    assert hypothesis.period_estimate == pytest.approx(10.0)


def test_unstable_phase_anchor_predicts_from_last_observed_plus_period():
    engine = _engine_with_age()
    hypothesis: RecurrenceHypothesis | None = None
    for i, tick in enumerate((0, 10)):
        hypothesis = engine.observe_recurrence_occurrence(
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:unstable",
            occurrence_id=f"occ:{i}",
            evidence_identity=f"evidence:{i}",
            tick=tick,
            lane=EvidenceLane.ORGANISM_OBSERVABLE,
        )
    assert hypothesis is not None
    assert hypothesis.phase_anchor_stable is False
    assert hypothesis.period_estimate == pytest.approx(10.0)
    assert hypothesis.last_observed_tick == 10

    prediction = engine.predict_recurrence(
        hypothesis.recurrence_id,
        current_age=25,
    )
    assert prediction is not None
    assert prediction.phase_anchor_stable is False
    assert prediction.predicted_center == pytest.approx(
        float(hypothesis.last_observed_tick) + hypothesis.period_estimate
    )


def _commit_in_tick_observation(
    engine: TemporalEngine,
    *,
    event_kind: str = "habitat.feeder_cycle",
    context_key: str = "feeder:plan",
    occurrence_id: str,
    evidence_identity: str,
    tick: int,
    txn_id: str = "txn:test",
) -> None:
    plan = engine.prepare_finalized_evidence(
        source_transaction_id=txn_id,
        event_kind=event_kind,
        internal_context_key=context_key,
        occurrence_id=occurrence_id,
        evidence_identity=evidence_identity,
        tick=tick,
    )
    engine.commit_observation_plan(plan)


def test_in_tick_commit_applies_hypothesis_delta_and_abandon_is_rollback_safe():
    engine = _engine_with_age()
    before = engine.state
    plan = engine.prepare_finalized_evidence(
        source_transaction_id="txn:a",
        event_kind="habitat.feeder_cycle",
        internal_context_key="feeder:rollback",
        occurrence_id="occ:0",
        evidence_identity="evidence:0",
        tick=0,
    )
    engine.abandon_observation_plan(plan.observation_plan_id)
    after = engine.state
    assert after is before
    assert after.recurrence_index == ()

    plan2 = engine.prepare_finalized_evidence(
        source_transaction_id="txn:b",
        event_kind="habitat.feeder_cycle",
        internal_context_key="feeder:rollback",
        occurrence_id="occ:0",
        evidence_identity="evidence:0",
        tick=0,
    )
    hypothesis = engine.commit_observation_plan(plan2)
    assert hypothesis.observation_count == 1
    assert hypothesis.o_lane_occurrence_count == 1


def test_same_observation_plan_cannot_commit_twice():
    engine = _engine_with_age()
    plan = engine.prepare_finalized_evidence(
        source_transaction_id="txn:dup",
        event_kind="habitat.feeder_cycle",
        internal_context_key="feeder:dup",
        occurrence_id="occ:0",
        evidence_identity="evidence:0",
        tick=0,
    )
    engine.commit_observation_plan(plan)
    with pytest.raises(TemporalEngineError, match="observation_plan_already_committed"):
        engine.commit_observation_plan(plan)


def test_post_hoc_missing_or_stale_anchors_fail_closed():
    engine = _engine_with_age()
    engine.register_post_hoc_anchor(
        source_event_id="evt:1",
        source_event_hash="hash:1",
        committed_advance_id=engine.state.last_advance_id,
        committed_age_ticks=0,
        committed_temporal_state_version=engine.state.state_version,
    )
    with pytest.raises(TemporalEngineError, match="post_hoc_source_anchor_missing"):
        engine.prepare_finalized_evidence(
            source_transaction_id="txn:post",
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:post",
            occurrence_id="occ:post",
            evidence_identity="evidence:post",
            tick=5,
            commit_mode=CommitMode.POST_HOC,
            source_event_id="evt:missing",
            source_event_hash="hash:missing",
            committed_advance_id=engine.state.last_advance_id,
            committed_age_ticks=5,
            committed_temporal_state_version=engine.state.state_version,
        )

    with pytest.raises(TemporalEngineError, match="post_hoc_source_event_hash_mismatch"):
        engine.prepare_finalized_evidence(
            source_transaction_id="txn:post",
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:post",
            occurrence_id="occ:post2",
            evidence_identity="evidence:post2",
            tick=5,
            commit_mode=CommitMode.POST_HOC,
            source_event_id="evt:1",
            source_event_hash="hash:stale",
            committed_advance_id=engine.state.last_advance_id,
            committed_age_ticks=5,
            committed_temporal_state_version=engine.state.state_version,
        )


def test_post_hoc_cannot_alter_historical_occurrence_age():
    engine = _engine_with_age()
    _commit_in_tick_observation(
        engine,
        context_key="feeder:immutable",
        occurrence_id="occ:fixed",
        evidence_identity="evidence:fixed",
        tick=10,
    )
    engine.register_post_hoc_anchor(
        source_event_id="evt:hist",
        source_event_hash="hash:hist",
        committed_advance_id=engine.state.last_advance_id,
        committed_age_ticks=99,
        committed_temporal_state_version=engine.state.state_version,
    )
    with pytest.raises(TemporalEngineError, match="post_hoc_occurrence_age_immutable"):
        engine.prepare_finalized_evidence(
            source_transaction_id="txn:rewrite",
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:immutable",
            occurrence_id="occ:fixed",
            evidence_identity="evidence:rewrite",
            tick=99,
            commit_mode=CommitMode.POST_HOC,
            source_event_id="evt:hist",
            source_event_hash="hash:hist",
            committed_advance_id=engine.state.last_advance_id,
            committed_age_ticks=99,
            committed_temporal_state_version=engine.state.state_version,
        )


def test_post_hoc_prepare_uses_committed_age_for_immutability():
    engine = _engine_with_age(age=50)
    _commit_in_tick_observation(
        engine,
        context_key="feeder:anchored",
        occurrence_id="occ:anchored",
        evidence_identity="evidence:anchored",
        tick=10,
    )
    engine.register_post_hoc_anchor(
        source_event_id="evt:anchored",
        source_event_hash="hash:anchored",
        committed_advance_id=engine.state.last_advance_id,
        committed_age_ticks=10,
        committed_temporal_state_version=engine.state.state_version,
    )
    plan = engine.prepare_finalized_evidence(
        source_transaction_id="txn:anchored",
        event_kind="habitat.feeder_cycle",
        internal_context_key="feeder:anchored",
        occurrence_id="occ:anchored",
        evidence_identity="evidence:post-hoc",
        tick=50,
        commit_mode=CommitMode.POST_HOC,
        source_event_id="evt:anchored",
        source_event_hash="hash:anchored",
        committed_advance_id=engine.state.last_advance_id,
        committed_age_ticks=10,
        committed_temporal_state_version=engine.state.state_version,
    )
    assert plan.hypothesis_deltas[0].tick == 10


def test_same_occurrence_id_across_in_tick_and_post_hoc_counts_once():
    engine = _engine_with_age()
    _commit_in_tick_observation(
        engine,
        context_key="feeder:cross",
        occurrence_id="occ:shared",
        evidence_identity="evidence:in-tick",
        tick=10,
        txn_id="txn:in",
    )
    before_count = engine.state.recurrence_index[0][1]["observation_count"]
    engine.register_post_hoc_anchor(
        source_event_id="evt:cross",
        source_event_hash="hash:cross",
        committed_advance_id=engine.state.last_advance_id,
        committed_age_ticks=10,
        committed_temporal_state_version=engine.state.state_version,
    )
    plan = engine.prepare_finalized_evidence(
        source_transaction_id="txn:post",
        event_kind="habitat.feeder_cycle",
        internal_context_key="feeder:cross",
        occurrence_id="occ:shared",
        evidence_identity="evidence:post-hoc",
        tick=10,
        commit_mode=CommitMode.POST_HOC,
        source_event_id="evt:cross",
        source_event_hash="hash:cross",
        committed_advance_id=engine.state.last_advance_id,
        committed_age_ticks=10,
        committed_temporal_state_version=engine.state.state_version,
    )
    hypothesis = engine.commit_observation_plan(plan)
    assert hypothesis.observation_count == before_count == 1
    assert len(hypothesis.evidence_identities) == 2


def test_observation_window_miss_is_idempotent_and_single_miss_keeps_active():
    engine = _engine_with_age()
    hypothesis = _observe_periodic(engine, period=10, count=4)
    assert hypothesis.status == HypothesisStatus.ACTIVE
    evidence = ObservationWindowEvidence(
        recurrence_id=hypothesis.recurrence_id,
        expectation_version=hypothesis.hypothesis_version,
        window_start=40.0,
        window_end=50.0,
        coverage_start=40.0,
        coverage_end=50.0,
        observability_quality=1.0,
        supporting_observation_refs=(),
        matched_occurrence_id=None,
    )
    first = engine.record_observation_window_miss(evidence)
    assert first is not None
    assert first.status == HypothesisStatus.ACTIVE
    assert first.miss_count == 1
    second = engine.record_observation_window_miss(evidence)
    assert second is not None
    assert second.miss_count == 1
    assert len(engine.state.observation_miss_keys) == 1


def test_partial_observation_coverage_does_not_register_miss():
    engine = _engine_with_age()
    hypothesis = _observe_periodic(engine, period=10, count=4)
    evidence = ObservationWindowEvidence(
        recurrence_id=hypothesis.recurrence_id,
        expectation_version=hypothesis.hypothesis_version,
        window_start=40.0,
        window_end=50.0,
        coverage_start=40.0,
        coverage_end=42.0,
        observability_quality=1.0,
        supporting_observation_refs=(),
        matched_occurrence_id=None,
    )
    result = engine.record_observation_window_miss(evidence)
    assert result is None
    assert engine.state.observation_miss_keys == ()


def test_dedup_eviction_does_not_allow_recount():
    summary = empty_dedup_summary()
    for index in range(MAX_RECENT_EVIDENCE_IDENTITIES + 2):
        summary = register_identities(
            summary,
            evidence_identities=(f"evidence:{index}",),
        )
    first_evicted = "evidence:0"
    assert first_evicted in summary.compacted_identities
    assert identity_seen(summary, evidence_identity=first_evicted)


def test_authoritative_prepare_seeds_candidate_only():
    engine = _engine_with_age()
    for index in range(6):
        plan = engine.prepare_authoritative_event(
            source_transaction_id=f"txn:auth:{index}",
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:auth-plan",
            occurrence_id=f"occ:{index}",
            evidence_identity=f"evidence:{index}",
            tick=index * 10,
        )
        hypothesis = engine.commit_observation_plan(plan)
    assert hypothesis.status == HypothesisStatus.CANDIDATE
    assert hypothesis.o_lane_occurrence_count == 0
    assert hypothesis.a_lane_seed_count == 6


def test_disallowed_event_and_evidence_kinds_rejected_by_allowlist():
    engine = _engine_with_age()
    with pytest.raises(TemporalEngineError, match="observable_evidence_disallowed"):
        engine.prepare_finalized_evidence(
            source_transaction_id="txn:bad",
            event_kind="forbidden.evidence.kind",
            internal_context_key="ctx",
            occurrence_id="occ:bad",
            evidence_identity="evidence:bad",
            tick=0,
        )
    with pytest.raises(TemporalEngineError, match="authoritative_event_disallowed"):
        engine.prepare_authoritative_event(
            source_transaction_id="txn:bad-auth",
            event_kind="forbidden.authoritative.kind",
            internal_context_key="ctx",
            occurrence_id="occ:bad-auth",
            evidence_identity="evidence:bad-auth",
            tick=0,
        )
    with pytest.raises(AllowlistError, match="observable_evidence_disallowed"):
        assert_observable_evidence_allowed("forbidden.evidence.kind")
