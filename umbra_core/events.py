"""Event retention policy — authoritative vs diagnostic.

Authoritative events are never omitted: they are required for identity,
physiology causality, governance audit, outcome verification, or replay
integrity. Diagnostic events may be sampled or omitted; replay must not
depend on them.
"""

from __future__ import annotations

# Must be emitted on every occurrence (no cadence skip).
AUTHORITATIVE_EVENT_TYPES = frozenset(
    {
        "birth",
        "physiology_drift",
        "proposal",
        "denial",
        "outcome_verified",
        "restart_recovery",
        "lifecycle",
        "embodiment_bind",
        "body_schema_supersede",
    }
)

# Optional / diagnostic — may be downsampled or omitted; not required for replay.
DIAGNOSTIC_EVENT_TYPES = frozenset(
    {
        "observation",  # not currently emitted; reserved
        "arbitration_scores",  # reserved diagnostic
        "metrics_sample",  # reserved diagnostic
        "self_attribution",  # persisted in snapshot; sample to ledger
        "prediction_error",  # persisted in snapshot; sample to ledger
    }
)

# Retention / operational policy (not omission of authoritative types).
SNAPSHOT_EVERY_TICKS_DEFAULT = 200
WAL_CHECKPOINT_EVERY_TICKS = 500
COVERAGE_SET_BOUND = 500  # in-memory cells/visited bound (not event ledger)


def is_authoritative(event_type: str) -> bool:
    return event_type in AUTHORITATIVE_EVENT_TYPES


def is_diagnostic(event_type: str) -> bool:
    return event_type in DIAGNOSTIC_EVENT_TYPES
