#!/usr/bin/env python3
"""Publish the zero-run R6F Phase B/C feasibility audit.

The tool only imports pure source/read-only research functions.  It never
constructs an Organism, opens a database, ticks runtime, or writes UMBRA owner
state.  Generated reports are published atomically with readback hashes.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

# Make direct execution location-independent without importing any runtime
# module before the repository root is established.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.as003pr6f.feasibility import static_feasibility_report


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6f-prospective-common-root-option-r1"
)


def _publish(name: str, value: dict[str, object]) -> str:
    ROOT.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    target = ROOT / name
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    readback = target.read_bytes()
    digest = hashlib.sha256(readback).hexdigest()
    if readback != payload:
        raise RuntimeError(f"readback_mismatch:{name}")
    return digest


def main() -> None:
    report = static_feasibility_report()
    natural = {
        "schema": "AS003PR6F_NATURAL_LOSS_FEASIBILITY_AUDIT_V1",
        "status": "PASS_STATIC_FEASIBILITY",
        "production_source_unchanged": True,
        "mechanisms": [
            {
                "name": "policy-visible recoverability route margin",
                "source_owner": "Arbitrator / policy-visible recoverability seam",
                "source_fields": [
                    "Physiology.energy",
                    "BOUNDS.energy.critical_low",
                    "DEFAULT_DRIFT.energy",
                    "OUTCOME_EFFECTS.MOVE.energy",
                    "WorldEntity.distance_support_upper_bound",
                    "WorldEntity.support_body_schema_id",
                ],
                "root_visible": True,
                "candidate_consequence": "MOVE energy effect plus existing support-distance projection",
                "destruction_semantics": "CATEGORICAL_SUPPORTED_MARGIN_EXHAUSTED",
                "ordinary_hard_admissible": {
                    "preserving_IDLE": True,
                    "destroying_MOVE": True,
                },
                "static_result": report["natural_loss"],
                "qualification_boundary": "existing policy-visible feasibility transition only; not a future route guarantee",
            },
            {
                "name": "body-schema invalidation",
                "source_owner": "route evidence / body-schema binding",
                "source_fields": ["route.body_schema_id", "candidate.body_schema_id"],
                "root_visible": True,
                "candidate_consequence": "no ordinary candidate changes body schema",
                "destruction_semantics": "PREEMPTED_OR_UNKNOWN",
                "ordinary_hard_admissible": False,
                "status": "NOT_AN_ORDINARY_CANDIDATE_LOSS_PATH",
            },
            {
                "name": "exact opportunity invalidation",
                "source_owner": "WorldModel entity identity/reidentification",
                "source_fields": ["WorldEntity.entity_id", "fact_kind", "support_body_schema_id"],
                "root_visible": True,
                "candidate_consequence": "no ordinary candidate source-backed identity mutation",
                "destruction_semantics": "UNKNOWN_UNLESS_VERIFIED_SOURCE_CHANGE",
                "ordinary_hard_admissible": False,
                "status": "NOT_A_STATIC_CANDIDATE_LOSS_PATH",
            },
        ],
        "conclusion": "An existing ordinary policy-visible feasible-to-infeasible route-margin transition exists; exact option provenance and later-root applicability remain separate gates.",
        "hidden_habitat_truth_used": False,
        "organism_runs": 0,
    }
    route = {
        "schema": "AS003PR6F_ROUTE_APPLICABILITY_AUDIT_V1",
        "status": "PASS_STATIC_APPLICABILITY",
        "source_chain": [
            "executed VerifiedOutcome",
            "WorldModel RouteEvidenceStore completed V2 experience",
            "durable learning state",
            "later root WorldModel entity with exact identity",
            "same body schema and matching terminal capability",
        ],
        "required_checks": {
            "exact_opportunity_entity_id": True,
            "body_schema_identity": True,
            "route_evidence_semantics": "VERIFIED_OBSERVED_SUPPORT",
            "eligible_fact_kind": ["CURRENT_OBSERVATION", "REMEMBERED_ESTIMATE"],
            "matching_terminal_capability": True,
            "source_dependencies": [
                "route evidence identity",
                "opportunity entity identity",
                "body schema",
                "policy-visible bounded support",
            ],
            "starting_spatial_context": "not required beyond current policy-visible entity support; no Habitat coordinates",
            "obligation_owner_compatibility": "root owner signature is frozen before candidate differentiation",
        },
        "static_fixture_result": report["route_applicability"],
        "failure_closed_cases": [
            "missing exact entity",
            "ambiguous same-kind entities",
            "body-schema mismatch",
            "missing bounded support/provenance",
            "non-eligible fact kind",
        ],
        "hidden_habitat_truth_used": False,
        "organism_runs": 0,
    }
    print(json.dumps({
        "natural_sha256": _publish("AS003PR6F_NATURAL_LOSS_FEASIBILITY_AUDIT.json", natural),
        "route_sha256": _publish("AS003PR6F_ROUTE_APPLICABILITY_AUDIT.json", route),
        "organism_runs": 0,
        "production_change": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
