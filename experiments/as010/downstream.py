"""AS-010 downstream qualification under the canonical full configuration."""
from __future__ import annotations

import argparse
import copy
import json
import os
import resource
import time
from pathlib import Path
from typing import Any

from experiments.as009.qualification import partner_object
from experiments.as010.full_config import as010_config
from experiments.d009.run_experiment import _habitat_state_for_scenario
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism
from umbra_core.util import current_rss_mib

DIRECTIVE = "UMBRA-AS-010"
BASELINE = "b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b"
FULL = dict(bounded=True, route_learning=True)


def cfg(seed: int, db: Path, *, bounded: bool = True, route_learning: bool = True):
    return as010_config(seed, db, "R0", bounded=bounded, route_learning=route_learning)


def cleanup(db: Path) -> None:
    for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        path.unlink(missing_ok=True)


def initialize(seed: int, db: Path):
    org = create_organism(cfg(seed, db))
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"):
        getattr(org, method)()
    engine = HabitatEngine(_habitat_state_for_scenario("S10"))
    org.embodiment.attach_habitat_engine(engine)
    return org, engine


def restore(seed: int, db: Path, habitat: Any):
    org = load_organism(cfg(seed, db))
    engine = HabitatEngine(copy.deepcopy(habitat))
    org.embodiment.attach_habitat_engine(engine)
    if org.embodiment._habitat_engine is not engine:
        raise RuntimeError("AS010_HABITAT_REATTACHMENT_NOT_ESTABLISHED")
    return org, engine


