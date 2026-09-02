#!/usr/bin/env python3
"""Pure deterministic qualification runner for the R5 comparator corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as003pr5.semantic_comparator import compare_run_records
from tests.test_as003pr5_semantic_comparator import CORPUS, PREFORK, _case


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
                "semantic_difference_count": report["semantic_difference_count"],
            }
        )

result = {
    "schema": "AS003PR5_COMPARATOR_QUALIFICATION_V1",
    "directive": "UMBRA-AS-003P-R5",
    "result": "PASS" if false_positives == false_negatives == 0 else "FAIL",
    "case_count": len(CORPUS["cases"]),
    "repeat_runs": 2,
    "observations": len(rows),
    "false_positives": false_positives,
    "false_negatives": false_negatives,
    "generic_uuid_detection": False,
    "organism_constructions": 0,
    "organism_ticks": 0,
    "artifact_sha256": {
        "comparator": digest(ROOT / "experiments/as003pr5/semantic_comparator.py"),
        "source_contract": digest(ROOT / "experiments/as003pr5/AS003PR5_PARITY_SOURCE_CONTRACT.json"),
        "corpus": digest(ROOT / "experiments/as003pr5/AS003PR5_COMPARATOR_CORPUS.json"),
        "tests": digest(ROOT / "tests/test_as003pr5_semantic_comparator.py"),
    },
    "rows": rows,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
