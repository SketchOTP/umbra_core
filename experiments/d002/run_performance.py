"""D-002 performance: 100k accelerated ticks + optional real-time soak sample."""

from __future__ import annotations

import json
import os
import resource
import time
from pathlib import Path

from umbra_core.runtime import OrganismConfig, create_organism, load_organism


def rss_mib() -> float:
    # Linux: ru_maxrss is KiB
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def run_100k(db: Path) -> dict:
    cfg = OrganismConfig(db_path=str(db), seed=42, snapshot_every=500)
    org = create_organism(cfg)
    samples = []
    t0 = time.time()
    cpu0 = time.process_time()
    n = 100_000
    for i in range(n):
        org.tick_once()
        if i % 5000 == 0:
            samples.append({"tick": i, "rss_mib": rss_mib(), "t": time.time() - t0})
    elapsed = time.time() - t0
    cpu = time.process_time() - cpu0
    org.snapshot_if_due(force=True)
    # restart continuity probe
    aid = org.identity.agent_id
    sid = org.self_model.active.body_schema_id
    org.close()
    org2 = load_organism(OrganismConfig(db_path=str(db), seed=42))
    ok = org2.identity.agent_id == aid and org2.self_model.active.body_schema_id == sid
    org2.close()
    db_size = db.stat().st_size / (1024 * 1024)
    return {
        "ticks": n,
        "elapsed_s": elapsed,
        "cpu_s": cpu,
        "cpu_pct_of_one_core": 100.0 * cpu / max(elapsed, 1e-6),
        "rss_p95_mib": sorted(s["rss_mib"] for s in samples)[int(0.95 * (len(samples) - 1))],
        "rss_samples": samples,
        "db_mib": db_size,
        "restart_continuity": ok,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    work = root / ".soak" / "d002_perf"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "perf_100k.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)
    out = run_100k(db)
    dest = root / "docs/evidence/d002" / "performance-100k.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rss_samples"}, indent=2))


if __name__ == "__main__":
    main()
