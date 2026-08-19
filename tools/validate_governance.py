#!/usr/bin/env python3
"""Validate UMBRA project truth and the active Authority 3.0 governance surface."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


AUTHORITY_FILES = (
    ".agent/PROJECT_GOAL.md",
    ".agent/PROJECT_PROFILE.md",
    ".agent/CURRENT.md",
    ".agent/REPO_MAP.md",
    ".agent/INDEX.md",
    ".agent/EXTERNAL.md",
    ".agent/tasks/README.md",
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
AUTHORITY_V3_FILES = (
    ".agents/skills/authority/SKILL.md",
    ".agents/skills/authority/references/directive-contract.md",
    ".agents/skills/authority/references/result-contract.md",
    ".agents/skills/authority/references/evidence.md",
    ".agents/skills/authority/references/state-files.md",
    ".agents/skills/authority/references/safety.md",
    ".agents/skills/external-discovery/SKILL.md",
)
LEGACY_ARCHIVE_HASHES = {
    ".agent/legacy/pre-authority-3.0-20260819/state/CURRENT.md":
        "cbe46686f0a99785d166e6868be3632d5d69eb8ab0ef75e0ddc4bc4659a37b82",
    ".agent/legacy/pre-authority-3.0-20260819/state/PROJECT_PROFILE.md":
        "8d0d7eb8481024134f9cd958db8a6ae9ab2e2301937e966e815227089f5a970c",
    ".agent/legacy/pre-authority-3.0-20260819/state/REPO_MAP.md":
        "4830d3e8b2782dc84daab8ce4aadf3f69a5bd1dc667f463e0f261abff7838cdc",
    ".agent/legacy/pre-authority-3.0-20260819/skills/external-discovery/SKILL.md":
        "07b74825d47d07b56bd373974b0e949aa3b743142b67b02bbe6378379125fe0c",
    ".agent/legacy/pre-authority-3.0-20260819/validators/validate_governance.py":
        "dd7e713039619343590c6bb177d49f56a96221a06e33600866024858680de6ad",
    ".agent/legacy/pre-authority-3.0-20260819/validators/test_validate_governance.py":
        "c3070bbc2a39320b40032fe0208ae0755e7efb8e48f4891ca78f9fb5cd98b351",
    ".agent/legacy/pre-authority-3.0-20260819/baseline-tracked/AGENTS.md":
        "78c9cf37dfa539c6cf72ac87d38c1224dbdccb67d82aa727e219f30f5c205bf9",
    ".agent/legacy/pre-authority-3.0-20260819/baseline-tracked/tools/validate_governance.py":
        "d31051f2db695eb74ea7c16992bb6cd3213195fb026f52b12f81c586e6840dd2",
    ".agent/legacy/pre-authority-3.0-20260819/baseline-tracked/tests/test_governance_validation.py":
        "532452d3a1ca40e675f2658579806f0f23a867b863413c924642d4fa559cde53",
}
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
    "qualified sequential baseline: d-009 seal `af35371`",
    "d-010 verdict: `umbra_d010_performance_fail`",
    "d-012b2 remains `umbra_d012b_p0_integrity_fail`",
    "d-013ao is accepted as `d013ao_shadow_recoverability_view_qualified`",
    "d-013ap is authorized only as a non-formal",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in (*AUTHORITY_FILES, *AUTHORITY_V3_FILES):
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
    agents = root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        required_router = (
            "# Authority Repository Agent Router",
            ".agents/skills/authority/SKILL.md",
            ".agent/INDEX.md",
            "E5_OPERATIONALLY_OBSERVED",
            "CODEX RESULT",
        )
        for claim in required_router:
            if claim not in text:
                errors.append(f"AGENTS.md: missing Authority 3.0 router claim: {claim}")
        lower = text.lower()
        if "jcodemunch" in lower or "codemunch" in lower:
            errors.append("AGENTS.md: obsolete jCodemunch requirement is prohibited")
        if "authority-governance/skill.md" in lower:
            errors.append("AGENTS.md: legacy authority-governance skill remains active")
        if "commandments_of_the_code.md" in lower:
            errors.append("AGENTS.md: legacy Commandments remain an active parallel router")
    index = root / ".agent/INDEX.md"
    if index.is_file():
        text = index.read_text(encoding="utf-8")
        for claim in (
            "Authority schema: 3.0",
            "Project: UMBRA-CORE",
            "https://github.com/SketchOTP/umbra_core",
            "PROJECT_GOAL.md",
            "PROJECT_PROFILE.md",
            "CURRENT.md",
        ):
            if claim not in text:
                errors.append(f".agent/INDEX.md: missing project-specific claim: {claim}")
    for relative in (".agent/INDEX.md", ".agent/PROJECT_PROFILE.md", ".agent/CURRENT.md"):
        path = root / relative
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if "<PROJECT " in text or "<URL>" in text or "<STAGE>" in text:
                errors.append(f"{relative}: unresolved Authority template placeholder")
    for relative, expected in LEGACY_ARCHIVE_HASHES.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing Authority 3.0 legacy archive file: {relative}")
        elif sha256(path) != expected:
            errors.append(f"Authority 3.0 legacy archive hash mismatch: {relative}")
    for relative in (".agent/tasks/active", ".agent/tasks/completed"):
        if not (root / relative).is_dir():
            errors.append(f"missing Authority 3.0 task directory: {relative}")
    if not (root / ".agent/tasks/active/.gitkeep").is_file():
        errors.append("missing Authority 3.0 active task-directory placeholder")
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
