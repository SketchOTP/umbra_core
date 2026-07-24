"""D-009 diagnostic controllers — C2 scripted motion / C3 random manipulation.

Must not be imported by `umbra_core` or share production habitat schemas.
`condition_to_habitat_config` raises for C2/C3 for the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from umbra_core.util import SeededRNG

if TYPE_CHECKING:
    from umbra_core.habitat.engine import HabitatEngine

_AFFORDANCE_REFS = (
    "affordance:resource:use",
    "affordance:rest:activate",
    "affordance:portable:pick_up",
)
_OBJECT_KINDS = ("resource", "rest", "portable", "station")


@dataclass
class ScriptedObjectMovementController:
    """C2: relocate habitat objects on a fixed schedule without governed organism execution."""

    schedule: tuple[tuple[int, str, float, float], ...] = (
        (5, "resource:0", 8.0, 8.0),
        (12, "resource:0", 2.0, 2.0),
        (20, "rest:0", 15.0, 15.0),
    )
    _applied: set[tuple[int, str, float, float]] = field(default_factory=set, repr=False)

    def advance(self, engine: HabitatEngine, tick: int) -> int:
        moved = 0
        for entry in self.schedule:
            if entry[0] != tick or entry in self._applied:
                continue
            _, object_id, x, y = entry
            engine.commit_free_location(object_id, x, y)
            self._applied.add(entry)
            moved += 1
        return moved

    def fingerprint_proxy(self) -> tuple[tuple[int, str, float, float], ...]:
        return self.schedule


@dataclass
class RandomManipulationController:
    """C3: random address/affordance pairs with no perception or history binding."""

    seed: int
    _rng: SeededRNG | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._rng = SeededRNG(self.seed)

    def sample_params(self, tick: int) -> dict[str, Any]:
        assert self._rng is not None
        return {
            "target_address_ref": f"addr:random:{tick}:{self._rng.randint(0, 9999)}",
            "perception_evidence_ref": f"ev:random:{self._rng.randint(0, 9999)}",
            "perception_state_version": self._rng.randint(1, 50),
            "perceived_object_kind": self._rng.choice(list(_OBJECT_KINDS)),
            "perceived_affordance_ref": self._rng.choice(list(_AFFORDANCE_REFS)),
            "kind": self._rng.choice(["USE", "PICK_UP", "PLACE", "ACTIVATE"]),
            "source": "RANDOM_DIAGNOSTIC",
        }

    def fingerprint_proxy(self) -> int:
        return self.seed


_DIAGNOSTIC_CONTROLLER_NAMES = frozenset(
    {"ScriptedObjectMovementController", "RandomManipulationController"}
)


def assert_not_production_schema(obj: object) -> None:
    name = type(obj).__name__
    if name in _DIAGNOSTIC_CONTROLLER_NAMES:
        return
    raise TypeError(f"unexpected_diagnostic:{name}")
