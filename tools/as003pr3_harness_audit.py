#!/usr/bin/env python3
"""Static equivalence audit for the AS-003P-R3 raw-preserving harness."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as003p import shadow_diagnostic as frozen  # noqa: E402
from experiments.as003pr3 import shadow_diagnostic as r3  # noqa: E402


def calls(source: str) -> list[str]:
    tree = ast.parse(source)
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            result.append(node.func.attr)
        elif isinstance(node.func, ast.Name):
            result.append(node.func.id)
    return result


original_source = inspect.getsource(frozen.run_one)
r3_source = inspect.getsource(r3.run_one_raw)
original_calls = calls(original_source)
r3_calls = calls(r3_source)

checks = {
    "fixture_object_identical": r3.frozen.fixture is frozen.fixture,
    "seed_identical": r3.SEED == frozen.SEED == 45878900,
    "horizon_identical": r3.HORIZON == frozen.HORIZON == 500,
    "prepare_call_count_identical": original_calls.count("prepare") == r3_calls.count("prepare") == 1,
    "tick_call_count_identical": original_calls.count("tick_once") == r3_calls.count("tick_once") == 1,
    "tick_loop_identical": "for _ in range(HORIZON)" in original_source and "for _ in range(HORIZON)" in r3_source,
    "regime_identical": 'prepare(SEED, db, "R0")' in original_source and 'prepare(SEED, db, "R0")' in r3_source,
    "decision_trace_identical": "cfg.decision_trace_path" in original_source and "cfg.decision_trace_path" in r3_source,
    "shadow_enablement_identical": "cfg.planning_shadow_path" in original_source and "cfg.planning_shadow_path" in r3_source,
    "timeline_fields_identical": all(
        f'"{field}"' in original_source and f'"{field}"' in r3_source
        for field in ("tick", "capability", "denied", "action_issued", "no_safe_action", "physiology", "outcome")
    ),
    "no_old_normalizer_on_raw_inputs": all(
        token not in r3_source for token in ("_normalized_state", "_normalized_events", "_semantic_runtime_value")
    ),
    "exact_one_control_leg": inspect.getsource(r3.main).count("run_one_raw(shadow=False") == 1,
    "exact_one_shadow_leg": inspect.getsource(r3.main).count("run_one_raw(shadow=True") == 1,
    "no_retry_loop": "while " not in inspect.getsource(r3.main),
}

result = {
    "schema": "AS003PR3_HARNESS_EQUIVALENCE_V1",
    "directive": "UMBRA-AS-003P-R3",
    "result": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "scientific_execution_differences": 0 if all(checks.values()) else None,
    "permitted_differences": [
        {"category": "EVIDENCE_ROOT_ONLY", "detail": "fresh R3 create-once evidence root"},
        {"category": "DIRECTIVE_METADATA_ONLY", "detail": "R3 schema and artifact names"},
        {"category": "PROTOCOL_BOOTSTRAP_ONLY", "detail": "repository-root module invocation"},
        {"category": "RAW_COMPARISON_INPUT_CAPTURE", "detail": "raw state/events retained instead of pre-normalized inputs"},
        {"category": "FROZEN_COMPARATOR_ONLY", "detail": "prospectively locked semantic parity report"}
    ],
    "fixture": {"regime": "R0", "scenario": "S0", "seed": r3.SEED, "horizon": r3.HORIZON},
    "r3_harness_sha256": hashlib.sha256((ROOT / "experiments/as003pr3/shadow_diagnostic.py").read_bytes()).hexdigest(),
    "organism_constructions": 0,
    "organism_ticks": 0,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
