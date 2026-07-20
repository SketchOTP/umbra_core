"""Internal physiological state: energy + temperature.

Authority: autonomous drift, elapsed time, authenticated action outcomes,
and controlled experimental intervention only. Policy never assigns values.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
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


ENERGY = Bounds(0.0, 0.35, 0.70, 0.85, 1.0)
TEMPERATURE = Bounds(0.0, 0.30, 0.50, 0.70, 1.0)


@dataclass
class Physiology:
    """Vector-valued internal state H = (energy, temperature)."""

    energy: float = 0.70
    temperature: float = 0.50
    energy_drift: float = -0.008  # deteriorates while idle
    temperature_ambient_pull: float = 0.0  # set by environment region
    # ponytail: ceiling = two variables; upgrade = add integrity/social load later
    locked: bool = False  # experimental clamp
    history: list[tuple[float, float]] = field(default_factory=list)

    def copy(self) -> Physiology:
        return Physiology(
            energy=self.energy,
            temperature=self.temperature,
            energy_drift=self.energy_drift,
            temperature_ambient_pull=self.temperature_ambient_pull,
            locked=self.locked,
            history=list(self.history),
        )

    def as_vector(self) -> tuple[float, float]:
        return (self.energy, self.temperature)

    def ideals(self) -> tuple[float, float]:
        return (ENERGY.ideal, TEMPERATURE.ideal)

    def viable_mask(self) -> tuple[bool, bool]:
        return (ENERGY.in_viable(self.energy), TEMPERATURE.in_viable(self.temperature))

    def critical_any(self) -> bool:
        return ENERGY.critical_violation(self.energy) or TEMPERATURE.critical_violation(
            self.temperature
        )

    def tick_autonomous(self, dt: float = 1.0, drift_enabled: bool = True) -> None:
        """Advance physiology without an action outcome (idle / observer absence)."""
        if self.locked or not drift_enabled:
            self.history.append(self.as_vector())
            return
        self.energy = _clamp(self.energy + self.energy_drift * dt)
        # ambient region slowly pulls temperature
        self.temperature = _clamp(
            self.temperature + self.temperature_ambient_pull * dt * 0.05
        )
        self.history.append(self.as_vector())

    def apply_outcome(
        self,
        *,
        d_energy: float = 0.0,
        d_temperature: float = 0.0,
        drift_enabled: bool = True,
        dt: float = 1.0,
    ) -> None:
        """Apply authenticated external outcome + autonomous drift for the step."""
        if self.locked:
            self.history.append(self.as_vector())
            return
        self.energy = _clamp(self.energy + d_energy)
        self.temperature = _clamp(self.temperature + d_temperature)
        if drift_enabled:
            self.energy = _clamp(self.energy + self.energy_drift * dt)
            self.temperature = _clamp(
                self.temperature + self.temperature_ambient_pull * dt * 0.05
            )
        self.history.append(self.as_vector())

    def intervene(self, energy: float | None = None, temperature: float | None = None) -> None:
        """Controlled experimental intervention (not available to policy)."""
        if energy is not None:
            self.energy = _clamp(energy)
        if temperature is not None:
            self.temperature = _clamp(temperature)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
