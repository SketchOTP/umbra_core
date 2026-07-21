"""D-002P 2h soak — VmRSS OLS from first RUNTIME_READY through shutdown."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.util import current_rss_mib, ols_slope, peak_rss_mib


ROOT = Path(__file__).resolve().parents[2]
METHOD_PATH = ROOT / "docs/evidence/d002p/method-preregistration.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    import subprocess

    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> None:
    method = json.loads(METHOD_PATH.read_text())
    assert method["metric"] == "current_VmRSS"
    assert method["measurement_start"] == "first_persisted_RUNTIME_READY_event"
    assert method["outlier_handling"] == "none"
    assert method["pass_thresholds"]["rss_slope_mib_per_h_max"] == 1.0
    assert method["no_steady_state_exemption"] is True
    assert method["runtime_ready_semantics"]["rss_gated"] is False

    duration = float(os.environ.get("UMBRA_D002P_SOAK_SECONDS", str(method["duration_s"])))
    sample_interval = float(method["sample_interval_s"])
    thr = method["pass_thresholds"]
    commit = _git_head()

    work = ROOT / ".soak" / "d002p_soak"
    work.mkdir(parents=True, exist_ok=True)
    db = work / "soak.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    source_paths = [
        ROOT / "umbra_core/runtime.py",
        ROOT / "umbra_core/events.py",
        ROOT / "umbra_core/util.py",
        ROOT / "umbra_core/persistence.py",
        ROOT / "umbra_core/self_model/engine.py",
        ROOT / "experiments/d002p/run_soak.py",
        METHOD_PATH,
    ]
    source_hashes = {str(p.relative_to(ROOT)): _sha256_file(p) for p in source_paths}
    config = {"seed": 7, "hz": 2.0, "snapshot_every": 200, "db": "new"}
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()

    cfg = OrganismConfig(db_path=str(db), seed=7, hz=2.0, snapshot_every=200)
    org = create_organism(cfg)
    ready_events = [e for e in org.store.iter_events() if e["event_type"] == "runtime_ready"]
    assert len(ready_events) == 1
    assert ready_events[0]["payload"]["rss_gated"] is False

    t0 = time.monotonic()  # measurement clock starts at RUNTIME_READY (already emitted)
    cpu0 = time.process_time()
    samples: list[dict] = []
    next_sample = t0
    log_path = ROOT / "docs/evidence/d002p" / "soak-2h.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Immediate sample at RUNTIME_READY boundary
    samples.append(
        {
            "tick": org.tick,
            "wall_s": 0.0,
            "vmrss_mib": current_rss_mib(),
            "ru_maxrss_mib": peak_rss_mib(),
            "cpu_s": 0.0,
            "at": "runtime_ready",
        }
    )

    crashed = False
    try:
        with log_path.open("w") as log:
            log.write(json.dumps(samples[0]) + "\n")
            log.flush()
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
                        "ru_maxrss_mib": peak_rss_mib(),
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
        body_hash = org.self_model.state_hash() if org.self_model else None
        bounds = {
            "predictions": len(org.self_model.predictions) if org.self_model else 0,
            "errors": len(org.self_model.errors) if org.self_model else 0,
            "attributions": len(org.self_model.attributions) if org.self_model else 0,
            "change_evidence": len(org.self_model.change_evidence) if org.self_model else 0,
            "cells": len(org.metrics["cells"]),
            "snapshots": int(
                org.store.conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
            ),
        }
        org.store.validate_chain()
        org.close()

    hours = [s["wall_s"] / 3600.0 for s in samples]
    vmrss = [s["vmrss_mib"] for s in samples]
    slope = ols_slope(hours, vmrss)
    rss_sorted = sorted(vmrss)
    p95 = rss_sorted[int(0.95 * (len(rss_sorted) - 1))] if rss_sorted else current_rss_mib()

    org2 = load_organism(OrganismConfig(db_path=str(db), seed=7, hz=2.0, snapshot_every=200))
    restart_ok = org2.identity.agent_id == agent_id and (
        org2.self_model is not None and org2.self_model.active.body_schema_id == body_schema_id
    )
    org2.store.validate_chain()
    org2.close()

    cpu_mean = 100.0 * cpu / max(wall, 1e-6)
    gate = (
        wall >= thr["duration_s_min"] * 0.99
        and cpu_mean <= thr["cpu_mean_pct_of_one_core_max"]
        and p95 <= thr["rss_p95_mib_max"]
        and slope <= thr["rss_slope_mib_per_h_max"]
        and not crashed
        and restart_ok
    )
    summary = {
        "method_path": str(METHOD_PATH.relative_to(ROOT)),
        "method_sha256": _sha256_file(METHOD_PATH),
        "git_commit": commit,
        "config_hash": config_hash,
        "source_hashes": source_hashes,
        "measurement_start": "runtime_ready",
        "duration_s": wall,
        "ticks": samples[-1]["tick"] if samples else 0,
        "sample_count": len(samples),
        "sample_interval_s": sample_interval,
        "cpu_mean_pct": cpu_mean,
        "rss_p95_mib": p95,
        "rss_first_mib": vmrss[0] if vmrss else None,
        "rss_last_mib": vmrss[-1] if vmrss else None,
        "rss_slope_mib_per_h": slope,
        "rss_slope_method": "runtime_ready_to_shutdown_ols_vmrss",
        "db_mib": db.stat().st_size / (1024 * 1024),
        "agent_id": agent_id,
        "body_schema_id": body_schema_id,
        "body_model_hash": body_hash,
        "collection_bounds": bounds,
        "crash_free": not crashed,
        "ledger_integrity": True,
        "identity_after_restart": restart_ok,
        "gate_performance_pass": gate,
        "config": config,
        "parent_d002v_verdict": method["parent_d002v_verdict"],
    }
    out = ROOT / "docs/evidence/d002p" / "performance-results.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    (ROOT / "docs/evidence/d002p" / "soak-2h-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
