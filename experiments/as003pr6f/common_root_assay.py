"""One-shot R6F common-root route acquisition assay.

This module is intentionally limited to one ordinary organism run.  It does
not install a final selector, read planning evidence, execute a comparison
candidate, or alter any owner.  After a verified route experience is acquired,
the next decision root and its ordinary IDLE/MOVE pool are captured for pure
offline R6E relation analysis.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d009.scenario_plants import apply_scenario_plants
from umbra_core.arbitration import Candidate
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.recoverability.contracts import candidate_is_admissible
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.temporal.config import TemporalConfig
from umbra_core.util import canonical_fingerprint, verified_outcome_effect_branches
from umbra_core.world_model import WorldModelConfig


EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6f-prospective-common-root-option-r1"
)
BASELINE = "670808a93de5d7a2eca4b9b237cf58b084fded30"
SCENARIO = "S0"
SEED_DERIVATION = f"UMBRA-AS-003P-R6F|{BASELINE}|{SCENARIO}"
SEED_DIGEST = hashlib.sha256(SEED_DERIVATION.encode()).hexdigest()
SEED = int(SEED_DIGEST, 16) % 100000
MAX_TICKS = 500


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
        experimental_final_selector=None,
    )


def _entity_policy_rows(organism: Any) -> list[dict[str, Any]]:
    """Project persisted WorldModel entities without Habitat truth."""
    result: list[dict[str, Any]] = []
    for entity in organism.world_model.entities.values():
        state = dict(entity.estimated_state)
        result.append(
            {
                "kind": entity.entity_kind,
                "relative_direction": state.get("relative_direction", 0.0),
                "estimated_distance": state.get("estimated_distance", 0.0),
                "confidence": entity.confidence,
                "uncertainty": entity.uncertainty,
                "distance_support_upper_bound": entity.distance_support_upper_bound,
                "support_center_dx": entity.support_center_dx,
                "support_center_dy": entity.support_center_dy,
                "support_radius": entity.support_radius,
                "support_provenance": entity.support_provenance,
                "support_source_kind": entity.support_source_kind,
                "support_semantics": "VERIFIED_OBSERVED_SUPPORT",
                "support_body_schema_id": entity.support_body_schema_id,
                "fact_kind": entity.fact_kind,
                "source": "world_model_root_state",
                "verified_recovery_count": entity.verified_recovery_count,
                "last_verified_success_tick": entity.last_verified_success_tick,
            }
        )
    return result


def _candidate_record(candidate: Candidate, *, emitted: bool, hard_admissible: bool) -> dict[str, Any]:
    return {
        "capability": candidate.capability,
        "params": dict(candidate.params),
        "emitted": emitted,
        "hard_admissible": hard_admissible,
        "identity": canonical_fingerprint(
            {"capability": candidate.capability, "params": dict(candidate.params)}
        ),
    }


def _publish(name: str, value: dict[str, Any]) -> str:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    target = EVIDENCE_ROOT / name
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=EVIDENCE_ROOT)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(EVIDENCE_ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    readback = target.read_bytes()
    if readback != payload:
        raise RuntimeError(f"evidence_readback_mismatch:{name}")
    return hashlib.sha256(readback).hexdigest()


def run_once() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="u-r6f-", dir="/dev/shm") as temporary:
        root = Path(temporary)
        trace_path = root / "decision.jsonl"
        organism = create_organism(_config(root / "organism.sqlite", trace_path))
        try:
            organism.embodiment.attach_habitat_engine(
                HabitatEngine(_habitat_state_for_scenario(SCENARIO))
            )
            # Preserve the existing R6B route-assay starting body placement.
            organism.embodiment.body.x = 2.0
            organism.embodiment.body.y = 3.0
            organism.embodiment.body.heading = 0.0

            ticks: list[dict[str, Any]] = []
            route = None
            for _ in range(MAX_TICKS):
                ticks.append(organism.tick_once())
                experiences = list(organism.world_model.route_evidence.experiences)
                if experiences:
                    route = experiences[0]
                    break

            trace_rows = (
                [json.loads(line) for line in trace_path.read_text().splitlines()]
                if trace_path.exists()
                else []
            )
            if route is None:
                return {
                    "schema": "AS003PR6F_OPERATIONAL_ACQUISITION_RESULT_V1",
                    "status": "COMMON_ROOT_ACQUISITION_REACHABILITY_FAIL",
                    "seed": SEED,
                    "seed_derivation": SEED_DERIVATION,
                    "scenario": SCENARIO,
                    "max_ticks": MAX_TICKS,
                    "ticks_executed": len(ticks),
                    "tick_results": ticks,
                    "trace_rows": len(trace_rows),
                    "route_experience": None,
                    "organism_runs": 1,
                    "retries": 0,
                    "reseeds": 0,
                    "planning_reader": False,
                }

            root_tick = int(organism.tick) + 1
            root_state = organism.authoritative_state()
            root_snapshot_id = organism.snapshot_if_due(force=True)
            body_schema_id = organism.self_model.active.body_schema_id
            entity_rows = _entity_policy_rows(organism)
            emitted = organism.arbitrator.generate_candidates(
                organism.phys, entity_rows, root_tick
            )
            by_key = {
                (candidate.capability, canonical_fingerprint(candidate.params)): candidate
                for candidate in emitted
            }
            pair_specs = (
                ("IDLE", {}),
                ("MOVE", {"heading_delta": 0.0, "step": 1.0}),
            )
            pair: list[dict[str, Any]] = []
            for capability, params in pair_specs:
                key = (capability, canonical_fingerprint(params))
                candidate = by_key.get(key)
                if candidate is None:
                    pair.append(
                        {
                            "capability": capability,
                            "params": params,
                            "emitted": False,
                            "hard_admissible": False,
                        }
                    )
                    continue
                admissible = candidate_is_admissible(
                    candidate,
                    physiology=organism.phys,
                    observations=entity_rows,
                    arbitration_state=organism.arbitrator.state,
                    effect_branches=verified_outcome_effect_branches(candidate.capability),
                )
                pair.append(_candidate_record(candidate, emitted=True, hard_admissible=admissible))

            route_dict = route.to_dict()
            exact_entity = organism.world_model.entities.get(route.opportunity_entity_id)
            resource_rows = [
                row for row in entity_rows if row.get("kind") == route.opportunity_entity_kind
            ]
            current_route = None
            move_destroys = False
            if exact_entity is not None:
                current_route = organism.arbitrator._energy_route_budget(
                    organism.phys,
                    {
                        **exact_entity.to_dict(),
                        **exact_entity.estimated_state,
                    },
                )
                move_destroys = organism.arbitrator._ordinary_action_destroys_recovery_route(
                    organism.phys,
                    {
                        **exact_entity.to_dict(),
                        **exact_entity.estimated_state,
                    },
                    Candidate("MOVE", {"heading_delta": 0.0, "step": 1.0}),
                )
            return {
                "schema": "AS003PR6F_OPERATIONAL_ACQUISITION_RESULT_V1",
                "status": "COMMON_ROOT_ACQUIRED",
                "seed": SEED,
                "seed_derivation": SEED_DERIVATION,
                "scenario": SCENARIO,
                "max_ticks": MAX_TICKS,
                "ticks_executed": len(ticks),
                "tick_results": ticks,
                "trace_rows": len(trace_rows),
                "route_experience": route_dict,
                "route_learning_tick": int(route.final_tick),
                "root_tick": root_tick,
                "root_snapshot_id": root_snapshot_id,
                "root_state_fingerprint": canonical_fingerprint(root_state),
                "root_state": root_state,
                "body_schema_id": body_schema_id,
                "root_policy_entity_rows": entity_rows,
                "root_resource_row_count": len(resource_rows),
                "ordinary_emitted_candidate_count": len(emitted),
                "candidate_pair": pair,
                "current_route": current_route,
                "move_destroys_existing_route_margin": move_destroys,
                "candidate_pair_executed_as_intervention": False,
                "planning_reader": False,
                "organism_runs": 1,
                "retries": 0,
                "reseeds": 0,
            }
        finally:
            organism.close()


def main() -> None:
    result = run_once()
    digest = _publish("AS003PR6F_OPERATIONAL_ACQUISITION_RESULT.json", result)
    print(json.dumps({"artifact_sha256": digest, "status": result["status"], "organism_runs": 1}, sort_keys=True))


if __name__ == "__main__":
    main()
