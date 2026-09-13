#!/usr/bin/env python3
"""Literal AS-017 development CLI with local SQLite and durable case copies."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.as017.development import DIRECTIVE, HORIZON, execute
from tools.as017_evidence import (
    EvidenceFormatError,
    StageJournal,
    publish_file_once,
    publish_json_once,
    reduce_acceptance_trace,
    reduce_certificate_linkage,
    stream_sha256,
    validate_sqlite_copy,
)


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--local-work", type=Path, required=True)
    parser.add_argument("--evidence-work", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--publication-smoke", action="store_true")
    args = parser.parse_args()
    accounting_path = args.local_work.parent / f"{args.local_work.name}.stages.jsonl"
    if args.local_work.exists() or args.evidence_work.exists() or args.result.exists() or accounting_path.exists():
        raise RuntimeError("AS017_CREATE_ONCE_PATH_ALREADY_EXISTS")
    if head() != args.candidate_commit:
        raise RuntimeError("AS017_CANDIDATE_COMMIT_MISMATCH")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("directive") != DIRECTIVE or manifest.get("horizon_ticks") != HORIZON:
        raise RuntimeError("AS017_MANIFEST_CONTRACT_INVALID")
    manifest_hash = stream_sha256(args.manifest)
    journal = StageJournal(accounting_path)
    journal.append(
        "REGISTERED",
        candidate_commit=args.candidate_commit,
        manifest_sha256=manifest_hash,
        pid=os.getpid(),
        expected_cases=sum(len(manifest["development_regimes"][regime]) for regime in ("R0", "R1", "R2", "R3")),
        target_ticks=HORIZON,
    )

    if args.publication_smoke:
        args.local_work.mkdir(parents=True, exist_ok=False)
        database = args.local_work / "publication-smoke.sqlite"
        connection = sqlite3.connect(database)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE smoke (value TEXT NOT NULL)")
            connection.execute("INSERT INTO smoke VALUES ('local-runtime-storage')")
            connection.commit()
        finally:
            connection.close()
        database_hash = publish_file_once(
            database, args.evidence_work / "case-databases" / database.name
        )
        with sqlite3.connect(args.evidence_work / "case-databases" / database.name) as exported:
            observed = exported.execute("SELECT value FROM smoke").fetchall()
        if observed != [("local-runtime-storage",)]:
            raise RuntimeError("AS017_PUBLICATION_SMOKE_CONTENT_MISMATCH")
        payload = {
            "schema": "AS017_DEVELOPMENT_PUBLICATION_SMOKE_V1",
            "directive": DIRECTIVE,
            "terminal": "AS017_PUBLICATION_SMOKE_PASS",
            "candidate_commit": args.candidate_commit,
            "seed_manifest_sha256": manifest_hash,
            "runtime_storage": "local_sqlite_wal_shm",
            "database_sha256": database_hash,
            "formal_seed_consumption": 0,
        }
        digest = publish_json_once(args.result, payload)
        journal.append("RUNNER_FINISHED", terminal="AS017_PUBLICATION_SMOKE_PASS", result_sha256=digest)
        journal.close()
        print(json.dumps({"terminal": "AS017_PUBLICATION_SMOKE_PASS", "sha256": digest}, sort_keys=True))
        return

    def case_id(row: dict) -> str:
        return f"{row['regime']}-{row['seed_index']:02d}-{row['seed']}"

    def on_case_start(info: dict) -> None:
        journal.append(
            "STARTED",
            case_id=f"{info['regime']}-{info['seed_index']:02d}-{info['seed']}",
            regime=info["regime"], seed=info["seed"], seed_index=info["seed_index"],
            target_ticks=info["target_ticks"], pid=os.getpid(), started_monotonic=time.monotonic(),
        )

    def on_execution_finished(row: dict) -> None:
        local_result = args.local_work / "case-results" / f"{case_id(row)}.json"
        local_result_hash = publish_json_once(local_result, row)
        journal.append(
            "EXECUTION_FINISHED",
            case_id=case_id(row),
            ticks=row.get("ticks"),
            terminal=row.get("terminal"),
            local_result_path=str(local_result),
            local_result_sha256=local_result_hash,
        )

    def on_case(row: dict) -> None:
        cid = case_id(row)
        database = args.local_work / f"{row['regime']}-{row['seed']}.sqlite"
        trace = args.local_work / str(row["decision_trace_filename"])
        if not database.is_file() or not trace.is_file():
            raise RuntimeError("AS017_LOCAL_ARTIFACT_MISSING")
        compact_trace = args.local_work / "case-traces-compact" / trace.name
        trace_summary = reduce_acceptance_trace(trace, compact_trace)
        if trace_summary["rows"] != row.get("ticks"):
            raise EvidenceFormatError(
                f"trace_row_count_mismatch:expected_{row.get('ticks')}_got_{trace_summary['rows']}"
            )
        database_validation = validate_sqlite_copy(database)
        journal.append(
            "LOCALLY_VALIDATED",
            case_id=cid,
            database_path=str(database),
            trace_path=str(trace),
            database_bytes=database.stat().st_size,
            trace_bytes=trace.stat().st_size,
            database_validation=database_validation,
            trace_processing=trace_summary,
        )
        destination = args.evidence_work / "case-databases" / database.name
        journal.append("EXPORT_STARTED", case_id=cid, artifact="database", destination=str(destination))
        row["database_sha256"] = publish_file_once(database, destination)
        journal.append("EXPORT_VERIFIED", case_id=cid, artifact="database", sha256=row["database_sha256"])
        row["candidate_commit"] = args.candidate_commit
        row["seed_manifest_sha256"] = manifest_hash
        trace_destination = args.evidence_work / "case-traces" / compact_trace.name
        journal.append("EXPORT_STARTED", case_id=cid, artifact="compact_trace", destination=str(trace_destination))
        row["decision_trace_sha256"] = publish_file_once(compact_trace, trace_destination)
        journal.append("EXPORT_VERIFIED", case_id=cid, artifact="compact_trace", sha256=row["decision_trace_sha256"])
        linkage_records = args.local_work / "certificate-linkage" / f"{cid}.jsonl"
        linkage = reduce_certificate_linkage(compact_trace, linkage_records)
        linkage["candidate_commit"] = args.candidate_commit
        linkage_path = args.evidence_work / "certificate-linkage" / f"{cid}.summary.json"
        linkage_records_destination = args.evidence_work / "certificate-linkage" / linkage_records.name
        journal.append("EXPORT_STARTED", case_id=cid, artifact="linkage_records", destination=str(linkage_records_destination))
        linkage["records_sha256"] = publish_file_once(linkage_records, linkage_records_destination)
        journal.append("EXPORT_VERIFIED", case_id=cid, artifact="linkage_records", sha256=linkage["records_sha256"])
        row["certificate_linkage_sha256"] = publish_json_once(linkage_path, linkage)
        row["certificate_linkage_summary_filename"] = linkage_path.name
        row["certificate_linkage_records_filename"] = linkage_records_destination.name
        row["trace_processing"] = trace_summary
        case_result_destination = args.evidence_work / "case-results" / f"{cid}.json"
        case_result_sha256 = publish_json_once(case_result_destination, row)
        journal.append("EXPORT_VERIFIED", case_id=cid, artifact="case_result", sha256=case_result_sha256)
        journal.append(
            "CASE_FINISHED",
            case_id=cid,
            required_artifacts=["database", "compact_trace", "linkage_records", "linkage_summary", "case_result"],
            case_result_sha256=case_result_sha256,
        )

    def on_case_accounted(row: dict) -> None:
        try:
            on_case(row)
        except Exception as exc:
            journal.append(
                "EXPORT_PENDING",
                case_id=case_id(row),
                exception_type=type(exc).__name__,
                exception=str(exc),
            )
            raise

    try:
        journal.append("RUNNER_STARTED", pid=os.getpid(), started_monotonic=time.monotonic())
        result = execute(manifest, args.local_work, on_case=on_case_accounted, on_case_start=on_case_start,
                         on_execution_finished=on_execution_finished)
        result.update(candidate_commit=args.candidate_commit, seed_manifest_sha256=manifest_hash,
                      runtime_storage="local_sqlite_wal_shm", formal_seed_consumption=0,
                      retries=0, reseeds=0)
        digest = publish_json_once(args.result, result)
        journal.append("CAMPAIGN_FINISHED", terminal=result["terminal"], completed_runs=result.get("completed_runs"), result_sha256=digest)
        print(json.dumps({"terminal": result["terminal"], "sha256": digest}, sort_keys=True))
        if not result["all_completed"]:
            raise SystemExit(1)
    except BaseException as exc:
        journal.append("RUNNER_INTERRUPTED", exception_type=type(exc).__name__, exception=str(exc), pid=os.getpid())
        raise
    finally:
        journal.close()


if __name__ == "__main__":
    main()
