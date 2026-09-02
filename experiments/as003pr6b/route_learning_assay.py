"""R6B bounded operational success/failure assay.

Exactly two bounded organisms are created by this module: one nominal route
episode and one existing-body movement-failure episode.  The assay selects
only candidates already emitted by the ordinary runtime, records no planning
result, and stops as soon as the route episode closes.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any

from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d009.scenario_plants import apply_scenario_plants
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.temporal.config import TemporalConfig
from umbra_core.world_model import WorldModelConfig

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6b-verified-route-learning-r1"
)
SEED = 6103
SCENARIO = "S0"
MAX_TICKS = 8


def _selector(context: dict[str, Any]) -> dict[str, Any]:
    observations = [
        row for row in context.get("observations", [])
        if row.get("kind") == "resource"
    ]
    distance = min(
        (float(row.get("estimated_distance", 999.0)) for row in observations),
        default=999.0,
    )
    desired = "CHARGE" if distance <= 1.3 else "APPROACH"
    pool = context["candidate_pool"]
    for row in pool:
        if row.get("capability") != desired:
            continue
        if (row.get("params") or {}).get("toward") != "resource":
            continue
        from umbra_core.arbitration import Candidate

        return {
            "candidate": Candidate(str(row["capability"]), dict(row.get("params") or {})),
            "trace": {
                "assay": "R6B_ROUTE_LEARNING",
                "desired": desired,
                "distance": distance,
                "selected_emitted_candidate": True,
            },
        }
    # The callback is still constrained to an emitted candidate.  This records
    # an honest assay miss rather than inventing a route action.
    current = context["current_candidate"]
    from umbra_core.arbitration import Candidate

    return {
        "candidate": Candidate(str(current["capability"]), dict(current.get("params") or {})),
        "trace": {
            "assay": "R6B_ROUTE_LEARNING",
            "desired": desired,
            "distance": distance,
            "selected_emitted_candidate": False,
            "fallback": "current_emitted_candidate",
        },
    }


def _config(db_path: Path, trace_path: Path) -> OrganismConfig:
    return OrganismConfig(
        db_path=str(db_path),
        seed=SEED,
        condition="C0",
        snapshot_every=50,
        temporal_enabled=True,
        temporal_config=TemporalConfig(),
        temporal_scenario_id=SCENARIO,
        temporal_scenario_hook=apply_scenario_plants,
        habitat_enabled=True,
        habitat_scenario_id=SCENARIO,
        habitat_scenario_hook=apply_scenario_plants,
        self_model_enabled=True,
        world_model_enabled=True,
        world_model_config=WorldModelConfig(
            learning_enabled=False,
            prediction_enabled=False,
            affordance_learning=False,
            planning_enabled=False,
            route_demand_learning_enabled=True,
        ),
        development_enabled=False,
        memory_enabled=False,
        social_enabled=False,
        individuality_enabled=False,
        embodiment_adapter_enabled=True,
        expression_enabled=False,
        drift_enabled=False,
        wall_time_fn=lambda: 0.0,
        decision_trace_path=str(trace_path),
        experimental_final_selector=_selector,
    )


def _run(label: str, *, force_failure: bool) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"u-r6b-{label}-", dir="/dev/shm") as tmp:
        root = Path(tmp)
        trace_path = root / "decision.jsonl"
        organism = create_organism(_config(root / "organism.sqlite", trace_path))
        try:
            organism.embodiment.attach_habitat_engine(
                HabitatEngine(_habitat_state_for_scenario(SCENARIO))
            )
            organism.embodiment.body.x = 2.0
            organism.embodiment.body.y = 3.0
            organism.embodiment.body.heading = 0.0
            if force_failure:
                # Existing bounded D-002 body fault; no new route truth.
                organism.embodiment.body.movement_reliability = 0.0
            ticks = []
            for _ in range(MAX_TICKS):
                ticks.append(organism.tick_once())
                experiences = [
                    item.to_dict() for item in organism.world_model.route_evidence.experiences
                ]
                if experiences:
                    break
            experiences = [
                item.to_dict() for item in organism.world_model.route_evidence.experiences
            ]
            trace_rows = (
                [json.loads(line) for line in trace_path.read_text().splitlines()]
                if trace_path.exists()
                else []
            )
            return {
                "label": label,
                "seed": SEED,
                "scenario": SCENARIO,
                "max_ticks": MAX_TICKS,
                "ticks_executed": len(ticks),
                "tick_results": ticks,
                "route_experiences": experiences,
                "route_count_bounded": organism.world_model.route_evidence.counts_bounded(),
                "selector_route_requests": sum(
                    1
                    for row in trace_rows
                    if row.get("d014h3d_selector", {}).get("selected_candidate", {}).get("capability")
                    == "APPROACH"
                ),
                "trace_rows": len(trace_rows),
                "force_failure": force_failure,
            }
        finally:
            organism.close()


def main() -> None:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    success = _run("success", force_failure=False)
    failure = _run("failure", force_failure=True)
    result = {
        "schema": "AS003PR6B_OPERATIONAL_ASSAY_V1",
        "classification": "BOUNDED_OPERATIONAL_ACQUISITION",
        "production_authority": False,
        "planning_reader": False,
        "organism_runs": 2,
        "retries": 0,
        "reseeds": 0,
        "success_assay": success,
        "failure_assay": failure,
    }
    # The outer evidence publisher adds atomic publication/readback for the
    # command record.  Keep this harness itself free of evidence interpretation.
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
