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
            CREATE TABLE IF NOT EXISTS social_evidence_links (
              link_id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              hypothesis_id TEXT NOT NULL,
              context TEXT NOT NULL,
              signal TEXT NOT NULL,
              episode_id TEXT NOT NULL,
              pending_interaction_id TEXT NOT NULL,
              classification TEXT NOT NULL,
              relation TEXT NOT NULL,
              tick INTEGER NOT NULL,
              UNIQUE(hypothesis_id, context, signal, episode_id, relation)
            );
            CREATE TABLE IF NOT EXISTS social_hypothesis_provenance_links (
              link_id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              operation TEXT NOT NULL,
              result_hypothesis_id TEXT NOT NULL,
              source_hypothesis_id TEXT NOT NULL,
              tick INTEGER NOT NULL,
              UNIQUE(operation, result_hypothesis_id, source_hypothesis_id)
            );
            CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
            """
        )

    def close(self) -> None:
        try:
            self.conn.execute("DROP TABLE IF EXISTS runtime_warm")
        except sqlite3.Error:
            pass
        self.conn.close()

    def warm_runtime_residency(self, bytes_size: int = 6 * 1024 * 1024) -> None:
        """Pre-reside SQLite/page-cache capacity before RUNTIME_READY.

        Sized to the measured early-window residency (~5–6 MiB; not an RSS wait loop).
        """
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS runtime_warm (id INTEGER PRIMARY KEY, payload BLOB NOT NULL)"
        )
        self.conn.execute("DELETE FROM runtime_warm")
        self.conn.execute(
            "INSERT INTO runtime_warm(id, payload) VALUES (1, ?)",
            (bytes(bytes_size),),
        )
        # Touch the blob so pages fault in.
        row = self.conn.execute("SELECT length(payload) FROM runtime_warm WHERE id=1").fetchone()
        if int(row[0]) != bytes_size:
            raise PersistenceError("runtime_warm_size_mismatch")


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

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
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

    def iter_events(self, from_sequence: int = 1) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE sequence >= ? ORDER BY sequence ASC",
            (from_sequence,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def last_event_of_types(self, event_types: tuple[str, ...]) -> dict[str, Any] | None:
        """Indexed lookup for the newest event among `event_types` — avoids
        loading the full ledger to check for a rare authoritative event
        (e.g. D-008 body attachment) on every organism load."""
        placeholders = ",".join("?" for _ in event_types)
        row = self.conn.execute(
            f"SELECT * FROM events WHERE event_type IN ({placeholders}) "
            "ORDER BY sequence DESC LIMIT 1",
            tuple(event_types),
        ).fetchone()
        return self._row_to_event(row) if row is not None else None

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

    # --- D-006 social evidence links + atomic outcome commit -------------

    def insert_social_evidence_link(
        self,
        *,
        agent_id: str,
        hypothesis_id: str,
        context: str,
        signal: str,
        episode_id: str,
        pending_interaction_id: str,
        classification: str,
        relation: str,
        tick: int,
    ) -> None:
        """Normalized provenance row tying an immutable episode to a contingency cell.

        UNIQUE(hypothesis_id, context, signal, episode_id, relation) is the durable
        guard against double-counting the same episode as evidence twice.
        """
        self.conn.execute(
            """
            INSERT INTO social_evidence_links(
              link_id, agent_id, hypothesis_id, context, signal, episode_id,
              pending_interaction_id, classification, relation, tick
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id(),
                agent_id,
                hypothesis_id,
                context,
                signal,
                episode_id,
                pending_interaction_id,
                classification,
                relation,
                int(tick),
            ),
        )

    def social_evidence_links_for(self, hypothesis_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM social_evidence_links WHERE hypothesis_id=? ORDER BY rowid ASC",
            (hypothesis_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def insert_social_hypothesis_provenance_link(
        self,
        *,
        agent_id: str,
        operation: str,
        result_hypothesis_id: str,
        source_hypothesis_id: str,
        tick: int,
    ) -> None:
        """Normalized merge/split lineage — full provenance recoverable beyond bounded active sets."""
        self.conn.execute(
            """
            INSERT INTO social_hypothesis_provenance_links(
              link_id, agent_id, operation, result_hypothesis_id, source_hypothesis_id, tick
            ) VALUES (?,?,?,?,?,?)
            """,
            (
                new_id(),
                agent_id,
                operation,
                result_hypothesis_id,
                source_hypothesis_id,
                int(tick),
            ),
        )

    def social_hypothesis_provenance_links_for(self, hypothesis_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM social_hypothesis_provenance_links
            WHERE result_hypothesis_id=? ORDER BY rowid ASC
            """,
            (hypothesis_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def atomic_social_outcome(
        self,
        stages: list[Any],
        *,
        on_commit: Any = None,
        crash_after_stage: int | None = None,
    ) -> None:
        """Run ordered durable stage writers in ONE SQLite transaction.

        `stages` is an ordered list of zero-arg callables; each performs the durable
        writes for one outcome stage (finalize episode event, episode event, evidence
        links, reliability event, pending/contingency authority events). Everything is
        wrapped in a single BEGIN IMMEDIATE .. COMMIT, so a crash before COMMIT rolls
        back every prior stage — no episode without its aggregate, no contingency
        update without its episode, no reliability pointing at nonexistent evidence.

        `crash_after_stage` (1-based) raises after that stage's writes but before COMMIT
        to exercise crash injection; the transaction rolls back and PersistenceError
        propagates. `on_commit` (in-memory model mutation) runs only after COMMIT
        succeeds, so a rollback never leaves partial in-memory state either.
        """
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            for i, stage in enumerate(stages, start=1):
                stage()
                if crash_after_stage is not None and i == crash_after_stage:
                    raise PersistenceError(f"crash_injection_after_stage_{crash_after_stage}")
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        if on_commit is not None:
            on_commit()

    def corrupt_event_payload(self, sequence: int, new_payload: dict[str, Any]) -> None:
        """Test helper — mutates payload without updating hashes."""
        payload_s = json.dumps(new_payload, sort_keys=True, separators=(",", ":"))
        self.conn.execute(
            "UPDATE events SET payload=? WHERE sequence=?",
            (payload_s, sequence),
        )
