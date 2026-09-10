#!/usr/bin/env python3
"""Revalidate affected excluded R1--R3 development regimes after AS-016 repair.

This is deliberately separate from the original mixed R0--R3 development
surface: R0 already has a create-once durable post-repair result, while these
rows must be exercised against the later direct-path continuity change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as016.qualification import run_case
from tools.as016_evidence import ROOT as EVIDENCE_ROOT
from tools.as016_evidence import publish


CASES = (("R1", 41616032), ("R2", 41616033), ("R3", 41616034))
HORIZON = 4_000
WORK = EVIDENCE_ROOT / "AS016_POST_DIRECT_PATH_R1_R3_REVALIDATION_WORK_V1"


def main() -> None:
    if WORK.exists():
        raise FileExistsError(f"create_once_development_work_exists:{WORK}")
    WORK.mkdir(parents=True)
    rows: list[dict[str, object]] = []
    for regime, seed in CASES:
        row = run_case(regime, seed, WORK, HORIZON)
        rows.append(row)
        if row.get("terminal") != "completed" or row.get("ticks") != HORIZON:
            break
    passed = len(rows) == len(CASES) and all(
        row.get("terminal") == "completed" and row.get("ticks") == HORIZON
        for row in rows
    )
    result = {
        "schema": "AS016_POST_DIRECT_PATH_R1_R3_REVALIDATION_V1",
        "directive": "UMBRA-AS-016",
        "classification": "excluded_development_revalidation_not_formal_qualification",
        "formal_seeds_used": [],
        "horizon_ticks": HORIZON,
        "source_change": "direct_regulatory_path_not_proven_preserves_policy_visible_may_route",
        "rows": rows,
        "status": "PASS" if passed else "FAIL",
    }
    digest = publish("AS016_POST_DIRECT_PATH_R1_R3_REVALIDATION_V1.json", result)
    print(json.dumps({"status": result["status"], "sha256": digest}, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
