"""UMBRA-D-009 Task 14 performance — Supplement S3 adaptive soak (Gate 13).

Modes (fresh process recommended via --mode):
  P0  HabitatEngine compatibility (C13: MANIPULATE/routines/dynamics off)
  P1  Full D-009 habitat agency + HeadlessRenderer
  P2  Full D-009 habitat agency + TkinterRenderer (real Canvas + event loop)

Also: accelerated 100k boundedness, renderer lifecycle stress (≥100 cycles).

Timing from experiments/d009/performance-protocol.json (S3). Absolute RSS/CPU
limits remain in thresholds.json.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d009.run_experiment import _habitat_state_for_scenario  # noqa: E402
from experiments.d009.scenario_plants import apply_scenario_plants  # noqa: E402
from umbra_core.embodiment_adapters.profiles import (  # noqa: E402
    ABSTRACT_SHAPE_BODY_D009,
    profile_definition_hash,
)
from umbra_core.expression import HeadlessRenderer  # noqa: E402
from umbra_core.expression.frame_ring import FRAME_RING_CAPACITY, RendererCursor  # noqa: E402
from umbra_core.habitat.config import HabitatConfig, p0_compatibility_config  # noqa: E402
from umbra_core.habitat.engine import HabitatEngine  # noqa: E402
from umbra_core.runtime import OrganismConfig, create_organism, load_organism  # noqa: E402
from umbra_core.util import current_rss_mib, ols_slope  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "d009"
THR = json.loads((ROOT / "experiments" / "d009" / "thresholds.json").read_text())
PROTO = json.loads((ROOT / "experiments" / "d009" / "performance-protocol.json").read_text())
WORK = ROOT / ".soak" / "d009_perf"
SCENARIO = str(PROTO.get("scenario", "S0"))
FRAME_RING_CAP = int(THR.get("frame_ring_capacity", 256))


def _software_commit() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def _smoke_scale() -> float:
    """D009_PERF_SMOKE=1 shortens walls for structural dry-runs (not sealable)."""
    if os.environ.get("D009_PERF_SMOKE") == "1":
        return float(os.environ.get("D009_PERF_SMOKE_SCALE", "0.02"))
    return 1.0


def _proto_timing() -> dict[str, float | int]:
    scale = _smoke_scale()
    warmup = max(1.0, float(PROTO["warmup_seconds"]) * scale)
    initial = max(5.0, float(PROTO["initial_measurement_seconds"]) * scale)
    extension = max(5.0, float(PROTO["extension_seconds"]) * scale)
    maximum = max(initial, float(PROTO["max_measurement_seconds"]) * scale)
    interval = max(0.5, float(PROTO["sample_interval_seconds"]) * min(1.0, scale * 5))
    min_samples = max(3, int(math.ceil(int(PROTO["minimum_samples"]) * scale)))
    return {
        "warmup_seconds": warmup,
        "initial_measurement_seconds": initial,
        "extension_seconds": extension,
        "max_measurement_seconds": maximum,
        "sample_interval_seconds": interval,
        "minimum_samples": min_samples,
        "tick_hz": float(PROTO["tick_hz"]),
        "seed": int(PROTO["seed"]),
        "lifecycle_cycles_min": int(PROTO["lifecycle_cycles_min"]) if scale >= 1.0 else 5,
    }


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    idx = int(round(p * (len(ys) - 1)))
    return float(ys[max(0, min(len(ys) - 1, idx))])


def _bin_median_samples(
    samples: list[dict[str, Any]], bin_seconds: float = 30.0
) -> list[dict[str, Any]]:
    if not samples:
        return []
    bins: dict[int, list[float]] = {}
    t0 = float(samples[0]["t"])
    for s in samples:
        idx = int(max(0.0, float(s["t"]) - t0) // bin_seconds)
        bins.setdefault(idx, []).append(float(s["rss_mib"]))
    out: list[dict[str, Any]] = []
    for idx in sorted(bins):
        out.append(
            {
                "t": t0 + (idx + 0.5) * bin_seconds,
                "rss_mib": float(statistics.median(bins[idx])),
            }
        )
    return out


def _robust_slope_mib_per_hour(samples: list[dict[str, Any]]) -> tuple[float, list[float]]:
    binned = _bin_median_samples(samples)
    pts = [(float(s["t"]) / 3600.0, float(s["rss_mib"])) for s in binned if float(s["t"]) >= 0]
    if len(pts) < 3:
        return 0.0, [0.0, 0.0]
    slopes: list[float] = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dx = pts[j][0] - pts[i][0]
            if abs(dx) < 1e-12:
                continue
            slopes.append((pts[j][1] - pts[i][1]) / dx)
    if not slopes:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return float(ols_slope(xs, ys)), [0.0, 0.0]
    slopes.sort()
    mid = statistics.median(slopes)
    lo = _percentile(slopes, 0.025)
    hi = _percentile(slopes, 0.975)
    return float(mid), [float(lo), float(hi)]


def _segment_medians(samples: list[dict[str, Any]]) -> list[float]:
    binned = _bin_median_samples(samples) or samples
    if not binned:
        return [0.0, 0.0, 0.0]
    n = len(binned)
    cuts = [0, n // 3, (2 * n) // 3, n]
    out: list[float] = []
    for a, b in zip(cuts, cuts[1:]):
        chunk = [float(s["rss_mib"]) for s in binned[a:b]] or [float(binned[-1]["rss_mib"])]
        out.append(float(statistics.median(chunk)))
    while len(out) < 3:
        out.append(out[-1] if out else 0.0)
    return out[:3]


def _sustained_monotonic_growth(seg: list[float], eps: float = 0.25) -> bool:
    return seg[0] + eps < seg[1] and seg[1] + eps < seg[2]


def _db_size_mib(path: Path) -> float:
    total = 0
    for p in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if p.exists():
            total += p.stat().st_size
    return total / (1024.0 * 1024.0)


def _require_tk() -> Any:
    try:
        import tkinter as tk
    except ImportError as exc:
        raise SystemExit(f"fail_closed:python3-tk_missing:{exc}") from exc
    if not os.environ.get("DISPLAY"):
        raise SystemExit("fail_closed:DISPLAY_unset")
    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
    except tk.TclError as exc:
        raise SystemExit(f"fail_closed:no_tk_display:{exc}") from exc
    return tk


def _base_cfg(db_path: str, *, mode: str, hz: float, seed: int) -> OrganismConfig:
    if mode == "P0":
        habitat_cfg = p0_compatibility_config()
        expression = False
    else:
        habitat_cfg = HabitatConfig()
        expression = True
    return OrganismConfig(
        db_path=db_path,
        seed=seed,
        hz=hz,
        condition="C0",
        self_model_enabled=True,
        world_model_enabled=True,
        memory_enabled=True,
        individuality_enabled=True,
        individuality_history="H0",
        habitat_enabled=True,
        habitat_config=habitat_cfg,
        habitat_scenario_id=SCENARIO,
        habitat_scenario_hook=apply_scenario_plants,
        embodiment_adapter_enabled=True,
        expression_enabled=expression,
        drift_enabled=True,
    )


def _prepare_organism(org: Any) -> None:
    """History plants mutate legacy habitat only — apply before engine attach."""
    org._ensure_development_intervention()
    org._ensure_memory_history()
    org._ensure_social_history()
    org._ensure_individuality_history()


def _attach_habitat(org: Any) -> HabitatEngine:
    engine = HabitatEngine(_habitat_state_for_scenario(SCENARIO))
    org.embodiment.attach_habitat_engine(engine)
    org.embodiment.body.x = 4.0
    org.embodiment.body.y = 3.0
    org.perception.perceive_habitat_objects(org.embodiment, 1.0, org.rng)
    return engine


def _fresh_db(name: str) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    db = WORK / name
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        p.unlink(missing_ok=True)
    return db


def _habitat_bounded(org: Any, engine: HabitatEngine) -> bool:
    snap = engine.snapshot_view()
    if len(snap.objects) > int(THR["max_objects"]):
        return False
    if len(snap.zones) > int(THR["max_zones"]):
        return False
    if len(org.frame_ring) > FRAME_RING_CAP:
        return False
    for entry in org.frame_ring:
        if (
            len(entry.render_packet.habitat_read_model.entities)
            > int(THR["habitat_read_model_max_entities"])
        ):
            return False
    return True


def run_100k() -> dict[str, Any]:
    timing = _proto_timing()
    n = int(THR["ticks_accelerated_min"])
    if _smoke_scale() < 1.0:
        n = max(2000, int(n * _smoke_scale()))
    db = _fresh_db("accelerated_100k.sqlite")
    cfg = _base_cfg(str(db), mode="P1", hz=float(timing["tick_hz"]), seed=int(timing["seed"]))
    org = create_organism(cfg)
    assert org._runtime_ready
    _prepare_organism(org)
    engine = _attach_habitat(org)
    cursor = RendererCursor(renderer_id="100k")
    renderer = HeadlessRenderer(renderer_id="100k")
    t0 = time.time()
    cpu0 = time.process_time()
    max_occ = 0
    gens: list[int] = []
    samples: list[dict[str, Any]] = []
    habitat_ok = True
    try:
        for i in range(n):
            org.tick_once()
            entry = org.frame_ring.read_latest(cursor)
            if entry is not None:
                renderer.render(entry)
            max_occ = max(max_occ, len(org.frame_ring))
            gens.append(org.embodiment_adapter.state.attachment_generation)
            if not _habitat_bounded(org, engine):
                habitat_ok = False
            if i % 5000 == 0 or i == n - 1:
                samples.append({"tick": i, "rss_mib": current_rss_mib(), "t": time.time() - t0})
        snap = org.authoritative_state()
        frames_absent = "frame_ring" not in snap and "expression" not in snap
        gen_mono = gens == sorted(gens)
        bounded = (
            habitat_ok
            and max_occ <= FRAME_RING_CAPACITY
            and max_occ <= FRAME_RING_CAP
            and frames_absent
            and gen_mono
        )
        org.snapshot_if_due(force=True)
        before = org.embodiment_adapter.state.to_state()
        org.close()
        loaded = load_organism(cfg)
        _prepare_organism(loaded)
        _attach_habitat(loaded)
        restart_ok = loaded.embodiment_adapter.state.to_state() == before
        loaded.close()
    except Exception:
        org.close()
        raise
    elapsed = time.time() - t0
    cpu = time.process_time() - cpu0
    rss_vals = [s["rss_mib"] for s in samples] or [current_rss_mib()]
    out = {
        "directive": "UMBRA-D-009",
        "adaptive_soak_supplement": "S3",
        "software_commit": _software_commit(),
        "ticks": n,
        "elapsed_s": elapsed,
        "cpu_s": cpu,
        "cpu_frac_of_one_core": cpu / max(elapsed, 1e-6),
        "rss_p95_mib": _percentile(rss_vals, 0.95),
        "frame_ring_max_occupancy": max_occ,
        "frame_ring_capacity_limit": FRAME_RING_CAP,
        "habitat_bounded": habitat_ok,
        "attachment_generations_monotonic": gen_mono,
        "presentation_absent_from_snapshot": frames_absent,
        "restart_continuity": restart_ok,
        "rss_samples": samples,
        "pass": bool(
            bounded
            and restart_ok
            and n >= (int(THR["ticks_accelerated_min"]) if _smoke_scale() >= 1.0 else n)
            and _percentile(rss_vals, 0.95) <= float(THR["rss_p95_mib_max"])
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "accelerated-100k-results.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n"
    )
    return out


def run_lifecycle() -> dict[str, Any]:
    _require_tk()
    import importlib

    TkinterRenderer = importlib.import_module("ui.reference_companion.tkinter_renderer").TkinterRenderer

    timing = _proto_timing()
    cycles = int(timing["lifecycle_cycles_min"])
    db = _fresh_db("lifecycle.sqlite")
    cfg = _base_cfg(str(db), mode="P2", hz=float(timing["tick_hz"]), seed=int(timing["seed"]) + 1)
    org = create_organism(cfg)
    assert org._runtime_ready
    _prepare_organism(org)
    _attach_habitat(org)
    tick_before = org.tick
    failures: list[str] = []
    continued = False
    try:
        for i in range(cycles):
            renderer = TkinterRenderer(
                renderer_id=f"life-{i}",
                diagnostics_visible=bool(PROTO["diagnostics_visible"]),
            )
            cursor = RendererCursor(renderer_id=f"life-{i}")
            org.tick_once()
            entry = org.frame_ring.read_latest(cursor)
            if entry is not None:
                renderer.render(entry)
            renderer.root.update_idletasks()
            renderer.root.update()
            renderer.close()
            try:
                if renderer.root.winfo_exists():
                    failures.append(f"root_alive_after_close:{i}")
            except Exception:
                pass
            org.tick_once()
        continued = org.tick > tick_before + cycles
    finally:
        org.close()
    out = {
        "directive": "UMBRA-D-009",
        "adaptive_soak_supplement": "S3",
        "software_commit": _software_commit(),
        "cycles": cycles,
        "failures": failures,
        "organism_continued": continued,
        "pass": bool(continued and not failures and cycles >= (100 if _smoke_scale() >= 1.0 else 5)),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "renderer-lifecycle-results.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n"
    )
    return out


def _ambiguity(
    *,
    slope: float,
    slope_ci: list[float],
    seg: list[float],
    sample_count: int,
    min_samples: int,
    renderer_exceptions: int,
    max_measurement: float,
    measured: float,
) -> str | None:
    if sample_count < min_samples:
        return "insufficient_samples"
    if renderer_exceptions > 0:
        return "renderer_errors"
    if _sustained_monotonic_growth(seg):
        return "sustained_segment_growth"
    lo, hi = slope_ci
    limit = float(THR["rss_slope_mib_per_hour_max"])
    near = limit * 0.6
    if slope > near and lo < limit < hi and (hi - lo) > 0.5:
        return "rss_slope_ci_ambiguous"
    if measured + 1.0 < max_measurement and slope > limit * 0.8 and hi > limit:
        return "rss_slope_near_limit_unstable"
    return None


def run_mode(mode: str) -> dict[str, Any]:
    if mode not in ("P0", "P1", "P2"):
        raise SystemExit(f"unknown_mode:{mode}")
    timing = _proto_timing()
    TkinterRenderer = None
    if mode == "P2":
        _require_tk()
        import importlib

        TkinterRenderer = importlib.import_module(
            "ui.reference_companion.tkinter_renderer"
        ).TkinterRenderer

    db = _fresh_db(f"soak_{mode}.sqlite")
    hz = float(timing["tick_hz"])
    period = 1.0 / hz
    cfg = _base_cfg(str(db), mode=mode, hz=hz, seed=int(timing["seed"]))
    org = create_organism(cfg)
    assert org._runtime_ready
    _prepare_organism(org)
    engine = _attach_habitat(org)

    renderer: Any = None
    cursor: RendererCursor | None = None
    pending_callbacks = 0
    rendered = 0
    dropped_stale = 0
    exceptions = 0
    max_occ = 0
    cursor_count = 0

    if mode == "P1":
        renderer = HeadlessRenderer(renderer_id="P1")
        cursor = RendererCursor(renderer_id="P1")
        cursor_count = 1
    elif mode == "P2":
        assert TkinterRenderer is not None
        renderer = TkinterRenderer(
            renderer_id="P2",
            diagnostics_visible=bool(PROTO["diagnostics_visible"]),
        )
        cursor = RendererCursor(renderer_id="P2")
        cursor_count = 1

    t_ready = time.time()
    cpu0 = time.process_time()
    db0 = _db_size_mib(db)
    samples_all: list[dict[str, Any]] = []
    sample_interval = float(timing["sample_interval_seconds"])
    next_sample = t_ready + sample_interval
    warmup = float(timing["warmup_seconds"])
    initial = float(timing["initial_measurement_seconds"])
    extension_step = float(timing["extension_seconds"])
    max_meas = float(timing["max_measurement_seconds"])
    min_samples = int(timing["minimum_samples"])

    def _tick_body() -> None:
        nonlocal rendered, dropped_stale, exceptions, max_occ, pending_callbacks
        org.tick_once()
        max_occ = max(max_occ, len(org.frame_ring))
        if cursor is not None and renderer is not None:
            entry = org.frame_ring.read_latest(cursor)
            if entry is None:
                dropped_stale += 1
            else:
                try:
                    if mode == "P2":
                        pending_callbacks += 1
                        renderer.render(entry)
                        renderer.root.update_idletasks()
                        renderer.root.update()
                        pending_callbacks = max(0, pending_callbacks - 1)
                    else:
                        renderer.render(entry)
                    rendered += 1
                    if getattr(renderer, "last_render_error", None) is not None:
                        exceptions += 1
                except Exception:
                    exceptions += 1
                    traceback.print_exc()

    def _run_until(deadline: float) -> None:
        nonlocal next_sample
        while time.time() < deadline:
            t_loop = time.monotonic()
            _tick_body()
            now = time.time()
            if now >= next_sample:
                samples_all.append(
                    {
                        "t": now - t_ready,
                        "rss_mib": current_rss_mib(),
                        "tick": org.tick,
                        "cpu_s": time.process_time() - cpu0,
                        "ring_occupancy": len(org.frame_ring),
                        "habitat_objects": len(engine.snapshot_view().objects),
                    }
                )
                next_sample += sample_interval
            sleep_for = period - (time.monotonic() - t_loop)
            if sleep_for > 0:
                time.sleep(sleep_for)

    extension_seconds = 0.0
    extension_reason: str | None = None
    jsonl_path = OUT / f"soak-{mode}.jsonl"
    try:
        _run_until(t_ready + warmup + initial)
        while True:
            elapsed_total = time.time() - t_ready
            measured = max(0.0, elapsed_total - warmup)
            post = [s for s in samples_all if s["t"] >= warmup]
            slope, ci = _robust_slope_mib_per_hour(post)
            seg = _segment_medians(post)
            reason = _ambiguity(
                slope=slope,
                slope_ci=ci,
                seg=seg,
                sample_count=len(post),
                min_samples=min_samples,
                renderer_exceptions=exceptions,
                max_measurement=max_meas,
                measured=measured,
            )
            if reason is None:
                break
            remaining = max_meas - measured
            if remaining < 1.0:
                extension_reason = f"inconclusive_after_max:{reason}"
                break
            step = min(extension_step, remaining)
            extension_seconds += step
            extension_reason = reason
            _run_until(time.time() + step)
    finally:
        try:
            if renderer is not None and hasattr(renderer, "close"):
                renderer.close()
        except Exception:
            pass
        org.snapshot_if_due(force=True)
        org.close()
        OUT.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w") as log:
            for row in samples_all:
                log.write(json.dumps(row) + "\n")

    elapsed = time.time() - t_ready
    cpu = time.process_time() - cpu0
    post = [s for s in samples_all if s["t"] >= warmup]
    slope, ci = _robust_slope_mib_per_hour(post)
    seg = _segment_medians(post)
    rss_vals = [float(s["rss_mib"]) for s in post] or [current_rss_mib()]
    cpu_frac = cpu / max(elapsed, 1e-6)
    cpu_fracs = []
    for i, s in enumerate(post):
        if i == 0:
            continue
        dt = float(s["t"]) - float(post[i - 1]["t"])
        dc = float(s["cpu_s"]) - float(post[i - 1]["cpu_s"])
        if dt > 0:
            cpu_fracs.append(dc / dt)
    display_env = os.environ.get("DISPLAY", "")
    tk_version = None
    if mode == "P2":
        import tkinter as tk

        tk_version = str(tk.TkVersion)

    measured = max(0.0, elapsed - warmup)
    limit = float(THR["rss_slope_mib_per_hour_max"])
    inconclusive_threat = bool(
        extension_reason
        and str(extension_reason).startswith("inconclusive")
        and (
            slope > limit * 0.8
            or _sustained_monotonic_growth(seg)
            or exceptions > 0
            or len(post) < min_samples
        )
    )
    abs_ok = (
        _percentile(rss_vals, 0.95) <= float(THR["rss_p95_mib_max"])
        and slope <= limit
        and cpu_frac <= float(THR["cpu_mean_frac_max"])
        and not _sustained_monotonic_growth(seg)
        and exceptions == 0
        and len(post) >= min_samples
        and measured + 1e-3 >= initial
        and not inconclusive_threat
        and max_occ <= FRAME_RING_CAP
    )
    out = {
        "directive": "UMBRA-D-009",
        "adaptive_soak_supplement": "S3",
        "mode": mode,
        "software_commit": _software_commit(),
        "warmup_seconds": warmup,
        "initial_measurement_seconds": initial,
        "extension_seconds": extension_seconds,
        "total_measurement_seconds": measured,
        "extension_reason": extension_reason,
        "sample_interval_seconds": sample_interval,
        "sample_count": len(post),
        "display_environment": display_env if mode == "P2" else "n/a",
        "tkinter_version": tk_version,
        "profile_hashes": {
            ABSTRACT_SHAPE_BODY_D009.profile_id: profile_definition_hash(ABSTRACT_SHAPE_BODY_D009),
        },
        "rss_p50_mib": _percentile(rss_vals, 0.50),
        "rss_p95_mib": _percentile(rss_vals, 0.95),
        "rss_peak_mib": max(rss_vals),
        "rss_slope_mib_per_hour": slope,
        "rss_slope_confidence_interval": ci,
        "rss_segment_medians_mib": seg,
        "cpu_mean_fraction": cpu_frac,
        "cpu_p95_fraction": _percentile(cpu_fracs, 0.95) if cpu_fracs else cpu_frac,
        "database_growth_mib": max(0.0, _db_size_mib(db) - db0),
        "frame_ring_max_occupancy": max_occ,
        "renderer_cursor_count": cursor_count,
        "pending_callback_count": pending_callbacks,
        "rendered_frame_count": rendered,
        "dropped_stale_frame_count": dropped_stale,
        "renderer_exception_count": exceptions,
        "duration_s": elapsed,
        "pass": bool(abs_ok),
        "smoke_scaled": _smoke_scale() < 1.0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    name = {"P0": "performance-core.json", "P1": "performance-headless.json", "P2": "performance-tkinter.json"}[
        mode
    ]
    (OUT / name).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def _delta(a: dict[str, Any], b: dict[str, Any]) -> dict[str, float]:
    return {
        "rss_p95_mib": float(a["rss_p95_mib"]) - float(b["rss_p95_mib"]),
        "rss_slope_mib_per_hour": float(a["rss_slope_mib_per_hour"]) - float(b["rss_slope_mib_per_hour"]),
        "cpu_mean_fraction": float(a["cpu_mean_fraction"]) - float(b["cpu_mean_fraction"]),
    }


def recompose(
    p0: dict[str, Any] | None = None,
    p1: dict[str, Any] | None = None,
    p2: dict[str, Any] | None = None,
    accel: dict[str, Any] | None = None,
    life: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def load(name: str) -> dict[str, Any] | None:
        p = OUT / name
        return json.loads(p.read_text()) if p.exists() else None

    p0 = p0 or load("performance-core.json")
    p1 = p1 or load("performance-headless.json")
    p2 = p2 or load("performance-tkinter.json")
    accel = accel or load("accelerated-100k-results.json")
    life = life or load("renderer-lifecycle-results.json")
    if not all((p0, p1, p2, accel, life)):
        missing = [
            n
            for n, v in (
                ("performance-core.json", p0),
                ("performance-headless.json", p1),
                ("performance-tkinter.json", p2),
                ("accelerated-100k-results.json", accel),
                ("renderer-lifecycle-results.json", life),
            )
            if v is None
        ]
        raise SystemExit(f"recompose_missing:{missing}")

    assert p0 and p1 and p2 and accel and life
    habitat_over_core = _delta(p1, p0)
    tkinter_over_headless = _delta(p2, p1)
    tkinter_over_core = _delta(p2, p0)

    def inc_ok(d: dict[str, float]) -> bool:
        return (
            d["rss_p95_mib"] <= float(THR["ui_incremental_rss_p95_mib_max"])
            and d["rss_slope_mib_per_hour"] <= float(THR["ui_incremental_rss_slope_mib_per_hour_max"])
            and d["cpu_mean_fraction"] <= float(THR["ui_incremental_cpu_mean_frac_max"])
        )

    modes_ok = all(m.get("pass") for m in (p0, p1, p2))
    inc_pass = inc_ok(habitat_over_core) and inc_ok(tkinter_over_headless) and inc_ok(tkinter_over_core)
    smoke = any(m.get("smoke_scaled") for m in (p0, p1, p2))
    out = {
        "directive": "UMBRA-D-009",
        "adaptive_soak_supplement": "S3",
        "supplement_note": (
            "D-009 Task 14 used authorized adaptive-soak Supplement S3 "
            "(warm-up 300s + initial 1800s measurement, adaptive extension to "
            "max 3600s per mode) rather than the original fixed two-hour duration."
        ),
        "software_commit": _software_commit(),
        "protocol": PROTO,
        "thresholds": {
            "rss_p95_mib_max": THR["rss_p95_mib_max"],
            "rss_slope_mib_per_hour_max": THR["rss_slope_mib_per_hour_max"],
            "cpu_mean_frac_max": THR["cpu_mean_frac_max"],
            "ui_incremental_rss_p95_mib_max": THR["ui_incremental_rss_p95_mib_max"],
            "ui_incremental_rss_slope_mib_per_hour_max": THR["ui_incremental_rss_slope_mib_per_hour_max"],
            "ui_incremental_cpu_mean_frac_max": THR["ui_incremental_cpu_mean_frac_max"],
        },
        "modes": {"P0": p0, "P1": p1, "P2": p2},
        "habitat_agency_over_core": habitat_over_core,
        "tkinter_over_headless": tkinter_over_headless,
        "tkinter_over_core": tkinter_over_core,
        "accelerated_100k": {"pass": accel.get("pass"), "ticks": accel.get("ticks")},
        "renderer_lifecycle": {"pass": life.get("pass"), "cycles": life.get("cycles")},
        "smoke_scaled": smoke,
        "pass": bool(
            modes_ok
            and inc_pass
            and accel.get("pass")
            and life.get("pass")
            and not smoke
        ),
    }
    out["soak"] = {
        "protocol": "S3",
        "duration_s": min(float(m["total_measurement_seconds"]) for m in (p0, p1, p2)),
        "rss_p95_mib": max(float(m["rss_p95_mib"]) for m in (p0, p1, p2)),
        "rss_slope_mib_per_hour": max(float(m["rss_slope_mib_per_hour"]) for m in (p0, p1, p2)),
        "cpu_mean_frac": max(float(m["cpu_mean_fraction"]) for m in (p0, p1, p2)),
    }
    out["ui_incremental"] = {
        "rss_p95_mib": tkinter_over_core["rss_p95_mib"],
        "rss_slope_mib_per_hour": tkinter_over_core["rss_slope_mib_per_hour"],
        "cpu_mean_frac": tkinter_over_core["cpu_mean_fraction"],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "performance-results.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["P0", "P1", "P2", "100k", "lifecycle", "recompose", "all"],
        default="all",
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if args.mode == "100k":
        r = run_100k()
        print(json.dumps({"100k_pass": r["pass"]}, indent=2))
        raise SystemExit(0 if r["pass"] else 1)
    if args.mode == "lifecycle":
        r = run_lifecycle()
        print(json.dumps({"lifecycle_pass": r["pass"]}, indent=2))
        raise SystemExit(0 if r["pass"] else 1)
    if args.mode in ("P0", "P1", "P2"):
        r = run_mode(args.mode)
        print(json.dumps({"mode": args.mode, "pass": r["pass"]}, indent=2))
        raise SystemExit(0 if r["pass"] else 1)
    if args.mode == "recompose":
        r = recompose()
        print(json.dumps({"pass": r["pass"], "smoke": r["smoke_scaled"]}, indent=2))
        raise SystemExit(0 if r["pass"] else 1)

    results: dict[str, Any] = {}
    for step in ("100k", "lifecycle", "P0", "P1", "P2"):
        print(f"=== running {step} ===", flush=True)
        env = os.environ.copy()
        proc = subprocess.run(
            [sys.executable, "-m", "experiments.d009.run_performance", "--mode", step],
            cwd=ROOT,
            env=env,
        )
        if proc.returncode != 0:
            raise SystemExit(f"step_failed:{step}:{proc.returncode}")
        results[step] = "ok"
    summary = recompose()
    print(json.dumps({"steps": results, "pass": summary["pass"]}, indent=2))
    raise SystemExit(0 if summary["pass"] else 1)


if __name__ == "__main__":
    main()
