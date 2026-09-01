"""Static retained-evidence projection for AS-003O; imports no UMBRA code."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence")
REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from tools.as003o_evidence import write_bytes, canonical_bytes  # noqa: E402


def _read(name: str) -> dict[str, object]:
    matches = sorted(ROOT.glob(f"umbra-as-003*/{name}"))
    if not matches:
        raise RuntimeError(f"retained artifact unavailable: {name}")
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def main() -> None:
    k = _read("AS003K_PROSPECTIVE_REGULATORY_HORIZON_AUDIT.json")
    l = _read("AS003L_BOUNDEDNESS_AND_PLANNING_BOUNDARY.json")
    m = _read("AS003M_MULTISTEP_EVIDENCE_COMPOSITION_AUDIT.json")
    payload = {
        "schema": "AS003O_RETAINED_EVIDENCE_PROJECTION_V1",
        "method": "static retained-artifact and source-fixture projection only; no runtime import or organism execution",
        "inputs": {
            "AS003K": {"artifact": "AS003K_PROSPECTIVE_REGULATORY_HORIZON_AUDIT.json", "result": k.get("result")},
            "AS003L": {"artifact": "AS003L_BOUNDEDNESS_AND_PLANNING_BOUNDARY.json", "result": l.get("result")},
            "AS003M": {"artifact": "AS003M_MULTISTEP_EVIDENCE_COMPOSITION_AUDIT.json", "result": m.get("result")},
        },
        "adaptable_source_fixture_cases": {
            "exact_root_physiology": "SUPPORTED: four direct current owner observations map to exact VERIFIED_OBSERVED_SUPPORT root envelopes",
            "explicit_timed_opportunity_plus_capability": "SUPPORTED in focused fixture: categorical duration, body match, route/capability, correlated branches, and root-relative persistence horizon construct a CHARGE/REST/INSPECT service",
            "current_observation_only": "UNKNOWN: current presence carries no future persistence guarantee",
            "probabilistic_capability_or_unknown_route": "UNKNOWN: source support cannot be promoted",
        },
        "retained_source_coverage": {
            "fully_adaptable_real_owner_snapshots": 0,
            "reason": "AS003K/L/M retain analysis and literal matrices, not a complete immutable current Physiology+body+capability+route+timed-opportunity+commitment source snapshot",
            "constructible_from_retained_actual_sources": [],
            "blocked_missing_fields": ["opportunity identity plus authoritative valid-through horizon", "categorical completion/timing envelope for the actual service/route", "body-schema-matched categorical capability support", "immutable pending-commitment snapshot coupled to the source tick"],
        },
        "continuation_results": {"P1": "lawful and mechanically demonstrated on explicit source fixtures; not established for retained actual source states", "P2": "exact branch-aligned strict witness-set inclusion is representable; retained actual source states do not provide aligned continuation sets"},
        "selection_pressure": "NOT_ESTABLISHED: current retained artifacts do not expose all source-backed prerequisites, so no lawful claim that continuation evidence would alter an ordinary frontier is possible",
        "as002_interface": "provisional relational evidence only; no AS-002 mutation, scalarization, source priority, or recovery override",
        "integrity": {"organism_runs": 0, "diagnostic_runs": 0, "qualification_runs": 0, "retries": 0, "reseeds": 0},
    }
    print(write_bytes("AS003O_RETAINED_EVIDENCE_PROJECTION.json", canonical_bytes(payload)))


if __name__ == "__main__":
    main()
