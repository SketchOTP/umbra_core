#!/usr/bin/env python3
"""Run the project-specific Authority 3.0 governance validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_governance.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("umbra_governance_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        print(f"BLOCKED: unable to load {VALIDATOR}")
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    errors = module.validate(ROOT)
    for error in errors:
        print(error)
    if errors:
        print(f"Authority 3.0 validation FAILED: {len(errors)} error(s)")
        return 1
    print("Authority 3.0 validation PASSED")
    print(f"- schema: 3.0")
    print(f"- required active files: {len(module.AUTHORITY_V3_FILES)}")
    print(f"- preserved legacy artifacts: {len(module.LEGACY_ARCHIVE_HASHES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
