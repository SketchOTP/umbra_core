"""Default-disabled, non-authoritative production decision tracing for D-014H2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else str(value)
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, set):
        return sorted((_safe(v) for v in value), key=lambda item: repr(item))
    if hasattr(value, "to_dict"):
        try:
            return _safe(value.to_dict())
        except Exception:
            return "<unserializable>"
    return str(value)


def canonical_fingerprint(value: Any) -> str:
    payload = json.dumps(_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def trace_row_hash(row: dict[str, Any]) -> str:
    """Hash a trace row without its derived identity field."""
    base = dict(row)
    base.pop("trace_row_hash", None)
    return canonical_fingerprint(base)


def verify_trace_row_hash(row: dict[str, Any]) -> bool:
    stored = row.get("trace_row_hash")
    return isinstance(stored, str) and stored == trace_row_hash(row)


def candidate_to_trace(candidate: Any) -> dict[str, Any] | None:
    if candidate is None:
        return None
    return {
        "capability": str(getattr(candidate, "capability", "")),
        "params": _safe(dict(getattr(candidate, "params", {}) or {})),
        "scores": _safe(dict(getattr(candidate, "scores", {}) or {})),
        "total": float(getattr(candidate, "total", 0.0)),
    }


def _compact_distributed_competition(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    keep = (
        "schema",
        "admissible_candidate_count",
        "applicable_channel_count",
        "distributed_changed_winner",
        "eliminated_candidate_count",
        "frontier_equals_full_pool",
        "frontier_full_pool_ratio",
        "frontier_size",
        "pairwise_dominance_count",
        "selected_identity",
        "stochastic_resolution_required",
        "supported_count_by_channel",
        "unknown_count_by_channel",
    )
    result = {key: value[key] for key in keep if key in value}
    continuation = value.get("continuation")
    if isinstance(continuation, dict):
        result["continuation"] = {
            key: continuation[key]
            for key in ("root_fingerprint", "root_size", "survivor_count", "unknown_rate")
            if key in continuation
        }
    return result


_COMPACT_FIELDS = (
    "tick",
    "decision_cycle",
    "active_ticks",
    "organism_age",
    "physiology",
    "body_schema_generation",
    "policy_observation_fingerprint",
    "critical_recovery_context",
    "base_candidate",
    "final_candidate",
    "final_candidate_lineage",
    "final_safety_transition",
    "final_authority_reachable_effect_branches",
    "governance_proposal",
    "governance_decision",
    "verified_outcome_linkage",
    "verified_executability_denials",
    "viability_kernel",
    "recovery_certificate_continuation",
)


def compact_acceptance_row(row: dict[str, Any]) -> dict[str, Any]:
    """Project one trace row without recursively copying diagnostic bulk."""
    compact = {key: row[key] for key in _COMPACT_FIELDS if key in row}
    compact["schema"] = "AS017_ACCEPTANCE_TRACE_ROW_V1"
    competition = _compact_distributed_competition(row.get("distributed_competition"))
    if competition is not None:
        compact["distributed_competition_summary"] = competition
    compact["omitted_diagnostic_fields"] = {
        key: key in row
        for key in (
            "distributed_competition",
            "development_transition",
            "memory_transition",
            "social_transition",
            "world_model_transition",
            "individuality_context",
            "manipulation_bindings",
            "temporal_proposals_or_modifiers",
        )
    }
    return compact


class DecisionTraceSink:
    """Best-effort file sink. It is never consulted by organism policy."""

    def __init__(self, path: str | None, *, mode: str = "full"):
        self.path = path
        self.mode = mode
        self._handle = None
        if not path:
            return
        try:
            destination = Path(path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            self._handle = destination.open("a", encoding="utf-8", buffering=1)
        except Exception:
            self._handle = None

    @property
    def enabled(self) -> bool:
        return self._handle is not None

    def record(self, row: dict[str, Any]) -> bool:
        if self._handle is None:
            return False
        try:
            source_row = row
            if self.mode == "compact_acceptance":
                source_row = compact_acceptance_row(row)
            elif self.mode != "full":
                raise ValueError(f"unknown_decision_trace_mode:{self.mode}")
            safe_row = _safe(source_row)
            encoded = json.dumps(safe_row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            record = dict(safe_row)
            record["trace_row_hash"] = trace_row_hash(safe_row)
            self._handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
            self._handle.flush()
            return True
        except Exception:
            return False

    def close(self) -> None:
        handle, self._handle = self._handle, None
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass
