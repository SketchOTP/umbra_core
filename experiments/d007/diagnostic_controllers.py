"""D-007 diagnostic controllers — C2 authored traits / C3 random drift.

These MUST NOT share production IndividualityEngine schemas or influence C0.
Isolated under experiments/d007/ (same pattern as D-006 AffectionController).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umbra_core.individuality.engine import DISPOSITION_DIMENSIONS
from umbra_core.util import SeededRNG, clamp


@dataclass
class AuthoredTraitController:
    """C2: fixed authored trait vector — diagnostic only."""

    traits: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.traits:
            # Distinct authored profile — never written into production state.
            self.traits = {
                "exploration_tendency": 0.8,
                "novelty_tolerance": 0.7,
                "persistence_after_failure": 0.9,
                "uncertainty_caution": -0.6,
                "stimulation_tolerance": 0.5,
                "recovery_pacing": 0.2,
                "activity_timing_preference": 0.4,
                "social_initiative_by_context": 0.85,
            }

    def vector(self) -> dict[str, float]:
        return {d: float(self.traits.get(d, 0.0)) for d in DISPOSITION_DIMENSIONS}

    def fingerprint_proxy(self) -> dict[str, float]:
        return self.vector()


@dataclass
class RandomDriftController:
    """C3: random trait drift with no causal history updates — diagnostic only."""

    seed: int
    traits: dict[str, float] = field(default_factory=dict)
    _rng: SeededRNG | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._rng = SeededRNG(self.seed)
        if not self.traits:
            self.traits = {d: 0.0 for d in DISPOSITION_DIMENSIONS}

    def drift(self, steps: int = 1) -> dict[str, float]:
        assert self._rng is not None
        for _ in range(steps):
            for d in DISPOSITION_DIMENSIONS:
                self.traits[d] = clamp(self.traits[d] + self._rng.gauss(0.0, 0.25), -1.0, 1.0)
        return dict(self.traits)

    def vector(self) -> dict[str, float]:
        return {d: float(self.traits.get(d, 0.0)) for d in DISPOSITION_DIMENSIONS}

    def fingerprint_proxy(self) -> dict[str, float]:
        return self.vector()


def assert_not_production_schema(obj: Any) -> None:
    """Guard: diagnostic controllers must never be serialized into organism snapshots."""
    name = type(obj).__name__
    if name in ("AuthoredTraitController", "RandomDriftController"):
        return
    raise TypeError(f"unexpected_diagnostic:{name}")
