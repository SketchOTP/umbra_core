"""Frozen R5 analysis semantics with fresh R5A provenance only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.as003pr5.analysis import analyze as _analyze_r5


def analyze(planning_path: Path, decision_path: Path) -> dict[str, dict[str, Any]]:
    prior = _analyze_r5(planning_path, decision_path)
    result: dict[str, dict[str, Any]] = {}
    for old_name, value in prior.items():
        new_name = old_name.replace("AS003PR5", "AS003PR5A")
        value["schema"] = value["schema"].replace("AS003PR5", "AS003PR5A")
        value["directive"] = "UMBRA-AS-003P-R5A"
        value["source"] = "fresh observer-safe AS-003P-R5A SHADOW trace only"
        value["historical_r1_r3_r5_modal_counts_used"] = False
        result[new_name] = value
    return result
