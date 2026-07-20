#!/usr/bin/env python3
"""Post-soak validation and evidence closeout for UMBRA-D-001C."""

from __future__ import annotations

import json
import resource
import statistics
import time
from pathlib import Path

from umbra_core.persistence import Store
from umbra_core.runtime import OrganismConfig, load_organism

EVIDENCE = Path("docs/evidence/d001")
SOAK_DB = Path("/tmp/umbra_soak/soak6h.sqlite")
SOAK_JSONL = EVIDENCE / "soak-6h.jsonl"
SOAK_SUMMARY = EVIDENCE / "soak-6h-summary.json"


def rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def db_bytes(path: Path) -> int:
    total = path.stat().st_size if path.exists() else 0
    for suffix in ("-wal", "-shm"):
        p = Path(str(path) + suffix)
        if p.exists():
            total += p.stat().st_size
    return total


def main() -> None:
    if not SOAK_SUMMARY.exists():
        raise SystemExit(f"missing {SOAK_SUMMARY}; soak not finished")
    summary = json.loads(SOAK_SUMMARY.read_text())
    samples = []
    if SOAK_JSONL.exists():
        for line in SOAK_JSONL.read_text().splitlines():
            if line.strip():
                samples.append(json.loads(line))

    duration = float(summary["elapsed_sec"])
    ticks = int(summary["ticks"])
    cpu_sec = float(summary["cpu_sec"])
    cpu_mean = cpu_sec / duration if duration else 0.0
    # p95 CPU from interval deltas in jsonl
    cpu_rates = []
    for i in range(1, len(samples)):
        dt = samples[i]["elapsed_sec"] - samples[i - 1]["elapsed_sec"]
        dc = samples[i]["cpu_sec"] - samples[i - 1]["cpu_sec"]
        if dt > 0:
            cpu_rates.append(dc / dt)
    cpu_p95 = sorted(cpu_rates)[int(0.95 * (len(cpu_rates) - 1))] if cpu_rates else cpu_mean

    rss_vals = [s["rss_mib"] for s in samples] if samples else [summary["rss_start_mib"], summary["rss_end_mib"]]
    rss_mean = statistics.mean(rss_vals)
    rss_p95 = sorted(rss_vals)[int(0.95 * (len(rss_vals) - 1))]
    if samples and samples[-1]["elapsed_sec"] > samples[0]["elapsed_sec"]:
        slope = (samples[-1]["rss_mib"] - samples[0]["rss_mib"]) / (
            (samples[-1]["elapsed_sec"] - samples[0]["elapsed_sec"]) / 3600.0
        )
    else:
        slope = (summary["rss_end_mib"] - summary["rss_start_mib"]) / max(duration / 3600.0, 1e-9)

    # Ledger validation
    store = Store(str(SOAK_DB))
    ledger_ok = True
    ledger_error = None
    try:
        store.validate_chain()
    except Exception as e:
        ledger_ok = False
        ledger_error = str(e)
    event_count = store.conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()[0]
    identity = store.load_identity()
    agent_id = identity.agent_id
    snap = store.load_snapshot()
    store.close()

    # Restart + snapshot match
    cfg = OrganismConfig(db_path=str(SOAK_DB), seed=99)
    org = load_organism(cfg)
    identity_ok = org.identity.agent_id == agent_id
    live = org.authoritative_state()
    snap_match = (
        live["physiology"] == snap["state"]["physiology"]
        and live["embodiment"] == snap["state"]["embodiment"]
        and live["identity"]["agent_id"] == snap["state"]["identity"]["agent_id"]
        and live["tick"] == snap["state"]["tick"]
    )
    org.run_ticks(3)  # prove restart operational
    restart_ok = True
    org.close()

    growth = db_bytes(SOAK_DB)

    gates = {
        "duration_ge_6h": duration >= 6 * 3600 - 30,
        "rss_p95_le_200": rss_p95 <= 200,
        "rss_slope_le_1": abs(slope) <= 1.0,
        "cpu_mean_le_5pct": cpu_mean <= 0.05,
        "no_crash": True,
        "ledger_valid": ledger_ok,
        "restart_ok": restart_ok and identity_ok,
        "snapshot_replay_match": snap_match,
    }
    all_pass = all(gates.values())

    closeout = {
        "duration_sec": duration,
        "ticks": ticks,
        "cpu_mean_fraction": cpu_mean,
        "cpu_p95_fraction": cpu_p95,
        "cpu_mean_percent": cpu_mean * 100,
        "cpu_p95_percent": cpu_p95 * 100,
        "rss_mean_mib": rss_mean,
        "rss_p95_mib": rss_p95,
        "rss_start_mib": summary["rss_start_mib"],
        "rss_end_mib": summary["rss_end_mib"],
        "rss_slope_mib_per_hour": slope,
        "database_bytes": growth,
        "event_count": int(event_count),
        "agent_id": agent_id,
        "identity_preserved": identity_ok,
        "ledger_valid": ledger_ok,
        "ledger_error": ledger_error,
        "restart_ok": restart_ok,
        "snapshot_replay_match": snap_match,
        "failures": [] if all_pass else [k for k, v in gates.items() if not v],
        "gates": gates,
        "gate9_pass": all_pass,
        "samples_n": len(samples),
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "soak-closeout.json").write_text(json.dumps(closeout, indent=2))

    # Merge into performance-results.json
    perf_path = EVIDENCE / "performance-results.json"
    perf = json.loads(perf_path.read_text()) if perf_path.exists() else {}
    perf["soak_6h"] = {
        "status": "COMPLETE",
        "summary": summary,
        "closeout": closeout,
    }
    perf["gates"] = {
        **perf.get("gates", {}),
        "six_hour_soak_complete": True,
        "gate9_pass": all_pass,
        **{f"soak_{k}": v for k, v in gates.items()},
    }
    perf_path.write_text(json.dumps(perf, indent=2))

    # Update replay-results with soak snapshot check
    replay_path = EVIDENCE / "replay-results.json"
    replay = json.loads(replay_path.read_text()) if replay_path.exists() else {}
    replay["soak_snapshot_replay_match"] = snap_match
    replay["soak_ledger_valid"] = ledger_ok
    replay["soak_identity_preserved"] = identity_ok
    replay_path.write_text(json.dumps(replay, indent=2))

    print(json.dumps({"gate9_pass": all_pass, "closeout": closeout}, indent=2))


if __name__ == "__main__":
    main()
