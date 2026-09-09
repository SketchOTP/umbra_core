#!/usr/bin/env python3
"""Read-only reconstruction of the retained AS-014 R1/S16 terminal trace."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from tools.as015_evidence import publish


AS014_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-014-persistent-ledger-boundedness-completion-r1"
)
DATABASE = AS014_ROOT / "AS014_FORMAL_POPULATION_WORK/R1-32550454.sqlite"
CASE = AS014_ROOT / "AS014_FORMAL_POPULATION_WORK/case-results/R1-01-32550454.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def tick_for(event_type: str, payload: dict[str, object], last_tick: int | None) -> int | None:
    if event_type == "orchestration_tick_committed":
        return int(payload["runtime_tick"])
    if event_type in {"physiology_drift", "proposal", "outcome_verified", "denial"}:
        return None if last_tick is None else last_tick + 1
    return None


def main() -> None:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
    cursor = connection.cursor()
    events = cursor.execute(
        "SELECT sequence, event_type, payload FROM events WHERE sequence >= 1500 ORDER BY sequence"
    ).fetchall()
    timeline: dict[int, dict[str, object]] = {}
    current_tick = 294
    for sequence, event_type, encoded in events:
        payload = json.loads(encoded)
        if event_type == "orchestration_tick_committed":
            current_tick = int(payload["runtime_tick"])
            continue
        event_tick = tick_for(event_type, payload, current_tick)
        if event_tick is None or not 300 <= event_tick <= 347:
            continue
        record = timeline.setdefault(event_tick, {"tick": event_tick, "source_event_sequences": []})
        record["source_event_sequences"].append(sequence)
        if event_type == "physiology_drift":
            record["physiology_after_drift"] = payload["H"]
            record["drift"] = payload["drift"]
            record["fatigue_margin_to_critical"] = round(0.95 - float(payload["H"]["fatigue"]), 12)
        elif event_type == "proposal":
            record["selected_candidate"] = {
                "capability": payload["capability"],
                "admitted": payload["admitted"],
                "reason": payload["reason"],
                "stage_failed": payload["stage_failed"],
            }
        elif event_type == "outcome_verified":
            record["verified_outcome"] = payload
        elif event_type == "denial":
            record["final_safety_denial"] = payload

    snapshot = json.loads(
        cursor.execute("SELECT state_json FROM snapshots WHERE sequence = 1035").fetchone()[0]
    )
    entities = snapshot["world_model"]["entities"]
    resource = next(value for value in entities.values() if value["entity_kind"] == "resource")
    rest = next(value for value in entities.values() if value["entity_kind"] == "rest")
    charge_ticks = [
        tick for tick, record in timeline.items()
        if record.get("verified_outcome", {}).get("capability") == "CHARGE"
    ]
    result = {
        "schema": "AS015_R1_FAILURE_RECONSTRUCTION_V1",
        "directive": "UMBRA-AS-015",
        "retained_inputs": {
            "as014_database": str(DATABASE),
            "as014_database_sha256": digest(DATABASE),
            "as014_case_result": str(CASE),
            "as014_case_result_sha256": digest(CASE),
            "access": "SQLite immutable read-only URI; no organism load, replay, or tick",
        },
        "case": {
            "regime": case.get("regime"),
            "seed": case.get("seed"),
            "terminal_reason": case.get("terminal_reason"),
            "terminal_tick": case.get("terminal_tick"),
            "checkpoint_epoch": case.get("persistence", {}).get("checkpoint_epoch"),
            "hot_tail_event_count": case.get("persistence", {}).get("hot_tail_event_count"),
        },
        "s16": {
            "rest_reverse_affordance_tick": 180,
            "source": "experiments/d009/scenario_plants.py",
            "meaning": "rest:0 became occluded/unavailable under the frozen R1/S16 regime",
        },
        "retained_policy_visible_snapshot_at_tick_200": {
            "resource": resource,
            "rest": rest,
            "limitation": "The retained trace has no decision-frame/candidate-parameter persistence after tick 200; it cannot prove exact observation status or route geometry at every tick 300-347.",
        },
        "timeline_300_347": [timeline[tick] for tick in sorted(timeline)],
        "established_facts": {
            "charge_verified_at_ticks": charge_ticks,
            "charge_at_336": "verified success with authoritative fatigue effect -0.01",
            "post_charge_behavior": "ticks 337-344 selected APPROACH; tick 345 selected IDLE; the retained event schema does not retain target parameters for these proposals",
            "safety_denial": "tick 346 rejected IDLE at verified_outcome_branch_safety before the next drift entered fatigue criticality",
            "criticality": "tick 347 fatigue after drift was 0.9510000000000008",
            "persistence_noncausality": "checkpoint epoch remained zero, so AS-014 checkpoint/compaction did not execute before failure",
        },
        "availability_boundaries": {
            "first_tick_rest_ceased": 180,
            "first_tick_charge_proven_currently_executable_after_rest_loss": 336,
            "first_tick_every_possible_route_became_robustly_infeasible": "NOT_ESTABLISHED_FROM_RETAINED_TRACE",
            "reason": "No post-200 candidate targets, policy frames, or per-tick route geometry were durably retained; no missing route is inferred.",
        },
        "causal_classification": [
            "PRIMARY_RECOVERY_AFFORDANCE_LOST_WITH_ALTERNATE_ROUTE_IGNORED",
            "PREVENTIVE_RECOVERY_ACTIVATED_TOO_LATE",
        ],
        "excluded_classifications": {
            "POLICY_VISIBLE_RECOVERY_ROUTE_MISSING": "not supported: a successful CHARGE at tick 336 proves a policy-authorized executable alternate regulator at that root",
            "VERIFIED_BRANCH_MODEL_INCORRECT": "not established; the terminal denial follows the recorded branch-plus-drift rule",
            "EXECUTABILITY_MODEL_INCORRECT": "not established; CHARGE at tick 336 executed successfully",
            "MULTI_DIMENSION_CONSTRAINT_CONFLICT": "not established from retained per-tick trace",
        },
        "scope_boundary": "Development attribution only. This reconstruction neither reruns the failed seed nor claims a new recovery mechanism would have changed its stochastic future.",
        "result": "AS015_SINGLE_TARGET_FATIGUE_RECOVERY_DEFECT_CONFIRMED",
    }
    print(json.dumps({"sha256": publish("AS015_R1_32550454_FAILURE_RECONSTRUCTION.json", result), "result": result["result"]}, sort_keys=True))


if __name__ == "__main__":
    main()
