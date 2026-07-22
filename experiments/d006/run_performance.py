"""D-006 performance: 100k accelerated ticks + RUNTIME_READY-anchored 2h VmRSS soak.

Modeled on experiments/d005/run_performance.py but with social_enabled=True (memory
and world model on, social_history H0). Thresholds come from the frozen
experiments/d006/thresholds.json (rss_p95<=180 MiB, slope<=1.0 MiB/h, cpu<=0.05 frac).

Modes (env D006_PERF_MODE): "100k", "soak", or "all"/"combine". Each mode writes its own
artifact and then recomposes docs/evidence/d006/performance-results.json from whatever
100k / soak artifacts exist on disk, so the long soak can run in the background in parallel
with seal preparation.
"""

from __future__ import annotations

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

OUT = ROOT / "docs/evidence/d006"


def thresholds() -> tuple[float, float, float]:
    t = json.loads((ROOT / "experiments/d006/thresholds.json").read_text())
    return (
        float(t["rss_p95_mib_max"]),
        float(t["rss_slope_mib_per_hour_max"]),
        float(t["cpu_mean_frac_max"]),
    )


def run_100k(db: Path) -> dict:
    cfg = OrganismConfig(
        db_path=str(db),
        seed=42,
        snapshot_every=500,
        social_enabled=True,
        memory_enabled=True,
        world_model_enabled=True,
        social_history="H0",
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
    social_state = org.social.accepted_state()
    bounded = org.memory.counts_bounded() and org.social.counts_bounded()
    org.close()
    org2 = load_organism(
        OrganismConfig(
            db_path=str(db),
            seed=42,
            social_enabled=True,
            memory_enabled=True,
            world_model_enabled=True,
        )
    )
    ok = (
        org2.identity.agent_id == aid
        and len(org2.memory.episodes) == n_ep
        and org2.social.accepted_state() == social_state
    )
    org2.close()
    rss_vals = sorted(s["rss_mib"] for s in samples)
    return {
        "ticks": n,
        "elapsed_s": elapsed,
        "cpu_s": cpu,
        "cpu_frac_of_one_core": cpu / max(elapsed, 1e-6),
        "rss_p95_mib": rss_vals[int(0.95 * (len(rss_vals) - 1))],
        "rss_samples": samples,
        "db_mib": db.stat().st_size / (1024 * 1024),
        "restart_continuity": ok,
        "counts_bounded": bounded,
    }


def run_soak(duration_s: float, sample_interval: float = 30.0) -> dict:
    rss_max, slope_max, cpu_max = thresholds()
    work = ROOT / ".soak" / "d006_soak"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "soak.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    cfg = OrganismConfig(
        db_path=str(db),
        seed=7,
        hz=2.0,
        snapshot_every=200,
        social_enabled=True,
        memory_enabled=True,
        world_model_enabled=True,
        social_history="H0",
    )
    org = create_organism(cfg)
    t_ready = time.time()  # RUNTIME_READY anchor: after birth/warm, before measurement
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
            samples.append({"t": now - t_ready, "rss_mib": current_rss_mib(), "tick": org.tick})
            next_sample += sample_interval
        sleep_for = period - (time.monotonic() - t0)
        if sleep_for > 0:
            time.sleep(sleep_for)
    elapsed = time.time() - t_ready
    cpu = time.process_time() - cpu0
    org.snapshot_if_due(force=True)
    bounded = org.memory.counts_bounded() and org.social.counts_bounded()
    org.close()

    xs = [s["t"] / 3600.0 for s in samples]
    ys = [s["rss_mib"] for s in samples]
    slope = ols_slope(xs, ys)
    rss_vals = sorted(ys)
    p95 = rss_vals[int(0.95 * (len(rss_vals) - 1))]
    cpu_frac = cpu / max(elapsed, 1e-6)
    gate = (
        elapsed >= duration_s * 0.99
        and p95 <= rss_max
        and slope <= slope_max
        and cpu_frac <= cpu_max
        and bounded
    )
    return {
        "duration_s": elapsed,
        "cpu_mean_frac": cpu_frac,
        "cpu_mean_pct": cpu_frac * 100.0,
        "rss_p95_mib": p95,
        "rss_slope_mib_per_hour": slope,
        "samples": samples,
        "counts_bounded": bounded,
        "gate_soak_pass": gate,
        "db_mib": db.stat().st_size / (1024 * 1024),
    }


def write_combined() -> dict:
    rss_max, slope_max, cpu_max = thresholds()
    results: dict = {
        "thresholds": {
            "rss_p95_mib_max": rss_max,
            "rss_slope_mib_per_hour_max": slope_max,
            "cpu_mean_frac_max": cpu_max,
        }
    }
    k_path = OUT / "performance-100k.json"
    s_path = OUT / "soak-2h-summary.json"
    k_pass = None
    s_pass = None
    if k_path.exists():
        k = json.loads(k_path.read_text())
        k_pass = (
            k["rss_p95_mib"] <= rss_max
            and k["counts_bounded"]
            and k["restart_continuity"]
        )
        results["performance_100k"] = {kk: vv for kk, vv in k.items() if kk != "rss_samples"}
        results["gate_100k_pass"] = k_pass
    if s_path.exists():
        s = json.loads(s_path.read_text())
        s_pass = bool(s.get("gate_soak_pass"))
        results["soak"] = s
        results["gate_soak_pass"] = s_pass
        results["rss_p95_mib"] = s["rss_p95_mib"]
        results["rss_slope_mib_per_hour"] = s["rss_slope_mib_per_hour"]
        results["cpu_mean_frac"] = s["cpu_mean_frac"]
        results["cpu_mean_pct"] = s["cpu_mean_pct"]
        results["duration_s"] = s["duration_s"]
        results["counts_bounded"] = s["counts_bounded"]
    if k_pass is not None and s_pass is not None:
        results["gate_performance_pass"] = bool(k_pass and s_pass)
    (OUT / "performance-results.json").write_text(json.dumps(results, indent=2, sort_keys=True))
    return results


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mode = os.environ.get("D006_PERF_MODE", "all")

    if mode in ("all", "100k"):
        work = ROOT / ".soak" / "d006_perf"
        work.mkdir(parents=True, exist_ok=True)
        db = work / "perf100k.sqlite"
        for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
            p.unlink(missing_ok=True)
        print("running 100k...", flush=True)
        k = run_100k(db)
        (OUT / "performance-100k.json").write_text(json.dumps(k, indent=2, sort_keys=True))

    if mode in ("all", "soak"):
        dur = float(os.environ.get("D006_SOAK_SECONDS", "7200"))
        print(f"running soak {dur}s...", flush=True)
        soak = run_soak(dur)
        (OUT / "soak-2h-summary.json").write_text(
            json.dumps({k: v for k, v in soak.items() if k != "samples"}, indent=2, sort_keys=True)
        )
        with (OUT / "soak-2h.jsonl").open("w") as f:
            for s in soak["samples"]:
                f.write(json.dumps(s) + "\n")

    results = write_combined()
    print(json.dumps({k: results.get(k) for k in (
        "gate_performance_pass", "gate_100k_pass", "gate_soak_pass",
        "rss_p95_mib", "rss_slope_mib_per_hour", "cpu_mean_frac",
        "duration_s", "counts_bounded",
    ) if k in results}, indent=2))


if __name__ == "__main__":
    main()
