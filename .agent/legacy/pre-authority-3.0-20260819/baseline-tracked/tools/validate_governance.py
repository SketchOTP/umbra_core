#!/usr/bin/env python3
"""Reject stale UMBRA authority claims and cross-project contamination."""

from __future__ import annotations

import argparse
from pathlib import Path


AUTHORITY_FILES = (
    ".agent/PROJECT_GOAL.md",
    ".agent/PROJECT_PROFILE.md",
    ".agent/CURRENT.md",
    ".agent/REPO_MAP.md",
    "AGENTS.md",
    "COMMANDMENTS_OF_THE_CODE.md",
    ".cursor/rules/00-core-governance.mdc",
    ".cursor/rules/00-overall_governance.mdc",
    ".cursor/rules/01-ponytail-directive-memory.mdc",
    ".cursor/rules/01-repository-memory.mdc",
    ".cursor/rules/02-mimir-v2.mdc",
    ".cursor/rules/04-umbra-architecture.mdc",
    "docs/architecture/OPEN_QUESTIONS.md",
    "docs/architecture/GOVERNANCE_AND_CAPABILITIES.md",
)
PROHIBITED = (
    "digital cell",
    "protocell",
    "digital chemistry",
    "molecular metabolism",
    "membrane self-production",
    "cell division",
    "cellular reproduction",
    "chemical evolution",
    "open-ended evolution",
)
ALLOWED_CONTEXT = ("not", "outside", "external", "rejected", "historical", "superseded", "quoted prior-art")
REQUIRED_STATUS = (
    "qualified release baseline: d-009",
    "d-009 seal: af35371",
    "d-010 verdict: umbra_d010_performance_fail",
    "d-010 gates 0-12: pass",
    "d-010 gate 13: fail",
    "d-010 stage b v7: not created",
    "d-010 parent mimir: open",
    "next scientific work: not authorized by this directive",
)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in AUTHORITY_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing authority file: {relative}")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            context = " ".join(lines[max(0, index - 2) : index + 1]).lower()
            if any(term in line.lower() for term in PROHIBITED) and not any(
                qualifier in context for qualifier in ALLOWED_CONTEXT
            ):
                errors.append(f"{relative}:{index + 1}: prohibited UMBRA objective: {line.strip()}")
        text = "\n".join(lines).lower()
        if "d-010 in progress" in text:
            errors.append(f"{relative}: stale D-010 in-progress claim")
    profile = root / ".agent/PROJECT_PROFILE.md"
    if profile.is_file():
        text = profile.read_text(encoding="utf-8").lower()
        for claim in REQUIRED_STATUS:
            if claim not in text:
                errors.append(f".agent/PROJECT_PROFILE.md: missing status claim: {claim}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root)
    for error in errors:
        print(error)
    if errors:
        return 1
    print("governance validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
