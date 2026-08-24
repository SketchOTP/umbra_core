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


def candidate_to_trace(candidate: Any) -> dict[str, Any] | None:
    if candidate is None:
        return None
    return {
        "capability": str(getattr(candidate, "capability", "")),
        "params": _safe(dict(getattr(candidate, "params", {}) or {})),
        "scores": _safe(dict(getattr(candidate, "scores", {}) or {})),
        "total": float(getattr(candidate, "total", 0.0)),
    }


class DecisionTraceSink:
    """Best-effort file sink. It is never consulted by organism policy."""

    def __init__(self, path: str | None):
        self.path = path
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
            safe_row = _safe(row)
            encoded = json.dumps(safe_row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            record = dict(safe_row)
            record["trace_row_hash"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
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
