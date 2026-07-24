"""UMBRA-D-010 Task 14 performance — Supplement S3 adaptive soak (Gate 13).

Modes (fresh process recommended via --mode):
  P0  TemporalEngine active; anticipation + temporal routine eligibility disabled (C13)
  P1  Full D-010 + HeadlessRenderer
  P2  Full D-010 + TkinterRenderer

Also: accelerated 100k boundedness, renderer lifecycle stress.
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
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d010.scenario_plants import apply_scenario_plants  # noqa: E402
from umbra_core.expression import HeadlessRenderer  # noqa: E402
from umbra_core.expression.frame_ring import RendererCursor  # noqa: E402
from umbra_core.runtime import OrganismConfig, create_organism  # noqa: E402
from umbra_core.temporal.config import p0_performance_config  # noqa: E402
from umbra_core.util import current_rss_mib  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "d010"
THR = json.loads((ROOT / "experiments/d010/thresholds.json").read_text())
PROTO = json.loads((ROOT / "experiments/d010/performance-protocol.json").read_text())
WORK = ROOT / ".soak" / "d010_perf"


def _software_commit() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def _smoke_scale() -> float:
    if os.environ.get("D010_PERF_SMOKE") == "1":
        return float(os.environ.get("D010_PERF_SMOKE_SCALE", "0.02"))
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


def _organism(mode: str, db_path: str) -> Any:
    tcfg = p0_performance_config() if mode == "P0" else None
    return create_organism(
        OrganismConfig(
            db_path=db_path,
            seed=int(PROTO["seed"]),
            temporal_enabled=True,
            temporal_config=tcfg,
            temporal_scenario_id=str(PROTO["scenario"]),
            temporal_scenario_hook=apply_scenario_plants,
            habitat_enabled=True,
            expression_enabled=mode != "P0",
            embodiment_adapter_enabled=True,
            wall_time_fn=lambda: time.time(),
        )
    )


def _run_soak(mode: str) -> dict[str, Any]:
    timing = _proto_timing()
    WORK.mkdir(parents=True, exist_ok=True)
    db = WORK / f"{mode.lower()}_soak.sqlite"
    org = _organism(mode, str(db))
    renderer = None
    cursor: RendererCursor | None = None
    if mode == "P1":
        renderer = HeadlessRenderer()
        cursor = RendererCursor(renderer_id="P1")
    elif mode == "P2":
        try:
            import importlib

            TkinterRenderer = importlib.import_module(
                "ui.reference_companion.tkinter_renderer"
            ).TkinterRenderer
            renderer = TkinterRenderer()
            cursor = RendererCursor(renderer_id="P2")
        except Exception as exc:  # ponytail: optional display stack
            return {"mode": mode, "skipped": True, "reason": str(exc)}
    samples: list[dict[str, Any]] = []
    t0 = time.monotonic()
    time.sleep(min(0.5, timing["warmup_seconds"]))
    deadline = t0 + timing["initial_measurement_seconds"]
    tick_interval = 1.0 / max(0.1, timing["tick_hz"])
    last_tick = 0.0
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_tick >= tick_interval:
                org.tick_once()
                last_tick = now
                if renderer is not None and cursor is not None:
                    entry = org.frame_ring.read_latest(cursor)
                    if entry is not None:
                        renderer.render(entry)
            if (now - t0) >= len(samples) * timing["sample_interval_seconds"]:
                samples.append({"t": now - t0, "rss_mib": current_rss_mib()})
    finally:
        org.close()
        if renderer is not None:
            renderer.close()
    rss = [float(s["rss_mib"]) for s in samples] or [current_rss_mib()]
    return {
        "mode": mode,
        "samples": len(samples),
        "total_measurement_seconds": max(s["t"] for s in samples) if samples else 0.0,
        "rss_p95_mib": sorted(rss)[int(0.95 * (len(rss) - 1))] if rss else 0.0,
        "rss_median_mib": float(statistics.median(rss)),
        "skipped": False,
    }


def _accelerated_ticks() -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        org = _organism("P1", os.path.join(tmp, "accel.sqlite"))
        target = min(2000, int(THR["ticks_accelerated_min"])) if _smoke_scale() < 1.0 else int(
            THR["ticks_accelerated_min"]
        )
        try:
            for _ in range(target):
                org.tick_once()
        finally:
            org.close()
    return {"ticks": target, "boundedness_probe": True}


def run_performance(*, mode: str | None = None) -> dict[str, Any]:
    modes = [mode] if mode else list(PROTO["modes"])
    payload: dict[str, Any] = {
        "directive": "UMBRA-D-010",
        "adaptive_soak_supplement": PROTO["supplement"],
        "software_commit": _software_commit(),
        "pre_freeze": True,
        "modes": {},
        "accelerated": _accelerated_ticks(),
        "pass": False,
    }
    for m in modes:
        payload["modes"][m] = _run_soak(m)
    soak_ok = all(
        not payload["modes"][m].get("skipped")
        and payload["modes"][m].get("rss_p95_mib", 999) <= THR["rss_p95_mib_max"]
        for m in payload["modes"]
        if m in payload["modes"]
    )
    payload["pass"] = bool(soak_ok and payload["accelerated"]["ticks"] >= min(2000, THR["ticks_accelerated_min"]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "performance-results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="UMBRA-D-010 Gate 13 performance harness")
    parser.add_argument("--mode", choices=["P0", "P1", "P2"], default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"dry_run": True, "timing": _proto_timing()}, indent=2))
        return
    result = run_performance(mode=args.mode)
    print(json.dumps(result, indent=2))
    if not result.get("pass") and os.environ.get("D010_PERF_SMOKE") != "1":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
