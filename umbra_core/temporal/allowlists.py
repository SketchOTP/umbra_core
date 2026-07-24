"""D-010 draft allowlists for authoritative events and observable evidence."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from umbra_core.util import canon_json, sha256_hex

DEFAULT_ALLOWLIST_DIR = Path(__file__).resolve().parents[2] / "experiments" / "d010"
AUTHORITATIVE_ALLOWLIST_NAME = "authoritative-event-allowlist.json"
OBSERVABLE_ALLOWLIST_NAME = "observable-evidence-allowlist.json"


class AllowlistError(Exception):
    """Allowlist load or validation failure."""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AllowlistError(f"allowlist_missing:{path.name}")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise AllowlistError(f"allowlist_invalid:{path.name}")
    return data


def compute_allowlist_hash(data: dict[str, Any]) -> str:
    return sha256_hex(canon_json(data))


@lru_cache(maxsize=4)
def load_authoritative_event_allowlist(
    allowlist_dir: str | None = None,
) -> dict[str, Any]:
    root = Path(allowlist_dir) if allowlist_dir else DEFAULT_ALLOWLIST_DIR
    data = _load_json(root / AUTHORITATIVE_ALLOWLIST_NAME)
    if "allowed_event_kinds" not in data:
        raise AllowlistError("authoritative_allowlist_missing_kinds")
    return data


@lru_cache(maxsize=4)
def load_observable_evidence_allowlist(
    allowlist_dir: str | None = None,
) -> dict[str, Any]:
    root = Path(allowlist_dir) if allowlist_dir else DEFAULT_ALLOWLIST_DIR
    data = _load_json(root / OBSERVABLE_ALLOWLIST_NAME)
    if "allowed_evidence_kinds" not in data:
        raise AllowlistError("observable_allowlist_missing_kinds")
    return data


def assert_authoritative_event_allowed(
    event_kind: str,
    *,
    allowlist_dir: str | None = None,
) -> None:
    allowlist = load_authoritative_event_allowlist(allowlist_dir)
    allowed = set(allowlist["allowed_event_kinds"])
    if event_kind not in allowed:
        raise AllowlistError(f"authoritative_event_disallowed:{event_kind}")


def assert_observable_evidence_allowed(
    evidence_kind: str,
    *,
    allowlist_dir: str | None = None,
) -> None:
    allowlist = load_observable_evidence_allowlist(allowlist_dir)
    allowed = set(allowlist["allowed_evidence_kinds"])
    if evidence_kind not in allowed:
        raise AllowlistError(f"observable_evidence_disallowed:{evidence_kind}")
