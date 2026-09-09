#!/usr/bin/env python3
"""Record the sealed AS-015 starting state before any organism execution."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.as015_evidence import publish


BASELINE = "b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7"
AS014_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-014-persistent-ledger-boundedness-completion-r1"
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    required = {
        "AS014_RESULT.md": ROOT / ".agent/tasks/active/UMBRA-AS-014/RESULT.md",
        "AS014_MANIFEST.json": AS014_ROOT / "AS014_EVIDENCE_MANIFEST.json",
        "AS014_FAILURE_ROW.json": AS014_ROOT / "AS014_FORMAL_POPULATION_WORK/case-results/R1-01-32550454.json",
    }
    value = {
        "schema": "AS015_STATE_RECONCILIATION_V1",
        "directive": "UMBRA-AS-015",
        "phase": "pre_production_change",
        "baseline": BASELINE,
        "head_at_reconciliation": git("rev-parse", "HEAD"),
        "local_master_at_reconciliation": git("rev-parse", "master"),
        "github_master_at_reconciliation": git("rev-parse", "github/master"),
        "baseline_reconciled": all(git("rev-parse", ref) == BASELINE for ref in ("HEAD", "master", "github/master")),
        "as014": {
            "verdict": "AS014_FRESH_R1_FAIL",
            "failed_seed": 32550454,
            "first_no_safe_action_tick": 346,
            "critical_fatigue_tick": 347,
            "checkpoint_epoch": 0,
            "formal_retry_reseed": "0/0",
            "preserved": True,
        },
        "required_artifacts": {name: str(path) for name, path in required.items()},
        "required_artifacts_present": {name: path.is_file() for name, path in required.items()},
        "organism_execution_before_as015_lock": 0,
        "notion_current_authority": "UMBRA-AS-015 (canonical SOT fetched before this record)",
        "result": "PASS",
    }
    if not value["baseline_reconciled"] or not all(value["required_artifacts_present"].values()):
        value["result"] = "FAIL"
    publish("AS015_STATE_RECONCILIATION.json", value)
    print(json.dumps(value, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
