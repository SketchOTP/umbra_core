"""Dependency-free runner for the AS-003N focused pure test module.

The project host lacks pytest.  This runner executes the exact test functions
from the focused module and imports no organism runtime.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys


TEST_PATH = Path(__file__).resolve().parents[1] / "tests" / "test_as003n_hypothetical.py"


def main() -> None:
    repository = TEST_PATH.parents[1]
    if str(repository) not in sys.path:
        sys.path.insert(0, str(repository))
    spec = importlib.util.spec_from_file_location("as003n_pure", TEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("focused AS-003N test module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests = [func for name, func in inspect.getmembers(module, inspect.isfunction) if name.startswith("test_")]
    for func in tests:
        func()
        print(f"PASS {func.__name__}")
    print(f"{len(tests)} focused pure tests passed")


if __name__ == "__main__":
    main()
