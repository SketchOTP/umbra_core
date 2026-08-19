from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("governance_validator", ROOT / "tools" / "validate_governance.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def _authority_root(tmp_path: Path) -> Path:
    for relative in validator.AUTHORITY_FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "external to UMBRA CORE\n"
        if relative == ".agent/PROJECT_PROFILE.md":
            content += "\n".join(validator.REQUIRED_STATUS)
        path.write_text(content, encoding="utf-8")
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
    (root / "AGENTS.md").write_text(
        "Historical quoted prior-art record: protocell work is rejected and external to UMBRA CORE.\n",
        encoding="utf-8",
    )
    assert validator.validate(root) == []
