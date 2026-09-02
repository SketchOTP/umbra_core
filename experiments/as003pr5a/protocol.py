"""Pure storage protocol helpers for UMBRA-AS-003P-R5A.

This module never creates or loads an organism. The retained R5 root is opened
read-only and immutable only after its WAL is proven empty.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pickle
import sqlite3
from typing import Any


R5_EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r5-common-root-modal-shadow-r1"
)
RETAINED_WORK_ROOT = R5_EVIDENCE_ROOT / "r5-work"
RETAINED_DATABASE = RETAINED_WORK_ROOT / "shared-root.sqlite"
RETAINED_HABITAT = RETAINED_WORK_ROOT / "shared-habitat.pickle"
RETAINED_STORAGE_FILES = (
    RETAINED_DATABASE,
    Path(f"{RETAINED_DATABASE}-wal"),
    Path(f"{RETAINED_DATABASE}-shm"),
    RETAINED_HABITAT,
)


class ProtocolMetadataError(RuntimeError):
    """The persisted metadata cannot be interpreted under the Store contract."""


def canonical_json(value: Any, *, newline: bool = False) -> bytes:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return data + (b"\n" if newline else b"")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def storage_inventory() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for path in RETAINED_STORAGE_FILES:
        key = path.name
        if not path.exists():
            rows[key] = {"exists": False}
            continue
        stat = path.stat()
        rows[key] = {
            "exists": True,
            "size": stat.st_size,
            "sha256": sha256_file(path),
            "inode": stat.st_ino,
            "mode": oct(stat.st_mode & 0o7777),
            "uid": stat.st_uid,
            "gid": stat.st_gid,
            "mtime_ns": stat.st_mtime_ns,
        }
    return rows


def open_retained_database_read_only() -> sqlite3.Connection:
    wal = Path(f"{RETAINED_DATABASE}-wal")
    if wal.exists() and wal.stat().st_size != 0:
        raise ProtocolMetadataError("retained_root_nonempty_wal_requires_architect_review")
    connection = sqlite3.connect(
        f"file:{RETAINED_DATABASE.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def read_snapshot_metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    latest_row = connection.execute(
        "SELECT value FROM meta WHERE key='latest_snapshot'"
    ).fetchone()
    ledger_row = connection.execute(
        "SELECT value FROM meta WHERE key='ledger_tip'"
    ).fetchone()
    latest_id = str(latest_row[0]) if latest_row else None
    try:
        ledger_tip = json.loads(ledger_row[0]) if ledger_row else None
    except (TypeError, json.JSONDecodeError) as error:
        raise ProtocolMetadataError("malformed_ledger_tip_json") from error
    snapshot = None
    if latest_id is not None:
        row = connection.execute(
            "SELECT snapshot_id, agent_id, sequence, monotonic_time, state_json, state_hash "
            "FROM snapshots WHERE snapshot_id=?",
            (latest_id,),
        ).fetchone()
        if row is None:
            raise ProtocolMetadataError("latest_snapshot_reference_missing")
        columns = (
            "snapshot_id",
            "agent_id",
            "sequence",
            "monotonic_time",
            "state_json",
            "state_hash",
        )
        snapshot = dict(zip(columns, row, strict=True))
        if sha256_bytes(snapshot["state_json"].encode()) != snapshot["state_hash"]:
            raise ProtocolMetadataError("snapshot_hash_mismatch")
    return {
        "latest_snapshot_id": latest_id,
        "latest_snapshot": snapshot,
        "ledger_tip": ledger_tip,
    }


def _validate_ledger(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute("SELECT * FROM events ORDER BY sequence ASC").fetchall()
    previous = "genesis"
    expected_sequence = 1
    for row in rows:
        payload = json.loads(row["payload"])
        if row["sequence"] != expected_sequence:
            raise ProtocolMetadataError("event_sequence_gap")
        payload_hash = sha256_bytes(canonical_json(payload))
        if payload_hash != row["payload_hash"]:
            raise ProtocolMetadataError("event_payload_hash_mismatch")
        if row["previous_event_hash"] != previous:
            raise ProtocolMetadataError("event_previous_hash_mismatch")
        envelope = {
            "event_id": row["event_id"],
            "agent_id": row["agent_id"],
            "sequence": row["sequence"],
            "event_type": row["event_type"],
            "schema_version": row["schema_version"],
            "monotonic_time": row["monotonic_time"],
            "wall_time": row["wall_time"],
            "causal_parent_ids": json.loads(row["causal_parent_ids"]),
            "payload_hash": row["payload_hash"],
            "previous_event_hash": row["previous_event_hash"],
            "payload": payload,
        }
        event_hash = sha256_bytes(canonical_json(envelope))
        if event_hash != row["event_hash"]:
            raise ProtocolMetadataError("event_hash_mismatch")
        previous = event_hash
        expected_sequence += 1
    ledger_row = connection.execute(
        "SELECT value FROM meta WHERE key='ledger_tip'"
    ).fetchone()
    try:
        ledger_tip = json.loads(ledger_row[0]) if ledger_row else None
    except (TypeError, json.JSONDecodeError) as error:
        raise ProtocolMetadataError("malformed_ledger_tip_json") from error
    expected_tip = {"sequence": len(rows), "event_hash": previous}
    if ledger_tip != expected_tip:
        raise ProtocolMetadataError("ledger_tip_mismatch")
    return {
        "event_count": len(rows),
        "latest_event_hash": previous,
        "ledger_tip": ledger_tip,
        "valid": True,
    }


def retained_root_attestation() -> dict[str, Any]:
    before = storage_inventory()
    required = ("shared-root.sqlite", "shared-habitat.pickle")
    if not all(before[name].get("exists") for name in required):
        raise ProtocolMetadataError("retained_root_file_missing")
    with open_retained_database_read_only() as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        metadata = read_snapshot_metadata(connection)
        ledger = _validate_ledger(connection)
        counts = {
            row[0]: connection.execute(
                'SELECT COUNT(*) FROM "' + str(row[0]).replace('"', '""') + '"'
            ).fetchone()[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        }
    snapshot = metadata["latest_snapshot"]
    if snapshot is None:
        raise ProtocolMetadataError("latest_snapshot_missing")
    state = json.loads(snapshot["state_json"])
    from umbra_core.habitat.state import canonical_serialize

    habitat = pickle.loads(RETAINED_HABITAT.read_bytes())
    habitat_canonical = canonical_serialize(habitat)
    after = storage_inventory()
    immutable = {
        name: before[name].get("sha256") == after[name].get("sha256")
        for name in before
    }
    identity = state.get("identity") or {}
    adapter = state.get("embodiment_adapter") or {}
    self_model = state.get("self_model") or {}
    rng_sha256 = sha256_bytes(canonical_json(state.get("rng_state")))
    habitat_sha256 = sha256_bytes(canonical_json(habitat_canonical))
    checks = {
        "sqlite_integrity": integrity == "ok",
        "event_count": ledger["event_count"] == 5,
        "snapshot_sequence": snapshot["sequence"] == 5,
        "snapshot_state_hash": snapshot["state_hash"]
        == "25f048b5bd6a6be67ac6a1c3d4e984407ec19ec25c3f099232c5102af5467051",
        "rng_sha256": rng_sha256
        == "e2c69703d1fc3181bb62beaf9584410dfad02dba8141c3536198b0ce792aad68",
        "habitat_canonical_sha256": habitat_sha256
        == "a6b918441342908673c80e1771e30dc1cb51020e716efe0d481fd40e693ed24b",
        "storage_byte_hashes_unchanged": all(immutable.values()),
    }
    return {
        "schema": "AS003PR5A_RETAINED_ROOT_ATTESTATION_V1",
        "directive": "UMBRA-AS-003P-R5A",
        "result": "PASS" if all(checks.values()) else "FAIL",
        "retrieval": "READ_ONLY_SQLITE_IMMUTABLE_NO_ORGANISM_LOAD",
        "sqlite_integrity": integrity,
        "storage_pre": before,
        "storage_post": after,
        "storage_byte_hashes_unchanged": immutable,
        "all_storage_byte_hashes_unchanged": all(immutable.values()),
        "locked_fact_checks": checks,
        "table_row_counts": counts,
        "ledger": ledger,
        "snapshot": {
            "latest_snapshot_meta_semantics": "RAW_TEXT",
            "snapshot_id": metadata["latest_snapshot_id"],
            "agent_id": snapshot["agent_id"],
            "sequence": snapshot["sequence"],
            "monotonic_time": snapshot["monotonic_time"],
            "state_hash": snapshot["state_hash"],
        },
        "constitutional_identity": identity,
        "body": {
            "body_instance_id": adapter.get("body_instance_id"),
            "attachment_generation": adapter.get("attachment_generation"),
            "profile_id": adapter.get("body_profile_id"),
        },
        "self_model_sha256": sha256_bytes(canonical_json(self_model)),
        "self_model_binding": (self_model.get("active") or {}).get("body_binding_id"),
        "self_model_schema": (self_model.get("active") or {}).get("body_schema_id"),
        "physiology": state.get("physiology"),
        "world_model_sha256": sha256_bytes(canonical_json(state.get("world_model"))),
        "pending_action": state.get("pending_action"),
        "delayed_proposal": state.get("delayed_proposal"),
        "root_tick": state.get("tick"),
        "root_monotonic_time": state.get("monotonic_time"),
        "rng_sha256": rng_sha256,
        "habitat_canonical_sha256": habitat_sha256,
        "habitat_pickle_sha256": sha256_file(RETAINED_HABITAT),
    }
