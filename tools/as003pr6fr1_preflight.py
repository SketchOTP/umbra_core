"""Complete no-organism executable import preflight for R6F-R1."""

from __future__ import annotations

import importlib
import json
import py_compile
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
INTERPRETER = Path("/home/sketch/cs14n-runtime/bin/python")
MODULE = "experiments.as003pr6fr1.common_root_assay"
sys.path.insert(0, str(REPO))
DIRECT_DEPENDENCIES = (
    "experiments.d009.run_experiment",
    "experiments.d009.scenario_plants",
    "umbra_core.arbitration",
    "umbra_core.decision_trace",
    "umbra_core.habitat.engine",
    "umbra_core.physiology",
    "umbra_core.recoverability.contracts",
    "umbra_core.runtime",
    "umbra_core.temporal.config",
    "umbra_core.world_model",
)


def main() -> None:
    modules = sorted((REPO / "experiments/as003pr6fr1").glob("*.py"))
    for path in modules:
        py_compile.compile(str(path), doraise=True)

    decision_trace = importlib.import_module("umbra_core.decision_trace")
    physiology = importlib.import_module("umbra_core.physiology")
    fingerprint = getattr(decision_trace, "canonical_fingerprint")
    branches = getattr(physiology, "verified_outcome_effect_branches")
    pure_probe = {
        "fingerprint_callable": callable(fingerprint),
        "fingerprint_probe": fingerprint({"r6fr1": "pure"}),
        "branches_callable": callable(branches),
        "branches_probe_count": len(branches("IDLE")),
    }
    imported = {name: bool(importlib.import_module(name)) for name in DIRECT_DEPENDENCIES}
    import_check = subprocess.run(
        [str(INTERPRETER), "-c", f"import {MODULE}; print('R6FR1_IMPORT_OK')"],
        cwd=REPO,
        env={key: value for key, value in __import__("os").environ.items() if key != "PYTHONPATH"},
        capture_output=True,
        text=True,
        check=False,
    )
    result = {
        "schema": "AS003PR6FR1_EXECUTABLE_PREFLIGHT_V1",
        "repository": str(REPO),
        "interpreter": str(INTERPRETER),
        "python_version": sys.version.split()[0],
        "compiled_modules": [str(path.relative_to(REPO)) for path in modules],
        "direct_dependencies": imported,
        "symbol_resolution": {
            "canonical_fingerprint": "umbra_core.decision_trace",
            "verified_outcome_effect_branches": "umbra_core.physiology",
            **pure_probe,
        },
        "full_assay_import": {
            "module": MODULE,
            "exit_status": import_check.returncode,
            "stdout": import_check.stdout.strip(),
            "stderr": import_check.stderr.strip(),
            "main_called": False,
            "run_once_called": False,
            "organism_created": 0,
            "ticks": 0,
        },
        "status": "PASS" if import_check.returncode == 0 and all(imported.values()) else "FAIL",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
