"""Literal CLI-surface preflight for every AS-014 downstream execution mode."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from experiments.as014.downstream import VARIANTS
from experiments.as014.full_config import BASELINE, DIRECTIVE
from tools.as014_evidence import publish


PYTHON = "/home/sketch/cs14n-runtime/bin/python"
SEEDS = {
    "boundedness": 41414021,
    "soak": 41414022,
    "ablation": 41414023,
}


def _run(root: Path, mode: str, seed: int, variant: str | None = None) -> dict[str, Any]:
    suffix = f"{mode}-{variant or 'default'}"
    work, checkpoint, output = root / f"work-{suffix}", root / f"{suffix}.computed-result.json", root / f"{suffix}.json"
    command = [
        PYTHON, "-m", "experiments.as014.run_downstream", "--mode", mode,
        "--seed", str(seed), "--work", str(work), "--checkpoint", str(checkpoint),
        "--output", str(output), "--preflight-ledger-tail", "64",
    ]
    if mode == "boundedness":
        command += ["--ticks", "40"]
    elif mode == "soak":
        command += ["--warmup-seconds", "3", "--measure-seconds", "3"]
    else:
        command += ["--variant", str(variant), "--ticks", "40"]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    result: dict[str, Any] = {
        "mode": mode,
        "variant": variant,
        "seed": seed,
        "command": command,
        "exit_code": completed.returncode,
        "output_exists": output.exists(),
        "checkpoint_exists": checkpoint.exists(),
        "temporary_publication_files": sorted(str(path.name) for path in root.glob(".*.tmp")),
        "stderr_tail": completed.stderr[-2000:],
    }
    if completed.returncode == 0 and output.exists() and checkpoint.exists():
        output_value, checkpoint_value = json.loads(output.read_text()), json.loads(checkpoint.read_text())
        result.update({
            "result_schema": output_value.get("schema"),
            "result_seed": output_value.get("seed"),
            "result_directive": output_value.get("directive"),
            "checkpoint_matches_output": checkpoint_value == output_value,
            "process_cpu_recorded": "process_cpu_seconds" in output_value,
            "restart_result_recorded": "restart_continuity" in output_value,
        })
    result["pass"] = bool(
        result["exit_code"] == 0
        and result["output_exists"]
        and result["checkpoint_exists"]
        and result.get("checkpoint_matches_output")
        and result.get("result_seed") == seed
        and result.get("result_directive") == DIRECTIVE
        and not result["temporary_publication_files"]
    )
    return result


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="as014-cli-preflight-") as directory:
        root = Path(directory)
        rows = [_run(root, "boundedness", SEEDS["boundedness"]), _run(root, "soak", SEEDS["soak"])]
        rows.extend(_run(root, "ablation", SEEDS["ablation"], variant) for variant in VARIANTS)
        result = {
            "schema": "AS014_FULL_CLI_SURFACE_PREFLIGHT_V1",
            "directive": DIRECTIVE,
            "baseline": BASELINE,
            "formal_seeds_used": [],
            "rows": rows,
            "status": "PASS" if all(row["pass"] for row in rows) else "FAIL",
        }
    publish("AS014_FULL_CLI_SURFACE_PREFLIGHT.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
