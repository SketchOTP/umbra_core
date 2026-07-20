"""Reward formulations R0–R4.

R4 (hard-coded need-priority) is a negative control, not a UMBRA candidate.
"""

from __future__ import annotations

from collections.abc import Callable

from drives import DRIVES, drive_components
from physiology import Physiology


DriveFn = Callable[[Physiology], float]


def reward_external_fixed(_before: Physiology, _after: Physiology, event: str) -> float:
    """R0 — external fixed reward for named events (non-homeostatic)."""
    table = {"food": 1.0, "warm": 0.5, "cool": 0.5, "noop": 0.0, "move": -0.01}
    return table.get(event, 0.0)


def reward_neg_drive(before: Physiology, after: Physiology, drive_fn: DriveFn) -> float:
    """R1 — negative current drive (after-state)."""
    del before
    return -drive_fn(after)


def reward_drive_reduction(before: Physiology, after: Physiology, drive_fn: DriveFn) -> float:
    """R2 — Keramati–Gutkin: D(H_t) - D(H_{t+1})."""
    return drive_fn(before) - drive_fn(after)


def reward_terminal_survival(before: Physiology, after: Physiology, drive_fn: DriveFn) -> float:
    """R3 — sparse survival: +1 if not critical, -10 if critical."""
    del before, drive_fn
    return -10.0 if after.critical_any() else 1.0


def hardcoded_need_action(phys: Physiology) -> str:
    """R4 controller: always serve the currently largest absolute deviation.

    Negative control — frozen priority by instantaneous max deficit, not learning.
    """
    comps = drive_components(phys)
    need = max(comps, key=comps.get)
    if need == "energy":
        return "SEEK_FOOD"
    # temperature: decide warm vs cool by signed deviation
    from drives import signed_deviations

    s = signed_deviations(phys)
    return "SEEK_WARM" if s["temperature"] < 0 else "SEEK_COOL"


REWARDS = {
    "R0": "external_fixed",
    "R1": "negative_drive",
    "R2": "drive_reduction",
    "R3": "terminal_survival",
    "R4": "hardcoded_need_priority",
}


def compute_reward(
    name: str,
    before: Physiology,
    after: Physiology,
    event: str,
    drive_name: str = "D3",
) -> float:
    drive_fn = DRIVES[drive_name]
    if name == "R0":
        return reward_external_fixed(before, after, event)
    if name == "R1":
        return reward_neg_drive(before, after, drive_fn)
    if name == "R2":
        return reward_drive_reduction(before, after, drive_fn)
    if name == "R3":
        return reward_terminal_survival(before, after, drive_fn)
    if name == "R4":
        # controller, not a scalar reward — return 0 for logging
        return 0.0
    raise KeyError(name)
