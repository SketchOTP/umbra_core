#!/usr/bin/env python3
"""Pure AS-015 generalization and ordinary-behavior noninterference audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.as015.full_config import BASELINE, DIRECTIVE
from tools.as015_evidence import publish
from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology
from umbra_core.recoverability.contracts import EXECUTABLE, NOT_EXECUTABLE
from umbra_core.recoverability.viability import ROBUST_NOW, enumerate_regulatory_recovery_routes
from umbra_core.util import SeededRNG


def _branches(candidate: Candidate):
    return {
        "CHARGE": ({"energy": 0.14, "fatigue": -0.01, "stimulation": -0.005},),
        "REST": ({"energy": 0.015, "fatigue": -0.08, "integrity": 0.055, "stimulation": -0.02},),
        "INSPECT": ({"energy": -0.003, "fatigue": 0.002, "stimulation": 0.04},),
    }.get(candidate.capability, ({},))


def _routes(values: dict[str, float], needs: list[str], candidates: list[Candidate]):
    return enumerate_regulatory_recovery_routes(
        physiology=values,
        active_needs=needs,
        candidates=candidates,
        observations=[
            {"kind": "resource", "estimated_distance": 1.0},
            {"kind": "rest", "estimated_distance": 1.0},
            {"kind": "inspect", "estimated_distance": 1.0},
        ],
        authority_effect_branches_for=_branches,
        current_executability_for=lambda _: EXECUTABLE,
    )


def _robust(routes: Any) -> set[tuple[str, str]]:
    return {
        (route.need, route.endpoint_capability)
        for route in routes
        if route.status == ROBUST_NOW
    }


def main() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    rest = Candidate("REST", {"toward": "rest"})
    inspect = Candidate("INSPECT", {"toward": "inspect"})
    cases = {
        "energy_recovery": _robust(_routes(
            {"energy": 0.20, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55}, ["energy"], [charge]
        )),
        "fatigue_alternate_charge": _robust(_routes(
            {"energy": 0.50, "fatigue": 0.80, "integrity": 0.90, "stimulation": 0.55}, ["fatigue"], [charge]
        )),
        "integrity_recovery": _robust(_routes(
            {"energy": 0.60, "fatigue": 0.20, "integrity": 0.20, "stimulation": 0.55}, ["integrity"], [rest]
        )),
        "stimulation_recovery": _robust(_routes(
            {"energy": 0.60, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.20}, ["stimulation"], [inspect]
        )),
        "multi_need": _robust(_routes(
            {"energy": 0.20, "fatigue": 0.80, "integrity": 0.90, "stimulation": 0.55}, ["energy", "fatigue"], [charge, rest]
        )),
        "integrity_conflict_rejected": _robust(_routes(
            {"energy": 0.60, "fatigue": 0.80, "integrity": 0.90, "stimulation": 0.051}, ["fatigue"], [charge]
        )),
        "unrecoverable": _robust(_routes(
            {"energy": 0.20, "fatigue": 0.80, "integrity": 0.20, "stimulation": 0.20}, ["energy", "fatigue", "integrity", "stimulation"], []
        )),
    }
    expected = {
        "energy_recovery": {("energy", "CHARGE")},
        "fatigue_alternate_charge": {("fatigue", "CHARGE")},
        "integrity_recovery": {("integrity", "REST")},
        "stimulation_recovery": {("stimulation", "INSPECT")},
        "multi_need": {("energy", "CHARGE"), ("energy", "REST"), ("fatigue", "CHARGE"), ("fatigue", "REST")},
        "integrity_conflict_rejected": set(),
        "unrecoverable": set(),
    }
    baseline_rng, kernel_rng = SeededRNG(9271), SeededRNG(9271)
    observation = [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 0.5}]
    no_need = Physiology()
    baseline = Arbitrator().select(
        no_need, observation, 10, baseline_rng, authority_effect_branches=_branches,
        candidate_executability=lambda _: NOT_EXECUTABLE, viability_kernel_enabled=False,
    )
    kernel = Arbitrator().select(
        Physiology(), observation, 10, kernel_rng, authority_effect_branches=_branches,
        candidate_executability=lambda _: NOT_EXECUTABLE, viability_kernel_enabled=True,
    )
    def fatal_branches(_candidate: Candidate):
        # A genuinely unrecoverable root: every reachable action branch newly
        # crosses at least one critical bound.  This is distinct from merely
        # hiding ordinary candidates while leaving a safe fallback available.
        return ({"energy": -0.20, "fatigue": 0.20, "integrity": -0.20, "stimulation": -0.20},)

    unrecoverable = Arbitrator().select(
        Physiology(energy=0.05, fatigue=0.80, integrity=0.20, stimulation=0.20), [], 10, SeededRNG(19),
        authority_effect_branches=fatal_branches,
        candidate_executability=lambda _: NOT_EXECUTABLE,
    )
    generalization_pass = all(cases[name] == expected[name] for name in expected)
    noninterference_pass = (
        (baseline.capability, dict(baseline.params)) == (kernel.capability, dict(kernel.params))
        and baseline_rng.export_state() == kernel_rng.export_state()
    )
    result = {
        "schema": "AS015_GENERALIZATION_AND_NONINTERFERENCE_AUDIT_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "classification": "PURE_PRELOCK_EVIDENCE",
        "generalization_cases": {name: sorted([list(item) for item in values]) for name, values in cases.items()},
        "generalization_expected": {name: sorted([list(item) for item in values]) for name, values in expected.items()},
        "generalization_pass": generalization_pass,
        "ordinary_noninterference": {
            "selected_candidate_equal": (baseline.capability, dict(baseline.params)) == (kernel.capability, dict(kernel.params)),
            "rng_state_equal": baseline_rng.export_state() == kernel_rng.export_state(),
            "pass": noninterference_pass,
        },
        "unrecoverable_result": {
            "capability": unrecoverable.capability,
            "source": unrecoverable.params.get("source"),
            "no_safe_action_preserved": unrecoverable.params.get("source") == "no_safe_action",
        },
        "result": "PASS" if generalization_pass and noninterference_pass and unrecoverable.params.get("source") == "no_safe_action" else "FAIL",
    }
    publish("AS015_GENERALIZATION_AND_NONINTERFERENCE_AUDIT_R1.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
