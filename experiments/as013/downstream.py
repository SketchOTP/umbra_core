"""AS-013 publication-safe boundedness, soak, and matched ablations.

This module is deliberately experiment-only.  It restores HabitatEngine before
any authoritative read after every reload and keeps the frozen metric and
causal contracts in one executable namespace.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import time
from pathlib import Path
from typing import Any

from experiments.as010.full_config import semantic_fingerprint
from experiments.as013.full_config import BASELINE, DIRECTIVE, config
from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.as013.publication import publish_json
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism
from umbra_core.util import current_rss_mib

THRESHOLDS = {
    "rss_hard_max_mib": 180.0,
    "rss_slope_mib_per_hour_max": 1.0,
    "database_growth_bytes_max": 67_108_864,
    "event_growth_records_per_tick_max": 32,
    "cpu_mean_fraction_max": 0.05,
}
SOAK = {
    "warmup_seconds": 300.0,
    "measure_seconds": 3600.0,
    "sample_interval_seconds": 5.0,
    "minimum_samples": 360,
    "tick_hz": 2.0,
}
VARIANTS = ("full", "terminal_readiness_disabled", "continuation_disabled", "route_learning_disabled")


def cleanup(db: Path) -> None:
    for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        path.unlink(missing_ok=True)


def _ensure_histories(org: Any) -> None:
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"):
        getattr(org, method)()


def initialize(
    seed: int,
    db: Path,
    regime: str = "R0",
    *,
    bounded_continuation: bool = True,
    route_learning: bool = True,
) -> tuple[Any, HabitatEngine]:
    """Create one organism with explicit full/ablation semantics."""
    organism = create_organism(
        config(
            seed,
            db,
            regime,
            bounded_continuation=bounded_continuation,
            route_learning=route_learning,
        )
    )
    _ensure_histories(organism)
    scenario = {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}[regime]
    engine = HabitatEngine(_habitat_state_for_scenario(scenario))
    organism.embodiment.attach_habitat_engine(engine)
    if organism.embodiment._habitat_engine is not engine:
        raise RuntimeError("AS012_HABITAT_ENGINE_ATTACHMENT_NOT_ESTABLISHED")
    binding = organism.embodiment.habitat_authority_binding
    snap = engine.snapshot_view()
    if binding is None or binding["habitat_id"] != snap.habitat_id or binding["state_version"] != snap.state_version or binding["state_hash"] != snap.state_hash:
        raise RuntimeError("AS012_HABITAT_AUTHORITY_BINDING_INVALID")
    return organism, engine


def restore_with_habitat(
    seed: int,
    db: Path,
    habitat: Any,
    regime: str = "R0",
    *,
    bounded_continuation: bool = True,
    route_learning: bool = True,
) -> tuple[Any, HabitatEngine]:
    """Load, restore exact Habitat state, attach, then permit authoritative reads."""
    organism = load_organism(
        config(
            seed,
            db,
            regime,
            bounded_continuation=bounded_continuation,
            route_learning=route_learning,
        )
    )
    engine = HabitatEngine(copy.deepcopy(habitat))
    organism.embodiment.attach_habitat_engine(engine)
    binding = organism.embodiment.habitat_authority_binding
    snap = engine.snapshot_view()
    if organism.embodiment._habitat_engine is not engine or binding is None:
        raise RuntimeError("AS012_HABITAT_REATTACHMENT_NOT_ESTABLISHED")
    if binding["habitat_id"] != snap.habitat_id or binding["state_version"] != snap.state_version or binding["state_hash"] != snap.state_hash:
        raise RuntimeError("AS012_HABITAT_AUTHORITY_BINDING_INVALID")
    return organism, engine


def db_bytes(db: Path) -> int:
    return sum(path.stat().st_size for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")) if path.exists())


def rss_slope_per_hour(samples: list[dict[str, float]]) -> float | None:
    if len(samples) < 2:
        return None
    xs = [item["elapsed_seconds"] / 3600.0 for item in samples]
    ys = [item["rss_mib"] for item in samples]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((x - xm) ** 2 for x in xs)
    return 0.0 if denominator == 0 else sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denominator


def _counts(organism: Any) -> dict[str, int]:
    return {
        "events": int(organism.store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]),
        "route_experiences": len(getattr(getattr(organism, "world_model", None), "route_experiences", ()) or ()),
        "continuation_frontier": len(getattr(organism, "_pending_world_plan", None) or ()),
        "frame_ring": len(getattr(organism, "frame_ring", ()) or ()),
    }


def _journal_append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _finalize_and_restart(
    organism: Any,
    engine: HabitatEngine,
    seed: int,
    db: Path,
    regime: str,
    *,
    bounded_continuation: bool = True,
    route_learning: bool = True,
) -> dict[str, Any]:
    if organism.embodiment._habitat_engine is not engine:
        raise RuntimeError("AS012_FINALIZATION_ENGINE_MISMATCH")
    before = organism.authoritative_state()
    habitat = copy.deepcopy(engine.state)
    snapshot_id = organism.snapshot_if_due(force=True)
    organism.store.validate_chain()
    organism.close()
    restored, restored_engine = restore_with_habitat(
        seed,
        db,
        habitat,
        regime,
        bounded_continuation=bounded_continuation,
        route_learning=route_learning,
    )
    after = restored.authoritative_state()
    restored.store.validate_chain()
    event_count = int(restored.store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
    restart_ok = after["identity"] == before["identity"] and after["tick"] == before["tick"]
    restored.close()
    return {
        "snapshot_id": snapshot_id,
        "restart_continuity": restart_ok,
        "event_count": event_count,
        "habitat_state_hash": restored_engine.snapshot_view().state_hash,
    }


def boundedness(seed: int, work: Path, ticks: int = 100_000) -> dict[str, Any]:
    db = work / "boundedness.sqlite"
    journal = work / "boundedness.metrics.jsonl"
    initial_bytes = db_bytes(db)
    organism, engine = initialize(seed, db, "R0", bounded_continuation=True, route_learning=True)
    samples: list[dict[str, float]] = []
    started = time.perf_counter()
    cpu_started = time.process_time()
    for index in range(ticks):
        organism.tick_once()
        if index == 0 or (index + 1) % 5000 == 0:
            row = {"tick": index + 1, "elapsed_seconds": time.perf_counter() - started, "process_cpu_seconds": time.process_time() - cpu_started, "rss_mib": float(current_rss_mib()), "db_bytes": db_bytes(db), **_counts(organism)}
            samples.append({"tick": float(row["tick"]), "elapsed_seconds": float(row["elapsed_seconds"]), "rss_mib": float(row["rss_mib"])})
            _journal_append(journal, row)
    final = _finalize_and_restart(organism, engine, seed, db, "R0")
    elapsed = time.perf_counter() - started
    cpu_seconds = time.process_time() - cpu_started
    database_final = db_bytes(db)
    rss_values = [item["rss_mib"] for item in samples]
    result: dict[str, Any] = {
        "schema": "AS013_BOUNDEDNESS_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "seed": seed,
        "ticks": ticks, "samples": samples, "journal": str(journal), "rss_peak_mib": max(rss_values),
        "rss_slope_mib_per_hour": rss_slope_per_hour(samples), "cpu_seconds": cpu_seconds,
        "elapsed_seconds": elapsed, "cpu_fraction_one_core": cpu_seconds / max(elapsed, 1e-9),
        "database_initial_bytes": initial_bytes, "database_final_bytes": database_final,
        "database_growth_bytes": database_final - initial_bytes, **final,
        "counts_bounded": final["event_count"] <= ticks * THRESHOLDS["event_growth_records_per_tick_max"],
        "full_configuration": True, "metric_journal_contains_process_cpu_seconds": True,
    }
    result["pass"] = bool(
        ticks == 100_000
        and result["restart_continuity"]
        and result["counts_bounded"]
        and result["rss_peak_mib"] <= THRESHOLDS["rss_hard_max_mib"]
        and abs(result["rss_slope_mib_per_hour"] or 0.0) <= THRESHOLDS["rss_slope_mib_per_hour_max"]
        and result["database_growth_bytes"] <= THRESHOLDS["database_growth_bytes_max"]
        and result["cpu_fraction_one_core"] <= THRESHOLDS["cpu_mean_fraction_max"]
    )
    return result


def _run_window(organism: Any, seconds: float, interval: float, journal: Path, samples: list[dict[str, float]], cpu_started: float) -> tuple[int, float]:
    started = time.perf_counter(); next_sample = 0.0; ticks = 0; period = 1.0 / float(organism.config.hz); end = time.monotonic() + seconds
    organism.running = True
    try:
        while time.monotonic() < end:
            tick_started = time.monotonic(); organism.tick_once(); ticks += 1
            elapsed = time.perf_counter() - started
            if elapsed >= next_sample:
                row = {"elapsed_seconds": elapsed, "process_cpu_seconds": time.process_time() - cpu_started, "tick": organism.tick, "rss_mib": float(current_rss_mib()), **_counts(organism)}
                samples.append({"elapsed_seconds": float(elapsed), "tick": float(organism.tick), "rss_mib": float(row["rss_mib"])})
                _journal_append(journal, row)
                next_sample += interval
            delay = period - (time.monotonic() - tick_started)
            if delay > 0:
                time.sleep(delay)
    finally:
        organism.running = False
    return ticks, time.perf_counter() - started


def soak(seed: int, work: Path, *, warmup_seconds: float = SOAK["warmup_seconds"], measure_seconds: float = SOAK["measure_seconds"]) -> dict[str, Any]:
    db = work / "soak.sqlite"; journal = work / "soak.metrics.jsonl"
    organism, engine = initialize(seed, db, "R0", bounded_continuation=True, route_learning=True)
    warmup_samples: list[dict[str, float]] = []; measure_samples: list[dict[str, float]] = []
    started = time.perf_counter(); cpu_started = time.process_time()
    warmup_ticks, _ = _run_window(organism, warmup_seconds, SOAK["sample_interval_seconds"], journal, warmup_samples, cpu_started)
    measure_ticks, measure_elapsed = _run_window(organism, measure_seconds, SOAK["sample_interval_seconds"], journal, measure_samples, cpu_started)
    final = _finalize_and_restart(organism, engine, seed, db, "R0")
    elapsed = time.perf_counter() - started; cpu_seconds = time.process_time() - cpu_started
    samples = [sample for sample in measure_samples if sample["elapsed_seconds"] >= SOAK["sample_interval_seconds"]]
    rss_values = [item["rss_mib"] for item in samples] or [float(current_rss_mib())]
    result: dict[str, Any] = {
        "schema": "AS013_REALTIME_SOAK_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "seed": seed,
        "warmup_seconds": warmup_seconds, "measure_seconds_requested": measure_seconds, "measure_seconds_actual": measure_elapsed,
        "warmup_ticks": warmup_ticks, "measure_ticks": measure_ticks, "ticks": warmup_ticks + measure_ticks,
        "samples": samples, "sample_count": len(samples), "journal": str(journal), "rss_peak_mib": max(rss_values),
        "rss_slope_mib_per_hour": rss_slope_per_hour(samples), "cpu_seconds": cpu_seconds,
        "cpu_fraction_one_core": cpu_seconds / max(elapsed, 1e-9), "full_configuration": True, **final,
    }
    result["pass"] = bool(
        measure_elapsed >= measure_seconds * 0.99
        and len(samples) >= SOAK["minimum_samples"]
        and result["rss_peak_mib"] <= THRESHOLDS["rss_hard_max_mib"]
        and abs(result["rss_slope_mib_per_hour"] or 0.0) <= THRESHOLDS["rss_slope_mib_per_hour_max"]
        and result["cpu_fraction_one_core"] <= THRESHOLDS["cpu_mean_fraction_max"]
        and result["event_count"] <= result["ticks"] * THRESHOLDS["event_growth_records_per_tick_max"]
        and result["restart_continuity"]
    )
    return result


def _disable_terminal_readiness(organism: Any) -> dict[str, Any]:
    original = organism._candidate_executability
    calls = {"count": 0, "terminal_candidates": 0}
    def permissive(candidate: Any) -> Any:
        calls["count"] += 1
        if getattr(candidate, "capability", None) in {"CHARGE", "REST", "INSPECT"}:
            calls["terminal_candidates"] += 1
            return "EXECUTABLE"
        return original(candidate)
    organism._candidate_executability = permissive
    return calls


def ablation(seed: int, work: Path, variant: str, ticks: int = 7200) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise ValueError(variant)
    bounded = variant != "continuation_disabled"; route = variant != "route_learning_disabled"
    db = work / f"{variant}.sqlite"
    organism, engine = initialize(seed, db, "R1", bounded_continuation=bounded, route_learning=route)
    readiness = {"count": 0, "terminal_candidates": 0}
    if variant == "terminal_readiness_disabled":
        readiness = _disable_terminal_readiness(organism)
    for _ in range(ticks):
        organism.tick_once()
    critical = organism.metrics.get("critical_violations", 0)
    final = _finalize_and_restart(organism, engine, seed, db, "R1", bounded_continuation=bounded, route_learning=route)
    result = {
        "schema": "AS013_ABLATION_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE,
        "variant": variant, "seed": seed, "ticks": ticks, "critical_violations": critical,
        "bounded_continuation_enabled": bounded, "route_learning_enabled": route,
        "terminal_readiness_seam": variant == "terminal_readiness_disabled", "readiness_calls": readiness,
        "configuration_fingerprint": semantic_fingerprint(config(seed, db, "R1", bounded_continuation=bounded, route_learning=route)),
        **final,
    }
    result["pass"] = result["ticks"] == 7200 and result["restart_continuity"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("boundedness", "soak", "ablation"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--variant", default="full")
    parser.add_argument("--ticks", type=int, default=100_000)
    parser.add_argument("--warmup-seconds", type=float, default=SOAK["warmup_seconds"])
    parser.add_argument("--measure-seconds", type=float, default=SOAK["measure_seconds"])
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    if args.mode == "boundedness":
        result = boundedness(args.seed, args.work, args.ticks)
    elif args.mode == "soak":
        result = soak(args.seed, args.work, warmup_seconds=args.warmup_seconds, measure_seconds=args.measure_seconds)
    else:
        result = ablation(args.seed, args.work, args.variant, args.ticks)
    checkpoint_hash = publish_json(args.checkpoint, result, schema=result["schema"])
    output_hash = publish_json(args.output, result, schema=result["schema"])
    if checkpoint_hash != output_hash:
        raise RuntimeError("AS013_CHECKPOINT_OUTPUT_HASH_MISMATCH")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
