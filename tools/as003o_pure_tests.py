"""Dependency-free runner for AS-003O focused pure proof."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys


TEST_PATH = Path(__file__).resolve().parents[1] / "tests" / "test_as003o_source_backed_continuation.py"


def main() -> None:
    repository = TEST_PATH.parents[1]
    sys.path.insert(0, str(repository)) if str(repository) not in sys.path else None
    spec = importlib.util.spec_from_file_location("as003o_pure", TEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("focused AS-003O test module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests = [item for name, item in inspect.getmembers(module, inspect.isfunction) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} focused pure tests passed")


if __name__ == "__main__":
    main()
