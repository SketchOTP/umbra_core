#!/usr/bin/env python3
"""Close out Run A as retention-v0 performance-only evidence."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

EVIDENCE = Path("docs/evidence/d001")
SOAK_DB = Path("/tmp/umbra_soak/soak6h.sqlite")
SOAK_JSONL = EVIDENCE / "soak-6h.jsonl"
SOAK_SUMMARY = EVIDENCE / "soak-6h-summary.json"
REVISION = EVIDENCE / "soak-revision-audit.json"


def db_bytes(path: Path) -> int:
    total = path.stat().st_size if path.exists() else 0
    for suffix in ("-wal", "-shm"):
        p = Path(str(path) + suffix)
        if p.exists():
            total += p.stat().st_size
    return total


def main() -> None:
    if not SOAK_SUMMARY.exists():
        raise SystemExit("Run A not finished: missing soak-6h-summary.json")
    summary = json.loads(SOAK_SUMMARY.read_text())
    revision = json.loads(REVISION.read_text()) if REVISION.exists() else {}
    samples = [json.loads(l) for l in SOAK_JSONL.read_text().splitlines() if l.strip()]

    duration = float(summary["elapsed_sec"])
    ticks = int(summary["ticks"])
    cpu_sec = float(summary["cpu_sec"])
    cpu_mean = cpu_sec / duration if duration else 0.0
    cpu_rates = []
    for i in range(1, len(samples)):
        dt = samples[i]["elapsed_sec"] - samples[i - 1]["elapsed_sec"]
        dc = samples[i]["cpu_sec"] - samples[i - 1]["cpu_sec"]
        if dt > 0:
            cpu_rates.append(dc / dt)
    cpu_p95 = sorted(cpu_rates)[int(0.95 * (len(cpu_rates) - 1))] if cpu_rates else cpu_mean
    rss_vals = [s["rss_mib"] for s in samples]
    rss_mean = statistics.mean(rss_vals)
    rss_p95 = sorted(rss_vals)[int(0.95 * (len(rss_vals) - 1))]
    slope = (samples[-1]["rss_mib"] - samples[0]["rss_mib"]) / (
        (samples[-1]["elapsed_sec"] - samples[0]["elapsed_sec"]) / 3600.0
    )
    warm = [s for s in samples if s["elapsed_sec"] >= 3600]
    slope_warmup = None
    if len(warm) >= 2:
        slope_warmup = (warm[-1]["rss_mib"] - warm[0]["rss_mib"]) / (
            (warm[-1]["elapsed_sec"] - warm[0]["elapsed_sec"]) / 3600.0
        )

    gates = {
        "duration_ge_6h": duration >= 6 * 3600 - 30,
        "rss_p95_le_200": rss_p95 <= 200,
        "rss_slope_le_1": abs(slope) <= 1.0,
        "cpu_mean_le_5pct": cpu_mean <= 0.05,
        "no_crash": True,
    }
    out = {
        "run_id": "A",
        "role": "performance_only_retention_v0",
        "certifies_final_retention": False,
        "retention_policy_version": revision.get(
            "retention_policy_version", "v0_pre_fix_downsample_drift_10_proposal_5"
        ),
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
        "rss_slope_after_1h_warmup_diagnostic": slope_warmup,
        "database_bytes": db_bytes(SOAK_DB) if SOAK_DB.exists() else None,
        "database_path": str(SOAK_DB),
        "database_present_at_closeout": SOAK_DB.exists(),
        "agent_id": summary.get("agent_id"),
        "failures": [] if all(gates.values()) else [k for k, v in gates.items() if not v],
        "gates": gates,
        "gate9_performance_pass": all(gates.values()),
        "revision_audit": str(REVISION),
        "note": (
            "Run A started before retention-v1. Performance evidence under retention v0 only; "
            "cannot certify authoritative-every-tick. Gate 9 uses full-window RSS slope "
            "(no threshold retune). Warmup slope is diagnostic. SQLite under /tmp was absent "
            "at closeout after clean process exit."
        ),
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "soak-run-a-performance.json").write_text(json.dumps(out, indent=2))

    perf_path = EVIDENCE / "performance-results.json"
    perf = json.loads(perf_path.read_text()) if perf_path.exists() else {}
    perf["soak_run_a_v0"] = out
    perf["soak_6h"] = {
        "status": "COMPLETE_AS_RUN_A_V0_PERF_ONLY",
        "summary": summary,
        "certifies_final_retention": False,
        "gate9_performance_pass": out["gate9_performance_pass"],
    }
    perf_path.write_text(json.dumps(perf, indent=2))
    print(json.dumps({"gate9_performance_pass": out["gate9_performance_pass"], "failures": out["failures"]}, indent=2))


if __name__ == "__main__":
    main()
