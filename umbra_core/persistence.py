"""SQLite WAL persistence — event ledger authority + materialised snapshots."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from umbra_core.identity import (
    ConstitutionalIdentity,
    IdentityError,
    identity_from_dict,
)
from umbra_core.util import SCHEMA_VERSION, canon_json, new_id, sha256_hex


class PersistenceError(Exception):
    """Fail-closed persistence / ledger failure."""


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA cache_size=-4000")  # ~4 MiB page cache
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA mmap_size=0")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS identity (
              agent_id TEXT PRIMARY KEY,
              record_json TEXT NOT NULL,
              commitment TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
              sequence INTEGER PRIMARY KEY,
              event_id TEXT UNIQUE NOT NULL,
              agent_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              schema_version TEXT NOT NULL,
              monotonic_time REAL NOT NULL,
              wall_time REAL NOT NULL,
              causal_parent_ids TEXT NOT NULL,
              payload TEXT NOT NULL,
              payload_hash TEXT NOT NULL,
              previous_event_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
              snapshot_id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              monotonic_time REAL NOT NULL,
              state_json TEXT NOT NULL,
              state_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )

    def close(self) -> None:
        self.conn.close()

    def save_identity(self, ident: ConstitutionalIdentity) -> None:
        payload = json.dumps(ident.as_dict(), sort_keys=True)
        self.conn.execute(
            "INSERT OR REPLACE INTO identity(agent_id, record_json, commitment) VALUES (?,?,?)",
            (ident.agent_id, payload, ident.identity_commitment),
        )

    def load_identity(self) -> ConstitutionalIdentity:
        row = self.conn.execute("SELECT record_json, commitment FROM identity LIMIT 1").fetchone()
        if row is None:
            raise IdentityError("no_identity")
        data = json.loads(row["record_json"])
        if data.get("identity_commitment") != row["commitment"]:
            raise IdentityError("identity_row_commitment_mismatch")
        return identity_from_dict(data)

    def last_sequence(self) -> int:
        row = self.conn.execute("SELECT MAX(sequence) AS m FROM events").fetchone()
        return int(row["m"] or 0)

    def last_event_hash(self) -> str:
        row = self.conn.execute(
            "SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        return str(row["event_hash"]) if row else "genesis"

    def append_event(
        self,
        *,
        agent_id: str,
        event_type: str,
        monotonic_time: float,
        wall_time: float,
        payload: dict[str, Any],
        causal_parent_ids: list[str] | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        seq = self.last_sequence() + 1
        eid = event_id or new_id()
        parents = causal_parent_ids or []
        payload_s = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        payload_hash = sha256_hex(payload_s)
        prev = self.last_event_hash()
        envelope = {
            "event_id": eid,
            "agent_id": agent_id,
            "sequence": seq,
            "event_type": event_type,
            "schema_version": SCHEMA_VERSION,
            "monotonic_time": monotonic_time,
            "wall_time": wall_time,
            "causal_parent_ids": parents,
            "payload_hash": payload_hash,
            "previous_event_hash": prev,
        }
        event_hash = sha256_hex(canon_json({**envelope, "payload": payload}))
        self.conn.execute(
            """
            INSERT INTO events(
              sequence, event_id, agent_id, event_type, schema_version,
              monotonic_time, wall_time, causal_parent_ids, payload,
              payload_hash, previous_event_hash, event_hash
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                seq,
                eid,
                agent_id,
                event_type,
                SCHEMA_VERSION,
                monotonic_time,
                wall_time,
                json.dumps(parents),
                payload_s,
                payload_hash,
                prev,
                event_hash,
            ),
        )
        return {**envelope, "payload": payload, "event_hash": event_hash}

    def save_snapshot(self, agent_id: str, sequence: int, monotonic_time: float, state: dict[str, Any]) -> str:
        sid = new_id()
        state_s = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
        state_hash = sha256_hex(state_s)
        self.conn.execute(
            """
            INSERT INTO snapshots(snapshot_id, agent_id, sequence, monotonic_time, state_json, state_hash)
            VALUES (?,?,?,?,?,?)
            """,
            (sid, agent_id, sequence, monotonic_time, state_s, state_hash),
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('latest_snapshot', ?)",
            (sid,),
        )
        return sid

    def prune_snapshots(self, keep: int = 2) -> int:
        """Retain the newest `keep` snapshots; durable history is the event ledger."""
        if keep < 1:
            raise ValueError("keep_must_be_positive")
        rows = self.conn.execute(
            "SELECT snapshot_id FROM snapshots ORDER BY sequence DESC, rowid DESC"
        ).fetchall()
        if len(rows) <= keep:
            return 0
        keep_ids = [r["snapshot_id"] for r in rows[:keep]]
        drop = [r["snapshot_id"] for r in rows[keep:]]
        self.conn.executemany(
            "DELETE FROM snapshots WHERE snapshot_id=?",
            [(sid,) for sid in drop],
        )
        # Keep meta pointer on the newest retained snapshot.
        self.conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('latest_snapshot', ?)",
            (keep_ids[0],),
        )
        return len(drop)

    def load_snapshot(self, snapshot_id: str | None = None) -> dict[str, Any]:
        if snapshot_id is None:
            row = self.conn.execute("SELECT value FROM meta WHERE key='latest_snapshot'").fetchone()
            if row is None:
                raise PersistenceError("no_snapshot")
            snapshot_id = row["value"]
        row = self.conn.execute(
            "SELECT * FROM snapshots WHERE snapshot_id=?", (snapshot_id,)
        ).fetchone()
        if row is None:
            raise PersistenceError("snapshot_missing")
        state = json.loads(row["state_json"])
        if sha256_hex(row["state_json"]) != row["state_hash"]:
            raise PersistenceError("snapshot_hash_mismatch")
        return {
            "snapshot_id": row["snapshot_id"],
            "agent_id": row["agent_id"],
            "sequence": row["sequence"],
            "monotonic_time": row["monotonic_time"],
            "state": state,
            "state_hash": row["state_hash"],
        }

    def iter_events(self, from_sequence: int = 1) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE sequence >= ? ORDER BY sequence ASC",
            (from_sequence,),
        ).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "event_id": r["event_id"],
                    "agent_id": r["agent_id"],
                    "sequence": r["sequence"],
                    "event_type": r["event_type"],
                    "schema_version": r["schema_version"],
                    "monotonic_time": r["monotonic_time"],
                    "wall_time": r["wall_time"],
                    "causal_parent_ids": json.loads(r["causal_parent_ids"]),
                    "payload": json.loads(r["payload"]),
                    "payload_hash": r["payload_hash"],
                    "previous_event_hash": r["previous_event_hash"],
                    "event_hash": r["event_hash"],
                }
            )
        return out

    def validate_chain(self) -> None:
        events = self.iter_events(1)
        prev_hash = "genesis"
        expect_seq = 1
        for ev in events:
            if ev["sequence"] != expect_seq:
                raise PersistenceError(f"sequence_gap:expected_{expect_seq}_got_{ev['sequence']}")
            payload_s = json.dumps(ev["payload"], sort_keys=True, separators=(",", ":"), default=str)
            if sha256_hex(payload_s) != ev["payload_hash"]:
                raise PersistenceError(f"payload_hash_mismatch:seq_{ev['sequence']}")
            if ev["previous_event_hash"] != prev_hash:
                raise PersistenceError(f"chain_break:seq_{ev['sequence']}")
            envelope = {
                "event_id": ev["event_id"],
                "agent_id": ev["agent_id"],
                "sequence": ev["sequence"],
                "event_type": ev["event_type"],
                "schema_version": ev["schema_version"],
                "monotonic_time": ev["monotonic_time"],
                "wall_time": ev["wall_time"],
                "causal_parent_ids": ev["causal_parent_ids"],
                "payload_hash": ev["payload_hash"],
                "previous_event_hash": ev["previous_event_hash"],
            }
            expected = sha256_hex(canon_json({**envelope, "payload": ev["payload"]}))
            if expected != ev["event_hash"]:
                raise PersistenceError(f"event_hash_mismatch:seq_{ev['sequence']}")
            prev_hash = ev["event_hash"]
            expect_seq += 1

    def corrupt_event_payload(self, sequence: int, new_payload: dict[str, Any]) -> None:
        """Test helper — mutates payload without updating hashes."""
        payload_s = json.dumps(new_payload, sort_keys=True, separators=(",", ":"))
        self.conn.execute(
            "UPDATE events SET payload=? WHERE sequence=?",
            (payload_s, sequence),
        )
