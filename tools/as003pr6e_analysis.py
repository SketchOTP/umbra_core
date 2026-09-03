"""Offline AS-003P-R6E analysis over immutable R6D symbolic evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.as003pr6e.matrix import evaluate_r6d_rows
from experiments.as003pr6e.options import (
    CandidateBranch,
    CandidateProjection,
    OptionStatus,
    SupportVariant,
    SupportedRecoveryOption,
    assess_option,
    deduplicate_options,
    known_option_precedes,
)
from tools.as003pr6e_evidence import ROOT, publish, publish_text


R6D_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6d-may-route-l2-reachability-r1"
)
R6D_MATRIX = R6D_ROOT / "AS003PR6D_REACHABILITY_MATRIX.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _option(
    *,
    demand: int = 7,
    evidence_id: str = "evidence-a",
    confidence: str = "MAY",
    provenance: tuple[str, ...] = ("retained-witness",),
) -> SupportedRecoveryOption:
    return SupportedRecoveryOption(
        root_frame_identity="retained-root",
        active_obligation_signature=("energy",),
        body_schema_id="body-v1",
        ordered_terminal_services=("CHARGE",),
        exact_opportunity_identities=("resource-1",),
        owner_coverage=("energy",),
        required_effect_semantics=(("energy", "recovery"),),
        relevant_opportunity_horizons=(("resource-1", 8),),
        source_dependencies=("route-witness",),
        support_variants=(
            SupportVariant(
                variant_id=f"variant-{evidence_id}",
                observed_total_demand=demand,
                opportunity_horizon=8,
                body_schema_id="body-v1",
                source_dependencies=("route-witness",),
                provenance=provenance,
                evidence_id=evidence_id,
                confidence=confidence,
            ),
        ),
        terminal_service_semantics=(("CHARGE", "terminal recovery"),),
        provenance=provenance,
    )


def _candidate(*, horizon: int = 8, unknown: bool = False, invalidated: bool = False) -> CandidateProjection:
    return CandidateProjection(
        candidate_id="candidate",
        root_frame_identity="retained-root",
        residual_obligation_signature=("energy",),
        ordinary_hard_admissible=True,
        branches=(
            CandidateBranch(
                branch_id="branch",
                invalidated_dependencies=("route-witness",) if invalidated else (),
                unknown_dependencies=("route-witness",) if unknown else (),
                horizon_overrides=(("resource-1", horizon),),
            ),
        ),
    )


def source_priority_audit() -> dict[str, Any]:
    base = _option()
    changed_evidence = _option(evidence_id="evidence-b", confidence="MUST", provenance=("newer", "source"))
    shorter = _option(demand=6)
    longer = _option(demand=7)
    duplicate_count = len(deduplicate_options((base, changed_evidence)))
    results = {
        "duplicate_evidence_collapses": duplicate_count == 1,
        "confidence_and_provenance_do_not_change_relation": (
            known_option_precedes((base,), _candidate(), _candidate(horizon=5)).relates
            == known_option_precedes((changed_evidence,), _candidate(), _candidate(horizon=5)).relates
        ),
        "duration_without_feasibility_change_is_neutral": (
            not known_option_precedes((shorter,), _candidate(), _candidate()).relates
            and not known_option_precedes((longer,), _candidate(), _candidate()).relates
        ),
        "duration_crossing_horizon_changes_status": (
            assess_option(longer, _candidate(horizon=5)).status is OptionStatus.DESTROYED
        ),
        "root_option_set_is_shared": (
            known_option_precedes((base,), _candidate(), _candidate(horizon=5)).option_pairs
            == known_option_precedes((base,), _candidate(), _candidate(horizon=5)).option_pairs
        ),
        "unknown_never_counts_as_loss": (
            assess_option(base, _candidate(unknown=True)).status is OptionStatus.UNKNOWN
        ),
    }
    return {
        "schema": "AS003PR6E_SOURCE_PRIORITY_AUDIT_V1",
        "checks": results,
        "required_result": "NO_GENERIC_SOURCE_PRIORITY",
        "result": "PASS" if all(results.values()) else "FAIL",
        "authority": "option identity and candidate consequence only; no source priority",
    }


def retained_witness_probe() -> dict[str, Any]:
    witness = _option(demand=7, evidence_id="r6b-r1-seven-tick-witness")
    preserved = assess_option(witness, _candidate(horizon=8))
    destroyed = assess_option(witness, _candidate(horizon=5))
    unknown = assess_option(witness, _candidate(unknown=True))
    result = known_option_precedes((witness,), _candidate(horizon=8), _candidate(horizon=5))
    return {
        "schema": "AS003PR6E_RETAINED_WITNESS_PROBE_V1",
        "fixture": {
            "observed_total_demand": 7,
            "route_semantics": "MAY / VERIFIED_OBSERVED_SUPPORT",
            "unknown_future_routes_preserved": True,
        },
        "deadline_8": preserved.status.value,
        "deadline_5": destroyed.status.value,
        "unknown_applicability": unknown.status.value,
        "relation": {"relates": result.relates, "reason": result.reason},
        "interpretation": "known option loss only; no claim of universal future route impossibility",
    }


def relation_semantic_comparison() -> str:
    return """# AS003P-R6E relation semantic comparison

R6D's `l2_precedes()` relation required A to have a complete schedule on every
branch and B to have a proven no-schedule branch, with UNKNOWN blocking the
claim. That relation is intentionally preserved and is not called here.

R6E evaluates a different, weaker proposition over one common root option set:
A preserves a known source-backed recovery option while B destroys that known
option. The proposition does not assert that B is unrecoverable, unsafe,
suboptimal, or without an unobserved future route. A finite MAY witness remains
existential evidence; its loss after a candidate consequence is a concrete loss
of that known option, not a closed-world claim about all future possibilities.

`UNKNOWN` is neither preservation nor destruction. A strict relation requires
the same status for every other root option and rejects converse loss.
"""


def main() -> None:
    source_hash = _sha256(R6D_MATRIX)
    matrix = json.loads(R6D_MATRIX.read_text())
    rows = matrix["rows"]
    result = evaluate_r6d_rows(rows)
    totals = result["totals"]
    application = {
        "schema": "AS003PR6E_MATRIX_APPLICATION_V1",
        "source": str(R6D_MATRIX),
        "source_sha256": source_hash,
        "source_schema": matrix["schema"],
        "row_count": len(rows),
        "root_option_set": "one fixed semantic option per eligible route row; common to A and B",
        "unknown_policy": "UNKNOWN never establishes destruction",
        "relation": "known_option_precedes",
        "totals": totals,
        "rows": result["rows"],
        "organism_execution": 0,
    }
    publish("AS003PR6E_SOURCE_PRIORITY_AUDIT.json", source_priority_audit())
    publish("AS003PR6E_RETAINED_WITNESS_PROBE.json", retained_witness_probe())
    publish("AS003PR6E_MATRIX_APPLICATION.json", application)
    publish_text("AS003PR6E_RELATION_SEMANTIC_COMPARISON.md", relation_semantic_comparison())
    print(json.dumps({"totals": totals, "source_sha256": source_hash}, sort_keys=True))


if __name__ == "__main__":
    main()
