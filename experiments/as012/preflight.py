"""Exact AS-012 entrypoint preflight using only non-formal seeds."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from experiments.as012.downstream import VARIANTS, ablation, boundedness, soak
from experiments.as012.full_config import BASELINE, DIRECTIVE


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="as012-exact-entrypoint-preflight-"))
    rows = []
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        b = boundedness(39124001, root / "boundedness", ticks=40)
        rows.append({"entrypoint": "boundedness", "returned": True, "ticks": b["ticks"], "cpu_metric_present": "cpu_fraction_one_core" in b, "restart_continuity": b["restart_continuity"]})
        s = soak(39124002, root / "soak", warmup_seconds=0.2, measure_seconds=0.2)
        rows.append({"entrypoint": "soak", "returned": True, "ticks": s["ticks"], "result_schema": s["schema"], "restart_continuity": s["restart_continuity"]})
        for variant in VARIANTS:
            result = ablation(39124003, root / f"ablation-{variant}", variant, ticks=8)
            rows.append({"entrypoint": "ablation", "variant": variant, "returned": True, "seed": result["seed"], "bounded": result["bounded_continuation_enabled"], "route": result["route_learning_enabled"], "terminal_seam": result["terminal_readiness_seam"], "fingerprint": result["configuration_fingerprint"]})
        status = "PASS" if all(row["returned"] for row in rows) else "FAIL"
        result = {"schema": "AS012_EXACT_ENTRYPOINT_PREFLIGHT_V1", "directive": DIRECTIVE, "baseline": BASELINE, "formal_seeds_used": [], "matched_ablation_preflight_seed": 39124003, "rows": rows, "status": status}
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            tmp = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
            with tmp.open("xb") as handle:
                handle.write(rendered.encode()); handle.flush(); os.fsync(handle.fileno())
            if args.output.exists():
                tmp.unlink(missing_ok=True); raise FileExistsError(args.output)
            os.replace(tmp, args.output)
            fd = os.open(args.output.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        print(rendered, end="")
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
