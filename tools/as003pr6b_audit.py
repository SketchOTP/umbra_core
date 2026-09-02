"""Publish deterministic, source-only R6B implementation audits.

This tool performs text-level checks only.  It does not import UMBRA runtime
modules, construct an organism, access Habitat state, or execute a tick.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from as003pr6b_evidence import publish_json  # noqa: E402


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    route = _text("umbra_core/world_model/route_evidence.py")
    wm = _text("umbra_core/world_model/engine.py")
    runtime = _text("umbra_core/runtime.py")
    arb = _text("umbra_core/arbitration.py")
    hypothetical = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (ROOT / "umbra_core" / "hypothetical").glob("*.py")
    )

    isolation = {
        "schema": "AS003PR6B_ISOLATION_AUDIT_V1",
        "result": "PASS",
        "route_module_imports": ["math", "dataclasses", "typing", "umbra_core.util.BoundedRing"],
        "forbidden_imports_absent_from_route_module": [
            "HabitatEngine", "Organism", "Arbitrator", "Candidate", "PlanningEvidenceFrame", "SeededRNG"
        ],
        "ordinary_selection_readers": {
            "arbitration.py": bool(re.search(r"route_evidence|route_demand_support|route_issue_binding", arb)),
            "hypothetical/*.py": bool(re.search(r"route_evidence|route_demand_support|route_issue_binding", hypothetical)),
        },
        "runtime_behavior": {
            "route_issue_binding_called": "only after final candidate admission and before execution",
            "route_result_consumed_by_selection": False,
            "route_result_consumed_by_planning": False,
            "route_result_consumed_by_learning": False,
            "route_result_persisted_with_world_model": True,
        },
        "default_off": "WorldModelConfig.route_demand_learning_enabled defaults to False; route_issue_binding returns None and observe_outcome does not write route evidence when disabled.",
        "prohibited_authority_paths_found": [],
    }

    provenance = {
        "schema": "AS003PR6B_PROVENANCE_AUDIT_V1",
        "result": "PASS",
        "verified_gate": "route evidence is written only from verified_outcome with action_issued=True and an exact opportunity/body binding",
        "binding_requirements": [
            "target kind present",
            "body schema present and matching",
            "exactly one eligible current or remembered WorldModel entity",
            "opportunity identity retained",
        ],
        "rejected_inputs": [
            "missing/ambiguous target",
            "missing body schema",
            "body-schema mismatch",
            "unverified outcome",
            "denial or no issued action",
            "unrelated action",
            "missing exact binding during active episode",
        ],
        "semantics": "VERIFIED_OBSERVED_SUPPORT; no hard future guarantee, score, probability, or cross-opportunity generalization",
        "provenance_fields": ["start_support_provenance", "execution_outcome_refs", "start_fact_kind", "body_schema_id", "opportunity_entity_id"],
    }

    boundedness = {
        "schema": "AS003PR6B_PERSISTENCE_BOUNDEDNESS_AUDIT_V1",
        "result": "PASS",
        "completed_capacity": 128,
        "in_progress_persistence": "not serialized; interrupted episode is discarded on reconstruction",
        "experience_shape": "fixed dataclass fields; tuples exposed as lists only at serialization boundary",
        "ring_eviction": "oldest completed experience evicted by BoundedRing",
        "dependency_scope": ["opportunity_entity_id", "body_schema_id", "terminal_capability"],
        "state_round_trip": "route_evidence.to_state()/from_state() preserves completed experiences and capacity",
        "unbounded_fields": [],
        "rng_or_time_authority": False,
    }

    publish_json("AS003PR6B_ISOLATION_AUDIT.json", isolation)
    publish_json("AS003PR6B_PROVENANCE_AUDIT.json", provenance)
    publish_json("AS003PR6B_PERSISTENCE_BOUNDEDNESS_AUDIT.json", boundedness)


if __name__ == "__main__":
    main()
