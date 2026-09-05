"""AS-011 downstream boundedness, soak, and ablation harness.

This namespace owns protocol recovery only.  It deliberately does not alter
the production Habitat authority contract.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import resource
import time
from pathlib import Path
from typing import Any, Callable

from experiments.as009.qualification import partner_object
from experiments.as010.full_config import semantic_fingerprint
from experiments.as011.full_config import BASELINE, DIRECTIVE, as011_config
from experiments.d009.run_experiment import _habitat_state_for_scenario
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
SOAK = {"warmup_seconds": 300.0, "initial_measurement_seconds": 1800.0, "extension_seconds": 900.0, "max_measurement_seconds": 3600.0, "sample_interval_seconds": 5.0, "minimum_samples": 360, "tick_hz": 2.0}


def cleanup(db: Path) -> None:
    for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        path.unlink(missing_ok=True)


def _ensure_histories(org: Any) -> None:
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"):
        getattr(org, method)()


def initialize(seed: int, db: Path, regime: str = "R0", *, bounded: bool = True, route_learning: bool = True) -> tuple[Any, HabitatEngine]:
    org = create_organism(as011_config(seed, db, regime, bounded=bounded, route_learning=route_learning))
    _ensure_histories(org)
    engine = HabitatEngine(_habitat_state_for_scenario("S10" if regime == "R2" else "S0"))
    org.embodiment.attach_habitat_engine(engine)
    return org, engine


def restore_with_habitat(seed: int, db: Path, habitat: Any, regime: str = "R0") -> tuple[Any, HabitatEngine]:
    """Restore Habitat authority before any authoritative organism read."""
    org = load_organism(as011_config(seed, db, regime))
    engine = HabitatEngine(copy.deepcopy(habitat))
    org.embodiment.attach_habitat_engine(engine)
    binding = org.embodiment.habitat_authority_binding
    snapshot = engine.snapshot_view()
    if binding is None or binding["habitat_id"] != snapshot.habitat_id or binding["state_version"] != snapshot.state_version or binding["state_hash"] != snapshot.state_hash:
        raise RuntimeError("AS011_HABITAT_AUTHORITY_BINDING_INVALID")
    return org, engine


def db_bytes(db: Path) -> int:
    return sum(path.stat().st_size for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")) if path.exists())


def rss_slope_per_hour(samples: list[dict[str, float]]) -> float | None:
    if len(samples) < 2:
        return None
    xs = [sample["elapsed_seconds"] / 3600.0 for sample in samples]
    ys = [sample["rss_mib"] for sample in samples]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((x - xm) ** 2 for x in xs)
    return 0.0 if denominator == 0 else sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denominator


def _finalize_and_restart(org: Any, engine: HabitatEngine, seed: int, db: Path, regime: str) -> dict[str, Any]:
    before = org.authoritative_state()
    habitat = copy.deepcopy(engine.state)
    snapshot_id = org.snapshot_if_due(force=True)
    org.store.validate_chain()
    org.close()
    restored, restored_engine = restore_with_habitat(seed, db, habitat, regime)
    after = restored.authoritative_state()
    events = restored.store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    restart_ok = after["identity"] == before["identity"] and after["tick"] == before["tick"]
    restored.store.validate_chain()
    restored.close()
    return {"snapshot_id": snapshot_id, "restart_continuity": restart_ok, "event_count": events, "habitat_state_hash": restored_engine.snapshot_view().state_hash}


def boundedness(seed: int, work: Path, ticks: int = 100_000) -> dict[str, Any]:
    db = work / "boundedness.sqlite"
    initial_bytes = db_bytes(db)
    org, engine = initialize(seed, db, bounded=bounded, route_learning=route)
    samples: list[dict[str, float]] = []
    started = time.perf_counter()
    cpu_started = time.process_time()
    for index in range(ticks):
        org.tick_once()
        if index == 0 or (index + 1) % 5000 == 0:
            samples.append({"tick": float(index + 1), "rss_mib": float(current_rss_mib()), "elapsed_seconds": time.perf_counter() - started})
    final = _finalize_and_restart(org, engine, seed, db, "R0")
    elapsed = time.perf_counter() - started
    db_size = db_bytes(db)
    rss_values = [sample["rss_mib"] for sample in samples]
    events = int(final["event_count"])
    result = {
        "schema": "AS011_BOUNDEDNESS_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "seed": seed,
        "ticks": ticks, "samples": samples, "rss_peak_mib": max(rss_values), "rss_slope_mib_per_hour": rss_slope_per_hour(samples),
        "cpu_seconds": time.process_time() - cpu_started, "elapsed_seconds": elapsed, "event_count": events,
        "database_initial_bytes": initial_bytes, "database_final_bytes": db_size, "database_growth_bytes": db_size - initial_bytes,
        **final, "counts_bounded": events <= ticks * THRESHOLDS["event_growth_records_per_tick_max"], "full_configuration": True,
    }
    result["pass"] = bool(ticks == 100_000 and result["restart_continuity"] and result["counts_bounded"] and result["rss_peak_mib"] <= THRESHOLDS["rss_hard_max_mib"] and abs(result["rss_slope_mib_per_hour"] or 0.0) <= THRESHOLDS["rss_slope_mib_per_hour_max"] and result["database_growth_bytes"] <= THRESHOLDS["database_growth_bytes_max"])
    return result


def _run_window(org: Any, seconds: float, sample_interval: float, samples: list[dict[str, float]] | None = None) -> tuple[int, float]:
    samples = samples if samples is not None else []
    started = time.perf_counter(); next_sample = 0.0; ticks = 0
    period = 1.0 / float(org.config.hz)
    end = time.monotonic() + seconds
    org.running = True
    try:
        while time.monotonic() < end:
            t0 = time.monotonic(); org.tick_once(); ticks += 1
            elapsed = time.perf_counter() - started
            if elapsed >= next_sample:
                samples.append({"elapsed_seconds": elapsed, "rss_mib": float(current_rss_mib()), "tick": float(org.tick)})
                next_sample += sample_interval
            sleep_for = period - (time.monotonic() - t0)
            if sleep_for > 0:
                time.sleep(sleep_for)
    finally:
        org.running = False
    return ticks, time.perf_counter() - started


def soak(seed: int, work: Path, *, warmup_seconds: float = SOAK["warmup_seconds"], measure_seconds: float = SOAK["max_measurement_seconds"]) -> dict[str, Any]:
    db = work / "soak.sqlite"
    org, engine = initialize(seed, db)
    all_samples: list[dict[str, float]] = []
    cpu_started = time.process_time(); total_started = time.perf_counter()
    warmup_ticks, _ = _run_window(org, warmup_seconds, SOAK["sample_interval_seconds"], all_samples)
    measure_start = time.perf_counter(); measure_samples: list[dict[str, float]] = []
    measure_ticks, measure_elapsed = _run_window(org, measure_seconds, SOAK["sample_interval_seconds"], measure_samples)
    final = _finalize_and_restart(org, engine, seed, db, "R0")
    total_elapsed = time.perf_counter() - total_started
    size = db_bytes(db)
    samples = [sample for sample in measure_samples if sample["elapsed_seconds"] >= SOAK["sample_interval_seconds"]]
    rss_values = [sample["rss_mib"] for sample in samples] or [current_rss_mib()]
    result = {"schema": "AS011_REALTIME_SOAK_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "seed": seed, "warmup_seconds": warmup_seconds, "measure_seconds_requested": measure_seconds, "measure_seconds_actual": measure_elapsed, "warmup_ticks": warmup_ticks, "measure_ticks": measure_ticks, "ticks": warmup_ticks + measure_ticks, "samples": samples, "sample_count": len(samples), "rss_peak_mib": max(rss_values), "rss_slope_mib_per_hour": rss_slope_per_hour(samples), "cpu_seconds": time.process_time() - cpu_started, "cpu_fraction_one_core": (time.process_time() - cpu_started) / max(total_elapsed, 1e-9), "event_count": final["event_count"], "database_bytes": size, **final, "full_configuration": True}
    result["pass"] = bool(measure_elapsed >= measure_seconds * .99 and len(samples) >= SOAK["minimum_samples"] and result["rss_peak_mib"] <= THRESHOLDS["rss_hard_max_mib"] and abs(result["rss_slope_mib_per_hour"] or 0.0) <= THRESHOLDS["rss_slope_mib_per_hour_max"] and result["cpu_fraction_one_core"] <= THRESHOLDS["cpu_mean_fraction_max"] and result["event_count"] <= result["ticks"] * THRESHOLDS["event_growth_records_per_tick_max"] and result["restart_continuity"])
    return result


def _disable_terminal_readiness(org: Any) -> dict[str, Any]:
    original = org._candidate_executability
    calls = {"count": 0, "terminal_candidates": 0}
    def permissive(candidate: Any) -> Any:
        calls["count"] += 1
        if getattr(candidate, "capability", None) in {"CHARGE", "REST", "INSPECT"}:
            calls["terminal_candidates"] += 1
            return "EXECUTABLE"
        return original(candidate)
    org._candidate_executability = permissive
    return calls


def ablation(seed: int, work: Path, variant: str) -> dict[str, Any]:
    if variant not in {"full", "terminal_readiness_disabled", "continuation_disabled", "route_learning_disabled"}:
        raise ValueError(variant)
    bounded = variant != "continuation_disabled"
    route = variant != "route_learning_disabled"
    db = work / f"{variant}.sqlite"
    org, engine = initialize(seed, db)
    readiness = {"count": 0, "terminal_candidates": 0}
    if variant == "terminal_readiness_disabled":
        readiness = _disable_terminal_readiness(org)
    for _ in range(7200):
        org.tick_once()
    critical_violations = org.metrics["critical_violations"]
    final = _finalize_and_restart(org, engine, seed, db, "R0")
    result = {"schema": "AS011_ABLATION_RESULT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "variant": variant, "seed": seed, "ticks": 7200, "critical_violations": critical_violations, "bounded_continuation_enabled": bounded, "route_learning_enabled": route, "terminal_readiness_seam": variant == "terminal_readiness_disabled", "readiness_calls": readiness, "full_configuration": variant == "full", **final}
    result["pass"] = result["ticks"] == 7200 and result["restart_continuity"]
    cleanup(db)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("boundedness", "soak", "ablation"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", default="full")
    parser.add_argument("--warmup-seconds", type=float, default=SOAK["warmup_seconds"])
    parser.add_argument("--measure-seconds", type=float, default=SOAK["max_measurement_seconds"])
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    if args.mode == "boundedness":
        result = boundedness(args.seed, args.work)
    elif args.mode == "soak":
        result = soak(args.seed, args.work, warmup_seconds=args.warmup_seconds, measure_seconds=args.measure_seconds)
    else:
        result = ablation(args.seed, args.work, args.variant)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode()); handle.flush(); os.fsync(handle.fileno())
    if args.output.exists():
        tmp.unlink(missing_ok=True); raise FileExistsError(args.output)
    os.replace(tmp, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
