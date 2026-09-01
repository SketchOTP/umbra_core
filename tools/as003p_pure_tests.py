#!/usr/bin/env python3
"""Dependency-free runner for the locked AS-003P focused pure tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import traceback


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
path = ROOT / "tests" / "test_as003p_modal_planning.py"
spec = importlib.util.spec_from_file_location("as003p_tests", path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

failed = 0
tests = sorted((name, value) for name, value in vars(module).items() if name.startswith("test_") and callable(value))
for name, test in tests:
    try:
        test()
        print(f"PASS {name}")
    except Exception:
        failed += 1
        print(f"FAIL {name}")
        traceback.print_exc()
print(f"RESULT {len(tests) - failed}/{len(tests)} PASS")
raise SystemExit(1 if failed else 0)
