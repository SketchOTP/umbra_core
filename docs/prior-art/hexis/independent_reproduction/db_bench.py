"""Measured SQLite vs lightweight ledger benchmarks for Track 3 database decision."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from store import CognitiveStore, apply_history, matched_agent


def _measure_sqlite(n_writes: int = 2000) -> dict:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "bench.sqlite"
        s = CognitiveStore(path)
        aid = matched_agent(s, "bench")
        t0 = time.perf_counter()
        for i in range(n_writes):
            s.record_episode(aid, action="a", outcome="o", content=f"row-{i}")
        write_s = time.perf_counter() - t0
        t1 = time.perf_counter()
        for _ in range(100):
            s.conn.execute("SELECT COUNT(*) FROM episodic WHERE agent_id=?", (aid,)).fetchone()
        read_s = time.perf_counter() - t1
        # restart recovery
        s.close()
        t2 = time.perf_counter()
        s2 = CognitiveStore(path)
        n = s2.conn.execute("SELECT COUNT(*) AS c FROM episodic").fetchone()["c"]
        open_s = time.perf_counter() - t2
        bak = Path(td) / "bak.sqlite"
        t3 = time.perf_counter()
        s2.backup(bak)
        bak_s = time.perf_counter() - t3
        size = path.stat().st_size
        s2.close()
        return {
            "engine": "sqlite_wal",
            "writes": n_writes,
            "write_seconds": round(write_s, 4),
            "read_100_seconds": round(read_s, 4),
            "reopen_seconds": round(open_s, 4),
            "backup_seconds": round(bak_s, 4),
            "rows_after_restart": n,
            "file_bytes": size,
            "background_services": 0,
            "installation_complexity": "single_file",
            "offline_operation": True,
            "robot_deployment_fit": "high",
        }


def _postgres_proxy_notes() -> dict:
    """No live Postgres required for decision evidence; record operational dimensions."""
    return {
        "engine": "postgresql_hexis_style",
        "measured_locally": False,
        "writes": None,
        "background_services": "postgres + extensions (AGE, pgvector) + workers",
        "installation_complexity": "container_stack",
        "offline_operation": "possible_but_heavy",
        "robot_deployment_fit": "low_for_standalone_pet",
        "transactional_integrity": "excellent",
        "graph_queries": "native_via_AGE",
        "vector_search": "native_via_pgvector",
        "notes": "Hexis treats Postgres as cognitive authority; UMBRA standalone companion favors embedded authority.",
    }


def run_benchmark(out_path: Path) -> dict:
    sqlite_m = _measure_sqlite()
    pg = _postgres_proxy_notes()
    hybrid = {
        "engine": "hybrid_sqlite_ledger_plus_optional_indexes",
        "transactional_integrity": "sqlite_wal_primary",
        "optional_external_indexes": ["vector", "graph"],
        "robot_deployment_fit": "high",
        "scale_path": "optional Postgres tier if multi-writer cloud needed",
    }
    result = {
        "track": "UMBRA-D-000-track3",
        "measurements": {"sqlite": sqlite_m, "postgresql": pg, "hybrid": hybrid},
        "sqlite": sqlite_m,
        "selected_classification": "HYBRID_PRIMARY",
        "rationale": (
            "Measured SQLite WAL sustains thousands of episodic writes with restart/backup "
            "on a single file and zero background services. Hexis PostgreSQL+AGE+pgvector is "
            "excellent for multi-service cognitive servers but is not required for a standalone "
            "Linux companion. Recommend SQLite (or equivalent embedded ledger) as primary "
            "authority with optional external indexes as a scale tier — not Postgres-as-brain."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    run_benchmark(root / "docs/evidence/d000-track3/database-benchmark.json")
    print("OK database-benchmark.json")
