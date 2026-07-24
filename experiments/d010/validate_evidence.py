#!/usr/bin/env python3
"""Independent evidence validator for UMBRA-D-010 (pre-freeze / Task 13)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d010 import evidence as ev
OUT = ROOT / "docs" / "evidence" / "d010"

REQUIRED_FILES = (
    "regression-results.json",
    "temporal-authority-results.json",
    "recurrence-results.json",
    "future-leakage-results.json",
    "anticipation-results.json",
    "revision-results.json",
    "temporal-routine-results.json",
    "autonomy-results.json",
    "absence-safety-results.json",
    "individuality-timing-results.json",
    "restart-downtime-results.json",
    "replay-results.json",
    "boundedness-results.json",
    "experiment-summary.json",
)

FORBIDDEN_SUBSTRINGS = (
    "UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED",
    "TASK 14 AUTHORIZED: YES",
)


def _load(name: str) -> dict:
    path = OUT / name
    if not path.is_file():
        raise SystemExit(f"missing:{name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _forbidden_claims() -> list[str]:
    errors: list[str] = []
    for path in OUT.glob("*"):
        if path.suffix not in {".json", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN_SUBSTRINGS:
            if token in text:
                errors.append(f"forbidden_claim:{path.name}:{token}")
    return errors


def _hash_consistency(rows: list[dict]) -> list[str]:
    if not rows:
        return ["empty_raw_ledger"]
    thr_h = rows[0].get("thresholds_hash")
    errors: list[str] = []
    for row in rows:
        if row.get("thresholds_hash") != thr_h:
            errors.append("mixed_thresholds_hash")
            break
    return errors


def main() -> None:
    errors: list[str] = []
    for name in REQUIRED_FILES:
        if not (OUT / name).is_file():
            errors.append(f"missing_summary:{name}")
    raw_path = OUT / "raw-results.jsonl"
    rows: list[dict] = []
    if raw_path.is_file():
        rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        errors.extend(_hash_consistency(rows))
    errors.extend(_forbidden_claims())
    validation = {
        "directive": ev.DIRECTIVE,
        "pre_freeze": True,
        "errors": errors,
        "pass": not errors,
        "raw_rows": len(rows),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "evidence-validation.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(validation, indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
