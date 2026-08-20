"""SQLite-backed durable ledger for the synthetic AXH qualification harness."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

from .protocol import canonical


class LedgerError(RuntimeError):
    pass


class NonDeterministicDuplicateResult(LedgerError):
    """The same logical branch produced conflicting scientific results."""


def result_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(raw)
    with temp.open("rb") as handle:
        handle.flush()
    temp.replace(path)
    return hashlib.sha256(raw).hexdigest()


class DurableLedger:
    """A fail-closed SQLite execution ledger.

    Scientific completion is represented only by a transaction that records a
    verified immutable result hash. Operational metadata never enters the
    canonical scientific dataset.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._schema()

    def close(self) -> None:
        self.conn.close()

    def _schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS execution (
                execution_id TEXT PRIMARY KEY,
                protocol_fingerprint TEXT NOT NULL,
                source_baseline TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('RUNNING','COMPLETE','INCOMPLETE')),
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS branch (
                logical_branch_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL REFERENCES execution(execution_id),
                target TEXT NOT NULL,
                start_tick INTEGER NOT NULL,
                prefix_depth INTEGER NOT NULL,
                parent_branch_id TEXT,
                action_json TEXT NOT NULL,
                input_state_hash TEXT NOT NULL,
                rng_state_hash TEXT NOT NULL,
                remaining_forced_depth INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('PENDING','RUNNING','COMPLETE','FAILED')),
                attempt_count INTEGER NOT NULL DEFAULT 0,
                result_hash TEXT,
                result_path TEXT,
                expanded INTEGER NOT NULL DEFAULT 0 CHECK(expanded IN (0,1)),
                last_error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS branch_status_idx ON branch(execution_id, status);
            CREATE TABLE IF NOT EXISTS frontier (
                execution_id TEXT NOT NULL REFERENCES execution(execution_id),
                parent_branch_id TEXT NOT NULL REFERENCES branch(logical_branch_id),
                child_branch_id TEXT NOT NULL REFERENCES branch(logical_branch_id),
                PRIMARY KEY(execution_id, parent_branch_id, child_branch_id)
            );
            CREATE TABLE IF NOT EXISTS confirmation (
                confirmation_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL REFERENCES execution(execution_id),
                source_branch_id TEXT NOT NULL REFERENCES branch(logical_branch_id),
                horizon INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('PENDING','RUNNING','COMPLETE','FAILED')),
                result_hash TEXT,
                result_path TEXT,
                last_error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orchestrator_event (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL REFERENCES execution(execution_id),
                event_type TEXT NOT NULL,
                logical_branch_id TEXT,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dedup (
                execution_id TEXT NOT NULL REFERENCES execution(execution_id),
                dedup_key TEXT NOT NULL,
                representative_branch_id TEXT NOT NULL,
                PRIMARY KEY(execution_id, dedup_key)
            );
            """
        )

    def _now(self) -> float:
        return time.time()

    def _event(self, execution_id: str, event_type: str, payload: dict[str, Any], logical_branch_id: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO orchestrator_event(execution_id,event_type,logical_branch_id,payload_json,created_at) VALUES(?,?,?,?,?)",
            (execution_id, event_type, logical_branch_id, canonical(payload), self._now()),
        )

    def create_execution(self, execution_id: str, protocol_fingerprint: str, source_baseline: str) -> None:
        now = self._now()
        self.conn.execute(
            "INSERT INTO execution(execution_id,protocol_fingerprint,source_baseline,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (execution_id, protocol_fingerprint, source_baseline, "RUNNING", now, now),
        )
        self._event(execution_id, "EXECUTION_CREATED", {"protocol_fingerprint": protocol_fingerprint, "source_baseline": source_baseline})

    def verify_execution(self, execution_id: str, protocol_fingerprint: str, source_baseline: str) -> None:
        row = self.conn.execute("SELECT * FROM execution WHERE execution_id=?", (execution_id,)).fetchone()
        if row is None:
            raise LedgerError("execution_missing")
        if row["protocol_fingerprint"] != protocol_fingerprint or row["source_baseline"] != source_baseline:
            raise LedgerError("protocol_or_source_mismatch")

    def ensure_branch(self, execution_id: str, spec: dict[str, Any], logical_branch_id: str) -> bool:
        now = self._now()
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO branch(logical_branch_id,execution_id,target,start_tick,prefix_depth,parent_branch_id,action_json,input_state_hash,rng_state_hash,remaining_forced_depth,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                logical_branch_id,
                execution_id,
                spec["target"],
                int(spec["start_tick"]),
                int(spec["prefix_depth"]),
                spec.get("parent_branch_id"),
                canonical(spec["action"]),
                spec["input_state_hash"],
                spec["rng_state_hash"],
                int(spec["remaining_forced_depth"]),
                "PENDING",
                now,
                now,
            ),
        )
        if cur.rowcount:
            return True
        row = self.conn.execute("SELECT execution_id,action_json,input_state_hash,rng_state_hash FROM branch WHERE logical_branch_id=?", (logical_branch_id,)).fetchone()
        if row is None or row["execution_id"] != execution_id or row["action_json"] != canonical(spec["action"]):
            raise LedgerError("logical_branch_id_collision")
        return False

    def claim_branch(self, execution_id: str, logical_branch_id: str) -> bool:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT status FROM branch WHERE execution_id=? AND logical_branch_id=?", (execution_id, logical_branch_id)).fetchone()
            if row is None:
                raise LedgerError("branch_missing")
            if row["status"] == "COMPLETE":
                self.conn.execute("COMMIT")
                return False
            if row["status"] == "RUNNING":
                self.conn.execute("ROLLBACK")
                return False
            self.conn.execute("UPDATE branch SET status='RUNNING',attempt_count=attempt_count+1,updated_at=? WHERE logical_branch_id=?", (self._now(), logical_branch_id))
            self._event(execution_id, "BRANCH_CLAIMED", {}, logical_branch_id)
            self.conn.execute("COMMIT")
            return True
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def recover_running(self, execution_id: str) -> int:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            rows = self.conn.execute("SELECT logical_branch_id FROM branch WHERE execution_id=? AND status='RUNNING'", (execution_id,)).fetchall()
            for row in rows:
                self.conn.execute("UPDATE branch SET status='PENDING',updated_at=? WHERE logical_branch_id=?", (self._now(), row["logical_branch_id"]))
                self._event(execution_id, "BRANCH_REQUEUED_AFTER_PARENT_RECOVERY", {}, row["logical_branch_id"])
            self.conn.execute("COMMIT")
            return len(rows)
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def publish_result(self, execution_id: str, logical_branch_id: str, payload: dict[str, Any], result_path: str, payload_hash: str | None = None) -> str:
        computed = result_hash(payload)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT status,result_hash FROM branch WHERE execution_id=? AND logical_branch_id=?", (execution_id, logical_branch_id)).fetchone()
            if row is None:
                raise LedgerError("branch_missing")
            if row["status"] == "COMPLETE":
                if row["result_hash"] == computed:
                    self.record_event(execution_id, "DUPLICATE_RESULT_IDEMPOTENT", {"result_hash": computed}, logical_branch_id)
                    self.conn.execute("COMMIT")
                    return "DUPLICATE_SAME"
                raise NonDeterministicDuplicateResult("NONDETERMINISTIC_DUPLICATE_RESULT")
            if row["status"] != "RUNNING":
                raise LedgerError("branch_not_running")
            if payload_hash is not None:
                path = Path(result_path)
                if not path.is_file() or content_hash(path) != payload_hash:
                    raise LedgerError("result_content_hash_mismatch")
            self.conn.execute("UPDATE branch SET status='COMPLETE',result_hash=?,result_path=?,updated_at=? WHERE logical_branch_id=?", (computed, result_path, self._now(), logical_branch_id))
            self._event(execution_id, "BRANCH_COMPLETE", {"result_hash": computed, "result_path": result_path}, logical_branch_id)
            self.conn.execute("COMMIT")
            return "COMPLETE"
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def fail_branch(self, execution_id: str, logical_branch_id: str, error: str) -> None:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("UPDATE branch SET status='FAILED',last_error=?,updated_at=? WHERE execution_id=? AND logical_branch_id=?", (error, self._now(), execution_id, logical_branch_id))
            self._event(execution_id, "BRANCH_FAILED", {"error": error}, logical_branch_id)
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def expand_frontier(self, execution_id: str, parent_id: str, children: Iterable[tuple[str, dict[str, Any]]], crash: bool = False) -> list[str]:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            parent = self.conn.execute("SELECT status,expanded FROM branch WHERE execution_id=? AND logical_branch_id=?", (execution_id, parent_id)).fetchone()
            if parent is None:
                raise LedgerError("parent_missing")
            if parent["status"] != "COMPLETE":
                raise LedgerError("parent_not_complete")
            if parent["expanded"]:
                self.conn.execute("COMMIT")
                return [r["child_branch_id"] for r in self.conn.execute("SELECT child_branch_id FROM frontier WHERE parent_branch_id=?", (parent_id,)).fetchall()]
            ids: list[str] = []
            for child_id, spec in children:
                self.ensure_branch(execution_id, spec, child_id)
                self.conn.execute("INSERT OR IGNORE INTO frontier(execution_id,parent_branch_id,child_branch_id) VALUES(?,?,?)", (execution_id, parent_id, child_id))
                ids.append(child_id)
            if crash:
                raise RuntimeError("INJECTED_CRASH_DURING_FRONTIER_EXPANSION")
            self.conn.execute("UPDATE branch SET expanded=1,updated_at=? WHERE logical_branch_id=?", (self._now(), parent_id))
            self._event(execution_id, "FRONTIER_EXPANDED", {"children": ids}, parent_id)
            self.conn.execute("COMMIT")
            return ids
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def schedule_confirmation(self, execution_id: str, confirmation_id: str, source_branch_id: str, horizon: int) -> bool:
        now = self._now()
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO confirmation(confirmation_id,execution_id,source_branch_id,horizon,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (confirmation_id, execution_id, source_branch_id, int(horizon), "PENDING", now, now),
        )
        return bool(cur.rowcount)

    def claim_confirmation(self, execution_id: str, confirmation_id: str) -> bool:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT status FROM confirmation WHERE execution_id=? AND confirmation_id=?", (execution_id, confirmation_id)).fetchone()
            if row is None:
                raise LedgerError("confirmation_missing")
            if row["status"] == "COMPLETE":
                self.conn.execute("COMMIT")
                return False
            self.conn.execute("UPDATE confirmation SET status='RUNNING',updated_at=? WHERE confirmation_id=?", (self._now(), confirmation_id))
            self._event(execution_id, "CONFIRMATION_CLAIMED", {}, confirmation_id)
            self.conn.execute("COMMIT")
            return True
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def publish_confirmation(self, execution_id: str, confirmation_id: str, payload: dict[str, Any], result_path: str) -> str:
        rh = result_hash(payload)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT status,result_hash FROM confirmation WHERE execution_id=? AND confirmation_id=?", (execution_id, confirmation_id)).fetchone()
            if row is None:
                raise LedgerError("confirmation_missing")
            if row["status"] == "COMPLETE":
                self.conn.execute("COMMIT")
                if row["result_hash"] != rh:
                    raise NonDeterministicDuplicateResult("NONDETERMINISTIC_DUPLICATE_CONFIRMATION")
                return "DUPLICATE_SAME"
            self.conn.execute("UPDATE confirmation SET status='COMPLETE',result_hash=?,result_path=?,updated_at=? WHERE confirmation_id=?", (rh, result_path, self._now(), confirmation_id))
            self._event(execution_id, "CONFIRMATION_COMPLETE", {"result_hash": rh, "result_path": result_path}, confirmation_id)
            self.conn.execute("COMMIT")
            return "COMPLETE"
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def record_event(self, execution_id: str, event_type: str, payload: dict[str, Any], logical_branch_id: str | None = None) -> None:
        self._event(execution_id, event_type, payload, logical_branch_id)

    def counts(self, execution_id: str) -> dict[str, Any]:
        branches = {row["status"]: row["n"] for row in self.conn.execute("SELECT status,COUNT(*) n FROM branch WHERE execution_id=? GROUP BY status", (execution_id,)).fetchall()}
        confirmations = {row["status"]: row["n"] for row in self.conn.execute("SELECT status,COUNT(*) n FROM confirmation WHERE execution_id=? GROUP BY status", (execution_id,)).fetchall()}
        frontier = self.conn.execute("SELECT COUNT(*) n FROM branch WHERE execution_id=? AND status='COMPLETE' AND expanded=0", (execution_id,)).fetchone()["n"]
        return {"branches": {x: branches.get(x, 0) for x in ("PENDING", "RUNNING", "COMPLETE", "FAILED")}, "confirmations": {x: confirmations.get(x, 0) for x in ("PENDING", "RUNNING", "COMPLETE", "FAILED")}, "unexpanded_complete_parents": frontier}

    def completeness(self, execution_id: str, protocol_fingerprint: str) -> dict[str, Any]:
        self.verify_execution(execution_id, protocol_fingerprint, self.conn.execute("SELECT source_baseline FROM execution WHERE execution_id=?", (execution_id,)).fetchone()[0])
        counts = self.counts(execution_id)
        complete = (
            counts["branches"]["PENDING"] == 0
            and counts["branches"]["RUNNING"] == 0
            and counts["branches"]["FAILED"] == 0
            and counts["confirmations"]["PENDING"] == 0
            and counts["confirmations"]["RUNNING"] == 0
            and counts["confirmations"]["FAILED"] == 0
            and counts["unexpanded_complete_parents"] == 0
        )
        return {"execution_complete": bool(complete), "counts": counts}

    def canonical_dataset(self, execution_id: str) -> dict[str, Any]:
        branches = [dict(row) for row in self.conn.execute("SELECT logical_branch_id,target,start_tick,prefix_depth,parent_branch_id,action_json,input_state_hash,rng_state_hash,remaining_forced_depth,status,result_hash FROM branch WHERE execution_id=? ORDER BY logical_branch_id", (execution_id,)).fetchall()]
        for row in branches:
            row["action"] = json.loads(row.pop("action_json"))
        frontiers = [dict(row) for row in self.conn.execute("SELECT parent_branch_id,child_branch_id FROM frontier WHERE execution_id=? ORDER BY parent_branch_id,child_branch_id", (execution_id,)).fetchall()]
        confirmations = [dict(row) for row in self.conn.execute("SELECT confirmation_id,source_branch_id,horizon,status,result_hash FROM confirmation WHERE execution_id=? ORDER BY confirmation_id", (execution_id,)).fetchall()]
        return {"branches": branches, "frontier": frontiers, "confirmations": confirmations}

    def mark_execution_status(self, execution_id: str, status: str) -> None:
        if status not in {"RUNNING", "COMPLETE", "INCOMPLETE"}:
            raise LedgerError("invalid_execution_status")
        self.conn.execute("UPDATE execution SET status=?,updated_at=? WHERE execution_id=?", (status, self._now(), execution_id))
