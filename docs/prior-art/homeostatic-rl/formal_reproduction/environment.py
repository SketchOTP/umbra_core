"""Minimal spatial environment: food, warm, cool, neutral regions.

Actions are locomotion / consume — never GO_EAT / GO_WARM / GO_COOL commands.
Policy may observe internal state; physiology authority stays in Physiology.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from physiology import Physiology

# Grid positions (x, y). Regions:
# food at (3, 1), warm at (0, 2), cool at (3, 2), start/neutral (1, 1)
FOOD = (3, 1)
WARM = (0, 2)
COOL = (3, 2)
NEUTRAL = (1, 1)

ACTIONS = ("N", "S", "E", "W", "STAY", "CONSUME")
# Forbidden direct need commands (must never appear as actions)
FORBIDDEN_COMMANDS = frozenset({"GO_EAT", "GO_WARM", "GO_COOL"})


@dataclass
class EnvConfig:
    food_pos: tuple[int, int] = FOOD
    warm_pos: tuple[int, int] = WARM
    cool_pos: tuple[int, int] = COOL
    food_energy: float = 0.25
    food_delay: int = 0  # delayed physiological effect (I6)
    action_cost: float = 0.01
    travel_noise: float = 0.0  # uncertain outcome
    deceptive_cue: bool = False  # I7: cue at wrong cell
    resource_abundant: bool = False  # I8
    hide_internal: bool = False
    drift_enabled: bool = True
    prediction_enabled: bool = True  # agent-side; env still causal
    width: int = 4
    height: int = 3


@dataclass
class World:
    cfg: EnvConfig = field(default_factory=EnvConfig)
    pos: tuple[int, int] = NEUTRAL
    phys: Physiology = field(default_factory=Physiology)
    pending_energy: list[tuple[int, float]] = field(default_factory=list)
    t: int = 0
    rng: random.Random = field(default_factory=random.Random)

    def reset(
        self,
        seed: int = 0,
        energy: float | None = None,
        temperature: float | None = None,
        pos: tuple[int, int] | None = None,
    ) -> dict:
        self.rng = random.Random(seed)
        self.t = 0
        self.pos = pos or NEUTRAL
        self.phys = Physiology()
        if energy is not None or temperature is not None:
            self.phys.intervene(energy=energy, temperature=temperature)
        self.pending_energy = []
        self._update_ambient()
        return self.observe()

    def _update_ambient(self) -> None:
        if self.pos == self.cfg.warm_pos:
            self.phys.temperature_ambient_pull = 0.4
        elif self.pos == self.cfg.cool_pos:
            self.phys.temperature_ambient_pull = -0.4
        else:
            self.phys.temperature_ambient_pull = 0.0

    def observe(self) -> dict:
        obs = {
            "x": self.pos[0],
            "y": self.pos[1],
            "at_food": self.pos == self.cfg.food_pos,
            "at_warm": self.pos == self.cfg.warm_pos,
            "at_cool": self.pos == self.cfg.cool_pos,
            "t": self.t,
        }
        if self.cfg.deceptive_cue:
            # cue claims food is at warm cell
            obs["food_cue"] = self.cfg.warm_pos
        else:
            obs["food_cue"] = self.cfg.food_pos
        if not self.cfg.hide_internal:
            obs["energy"] = self.phys.energy
            obs["temperature"] = self.phys.temperature
        else:
            obs["energy"] = None
            obs["temperature"] = None
        return obs

    def step(self, action: str) -> tuple[dict, str, dict]:
        """Returns (obs, event_label, info). Never accepts GO_* commands."""
        if action in FORBIDDEN_COMMANDS:
            raise ValueError(f"forbidden direct need command: {action}")
        if action not in ACTIONS:
            raise ValueError(f"unknown action: {action}")

        before = self.phys.copy()
        d_e, d_t = 0.0, 0.0
        event = "noop"
        moved = False

        x, y = self.pos
        if action == "N":
            y = min(self.cfg.height - 1, y + 1)
            moved = True
        elif action == "S":
            y = max(0, y - 1)
            moved = True
        elif action == "E":
            x = min(self.cfg.width - 1, x + 1)
            moved = True
        elif action == "W":
            x = max(0, x - 1)
            moved = True
        elif action == "STAY":
            event = "noop"
        elif action == "CONSUME":
            if self.pos == self.cfg.food_pos or (
                self.cfg.resource_abundant and self.pos == NEUTRAL
            ):
                amount = self.cfg.food_energy
                if self.cfg.travel_noise > 0:
                    amount *= 1.0 + self.rng.uniform(
                        -self.cfg.travel_noise, self.cfg.travel_noise
                    )
                if self.cfg.food_delay > 0:
                    self.pending_energy.append((self.t + self.cfg.food_delay, amount))
                    event = "food_pending"
                else:
                    d_e += amount
                    event = "food"
            else:
                event = "consume_miss"

        if moved:
            self.pos = (x, y)
            event = "move"
            d_e -= self.cfg.action_cost

        # deliver delayed food
        still = []
        for due, amt in self.pending_energy:
            if due <= self.t + 1:
                d_e += amt
                event = "food"
            else:
                still.append((due, amt))
        self.pending_energy = still

        # region temperature effect on occupy
        self._update_ambient()
        if self.pos == self.cfg.warm_pos and action == "STAY":
            d_t += 0.08
            event = "warm"
        elif self.pos == self.cfg.cool_pos and action == "STAY":
            d_t -= 0.08
            event = "cool"

        self.phys.apply_outcome(
            d_energy=d_e,
            d_temperature=d_t,
            drift_enabled=self.cfg.drift_enabled,
        )
        self.t += 1
        info = {
            "before": before,
            "after": self.phys.copy(),
            "event": event,
            "action": action,
        }
        return self.observe(), event, info
