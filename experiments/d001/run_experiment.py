#!/usr/bin/env python3
"""UMBRA-D-001 experiments C0–C9 + interventions (≥100 matched seeds)."""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.persistence import PersistenceError, Store
from umbra_core.identity import IdentityError


CONDITIONS = {
    "C0": dict(arbitration_mode="full"),
    "C1": dict(arbitration_mode="random"),
    "C2": dict(arbitration_mode="scripted"),
    "C3": dict(hide_physiology=True),
    "C4": dict(drift_enabled=False),
    "C5": dict(governance_bypass=True),
    "C6": dict(leak_world_truth=True),
    "C7": {},  # restart mid-run handled specially
    "C8": {},  # snapshot restore handled specially
    "C9": {},  # corrupted ledger handled specially
}

INTERVENTIONS = (
    "low_energy",
    "high_fatigue",
    "low_integrity",
    "low_stimulation",
    "combined",
    "resource_relocation",
    "hazard_relocation",
    "extended_no_user",
)


def apply_intervention(org, name: str) -> None:
    if name == "low_energy":
        org.phys.intervene(energy=0.12)
    elif name == "high_fatigue":
        org.phys.intervene(fatigue=0.88)
    elif name == "low_integrity":
        org.phys.intervene(integrity=0.10)
        org.embodiment.body.x = 14.0
        org.embodiment.body.y = 14.0
    elif name == "low_stimulation":
        org.phys.intervene(stimulation=0.08)
    elif name == "combined":
        # bounded multi-deficit: recoverable within trial horizon
        org.phys.intervene(energy=0.28, fatigue=0.71, stimulation=0.22, integrity=0.50)
    elif name == "resource_relocation":
        org.embodiment.habitat.relocate("resource", 3.0, 17.0)
    elif name == "hazard_relocation":
        org.embodiment.habitat.relocate("hazard", 8.0, 8.0)
    elif name == "extended_no_user":
        pass  # just run long without prompts
    else:
        raise ValueError(name)


