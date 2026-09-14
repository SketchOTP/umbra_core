#!/usr/bin/env python3
"""Copy-only semantic and SQLite validation for an AS-017 development attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.as017_evidence import publish_json_once, stream_sha256, validate_sqlite_copy
from tools.as017_validate_linkage_v2 import validate_linkage_v2


def _hash(path: Path) -> str:
    return stream_sha256(path)


def _validate_database(source: Path, expected_hash: str, expected_tick: int, scratch: Path) -> dict[str, Any]:
    isolated = scratch / source.name
    shutil.copyfile(source, isolated)
    result: dict[str, Any] = {
        "source": str(source),
        "isolated_copy": str(isolated),
        "source_sha256": _hash(source),
        "expected_sha256": expected_hash,
        "sqlite": validate_sqlite_copy(isolated),
        "failures": [],
    }
    if result["source_sha256"] != expected_hash:
        result["failures"].append("database_hash_mismatch")
    if result["sqlite"] != {"integrity_check": "ok", "foreign_key_check_rows": 0}:
        result["failures"].append("sqlite_integrity_or_foreign_key_failure")
    connection = sqlite3.connect(f"file:{isolated}?mode=ro", uri=True)
    try:
        identity = connection.execute("SELECT agent_id, commitment FROM identity").fetchone()
        meta = dict(connection.execute("SELECT key, value FROM meta").fetchall())
        events = connection.execute(
            "SELECT sequence, event_hash FROM events ORDER BY sequence"
        ).fetchall()
        checkpoint = connection.execute(
            "SELECT checkpoint_epoch, compacted_sequence_start, compacted_sequence_end, "
            "compacted_event_count, terminal_event_hash, creation_tick, checkpoint_hash "
            "FROM ledger_checkpoints ORDER BY checkpoint_epoch DESC LIMIT 1"
        ).fetchone()
        snapshots = connection.execute(
            "SELECT sequence, monotonic_time, state_hash FROM snapshots ORDER BY sequence"
        ).fetchall()
    finally:
        connection.close()
    result.update({
        "identity_present": identity is not None,
        "identity_agent_id": identity[0] if identity else None,
        "event_count": len(events),
        "event_sequence_min": events[0][0] if events else None,
        "event_sequence_max": events[-1][0] if events else None,
        "event_tip_hash": events[-1][1] if events else None,
        "meta": meta,
        "checkpoint": checkpoint,
        "snapshot_count": len(snapshots),
        "snapshot_terminal_sequence": snapshots[-1][0] if snapshots else None,
        "snapshot_terminal_tick": snapshots[-1][1] if snapshots else None,
    })
    if identity is None:
        result["failures"].append("identity_missing")
    if not snapshots or snapshots[-1][1] != expected_tick:
        result["failures"].append("snapshot_terminal_tick_mismatch")
    if not checkpoint:
        result["failures"].append("checkpoint_missing")
    else:
        start, end, count, terminal_hash, creation_tick = checkpoint[1:6]
        if end - start + 1 != count:
            result["failures"].append("checkpoint_range_count_mismatch")
        if events and end + 1 != events[0][0]:
            result["failures"].append("checkpoint_tail_join_mismatch")
        if creation_tick > expected_tick:
            result["failures"].append("checkpoint_after_terminal_tick")
        if meta.get("ledger_tip"):
            tip = json.loads(meta["ledger_tip"])
            if tip.get("sequence") != result["event_sequence_max"] or tip.get("event_hash") != result["event_tip_hash"]:
                result["failures"].append("ledger_tip_mismatch")
        if terminal_hash == result["event_tip_hash"]:
            result["failures"].append("checkpoint_terminal_hash_is_current_tail_hash")
    result["verdict"] = "PASS" if not result["failures"] else "FAIL"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("AS017_V8C_VALIDATION_OUTPUT_ALREADY_EXISTS")
    campaign = json.loads(args.result.read_text(encoding="utf-8"))
    failures: list[str] = []
    case_reports: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="as017-v8c-db-audit-") as scratch_name:
        scratch = Path(scratch_name)
        for row in campaign["rows"]:
            case_name = f"{row['regime']}-{row['seed']}"
            database = args.evidence_root / "case-databases" / f"{case_name}.sqlite"
            db_report = _validate_database(database, row["database_sha256"], row["target_ticks"], scratch)
            summary = args.evidence_root / "certificate-linkage" / f"{row['regime']}-{row['seed_index']:02d}-{row['seed']}.summary.json"
            summary_data = json.loads(summary.read_text(encoding="utf-8"))
            linkage_report = validate_linkage_v2(
                summary,
                Path(summary_data["records_path"]),
                Path(summary_data["trace_path"]),
                args.candidate_commit,
            )
            case_report = {
                "case": case_name,
                "regime": row["regime"],
                "seed": row["seed"],
                "ticks": row["ticks"],
                "terminal": row["terminal"],
                "candidate_commit": row["candidate_commit"],
                "manifest_sha256": row["seed_manifest_sha256"],
                "database": db_report,
                "linkage": linkage_report,
            }
            case_report["verdict"] = "PASS" if row["ticks"] == row["target_ticks"] and row["terminal"] == "completed" and db_report["verdict"] == "PASS" and linkage_report["verdict"] == "PASS" else "FAIL"
            if case_report["verdict"] != "PASS":
                failures.append(case_name)
            case_reports.append(case_report)
    payload = {
        "schema": "AS017_V8C_COPY_ONLY_VALIDATION_V2",
        "attempt_id": "V8C",
        "candidate_commit": args.candidate_commit,
        "result_sha256": _hash(args.result),
        "expected_cases": campaign["expected_runs"],
        "reported_cases": campaign["completed_runs"],
        "formal_seed_consumption": campaign["formal_seed_consumption"],
        "retries": campaign["retries"],
        "reseeds": campaign["reseeds"],
        "case_reports": case_reports,
        "failed_cases": failures,
        "verdict": "PASS" if len(case_reports) == campaign["expected_runs"] and not failures else "FAIL",
    }
    digest = publish_json_once(args.output, payload)
    print(json.dumps({"verdict": payload["verdict"], "cases": len(case_reports), "sha256": digest}, sort_keys=True))
    if payload["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
