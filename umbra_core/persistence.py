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
              state_hash TEXT NOT NULL,
              protected INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS ledger_checkpoints (
              checkpoint_id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              checkpoint_epoch INTEGER NOT NULL UNIQUE,
              compacted_sequence_start INTEGER NOT NULL,
              compacted_sequence_end INTEGER NOT NULL,
              compacted_event_count INTEGER NOT NULL,
              previous_checkpoint_hash TEXT NOT NULL,
              terminal_event_hash TEXT NOT NULL,
              snapshot_id TEXT NOT NULL,
              snapshot_state_hash TEXT NOT NULL,
              habitat_binding_json TEXT NOT NULL,
              habitat_checkpoint_json TEXT,
              body_attachment_json TEXT NOT NULL,
              schema_version TEXT NOT NULL,
              creation_tick INTEGER NOT NULL,
              creation_wall_time REAL NOT NULL,
              checkpoint_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkpoint_provenance (
              checkpoint_id TEXT NOT NULL,
              provenance_key TEXT NOT NULL,
              event_json TEXT NOT NULL,
              event_hash TEXT NOT NULL,
              PRIMARY KEY(checkpoint_id, provenance_key)
            );
            CREATE INDEX IF NOT EXISTS idx_checkpoint_provenance_checkpoint
              ON checkpoint_provenance(checkpoint_id);
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
            CREATE TABLE IF NOT EXISTS habitat_execution_journal (
              execution_id TEXT PRIMARY KEY,
              request_id TEXT UNIQUE NOT NULL,
              status TEXT NOT NULL,
              canonical_payload_hash TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              transaction_id TEXT NOT NULL,
              prepared_tick INTEGER NOT NULL,
              outcome_id TEXT,
              failure_code TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_habitat_execution_journal_request
              ON habitat_execution_journal(request_id);
            """
        )
        # SQLite does not add a column to an existing table created by an older
        # qualified schema. This is a persistence schema migration, not a
        # reinterpretation of historical snapshots.
        snapshot_columns = {
            str(row["name"])
            for row in self.conn.execute("PRAGMA table_info(snapshots)").fetchall()
        }
        if "protected" not in snapshot_columns:
            self.conn.execute(
                "ALTER TABLE snapshots ADD COLUMN protected INTEGER NOT NULL DEFAULT 0"
            )
        self.event_storage_budget: int | None = None

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
        if row["m"] is not None:
            return int(row["m"])
        checkpoint = self.latest_checkpoint()
        return int(checkpoint["compacted_sequence_end"]) if checkpoint else 0

    def last_event_hash(self) -> str:
        row = self.conn.execute(
            "SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is not None:
            return str(row["event_hash"])
        checkpoint = self.latest_checkpoint()
        return str(checkpoint["terminal_event_hash"]) if checkpoint else "genesis"

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
        self._check_event_storage_budget()
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
        own_transaction = not self.conn.in_transaction
        if own_transaction:
            self.conn.execute("BEGIN IMMEDIATE")
        try:
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
            self.conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                ("ledger_tip", json.dumps({"sequence": seq, "event_hash": event_hash}, sort_keys=True)),
            )
            if own_transaction:
                self.conn.execute("COMMIT")
        except BaseException:
            if own_transaction and self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise
        return {**envelope, "payload": payload, "event_hash": event_hash}

    def save_snapshot(
        self,
        agent_id: str,
        sequence: int,
        monotonic_time: float,
        state: dict[str, Any],
        *,
        protected: bool = False,
    ) -> str:
        sid = new_id()
        state_s = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
        state_hash = sha256_hex(state_s)
        self.conn.execute(
            """
            INSERT INTO snapshots(snapshot_id, agent_id, sequence, monotonic_time, state_json, state_hash, protected)
            VALUES (?,?,?,?,?,?,?)
            """,
            (sid, agent_id, sequence, monotonic_time, state_s, state_hash, int(protected)),
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('latest_snapshot', ?)",
            (sid,),
        )
        return sid

    def prune_snapshots(self, keep: int = 2) -> int:
        """Retain bounded ordinary snapshots and never drop checkpoint anchors."""
        if keep < 1:
            raise ValueError("keep_must_be_positive")
        rows = self.conn.execute(
            "SELECT snapshot_id, protected FROM snapshots ORDER BY sequence DESC, rowid DESC"
        ).fetchall()
        ordinary = [r for r in rows if not bool(r["protected"])]
        if len(ordinary) <= keep:
            return 0
        keep_ids = [r["snapshot_id"] for r in ordinary[:keep]]
        drop = [r["snapshot_id"] for r in ordinary[keep:]]
        self.conn.executemany(
            "DELETE FROM snapshots WHERE snapshot_id=?",
            [(sid,) for sid in drop],
        )
        # The newest snapshot overall (including a protected checkpoint) remains
        # the normal restart point; deleting ordinary snapshots must not move it.
        newest = rows[0]["snapshot_id"]
        self.conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('latest_snapshot', ?)",
            (newest,),
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
    def _checkpoint_envelope(
        *,
        checkpoint_id: str,
        agent_id: str,
        checkpoint_epoch: int,
        compacted_sequence_start: int,
        compacted_sequence_end: int,
        compacted_event_count: int,
        previous_checkpoint_hash: str,
        terminal_event_hash: str,
        snapshot_id: str,
        snapshot_state_hash: str,
        habitat_binding: dict[str, Any],
        habitat_checkpoint: dict[str, Any] | None,
        body_attachment: dict[str, Any],
        schema_version: str,
        creation_tick: int,
        creation_wall_time: float,
    ) -> dict[str, Any]:
        return {
            "checkpoint_id": checkpoint_id,
            "agent_id": agent_id,
            "checkpoint_epoch": checkpoint_epoch,
            "compacted_sequence_start": compacted_sequence_start,
            "compacted_sequence_end": compacted_sequence_end,
            "compacted_event_count": compacted_event_count,
            "previous_checkpoint_hash": previous_checkpoint_hash,
            "terminal_event_hash": terminal_event_hash,
            "snapshot_id": snapshot_id,
            "snapshot_state_hash": snapshot_state_hash,
            "habitat_binding": habitat_binding,
            "habitat_checkpoint": habitat_checkpoint,
            "body_attachment": body_attachment,
            "schema_version": schema_version,
            "creation_tick": creation_tick,
            "creation_wall_time": creation_wall_time,
        }

    @staticmethod
    def _checkpoint_from_row(row: sqlite3.Row) -> dict[str, Any]:
        habitat_checkpoint = row["habitat_checkpoint_json"]
        return {
            "checkpoint_id": str(row["checkpoint_id"]),
            "agent_id": str(row["agent_id"]),
            "checkpoint_epoch": int(row["checkpoint_epoch"]),
            "compacted_sequence_start": int(row["compacted_sequence_start"]),
            "compacted_sequence_end": int(row["compacted_sequence_end"]),
            "compacted_event_count": int(row["compacted_event_count"]),
            "previous_checkpoint_hash": str(row["previous_checkpoint_hash"]),
            "terminal_event_hash": str(row["terminal_event_hash"]),
            "snapshot_id": str(row["snapshot_id"]),
            "snapshot_state_hash": str(row["snapshot_state_hash"]),
            "habitat_binding": json.loads(row["habitat_binding_json"]),
            "habitat_checkpoint": json.loads(habitat_checkpoint) if habitat_checkpoint else None,
            "body_attachment": json.loads(row["body_attachment_json"]),
            "schema_version": str(row["schema_version"]),
            "creation_tick": int(row["creation_tick"]),
            "creation_wall_time": float(row["creation_wall_time"]),
            "checkpoint_hash": str(row["checkpoint_hash"]),
        }

    def latest_checkpoint(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM ledger_checkpoints ORDER BY checkpoint_epoch DESC LIMIT 1"
        ).fetchone()
        return self._checkpoint_from_row(row) if row is not None else None

    def has_compacted_prefix(self) -> bool:
        return self.latest_checkpoint() is not None

    def _validate_latest_checkpoint(self) -> dict[str, Any] | None:
        checkpoint = self.latest_checkpoint()
        if checkpoint is None:
            return None
        envelope = self._checkpoint_envelope(**{
            key: checkpoint[key]
            for key in (
                "checkpoint_id", "agent_id", "checkpoint_epoch",
                "compacted_sequence_start", "compacted_sequence_end",
                "compacted_event_count", "previous_checkpoint_hash",
                "terminal_event_hash", "snapshot_id", "snapshot_state_hash",
                "habitat_binding", "habitat_checkpoint", "body_attachment",
                "schema_version", "creation_tick", "creation_wall_time",
            )
        })
        if sha256_hex(canon_json(envelope)) != checkpoint["checkpoint_hash"]:
            raise PersistenceError("checkpoint_hash_mismatch")
        snapshot = self.load_snapshot(checkpoint["snapshot_id"])
        if snapshot["state_hash"] != checkpoint["snapshot_state_hash"]:
            raise PersistenceError("checkpoint_snapshot_hash_mismatch")
        if snapshot["sequence"] < checkpoint["compacted_sequence_end"]:
            raise PersistenceError("checkpoint_snapshot_precedes_prefix")
        return checkpoint

    def checkpoint_provenance(self, checkpoint_id: str | None = None) -> list[dict[str, Any]]:
        checkpoint = self.latest_checkpoint() if checkpoint_id is None else None
        selected = checkpoint_id or (checkpoint["checkpoint_id"] if checkpoint else None)
        if selected is None:
            return []
        rows = self.conn.execute(
            "SELECT provenance_key, event_json, event_hash FROM checkpoint_provenance "
            "WHERE checkpoint_id=? ORDER BY provenance_key",
            (selected,),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            event = json.loads(row["event_json"])
            if str(event.get("event_hash")) != str(row["event_hash"]):
                raise PersistenceError("checkpoint_provenance_hash_mismatch")
            result.append({"provenance_key": str(row["provenance_key"]), "event": event})
        return result

    def compact_authoritative_prefix(
        self,
        *,
        agent_id: str,
        snapshot_id: str,
        creation_tick: int,
        creation_wall_time: float,
        habitat_binding: dict[str, Any] | None,
        habitat_checkpoint: dict[str, Any] | None,
        body_attachment: dict[str, Any] | None,
        protected_event_types: tuple[str, ...] = (),
        keep_checkpoints: int = 4,
        crash_after: str | None = None,
    ) -> dict[str, Any] | None:
        """Atomically replace the current hot prefix with a verifiable anchor.

        Sequences are never renumbered.  The next event's predecessor hash is
        the terminal hash committed by this checkpoint, so normal validation is
        checkpoint-plus-tail rather than a fabricated genesis replay.
        """
        if keep_checkpoints < 1:
            raise ValueError("keep_checkpoints_must_be_positive")
        if self.has_prepared_habitat_execution():
            raise PersistenceError("compaction_prepared_habitat_execution")
        self.validate_chain()
        snapshot = self.load_snapshot(snapshot_id)
        if snapshot["agent_id"] != agent_id:
            raise PersistenceError("checkpoint_snapshot_agent_mismatch")
        through = int(snapshot["sequence"])
        if through != self.last_sequence():
            raise PersistenceError("checkpoint_snapshot_not_current_tip")
        previous = self.latest_checkpoint()
        start = int(previous["compacted_sequence_end"]) + 1 if previous else 1
        if through < start:
            return None
        rows = self.conn.execute(
            "SELECT * FROM events WHERE sequence BETWEEN ? AND ? ORDER BY sequence ASC",
            (start, through),
        ).fetchall()
        if not rows:
            raise PersistenceError("checkpoint_missing_hot_tail")
        if int(rows[0]["sequence"]) != start or int(rows[-1]["sequence"]) != through:
            raise PersistenceError("checkpoint_tail_sequence_gap")
        protected: dict[str, dict[str, Any]] = {}
        for event_type in protected_event_types:
            event = self.last_event_of_types((event_type,))
            if event is not None:
                protected[f"event_type:{event_type}"] = event
        checkpoint_id = new_id()
        epoch = int(previous["checkpoint_epoch"]) + 1 if previous else 1
        terminal_hash = str(rows[-1]["event_hash"])
        envelope = self._checkpoint_envelope(
            checkpoint_id=checkpoint_id,
            agent_id=agent_id,
            checkpoint_epoch=epoch,
            compacted_sequence_start=start,
            compacted_sequence_end=through,
            compacted_event_count=len(rows),
            previous_checkpoint_hash=(
                str(previous["checkpoint_hash"]) if previous else "genesis"
            ),
            terminal_event_hash=terminal_hash,
            snapshot_id=snapshot_id,
            snapshot_state_hash=str(snapshot["state_hash"]),
            habitat_binding=dict(habitat_binding or {}),
            habitat_checkpoint=(dict(habitat_checkpoint) if habitat_checkpoint else None),
            body_attachment=dict(body_attachment or {}),
            schema_version=SCHEMA_VERSION,
            creation_tick=int(creation_tick),
            creation_wall_time=float(creation_wall_time),
        )
        checkpoint_hash = sha256_hex(canon_json(envelope))
        if crash_after == "checkpoint_prepared":
            raise PersistenceError("crash_injection_checkpoint_prepared")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("UPDATE snapshots SET protected=1 WHERE snapshot_id=?", (snapshot_id,))
            self.conn.execute(
                """
                INSERT INTO ledger_checkpoints(
                  checkpoint_id, agent_id, checkpoint_epoch,
                  compacted_sequence_start, compacted_sequence_end, compacted_event_count,
                  previous_checkpoint_hash, terminal_event_hash, snapshot_id, snapshot_state_hash,
                  habitat_binding_json, habitat_checkpoint_json, body_attachment_json,
                  schema_version, creation_tick, creation_wall_time, checkpoint_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    checkpoint_id, agent_id, epoch, start, through, len(rows),
                    envelope["previous_checkpoint_hash"], terminal_hash, snapshot_id,
                    snapshot["state_hash"], json.dumps(envelope["habitat_binding"], sort_keys=True),
                    json.dumps(envelope["habitat_checkpoint"], sort_keys=True) if envelope["habitat_checkpoint"] is not None else None,
                    json.dumps(envelope["body_attachment"], sort_keys=True), SCHEMA_VERSION,
                    int(creation_tick), float(creation_wall_time), checkpoint_hash,
                ),
            )
            for key, event in protected.items():
                self.conn.execute(
                    "INSERT INTO checkpoint_provenance(checkpoint_id, provenance_key, event_json, event_hash) VALUES (?,?,?,?)",
                    (checkpoint_id, key, json.dumps(event, sort_keys=True, separators=(",", ":")), event["event_hash"]),
                )
            if crash_after == "checkpoint_commit":
                raise PersistenceError("crash_injection_checkpoint_commit")
            self.conn.execute("DELETE FROM events WHERE sequence <= ?", (through,))
            if crash_after == "prefix_removal":
                raise PersistenceError("crash_injection_prefix_removal")
            self.conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                ("ledger_checkpoint", json.dumps({"checkpoint_id": checkpoint_id, "checkpoint_hash": checkpoint_hash}, sort_keys=True)),
            )
            self.conn.execute("COMMIT")
        except BaseException:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise
        # Old anchors are not live authority after their successor has committed.
        old_rows = self.conn.execute(
            "SELECT checkpoint_id, snapshot_id FROM ledger_checkpoints "
            "WHERE checkpoint_id != ? ORDER BY checkpoint_epoch DESC",
            (checkpoint_id,),
        ).fetchall()
        for old in old_rows[keep_checkpoints - 1:]:
            old_id, old_snapshot = str(old["checkpoint_id"]), str(old["snapshot_id"])
            self.conn.execute("DELETE FROM checkpoint_provenance WHERE checkpoint_id=?", (old_id,))
            self.conn.execute("DELETE FROM ledger_checkpoints WHERE checkpoint_id=?", (old_id,))
            still_protected = self.conn.execute(
                "SELECT 1 FROM ledger_checkpoints WHERE snapshot_id=? LIMIT 1", (old_snapshot,)
            ).fetchone()
            if still_protected is None:
                self.conn.execute("UPDATE snapshots SET protected=0 WHERE snapshot_id=?", (old_snapshot,))
        self.prune_snapshots(keep=2)
        self.validate_chain()
        return {**envelope, "checkpoint_hash": checkpoint_hash, "protected_provenance_count": len(protected)}

    def reclaim_physical_storage(self, *, crash_after: str | None = None) -> None:
        """Reclaim free SQLite pages only after a valid logical checkpoint.

        SQLite's own VACUUM is used deliberately: no application-level file
        replacement is introduced while an organism owns the connection.
        """
        if self.conn.in_transaction:
            raise PersistenceError("reclaim_active_transaction")
        self._validate_latest_checkpoint()
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        if crash_after == "before_vacuum":
            raise PersistenceError("crash_injection_before_vacuum")
        self.conn.execute("VACUUM")
        if crash_after == "after_vacuum":
            raise PersistenceError("crash_injection_after_vacuum")
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.validate_chain()

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
        tail_event = self._row_to_event(row) if row is not None else None
        checkpoint_event: dict[str, Any] | None = None
        checkpoint = self.latest_checkpoint()
        if checkpoint is not None:
            candidates = [
                item["event"]
                for item in self.checkpoint_provenance(checkpoint["checkpoint_id"])
                if item["event"].get("event_type") in event_types
            ]
            if candidates:
                checkpoint_event = max(candidates, key=lambda item: int(item["sequence"]))
        if tail_event is None:
            return checkpoint_event
        if checkpoint_event is None:
            return tail_event
        return tail_event if int(tail_event["sequence"]) >= int(checkpoint_event["sequence"]) else checkpoint_event

    def validate_chain(self) -> None:
        checkpoint = self._validate_latest_checkpoint()
        from_sequence = int(checkpoint["compacted_sequence_end"]) + 1 if checkpoint else 1
        events = self.iter_events(from_sequence)
        prev_hash = str(checkpoint["terminal_event_hash"]) if checkpoint else "genesis"
        expect_seq = from_sequence
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
        row = self.conn.execute("SELECT value FROM meta WHERE key = 'ledger_tip'").fetchone()
        if row is not None:
            tip = json.loads(row[0])
            if tip != {"sequence": expect_seq - 1, "event_hash": prev_hash}:
                raise PersistenceError("ledger_tip_mismatch")

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

    # --- D-009 habitat execution journal + atomic manipulation commit --------

    def insert_habitat_execution_journal_prepared(
        self,
        *,
        execution_id: str,
        request_id: str,
        canonical_payload_hash: str,
        payload_json: str,
        transaction_id: str,
        prepared_tick: int,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO habitat_execution_journal(
              execution_id, request_id, status, canonical_payload_hash,
              payload_json, transaction_id, prepared_tick, outcome_id, failure_code
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                execution_id,
                request_id,
                "PREPARED",
                canonical_payload_hash,
                payload_json,
                transaction_id,
                int(prepared_tick),
                None,
                None,
            ),
        )

    def get_habitat_execution_journal(self, execution_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM habitat_execution_journal WHERE execution_id=?",
            (execution_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def get_habitat_execution_journal_by_request_id(self, request_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM habitat_execution_journal WHERE request_id=?",
            (request_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def has_prepared_habitat_execution(self) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM habitat_execution_journal WHERE status='PREPARED' LIMIT 1"
        ).fetchone()
        return row is not None

    def update_habitat_execution_journal_terminal(
        self,
        *,
        execution_id: str,
        status: str,
        outcome_id: str | None,
        failure_code: str | None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE habitat_execution_journal
            SET status=?, outcome_id=?, failure_code=?
            WHERE execution_id=?
            """,
            (status, outcome_id, failure_code, execution_id),
        )

    def finalize_habitat_execution_journal_recovery(
        self,
        *,
        execution_id: str,
        status: str,
        outcome_id: str | None,
        failure_code: str | None,
    ) -> None:
        self.update_habitat_execution_journal_terminal(
            execution_id=execution_id,
            status=status,
            outcome_id=outcome_id,
            failure_code=failure_code,
        )

    def find_habitat_execution_commit_evidence(
        self,
        *,
        execution_id: str,
        transaction_id: str,
        agent_id: str,
    ) -> dict[str, Any] | None:
        rows = self.conn.execute(
            """
            SELECT payload FROM events
            WHERE agent_id=? AND event_type='outcome_verified'
            ORDER BY sequence DESC
            """,
            (agent_id,),
        ).fetchall()
        for r in rows:
            payload = json.loads(r["payload"])
            if payload.get("execution_id") != execution_id:
                continue
            raw = payload.get("raw") or {}
            if raw.get("transaction_id") != transaction_id:
                continue
            return {
                "status": "COMMITTED_SUCCESS" if payload.get("success") else "COMMITTED_FAILURE",
                "outcome_id": payload.get("outcome_id"),
                "failure_code": None if payload.get("success") else payload.get("reason"),
            }
        return None

    def list_habitat_events_for_execution(
        self,
        *,
        agent_id: str,
        execution_id: str,
        transaction_id: str,
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT event_type, payload FROM events
            WHERE agent_id=? AND event_type LIKE 'habitat_%'
            ORDER BY sequence ASC
            """,
            (agent_id,),
        ).fetchall()
        events: list[dict[str, Any]] = []
        for r in rows:
            if r["event_type"] == "habitat_body_zone_transitioned":
                continue
            payload = json.loads(r["payload"])
            if payload.get("execution_id") != execution_id:
                continue
            if payload.get("transaction_id") != transaction_id:
                continue
            events.append({"event_type": r["event_type"], "payload": payload})
        return events

    def get_verified_outcome_by_id(self, outcome_id: str, *, agent_id: str):
        row = self.conn.execute(
            """
            SELECT payload FROM events
            WHERE agent_id=? AND event_type='outcome_verified' AND event_id=?
            LIMIT 1
            """,
            (agent_id, outcome_id),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload"])
        from umbra_core.governance import VerifiedOutcome

        return VerifiedOutcome(
            outcome_id=str(payload.get("outcome_id", outcome_id)),
            capability=str(payload.get("capability", "MANIPULATE")),
            success=bool(payload.get("success")),
            reason=str(payload.get("reason", "")),
            physiology_effects=dict(payload.get("effects") or {}),
            raw=dict(payload.get("raw") or {}),
            verified=bool(payload.get("verified", True)),
        )

    def _check_event_storage_budget(self) -> None:
        if self.event_storage_budget is None:
            return
        count = self.conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()
        if int(count["c"]) >= self.event_storage_budget:
            from umbra_core.habitat.execution_journal import EVENT_STORAGE_BUDGET_EXCEEDED
            from umbra_core.habitat.state import MutationRejected

            raise MutationRejected(EVENT_STORAGE_BUDGET_EXCEEDED)

    def atomic_manipulation_outcome(
        self,
        stages: list[Any],
        *,
        on_commit: Any = None,
        crash_after_stage: int | None = None,
    ) -> None:
        """Atomic habitat manipulation durable commit — mirrors atomic_social_outcome."""
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

    def atomic_profile_migration(
        self,
        stages: list[Any],
        *,
        on_commit: Any = None,
        crash_after_stage: int | None = None,
    ) -> None:
        """Atomic D-009 profile swap + optional held-binding rebase commit."""
        self.atomic_manipulation_outcome(
            stages,
            on_commit=on_commit,
            crash_after_stage=crash_after_stage,
        )

    def atomic_body_replacement(
        self,
        stages: list[Any],
        *,
        on_commit: Any = None,
        crash_after_stage: int | None = None,
    ) -> None:
        """Atomic AS-003S replacement event + prospective snapshot commit."""
        self.atomic_manipulation_outcome(
            stages,
            on_commit=on_commit,
            crash_after_stage=crash_after_stage,
        )

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

    def atomic_downtime_reconciliation_commit(
        self,
        stages: list[Any],
        *,
        on_commit: Any = None,
        crash_after_stage: int | None = None,
    ) -> None:
        """Atomic D-010 downtime reconciliation durable commit."""
        self.atomic_social_outcome(
            stages,
            on_commit=on_commit,
            crash_after_stage=crash_after_stage,
        )

    def atomic_orchestration_tick_commit(
        self,
        stages: list[Any],
        *,
        on_commit: Any = None,
        crash_after_stage: int | None = None,
    ) -> None:
        """Atomic D-010 orchestration tick durable commit."""
        self.atomic_social_outcome(
            stages,
            on_commit=on_commit,
            crash_after_stage=crash_after_stage,
        )

    def corrupt_event_payload(self, sequence: int, new_payload: dict[str, Any]) -> None:
        """Test helper — mutates payload without updating hashes."""
        payload_s = json.dumps(new_payload, sort_keys=True, separators=(",", ":"))
        self.conn.execute(
            "UPDATE events SET payload=? WHERE sequence=?",
            (payload_s, sequence),
        )
