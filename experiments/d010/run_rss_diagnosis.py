"""Harness-only D-010-R1 RSS isolation diagnostics.

Production-unreachable: invoke only via this module. Modes ablate temporal write
path and allocator trim to isolate Gate 13 slope drivers.

Usage:
  python experiments/d010/run_rss_diagnosis.py --mode P0_baseline --seconds 180
  python experiments/d010/run_rss_diagnosis.py --mode P0_trim_snapshot --seconds 180
  python experiments/d010/run_rss_diagnosis.py --mode P0_slim_advance --seconds 180
  python experiments/d010/run_rss_diagnosis.py --mode temporal_off --seconds 180
  python experiments/d010/run_rss_diagnosis.py --mode advance_only --seconds 180
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import json
import os
import sqlite3
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d010.scenario_plants import apply_scenario_plants  # noqa: E402
from umbra_core.runtime import OrganismConfig, create_organism  # noqa: E402
from umbra_core.temporal.config import p0_performance_config  # noqa: E402
from umbra_core.util import current_rss_mib, ols_slope  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "d010" / "rss-diagnosis"
WORK = ROOT / ".soak" / "d010_rss_diag"
PROTO = json.loads((ROOT / "experiments/d010/performance-protocol.json").read_text())
SEED = int(PROTO["seed"])
HZ = float(PROTO["tick_hz"])


def _malloc_trim() -> None:
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except OSError:
        pass


def _db_size_mib(path: Path) -> float:
    total = 0
    for p in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if p.exists():
            total += p.stat().st_size
    return total / (1024.0 * 1024.0)


def _sqlite_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    con = sqlite3.connect(path)
    try:
        events = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        ticks = con.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='orchestration_tick_committed'"
        ).fetchone()[0]
        payload = con.execute("SELECT SUM(LENGTH(payload)) FROM events").fetchone()[0] or 0
        snaps = con.execute("SELECT COUNT(*), AVG(LENGTH(state_json)) FROM snapshots").fetchone()
        freelist = con.execute("PRAGMA freelist_count").fetchone()[0]
        pages = con.execute("PRAGMA page_count").fetchone()[0]
        return {
            "events": events,
            "tick_events": ticks,
            "payload_mib": payload / (1024 * 1024),
            "snapshots": snaps[0],
            "snapshot_avg_bytes": snaps[1],
            "freelist_pages": freelist,
            "page_count": pages,
        }
    finally:
        con.close()


def _object_counts(org: Any) -> dict[str, Any]:
    temporal = getattr(org, "temporal", None)
    state = temporal.state if temporal is not None else None
    recurrence_n = 0
    dedup = {}
    if state is not None:
        recurrence_n = len(state.recurrence_index)
        dedup = {
            "recent": len(state.dedup_summary.recent_evidence_identities),
            "retained": len(state.dedup_summary.retained_occurrence_identities),
            "compacted": len(state.dedup_summary.compacted_identity_digest),
        }
    ring = len(org.frame_ring) if getattr(org, "frame_ring", None) is not None else 0
    return {
        "tick": org.tick,
        "recurrence_hypotheses": recurrence_n,
        "dedup": dedup,
        "frame_ring": ring,
        "gc_counts": list(gc.get_count()),
        "gc_stats": gc.get_stats() if hasattr(gc, "get_stats") else [],
    }


def _install_slim_advance() -> Callable[[], None]:
    """Harness-only: drop prior_* anchors from wire payload (measure contribution)."""
    import umbra_core.runtime as runtime_mod
    import umbra_core.temporal.events as tev

    original = tev.advance_record_to_dict

    def slim(record: Any) -> dict[str, Any]:
        data = original(record)
        data.pop("prior_time_anchor", None)
        data.pop("prior_wall_clock_mapping", None)
        return data

    tev.advance_record_to_dict = slim  # type: ignore[assignment]

    def restore() -> None:
        tev.advance_record_to_dict = original  # type: ignore[assignment]

    return restore


def _install_omit_advance() -> Callable[[], None]:
    """Harness-only: empty advance record in tick payload (patch runtime binding)."""
    import umbra_core.runtime as runtime_mod
    import umbra_core.temporal.events as tev

    original = runtime_mod.build_orchestration_tick_payload

    def omit(*, orchestration_sequence: int, runtime_tick: int, record: Any, envelope: Any) -> dict:
        return {
            "orchestration_sequence": orchestration_sequence,
            "runtime_tick": runtime_tick,
            "temporal_advance_record": {"omitted_diagnostic": True},
            "temporal_transaction": tev.envelope_to_dict(envelope),
        }

    runtime_mod.build_orchestration_tick_payload = omit  # type: ignore[assignment]

    def restore() -> None:
        runtime_mod.build_orchestration_tick_payload = original  # type: ignore[assignment]

    return restore


def _install_trim_on_snapshot(org: Any) -> Callable[[], None]:
    original = org.snapshot_if_due

    def wrapped(force: bool = False) -> str | None:
        sid = original(force=force)
        if sid is not None:
            _malloc_trim()
        return sid

    org.snapshot_if_due = wrapped  # type: ignore[method-assign]

    def restore() -> None:
        org.snapshot_if_due = original  # type: ignore[method-assign]

    return restore


def _gate13_robust_slope(post: list[dict[str, Any]]) -> float:
    """Use the exact Gate 13 estimator so diagnosis and gate are comparable."""
    from experiments.d010.run_performance import _robust_slope_mib_per_hour

    return float(_robust_slope_mib_per_hour(post)[0]) if len(post) >= 3 else 0.0


def _install_release_variant(mode: str) -> Callable[[], None]:
    """Harness-only: swap runtime._release_native_arenas to isolate its two halves.

    P0_no_shrink  -> malloc_trim only (no SQLite PRAGMA shrink_memory)
    P0_no_release -> neither (pre-D-010-R1 behaviour on remediated source)
    """
    import umbra_core.runtime as runtime_mod

    original = runtime_mod._release_native_arenas

    def trim_only() -> None:
        _malloc_trim()

    def nothing() -> None:
        return None

    runtime_mod._release_native_arenas = (  # type: ignore[assignment]
        trim_only if mode == "P0_no_shrink" else nothing
    )

    def restore() -> None:
        runtime_mod._release_native_arenas = original  # type: ignore[assignment]

    return restore


def _install_wal_only_release(org: Any) -> Callable[[], None]:
    """Harness-only: suppress snapshot-path arena release; keep WAL-path release.

    Mirrors D-002P (trim only after wal_checkpoint) on top of bounded-id fix.
    """
    import umbra_core.runtime as runtime_mod

    original_snap = org.snapshot_if_due
    release = runtime_mod._release_native_arenas

    def snap_no_release(force: bool = False) -> str | None:
        # Temporarily disable release while snapshot path runs.
        runtime_mod._release_native_arenas = lambda: None  # type: ignore[assignment]
        try:
            return original_snap(force=force)
        finally:
            runtime_mod._release_native_arenas = release  # type: ignore[assignment]

    org.snapshot_if_due = snap_no_release  # type: ignore[method-assign]

    def restore() -> None:
        org.snapshot_if_due = original_snap  # type: ignore[method-assign]
        runtime_mod._release_native_arenas = release  # type: ignore[assignment]

    return restore


def _install_fast_release(org: Any, mode: str, every: int = 20) -> Callable[[], None]:
    """Harness-only: run the arena release every `every` ticks instead of only at
    snapshot / WAL boundaries, to measure sawtooth amplitude versus cadence."""
    import umbra_core.runtime as runtime_mod

    original = org.tick_once
    release = runtime_mod._release_native_arenas
    shrink = mode == "P0_release_fast"
    # Disable the snapshot/WAL-boundary release so only the fast cadence acts.
    runtime_mod._release_native_arenas = lambda: None  # type: ignore[assignment]

    def wrapped(*a: Any, **kw: Any) -> Any:
        out = original(*a, **kw)
        if org.tick % every == 0:
            if shrink:
                release()
            else:
                _malloc_trim()
        return out

    org.tick_once = wrapped  # type: ignore[method-assign]

    def restore() -> None:
        org.tick_once = original  # type: ignore[method-assign]
        runtime_mod._release_native_arenas = release  # type: ignore[assignment]

    return restore


def _make_organism(mode: str, db_path: str) -> Any:
    temporal_enabled = mode != "temporal_off"
    tcfg = p0_performance_config() if mode.startswith("P0") or mode in {
        "advance_only",
        "temporal_off",
    } else None
    # advance_only: temporal on, habitat/expression off to minimize non-temporal writes
    habitat = mode != "advance_only"
    return create_organism(
        OrganismConfig(
            db_path=db_path,
            seed=SEED,
            hz=HZ,
            temporal_enabled=temporal_enabled,
            temporal_config=tcfg if temporal_enabled else None,
            temporal_scenario_id="S0" if temporal_enabled else None,
            temporal_scenario_hook=apply_scenario_plants if temporal_enabled else None,
            habitat_enabled=habitat,
            expression_enabled=False,
            embodiment_adapter_enabled=True,
            wall_time_fn=lambda: time.time(),
        )
    )


def run_mode(
    mode: str,
    seconds: float,
    sample_interval: float = 2.0,
    warmup_seconds: float = 300.0,
) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    db = WORK / f"{mode}.sqlite"
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)

    restores: list[Callable[[], None]] = []
    if mode == "P0_slim_advance":
        restores.append(_install_slim_advance())
    elif mode == "P0_omit_advance":
        restores.append(_install_omit_advance())
    elif mode in {"P0_no_shrink", "P0_no_release"}:
        restores.append(_install_release_variant(mode))

    tracemalloc.start()
    org = _make_organism(mode, str(db))
    if mode == "P0_trim_snapshot":
        restores.append(_install_trim_on_snapshot(org))
    elif mode == "P0_wal_only_release":
        restores.append(_install_wal_only_release(org))
    elif mode in {"P0_trim_fast", "P0_release_fast"}:
        # Fast cadence replaces the snapshot/WAL-boundary release so the candidate
        # design is measured on its own, not stacked on production behaviour.
        restores.append(_install_fast_release(org, mode))

    period = 1.0 / HZ
    t0 = time.time()
    cpu0 = time.process_time()
    samples: list[dict[str, Any]] = []
    next_sample = t0
    try:
        while time.time() - t0 < seconds:
            loop = time.monotonic()
            org.tick_once()
            now = time.time()
            if now >= next_sample:
                current, peak = tracemalloc.get_traced_memory()
                samples.append(
                    {
                        "t": now - t0,
                        "rss_mib": current_rss_mib(),
                        "tick": org.tick,
                        "cpu_s": time.process_time() - cpu0,
                        "traced_heap_mib": current / (1024 * 1024),
                        "traced_peak_mib": peak / (1024 * 1024),
                        "db_mib": _db_size_mib(db),
                        "objects": _object_counts(org),
                    }
                )
                next_sample += sample_interval
            sleep_for = period - (time.monotonic() - loop)
            if sleep_for > 0:
                time.sleep(sleep_for)
        org.snapshot_if_due(force=True)
    finally:
        org.close()
        for restore in restores:
            restore()
        tracemalloc.stop()

    post = [s for s in samples if float(s["t"]) >= warmup_seconds] or samples
    rss = [float(s["rss_mib"]) for s in post]
    ts_h = [float(s["t"]) / 3600.0 for s in post]
    slope = float(ols_slope(ts_h, rss)) if len(rss) >= 3 else 0.0
    n = len(rss)
    cuts = [0, n // 3, (2 * n) // 3, n] if n else [0, 0, 0, 0]
    segs = []
    for a, b in zip(cuts, cuts[1:]):
        chunk = rss[a:b] or (rss[-1:] if rss else [0.0])
        segs.append(float(statistics.median(chunk)))

    jumps = []
    for i in range(1, len(post)):
        d = float(post[i]["rss_mib"]) - float(post[i - 1]["rss_mib"])
        if d >= 0.25:
            jumps.append(
                {
                    "delta_mib": d,
                    "t": post[i]["t"],
                    "tick": post[i]["tick"],
                }
            )

    db_series = [float(s["db_mib"]) for s in samples]
    heap_series = [float(s["traced_heap_mib"]) for s in post]

    out = {
        "mode": mode,
        "seconds": seconds,
        "warmup_seconds": warmup_seconds,
        "seed": SEED,
        "hz": HZ,
        "sample_count": len(samples),
        "post_warmup_samples": len(post),
        "rss_start_mib": float(samples[0]["rss_mib"]) if samples else None,
        "rss_end_mib": float(samples[-1]["rss_mib"]) if samples else None,
        "rss_delta_all_mib": (
            float(samples[-1]["rss_mib"]) - float(samples[0]["rss_mib"])
            if len(samples) >= 2
            else None
        ),
        "rss_delta_post_mib": (rss[-1] - rss[0]) if len(rss) >= 2 else None,
        "rss_ols_slope_mib_per_hour": slope,
        "rss_robust_slope_mib_per_hour": _gate13_robust_slope(post),
        "rss_min_post_mib": min(rss) if rss else None,
        "rss_max_post_mib": max(rss) if rss else None,
        "rss_segment_medians_mib": segs,
        "sustained_segment_growth": bool(
            len(segs) == 3 and segs[0] + 0.25 < segs[1] and segs[1] + 0.25 < segs[2]
        ),
        "db_growth_during_run_mib": (
            (db_series[-1] - db_series[0]) if len(db_series) >= 2 else None
        ),
        "db_end_file_mib": _db_size_mib(db),
        "traced_heap_delta_post_mib": (
            (heap_series[-1] - heap_series[0]) if len(heap_series) >= 2 else None
        ),
        "jumps_ge_0_25_post": jumps,
        "sqlite": _sqlite_stats(db),
        "final_objects": samples[-1]["objects"] if samples else {},
        "harness_only": True,
        "production_unreachable": True,
    }
    path = OUT / f"{mode}.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    (OUT / f"{mode}.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mode",
        required=True,
        choices=[
            "P0_baseline",
            "P0_trim_snapshot",
            "P0_slim_advance",
            "P0_omit_advance",
            "P0_no_shrink",
            "P0_no_release",
            "P0_trim_fast",
            "P0_release_fast",
            "P0_wal_only_release",
            "temporal_off",
            "advance_only",
        ],
    )
    ap.add_argument("--seconds", type=float, default=900.0)
    ap.add_argument("--warmup-seconds", type=float, default=300.0)
    ap.add_argument("--sample-interval", type=float, default=2.0)
    args = ap.parse_args()
    out = run_mode(args.mode, args.seconds, args.sample_interval, args.warmup_seconds)
    skip = {"jumps_ge_0_25_post", "final_objects"}
    print(json.dumps({k: out[k] for k in out if k not in skip}, indent=2))
    print("jumps_post", len(out["jumps_ge_0_25_post"]))


if __name__ == "__main__":
    main()
