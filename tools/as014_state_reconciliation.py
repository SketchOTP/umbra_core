#!/usr/bin/env python3
"""Read-only AS-014 start and predecessor reconciliation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.as014_evidence import publish


BASELINE = "a97171a2dab7c1750e2556727bce9e3648bb359a"
AS007_FREEZE = "f0ac33212b3cb0081e16341bba31db69043a9292"
AS013 = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-013-publication-safe-boundedness-recovery-r1")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    predecessor = json.loads((AS013 / "AS013_LONG_HORIZON_BOUNDEDNESS_FAILURE.json").read_text())
    baseline_production = git("diff", "--name-only", f"{AS007_FREEZE}..{BASELINE}", "--", "umbra_core").splitlines()
    current = git("rev-parse", "HEAD")
    value = {
        "schema": "AS014_STATE_RECONCILIATION_V1",
        "directive": "UMBRA-AS-014",
        "starting_baseline": BASELINE,
        "as007_scientific_freeze": AS007_FREEZE,
        "current_head_at_reconciliation": current,
        "baseline_is_ancestor_of_current": subprocess.run(
            ["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=ROOT, check=False
        ).returncode == 0,
        "production_delta_as007_to_as014_start": baseline_production,
        "as013_permanent_verdict": predecessor.get("terminal_verdict"),
        "as013_completed_ticks": predecessor.get("result", {}).get("ticks"),
        "as013_retained_files": sorted(path.name for path in AS013.iterdir() if path.is_file()),
        "inherited_qualified": {
            "as007_known_r1_full_configuration": "retained",
            "as010_full_configuration_population": "32/32 retained",
            "as010_lifecycle": "PASS retained",
        },
        "as014_scope": "production persistence/replay repair and complete affected requalification",
        "result": "PASS" if not baseline_production and predecessor.get("terminal_verdict") == "AS013_LONG_HORIZON_BOUNDEDNESS_FAIL" else "FAIL",
    }
    publish("AS014_STATE_RECONCILIATION.json", value)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
