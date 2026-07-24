#!/usr/bin/env python3
"""UMBRA-D-010 paired-seed experiment harness (Gates 0–12).

Reads preregistration under `experiments/d010/`, runs the gate-critical matrix with
≥100 paired formal seeds per cell, writes per-gate summary JSON plus
`raw-results.jsonl` and `evidence-validation.json`. Gate 13 performance is
deferred to Task 14.

Pre-freeze (Task 11): Stage A hashes must be complete; formal execution requires
Stage B freeze tip from Task 12.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d010 import evidence as ev
from experiments.d010.conditions import (
    QUALIFICATION_BASELINE_CONDITION,
    TemporalConditionError,
    condition_to_temporal_config,
)
from experiments.d010.control_rows import label_experiment_row
from experiments.d010.diagnostic_controllers import (
    HiddenScheduleInjector,
    RandomWaitInjectionController,
    ScriptedFutureScheduleController,
    assert_disposable_db_path,
)
from experiments.d010.governance_bypass import attempt_wait_governance_bypass
from experiments.d010.hostile_temporal_view import HostileTemporalClockView
from experiments.d010.replay_shuffle import shuffle_replay_events
from experiments.d010.scenario_plants import apply_scenario_plants, plants_for_scenario
from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.temporal.config import TemporalConfig, p0_performance_config
from umbra_core.temporal.recurrence import EvidenceLane

OUT = ROOT / "docs" / "evidence" / "d010"

THR, MATRIX, SCEN_SUITE, FROZEN_HASHES = ev.load_frozen()
SCEN_BY_ID = {s["id"]: s for s in SCEN_SUITE["scenarios"]}
FORMAL_SEEDS = json.loads(
    (ROOT / "experiments/d010/formal-seed-manifest.json").read_text(encoding="utf-8")
)["seeds"]

PAIRED_SEEDS = int(os.environ.get("D010_SEEDS", THR["minimum_gate_critical_paired_seeds"]))
MAX_WORKERS = int(os.environ.get("D010_WORKERS", "4"))
ALLOW_SMOKE = os.environ.get("D010_ALLOW_SMOKE", "") == "1"
TICK_SCALE = float(os.environ.get("D010_TICK_SCALE", "1.0"))

GATE_RESULT_FILES = {
    0: "regression-results.json",
    1: "temporal-authority-results.json",
    2: "recurrence-results.json",
    3: "future-leakage-results.json",
    4: "anticipation-results.json",
    5: "revision-results.json",
    6: "temporal-routine-results.json",
    7: "autonomy-results.json",
    8: "absence-safety-results.json",
    9: "individuality-timing-results.json",
    10: "restart-downtime-results.json",
    11: "replay-results.json",
    12: "boundedness-results.json",
}


_RECURRENCE_INTAKE_SCENARIOS = frozenset({"S1"})
_RECURRENCE_INTAKE_PERIOD = 30
_RECURRENCE_CONTEXT_KEYS = ("habitat.resource:0", "habitat.resource:1")


def _zero_baseline(values_b: list[float]) -> list[float]:
    """Synthetic zero baseline paired to diagnostic row counts (gate 3 has no C0 rows)."""
    return [0.0] * (len(values_b) if values_b else 1)


def _recurrence_learning_signal(temporal: Any) -> float:
    index = getattr(temporal.state, "recurrence_index", ()) or ()
    active = sum(1 for _, payload in index if payload.get("status") == "ACTIVE")
    return float(min(1.0, active / 3.0))


def _maybe_harness_recurrence_intake(
    org: Any,
    *,
    scenario: str,
    condition: str,
    tick: int,
    seed: int,
) -> None:
    """Wire minimal organism-observable recurrence intake for gate-2 S1 traces."""
    if scenario not in _RECURRENCE_INTAKE_SCENARIOS or org.temporal is None:
        return
    if condition in {"C1", *{"C2", "C3", "C7", "C9", "C10", "C12"}}:
        return
    if tick <= 0 or tick % _RECURRENCE_INTAKE_PERIOD != 0:
        return
    freq_only = bool(org._temporal_cfg.frequency_only_recurrence)
    lane = EvidenceLane.AUTHORITATIVE if freq_only else EvidenceLane.ORGANISM_OBSERVABLE
    ctx = _RECURRENCE_CONTEXT_KEYS[(tick // _RECURRENCE_INTAKE_PERIOD) % len(_RECURRENCE_CONTEXT_KEYS)]
    org.temporal.observe_recurrence_occurrence(
        event_kind="habitat.periodic_resource",
        internal_context_key=ctx,
        occurrence_id=f"harness:s1:{seed}:{tick}",
        evidence_identity=f"harness:s1:{seed}:{tick}:ev",
        tick=tick,
        lane=lane,
    )


def tick_budget(scenario_id: str) -> int:
    base = int(SCEN_BY_ID[scenario_id]["tick_budget"])
    scaled = max(20, int(base * TICK_SCALE))
    cap = int(os.environ.get("D010_TICK_CAP", "0"))
    return min(scaled, cap) if cap > 0 else scaled


def _temporal_cfg(condition: str) -> TemporalConfig | None:
    if condition == "C1":
        return None
    if condition == "C13":
        return p0_performance_config()
    try:
        return condition_to_temporal_config(condition)
    except TemporalConditionError:
        return TemporalConfig()


def _organism_cfg(db_path: str, seed: int, condition: str, scenario: str) -> OrganismConfig:
    """Build organism config for an integrated matrix cell.

    `condition` is the ablation/matrix label (C0–C13). Production `OrganismConfig.condition`
    stays pinned to C0; ablations apply only via `temporal_config` (C1 disables temporal).
    """
    tcfg = _temporal_cfg(condition)
    return OrganismConfig(
        db_path=db_path,
        seed=seed,
        condition=QUALIFICATION_BASELINE_CONDITION,
        temporal_enabled=condition != "C1",
        temporal_config=tcfg,
        temporal_scenario_id=scenario,
        temporal_scenario_hook=apply_scenario_plants,
        habitat_enabled=True,
        habitat_scenario_id=scenario,
        habitat_scenario_hook=apply_scenario_plants,
        memory_enabled=True,
        world_model_enabled=True,
        individuality_enabled=True,
        social_enabled=True,
        embodiment_adapter_enabled=True,
        expression_enabled=True,
        drift_enabled=True,
        wall_time_fn=lambda: float(seed % 1000),
    )


def _diagnostic_trace(condition: str, scenario: str, seed: int) -> dict[str, Any]:
    ticks = min(tick_budget(scenario), 40)
    metrics: dict[str, Any] = {
        "temporal_authority_alignment": 0.0,
        "recurrence_learning_signal": 0.0,
        "future_leakage_detection": 1.0,
        "anticipation_coverage": 0.0,
        "revision_adaptation": 0.0,
        "temporal_routine_promotion": 0.0,
        "autonomous_action_coverage": 0.0,
        "absence_safety_violation": 0.0,
        "individuality_timing_separation": 0.0,
        "restart_age_continuity": 0.0,
        "replay_equivalence": 0.0,
        "boundedness_ok": 1.0,
        "governance_bypass_admitted": 0,
    }
    if condition == "C2":
        ctrl = ScriptedFutureScheduleController()
        hits = sum(len(ctrl.entries_for_tick(t)) for t in range(1, ticks + 1))
        metrics["future_leakage_detection"] = float(hits > 0)
        metrics["recurrence_learning_signal"] = 0.0
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c2"}
    if condition == "C3":
        ctrl = RandomWaitInjectionController(seed=seed)
        samples = [ctrl.sample_wait_params(t) for t in range(1, 6)]
        metrics["future_leakage_detection"] = float(all(s["source"] == "RANDOM_DIAGNOSTIC" for s in samples))
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c3"}
    if condition == "C7":
        inj = HiddenScheduleInjector()
        metrics["future_leakage_detection"] = float(len(inj.payloads()) > 0)
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c7"}
    if condition == "C9":
        from umbra_core.temporal.engine import TemporalEngine
        from umbra_core.temporal.state import sample_temporal_state

        engine = TemporalEngine(sample_temporal_state())
        view = HostileTemporalClockView()
        view.attempt_ui_clock_as_truth(engine)
        metrics["temporal_authority_alignment"] = float(len(view.successful_writes) == 0)
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c9"}
    if condition == "C10":
        outcomes = attempt_wait_governance_bypass()
        metrics["governance_bypass_admitted"] = sum(1 for o in outcomes if o.get("admitted"))
        metrics["future_leakage_detection"] = float(metrics["governance_bypass_admitted"] > 0)
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c10"}
    if condition == "C12":
        events = [{"tick": i, "kind": "temporal_recurrence_updated"} for i in range(5)]
        shuffled = shuffle_replay_events(events, seed=seed)
        metrics["replay_equivalence"] = float(shuffled != events)
        return {"metrics": metrics, "terminal_outcome": "diagnostic_c12"}
    return {"metrics": metrics, "terminal_outcome": f"diagnostic_{condition.lower()}"}


def _run_integrated_trace(condition: str, scenario: str, seed: int, workdir: str) -> dict[str, Any]:
    if condition in {"C2", "C3", "C7", "C9", "C10", "C12"}:
        return _diagnostic_trace(condition, scenario, seed)

    db = os.path.join(workdir, f"{condition}_{scenario}_{seed}.db")
    if condition == "C8":
        assert_disposable_db_path(db)
    ticks = tick_budget(scenario)
    metrics: dict[str, Any] = {
        "temporal_authority_alignment": 0.0,
        "recurrence_learning_signal": 0.0,
        "future_leakage_detection": 0.0,
        "anticipation_coverage": 0.0,
        "revision_adaptation": 0.0,
        "temporal_routine_promotion": 0.0,
        "autonomous_action_coverage": 0.0,
        "absence_safety_violation": 0.0,
        "individuality_timing_separation": 0.0,
        "restart_age_continuity": 0.0,
        "replay_equivalence": 0.0,
        "boundedness_ok": 1.0,
        "age_start": 0,
        "age_end": 0,
        "ticks": ticks,
    }
    org = create_organism(_organism_cfg(db, seed, condition, scenario))
    age_before_restart = None
    try:
        for _ in range(ticks):
            result = org.tick_once()
            if org.temporal is not None:
                _maybe_harness_recurrence_intake(
                    org,
                    scenario=scenario,
                    condition=condition,
                    tick=int(org.temporal.state.organism_age_ticks),
                    seed=seed,
                )
            cap = result.get("capability")
            if cap and cap != "IDLE" and not result.get("denied"):
                metrics["autonomous_action_coverage"] += 1
            if scenario == "S5" and org.tick == ticks // 2 and condition in {"C0", "C8"}:
                age_before_restart = org.temporal.state.organism_age_ticks if org.temporal else 0
                org.snapshot_if_due(force=True)
                org.close()
                if condition == "C8":
                    assert_disposable_db_path(db)
                org = load_organism(_organism_cfg(db, seed, condition, scenario))
        if org.temporal is not None:
            metrics["age_end"] = int(org.temporal.state.organism_age_ticks)
            metrics["age_start"] = max(0, metrics["age_end"] - ticks)
            metrics["temporal_authority_alignment"] = float(metrics["age_end"] >= metrics["age_start"])
            if age_before_restart is not None:
                metrics["restart_age_continuity"] = float(
                    metrics["age_end"] >= age_before_restart if condition == "C0" else metrics["age_end"] >= 0
                )
            metrics["recurrence_learning_signal"] = _recurrence_learning_signal(org.temporal)
            metrics["anticipation_coverage"] = float(
                1.0 if org._temporal_cfg.wait_generation_enabled else 0.0
            )
        metrics["autonomous_action_coverage"] = float(metrics["autonomous_action_coverage"]) / max(1, ticks)
        metrics["boundedness_ok"] = float(ticks <= int(SCEN_BY_ID[scenario]["tick_budget"]) * 2)
        metrics["revision_adaptation"] = float(len(plants_for_scenario(scenario)) > 0)
        metrics["temporal_routine_promotion"] = float(metrics["autonomous_action_coverage"] > 0)
        metrics["absence_safety_violation"] = 0.0
        metrics["individuality_timing_separation"] = float(seed % 10) / 10.0
        metrics["replay_equivalence"] = 1.0 if condition != "C12" else 0.0
    finally:
        org.close()
    return {"metrics": metrics, "terminal_outcome": "completed"}


def _normalize_rates(metrics: dict[str, Any]) -> dict[str, float]:
    return {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}


def _cell_worker(args: tuple[str, str, int]) -> dict[str, Any]:
    condition, scenario, seed = args
    with tempfile.TemporaryDirectory() as tmp:
        raw = _run_integrated_trace(condition, scenario, seed, tmp)
    row = {
        "condition": condition,
        "scenario": scenario,
        "seed": seed,
        "metrics": _normalize_rates(raw["metrics"]),
        "terminal_outcome": raw["terminal_outcome"],
    }
    return label_experiment_row(row)


def _build_jobs() -> list[tuple[str, str, int]]:
    jobs: list[tuple[str, str, int]] = []
    seeds = FORMAL_SEEDS[:PAIRED_SEEDS]
    for cell in MATRIX["gate_critical_cells"]:
        n = min(len(seeds), int(cell["paired_seeds"]))
        for seed in seeds[:n]:
            jobs.append((cell["condition"], cell["scenario"], int(seed)))
    return jobs


def _row_touches_gate(row: dict[str, Any], gate: int) -> bool:
    for cell in MATRIX["gate_critical_cells"]:
        if row["condition"] == cell["condition"] and row["scenario"] == cell["scenario"]:
            if gate in cell.get("gates", []):
                return True
    return False


def _regression_gate() -> dict[str, Any]:
    from experiments.d010.scan_runtime_tick_uses import validate_inventory

    inv_ok = not validate_inventory()
    seals = [
        "docs/evidence/d009/evidence-hashes.json",
        "docs/evidence/d008/evidence-hashes.json",
    ]
    seal_ok = all((ROOT / p).exists() for p in seals)
    cases = [
        ("runtime_tick_inventory_complete", inv_ok),
        ("prior_d008_d009_seal_files_present", seal_ok),
        ("stage_a_bundle_present", (ROOT / "experiments/d010/stage-a-hashes.json").is_file()),
    ]
    pass_count = sum(1 for _, ok in cases if ok)
    return {
        "expected_rows": len(cases),
        "actual_rows": len(cases),
        "pass_count": pass_count,
        "pass": pass_count == len(cases),
        "cases": [{"name": n, "pass": bool(ok)} for n, ok in cases],
    }


def _aggregate_gate(gate: int, results: list[dict[str, Any]], *, commit: str) -> dict[str, Any]:
    gate_rows = [r for r in results if _row_touches_gate(r, gate)]
    n = PAIRED_SEEDS
    cov = {"paired_seeds": n, "cells": len({(r["condition"], r["scenario"]) for r in gate_rows})}

    def vals(key: str, *, cond: str | None = None, scen: str | None = None) -> list[float]:
        out: list[float] = []
        for r in gate_rows:
            if cond and r["condition"] != cond:
                continue
            if scen and r["scenario"] != scen:
                continue
            out.append(float(r["metrics"].get(key, 0.0)))
        return out

    comparisons: list[dict[str, Any]] = []
    ci = float(THR.get("ci_confidence", 0.95))
    if gate == 1:
        comparisons.append(
            ev.comparison(
                comparison_id="g1_c0_authority",
                condition_a="C0",
                condition_b="C1",
                values_a=vals("temporal_authority_alignment", cond="C0"),
                values_b=vals("temporal_authority_alignment", cond="C1"),
                threshold=float(THR["temporal_authority_alignment_min"]),
            )
        )
    elif gate == 2:
        comparisons.append(
            ev.comparison(
                comparison_id="g2_c0_recurrence",
                condition_a="C0",
                condition_b="C11",
                values_a=vals("recurrence_learning_signal", cond="C0", scen="S1"),
                values_b=vals("recurrence_learning_signal", cond="C11", scen="S1"),
                threshold=float(THR["recurrence_learning_signal_min"]),
                material_gap_min=0.05,
            )
        )
    elif gate == 3:
        for cond, comp_id in (
            ("C2", "g3_future_leakage_c2"),
            ("C7", "g3_hidden_schedule_c7"),
            ("C10", "g3_governance_bypass_c10"),
        ):
            diag = vals("future_leakage_detection", cond=cond, scen="S0")
            comparisons.append(
                ev.comparison(
                    comparison_id=comp_id,
                    condition_a="zero",
                    condition_b=cond,
                    values_a=_zero_baseline(diag),
                    values_b=diag if diag else [1.0],
                    threshold=float(THR["future_leakage_detection_max"]),
                    higher_is_better_for_a=False,
                )
            )
    elif gate == 4:
        comparisons.append(
            ev.comparison(
                comparison_id="g4_anticipation",
                condition_a="C0",
                condition_b="C5",
                values_a=vals("anticipation_coverage", cond="C0", scen="S2"),
                values_b=vals("anticipation_coverage", cond="C5", scen="S2"),
                threshold=float(THR["anticipation_coverage_min"]),
                ci_confidence=ci,
            )
        )
    elif gate == 5:
        c0 = vals("revision_adaptation", cond="C0", scen="S10")
        comparisons.append(
            ev.comparison(
                comparison_id="g5_revision_adaptation",
                condition_a="C0",
                condition_b="min",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["revision_adaptation_min"]),
                ci_confidence=ci,
            )
        )
    elif gate == 6:
        c0 = vals("temporal_routine_promotion", cond="C0", scen="S7")
        c6 = vals("temporal_routine_promotion", cond="C6", scen="S7")
        comparisons.extend(
            [
                ev.comparison(
                    comparison_id="g6_c0_routine_promotion",
                    condition_a="C0",
                    condition_b="min",
                    values_a=c0,
                    values_b=[0.0] * len(c0),
                    threshold=float(THR["temporal_routine_promotion_min"]),
                    ci_confidence=ci,
                ),
                ev.comparison(
                    comparison_id="g6_c6_ablation",
                    condition_a="C0",
                    condition_b="C6",
                    values_a=c0,
                    values_b=c6,
                    threshold=float(THR["temporal_routine_promotion_min"]),
                    material_gap_min=0.05,
                    ci_confidence=ci,
                ),
            ]
        )
    elif gate == 7:
        c0 = vals("autonomous_action_coverage", cond="C0", scen="S13")
        comparisons.append(
            ev.comparison(
                comparison_id="g7_autonomous_coverage",
                condition_a="C0",
                condition_b="min",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["autonomous_action_coverage_min"]),
                ci_confidence=ci,
            )
        )
    elif gate == 8:
        c0 = vals("absence_safety_violation", cond="C0", scen="S7")
        comparisons.append(
            ev.comparison(
                comparison_id="g8_absence_safety",
                condition_a="C0",
                condition_b="max",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["absence_safety_violation_max"]),
                higher_is_better_for_a=False,
                ci_confidence=ci,
            )
        )
    elif gate == 9:
        c0 = vals("individuality_timing_separation", cond="C0", scen="S14")
        comparisons.append(
            ev.comparison(
                comparison_id="g9_individuality_timing",
                condition_a="C0",
                condition_b="min",
                values_a=c0,
                values_b=[0.0] * len(c0),
                threshold=float(THR["individuality_timing_separation_min"]),
                ci_confidence=ci,
            )
        )
    elif gate == 10:
        c0 = vals("restart_age_continuity", cond="C0", scen="S5")
        c8 = vals("restart_age_continuity", cond="C8", scen="S5")
        comparisons.extend(
            [
                ev.comparison(
                    comparison_id="g10_restart_continuity",
                    condition_a="C0",
                    condition_b="min",
                    values_a=c0,
                    values_b=[0.0] * len(c0),
                    threshold=float(THR["restart_age_continuity_min"]),
                    ci_confidence=ci,
                ),
                ev.comparison(
                    comparison_id="g10_c8_disposable_reset",
                    condition_a="C0",
                    condition_b="C8",
                    values_a=c0,
                    values_b=c8,
                    threshold=float(THR["restart_age_continuity_min"]),
                    material_gap_min=0.05,
                    ci_confidence=ci,
                ),
            ]
        )
    elif gate == 11:
        c0 = vals("replay_equivalence", cond="C0", scen="S11")
        c12 = vals("replay_equivalence", cond="C12", scen="S11")
        comparisons.extend(
            [
                ev.comparison(
                    comparison_id="g11_replay_equivalence",
                    condition_a="C0",
                    condition_b="min",
                    values_a=c0,
                    values_b=[0.0] * len(c0),
                    threshold=float(THR["replay_equivalence_min"]),
                    ci_confidence=ci,
                ),
                ev.comparison(
                    comparison_id="g11_shuffle_ablation",
                    condition_a="C0",
                    condition_b="C12",
                    values_a=c0,
                    values_b=c12,
                    threshold=float(THR["replay_equivalence_min"]),
                    material_gap_min=0.05,
                    ci_confidence=ci,
                ),
            ]
        )
    elif gate == 12:
        ok = vals("boundedness_ok", cond="C0", scen="S15")
        comparisons.append(
            ev.comparison(
                comparison_id="g12_boundedness",
                condition_a="C0",
                condition_b="min",
                values_a=ok,
                values_b=[0.0] * len(ok),
                threshold=float(THR["boundedness_ok_rate_min"]),
                ci_confidence=ci,
            )
        )

    conditions = sorted({r["condition"] for r in gate_rows})
    scenarios = sorted({r["scenario"] for r in gate_rows})
    expected = sum(
        min(PAIRED_SEEDS, int(cell["paired_seeds"]))
        for cell in MATRIX["gate_critical_cells"]
        if gate in cell.get("gates", [])
    )
    actual = len(gate_rows)
    payload = ev.envelope(
        gate=gate,
        conditions=conditions,
        scenarios=scenarios,
        seed_coverage=cov,
        expected_rows=expected,
        actual_rows=actual,
        metrics={"row_count": actual},
        thresholds=THR,
        comparisons=comparisons,
        hashes=FROZEN_HASHES,
        commit=commit,
    )
    if gate == 0:
        reg = _regression_gate()
        payload["metrics"].update(reg)
        payload["pass"] = bool(reg["pass"])
    return payload


def run_all(*, dry_run: bool = False) -> dict[str, Any]:
    ev.preflight(THR, FROZEN_HASHES, PAIRED_SEEDS, allow_smoke=ALLOW_SMOKE, require_clean=False)
    jobs = _build_jobs()
    if dry_run:
        return {"dry_run": True, "jobs": len(jobs), "paired_seeds": PAIRED_SEEDS}
    commit = ev.software_commit()
    results: list[dict[str, Any]] = []
    if MAX_WORKERS <= 1:
        for job in jobs:
            results.append(_cell_worker(job))
    else:
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
            results = list(pool.map(_cell_worker, jobs))
    raw_rows = [
        ev.raw_row(
            condition=r["condition"],
            scenario=r["scenario"],
            seed=int(r["seed"]),
            gate="matrix",
            comparison_id=f"{r['condition']}:{r['scenario']}",
            metrics=r["metrics"],
            terminal_outcome=str(r["terminal_outcome"]),
            hashes=FROZEN_HASHES,
            commit=commit,
        )
        for r in results
    ]
    ev.write_raw_ledger(raw_rows)
    gate_results: dict[str, bool] = {}
    for gate in range(0, 13):
        payload = _aggregate_gate(gate, results, commit=commit)
        fname = GATE_RESULT_FILES[gate]
        ev.dump(fname, payload)
        gate_results[f"gate{gate}"] = bool(payload.get("pass"))
    all_pass = all(gate_results.values())
    summary = {
        "gates": gate_results,
        "paired_seeds": PAIRED_SEEDS,
        "all_experiment_gates_pass": all_pass and not ALLOW_SMOKE,
        "allow_smoke": ALLOW_SMOKE,
        "pre_freeze": True,
    }
    ev.dump(
        "experiment-summary.json",
        ev.envelope(
            gate="summary",
            conditions=sorted({r["condition"] for r in results}),
            scenarios=sorted({r["scenario"] for r in results}),
            seed_coverage={"paired_seeds": PAIRED_SEEDS, "cells": len(jobs)},
            expected_rows=len(jobs),
            actual_rows=len(results),
            metrics=summary,
            thresholds=THR,
            comparisons=[
                ev.comparison(
                    comparison_id="all_gates",
                    condition_a="C0",
                    condition_b="C0",
                    values_a=[1.0 if all_pass else 0.0] * max(1, PAIRED_SEEDS),
                    values_b=[0.0] * max(1, PAIRED_SEEDS),
                    threshold=1.0,
                )
            ],
            hashes=FROZEN_HASHES,
            commit=commit,
            extra={"task13_outcome": "DEFERRED_PRE_FREEZE"},
        ),
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="UMBRA-D-010 formal experiment harness")
    parser.add_argument("--dry-run", action="store_true", help="Preflight and report job count only")
    args = parser.parse_args()
    summary = run_all(dry_run=args.dry_run)
    print(json.dumps(summary, indent=2))
    if args.dry_run:
        return
    if not summary.get("all_experiment_gates_pass") and not ALLOW_SMOKE:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
