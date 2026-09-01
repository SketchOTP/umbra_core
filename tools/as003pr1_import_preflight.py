#!/usr/bin/env python3
"""Import-only AS-003P-R1 preflight; never calls fixture or harness main."""

from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import umbra_core.runtime as runtime


calls = {"create_organism": 0, "load_organism": 0}


def forbidden_create(*args, **kwargs):
    calls["create_organism"] += 1
    raise RuntimeError("AS003PR1 import preflight attempted organism creation")


def forbidden_load(*args, **kwargs):
    calls["load_organism"] += 1
    raise RuntimeError("AS003PR1 import preflight attempted organism load")


runtime.create_organism = forbidden_create
runtime.load_organism = forbidden_load

fixture = importlib.import_module("experiments.close02r.qualification")
harness = importlib.import_module("experiments.as003pr1.shadow_diagnostic")

specs = {}
for name in (
    "experiments.close02r.qualification",
    "experiments.as003pr1.shadow_diagnostic",
    "umbra_core",
):
    spec = importlib.util.find_spec(name)
    specs[name] = None if spec is None else str(spec.origin)

result = {
    "schema": "AS003PR1_IMPORT_ONLY_PREFLIGHT_STDOUT_V1",
    "repository_root": str(ROOT),
    "python_executable": sys.executable,
    "python_version": sys.version,
    "sys_path": sys.path,
    "resolved_specs": specs,
    "fixture_module": fixture.__name__,
    "harness_module": harness.__name__,
    "harness_has_main": callable(harness.main),
    "fixture_prepare_called": False,
    "harness_main_called": False,
    "organism_create_calls": calls["create_organism"],
    "organism_load_calls": calls["load_organism"],
    "organism_ticks": 0,
    "result": "PASS" if not any(calls.values()) else "FAIL",
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
