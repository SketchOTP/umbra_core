"""D-010 temporal event payloads, envelopes, apply/replay helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from umbra_core.temporal.clock import TrustedSample
from umbra_core.temporal.observations import DedupSummary
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

if TYPE_CHECKING:
    from umbra_core.temporal.engine import TemporalAdvancePlan


class TemporalEngineError(Exception):
    """TemporalEngine invariant violation."""


class TemporalReplayError(Exception):
    """Fail-closed temporal replay / ledger reconstruction."""


ORCHESTRATION_TICK_COMMITTED = "orchestration_tick_committed"
TEMPORAL_ANCHOR_COMMITTED = "temporal_anchor_committed"
TEMPORAL_INITIALIZED = "temporal_initialized"


@dataclass(frozen=True)
class TemporalAdvanceRecord:
    advance_id: str
    orchestration_sequence: int
    trusted_sample_hash: str
    prior_state_version: int
    new_state_version: int
    prior_state_hash: str
    new_state_hash: str
    prior_age_ticks: int
    new_age_ticks: int
    prior_active_ticks: int
    new_active_ticks: int
    prior_time_anchor: TimeAnchor
    new_time_anchor: TimeAnchor
    prior_wall_clock_mapping: WallClockMapping | None
    new_wall_clock_mapping: WallClockMapping | None
    prior_clock_uncertainty: float
    new_clock_uncertainty: float


@dataclass(frozen=True)
class TemporalContainedEvent:
    event_kind: str
    transaction_event_index: int
    payload_hash: str


@dataclass(frozen=True)
class TemporalTransactionEnvelope:
    transaction_id: str
    prior_state_version: int
    new_state_version: int
    prior_state_hash: str
    new_state_hash: str
    ordered_events: tuple[TemporalContainedEvent, ...]


def _payload_hash(payload: dict[str, Any]) -> str:
    return sha256_hex(canon_json(canonical_serialize(payload)))


def _anchor_to_dict(anchor: TimeAnchor) -> dict[str, Any]:
    return canonical_serialize(anchor)


def _anchor_from_dict(data: dict[str, Any]) -> TimeAnchor:
    return TimeAnchor(
        organism_age_ticks=int(data["organism_age_ticks"]),
        organism_active_ticks=int(data["organism_active_ticks"]),
        state_version=int(data["state_version"]),
        state_hash=str(data["state_hash"]),
        wall_time=data.get("wall_time"),
        wall_time_source=data.get("wall_time_source"),
        wall_time_uncertainty=float(data["wall_time_uncertainty"]),
        session_id_at_commit=str(data["session_id_at_commit"]),
        advance_id=str(data["advance_id"]),
        anchor_trust_class=AnchorTrustClass(str(data["anchor_trust_class"])),
        trust_reason_codes=tuple(str(x) for x in data["trust_reason_codes"]),
        eligible_as_downtime_baseline=bool(data["eligible_as_downtime_baseline"]),
        source_sample_hash=str(data["source_sample_hash"]),
    )


def _mapping_to_dict(mapping: WallClockMapping | None) -> dict[str, Any] | None:
    if mapping is None:
        return None
    return canonical_serialize(mapping)


def _mapping_from_dict(data: dict[str, Any] | None) -> WallClockMapping | None:
    if data is None:
        return None
    return WallClockMapping(
        schema_version=str(data["schema_version"]),
        session_id=str(data["session_id"]),
        monotonic_ns_at_mapping=int(
            data.get("monotonic_ns_at_mapping", data.get("monotonic_ns", 0))
        ),
        wall_time_seconds=data.get("wall_time_seconds"),
        wall_time_source=data.get("wall_time_source"),
        uncertainty=float(data["uncertainty"]),
    )


def advance_record_to_dict(record: TemporalAdvanceRecord) -> dict[str, Any]:
    return {
        "advance_id": record.advance_id,
        "orchestration_sequence": record.orchestration_sequence,
        "trusted_sample_hash": record.trusted_sample_hash,
        "prior_state_version": record.prior_state_version,
        "new_state_version": record.new_state_version,
        "prior_state_hash": record.prior_state_hash,
        "new_state_hash": record.new_state_hash,
        "prior_age_ticks": record.prior_age_ticks,
        "new_age_ticks": record.new_age_ticks,
        "prior_active_ticks": record.prior_active_ticks,
        "new_active_ticks": record.new_active_ticks,
        "prior_time_anchor": _anchor_to_dict(record.prior_time_anchor),
        "new_time_anchor": _anchor_to_dict(record.new_time_anchor),
        "prior_wall_clock_mapping": _mapping_to_dict(record.prior_wall_clock_mapping),
        "new_wall_clock_mapping": _mapping_to_dict(record.new_wall_clock_mapping),
        "prior_clock_uncertainty": record.prior_clock_uncertainty,
        "new_clock_uncertainty": record.new_clock_uncertainty,
    }


def advance_record_from_dict(data: dict[str, Any]) -> TemporalAdvanceRecord:
    return TemporalAdvanceRecord(
        advance_id=str(data["advance_id"]),
        orchestration_sequence=int(data["orchestration_sequence"]),
        trusted_sample_hash=str(data["trusted_sample_hash"]),
        prior_state_version=int(data["prior_state_version"]),
        new_state_version=int(data["new_state_version"]),
        prior_state_hash=str(data["prior_state_hash"]),
        new_state_hash=str(data["new_state_hash"]),
        prior_age_ticks=int(data["prior_age_ticks"]),
        new_age_ticks=int(data["new_age_ticks"]),
        prior_active_ticks=int(data["prior_active_ticks"]),
        new_active_ticks=int(data["new_active_ticks"]),
        prior_time_anchor=_anchor_from_dict(data["prior_time_anchor"]),
        new_time_anchor=_anchor_from_dict(data["new_time_anchor"]),
        prior_wall_clock_mapping=_mapping_from_dict(data.get("prior_wall_clock_mapping")),
        new_wall_clock_mapping=_mapping_from_dict(data.get("new_wall_clock_mapping")),
        prior_clock_uncertainty=float(data["prior_clock_uncertainty"]),
        new_clock_uncertainty=float(data["new_clock_uncertainty"]),
    )


def envelope_to_dict(envelope: TemporalTransactionEnvelope) -> dict[str, Any]:
    return {
        "transaction_id": envelope.transaction_id,
        "prior_state_version": envelope.prior_state_version,
        "new_state_version": envelope.new_state_version,
        "prior_state_hash": envelope.prior_state_hash,
        "new_state_hash": envelope.new_state_hash,
        "ordered_events": [
            {
                "event_kind": event.event_kind,
                "transaction_event_index": event.transaction_event_index,
                "payload_hash": event.payload_hash,
            }
            for event in envelope.ordered_events
        ],
    }


def envelope_from_dict(data: dict[str, Any]) -> TemporalTransactionEnvelope:
    return TemporalTransactionEnvelope(
        transaction_id=str(data["transaction_id"]),
        prior_state_version=int(data["prior_state_version"]),
        new_state_version=int(data["new_state_version"]),
        prior_state_hash=str(data["prior_state_hash"]),
        new_state_hash=str(data["new_state_hash"]),
        ordered_events=tuple(
            TemporalContainedEvent(
                event_kind=str(item["event_kind"]),
                transaction_event_index=int(item["transaction_event_index"]),
                payload_hash=str(item["payload_hash"]),
            )
            for item in data["ordered_events"]
        ),
    )


def build_time_anchor(
    *,
    plan: Any,
    sample: TrustedSample,
    session_id: str,
    age_ticks: int,
    active_ticks: int,
    state_version: int,
) -> TimeAnchor:
    if sample.optional_wall_time is not None:
        trust_class = AnchorTrustClass.TRUSTED_SHORT
        trust_reasons = ("wall_sample_present",)
        eligible = True
    else:
        trust_class = AnchorTrustClass.MISSING_WALL
        trust_reasons = ("no_wall_sample",)
        eligible = False
    anchor = TimeAnchor(
        organism_age_ticks=age_ticks,
        organism_active_ticks=active_ticks,
        state_version=state_version,
        state_hash="",
        wall_time=sample.optional_wall_time,
        wall_time_source=sample.wall_time_source,
        wall_time_uncertainty=sample.wall_time_uncertainty,
        session_id_at_commit=session_id,
        advance_id=plan.advance_id,
        anchor_trust_class=trust_class,
        trust_reason_codes=trust_reasons,
        eligible_as_downtime_baseline=eligible,
        source_sample_hash=plan.trusted_sample_hash,
    )
    return with_anchor_state_hash(anchor)


def build_wall_clock_mapping(sample: TrustedSample, session_id: str) -> WallClockMapping | None:
    if sample.optional_wall_time is None:
        return None
    return WallClockMapping(
        schema_version="d010.wall-mapping.v1",
        session_id=session_id,
        monotonic_ns_at_mapping=sample.monotonic_ns,
        wall_time_seconds=sample.optional_wall_time,
        wall_time_source=sample.wall_time_source,
        uncertainty=sample.wall_time_uncertainty,
    )


def apply_advance_plan(
    state: TemporalState,
    plan: Any,
    sample: TrustedSample,
    session_id: str,
) -> TemporalState:
    if plan.expected_state_version != state.state_version:
        raise TemporalEngineError("expected_state_version_mismatch")
    if plan.expected_state_hash != state.state_hash:
        raise TemporalEngineError("expected_state_hash_mismatch")
    if plan.advance_id == state.last_advance_id:
        raise TemporalEngineError("advance_id_already_committed")

    new_version = state.state_version + 1
    new_anchor = build_time_anchor(
        plan=plan,
        sample=sample,
        session_id=session_id,
        age_ticks=plan.next_age_ticks,
        active_ticks=plan.next_active_ticks,
        state_version=new_version,
    )
    new_mapping = build_wall_clock_mapping(sample, session_id)
    if new_mapping is None:
        new_mapping = state.wall_clock_mapping
    new_uncertainty = (
        sample.wall_time_uncertainty
        if sample.optional_wall_time is not None
        else state.clock_uncertainty
    )

    from dataclasses import replace

    base = replace(
        state,
        organism_age_ticks=plan.next_age_ticks,
        organism_active_ticks=plan.next_active_ticks,
        last_committed_orchestration_sequence=plan.orchestration_sequence,
        last_advance_id=plan.advance_id,
        last_time_anchor=new_anchor,
        wall_clock_mapping=new_mapping,
        clock_uncertainty=new_uncertainty,
        state_version=new_version,
        state_hash="",
    )
    return with_state_hash(base)


def build_advance_record(
    prior_state: TemporalState,
    new_state: TemporalState,
    plan: Any,
) -> TemporalAdvanceRecord:
    return TemporalAdvanceRecord(
        advance_id=plan.advance_id,
        orchestration_sequence=plan.orchestration_sequence,
        trusted_sample_hash=plan.trusted_sample_hash,
        prior_state_version=prior_state.state_version,
        new_state_version=new_state.state_version,
        prior_state_hash=prior_state.state_hash,
        new_state_hash=new_state.state_hash,
        prior_age_ticks=prior_state.organism_age_ticks,
        new_age_ticks=new_state.organism_age_ticks,
        prior_active_ticks=prior_state.organism_active_ticks,
        new_active_ticks=new_state.organism_active_ticks,
        prior_time_anchor=prior_state.last_time_anchor,
        new_time_anchor=new_state.last_time_anchor,
        prior_wall_clock_mapping=prior_state.wall_clock_mapping,
        new_wall_clock_mapping=new_state.wall_clock_mapping,
        prior_clock_uncertainty=prior_state.clock_uncertainty,
        new_clock_uncertainty=new_state.clock_uncertainty,
    )


def build_tick_transaction_envelope(
    *,
    transaction_id: str,
    prior_state: TemporalState,
    new_state: TemporalState,
    record: TemporalAdvanceRecord,
) -> TemporalTransactionEnvelope:
    record_payload = advance_record_to_dict(record)
    return TemporalTransactionEnvelope(
        transaction_id=transaction_id,
        prior_state_version=prior_state.state_version,
        new_state_version=new_state.state_version,
        prior_state_hash=prior_state.state_hash,
        new_state_hash=new_state.state_hash,
        ordered_events=(
            TemporalContainedEvent(
                event_kind="temporal_tick_advance",
                transaction_event_index=0,
                payload_hash=_payload_hash(record_payload),
            ),
        ),
    )


def build_orchestration_tick_payload(
    *,
    orchestration_sequence: int,
    runtime_tick: int,
    record: TemporalAdvanceRecord,
    envelope: TemporalTransactionEnvelope,
) -> dict[str, Any]:
    return {
        "orchestration_sequence": orchestration_sequence,
        "runtime_tick": runtime_tick,
        "temporal_advance_record": advance_record_to_dict(record),
        "temporal_transaction": envelope_to_dict(envelope),
    }


def new_transaction_id() -> str:
    return f"txn:{new_id()}"


def apply_advance_record(state: TemporalState, record: TemporalAdvanceRecord) -> TemporalState:
    if record.prior_state_version != state.state_version:
        raise TemporalReplayError("prior_state_version_mismatch")
    if record.prior_state_hash != state.state_hash:
        raise TemporalReplayError("prior_state_hash_mismatch")
    if record.prior_age_ticks != state.organism_age_ticks:
        raise TemporalReplayError("prior_age_mismatch")
    new_state = _state_from_record_tail(state, record)
    if record.new_state_hash != new_state.state_hash:
        raise TemporalReplayError("new_state_hash_mismatch")
    return new_state


def _state_from_record_tail(state: TemporalState, record: TemporalAdvanceRecord) -> TemporalState:
    from dataclasses import replace

    return replace(
        state,
        organism_age_ticks=record.new_age_ticks,
        organism_active_ticks=record.new_active_ticks,
        last_committed_orchestration_sequence=record.orchestration_sequence,
        last_advance_id=record.advance_id,
        last_time_anchor=record.new_time_anchor,
        wall_clock_mapping=record.new_wall_clock_mapping,
        clock_uncertainty=record.new_clock_uncertainty,
        state_version=record.new_state_version,
        state_hash=record.new_state_hash,
    )


def replay_temporal_state_from_events(
    genesis: TemporalState,
    events: list[dict[str, Any]],
    *,
    require_advance_record: bool = True,
) -> TemporalState:
    state = genesis
    seen_advance_ids: set[str] = set()
    for event in events:
        if event.get("event_type") != ORCHESTRATION_TICK_COMMITTED:
            continue
        payload = event.get("payload") or {}
        raw_record = payload.get("temporal_advance_record")
        if raw_record is None:
            if require_advance_record:
                raise TemporalReplayError("missing_temporal_advance_record")
            continue
        record = advance_record_from_dict(raw_record)
        if record.advance_id in seen_advance_ids:
            raise TemporalReplayError("duplicate_advance_id")
        seen_advance_ids.add(record.advance_id)
        state = apply_advance_record(state, record)
    return state


def temporal_state_to_dict(state: TemporalState) -> dict[str, Any]:
    return canonical_serialize(state)


def temporal_state_from_dict(data: dict[str, Any]) -> TemporalState:
    anchor_data = data["last_time_anchor"]
    mapping_data = data.get("wall_clock_mapping")
    return TemporalState(
        schema_version=str(data["schema_version"]),
        temporal_epoch_id=str(data["temporal_epoch_id"]),
        initialized_from_commit=str(data["initialized_from_commit"]),
        pre_temporal_history_ref=str(data["pre_temporal_history_ref"]),
        organism_age_ticks=int(data["organism_age_ticks"]),
        organism_active_ticks=int(data["organism_active_ticks"]),
        last_committed_orchestration_sequence=int(data["last_committed_orchestration_sequence"]),
        last_advance_id=str(data["last_advance_id"]),
        last_time_anchor=_anchor_from_dict(anchor_data),
        wall_clock_mapping=_mapping_from_dict(mapping_data),
        clock_uncertainty=float(data["clock_uncertainty"]),
        recurrence_index=tuple(
            (str(k), dict(v)) for k, v in (data.get("recurrence_index") or [])
        ),
        dedup_summary=DedupSummary.from_dict(data.get("dedup_summary")),
        observation_miss_keys=tuple(
            str(x) for x in (data.get("observation_miss_keys") or [])
        ),
        state_version=int(data["state_version"]),
        definition_hash=str(data["definition_hash"]),
        state_hash=str(data["state_hash"]),
    )
