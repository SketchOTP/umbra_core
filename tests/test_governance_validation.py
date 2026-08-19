from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("governance_validator", ROOT / "tools" / "validate_governance.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def _authority_root(tmp_path: Path) -> Path:
    for relative in (*validator.AUTHORITY_FILES, *validator.AUTHORITY_V3_FILES):
        source = ROOT / relative
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, path)
    for relative in validator.LEGACY_ARCHIVE_HASHES:
        source = ROOT / relative
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, path)
    (tmp_path / ".agent/tasks/active").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agent/tasks/completed").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agent/tasks/active/.gitkeep").write_text(
        "# Preserves the Authority 3.0 active task-packet directory.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_corrected_active_governance_passes() -> None:
    assert validator.validate(ROOT) == []


def test_rejects_digital_cell_goal_statement(tmp_path: Path) -> None:
    root = _authority_root(tmp_path)
    (root / ".agent/PROJECT_GOAL.md").write_text("Digital Cell is an UMBRA objective.\n", encoding="utf-8")
    assert any("prohibited UMBRA objective" in error for error in validator.validate(root))


def test_rejects_chemistry_optional_statement(tmp_path: Path) -> None:
    root = _authority_root(tmp_path)
    (root / ".agent/PROJECT_PROFILE.md").write_text(
        "Digital chemistry is optional UMBRA work.\n" + "\n".join(validator.REQUIRED_STATUS), encoding="utf-8"
    )
    assert any("prohibited UMBRA objective" in error for error in validator.validate(root))


def test_rejects_stale_d010_in_progress_claim(tmp_path: Path) -> None:
    root = _authority_root(tmp_path)
    (root / ".agent/CURRENT.md").write_text("D-010 in progress\n", encoding="utf-8")
    assert any("stale D-010 in-progress claim" in error for error in validator.validate(root))


def test_permits_rejected_or_historical_references(tmp_path: Path) -> None:
    root = _authority_root(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8")
        + "\nHistorical quoted prior-art record: protocell work is rejected and external to UMBRA CORE.\n",
        encoding="utf-8",
    )
    assert validator.validate(root) == []


def test_rejects_missing_authority_v3_result_contract(tmp_path: Path) -> None:
    root = _authority_root(tmp_path)
    (root / ".agents/skills/authority/references/result-contract.md").unlink()
    assert any("missing authority file" in error for error in validator.validate(root))


def test_rejects_obsolete_jcodemunch_router_requirement(tmp_path: Path) -> None:
    root = _authority_root(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8") + "\nAlways use jCodemunch.\n",
        encoding="utf-8",
    )
    assert any("jCodemunch" in error for error in validator.validate(root))


def test_rejects_legacy_archive_mutation(tmp_path: Path) -> None:
    root = _authority_root(tmp_path)
    relative = next(iter(validator.LEGACY_ARCHIVE_HASHES))
    path = root / relative
    path.write_bytes(path.read_bytes() + b"mutated")
    assert any("legacy archive hash mismatch" in error for error in validator.validate(root))


def test_rejects_legacy_authority_skill_as_active_router(tmp_path: Path) -> None:
    root = _authority_root(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8")
        + "\nRead .agents/skills/authority-governance/SKILL.md.\n",
        encoding="utf-8",
    )
    assert any("legacy authority-governance" in error for error in validator.validate(root))
