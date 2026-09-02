#!/usr/bin/env python3
"""Zero-organism static/import preflight for the fresh R5A harness."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as003pr5a import common_root_pair
from tools.as003pr5a_evidence import ROOT as EVIDENCE_ROOT


source_path = ROOT / "experiments/as003pr5a/common_root_pair.py"
source = source_path.read_text(encoding="utf-8")
tree = ast.parse(source)
prepare_calls = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    function = node.func
    if isinstance(function, ast.Attribute) and function.attr == "prepare":
        prepare_calls.append(node.lineno)

required = (
    "AS003PR5A_STATE_RECONCILIATION.json",
    "AS003PR5A_METADATA_PROTOCOL_PREFLIGHT.json",
    "AS003PR5A_RETAINED_ROOT_ATTESTATION_CORRECTION.json",
    "AS003PR5A_COMPARATOR_INHERITANCE.json",
    "AS003PR5A_RETAINED_ROOT_CLONE_PROTOCOL.json",
)
checks = {
    "module_resolves": importlib.util.find_spec("experiments.as003pr5a.common_root_pair") is not None,
    "orchestrator_callable": callable(common_root_pair._orchestrate),
    "branch_callable": callable(common_root_pair._branch),
    "retained_root_phase_callable": callable(common_root_pair._retained_root_phase),
    "fixture_prepare_calls_absent": not prepare_calls,
    "fresh_work_root_absent": not common_root_pair.WORK_ROOT.exists(),
    "required_prebranch_evidence_present": all((EVIDENCE_ROOT / name).exists() for name in required),
    "r5a_root_creation_count_locked_zero": "\"root_creation_count\": 0" in source,
}
result = {
    "schema": "AS003PR5A_HARNESS_PROTOCOL_PREFLIGHT_V1",
    "directive": "UMBRA-AS-003P-R5A",
    "result": "PASS" if all(checks.values()) else "FAIL",
    "python_executable": sys.executable,
    "python_version": sys.version,
    "repository_root": str(ROOT),
    "module_file": str(source_path),
    "prepare_call_lines": prepare_calls,
    "checks": checks,
    "organism_creations": 0,
    "organism_loads": 0,
    "organism_ticks": 0,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
