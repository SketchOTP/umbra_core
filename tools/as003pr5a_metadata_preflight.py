#!/usr/bin/env python3
"""Synthetic-only snapshot metadata protocol qualification for AS-003P-R5A."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as003pr5a.protocol import ProtocolMetadataError, read_snapshot_metadata


def create_database(
    path: Path,
    *,
    latest: str | None = "snapshot-1",
    referenced: str | None = "snapshot-1",
    state: dict | None = None,
    state_hash: str | None = None,
    ledger_tip: str = '{"event_hash":"genesis","sequence":0}',
) -> None:
    payload = json.dumps(state or {"tick": 0}, sort_keys=True, separators=(",", ":"))
    digest = state_hash or hashlib.sha256(payload.encode()).hexdigest()
    with sqlite3.connect(path) as connection:
        connection.executescript(
            "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "CREATE TABLE snapshots(snapshot_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, "
            "sequence INTEGER NOT NULL, monotonic_time REAL NOT NULL, state_json TEXT NOT NULL, "
            "state_hash TEXT NOT NULL);"
        )
        if latest is not None:
            connection.execute("INSERT INTO meta VALUES ('latest_snapshot', ?)", (latest,))
        connection.execute("INSERT INTO meta VALUES ('ledger_tip', ?)", (ledger_tip,))
        if referenced is not None:
            connection.execute(
                "INSERT INTO snapshots VALUES (?, 'agent', 5, 0.0, ?, ?)",
                (referenced, payload, digest),
            )


rows: list[dict] = []


def run(case: str, setup: dict, expected: str) -> None:
    with tempfile.TemporaryDirectory(prefix="as003pr5a-metadata-") as temporary:
        path = Path(temporary) / "synthetic.sqlite"
        create_database(path, **setup)
        try:
            with sqlite3.connect(path) as connection:
                value = read_snapshot_metadata(connection)
            observed = "PASS"
            detail = {
                "latest_snapshot_id": value["latest_snapshot_id"],
                "sequence": None if value["latest_snapshot"] is None else value["latest_snapshot"]["sequence"],
                "state_hash": None if value["latest_snapshot"] is None else value["latest_snapshot"]["state_hash"],
                "ledger_tip": value["ledger_tip"],
            }
        except ProtocolMetadataError as error:
            observed = str(error)
            detail = {"error": str(error)}
        rows.append(
            {
                "case": case,
                "expected": expected,
                "observed": observed,
                "passed": observed == expected,
                "detail": detail,
            }
        )


run("RAW_TEXT_SNAPSHOT_ID", {}, "PASS")
run("MISSING_LATEST_SNAPSHOT", {"latest": None, "referenced": None}, "PASS")
run("MISSING_REFERENCED_SNAPSHOT", {"latest": "missing", "referenced": None}, "latest_snapshot_reference_missing")
run("UUID_LIKE_RAW_TEXT", {"latest": "a580866c-56e0-4fc0-94a5-8bfe70256e22", "referenced": "a580866c-56e0-4fc0-94a5-8bfe70256e22"}, "PASS")
run("LEDGER_TIP_JSON", {"ledger_tip": '{"event_hash":"abc","sequence":5}'}, "PASS")
run("SNAPSHOT_SEQUENCE_AND_HASH", {"state": {"tick": 0, "value": 7}}, "PASS")
run("CORRUPTED_SNAPSHOT_HASH", {"state_hash": "0" * 64}, "snapshot_hash_mismatch")
run("MALFORMED_LEDGER_TIP", {"ledger_tip": "not-json"}, "malformed_ledger_tip_json")

result = {
    "schema": "AS003PR5A_METADATA_PROTOCOL_PREFLIGHT_V1",
    "directive": "UMBRA-AS-003P-R5A",
    "result": "PASS" if all(row["passed"] for row in rows) else "FAIL",
    "case_count": len(rows),
    "organism_creations": 0,
    "organism_loads": 0,
    "organism_ticks": 0,
    "rows": rows,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
