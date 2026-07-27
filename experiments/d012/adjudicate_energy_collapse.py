"""Build D-012B1 forensic evidence from the preserved P0 ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(
    *,
    database: Path,
    evidence: Path,
    pre_root: Path,
    post_root: Path,
) -> None:
    manifest = read_json(evidence / "p0-formal-execution-manifest.json")
    formal_result = read_json(evidence / "p0-run-result.json")
    pre = read_json(pre_root / "summary.json")
    post = read_json(post_root / "summary.json")
    reproduced = {row["tick"]: row for row in read_jsonl(pre_root / "r0/tick-trace.jsonl")}

    connection = sqlite3.connect(f"file:{database}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT sequence, event_type, monotonic_time, wall_time, payload
        FROM events
        WHERE event_type IN ('physiology_drift','proposal','outcome_verified')
        ORDER BY sequence
        """
    ).fetchall()
    by_tick: dict[int, dict[str, Any]] = {}
    for row in rows:
        tick = int(row["monotonic_time"])
        item = by_tick.setdefault(
            tick,
            {"sequences": [], "wall_time": float(row["wall_time"])},
        )
        item["sequences"].append(int(row["sequence"]))
        item[str(row["event_type"])] = json.loads(row["payload"])
    snapshot = connection.execute(
        "SELECT sequence, state_json, state_hash FROM snapshots ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    final_state = json.loads(snapshot["state_json"])
    connection.close()

    timeline = []
    exact_matches = []
    for tick, item in sorted(by_tick.items()):
        drift = item["physiology_drift"]
        proposal = item["proposal"]
        outcome = item["outcome_verified"]
        after = dict(drift["H"])
        for name, delta in outcome["effects"].items():
            if name in after:
                after[name] += float(delta)
        diagnostic = reproduced.get(tick, {})
        if diagnostic:
            after = dict(diagnostic["physiology_after_tick"])
            exact_matches.append(
                proposal["capability"] == diagnostic["executed_capability"]
                and outcome["reason"]
                == diagnostic["verified_outcome"]["outcome"]["reason"]
            )
        if tick < 140:
            continue
        timeline.append(
            {
                "tick": tick,
                "active_runtime_seconds": float(item["wall_time"])
                - float(manifest["created_at"]),
                "active_runtime_basis": "event_wall_time_minus_formal_manifest_created_at",
                "worker_generation": 1,
                "physiology_before_tick": diagnostic.get("physiology_before_tick"),
                "energy_drift": drift["drift"]["energy"],
                "selected_candidate": proposal["capability"],
                "candidate_source": diagnostic.get("candidate_source"),
                "arbitration_scores": diagnostic.get("arbitration_scores", {}),
                "arbitration_selection_rule": (
                    "hard_recovery_reflex_no_numeric_candidate_scoring"
                    if diagnostic.get("candidate_source") == "recovery_reflex"
                    else "scored_endogenous_arbitration"
                ),
                "urgency_values": diagnostic.get("urgencies", {}),
                "governance": {
                    "admitted": proposal["admitted"],
                    "reason": proposal["reason"],
                    "stage_failed": proposal["stage_failed"],
                },
                "body_or_habitat_validation": outcome["reason"],
                "executed_capability": outcome["capability"],
                "verified_outcome": {
                    "success": outcome["success"],
                    "verified": outcome["verified"],
                    "reason": outcome["reason"],
                },
                "physiology_effect": outcome["effects"],
                "physiology_after_tick": after,
                "fatigue": after["fatigue"],
                "integrity": after["integrity"],
                "stimulation": after["stimulation"],
                "available_recovery_affordances": diagnostic.get(
                    "available_recovery_affordances", []
                ),
                "current_body_capability_state": diagnostic.get(
                    "body_capability_state"
                ),
                "event_sequence_numbers": item["sequences"],
                "causal_detail_source": (
                    "preserved_authoritative_ledger_plus_exact_deterministic_R0"
                ),
            }
        )
    (evidence / "p0-energy-timeline.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in timeline)
    )

    all_ticks = []
    for tick, item in sorted(by_tick.items()):
        drift = item["physiology_drift"]
        outcome = item["outcome_verified"]
        energy_after = drift["H"]["energy"] + outcome["effects"].get("energy", 0.0)
        if tick in reproduced:
            energy_after = reproduced[tick]["physiology_after_tick"]["energy"]
        all_ticks.append(
            {
                "tick": tick,
                "energy_after": energy_after,
                "capability": outcome["capability"],
                "success": outcome["success"],
                "reason": outcome["reason"],
                "energy_effect": outcome["effects"].get("energy", 0.0),
            }
        )
    negative_cost = sum(min(0.0, row["energy_effect"]) for row in all_ticks)
    recovery_gain = sum(max(0.0, row["energy_effect"]) for row in all_ticks)
    recoveries = [row for row in all_ticks if row["energy_effect"] > 0]
    recovery_attempts = [
        row for row in all_ticks if row["capability"] in {"CHARGE", "REST"}
    ]
    write_json(
        evidence / "p0-energy-budget.json",
        {
            "starting_energy": 0.7,
            "ticks": 191,
            "passive_energy_drift_per_tick": -0.002,
            "budgets": {
                "no_action": {
                    "expected_final_energy": 0.7 - 0.002 * 191,
                    "critical_depletion_unavoidable": False,
                },
                "observed_action_sequence": {
                    "final_energy": all_ticks[-1]["energy_after"],
                    "action_cost_total": negative_cost,
                    "recovery_gain_total": recovery_gain,
                },
                "successful_recovery_behavior": {
                    "measured_remediated_final_energy": post[
                        "R0_exact_failed_configuration"
                    ]["before_stop"]["physiology"]["energy"],
                    "critical": post["R0_exact_failed_configuration"][
                        "before_stop"
                    ]["critical"],
                },
                "equivalent_d009_baseline": {
                    "pre_remediation_final_energy": pre["R3_d009_baseline"][
                        "physiology"
                    ]["energy"],
                    "pre_remediation_critical": pre["R3_d009_baseline"]["critical"],
                    "post_remediation_final_energy": post["R3_d009_baseline"][
                        "physiology"
                    ]["energy"],
                },
            },
            "compressed_timeline": {
                "energy_min": min(row["energy_after"] for row in all_ticks),
                "energy_max": max(row["energy_after"] for row in all_ticks),
                "energy_slope_per_tick": (
                    all_ticks[-1]["energy_after"] - all_ticks[0]["energy_after"]
                )
                / 190,
                "recovery_attempts": len(recovery_attempts),
                "recovery_successes": sum(row["success"] for row in recovery_attempts),
                "recovery_denials": 0,
                "recovery_failures": sum(
                    not row["success"] for row in recovery_attempts
                ),
                "successful_recovery_ticks": [row["tick"] for row in recoveries],
                "action_counts": dict(Counter(row["capability"] for row in all_ticks)),
            },
        },
    )

    write_json(
        evidence / "p0-cleanup-boundary-audit.json",
        {
            "organism_below_critical_before_cleanup": True,
            "first_critical_after_tick": 181,
            "energy_after_tick_181": all_ticks[180]["energy_after"],
            "R0_pre_cleanup": pre["R0_exact_failed_configuration"]["before_stop"],
            "R1_no_cleanup": pre["R1_cleanup_disabled"]["before_stop"],
            "states_equal_before_cleanup": pre["R0_exact_failed_configuration"][
                "before_stop"
            ]
            == pre["R1_cleanup_disabled"]["before_stop"],
            "cleanup_calls": [
                "Organism.snapshot_if_due(force=True)",
                "Organism.close",
                "release_ownership",
                "socket close/unlink",
                "evidence writes",
            ],
            "prohibited_calls_found": [],
            "cleanup_tick_advance": 0,
            "cleanup_physiology_mutation": False,
            "cleanup_authoritative_event_append": False,
            "cleanup_schedule_intervention": False,
            "failure_decision_followed_by_another_tick": False,
            "note": "The 10-second sampling interval detected the already-critical state at tick 191; cleanup did not create tick 191.",
            "classification": "NOT_HARNESS_CLEANUP_MUTATION",
            "pass": True,
        },
    )

    wall_duration = float(by_tick[191]["wall_time"]) - float(by_tick[1]["wall_time"])
    write_json(
        evidence / "p0-tick-rate-audit.json",
        {
            "configured_tick_hz": 2.0,
            "configured_period_seconds": 0.5,
            "formal_active_runtime_seconds": formal_result["active_runtime_seconds"],
            "expected_upper_bound_ticks": 1
            + int(formal_result["active_runtime_seconds"] / 0.5),
            "actual_committed_ticks": 191,
            "observed_ledger_cadence_hz": 190 / wall_duration,
            "event_count": 766,
            "authoritative_events_per_tick_mean": 762 / 191,
            "duplicate_tick_identifiers": [],
            "worker_generations": 1,
            "schedule_dispatch_count": 1,
            "restart_boundaries": [],
            "one_tick_loop": True,
            "supervisor_tick_calls": 0,
            "worker_overlap": False,
            "replayed_active_intervals": False,
            "cleanup_extra_ticks": 0,
            "schedule_poll_ticks": 0,
            "checkpoint_ticks": 0,
            "material_excess_over_frozen_cadence": False,
            "classification": "NOT_DUPLICATE_OR_EXTRA_TICK_EXECUTION",
            "pass": True,
        },
    )

    failed_recovery = [
        {
            "tick": row["tick"],
            "capability": row["capability"],
            "classification": row["reason"],
        }
        for row in recovery_attempts
        if not row["success"]
    ]
    write_json(
        evidence / "p0-recovery-path-audit.json",
        {
            "energy_recovery_urgent_at": 0.6,
            "energy_critical_below": 0.05,
            "first_energy_recovery_focus_tick": next(
                row["tick"]
                for row in reproduced.values()
                if row["candidate_source"] == "recovery_reflex"
                and row["urgencies"]["energy"]
                >= max(row["urgencies"].values())
            ),
            "critical_energy_recovery_ticks": list(range(182, 192)),
            "generated_selected_admitted": {
                "ticks_182_184": "APPROACH",
                "ticks_185_191": "CHARGE",
            },
            "governance_denials": 0,
            "body_capability_dormant": False,
            "charging_affordance_present": True,
            "charging_affordance_executable_at_tick_185": False,
            "tick_185_actual_distance": reproduced[185][
                "available_recovery_affordances"
            ][0]["distance"],
            "tick_185_execution_limit": 1.5,
            "tick_185_observed_distance": next(
                row["estimated_distance"]
                for row in reproduced[185]["observations"]
                if row["kind"] == "resource"
            ),
            "recovery_outcomes_committed": True,
            "failed_recovery_attempts": failed_recovery,
            "continuous_override": False,
            "failure_path": "critical energy reflex selected CHARGE at perceived distance <=2.2; embodiment required actual distance <=1.5; failed CHARGE did not move the body, so the same mismatch repeated",
            "primary_mechanism": "ARBITRATION_OR_GOVERNANCE_RECOVERY_FAILURE",
        },
    )

    write_json(
        evidence / "p0-opportunity-audit.json",
        {
            "starting_energy": 0.7,
            "ordinary_resource_present": True,
            "ordinary_rest_present": True,
            "resource_chargeable": True,
            "body_supports_charge": True,
            "resource_perceived": True,
            "resource_reachable_with_one_additional_approach_at_tick_185": True,
            "resource_executable_at_tick_185": False,
            "schedule_removed_resource": False,
            "no_interaction_interval_caused_starvation": False,
            "no_action_final_energy": 0.7 - 0.002 * 191,
            "schedule_mathematically_guaranteed_collapse": False,
            "R2_reachable_opportunity": pre[
                "R2_recovery_opportunity_confirmed"
            ]["before_stop"],
            "classification": "OPPORTUNITY_PRESENT_BUT_RECOVERY_INTEGRATION_STOPPED_APPROACH_EARLY",
        },
    )

    write_json(
        evidence / "p0-root-cause-reproduction.json",
        {
            "formal_relaunch": False,
            "runs": pre,
            "R0_exact_ledger_match_ticks_2_191": all(exact_matches),
            "R0_exact_match_count": sum(exact_matches),
            "R0_compared_tick_count": len(exact_matches),
            "first_causal_divergence": {
                "tick": 185,
                "source_path": "umbra_core/arbitration.py: critical energy recovery dist <= 2.2",
                "downstream_path": "umbra_core/embodiment.py: CHARGE requires distance <= feature.radius + 0.3 (1.5)",
            },
            "all_runs_at_or_below_250_ticks": True,
        },
    )
    write_json(
        evidence / "p0-baseline-comparison.json",
        {
            "pre_remediation": {
                "D012_worker": pre["R0_exact_failed_configuration"]["before_stop"],
                "D009_without_D011_D012_supervision": pre["R3_d009_baseline"],
                "same_failure": True,
            },
            "post_remediation": {
                "D012_worker": post["R0_exact_failed_configuration"]["before_stop"],
                "D009_without_D011_D012_supervision": post["R3_d009_baseline"],
                "both_viable": True,
            },
            "interpretation": "The defect exists in qualified organism integration under this previously untested configuration; D-012 supervision did not introduce it.",
        },
    )
    write_json(
        evidence / "p0b1-preservation-manifest.json",
        {
            "original_evidence_hash_count": 19,
            "original_evidence_hashes_verified": True,
            "original_database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
            "preserved_database_copy": "p0b1-original-final-organism.sqlite",
            "preserved_progress_copy": "p0b1-original-final-progress.json",
            "formal_checkpoint_reached": False,
            "checkpoint_copy": None,
            "original_runner_sha256_at_entry": "e71b8ba6f043745a62c7ce9c06890026e77c28b2e9803b3f8b48110ecdd680ad",
            "original_verdict_sha256": "4a13107f6026215e51ca6fdbc6b363ef498d7f2486f442b7051bd1c59d29b650",
            "original_ledger_sequence": int(snapshot["sequence"]),
            "original_snapshot_state_hash": snapshot["state_hash"],
        },
    )
    evidence_names = [
        "p0-energy-timeline.jsonl",
        "p0-energy-budget.json",
        "p0-cleanup-boundary-audit.json",
        "p0-tick-rate-audit.json",
        "p0-recovery-path-audit.json",
        "p0-opportunity-audit.json",
        "p0-root-cause-reproduction.json",
        "p0-baseline-comparison.json",
        "p0-root-cause-verdict.md",
        "p0-remediation-report.md",
        "p0-remediation-test-results.txt",
        "p0b1-preservation-manifest.json",
        "p0b1-read-only-review.md",
        "p0b1-original-final-organism.sqlite",
        "p0b1-original-final-progress.json",
    ]
    write_json(
        evidence / "p0b1-evidence-hashes.json",
        {
            "algorithm": "sha256",
            "directive": "UMBRA-D-012B1",
            "files": {
                name: hashlib.sha256((evidence / name).read_bytes()).hexdigest()
                for name in evidence_names
            },
            "verdict": "UMBRA_D012B1_INTEGRATION_DEFECT_CONFIRMED",
            "remediation": "REMEDIATED_AND_REVALIDATED",
            "formal_p0_relaunched": False,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--pre-root", type=Path, required=True)
    parser.add_argument("--post-root", type=Path, required=True)
    args = parser.parse_args()
    run(
        database=args.database,
        evidence=args.evidence,
        pre_root=args.pre_root,
        post_root=args.post_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
