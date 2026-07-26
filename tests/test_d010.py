"""UMBRA-D-010 temporal continuity tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from umbra_core.arbitration import (
    ACTIVE_POSITIVE_CAP,
    Arbitrator,
    Candidate,
    UNCERTAIN_POSITIVE_CAP,
    active_fallback_biases,
    apply_temporal_modifiers,
    propose_wait_candidates,
)
from umbra_core.governance import Governance, Proposal, WaitAdmissionContext
from umbra_core.physiology import Physiology
from umbra_core.temporal.policy import PolicyExpectationView
from umbra_core.util import SeededRNG
from umbra_core.wait_execution import (
    FallbackBias,
    MAXIMUM_WAIT_TICKS,
    MAX_FALLBACK_BOUNDED_DELTA,
    WaitJournal,
    normalize_fallback_bias,
    wait_deadline_age_tick,
)
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


def _active_policy_view(
    *,
    recurrence_id: str = "rec:test",
    window_start: float = 40.0,
    window_end: float = 60.0,
    expectation_version: int = 1,
) -> PolicyExpectationView:
    return PolicyExpectationView(
        recurrence_id=recurrence_id,
        window_start=window_start,
        window_end=window_end,
        confidence=0.85,
        uncertainty=0.1,
        expected_context="habitat.feeder_cycle",
        expectation_version=expectation_version,
        status="ACTIVE",
    )


def _uncertain_policy_view(**kwargs) -> PolicyExpectationView:
    view = _active_policy_view(**kwargs)
    return replace(view, status="UNCERTAIN", confidence=0.4, uncertainty=0.5)


def test_policy_view_excludes_candidates_and_raw_authoritative_events():
    engine = _engine_with_age()
    for i in range(6):
        plan = engine.prepare_authoritative_event(
            source_transaction_id=f"txn:{i}",
            event_kind="habitat.feeder_cycle",
            internal_context_key="feeder:hidden",
            occurrence_id=f"occ:{i}",
            evidence_identity=f"evidence:{i}",
            tick=i * 10,
        )
        engine.commit_observation_plan(plan)
    _observe_periodic(engine, period=10, count=4, context_key="feeder:visible")
    views = engine.build_policy_expectation_views(current_age=35)
    statuses = {v.status for v in views}
    assert "CANDIDATE" not in statuses
    assert all(v.expected_context == "habitat.feeder_cycle" for v in views)
    assert all("feeder:" not in v.expected_context for v in views)


def test_active_view_applies_capped_modifier_uncertain_smaller_only():
    active = _active_policy_view()
    uncertain = _uncertain_policy_view()
    active_cand = Candidate("MOVE", {})
    uncertain_cand = Candidate("MOVE", {})
    apply_temporal_modifiers([active_cand], (active,), effective_age_ticks=45)
    apply_temporal_modifiers([uncertain_cand], (uncertain,), effective_age_ticks=45)
    assert 0.0 < active_cand.scores["temporal_modifier"] <= ACTIVE_POSITIVE_CAP
    assert 0.0 < uncertain_cand.scores["temporal_modifier"] <= UNCERTAIN_POSITIVE_CAP
    assert uncertain_cand.scores["temporal_modifier"] < active_cand.scores["temporal_modifier"]


def test_uncertain_expectation_cannot_generate_wait():
    views = (_uncertain_policy_view(),)
    cands = propose_wait_candidates(views, effective_age_ticks=45)
    assert cands == []


def test_wait_rejected_outside_open_window():
    gov = Governance()
    journal = WaitJournal()
    proposal = Proposal(
        proposal_id="prop:outside",
        capability="WAIT",
        params={
            "recurrence_id": "rec:test",
            "window_start": 40.0,
            "window_end": 60.0,
            "maximum_wait_ticks": MAXIMUM_WAIT_TICKS,
            "expectation_version": 1,
        },
    )
    decision = gov.admit(
        proposal,
        wait_context=WaitAdmissionContext(
            effective_age_ticks=30,
            expectation_status="ACTIVE",
            wait_journal=journal,
        ),
    )
    assert not decision.admitted
    assert decision.reason == "wait_outside_open_window"
    assert journal.active_execution() is None
    assert len(journal.suppressions) == 1


def test_wait_admitted_only_inside_window_with_bounded_deadline():
    gov = Governance()
    journal = WaitJournal()
    age = 45
    window_end = 60.0
    deadline = wait_deadline_age_tick(
        started_age_tick=age,
        window_end=window_end,
        maximum_wait_ticks=MAXIMUM_WAIT_TICKS,
    )
    proposal = Proposal(
        proposal_id="prop:inside",
        capability="WAIT",
        params={
            "recurrence_id": "rec:test",
            "window_start": 40.0,
            "window_end": window_end,
            "maximum_wait_ticks": MAXIMUM_WAIT_TICKS,
            "expectation_version": 1,
            "wait_deadline": deadline,
            "internal_context_key": "feeder:a",
            "expected_occurrence_id": "occ:expected",
        },
    )
    wait_context = WaitAdmissionContext(
        effective_age_ticks=age,
        expectation_status="ACTIVE",
        wait_journal=journal,
    )
    decision = gov.admit(proposal, wait_context=wait_context)
    assert decision.admitted
    outcome = gov.execute_and_verify(
        proposal,
        decision,
        embodiment=None,  # type: ignore[arg-type]
        rng=SeededRNG(1),
        wait_context=wait_context,
    )
    assert outcome is not None
    assert outcome.raw.get("execution_id") is not None
    active = journal.active_execution()
    assert active is not None
    assert active.deadline_age_tick == deadline == min(age + MAXIMUM_WAIT_TICKS, int(window_end))


def test_rollback_abandon_creates_no_active_wait_execution():
    journal = WaitJournal()
    prepared = journal.prepare_wait(
        recurrence_id="rec:test",
        expectation_version=1,
        window_start=40.0,
        window_end=60.0,
        started_age_tick=45,
        execution_id="exec:rollback",
    )
    journal.abandon_prepare(prepared.execution_id)
    assert journal.get_execution("exec:rollback") is None
    assert journal.active_execution() is None


def test_wait_execution_has_one_terminal_outcome_and_retry_returns_same():
    journal = WaitJournal()
    prepared = journal.prepare_wait(
        recurrence_id="rec:test",
        expectation_version=1,
        window_start=40.0,
        window_end=60.0,
        started_age_tick=45,
        execution_id="exec:terminal",
    )
    journal.admit_prepared(prepared.execution_id)
    first = journal.finalize("exec:terminal", "EXPIRED", terminal_reason="deadline")
    second = journal.finalize("exec:terminal", "INTERRUPTED", terminal_reason="retry")
    assert first.status == second.status == "EXPIRED"
    assert first.terminal_reason == "deadline"


def test_o_lane_occurrence_observed_a_lane_alone_cannot():
    journal = WaitJournal()
    prepared = journal.prepare_wait(
        recurrence_id="rec:test",
        expectation_version=1,
        window_start=40.0,
        window_end=60.0,
        started_age_tick=45,
        internal_context_key="feeder:a",
        expected_occurrence_id="occ:o",
        execution_id="exec:lane",
    )
    journal.admit_prepared(prepared.execution_id)
    unchanged = journal.try_complete_with_occurrence(
        "exec:lane",
        recurrence_id="rec:test",
        expectation_version=1,
        occurrence_id="occ:a",
        internal_context_key="feeder:a",
        observation_age_tick=50,
        lane=EvidenceLane.AUTHORITATIVE,
    )
    assert unchanged is not None
    assert unchanged.status == "ACTIVE"
    wrong_occurrence = journal.try_complete_with_occurrence(
        "exec:lane",
        recurrence_id="rec:test",
        expectation_version=1,
        occurrence_id="occ:wrong",
        internal_context_key="feeder:a",
        observation_age_tick=50,
        lane=EvidenceLane.ORGANISM_OBSERVABLE,
    )
    assert wrong_occurrence is not None
    assert wrong_occurrence.status == "ACTIVE"
    wrong_context = journal.try_complete_with_occurrence(
        "exec:lane",
        recurrence_id="rec:test",
        expectation_version=1,
        occurrence_id="occ:o",
        internal_context_key="feeder:other",
        observation_age_tick=50,
        lane=EvidenceLane.ORGANISM_OBSERVABLE,
    )
    assert wrong_context is not None
    assert wrong_context.status == "ACTIVE"
    completed = journal.try_complete_with_occurrence(
        "exec:lane",
        recurrence_id="rec:test",
        expectation_version=1,
        occurrence_id="occ:o",
        internal_context_key="feeder:a",
        observation_age_tick=50,
        lane=EvidenceLane.ORGANISM_OBSERVABLE,
    )
    assert completed is not None
    assert completed.status == "OCCURRENCE_OBSERVED"


def test_wait_anti_reentry_survives_restart_and_revised_expectation_may_bypass():
    journal = WaitJournal()
    journal.record_suppression(
        recurrence_id="rec:test",
        expectation_version=1,
        terminal_reason="governance_reject",
        suppressed_until_age_tick=55,
        governance_decision_id="dec:1",
    )
    state = journal.to_state()
    restored = WaitJournal.from_state(state)
    assert restored.is_suppressed("rec:test", 1, effective_age_ticks=50)
    assert not restored.is_suppressed("rec:test", 1, effective_age_ticks=56)
    assert restored.may_bypass_suppression("rec:test", 1, 2)
    assert not restored.is_suppressed("rec:test", 2, effective_age_ticks=50)


def test_governance_reject_creates_suppression_without_fake_wait_execution():
    gov = Governance()
    journal = WaitJournal()
    proposal = Proposal(
        proposal_id="prop:reject",
        capability="WAIT",
        params={
            "recurrence_id": "rec:test",
            "window_start": 40.0,
            "window_end": 60.0,
            "maximum_wait_ticks": MAXIMUM_WAIT_TICKS,
            "expectation_version": 1,
        },
    )
    decision = gov.admit(
        proposal,
        wait_context=WaitAdmissionContext(
            effective_age_ticks=20,
            expectation_status="ACTIVE",
            wait_journal=journal,
        ),
    )
    assert not decision.admitted
    assert journal.active_execution() is None
    assert len(journal.suppressions) == 1
    assert journal.suppressions[0].governance_decision_id == "prop:reject"


def test_temporal_miss_cannot_write_relationships_or_physiology():
    engine = _engine_with_age()
    phys_before = Physiology()
    hypothesis = _observe_periodic(engine, period=10, count=4)
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
    engine.record_observation_window_miss(evidence)
    phys_after = Physiology()
    assert phys_before.to_state() == phys_after.to_state()


def test_modifier_caps_apply_before_signed_cancellation():
    views = (
        _active_policy_view(recurrence_id="rec:a"),
        _active_policy_view(recurrence_id="rec:b"),
        _active_policy_view(recurrence_id="rec:c"),
    )
    cand = Candidate("MOVE", {})
    apply_temporal_modifiers([cand], views, effective_age_ticks=45)
    assert cand.scores["temporal_modifier"] <= 0.40


def test_physiology_urgency_outranks_temporal_modifiers():
    arb = Arbitrator()
    phys = Physiology()
    phys.energy = 0.05
    observations = [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 1.0}]
    views = (_active_policy_view(),)
    chosen = arb.select(
        phys,
        observations,
        tick=45,
        rng=SeededRNG(1),
        policy_expectations=views,
        effective_age_ticks=45,
    )
    assert chosen.capability in ("CHARGE", "APPROACH", "MOVE")


def test_waiting_is_bounded():
    journal = WaitJournal()
    prepared = journal.prepare_wait(
        recurrence_id="rec:test",
        expectation_version=1,
        window_start=40.0,
        window_end=44.0,
        started_age_tick=40,
        maximum_wait_ticks=20,
        execution_id="exec:bounded",
    )
    assert prepared.deadline_age_tick == 44


def test_fallback_bias_reenters_arbitration_and_expires():
    journal = WaitJournal()
    bias = FallbackBias(candidate_class="REST", bounded_delta=0.08, expires_after_ticks=3)
    prepared = journal.prepare_wait(
        recurrence_id="rec:test",
        expectation_version=1,
        window_start=40.0,
        window_end=60.0,
        started_age_tick=45,
        fallback_bias=bias,
        execution_id="exec:fallback",
    )
    journal.admit_prepared(prepared.execution_id)
    assert active_fallback_biases(journal, effective_age_ticks=46) == ()
    journal.finalize("exec:fallback", "EXPIRED")
    cand = Candidate("REST", {})
    apply_temporal_modifiers(
        [cand],
        (),
        effective_age_ticks=46,
        fallback_biases=active_fallback_biases(journal, effective_age_ticks=46),
    )
    assert cand.scores.get("fallback_bias", 0.0) == pytest.approx(0.08)
    expired_cand = Candidate("REST", {})
    apply_temporal_modifiers(
        [expired_cand],
        (),
        effective_age_ticks=50,
        fallback_biases=active_fallback_biases(journal, effective_age_ticks=50),
    )
    assert expired_cand.scores.get("fallback_bias", 0.0) == 0.0


def test_fallback_bias_bounded_delta_is_capped():
    oversized = FallbackBias(candidate_class="REST", bounded_delta=0.5, expires_after_ticks=3)
    capped = normalize_fallback_bias(oversized)
    assert capped is not None
    assert capped.bounded_delta == pytest.approx(MAX_FALLBACK_BOUNDED_DELTA)
    journal = WaitJournal()
    prepared = journal.prepare_wait(
        recurrence_id="rec:test",
        expectation_version=1,
        window_start=40.0,
        window_end=60.0,
        started_age_tick=45,
        fallback_bias=oversized,
        execution_id="exec:cap",
    )
    assert prepared.fallback_bias is not None
    assert prepared.fallback_bias.bounded_delta == pytest.approx(MAX_FALLBACK_BOUNDED_DELTA)


def test_hazard_urgency_outranks_temporal_modifiers():
    arb = Arbitrator()
    phys = Physiology()
    phys.integrity = 0.08
    observations = [
        {"kind": "hazard", "relative_direction": 0.0, "estimated_distance": 1.0},
    ]
    views = (_active_policy_view(),)
    chosen = arb.select(
        phys,
        observations,
        tick=45,
        rng=SeededRNG(1),
        policy_expectations=views,
        effective_age_ticks=45,
    )
    assert chosen.capability in ("RETREAT", "MOVE")


# --- Task 7: Memory temporal_binding + BoundRoutineEligibility ----------------


def _temporal_binding(**kwargs):
    from umbra_core.memory.engine import TemporalBinding

    defaults = {
        "recurrence_id": "rec:test",
        "minimum_confidence": 0.5,
        "eligibility_lead_ticks": 2,
        "eligibility_lag_ticks": 2,
        "maximum_start_delay": 10,
        "allowed_expectation_statuses": ("ACTIVE",),
    }
    defaults.update(kwargs)
    return TemporalBinding(**defaults)


def _promote_bound_environmental_routine(mem, *, binding=None, episode_ids=None):
    from umbra_core.memory import MemoryEngine, RoutineLifecycle
    from umbra_core.memory.engine import EnvironmentalRoutineSpec

    if binding is None:
        binding = _temporal_binding()
    if episode_ids is None:
        episode_ids = ["ep:1", "ep:2", "ep:3"]
    return mem.promote_environmental_routine(
        EnvironmentalRoutineSpec(
            object_kind="resource",
            affordance_ref="affordance:resource:use",
            zone_id="zone:general",
            soft_proposals=[],
            supporting_episode_ids=episode_ids,
            temporal_binding=binding,
        ),
        tick=5,
        lifecycle=RoutineLifecycle.ACTIVE.value,
    )


def test_temporal_binding_multi_episode_promote_eligible_under_active_expectation():
    from umbra_core.memory import MemoryEngine

    mem = MemoryEngine.create("agent:test")
    skill_id = _promote_bound_environmental_routine(mem)
    view = _active_policy_view(window_start=40.0, window_end=60.0, expectation_version=1)
    eligibility = mem.evaluate_bound_routine_eligibility(
        skill_id, view, current_age_tick=45
    )
    assert eligibility is not None
    assert eligibility.eligible
    assert eligibility.allows_activation
    assert eligibility.expectation_version == 1
    assert eligibility.evaluated_window_start == pytest.approx(38.0)
    assert eligibility.evaluated_window_end == pytest.approx(62.0)
    assert len(mem.temporal_routine_promote_events) == 1
    assert mem.temporal_routine_promote_events[0]["recurrence_id"] == "rec:test"


def test_temporal_binding_interruptible_no_timer_launch():
    from umbra_core.memory import MemoryEngine, RoutineLifecycle

    mem = MemoryEngine.create("agent:test")
    skill_id = _promote_bound_environmental_routine(mem)
    view = _active_policy_view()
    eligibility = mem.evaluate_bound_routine_eligibility(skill_id, view, current_age_tick=45)
    assert eligibility is not None and eligibility.eligible
    lifecycle = mem.update_environmental_routine_lifecycle(
        skill_id, success=False, interrupted=True, tick=46
    )
    assert lifecycle == RoutineLifecycle.WEAKENED.value
    proposals = mem.routine_soft_proposals(mem.procedural[skill_id], bindings=[])
    assert proposals == []
    assert not hasattr(mem, "launch_temporal_routine")


def test_temporal_binding_stale_expectation_version_blocked():
    from umbra_core.memory import MemoryEngine

    mem = MemoryEngine.create("agent:test")
    skill_id = _promote_bound_environmental_routine(mem)
    current = _active_policy_view(expectation_version=2)
    stale = _active_policy_view(expectation_version=1)
    mem.evaluate_bound_routine_eligibility(skill_id, current, current_age_tick=45)
    stale_eligibility = mem.evaluate_bound_routine_eligibility(
        skill_id, stale, current_age_tick=45
    )
    assert stale_eligibility is not None
    assert not stale_eligibility.eligible
    assert stale_eligibility.reason == "stale_expectation_version"


def test_temporal_binding_schedule_revision_updates_eligibility():
    from umbra_core.memory import MemoryEngine

    mem = MemoryEngine.create("agent:test")
    skill_id = _promote_bound_environmental_routine(mem)
    revised = _active_policy_view(expectation_version=2, window_start=50.0, window_end=70.0)
    eligibility = mem.evaluate_bound_routine_eligibility(
        skill_id, revised, current_age_tick=55
    )
    assert eligibility is not None
    assert eligibility.eligible
    assert eligibility.expectation_version == 2
    assert eligibility.evaluated_window_start == pytest.approx(48.0)


def test_temporal_binding_uncertain_no_activation_or_wait_chain():
    from umbra_core.memory import MemoryEngine

    mem = MemoryEngine.create("agent:test")
    binding = _temporal_binding(allowed_expectation_statuses=("ACTIVE", "UNCERTAIN"))
    skill_id = _promote_bound_environmental_routine(mem, binding=binding)
    view = _uncertain_policy_view()
    eligibility = mem.evaluate_bound_routine_eligibility(
        skill_id, view, current_age_tick=45
    )
    assert eligibility is not None
    assert eligibility.exploratory_only
    assert not eligibility.allows_activation
    assert not eligibility.allows_wait_chain


def test_temporal_binding_retired_recurrence_disables_binding_retains_provenance():
    from umbra_core.memory import MemoryEngine

    mem = MemoryEngine.create("agent:test")
    skill_id = _promote_bound_environmental_routine(mem)
    sk = mem.procedural[skill_id]
    mem.disable_temporal_binding_for_recurrence("rec:test", tick=10)
    binding = sk.applicability["temporal_binding"]
    assert binding["disabled"] is True
    assert binding["recurrence_id"] == "rec:test"
    assert len(sk.source_episode_ids) >= 3
    view = _active_policy_view()
    eligibility = mem.evaluate_bound_routine_eligibility(
        skill_id, view, current_age_tick=45
    )
    assert eligibility is not None
    assert not eligibility.eligible
    assert eligibility.reason == "recurrence_retired"


def test_temporal_binding_miss_weakens_binding_not_physiology():
    from umbra_core.memory import MemoryEngine
    from umbra_core.physiology import Physiology

    mem = MemoryEngine.create("agent:test")
    phys = Physiology()
    before_energy = phys.energy
    skill_id = _promote_bound_environmental_routine(mem)
    binding_before = mem.procedural[skill_id].applicability["temporal_binding"]["strength"]
    mem.record_temporal_binding_miss(skill_id, tick=20)
    binding_after = mem.procedural[skill_id].applicability["temporal_binding"]["strength"]
    assert binding_after < binding_before
    assert phys.energy == before_energy
    with pytest.raises(RuntimeError, match="memory_cannot_modify_physiology"):
        mem.apply_memory_to_physiology(phys)


def test_temporal_binding_repromote_attaches_binding_to_existing_skill():
    from umbra_core.memory import MemoryEngine, RoutineLifecycle
    from umbra_core.memory.engine import EnvironmentalRoutineSpec

    mem = MemoryEngine.create("agent:test")
    episode_ids = ["ep:1", "ep:2", "ep:3"]
    skill_id = mem.promote_environmental_routine(
        EnvironmentalRoutineSpec(
            object_kind="resource",
            affordance_ref="affordance:resource:use",
            zone_id="zone:general",
            soft_proposals=[],
            supporting_episode_ids=episode_ids,
        ),
        tick=1,
        lifecycle=RoutineLifecycle.ACTIVE.value,
    )
    assert "temporal_binding" not in mem.procedural[skill_id].applicability

    binding = _temporal_binding()
    same_id = mem.promote_environmental_routine(
        EnvironmentalRoutineSpec(
            object_kind="resource",
            affordance_ref="affordance:resource:use",
            zone_id="zone:general",
            soft_proposals=[],
            supporting_episode_ids=episode_ids,
            temporal_binding=binding,
        ),
        tick=5,
        lifecycle=RoutineLifecycle.ACTIVE.value,
    )
    assert same_id == skill_id
    sk = mem.procedural[skill_id]
    assert sk.applicability["temporal_binding"]["recurrence_id"] == "rec:test"
    assert sk.source_episode_ids == episode_ids
    assert len(mem.temporal_routine_promote_events) == 1


def test_temporal_binding_repromote_updates_binding_preserves_runtime_state():
    from umbra_core.memory import MemoryEngine, RoutineLifecycle
    from umbra_core.memory.engine import EnvironmentalRoutineSpec

    mem = MemoryEngine.create("agent:test")
    episode_ids = ["ep:1", "ep:2", "ep:3"]
    skill_id = _promote_bound_environmental_routine(mem)
    mem.procedural[skill_id].applicability["temporal_binding"]["strength"] = 0.6
    mem.evaluate_bound_routine_eligibility(
        skill_id, _active_policy_view(expectation_version=1), current_age_tick=45
    )

    updated = _temporal_binding(maximum_start_delay=20, eligibility_lead_ticks=5)
    mem.promote_environmental_routine(
        EnvironmentalRoutineSpec(
            object_kind="resource",
            affordance_ref="affordance:resource:use",
            zone_id="zone:general",
            soft_proposals=[],
            supporting_episode_ids=episode_ids,
            temporal_binding=updated,
        ),
        tick=10,
        lifecycle=RoutineLifecycle.ACTIVE.value,
    )
    binding = mem.procedural[skill_id].applicability["temporal_binding"]
    assert binding["maximum_start_delay"] == 20
    assert binding["eligibility_lead_ticks"] == 5
    assert binding["strength"] == 0.6
    assert binding["last_bound_expectation_version"] == 1
    assert len(mem.temporal_routine_promote_events) == 2


def test_temporal_binding_maximum_start_delay_exceeded():
    from umbra_core.memory import MemoryEngine

    mem = MemoryEngine.create("agent:test")
    binding = _temporal_binding(maximum_start_delay=5)
    skill_id = _promote_bound_environmental_routine(mem, binding=binding)
    view = _active_policy_view(window_start=40.0, window_end=60.0)
    eligibility = mem.evaluate_bound_routine_eligibility(
        skill_id, view, current_age_tick=46
    )
    assert eligibility is not None
    assert not eligibility.eligible
    assert eligibility.reason == "maximum_start_delay_exceeded"


# --- Task 8: downtime reconciliation + elapsed contracts ---


def _trusted_wall_anchor(
    *,
    wall_time: float = 1000.0,
    age: int = 10,
    session_id: str = "session:prior",
) -> TimeAnchor:
    from umbra_core.temporal.state import with_anchor_state_hash

    anchor = TimeAnchor(
        organism_age_ticks=age,
        organism_active_ticks=age,
        state_version=1,
        state_hash="",
        wall_time=wall_time,
        wall_time_source="runtime.wall_time_fn",
        wall_time_uncertainty=0.0,
        session_id_at_commit=session_id,
        advance_id="advance:prior",
        anchor_trust_class=AnchorTrustClass.TRUSTED_SHORT,
        trust_reason_codes=("trusted_short_gap",),
        eligible_as_downtime_baseline=True,
        source_sample_hash="abc123",
    )
    return with_anchor_state_hash(anchor)


def _engine_with_trusted_anchor(*, age: int = 10) -> TemporalEngine:
    state = sample_temporal_state()
    anchor = _trusted_wall_anchor(age=age)
    state = with_state_hash(
        replace(
            state,
            organism_age_ticks=age,
            organism_active_ticks=age,
            last_time_anchor=anchor,
            state_version=2,
        )
    )
    return TemporalEngine(state)


def _wall_sample(
    *,
    wall_time: float,
    session_id: str = "session:restart",
    uncertainty: float = 0.0,
    source: str = "runtime.wall_time_fn",
) -> TrustedSample:
    return TrustedSample(
        session_id=session_id,
        monotonic_ns=9_000_000,
        optional_wall_time=wall_time,
        wall_time_source=source,
        wall_time_uncertainty=uncertainty,
        sample_sequence=1,
    )


def test_trusted_short_downtime_advances_age():
    from umbra_core.temporal.downtime import SECONDS_PER_AGE_TICK

    engine = _engine_with_trusted_anchor(age=10)
    elapsed = 120.0
    sample = _wall_sample(wall_time=1000.0 + elapsed)
    plan = engine.reconcile_downtime(sample, session_id="session:restart")
    assert plan.trust_class == AnchorTrustClass.TRUSTED_SHORT
    assert plan.age_advance == int(elapsed / SECONDS_PER_AGE_TICK)
    assert plan.next_age_ticks == 10 + plan.age_advance
    assert plan.conservative is False


def test_uncertain_downtime_has_zero_age_advance():
    engine = _engine_with_trusted_anchor(age=5)
    sample = _wall_sample(wall_time=1000.0, uncertainty=2.0)
    plan = engine.reconcile_downtime(sample, session_id="session:restart")
    assert plan.age_advance == 0
    assert plan.next_age_ticks == 5
    assert plan.conservative is True


def test_conservative_anchor_not_eligible_as_downtime_baseline():
    engine = _engine_with_trusted_anchor(age=3)
    sample = _wall_sample(wall_time=1060.0, uncertainty=2.0)
    plan = engine.reconcile_downtime(sample, session_id="session:restart")
    result = engine.commit_downtime_reconciliation(plan, sample, transaction_id="txn:1")
    assert result.new_state.last_time_anchor.eligible_as_downtime_baseline is False


def test_downtime_reconciliation_commits_new_session_anchor():
    engine = _engine_with_trusted_anchor(age=4)
    sample = _wall_sample(wall_time=1120.0, session_id="session:new")
    plan = engine.reconcile_downtime(sample, session_id="session:new")
    result = engine.commit_downtime_reconciliation(plan, sample, transaction_id="txn:2")
    anchor = result.new_state.last_time_anchor
    assert anchor.session_id_at_commit == "session:new"
    assert anchor.advance_id.startswith("reconcile:")


def test_same_downtime_interval_idempotent_retry():
    engine = _engine_with_trusted_anchor(age=6)
    sample = _wall_sample(wall_time=1180.0)
    plan1 = engine.reconcile_downtime(sample, session_id="session:restart")
    plan2 = engine.reconcile_downtime(sample, session_id="session:restart")
    assert plan2.downtime_interval_id == plan1.downtime_interval_id
    assert plan2.canonical_plan_hash == plan1.canonical_plan_hash
    result1 = engine.commit_downtime_reconciliation(plan1, sample, transaction_id="txn:3")
    result2 = engine.commit_downtime_reconciliation(plan1, sample, transaction_id="txn:3b")
    assert result2.new_state.organism_age_ticks == result1.new_state.organism_age_ticks


def test_same_downtime_interval_payload_mismatch_fails_closed():
    from umbra_core.temporal.downtime import DowntimeReconciliationError

    engine = _engine_with_trusted_anchor(age=6)
    sample = _wall_sample(wall_time=1180.0)
    plan = engine.reconcile_downtime(sample, session_id="session:restart")
    tampered = replace(
        plan,
        age_advance=plan.age_advance + 1,
        next_age_ticks=plan.next_age_ticks + 1,
    )
    with pytest.raises(DowntimeReconciliationError, match="RECONCILIATION_PAYLOAD_MISMATCH"):
        engine.commit_downtime_reconciliation(tampered, sample, transaction_id="txn:bad")


def test_prepared_reconciliation_sample_is_sticky():
    engine = _engine_with_trusted_anchor(age=8)
    sample1 = _wall_sample(wall_time=1300.0, session_id="session:restart")
    plan1 = engine.reconcile_downtime(sample1, session_id="session:restart")
    engine.abandon_downtime_reconciliation(plan1.reconciliation_id)
    sample2 = _wall_sample(wall_time=1400.0, session_id="session:restart")
    plan2 = engine.reconcile_downtime(sample2, session_id="session:restart")
    assert plan2.trusted_sample_hash == plan1.trusted_sample_hash
    assert plan2.elapsed_seconds == plan1.elapsed_seconds


def test_required_contract_failure_replans_conservatively():
    engine = _engine_with_trusted_anchor(age=12)
    sample = _wall_sample(wall_time=1120.0)
    plan = engine.reconcile_downtime(
        sample,
        session_id="session:restart",
        subsystem_snapshots={"physiology": None},  # type: ignore[arg-type]
    )
    assert plan.conservative is True
    assert plan.age_advance == 0


def test_wait_recovery_delta_resolves_active_waits():
    from umbra_core.wait_execution import WaitJournal, apply_wait_recovery_deltas

    journal = WaitJournal()
    prepared = journal.prepare_wait(
        recurrence_id="rec:test",
        expectation_version=1,
        window_start=0.0,
        window_end=20.0,
        started_age_tick=5,
        execution_id="wait:1",
    )
    journal.admit_prepared(prepared.execution_id)
    engine = _engine_with_trusted_anchor(age=5)
    sample = _wall_sample(wall_time=1600.0)
    plan = engine.reconcile_downtime(sample, session_id="session:restart", wait_journal=journal)
    assert plan.wait_recovery_deltas
    updated = apply_wait_recovery_deltas(journal, plan.wait_recovery_deltas)
    assert updated.get_execution("wait:1").status == "EXPIRED"


def test_failed_reconciliation_leaves_waits_unchanged():
    from umbra_core.wait_execution import WaitJournal

    engine = _engine_with_trusted_anchor(age=5)
    journal = WaitJournal()
    prepared = journal.prepare_wait(
        recurrence_id="rec:test",
        expectation_version=1,
        window_start=0.0,
        window_end=100.0,
        started_age_tick=5,
        execution_id="wait:2",
    )
    journal.admit_prepared(prepared.execution_id)
    sample = _wall_sample(wall_time=1060.0)
    plan = engine.reconcile_downtime(sample, session_id="session:restart", wait_journal=journal)
    engine.abandon_downtime_reconciliation(plan.reconciliation_id)
    assert journal.get_execution("wait:2").status == "ACTIVE"


def test_replay_uses_recorded_downtime_deltas():
    from umbra_core.temporal.events import (
        TEMPORAL_DOWNTIME_RECONCILED,
        apply_downtime_reconciled_record,
        build_downtime_reconciled_record,
        downtime_reconciled_record_from_dict,
        downtime_reconciled_record_to_dict,
        replay_temporal_state_from_events,
    )

    engine = _engine_with_trusted_anchor(age=7)
    prior_state = engine.state
    sample = _wall_sample(wall_time=1420.0)
    plan = engine.reconcile_downtime(sample, session_id="session:restart")
    result = engine.commit_downtime_reconciliation(plan, sample, transaction_id="txn:replay")
    record = build_downtime_reconciled_record(prior_state, result.new_state, plan)
    replayed = apply_downtime_reconciled_record(prior_state, record)
    assert replayed.organism_age_ticks == result.new_state.organism_age_ticks
    assert replayed.last_time_anchor.session_id_at_commit == "session:restart"

    events = [
        {
            "event_type": TEMPORAL_DOWNTIME_RECONCILED,
            "payload": {
                "downtime_reconciled_record": downtime_reconciled_record_to_dict(record),
            },
        }
    ]
    from_events = replay_temporal_state_from_events(prior_state, events, require_advance_record=False)
    assert from_events.organism_age_ticks == result.new_state.organism_age_ticks


def test_replay_does_not_read_wall_clock():
    from umbra_core.temporal.events import (
        apply_downtime_reconciled_record,
        downtime_reconciled_record_to_dict,
        build_downtime_reconciled_record,
    )

    prior = _trusted_wall_anchor(age=3)
    new_anchor = _trusted_wall_anchor(age=3, wall_time=99999.0)
    state = with_state_hash(
        replace(
            sample_temporal_state(),
            organism_age_ticks=3,
            organism_active_ticks=3,
            state_version=2,
            state_hash="prior",
            last_time_anchor=prior,
        )
    )
    new_state = with_state_hash(
        replace(
            state,
            organism_age_ticks=3,
            last_time_anchor=new_anchor,
            state_version=3,
        )
    )
    from umbra_core.temporal.downtime import DowntimeReconciliationPlan

    plan = DowntimeReconciliationPlan(
        downtime_interval_id="downtime:test",
        reconciliation_id="rec:test",
        canonical_plan_hash="hash",
        expected_state_version=2,
        expected_state_hash="prior",
        session_id="session:restart",
        trusted_sample_hash="sample",
        trust_class=AnchorTrustClass.UNCERTAIN,
        trust_reason_codes=("conservative",),
        elapsed_seconds=0.0,
        age_advance=0,
        fractional_remainder=0.0,
        prior_age_ticks=3,
        next_age_ticks=3,
        prior_active_ticks=3,
        next_active_ticks=3,
        prior_time_anchor=prior,
        new_time_anchor=new_anchor,
        registry_hash="reg",
        effect_plan_ids=(),
        effect_plan_hashes=(),
        skipped_contract_ids=(),
        expectation_recovery_deltas=(),
        wait_recovery_deltas=(),
        conservative=True,
    )
    record = build_downtime_reconciled_record(state, new_state, plan)
    replayed = apply_downtime_reconciled_record(state, record)
    assert replayed.organism_age_ticks == 3
    assert record.trust_class == "UNCERTAIN"
    assert record.age_advance == 0


def test_stale_wall_sample_fails_trust_classification():
    from umbra_core.temporal.downtime import SAMPLE_FRESHNESS_SECONDS
    from umbra_core.temporal.state import WallClockMapping, with_state_hash

    engine = _engine_with_trusted_anchor(age=10)
    mapping = WallClockMapping(
        schema_version="d010.wall-mapping.v1",
        session_id="session:prior",
        monotonic_ns_at_mapping=9_000_000,
        wall_time_seconds=1000.0,
        wall_time_source="runtime.wall_time_fn",
        uncertainty=0.0,
    )
    engine._state = with_state_hash(replace(engine.state, wall_clock_mapping=mapping))
    stale_wall = 1000.0 + SAMPLE_FRESHNESS_SECONDS + 10.0
    sample = _wall_sample(wall_time=stale_wall)
    plan = engine.reconcile_downtime(sample, session_id="session:restart")
    assert plan.trust_class == AnchorTrustClass.UNCERTAIN
    assert "sample_not_fresh" in plan.trust_reason_codes


def test_no_downtime_derived_occurrence_or_miss():
    engine = _engine_with_trusted_anchor(age=9)
    sample = _wall_sample(wall_time=1540.0)
    plan = engine.reconcile_downtime(sample, session_id="session:restart")
    for delta in plan.expectation_recovery_deltas:
        assert delta.action in {"EXPIRE", "INVALIDATE", "DECAY_CONFIDENCE", "PRESERVE"}
    assert not any("occurrence" in d.action.lower() for d in plan.expectation_recovery_deltas)
    assert not any("miss" in d.action.lower() for d in plan.expectation_recovery_deltas)


def test_all_production_runtime_tick_uses_are_classified():
    from experiments.d010.scan_runtime_tick_uses import validate_inventory

    errors = validate_inventory()
    assert errors == [], "\n".join(errors)


def test_runtime_subsystem_uses_effective_organism_age_not_orchestration_tick(
    tmp_path, monkeypatch
):
    """Migrated T site: social.recognize receives TickTemporalContext effective age."""
    org = _temporal_org(tmp_path, social_enabled=True)
    captured: list[int] = []
    original = org.social.recognize

    def capture(cues, tick, *, store):
        captured.append(int(tick))
        return original(cues, tick, store=store)

    monkeypatch.setattr(org.social, "recognize", capture)

    def fake_context(plan):
        base = build_tick_temporal_context(plan)
        return replace(base, effective_age_ticks=42)

    monkeypatch.setattr("umbra_core.runtime.build_tick_temporal_context", fake_context)
    org.tick_once()
    assert captured == [42]
    assert org.tick == 1


# --- Task 10: conditions C0–C13 + scenarios S0–S17 scaffolding ---


@pytest.mark.parametrize("ablation", ["C1", "C4", "C5", "C6", "C8", "C11"])
def test_harness_integrated_ablations_create_organism_and_tick(tmp_path, ablation):
    from experiments.d010.conditions import condition_to_temporal_config
    from experiments.d010.run_experiment import _organism_cfg
    from umbra_core.runtime import create_organism

    db = tmp_path / f"{ablation}.db"
    org = create_organism(_organism_cfg(str(db), seed=50001, condition=ablation, scenario="S0"))
    try:
        assert org.config.condition == "C0"
        if ablation == "C1":
            assert org.temporal is None
        else:
            assert org.temporal is not None
            expected = condition_to_temporal_config(ablation)
            assert org._temporal_cfg == expected
        org.tick_once()
    finally:
        org.close()


def test_experimental_controls_are_production_unreachable(tmp_path):
    from experiments.d010.conditions import (
        TemporalConditionError,
        condition_to_temporal_config,
    )
    from umbra_core.runtime import OrganismConfig, create_organism
    from umbra_core.temporal.config import TemporalConfigError

    for condition in [f"C{i}" for i in range(1, 14)]:
        with pytest.raises(TemporalConfigError):
            create_organism(
                OrganismConfig(
                    db_path=str(tmp_path / f"{condition}.sqlite"),
                    condition=condition,
                    temporal_enabled=True,
                )
            )
    for diagnostic in ("C2", "C3", "C7", "C9", "C10", "C12"):
        with pytest.raises(TemporalConditionError):
            condition_to_temporal_config(diagnostic)
    assert condition_to_temporal_config("C0") == condition_to_temporal_config("C0")
    c13 = condition_to_temporal_config("C13")
    assert c13.p0_performance_mode is True
    assert c13.anticipation_enabled is False


@pytest.mark.parametrize("condition", ["C2", "C3", "C7", "C9", "C10", "C12"])
def test_condition_to_temporal_config_rejects_diagnostic_only_conditions(condition):
    from experiments.d010.conditions import TemporalConditionError, condition_to_temporal_config

    with pytest.raises(TemporalConditionError):
        condition_to_temporal_config(condition)


def test_c8_disposable_db_guard_accepts_tmp_and_scratch_paths(tmp_path):
    from pathlib import Path

    from experiments.d010.diagnostic_controllers import assert_disposable_db_path

    root = Path(__file__).resolve().parents[1]
    assert_disposable_db_path(tmp_path / "c8_scratch.sqlite")
    assert_disposable_db_path(root / "experiments" / "d010" / "c8_scratch.sqlite")


def test_c8_disposable_db_guard_rejects_production_paths():
    from pathlib import Path

    from experiments.d010.diagnostic_controllers import assert_disposable_db_path

    root = Path(__file__).resolve().parents[1]
    for bad in (
        root / "docs" / "evidence" / "d010" / "organism.sqlite",
        root / ".agent" / "organism.sqlite",
        root / "umbra_core" / "organism.sqlite",
    ):
        with pytest.raises(ValueError):
            assert_disposable_db_path(bad)


def test_control_rows_cannot_enter_c0_summaries():
    from experiments.d010.control_rows import (
        assert_row_may_enter_c0_summary,
        label_experiment_row,
        rows_eligible_for_c0_summary,
    )

    rows = [
        {"condition": "C0", "seed": 1, "metric": 0.9},
        label_experiment_row({"condition": "C5", "seed": 2, "metric": 0.1}),
        {"condition": "C0", "seed": 3, "control_row": True, "metric": 0.5},
    ]
    eligible = rows_eligible_for_c0_summary(rows)
    assert eligible == [{"condition": "C0", "seed": 1, "metric": 0.9}]
    with pytest.raises(ValueError, match="control_row_cannot_enter_c0_summary"):
        assert_row_may_enter_c0_summary(rows[1])
    with pytest.raises(ValueError, match="control_row_cannot_enter_c0_summary"):
        assert_row_may_enter_c0_summary(rows[2])


def test_c13_p0_mode_disables_anticipation_and_temporal_routine_eligibility(tmp_path):
    from experiments.d010.conditions import condition_to_temporal_config
    from umbra_core.runtime import OrganismConfig, create_organism
    from umbra_core.temporal.config import p0_performance_config
    from umbra_core.temporal.policy import PolicyExpectationView

    cfg = p0_performance_config()
    assert cfg == condition_to_temporal_config("C13")
    org = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "p0.sqlite"),
            temporal_enabled=True,
            temporal_config=cfg,
            memory_enabled=True,
            condition="C0",
        )
    )
    assert org.temporal is not None
    assert org._temporal_cfg.p0_performance_mode is True
    wait_on, modifiers_on = org._arbitration_temporal_flags()
    assert wait_on is False
    assert modifiers_on is False
    view = PolicyExpectationView(
        recurrence_id="rec:test",
        window_start=1.0,
        window_end=5.0,
        confidence=0.9,
        uncertainty=0.1,
        expected_context="resource",
        expectation_version=1,
        status="ACTIVE",
    )
    assert org._policy_expectation_views(organism_age=3) is None
    assert (
        org._temporal_routine_proposals((view,), organism_age=3, bindings=[]) == []
    )
    org.close()


def test_scenario_plants_change_timing_opportunity_only():
    from experiments.d010.scenario_plants import (
        apply_scenario_plants,
        assert_timing_opportunity_only_plant,
        plants_for_scenario,
        scenario_ids,
    )

    assert scenario_ids() == tuple(f"S{i}" for i in range(18))
    assert apply_scenario_plants(None, "S1", tick=60) == 1
    assert apply_scenario_plants(None, "S10", tick=40) == 1
    for scenario_id in scenario_ids():
        for plant in plants_for_scenario(scenario_id):
            assert_timing_opportunity_only_plant(plant)


def test_scripted_future_schedule_is_isolated_diagnostic():
    from experiments.d010.diagnostic_controllers import (
        RandomWaitInjectionController,
        ScriptedFutureScheduleController,
        assert_not_production_schema,
    )
    from experiments.d010.conditions import TemporalConditionError, condition_to_temporal_config

    with pytest.raises(TemporalConditionError):
        condition_to_temporal_config("C2")
    scripted = ScriptedFutureScheduleController()
    assert scripted.entries_for_tick(10)[0]["source"] == "SCRIPTED_DIAGNOSTIC"
    assert_not_production_schema(scripted)
    random_wait = RandomWaitInjectionController(seed=11)
    first = random_wait.sample_wait_params(1)
    second = random_wait.sample_wait_params(2)
    assert first["source"] == "RANDOM_DIAGNOSTIC"
    assert first["recurrence_id"] != second["recurrence_id"]


def test_wait_governance_bypass_rejected():
    from experiments.d010.governance_bypass import attempt_wait_governance_bypass

    outcomes = attempt_wait_governance_bypass(tick=1)
    assert outcomes
    assert all(not row["admitted"] for row in outcomes)


def test_hostile_temporal_clock_rejected():
    from experiments.d010.hostile_temporal_view import HostileTemporalClockView
    from umbra_core.temporal.migration import TemporalMigrationContext, initialize_temporal_epoch

    ctx = TemporalMigrationContext(
        migration_id="d010.genesis.v1",
        source_commit="af35371",
        source_seal="UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED",
        pre_temporal_history_ref="event-log:pre-d010",
        genesis_session_id="session:hostile",
        genesis_monotonic_ns=1_000_000,
        genesis_sample_sequence=0,
    )
    engine = __import__(
        "umbra_core.temporal.engine", fromlist=["TemporalEngine"]
    ).TemporalEngine(initialize_temporal_epoch(None, ctx=ctx))
    hostile = HostileTemporalClockView()
    hostile.attempt_ui_clock_as_truth(engine)
    assert hostile.attempted_writes
    assert hostile.successful_writes == []


def test_temporal_control_code_not_imported_by_umbra_core_temporal():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "umbra_core" / "temporal"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            for module in modules:
                assert not module.startswith("experiments.d010"), (
                    f"{path} imports experiments.d010: {module}"
                )


ROOT = Path(__file__).resolve().parents[1]


def test_development_formal_seed_manifests_disjoint():
    from experiments.d010.stage_a import validate_seed_nonoverlap

    validate_seed_nonoverlap()


def test_test_manifest_enumerates_required_tests():
    from experiments.d010.stage_a import collect_pytest_test_ids, load_test_manifest, required_test_ids

    manifest = load_test_manifest()
    present = collect_pytest_test_ids()
    missing = set(required_test_ids(manifest)) - present
    assert not missing, sorted(missing)[:5]


def test_stage_a_hashes_have_no_placeholders():
    from experiments.d010.stage_a import assert_no_placeholder_hashes, compute_stage_a_hashes

    hashes = compute_stage_a_hashes()
    assert_no_placeholder_hashes(hashes)
    payload = json.loads((ROOT / "experiments/d010/stage-a-hashes.json").read_text(encoding="utf-8"))
    assert payload.get("bundle_hash")
    assert "PLACEHOLDER" not in json.dumps(payload)


def test_adaptive_performance_protocol_contract():
    thr = json.loads((ROOT / "experiments/d010/thresholds.json").read_text(encoding="utf-8"))
    proto = json.loads((ROOT / "experiments/d010/performance-protocol.json").read_text(encoding="utf-8"))
    assert thr["rss_p95_mib_max"] == 180
    assert thr["ticks_accelerated_min"] >= 100000
    assert proto["supplement"] == "S3"
    assert int(proto["initial_measurement_seconds"]) >= 1800
    if thr.get("frozen_before_execution"):
        assert thr.get("threshold_freeze_timestamp")
        assert thr.get("allowed_verdicts")
        contract = json.loads(
            (ROOT / "experiments/d010/formal-execution-contract.json").read_text(encoding="utf-8")
        )
        assert contract.get("frozen_before_execution") is True
        assert contract.get("freeze_bundle_hash")
        assert contract.get("implementation_source_hash")
        assert "freeze_commit" not in contract
    perf = ROOT / "docs/evidence/d010/performance-results.json"
    if perf.exists():
        data = json.loads(perf.read_text(encoding="utf-8"))
        assert data.get("adaptive_soak_supplement") == "S3"


def test_d010_harness_runners_smoke():
    import subprocess
    import sys

    runners = [
        [sys.executable, "experiments/d010/run_experiment.py", "--dry-run"],
        [sys.executable, "experiments/d010/run_performance.py", "--dry-run"],
    ]
    for cmd in runners:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr[-500:]
    import experiments.d010.run_seal as seal_mod

    assert callable(seal_mod.main)


def test_aggregate_gates_0_through_12_no_paired_length_mismatch():
    from experiments.d010.run_experiment import _aggregate_gate

    conditions = [f"C{i}" for i in range(14)]
    scenarios = [f"S{i}" for i in range(18)]
    metric_keys = [
        "temporal_authority_alignment",
        "recurrence_learning_signal",
        "future_leakage_detection",
        "anticipation_coverage",
        "revision_adaptation",
        "temporal_routine_promotion",
        "autonomous_action_coverage",
        "absence_safety_violation",
        "individuality_timing_separation",
        "restart_age_continuity",
        "replay_equivalence",
        "boundedness_ok",
    ]
    synthetic: list[dict] = []
    for seed in range(50001, 50101):
        for cond in conditions:
            for scen in scenarios:
                synthetic.append(
                    {
                        "condition": cond,
                        "scenario": scen,
                        "seed": seed,
                        "metrics": {k: float((seed + hash(cond) + hash(scen)) % 7) / 10.0 for k in metric_keys},
                        "terminal_outcome": "synthetic",
                    }
                )
    for gate in range(0, 13):
        payload = _aggregate_gate(gate, synthetic, commit="synthetic")
        assert "comparisons" in payload
        for comp in payload["comparisons"]:
            assert comp["paired_seed_count"] == comp.get("paired_seed_count")


def test_s1_integrated_c0_recurrence_learning_signal_positive(tmp_path):
    from experiments.d010.run_experiment import _run_integrated_trace

    raw = _run_integrated_trace("C0", "S1", 50001, str(tmp_path))
    signal = float(raw["metrics"]["recurrence_learning_signal"])
    assert signal > 0.0


def test_s1_integrated_c11_recurrence_weaker_than_c0(tmp_path):
    from experiments.d010.run_experiment import _run_integrated_trace

    c0 = _run_integrated_trace("C0", "S1", 50001, str(tmp_path / "c0"))
    c11 = _run_integrated_trace("C11", "S1", 50001, str(tmp_path / "c11"))
    assert float(c0["metrics"]["recurrence_learning_signal"]) > float(
        c11["metrics"]["recurrence_learning_signal"]
    )


def test_gate6_c0_s7_promotion_count_meets_threshold(tmp_path):
    from experiments.d010.run_experiment import _run_integrated_trace

    thr = json.loads((ROOT / "experiments/d010/thresholds.json").read_text(encoding="utf-8"))
    raw = _run_integrated_trace("C0", "S7", 50001, str(tmp_path))
    count = float(raw["metrics"]["temporal_routine_promotion"])
    assert count >= float(thr["temporal_routine_promotion_min"])


def test_gate6_c6_weaker_than_c0_s7(tmp_path):
    from experiments.d010.run_experiment import _run_integrated_trace

    c0 = _run_integrated_trace("C0", "S7", 50001, str(tmp_path / "c0"))
    c6 = _run_integrated_trace("C6", "S7", 50001, str(tmp_path / "c6"))
    gap = float(c0["metrics"]["temporal_routine_promotion"]) - float(
        c6["metrics"]["temporal_routine_promotion"]
    )
    assert gap >= 0.05


def test_gate10_c0_restart_continuity_high_c8_low(tmp_path):
    from experiments.d010.run_experiment import _run_integrated_trace

    c0 = _run_integrated_trace("C0", "S5", 50001, str(tmp_path / "c0"))
    c8 = _run_integrated_trace("C8", "S5", 50001, str(tmp_path / "c8"))
    assert float(c0["metrics"]["restart_age_continuity"]) >= 0.9
    assert float(c8["metrics"]["restart_age_continuity"]) < 0.5
    gap = float(c0["metrics"]["restart_age_continuity"]) - float(
        c8["metrics"]["restart_age_continuity"]
    )
    assert gap >= 0.05


def test_gate11_c12_replay_equivalence_low_after_shuffle(tmp_path):
    from experiments.d010.run_experiment import _run_integrated_trace

    c0 = _run_integrated_trace("C0", "S11", 50001, str(tmp_path / "c0"))
    c12 = _run_integrated_trace("C12", "S11", 50001, str(tmp_path / "c12"))
    assert float(c0["metrics"]["replay_equivalence"]) >= 0.9
    assert float(c12["metrics"]["replay_equivalence"]) < 0.5
    gap = float(c0["metrics"]["replay_equivalence"]) - float(c12["metrics"]["replay_equivalence"])
    assert gap >= 0.05


def test_validator_gate_summary_allowed_verdicts_no_false_positive(tmp_path, monkeypatch):
    from experiments.d010 import validate_evidence as ve

    evidence_dir = tmp_path / "d010"
    evidence_dir.mkdir()
    gate_summary = {
        "thresholds": {
            "allowed_verdicts": ["UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED"],
        }
    }
    (evidence_dir / "temporal-routine-results.json").write_text(
        json.dumps(gate_summary), encoding="utf-8"
    )
    monkeypatch.setattr(ve, "OUT", evidence_dir)
    assert ve._forbidden_claims() == []


def test_validator_final_verdict_qualified_claim_fails(tmp_path, monkeypatch):
    from experiments.d010 import validate_evidence as ve

    evidence_dir = tmp_path / "d010"
    evidence_dir.mkdir()
    (evidence_dir / "final-verdict.md").write_text(
        "UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED\n", encoding="utf-8"
    )
    monkeypatch.setattr(ve, "OUT", evidence_dir)
    errors = ve._forbidden_claims()
    assert any("forbidden_claim:final-verdict.md" in err for err in errors)


def test_formal_harness_refuses_placeholder_hashes():
    from experiments.d010.stage_a import assert_no_placeholder_hashes

    with pytest.raises(ValueError, match="placeholder"):
        assert_no_placeholder_hashes({"experiments/d010/x.json": "PLACEHOLDER" * 4})


def test_seal_refuses_qualified_without_gates():
    from experiments.d010 import run_seal as seal_mod

    assert seal_mod._qualification_verdict(
        gates_ok=False,
        perf_ok=True,
        prior_ok=True,
        suite_ok=True,
    ) == "UMBRA_D010_PARTIAL_FOUNDATION"


def test_seal_refuses_qualified_without_perf():
    from experiments.d010 import run_seal as seal_mod

    assert seal_mod._qualification_verdict(
        gates_ok=True,
        perf_ok=False,
        prior_ok=True,
        suite_ok=True,
    ) == "UMBRA_D010_PERFORMANCE_FAIL"


def test_seal_emits_qualified_only_when_all_pass():
    from experiments.d010 import run_seal as seal_mod

    assert seal_mod._qualification_verdict(
        gates_ok=True,
        perf_ok=True,
        prior_ok=True,
        suite_ok=True,
    ) == "UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED"


def test_seal_gates_ok_reads_formal_run_outcome():
    from experiments.d010 import run_seal as seal_mod

    assert seal_mod._gates_ok(
        formal={"gates_1_12_pass": True},
        exp={},
    )
    assert seal_mod._gates_ok(
        formal={"outcome": "UMBRA_D010_TASK13_GATES_1_12_PASS"},
        exp={},
    )
    assert not seal_mod._gates_ok(formal={}, exp={})


def test_seal_perf_ok_rejects_pre_freeze_and_smoke():
    from experiments.d010 import run_seal as seal_mod

    assert not seal_mod._perf_ok({"pass": True, "adaptive_soak_supplement": "S3", "pre_freeze": True})
    assert not seal_mod._perf_ok({"pass": True, "adaptive_soak_supplement": "S3", "smoke_scaled": True})
    assert seal_mod._perf_ok({"pass": True, "adaptive_soak_supplement": "S3", "pre_freeze": False})


def test_performance_dry_run_reports_pre_freeze_false_when_not_smoke(monkeypatch):
    monkeypatch.delenv("D010_PERF_SMOKE", raising=False)
    import experiments.d010.run_performance as perf_mod

    timing = perf_mod._proto_timing()
    assert timing["warmup_seconds"] >= float(
        json.loads((ROOT / "experiments/d010/performance-protocol.json").read_text())["warmup_seconds"]
    )
    assert not perf_mod._is_smoke()


def test_wal_checkpoint_releases_native_arenas(tmp_path, monkeypatch):
    """D-010-R1: WAL checkpoint trims arenas; snapshot path must not (D-009 pattern)."""
    from umbra_core import runtime as runtime_mod
    from umbra_core.runtime import OrganismConfig, create_organism
    from umbra_core.temporal.config import p0_performance_config

    calls: list[int] = []

    def _track() -> None:
        calls.append(1)

    monkeypatch.setattr(runtime_mod, "_release_native_arenas", _track)
    db = tmp_path / "arena.sqlite"
    org = create_organism(
        OrganismConfig(
            db_path=str(db),
            seed=7,
            hz=2.0,
            temporal_enabled=True,
            temporal_config=p0_performance_config(),
            habitat_enabled=False,
            expression_enabled=False,
            embodiment_adapter_enabled=True,
        )
    )
    calls.clear()
    assert org.snapshot_if_due(force=True) is not None
    assert calls == []
    for _ in range(500):
        org.tick_once()
    assert len(calls) >= 1
    org.close()


def test_expression_adaptive_trim_on_rss_growth(tmp_path, monkeypatch):
    """D-010-R1: expression path trims only after measured RssAnon growth."""
    from umbra_core import runtime as runtime_mod
    from umbra_core.runtime import OrganismConfig, create_organism
    from umbra_core.temporal.config import p0_performance_config

    calls: list[int] = []
    rss_values = [40.0]

    def _track() -> None:
        calls.append(1)
        # Simulate post-trim drop so the next poll does not immediately re-trigger.
        rss_values[0] = max(39.0, rss_values[0] - 0.5)

    monkeypatch.setattr(runtime_mod, "_release_native_arenas", _track)
    monkeypatch.setattr(runtime_mod, "current_rss_mib", lambda: rss_values[0])
    org = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "adaptive.sqlite"),
            seed=7,
            hz=2.0,
            temporal_enabled=True,
            temporal_config=p0_performance_config(),
            habitat_enabled=True,
            expression_enabled=True,
            embodiment_adapter_enabled=True,
        )
    )
    calls.clear()
    # First cadence sample establishes baseline (may trim once).
    for _ in range(50):
        org.tick_once()
    baseline_calls = len(calls)
    # No growth → no additional trim at next cadence.
    for _ in range(50):
        org.tick_once()
    assert len(calls) == baseline_calls
    # Growth ≥ 0.4 MiB → trim on next cadence.
    rss_values[0] += 0.5
    for _ in range(50):
        org.tick_once()
    assert len(calls) == baseline_calls + 1
    org.close()


def test_committed_advance_ids_remain_bounded(tmp_path):
    """D-010-R1: in-process advance-id dedup must not grow with tick count."""
    from umbra_core.runtime import OrganismConfig, create_organism
    from umbra_core.temporal.config import p0_performance_config

    org = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "bound.sqlite"),
            seed=11,
            hz=2.0,
            temporal_enabled=True,
            temporal_config=p0_performance_config(),
            habitat_enabled=False,
            expression_enabled=False,
            embodiment_adapter_enabled=True,
        )
    )
    for _ in range(250):
        org.tick_once()
    assert len(org.temporal._committed_advance_ids) == 1
    assert next(iter(org.temporal._committed_advance_ids)) == org.temporal.state.last_advance_id
    org.close()

