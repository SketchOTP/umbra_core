#!/usr/bin/env python3
"""Exercise the literal AS-016 population CLI without formal seeds."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.as016_evidence import publish


def main() -> None:
    manifest = ROOT / "experiments/as016/preflight_population_manifest.json"
    with tempfile.TemporaryDirectory(prefix="as016-population-cli-") as directory:
        work = Path(directory) / "work"
        command = [
            sys.executable, "-m", "experiments.as016.run_qualification",
            "--manifest", str(manifest), "--work", str(work),
            "--preflight-horizon", "80", "--preflight-label", "POPULATION_CLI_V1",
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        result_path = Path(
            "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
            "umbra-as-016-regulatory-execution-recovery-requalification-r1/"
            "AS016_PREFLIGHT_POPULATION_CLI_V1_RESULT.json"
        )
        row = {
            "schema": "AS016_FORMAL_POPULATION_CLI_PREFLIGHT_V1",
            "directive": "UMBRA-AS-016",
            "classification": "development_only_not_formal_qualification",
            "formal_seeds_used": [],
            "manifest": str(manifest),
            "command": command,
            "exit_code": completed.returncode,
            "result_exists": result_path.exists(),
            "work_case_results": len(list((work / "case-results").glob("*.json"))),
            "stderr_tail": completed.stderr[-2000:],
        }
        if result_path.exists():
            value = json.loads(result_path.read_text())
            row["result"] = {
                key: value.get(key)
                for key in ("all_completed", "completed_runs", "expected_runs", "all_case_results_durable")
            }
        row["status"] = "PASS" if (
            row["exit_code"] == 0 and row["result_exists"]
            and row.get("result", {}).get("all_completed") is True
            and row.get("result", {}).get("all_case_results_durable") is True
            and row["work_case_results"] == 4
        ) else "FAIL"
    digest = publish("AS016_FORMAL_POPULATION_CLI_PREFLIGHT_V1.json", row)
    print(json.dumps({"status": row["status"], "sha256": digest}, sort_keys=True))
    if row["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
