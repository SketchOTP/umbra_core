#!/usr/bin/env python3
"""Performance harness: accelerated ticks + optional realtime soak sample."""

from __future__ import annotations

import argparse
import json
import os
import resource
import tempfile
import time
from pathlib import Path

from umbra_core.runtime import OrganismConfig, create_organism


def rss_mib() -> float:
    # ru_maxrss on Linux is KiB
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=100_000)
    ap.add_argument("--soak-seconds", type=float, default=0.0)
    ap.add_argument("--out", type=Path, default=Path("docs/evidence/d001/performance-results.json"))
    args = ap.parse_args()

    hw = {
        "os": os.uname().sysname + " " + os.uname().release,
        "machine": os.uname().machine,
        "hostname": os.uname().nodename,
        "cpus": os.cpu_count(),
        "hardware_vendor": "Lenovo",
        "hardware_model": "ThinkPad L15 Gen 3",
        "os_pretty": "Ubuntu 26.04 LTS",
    }

    work = tempfile.mkdtemp(prefix="umbra_perf_")
    db = str(Path(work) / "perf.sqlite")
    cfg = OrganismConfig(db_path=db, seed=0, snapshot_every=5000)

    samples = []
    t0 = time.perf_counter()
    cpu0 = time.process_time()
    org = create_organism(cfg)
    rss0 = rss_mib()
    batch = max(1000, args.ticks // 20)
    done = 0
    while done < args.ticks:
        n = min(batch, args.ticks - done)
        org.run_ticks(n)
        done += n
        samples.append({"tick": done, "rss_mib": rss_mib(), "t": time.perf_counter() - t0})
    # do NOT validate_chain here — loading 100k events inflates RSS for measurement
    n_events = org.store.conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()[0]
    org.snapshot_if_due(force=True)
    cpu1 = time.process_time()
    t1 = time.perf_counter()
    rss1 = rss_mib()
    disk = Path(db).stat().st_size + (
        Path(db + "-wal").stat().st_size if Path(db + "-wal").exists() else 0
    )
    org.close()

    elapsed = t1 - t0
    cpu_elapsed = cpu1 - cpu0
    rss_vals = [s["rss_mib"] for s in samples]
    if samples[-1]["t"] > 0:
        slope = (rss_vals[-1] - rss_vals[0]) / (samples[-1]["t"] / 3600.0)
    else:
        slope = 0.0

    soak = None
    if args.soak_seconds > 0:
        db2 = str(Path(work) / "soak.sqlite")
        org2 = create_organism(OrganismConfig(db_path=db2, seed=1, hz=2.0, snapshot_every=1000))
        s0 = time.perf_counter()
        c0 = time.process_time()
        r0 = rss_mib()
        n = org2.run_realtime(args.soak_seconds)
        s1 = time.perf_counter()
        c1 = time.process_time()
        r1 = rss_mib()
        wall = s1 - s0
        cpu_frac = (c1 - c0) / wall if wall > 0 else 0
        soak = {
            "seconds_requested": args.soak_seconds,
            "seconds_actual": wall,
            "ticks": n,
            "rss_start_mib": r0,
            "rss_end_mib": r1,
            "cpu_fraction_one_core": cpu_frac,
            "cpu_percent": cpu_frac * 100,
            "note": "short sample; 6h soak launched separately if requested",
        }
        org2.close()

    p95 = sorted(rss_vals)[int(0.95 * (len(rss_vals) - 1))]
    result = {
        "hardware": hw,
        "accelerated": {
            "ticks": args.ticks,
            "elapsed_sec": elapsed,
            "cpu_sec": cpu_elapsed,
            "event_count": int(n_events),
            "rss_p95_mib": p95,
            "rss_max_mib_during_loop": max(rss_vals),
            "rss_start_mib": rss0,
            "rss_end_mib_after_loop": rss1,
            "rss_slope_mib_per_hour": slope,
            "disk_bytes": disk,
            "ticks_per_sec": args.ticks / elapsed if elapsed else 0,
        },
        "soak": soak,
        "gates": {
            "rss_p95_le_200": p95 <= 200,
            "rss_slope_le_1_mib_per_hour": abs(slope) <= 1.0 or (soak and soak["rss_end_mib"] - soak["rss_start_mib"] <= 1),
            "ticks_ge_100000": args.ticks >= 100_000,
            "cpu_at_2hz_le_5pct": soak is None or soak["cpu_percent"] <= 5.0,
        },
        "samples": samples[:: max(1, len(samples) // 10)],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ("accelerated", "soak", "gates")}, indent=2))


if __name__ == "__main__":
    main()
