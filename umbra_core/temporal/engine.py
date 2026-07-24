"""TemporalEngine — sole durable temporal authority (D-010)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from umbra_core.temporal.allowlists import (
    AllowlistError,
    assert_authoritative_event_allowed,
    assert_observable_evidence_allowed,
)
from umbra_core.temporal.clock import TrustedSample, compute_sample_hash
from umbra_core.temporal.contracts import (
    ElapsedContractError,
    ElapsedTimeContractRegistry,
    calculate_all_effects,
    load_elapsed_contract_registry,
)
from umbra_core.temporal.downtime import (
    DowntimeReconciliationError,
    DowntimeReconciliationPlan,
    DowntimeReconciliationRecord,
    DowntimeReconciliationResult,
    ReconciliationStatus,
    apply_downtime_plan_to_state,
    build_downtime_anchor,
    classify_downtime_trust,
    compute_canonical_plan_hash,
    compute_downtime_interval_id,
    compute_expectation_recovery_deltas,
    compute_wait_recovery_deltas,
    new_reconciliation_id,
    plan_identity_payload,
    reconciliation_policy_hash,
)
from umbra_core.temporal.events import (
    TemporalAdvanceRecord,
    TemporalEngineError,
    apply_advance_plan,
    build_advance_record,
)
from umbra_core.temporal.observations import (
    CommitMode,
    DedupSummary,
    HypothesisDelta,
    ObservationWindowEvidence,
    TemporalObservationPlan,
    identity_seen,
    miss_eligible,
    new_observation_plan_id,
    observation_miss_key,
    register_identities,
)
from umbra_core.temporal.policy import (
    PolicyExpectationView,
    policy_expectation_views_from_index,
)
from umbra_core.temporal.recurrence import (
    CONTEXT_SCHEMA_VERSION,
    EvidenceLane,
    RecurrenceHypothesis,
    RecurrencePrediction,
    RecurrenceTracker,
    compute_recurrence_key,
    get_hypothesis_from_index,
    upsert_recurrence_index,
)
from umbra_core.temporal.state import TemporalState, with_state_hash
from umbra_core.util import new_id


@dataclass(frozen=True)
class AnchorDelta:
    """Proposed anchor mutation payload; applied on txn commit (Task 3)."""

    trusted_sample_hash: str
    orchestration_sequence: int


@dataclass(frozen=True)
class TemporalAdvancePlan:
    advance_id: str
    expected_state_version: int
    expected_state_hash: str
    orchestration_sequence: int
    trusted_sample_hash: str
    prior_age_ticks: int
    next_age_ticks: int
    prior_active_ticks: int
    next_active_ticks: int
    anchor_delta: AnchorDelta


@dataclass(frozen=True)
class TickTemporalContext:
    advance_id: str
    effective_age_ticks: int
    effective_active_ticks: int
    orchestration_sequence: int
    prior_state_version: int
    prior_state_hash: str


def build_tick_temporal_context(plan: TemporalAdvancePlan) -> TickTemporalContext:
    """Build speculative tick context from a prepared advance plan."""
    return TickTemporalContext(
        advance_id=plan.advance_id,
        effective_age_ticks=plan.next_age_ticks,
        effective_active_ticks=plan.next_active_ticks,
        orchestration_sequence=plan.orchestration_sequence,
        prior_state_version=plan.expected_state_version,
        prior_state_hash=plan.expected_state_hash,
    )


class TemporalEngine:
    """Sole durable temporal writer (Decision A)."""

    def __init__(self, state: TemporalState) -> None:
        self._state = state
        self._in_flight: TemporalAdvancePlan | None = None
        self._committed_advance_ids: set[str] = {state.last_advance_id}
        self._in_flight_observation: TemporalObservationPlan | None = None
        self._committed_observation_plan_ids: set[str] = set()
        self._post_hoc_anchor_registry: dict[str, dict[str, Any]] = {}
        self._reconciliation_journal: dict[str, DowntimeReconciliationRecord] = {}
        self._in_flight_reconciliation: DowntimeReconciliationPlan | None = None
        self._prepared_reconciliation_samples: dict[str, TrustedSample] = {}
        self._prepared_context_index: dict[str, str] = {}
        self._committed_reconciliation_ids: set[str] = set()
        self._committed_reconciliation_plans: dict[str, DowntimeReconciliationPlan] = {}

    @property
    def state(self) -> TemporalState:
        return self._state

    @property
    def in_flight_plan(self) -> TemporalAdvancePlan | None:
        return self._in_flight

    @property
    def in_flight_observation_plan(self) -> TemporalObservationPlan | None:
        return self._in_flight_observation

    def register_post_hoc_anchor(
        self,
        *,
        source_event_id: str,
        source_event_hash: str,
        committed_advance_id: str,
        committed_age_ticks: int,
        committed_temporal_state_version: int,
    ) -> None:
        """Record durable POST_HOC anchors from a committed source transaction."""
        self._post_hoc_anchor_registry[source_event_id] = {
            "source_event_hash": source_event_hash,
            "committed_advance_id": committed_advance_id,
            "committed_age_ticks": committed_age_ticks,
            "committed_temporal_state_version": committed_temporal_state_version,
        }

    def prepare_advance(
        self,
        sample: TrustedSample,
        orchestration_sequence: int,
    ) -> TemporalAdvancePlan:
        if self._in_flight is not None:
            raise TemporalEngineError("advance_already_prepared")

        prior_age = self._state.organism_age_ticks
        prior_active = self._state.organism_active_ticks
        sample_hash = compute_sample_hash(sample)
        plan = TemporalAdvancePlan(
            advance_id=f"advance:{new_id()}",
            expected_state_version=self._state.state_version,
            expected_state_hash=self._state.state_hash,
            orchestration_sequence=orchestration_sequence,
            trusted_sample_hash=sample_hash,
            prior_age_ticks=prior_age,
            next_age_ticks=prior_age + 1,
            prior_active_ticks=prior_active,
            next_active_ticks=prior_active + 1,
            anchor_delta=AnchorDelta(
                trusted_sample_hash=sample_hash,
                orchestration_sequence=orchestration_sequence,
            ),
        )
        self._in_flight = plan
        return plan

    def abandon_advance(self, advance_id: str) -> None:
        if self._in_flight is None:
            raise TemporalEngineError("no_advance_prepared")
        if self._in_flight.advance_id != advance_id:
            raise TemporalEngineError("advance_id_mismatch")
        self._in_flight = None

    def build_tick_context(self, plan: TemporalAdvancePlan) -> TickTemporalContext:
        return build_tick_temporal_context(plan)

    def commit_advance(
        self,
        plan: TemporalAdvancePlan,
        sample: TrustedSample,
        session_id: str,
    ) -> tuple[TemporalState, TemporalAdvanceRecord]:
        if self._in_flight is None:
            raise TemporalEngineError("no_advance_prepared")
        if self._in_flight.advance_id != plan.advance_id:
            raise TemporalEngineError("advance_id_mismatch")
        if plan.advance_id in self._committed_advance_ids:
            raise TemporalEngineError("advance_id_already_committed")

        prior = self._state
        new_state = apply_advance_plan(prior, plan, sample, session_id)
        record = build_advance_record(prior, new_state, plan)
        self._state = new_state
        self._in_flight = None
        self._committed_advance_ids.add(plan.advance_id)
        return new_state, record

    @property
    def in_flight_reconciliation_plan(self) -> DowntimeReconciliationPlan | None:
        return self._in_flight_reconciliation

    def reconcile_downtime(
        self,
        sample: TrustedSample,
        *,
        session_id: str,
        wait_journal: Any | None = None,
        registry: ElapsedTimeContractRegistry | None = None,
        subsystem_snapshots: dict[str, dict[str, Any]] | None = None,
    ) -> DowntimeReconciliationPlan:
        if self._in_flight_reconciliation is not None:
            return self._in_flight_reconciliation

        prior_anchor = self._state.last_time_anchor
        context_key = f"{prior_anchor.state_hash}:{session_id}"
        sticky_interval = self._prepared_context_index.get(context_key)
        if sticky_interval is not None:
            interval_id = sticky_interval
            sticky = self._prepared_reconciliation_samples[interval_id]
            effective_sample = sticky
        else:
            effective_sample = sample
            interval_id = compute_downtime_interval_id(
                prior_anchor=prior_anchor,
                sample=effective_sample,
            )
            self._prepared_reconciliation_samples[interval_id] = effective_sample
            self._prepared_context_index[context_key] = interval_id

        existing = self._reconciliation_journal.get(interval_id)
        if existing is not None and existing.status == ReconciliationStatus.COMMITTED:
            committed_plan = self._committed_reconciliation_plans.get(interval_id)
            if committed_plan is None:
                raise TemporalEngineError("committed_plan_missing")
            return committed_plan

        reg = registry or load_elapsed_contract_registry()
        snaps = dict(subsystem_snapshots or {})
        snaps.setdefault("temporal", {
            "state_version": self._state.state_version,
            "state_hash": self._state.state_hash,
        })
        snaps.setdefault("physiology", {"state_version": 0, "state_hash": "physiology:genesis"})
        snaps.setdefault("needs", {"state_version": 0, "state_hash": "needs:genesis"})

        trust = classify_downtime_trust(prior_anchor=prior_anchor, sample=effective_sample)
        effect_plans, skipped, required_failure = calculate_all_effects(
            reg,
            subsystem_snapshots=snaps,
            elapsed_seconds=trust.elapsed_seconds,
            uncertainty=effective_sample.wall_time_uncertainty,
            trust_class=trust.trust_class,
        )
        conservative = trust.conservative or required_failure
        age_advance = 0 if conservative else trust.age_advance
        fractional = 0.0 if conservative else trust.fractional_remainder

        prior_age = self._state.organism_age_ticks
        next_age = prior_age + age_advance
        reconciliation_id = new_reconciliation_id()

        def _predict(recurrence_id: str, *, current_age: int) -> Any:
            return self.predict_recurrence(recurrence_id, current_age=current_age)

        expectation_deltas = compute_expectation_recovery_deltas(
            self._state,
            new_age_ticks=next_age,
            predict_fn=_predict,
        )
        wait_deltas: tuple[Any, ...] = ()
        if wait_journal is not None:
            wait_deltas = compute_wait_recovery_deltas(wait_journal, new_age_ticks=next_age)

        effective_trust = replace(
            trust,
            conservative=conservative,
            age_advance=age_advance,
            fractional_remainder=fractional,
        )
        new_anchor = build_downtime_anchor(
            sample=effective_sample,
            session_id=session_id,
            age_ticks=next_age,
            active_ticks=self._state.organism_active_ticks,
            state_version=self._state.state_version + 1,
            trust=effective_trust,
            reconciliation_id=reconciliation_id,
        )

        identity = plan_identity_payload(
            downtime_interval_id=interval_id,
            trust_class=trust.trust_class,
            trust_reason_codes=trust.reason_codes,
            elapsed_seconds=trust.elapsed_seconds,
            age_advance=age_advance,
            fractional_remainder=fractional,
            prior_age_ticks=prior_age,
            next_age_ticks=next_age,
            registry_hash=reg.registry_hash,
            effect_plan_hashes=tuple(p.effect_plan_hash for p in effect_plans),
            skipped_contract_ids=tuple(skipped),
            expectation_recovery_deltas=expectation_deltas,
            wait_recovery_deltas=wait_deltas,
            conservative=conservative,
            trusted_sample_hash=compute_sample_hash(effective_sample),
        )
        canonical_hash = compute_canonical_plan_hash(identity)

        if existing is not None and existing.canonical_plan_hash != canonical_hash:
            raise DowntimeReconciliationError("RECONCILIATION_PAYLOAD_MISMATCH")

        plan = DowntimeReconciliationPlan(
            downtime_interval_id=interval_id,
            reconciliation_id=reconciliation_id,
            canonical_plan_hash=canonical_hash,
            expected_state_version=self._state.state_version,
            expected_state_hash=self._state.state_hash,
            session_id=session_id,
            trusted_sample_hash=compute_sample_hash(effective_sample),
            trust_class=trust.trust_class,
            trust_reason_codes=trust.reason_codes,
            elapsed_seconds=trust.elapsed_seconds,
            age_advance=age_advance,
            fractional_remainder=fractional,
            prior_age_ticks=prior_age,
            next_age_ticks=next_age,
            prior_active_ticks=self._state.organism_active_ticks,
            next_active_ticks=self._state.organism_active_ticks,
            prior_time_anchor=prior_anchor,
            new_time_anchor=new_anchor,
            registry_hash=reg.registry_hash,
            effect_plan_ids=tuple(p.effect_plan_id for p in effect_plans),
            effect_plan_hashes=tuple(p.effect_plan_hash for p in effect_plans),
            skipped_contract_ids=tuple(skipped),
            expectation_recovery_deltas=expectation_deltas,
            wait_recovery_deltas=wait_deltas,
            conservative=conservative,
        )
        self._in_flight_reconciliation = plan
        self._reconciliation_journal[interval_id] = DowntimeReconciliationRecord(
            downtime_interval_id=interval_id,
            reconciliation_id=reconciliation_id,
            canonical_plan_hash=canonical_hash,
            status=ReconciliationStatus.PREPARED,
            sticky_sample_hash=compute_sample_hash(effective_sample),
        )
        return plan

    def abandon_downtime_reconciliation(self, reconciliation_id: str) -> None:
        if self._in_flight_reconciliation is None:
            raise TemporalEngineError("no_reconciliation_prepared")
        if self._in_flight_reconciliation.reconciliation_id != reconciliation_id:
            raise TemporalEngineError("reconciliation_id_mismatch")
        self._in_flight_reconciliation = None

    def commit_downtime_reconciliation(
        self,
        plan: DowntimeReconciliationPlan,
        sample: TrustedSample,
        *,
        transaction_id: str,
    ) -> DowntimeReconciliationResult:
        interval_id = plan.downtime_interval_id
        existing = self._reconciliation_journal.get(interval_id)
        if existing is not None and existing.status == ReconciliationStatus.COMMITTED:
            if existing.canonical_plan_hash != plan.canonical_plan_hash:
                raise DowntimeReconciliationError("RECONCILIATION_PAYLOAD_MISMATCH")
            return DowntimeReconciliationResult(
                plan=plan,
                new_state=self._state,
                record=existing,
            )

        if self._in_flight_reconciliation is None:
            raise TemporalEngineError("no_reconciliation_prepared")
        if self._in_flight_reconciliation.reconciliation_id != plan.reconciliation_id:
            raise TemporalEngineError("reconciliation_id_mismatch")

        sticky = self._prepared_reconciliation_samples.get(interval_id, sample)
        if compute_sample_hash(sticky) != plan.trusted_sample_hash:
            raise DowntimeReconciliationError("RECONCILIATION_PAYLOAD_MISMATCH")

        new_state = apply_downtime_plan_to_state(self._state, plan, sticky)
        record = DowntimeReconciliationRecord(
            downtime_interval_id=interval_id,
            reconciliation_id=plan.reconciliation_id,
            canonical_plan_hash=plan.canonical_plan_hash,
            status=ReconciliationStatus.COMMITTED,
            transaction_id=transaction_id,
            sticky_sample_hash=plan.trusted_sample_hash,
        )
        self._state = new_state
        self._reconciliation_journal[interval_id] = record
        self._committed_reconciliation_ids.add(plan.reconciliation_id)
        self._committed_reconciliation_plans[interval_id] = plan
        self._in_flight_reconciliation = None
        return DowntimeReconciliationResult(plan=plan, new_state=new_state, record=record)

    def get_reconciliation_record(self, downtime_interval_id: str) -> DowntimeReconciliationRecord | None:
        return self._reconciliation_journal.get(downtime_interval_id)

    def replace_state(self, state: TemporalState) -> None:
        """Restore durable temporal state after restart (snapshot authority)."""
        self._state = state
        self._in_flight = None
        self._committed_advance_ids = {state.last_advance_id}
        self._in_flight_observation = None
        self._committed_observation_plan_ids = set()
        self._reconciliation_journal = {}
        self._in_flight_reconciliation = None
        self._prepared_reconciliation_samples = {}
        self._prepared_context_index = {}
        self._committed_reconciliation_ids = set()
        self._committed_reconciliation_plans = {}

    def prepare_finalized_evidence(
        self,
        *,
        source_transaction_id: str,
        event_kind: str,
        internal_context_key: str,
        occurrence_id: str,
        evidence_identity: str,
        tick: int,
        commit_mode: CommitMode = CommitMode.IN_TICK,
        source_event_id: str | None = None,
        source_event_hash: str | None = None,
        committed_advance_id: str | None = None,
        committed_age_ticks: int | None = None,
        committed_temporal_state_version: int | None = None,
        context_schema_version: str = CONTEXT_SCHEMA_VERSION,
    ) -> TemporalObservationPlan:
        if self._in_flight_observation is not None:
            raise TemporalEngineError("observation_plan_already_prepared")
        try:
            assert_observable_evidence_allowed(event_kind)
        except AllowlistError as exc:
            raise TemporalEngineError(str(exc)) from exc

        return self._prepare_observation_plan(
            lane=EvidenceLane.ORGANISM_OBSERVABLE,
            event_kind=event_kind,
            internal_context_key=internal_context_key,
            occurrence_id=occurrence_id,
            evidence_identity=evidence_identity,
            tick=tick,
            commit_mode=commit_mode,
            source_transaction_id=source_transaction_id,
            source_event_id=source_event_id,
            source_event_hash=source_event_hash,
            committed_advance_id=committed_advance_id,
            committed_age_ticks=committed_age_ticks,
            committed_temporal_state_version=committed_temporal_state_version,
            context_schema_version=context_schema_version,
        )

    def prepare_authoritative_event(
        self,
        *,
        source_transaction_id: str,
        event_kind: str,
        internal_context_key: str,
        occurrence_id: str,
        evidence_identity: str,
        tick: int,
        commit_mode: CommitMode = CommitMode.IN_TICK,
        source_event_id: str | None = None,
        source_event_hash: str | None = None,
        committed_advance_id: str | None = None,
        committed_age_ticks: int | None = None,
        committed_temporal_state_version: int | None = None,
        context_schema_version: str = CONTEXT_SCHEMA_VERSION,
    ) -> TemporalObservationPlan:
        if self._in_flight_observation is not None:
            raise TemporalEngineError("observation_plan_already_prepared")
        try:
            assert_authoritative_event_allowed(event_kind)
        except AllowlistError as exc:
            raise TemporalEngineError(str(exc)) from exc

        return self._prepare_observation_plan(
            lane=EvidenceLane.AUTHORITATIVE,
            event_kind=event_kind,
            internal_context_key=internal_context_key,
            occurrence_id=occurrence_id,
            evidence_identity=evidence_identity,
            tick=tick,
            commit_mode=commit_mode,
            source_transaction_id=source_transaction_id,
            source_event_id=source_event_id,
            source_event_hash=source_event_hash,
            committed_advance_id=committed_advance_id,
            committed_age_ticks=committed_age_ticks,
            committed_temporal_state_version=committed_temporal_state_version,
            context_schema_version=context_schema_version,
        )

    def _prepare_observation_plan(
        self,
        *,
        lane: EvidenceLane,
        event_kind: str,
        internal_context_key: str,
        occurrence_id: str,
        evidence_identity: str,
        tick: int,
        commit_mode: CommitMode,
        source_transaction_id: str | None,
        source_event_id: str | None,
        source_event_hash: str | None,
        committed_advance_id: str | None,
        committed_age_ticks: int | None,
        committed_temporal_state_version: int | None,
        context_schema_version: str,
    ) -> TemporalObservationPlan:
        if commit_mode == CommitMode.IN_TICK:
            if not source_transaction_id:
                raise TemporalEngineError("source_transaction_id_required")
            effective_tick = int(tick)
        else:
            self._validate_post_hoc_anchors(
                source_event_id=source_event_id,
                source_event_hash=source_event_hash,
                committed_advance_id=committed_advance_id,
                committed_age_ticks=committed_age_ticks,
                committed_temporal_state_version=committed_temporal_state_version,
                occurrence_id=occurrence_id,
            )
            effective_tick = int(committed_age_ticks)  # type: ignore[arg-type]

        delta = HypothesisDelta(
            event_kind=event_kind,
            internal_context_key=internal_context_key,
            occurrence_id=occurrence_id,
            evidence_identity=evidence_identity,
            tick=effective_tick,
            lane=lane.value,
            context_schema_version=context_schema_version,
        )
        plan = TemporalObservationPlan(
            observation_plan_id=new_observation_plan_id(),
            commit_mode=commit_mode,
            expected_temporal_state_version=self._state.state_version,
            expected_temporal_state_hash=self._state.state_hash,
            source_transaction_id=source_transaction_id,
            source_event_id=source_event_id,
            source_event_hash=source_event_hash,
            committed_advance_id=committed_advance_id,
            committed_age_ticks=committed_age_ticks,
            committed_temporal_state_version=committed_temporal_state_version,
            occurrence_id=occurrence_id,
            evidence_identities=(evidence_identity,),
            hypothesis_deltas=(delta,),
            temporal_events=(),
        )
        self._in_flight_observation = plan
        return plan

    def _validate_post_hoc_anchors(
        self,
        *,
        source_event_id: str | None,
        source_event_hash: str | None,
        committed_advance_id: str | None,
        committed_age_ticks: int | None,
        committed_temporal_state_version: int | None,
        occurrence_id: str,
    ) -> None:
        if not all(
            (
                source_event_id,
                source_event_hash,
                committed_advance_id,
                committed_age_ticks is not None,
                committed_temporal_state_version is not None,
            )
        ):
            raise TemporalEngineError("post_hoc_anchor_missing")

        anchor = self._post_hoc_anchor_registry.get(str(source_event_id))
        if anchor is None:
            raise TemporalEngineError("post_hoc_source_anchor_missing")
        if anchor["source_event_hash"] != source_event_hash:
            raise TemporalEngineError("post_hoc_source_event_hash_mismatch")
        if anchor["committed_advance_id"] != committed_advance_id:
            raise TemporalEngineError("post_hoc_advance_id_mismatch")
        if anchor["committed_age_ticks"] != committed_age_ticks:
            raise TemporalEngineError("post_hoc_age_mismatch")
        if anchor["committed_temporal_state_version"] != committed_temporal_state_version:
            raise TemporalEngineError("post_hoc_state_version_mismatch")

        anchored_age = int(committed_age_ticks)  # type: ignore[arg-type]
        for _rec_id, payload in self._state.recurrence_index:
            for occ_id, occ_tick, _lane in payload.get("occurrence_by_id") or []:
                if str(occ_id) == occurrence_id and int(occ_tick) != anchored_age:
                    raise TemporalEngineError("post_hoc_occurrence_age_immutable")

    def abandon_observation_plan(self, observation_plan_id: str) -> None:
        if self._in_flight_observation is None:
            raise TemporalEngineError("no_observation_plan_prepared")
        if self._in_flight_observation.observation_plan_id != observation_plan_id:
            raise TemporalEngineError("observation_plan_id_mismatch")
        self._in_flight_observation = None

    def commit_observation_plan(
        self,
        plan: TemporalObservationPlan,
    ) -> RecurrenceHypothesis:
        if plan.observation_plan_id in self._committed_observation_plan_ids:
            raise TemporalEngineError("observation_plan_already_committed")
        if self._in_flight_observation is None:
            raise TemporalEngineError("no_observation_plan_prepared")
        if self._in_flight_observation.observation_plan_id != plan.observation_plan_id:
            raise TemporalEngineError("observation_plan_id_mismatch")
        if plan.expected_temporal_state_version != self._state.state_version:
            raise TemporalEngineError("expected_state_version_mismatch")
        if plan.expected_temporal_state_hash != self._state.state_hash:
            raise TemporalEngineError("expected_state_hash_mismatch")

        if plan.commit_mode == CommitMode.POST_HOC:
            self._validate_post_hoc_anchors(
                source_event_id=plan.source_event_id,
                source_event_hash=plan.source_event_hash,
                committed_advance_id=plan.committed_advance_id,
                committed_age_ticks=plan.committed_age_ticks,
                committed_temporal_state_version=plan.committed_temporal_state_version,
                occurrence_id=plan.occurrence_id,
            )

        before = self._state
        hypothesis = self._apply_hypothesis_deltas(plan.hypothesis_deltas, before.dedup_summary)
        self._committed_observation_plan_ids.add(plan.observation_plan_id)
        self._in_flight_observation = None
        return hypothesis

    def _apply_hypothesis_deltas(
        self,
        deltas: tuple[HypothesisDelta, ...],
        dedup_summary: DedupSummary,
    ) -> RecurrenceHypothesis:
        hypothesis: RecurrenceHypothesis | None = None
        summary = dedup_summary
        for delta in deltas:
            if identity_seen(summary, evidence_identity=delta.evidence_identity):
                recurrence_key = compute_recurrence_key(
                    delta.event_kind,
                    delta.internal_context_key,
                    delta.context_schema_version,
                )
                existing = get_hypothesis_from_index(
                    self._state.recurrence_index,
                    f"rec:{recurrence_key[:16]}",
                )
                if existing is not None:
                    hypothesis = existing
                continue

            recurrence_key = compute_recurrence_key(
                delta.event_kind,
                delta.internal_context_key,
                delta.context_schema_version,
            )
            existing = get_hypothesis_from_index(
                self._state.recurrence_index,
                f"rec:{recurrence_key[:16]}",
            )
            lane = EvidenceLane(delta.lane)
            hypothesis = RecurrenceTracker().observe(
                existing,
                recurrence_key=recurrence_key,
                event_kind=delta.event_kind,
                internal_context_key=delta.internal_context_key,
                occurrence_id=delta.occurrence_id,
                evidence_identity=delta.evidence_identity,
                tick=delta.tick,
                lane=lane,
                context_schema_version=delta.context_schema_version,
            )
            new_index = upsert_recurrence_index(self._state.recurrence_index, hypothesis)
            occurrence_ids = (
                (delta.occurrence_id,)
                if not identity_seen(summary, occurrence_id=delta.occurrence_id)
                else ()
            )
            try:
                summary = register_identities(
                    summary,
                    evidence_identities=(delta.evidence_identity,),
                    occurrence_ids=occurrence_ids,
                )
            except ValueError as exc:
                if str(exc) == "dedup_compaction_overflow":
                    raise TemporalEngineError("dedup_compaction_overflow") from exc
                raise
            self._state = with_state_hash(
                replace(self._state, recurrence_index=new_index, dedup_summary=summary)
            )

        if hypothesis is None:
            raise TemporalEngineError("observation_plan_no_effect")
        return hypothesis

    def record_observation_window_miss(
        self,
        evidence: ObservationWindowEvidence,
    ) -> RecurrenceHypothesis | None:
        hypothesis = get_hypothesis_from_index(
            self._state.recurrence_index,
            evidence.recurrence_id,
        )
        if hypothesis is None:
            raise TemporalEngineError("recurrence_hypothesis_missing")
        if not miss_eligible(
            evidence,
            current_expectation_version=hypothesis.hypothesis_version,
        ):
            return None

        miss_key = observation_miss_key(
            evidence.recurrence_id,
            evidence.expectation_version,
            evidence.window_start,
            evidence.window_end,
        )
        if miss_key in self._state.observation_miss_keys:
            return hypothesis

        updated = RecurrenceTracker().record_miss(hypothesis)
        new_index = upsert_recurrence_index(self._state.recurrence_index, updated)
        self._state = with_state_hash(
            replace(
                self._state,
                recurrence_index=new_index,
                observation_miss_keys=self._state.observation_miss_keys + (miss_key,),
            )
        )
        return updated

    def observe_recurrence_occurrence(
        self,
        *,
        event_kind: str,
        internal_context_key: str,
        occurrence_id: str,
        evidence_identity: str,
        tick: int,
        lane: EvidenceLane,
        context_schema_version: str = CONTEXT_SCHEMA_VERSION,
    ) -> RecurrenceHypothesis:
        """Thin observe stub for Task 4 tests; full observation plans are Task 5.

        ponytail: bypasses durable dedup (register_identities); Task 5 commit path only.
        """
        recurrence_key = compute_recurrence_key(
            event_kind,
            internal_context_key,
            context_schema_version,
        )
        existing = get_hypothesis_from_index(
            self._state.recurrence_index,
            f"rec:{recurrence_key[:16]}",
        )
        hypothesis = RecurrenceTracker().observe(
            existing,
            recurrence_key=recurrence_key,
            event_kind=event_kind,
            internal_context_key=internal_context_key,
            occurrence_id=occurrence_id,
            evidence_identity=evidence_identity,
            tick=tick,
            lane=lane,
            context_schema_version=context_schema_version,
        )
        new_index = upsert_recurrence_index(self._state.recurrence_index, hypothesis)
        self._state = with_state_hash(
            replace(self._state, recurrence_index=new_index)
        )
        return hypothesis

    def predict_recurrence(
        self,
        recurrence_id: str,
        *,
        current_age: int | None = None,
    ) -> RecurrencePrediction | None:
        hypothesis = get_hypothesis_from_index(self._state.recurrence_index, recurrence_id)
        if hypothesis is None:
            return None
        age = (
            self._state.organism_age_ticks
            if current_age is None
            else int(current_age)
        )
        return RecurrenceTracker().predict(hypothesis, age)

    def record_recurrence_miss(self, recurrence_id: str) -> RecurrenceHypothesis:
        hypothesis = get_hypothesis_from_index(self._state.recurrence_index, recurrence_id)
        if hypothesis is None:
            raise TemporalEngineError("recurrence_hypothesis_missing")
        updated = RecurrenceTracker().record_miss(hypothesis)
        new_index = upsert_recurrence_index(self._state.recurrence_index, updated)
        self._state = with_state_hash(
            replace(self._state, recurrence_index=new_index)
        )
        return updated

    def build_policy_expectation_views(
        self,
        *,
        current_age: int | None = None,
    ) -> tuple[PolicyExpectationView, ...]:
        """Expose ACTIVE|UNCERTAIN expectations only; no wait ownership."""
        age = (
            self._state.organism_age_ticks
            if current_age is None
            else int(current_age)
        )

        def _predict(recurrence_id: str, *, current_age: int) -> RecurrencePrediction | None:
            return self.predict_recurrence(recurrence_id, current_age=current_age)

        return policy_expectation_views_from_index(
            self._state.recurrence_index,
            current_age=age,
            predict_fn=_predict,
        )
