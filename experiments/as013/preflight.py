"""End-to-end AS-013 CLI preflight using only non-formal seeds."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from experiments.as013.downstream import VARIANTS
from experiments.as013.full_config import BASELINE, DIRECTIVE


PYTHON = "/home/sketch/cs14n-runtime/bin/python"


def _run(root: Path, mode: str, seed: int, *, variant: str | None = None) -> dict:
    work = root / f"work-{mode}-{variant or 'default'}"
    output = root / f"{mode}-{variant or 'default'}.json"
    checkpoint = root / f"{mode}-{variant or 'default'}.computed-result.json"
    command = [PYTHON, "-m", "experiments.as013.downstream", "--mode", mode, "--seed", str(seed), "--work", str(work), "--checkpoint", str(checkpoint), "--output", str(output)]
    if variant is not None:
        command += ["--variant", variant, "--ticks", "8"]
    elif mode == "boundedness":
        command += ["--ticks", "40"]
    else:
        command += ["--warmup-seconds", "0.2", "--measure-seconds", "0.2"]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    row = {
        "mode": mode,
        "variant": variant,
        "seed": seed,
        "command": command,
        "exit_code": completed.returncode,
        "output_exists": output.exists(),
        "checkpoint_exists": checkpoint.exists(),
        "temporary_publication_files": [str(p) for p in root.glob(".*.tmp")],
        "stderr_tail": completed.stderr[-2000:],
    }
    if completed.returncode == 0 and output.exists() and checkpoint.exists():
        output_value = json.loads(output.read_text(encoding="utf-8"))
        checkpoint_value = json.loads(checkpoint.read_text(encoding="utf-8"))
        row.update({
            "schema": output_value.get("schema"),
            "checkpoint_schema": checkpoint_value.get("schema"),
            "checkpoint_equals_output": checkpoint_value == output_value,
            "result_seed": output_value.get("seed"),
            "result_directive": output_value.get("directive"),
            "cpu_metric_present": "cpu_seconds" in output_value,
        })
    row["pass"] = bool(
        completed.returncode == 0
        and output.exists()
        and checkpoint.exists()
        and row.get("checkpoint_equals_output") is True
        and row.get("result_seed") == seed
        and row.get("result_directive") == DIRECTIVE
    )
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="as013-cli-preflight-"))
    rows = []
    try:
        rows.append(_run(root, "boundedness", 39134001))
        rows.append(_run(root, "soak", 39134002))
        for variant in VARIANTS:
            rows.append(_run(root, "ablation", 39134003, variant=variant))
        result = {
            "schema": "AS013_FULL_CLI_SURFACE_PREFLIGHT_V1",
            "directive": DIRECTIVE,
            "baseline": BASELINE,
            "formal_seeds_used": [],
            "matched_ablation_preflight_seed": 39134003,
            "execution_surface": "subprocess python -m experiments.as013.downstream",
            "rows": rows,
            "status": "PASS" if all(row["pass"] for row in rows) else "FAIL",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        tmp = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
        with tmp.open("x", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        if args.output.exists():
            tmp.unlink(missing_ok=True)
            raise FileExistsError(args.output)
        os.replace(tmp, args.output)
        fd = os.open(args.output.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        print(rendered, end="")
        if result["status"] != "PASS":
            raise SystemExit(1)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
