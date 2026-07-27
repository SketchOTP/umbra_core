"""Atomic, versioned, checksummed bounded supervisor progress."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from .durability import atomic_write_text
from .failure_codes import SupervisionError
class ProgressStore:
    def __init__(self, path: Path) -> None: self.path = path
    def save(self, state: dict[str, object]) -> None:
        body = {"version": 1, "state": state}
        body["checksum"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        atomic_write_text(self.path, json.dumps(body, sort_keys=True))
    def load(self) -> dict[str, object]:
        try: body = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError) as exc: raise SupervisionError("PROGRESS_STATE_CORRUPT", str(exc)) from exc
        checksum = body.pop("checksum", None)
        expected = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if body.get("version") != 1 or checksum != expected: raise SupervisionError("PROGRESS_STATE_CORRUPT")
        return dict(body["state"])
