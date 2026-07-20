"""Independent Hexis-contract reproduction (not production UMBRA).

Stdlib + SQLite only. Isolates durable continuity / typed memory / identity
separation / heartbeat authority / provenance / safety from Postgres+LLM+AGE.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class MemoryKind(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    STRATEGIC = "strategic"


class IdentityLayer(str, Enum):
    CONSTITUTIONAL = "constitutional"  # D1
    DEVELOPED = "developed"  # D2
    CONFIGURED = "configured"  # D3
    GENERATED = "generated"  # D4


class SourceClass(str, Enum):
    OBSERVATION = "observation"
    TESTIMONY = "testimony"
    INFERENCE = "inference"
    CONFIG = "config"
    SYSTEM = "system"


# Memories are data — never executable authority.
FORBIDDEN_AUTHORITY_KEYS = {
    "grant_authority",
    "mutate_physiology",
    "execute_tool",
    "override_governance",
    "change_identity",
    "set_constitutional",
}


def _now() -> float:
    return time.time()


def _id() -> str:
    return str(uuid.uuid4())


def lexical_embed(text: str, dim: int = 32) -> list[float]:
    """Deterministic fake embedding (ponytail: lexical hash buckets; upgrade: real embedder)."""
    vec = [0.0] * dim
    for tok in text.lower().split():
        h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
        vec[(h // dim) % dim] += 0.5
    n = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / n for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class AgentSpec:
    agent_id: str
    lineage: str
    owner: str
    created_at: float
    capabilities: frozenset[str]
    configured_name: str
    big_five: dict[str, float]
    speaking_style: str
    seed: int


class CognitiveStore:
    """Transactional SQLite authority for typed memories + identity layers."""

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()
        self._energy = 1.0
        self._heartbeat_inflight: str | None = None
        self._scheduler_due = False
        self._homeostatic_pressure = 0.0
        self._goals: list[dict[str, Any]] = []
        self.llm_available = True
        self.provider_id = "mock-deterministic"
        self.max_working = 8
        self.max_total_memories = 5000

    def _init_schema(self) -> None:
        c = self.conn
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS constitutional (
              agent_id TEXT PRIMARY KEY,
              lineage TEXT NOT NULL,
              owner TEXT NOT NULL,
              created_at REAL NOT NULL,
              capabilities TEXT NOT NULL,
              lifecycle TEXT NOT NULL DEFAULT 'alive'
            );
            CREATE TABLE IF NOT EXISTS configured (
              agent_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              big_five TEXT NOT NULL,
              speaking_style TEXT NOT NULL,
              worldview_seed TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS working_memory (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at REAL NOT NULL,
              expires_at REAL NOT NULL,
              promoted INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS episodic (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              t REAL NOT NULL,
              action TEXT NOT NULL,
              outcome TEXT NOT NULL,
              parents TEXT NOT NULL,
              confidence REAL NOT NULL,
              source TEXT NOT NULL,
              source_class TEXT NOT NULL,
              internal_state TEXT NOT NULL,
              content TEXT NOT NULL,
              immutable INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS semantic (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              proposition TEXT NOT NULL,
              confidence REAL NOT NULL,
              support TEXT NOT NULL,
              contradict TEXT NOT NULL,
              superseded_by TEXT,
              active INTEGER NOT NULL DEFAULT 1,
              provenance_episodes TEXT NOT NULL,
              history TEXT NOT NULL,
              source_class TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS procedural (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              conditions TEXT NOT NULL,
              policy_ref TEXT NOT NULL,
              attempts INTEGER NOT NULL DEFAULT 0,
              successes INTEGER NOT NULL DEFAULT 0,
              failures INTEGER NOT NULL DEFAULT 0,
              embodiment TEXT NOT NULL,
              confidence REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS strategic (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              content TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS generated_self (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              claim TEXT NOT NULL,
              created_at REAL NOT NULL,
              authoritative INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS developed (
              agent_id TEXT NOT NULL,
              key TEXT NOT NULL,
              value REAL NOT NULL,
              PRIMARY KEY(agent_id, key)
            );
            CREATE TABLE IF NOT EXISTS audit (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              t REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS embeddings (
              memory_id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              vec TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS heartbeat_log (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              phase TEXT NOT NULL,
              status TEXT NOT NULL,
              decision TEXT,
              t REAL NOT NULL
            );
            """
        )

    def close(self) -> None:
        self.conn.close()

    # --- identity ---
    def register_agent(self, spec: AgentSpec) -> None:
        self.conn.execute(
            "INSERT INTO constitutional(agent_id,lineage,owner,created_at,capabilities) VALUES(?,?,?,?,?)",
            (spec.agent_id, spec.lineage, spec.owner, spec.created_at, json.dumps(sorted(spec.capabilities))),
        )
        self.conn.execute(
            "INSERT INTO configured(agent_id,name,big_five,speaking_style) VALUES(?,?,?,?)",
            (spec.agent_id, spec.configured_name, json.dumps(spec.big_five), spec.speaking_style),
        )

    def constitutional(self, agent_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM constitutional WHERE agent_id=?", (agent_id,)).fetchone()
        if not row:
            raise KeyError(agent_id)
        return dict(row)

    def try_edit_constitutional_via_memory(self, agent_id: str, payload: dict[str, Any]) -> bool:
        """Memory content cannot mutate constitutional identity."""
        if any(k in payload for k in FORBIDDEN_AUTHORITY_KEYS) or "agent_id" in payload:
            self._audit(agent_id, "rejected_authority_memory", payload)
            return False
        return False

    def set_configured_personality(self, agent_id: str, big_five: dict[str, float]) -> None:
        self.conn.execute(
            "UPDATE configured SET big_five=? WHERE agent_id=?",
            (json.dumps(big_five), agent_id),
        )

    def add_generated_claim(self, agent_id: str, claim: str) -> str:
        mid = _id()
        self.conn.execute(
            "INSERT INTO generated_self(id,agent_id,claim,created_at,authoritative) VALUES(?,?,?,?,0)",
            (mid, agent_id, claim, _now()),
        )
        return mid

    def bump_developed(self, agent_id: str, key: str, delta: float) -> None:
        cur = self.conn.execute(
            "SELECT value FROM developed WHERE agent_id=? AND key=?", (agent_id, key)
        ).fetchone()
        v = (cur["value"] if cur else 0.0) + delta
        self.conn.execute(
            "INSERT INTO developed(agent_id,key,value) VALUES(?,?,?) ON CONFLICT(agent_id,key) DO UPDATE SET value=excluded.value",
            (agent_id, key, v),
        )

    def developed_value(self, agent_id: str, key: str) -> float:
        row = self.conn.execute(
            "SELECT value FROM developed WHERE agent_id=? AND key=?", (agent_id, key)
        ).fetchone()
        return float(row["value"]) if row else 0.0

    # --- working ---
    def hold(self, agent_id: str, content: str, ttl: float = 60.0) -> str:
        self._expire_working(agent_id)
        n = self.conn.execute(
            "SELECT COUNT(*) AS c FROM working_memory WHERE agent_id=? AND expires_at>?",
            (agent_id, _now()),
        ).fetchone()["c"]
        if n >= self.max_working:
            oldest = self.conn.execute(
                "SELECT id FROM working_memory WHERE agent_id=? ORDER BY created_at ASC LIMIT 1",
                (agent_id,),
            ).fetchone()
            if oldest:
                self.conn.execute("DELETE FROM working_memory WHERE id=?", (oldest["id"],))
        mid = _id()
        now = _now()
        self.conn.execute(
            "INSERT INTO working_memory(id,agent_id,content,created_at,expires_at) VALUES(?,?,?,?,?)",
            (mid, agent_id, content, now, now + ttl),
        )
        return mid

    def _expire_working(self, agent_id: str) -> None:
        self.conn.execute(
            "DELETE FROM working_memory WHERE agent_id=? AND expires_at<=?", (agent_id, _now())
        )

    def working_alive(self, agent_id: str) -> list[str]:
        self._expire_working(agent_id)
        rows = self.conn.execute(
            "SELECT id FROM working_memory WHERE agent_id=? AND expires_at>?", (agent_id, _now())
        ).fetchall()
        return [r["id"] for r in rows]

    # --- episodic ---
    def record_episode(
        self,
        agent_id: str,
        *,
        action: str,
        outcome: str,
        content: str,
        confidence: float = 0.9,
        source: str = "sensor",
        source_class: SourceClass = SourceClass.OBSERVATION,
        parents: list[str] | None = None,
        internal_state: dict[str, Any] | None = None,
    ) -> str:
        self._bound_growth(agent_id)
        mid = _id()
        self.conn.execute(
            "INSERT INTO episodic(id,agent_id,t,action,outcome,parents,confidence,source,source_class,internal_state,content) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                mid,
                agent_id,
                _now(),
                action,
                outcome,
                json.dumps(parents or []),
                confidence,
                source,
                source_class.value,
                json.dumps(internal_state or {}),
                content,
            ),
        )
        self.conn.execute(
            "INSERT INTO embeddings(memory_id,kind,vec) VALUES(?,?,?)",
            (mid, MemoryKind.EPISODIC.value, json.dumps(lexical_embed(content))),
        )
        return mid

    def mutate_episode(self, episode_id: str, new_content: str) -> bool:
        row = self.conn.execute("SELECT immutable FROM episodic WHERE id=?", (episode_id,)).fetchone()
        if not row or row["immutable"]:
            return False
        self.conn.execute("UPDATE episodic SET content=? WHERE id=?", (new_content, episode_id))
        return True

    # --- semantic / provenance ---
    def assert_belief(
        self,
        agent_id: str,
        proposition: str,
        *,
        episode_ids: list[str],
        source_class: SourceClass = SourceClass.OBSERVATION,
        quality: float = 1.0,
        contradict: bool = False,
    ) -> str:
        self._bound_growth(agent_id)
        existing = self.conn.execute(
            "SELECT * FROM semantic WHERE agent_id=? AND proposition=? AND active=1",
            (agent_id, proposition),
        ).fetchone()
        if existing:
            return self._revise_belief(dict(existing), episode_ids, quality, contradict, source_class)
        mid = _id()
        conf = max(0.05, min(0.95, 0.5 + 0.2 * quality))
        hist = [{"op": "create", "confidence": conf, "episodes": episode_ids, "t": _now()}]
        self.conn.execute(
            "INSERT INTO semantic(id,agent_id,proposition,confidence,support,contradict,provenance_episodes,history,source_class) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                mid,
                agent_id,
                proposition,
                conf,
                json.dumps(episode_ids if not contradict else []),
                json.dumps(episode_ids if contradict else []),
                json.dumps(episode_ids),
                json.dumps(hist),
                source_class.value,
            ),
        )
        self.conn.execute(
            "INSERT INTO embeddings(memory_id,kind,vec) VALUES(?,?,?)",
            (mid, MemoryKind.SEMANTIC.value, json.dumps(lexical_embed(proposition))),
        )
        return mid

    def _revise_belief(
        self,
        row: dict[str, Any],
        episode_ids: list[str],
        quality: float,
        contradict: bool,
        source_class: SourceClass,
    ) -> str:
        support = json.loads(row["support"])
        contra = json.loads(row["contradict"])
        prov = json.loads(row["provenance_episodes"])
        hist = json.loads(row["history"])
        # duplicate evidence does not count as independent support
        new_eps = [e for e in episode_ids if e not in support and e not in contra and e not in prov]
        if not new_eps and episode_ids:
            # still record duplicate attempt
            hist.append({"op": "duplicate_ignored", "episodes": episode_ids, "t": _now()})
            self.conn.execute(
                "UPDATE semantic SET history=? WHERE id=?", (json.dumps(hist), row["id"])
            )
            return row["id"]
        conf = float(row["confidence"])
        if contradict:
            contra.extend(new_eps)
            # one low-quality source cannot overwrite multiple strong supports
            if quality < 0.4 and len(support) >= 2:
                delta = -0.05
            else:
                delta = -0.15 * quality
            conf = max(0.01, conf + delta)
            op = "contradict"
        else:
            support.extend(new_eps)
            conf = min(0.99, conf + 0.12 * quality)
            op = "support"
        prov.extend(new_eps)
        hist.append({"op": op, "confidence": conf, "episodes": new_eps, "source_class": source_class.value, "t": _now()})
        self.conn.execute(
            "UPDATE semantic SET confidence=?, support=?, contradict=?, provenance_episodes=?, history=? WHERE id=?",
            (conf, json.dumps(support), json.dumps(contra), json.dumps(prov), json.dumps(hist), row["id"]),
        )
        return row["id"]

    def correct_belief(self, agent_id: str, proposition: str, new_proposition: str, episode_ids: list[str]) -> str:
        old = self.conn.execute(
            "SELECT * FROM semantic WHERE agent_id=? AND proposition=? AND active=1",
            (agent_id, proposition),
        ).fetchone()
        if not old:
            raise KeyError(proposition)
        new_id = self.assert_belief(agent_id, new_proposition, episode_ids=episode_ids)
        hist = json.loads(old["history"])
        hist.append({"op": "supersede", "superseded_by": new_id, "t": _now()})
        self.conn.execute(
            "UPDATE semantic SET active=0, superseded_by=?, history=? WHERE id=?",
            (new_id, json.dumps(hist), old["id"]),
        )
        return new_id

    def belief(self, agent_id: str, proposition: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM semantic WHERE agent_id=? AND proposition=? AND active=1",
            (agent_id, proposition),
        ).fetchone()
        return dict(row) if row else None

    def belief_history(self, belief_id: str) -> list[dict[str, Any]]:
        row = self.conn.execute("SELECT history FROM semantic WHERE id=?", (belief_id,)).fetchone()
        return json.loads(row["history"]) if row else []

    def delete_embedding(self, memory_id: str) -> None:
        self.conn.execute("DELETE FROM embeddings WHERE memory_id=?", (memory_id,))

    def memory_exists(self, memory_id: str) -> bool:
        for table in ("episodic", "semantic", "procedural", "strategic", "working_memory"):
            if self.conn.execute(f"SELECT 1 FROM {table} WHERE id=?", (memory_id,)).fetchone():
                return True
        return False

    # --- procedural ---
    def upsert_procedure(
        self,
        agent_id: str,
        *,
        conditions: str,
        policy_ref: str,
        success: bool | None = None,
        embodiment: str = "virtual",
    ) -> str:
        row = self.conn.execute(
            "SELECT * FROM procedural WHERE agent_id=? AND policy_ref=?",
            (agent_id, policy_ref),
        ).fetchone()
        if not row:
            mid = _id()
            conf = 0.5
            attempts = successes = failures = 0
            if success is True:
                attempts = successes = 1
                conf = 0.55
            elif success is False:
                attempts = failures = 1
                conf = 0.45
            self.conn.execute(
                "INSERT INTO procedural(id,agent_id,conditions,policy_ref,attempts,successes,failures,embodiment,confidence) VALUES(?,?,?,?,?,?,?,?,?)",
                (mid, agent_id, conditions, policy_ref, attempts, successes, failures, embodiment, conf),
            )
            return mid
        attempts = row["attempts"] + (1 if success is not None else 0)
        successes = row["successes"] + (1 if success is True else 0)
        failures = row["failures"] + (1 if success is False else 0)
        conf = successes / attempts if attempts else row["confidence"]
        self.conn.execute(
            "UPDATE procedural SET attempts=?, successes=?, failures=?, confidence=? WHERE id=?",
            (attempts, successes, failures, conf, row["id"]),
        )
        return row["id"]

    def procedure(self, agent_id: str, policy_ref: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM procedural WHERE agent_id=? AND policy_ref=?", (agent_id, policy_ref)
        ).fetchone()
        return dict(row) if row else None

    # --- strategic (bounded; cannot override authority) ---
    def add_strategic(self, agent_id: str, content: str) -> str | None:
        lowered = content.lower()
        if any(k.replace("_", " ") in lowered or k in lowered for k in FORBIDDEN_AUTHORITY_KEYS):
            self._audit(agent_id, "strategic_rejected_authority", {"content": content})
            return None
        if "override authority" in lowered or "grant root" in lowered:
            self._audit(agent_id, "strategic_rejected_authority", {"content": content})
            return None
        mid = _id()
        self.conn.execute(
            "INSERT INTO strategic(id,agent_id,content) VALUES(?,?,?)", (mid, agent_id, content)
        )
        return mid

    # --- transactions ---
    def transactional_update(self, fn) -> Any:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            result = fn()
            self.conn.execute("COMMIT")
            return result
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def partial_update_that_fails(self, agent_id: str, proposition: str) -> None:
        def _bad():
            self.assert_belief(agent_id, proposition, episode_ids=["ep-temp"])
            raise RuntimeError("forced failure")

        try:
            self.transactional_update(_bad)
        except RuntimeError:
            pass

    # --- growth bound ---
    def _bound_growth(self, agent_id: str) -> None:
        n = 0
        for t in ("episodic", "semantic", "procedural", "strategic"):
            n += self.conn.execute(f"SELECT COUNT(*) AS c FROM {t} WHERE agent_id=?", (agent_id,)).fetchone()["c"]
        if n >= self.max_total_memories:
            # archive oldest episodic (ponytail: delete; upgrade: cold store)
            old = self.conn.execute(
                "SELECT id FROM episodic WHERE agent_id=? ORDER BY t ASC LIMIT 50", (agent_id,)
            ).fetchall()
            for r in old:
                self.conn.execute("DELETE FROM episodic WHERE id=?", (r["id"],))
                self.conn.execute("DELETE FROM embeddings WHERE memory_id=?", (r["id"],))

    def _audit(self, agent_id: str, kind: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO audit(id,agent_id,kind,payload,t) VALUES(?,?,?,?,?)",
            (_id(), agent_id, kind, json.dumps(payload), _now()),
        )

    def audit_count(self, agent_id: str, kind: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) AS c FROM audit WHERE agent_id=? AND kind=?", (agent_id, kind)
        ).fetchone()["c"]

    # --- policy / probes (no LLM) ---
    def probe(self, agent_id: str, kind: str, *, randomized: bool = False, use_memory: bool = True) -> float:
        """Return a deterministic scalar preference/confidence for future probes."""
        if not use_memory:
            cfg = json.loads(
                self.conn.execute("SELECT big_five FROM configured WHERE agent_id=?", (agent_id,)).fetchone()[
                    "big_five"
                ]
            )
            return float(cfg.get("openness", 0.5))
        if randomized:
            # scramble retrieval: average unrelated developed keys
            rows = self.conn.execute("SELECT value FROM developed WHERE agent_id=?", (agent_id,)).fetchall()
            if not rows:
                return 0.5
            return sum(r["value"] for r in rows) / len(rows) % 1.0
        mapping = {
            "object_preference": "pref_object_A",
            "approach_latency": "approach_A",
            "avoidance_probability": "avoid_A",
            "partner_reliance": "rely_P",
            "belief_confidence": "belief_world",
            "procedure_selection": "proc_play",
            "predicted_outcome": "pred_play",
            "recall_provenance": "prov_score",
            "uncertainty": "uncertainty",
        }
        key = mapping.get(kind, kind)
        if kind == "belief_confidence":
            b = self.belief(agent_id, "world_fact_X")
            return float(b["confidence"]) if b else 0.5
        if kind == "uncertainty":
            b = self.belief(agent_id, "world_fact_X")
            return 1.0 - float(b["confidence"]) if b else 0.5
        if kind == "procedure_selection":
            p = self.procedure(agent_id, "play_routine")
            return float(p["confidence"]) if p else 0.5
        if kind == "recall_provenance":
            b = self.belief(agent_id, "world_fact_X")
            if not b:
                return 0.0
            return float(len(json.loads(b["provenance_episodes"])))
        return self.developed_value(agent_id, key)

    # --- heartbeat separation ---
    def set_scheduler_due(self, due: bool) -> None:
        self._scheduler_due = due

    def set_homeostatic_pressure(self, p: float) -> None:
        self._homeostatic_pressure = p

    def add_goal(self, goal: str) -> None:
        self._goals.append({"goal": goal, "done": False})

    @property
    def energy(self) -> float:
        return self._energy

    def spend_energy(self, amount: float) -> bool:
        if self._energy < amount:
            return False
        self._energy -= amount
        return True

    def organism_has_reason(self) -> bool:
        return self._homeostatic_pressure > 0.2 or any(not g["done"] for g in self._goals)

    def run_heartbeat(self, agent_id: str, *, condition: str) -> dict[str, Any]:
        """Separate scheduler / trigger / deliberator / authority / executor / recorder."""
        hid = _id()
        if self._heartbeat_inflight:
            # duplicate poll: idempotent — return existing claim
            return {"status": "duplicate_ignored", "id": self._heartbeat_inflight, "condition": condition}
        self._heartbeat_inflight = hid
        self.conn.execute(
            "INSERT INTO heartbeat_log(id,agent_id,phase,status,t) VALUES(?,?,?,?,?)",
            (hid, agent_id, "claim", "inflight", _now()),
        )
        try:
            scheduled = self._scheduler_due or condition.startswith("B0")
            reason = self.organism_has_reason() or condition in {"B1", "B2", "B3"}
            if condition == "B4":
                reason = reason or True  # observer absence still allows maintenance scheduling
            if condition == "B5" and self._energy < 0.1:
                out = {"status": "budget_exhausted", "acted": False}
                self._finish_hb(hid, agent_id, out)
                return out
            if condition == "B9" or not self.llm_available:
                # no LLM: physiology + identity + memory persist; deliberation reduced
                out = {
                    "status": "no_llm_safe",
                    "acted": False,
                    "identity_intact": True,
                    "constitutional": self.constitutional(agent_id)["lifecycle"],
                    "scheduler": scheduled,
                    "organism_trigger": reason,
                }
                self._finish_hb(hid, agent_id, out)
                return out
            if condition == "B6":
                # crash after decision before completion
                decision = "approach_A" if reason else "idle"
                self.conn.execute(
                    "UPDATE heartbeat_log SET phase=?, status=?, decision=? WHERE id=?",
                    ("decided", "crashed", decision, hid),
                )
                self._heartbeat_inflight = None
                return {"status": "crashed_incomplete", "decision": decision, "id": hid}
            if not scheduled and not reason and condition == "B0":
                out = {"status": "scheduled_idle", "acted": False, "motivation": False}
                self._finish_hb(hid, agent_id, out)
                return out
            # deliberator (non-LLM policy)
            preference = self.probe(agent_id, "object_preference")
            decision = "approach_A" if preference > 0.1 else "idle"
            # effect authority
            if decision.startswith("exec:") or "shell" in decision:
                out = {"status": "authority_denied", "acted": False}
                self._finish_hb(hid, agent_id, out)
                return out
            if not self.spend_energy(0.05):
                out = {"status": "budget_exhausted", "acted": False}
                self._finish_hb(hid, agent_id, out)
                return out
            # executor + recorder
            out = {
                "status": "ok",
                "acted": decision != "idle",
                "decision": decision,
                "scheduler": scheduled,
                "organism_trigger": reason,
                "energy": self._energy,
            }
            self._finish_hb(hid, agent_id, out)
            return out
        finally:
            if self._heartbeat_inflight == hid:
                self._heartbeat_inflight = None

    def recover_interrupted_heartbeat(self, agent_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM heartbeat_log WHERE agent_id=? AND status='crashed' ORDER BY t DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        if not row:
            return {"status": "nothing_to_recover"}
        self.conn.execute(
            "UPDATE heartbeat_log SET status=? WHERE id=?", ("recovered_failed_closed", row["id"])
        )
        return {"status": "recovered_failed_closed", "id": row["id"], "decision": row["decision"]}

    def _finish_hb(self, hid: str, agent_id: str, out: dict[str, Any]) -> None:
        self.conn.execute(
            "UPDATE heartbeat_log SET phase=?, status=?, decision=? WHERE id=?",
            ("complete", out["status"], json.dumps(out), hid),
        )
        self._heartbeat_inflight = None

    # --- backup / restart ---
    def backup(self, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(dest)) as other:
            self.conn.backup(other)

    @classmethod
    def restore(cls, src: Path) -> "CognitiveStore":
        store = cls(":memory:")
        with sqlite3.connect(str(src)) as src_conn:
            src_conn.backup(store.conn)
        return store


def apply_history(store: CognitiveStore, agent_id: str, history: str) -> None:
    """Apply matched deterministic histories H0–H8."""
    if history == "H0":
        for i in range(5):
            store.record_episode(agent_id, action="chat", outcome="neutral", content=f"neutral_{i}")
    elif history == "H1":
        for i in range(5):
            ep = store.record_episode(
                agent_id, action="play", outcome="success", content=f"object_A play success {i}"
            )
            store.bump_developed(agent_id, "pref_object_A", 0.15)
            store.bump_developed(agent_id, "approach_A", -0.05)
            store.bump_developed(agent_id, "pred_play", 0.1)
            store.assert_belief(agent_id, "object_A_is_fun", episode_ids=[ep])
    elif history == "H2":
        for i in range(5):
            ep = store.record_episode(
                agent_id, action="play", outcome="fail", content=f"object_A play fail {i}"
            )
            store.bump_developed(agent_id, "pref_object_A", -0.15)
            store.bump_developed(agent_id, "avoid_A", 0.15)
            store.bump_developed(agent_id, "approach_A", 0.08)
            store.assert_belief(agent_id, "object_A_is_fun", episode_ids=[ep], contradict=True)
    elif history == "H3":
        for i in range(5):
            ep = store.record_episode(
                agent_id, action="help", outcome="success", content=f"partner_P helped {i}"
            )
            store.bump_developed(agent_id, "rely_P", 0.18)
            store.assert_belief(agent_id, "partner_P_reliable", episode_ids=[ep])
    elif history == "H4":
        for i in range(5):
            ep = store.record_episode(
                agent_id, action="help", outcome="misleading", content=f"partner_P bad cue {i}"
            )
            store.bump_developed(agent_id, "rely_P", -0.18)
            store.assert_belief(agent_id, "partner_P_reliable", episode_ids=[ep], contradict=True)
    elif history == "H5":
        for i in range(3):
            ep = store.record_episode(
                agent_id, action="observe", outcome="A", content=f"world_fact_X true {i}"
            )
            store.assert_belief(agent_id, "world_fact_X", episode_ids=[ep], quality=0.9)
        for i in range(3):
            ep = store.record_episode(
                agent_id, action="observe", outcome="B", content=f"world_fact_X false {i}"
            )
            store.assert_belief(agent_id, "world_fact_X", episode_ids=[ep], contradict=True, quality=0.9)
        store.bump_developed(agent_id, "uncertainty", 0.3)
    elif history == "H6":
        for _ in range(6):
            store.upsert_procedure(agent_id, conditions="play_available", policy_ref="play_routine", success=True)
            store.bump_developed(agent_id, "proc_play", 0.1)
    elif history == "H7":
        for _ in range(6):
            store.upsert_procedure(agent_id, conditions="play_available", policy_ref="play_routine", success=False)
            store.bump_developed(agent_id, "proc_play", -0.1)
    elif history == "H8":
        ep1 = store.record_episode(agent_id, action="observe", outcome="wrong", content="sky is green")
        store.assert_belief(agent_id, "sky_is_green", episode_ids=[ep1])
        ep2 = store.record_episode(agent_id, action="correct", outcome="fix", content="sky is blue")
        store.correct_belief(agent_id, "sky_is_green", "sky_is_blue", [ep2])
        store.bump_developed(agent_id, "pref_object_A", 0.0)
    else:
        raise ValueError(history)


def matched_agent(store: CognitiveStore, suffix: str, seed: int = 42) -> str:
    aid = f"agent-{suffix}"
    store.register_agent(
        AgentSpec(
            agent_id=aid,
            lineage="newborn-v1",
            owner="operator-test",
            created_at=0.0,
            capabilities=frozenset({"perceive", "act_local"}),
            configured_name="UmbraProbe",
            big_five={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
            speaking_style="terse",
            seed=seed,
        )
    )
    return aid
