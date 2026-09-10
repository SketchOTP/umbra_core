"""Literal AS-016 CLI-surface preflight for downstream qualification modes."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from experiments.as016.downstream import VARIANTS
from experiments.as016.full_config import BASELINE, DIRECTIVE
from tools.as016_evidence import publish


SEEDS = {"lifecycle": 41616011, "boundedness": 41616012, "soak": 41616013, "ablation": 41616014}


def _run(root: Path, mode: str, seed: int, variant: str | None = None) -> dict[str, Any]:
    suffix = f"{mode}-{variant or 'default'}"
    work, checkpoint, output = root / f"work-{suffix}", root / f"{suffix}.computed-result.json", root / f"{suffix}.json"
    command = [sys.executable, "-m", "experiments.as016.run_downstream", "--mode", mode, "--seed", str(seed), "--work", str(work), "--checkpoint", str(checkpoint), "--output", str(output), "--preflight-ledger-tail", "64"]
    if mode == "boundedness":
        command += ["--ticks", "80"]
    elif mode == "soak":
        command += ["--warmup-seconds", "3", "--measure-seconds", "3"]
    elif mode == "ablation":
        command += ["--variant", str(variant), "--ticks", "80"]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    row: dict[str, Any] = {
        "mode": mode, "variant": variant, "seed": seed, "command": command,
        "exit_code": completed.returncode, "output_exists": output.exists(),
        "checkpoint_exists": checkpoint.exists(),
        "temporary_publication_files": sorted(path.name for path in root.glob(".*.tmp")),
        "stderr_tail": completed.stderr[-2000:],
    }
    if completed.returncode == 0 and output.exists() and checkpoint.exists():
        final, checkpoint_value = json.loads(output.read_text()), json.loads(checkpoint.read_text())
        row.update(result_schema=final.get("schema"), result_seed=final.get("seed"), result_directive=final.get("directive"), checkpoint_matches_output=checkpoint_value == final)
    row["pass"] = bool(row["exit_code"] == 0 and row["output_exists"] and row["checkpoint_exists"] and row.get("checkpoint_matches_output") and row.get("result_seed") == seed and row.get("result_directive") == DIRECTIVE and not row["temporary_publication_files"])
    return row


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="as016-cli-preflight-") as directory:
        root = Path(directory)
        rows = [_run(root, "lifecycle", SEEDS["lifecycle"]), _run(root, "boundedness", SEEDS["boundedness"]), _run(root, "soak", SEEDS["soak"])]
        rows.extend(_run(root, "ablation", SEEDS["ablation"], variant) for variant in VARIANTS)
        result = {
            # V1 was durably published before the later direct-path
            # recoverability correction.  This independently exercises the
            # unchanged literal CLI surface against the current candidate.
            "schema": "AS016_FULL_CLI_SURFACE_PREFLIGHT_V2", "directive": DIRECTIVE,
            "baseline": BASELINE, "formal_seeds_used": [], "rows": rows,
            "status": "PASS" if all(row["pass"] for row in rows) else "FAIL",
        }
    publish("AS016_FULL_CLI_SURFACE_PREFLIGHT_V2.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
