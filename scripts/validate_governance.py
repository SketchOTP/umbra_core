#!/usr/bin/env python3
"""Compatibility entry point for UMBRA Authority 3.0 governance validation."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def load_validator(root: Path):
    validator_path = root / "tools" / "validate_governance.py"
    spec = importlib.util.spec_from_file_location("umbra_governance_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--mode",
        default="AUTHORITY_3",
        help="Accepted for legacy command compatibility; Authority 3.0 has one active project mode.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        validator = load_validator(root)
    except RuntimeError as error:
        print(f"Governance validation BLOCKED: {error}")
        return 1
    errors = validator.validate(root)
    for error in errors:
        print(error)
    if errors:
        print(f"Governance validation FAILED: {len(errors)} error(s)")
        return 1
    print("Governance validation PASSED")
    print("- Authority schema: 3.0")
    if args.mode != "AUTHORITY_3":
        print(f"- Legacy --mode {args.mode!r} accepted as a compatibility alias")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
