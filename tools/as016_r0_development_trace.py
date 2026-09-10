#!/usr/bin/env python3
"""Preserve the AS-016 excluded R0 diagnostic authority path once."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as014.qualification import _ensure_histories
from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.as016.full_config import config, fingerprint
from tools.as016_evidence import ROOT as EVIDENCE_ROOT
from tools.as016_evidence import publish
from umbra_core.decision_trace import DecisionTraceSink
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism


SEED = 41616031
WORK = EVIDENCE_ROOT / "AS016_R0_41616031_DEVELOPMENT_TRACE_WORK_V1"
TRACE = WORK / "decision-trace.jsonl"
TRACE_START_TICK = 2_064
HORIZON = 4_000


def main() -> None:
    if WORK.exists():
        raise FileExistsError(f"create_once_development_work_exists:{WORK}")
    WORK.mkdir(parents=True)
    database = WORK / f"R0-{SEED}.sqlite"
    organism = create_organism(config(SEED, database, "R0"))
    _ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario("S0"))
    organism.embodiment.attach_habitat_engine(engine)
    organism.embodiment.body.x, organism.embodiment.body.y = 4.0, 3.0
    organism.perception.perceive_habitat_objects(organism.embodiment, 1.0, organism.rng)
    actions: dict[str, int] = {}
    first_no_safe: int | None = None
    failure: dict[str, object] | None = None
    started = time.monotonic()
    try:
        for _ in range(HORIZON):
            if organism.tick + 1 == TRACE_START_TICK:
                organism._decision_trace = DecisionTraceSink(TRACE)
            decision = organism.tick_once()
            capability = str(decision.get("capability"))
            actions[capability] = actions.get(capability, 0) + 1
            if decision.get("no_safe_action") and first_no_safe is None:
                first_no_safe = organism.tick
            if organism.phys.critical_any():
                failure = {
                    "tick": organism.tick,
                    "physiology": organism.phys.as_dict(),
                    "result": decision,
                }
                break
        organism.store.validate_chain()
        row = {
            "schema": "AS016_R0_DEVELOPMENT_CASE_V1",
            "directive": "UMBRA-AS-016",
            "regime": "R0",
            "scenario": "S0",
            "seed": SEED,
            "ticks": organism.tick,
            "target_ticks": HORIZON,
            "terminal": "completed" if failure is None and organism.tick >= HORIZON else "scientific_failure",
            "critical_failure": failure,
            "first_no_safe_action": first_no_safe,
            "actions": actions,
            "configuration": fingerprint(organism.config),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "trace_start_tick": TRACE_START_TICK,
        }
    finally:
        organism.close_decision_trace()
        organism.close()
    result = {
        "schema": "AS016_R0_DEVELOPMENT_TRACE_V1",
        "directive": "UMBRA-AS-016",
        "classification": "excluded_development_trace_not_formal_qualification",
        "seed": SEED,
        "formal_seeds_used": [],
        "work_directory": str(WORK),
        "decision_trace_path": str(TRACE),
        "decision_trace_exists": TRACE.exists(),
        "decision_trace_bytes": TRACE.stat().st_size if TRACE.exists() else 0,
        "case": row,
    }
    digest = publish("AS016_R0_41616031_DEVELOPMENT_TRACE_V1.json", result)
    print(json.dumps({"terminal": row["terminal"], "sha256": digest}, sort_keys=True))
    if row["terminal"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
