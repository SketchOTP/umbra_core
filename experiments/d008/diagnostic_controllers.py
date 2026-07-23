"""D-008 diagnostic controllers — C1 scripted animation / C2 random
presentation / C3 scalar mood->animation controller — plus a C8
disposable-DB path guard.

These MUST NOT share the production `ExpressionEngine`/`PresentationState`
schema and MUST NOT be importable from `umbra_core` (same isolation pattern
as D-006's `AffectionController` / D-007's `diagnostic_controllers.py`).
`condition_to_expression_config` (umbra_core.expression) raises for C1/C2/C3
precisely so nothing can wire these into the production organism.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from umbra_core.util import SeededRNG

# Deliberately distinct from `umbra_core.expression.presentation_state.POSTURES`
# naming/shape — a schedule of bare labels, not a `PresentationState`.
_SCRIPTED_LABELS: tuple[str, ...] = ("NEUTRAL", "ACTIVE", "OBSERVING", "RESTING", "INTERACTING")


@dataclass
class ScriptedAnimationScheduler:
    """C1: a fixed animation schedule advanced purely by call count — never
    reads physiology, action outcome, attention, or individuality."""

    schedule: tuple[str, ...] = _SCRIPTED_LABELS
    _step: int = field(default=0, repr=False)

    def advance(self) -> str:
        label = self.schedule[self._step % len(self.schedule)]
        self._step += 1
        return label

    def fingerprint_proxy(self) -> tuple[str, ...]:
        return self.schedule


@dataclass
class RandomPresentationController:
    """C2: presentation label drawn from a seeded RNG each step — no causal
    link to action, physiology, attention, or individuality."""

    seed: int
    _rng: SeededRNG | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._rng = SeededRNG(self.seed)

    def advance(self) -> str:
        assert self._rng is not None
        return self._rng.choice(list(_SCRIPTED_LABELS))


@dataclass
class ScalarMoodController:
    """C3: a single externally-set scalar "mood" maps directly to a canned
    label via a fixed lookup table — never derived from real physiology or
    action history, only from whatever the caller pokes into `mood`."""

    mood: float = 0.0

    def render(self) -> str:
        if self.mood >= 0.66:
            return "ACTIVE"
        if self.mood >= 0.33:
            return "NEUTRAL"
        return "RESTING"


_DIAGNOSTIC_CONTROLLER_NAMES = frozenset(
    {"ScriptedAnimationScheduler", "RandomPresentationController", "ScalarMoodController"}
)


def assert_not_production_schema(obj: object) -> None:
    """Guard: diagnostic controllers must never be serialized into organism
    snapshots or accepted by production `ExpressionEngine`/`PresentationState`."""
    name = type(obj).__name__
    if name in _DIAGNOSTIC_CONTROLLER_NAMES:
        return
    raise TypeError(f"unexpected_diagnostic:{name}")


# --- C8: body-profile change resets presentation and organism history —
# design §4 requires this to run only against a disposable experimental DB,
# never a sealed/production persistence path. ---

_SCRATCH_ROOT = Path(__file__).resolve().parent  # experiments/d008/


def assert_disposable_db_path(db_path: str | Path) -> None:
    """Raise unless `db_path` resolves under the system temp directory or
    directly under `experiments/d008/` — the only locations C8 (which
    intentionally resets organism history) is allowed to touch. Rejects any
    path that could collide with sealed evidence, `.agent/`, or a real
    production organism DB."""
    resolved = Path(db_path).resolve()
    tmp_root = Path(tempfile.gettempdir()).resolve()
    allowed_roots = (tmp_root, _SCRATCH_ROOT)
    if any(resolved == root or root in resolved.parents for root in allowed_roots):
        return
    raise ValueError(f"c8_requires_disposable_db_path_got:{resolved}")
