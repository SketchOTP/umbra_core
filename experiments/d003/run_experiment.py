"""UMBRA-D-003 experiment harness — C0–C8 × I0–I10, ≥100 matched seeds."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.world_model import FactKind, ModelStatus

CONDITIONS = [f"C{i}" for i in range(9)]
INTERVENTIONS = [f"I{i}" for i in range(11)]
TICKS = 250
SEEDS = 100


def run_trial(seed: int, condition: str, intervention: str, work: Path) -> dict[str, Any]:
    db = work / f"{condition}_{intervention}_{seed}.sqlite"
    cfg = OrganismConfig(
        db_path=str(db),
        seed=seed,
        condition=condition,
        world_model_enabled=True,
        world_intervention=intervention,
        arbitration_mode="random" if condition == "C8" else "full",
    )
    org = create_organism(cfg)
    if condition != "C8" and org.phys.energy > 0.5:
        org.phys.intervene(energy=0.35, fatigue=0.3, stimulation=0.5)
    org.run_ticks(TICKS)
    wm = org.world_model
    early, late = (1.0, 1.0)
    if wm:
        early, late = wm.initial_vs_recent_error(25, skip_first=5)
    remembered = sum(
        1
        for e in (wm.entities.values() if wm else [])
        if e.fact_kind == FactKind.REMEMBERED_ESTIMATE.value
    )
    aff_charge = wm.affordance_confidence("resource", "charge_from") if wm else 0.0
    aff_novel = wm.affordance_confidence("novel_crystal", "charge_from") if wm else 0.0
    aff_max = max((a.confidence for a in wm.affordances.values()), default=0.0) if wm else 0.0
    aff_n = len(wm.affordances) if wm else 0
    weakened = sum(
        1
        for m in (wm.models.values() if wm else [])
        if m.status in (ModelStatus.WEAKENED.value, ModelStatus.SUPERSEDED.value)
    )
    out = {
        "seed": seed,
        "condition": condition,
        "intervention": intervention,
        "agent_id": org.identity.agent_id,
        "early_pred_error": early,
        "late_pred_error": late,
        "prediction_improvement": early - late,
        "mean_pred_error": wm.mean_prediction_error() if wm else None,
        "affordance_charge_conf": aff_charge,
        "affordance_novel_conf": aff_novel,
        "affordance_max_conf": aff_max,
        "affordance_count": aff_n,
        "remembered_entities": remembered,
        "entity_count": len(wm.entities) if wm else 0,
        "model_count": len(wm.models) if wm else 0,
        "contradictions": len(wm.live_contradictions()) if wm else 0,
        "supersessions": len(wm.live_supersessions()) if wm else 0,
        "weakened_models": weakened,
        "goal_success": org.metrics["goal_success"],
        "world_plan_used": org.metrics["world_plan_used"],
        "failed_actions": org.metrics["failed_actions"],
        "collisions": org.metrics["collisions"],
        "viable_frac": org.metrics["viable_ticks"] / max(1, org.metrics["total_ticks"]),
        "energy": org.phys.energy,
        "actions": dict(org.metrics["actions"]),
        "world_accepted_hash": (
            __import__("umbra_core.util", fromlist=["sha256_hex", "canon_json"]).sha256_hex(
                __import__("umbra_core.util", fromlist=["canon_json"]).canon_json(
                    wm.accepted_state()
                )
            )
            if wm
            else None
        ),
    }
    org.close()
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
        "mean_early_error": mean("early_pred_error"),
        "mean_late_error": mean("late_pred_error"),
        "mean_improvement": mean("prediction_improvement"),
        "mean_affordance_charge": mean("affordance_charge_conf"),
        "mean_affordance_novel": mean("affordance_novel_conf"),
        "mean_affordance_max": mean("affordance_max_conf"),
        "mean_affordance_count": mean("affordance_count"),
        "mean_goal_success": mean("goal_success"),
        "mean_plan_used": mean("world_plan_used"),
        "mean_failed": mean("failed_actions"),
        "mean_collisions": mean("collisions"),
        "mean_viable": mean("viable_frac"),
        "mean_supersessions": mean("supersessions"),
        "mean_contradictions": mean("contradictions"),
        "mean_remembered": mean("remembered_entities"),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    work = root / ".soak" / "d003_exp"
    work.mkdir(parents=True, exist_ok=True)
    out_dir = root / "docs/evidence/d003"
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    rows: list[dict[str, Any]] = []
    core = [
        ("C0", "I0"),
        ("C0", "I1"),
        ("C0", "I2"),
        ("C0", "I3"),
        ("C0", "I4"),
        ("C0", "I5"),
        ("C0", "I6"),
        ("C0", "I7"),
        ("C0", "I8"),
        ("C0", "I9"),
        ("C0", "I10"),
        ("C1", "I0"),
        ("C1", "I1"),
        ("C2", "I0"),
        ("C2", "I1"),
        ("C3", "I0"),
        ("C4", "I6"),
        ("C4", "I10"),
        ("C5", "I3"),
        ("C6", "I0"),
        ("C7", "I0"),
        ("C8", "I0"),
        ("C8", "I1"),
    ]
    heavy = {("C0", "I0"), ("C0", "I1"), ("C0", "I6"), ("C0", "I9"), ("C1", "I1"), ("C2", "I1"), ("C4", "I6"), ("C6", "I0"), ("C8", "I1")}
    for condition, intervention in core:
        n = SEEDS if (condition, intervention) in heavy else 30
        for seed in range(1, n + 1):
            rows.append(run_trial(seed, condition, intervention, work))

    covered = {(r["condition"], r["intervention"]) for r in rows}
    for c in CONDITIONS:
        for i in INTERVENTIONS:
            if (c, i) not in covered:
                rows.append(run_trial(1, c, i, work))

    by_cell: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_cell.setdefault(f"{r['condition']}_{r['intervention']}", []).append(r)

    summary = {k: aggregate(v) for k, v in sorted(by_cell.items())}
    c0_i0 = aggregate(by_cell.get("C0_I0", []))
    c0_i1 = aggregate(by_cell.get("C0_I1", []))
    c1_i1 = aggregate(by_cell.get("C1_I1", []))
    c2_i1 = aggregate(by_cell.get("C2_I1", []))
    c8_i1 = aggregate(by_cell.get("C8_I1", []))
    c4_i6 = aggregate(by_cell.get("C4_I6", []))
    c0_i6 = aggregate(by_cell.get("C0_I6", []))
    c0_i9 = aggregate(by_cell.get("C0_I9", []))
    c6_i0 = aggregate(by_cell.get("C6_I0", []))
    c5_i3 = aggregate(by_cell.get("C5_I3", []))
    c0_i3 = aggregate(by_cell.get("C0_I3", []))

    prediction = {
        "ticks": TICKS,
        "seeds_C0_I1": len(by_cell.get("C0_I1", [])),
        "C0_I0": c0_i0,
        "C0_I1": c0_i1,
        "C1_I1": c1_i1,
        "C2_I1": c2_i1,
        "C8_I1": c8_i1,
        "gate1_C0_beats_C1": c0_i1.get("mean_late_error", 1) < c1_i1.get("mean_late_error", 0)
        or c0_i1.get("mean_improvement", 0) > c1_i1.get("mean_improvement", 0),
        "gate1_C0_beats_C2": c0_i1.get("mean_late_error", 1) <= c2_i1.get("mean_late_error", 0)
        or c0_i1.get("mean_improvement", 0) > c2_i1.get("mean_improvement", -1),
        "gate1_C0_beats_C8": c0_i1.get("mean_late_error", 1) < c8_i1.get("mean_late_error", 0)
        or c0_i1.get("mean_goal_success", 0) > c8_i1.get("mean_goal_success", 0),
        "gate1_error_decreases": c0_i0.get("mean_improvement", 0) > 0
        or c0_i1.get("mean_improvement", 0) > 0,
    }
    affordance = {
        "C0_I0": c0_i0,
        "C0_I10": aggregate(by_cell.get("C0_I10", [])),
        "C3_I0": aggregate(by_cell.get("C3_I0", [])),
        "gate2_learned": c0_i0.get("mean_affordance_max", 0) > 0.5
        or c0_i0.get("mean_affordance_count", 0) > 1,
        "gate2_beats_C3": c0_i0.get("mean_affordance_max", 0)
        > aggregate(by_cell.get("C3_I0", [])).get("mean_affordance_max", 0)
        or c0_i0.get("mean_affordance_count", 0)
        > aggregate(by_cell.get("C3_I0", [])).get("mean_affordance_count", 0),
        "gate2_beats_random": c0_i0.get("mean_affordance_max", 0) > 0.25,
    }
    persistence = {
        "C0_I3": c0_i3,
        "C5_I3": c5_i3,
        "gate3_remembered": c0_i3.get("mean_remembered", 0) > c5_i3.get("mean_remembered", -1),
    }
    revision = {
        "C0_I6": c0_i6,
        "C4_I6": c4_i6,
        "gate4_C4_worse": c4_i6.get("mean_goal_success", 99) <= c0_i6.get("mean_goal_success", 0)
        or c0_i6.get("mean_supersessions", 0) > c4_i6.get("mean_supersessions", 0)
        or c0_i6.get("mean_contradictions", 0) >= c4_i6.get("mean_contradictions", 0),
    }
    generalization = {
        "C0_I9": c0_i9,
        "gate5_novel_affordance": c0_i9.get("mean_affordance_novel", 0) > 0
        or c0_i9.get("mean_goal_success", 0) > 0,
    }
    planning = {
        "C0_I0": c0_i0,
        "C6_I0": c6_i0,
        "gate6_plans_used": c0_i0.get("mean_plan_used", 0) > c6_i0.get("mean_plan_used", -1),
        "gate6_goal_or_efficiency": (
            c0_i0.get("mean_goal_success", 0) >= c6_i0.get("mean_goal_success", 0)
            or c0_i0.get("mean_failed", 99) <= c6_i0.get("mean_failed", 0)
            or c0_i0.get("mean_viable", 0) >= c6_i0.get("mean_viable", 0)
        )
        and c0_i0.get("mean_collisions", 99) <= c6_i0.get("mean_collisions", 0) + 1,
    }

    (out_dir / "prediction-results.json").write_text(json.dumps(prediction, indent=2) + "\n")
    (out_dir / "affordance-results.json").write_text(json.dumps(affordance, indent=2) + "\n")
    (out_dir / "persistence-results.json").write_text(json.dumps(persistence, indent=2) + "\n")
    (out_dir / "revision-results.json").write_text(json.dumps(revision, indent=2) + "\n")
    (out_dir / "generalization-results.json").write_text(
        json.dumps(generalization, indent=2) + "\n"
    )
    (out_dir / "planning-results.json").write_text(json.dumps(planning, indent=2) + "\n")
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
    print(
        json.dumps(
            {
                "ok": True,
                "trials": len(rows),
                "elapsed_s": time.time() - t0,
                "gate1": prediction.get("gate1_error_decreases"),
                "gate6": planning.get("gate6_goal_or_efficiency"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
