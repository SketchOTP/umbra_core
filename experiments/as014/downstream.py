"""AS-014 boundedness, real-time soak, and matched causal-ablation harness.

The harness is deliberately downstream-only: it owns no organism policy and
uses the production checkpoint-plus-tail restart path after every persisted
execution.  Accelerated CPU is reported for throughput analysis; the 5% CPU
limit is retained solely by the real-time S3 contract.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from experiments.as014.full_config import BASELINE, DIRECTIVE, config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from umbra_core.arbitration import Candidate
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism, restore_habitat_engine_from_checkpoint
from umbra_core.util import current_rss_mib


ACCELERATED = {
    "rss_hard_max_mib": 180.0,
    "rss_slope_mib_per_hour_max": 1.0,
    "event_growth_records_per_tick_max": 32,
    "ticks": 100_000,
}
SOAK = {
    "warmup_seconds": 300.0,
    "measure_seconds": 3600.0,
    "sample_interval_seconds": 5.0,
    "minimum_samples": 360,
    "tick_hz": 2.0,
    "cpu_mean_fraction_max": 0.05,
    "rss_hard_max_mib": 180.0,
    "rss_slope_mib_per_hour_max": 1.0,
}
VARIANTS = ("FULL", "TERMINAL_READINESS_DISABLED", "CONTINUATION_DISABLED", "ROUTE_LEARNING_DISABLED")


def _ensure_histories(organism: Any) -> None:
    for method in (
        "_ensure_development_intervention",
        "_ensure_memory_history",
        "_ensure_social_history",
        "_ensure_individuality_history",
    ):
        getattr(organism, method)()


def _db_bytes(db: Path) -> int:
    return sum(path.stat().st_size for path in (db, Path(f"{db}-wal"), Path(f"{db}-shm")) if path.exists())


def _journal_append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o640)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def _rss_slope(samples: list[dict[str, float]]) -> float | None:
    if len(samples) < 2:
        return None
    xs = [item["elapsed_seconds"] / 3600.0 for item in samples]
    ys = [item["rss_mib"] for item in samples]
    x_mean, y_mean = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((value - x_mean) ** 2 for value in xs)
    return 0.0 if denominator == 0 else sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator


def _counts(organism: Any) -> dict[str, int]:
    checkpoint = organism.store.latest_checkpoint()
    return {
        "hot_tail_events": len(organism.store.iter_events()),
        "checkpoint_count": int(organism.store.conn.execute("SELECT COUNT(*) FROM ledger_checkpoints").fetchone()[0]),
        "snapshot_count": int(organism.store.conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]),
        "checkpoint_epoch": int(checkpoint["checkpoint_epoch"]) if checkpoint else 0,
        "route_experiences": len(getattr(getattr(organism, "world_model", None), "route_experiences", ()) or ()),
        "continuation_frontier": len(getattr(organism, "_pending_world_plan", None) or ()),
        "frame_ring": len(getattr(organism, "frame_ring", ()) or ()),
    }


def initialize(
    seed: int,
    db: Path,
    regime: str,
    *,
    continuation: bool = True,
    route_learning: bool = True,
    ledger_overrides: dict[str, Any] | None = None,
) -> tuple[Any, HabitatEngine]:
    organism = create_organism(
        config(
            seed,
            db,
            regime,
            bounded_continuation=continuation,
            route_learning=route_learning,
            ledger_overrides=ledger_overrides,
        )
    )
    _ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario({"R0": "S0", "R1": "S16"}[regime]))
    organism.embodiment.attach_habitat_engine(engine)
    return organism, engine


def _finalize_restart(
    organism: Any,
    engine: HabitatEngine,
    seed: int,
    db: Path,
    regime: str,
    *,
    continuation: bool,
    route_learning: bool,
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if organism.embodiment._habitat_engine is not engine:
        raise RuntimeError("AS014_FINALIZATION_ENGINE_MISMATCH")
    before = organism.authoritative_state()
    snapshot_id = organism.snapshot_if_due(force=True)
    organism.store.validate_chain()
    organism.close()
    restored = load_organism(
        config(
            seed,
            db,
            regime,
            bounded_continuation=continuation,
            route_learning=route_learning,
            ledger_overrides=ledger_overrides,
        )
    )
    restored_engine = restore_habitat_engine_from_checkpoint(restored)
    after = restored.authoritative_state()
    restored.store.validate_chain()
    result = {
        "snapshot_id": snapshot_id,
        "restart_continuity": after["identity"] == before["identity"] and after["tick"] == before["tick"],
        "restart_habitat_state_hash": restored_engine.snapshot_view().state_hash,
        "final_hot_tail_events": len(restored.store.iter_events()),
        "final_checkpoint_count": int(restored.store.conn.execute("SELECT COUNT(*) FROM ledger_checkpoints").fetchone()[0]),
        "final_snapshot_count": int(restored.store.conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]),
        "final_event_sequence": restored.store.last_sequence(),
    }
    restored.close()
    return result


def boundedness(
    seed: int,
    work: Path,
    ticks: int = ACCELERATED["ticks"],
    *,
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    db, journal = work / "boundedness.sqlite", work / "boundedness.metrics.jsonl"
    organism, engine = initialize(seed, db, "R0", ledger_overrides=ledger_overrides)
    initial_bytes, started, cpu_started = _db_bytes(db), time.perf_counter(), time.process_time()
    samples: list[dict[str, float]] = []
    first_no_safe: int | None = None
    critical = False
    for index in range(ticks):
        decision = organism.tick_once()
        if decision.get("no_safe_action") and first_no_safe is None:
            first_no_safe = organism.tick
        critical = critical or organism.phys.critical_any()
        if index == 0 or (index + 1) % 5000 == 0:
            row: dict[str, Any] = {
                "tick": organism.tick,
                "elapsed_seconds": time.perf_counter() - started,
                "process_cpu_seconds": time.process_time() - cpu_started,
                "rss_mib": float(current_rss_mib()),
                "hot_operational_bytes": _db_bytes(db),
                **_counts(organism),
            }
            _journal_append(journal, row)
            samples.append({key: float(row[key]) for key in ("tick", "elapsed_seconds", "rss_mib")})
    final = _finalize_restart(
        organism, engine, seed, db, "R0", continuation=True, route_learning=True,
        ledger_overrides=ledger_overrides,
    )
    elapsed, cpu_seconds = time.perf_counter() - started, time.process_time() - cpu_started
    rss_values = [sample["rss_mib"] for sample in samples]
    checkpoint_epochs = [int(json.loads(line)["checkpoint_epoch"]) for line in journal.read_text().splitlines()]
    result: dict[str, Any] = {
        "schema": "AS014_BOUNDEDNESS_RESULT_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "seed": seed,
        "ticks": ticks,
        "journal": str(journal),
        "samples": samples,
        "rss_peak_mib": max(rss_values),
        "rss_slope_mib_per_hour": _rss_slope(samples),
        "process_cpu_seconds": cpu_seconds,
        "elapsed_seconds": elapsed,
        "cpu_fraction_one_core_reported": cpu_seconds / max(elapsed, 1e-9),
        "hot_operational_bytes_initial": initial_bytes,
        "hot_operational_bytes_final": _db_bytes(db),
        "maintenance_epochs_observed": max(checkpoint_epochs, default=0),
        "first_no_safe_action": first_no_safe,
        "critical": critical,
        "accelerated_cpu_is_reporting_only": True,
        **final,
    }
    result["checks"] = {
        "exact_tick_horizon": ticks == ACCELERATED["ticks"],
        "no_critical_collapse": not critical,
        "no_no_safe_action_terminal": first_no_safe is None,
        "restart_continuity": result["restart_continuity"],
        "checkpoint_chain": result["final_checkpoint_count"] >= 1,
        "hot_tail_bounded": result["final_hot_tail_events"] <= 32_768,
        "checkpoint_count_bounded": result["final_checkpoint_count"] <= 4,
        "snapshot_count_bounded": result["final_snapshot_count"] <= 6,
        "repeated_maintenance": result["maintenance_epochs_observed"] >= 2,
        "rss_hard_max": result["rss_peak_mib"] <= ACCELERATED["rss_hard_max_mib"],
        "rss_slope": abs(result["rss_slope_mib_per_hour"] or 0.0) <= ACCELERATED["rss_slope_mib_per_hour_max"],
        "event_rate_bound": result["final_event_sequence"] <= ticks * ACCELERATED["event_growth_records_per_tick_max"],
    }
    result["pass"] = all(result["checks"].values())
    return result


def _run_realtime_window(organism: Any, seconds: float, journal: Path, samples: list[dict[str, float]], cpu_started: float, started: float) -> tuple[int, float]:
    period = 1.0 / SOAK["tick_hz"]
    end, next_sample, ticks = time.monotonic() + seconds, 0.0, 0
    organism.running = True
    try:
        while time.monotonic() < end:
            tick_started = time.monotonic()
            organism.tick_once()
            ticks += 1
            elapsed = time.perf_counter() - started
            if elapsed >= next_sample:
                row: dict[str, Any] = {
                    "tick": organism.tick,
                    "elapsed_seconds": elapsed,
                    "process_cpu_seconds": time.process_time() - cpu_started,
                    "rss_mib": float(current_rss_mib()),
                    "hot_operational_bytes": _db_bytes(Path(organism.config.db_path)),
                    **_counts(organism),
                }
                _journal_append(journal, row)
                samples.append({key: float(row[key]) for key in ("tick", "elapsed_seconds", "rss_mib")})
                next_sample += SOAK["sample_interval_seconds"]
            delay = period - (time.monotonic() - tick_started)
            if delay > 0:
                time.sleep(delay)
    finally:
        organism.running = False
    return ticks, time.perf_counter() - started


def soak(
    seed: int,
    work: Path,
    *,
    warmup_seconds: float = SOAK["warmup_seconds"],
    measure_seconds: float = SOAK["measure_seconds"],
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    db, journal = work / "soak.sqlite", work / "soak.metrics.jsonl"
    organism, engine = initialize(seed, db, "R0", ledger_overrides=ledger_overrides)
    started, cpu_started = time.perf_counter(), time.process_time()
    warmup_samples: list[dict[str, float]] = []
    measure_samples: list[dict[str, float]] = []
    warmup_ticks, _ = _run_realtime_window(organism, warmup_seconds, journal, warmup_samples, cpu_started, started)
    measure_start = time.perf_counter()
    measure_ticks, _ = _run_realtime_window(organism, measure_seconds, journal, measure_samples, cpu_started, started)
    measured_elapsed, elapsed, cpu_seconds = time.perf_counter() - measure_start, time.perf_counter() - started, time.process_time() - cpu_started
    final = _finalize_restart(
        organism, engine, seed, db, "R0", continuation=True, route_learning=True,
        ledger_overrides=ledger_overrides,
    )
    rss_values = [sample["rss_mib"] for sample in measure_samples] or [float(current_rss_mib())]
    result: dict[str, Any] = {
        "schema": "AS014_REALTIME_SOAK_RESULT_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "seed": seed,
        "warmup_seconds": warmup_seconds,
        "measure_seconds_requested": measure_seconds,
        "measure_seconds_actual": measured_elapsed,
        "warmup_ticks": warmup_ticks,
        "measure_ticks": measure_ticks,
        "sample_count": len(measure_samples),
        "journal": str(journal),
        "rss_peak_mib": max(rss_values),
        "rss_slope_mib_per_hour": _rss_slope(measure_samples),
        "process_cpu_seconds": cpu_seconds,
        "cpu_fraction_one_core": cpu_seconds / max(elapsed, 1e-9),
        **final,
    }
    result["checks"] = {
        "requested_duration": measured_elapsed >= measure_seconds * 0.99,
        "sample_count": len(measure_samples) >= SOAK["minimum_samples"],
        "rss_hard_max": result["rss_peak_mib"] <= SOAK["rss_hard_max_mib"],
        "rss_slope": abs(result["rss_slope_mib_per_hour"] or 0.0) <= SOAK["rss_slope_mib_per_hour_max"],
        "cpu_fraction": result["cpu_fraction_one_core"] <= SOAK["cpu_mean_fraction_max"],
        "restart_continuity": result["restart_continuity"],
        "hot_tail_bounded": result["final_hot_tail_events"] <= 32_768,
    }
    result["pass"] = all(result["checks"].values())
    return result


def _disable_terminal_readiness(organism: Any) -> dict[str, Any]:
    original = organism._candidate_executability
    calls = {"all": 0, "terminal": 0, "probe_changed": False}

    def permissive(candidate: Candidate) -> str:
        calls["all"] += 1
        if candidate.capability in {"CHARGE", "REST", "INSPECT"}:
            calls["terminal"] += 1
            return "EXECUTABLE"
        return original(candidate)

    probe = Candidate("CHARGE", {"toward": "unavailable"})
    calls["probe_changed"] = original(probe) != permissive(probe)
    organism._candidate_executability = permissive
    return calls


def ablation(
    seed: int,
    work: Path,
    variant: str,
    ticks: int = 7200,
    *,
    ledger_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise ValueError(variant)
    continuation, route_learning = variant != "CONTINUATION_DISABLED", variant != "ROUTE_LEARNING_DISABLED"
    db = work / f"{variant.lower()}.sqlite"
    organism, engine = initialize(
        seed, db, "R1", continuation=continuation, route_learning=route_learning,
        ledger_overrides=ledger_overrides,
    )
    readiness = {"all": 0, "terminal": 0, "probe_changed": False}
    if variant == "TERMINAL_READINESS_DISABLED":
        readiness = _disable_terminal_readiness(organism)
    actions: list[str] = []
    first_no_safe: int | None = None
    for _ in range(ticks):
        decision = organism.tick_once()
        actions.append(str(decision.get("capability")))
        if decision.get("no_safe_action") and first_no_safe is None:
            first_no_safe = organism.tick
    final = _finalize_restart(
        organism, engine, seed, db, "R1", continuation=continuation, route_learning=route_learning,
        ledger_overrides=ledger_overrides,
    )
    result = {
        "schema": "AS014_ABLATION_RESULT_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "variant": variant,
        "seed": seed,
        "ticks": ticks,
        "continuation_enabled": continuation,
        "route_learning_enabled": route_learning,
        "terminal_readiness_disabled": variant == "TERMINAL_READINESS_DISABLED",
        "readiness_seam": readiness,
        "configuration": fingerprint(config(
            seed, db, "R1", bounded_continuation=continuation, route_learning=route_learning,
            ledger_overrides=ledger_overrides,
        )),
        "action_timeline_hash": hashlib.sha256("\n".join(actions).encode()).hexdigest(),
        "action_counts": {capability: actions.count(capability) for capability in sorted(set(actions))},
        "first_no_safe_action": first_no_safe,
        **final,
    }
    result["pass"] = bool(ticks == 7200 and result["restart_continuity"])
    return result


__all__ = ["ACCELERATED", "SOAK", "VARIANTS", "ablation", "boundedness", "initialize", "soak"]