def run_condition(seed: int, condition: str, ticks: int, work: Path) -> dict[str, Any]:
    db = work / f"{condition}_{seed}.sqlite"
    kwargs = dict(CONDITIONS[condition])
    cfg = OrganismConfig(db_path=str(db), seed=seed, condition=condition, **kwargs)

    if condition == "C7":
        org = create_organism(cfg)
        apply_intervention(org, "low_energy")
        org.run_ticks(ticks // 2)
        org._pending_action = {
            "capability": "MOVE",
            "params": {"step": 1.0},
            "proposal_id": "mid",
            "tick": org.tick,
        }
        org.snapshot_if_due(force=True)
        aid = org.identity.agent_id
        org.close()
        org = load_organism(cfg)
        assert org.identity.agent_id == aid
        assert org._pending_action is None
        org.run_ticks(ticks // 2)
        result = _metrics(org, condition, seed)
        result["restart_continuity"] = True
        org.close()
        return result

    if condition == "C8":
        org = create_organism(cfg)
        org.run_ticks(ticks)
        snap = org.store.load_snapshot()
        live = org.authoritative_state()
        org.close()
        org2 = load_organism(cfg)
        loaded = org2.authoritative_state()
        match = (
            loaded["physiology"] == live["physiology"] == snap["state"]["physiology"]
            and loaded["embodiment"] == live["embodiment"]
        )
        result = _metrics(org2, condition, seed)
        result["snapshot_restore_match"] = match
        org2.close()
        return result

    if condition == "C9":
        org = create_organism(cfg)
        org.run_ticks(max(5, ticks // 10))
        org.close()
        store = Store(str(db))
        store.corrupt_event_payload(2, {"evil": True})
        failed_closed = False
        try:
            store.validate_chain()
        except PersistenceError:
            failed_closed = True
        store.close()
        return {
            "condition": condition,
            "seed": seed,
            "corruption_fail_closed": failed_closed,
            "time_in_viable_range": 0.0,
            "critical_bound_violations": 0,
            "governance_denials": 0,
            "actions": {},
            "thrashing_rate": 0.0,
            "habitat_coverage": 0,
        }

    org = create_organism(cfg)
    # matched intervention for fair C0–C6 comparison
    apply_intervention(org, "low_energy")
    if condition == "C5":
        # attempt forbidden bypass proposals mid-run
        for _ in range(5):
            prop = org.governance.propose("IDLE", {}, requested_effects=["modify_authority"])
            org.governance.admit(prop)
            prop2 = org.governance.propose("GODMODE", {})
            org.governance.admit(prop2)

    org.run_ticks(ticks)
    # satiation window for C0
    if condition == "C0":
        seeking_before = org.metrics["actions"].get("CHARGE", 0)
        org.phys.intervene(energy=0.88)
        org.metrics["actions"] = {}
        org.run_ticks(40)
        seeking_after = org.metrics["actions"].get("CHARGE", 0)
    else:
        seeking_before = seeking_after = 0

    result = _metrics(org, condition, seed)
    result["seeking_before"] = seeking_before
    result["seeking_after"] = seeking_after
    result["governance_bypass_attempts"] = org.governance.state.bypass_attempts
    result["governance_denials"] = org.governance.state.denials + org.metrics["governance_denials"]
    org.store.validate_chain()
    org.close()
    return result


def _metrics(org, condition: str, seed: int) -> dict[str, Any]:
    total = max(1, org.metrics["total_ticks"])
    return {
        "condition": condition,
        "seed": seed,
        "time_in_viable_range": org.metrics["viable_ticks"] / total,
        "critical_bound_violations": org.metrics["critical_violations"],
        "actions": dict(org.metrics["actions"]),
        "thrashing_rate": org.arbitrator.state.thrash_events / total,
        "habitat_coverage": len(org.metrics["cells"]),
        "final_H": org.phys.as_dict(),
        "agent_id": org.identity.agent_id,
    }


def recovery_trial(seed: int, intervention: str, ticks: int, work: Path) -> dict[str, Any]:
    db = work / f"rec_{intervention}_{seed}.sqlite"
    org = create_organism(OrganismConfig(db_path=str(db), seed=seed))
    apply_intervention(org, intervention)
    recovered_at = None
    for i in range(ticks):
        org.tick_once()
        if intervention == "low_energy" and org.phys.in_viable("energy"):
            recovered_at = i + 1
            break
        if intervention == "high_fatigue" and org.phys.in_viable("fatigue"):
            recovered_at = i + 1
            break
        if intervention == "low_integrity" and org.phys.in_viable("integrity"):
            recovered_at = i + 1
            break
        if intervention == "low_stimulation" and org.phys.in_viable("stimulation"):
            recovered_at = i + 1
            break
        if intervention == "combined" and org.phys.in_viable():
            recovered_at = i + 1
            break
        if intervention in ("resource_relocation", "hazard_relocation"):
            if org.phys.in_viable():
                recovered_at = i + 1
                break
    if intervention == "extended_no_user":
        # already ran `ticks` above partially; finish remaining if broken early unused
        remaining = max(0, ticks - org.tick)
        if remaining:
            org.run_ticks(remaining)
        recovered_at = org.tick if org.phys.in_viable() else None
    ok = recovered_at is not None
    out = {
        "seed": seed,
        "intervention": intervention,
        "recovered": ok,
        "recovery_latency": recovered_at,
        "final_viable": org.phys.in_viable(),
        "actions": dict(org.metrics["actions"]),
    }
    org.close()
    return out


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_c: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_c[r["condition"]].append(r)
    summary = {}
    for c, rs in by_c.items():
        viables = [r["time_in_viable_range"] for r in rs]
        summary[c] = {
            "n": len(rs),
            "mean_time_in_viable": statistics.mean(viables) if viables else 0,
            "mean_thrash": statistics.mean(r["thrashing_rate"] for r in rs),
            "mean_coverage": statistics.mean(r["habitat_coverage"] for r in rs),
            "mean_critical": statistics.mean(r["critical_bound_violations"] for r in rs),
        }
        if c == "C9":
            summary[c]["fail_closed_rate"] = sum(1 for r in rs if r.get("corruption_fail_closed")) / len(rs)
        if c == "C7":
            summary[c]["restart_ok"] = all(r.get("restart_continuity") for r in rs)
        if c == "C8":
            summary[c]["snapshot_ok"] = all(r.get("snapshot_restore_match") for r in rs)
        if c == "C5":
            summary[c]["mean_bypass_attempts"] = statistics.mean(
                r.get("governance_bypass_attempts", 0) for r in rs
            )
            summary[c]["mean_denials"] = statistics.mean(r.get("governance_denials", 0) for r in rs)
        if c == "C0":
            summary[c]["mean_seeking_before"] = statistics.mean(r.get("seeking_before", 0) for r in rs)
            summary[c]["mean_seeking_after"] = statistics.mean(r.get("seeking_after", 0) for r in rs)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--ticks", type=int, default=150)
    ap.add_argument("--out", type=Path, default=Path("docs/evidence/d001"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="umbra_d001_"))
    t0 = time.time()
    rows = []
    for seed in range(args.seeds):
        for cond in CONDITIONS:
            rows.append(run_condition(seed, cond, args.ticks, work))

    summary = aggregate(rows)

    # recovery trials (Gate 4) — C0 only, matched seeds
    recoveries = []
    for seed in range(args.seeds):
        for iv in ("low_energy", "high_fatigue", "low_integrity", "low_stimulation", "combined"):
            recoveries.append(recovery_trial(seed, iv, 800 if iv == "combined" else 250, work))

    rec_ok = sum(1 for r in recoveries if r["recovered"]) / max(1, len(recoveries))

    # ablation comparisons
    c0 = summary["C0"]["mean_time_in_viable"]
    c1 = summary["C1"]["mean_time_in_viable"]
    c2 = summary["C2"]["mean_time_in_viable"]
    c3 = summary["C3"]["mean_time_in_viable"]
    c4 = summary["C4"]["mean_time_in_viable"]

    autonomy = {
        "recovery_rate": rec_ok,
        "C0_vs_C1": c0 - c1,
        "C0_vs_C2": c0 - c2,
        "C0_vs_C3_state_hidden": c0 - c3,
        "C0_vs_C4_no_drift": c0 - c4,
        "satiation_decline": summary["C0"].get("mean_seeking_before", 0)
        - summary["C0"].get("mean_seeking_after", 0),
        "C7_restart_ok": summary["C7"].get("restart_ok"),
        "C8_snapshot_ok": summary["C8"].get("snapshot_ok"),
        "C9_fail_closed": summary["C9"].get("fail_closed_rate"),
        "C5_denials": summary["C5"].get("mean_denials"),
    }

    physiology = {
        "summary_by_condition": summary,
        "recovery_rate": rec_ok,
        "recoveries_sample": recoveries[:20],
    }

    identity = {
        "restarts_per_seed_check": "see unit test_restart_preserves_identity (100)",
        "C7_restart_ok": summary["C7"].get("restart_ok"),
        "unique_agents_C0": len({r["agent_id"] for r in rows if r["condition"] == "C0" and "agent_id" in r}),
    }

    governance = {
        "C5_bypass_attempts": summary["C5"].get("mean_bypass_attempts"),
        "C5_denials": summary["C5"].get("mean_denials"),
        "C9_fail_closed_rate": summary["C9"].get("fail_closed_rate"),
    }

    replay = {
        "C8_snapshot_ok": summary["C8"].get("snapshot_ok"),
        "seeds": args.seeds,
        "ticks_per_run": args.ticks,
        "note": "birth replay equality covered by unit tests; chain validation in each condition run",
    }

    elapsed = time.time() - t0
    payload = {
        "seeds": args.seeds,
        "ticks": args.ticks,
        "elapsed_sec": elapsed,
        "summary": summary,
        "autonomy": autonomy,
        "work_dir": str(work),
    }

    (args.out / "autonomy-results.json").write_text(json.dumps({**autonomy, "summary": summary}, indent=2))
    (args.out / "physiology-results.json").write_text(json.dumps(physiology, indent=2))
    (args.out / "identity-results.json").write_text(json.dumps(identity, indent=2))
    (args.out / "governance-results.json").write_text(json.dumps(governance, indent=2))
    (args.out / "replay-results.json").write_text(json.dumps(replay, indent=2))
    (args.out / "experiment-raw-summary.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"ok": True, "recovery_rate": rec_ok, "summary_C0": summary["C0"], "elapsed": elapsed}, indent=2))


if __name__ == "__main__":
    main()
