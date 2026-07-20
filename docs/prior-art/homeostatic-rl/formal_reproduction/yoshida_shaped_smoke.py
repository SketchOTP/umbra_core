#!/usr/bin/env python3
"""Source-derived smoke: Yoshida homeostatic_shaped (no MuJoCo).

Equations from deeprl_gfn commit 2f7af293… two_resource_env.py::_homeostatic_shaped
"""
from __future__ import annotations

import json
import numpy as np


def homeostatic_shaped(prev, curr, target, weight=(1.0, 1.0)) -> float:
    w = np.asarray(weight, dtype=float)
    d = lambda intero: w * (np.asarray(intero, dtype=float) - np.asarray(target, dtype=float))
    return float(-np.linalg.norm(d(curr)) ** 2 + np.linalg.norm(d(prev)) ** 2)


def main() -> None:
    target = np.array([0.5, 0.5])
    r_rec = homeostatic_shaped([0.1, 0.5], [0.4, 0.5], target)
    r_over = homeostatic_shaped([0.5, 0.5], [0.9, 0.5], target)
    r_def = homeostatic_shaped([0.1, 0.5], [0.2, 0.5], target)
    r_sat = homeostatic_shaped([0.48, 0.5], [0.58, 0.5], target)
    assert r_rec > 0 and r_over < 0 and r_def > r_sat
    print(json.dumps({"ok": True, "r_rec": r_rec, "r_over": r_over, "r_def": r_def, "r_sat": r_sat}))
    print("OK yoshida_homeostatic_shaped_source_derived")


if __name__ == "__main__":
    main()
