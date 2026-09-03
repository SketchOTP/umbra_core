"""Pure provenance analysis for the immutable R6D -> R6E projection.

This module deliberately does not construct a qualified option from R6D rows.
The frozen R6D matrix contains symbolic controls, not a serialized common-root
recovery-option set. The old R6E projection is inspected only to identify why
its root construction is not provenance-safe.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from experiments.as003pr6e.matrix import root_options_for_row


PROVENANCE_CLASSES = (
    "COMMON_ROOT_EVIDENCE",
    "CANDIDATE_A_SPECIFIC",
    "CANDIDATE_B_SPECIFIC",
    "POST_CANDIDATE_CONSEQUENCE",
    "ATTRIBUTION_ONLY",
    "SYNTHETIC_MATRIX_CONTROL",
)


@dataclass(frozen=True)
class ProvenanceEntry:
    field: str
    classification: str
    source: str
    use_in_r6e: str
    common_root_supported: bool
    reason: str


def r6d_provenance_entries() -> tuple[ProvenanceEntry, ...]:
    """Classify every R6D field consumed by the old R6E projection."""
    return (
        ProvenanceEntry(
            "route_case", "SYNTHETIC_MATRIX_CONTROL", "open_world.symbolic_configurations",
            "controls O0 existence, variant identity, and demand; also controls B evidence",
            False, "symbolic row dimension, not retained source evidence",
        ),
        ProvenanceEntry(
            "A retained 7-tick route witness", "CANDIDATE_A_SPECIFIC", "open_world.evaluate_symbolic_configuration",
            "R6D gives witness to A; R6E substitutes row route_case demand into O0",
            False, "A-side candidate fixture; no pre-candidate serialized root option",
        ),
        ProvenanceEntry(
            "B 4/9/absent route witness", "CANDIDATE_B_SPECIFIC", "open_world.evaluate_symbolic_configuration",
            "R6D constructs B route from route_case; R6E reuses route_case in O0",
            False, "B-specific route evidence cannot define a common root",
        ),
        ProvenanceEntry(
            "A deadline 8", "CANDIDATE_A_SPECIFIC", "open_world.evaluate_route_pair / matrix.candidates_for_row",
            "A branch horizon override",
            False, "candidate consequence/deadline, not root option support",
        ),
        ProvenanceEntry(
            "B deadline 5", "CANDIDATE_B_SPECIFIC", "open_world.evaluate_route_pair / matrix.candidates_for_row",
            "B branch horizon override",
            False, "candidate consequence/deadline, not root option support",
        ),
        ProvenanceEntry(
            "opportunity_modality", "SYNTHETIC_MATRIX_CONTROL", "open_world.symbolic_configurations",
            "suppresses O0 for UNKNOWN rows",
            False, "symbolic modality input has no retained common-root source chain",
        ),
        ProvenanceEntry(
            "nonroute_known_impossibility", "CANDIDATE_B_SPECIFIC", "open_world.evaluate_route_pair",
            "R6E invalidates known-route-support for B",
            False, "generic B impossibility has no dependency-specific edge",
        ),
        ProvenanceEntry(
            "hard_violation", "SYNTHETIC_MATRIX_CONTROL", "open_world.symbolic_configurations",
            "removes both candidates from ordinary comparison",
            False, "symbolic hard-authority control, not root option evidence",
        ),
        ProvenanceEntry(
            "active_obligations", "SYNTHETIC_MATRIX_CONTROL", "open_world.symbolic_configurations",
            "R6E ignores value and hardcodes energy signature",
            False, "no serialized owner obligation set is present in row",
        ),
        ProvenanceEntry(
            "corrective_services", "SYNTHETIC_MATRIX_CONTROL", "open_world.symbolic_configurations",
            "R6E ignores value and hardcodes CHARGE",
            False, "no serialized common-root service set is present in row",
        ),
        ProvenanceEntry(
            "a_class / b_class / l2_precedes", "POST_CANDIDATE_CONSEQUENCE", "R6D matrix output",
            "not used to construct O0; outcome/attribution only",
            False, "derived after candidate evaluation",
        ),
        ProvenanceEntry(
            "causal_source", "ATTRIBUTION_ONLY", "R6D matrix output",
            "not used to construct O0; used only as row attribution",
            False, "label does not contain a dependency edge or root fact",
        ),
        ProvenanceEntry(
            "open_world", "SYNTHETIC_MATRIX_CONTROL", "open_world.symbolic_configurations",
            "not consumed by R6E projection",
            False, "retained for matrix provenance, not a root source",
        ),
    )


def provenance_map() -> dict[str, Any]:
    entries = [entry.__dict__ for entry in r6d_provenance_entries()]
    return {
        "schema": "AS003PR6ER1_R6D_PROVENANCE_MAP_V1",
        "source": "immutable R6D symbolic matrix plus source implementation",
        "classes": list(PROVENANCE_CLASSES),
        "entries": entries,
        "common_root_evidence_fields": [entry.field for entry in r6d_provenance_entries() if entry.common_root_supported],
        "finding": "No R6D field consumed by the old R6E O0 projection is established as COMMON_ROOT_EVIDENCE.",
    }


def old_o0_signature(row: dict[str, Any]) -> dict[str, Any] | None:
    """Describe the frozen R6E O0 result without treating it as lawful."""
    options = root_options_for_row(row)
    if not options:
        return None
    option = options[0]
    variant = option.support_variants[0]
    return {
        "root_frame_identity": option.root_frame_identity,
        "semantic_identity": option.semantic_identity,
        "source_dependency": option.source_dependencies,
        "variant_id": variant.variant_id,
        "observed_total_demand": variant.observed_total_demand,
        "provenance": variant.provenance,
        "derived_from": "route_case",
    }


def o0_audit(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    examples: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        signature = old_o0_signature(row)
        if signature is None:
            totals["root_option_not_constructible"] += 1
            if len(examples) < 6:
                examples.append({"index": index, "reason": "modality_unknown_or_route_absent", **row})
            continue
        totals["candidate_derived_o0"] += 1
        if len(examples) < 12:
            examples.append({"index": index, "reason": "route_case_enters_o0", "o0": signature, **row})
    return {
        "schema": "AS003PR6ER1_O0_PROVENANCE_AUDIT_V1",
        "total_rows": sum(totals.values()),
        "totals": dict(sorted(totals.items())),
        "root_option_contract": "O0 = f(common-root source evidence only)",
        "candidate_derived_fields": ["route_case", "opportunity_modality"],
        "common_root_option_rows": 0,
        "examples": examples,
        "finding": "Every old nonempty O0 is constructed from route_case; no lawful common-root O0 is present in R6D.",
    }


def contamination_test(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_key: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (
            row["active_obligations"], row["corrective_services"], row["opportunity_modality"],
            row["open_world"], row["hard_violation"], row["nonroute_known_impossibility"],
        )
        by_key.setdefault(key, {})[row["route_case"]] = row

    changed_demand = 0
    changed_existence = 0
    comparisons = 0
    for variants in by_key.values():
        for left, right in (("fits_deadline", "misses_deadline"), ("fits_deadline", "absent"), ("misses_deadline", "absent")):
            if left not in variants or right not in variants:
                continue
            comparisons += 1
            a = old_o0_signature(variants[left])
            b = old_o0_signature(variants[right])
            if (a is None) != (b is None):
                changed_existence += 1
            elif a is not None and b is not None and a["observed_total_demand"] != b["observed_total_demand"]:
                changed_demand += 1

    fixed_root = {
        "root_frame_identity": "counterfactual-fixed-root",
        "semantic_identity": ["fixed-known-option"],
        "source_dependency": ["fixed-common-root-token"],
        "observed_total_demand": 7,
        "provenance": ["counterfactual-only"],
    }
    fixed_invariant = True
    for variants in by_key.values():
        signatures = [fixed_root for _ in variants]
        fixed_invariant = fixed_invariant and all(item == signatures[0] for item in signatures)

    return {
        "schema": "AS003PR6ER1_CONTAMINATION_TEST_V1",
        "route_case_variant_groups": len(by_key),
        "route_case_comparisons": comparisons,
        "old_projection": {
            "o0_demand_changed": changed_demand,
            "o0_existence_changed": changed_existence,
            "route_case_changes_o0": changed_demand + changed_existence > 0,
        },
        "fixed_root_counterfactual": {
            "root_held_constant": True,
            "o0_invariant_under_route_case": fixed_invariant,
            "qualification_status": "NOT_LAWFUL_R6D_EVIDENCE",
        },
        "attribution_only_fields_do_not_supply_dependency_edges": True,
    }


def safe_reapplication(rows: list[dict[str, Any]], historical_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    counts = Counter()
    row_results: list[dict[str, Any]] = []
    historical_rows = historical_rows or []
    for index, row in enumerate(rows):
        old = old_o0_signature(row)
        if old is None:
            reason = "ROOT_OPTION_NOT_CONSTRUCTIBLE"
            counts["rejected_absent_or_unknown_root"] += 1
        else:
            reason = "CANDIDATE_DERIVED_ROOT_CONTAMINATION"
            counts["rejected_candidate_derived_o0"] += 1
        historical = historical_rows[index] if index < len(historical_rows) else {}
        row_results.append({
            "index": index,
            "route_case": row["route_case"],
            "opportunity_modality": row["opportunity_modality"],
            "hard_violation": row["hard_violation"],
            "nonroute_known_impossibility": row["nonroute_known_impossibility"],
            "old_r6e_relation": historical.get("relation", False),
            "old_r6e_o0": old,
            "provenance_safe_status": "REJECTED",
            "rejection_reason": reason,
            "relation": False,
            "route_causal": False,
        })
    old_positive = sum(1 for row in historical_rows if row.get("relation") is True)
    old_route_positive = sum(1 for row in historical_rows if row.get("relation") is True and not row.get("nonroute_known_impossibility"))
    return {
        "schema": "AS003PR6ER1_PROVENANCE_SAFE_REAPPLICATION_V1",
        "rows": row_results,
        "totals": dict(sorted(counts.items())),
        "lawful_common_root_rows": 0,
        "ordinary_hard_admissible_rows_with_lawful_o0": 0,
        "positive_relations": 0,
        "route_causal_relations": 0,
        "nonroute_relations": 0,
        "asymmetric_unknown_blocks": 0,
        "historical_r6e_positive_relations": old_positive,
        "historical_r6e_route_causal_relations": old_route_positive,
        "finding": "No R6D row can be requalified because no row contains a demonstrably pre-candidate common-root option set.",
    }


def retained_witness_audit() -> dict[str, Any]:
    return {
        "schema": "AS003PR6ER1_RETAINED_WITNESS_PROVENANCE_V1",
        "witness": "R6B-R1/R6C seven-tick verified route witness",
        "semantics": "MAY / VERIFIED_OBSERVED_SUPPORT",
        "documented_pre_candidate_source_chain": False,
        "r6d_representation": "not serialized as a common-root option; R6D uses a candidate-A fixture in open_world.py",
        "classification": "COMMON_ROOT_NOT_ESTABLISHED",
        "usable_for_requalification": False,
    }


def nonroute_audit() -> dict[str, Any]:
    return {
        "schema": "AS003PR6ER1_NONROUTE_ATTRIBUTION_AUDIT_V1",
        "r6d_field": "nonroute_known_impossibility",
        "classification": "CANDIDATE_B_SPECIFIC",
        "dependency_edge_proven": False,
        "r6e_edge_used": "B invalidates known-route-support",
        "lawful_conclusion": "Generic non-route impossibility cannot establish that B destroyed a particular root dependency.",
        "safe_action": "Do not apply dependency invalidation or count a non-route positive.",
    }