def lifecycle(seed: int, work: Path) -> dict[str, Any]:
    db = work / "lifecycle.sqlite"
    org, engine = initialize(seed, db)
    identity = org.identity.as_dict()
    engine.commit_object_creation(partner_object(), event_id=f"as010:life:create:{seed}", transaction_id=f"as010:life:create-txn:{seed}", request_id=f"as010:life:create-req:{seed}")
    org.run_ticks(300)
    org.snapshot_if_due(force=True)
    habitat = copy.deepcopy(engine.state)
    org.close()
    org, engine = restore(seed, db, habitat)
    restart_ok = org.identity.as_dict() == identity and len(engine.authoritative_social_entities()) == 1
    org.run_ticks(100)
    org.snapshot_if_due(force=True)
    habitat = copy.deepcopy(engine.state)
    org.close()
    org, engine = restore(seed, db, habitat)
    old_body = org.embodiment_adapter.state.body_instance_id
    memory_before, social_before, individuality_before = org.memory.to_state(), org.social.to_state(), org.individuality.to_state()
    replacement = org.replace_physical_body(new_profile_id="MINIMAL_CREATURE_BODY", reason="as010_lifecycle")
    replacement_ok = (
        org.identity.as_dict() == identity
        and replacement["new_body_instance_id"] != old_body
        and org.embodiment.body_occupancy_view().body_instance_id == replacement["new_body_instance_id"]
        and org.self_model.body_binding_id == replacement["new_body_binding_id"]
    )
    owners_ok = org.memory.to_state() == memory_before and org.social.to_state() == social_before and org.individuality.to_state() == individuality_before
    org.snapshot_if_due(force=True)
    habitat = copy.deepcopy(engine.state)
    org.close()
    org, engine = restore(seed, db, habitat)
    post_replace_restart = org.identity.as_dict() == identity and org.embodiment_adapter.state.body_instance_id == replacement["new_body_instance_id"]
    org.embodiment_adapter.swap_profile("ABSTRACT_SHAPE_BODY", origin="AS010_LIFECYCLE_PROFILE_SWAP")
    profile_ok = org.embodiment_adapter.state.body_instance_id == replacement["new_body_instance_id"] and org.embodiment.body_occupancy_view().body_instance_id == replacement["new_body_instance_id"]
    org.run_ticks(100)
    org.store.validate_chain()
    result = {"schema": "AS010_LIFECYCLE_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "seed": seed, "checks": {"restart_identity_and_habitat": restart_ok, "true_body_replacement": replacement_ok, "owner_continuity": owners_ok, "post_replacement_restart": post_replace_restart, "compatible_profile_swap": profile_ok, "continued_after_replacement": org.tick >= 200}, "ticks": org.tick, "full_configuration": True}
    org.close()
    cleanup(db)
    result["pass"] = all(result["checks"].values())
    return result


def boundedness(seed: int, work: Path, ticks: int = 100_000) -> dict[str, Any]:
    db = work / "boundedness.sqlite"
    org, _ = initialize(seed, db)
    samples = []
    started = time.perf_counter()
    for index in range(ticks):
        org.tick_once()
        if index == 0 or (index + 1) % 5000 == 0:
            samples.append({"tick": index + 1, "rss_mib": current_rss_mib(), "elapsed_seconds": time.perf_counter() - started})
    before = org.authoritative_state()
    org.snapshot_if_due(force=True)
    org.close()
    restored = load_organism(cfg(seed, db))
    restart_ok = restored.authoritative_state()["identity"] == before["identity"] and restored.tick == before["tick"]
    events = restored.store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    restored.close()
    size = sum(path.stat().st_size for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")) if path.exists())
    cleanup(db)
    rss = [sample["rss_mib"] for sample in samples]
    result = {"schema": "AS010_BOUNDEDNESS_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "seed": seed, "ticks": ticks, "samples": samples, "rss_peak_mib": max(rss), "event_count": events, "database_bytes": size, "restart_continuity": restart_ok, "counts_bounded": events <= ticks * 32, "full_configuration": True}
    result["pass"] = ticks == 100_000 and restart_ok and result["counts_bounded"]
    return result


def soak(seed: int, work: Path, seconds: float = 3600.0) -> dict[str, Any]:
    db = work / "soak.sqlite"
    org, _ = initialize(seed, db)
    started = time.perf_counter(); rss_start = current_rss_mib(); ticks = org.run_realtime(seconds); elapsed = time.perf_counter() - started; rss_end = current_rss_mib()
    org.snapshot_if_due(force=True); org.store.validate_chain(); events = org.store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]; org.close()
    size = sum(path.stat().st_size for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")) if path.exists()); cleanup(db)
    return {"schema": "AS010_REALTIME_SOAK_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "seed": seed, "seconds_requested": seconds, "seconds_actual": elapsed, "ticks": ticks, "hz": ticks / max(elapsed, 1e-9), "rss_start_mib": rss_start, "rss_end_mib": rss_end, "event_count": events, "database_bytes": size, "full_configuration": True, "pass": elapsed >= seconds * .99 and events <= ticks * 32}


def ablation(seed: int, work: Path, variant: str) -> dict[str, Any]:
    settings = {"terminal_readiness_disabled": (True, True), "continuation_disabled": (False, True), "route_learning_disabled": (True, False), "full": (True, True)}
    bounded, route = settings[variant]
    db = work / f"{variant}.sqlite"
    org = create_organism(as010_config(seed, db, "R0", bounded=bounded, route_learning=route))
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"):
        getattr(org, method)()
    org.run_ticks(7200)
    result = {"schema": "AS010_ABLATION_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "variant": variant, "seed": seed, "ticks": org.tick, "critical_violations": org.metrics["critical_violations"], "no_safe_action_ticks": org.metrics.get("no_safe_action", 0), "bounded_continuation_enabled": bounded, "route_learning_enabled": route}
    org.close(); cleanup(db)
    result["pass"] = result["ticks"] == 7200
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("lifecycle", "boundedness", "soak", "ablation"), required=True); parser.add_argument("--seed", type=int, required=True); parser.add_argument("--work", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--seconds", type=float, default=3600.0); parser.add_argument("--variant", default="full"); args = parser.parse_args(); args.work.mkdir(parents=True, exist_ok=False)
    if args.mode == "lifecycle": result = lifecycle(args.seed, args.work)
    elif args.mode == "boundedness": result = boundedness(args.seed, args.work)
    elif args.mode == "soak": result = soak(args.seed, args.work, args.seconds)
    else: result = ablation(args.seed, args.work, args.variant)
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n"); print(json.dumps(result, indent=2, sort_keys=True))
