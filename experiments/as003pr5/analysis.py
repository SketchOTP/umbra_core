"""Frozen R5-only interpretation of observer-safe modal shadow evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.as003pr3_analyze import analyze as _analyze_prior


def analyze(planning_path: Path, decision_path: Path) -> dict[str, dict[str, Any]]:
    """Reuse the preregistered AS-003L exposure predicates with R5 provenance."""
    prior = _analyze_prior(planning_path, decision_path)
    mapping = {
        "AS003PR3_MODAL_EVIDENCE_SUMMARY.json": "AS003PR5_MODAL_EVIDENCE_SUMMARY.json",
        "AS003PR3_CONFLICT_EXPOSURE_AUDIT.json": "AS003PR5_CONFLICT_EXPOSURE_AUDIT.json",
        "AS003PR3_AS003L_REASSESSMENT.json": "AS003PR5_AS003L_BLOCKER_RESULT.json",
        "AS003PR3_AS002_FUTURE_RELATION.json": "AS003PR5_AS002_FUTURE_BOUNDARY.json",
    }
    result: dict[str, dict[str, Any]] = {}
    for old_name, new_name in mapping.items():
        value = prior[old_name]
        value["schema"] = value["schema"].replace("AS003PR3", "AS003PR5")
        value["directive"] = "UMBRA-AS-003P-R5"
        value["source"] = "fresh observer-safe AS-003P-R5 SHADOW trace only"
        value["historical_r1_r3_modal_counts_used"] = False
        result[new_name] = value
    exposure = result["AS003PR5_CONFLICT_EXPOSURE_AUDIT.json"]
    prior_result = exposure.pop("result")
    exposure["classification"] = (
        "SUFFICIENT_CONFLICT_EXPOSURE"
        if exposure["decisions_exposing_as003l_residual_conflict"] > 0
        else "LIMITED_CONFLICT_EXPOSURE"
        if exposure["ordinary_decisions"] > 0
        else "NO_RELEVANT_CONFLICT_EXPOSURE"
    )
    exposure["detailed_result"] = prior_result
    future = result["AS003PR5_AS002_FUTURE_BOUNDARY.json"]
    future["disposition"] = (
        "RELATIONAL_CONTRACT_RESEARCH_JUSTIFIED"
        if result["AS003PR5_AS003L_BLOCKER_RESULT.json"]["classification"] == "BLOCKER_EXPRESSED"
        else "TARGETED_EXPOSURE_REQUIRED"
        if result["AS003PR5_AS003L_BLOCKER_RESULT.json"]["classification"] == "FIXTURE_DID_NOT_EXPOSE_BLOCKER"
        else "NO_RELATION_SUPPORTED"
    )
    return result
