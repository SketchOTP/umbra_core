"""D-002V 2h soak — current VmRSS full-window OLS slope (method frozen before run)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.util import current_rss_mib, ols_slope, peak_rss_mib


ROOT = Path(__file__).resolve().parents[2]
METHOD_PATH = ROOT / "docs/evidence/d002v/method-preregistration.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    method = json.loads(METHOD_PATH.read_text())
    assert method["metric"] == "current_VmRSS"
    assert method["window"] == "full_run"
    assert method["warmup_policy"].startswith("none")
    assert method["regression_method"] == "ordinary_least_squares_slope"
    assert method["sample_interval_s"] == 10
    assert method["outlier_handling"] == "none"

    duration = float(os.environ.get("UMBRA_D002V_SOAK_SECONDS", str(method["duration_s"])))
    sample_interval = float(method["sample_interval_s"])
    thr = method["pass_thresholds"]

    work = ROOT / ".soak" / "d002v_soak"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "soak.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    cfg = OrganismConfig(db_path=str(db), seed=7, hz=2.0, snapshot_every=200)
    org = create_organism(cfg)
    t0 = time.monotonic()
    cpu0 = time.process_time()
    samples: list[dict] = []
    next_sample = t0
    log_path = ROOT / "docs/evidence/d002v" / "soak-2h.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    crashed = False
    try:
        with log_path.open("w") as log:
            while time.monotonic() - t0 < duration:
                period = 1.0 / cfg.hz
                s0 = time.monotonic()
                org.tick_once()
                elapsed = time.monotonic() - s0
                sleep_for = period - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)
                now = time.monotonic()
                if now >= next_sample:
                    wall_s = now - t0
                    sample = {
                        "tick": org.tick,
                        "wall_s": wall_s,
                        "vmrss_mib": current_rss_mib(),
                        "ru_maxrss_mib": peak_rss_mib(),  # diagnostic only — not Gate1 signal
                        "cpu_s": time.process_time() - cpu0,
                    }
                    samples.append(sample)
                    log.write(json.dumps(sample) + "\n")
                    log.flush()
                    next_sample = now + sample_interval
    except Exception:
        crashed = True
        raise
    finally:
        wall = time.monotonic() - t0
        cpu = time.process_time() - cpu0
        org.snapshot_if_due(force=True)
        agent_id = org.identity.agent_id
        body_schema_id = org.self_model.active.body_schema_id if org.self_model else None
        org.store.validate_chain()
        org.close()

    hours = [s["wall_s"] / 3600.0 for s in samples]
    vmrss = [s["vmrss_mib"] for s in samples]
    slope = ols_slope(hours, vmrss)
    rss_sorted = sorted(vmrss)
    p95 = rss_sorted[int(0.95 * (len(rss_sorted) - 1))] if rss_sorted else current_rss_mib()

    # Restart identity / snapshot continuity
    org2 = load_organism(OrganismConfig(db_path=str(db), seed=7, hz=2.0, snapshot_every=200))
    restart_ok = org2.identity.agent_id == agent_id and (
        org2.self_model is not None and org2.self_model.active.body_schema_id == body_schema_id
    )
    org2.store.validate_chain()
    org2.close()

    cpu_mean = 100.0 * cpu / max(wall, 1e-6)
    summary = {
        "method_path": str(METHOD_PATH.relative_to(ROOT)),
        "method_sha256": _sha256_file(METHOD_PATH),
        "git_commit": method["starting_commit"],
        "duration_s": wall,
        "ticks": samples[-1]["tick"] if samples else 0,
        "sample_count": len(samples),
        "sample_interval_s": sample_interval,
        "cpu_mean_pct": cpu_mean,
        "rss_p95_mib": p95,
        "rss_first_mib": vmrss[0] if vmrss else None,
        "rss_last_mib": vmrss[-1] if vmrss else None,
        "rss_slope_mib_per_h": slope,
        "rss_slope_method": "full_window_ols_vmrss",
        "db_mib": db.stat().st_size / (1024 * 1024),
        "agent_id": agent_id,
        "body_schema_id": body_schema_id,
        "crash_free": not crashed,
        "ledger_integrity": True,
        "identity_after_restart": restart_ok,
        "gate1_pass": (
            wall >= thr["duration_s_min"] * 0.99
            and cpu_mean <= thr["cpu_mean_pct_of_one_core_max"]
            and p95 <= thr["rss_p95_mib_max"]
            and slope <= thr["rss_slope_mib_per_h_max"]
            and not crashed
            and restart_ok
        ),
    }
    out = ROOT / "docs/evidence/d002v" / "performance-results.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    (ROOT / "docs/evidence/d002v" / "soak-2h-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
