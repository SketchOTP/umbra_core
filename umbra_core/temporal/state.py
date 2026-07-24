"""D-010 TemporalState, TimeAnchor, canonical hashing, and epoch helpers."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from enum import Enum
from typing import Any

from umbra_core.util import canon_json, sha256_hex

TEMPORAL_SCHEMA_VERSION = "d010.temporal-state.v1"
GENESIS_ADVANCE_ID = "advance:genesis"


class AnchorTrustClass(str, Enum):
    TRUSTED_SHORT = "TRUSTED_SHORT"
    UNCERTAIN = "UNCERTAIN"
    EXCESSIVE = "EXCESSIVE"
    MISSING_WALL = "MISSING_WALL"


@dataclass(frozen=True)
class WallClockMapping:
    schema_version: str
    session_id: str
    monotonic_ns_at_mapping: int
    wall_time_seconds: float | None
    wall_time_source: str | None
    uncertainty: float


@dataclass(frozen=True)
class TimeAnchor:
    organism_age_ticks: int
    organism_active_ticks: int
    state_version: int
    state_hash: str
    wall_time: float | None
    wall_time_source: str | None
    wall_time_uncertainty: float
    session_id_at_commit: str
    advance_id: str
    anchor_trust_class: AnchorTrustClass
    trust_reason_codes: tuple[str, ...]
    eligible_as_downtime_baseline: bool
    source_sample_hash: str


@dataclass(frozen=True)
class TemporalState:
    schema_version: str
    temporal_epoch_id: str
    initialized_from_commit: str
    pre_temporal_history_ref: str
    organism_age_ticks: int
    organism_active_ticks: int
    last_committed_orchestration_sequence: int
    last_advance_id: str
    last_time_anchor: TimeAnchor
    wall_clock_mapping: WallClockMapping | None
    clock_uncertainty: float
    recurrence_index: tuple[tuple[str, dict[str, Any]], ...]
    state_version: int
    definition_hash: str
    state_hash: str


def canonical_serialize(value: Any) -> Any:
    """Stable JSON-compatible structure for hashing."""
    return _canonical_value(value)


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_canonical_value(item) for item in value)
    if hasattr(value, "__dataclass_fields__"):
        return {
            field.name: _canonical_value(getattr(value, field.name))
            for field in fields(value)
        }
    raise TypeError(f"unsupported_canonical_type:{type(value)!r}")


def _hash_canonical(value: Any) -> str:
    return sha256_hex(canon_json(canonical_serialize(value)))


def compute_definition_hash(state: TemporalState) -> str:
    payload = {
        "schema_version": state.schema_version,
        "temporal_epoch_id": state.temporal_epoch_id,
        "initialized_from_commit": state.initialized_from_commit,
        "pre_temporal_history_ref": state.pre_temporal_history_ref,
    }
    return _hash_canonical(payload)


def compute_state_hash(state: TemporalState) -> str:
    payload = canonical_serialize(state)
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.pop("state_hash", None)
    return _hash_canonical(payload)


def compute_anchor_state_hash(anchor: TimeAnchor) -> str:
    payload = canonical_serialize(anchor)
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.pop("state_hash", None)
    return _hash_canonical(payload)


def with_state_hash(state: TemporalState) -> TemporalState:
    base = replace(state, state_hash="")
    return replace(base, state_hash=compute_state_hash(base))


def with_anchor_state_hash(anchor: TimeAnchor) -> TimeAnchor:
    base = replace(anchor, state_hash="")
    return replace(base, state_hash=compute_anchor_state_hash(base))


def assert_age_never_decreases(prior_age_ticks: int, new_age_ticks: int) -> None:
    if new_age_ticks < prior_age_ticks:
        raise ValueError(
            f"organism_age_ticks_decreased:{prior_age_ticks}->{new_age_ticks}"
        )


def sample_temporal_state() -> TemporalState:
    """Frozen fixture for definition/state hash stability tests."""
    from umbra_core.temporal.migration import TemporalMigrationContext, initialize_temporal_epoch

    ctx = TemporalMigrationContext(
        migration_id="d010.genesis.v1",
        source_commit="af35371",
        source_seal="UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED",
        pre_temporal_history_ref="event-log:pre-d010",
        genesis_session_id="session:genesis",
        genesis_monotonic_ns=1_000_000,
        genesis_sample_sequence=0,
    )
    return initialize_temporal_epoch(None, ctx=ctx)
