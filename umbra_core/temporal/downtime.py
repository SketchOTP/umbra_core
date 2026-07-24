"""D-010 downtime reconciliation plans and trust classification (§4)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from umbra_core.temporal.clock import TrustedSample, compute_sample_hash
from umbra_core.temporal.state import (
    AnchorTrustClass,
    TemporalState,
    TimeAnchor,
    WallClockMapping,
    canonical_serialize,
    with_anchor_state_hash,
    with_state_hash,
)
from umbra_core.util import canon_json, new_id, sha256_hex

# ponytail: frozen at D-010 Task 8; hardened at Stage B freeze.
ACCEPTED_WALL_SOURCES = frozenset({"runtime.wall_time_fn", "system.clock"})
MAX_TRUSTED_DOWNTIME_SECONDS = 3600.0
MAX_WALL_UNCERTAINTY = 1.0
SAMPLE_FRESHNESS_SECONDS = 30.0
SECONDS_PER_AGE_TICK = 60.0
MAX_DOWNTIME_AGE_ADVANCE = 60
RECONCILIATION_POLICY_VERSION = "d010.reconciliation-policy.v1"

DOWNTIME_INTERVAL_ALREADY_RECONCILED = "DOWNTIME_INTERVAL_ALREADY_RECONCILED"
RECONCILIATION_PAYLOAD_MISMATCH = "RECONCILIATION_PAYLOAD_MISMATCH"
TEMPORAL_ANCHOR_MISMATCH = "TEMPORAL_ANCHOR_MISMATCH"
WALL_TIME_UNTRUSTED = "WALL_TIME_UNTRUSTED"
RECONCILIATION_STATE_CONFLICT = "RECONCILIATION_STATE_CONFLICT"


class DowntimeReconciliationError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ReconciliationStatus(str, Enum):
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"


def reconciliation_policy_hash() -> str:
    payload = {
        "policy_version": RECONCILIATION_POLICY_VERSION,
        "accepted_wall_sources": sorted(ACCEPTED_WALL_SOURCES),
        "max_trusted_downtime_seconds": MAX_TRUSTED_DOWNTIME_SECONDS,
        "max_wall_uncertainty": MAX_WALL_UNCERTAINTY,
        "sample_freshness_seconds": SAMPLE_FRESHNESS_SECONDS,
        "seconds_per_age_tick": SECONDS_PER_AGE_TICK,
        "max_downtime_age_advance": MAX_DOWNTIME_AGE_ADVANCE,
    }
    return sha256_hex(canon_json(payload))


@dataclass(frozen=True)
class TrustClassification:
    trust_class: AnchorTrustClass
    reason_codes: tuple[str, ...]
    elapsed_seconds: float
    age_advance: int
    fractional_remainder: float
    conservative: bool


@dataclass(frozen=True)
class ExpectationRecoveryDelta:
    recurrence_id: str
    expected_hypothesis_version: int
    expected_expectation_version: int
    action: str
    bounded_delta: float


@dataclass(frozen=True)
class WaitRecoveryDelta:
    execution_id: str
    expected_status: str
    terminal_status: str
    terminal_reason: str
    suppression_plan: dict[str, Any] | None


@dataclass(frozen=True)
class DowntimeReconciliationRecord:
    downtime_interval_id: str
    reconciliation_id: str
    canonical_plan_hash: str
    status: ReconciliationStatus
    transaction_id: str | None = None
    sticky_sample_hash: str | None = None


@dataclass(frozen=True)
class DowntimeReconciliationPlan:
    downtime_interval_id: str
    reconciliation_id: str
    canonical_plan_hash: str
    expected_state_version: int
    expected_state_hash: str
    session_id: str
    trusted_sample_hash: str
    trust_class: AnchorTrustClass
    trust_reason_codes: tuple[str, ...]
    elapsed_seconds: float
    age_advance: int
    fractional_remainder: float
    prior_age_ticks: int
    next_age_ticks: int
    prior_active_ticks: int
    next_active_ticks: int
    prior_time_anchor: TimeAnchor
    new_time_anchor: TimeAnchor
    registry_hash: str
    effect_plan_ids: tuple[str, ...]
    effect_plan_hashes: tuple[str, ...]
    skipped_contract_ids: tuple[str, ...]
    expectation_recovery_deltas: tuple[ExpectationRecoveryDelta, ...]
    wait_recovery_deltas: tuple[WaitRecoveryDelta, ...]
    conservative: bool


@dataclass(frozen=True)
class DowntimeReconciliationResult:
    plan: DowntimeReconciliationPlan
    new_state: TemporalState
    record: DowntimeReconciliationRecord


def compute_downtime_interval_id(
    *,
    prior_anchor: TimeAnchor,
    sample: TrustedSample,
    policy_hash: str | None = None,
) -> str:
    payload = {
        "prior_anchor_state_hash": prior_anchor.state_hash,
        "prior_anchor_advance_id": prior_anchor.advance_id,
        "prior_anchor_session_id": prior_anchor.session_id_at_commit,
        "current_session_id": sample.session_id,
        "current_sample_hash": compute_sample_hash(sample),
        "reconciliation_policy_hash": policy_hash or reconciliation_policy_hash(),
    }
    return f"downtime:{sha256_hex(canon_json(canonical_serialize(payload)))[:32]}"


def plan_identity_payload(
    *,
    downtime_interval_id: str,
    trust_class: AnchorTrustClass,
    trust_reason_codes: tuple[str, ...],
    elapsed_seconds: float,
    age_advance: int,
    fractional_remainder: float,
    prior_age_ticks: int,
    next_age_ticks: int,
    registry_hash: str,
    effect_plan_hashes: tuple[str, ...],
    skipped_contract_ids: tuple[str, ...],
    expectation_recovery_deltas: tuple[ExpectationRecoveryDelta, ...],
    wait_recovery_deltas: tuple[WaitRecoveryDelta, ...],
    conservative: bool,
    trusted_sample_hash: str,
) -> dict[str, Any]:
    return canonical_serialize(
        {
            "downtime_interval_id": downtime_interval_id,
            "trust_class": trust_class,
            "trust_reason_codes": trust_reason_codes,
            "elapsed_seconds": elapsed_seconds,
            "age_advance": age_advance,
            "fractional_remainder": fractional_remainder,
            "prior_age_ticks": prior_age_ticks,
            "next_age_ticks": next_age_ticks,
            "registry_hash": registry_hash,
            "effect_plan_hashes": effect_plan_hashes,
            "skipped_contract_ids": skipped_contract_ids,
            "expectation_recovery_deltas": expectation_recovery_deltas,
            "wait_recovery_deltas": wait_recovery_deltas,
            "conservative": conservative,
            "trusted_sample_hash": trusted_sample_hash,
        }
    )


def compute_canonical_plan_hash(plan_fields: dict[str, Any]) -> str:
    return sha256_hex(canon_json(canonical_serialize(plan_fields)))


def plan_canonical_identity(plan: DowntimeReconciliationPlan) -> dict[str, Any]:
    return plan_identity_payload(
        downtime_interval_id=plan.downtime_interval_id,
        trust_class=plan.trust_class,
        trust_reason_codes=plan.trust_reason_codes,
        elapsed_seconds=plan.elapsed_seconds,
        age_advance=plan.age_advance,
        fractional_remainder=plan.fractional_remainder,
        prior_age_ticks=plan.prior_age_ticks,
        next_age_ticks=plan.next_age_ticks,
        registry_hash=plan.registry_hash,
        effect_plan_hashes=plan.effect_plan_hashes,
        skipped_contract_ids=plan.skipped_contract_ids,
        expectation_recovery_deltas=plan.expectation_recovery_deltas,
        wait_recovery_deltas=plan.wait_recovery_deltas,
        conservative=plan.conservative,
        trusted_sample_hash=plan.trusted_sample_hash,
    )


def verify_plan_canonical_hash(plan: DowntimeReconciliationPlan) -> bool:
    return compute_canonical_plan_hash(plan_canonical_identity(plan)) == plan.canonical_plan_hash


def classify_downtime_trust(
    *,
    prior_anchor: TimeAnchor,
    sample: TrustedSample,
    wall_clock_mapping: WallClockMapping | None = None,
) -> TrustClassification:
    reasons: list[str] = []

    if sample.optional_wall_time is None:
        reasons.append("missing_wall_sample")
        return TrustClassification(
            trust_class=AnchorTrustClass.MISSING_WALL,
            reason_codes=tuple(reasons),
            elapsed_seconds=0.0,
            age_advance=0,
            fractional_remainder=0.0,
            conservative=True,
        )

    if prior_anchor.wall_time is None or not prior_anchor.eligible_as_downtime_baseline:
        reasons.append("prior_anchor_not_eligible_baseline")
        return TrustClassification(
            trust_class=AnchorTrustClass.UNCERTAIN,
            reason_codes=tuple(reasons),
            elapsed_seconds=0.0,
            age_advance=0,
            fractional_remainder=0.0,
            conservative=True,
        )

    if sample.wall_time_source not in ACCEPTED_WALL_SOURCES:
        reasons.append("wall_source_not_accepted")
        return TrustClassification(
            trust_class=AnchorTrustClass.UNCERTAIN,
            reason_codes=tuple(reasons),
            elapsed_seconds=0.0,
            age_advance=0,
            fractional_remainder=0.0,
            conservative=True,
        )

    if sample.wall_time_uncertainty > MAX_WALL_UNCERTAINTY:
        reasons.append("wall_uncertainty_excessive")
        return TrustClassification(
            trust_class=AnchorTrustClass.EXCESSIVE,
            reason_codes=tuple(reasons),
            elapsed_seconds=0.0,
            age_advance=0,
            fractional_remainder=0.0,
            conservative=True,
        )

    if wall_clock_mapping is not None and wall_clock_mapping.wall_time_seconds is not None:
        monotonic_elapsed_s = (
            sample.monotonic_ns - wall_clock_mapping.monotonic_ns_at_mapping
        ) / 1e9
        estimated_wall = wall_clock_mapping.wall_time_seconds + monotonic_elapsed_s
        if abs(float(sample.optional_wall_time) - estimated_wall) > SAMPLE_FRESHNESS_SECONDS:
            reasons.append("sample_not_fresh")
            return TrustClassification(
                trust_class=AnchorTrustClass.UNCERTAIN,
                reason_codes=tuple(reasons),
                elapsed_seconds=0.0,
                age_advance=0,
                fractional_remainder=0.0,
                conservative=True,
            )

    elapsed = float(sample.optional_wall_time) - float(prior_anchor.wall_time)
    if elapsed < 0.0:
        reasons.append("wall_time_backward_jump")
        return TrustClassification(
            trust_class=AnchorTrustClass.UNCERTAIN,
            reason_codes=tuple(reasons),
            elapsed_seconds=elapsed,
            age_advance=0,
            fractional_remainder=0.0,
            conservative=True,
        )

    if elapsed > MAX_TRUSTED_DOWNTIME_SECONDS:
        reasons.append("downtime_gap_excessive")
        return TrustClassification(
            trust_class=AnchorTrustClass.EXCESSIVE,
            reason_codes=tuple(reasons),
            elapsed_seconds=elapsed,
            age_advance=0,
            fractional_remainder=0.0,
            conservative=True,
        )

    if (
        prior_anchor.wall_time_source is not None
        and sample.wall_time_source != prior_anchor.wall_time_source
    ):
        reasons.append("wall_source_discontinuity")
        return TrustClassification(
            trust_class=AnchorTrustClass.UNCERTAIN,
            reason_codes=tuple(reasons),
            elapsed_seconds=elapsed,
            age_advance=0,
            fractional_remainder=0.0,
            conservative=True,
        )

    if wall_clock_mapping is not None and wall_clock_mapping.wall_time_seconds is not None:
        monotonic_elapsed_s = (
            sample.monotonic_ns - wall_clock_mapping.monotonic_ns_at_mapping
        ) / 1e9
        if abs(elapsed - monotonic_elapsed_s) > SAMPLE_FRESHNESS_SECONDS:
            reasons.append("wall_monotonic_implausible")
            return TrustClassification(
                trust_class=AnchorTrustClass.UNCERTAIN,
                reason_codes=tuple(reasons),
                elapsed_seconds=elapsed,
                age_advance=0,
                fractional_remainder=0.0,
                conservative=True,
            )

    tick_equiv = elapsed / SECONDS_PER_AGE_TICK
    age_advance = min(int(tick_equiv), MAX_DOWNTIME_AGE_ADVANCE)
    fractional = tick_equiv - age_advance
    reasons.append("trusted_short_gap")
    return TrustClassification(
        trust_class=AnchorTrustClass.TRUSTED_SHORT,
        reason_codes=tuple(reasons),
        elapsed_seconds=elapsed,
        age_advance=age_advance,
        fractional_remainder=fractional,
        conservative=False,
    )


def build_downtime_anchor(
    *,
    sample: TrustedSample,
    session_id: str,
    age_ticks: int,
    active_ticks: int,
    state_version: int,
    trust: TrustClassification,
    reconciliation_id: str,
) -> TimeAnchor:
    sample_hash = compute_sample_hash(sample)
    eligible = (
        trust.trust_class == AnchorTrustClass.TRUSTED_SHORT
        and not trust.conservative
    )
    anchor = TimeAnchor(
        organism_age_ticks=age_ticks,
        organism_active_ticks=active_ticks,
        state_version=state_version,
        state_hash="",
        wall_time=sample.optional_wall_time,
        wall_time_source=sample.wall_time_source,
        wall_time_uncertainty=sample.wall_time_uncertainty,
        session_id_at_commit=session_id,
        advance_id=f"reconcile:{reconciliation_id}",
        anchor_trust_class=trust.trust_class,
        trust_reason_codes=trust.reason_codes,
        eligible_as_downtime_baseline=eligible,
        source_sample_hash=sample_hash,
    )
    return with_anchor_state_hash(anchor)


def apply_expectation_recovery_deltas(
    state: TemporalState,
    deltas: tuple[ExpectationRecoveryDelta, ...],
) -> TemporalState:
    from umbra_core.temporal.recurrence import (
        HypothesisStatus,
        get_hypothesis_from_index,
        upsert_recurrence_index,
    )

    current = state
    for delta in deltas:
        hypothesis = get_hypothesis_from_index(current.recurrence_index, delta.recurrence_id)
        if hypothesis is None:
            raise DowntimeReconciliationError(RECONCILIATION_PAYLOAD_MISMATCH)
        if hypothesis.hypothesis_version != delta.expected_hypothesis_version:
            raise DowntimeReconciliationError(RECONCILIATION_PAYLOAD_MISMATCH)
        if delta.expected_expectation_version != hypothesis.hypothesis_version:
            raise DowntimeReconciliationError(RECONCILIATION_PAYLOAD_MISMATCH)

        if delta.action == "EXPIRE":
            updated = replace(
                hypothesis,
                status=HypothesisStatus.INACTIVE,
                hypothesis_version=hypothesis.hypothesis_version + 1,
            )
        elif delta.action == "DECAY_CONFIDENCE":
            updated = replace(
                hypothesis,
                miss_count=hypothesis.miss_count + 1,
                hypothesis_version=hypothesis.hypothesis_version + 1,
            )
        elif delta.action in {"INVALIDATE", "PRESERVE"}:
            continue
        else:
            continue
        new_index = upsert_recurrence_index(current.recurrence_index, updated)
        current = replace(current, recurrence_index=new_index)
    return current


def apply_downtime_plan_to_state(
    state: TemporalState,
    plan: DowntimeReconciliationPlan,
    sample: TrustedSample,
) -> TemporalState:
    if plan.expected_state_version != state.state_version:
        raise DowntimeReconciliationError(TEMPORAL_ANCHOR_MISMATCH)
    if plan.expected_state_hash != state.state_hash:
        raise DowntimeReconciliationError(TEMPORAL_ANCHOR_MISMATCH)

    from umbra_core.temporal.events import build_wall_clock_mapping

    new_version = state.state_version + 1
    new_anchor = replace(
        plan.new_time_anchor,
        state_version=new_version,
    )
    new_anchor = with_anchor_state_hash(new_anchor)
    new_mapping = build_wall_clock_mapping(sample, plan.session_id)
    if new_mapping is None:
        new_mapping = state.wall_clock_mapping
    new_uncertainty = (
        sample.wall_time_uncertainty
        if sample.optional_wall_time is not None
        else state.clock_uncertainty
    )
    base = replace(
        state,
        organism_age_ticks=plan.next_age_ticks,
        organism_active_ticks=plan.next_active_ticks,
        last_advance_id=new_anchor.advance_id,
        last_time_anchor=new_anchor,
        wall_clock_mapping=new_mapping,
        clock_uncertainty=new_uncertainty,
        state_version=new_version,
        state_hash="",
    )
    if plan.expectation_recovery_deltas:
        base = apply_expectation_recovery_deltas(base, plan.expectation_recovery_deltas)
    # ponytail: ElapsedEffectPlan declarative effects are recorded on the plan; subsystem
    # apply hooks for physiology/needs are deferred until Task 9+ exposes elapsed reconciliation.
    return with_state_hash(base)


def new_reconciliation_id() -> str:
    return new_id()


def compute_wait_recovery_deltas(
    wait_journal: Any,
    *,
    new_age_ticks: int,
) -> tuple[WaitRecoveryDelta, ...]:
    from umbra_core.wait_execution import NON_TERMINAL_WAIT_STATUSES, SUPPRESSION_DURATION_TICKS

    deltas: list[WaitRecoveryDelta] = []
    for execution in wait_journal.executions.values():
        if execution.status not in NON_TERMINAL_WAIT_STATUSES:
            continue
        if new_age_ticks < execution.deadline_age_tick:
            continue
        deltas.append(
            WaitRecoveryDelta(
                execution_id=execution.execution_id,
                expected_status=execution.status,
                terminal_status="EXPIRED",
                terminal_reason="downtime_window_elapsed",
                suppression_plan={
                    "recurrence_id": execution.recurrence_id,
                    "expectation_version": execution.expectation_version,
                    "suppressed_until_age_tick": execution.deadline_age_tick + SUPPRESSION_DURATION_TICKS,
                },
            )
        )
    return tuple(deltas)


def compute_expectation_recovery_deltas(
    state: TemporalState,
    *,
    new_age_ticks: int,
    predict_fn: Any,
) -> tuple[ExpectationRecoveryDelta, ...]:
    from umbra_core.temporal.policy import policy_expectation_views_from_index
    from umbra_core.temporal.recurrence import get_hypothesis_from_index

    deltas: list[ExpectationRecoveryDelta] = []
    views = policy_expectation_views_from_index(
        state.recurrence_index,
        current_age=new_age_ticks,
        predict_fn=predict_fn,
    )
    for view in views:
        if float(view.window_end) >= float(new_age_ticks):
            continue
        hypothesis = get_hypothesis_from_index(state.recurrence_index, view.recurrence_id)
        if hypothesis is None:
            continue
        action = "EXPIRE" if view.status == "ACTIVE" else "DECAY_CONFIDENCE"
        bounded_delta = -0.05 if action == "DECAY_CONFIDENCE" else 0.0
        deltas.append(
            ExpectationRecoveryDelta(
                recurrence_id=view.recurrence_id,
                expected_hypothesis_version=hypothesis.hypothesis_version,
                expected_expectation_version=view.expectation_version,
                action=action,
                bounded_delta=bounded_delta,
            )
        )
    return tuple(deltas)
