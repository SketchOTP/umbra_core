"""Event retention policy — authoritative vs diagnostic.

Authoritative events are never omitted: they are required for identity,
physiology causality, governance audit, outcome verification, or replay
integrity. Diagnostic events may be sampled or omitted; replay must not
depend on them.
"""

from __future__ import annotations

# D-006 social conceptual events → authority class (ledger type names).
SOCIAL_EVENT_AUTHORITY: dict[str, str] = {
    "social_hypothesis_created": "AUTHORITATIVE",
    "social_hypothesis_merged": "AUTHORITATIVE",
    "social_hypothesis_split": "AUTHORITATIVE",
    "social_hypothesis_contested": "AUTHORITATIVE",
    "social_hypothesis_retired": "AUTHORITATIVE",
    "social_recognition_updated": "AUTHORITATIVE",
    "social_pending_created": "AUTHORITATIVE",
    "social_pending_resolved": "AUTHORITATIVE",
    "social_pending_expired": "AUTHORITATIVE",
    "social_pending_interrupted": "AUTHORITATIVE",
    "social_episode_finalized": "AUTHORITATIVE",
    "social_episode_outcome": "AUTHORITATIVE",
    "social_contingency_updated": "AUTHORITATIVE",
    "social_reliability_revised": "AUTHORITATIVE",
    "social_satiation_anchor_updated": "AUTHORITATIVE",
    "social_routine_promoted": "AUTHORITATIVE",
    "social_routine_deactivated": "AUTHORITATIVE",
    "social_match_score": "DIAGNOSTIC",
}

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
        "world_model_supersede",
        "runtime_ready",
        "memory_correction",
    }
    | {name for name, klass in SOCIAL_EVENT_AUTHORITY.items() if klass == "AUTHORITATIVE"}
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

# Self-model conceptual events → authority class (D-002V Gate 2).
# AUTHORITATIVE: required for accepted body-model provenance / reconstruction contracts.
# DERIVABLE: may be omitted from ledger if deterministic derivation from authoritative
#            inputs + same seed/config is specified.
# DIAGNOSTIC: may be sampled; never required for birth/snapshot replay equality.
SELF_MODEL_EVENT_AUTHORITY: dict[str, str] = {
    # Predictions are recomputed each tick from active schema + params (and retained
    # in snapshot bounded history). Not a ledger event type.
    "action_prediction": "DERIVABLE",
    # Ledger samples every 10 ticks; full history in SelfModel.errors / snapshot
    # (bounded). Birth resimulation recomputes from outcome_verified + body state.
    "prediction_error": "DIAGNOSTIC",
    # Ledger samples every 10 ticks; attributions in snapshot (bounded). Resimulation
    # recomputes from body delta vs prediction without world truth.
    "self_attribution": "DIAGNOSTIC",
    # Accumulated residuals live in SelfModel.change_evidence (snapshot-bounded).
    # Not a ledger event; supersession is the authoritative ledger consequence.
    "body_change_evidence": "DERIVABLE",
    # Every schema rewrite emits body_schema_supersede (no sampling).
    "body_model_supersession": "AUTHORITATIVE",
    # Capability affordance changes are part of BodySchema state (snapshot +
    # supersession). No separate ledger type; not sampled away.
    "capability_degradation": "AUTHORITATIVE",
    "capability_dormancy": "AUTHORITATIVE",
}

# Ledger type aliases used at emit sites for the conceptual names above.
SELF_MODEL_LEDGER_ALIASES: dict[str, str] = {
    "body_model_supersession": "body_schema_supersede",
}

# Bounded in-memory / snapshot history for diagnostic self-model streams.
PREDICTION_HISTORY_BOUND = 256  # matches MAX_PREDICTION_HISTORY / MAX_ERROR_HISTORY
CHANGE_EVIDENCE_BOUND = 64
SUPERSESSION_HISTORY_BOUND = 32  # matches MAX_MODEL_VERSIONS

# Retention / operational policy (not omission of authoritative types).
SNAPSHOT_EVERY_TICKS_DEFAULT = 200
WAL_CHECKPOINT_EVERY_TICKS = 500
COVERAGE_SET_BOUND = 500  # in-memory cells/visited bound (not event ledger)
SNAPSHOT_RETAIN_COUNT = 2  # keep latest N snapshots; ledger remains authoritative

# Cadence for diagnostic self-model ledger samples (identical to sealed D-002).
DIAGNOSTIC_SELF_MODEL_SAMPLE_EVERY_TICKS = 10

# Emitted once after migration/identity/snapshot/bounded-init/loop readiness.
RUNTIME_READY_EVENT = "runtime_ready"


def is_authoritative(event_type: str) -> bool:
    return event_type in AUTHORITATIVE_EVENT_TYPES


def is_diagnostic(event_type: str) -> bool:
    return event_type in DIAGNOSTIC_EVENT_TYPES


def self_model_authority_class(name: str) -> str:
    if name not in SELF_MODEL_EVENT_AUTHORITY:
        raise KeyError(f"unknown_self_model_event:{name}")
    return SELF_MODEL_EVENT_AUTHORITY[name]


def social_event_authority_class(name: str) -> str:
    if name not in SOCIAL_EVENT_AUTHORITY:
        raise KeyError(f"unknown_social_event:{name}")
    return SOCIAL_EVENT_AUTHORITY[name]
