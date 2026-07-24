"""D-010 diagnostic controllers — C2 scripted schedule / C3 random WAIT / C7 hidden schedule.

Must not be imported by `umbra_core.temporal` or share production temporal schemas.
`condition_to_temporal_config` raises for C2/C3/C7 for the same reason.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from umbra_core.util import SeededRNG

_SCRATCH_ROOT = Path(__file__).resolve().parent  # experiments/d010/


@dataclass(frozen=True)
class FutureScheduleEntry:
    tick: int
    recurrence_id: str
    window_start: float
    window_end: float
    confidence: float = 0.95


@dataclass
class ScriptedFutureScheduleController:
    """C2: inject a fixed future schedule without organism-observable evidence."""

    schedule: tuple[FutureScheduleEntry, ...] = (
        FutureScheduleEntry(10, "rec:scripted:a", 12.0, 18.0),
        FutureScheduleEntry(25, "rec:scripted:b", 30.0, 36.0),
    )
    _applied: set[tuple[int, str]] = field(default_factory=set, repr=False)

    def entries_for_tick(self, tick: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for entry in self.schedule:
            key = (entry.tick, entry.recurrence_id)
            if entry.tick != tick or key in self._applied:
                continue
            self._applied.add(key)
            out.append(
                {
                    "recurrence_id": entry.recurrence_id,
                    "window_start": entry.window_start,
                    "window_end": entry.window_end,
                    "confidence": entry.confidence,
                    "source": "SCRIPTED_DIAGNOSTIC",
                }
            )
        return out

    def fingerprint_proxy(self) -> tuple[tuple[int, str, float, float], ...]:
        return tuple(
            (e.tick, e.recurrence_id, e.window_start, e.window_end) for e in self.schedule
        )


@dataclass
class RandomWaitInjectionController:
    """C3: random WAIT / anticipation parameters with no policy binding."""

    seed: int
    _rng: SeededRNG | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._rng = SeededRNG(self.seed)

    def sample_wait_params(self, tick: int) -> dict[str, Any]:
        assert self._rng is not None
        return {
            "recurrence_id": f"rec:random:{self._rng.randint(0, 9999)}",
            "window_start": float(tick + self._rng.randint(1, 5)),
            "window_end": float(tick + self._rng.randint(6, 12)),
            "confidence": self._rng.uniform(0.4, 0.9),
            "source": "RANDOM_DIAGNOSTIC",
        }

    def fingerprint_proxy(self) -> int:
        return self.seed


@dataclass
class HiddenScheduleInjector:
    """C7: authoritative schedule tuples outside production policy construction."""

    injections: tuple[tuple[str, dict[str, Any]], ...] = (
        (
            "hidden:schedule:0",
            {
                "recurrence_id": "rec:hidden:0",
                "window_start": 5.0,
                "window_end": 9.0,
                "authority": "harness_hidden",
            },
        ),
    )

    def payloads(self) -> list[dict[str, Any]]:
        return [
            {"schedule_id": schedule_id, **payload, "source": "HIDDEN_SCHEDULE_DIAGNOSTIC"}
            for schedule_id, payload in self.injections
        ]


_DIAGNOSTIC_CONTROLLER_NAMES = frozenset(
    {
        "ScriptedFutureScheduleController",
        "RandomWaitInjectionController",
        "HiddenScheduleInjector",
    }
)


def assert_not_production_schema(obj: object) -> None:
    name = type(obj).__name__
    if name in _DIAGNOSTIC_CONTROLLER_NAMES:
        return
    raise TypeError(f"unexpected_diagnostic:{name}")


def assert_disposable_db_path(db_path: str | Path) -> None:
    """C8 guard — only tmp or experiments/d010 scratch may be reset."""
    resolved = Path(db_path).resolve()
    tmp_root = Path(tempfile.gettempdir()).resolve()
    allowed_roots = (tmp_root, _SCRATCH_ROOT)
    if any(resolved == root or root in resolved.parents for root in allowed_roots):
        return
    raise ValueError(f"c8_requires_disposable_db_path_got:{resolved}")
