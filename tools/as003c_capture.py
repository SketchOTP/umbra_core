#!/usr/bin/env python3
"""Durably capture one frozen AS-003C post-freeze command.

The helper is evidence infrastructure only.  It writes command metadata, raw
stdout/stderr, optional JUnit-derived individual test records, and a sibling
SHA-256 inventory with fsync plus atomic rename before returning the captured
command's exit code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any
import uuid
import xml.etree.ElementTree as ET


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        written = 0
        while written < len(payload):
            count = os.write(fd, payload[written:])
            if count <= 0:
                raise OSError("short_write")
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def durable_json(path: Path, value: Any) -> None:
    durable_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def seal_existing(path: Path) -> None:
    """Force an externally-produced artifact and its directory to stable storage."""

    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def git_text(workdir: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(workdir), *args], text=True).strip()
    except subprocess.CalledProcessError:
        return None


def junit_records(path: Path) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot()
    records: list[dict[str, Any]] = []
    for case in root.iter("testcase"):
        node_id = f"{case.get('file') or case.get('classname') or '<unknown>'}::{case.get('name') or '<unknown>'}"
        failures = []
        status = "passed"
        for child in case:
            if child.tag in {"failure", "error"}:
                status = "failed"
                failures.append({
                    "kind": child.tag,
                    "message": child.get("message"),
                    "assertion": child.text or "",
                })
            elif child.tag == "skipped" and status == "passed":
                status = "skipped"
                failures.append({"kind": "skipped", "message": child.get("message"), "assertion": child.text or ""})
        records.append({"node_id": node_id, "status": status, "duration_seconds": float(case.get("time") or 0.0), "details": failures})
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command or args.command[0] != "--":
        parser.error("command must follow --")
    command = args.command[1:]
    if not command:
        parser.error("missing command")
    if "/" in args.label or args.label in {".", ".."}:
        parser.error("unsafe label")
    evidence = args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=True)
    prefix = evidence / args.label
    stdout_path = prefix.with_suffix(".stdout.log")
    stderr_path = prefix.with_suffix(".stderr.log")
    record_path = prefix.with_suffix(".command.json")
    tests_path = prefix.with_suffix(".tests.json")
    inventory_path = prefix.with_suffix(".sha256.json")
    for path in (stdout_path, stderr_path, record_path, tests_path, inventory_path):
        if path.exists():
            raise FileExistsError(path)

    started = utc_now()
    monotonic_started = time.monotonic()
    completed = subprocess.run(command, cwd=args.workdir, text=False, capture_output=True, check=False)
    ended = utc_now()
    durable_bytes(stdout_path, completed.stdout)
    durable_bytes(stderr_path, completed.stderr)
    test_records: list[dict[str, Any]] | None = None
    junit_note: str | None = None
    if args.junit is not None:
        if args.junit.exists():
            try:
                seal_existing(args.junit)
                test_records = junit_records(args.junit)
                durable_json(tests_path, {"junit_path": str(args.junit), "records": test_records})
            except (ET.ParseError, OSError, ValueError) as exc:
                junit_note = f"junit_parse_failed:{type(exc).__name__}:{exc}"
        else:
            junit_note = "junit_missing"
    additional_artifacts: list[Path] = []
    for artifact in args.artifact:
        if not artifact.exists() or not artifact.is_file():
            raise FileNotFoundError(f"artifact_missing:{artifact}")
        seal_existing(artifact)
        additional_artifacts.append(artifact)
    record = {
        "schema": "AS003C_POSTFREEZE_COMMAND_EVIDENCE_V1",
        "label": args.label,
        "command": command,
        "working_directory": str(args.workdir),
        "started_at": started,
        "ended_at": ended,
        "elapsed_seconds": round(time.monotonic() - monotonic_started, 6),
        "exit_code": completed.returncode,
        "git_commit": git_text(args.workdir, "rev-parse", "HEAD"),
        "git_status_porcelain": git_text(args.workdir, "status", "--porcelain"),
        "environment": {
            name: os.environ.get(name)
            for name in ("LANG", "LC_ALL", "PYTHONPATH", "VIRTUAL_ENV")
        },
        "junit_path": str(args.junit) if args.junit else None,
        "junit_note": junit_note,
        "individual_test_record_count": len(test_records) if test_records is not None else None,
        "failing_node_ids": [record["node_id"] for record in test_records or [] if record["status"] == "failed"],
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "additional_artifacts": [str(path) for path in additional_artifacts],
    }
    durable_json(record_path, record)
    inventory_paths = [stdout_path, stderr_path, record_path]
    if args.junit is not None and args.junit.exists():
        inventory_paths.append(args.junit)
    if tests_path.exists():
        inventory_paths.append(tests_path)
    inventory_paths.extend(additional_artifacts)
    durable_json(inventory_path, {
        "schema": "AS003C_COMMAND_SHA256_INVENTORY_V1",
        "label": args.label,
        "files": {str(path): sha256(path) for path in inventory_paths},
    })
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
