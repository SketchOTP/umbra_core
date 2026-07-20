"""Drive formulations D1–D3 (Keramati–Gutkin style).

D1 — sum of absolute deviations from ideal
D2 — Euclidean vector deviation
D3 — nonlinear Keramati-style (squared deviations; convex / overshoot-sensitive)
"""

from __future__ import annotations

import math

from physiology import ENERGY, TEMPERATURE, Physiology


def drive_linear(phys: Physiology) -> float:
    """D1 — linear absolute deviation."""
    e, t = phys.as_vector()
    ie, it = phys.ideals()
    return abs(e - ie) + abs(t - it)


def drive_euclidean(phys: Physiology) -> float:
    """D2 — Euclidean ||H - H*||."""
    e, t = phys.as_vector()
    ie, it = phys.ideals()
    return math.sqrt((e - ie) ** 2 + (t - it) ** 2)


def drive_nonlinear(phys: Physiology) -> float:
    """D3 — nonlinear (squared) drive: overshoot and deficit both costly.

    Matches the spirit of Keramati & Gutkin convex drive: D = sum_i (h_i - h_i*)^2.
    """
    e, t = phys.as_vector()
    ie, it = phys.ideals()
    return (e - ie) ** 2 + (t - it) ** 2


DRIVES = {
    "D1": drive_linear,
    "D2": drive_euclidean,
    "D3": drive_nonlinear,
}


def drive_components(phys: Physiology) -> dict[str, float]:
    """Per-need absolute deviations (for competition diagnostics)."""
    e, t = phys.as_vector()
    return {
        "energy": abs(e - ENERGY.ideal),
        "temperature": abs(t - TEMPERATURE.ideal),
    }


def signed_deviations(phys: Physiology) -> dict[str, float]:
    e, t = phys.as_vector()
    return {"energy": e - ENERGY.ideal, "temperature": t - TEMPERATURE.ideal}
