"""Literal AS-015 CLI-surface preflight for every frozen downstream mode."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from experiments.as015.downstream import VARIANTS
from experiments.as015.full_config import BASELINE, DIRECTIVE
from tools.as015_evidence import publish


SEEDS = {
    "lifecycle": 41515011,
    "boundedness": 41515012,
    "soak": 41515013,
    "ablation": 41515014,
}


def _run(root: Path, mode: str, seed: int, variant: str | None = None) -> dict[str, Any]:
    suffix = f"{mode}-{variant or 'default'}"
    work = root / f"work-{suffix}"
    checkpoint = root / f"{suffix}.computed-result.json"
    output = root / f"{suffix}.json"
    command = [
        sys.executable,
        "-m",
        "experiments.as015.run_downstream",
        "--mode",
        mode,
        "--seed",
        str(seed),
        "--work",
        str(work),
        "--checkpoint",
        str(checkpoint),
        "--output",
        str(output),
        "--preflight-ledger-tail",
        "64",
    ]
    if mode == "boundedness":
        command += ["--ticks", "80"]
    elif mode == "soak":
        command += ["--warmup-seconds", "3", "--measure-seconds", "3"]
    elif mode == "ablation":
        command += ["--variant", str(variant), "--ticks", "80"]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    row: dict[str, Any] = {
        "mode": mode,
        "variant": variant,
        "seed": seed,
        "command": command,
        "exit_code": completed.returncode,
        "output_exists": output.exists(),
        "checkpoint_exists": checkpoint.exists(),
        "temporary_publication_files": sorted(path.name for path in root.glob(".*.tmp")),
        "stderr_tail": completed.stderr[-2000:],
    }
    if completed.returncode == 0 and output.exists() and checkpoint.exists():
        final = json.loads(output.read_text())
        checkpoint_value = json.loads(checkpoint.read_text())
        row.update(
            result_schema=final.get("schema"),
            result_seed=final.get("seed"),
            result_directive=final.get("directive"),
            checkpoint_matches_output=checkpoint_value == final,
            restart_result_recorded="restart_continuity" in final or mode == "lifecycle",
            viability_kernel_recorded="viability_kernel_enabled" in final
            or mode == "lifecycle",
        )
    row["pass"] = bool(
        row["exit_code"] == 0
        and row["output_exists"]
        and row["checkpoint_exists"]
        and row.get("checkpoint_matches_output")
        and row.get("result_seed") == seed
        and row.get("result_directive") == DIRECTIVE
        and not row["temporary_publication_files"]
    )
    return row


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="as015-cli-preflight-") as directory:
        root = Path(directory)
        rows = [
            _run(root, "lifecycle", SEEDS["lifecycle"]),
            _run(root, "boundedness", SEEDS["boundedness"]),
            _run(root, "soak", SEEDS["soak"]),
        ]
        rows.extend(
            _run(root, "ablation", SEEDS["ablation"], variant)
            for variant in VARIANTS
        )
        result = {
            "schema": "AS015_FULL_CLI_SURFACE_PREFLIGHT_V2",
            "directive": DIRECTIVE,
            "baseline": BASELINE,
            "candidate_revision": "verified_executability_denial_learning",
            "formal_seeds_used": [],
            "rows": rows,
            "status": "PASS" if all(row["pass"] for row in rows) else "FAIL",
        }
    publish("AS015_FULL_CLI_SURFACE_PREFLIGHT_V2.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
