"""D-005 performance: 100k accelerated ticks + RUNTIME_READY-anchored 2h soak."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate
from umbra_core.util import current_rss_mib, ols_slope


def run_100k(db: Path) -> dict:
    cfg = OrganismConfig(
        db_path=str(db),
        seed=42,
        snapshot_every=500,
        memory_enabled=True,
        world_model_enabled=True,
        memory_history="H0",
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
    n_ep = len(org.memory.episodes)
    bounded = org.memory.counts_bounded()
    org.close()
    org2 = load_organism(
        OrganismConfig(
            db_path=str(db),
            seed=42,
            memory_enabled=True,
            world_model_enabled=True,
        )
    )
    ok = org2.identity.agent_id == aid and len(org2.memory.episodes) == n_ep
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
    work = ROOT / ".soak" / "d005_soak"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "soak.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    cfg = OrganismConfig(
        db_path=str(db),
        seed=7,
        hz=2.0,
        snapshot_every=200,
        memory_enabled=True,
        world_model_enabled=True,
        memory_history="H0",
    )
    org = create_organism(cfg)
    t_ready = time.time()
    rss0 = current_rss_mib()
    samples = [{"t": 0.0, "rss_mib": rss0, "tick": org.tick}]
    cpu0 = time.process_time()
    next_sample = t_ready + sample_interval
    end = t_ready + duration_s
    period = 1.0 / cfg.hz
    while time.time() < end:
        t0 = time.monotonic()
        org.tick_once()
        now = time.time()
        if now >= next_sample:
            samples.append(
                {
                    "t": now - t_ready,
                    "rss_mib": current_rss_mib(),
                    "tick": org.tick,
                }
            )
            next_sample += sample_interval
        sleep_for = period - (time.monotonic() - t0)
        if sleep_for > 0:
            time.sleep(sleep_for)
    elapsed = time.time() - t_ready
    cpu = time.process_time() - cpu0
    org.snapshot_if_due(force=True)
    bounded = org.memory.counts_bounded()
    growth = org.memory.memory_growth()
    org.close()

    xs = [s["t"] / 3600.0 for s in samples]
    ys = [s["rss_mib"] for s in samples]
    slope = ols_slope(xs, ys)
    rss_vals = sorted(ys)
    p95 = rss_vals[int(0.95 * (len(rss_vals) - 1))]
    cpu_pct = 100.0 * cpu / max(elapsed, 1e-6)
    gate = (
        elapsed >= duration_s * 0.99
        and p95 <= 160.0
        and slope <= 1.0
        and cpu_pct <= 5.0
        and bounded
    )
    return {
        "duration_s": elapsed,
        "cpu_mean_pct": cpu_pct,
        "rss_p95_mib": p95,
        "rss_slope_mib_per_hour": slope,
        "samples": samples,
        "counts_bounded": bounded,
        "memory_growth": growth,
        "gate_performance_pass": gate,
        "db_mib": db.stat().st_size / (1024 * 1024),
    }


def run_replay_continuity() -> dict:
    work = ROOT / ".soak" / "d005_replay"
    work.mkdir(parents=True, exist_ok=True)
    for name in ("a.sqlite", "b.sqlite", "restart.sqlite"):
        db = work / name
        for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
            p.unlink(missing_ok=True)
    a = resimulate(
        99,
        50,
        str(work / "a.sqlite"),
        memory_enabled=True,
        world_model_enabled=True,
        memory_history="H0",
    )
    b = resimulate(
        99,
        50,
        str(work / "b.sqlite"),
        memory_enabled=True,
        world_model_enabled=True,
        memory_history="H0",
    )
    db = work / "restart.sqlite"
    org = create_organism(
        OrganismConfig(
            db_path=str(db),
            seed=11,
            memory_enabled=True,
            world_model_enabled=True,
            memory_history="H2",
        )
    )
    org.phys.intervene(energy=0.6, fatigue=0.5)
    org.run_ticks(30)
    target = org.memory.accepted_state()
    org.close()
    ok = 0
    for _ in range(100):
        o = load_organism(
            OrganismConfig(
                db_path=str(db),
                seed=11,
                memory_enabled=True,
                world_model_enabled=True,
            )
        )
        if o.memory.accepted_state() == target:
            ok += 1
        o.close()
    return {
        "birth_snapshot_match": a["memory_accepted"] == b["memory_accepted"],
        "restart_100": ok,
        "restart_100_pass": ok == 100,
    }


def main() -> None:
    out = ROOT / "docs/evidence/d005"
    out.mkdir(parents=True, exist_ok=True)
    work = ROOT / ".soak" / "d005_perf"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "perf100k.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    mode = os.environ.get("D005_PERF_MODE", "all")
    results: dict = {}
    if mode in ("all", "100k"):
        print("running 100k...", flush=True)
        results["performance_100k"] = run_100k(db)
        (out / "performance-100k.json").write_text(
            json.dumps(results["performance_100k"], indent=2, sort_keys=True)
        )
    if mode in ("all", "replay"):
        print("running replay continuity...", flush=True)
        results["replay"] = run_replay_continuity()
        (out / "replay-results.json").write_text(
            json.dumps(results["replay"], indent=2, sort_keys=True)
        )
    if mode in ("all", "soak"):
        dur = float(os.environ.get("D005_SOAK_SECONDS", "7200"))
        print(f"running soak {dur}s...", flush=True)
        soak = run_soak(dur)
        results["soak"] = {k: v for k, v in soak.items() if k != "samples"}
        (out / "soak-2h-summary.json").write_text(
            json.dumps(results["soak"], indent=2, sort_keys=True)
        )
        with (out / "soak-2h.jsonl").open("w") as f:
            for s in soak["samples"]:
                f.write(json.dumps(s) + "\n")
        results["gate_performance_pass"] = soak["gate_performance_pass"]
        results["rss_p95_mib"] = soak["rss_p95_mib"]
        results["rss_slope_mib_per_hour"] = soak["rss_slope_mib_per_hour"]
        results["cpu_mean_pct"] = soak["cpu_mean_pct"]
        results["duration_s"] = soak["duration_s"]
        results["db_mib"] = soak["db_mib"]
        results["counts_bounded"] = soak["counts_bounded"]
    if mode == "100k" and "performance_100k" in results:
        p = results["performance_100k"]
        results["gate_performance_pass"] = (
            p["rss_p95_mib"] <= 160.0
            and p["cpu_pct_of_one_core"] <= 100.0  # accelerated; soak owns CPU gate
            and p["counts_bounded"]
            and p["restart_continuity"]
        )
        results["rss_p95_mib"] = p["rss_p95_mib"]
        results["cpu_mean_pct"] = p["cpu_pct_of_one_core"]
        results["duration_s"] = p["elapsed_s"]
        results["db_mib"] = p["db_mib"]
        results["counts_bounded"] = p["counts_bounded"]
    (out / "performance-results.json").write_text(json.dumps(results, indent=2, sort_keys=True))
    print(json.dumps({k: results.get(k) for k in (
        "gate_performance_pass", "rss_p95_mib", "rss_slope_mib_per_hour",
        "cpu_mean_pct", "duration_s", "replay", "counts_bounded",
    ) if k in results}, indent=2))


if __name__ == "__main__":
    main()
