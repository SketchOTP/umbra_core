#!/usr/bin/env python3
"""Literal AS-017 development CLI with local SQLite and durable case copies."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.as017.development import DIRECTIVE, HORIZON, execute


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish_json_once(path: Path, payload: dict) -> str:
    data = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if path.read_bytes() != data:
        raise RuntimeError("AS017_PUBLICATION_READBACK_MISMATCH")
    return hashlib.sha256(data).hexdigest()


def publish_file_once(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open("rb") as src, destination.open("xb") as dst:
        while chunk := src.read(1024 * 1024):
            digest.update(chunk)
            dst.write(chunk)
        dst.flush()
        os.fsync(dst.fileno())
    actual = sha256(destination)
    if actual != digest.hexdigest():
        raise RuntimeError("AS017_DATABASE_COPY_READBACK_MISMATCH")
    return actual


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
    if args.local_work.exists() or args.evidence_work.exists() or args.result.exists():
        raise RuntimeError("AS017_CREATE_ONCE_PATH_ALREADY_EXISTS")
    if head() != args.candidate_commit:
        raise RuntimeError("AS017_CANDIDATE_COMMIT_MISMATCH")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("directive") != DIRECTIVE or manifest.get("horizon_ticks") != HORIZON:
        raise RuntimeError("AS017_MANIFEST_CONTRACT_INVALID")
    manifest_hash = sha256(args.manifest)

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
            "candidate_commit": args.candidate_commit,
            "seed_manifest_sha256": manifest_hash,
            "runtime_storage": "local_sqlite_wal_shm",
            "database_sha256": database_hash,
            "formal_seed_consumption": 0,
        }
        digest = publish_json_once(args.result, payload)
        print(json.dumps({"terminal": "AS017_PUBLICATION_SMOKE_PASS", "sha256": digest}, sort_keys=True))
        return

    def on_case(row: dict) -> None:
        database = args.local_work / f"{row['regime']}-{row['seed']}.sqlite"
        destination = args.evidence_work / "case-databases" / database.name
        row["database_sha256"] = publish_file_once(database, destination)
        row["candidate_commit"] = args.candidate_commit
        row["seed_manifest_sha256"] = manifest_hash
        publish_json_once(args.evidence_work / "case-results" / f"{row['regime']}-{row['seed_index']:02d}-{row['seed']}.json", row)

    result = execute(manifest, args.local_work, on_case=on_case)
    result.update(candidate_commit=args.candidate_commit, seed_manifest_sha256=manifest_hash,
                  runtime_storage="local_sqlite_wal_shm", formal_seed_consumption=0,
                  retries=0, reseeds=0)
    digest = publish_json_once(args.result, result)
    print(json.dumps({"terminal": result["terminal"], "sha256": digest}, sort_keys=True))
    if not result["all_completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
