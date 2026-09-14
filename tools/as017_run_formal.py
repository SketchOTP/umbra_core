#!/usr/bin/env python3
"""Literal AS-017 formal CLI with a contract-only preflight mode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.as017.qualification import DIRECTIVE, execute, validate_manifest
from tools.as017_evidence import StageJournal, publish_json_once, stream_sha256
from tools.as017_formal_acceptance import accept_case

ROOT = Path(__file__).resolve().parents[1]


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def require_clean_candidate(candidate_commit: str) -> str:
    execution_head = head()
    if execution_head != candidate_commit:
        raise RuntimeError("AS017_FORMAL_CANDIDATE_COMMIT_MISMATCH")
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if status:
        raise RuntimeError("AS017_FORMAL_EXECUTION_WORKTREE_NOT_CLEAN")
    return execution_head


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    execution_head = require_clean_candidate(args.candidate_commit)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    manifest_hash = stream_sha256(args.manifest)
    if args.preflight:
        print(json.dumps({
            "schema": "AS017_FORMAL_CLI_PREFLIGHT_V1",
            "directive": DIRECTIVE,
            "candidate_commit": args.candidate_commit,
            "execution_head": execution_head,
            "manifest_sha256": manifest_hash,
            "formal_seed_consumption": 0,
            "organisms_created": 0,
            "status": "PASS",
        }, sort_keys=True))
        return
    if args.result is None:
        raise RuntimeError("AS017_FORMAL_RESULT_REQUIRED")
    if args.work.exists() or args.result.exists():
        raise RuntimeError("AS017_FORMAL_CREATE_ONCE_PATH_ALREADY_EXISTS")
    journal_path = args.work.parent / f"{args.work.name}.stages.jsonl"
    journal = StageJournal(journal_path)
    journal.append(
        "REGISTERED",
        candidate_commit=args.candidate_commit,
        manifest_sha256=manifest_hash,
        expected_cases=32,
        target_ticks=7200,
    )

    def on_case_start(info: dict[str, object]) -> None:
        journal.append("STARTED", case_id=f"{info['regime']}-{int(info['seed_index']):02d}-{info['seed']}", **info)

    def on_execution_finished(row: dict[str, object]) -> None:
        journal.append(
            "EXECUTION_FINISHED",
            case_id=f"{row['regime']}-{int(row['seed_index']):02d}-{row['seed']}",
            ticks=row.get("ticks"),
            terminal=row.get("terminal"),
        )

    def accept(row: dict[str, object]) -> dict[str, object]:
        return accept_case(row, args.work, args.candidate_commit, manifest_hash, journal)

    try:
        result = execute(
            manifest,
            args.work,
            candidate_commit=args.candidate_commit,
            manifest_sha256=manifest_hash,
            on_case_start=on_case_start,
            on_execution_finished=on_execution_finished,
            accept_case=accept,
        )
        result.update(
            candidate_commit=args.candidate_commit,
            seed_manifest_sha256=manifest_hash,
            runtime_storage="local_sqlite_wal_shm",
            retries=0,
            reseeds=0,
            substitutions=0,
        )
        digest = publish_json_once(args.result, result)
        journal.append(
            "CAMPAIGN_FINISHED",
            terminal=result["terminal"],
            completed_runs=result["completed_runs"],
            accepted_cases=result.get("accepted_cases", 0),
            formal_seed_consumption=result["formal_seed_consumption"],
            result_sha256=digest,
        )
        print(json.dumps({"terminal": result["terminal"], "completed_runs": result["completed_runs"], "accepted_cases": result.get("accepted_cases", 0), "formal_seed_consumption": result["formal_seed_consumption"]}, sort_keys=True))
        if not result["all_completed"]:
            raise SystemExit(1)
    except BaseException as exc:
        if not isinstance(exc, SystemExit):
            journal.append("RUNNER_INTERRUPTED", exception_type=type(exc).__name__, exception=str(exc))
        raise
    finally:
        journal.close()


if __name__ == "__main__":
    main()
