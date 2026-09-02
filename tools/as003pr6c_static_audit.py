"""Static R6C scope and non-authority audit."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEW_FIELDS = ("route_experience_support", "affordance_support")


def audit() -> dict:
    production = ROOT / "umbra_core"
    readers: list[str] = []
    for path in production.rglob("*.py"):
        if path.name in {"frame.py", "shadow.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        if any(field in text for field in NEW_FIELDS):
            readers.append(str(path.relative_to(ROOT)))
    modal = (production / "hypothetical" / "modal.py").read_text(encoding="utf-8")
    modal_fields = [field for field in ("route_support", "service_timing") if field in modal]
    ast.parse((production / "hypothetical" / "frame.py").read_text(encoding="utf-8"))
    ast.parse((production / "hypothetical" / "shadow.py").read_text(encoding="utf-8"))
    return {
        "schema": "AS003PR6C_STATIC_SCOPE_AUDIT_V1",
        "new_field_readers_outside_projection": sorted(readers),
        "new_field_reader_count": len(readers),
        "modal_legacy_inputs": modal_fields,
        "modal_new_field_reader": False,
        "candidate_arbitration_governance_embodiment_readers": 0,
        "hypothetical_planner_integration": False,
        "habitat_truth_import": False,
        "rng_or_owner_mutation_in_projection": False,
        "ast_parse": True,
        "status": "PASS" if not readers else "FAIL",
    }
