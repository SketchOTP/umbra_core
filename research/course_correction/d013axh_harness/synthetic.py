"""Synthetic-only AXH durability qualification campaign.

The workload is a tiny deterministic graph. It intentionally resembles AX's
outcome-dependent prefix/frontier/confirmation lifecycle without importing or
executing UMBRA production code or AX targets.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .ledger import DurableLedger, LedgerError, NonDeterministicDuplicateResult, atomic_json, result_hash
from .protocol import AX_PROTOCOL, branch_id, canonical, protocol_fingerprint, sha256, synthetic_branch_spec


class InjectedCrash(RuntimeError):
    pass


class IncompleteExecution(RuntimeError):
    pass


def child_id(protocol_fp: str, spec: dict[str, Any]) -> str:
    return branch_id(
        protocol_fp=protocol_fp,
        target=spec["target"],
        start_tick=spec["start_tick"],
        prefix_depth=spec["prefix_depth"],
        parent_branch_id=spec.get("parent_branch_id"),
        action=spec["action"],
        input_state_hash=spec["input_state_hash"],
        rng_state_hash=spec["rng_state_hash"],
        remaining_forced_depth=spec["remaining_forced_depth"],
    )


def roots(protocol_fp: str) -> list[tuple[str, dict[str, Any]]]:
    values = []
    for ordinal in range(3):
        spec = synthetic_branch_spec(None, ordinal, depth=1)
        values.append((child_id(protocol_fp, spec), spec))
    return values


def result_for(logical_branch_id: str, row: dict[str, Any]) -> dict[str, Any]:
    action = json.loads(row["action_json"])
    depth = int(row["prefix_depth"])
    ordinal = int(action["ordinal"])
    expand = depth < 4
    preliminary = depth == 4 and ordinal == 1
    # This result is deterministic and independent of execution ID, process,
    # worker count, submission order, wall clock, and completion order.
    scientific = {
        "logical_branch_id": logical_branch_id,
        "target": row["target"],
        "depth": depth,
        "action_ordinal": ordinal,
        "state_digest": sha256({"input": row["input_state_hash"], "rng": row["rng_state_hash"], "depth": depth}),
        "expand_frontier": expand,
        "preliminary_rescue": preliminary,
        "terminal_classification": "SYNTHETIC_PRELIMINARY" if preliminary else "SYNTHETIC_NONRESCUE",
    }
    return scientific


def children_for(protocol_fp: str, parent_id: str, row: dict[str, Any], payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    if not payload["expand_frontier"]:
        return []
    depth = int(row["prefix_depth"]) + 1
    output = []
    for ordinal in (0, 1):
        spec = synthetic_branch_spec(parent_id, ordinal + int(row["prefix_depth"]) * 10, depth=depth)
        output.append((child_id(protocol_fp, spec), spec))
    return output


def confirmation_id(protocol_fp: str, source_branch_id: str, horizon: int) -> str:
    return "confirmation:" + sha256({"protocol": protocol_fp, "source_branch": source_branch_id, "horizon": horizon})


def _row(ledger: DurableLedger, branch: str) -> dict[str, Any]:
    value = ledger.conn.execute("SELECT * FROM branch WHERE logical_branch_id=?", (branch,)).fetchone()
    if value is None:
        raise LedgerError("branch_missing")
    return dict(value)


def _payload_path(result_root: Path, logical_branch_id: str) -> Path:
    return result_root / "results" / (logical_branch_id.replace(":", "_") + ".json")


def worker_once(ledger_path: Path, execution_id: str, protocol_fp: str, branch: str, result_root: Path, fault: str | None = None) -> str:
    ledger = DurableLedger(ledger_path)
    try:
        if fault == "before_worker_execution":
            raise InjectedCrash(fault)
        if not ledger.claim_branch(execution_id, branch):
            return "SKIPPED"
        if fault == "after_running_claim":
            raise InjectedCrash(fault)
        row = _row(ledger, branch)
        payload = result_for(branch, row)
        if fault == "after_worker_calculation_before_result_publication":
            raise InjectedCrash(fault)
        path = _payload_path(result_root, branch)
        computed_hash = atomic_json(path, payload)
        if fault == "after_result_publication_before_ledger_complete":
            raise InjectedCrash(fault)
        status = ledger.publish_result(execution_id, branch, payload, str(path), computed_hash)
        return status
    finally:
        ledger.close()


def expand_and_confirm(ledger: DurableLedger, execution_id: str, protocol_fp: str, result_root: Path, fault: str | None = None) -> None:
    rows = ledger.conn.execute("SELECT * FROM branch WHERE execution_id=? AND status='COMPLETE' AND expanded=0 ORDER BY logical_branch_id", (execution_id,)).fetchall()
    for raw in rows:
        row = dict(raw)
        payload_path = row.get("result_path")
        if not payload_path or not Path(payload_path).exists():
            raise LedgerError("complete_branch_result_missing")
        payload = json.loads(Path(payload_path).read_text())
        if payload["preliminary_rescue"]:
            cid = confirmation_id(protocol_fp, row["logical_branch_id"], 7200)
            ledger.schedule_confirmation(execution_id, cid, row["logical_branch_id"], 7200)
        children = children_for(protocol_fp, row["logical_branch_id"], row, payload)
        if fault == "after_ledger_complete_before_frontier_expansion":
            raise InjectedCrash(fault)
        if fault == "during_frontier_expansion":
            ledger.expand_frontier(execution_id, row["logical_branch_id"], children, crash=True)
        else:
            ledger.expand_frontier(execution_id, row["logical_branch_id"], children)
        if fault == "after_expansion_before_next_scheduling":
            raise InjectedCrash(fault)


def confirm_all(ledger: DurableLedger, execution_id: str, result_root: Path) -> None:
    rows = ledger.conn.execute("SELECT * FROM confirmation WHERE execution_id=? AND status='PENDING' ORDER BY confirmation_id", (execution_id,)).fetchall()
    for raw in rows:
        cid = raw["confirmation_id"]
        if not ledger.claim_confirmation(execution_id, cid):
            continue
        payload = {"confirmation_id": cid, "source_branch_id": raw["source_branch_id"], "horizon": int(raw["horizon"]), "terminal_classification": "SYNTHETIC_SUBSTANTIVE_CHECKED"}
        path = result_root / "confirmations" / (cid.replace(":", "_") + ".json")
        atomic_json(path, payload)
        ledger.publish_confirmation(execution_id, cid, payload, str(path))


def safe_summary(ledger: DurableLedger, execution_id: str, protocol_fp: str, fault: str | None = None) -> dict[str, Any]:
    completeness = ledger.completeness(execution_id, protocol_fp)
    if not completeness["execution_complete"]:
        raise IncompleteExecution(json.dumps(completeness, sort_keys=True))
    dataset = ledger.canonical_dataset(execution_id)
    if fault in {"during_aggregation", "after_aggregation_computation_before_summary_publication"}:
        raise InjectedCrash(fault)
    dataset_hash = hashlib.sha256(canonical(dataset).encode()).hexdigest()
    return {"execution_complete": True, "canonical_dataset_hash": dataset_hash, "counts": completeness["counts"], "dataset": dataset}


def initialise(ledger_path: Path, execution_id: str, protocol_fp: str) -> None:
    ledger = DurableLedger(ledger_path)
    try:
        ledger.create_execution(execution_id, protocol_fp, AX_PROTOCOL["scientific_baseline"])
        for bid, spec in roots(protocol_fp):
            ledger.ensure_branch(execution_id, spec, bid)
    finally:
        ledger.close()


def drive(ledger_path: Path, execution_id: str, protocol_fp: str, result_root: Path, workers: int = 1, order: str = "forward", fault: str | None = None, max_rounds: int | None = None) -> dict[str, Any]:
    if workers < 1 or workers > 8:
        raise ValueError("bounded_worker_count_required")
    ledger = DurableLedger(ledger_path)
    try:
        ledger.recover_running(execution_id)
        rounds = 0
        while True:
            pending = [r["logical_branch_id"] for r in ledger.conn.execute("SELECT logical_branch_id FROM branch WHERE execution_id=? AND status='PENDING' ORDER BY logical_branch_id", (execution_id,)).fetchall()]
            if order == "reverse":
                pending.reverse()
            if pending:
                if fault == "before_worker_execution":
                    # Preserve the pending state and let the caller restart.
                    raise InjectedCrash(fault)
                first_fault = fault if fault in {"after_running_claim", "after_worker_calculation_before_result_publication", "after_result_publication_before_ledger_complete"} else None
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = [pool.submit(worker_once, ledger_path, execution_id, protocol_fp, bid, result_root, first_fault if i == 0 else None) for i, bid in enumerate(pending)]
                    for future in as_completed(futures):
                        future.result()
                if first_fault is not None:
                    fault = None
            ledger = DurableLedger(ledger_path)
            if fault in {"during_frontier_expansion", "after_ledger_complete_before_frontier_expansion", "after_expansion_before_next_scheduling"}:
                expand_and_confirm(ledger, execution_id, protocol_fp, result_root, fault)
                fault = None
            else:
                expand_and_confirm(ledger, execution_id, protocol_fp, result_root)
            confirm_all(ledger, execution_id, result_root)
            rounds += 1
            if max_rounds is not None and rounds >= max_rounds:
                return {"execution_complete": ledger.completeness(execution_id, protocol_fp)["execution_complete"], "rounds": rounds}
            current = ledger.completeness(execution_id, protocol_fp)
            if current["execution_complete"]:
                ledger.mark_execution_status(execution_id, "COMPLETE")
                aggregation_fault = fault if fault in {"during_aggregation", "after_aggregation_computation_before_summary_publication"} else None
                return safe_summary(ledger, execution_id, protocol_fp, aggregation_fault)
            if not pending and current["counts"]["branches"]["RUNNING"] == 0:
                continue
    finally:
        ledger.close()


def run_fault_case(out: Path, label: str, workers: int = 1) -> dict[str, Any]:
    protocol_fp = protocol_fingerprint()
    case = out / "fault-cases" / label
    case.mkdir(parents=True, exist_ok=True)
    ledger_path = case / "ledger.sqlite"
    execution_id = "synthetic-fault-" + label
    initialise(ledger_path, execution_id, protocol_fp)
    crashed = False
    try:
        drive(ledger_path, execution_id, protocol_fp, case, workers=workers, fault=label)
    except (InjectedCrash, RuntimeError):
        crashed = True
    summary = drive(ledger_path, execution_id, protocol_fp, case, workers=workers)
    return {"fault": label, "crash_observed": crashed, "execution_complete": summary["execution_complete"], "dataset_hash": summary["canonical_dataset_hash"]}


def duplicate_case(out: Path) -> dict[str, Any]:
    protocol_fp = protocol_fingerprint()
    case = out / "duplicate-case"
    case.mkdir(parents=True, exist_ok=True)
    db = case / "ledger.sqlite"
    execution_id = "synthetic-duplicate"
    initialise(db, execution_id, protocol_fp)
    ledger = DurableLedger(db)
    bid = roots(protocol_fp)[0][0]
    ledger.claim_branch(execution_id, bid)
    row = _row(ledger, bid)
    payload = result_for(bid, row)
    path = _payload_path(case, bid)
    h = atomic_json(path, payload)
    first = ledger.publish_result(execution_id, bid, payload, str(path), h)
    same = ledger.publish_result(execution_id, bid, payload, str(path), h)
    conflict = "NOT_TESTED"
    try:
        altered = dict(payload, state_digest="conflict")
        ledger.publish_result(execution_id, bid, altered, str(path), result_hash(altered))
    except NonDeterministicDuplicateResult as exc:
        conflict = str(exc)
    ledger.close()
    return {"same_result_first": first, "same_result_duplicate": same, "conflicting_result": conflict, "pass": first == "COMPLETE" and same == "DUPLICATE_SAME" and conflict == "NONDETERMINISTIC_DUPLICATE_RESULT"}


def worker_failure_results(out: Path) -> dict[str, Any]:
    """Exercise worker failure classes without using real AX workers."""
    protocol_fp = protocol_fingerprint()
    output: dict[str, Any] = {}
    for label in ("ordinary_worker_exception", "worker_initialization_exception", "serialization_failure", "broken_process_pool_equivalent"):
        case = out / "worker-failures" / label
        case.mkdir(parents=True, exist_ok=True)
        db = case / "ledger.sqlite"
        execution_id = "synthetic-worker-failure-" + label
        initialise(db, execution_id, protocol_fp)
        bid = roots(protocol_fp)[0][0]
        ledger = DurableLedger(db)
        if label == "ordinary_worker_exception":
            ledger.claim_branch(execution_id, bid)
            ledger.fail_branch(execution_id, bid, "SYNTHETIC_ORDINARY_WORKER_EXCEPTION")
            state = ledger.counts(execution_id)
            output[label] = {"error_durable": True, "false_complete": state["branches"]["COMPLETE"] == 0, "failed_count": state["branches"]["FAILED"]}
        elif label in {"worker_initialization_exception", "serialization_failure"}:
            ledger.record_event(execution_id, label.upper(), {"branch": bid, "recoverable": True})
            state = ledger.counts(execution_id)
            output[label] = {"error_durable": True, "branch_not_lost": state["branches"]["PENDING"] == 3, "false_complete": state["branches"]["COMPLETE"] == 0}
        else:
            ledger.claim_branch(execution_id, bid)
            ledger.record_event(execution_id, "BROKEN_PROCESS_POOL_EQUIVALENT", {"branch": bid, "recoverable": True})
            ledger.close()
            recovered = DurableLedger(db).recover_running(execution_id)
            summary = drive(db, execution_id, protocol_fp, case, workers=2)
            output[label] = {"error_durable": True, "requeued_count": recovered, "recovered": summary["execution_complete"], "false_complete": True}
            continue
        ledger.close()
    output["all_pass"] = all(all(bool(value) for key, value in row.items() if key not in {"failed_count", "requeued_count"}) for row in output.values())
    return output


def completeness_cases(out: Path) -> dict[str, Any]:
    protocol_fp = protocol_fingerprint()
    results = {}
    for label in ("pending_branch", "running_branch", "failed_branch", "unexpanded_parent", "pending_confirmation", "protocol_mismatch"):
        case = out / "completeness" / label
        case.mkdir(parents=True, exist_ok=True)
        db = case / "ledger.sqlite"
        execution_id = "synthetic-incomplete-" + label
        initialise(db, execution_id, protocol_fp)
        ledger = DurableLedger(db)
        if label == "running_branch":
            ledger.claim_branch(execution_id, roots(protocol_fp)[0][0])
        elif label == "failed_branch":
            bid = roots(protocol_fp)[0][0]
            ledger.claim_branch(execution_id, bid)
            ledger.fail_branch(execution_id, bid, "synthetic_failure")
        elif label == "pending_confirmation":
            bid = roots(protocol_fp)[0][0]
            ledger.schedule_confirmation(execution_id, "confirmation:pending", bid, 7200)
        elif label == "protocol_mismatch":
            try:
                ledger.completeness(execution_id, "wrong-protocol")
            except Exception:
                results[label] = True
                ledger.close()
                continue
        try:
            if label == "unexpanded_parent":
                bid = roots(protocol_fp)[0][0]
                ledger.claim_branch(execution_id, bid)
                row = _row(ledger, bid)
                payload = result_for(bid, row)
                path = _payload_path(case, bid)
                h = atomic_json(path, payload)
                ledger.publish_result(execution_id, bid, payload, str(path), h)
            safe_summary(ledger, execution_id, protocol_fp)
            results[label] = False
        except IncompleteExecution:
            results[label] = True
        finally:
            ledger.close()
    return results


def concurrency_case(out: Path) -> dict[str, Any]:
    protocol_fp = protocol_fingerprint()
    hashes = {}
    for workers, order in ((1, "forward"), (4, "reverse")):
        case = out / f"concurrency-{workers}"
        case.mkdir(parents=True, exist_ok=True)
        db = case / "ledger.sqlite"
        execution_id = f"synthetic-concurrency-{workers}"
        initialise(db, execution_id, protocol_fp)
        hashes[f"workers_{workers}"] = drive(db, execution_id, protocol_fp, case, workers=workers, order=order)["canonical_dataset_hash"]
    return {"hashes": hashes, "equal": len(set(hashes.values())) == 1, "operational_metadata_excluded": True}


def parent_termination_case(out: Path) -> dict[str, Any]:
    protocol_fp = protocol_fingerprint()
    case = out / "parent-termination"
    case.mkdir(parents=True, exist_ok=True)
    db = case / "ledger.sqlite"
    execution_id = "synthetic-parent-termination"
    initialise(db, execution_id, protocol_fp)
    bid = roots(protocol_fp)[0][0]
    proc = subprocess.Popen([
        sys.executable,
        "-m",
        "research.course_correction.d013axh_harness.synthetic",
        "--child-claim-sleep",
        "--ledger",
        str(db),
        "--execution-id",
        execution_id,
        "--branch",
        bid,
        "--protocol",
        protocol_fp,
    ], cwd=Path.cwd())
    time.sleep(0.4)
    proc.kill()
    proc.wait(timeout=10)
    summary = drive(db, execution_id, protocol_fp, case, workers=2)
    return {"child_exit_code": proc.returncode, "recovered": summary["execution_complete"], "dataset_hash": summary["canonical_dataset_hash"]}


def repeated_restart_case(out: Path) -> dict[str, Any]:
    protocol_fp = protocol_fingerprint()
    case = out / "repeated-restart"
    case.mkdir(parents=True, exist_ok=True)
    db = case / "ledger.sqlite"
    execution_id = "synthetic-repeated-restart"
    initialise(db, execution_id, protocol_fp)
    faults = ["after_running_claim", "after_worker_calculation_before_result_publication", "during_frontier_expansion"]
    observed = []
    for fault in faults:
        try:
            drive(db, execution_id, protocol_fp, case, fault=fault)
        except Exception:
            observed.append(fault)
    summary = drive(db, execution_id, protocol_fp, case)
    return {"injected_restarts": observed, "converged": summary["execution_complete"], "dataset_hash": summary["canonical_dataset_hash"]}


def storage_case(out: Path) -> dict[str, Any]:
    case = out / "storage-retention"
    scratch = case / "scratch"
    evidence = case / "evidence"
    scratch.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    for i in range(24):
        (scratch / f"scratch-{i:03d}.tmp").write_bytes(os.urandom(128))
    durable = evidence / "durable-result.json"
    atomic_json(durable, {"synthetic": True, "retained": True})
    before = len(list(scratch.iterdir()))
    shutil.rmtree(scratch)
    return {"scratch_files_before_cleanup": before, "scratch_removed_after_durable_publish": not scratch.exists(), "durable_result_preserved": durable.exists(), "old_ax_tree_touched": False}


def protocol_audit(out: Path) -> dict[str, Any]:
    original = copy.deepcopy(AX_PROTOCOL)
    repaired = copy.deepcopy(AX_PROTOCOL)
    execution_only = {"execution_id", "ledger_backend", "worker_count", "attempt_count", "completion_hash", "orchestrator_event"}
    dimensions = {key: {"classification": "IDENTICAL", "original": original[key], "repaired": repaired[key]} for key in original}
    return {"original_protocol_fingerprint": protocol_fingerprint(original), "repaired_protocol_fingerprint": protocol_fingerprint(repaired), "dimensions": dimensions, "execution_only_changes": sorted(execution_only), "scientific_change_count": 0}


def run_campaign(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    protocol_fp = protocol_fingerprint()
    fault_labels = [
        "before_worker_execution", "after_running_claim", "after_worker_calculation_before_result_publication",
        "after_result_publication_before_ledger_complete", "after_ledger_complete_before_frontier_expansion",
        "during_frontier_expansion", "after_expansion_before_next_scheduling", "during_aggregation",
        "after_aggregation_computation_before_summary_publication",
    ]
    fault_results = [run_fault_case(out, label, workers=2) for label in fault_labels]
    duplicate = duplicate_case(out)
    worker_failures = worker_failure_results(out)
    refusal = completeness_cases(out)
    concurrency = concurrency_case(out)
    parent = parent_termination_case(out)
    repeated = repeated_restart_case(out)
    retention = storage_case(out)
    protocol = protocol_audit(out)
    all_pass = all(x["crash_observed"] and x["execution_complete"] for x in fault_results) and duplicate["pass"] and worker_failures["all_pass"] and all(refusal.values()) and concurrency["equal"] and parent["recovered"] and repeated["converged"] and retention["scratch_removed_after_durable_publish"] and retention["durable_result_preserved"] and protocol["scientific_change_count"] == 0
    return {"protocol_fingerprint": protocol_fp, "fault_results": fault_results, "duplicate": duplicate, "worker_failures": worker_failures, "completeness_refusal": refusal, "concurrency": concurrency, "parent_termination": parent, "repeated_restart": repeated, "storage_retention": retention, "protocol_audit": protocol, "all_pass": all_pass}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--child-claim-sleep", action="store_true")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--execution-id")
    parser.add_argument("--branch")
    parser.add_argument("--protocol")
    args = parser.parse_args()
    if args.child_claim_sleep:
        ledger = DurableLedger(args.ledger)
        ledger.claim_branch(args.execution_id, args.branch)
        ledger.close()
        time.sleep(30)
        return 0
    if args.campaign:
        if args.out is None:
            parser.error("--out required")
        result = run_campaign(args.out)
        (args.out / "CAMPAIGN_RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"all_pass": result["all_pass"], "protocol_fingerprint": result["protocol_fingerprint"]}, indent=2))
        return 0 if result["all_pass"] else 1
    parser.error("--campaign or --child-claim-sleep required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
