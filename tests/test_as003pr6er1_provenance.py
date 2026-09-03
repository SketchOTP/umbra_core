from __future__ import annotations

from experiments.as003pr6e.matrix import root_options_for_row
from experiments.as003pr6e_r1.audit import (
    contamination_test,
    o0_audit,
    provenance_map,
    safe_reapplication,
)


def row(route_case: str, modality: str = "MUST") -> dict[str, object]:
    return {
        "active_obligations": 1,
        "corrective_services": 1,
        "opportunity_modality": modality,
        "route_case": route_case,
        "open_world": True,
        "hard_violation": False,
        "nonroute_known_impossibility": False,
        "relation": False,
    }


def test_route_case_changes_frozen_o0_but_not_a_valid_common_root() -> None:
    fits = root_options_for_row(row("fits_deadline"))[0].support_variants[0]
    misses = root_options_for_row(row("misses_deadline"))[0].support_variants[0]
    assert fits.observed_total_demand == 4
    assert misses.observed_total_demand == 7
    result = contamination_test([row("fits_deadline"), row("misses_deadline"), row("absent")])
    assert result["old_projection"]["route_case_changes_o0"] is True
    assert result["fixed_root_counterfactual"]["o0_invariant_under_route_case"] is True


def test_provenance_map_has_no_established_common_root_field() -> None:
    mapping = provenance_map()
    assert mapping["common_root_evidence_fields"] == []
    assert any(item["field"] == "route_case" and item["classification"] == "SYNTHETIC_MATRIX_CONTROL" for item in mapping["entries"])


def test_safe_reapplication_rejects_every_row_without_inventing_o0() -> None:
    rows = [row("fits_deadline"), row("misses_deadline"), row("absent"), row("fits_deadline", "UNKNOWN")]
    audit = o0_audit(rows)
    assert audit["common_root_option_rows"] == 0
    safe = safe_reapplication(rows, [{"relation": False}] * len(rows))
    assert safe["positive_relations"] == 0
    assert safe["route_causal_relations"] == 0
    assert safe["totals"] == {"rejected_absent_or_unknown_root": 2, "rejected_candidate_derived_o0": 2}


def test_nonroute_attribution_is_not_a_dependency_edge() -> None:
    rows = [row("fits_deadline")]
    rows[0]["nonroute_known_impossibility"] = True
    safe = safe_reapplication(rows)
    assert safe["positive_relations"] == 0
    assert safe["rows"][0]["provenance_safe_status"] == "REJECTED"
