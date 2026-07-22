"""D-003 performance: 100k accelerated ticks + RUNTIME_READY-anchored 2h soak."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.util import current_rss_mib, ols_slope


def run_100k(db: Path) -> dict:
    cfg = OrganismConfig(
        db_path=str(db),
        seed=42,
        snapshot_every=500,
        world_model_enabled=True,
        world_intervention="I0",
    )
    org = create_organism(cfg)
    samples = []
    t0 = time.time()
    cpu0 = time.process_time()
    n = 100_000
    for i in range(n):
        org.tick_once()
        if i % 5000 == 0:
            samples.append({"tick": i, "rss_mib": current_rss_mib(), "t": time.time() - t0})
    elapsed = time.time() - t0
    cpu = time.process_time() - cpu0
    org.snapshot_if_due(force=True)
    aid = org.identity.agent_id
    n_models = len(org.world_model.models)
    bounded = org.world_model.counts_bounded()
    org.close()
    org2 = load_organism(
        OrganismConfig(db_path=str(db), seed=42, world_model_enabled=True)
    )
    ok = org2.identity.agent_id == aid and len(org2.world_model.models) == n_models
    org2.close()
    rss_vals = sorted(s["rss_mib"] for s in samples)
    return {
        "ticks": n,
        "elapsed_s": elapsed,
        "cpu_s": cpu,
        "cpu_pct_of_one_core": 100.0 * cpu / max(elapsed, 1e-6),
        "rss_p95_mib": rss_vals[int(0.95 * (len(rss_vals) - 1))],
        "rss_samples": samples,
        "db_mib": db.stat().st_size / (1024 * 1024),
        "restart_continuity": ok,
        "counts_bounded": bounded,
    }


def run_soak(duration_s: float, sample_interval: float = 30.0) -> dict:
    work = ROOT / ".soak" / "d003_soak"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "soak.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    cfg = OrganismConfig(
        db_path=str(db),
        seed=7,
        hz=2.0,
        snapshot_every=200,
        world_model_enabled=True,
        world_intervention="I0",
    )
    org = create_organism(cfg)
    ready = [e for e in org.store.iter_events() if e["event_type"] == "runtime_ready"]
    assert len(ready) == 1

    t0 = time.monotonic()
    cpu0 = time.process_time()
    samples: list[dict] = []
    next_sample = t0
    log_path = ROOT / "docs/evidence/d003" / "soak-2h.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as log:
        while True:
            now = time.monotonic()
            if now - t0 >= duration_s:
                break
            org.tick_once()
            if now >= next_sample:
                rss = current_rss_mib()
                row = {
                    "t_s": now - t0,
                    "tick": org.tick,
                    "rss_mib": rss,
                    "cpu_s": time.process_time() - cpu0,
                }
                samples.append(row)
                log.write(json.dumps(row) + "\n")
                log.flush()
                next_sample = now + sample_interval
            # real-time pacing ~2 Hz
            time.sleep(max(0.0, 0.5 - (time.monotonic() - now)))

    elapsed = time.monotonic() - t0
    cpu = time.process_time() - cpu0
    xs = [s["t_s"] / 3600.0 for s in samples]
    ys = [s["rss_mib"] for s in samples]
    slope = ols_slope(xs, ys) if len(xs) >= 2 else 0.0
    rss_sorted = sorted(ys)
    p95 = rss_sorted[int(0.95 * (len(rss_sorted) - 1))] if rss_sorted else 0.0
    bounded = org.world_model.counts_bounded()
    org.close()
    return {
        "duration_s": elapsed,
        "samples": len(samples),
        "cpu_mean_pct": 100.0 * cpu / max(elapsed, 1e-6),
        "rss_p95_mib": p95,
        "rss_slope_mib_per_h": slope,
        "counts_bounded": bounded,
        "measurement_start": "first_persisted_RUNTIME_READY",
        "gate_performance_pass": (
            elapsed >= duration_s * 0.99
            and p95 <= 120.0
            and slope <= 1.0
            and (100.0 * cpu / max(elapsed, 1e-6)) <= 5.0
            and bounded
        ),
    }


def main() -> None:
    out_dir = ROOT / "docs/evidence/d003"
    out_dir.mkdir(parents=True, exist_ok=True)
    mode = os.environ.get("UMBRA_D003_PERF_MODE", "all")  # 100k | soak | all

    result: dict = {}
    if mode in ("100k", "all"):
        work = ROOT / ".soak" / "d003_perf"
        work.mkdir(parents=True, exist_ok=True)
        db = work / "perf_100k.sqlite"
        for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
            p.unlink(missing_ok=True)
        k = run_100k(db)
        (out_dir / "performance-100k.json").write_text(
            json.dumps({kk: vv for kk, vv in k.items() if kk != "rss_samples"}, indent=2)
            + "\n"
        )
        result["100k"] = {kk: vv for kk, vv in k.items() if kk != "rss_samples"}

    if mode in ("soak", "all"):
        duration = float(os.environ.get("UMBRA_D003_SOAK_SECONDS", "7200"))
        soak = run_soak(duration)
        result["soak"] = soak
        perf = {
            "duration_s": soak["duration_s"],
            "cpu_mean_pct": soak["cpu_mean_pct"],
            "rss_p95_mib": soak["rss_p95_mib"],
            "rss_slope_mib_per_h": soak["rss_slope_mib_per_h"],
            "counts_bounded": soak["counts_bounded"],
            "measurement_start": soak["measurement_start"],
            "gate_performance_pass": soak["gate_performance_pass"],
            "100k": result.get("100k"),
            "method": "current_VmRSS from first RUNTIME_READY",
        }
        (out_dir / "performance-results.json").write_text(json.dumps(perf, indent=2) + "\n")
        (out_dir / "soak-2h-summary.json").write_text(json.dumps(soak, indent=2) + "\n")

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
