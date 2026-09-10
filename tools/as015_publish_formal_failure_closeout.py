#!/usr/bin/env python3
"""Seal the first AS-015 formal failure without reinterpreting it."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from tools.as015_evidence import ROOT, publish


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    failure_path = ROOT / "AS015_FORMAL_POPULATION_FAILURE_V1.json"
    failure = json.loads(failure_path.read_text())
    rows = failure["rows"]
    failed = rows[-1]
    if failure.get("terminal") != "AS015_FRESH_R2_FAIL" or failed.get("terminal") != "scientific_failure":
        raise RuntimeError("AS015_FIRST_FORMAL_FAILURE_RECORD_INVALID")
    if len(rows) != 19 or int(failed["seed"]) != 1995954:
        raise RuntimeError("AS015_FIRST_FORMAL_FAILURE_UNEXPECTED")
    critical = failed["critical_failure"]
    closeout = {
        "schema": "AS015_FORMAL_POPULATION_CLOSEOUT_V1",
        "directive": "UMBRA-AS-015",
        "terminal_verdict": "AS015_FRESH_R2_FAIL",
        "scientific_implementation_sha": "76182fca517b69ee6b9eef6c9ec9d44efa520d49",
        "governance_publication_sha": "3d277949ccae06d77cced66a1b1d89432605b777",
        "lock": {
            "file": "AS015_SCIENTIFIC_LOCK_V1.json",
            "sha256": _sha(ROOT / "AS015_SCIENTIFIC_LOCK_V1.json"),
        },
        "formal_seed_manifest": {
            "file": "AS015_SEED_MANIFEST.json",
            "sha256": _sha(ROOT / "AS015_SEED_MANIFEST.json"),
            "used_prefix_only": True,
        },
        "population": {
            "expected_organisms": 32,
            "completed_case_records": len(rows),
            "successful_completed_cases": sum(row["terminal"] == "completed" for row in rows),
            "by_regime": dict(Counter(row["regime"] for row in rows)),
            "completed_ticks": sum(int(row["ticks"]) for row in rows),
            "all_case_records_durable": failure.get("all_case_results_durable") is True,
            "failure_record": {
                "regime": failed["regime"],
                "seed_index": failed["seed_index"],
                "seed": failed["seed"],
                "ticks": failed["ticks"],
                "first_no_safe_action_tick": failed["first_no_safe_action"],
                "critical_tick": critical["tick"],
                "critical_physiology": critical["physiology"],
                "last_verified_outcome_reason": critical["result"]["outcome"]["reason"],
            },
        },
        "frozen_stop_rule_applied": {
            "retry": 0,
            "reseed": 0,
            "substitution": 0,
            "production_change": 0,
            "downstream_lifecycle": "NOT_RUN",
            "downstream_100k": "NOT_RUN",
            "downstream_s3": "NOT_RUN",
            "downstream_ablation": "NOT_RUN",
            "close_03": "NOT_RUN",
        },
        "interpretation_boundary": (
            "This artifact preserves the frozen R2 scientific failure. It does not "
            "attribute an underlying recovery, perception, world-model, persistence, "
            "or harness cause beyond the recorded formal facts."
        ),
        "failure_artifact": {
            "file": failure_path.name,
            "sha256": _sha(failure_path),
        },
    }
    digest = publish("AS015_FORMAL_POPULATION_CLOSEOUT_V1.json", closeout)
    print(json.dumps({"terminal_verdict": closeout["terminal_verdict"], "sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
