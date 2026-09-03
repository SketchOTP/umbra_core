"""Analysis-only projection of the immutable R6D symbolic matrix into R6E."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .options import CandidateBranch, CandidateProjection, SupportVariant, SupportedRecoveryOption, known_option_precedes


def root_options_for_row(row: dict[str, Any]) -> tuple[SupportedRecoveryOption, ...]:
    if row["opportunity_modality"] == "UNKNOWN" or row["route_case"] == "absent":
        return ()
    demand = 4 if row["route_case"] == "fits_deadline" else 7
    return (
        SupportedRecoveryOption(
            root_frame_identity="r6d-symbolic-root",
            active_obligation_signature=("energy",),
            body_schema_id="body",
            ordered_terminal_services=("CHARGE",),
            exact_opportunity_identities=("opportunity",),
            owner_coverage=("energy",),
            required_effect_semantics=(("energy", "recovery"),),
            relevant_opportunity_horizons=(("opportunity", 8),),
            source_dependencies=("known-route-support",),
            support_variants=(
                SupportVariant(
                    variant_id=f"r6d-{row['route_case']}",
                    observed_total_demand=demand,
                    opportunity_horizon=8,
                    body_schema_id="body",
                    source_dependencies=("known-route-support",),
                    provenance=("R6C-retained-witness",),
                    evidence_id="administrative-evidence-id",
                    confidence="diagnostic-only",
                ),
            ),
            terminal_service_semantics=(("CHARGE", "regulatory recovery"),),
            provenance=("R6C-retained-witness",),
        ),
    )


def candidates_for_row(row: dict[str, Any]) -> tuple[CandidateProjection, CandidateProjection]:
    a_branch = CandidateBranch(
        "A-branch",
        horizon_overrides=(("opportunity", 8),),
        supported=True,
    )
    # The symbolic non-route case represents a candidate consequence that
    # invalidates the known root option.  Keep the option's own dependency
    # identity as the causal edge; the row label is only attribution metadata.
    b_invalidated = ("known-route-support",) if row["nonroute_known_impossibility"] else ()
    b_branch = CandidateBranch(
        "B-branch",
        horizon_overrides=(("opportunity", 5),),
        invalidated_dependencies=b_invalidated,
        supported=True,
    )
    signature = (f"obligations:{row['active_obligations']}", f"services:{row['corrective_services']}")
    return (
        CandidateProjection("A", "r6d-symbolic-root", signature, not row["hard_violation"], (a_branch,)),
        CandidateProjection("B", "r6d-symbolic-root", signature, not row["hard_violation"], (b_branch,)),
    )


def evaluate_r6d_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    rows_out: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        options = root_options_for_row(row)
        if not options:
            totals["root_option_empty"] += 1
            rows_out.append({"index": index, **row, "relation": False, "reason": "ROOT_OPTION_SET_EMPTY", "option_statuses": []})
            continue
        candidate_a, candidate_b = candidates_for_row(row)
        if row["hard_violation"]:
            totals["hard_preempted"] += 1
        result = known_option_precedes(options, candidate_a, candidate_b)
        if result.relates:
            totals["relation_positive"] += 1
            if row["nonroute_known_impossibility"]:
                totals["nonroute_relation"] += 1
            else:
                totals["route_causal_relation"] += 1
        elif result.reason == "ASYMMETRIC_UNKNOWN":
            totals["asymmetric_unknown_blocked"] += 1
        elif result.reason == "INCOMPARABLE_OBLIGATION_SIGNATURE":
            totals["obligation_mismatch"] += 1
        option_statuses = [
            {"a": status_a.value, "b": status_b.value}
            for _, status_a, status_b in result.option_pairs
        ]
        rows_out.append({"index": index, **row, "relation": result.relates, "reason": result.reason, "option_statuses": option_statuses})
    return {"totals": dict(sorted(totals.items())), "rows": rows_out}
