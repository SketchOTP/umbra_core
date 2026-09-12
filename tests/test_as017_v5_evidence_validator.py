from __future__ import annotations

from copy import deepcopy

from tools.as017_review_v5_evidence import (
    producer_identity,
    validate_linkage,
)


def _fixture(*, translated: bool = False) -> tuple[dict, dict, str]:
    requested = {"heading_delta": 0.25, "toward": "resource"} if translated else {"toward": "resource"}
    applied = {"heading": 1.25, "toward": "resource"} if translated else {"toward": "resource"}
    first = {"capability": "ORIENT" if translated else "CHARGE", "requested_params": requested}
    selected = {"capability": first["capability"], "params": requested, "scores": {}, "total": 0.0}
    proposal = {"capability": first["capability"], "params": requested, "proposal_id": "proposal-1"}
    outcome = {
        "capability": first["capability"],
        "requested_params": requested,
        "applied_params": applied,
        "governance_proposal_id": "proposal-1",
        "verified_outcome_id": "outcome-1",
    }
    certificate = {
        "root_id": "root-1",
        "first_candidate": first,
        "first_candidate_identity": producer_identity(first, parameter_field="requested_params"),
        "status": "PROVEN",
        "witness": [producer_identity(first, parameter_field="requested_params")],
    }
    continuation = {
        "status": "TERMINAL_RECOVERY_REVALIDATED",
        "certificate_root_id": "root-1",
        "certificate_identity": certificate["first_candidate_identity"],
        "governance_proposal_id": "proposal-1",
    }
    decision = {"admitted": True}
    row = {
        "tick": 1,
        "trace_row_hash": "row-1",
        "final_candidate": selected,
        "governance_proposal": proposal,
        "governance_decision": decision,
        "verified_outcome_linkage": outcome,
        "viability_kernel": {"selected_recovery_certificate": certificate},
    }
    link = {
        "tick": 1,
        "trace_row_hash": "row-1",
        "certificate": certificate,
        "selected_candidate": selected,
        "governance_proposal": proposal,
        "governance_decision": decision,
        "verified_outcome": outcome,
        "continuation": continuation,
    }
    linkage = {
        "schema": "AS017_RECOVERY_CERTIFICATE_LINKAGE_V1",
        "candidate_commit": "candidate-1",
        "trace_sha256": "trace-1",
        "linked_records": [link],
        "linked_count": 1,
        "unmatched_count": 0,
    }
    return linkage, {"row-1": row}, "trace-1"


def test_valid_requested_and_adapter_translated_records_pass() -> None:
    for translated in (False, True):
        linkage, rows, trace_hash = _fixture(translated=translated)
        summary, failures = validate_linkage(linkage, rows, trace_hash, "candidate-1")
        assert failures == []
        if translated:
            assert summary["parameter_discrepancies"][0]["status"] == "EXPLAINED_ADAPTER_TRANSLATION"


def test_wrong_candidate_root_and_outcome_remain_detectable() -> None:
    linkage, rows, trace_hash = _fixture()

    wrong_candidate = deepcopy(linkage)
    wrong_candidate["linked_records"][0]["selected_candidate"]["params"]["toward"] = "rest"
    _, failures = validate_linkage(wrong_candidate, rows, trace_hash, "candidate-1")
    assert any("selected_trace_mismatch" in failure for failure in failures)

    wrong_root = deepcopy(linkage)
    wrong_root["linked_records"][0]["certificate"]["root_id"] = "root-other"
    _, failures = validate_linkage(wrong_root, rows, trace_hash, "candidate-1")
    assert any("certificate_trace_mismatch" in failure for failure in failures)

    wrong_outcome = deepcopy(linkage)
    wrong_outcome["linked_records"][0]["verified_outcome"]["verified_outcome_id"] = "outcome-other"
    _, failures = validate_linkage(wrong_outcome, rows, trace_hash, "candidate-1")
    assert any("outcome_trace_mismatch" in failure for failure in failures)


def test_missing_adapter_translation_is_not_waived() -> None:
    linkage, rows, trace_hash = _fixture(translated=True)
    linkage["linked_records"][0]["verified_outcome"]["applied_params"].pop("heading")
    _, failures = validate_linkage(linkage, rows, trace_hash, "candidate-1")
    assert any("adapter_translation_missing" in failure for failure in failures)
