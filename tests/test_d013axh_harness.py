"""Synthetic-only D-013AXH durability qualification tests."""

from pathlib import Path

import pytest

from research.course_correction.d013axh_harness.ledger import DurableLedger, NonDeterministicDuplicateResult, atomic_json
from research.course_correction.d013axh_harness.protocol import AX_PROTOCOL, branch_id, protocol_fingerprint, synthetic_branch_spec
from research.course_correction.d013axh_harness.synthetic import completeness_cases, concurrency_case, duplicate_case, run_fault_case


def _root_spec():
    protocol = protocol_fingerprint()
    spec = synthetic_branch_spec(None, 0, depth=1)
    return protocol, spec, branch_id(
        protocol_fp=protocol,
        target=spec["target"],
        start_tick=spec["start_tick"],
        prefix_depth=spec["prefix_depth"],
        parent_branch_id=spec.get("parent_branch_id"),
        action=spec["action"],
        input_state_hash=spec["input_state_hash"],
        rng_state_hash=spec["rng_state_hash"],
        remaining_forced_depth=spec["remaining_forced_depth"],
    )


def test_logical_branch_id_excludes_execution_identity():
    protocol, spec, first = _root_spec()
    second = branch_id(
        protocol_fp=protocol,
        target=spec["target"],
        start_tick=spec["start_tick"],
        prefix_depth=spec["prefix_depth"],
        parent_branch_id=spec.get("parent_branch_id"),
        action=spec["action"],
        input_state_hash=spec["input_state_hash"],
        rng_state_hash=spec["rng_state_hash"],
        remaining_forced_depth=spec["remaining_forced_depth"],
    )
    assert first == second
    assert "execution" not in first


def test_atomic_result_and_conflicting_duplicate_fail_closed(tmp_path: Path):
    protocol, spec, bid = _root_spec()
    ledger = DurableLedger(tmp_path / "ledger.sqlite")
    ledger.create_execution("exec-a", protocol, AX_PROTOCOL["scientific_baseline"])
    ledger.ensure_branch("exec-a", spec, bid)
    assert ledger.claim_branch("exec-a", bid)
    payload = {"logical_branch_id": bid, "value": 1}
    path = tmp_path / "results.json"
    digest = atomic_json(path, payload)
    assert ledger.publish_result("exec-a", bid, payload, str(path), digest) == "COMPLETE"
    assert ledger.publish_result("exec-a", bid, payload, str(path), digest) == "DUPLICATE_SAME"
    with pytest.raises(NonDeterministicDuplicateResult):
        ledger.publish_result("exec-a", bid, {"logical_branch_id": bid, "value": 2}, str(path))
    ledger.close()


@pytest.mark.parametrize("fault", [
    "before_worker_execution",
    "after_running_claim",
    "after_worker_calculation_before_result_publication",
    "after_result_publication_before_ledger_complete",
    "after_ledger_complete_before_frontier_expansion",
    "during_frontier_expansion",
    "after_expansion_before_next_scheduling",
    "during_aggregation",
    "after_aggregation_computation_before_summary_publication",
])
def test_crash_recovery_matrix_case(tmp_path: Path, fault: str):
    result = run_fault_case(tmp_path, fault, workers=2)
    assert result["crash_observed"] is True
    assert result["execution_complete"] is True
    assert result["dataset_hash"]


def test_completeness_refuses_incomplete_states(tmp_path: Path):
    results = completeness_cases(tmp_path)
    assert results and all(results.values())


def test_concurrency_invariance(tmp_path: Path):
    result = concurrency_case(tmp_path)
    assert result["equal"] is True
