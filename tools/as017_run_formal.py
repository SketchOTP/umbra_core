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
from tools.as017_evidence import publish_json_once, stream_sha256


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def require_clean_candidate(candidate_commit: str) -> str:
    execution_head = head()
    if execution_head != candidate_commit:
        raise RuntimeError("AS017_FORMAL_CANDIDATE_COMMIT_MISMATCH")
    status = subprocess.check_output(["git", "status", "--porcelain"], text=True)
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
    result = execute(manifest, args.work)
    result.update(
        candidate_commit=args.candidate_commit,
        seed_manifest_sha256=manifest_hash,
        formal_seed_consumption=0,
        retries=0,
        reseeds=0,
    )
    publish_json_once(args.result, result)
    print(json.dumps({"terminal": result["terminal"], "completed_runs": result["completed_runs"]}, sort_keys=True))
    if not result["all_completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
