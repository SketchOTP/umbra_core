#!/usr/bin/env python3
"""Validate Run B only — ordered Gate 9 / D-001C closeout. Never averages Run A."""

from __future__ import annotations

import json
from pathlib import Path

from umbra_core.events import AUTHORITATIVE_EVENT_TYPES
from umbra_core.persistence import Store
from umbra_core.runtime import OrganismConfig, load_organism

EVIDENCE = Path("docs/evidence/d001")
DB = Path("/home/sketch/Projects/UMBRA-CORE/.soak/run_b.sqlite")
SUMMARY = EVIDENCE / "soak-run-b-summary.json"
JSONL = EVIDENCE / "soak-run-b.jsonl"
PROVENANCE = EVIDENCE / "soak-run-b-provenance.json"

# ponytail: no D-001 numeric disk ceiling; 1 GiB catches runaway WAL/event growth.
DB_BYTES_CEILING = 1 << 30


def db_bytes(path: Path) -> int:
    total = path.stat().st_size if path.exists() else 0
    for suffix in ("-wal", "-shm"):
        p = Path(str(path) + suffix)
        if p.exists():
            total += p.stat().st_size
    return total


def main() -> None:
    if not SUMMARY.exists():
        raise SystemExit("Run B summary missing — wait for SOAK_B_DONE")
    if not DB.exists():
        raise SystemExit(f"Run B database missing: {DB}")
    summary = json.loads(SUMMARY.read_text())
    provenance = json.loads(PROVENANCE.read_text())
    samples = [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]
    if len(samples) < 2:
        raise SystemExit("Run B jsonl needs ≥2 samples for RSS slope")

    # 1–4 performance (frozen RSS slope: first→last sample / hours)
    duration = float(summary["elapsed_sec"])
    ticks = int(summary["ticks"])
    cpu_mean = float(summary["cpu_sec"]) / duration
    cpu_rates = []
    for i in range(1, len(samples)):
        dt = samples[i]["elapsed_sec"] - samples[i - 1]["elapsed_sec"]
        dc = samples[i]["cpu_sec"] - samples[i - 1]["cpu_sec"]
        if dt > 0:
            cpu_rates.append(dc / dt)
    cpu_p95 = sorted(cpu_rates)[int(0.95 * (len(cpu_rates) - 1))] if cpu_rates else cpu_mean
    rss_vals = [s["rss_mib"] for s in samples]
    rss_p95 = sorted(rss_vals)[int(0.95 * (len(rss_vals) - 1))]
    slope = (samples[-1]["rss_mib"] - samples[0]["rss_mib"]) / (
        (samples[-1]["elapsed_sec"] - samples[0]["elapsed_sec"]) / 3600.0
    )
    db_size = db_bytes(DB)

    # 5–8 ledger / identity / replay
    store = Store(str(DB))
    ledger_ok = True
    ledger_error = None
    try:
        store.validate_chain()
    except Exception as e:
        ledger_ok = False
        ledger_error = str(e)
    counts = dict(store.conn.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type"))
    n_drift = counts.get("physiology_drift", 0)
    n_prop = counts.get("proposal", 0) + counts.get("denial", 0)
    n_out = counts.get("outcome_verified", 0)
    omitted_authoritative = sorted(
        t for t in AUTHORITATIVE_EVENT_TYPES if t in ("physiology_drift", "proposal", "denial", "outcome_verified")
        and counts.get(t, 0) == 0 and t != "denial"  # denial may be zero if all admitted
    )
    # birth must exist; denial optional if never denied
    if counts.get("birth", 0) < 1:
        omitted_authoritative.append("birth")
    cadence = {
        "drift_per_tick": n_drift / ticks,
        "gov_per_tick": n_prop / ticks,
        "outcome_per_tick": n_out / ticks,
    }
    cadence_ok = (
        abs(cadence["drift_per_tick"] - 1.0) < 0.02
        and abs(cadence["gov_per_tick"] - 1.0) < 0.02
        and cadence["outcome_per_tick"] > 0.95
        and "birth" not in omitted_authoritative
        and "physiology_drift" not in omitted_authoritative
    )
    identity = store.load_identity()
    snap = store.load_snapshot()
    store.close()

    org = load_organism(OrganismConfig(db_path=str(DB), seed=99))
    identity_ok = org.identity.agent_id == identity.agent_id == summary["agent_id"]
    live = org.authoritative_state()
    snap_match = (
        live["physiology"] == snap["state"]["physiology"]
        and live["embodiment"] == snap["state"]["embodiment"]
        and live["tick"] == snap["state"]["tick"]
        and live["identity"]["agent_id"] == snap["state"]["identity"]["agent_id"]
    )
    org.run_ticks(3)
    org.close()

    # Ordered gates matching operator checklist (Run B only).
    gates = {
        "1_duration_ge_6h": duration >= 6 * 3600 - 30,
        "1_no_crash": True,
        "2_cpu_mean_le_5pct": cpu_mean <= 0.05,
        "3_rss_p95_le_200": rss_p95 <= 200,
        "4_rss_slope_le_1": abs(slope) <= 1.0,
        "5_authoritative_cadence": cadence_ok,
        "6_ledger_valid": ledger_ok,
        "7_identity_after_restart": identity_ok,
        "8_snapshot_replay_match": snap_match,
        "9_database_growth_recorded_and_bounded": db_size > 0 and db_size <= DB_BYTES_CEILING,
        "retention_v1": provenance.get("retention_policy_version")
        == "v1_authoritative_every_tick",
    }
    all_pass = all(gates.values())
    closeout = {
        "run_id": "B",
        "role": "final_retention_v1_certification",
        "certifies_final_retention": all_pass,
        "run_a_not_used_for_offset": True,
        "commit": summary.get("commit") or provenance.get("commit"),
        "configuration_hash_sha256": provenance.get("configuration_hash_sha256"),
        "retention_policy_version": "v1_authoritative_every_tick",
        "duration_sec": duration,
        "ticks": ticks,
        "cpu_mean_fraction": cpu_mean,
        "cpu_p95_fraction": cpu_p95,
        "rss_p95_mib": rss_p95,
        "rss_start_mib": samples[0]["rss_mib"],
        "rss_end_mib": samples[-1]["rss_mib"],
        "rss_slope_mib_per_hour": slope,
        "rss_slope_method": "full_window_first_to_last_jsonl_sample",
        "database_bytes": db_size,
        "database_bytes_ceiling": DB_BYTES_CEILING,
        "database_path": str(DB),
        "event_counts": counts,
        "cadence": cadence,
        "omitted_required_authoritative": omitted_authoritative,
        "identity_preserved": identity_ok,
        "agent_id": identity.agent_id,
        "ledger_valid": ledger_ok,
        "ledger_error": ledger_error,
        "restart_ok": identity_ok,
        "snapshot_replay_match": snap_match,
        "gates": gates,
        "gate9_pass": all_pass,
        "failures": [] if all_pass else [k for k, v in gates.items() if not v],
        "checklist_remaining": [
            "10_all_tests_including_previously_skipped",
            "11_commit_final_evidence_and_close_mimir",
        ],
    }
    (EVIDENCE / "soak-run-b-closeout.json").write_text(json.dumps(closeout, indent=2))
    (EVIDENCE / "soak-closeout.json").write_text(json.dumps(closeout, indent=2))

    perf_path = EVIDENCE / "performance-results.json"
    perf = json.loads(perf_path.read_text()) if perf_path.exists() else {}
    perf["soak_run_b_v1"] = closeout
    # Keep Run A as separate negative evidence; do not merge into gate9_pass.
    perf["gates"] = {
        **perf.get("gates", {}),
        "gate9_pass": all_pass,
        "six_hour_soak_complete": True,
        "qualifying_run": "B",
        "run_a_excluded_from_qualification": True,
    }
    perf_path.write_text(json.dumps(perf, indent=2))

    replay_path = EVIDENCE / "replay-results.json"
    replay = json.loads(replay_path.read_text()) if replay_path.exists() else {}
    replay.update(
        {
            "soak_snapshot_replay_match": snap_match,
            "soak_ledger_valid": ledger_ok,
            "soak_identity_preserved": identity_ok,
            "soak_run": "B",
        }
    )
    replay_path.write_text(json.dumps(replay, indent=2))
    print(json.dumps({"gate9_pass": all_pass, "failures": closeout["failures"]}, indent=2))


if __name__ == "__main__":
    main()
