"""Bounded, non-formal D-012B1 energy-collapse reproductions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d012.campaign_supervisor import freeze_hash
from experiments.d012.database_ownership import read_ownership
from experiments.d012.organism_worker import organism_config
from experiments.d012.process_identity import identity_matches
from experiments.d012.worker_launcher import WorkerClient, manifest_for
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.state import FreeLocation
from umbra_core.runtime import create_organism


EXP = Path(__file__).resolve().parent


def worker_run(root: Path, *, cleanup: bool, reachable: bool = False) -> dict[str, Any]:
    root.mkdir(parents=True)
    execution_id = f"d012b1-{root.name}"
    manifest = manifest_for(
        root,
        execution_id=execution_id,
        generation=1,
        ownership_generation=1,
        freeze_manifest_hash=freeze_hash(EXP),
        active_runtime=0.0,
        database_path=root / "organism.sqlite",
        tick_period_seconds=0.5,
        diagnostic_trace_path=str(root / "tick-trace.jsonl"),
        diagnostic_recovery_reachable=reachable,
    )
    client = WorkerClient.launch(root / "worker-manifest-1.json", manifest)
    try:
        started = client.request("START")
        scheduled = client.request("RUN_EVENT", event_index=0)
        client.request("RUN_DIAGNOSTIC_TICKS", count=190)
        metrics = client.request("METRICS")
    except BaseException:
        client.force_kill()
        client.socket_path.unlink(missing_ok=True)
        raise
    before_stop = {
        "tick": metrics["metrics"]["tick"],
        "physiology": metrics["metrics"]["physiology"],
        "critical": metrics["metrics"]["physiology_critical"],
        "chain_tip": metrics["chain_tip"],
        "organism_id": metrics["organism_id"],
    }
    if cleanup:
        client.shutdown(95.5)
        cleanup_mode = "quiesce_snapshot_close"
    else:
        client.force_kill()
        client.socket_path.unlink(missing_ok=True)
        cleanup_mode = "force_kill_without_quiesce"
        reclaim = manifest_for(
            root,
            execution_id=execution_id,
            generation=2,
            ownership_generation=2,
            freeze_manifest_hash=freeze_hash(EXP),
            active_runtime=95.5,
            reclaim_dead=True,
            database_path=root / "organism.sqlite",
        )
        cleanup_client = WorkerClient.launch(root / "worker-manifest-2.json", reclaim)
        cleanup_client.request("QUIESCE", active_runtime=95.5)
        cleanup_client.force_kill()
        cleanup_client.socket_path.unlink(missing_ok=True)
    owner = read_ownership(root / "database-ownership.json")
    return {
        "worker_architecture": "spawn_only_distinct_process",
        "seed": 12012,
        "schedule_prefix": scheduled["event"]["event"],
        "start_tick": started["chain_tip"],
        "before_stop": before_stop,
        "cleanup_mode": cleanup_mode,
        "trace_path": str(root / "tick-trace.jsonl"),
        "worker_alive": identity_matches(client.pid, client.identity),
        "socket_exists": (root / "organism-worker-1.sock").exists(),
        "ownership_status": None if owner is None else owner["status"],
    }


def d009_baseline(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True)
    organism = create_organism(organism_config(root / "organism.sqlite"))
    organism._ensure_development_intervention()
    organism._ensure_memory_history()
    organism._ensure_social_history()
    organism._ensure_individuality_history()
    engine = HabitatEngine(_habitat_state_for_scenario("S2"))
    for obj in engine.snapshot_view().objects.values():
        if isinstance(obj.location, FreeLocation):
            engine.commit_free_location(
                obj.object_id, obj.location.x + 0.001, obj.location.y
            )
            break
    organism.embodiment.attach_habitat_engine(engine)
    organism.run_ticks(191)
    result = {
        "architecture": "qualified_d009_organism_without_d011_d012_supervision",
        "seed": 12012,
        "tick": organism.tick,
        "physiology": organism.phys.as_dict(),
        "critical": organism.phys.critical_any(),
        "chain_tip": organism.store.last_sequence(),
        "organism_id": organism.identity.agent_id,
    }
    organism.close()
    return result


def run(root: Path) -> dict[str, Any]:
    if root.exists():
        raise FileExistsError(root)
    root.mkdir(parents=True)
    result = {
        "formal_relaunch": False,
        "maximum_committed_ticks": 191,
        "R0_exact_failed_configuration": worker_run(root / "r0", cleanup=True),
        "R1_cleanup_disabled": worker_run(root / "r1", cleanup=False),
        "R2_recovery_opportunity_confirmed": worker_run(
            root / "r2", cleanup=True, reachable=True
        ),
        "R3_d009_baseline": d009_baseline(root / "r3"),
    }
    (root / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
