#!/usr/bin/env python3
"""Byte-identity and locked-corpus integrity check for the inherited R5 comparator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as003pr5.semantic_comparator import compare_run_records
from tests.test_as003pr5_semantic_comparator import CORPUS, PREFORK, _case


LOCK_COMMIT = "14d9ce3252701d95e840bad6e28b0efd17e6cdd4"
FILES = (
    "experiments/as003pr5/AS003PR5_COMMON_ROOT_CONTRACT.json",
    "experiments/as003pr5/AS003PR5_HABITAT_ROOT_CONTRACT.json",
    "experiments/as003pr5/AS003PR5_PARITY_SOURCE_CONTRACT.json",
    "experiments/as003pr5/AS003PR5_COMPARATOR_CORPUS.json",
    "experiments/as003pr5/AS003PR5_COMPARATOR_LOCK.json",
    "experiments/as003pr5/semantic_comparator.py",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


identity = {}
for relative in FILES:
    current = (ROOT / relative).read_bytes()
    locked = subprocess.check_output(["git", "show", f"{LOCK_COMMIT}:{relative}"], cwd=ROOT)
    identity[relative] = {
        "current_sha256": digest(current),
        "locked_sha256": digest(locked),
        "byte_identical": current == locked,
    }

rows = []
false_positives = 0
false_negatives = 0
for repeat in range(2):
    for case in CORPUS["cases"]:
        left, right = _case(case["id"])
        report = compare_run_records(left, right, pre_fork_exact_ids=PREFORK)
        observed = bool(report["semantic_equal"])
        expected = bool(case["expected_equal"])
        false_positives += int(observed and not expected)
        false_negatives += int((not observed) and expected)
        rows.append(
            {
                "repeat": repeat + 1,
                "case": case["id"],
                "expected_equal": expected,
                "observed_equal": observed,
            }
        )

byte_identical = all(row["byte_identical"] for row in identity.values())
passed = byte_identical and false_positives == false_negatives == 0
result = {
    "schema": "AS003PR5A_COMPARATOR_INHERITANCE_V1",
    "directive": "UMBRA-AS-003P-R5A",
    "result": "PASS" if passed else "FAIL",
    "lock_commit": LOCK_COMMIT,
    "byte_identity": "BYTE_IDENTICAL" if byte_identical else "MISMATCH",
    "files": identity,
    "case_count": len(CORPUS["cases"]),
    "repeat_runs": 2,
    "observations": len(rows),
    "false_positives": false_positives,
    "false_negatives": false_negatives,
    "organism_creations": 0,
    "organism_loads": 0,
    "organism_ticks": 0,
    "rows": rows,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if passed else 1)
