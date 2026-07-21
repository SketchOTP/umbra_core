"""UMBRA-D-002 experiment harness — C0–C7 × I0–I11, ≥100 matched seeds."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.self_model import Attribution

CONDITIONS = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7"]
INTERVENTIONS = [f"I{i}" for i in range(12)]
TICKS = 250
SEEDS = 100


def run_trial(seed: int, condition: str, intervention: str, work: Path) -> dict[str, Any]:
    db = work / f"{condition}_{intervention}_{seed}.sqlite"
    cfg = OrganismConfig(
        db_path=str(db),
        seed=seed,
        condition=condition,
        intervention=intervention,
        arbitration_mode="random" if condition == "C7" else "full",
    )
    org = create_organism(cfg)
    org.run_ticks(TICKS)
    sm = org.self_model
    early, late = (1.0, 1.0)
    if sm and sm.errors:
        early, late = sm.initial_vs_recent_error(25, skip_first=5)
    attrs = sm.attributions if sm else []
    self_n = sum(1 for a in attrs if a.label == Attribution.SELF_CAUSED.value)
    ext_n = sum(1 for a in attrs if a.label == Attribution.EXTERNAL_CAUSED.value)
    unk_n = sum(1 for a in attrs if a.label == Attribution.UNKNOWN.value)
    false_self = 0
    if intervention == "I8":
        # external shove tick — self attribution there is false
        false_self = sum(
            1
            for a in attrs
            if a.tick == 40 and a.label == Attribution.SELF_CAUSED.value
        )
    out = {
        "seed": seed,
        "condition": condition,
        "intervention": intervention,
        "agent_id": org.identity.agent_id,
        "early_body_error": early,
        "late_body_error": late,
        "prediction_improvement": early - late,
        "mean_body_error": sm.mean_body_prediction_error() if sm else None,
        "self_attributions": self_n,
        "external_attributions": ext_n,
        "unknown_attributions": unk_n,
        "false_self_attribution": false_self,
        "schema_versions": (sm.active.version if sm else 0),
        "supersessions": len(sm.supersessions) if sm else 0,
        "confidence": sm.active.confidence if sm else None,
        "step_gain": sm.active.expected_motion.get("step_gain") if sm else None,
        "failed_actions": org.metrics["failed_actions"],
        "collisions": org.metrics["collisions"],
        "viable_frac": org.metrics["viable_ticks"] / max(1, org.metrics["total_ticks"]),
        "actions": dict(org.metrics["actions"]),
        "body_schema_id": sm.active.body_schema_id if sm else None,
        "self_model_hash": sm.state_hash() if sm else None,
    }
    org.close()
    # remove db to save disk (ponytail: evidence is aggregated JSON)
    try:
        db.unlink(missing_ok=True)
        Path(str(db) + "-wal").unlink(missing_ok=True)
        Path(str(db) + "-shm").unlink(missing_ok=True)
    except OSError:
        pass
    return out


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}

    def mean(key: str) -> float:
        xs = [r[key] for r in rows if r.get(key) is not None]
        return sum(xs) / len(xs) if xs else 0.0

    return {
        "n": len(rows),
        "mean_early_error": mean("early_body_error"),
        "mean_late_error": mean("late_body_error"),
        "mean_improvement": mean("prediction_improvement"),
        "mean_failed_actions": mean("failed_actions"),
        "mean_collisions": mean("collisions"),
        "mean_viable_frac": mean("viable_frac"),
        "mean_false_self": mean("false_self_attribution"),
        "mean_external": mean("external_attributions"),
        "mean_supersessions": mean("supersessions"),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    work = root / ".soak" / "d002_exp"
    work.mkdir(parents=True, exist_ok=True)
    out_dir = root / "docs/evidence/d002"
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    # Full factorial is huge (8*12*100=9600). Preregistered: 100 seeds on
    # critical cells + subsample elsewhere.
    rows: list[dict[str, Any]] = []
    # Core prediction cells
    core = [
        ("C0", "I0"),
        ("C0", "I1"),
        ("C0", "I3"),
        ("C0", "I4"),
        ("C0", "I5"),
        ("C0", "I8"),
        ("C0", "I9"),
        ("C0", "I10"),
        ("C0", "I11"),
        ("C1", "I1"),
        ("C2", "I1"),
        ("C3", "I8"),
        ("C4", "I1"),
        ("C5", "I0"),
        ("C6", "I0"),
        ("C7", "I0"),
    ]
    # Ensure ≥100 matched seeds on C0/I0 and C0/I1 (Gate 1)
    for condition, intervention in core:
        n = SEEDS if (condition, intervention) in {("C0", "I0"), ("C0", "I1"), ("C0", "I8"), ("C1", "I1"), ("C2", "I1")} else 30
        for seed in range(1, n + 1):
            rows.append(run_trial(seed, condition, intervention, work))

    # Coverage pass: one seed per remaining condition×intervention
    covered = {(r["condition"], r["intervention"]) for r in rows}
    for c in CONDITIONS:
        for i in INTERVENTIONS:
            if (c, i) not in covered:
                rows.append(run_trial(1, c, i, work))

    by_cell: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        key = f"{r['condition']}_{r['intervention']}"
        by_cell.setdefault(key, []).append(r)

    summary = {k: aggregate(v) for k, v in sorted(by_cell.items())}
    c0_i1 = aggregate(by_cell.get("C0_I1", []))
    c1_i1 = aggregate(by_cell.get("C1_I1", []))
    c2_i1 = aggregate(by_cell.get("C2_I1", []))

    prediction = {
        "ticks": TICKS,
        "seeds_C0_I1": len(by_cell.get("C0_I1", [])),
        "C0_I1": c0_i1,
        "C1_I1": c1_i1,
        "C2_I1": c2_i1,
        "gate1_C0_beats_C1": c0_i1.get("mean_late_error", 1) < c1_i1.get("mean_late_error", 0),
        "gate1_C0_beats_C2": c0_i1.get("mean_late_error", 1) < c2_i1.get("mean_late_error", 0)
        or c0_i1.get("mean_improvement", 0) > c2_i1.get("mean_improvement", 0),
        "gate1_error_decreases": c0_i1.get("mean_improvement", 0) > 0,
    }
    attribution = {
        "C0_I8": aggregate(by_cell.get("C0_I8", [])),
        "C3_I8": aggregate(by_cell.get("C3_I8", [])),
        "false_self_rate_C0_I8": aggregate(by_cell.get("C0_I8", [])).get("mean_false_self", 0),
    }
    body_change = {
        "C0_I1": c0_i1,
        "C0_I3": aggregate(by_cell.get("C0_I3", [])),
        "C0_I5": aggregate(by_cell.get("C0_I5", [])),
        "C4_I1": aggregate(by_cell.get("C4_I1", [])),
    }
    adaptation = {
        "C0_I9": aggregate(by_cell.get("C0_I9", [])),
        "C0_I11": aggregate(by_cell.get("C0_I11", [])),
        "C0_I10": aggregate(by_cell.get("C0_I10", [])),
    }

    (out_dir / "prediction-results.json").write_text(json.dumps(prediction, indent=2) + "\n")
    (out_dir / "attribution-results.json").write_text(json.dumps(attribution, indent=2) + "\n")
    (out_dir / "body-change-results.json").write_text(json.dumps(body_change, indent=2) + "\n")
    (out_dir / "adaptation-results.json").write_text(json.dumps(adaptation, indent=2) + "\n")
    (out_dir / "experiment-summary.json").write_text(
        json.dumps(
            {
                "elapsed_s": time.time() - t0,
                "total_trials": len(rows),
                "cells": summary,
                "conditions": CONDITIONS,
                "interventions": INTERVENTIONS,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"ok": True, "trials": len(rows), "elapsed": time.time() - t0, "prediction": prediction}, indent=2))


if __name__ == "__main__":
    main()
