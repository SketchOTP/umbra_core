"""Evaluator-only behavioral fingerprint for D-007.

Never written into organism state or passed to IndividualityEngine as labels.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from umbra_core.arbitration import Candidate
from umbra_core.individuality import DISPOSITION_DIMENSIONS, IndividualityEngine
from umbra_core.util import SeededRNG

ROOT = Path(__file__).resolve().parents[2]
PROBES = json.loads((ROOT / "experiments/d007/probe-suite.json").read_text())


def probe_modifier_vector(engine: IndividualityEngine | None, *, seed: int = 0) -> dict[str, float]:
    """Score each held-out probe by mean individuality modifier magnitude/sign.

    For C1 (no engine) returns zeros. For diagnostic C2/C3 controllers, callers
    should pass a proxy vector via `fingerprint_from_vector`.
    """
    out: dict[str, float] = {}
    if engine is None or not engine.config.enabled:
        return {p["id"]: 0.0 for p in PROBES["probes"]}

    rng = SeededRNG(seed + 99)
    for p in PROBES["probes"]:
        scope = p["context"]
        caps = p["capability_focus"]
        scores = []
        for cap in caps:
            cand = Candidate(cap, {})
            # Phase hint for timing probes
            phase = rng.uniform(0.0, 1.0) if "timing" in p["id"] or "routine" in p["id"] else None
            mod = engine.modifier_for_candidate(
                cand, context_scope=scope, critical_physiology=False, phase_hint=phase
            )
            scores.append(mod)
        out[p["id"]] = sum(scores) / max(1, len(scores))
    return out


def fingerprint_from_vector(vec: dict[str, float]) -> dict[str, float]:
    """Map disposition vector → probe-aligned fingerprint proxy (diagnostics)."""
    # Rough alignment of dimensions to probes for C2/C3 comparison only.
    mapping = {
        "P_explore_safe": "exploration_tendency",
        "P_novelty": "novelty_tolerance",
        "P_persist_solvable": "persistence_after_failure",
        "P_uncertain_hazard": "uncertainty_caution",
        "P_high_stim": "stimulation_tolerance",
        "P_recovery": "recovery_pacing",
        "P_timing": "activity_timing_preference",
        "P_social_play": "social_initiative_by_context",
        "P_social_assist": "social_initiative_by_context",
        "P_object_A": "novelty_tolerance",
        "P_object_B": "novelty_tolerance",
        "P_interrupt": "recovery_pacing",
        "P_routine": "activity_timing_preference",
    }
    return {pid: float(vec.get(dim, 0.0)) for pid, dim in mapping.items()}


def fingerprint_distance(a: dict[str, float], b: dict[str, float]) -> float:
    keys = sorted(set(a) | set(b))
    if not keys:
        return 0.0
    return math.sqrt(sum((float(a.get(k, 0.0)) - float(b.get(k, 0.0))) ** 2 for k in keys) / len(keys))


def fingerprint_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """1 / (1 + distance) ∈ (0, 1]."""
    return 1.0 / (1.0 + fingerprint_distance(a, b))


def disposition_l2(a: dict[str, float], b: dict[str, float]) -> float:
    keys = list(DISPOSITION_DIMENSIONS)
    return math.sqrt(sum((float(a.get(k, 0.0)) - float(b.get(k, 0.0))) ** 2 for k in keys) / len(keys))


def action_entropy(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log(p + 1e-12)
    return h


def reid_match(gallery: dict[str, float], probe: dict[str, float], *, tol: float) -> bool:
    return fingerprint_distance(gallery, probe) <= tol
