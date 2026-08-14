"""Non-mutating SQLite validation for terminal formal evidence databases."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from umbra_core.identity import identity_from_dict
from umbra_core.util import canon_json, sha256_hex


def _event(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "event_id": row["event_id"],
        "agent_id": row["agent_id"],
        "sequence": row["sequence"],
        "event_type": row["event_type"],
        "schema_version": row["schema_version"],
        "monotonic_time": row["monotonic_time"],
        "wall_time": row["wall_time"],
        "causal_parent_ids": json.loads(row["causal_parent_ids"]),
        "payload": json.loads(row["payload"]),
        "payload_hash": row["payload_hash"],
        "previous_event_hash": row["previous_event_hash"],
        "event_hash": row["event_hash"],
    }


def _validate_events(conn: sqlite3.Connection) -> tuple[int, str, str]:
    rows = conn.execute("SELECT * FROM events ORDER BY sequence ASC").fetchall()
    previous = "genesis"
    for expected_sequence, raw in enumerate(rows, 1):
        event = _event(raw)
        if event["sequence"] != expected_sequence:
            raise ValueError(f"sequence_gap:{expected_sequence}:{event['sequence']}")
        payload_s = json.dumps(event["payload"], sort_keys=True, separators=(",", ":"), default=str)
        if sha256_hex(payload_s) != event["payload_hash"]:
            raise ValueError(f"payload_hash_mismatch:{expected_sequence}")
        if event["previous_event_hash"] != previous:
            raise ValueError(f"chain_break:{expected_sequence}")
        envelope = {
            key: event[key]
            for key in (
                "event_id", "agent_id", "sequence", "event_type", "schema_version",
                "monotonic_time", "wall_time", "causal_parent_ids", "payload_hash",
                "previous_event_hash",
            )
        }
        expected_hash = sha256_hex(canon_json({**envelope, "payload": event["payload"]}))
        if expected_hash != event["event_hash"]:
            raise ValueError(f"event_hash_mismatch:{expected_sequence}")
        previous = event["event_hash"]
    tip_row = conn.execute("SELECT value FROM meta WHERE key='ledger_tip'").fetchone()
    if tip_row is not None:
        tip = json.loads(tip_row[0])
        if tip != {"sequence": len(rows), "event_hash": previous}:
            raise ValueError("ledger_tip_mismatch")
    return len(rows), previous, "ok"


def validate_read_only(database: str | Path) -> dict[str, Any]:
    """Validate identity, ledger, snapshots, and terminal state with no writes."""
    path = Path(database).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        required = {"identity", "events", "snapshots", "meta"}
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = required - tables
        if missing:
            raise ValueError("missing_tables:" + ",".join(sorted(missing)))
        identity_row = conn.execute(
            "SELECT record_json, commitment FROM identity LIMIT 1"
        ).fetchone()
        if identity_row is None:
            raise ValueError("identity_missing")
        identity_data = json.loads(identity_row["record_json"])
        identity = identity_from_dict(identity_data)
        if identity.identity_commitment != identity_row["commitment"]:
            raise ValueError("identity_row_commitment_mismatch")
        event_count, chain_tip_hash, chain_status = _validate_events(conn)
        snapshot_count = int(conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])
        for row in conn.execute("SELECT state_json, state_hash FROM snapshots"):
            if sha256_hex(row["state_json"]) != row["state_hash"]:
                raise ValueError("snapshot_hash_mismatch")
            json.loads(row["state_json"])
        tip_row = conn.execute("SELECT value FROM meta WHERE key='ledger_tip'").fetchone()
        ledger_tip = json.loads(tip_row[0]) if tip_row else None
        runtime_ready_count = int(conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='runtime_ready'"
        ).fetchone()[0])
        return {
            "database": str(path),
            "sqlite_integrity": conn.execute("PRAGMA integrity_check").fetchone()[0],
            "identity": identity.agent_id,
            "event_count": event_count,
            "max_event_sequence": event_count,
            "chain_tip_hash": chain_tip_hash,
            "ledger_tip": ledger_tip,
            "snapshot_count": snapshot_count,
            "runtime_ready_count": runtime_ready_count,
            "chain_status": chain_status,
            "mutating_api_used": False,
        }
    finally:
        conn.close()
