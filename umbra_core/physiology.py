"""Vector physiology — policy may read, never write."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umbra_core.util import clamp


@dataclass(frozen=True)
class Bounds:
    critical_low: float
    viable_low: float
    ideal: float
    viable_high: float
    critical_high: float

    def in_viable(self, x: float) -> bool:
        return self.viable_low <= x <= self.viable_high

    def critical_violation(self, x: float) -> bool:
        return x < self.critical_low or x > self.critical_high

    def deficit(self, x: float) -> float:
        """Positive when below ideal (or above for fatigue-like vars handled by caller)."""
        return self.ideal - x

    def overshoot(self, x: float) -> float:
        if x > self.viable_high:
            return x - self.viable_high
        if x < self.viable_low:
            return self.viable_low - x
        return 0.0


# Fatigue is inverted urgency: high fatigue is bad (ideal low).
BOUNDS: dict[str, Bounds] = {
    "energy": Bounds(0.05, 0.30, 0.70, 0.90, 1.0),
    "fatigue": Bounds(0.0, 0.05, 0.20, 0.70, 0.95),
    "integrity": Bounds(0.05, 0.35, 0.85, 0.98, 1.0),
    "stimulation": Bounds(0.05, 0.25, 0.55, 0.80, 1.0),
}

# Autonomous drift per tick (dt=1.0 at 2 Hz → scale by dt).
DEFAULT_DRIFT = {
    "energy": -0.002,
    "fatigue": 0.002,
    "integrity": -0.0002,
    "stimulation": -0.002,
}


@dataclass
class Physiology:
    energy: float = 0.70
    fatigue: float = 0.20
    integrity: float = 0.90
    stimulation: float = 0.55
    drift_enabled: bool = True
    # ponytail: ceiling = four homeostatic vars; upgrade = social/thermal later
    history_len: int = 0

    def as_dict(self) -> dict[str, float]:
        return {
            "energy": self.energy,
            "fatigue": self.fatigue,
            "integrity": self.integrity,
            "stimulation": self.stimulation,
        }

    def copy(self) -> Physiology:
        return Physiology(
            energy=self.energy,
            fatigue=self.fatigue,
            integrity=self.integrity,
            stimulation=self.stimulation,
            drift_enabled=self.drift_enabled,
            history_len=self.history_len,
        )

    def get(self, name: str) -> float:
        return float(getattr(self, name))

    def set_var(self, name: str, value: float) -> None:
        """Internal write path only (physiology owner / verified outcomes)."""
        setattr(self, name, clamp(value))

    def in_viable(self, name: str | None = None) -> bool:
        if name is None:
            return all(self.in_viable(n) for n in BOUNDS)
        return BOUNDS[name].in_viable(self.get(name))

    def needs_recovery(self) -> list[str]:
        """Variables below/above viable band (includes critical)."""
        out = []
        for n, b in BOUNDS.items():
            x = self.get(n)
            if not b.in_viable(x):
                out.append(n)
        return out

    def critical_any(self) -> bool:
        return any(BOUNDS[n].critical_violation(self.get(n)) for n in BOUNDS)

    def critical_vars(self) -> list[str]:
        return [n for n in BOUNDS if BOUNDS[n].critical_violation(self.get(n))]

    def urgency(self, name: str) -> float:
        """Higher = more need to correct. Fatigue uses excess above ideal."""
        b = BOUNDS[name]
        x = self.get(name)
        if name == "fatigue":
            # want low; urgency rises as fatigue rises above ideal
            return max(0.0, x - b.ideal) + 2.0 * b.overshoot(x)
        # want near ideal; deficit below ideal + overshoot penalty
        return max(0.0, b.ideal - x) + 2.0 * b.overshoot(x)

    def vector_urgency(self) -> dict[str, float]:
        return {n: self.urgency(n) for n in BOUNDS}

    def tick_drift(self, dt: float = 1.0) -> dict[str, float]:
        before = self.as_dict()
        if not self.drift_enabled:
            self.history_len += 1
            return {k: 0.0 for k in before}
        for name, rate in DEFAULT_DRIFT.items():
            self.set_var(name, self.get(name) + rate * dt)
        self.history_len += 1
        after = self.as_dict()
        return {k: after[k] - before[k] for k in before}

    def apply_outcome_effects(self, effects: dict[str, float]) -> None:
        """Apply verified outcome deltas only (never policy-assigned absolute H)."""
        for name, delta in effects.items():
            if name not in BOUNDS:
                continue
            self.set_var(name, self.get(name) + float(delta))

    def intervene(self, **kwargs: float) -> None:
        """Experimental / test intervention — not available to policy."""
        for k, v in kwargs.items():
            if k in BOUNDS:
                self.set_var(k, v)

    def satiation_penalty(self, name: str) -> float:
        """When already in viable band near ideal, further seeking is costly."""
        b = BOUNDS[name]
        x = self.get(name)
        if name == "fatigue":
            # already rested enough
            if x <= b.ideal:
                return 1.0 + (b.ideal - x)
            return 0.0
        if abs(x - b.ideal) < 0.08 and b.in_viable(x):
            return 1.0 + abs(x - b.ideal)
        if x > b.viable_high:
            return 2.0 + (x - b.viable_high)
        return 0.0

    def to_state(self) -> dict[str, Any]:
        d = self.as_dict()
        d["drift_enabled"] = self.drift_enabled
        d["history_len"] = self.history_len
        return d

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> Physiology:
        return cls(
            energy=float(d.get("energy", 0.70)),
            fatigue=float(d.get("fatigue", 0.20)),
            integrity=float(d.get("integrity", 0.90)),
            stimulation=float(d.get("stimulation", 0.55)),
            drift_enabled=bool(d.get("drift_enabled", True)),
            history_len=int(d.get("history_len", 0)),
        )


# Expected physiological effect templates keyed by capability + success.
# Applied only after governance verification.
OUTCOME_EFFECTS: dict[str, dict[str, float]] = {
    "IDLE": {"energy": -0.0005, "fatigue": 0.0005, "stimulation": -0.001, "integrity": 0.02},
    "ORIENT": {"energy": -0.001, "fatigue": 0.001, "stimulation": 0.005},
    "MOVE": {"energy": -0.005, "fatigue": 0.004, "stimulation": 0.003},
    "APPROACH": {"energy": -0.004, "fatigue": 0.003, "stimulation": 0.004},
    "RETREAT": {"energy": -0.005, "fatigue": 0.004, "stimulation": 0.003, "integrity": 0.01},
    "INSPECT": {"energy": -0.003, "fatigue": 0.002, "stimulation": 0.04},
    "REST": {"energy": 0.015, "fatigue": -0.08, "stimulation": -0.02, "integrity": 0.055},
    "CHARGE": {"energy": 0.14, "fatigue": -0.01, "stimulation": -0.005},
    "SIGNAL_PLAY": {"energy": -0.001, "stimulation": 0.01},
    "SIGNAL_ASSISTANCE": {"energy": -0.001, "stimulation": 0.005},
    "HAZARD_HIT": {"integrity": -0.04, "stimulation": 0.02, "energy": -0.006},
    "FAILED_MOVE": {"energy": -0.003, "fatigue": 0.003},
}
