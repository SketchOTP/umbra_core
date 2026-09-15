#!/usr/bin/env python3
"""Literal AS-018 formal CLI; preflight never creates an organism."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.as018.qualification import EXECUTION_SUBJECT, execute, validate_manifest
from tools.as017_evidence import StageJournal, publish_json_once, stream_sha256
from tools.as018_formal_acceptance import accept_case


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V1.json"


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def require_clean_candidate(candidate_commit: str) -> str:
    execution_head = head()
    if execution_head != candidate_commit:
        raise RuntimeError("AS018_FORMAL_CANDIDATE_COMMIT_MISMATCH")
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if status:
        raise RuntimeError("AS018_FORMAL_EXECUTION_WORKTREE_NOT_CLEAN")
    return execution_head


def require_lock(lock_path: Path, expected_hash: str, candidate_commit: str) -> dict[str, object]:
    if not lock_path.is_file() or stream_sha256(lock_path) != expected_hash:
        raise RuntimeError("AS018_FORMAL_LOCK_HASH_MISMATCH")
    value = json.loads(lock_path.read_text(encoding="utf-8"))
    if value.get("schema") != "AS018_SCIENTIFIC_LOCK_CONTRACT_V1":
        raise RuntimeError("AS018_FORMAL_LOCK_SCHEMA_INVALID")
    if value.get("organism_implementation_sha") != "e8d048b510a477e677637b67bc0f56473cfe6540":
        raise RuntimeError("AS018_FORMAL_LOCK_ORGANISM_MISMATCH")
    frozen_tree = value.get("publication_model", {}).get("production_subtree_sha_at_organism_subject")
    if value.get("formal_execution_subject") != candidate_commit:
        try:
            current_tree = subprocess.check_output(
                ["git", "rev-parse", f"{candidate_commit}:umbra_core"], cwd=ROOT, text=True
            ).strip()
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("AS018_FORMAL_LOCK_EXECUTION_SUBJECT_MISMATCH") from exc
        if current_tree != frozen_tree:
            raise RuntimeError("AS018_FORMAL_LOCK_PRODUCTION_SUBTREE_MISMATCH")
    if value.get("lock_status") != "ESTABLISHED_BEFORE_FORMAL_ORGANISM_CREATION":
        raise RuntimeError("AS018_FORMAL_LOCK_NOT_ESTABLISHED")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    parser.add_argument("--lock-sha256", required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    execution_head = require_clean_candidate(args.candidate_commit)
    lock = require_lock(args.lock, args.lock_sha256, args.candidate_commit)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    manifest_hash = stream_sha256(args.manifest)
    if lock["seed_contract"]["manifest_sha256"] != manifest_hash:
        raise RuntimeError("AS018_FORMAL_LOCK_MANIFEST_HASH_MISMATCH")
    if args.preflight:
        print(json.dumps({
            "schema": "AS018_FORMAL_CLI_PREFLIGHT_V1",
            "directive": "UMBRA-AS-018",
            "candidate_commit": args.candidate_commit,
            "execution_head": execution_head,
            "lock_sha256": args.lock_sha256,
            "manifest_sha256": manifest_hash,
            "formal_seed_consumption": 0,
            "formal_organisms_created": 0,
            "scientific_execution_started": False,
            "status": "PASS",
        }, sort_keys=True))
        return
    if args.result is None:
        raise RuntimeError("AS018_FORMAL_RESULT_REQUIRED")
    if args.work.exists() or args.result.exists():
        raise RuntimeError("AS018_FORMAL_CREATE_ONCE_PATH_ALREADY_EXISTS")
    journal_path = args.work.parent / f"{args.work.name}.stages.jsonl"
    journal = StageJournal(journal_path)
    case_ids = [
        f"{regime}-{index:02d}-{int(seed)}"
        for regime in ("R0", "R1", "R2", "R3")
        for index, seed in enumerate(manifest["formal_regimes"][regime])
    ]
    journal.append(
        "REGISTERED",
        candidate_commit=args.candidate_commit,
        lock_sha256=args.lock_sha256,
        manifest_sha256=manifest_hash,
        expected_cases=32,
        registered_case_ids=case_ids,
        target_ticks=7200,
    )

    def on_stage(stage: str, case_id: str, fields: dict[str, object]) -> None:
        if stage == "REGISTERED":
            journal.append("REGISTERED_CASE", case_id=case_id)

    def on_case_start(info: dict[str, object]) -> None:
        journal.append("STARTED", **info)

    def on_execution_finished(row: dict[str, object]) -> None:
        journal.append(
            "EXECUTION_FINISHED",
            case_id=f"{row['regime']}-{int(row['seed_index']):02d}-{row['seed']}",
            ticks=row.get("ticks"),
            terminal=row.get("terminal"),
        )

    def accept(row: dict[str, object]) -> dict[str, object]:
        case_id = f"{row['regime']}-{int(row['seed_index']):02d}-{row['seed']}"
        journal.append("VALIDATION_STARTED", case_id=case_id)
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
            on_stage=on_stage,
        )
        result.update(
            lock_sha256=args.lock_sha256,
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
        print(json.dumps({
            "terminal": result["terminal"],
            "completed_runs": result["completed_runs"],
            "accepted_cases": result.get("accepted_cases", 0),
            "formal_seed_consumption": result["formal_seed_consumption"],
        }, sort_keys=True))
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
