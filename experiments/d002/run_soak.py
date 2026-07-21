"""D-002 2-hour real-time soak at config.hz (default 2 Hz)."""

from __future__ import annotations

import json
import resource
import time
from pathlib import Path

from umbra_core.runtime import OrganismConfig, create_organism


def rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    work = root / ".soak" / "d002_soak"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "soak.sqlite"
    duration = float((__import__("os").environ.get("UMBRA_D002_SOAK_SECONDS", "7200")))
    cfg = OrganismConfig(db_path=str(db), seed=7, hz=2.0, snapshot_every=200)
    org = create_organism(cfg)
    t0 = time.monotonic()
    cpu0 = time.process_time()
    samples = []
    log_path = root / "docs/evidence/d002" / "soak-2h.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as log:
        while time.monotonic() - t0 < duration:
            period = 1.0 / cfg.hz
            s0 = time.monotonic()
            org.tick_once()
            elapsed = time.monotonic() - s0
            sleep_for = period - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
            if org.tick % 120 == 0:  # ~1/min at 2Hz
                sample = {
                    "tick": org.tick,
                    "wall_s": time.monotonic() - t0,
                    "rss_mib": rss_mib(),
                    "cpu_s": time.process_time() - cpu0,
                }
                samples.append(sample)
                log.write(json.dumps(sample) + "\n")
                log.flush()
    wall = time.monotonic() - t0
    cpu = time.process_time() - cpu0
    org.snapshot_if_due(force=True)
    summary = {
        "duration_s": wall,
        "ticks": org.tick,
        "cpu_mean_pct": 100.0 * cpu / max(wall, 1e-6),
        "rss_p95_mib": sorted(s["rss_mib"] for s in samples)[int(0.95 * (len(samples) - 1))] if samples else rss_mib(),
        "rss_first": samples[0]["rss_mib"] if samples else None,
        "rss_last": samples[-1]["rss_mib"] if samples else None,
        "rss_slope_mib_per_h": (
            (samples[-1]["rss_mib"] - samples[0]["rss_mib"]) / max((samples[-1]["wall_s"] - samples[0]["wall_s"]) / 3600.0, 1e-9)
            if len(samples) >= 2
            else 0.0
        ),
        "db_mib": db.stat().st_size / (1024 * 1024),
        "agent_id": org.identity.agent_id,
        "body_schema_id": org.self_model.active.body_schema_id if org.self_model else None,
        "gate9_pass": None,
    }
    summary["gate9_pass"] = (
        summary["duration_s"] >= duration * 0.99
        and summary["cpu_mean_pct"] <= 5.0
        and summary["rss_p95_mib"] <= 100.0
        and summary["rss_slope_mib_per_h"] <= 1.0
    )
    org.close()
    (root / "docs/evidence/d002" / "soak-2h-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
