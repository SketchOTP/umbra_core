#!/usr/bin/env python3
"""Run the AS-016 four-regime development surface with excluded seeds only."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as016.qualification import run_case
from tools.as016_evidence import publish


CASES = (
    ("R0", 41616031),
    ("R1", 41616032),
    ("R2", 41616033),
    ("R3", 41616034),
)
HORIZON = 4_000


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="as016-nonformal-") as directory:
        work = Path(directory)
        rows = [run_case(regime, seed, work, HORIZON) for regime, seed in CASES]
    result = {
        "schema": "AS016_NONFORMAL_R0_R3_SURFACE_V1",
        "directive": "UMBRA-AS-016",
        "classification": "development_only_not_formal_qualification",
        "formal_seeds_used": [],
        "horizon_ticks": HORIZON,
        "rows": rows,
        "status": "PASS" if all(row.get("terminal") == "completed" and row.get("ticks") == HORIZON for row in rows) else "FAIL",
    }
    digest = publish("AS016_NONFORMAL_R0_R3_SURFACE_V1.json", result)
    print(json.dumps({"status": result["status"], "sha256": digest}, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
