"""D-002P Phase 1 — attribute RSS / structure growth across time windows.

Runs a wall-clock profile (default 30 min; set UMBRA_D002P_PROFILE_SECONDS).
Does not change organism behavior; diagnostic only.
"""

from __future__ import annotations

import gc
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.runtime import OrganismConfig, create_organism  # noqa: E402
from umbra_core.util import current_rss_mib  # noqa: E402


WINDOWS = (
    (0, 600, "0-10min"),
    (600, 1800, "10-30min"),
    (1800, 3600, "30-60min"),
    (3600, 7200, "60-120min"),
)


def _struct_sizes(org: Any) -> dict[str, int]:
    sm = org.self_model
    return {
        "metrics.cells": len(org.metrics.get("cells", ())),
        "metrics.prediction_errors": len(org.metrics.get("prediction_errors", [])),
        "arbitration.visited_cells": len(org.arbitrator.state.visited_cells),
        "perception.observations": len(org.perception.observations),
        "sm.predictions": len(sm.predictions) if sm else 0,
        "sm.errors": len(sm.errors) if sm else 0,
        "sm.attributions": len(sm.attributions) if sm else 0,
        "sm.change_evidence": len(sm.change_evidence) if sm else 0,
        "sm.supersessions": len(sm.supersessions) if sm else 0,
        "sm.archive": len(sm.archive) if sm else 0,
        "sm._obs_range_window": len(sm._obs_range_window) if sm else 0,
        "db_events": org.store.last_sequence(),
        "db_snapshots": int(
            org.store.conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        ),
        "db_bytes": Path(org.store.path).stat().st_size,
    }


def _top_tracemalloc(n: int = 15) -> list[dict[str, Any]]:
    snap = tracemalloc.take_snapshot()
    stats = snap.statistics("lineno")[:n]
    out = []
    for s in stats:
        out.append(
            {
                "size_kib": round(s.size / 1024, 2),
                "count": s.count,
                "traceback": str(s.traceback),
            }
        )
    return out


def main() -> None:
    duration = float(os.environ.get("UMBRA_D002P_PROFILE_SECONDS", "1800"))
    sample_interval = float(os.environ.get("UMBRA_D002P_PROFILE_INTERVAL", "30"))
    work = ROOT / ".soak" / "d002p_profile"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "profile.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    gc.collect()
    tracemalloc.start(25)
    cfg = OrganismConfig(db_path=str(db), seed=7, hz=2.0, snapshot_every=200)
    org = create_organism(cfg)
    t0 = time.monotonic()
    samples: list[dict[str, Any]] = []
    next_sample = t0
    period = 1.0 / cfg.hz

    while time.monotonic() - t0 < duration:
        s0 = time.monotonic()
        org.tick_once()
        elapsed = time.monotonic() - s0
        sleep_for = period - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)
        now = time.monotonic()
        if now >= next_sample:
            wall = now - t0
            sizes = _struct_sizes(org)
            samples.append(
                {
                    "wall_s": wall,
                    "tick": org.tick,
                    "vmrss_mib": current_rss_mib(),
                    "structures": sizes,
                    "tracemalloc_top": _top_tracemalloc(8),
                }
            )
            next_sample = now + sample_interval

    org.snapshot_if_due(force=True)
    final = _struct_sizes(org)
    org.close()
    tracemalloc.stop()

    # Window deltas
    window_summaries = []
    for start, end, label in WINDOWS:
        if start >= duration:
            break
        win = [s for s in samples if start <= s["wall_s"] < min(end, duration)]
        if len(win) < 2:
            continue
        rss0, rss1 = win[0]["vmrss_mib"], win[-1]["vmrss_mib"]
        hours = (win[-1]["wall_s"] - win[0]["wall_s"]) / 3600.0
        slope = (rss1 - rss0) / hours if hours > 0 else 0.0
        s0, s1 = win[0]["structures"], win[-1]["structures"]
        growth = {k: s1[k] - s0[k] for k in s0}
        window_summaries.append(
            {
                "window": label,
                "n_samples": len(win),
                "rss_start_mib": rss0,
                "rss_end_mib": rss1,
                "rss_delta_mib": rss1 - rss0,
                "approx_slope_mib_per_h": slope,
                "structure_deltas": growth,
            }
        )

    out = {
        "duration_s": duration,
        "sample_interval_s": sample_interval,
        "sample_count": len(samples),
        "rss_first_mib": samples[0]["vmrss_mib"] if samples else None,
        "rss_last_mib": samples[-1]["vmrss_mib"] if samples else None,
        "final_structures": final,
        "windows": window_summaries,
        "samples": samples,
    }
    dest = ROOT / "docs/evidence/d002p" / "memory-profile.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in out if k != "samples"}, indent=2))


if __name__ == "__main__":
    main()
