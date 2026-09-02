#!/usr/bin/env python3
"""Zero-organism import and protocol preflight for AS-003P-R5."""

from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import umbra_core.runtime as runtime


calls = {"create_organism": 0, "load_organism": 0, "tick_once": 0}


def forbidden_create(*args, **kwargs):
    calls["create_organism"] += 1
    raise RuntimeError("R5 preflight attempted organism creation")


def forbidden_load(*args, **kwargs):
    calls["load_organism"] += 1
    raise RuntimeError("R5 preflight attempted organism load")


def forbidden_tick(*args, **kwargs):
    calls["tick_once"] += 1
    raise RuntimeError("R5 preflight attempted organism tick")


runtime.create_organism = forbidden_create
runtime.load_organism = forbidden_load
runtime.Organism.tick_once = forbidden_tick

modules = [
    "experiments.close02r.qualification",
    "experiments.as003pr5.semantic_comparator",
    "experiments.as003pr5.analysis",
    "experiments.as003pr5.common_root_pair",
    "umbra_core",
]
loaded = {name: importlib.import_module(name).__name__ for name in modules}
specs = {
    name: (None if (spec := importlib.util.find_spec(name)) is None else str(spec.origin))
    for name in modules
}

# Synthetic SQLite backup proof; no UMBRA Store or owner is constructed.
with tempfile.TemporaryDirectory(prefix="as003pr5-preflight-") as temporary:
    source = Path(temporary) / "source.sqlite"
    target = Path(temporary) / "target.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE proof(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO proof VALUES('root','exact')")
        connection.commit()
    with sqlite3.connect(source) as source_connection, sqlite3.connect(target) as target_connection:
        source_connection.backup(target_connection)
    with sqlite3.connect(target) as connection:
        sqlite_backup_equal = connection.execute("SELECT value FROM proof WHERE key='root'").fetchone()[0] == "exact"

result = {
    "schema": "AS003PR5_PROTOCOL_PREFLIGHT_V1",
    "directive": "UMBRA-AS-003P-R5",
    "result": "PASS" if not any(calls.values()) and sqlite_backup_equal and all(specs.values()) else "FAIL",
    "repository_root": str(ROOT),
    "python_executable": sys.executable,
    "python_version": sys.version,
    "module_invocation": f"{sys.executable} -m experiments.as003pr5.common_root_pair orchestrate",
    "resolved_specs": specs,
    "loaded_modules": loaded,
    "sqlite_backup_synthetic_equal": sqlite_backup_equal,
    "barrier_protocol": "persistent child stdin READY/GO barrier",
    "organism_constructions": calls["create_organism"],
    "organism_loads": calls["load_organism"],
    "organism_ticks": calls["tick_once"],
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
