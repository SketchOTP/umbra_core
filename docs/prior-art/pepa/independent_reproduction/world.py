"""Deterministic embodied micro-world for Track 6 PEPA mechanism tests.

ponytail: ceiling = discrete grid + fixed skill set; upgrade = continuous kinematics.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


# Fixed Sys1 skill repertoire (PEPA-style bounded action set).
SKILLS = (
    "idle",
    "move",
    "eat",
    "play",
    "social",
    "explore",
    "charge",
    "rest",
)

UNSAFE_WHEN_CRITICAL = frozenset({"explore", "play", "social", "move"})


@dataclass
class Body:
    """Embodiment costs and capability binding."""

    battery: float = 0.85
    fatigue: float = 0.1
    position: int = 0  # 0..n_cells-1
    body_id: str = "virtual-quad"
    skills: tuple[str, ...] = SKILLS
    cost_scale: float = 1.0  # 0.0 = C8 no embodiment costs


@dataclass
class Physiology:
    """Homeostatic drives (Track 2 lineage) — not authored personality."""

    energy: float = 0.75
    play: float = 0.45
    social: float = 0.45
    curiosity: float = 0.45
    energy_drift: float = -0.0025
    play_drift: float = 0.0015
    social_drift: float = 0.0015
    curiosity_drift: float = 0.0012

    def copy(self) -> Physiology:
        return Physiology(
            energy=self.energy,
            play=self.play,
            social=self.social,
            curiosity=self.curiosity,
            energy_drift=self.energy_drift,
            play_drift=self.play_drift,
            social_drift=self.social_drift,
            curiosity_drift=self.curiosity_drift,
        )

    def tick(self) -> None:
        self.energy = _clamp(self.energy + self.energy_drift)
        self.play = _clamp(self.play + self.play_drift)
        self.social = _clamp(self.social + self.social_drift)
        self.curiosity = _clamp(self.curiosity + self.curiosity_drift)

    def drives(self) -> dict[str, float]:
        # higher = more urgent need (deviation from satiated high-energy / low-drive)
        return {
            "energy": max(0.0, 0.75 - self.energy),
            "play": self.play,
            "social": self.social,
            "curiosity": self.curiosity,
        }

    def critical_energy(self) -> bool:
        return self.energy < 0.25

    def viable(self) -> bool:
        return self.energy > 0.05


@dataclass
class World:
    n_cells: int = 8
    food_cells: set[int] = field(default_factory=lambda: {1, 5})
    play_cells: set[int] = field(default_factory=lambda: {2, 6})
    social_cells: set[int] = field(default_factory=lambda: {3})
    charge_cell: int = 0
    partner_reliable: bool = True
    scarcity: bool = False
    layout_epoch: int = 0
    tick: int = 0
    rng: random.Random = field(default_factory=random.Random)

    def reset(self, seed: int, history: str = "H0") -> None:
        self.rng = random.Random(seed ^ (self.layout_epoch * 9973))
        self.tick = 0
        self.food_cells = {1, 5}
        self.play_cells = {2, 6}
        self.social_cells = {3}
        self.charge_cell = 0
        self.partner_reliable = True
        self.scarcity = False
        self._apply_history(history)

    def _apply_history(self, history: str) -> None:
        if history == "H5":
            self.scarcity = True
            self.food_cells = {1}
        elif history == "H3":
            self.partner_reliable = True
        elif history == "H4":
            self.partner_reliable = False
        elif history == "H6":
            # layout change mid-life applied via mutate_layout
            pass

    def mutate_layout(self) -> None:
        self.layout_epoch += 1
        # rotate resource locations
        self.food_cells = {(c + 2) % self.n_cells for c in self.food_cells}
        self.play_cells = {(c + 2) % self.n_cells for c in self.play_cells}
        self.social_cells = {(c + 1) % self.n_cells for c in self.social_cells}

    def step(self, body: Body, phys: Physiology, action: str) -> dict[str, Any]:
        """Execute one skill; return outcome record."""
        self.tick += 1
        phys.tick()
        if action not in body.skills:
            return {"ok": False, "reason": "unknown_skill", "action": action}

        cost = _action_cost(action) * body.cost_scale
        body.battery = _clamp(body.battery - cost * 0.012)
        body.fatigue = _clamp(body.fatigue + cost * 0.008)
        phys.energy = _clamp(phys.energy - cost * 0.008)

        outcome: dict[str, Any] = {
            "ok": True,
            "action": action,
            "pos": body.position,
            "reward_proxy": 0.0,
        }

        if action == "idle":
            outcome["reward_proxy"] = 0.0
        elif action == "rest":
            body.fatigue = _clamp(body.fatigue - 0.05)
            phys.energy = _clamp(phys.energy + 0.01)
            outcome["reward_proxy"] = 0.05
        elif action == "charge":
            if body.position == self.charge_cell:
                body.battery = _clamp(body.battery + 0.12)
                phys.energy = _clamp(phys.energy + 0.08)
                outcome["reward_proxy"] = 0.3
                outcome["charged"] = True
            else:
                outcome["ok"] = False
                outcome["reason"] = "not_at_charger"
        elif action == "move":
            body.position = (body.position + 1) % self.n_cells
            outcome["pos"] = body.position
            outcome["reward_proxy"] = 0.01
        elif action == "eat":
            if body.position in self.food_cells:
                gain = 0.08 if not self.scarcity else 0.04
                if self.scarcity and self.rng.random() < 0.4:
                    outcome["ok"] = False
                    outcome["reason"] = "scarce_miss"
                else:
                    phys.energy = _clamp(phys.energy + gain)
                    outcome["reward_proxy"] = 0.25
                    outcome["ate"] = True
            else:
                outcome["ok"] = False
                outcome["reason"] = "no_food"
        elif action == "play":
            if body.position in self.play_cells:
                # satiation: play drive decreases when satisfied via play
                before = phys.play
                phys.play = _clamp(phys.play - 0.12)
                outcome["reward_proxy"] = 0.2 * before
                outcome["played"] = True
            else:
                # failed play histories still attempt but fail more
                outcome["ok"] = False
                outcome["reason"] = "no_play_spot"
        elif action == "social":
            if body.position in self.social_cells:
                if self.partner_reliable or self.rng.random() < 0.35:
                    before = phys.social
                    phys.social = _clamp(phys.social - 0.12)
                    outcome["reward_proxy"] = 0.2 * before
                    outcome["social_ok"] = True
                else:
                    outcome["ok"] = False
                    outcome["reason"] = "unreliable_partner"
                    phys.social = _clamp(phys.social + 0.03)
            else:
                outcome["ok"] = False
                outcome["reason"] = "no_partner"
        elif action == "explore":
            body.position = self.rng.randrange(self.n_cells)
            before = phys.curiosity
            phys.curiosity = _clamp(phys.curiosity - 0.1)
            outcome["reward_proxy"] = 0.15 * before
            outcome["explored"] = True
            outcome["pos"] = body.position

        if body.battery < 0.08 or not phys.viable():
            outcome["viability_fail"] = True
        return outcome


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _action_cost(action: str) -> float:
    return {
        "idle": 0.2,
        "rest": 0.3,
        "charge": 0.5,
        "move": 1.0,
        "eat": 0.8,
        "play": 1.2,
        "social": 1.0,
        "explore": 1.5,
    }.get(action, 1.0)
