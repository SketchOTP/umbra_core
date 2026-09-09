#!/usr/bin/env python3
"""Targeted development proof for AS-015 kernel activation and dormancy.

This is deliberately a short, non-formal S16 trace.  It does not consume a
formal population seed or replace the population qualification.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.as014.qualification import _ensure_histories
from experiments.as015.full_config import BASELINE, DIRECTIVE, config
from experiments.d009.run_experiment import _habitat_state_for_scenario
from tools.as015_evidence import ROOT, publish
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism, restore_habitat_engine_from_checkpoint


SEED = 41515015
HORIZON = 450


def main() -> None:
    # The first pre-lock diagnostic completed organism execution but its own
    # restart observation incorrectly required a compaction checkpoint.  Keep
    # that partial work immutable and run this corrected authority-path proof
    # in a new create-once work area.
    work = ROOT / "AS015_KERNEL_APPLICABILITY_REATTACHMENT_WORK"
    if work.exists():
        raise FileExistsError(work)
    work.mkdir(parents=True)
    db, trace = work / "kernel.sqlite", work / "decision-trace.jsonl"
    value = config(SEED, db, "R1")
    value.decision_trace_path = str(trace)
    organism = create_organism(value)
    _ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario("S16"))
    organism.embodiment.attach_habitat_engine(engine)
    organism.embodiment.body.x, organism.embodiment.body.y = 4.0, 3.0
    organism.perception.perceive_habitat_objects(organism.embodiment, 1.0, organism.rng)
    try:
        for _ in range(HORIZON):
            organism.tick_once()
        organism.snapshot_if_due(force=True)
        before = dict(organism.arbitrator.state.last_viability_kernel or {})
        habitat_state = copy.deepcopy(engine.state)
        organism.close()
        restored = load_organism(config(SEED, db, "R1"))
        restored_engine = HabitatEngine(copy.deepcopy(habitat_state))
        restored.embodiment.attach_habitat_engine(restored_engine)
        binding = restored.embodiment.habitat_authority_binding
        view = restored_engine.snapshot_view()
        if binding is None or binding["habitat_id"] != view.habitat_id or binding["state_hash"] != view.state_hash:
            raise RuntimeError("AS015_KERNEL_PROOF_HABITAT_REATTACHMENT_INVALID")
        after = dict(restored.arbitrator.state.last_viability_kernel or {})
        restored.close()
    except BaseException:
        organism.close()
        raise

    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    activations = [row["viability_kernel"] for row in rows if row.get("viability_kernel")]
    active_ticks = [int(item["active_tick"]) for item in activations]
    dormant_rows = [
        row
        for row in rows
        if not (row.get("critical_recovery_context") or {}).get("active_recovery_needs")
        and row.get("viability_kernel") is None
    ]
    invalid_route_fields = [
        key
        for item in activations
        for route in item.get("routes", [])
        for key in route
        if key in {"object_id", "entity_id", "habitat_id", "coordinates", "confidence"}
    ]
    result: dict[str, Any] = {
        "schema": "AS015_KERNEL_APPLICABILITY_PROOF_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "classification": "NONFORMAL_DEVELOPMENT_EVIDENCE",
        "seed": SEED,
        "horizon": HORIZON,
        "formal_seeds_used": [],
        "activation_count": len(activations),
        "activation_ticks": active_ticks,
        "activation_examples": activations[:8],
        "dormant_tick_count": len(dormant_rows),
        "dormant_samples": [int(row["tick"]) for row in dormant_rows[:8]],
        "policy_source_only": not invalid_route_fields,
        "forbidden_route_fields": sorted(set(invalid_route_fields)),
        "branch_safety_unchanged": all(
            item.get("branch_safety") == "existing_verified_branch_safety_unchanged"
            for item in activations
        ),
        "restart_preserves_last_kernel_provenance": before == after and bool(after),
        "restart_habitat_hash": restored_engine.snapshot_view().state_hash,
        "result": "PASS" if activations and dormant_rows and before == after and not invalid_route_fields else "FAIL",
    }
    publish("AS015_KERNEL_APPLICABILITY_PROOF.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
