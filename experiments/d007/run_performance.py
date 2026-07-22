"""D-007 Gate 13 performance: 100k accelerated ticks + 2h RUNTIME_READY VmRSS soak.

Modeled on experiments/d006/run_performance.py. Individuality + social + memory +
world enabled; individuality_history H0. Real-time soak sleeps to config.hz.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.util import current_rss_mib, ols_slope

OUT = ROOT / "docs/evidence/d007"
THR = json.loads((ROOT / "experiments/d007/thresholds.json").read_text())


def run_100k(db_path: str, seed: int = 42) -> dict:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)
    cfg = OrganismConfig(
        db_path=db_path,
        seed=seed,
        individuality_enabled=True,
        individuality_history="H0",
        memory_enabled=True,
        world_model_enabled=True,
        social_enabled=True,
        social_history="H0",
        snapshot_every=500,
        hz=2.0,
    )
    org = create_organism(cfg)
    assert org._runtime_ready
    samples = []
    t0 = time.time()
    cpu0 = time.process_time()
    n = int(THR["ticks_accelerated_min"])
    for i in range(n):
        org.tick_once()
        if i % 5000 == 0:
            samples.append({"tick": i, "rss_mib": current_rss_mib(), "t": time.time() - t0})
    elapsed = time.time() - t0
    cpu = time.process_time() - cpu0
    org.snapshot_if_due(force=True)
    fp_before = org.individuality.accepted_state() if org.individuality else None
    bounded = (
        org.individuality is not None
        and len(org.individuality.dispositions) <= THR["max_disposition_records"]
    )
    org.close()
    org2 = load_organism(cfg)
    fp_after = org2.individuality.accepted_state() if org2.individuality else None
    restart_ok = fp_before == fp_after
    org2.close()
    rss_vals = sorted(s["rss_mib"] for s in samples) or [current_rss_mib()]
    p95 = rss_vals[int(0.95 * (len(rss_vals) - 1))]
    out = {
        "ticks": n,
        "elapsed_s": elapsed,
        "cpu_s": cpu,
        "cpu_frac_of_one_core": cpu / max(elapsed, 1e-6),
        "rss_p95_mib": p95,
        "rss_samples": samples,
        "restart_continuity": restart_ok,
        "counts_bounded": bounded,
        "pass": (
            p95 <= THR["rss_p95_mib_max"]
            and restart_ok
            and bounded
            and n >= THR["ticks_accelerated_min"]
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "performance-100k.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def run_soak(db_path: str | None = None, seed: int = 7, seconds: float | None = None) -> dict:
    seconds = float(seconds if seconds is not None else THR["soak_seconds_min"])
    work = ROOT / ".soak" / "d007_soak"
    work.mkdir(parents=True, exist_ok=True)
    db = Path(db_path) if db_path else work / "soak.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    cfg = OrganismConfig(
        db_path=str(db),
        seed=seed,
        individuality_enabled=True,
        individuality_history="H0",
        memory_enabled=True,
        world_model_enabled=True,
        social_enabled=True,
        social_history="H0",
        snapshot_every=200,
        hz=2.0,
    )
    org = create_organism(cfg)
    assert org._runtime_ready
    t_ready = time.time()
    rss0 = current_rss_mib()
    samples = [{"t": 0.0, "rss_mib": rss0, "tick": org.tick}]
    cpu0 = time.process_time()
    sample_interval = 30.0
    next_sample = t_ready + sample_interval
    end = t_ready + seconds
    period = 1.0 / cfg.hz
    jsonl = OUT / "soak-2h.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    with jsonl.open("w") as log:
        log.write(json.dumps(samples[0]) + "\n")
        while time.time() < end:
            t0 = time.monotonic()
            org.tick_once()
            now = time.time()
            if now >= next_sample:
                row = {
                    "t": now - t_ready,
                    "rss_mib": current_rss_mib(),
                    "tick": org.tick,
                    "cpu_s": time.process_time() - cpu0,
                }
                samples.append(row)
                log.write(json.dumps(row) + "\n")
                log.flush()
                next_sample += sample_interval
            sleep_for = period - (time.monotonic() - t0)
            if sleep_for > 0:
                time.sleep(sleep_for)
    elapsed = time.time() - t_ready
    cpu = time.process_time() - cpu0
    org.snapshot_if_due(force=True)
    bounded = (
        org.individuality is not None
        and len(org.individuality.dispositions) <= THR["max_disposition_records"]
    )
    org.close()

    xs = [s["t"] / 3600.0 for s in samples]
    ys = [s["rss_mib"] for s in samples]
    slope = ols_slope(xs, ys) if len(xs) >= 2 else 0.0
    rss_vals = sorted(ys)
    p95 = rss_vals[int(0.95 * (len(rss_vals) - 1))]
    cpu_frac = cpu / max(elapsed, 1e-6)
    summary = {
        "duration_s": elapsed,
        "rss_p95_mib": p95,
        "rss_slope_mib_per_hour": slope,
        "cpu_mean_frac": cpu_frac,
        "counts_bounded": bounded,
        "n_samples": len(samples),
        "pass": (
            elapsed >= THR["soak_seconds_min"] * 0.99
            and p95 <= THR["rss_p95_mib_max"]
            and slope <= THR["rss_slope_mib_per_hour_max"]
            and cpu_frac <= THR["cpu_mean_frac_max"]
            and bounded
        ),
    }
    (OUT / "soak-2h-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return summary


def recompose(perf_100k: dict | None, soak: dict | None) -> dict:
    if perf_100k is None and (OUT / "performance-100k.json").exists():
        perf_100k = json.loads((OUT / "performance-100k.json").read_text())
    if soak is None and (OUT / "soak-2h-summary.json").exists():
        soak = json.loads((OUT / "soak-2h-summary.json").read_text())
    out = {
        "ticks_accelerated_min": THR["ticks_accelerated_min"],
        "soak_seconds_min": THR["soak_seconds_min"],
        "thresholds": {
            "rss_p95_mib_max": THR["rss_p95_mib_max"],
            "rss_slope_mib_per_hour_max": THR["rss_slope_mib_per_hour_max"],
            "cpu_mean_frac_max": THR["cpu_mean_frac_max"],
        },
        "100k": perf_100k,
        "soak": soak,
        "pass": bool((perf_100k or {}).get("pass")) and bool((soak or {}).get("pass")),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "performance-results.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n"
    )
    return out


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(parents=True, exist_ok=True)
    base = OUT / ".perf"
    base.mkdir(exist_ok=True)
    p100 = None
    soak = None
    if mode in ("100k", "all"):
        p100 = run_100k(str(base / "100k.db"))
        print("100k", p100["pass"], p100["rss_p95_mib"])
    if mode in ("soak", "all"):
        soak = run_soak()
        print("soak", soak["pass"], soak["rss_p95_mib"], soak["duration_s"], soak["cpu_mean_frac"])
    if mode == "combine":
        pass
    recompose(p100, soak)


if __name__ == "__main__":
    main()
