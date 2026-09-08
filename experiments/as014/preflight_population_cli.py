"""Literal, non-formal preflight for the AS-014 population CLI surface."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from experiments.as014.publication import publish_json
from experiments.as014.qualification import REGIMES


PYTHON = "/home/sketch/cs14n-runtime/bin/python"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="as014-population-cli-preflight-") as directory:
        root = Path(directory)
        seeds = {
            regime: [41_414_300 + (regime_index * 8) + index for index in range(8)]
            for regime_index, regime in enumerate(REGIMES)
        }
        manifest = {
            "schema": "AS014_SEED_MANIFEST_V1",
            "directive": "AS014_FORMAL_RUNNER_PREFLIGHT",
            "formal_regimes": seeds,
            "formal": False,
            "preflight_horizon": 1,
        }
        manifest_path = root / "preflight-manifest.json"
        publish_json(manifest_path, manifest, schema="AS014_SEED_MANIFEST_V1")
        work = root / "work"
        completed = subprocess.run(
            [
                PYTHON,
                "-m",
                "experiments.as014.run_qualification",
                "--manifest",
                str(manifest_path),
                "--work",
                str(work),
                "--preflight-horizon",
                "1",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        checkpoint = work / "AS014_FULL_POPULATION.computed-result.json"
        case_count = len(list((work / "case-results").glob("*.json")))
        result = {
            "schema": "AS014_FORMAL_RUNNER_CLI_PREFLIGHT_V1",
            "directive": "UMBRA-AS-014",
            "formal": False,
            "command_exit_code": completed.returncode,
            "case_count": case_count,
            "checkpoint_exists": checkpoint.exists(),
            "stderr_tail": completed.stderr[-2000:],
            "checks": {
                "literal_cli_exit_zero": completed.returncode == 0,
                "all_32_case_results_durable": case_count == 32,
                "computed_result_exists": checkpoint.exists(),
            },
        }
    result["pass"] = all(result["checks"].values())
    # The inner CLI has already published its own durable preflight result;
    # preserve a separate wrapper record rather than overwrite it.
    from tools.as014_evidence import publish

    digest = publish("AS014_FORMAL_RUNNER_CLI_WRAPPER_PREFLIGHT.json", result)
    print(json.dumps({"pass": result["pass"], "sha256": digest}, sort_keys=True))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
