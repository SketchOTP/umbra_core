"""Policies for causal conditions C0–C8.

No GO_EAT / GO_WARM / GO_COOL actions — locomotion + CONSUME only.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from drives import DRIVES, drive_components, signed_deviations
from environment import ACTIONS, COOL, FOOD, WARM, World
from physiology import Physiology
from rewards import hardcoded_need_action


def _toward(pos: tuple[int, int], target: tuple[int, int], rng: random.Random) -> str:
    x, y = pos
    tx, ty = target
    opts = []
    if x < tx:
        opts.append("E")
    if x > tx:
        opts.append("W")
    if y < ty:
        opts.append("N")
    if y > ty:
        opts.append("S")
    if not opts:
        return "STAY"
    return rng.choice(opts)


def _path_len(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class RandomPolicy:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def act(self, obs: dict, world: World) -> str:
        del world
        return self.rng.choice(ACTIONS)


class FixedExternalRewardGreedy:
    """C1: chase food cue for fixed external reward (ignores physiology)."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def act(self, obs: dict, world: World) -> str:
        cue = obs.get("food_cue", world.cfg.food_pos)
        if obs["at_food"]:
            return "CONSUME"
        return _toward((obs["x"], obs["y"]), cue, self.rng)


class HardcodedNeedPriority:
    """C2 / R4 negative control."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def act(self, obs: dict, world: World) -> str:
        intent = hardcoded_need_action(world.phys)
        pos = (obs["x"], obs["y"])
        if intent == "SEEK_FOOD":
            if obs["at_food"]:
                return "CONSUME"
            return _toward(pos, world.cfg.food_pos, self.rng)
        if intent == "SEEK_WARM":
            if obs["at_warm"]:
                return "STAY"
            return _toward(pos, world.cfg.warm_pos, self.rng)
        if intent == "SEEK_COOL":
            if obs["at_cool"]:
                return "STAY"
            return _toward(pos, world.cfg.cool_pos, self.rng)
        return "STAY"


class DriveReductionMyopic:
    """C3/C4: one-step lookahead maximizing drive reduction (or neg-drive)."""

    def __init__(self, seed: int = 0, mode: str = "reduction", drive: str = "D3") -> None:
        self.rng = random.Random(seed)
        self.mode = mode
        self.drive = DRIVES[drive]

    def act(self, obs: dict, world: World) -> str:
        # If internal hidden, fall back to external greedy
        if obs.get("energy") is None:
            return FixedExternalRewardGreedy(self.rng.randint(0, 10**9)).act(obs, world)

        best_a = "STAY"
        best_v = float("-inf")
        for a in ACTIONS:
            # simulate without mutating world: copy
            sim = World(cfg=world.cfg, pos=world.pos, phys=world.phys.copy(), t=world.t)
            sim.rng = random.Random(self.rng.randint(0, 10**9))
            sim.pending_energy = list(world.pending_energy)
            before = sim.phys.copy()
            try:
                _, event, info = sim.step(a)
            except ValueError:
                continue
            after = info["after"]
            if self.mode == "neg_drive":
                v = -self.drive(after)
            else:
                v = self.drive(before) - self.drive(after)
            # small noise break ties
            v += self.rng.random() * 1e-6
            if v > best_v:
                best_v = v
                best_a = a
        return best_a


class AnticipatoryDriveReduction(DriveReductionMyopic):
    """C4 with prediction: if delay known, depart early when projected deficit rises.

    Uses a simple forward model of energy drift + travel time to food.
    """

    def __init__(self, seed: int = 0, drive: str = "D3", horizon: int = 12) -> None:
        super().__init__(seed=seed, mode="reduction", drive=drive)
        self.horizon = horizon

    def act(self, obs: dict, world: World) -> str:
        if obs.get("energy") is None or not world.cfg.prediction_enabled:
            return super().act(obs, world)

        pos = (obs["x"], obs["y"])
        travel = _path_len(pos, world.cfg.food_pos)
        # project energy after travel + delay
        e = world.phys.energy
        drift = world.phys.energy_drift if world.cfg.drift_enabled else 0.0
        delay = world.cfg.food_delay
        projected = e + drift * (travel + delay)
        # anticipatory: leave for food before critical if projection drops below viable
        from physiology import ENERGY

        if projected < ENERGY.viable_low and e > ENERGY.critical_low:
            if obs["at_food"]:
                return "CONSUME"
            return _toward(pos, world.cfg.food_pos, self.rng)

        # temperature anticipation via ambient
        t = world.phys.temperature
        from physiology import TEMPERATURE

        if t < TEMPERATURE.viable_low:
            if obs["at_warm"]:
                return "STAY"
            return _toward(pos, world.cfg.warm_pos, self.rng)
        if t > TEMPERATURE.viable_high:
            if obs["at_cool"]:
                return "STAY"
            return _toward(pos, world.cfg.cool_pos, self.rng)

        return super().act(obs, world)


class NoveltyBonus(AnticipatoryDriveReduction):
    """C8: drive reduction + bounded novelty (visit under-visited cells)."""

    def __init__(self, seed: int = 0) -> None:
        super().__init__(seed=seed)
        self.visits: dict[tuple[int, int], int] = {}

    def act(self, obs: dict, world: World) -> str:
        pos = (obs["x"], obs["y"])
        self.visits[pos] = self.visits.get(pos, 0) + 1
        # if all needs ok, explore least-visited neighbor
        comps = drive_components(world.phys)
        if max(comps.values()) < 0.15:
            neighbors = []
            for a, np_ in (
                ("N", (pos[0], min(world.cfg.height - 1, pos[1] + 1))),
                ("S", (pos[0], max(0, pos[1] - 1))),
                ("E", (min(world.cfg.width - 1, pos[0] + 1), pos[1])),
                ("W", (max(0, pos[0] - 1), pos[1])),
            ):
                neighbors.append((self.visits.get(np_, 0), a))
            neighbors.sort()
            return neighbors[0][1]
        return super().act(obs, world)


def make_policy(condition: str, seed: int = 0):
    if condition == "C0":
        return RandomPolicy(seed)
    if condition == "C1":
        return FixedExternalRewardGreedy(seed)
    if condition == "C2":
        return HardcodedNeedPriority(seed)
    if condition == "C3":
        return DriveReductionMyopic(seed, mode="neg_drive")
    if condition == "C4":
        return AnticipatoryDriveReduction(seed)
    if condition == "C5":
        return DriveReductionMyopic(seed, mode="reduction")  # used with hide_internal
    if condition == "C6":
        return AnticipatoryDriveReduction(seed)  # used with drift disabled
    if condition == "C7":
        return AnticipatoryDriveReduction(seed)  # used with prediction disabled
    if condition == "C8":
        return NoveltyBonus(seed)
    raise KeyError(condition)
