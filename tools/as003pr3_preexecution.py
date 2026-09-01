#!/usr/bin/env python3
"""Static pre-execution integrity gate for UMBRA-AS-003P-R3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r3-semantic-shadow-pair-r1"
)
BASELINE = "237251fd9e6b859284d45fe6da42a54a5e0d05a3"
PROTECTED = (
    "umbra_core/hypothetical/core.py",
    "umbra_core/hypothetical/adapters.py",
    "umbra_core/hypothetical/continuation.py",
    "umbra_core/hypothetical/frame.py",
    "umbra_core/hypothetical/modal.py",
    "umbra_core/hypothetical/shadow.py",
    "umbra_core/runtime.py",
)
LEG_ARTIFACTS = (
    "AS003PR3_PAIRED_EXECUTION_STARTED.json",
    "AS003PR3_CONTROL_RUN_RAW.json",
    "AS003PR3_SHADOW_RUN_RAW.json",
    "AS003PR3_CONTROL_DECISION_TRACE.jsonl",
    "AS003PR3_SHADOW_DECISION_TRACE.jsonl",
    "AS003PR3_PLANNING_SHADOW_TRACE.jsonl",
    "AS003PR3_SEMANTIC_OBSERVER_PARITY.json",
    "AS003PR3_PAIRED_EXECUTION_FINISHED.json",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def evidence_sha(name: str) -> str:
    return digest((EVIDENCE / name).read_bytes())


fingerprints = {}
for path in PROTECTED:
    baseline = digest(git_bytes(BASELINE, path))
    current = digest((ROOT / path).read_bytes())
    fingerprints[path] = {
        "baseline_sha256": baseline,
        "current_sha256": current,
        "byte_identical": baseline == current,
    }

runtime_source = (ROOT / "umbra_core/runtime.py").read_text(encoding="utf-8")
shadow_source = (ROOT / "umbra_core/hypothetical/shadow.py").read_text(encoding="utf-8")
production_delta = subprocess.check_output(
    ["git", "diff", "--name-only", f"{BASELINE}..HEAD", "--", "umbra_core"],
    cwd=ROOT,
    text=True,
).splitlines()
existing_leg_artifacts = [name for name in LEG_ARTIFACTS if (EVIDENCE / name).exists()]
checks = {
    "protected_files_byte_identical": all(row["byte_identical"] for row in fingerprints.values()),
    "production_delta_zero": production_delta == [],
    "as003p_pure_41_of_41": "RESULT 41/41 PASS" in (EVIDENCE / "AS003PR3_AS003P_PURE_TESTS.txt").read_text(),
    "r2_forensic_pure_9_of_9": "9 passed" in (EVIDENCE / "AS003PR3_R2_FORENSIC_PURE_TESTS.txt").read_text(),
    "r3_protocol_analysis_7_of_7": "7 passed" in (EVIDENCE / "AS003PR3_R3_PROTOCOL_ANALYSIS_TESTS.txt").read_text(),
    "authority_3_pass": "PASSED" in (EVIDENCE / "AS003PR3_AUTHORITY_V3.txt").read_text(),
    "governance_pass": "passed" in (EVIDENCE / "AS003PR3_GOVERNANCE_VALIDATION.txt").read_text(),
    "git_diff_check_pass": "git_diff_check=PASS" in (EVIDENCE / "AS003PR3_DIFF_INTEGRITY.txt").read_text(),
    "shadow_default_off": "planning_shadow_path: str | None = field(default=None, repr=False)" in runtime_source,
    "shadow_result_write_only": "write-only" in shadow_source and "behavioral_authority" in shadow_source,
    "shadow_rng_consumption_absent": "organism.rng" not in shadow_source and '"rng_consumed": False' in shadow_source,
    "fresh_root_has_no_leg_artifacts": existing_leg_artifacts == [],
}
result = {
    "schema": "AS003PR3_PREEXECUTION_INTEGRITY_V1",
    "directive": "UMBRA-AS-003P-R3",
    "baseline": BASELINE,
    "current_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "result": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "protected_scientific_fingerprints": fingerprints,
    "protected_production_delta": production_delta,
    "existing_leg_artifacts": existing_leg_artifacts,
    "validation_artifact_sha256": {
        name: evidence_sha(name)
        for name in (
            "AS003PR3_AS003P_PURE_TESTS.txt",
            "AS003PR3_R2_FORENSIC_PURE_TESTS.txt",
            "AS003PR3_R3_PROTOCOL_ANALYSIS_TESTS.txt",
            "AS003PR3_AUTHORITY_V3.txt",
            "AS003PR3_GOVERNANCE_VALIDATION.txt",
            "AS003PR3_DIFF_INTEGRITY.txt",
            "AS003PR3_HARNESS_EQUIVALENCE.json",
            "AS003PR3_IMPORTABILITY_PREFLIGHT.json",
        )
    },
    "organism_constructions": 0,
    "organism_ticks": 0,
    "control_executions": 0,
    "shadow_executions": 0,
    "retries": 0,
    "reseeds": 0,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
