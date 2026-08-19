#!/usr/bin/env python3
"""Deterministic positive and negative tests for UMBRA Authority 3.0 validation."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate_governance.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("umbra_governance_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_fixture(destination: Path, validator) -> None:
    for relative in (*validator.AUTHORITY_FILES, *validator.AUTHORITY_V3_FILES):
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for relative in validator.LEGACY_ARCHIVE_HASHES:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (destination / ".agent/tasks/active").mkdir(parents=True, exist_ok=True)
    (destination / ".agent/tasks/completed").mkdir(parents=True, exist_ok=True)
    (destination / ".agent/tasks/active/.gitkeep").write_text(
        "# Preserves the Authority 3.0 active task-packet directory.\n",
        encoding="utf-8",
    )


def expect_failure(name: str, mutate, validator) -> None:
    with tempfile.TemporaryDirectory(prefix="umbra-authority3-") as directory:
        fixture = Path(directory) / "fixture"
        fixture.mkdir()
        copy_fixture(fixture, validator)
        mutate(fixture)
        errors = validator.validate(fixture)
        if not errors:
            raise AssertionError(f"{name}: validator unexpectedly passed")


def main() -> int:
    validator = load_validator()
    errors = validator.validate(ROOT)
    if errors:
        raise AssertionError("clean Authority 3.0 repository failed:\n" + "\n".join(errors))

    expect_failure(
        "missing result contract",
        lambda root: (root / ".agents/skills/authority/references/result-contract.md").unlink(),
        validator,
    )
    expect_failure(
        "obsolete jCodemunch router",
        lambda root: (root / "AGENTS.md").write_text(
            (root / "AGENTS.md").read_text(encoding="utf-8")
            + "\nAlways use jCodemunch.\n",
            encoding="utf-8",
        ),
        validator,
    )
    expect_failure(
        "legacy archive mutation",
        lambda root: (
            lambda path: path.write_bytes(path.read_bytes() + b"mutation")
        )(root / next(iter(validator.LEGACY_ARCHIVE_HASHES))),
        validator,
    )
    expect_failure(
        "legacy workflow reactivated",
        lambda root: (root / "AGENTS.md").write_text(
            (root / "AGENTS.md").read_text(encoding="utf-8")
            + "\nRead .agents/skills/authority-governance/SKILL.md.\n",
            encoding="utf-8",
        ),
        validator,
    )
    print("Authority 3.0 governance tests PASSED")
    print("- clean repository positive fixture")
    print("- 4 fail-closed negative fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
